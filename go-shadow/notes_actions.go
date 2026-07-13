package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

func nullableVariantParent(noteID int, asVariant bool) any {
	if !asVariant {
		return nil
	}
	return noteID
}

func (s *server) handleNoteDetail(w http.ResponseWriter, r *http.Request) {
	rel := strings.TrimPrefix(r.URL.Path, "/api/notes/")
	if rel == "import/md" {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableImportExport {
			_, _ = io.Copy(io.Discard, r.Body)
			writeError(w, http.StatusMethodNotAllowed, "Import/export route is disabled")
			return
		}
		s.importMarkdown(w, r)
		return
	}
	if rel == "export/batch" {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableImportExport {
			_, _ = io.Copy(io.Discard, r.Body)
			writeError(w, http.StatusMethodNotAllowed, "Import/export route is disabled")
			return
		}
		s.exportBatchMarkdown(w, r)
		return
	}
	if rel == "reorder" {
		if r.Method != http.MethodPut {
			w.Header().Set("Allow", http.MethodPut)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.reorderNotes(w, r)
		return
	}
	if strings.HasPrefix(rel, "batch/") {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.handleNoteBatch(w, r, strings.TrimPrefix(rel, "batch/"))
		return
	}

	parts := strings.Split(rel, "/")
	if len(parts) == 0 {
		http.NotFound(w, r)
		return
	}
	noteID, err := strconv.Atoi(parts[0])
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if len(parts) == 2 && parts[1] == "attachments" {
		if r.Method != http.MethodGet && r.Method != http.MethodPost {
			w.Header().Set("Allow", "GET, POST")
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableAttachmentWrite {
			if r.Method == http.MethodPost {
				_, _ = io.Copy(io.Discard, r.Body)
			}
			writeError(w, http.StatusMethodNotAllowed, "Attachment write route is disabled")
			return
		}
		if r.Method == http.MethodGet {
			s.listNoteAttachments(w, noteID)
			return
		}
		s.uploadAttachment(w, r, noteID)
		return
	}
	if len(parts) > 1 {
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.handleNoteAction(w, r, noteID, parts[1:])
		return
	}
	if r.Method == http.MethodPut {
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.updateNote(w, r, noteID)
		return
	}
	if r.Method == http.MethodDelete {
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.deleteNote(w, noteID)
		return
	}
	if !requireGET(w, r) {
		return
	}
	row := s.db.QueryRow(`
		SELECT n.id, n.title, n.content, COALESCE(c.name, 'Uncategorized') AS category_name,
		       n.remarks, n.cover_image, COALESCE(n.cover_position, 'top') AS cover_position,
		       COALESCE(n.editor_layout, 'single') AS editor_layout,
		       COALESCE(n.is_pinned, 0) AS is_pinned, COALESCE(n.is_archived, 0) AS is_archived,
		       n.category_id, n.created_at, n.updated_at, n.prompt_params, n.parent_id, p.title AS parent_title,
		       (SELECT COUNT(*) FROM Notes child WHERE child.parent_id = n.id) AS variants_count
		FROM Notes n
		LEFT JOIN Categories c ON n.category_id = c.id
		LEFT JOIN Notes p ON n.parent_id = p.id
		WHERE n.id = ?`, noteID)

	var id, isPinned, isArchived, variantsCount int
	var title, content, categoryName, coverPosition, editorLayout, createdAt, updatedAt sql.NullString
	var remarks, coverImage, promptParams, parentTitle sql.NullString
	var categoryID, parentID sql.NullInt64
	if err := row.Scan(&id, &title, &content, &categoryName, &remarks, &coverImage, &coverPosition, &editorLayout, &isPinned, &isArchived, &categoryID, &createdAt, &updatedAt, &promptParams, &parentID, &parentTitle, &variantsCount); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	tags, err := s.noteTags(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	urls, err := s.noteURLs(id)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"id": id, "title": nullableString(title), "content": nullableString(content),
		"type": nullableString(categoryName), "remarks": nullableStringOrNil(remarks),
		"cover_image": nullableStringOrNil(coverImage), "cover_position": nullableString(coverPosition),
		"editor_layout": nullableString(editorLayout), "is_pinned": isPinned != 0,
		"is_archived": isArchived != 0, "category_id": nullableIntOrNil(categoryID),
		"prompt_params": parseJSONOrNil(promptParams), "created_at": nullableString(createdAt),
		"updated_at": nullableString(updatedAt), "tags": tags, "urls": urls,
		"parent_id": nullableIntOrNil(parentID), "parent_title": nullableStringOrNil(parentTitle),
		"variants_count": variantsCount,
	}})
}

