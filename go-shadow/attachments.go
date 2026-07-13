package main

import (
	"database/sql"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

func (s *server) handleAttachmentDetail(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/api/attachments/")
	attachmentID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}

	if r.Method == http.MethodDelete {
		if !s.runtime.enableAttachmentWrite {
			writeError(w, http.StatusMethodNotAllowed, "Attachment write route is disabled")
			return
		}
		s.deleteAttachment(w, attachmentID)
		return
	}
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", "GET, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if boolString(r, "raw") {
		if !s.runtime.enableAttachmentRawRead {
			if s.runtime.enableAttachmentTextRead {
				writeError(w, http.StatusMethodNotAllowed, "Raw attachment responses remain Python-owned")
				return
			}
			writeError(w, http.StatusMethodNotAllowed, "Attachment raw read route is disabled")
			return
		}
		s.serveAttachmentRaw(w, r, attachmentID)
		return
	}
	if !s.runtime.enableAttachmentTextRead && !s.runtime.enableAttachmentRawRead {
		writeError(w, http.StatusMethodNotAllowed, "Attachment text read route is disabled")
		return
	}
	s.readAttachmentText(w, attachmentID)
}

func (s *server) serveAttachmentRaw(w http.ResponseWriter, r *http.Request, attachmentID int) {
	row := s.db.QueryRow(`
		SELECT id, file_path, file_type, title
		FROM Note_Attachments
		WHERE id = ?`, attachmentID)

	var id int
	var filePath, fileType, title sql.NullString
	if err := row.Scan(&id, &filePath, &fileType, &title); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Attachment not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	resolved, _, ok := resolveAttachmentRawFile(s.runtime.dataDir, nullableString(filePath), nullableString(fileType))
	if !ok {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}
	file, err := os.Open(resolved)
	if err != nil {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}

	if contentType := attachmentRawContentType(resolved); contentType != "" {
		w.Header().Set("Content-Type", contentType)
	}
	http.ServeContent(w, r, safeAttachmentDownloadName(nullableString(title), resolved), info.ModTime(), file)
}

func (s *server) readAttachmentText(w http.ResponseWriter, attachmentID int) {
	row := s.db.QueryRow(`
		SELECT id, file_path, file_type, title
		FROM Note_Attachments
		WHERE id = ?`, attachmentID)

	var id int
	var filePath, fileType, title sql.NullString
	if err := row.Scan(&id, &filePath, &fileType, &title); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Attachment not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	resolved, _, ok := resolveAttachmentFile(s.runtime.dataDir, nullableString(filePath), nullableString(fileType))
	if !ok {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}
	content, err := os.ReadFile(resolved)
	if err != nil {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}

	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"id":        id,
			"title":     nullableString(title),
			"file_type": nullableString(fileType),
			"content":   normalizeTextContent(string(content)),
		},
	})
}

func normalizeTextContent(content string) string {
	content = strings.ReplaceAll(content, "\r\n", "\n")
	return strings.ReplaceAll(content, "\r", "\n")
}

