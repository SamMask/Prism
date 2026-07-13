package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"
)

func (s *server) handleCleanupOrphanImages(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "GET, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableMediaCleanup {
		writeError(w, http.StatusMethodNotAllowed, "Media cleanup route is disabled")
		return
	}
	if r.Method == http.MethodGet {
		s.getOrphanImages(w)
		return
	}
	s.deleteOrphanImages(w, r)
}

func (s *server) getOrphanImages(w http.ResponseWriter) {
	orphans, totalSize, err := s.orphanUploadImages()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	items := make([]response, 0, len(orphans))
	for _, orphan := range orphans {
		items = append(items, response{
			"filename": orphan.Filename,
			"size":     orphan.Size,
			"path":     "/static/uploads/" + orphan.Filename,
		})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"orphan_images":    items,
		"total_count":      len(items),
		"total_size_bytes": totalSize,
		"total_size_mb":    roundedMB(totalSize),
	}})
}

func (s *server) deleteOrphanImages(w http.ResponseWriter, r *http.Request) {
	var payload struct {
		Filenames []string `json:"filenames"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil && !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "Invalid JSON request")
		return
	}
	if len(payload.Filenames) == 0 {
		writeError(w, http.StatusBadRequest, "No filenames provided")
		return
	}

	orphans, _, err := s.orphanUploadImages()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	orphanSet := map[string]bool{}
	for _, orphan := range orphans {
		orphanSet[orphan.Filename] = true
	}

	deleted := []string{}
	deletedSet := map[string]bool{}
	errorsOut := []response{}
	for _, rawFilename := range payload.Filenames {
		filename, ok := uploadReferenceFilename(rawFilename)
		if !ok {
			errorsOut = append(errorsOut, response{"filename": rawFilename, "error": "Invalid path"})
			continue
		}
		if !orphanSet[filename] {
			errorsOut = append(errorsOut, response{"filename": filename, "error": "File is not orphan"})
			continue
		}
		deletedAny := false
		for _, candidate := range uploadDeleteCandidates(filename) {
			if deletedSet[candidate] {
				continue
			}
			if candidate != filename && !orphanSet[candidate] {
				continue
			}
			absPath, ok := s.resolveUploadFile(candidate)
			if !ok {
				continue
			}
			info, err := os.Stat(absPath)
			if err != nil {
				if os.IsNotExist(err) {
					continue
				}
				errorsOut = append(errorsOut, response{"filename": candidate, "error": err.Error()})
				continue
			}
			if !info.Mode().IsRegular() {
				continue
			}
			if err := os.Remove(absPath); err != nil {
				errorsOut = append(errorsOut, response{"filename": candidate, "error": err.Error()})
				continue
			}
			deleted = append(deleted, candidate)
			deletedSet[candidate] = true
			deletedAny = true
		}
		if !deletedAny {
			errorsOut = append(errorsOut, response{"filename": filename, "error": "File not found"})
		}
	}

	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"deleted":       deleted,
		"deleted_count": len(deleted),
		"errors":        errorsOut,
	}})
}

func (s *server) handleCleanupOriginals(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "GET, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableMediaCleanup {
		writeError(w, http.StatusMethodNotAllowed, "Media cleanup route is disabled")
		return
	}
	if r.Method == http.MethodGet {
		s.getOriginalImages(w)
		return
	}
	s.deleteAllOriginals(w)
}

func (s *server) getOriginalImages(w http.ResponseWriter) {
	originals, thumbnailCount, err := s.originalUploadImages()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	var originalSize int64
	for _, item := range originals {
		originalSize += item.Size
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"original_count":      len(originals),
		"original_size_bytes": originalSize,
		"original_size_mb":    roundedMB(originalSize),
		"thumbnail_count":     thumbnailCount,
	}})
}

func (s *server) deleteAllOriginals(w http.ResponseWriter) {
	originals, _, err := s.originalUploadImages()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if len(originals) == 0 {
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
			"deleted_count": 0,
			"saved_bytes":   0,
			"saved_mb":      0,
			"updated_notes": 0,
		}})
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	updatedNotes := 0
	for _, item := range originals {
		originalURL := "/static/uploads/" + item.Filename
		thumbnailURL := "/static/uploads/" + item.Thumbnail
		result, err := tx.Exec(`
			UPDATE Notes
			SET content = REPLACE(content, ?, ?),
			    updated_at = CURRENT_TIMESTAMP
			WHERE content LIKE ?`,
			originalURL, thumbnailURL, "%"+originalURL+"%")
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		rows, _ := result.RowsAffected()
		updatedNotes += int(rows)
		if _, err := tx.Exec(`
			UPDATE Notes
			SET cover_image = ?
			WHERE cover_image = ?`,
			thumbnailURL, originalURL); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	deletedCount := 0
	var savedBytes int64
	for _, item := range originals {
		absPath, ok := s.resolveUploadFile(item.Filename)
		if !ok {
			continue
		}
		if err := os.Remove(absPath); err != nil {
			if !os.IsNotExist(err) {
				log.Printf("original cleanup skipped file %s: %v", absPath, err)
			}
			continue
		}
		deletedCount++
		savedBytes += item.Size
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"deleted_count": deletedCount,
		"saved_bytes":   savedBytes,
		"saved_mb":      roundedMB(savedBytes),
		"updated_notes": updatedNotes,
	}})
}

func (s *server) handleCleanupBrokenImages(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodPost {
		w.Header().Set("Allow", "GET, POST")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableMediaCleanup {
		writeError(w, http.StatusMethodNotAllowed, "Media cleanup route is disabled")
		return
	}
	if r.Method == http.MethodGet {
		s.getBrokenImages(w)
		return
	}
	s.fixBrokenImages(w)
}

func (s *server) getBrokenImages(w http.ResponseWriter) {
	broken, err := s.brokenImageReferences()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	items := make([]response, 0, len(broken))
	fixableCount := 0
	for _, item := range broken {
		if item.CanFix {
			fixableCount++
		}
		entry := response{
			"note_id":        item.NoteID,
			"original_path":  item.OriginalPath,
			"thumbnail_path": item.ThumbnailPath,
			"can_fix":        item.CanFix,
			"reason":         item.Reason,
		}
		if item.IsCover {
			entry["is_cover"] = true
		}
		items = append(items, entry)
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"broken_paths":  items,
		"total_count":   len(items),
		"fixable_count": fixableCount,
	}})
}

func (s *server) fixBrokenImages(w http.ResponseWriter) {
	rows, err := s.db.Query("SELECT id, content, cover_image FROM Notes")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	type update struct {
		id      int
		content string
		cover   string
	}
	updates := []update{}
	fixedCount := 0
	for rows.Next() {
		var noteID int
		var content, cover sql.NullString
		if err := rows.Scan(&noteID, &content, &cover); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		newContent := nullableString(content)
		newCover := nullableString(cover)
		contentChanged := false
		coverChanged := false
		for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(newContent, -1) {
			if len(match) < 2 {
				continue
			}
			filename := match[1]
			if strings.Contains(filename, "_thumb") {
				continue
			}
			if s.uploadFileExists(filename) {
				continue
			}
			if thumb := s.findThumbnailForOriginal(filename); thumb != "" {
				oldPath := "/static/uploads/" + filename
				newPath := "/static/uploads/" + thumb
				newContent = strings.ReplaceAll(newContent, oldPath, newPath)
				fixedCount++
				contentChanged = true
			}
		}
		if newCover != "" && strings.Contains(newCover, "/static/uploads/") {
			filename, ok := uploadReferenceFilename(newCover)
			if ok && !strings.Contains(filename, "_thumb") && !s.uploadFileExists(filename) {
				if thumb := s.findThumbnailForOriginal(filename); thumb != "" {
					newCover = "/static/uploads/" + thumb
					fixedCount++
					coverChanged = true
				}
			}
		}
		if contentChanged || coverChanged {
			updates = append(updates, update{id: noteID, content: newContent, cover: newCover})
		}
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	for _, update := range updates {
		if _, err := tx.Exec(`
			UPDATE Notes
			SET content = ?, cover_image = ?, updated_at = CURRENT_TIMESTAMP
			WHERE id = ?`, update.content, update.cover, update.id); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"fixed_count":   fixedCount,
		"updated_notes": len(updates),
	}})
}

func staticUploadReferences(content, coverImage sql.NullString) []string {
	seen := map[string]bool{}
	paths := []string{}
	add := func(value string) {
		if value == "" || seen[value] {
			return
		}
		seen[value] = true
		paths = append(paths, value)
	}
	if coverImage.Valid && strings.HasPrefix(coverImage.String, "/static/uploads/") {
		add(coverImage.String)
	}
	if content.Valid {
		for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(content.String, -1) {
			if len(match) > 1 {
				add("/static/uploads/" + match[1])
			}
		}
	}
	return paths
}

func cleanupUploadFilenames(imagePath string) []string {
	filename := strings.TrimPrefix(imagePath, "/static/uploads/")
	ext := path.Ext(filename)
	nameWithoutExt := strings.TrimSuffix(filename, ext)
	candidates := []string{filename}
	if !strings.HasSuffix(filename, "_thumb.webp") {
		candidates = append(candidates, nameWithoutExt+"_thumb.webp")
	} else {
		originalBase := strings.ReplaceAll(nameWithoutExt, "_thumb", "")
		for _, originalExt := range []string{".jpg", ".png", ".gif", ".webp"} {
			candidates = append(candidates, originalBase+originalExt)
		}
	}
	return uniqueStrings(candidates)
}

func uploadDeleteFilename(rawURL string) (string, bool) {
	raw := strings.TrimSpace(strings.ReplaceAll(rawURL, "\\", "/"))
	if raw == "" {
		return "", false
	}
	if idx := strings.LastIndex(raw, "/static/uploads/"); idx >= 0 {
		raw = raw[idx+len("/static/uploads/"):]
	}
	filename := path.Base(raw)
	if filename == "." || filename == "/" || filename == "" || strings.Contains(filename, "..") || strings.HasPrefix(filename, ".") {
		return "", false
	}
	return filename, true
}

func uploadDeleteCandidates(filename string) []string {
	filename = strings.ReplaceAll(strings.TrimSpace(filename), "\\", "/")
	if filename == "" {
		return nil
	}
	ext := path.Ext(filename)
	nameWithoutExt := strings.TrimSuffix(filename, ext)
	candidates := []string{filename}
	if !strings.HasSuffix(nameWithoutExt, "_thumb") {
		candidates = append(candidates, nameWithoutExt+"_thumb.webp")
		if ext != "" {
			candidates = append(candidates, nameWithoutExt+"_thumb"+ext)
		}
	}
	return uniqueStrings(candidates)
}

func uploadReferenceFilename(raw string) (string, bool) {
	raw = strings.TrimSpace(strings.ReplaceAll(raw, "\\", "/"))
	if raw == "" {
		return "", false
	}
	if idx := strings.LastIndex(raw, "/static/uploads/"); idx >= 0 {
		raw = raw[idx+len("/static/uploads/"):]
	}
	raw = strings.TrimPrefix(raw, "/")
	cleaned := path.Clean(raw)
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return "", false
	}
	for _, part := range strings.Split(cleaned, "/") {
		if part == "" || part == "." || part == ".." {
			return "", false
		}
	}
	return cleaned, true
}

func addReferencedUploadFilename(referenced map[string]bool, raw string) {
	if filename, ok := uploadReferenceFilename(raw); ok {
		referenced[filename] = true
	}
}

func expandedUploadReferences(referenced map[string]bool) map[string]bool {
	expanded := map[string]bool{}
	for ref := range referenced {
		expanded[ref] = true
		base := strings.TrimSuffix(ref, path.Ext(ref))
		if !strings.HasSuffix(base, "_thumb") {
			ext := path.Ext(ref)
			if ext != "" {
				expanded[base+"_thumb"+ext] = true
			}
			expanded[base+"_thumb.webp"] = true
		}
	}
	return expanded
}

func possibleOriginalsForThumb(filename string) []string {
	baseName := strings.ReplaceAll(filename, "_thumb", "")
	baseNoExt := strings.TrimSuffix(baseName, path.Ext(baseName))
	candidates := []string{baseName}
	for _, ext := range []string{".jpg", ".jpeg", ".png", ".gif", ".webp"} {
		candidates = append(candidates, baseNoExt+ext)
	}
	return uniqueStrings(candidates)
}

func isCleanupImageFilename(filename string, includeSVG bool) bool {
	switch strings.ToLower(path.Ext(filename)) {
	case ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp":
		return true
	case ".svg":
		return includeSVG
	default:
		return false
	}
}

type uploadImageFile struct {
	Filename string
	Size     int64
}

type originalUploadImage struct {
	Filename  string
	Thumbnail string
	Size      int64
}

type brokenImageReference struct {
	NoteID        int
	OriginalPath  string
	ThumbnailPath any
	CanFix        bool
	IsCover       bool
	Reason        string
}

func (s *server) referencedUploadFilenames() (map[string]bool, error) {
	referenced := map[string]bool{}
	rows, err := s.db.Query("SELECT content, cover_image FROM Notes")
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var content, cover sql.NullString
		if err := rows.Scan(&content, &cover); err != nil {
			rows.Close()
			return nil, err
		}
		if content.Valid {
			for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(content.String, -1) {
				if len(match) > 1 {
					addReferencedUploadFilename(referenced, match[1])
				}
			}
		}
		if cover.Valid && cover.String != "" {
			addReferencedUploadFilename(referenced, cover.String)
		}
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()

	attachmentRows, err := s.db.Query("SELECT file_path FROM Note_Attachments")
	if err != nil {
		return referenced, nil
	}
	defer attachmentRows.Close()
	for attachmentRows.Next() {
		var filePath sql.NullString
		if err := attachmentRows.Scan(&filePath); err != nil {
			return nil, err
		}
		if !filePath.Valid || filePath.String == "" {
			continue
		}
		if strings.Contains(filePath.String, "/static/uploads/") {
			addReferencedUploadFilename(referenced, filePath.String)
			continue
		}
		resolved, ok := resolveAttachmentReferenceScanFile(s.runtime.dataDir, filePath.String)
		if !ok {
			continue
		}
		content, err := os.ReadFile(resolved)
		if err != nil {
			continue
		}
		for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(string(content), -1) {
			if len(match) > 1 {
				addReferencedUploadFilename(referenced, match[1])
			}
		}
	}
	return referenced, attachmentRows.Err()
}

func (s *server) expandedReferencedUploadFilenames() (map[string]bool, error) {
	referenced, err := s.referencedUploadFilenames()
	if err != nil {
		return nil, err
	}
	return expandedUploadReferences(referenced), nil
}

func (s *server) uploadImageFiles(includeSVG bool) ([]uploadImageFile, error) {
	entries, err := os.ReadDir(s.runtime.uploadsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	files := []uploadImageFile{}
	for _, entry := range entries {
		if entry.IsDir() || !isCleanupImageFilename(entry.Name(), includeSVG) {
			continue
		}
		info, err := entry.Info()
		if err != nil || !info.Mode().IsRegular() {
			continue
		}
		files = append(files, uploadImageFile{Filename: entry.Name(), Size: info.Size()})
	}
	return files, nil
}

func (s *server) orphanUploadImages() ([]uploadImageFile, int64, error) {
	files, err := s.uploadImageFiles(true)
	if err != nil {
		return nil, 0, err
	}
	referenced, err := s.referencedUploadFilenames()
	if err != nil {
		return nil, 0, err
	}
	expandedReferenced := expandedUploadReferences(referenced)
	orphans := []uploadImageFile{}
	var totalSize int64
	for _, file := range files {
		if expandedReferenced[file.Filename] {
			continue
		}
		if strings.Contains(file.Filename, "_thumb") {
			protected := false
			for _, original := range possibleOriginalsForThumb(file.Filename) {
				if referenced[original] {
					protected = true
					break
				}
			}
			if protected {
				continue
			}
		}
		orphans = append(orphans, file)
		totalSize += file.Size
	}
	return orphans, totalSize, nil
}

func (s *server) originalUploadImages() ([]originalUploadImage, int, error) {
	files, err := s.uploadImageFiles(false)
	if err != nil {
		return nil, 0, err
	}
	originals := []originalUploadImage{}
	thumbnailCount := 0
	for _, file := range files {
		base := strings.TrimSuffix(file.Filename, path.Ext(file.Filename))
		if strings.HasSuffix(base, "_thumb") {
			thumbnailCount++
			continue
		}
		if thumb := s.findThumbnailForOriginal(file.Filename); thumb != "" {
			originals = append(originals, originalUploadImage{
				Filename:  file.Filename,
				Thumbnail: thumb,
				Size:      file.Size,
			})
		}
	}
	return originals, thumbnailCount, nil
}

func (s *server) brokenImageReferences() ([]brokenImageReference, error) {
	rows, err := s.db.Query("SELECT id, content, cover_image FROM Notes")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	broken := []brokenImageReference{}
	for rows.Next() {
		var noteID int
		var content, cover sql.NullString
		if err := rows.Scan(&noteID, &content, &cover); err != nil {
			return nil, err
		}
		if content.Valid {
			for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(content.String, -1) {
				if len(match) < 2 {
					continue
				}
				filename := match[1]
				if strings.Contains(filename, "_thumb") {
					if !s.uploadFileExists(filename) {
						broken = append(broken, brokenImageReference{
							NoteID:       noteID,
							OriginalPath: "/static/uploads/" + filename,
							CanFix:       false,
							Reason:       "thumbnail_missing",
						})
					}
					continue
				}
				if !s.uploadFileExists(filename) {
					thumb := s.findThumbnailForOriginal(filename)
					broken = append(broken, brokenReference(noteID, "/static/uploads/"+filename, thumb, false))
				}
			}
		}
		if cover.Valid && strings.Contains(cover.String, "/static/uploads/") {
			filename, ok := uploadReferenceFilename(cover.String)
			if !ok || s.uploadFileExists(filename) {
				continue
			}
			if strings.Contains(filename, "_thumb") {
				broken = append(broken, brokenImageReference{
					NoteID:       noteID,
					OriginalPath: cover.String,
					CanFix:       false,
					IsCover:      true,
					Reason:       "thumbnail_missing",
				})
			} else {
				thumb := s.findThumbnailForOriginal(filename)
				broken = append(broken, brokenReference(noteID, cover.String, thumb, true))
			}
		}
	}
	return broken, rows.Err()
}

func brokenReference(noteID int, originalPath, thumbnail string, isCover bool) brokenImageReference {
	item := brokenImageReference{
		NoteID:       noteID,
		OriginalPath: originalPath,
		CanFix:       thumbnail != "",
		IsCover:      isCover,
		Reason:       "original_missing",
	}
	if thumbnail != "" {
		item.ThumbnailPath = "/static/uploads/" + thumbnail
	}
	return item
}

func (s *server) uploadFileExists(filename string) bool {
	absPath, ok := s.resolveUploadFile(filename)
	if !ok {
		return false
	}
	info, err := os.Stat(absPath)
	return err == nil && info.Mode().IsRegular()
}

func (s *server) findThumbnailForOriginal(filename string) string {
	ext := path.Ext(filename)
	base := strings.TrimSuffix(filename, ext)
	for _, candidate := range []string{base + "_thumb.webp", base + "_thumb" + ext} {
		if candidate == base+"_thumb" {
			continue
		}
		if s.uploadFileExists(candidate) {
			return candidate
		}
	}
	return ""
}

func roundedMB(size int64) float64 {
	if size <= 0 {
		return 0
	}
	return math.Round((float64(size)/(1024*1024))*100) / 100
}

func resolveAttachmentReferenceScanFile(dataDir, relativePath string) (string, bool) {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	ext := strings.ToLower(path.Ext(relativePath))
	if ext != ".md" && ext != ".markdown" && ext != ".txt" && ext != ".html" {
		return "", false
	}
	cleaned := path.Clean(relativePath)
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return "", false
	}
	if strings.HasPrefix(cleaned, "docs/notes/") {
		return resolveAutoExtractedNotePath(dataDir, cleaned)
	}
	if !strings.HasPrefix(cleaned, "docs/attachments/") {
		return "", false
	}

	resolved, ok := resolveAttachmentMutationPath(dataDir, cleaned)
	if !ok {
		return "", false
	}
	info, err := os.Lstat(resolved)
	if err != nil || !info.Mode().IsRegular() || info.Size() > maxUploadFileBytes {
		return "", false
	}
	evaluated, err := filepath.EvalSymlinks(resolved)
	if err != nil || filepath.Clean(evaluated) != filepath.Clean(resolved) {
		return "", false
	}
	root, err := filepath.Abs(dataDir)
	if err != nil || !isSubpath(evaluated, root) {
		return "", false
	}
	return evaluated, true
}

func uniqueStrings(values []string) []string {
	seen := map[string]bool{}
	unique := []string{}
	for _, value := range values {
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		unique = append(unique, value)
	}
	return unique
}

func (s *server) resolveUploadFile(filename string) (string, bool) {
	if strings.TrimSpace(filename) == "" {
		return "", false
	}
	filename = strings.ReplaceAll(filename, "\\", "/")
	filename = strings.TrimPrefix(filename, "/")
	if filepath.IsAbs(filename) || filepath.VolumeName(filename) != "" {
		return "", false
	}
	cleaned := path.Clean(filename)
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return "", false
	}
	for _, part := range strings.Split(cleaned, "/") {
		if part == "" || part == "." || part == ".." {
			return "", false
		}
	}
	absPath := filepath.Join(s.runtime.uploadsDir, filepath.FromSlash(cleaned))
	if !isSubpath(absPath, s.runtime.uploadsDir) {
		return "", false
	}
	return absPath, true
}

func intsToAny(values []int) []any {
	out := make([]any, 0, len(values))
	for _, value := range values {
		out = append(out, value)
	}
	return out
}