func (s *server) handleNoteAction(w http.ResponseWriter, r *http.Request, noteID int, parts []string) {
	switch parts[0] {
	case "pin":
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.toggleNoteBool(w, r, noteID, "is_pinned", "pinned")
	case "archive":
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.toggleNoteBool(w, r, noteID, "is_archived", "archived")
	case "duplicate":
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.duplicateNote(w, r, noteID)
	case "history":
		if len(parts) != 1 {
			http.NotFound(w, r)
			return
		}
		if r.Method == http.MethodGet {
			s.getNoteHistory(w, noteID)
			return
		}
		if r.Method == http.MethodDelete {
			s.deleteNoteHistory(w, noteID)
			return
		}
		w.Header().Set("Allow", "GET, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	case "check_separation":
		if r.Method != http.MethodGet || len(parts) != 1 {
			w.Header().Set("Allow", http.MethodGet)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.checkSeparation(w, noteID)
	case "separate":
		if r.Method != http.MethodPost || len(parts) != 1 {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.separateContent(w, r, noteID)
	case "restore":
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if len(parts) == 1 {
			s.restoreSeparatedContent(w, noteID)
			return
		}
		if len(parts) != 2 {
			http.NotFound(w, r)
			return
		}
		historyID, err := strconv.Atoi(parts[1])
		if err != nil {
			http.NotFound(w, r)
			return
		}
		_, _ = io.Copy(io.Discard, r.Body)
		s.restoreNoteVersion(w, noteID, historyID)
	default:
		http.NotFound(w, r)
	}
}

func (s *server) checkSeparation(w http.ResponseWriter, noteID int) {
	var content sql.NullString
	if err := s.db.QueryRow("SELECT content FROM Notes WHERE id = ?", noteID).Scan(&content); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	contentLength := len([]rune(nullableString(content)))
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"should_separate": contentLength > separationThreshold,
			"content_length":  contentLength,
			"threshold":       separationThreshold,
		},
	})
}

func (s *server) separateContent(w http.ResponseWriter, r *http.Request, noteID int) {
	payload := map[string]any{}
	_ = json.NewDecoder(r.Body).Decode(&payload)
	previewLen, ok := intField(payload, "preview_length")
	if !ok || previewLen <= 0 {
		previewLen = separationPreviewLength
	}

	var title, content sql.NullString
	if err := s.db.QueryRow("SELECT title, content FROM Notes WHERE id = ?", noteID).Scan(&title, &content); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	fullContent := nullableString(content)
	originalLength := len([]rune(fullContent))
	if originalLength <= separationThreshold {
		writeJSON(w, http.StatusOK, response{
			"status":  "info",
			"message": fmt.Sprintf("Content length (%d) is under threshold (%d), no separation needed", originalLength, separationThreshold),
		})
		return
	}

	if err := os.MkdirAll(s.notesDirectory(), 0755); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	filename := fmt.Sprintf("note_%d.md", noteID)
	absPath := filepath.Join(s.notesDirectory(), filename)
	if !isSubpath(absPath, s.runtime.dataDir) {
		writeError(w, http.StatusInternalServerError, "unsafe notes path")
		return
	}
	if err := os.WriteFile(absPath, []byte(fullContent), 0644); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	info, err := os.Stat(absPath)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	relativePath := path.Join("docs", "notes", filename)
	attachmentTitle := nullableString(title) + " (完整內容)"
	preview := separatedPreview(fullContent, previewLen)

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var attachmentID int
	err = tx.QueryRow("SELECT id FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1", noteID).Scan(&attachmentID)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if attachmentID != 0 {
		if _, err := tx.Exec("UPDATE Note_Attachments SET size_bytes = ?, title = ?, file_path = ?, file_type = 'md' WHERE id = ?", info.Size(), attachmentTitle, relativePath, attachmentID); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	} else {
		result, err := tx.Exec(`
			INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
			VALUES (?, ?, 'md', ?, ?, 1, CURRENT_TIMESTAMP)`, noteID, relativePath, attachmentTitle, info.Size())
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		newID, err := result.LastInsertId()
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		attachmentID = int(newID)
	}
	if _, err := tx.Exec("UPDATE Notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", preview, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status":  "success",
		"message": "內容已成功分離為附件",
		"data": response{
			"attachment_id":   attachmentID,
			"file_path":       relativePath,
			"original_length": originalLength,
			"preview_length":  len([]rune(preview)),
		},
	})
}