func (s *server) listNoteAttachments(w http.ResponseWriter, noteID int) {
	var existing int
	if err := s.db.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existing); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	rows, err := s.db.Query(`
		SELECT id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at
		FROM Note_Attachments
		WHERE note_id = ?
		ORDER BY created_at DESC`, noteID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	items := []response{}
	for rows.Next() {
		var id int
		var filePath, fileType, title, createdAt sql.NullString
		var sizeBytes, isAutoExtracted sql.NullInt64
		if err := rows.Scan(&id, &filePath, &fileType, &title, &sizeBytes, &isAutoExtracted, &createdAt); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		items = append(items, response{
			"id":                id,
			"file_path":         nullableString(filePath),
			"file_type":         nullableString(fileType),
			"title":             nullableStringOrNil(title),
			"size_bytes":        nullableIntOrNil(sizeBytes),
			"is_auto_extracted": isAutoExtracted.Valid && isAutoExtracted.Int64 != 0,
			"created_at":        sqliteDateTimeString(createdAt),
		})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": items})
}

func (s *server) uploadAttachment(w http.ResponseWriter, r *http.Request, noteID int) {
	var existing int
	if err := s.db.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existing); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, maxAttachmentFileBytes+attachmentUploadMultipartOverheadBytes)
	if err := r.ParseMultipartForm(maxAttachmentFileBytes); err != nil {
		if strings.Contains(strings.ToLower(err.Error()), "request body too large") {
			writeError(w, http.StatusBadRequest, attachmentTooLargeMessage())
			return
		}
		writeError(w, http.StatusBadRequest, "No file provided")
		return
	}
	if r.MultipartForm != nil {
		defer r.MultipartForm.RemoveAll()
	}
	file, header, err := r.FormFile("file")
	if err != nil {
		writeError(w, http.StatusBadRequest, "No file provided")
		return
	}
	defer file.Close()
	if header.Filename == "" {
		writeError(w, http.StatusBadRequest, "No file selected")
		return
	}
	if !allowedAttachmentFilename(header.Filename) {
		writeError(w, http.StatusBadRequest, "File type not allowed. Allowed types: markdown, md, txt")
		return
	}

	originalName := sanitizeAttachmentFilename(header.Filename)
	baseName, ext := splitAttachmentName(originalName)
	uniqueFilename := fmt.Sprintf("%s_%s%s", baseName, time.Now().Format("20060102_150405"), ext)
	if uniqueFilename == "" || uniqueFilename == "." {
		writeError(w, http.StatusBadRequest, "No file selected")
		return
	}

	if err := os.MkdirAll(s.runtime.attachmentsDir, 0755); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	targetPath := filepath.Join(s.runtime.attachmentsDir, uniqueFilename)
	target, err := os.OpenFile(targetPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	sizeBytes, copyErr := io.Copy(target, io.LimitReader(file, maxAttachmentFileBytes+1))
	closeErr := target.Close()
	if copyErr != nil {
		_ = os.Remove(targetPath)
		writeError(w, http.StatusInternalServerError, copyErr.Error())
		return
	}
	if sizeBytes > maxAttachmentFileBytes {
		_ = os.Remove(targetPath)
		writeError(w, http.StatusBadRequest, attachmentTooLargeMessage())
		return
	}
	if closeErr != nil {
		_ = os.Remove(targetPath)
		writeError(w, http.StatusInternalServerError, closeErr.Error())
		return
	}

	title := r.FormValue("title")
	if title == "" {
		title = baseName
	}
	relativePath := path.Join("docs/attachments", filepath.ToSlash(uniqueFilename))
	cursor, err := s.db.Exec(`
		INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
		VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)`,
		noteID, relativePath, strings.TrimPrefix(ext, "."), title, sizeBytes)
	if err != nil {
		_ = os.Remove(targetPath)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	attachmentID, err := cursor.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"id": attachmentID, "file_path": relativePath, "title": title, "size_bytes": sizeBytes,
	}})
}

func attachmentTooLargeMessage() string {
	return fmt.Sprintf("Attachment too large. Maximum size: %dMB", maxAttachmentFileBytes/(1024*1024))
}

func (s *server) deleteAttachment(w http.ResponseWriter, attachmentID int) {
	var filePath sql.NullString
	if err := s.db.QueryRow("SELECT file_path FROM Note_Attachments WHERE id = ?", attachmentID).Scan(&filePath); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Attachment not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if resolved, ok := resolveAttachmentMutationPath(s.runtime.dataDir, nullableString(filePath)); ok {
		if err := os.Remove(resolved); err != nil && !os.IsNotExist(err) {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if _, err := s.db.Exec("DELETE FROM Note_Attachments WHERE id = ?", attachmentID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func allowedAttachmentFilename(filename string) bool {
	name := filepath.Base(filename)
	ext := strings.TrimPrefix(strings.ToLower(filepath.Ext(name)), ".")
	return ext == "md" || ext == "txt" || ext == "markdown"
}

func sanitizeAttachmentFilename(filename string) string {
	name := filepath.Base(filename)
	return regexp.MustCompile(`[^\w\-_\. ]`).ReplaceAllString(name, "")
}

func splitAttachmentName(filename string) (string, string) {
	ext := filepath.Ext(filename)
	return strings.TrimSuffix(filename, ext), ext
}

func resolveAttachmentMutationPath(dataDir, relativePath string) (string, bool) {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	if relativePath == "" || filepath.IsAbs(relativePath) || filepath.VolumeName(relativePath) != "" || strings.Contains(relativePath, ":") {
		return "", false
	}
	cleaned := path.Clean(relativePath)
	if cleaned == "." || strings.HasPrefix(cleaned, "../") || cleaned == ".." || !strings.HasPrefix(cleaned, "docs/attachments/") {
		return "", false
	}
	root, err := filepath.Abs(dataDir)
	if err != nil {
		return "", false
	}
	candidate := filepath.Join(root, filepath.FromSlash(cleaned))
	absCandidate, err := filepath.Abs(candidate)
	if err != nil || !isSubpath(absCandidate, root) {
		return "", false
	}
	return absCandidate, true
}