func (s *server) restoreSeparatedContent(w http.ResponseWriter, noteID int) {
	var attachmentID int
	var filePath sql.NullString
	if err := s.db.QueryRow("SELECT id, file_path FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1", noteID).Scan(&attachmentID, &filePath); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "No auto-extracted attachment found for this note")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	resolved, ok := resolveAutoExtractedNotePath(s.runtime.dataDir, nullableString(filePath))
	if !ok {
		writeError(w, http.StatusNotFound, "Attachment file not found on disk")
		return
	}
	content, err := os.ReadFile(resolved)
	if err != nil {
		writeError(w, http.StatusNotFound, "Attachment file not found on disk")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	if _, err := tx.Exec("UPDATE Notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", normalizeTextContent(string(content)), noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("DELETE FROM Note_Attachments WHERE id = ?", attachmentID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	_ = os.Remove(resolved)
	writeJSON(w, http.StatusOK, response{"status": "success", "message": "內容已成功還原至筆記"})
}

func (s *server) notesDirectory() string {
	if s.runtime.notesDir != "" {
		return s.runtime.notesDir
	}
	return filepath.Join(s.runtime.dataDir, "docs", "notes")
}

func separatedPreview(content string, previewLen int) string {
	runes := []rune(content)
	if len(runes) <= previewLen {
		return content
	}
	return string(runes[:previewLen]) + "\n\n---\n📎 **[完整內容已分離為附件]**\n\n> 此筆記內容過長，已自動分離為附件。點擊附件可查看完整內容。"
}

func resolveAutoExtractedNotePath(dataDir, relativePath string) (string, bool) {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	if relativePath == "" || filepath.IsAbs(relativePath) || filepath.VolumeName(relativePath) != "" || strings.Contains(relativePath, ":") {
		return "", false
	}
	cleaned := path.Clean(relativePath)
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") || !strings.HasPrefix(cleaned, "docs/notes/") {
		return "", false
	}
	ext := strings.ToLower(path.Ext(cleaned))
	if ext != ".md" && ext != ".markdown" && ext != ".txt" {
		return "", false
	}
	root, err := filepath.Abs(dataDir)
	if err != nil {
		return "", false
	}
	evaluatedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return "", false
	}
	candidate := filepath.Join(root, filepath.FromSlash(cleaned))
	absCandidate, err := filepath.Abs(candidate)
	if err != nil || !isSubpath(absCandidate, root) {
		return "", false
	}
	info, err := os.Lstat(absCandidate)
	if err != nil || !info.Mode().IsRegular() || info.Size() > maxAttachmentFileBytes {
		return "", false
	}
	resolved, err := filepath.EvalSymlinks(absCandidate)
	if err != nil || !isSubpath(resolved, evaluatedRoot) {
		return "", false
	}
	return resolved, true
}

func (s *server) duplicateNoteAttachments(tx *sql.Tx, sourceNoteID int, targetNoteID int64, targetTitle string) ([]string, error) {
	rows, err := tx.Query(`
		SELECT id, file_path, file_type, title, is_auto_extracted
		FROM Note_Attachments
		WHERE note_id = ?
		ORDER BY id`, sourceNoteID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	createdFiles := []string{}
	cleanupCreated := func() {
		for _, filePath := range createdFiles {
			_ = os.Remove(filePath)
		}
	}

	for rows.Next() {
		var attachmentID int64
		var filePath, fileType, title sql.NullString
		var isAutoExtracted sql.NullInt64
		if err := rows.Scan(&attachmentID, &filePath, &fileType, &title, &isAutoExtracted); err != nil {
			cleanupCreated()
			return nil, err
		}

		srcRel := strings.TrimSpace(strings.ReplaceAll(nullableString(filePath), "\\", "/"))
		cleanedRel := path.Clean(srcRel)
		if cleanedRel == "." || cleanedRel == ".." || strings.HasPrefix(cleanedRel, "../") {
			cleanupCreated()
			return nil, fmt.Errorf("unsafe attachment path: %s", srcRel)
		}
		normalizedType := strings.TrimPrefix(strings.ToLower(strings.TrimSpace(nullableString(fileType))), ".")
		if normalizedType == "" {
			normalizedType = strings.TrimPrefix(strings.ToLower(path.Ext(cleanedRel)), ".")
		}

		var srcAbs string
		var destAbs string
		var destRel string
		autoExtracted := isAutoExtracted.Valid && isAutoExtracted.Int64 != 0
		if autoExtracted || strings.HasPrefix(cleanedRel, "docs/notes/") {
			var ok bool
			srcAbs, ok = resolveAutoExtractedNotePath(s.runtime.dataDir, cleanedRel)
			if !ok {
				cleanupCreated()
				return nil, fmt.Errorf("auto-extracted attachment file not found: %s", cleanedRel)
			}
			ext := strings.ToLower(path.Ext(cleanedRel))
			if ext == "" {
				ext = ".md"
			}
			normalizedType = strings.TrimPrefix(ext, ".")
			filename := fmt.Sprintf("note_%d%s", targetNoteID, ext)
			destRel = path.Join("docs", "notes", filename)
			destAbs = filepath.Join(s.notesDirectory(), filename)
			if !isSubpath(destAbs, s.runtime.dataDir) {
				cleanupCreated()
				return nil, fmt.Errorf("unsafe notes attachment destination: %s", destRel)
			}
			autoExtracted = true
		} else {
			var ok bool
			srcAbs, _, ok = resolveAttachmentFile(s.runtime.dataDir, cleanedRel, normalizedType)
			if !ok {
				cleanupCreated()
				return nil, fmt.Errorf("attachment file not found: %s", cleanedRel)
			}
			sourceName := sanitizeAttachmentFilename(path.Base(cleanedRel))
			baseName, ext := splitAttachmentName(sourceName)
			if baseName == "" {
				baseName = "attachment"
			}
			if ext == "" {
				ext = "." + normalizedType
			}
			filename := fmt.Sprintf("%s_copy_%d_%d%s", baseName, targetNoteID, attachmentID, ext)
			destRel = path.Join("docs", "attachments", filepath.ToSlash(filename))
			destAbs = filepath.Join(s.runtime.attachmentsDir, filename)
			if !isSubpath(destAbs, s.runtime.dataDir) {
				cleanupCreated()
				return nil, fmt.Errorf("unsafe attachment destination: %s", destRel)
			}
		}

		sizeBytes, err := copyFileAtomic(srcAbs, destAbs)
		if err != nil {
			cleanupCreated()
			return nil, err
		}
		createdFiles = append(createdFiles, destAbs)

		attachmentTitle := nullableStringOrNil(title)
		if autoExtracted {
			attachmentTitle = targetTitle + " (完整內容)"
		}
		if _, err := tx.Exec(`
			INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
			VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`,
			targetNoteID, destRel, normalizedType, attachmentTitle, sizeBytes, boolToInt(autoExtracted)); err != nil {
			cleanupCreated()
			return nil, err
		}
	}
	if err := rows.Err(); err != nil {
		cleanupCreated()
		return nil, err
	}
	return createdFiles, nil
}

func copyFileAtomic(sourcePath, destinationPath string) (int64, error) {
	if err := os.MkdirAll(filepath.Dir(destinationPath), 0755); err != nil {
		return 0, err
	}
	source, err := os.Open(sourcePath)
	if err != nil {
		return 0, err
	}
	defer source.Close()

	tempPath := destinationPath + ".tmp"
	target, err := os.OpenFile(tempPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
	if err != nil {
		return 0, err
	}
	sizeBytes, copyErr := io.Copy(target, source)
	closeErr := target.Close()
	if copyErr != nil {
		_ = os.Remove(tempPath)
		return 0, copyErr
	}
	if closeErr != nil {
		_ = os.Remove(tempPath)
		return 0, closeErr
	}
	_ = os.Remove(destinationPath)
	if err := os.Rename(tempPath, destinationPath); err != nil {
		_ = os.Remove(tempPath)
		return 0, err
	}
	return sizeBytes, nil
}

func removeFiles(paths []string) {
	for _, filePath := range paths {
		_ = os.Remove(filePath)
	}
}

func boolToInt(value bool) int {
	if value {
		return 1
	}
	return 0
}

func (s *server) toggleNoteBool(w http.ResponseWriter, r *http.Request, noteID int, column, payloadKey string) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var current int
	if err := tx.QueryRow("SELECT COALESCE("+column+", 0) FROM Notes WHERE id = ?", noteID).Scan(&current); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	payload := map[string]any{}
	_ = json.NewDecoder(r.Body).Decode(&payload)
	next := 0
	if raw, ok := payload[payloadKey]; ok {
		if truthy, ok := raw.(bool); ok && truthy {
			next = 1
		}
	} else if current == 0 {
		next = 1
	}
	query := "UPDATE Notes SET " + column + " = ?"
	if column == "is_archived" {
		query += ", updated_at = CURRENT_TIMESTAMP"
	}
	query += " WHERE id = ?"
	if _, err := tx.Exec(query, next, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"id": noteID, column: next != 0}})
}

func (s *server) duplicateNote(w http.ResponseWriter, r *http.Request, noteID int) {
	payload := map[string]any{}
	_ = json.NewDecoder(r.Body).Decode(&payload)
	asVariant, _ := payload["as_variant"].(bool)
	titleSuffix := stringField(payload, "title_suffix")
	if titleSuffix == "" {
		if asVariant {
			titleSuffix = " (Variant)"
		} else {
			titleSuffix = " (Copy)"
		}
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var title, content, remarks, coverImage, coverPosition, editorLayout, promptParams sql.NullString
	var categoryID sql.NullInt64
	if err := tx.QueryRow(`
		SELECT title, content, remarks, cover_image, cover_position, editor_layout, category_id, prompt_params
		FROM Notes WHERE id = ?`, noteID).Scan(&title, &content, &remarks, &coverImage, &coverPosition, &editorLayout, &categoryID, &promptParams); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	newTitle := nullableString(title) + titleSuffix
	var result sql.Result
	if asVariant {
		result, err = tx.Exec(`
			INSERT INTO Notes (title, content, remarks, cover_image, cover_position, editor_layout, category_id, prompt_params, parent_id)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			newTitle, nullableString(content), nullableStringOrNil(remarks), nullableStringOrNil(coverImage),
			nullableString(coverPosition), nullableString(editorLayout), nullableIntOrNil(categoryID), nullableStringOrNil(promptParams), noteID)
	} else {
		result, err = tx.Exec(`
			INSERT INTO Notes (title, content, remarks, cover_image, cover_position, editor_layout, category_id, prompt_params)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
			newTitle, nullableString(content), nullableStringOrNil(remarks), nullableStringOrNil(coverImage),
			nullableString(coverPosition), nullableString(editorLayout), nullableIntOrNil(categoryID), nullableStringOrNil(promptParams))
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	newID, err := result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("INSERT INTO Note_Tags (note_id, tag_id) SELECT ?, tag_id FROM Note_Tags WHERE note_id = ?", newID, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("INSERT INTO Source_Urls (note_id, url) SELECT ?, url FROM Source_Urls WHERE note_id = ?", newID, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	createdAttachmentFiles, err := s.duplicateNoteAttachments(tx, noteID, newID, newTitle)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		removeFiles(createdAttachmentFiles)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{
		"note_id": int(newID), "parent_id": nullableVariantParent(noteID, asVariant), "is_variant": asVariant,
	}})
}

func (s *server) reorderNotes(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "note_ids is required")
	if !ok {
		return
	}
	noteIDs, ok := requiredIntArrayField(w, payload, "note_ids", "note_ids is required")
	if !ok {
		return
	}
	if len(noteIDs) == 0 {
		writeError(w, http.StatusBadRequest, "note_ids must be a non-empty array")
		return
	}
	if len(noteIDs) > 500 {
		writeError(w, http.StatusBadRequest, "Maximum 500 notes per reorder")
		return
	}
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	for index, id := range noteIDs {
		if _, err := tx.Exec("UPDATE Notes SET sort_order = ? WHERE id = ?", index, id); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"reordered_count": len(noteIDs)}})
}

func (s *server) handleNoteBatch(w http.ResponseWriter, r *http.Request, action string) {
	switch action {
	case "type":
		s.batchUpdateType(w, r)
	case "tags":
		s.batchUpdateTags(w, r)
	case "delete":
		s.batchDeleteNotes(w, r)
	default:
		http.NotFound(w, r)
	}
}

func (s *server) batchUpdateType(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "note_ids and category_id are required")
	if !ok {
		return
	}
	categoryID, hasCategory := intField(payload, "category_id")
	if !hasCategory || categoryID == 0 {
		writeError(w, http.StatusBadRequest, "note_ids and category_id are required")
		return
	}
	noteIDs, ok := requiredIntArrayField(w, payload, "note_ids", "note_ids and category_id are required")
	if !ok {
		return
	}
	if len(noteIDs) > 500 {
		writeError(w, http.StatusBadRequest, "Maximum 500 notes per batch")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	var existingCategory int
	if err := tx.QueryRow("SELECT id FROM Categories WHERE id = ?", categoryID).Scan(&existingCategory); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusBadRequest, fmt.Sprintf("Category %d does not exist", categoryID))
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	result, err := tx.Exec("UPDATE Notes SET category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id IN ("+placeholders(len(noteIDs))+")", append([]any{categoryID}, intsToAny(noteIDs)...)...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	affected, _ := result.RowsAffected()
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"updated_count": int(affected)}})
}

func (s *server) batchUpdateTags(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "note_ids and tags are required")
	if !ok {
		return
	}
	tags := stringArrayField(payload, "tags")
	if len(tags) == 0 {
		writeError(w, http.StatusBadRequest, "note_ids and tags are required")
		return
	}
	noteIDs, ok := requiredIntArrayField(w, payload, "note_ids", "note_ids and tags are required")
	if !ok {
		return
	}
	if len(noteIDs) > 500 {
		writeError(w, http.StatusBadRequest, "Maximum 500 notes per batch")
		return
	}
	mode := defaultStringField(payload, "mode", "append")
	if mode != "append" && mode != "replace" {
		writeError(w, http.StatusBadRequest, `mode must be "append" or "replace"`)
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	tagsAdded := 0
	affectedNotes := 0
	for _, noteID := range noteIDs {
		var existing int
		if err := tx.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existing); err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				continue
			}
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		affectedNotes++
		if mode == "replace" {
			if _, err := tx.Exec("DELETE FROM Note_Tags WHERE note_id = ?", noteID); err != nil {
				writeError(w, http.StatusInternalServerError, err.Error())
				return
			}
		}
		added, err := appendNoteTags(tx, noteID, tags)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		tagsAdded += added
		if _, err := tx.Exec("UPDATE Notes SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", noteID); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"affected_notes": affectedNotes, "tags_added": tagsAdded, "mode": mode,
	}})
}

func (s *server) batchDeleteNotes(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "note_ids is required")
	if !ok {
		return
	}
	rawNoteIDs, hasNoteIDs := payload["note_ids"]
	if !hasNoteIDs || rawNoteIDs == nil {
		writeError(w, http.StatusBadRequest, "note_ids is required")
		return
	}
	if rawList, ok := rawNoteIDs.([]any); ok && len(rawList) == 0 {
		writeError(w, http.StatusBadRequest, "note_ids is required")
		return
	}
	noteIDs, ok := requiredIntArrayField(w, payload, "note_ids", "note_ids is required")
	if !ok {
		return
	}
	if len(noteIDs) > 500 {
		writeError(w, http.StatusBadRequest, "Maximum 500 notes per batch")
		return
	}
	if boolField(payload, "dry_run") {
		preview, err := s.previewBatchDelete(noteIDs)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, response{"status": "success", "data": preview})
		return
	}
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	refs, err := noteImageReferences(tx, noteIDs)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	attachmentPaths, err := s.noteAttachmentCleanupPaths(tx, noteIDs)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	for _, ref := range refs {
		s.cleanupNoteImages(tx, ref)
	}
	deleted, err := deleteNotesByID(tx, noteIDs)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	cleanupNoteAttachmentFiles(attachmentPaths)
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted_count": deleted}})
}

func (s *server) previewBatchDelete(noteIDs []int) (response, error) {
	if len(noteIDs) == 0 {
		return response{
			"dry_run":          true,
			"requested_count":  0,
			"deletable_count":  0,
			"missing_count":    0,
			"image_count":      0,
			"attachment_count": 0,
			"notes":            []response{},
		}, nil
	}

	tx, err := s.db.Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()

	rows, err := tx.Query(`
		SELECT id, title
		FROM Notes
		WHERE id IN (`+placeholders(len(noteIDs))+`)
		ORDER BY id`, intsToAny(noteIDs)...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	existing := map[int]bool{}
	notes := []response{}
	for rows.Next() {
		var id int
		var title sql.NullString
		if err := rows.Scan(&id, &title); err != nil {
			return nil, err
		}
		existing[id] = true
		notes = append(notes, response{"id": id, "title": nullableString(title)})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	missing := 0
	for _, noteID := range noteIDs {
		if !existing[noteID] {
			missing++
		}
	}

	refs, err := noteImageReferences(tx, noteIDs)
	if err != nil {
		return nil, err
	}
	imageFiles, err := s.previewNoteImageCleanupFiles(tx, refs)
	if err != nil {
		return nil, err
	}
	attachmentPaths, err := s.noteAttachmentCleanupPaths(tx, noteIDs)
	if err != nil {
		return nil, err
	}

	return response{
		"dry_run":          true,
		"requested_count":  len(noteIDs),
		"deletable_count":  len(notes),
		"missing_count":    missing,
		"image_count":      len(imageFiles),
		"attachment_count": len(attachmentPaths),
		"notes":            notes,
	}, nil
}

func (s *server) getNoteHistory(w http.ResponseWriter, noteID int) {
	var title string
	if err := s.db.QueryRow("SELECT title FROM Notes WHERE id = ?", noteID).Scan(&title); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	rows, err := s.db.Query(`
		SELECT id, content, diff_summary, created_at
		FROM Note_History
		WHERE note_id = ?
		ORDER BY created_at DESC
		LIMIT 50`, noteID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()
	history := []response{}
	for rows.Next() {
		var id int
		var content, diffSummary, createdAt sql.NullString
		if err := rows.Scan(&id, &content, &diffSummary, &createdAt); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		history = append(history, response{
			"id": id, "content": nullableString(content), "diff_summary": nullableString(diffSummary), "created_at": sqliteDateTimeString(createdAt),
		})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"note_id": noteID, "note_title": title, "history": history, "total": len(history),
	}})
}

func (s *server) restoreNoteVersion(w http.ResponseWriter, noteID, historyID int) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	var currentContent string
	if err := tx.QueryRow("SELECT content FROM Notes WHERE id = ?", noteID).Scan(&currentContent); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	var historyContent string
	if err := tx.QueryRow("SELECT content FROM Note_History WHERE id = ? AND note_id = ?", historyID, noteID).Scan(&historyContent); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "History version not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, ?, ?)", noteID, currentContent, "還原前自動備份"); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("UPDATE Notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", historyContent, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "message": "Note restored successfully"})
}

func (s *server) deleteNoteHistory(w http.ResponseWriter, noteID int) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	var existing int
	if err := tx.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existing); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	result, err := tx.Exec("DELETE FROM Note_History WHERE note_id = ?", noteID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	deleted, _ := result.RowsAffected()
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "message": fmt.Sprintf("Deleted %d history records", deleted), "data": response{"deleted_count": int(deleted)}})
}

func nullableString(value sql.NullString) string {
	if !value.Valid {
		return ""
	}
	return value.String
}

func sqliteDateTimeString(value sql.NullString) string {
	text := nullableString(value)
	if text == "" || !strings.Contains(text, "T") {
		return text
	}
	parsed, err := time.Parse(time.RFC3339Nano, text)
	if err != nil {
		return text
	}
	return parsed.Format("2006-01-02 15:04:05")
}

func nullableStringOrNil(value sql.NullString) any {
	if !value.Valid {
		return nil
	}
	return value.String
}

func nullableIntOrNil(value sql.NullInt64) any {
	if !value.Valid {
		return nil
	}
	return int(value.Int64)
}

func parseJSONOrNil(value sql.NullString) any {
	if !value.Valid || strings.TrimSpace(value.String) == "" {
		return nil
	}
	var parsed any
	if err := json.Unmarshal([]byte(value.String), &parsed); err != nil {
		return nil
	}
	return parsed
}
