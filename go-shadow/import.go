package main

import (
	"context"
	"crypto/md5"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"math"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

func (s *server) handleImportJSON(w http.ResponseWriter, r *http.Request) {
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

	payload, ok := decodeJSONObject(w, r, "No data provided")
	if !ok {
		return
	}
	importData, ok := objectField(payload, "data")
	if !ok {
		writeError(w, http.StatusBadRequest, "Invalid import data format")
		return
	}
	notes := objectArray(importData["notes"])
	if notes == nil {
		writeError(w, http.StatusBadRequest, "Invalid import data format")
		return
	}
	mode := strings.TrimSpace(stringValue(payload["mode"]))
	if mode == "" {
		mode = "skip"
	}

	// The body is fully parsed. The import writes attachment and upload files, so it runs under
	// noteFilesMu; its reply (duplicate titles, messages with request paths) has no size bound
	// and is written after the lock is released.
	status, payload := s.importJSONNotes(importData, notes, mode)
	writeJSON(w, status, payload)
}

func (s *server) importJSONNotes(importData map[string]any, notes []map[string]any, mode string) (int, response) {
	s.noteFilesMu.Lock()
	defer s.noteFilesMu.Unlock()
	tx, err := s.db.Begin()
	if err != nil {
		return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
	}
	defer tx.Rollback()

	if err := importJSONCategoriesTx(tx, objectArray(importData["categories"])); err != nil {
		return http.StatusBadRequest, response{"status": "error", "message": err.Error()}
	}
	defaultCategoryID, _ := defaultCategoryIDTx(tx)
	idMap := map[int]int{}
	pendingParents := [][2]int{} // {new note id, parent id in the file}
	importedCount := 0
	skippedCount := 0
	duplicates := []string{}
	createdFiles := []string{}
	cleanupCreated := func() {
		for _, filePath := range createdFiles {
			_ = os.Remove(filePath)
		}
	}

	for _, note := range notes {
		oldID, hasOldID := intValue(note["id"])
		title := strings.TrimSpace(stringValue(note["title"]))
		content := strings.TrimSpace(stringValue(note["content"]))
		contentPreview := content
		if len([]rune(contentPreview)) > 100 {
			contentPreview = string([]rune(contentPreview)[:100])
		}

		var existingID int
		err := tx.QueryRow(`
			SELECT id FROM Notes
			WHERE title = ? AND SUBSTR(content, 1, 100) = ?
			LIMIT 1`, title, contentPreview).Scan(&existingID)
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			cleanupCreated()
			return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
		}
		if err == nil {
			if mode == "skip" {
				skippedCount++
				if title == "" {
					duplicates = append(duplicates, "無標題")
				} else {
					duplicates = append(duplicates, title)
				}
				if hasOldID {
					idMap[oldID] = existingID
				}
				continue
			}
			if mode == "duplicate" {
				if title == "" {
					title = "(Imported)"
				} else {
					title += " (Import)"
				}
			}
		}
		if title == "" {
			title = "無標題"
		}

		categoryID := defaultCategoryID
		categoryName := strings.TrimSpace(stringValue(note["category"]))
		if categoryName == "" {
			categoryName = strings.TrimSpace(stringValue(note["type"]))
		}
		if categoryName != "" {
			if found, err := categoryIDForNameTx(tx, categoryName); err == nil && found > 0 {
				categoryID = found
			} else if err != nil && !errors.Is(err, sql.ErrNoRows) {
				cleanupCreated()
				return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
			}
		}

		createdAt := stringValue(note["created_at"])
		if strings.TrimSpace(createdAt) == "" {
			createdAt = time.Now().Format(time.RFC3339)
		}
		updatedAt := stringValue(note["updated_at"])
		if strings.TrimSpace(updatedAt) == "" {
			updatedAt = time.Now().Format(time.RFC3339)
		}

		sortOrder, hasSortOrder := intValue(note["sort_order"])
		result, err := tx.Exec(`
			INSERT INTO Notes (title, content, category_id, remarks, cover_image, created_at, updated_at,
				is_pinned, is_archived, cover_position, editor_layout, sort_order)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			title,
			content,
			nullableIntArg(categoryID, categoryID > 0),
			stringValue(note["remarks"]),
			stringValue(note["cover_image"]),
			createdAt,
			updatedAt,
			boolIntValue(note["is_pinned"]),
			boolIntValue(note["is_archived"]),
			defaultStringField(note, "cover_position", "top"),
			defaultStringField(note, "editor_layout", "single"),
			nullableIntArg(sortOrder, hasSortOrder),
		)
		if err != nil {
			cleanupCreated()
			return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
		}
		newID64, err := result.LastInsertId()
		if err != nil {
			cleanupCreated()
			return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
		}
		newID := int(newID64)
		if hasOldID {
			idMap[oldID] = newID
		}
		if oldParentID, ok := intValue(note["parent_id"]); ok {
			pendingParents = append(pendingParents, [2]int{newID, oldParentID})
		}
		if err := replaceNoteTags(tx, newID, stringArrayValue(note["tags"]), false); err != nil {
			cleanupCreated()
			return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
		}
		urls := stringArrayValue(note["urls"])
		if len(urls) == 0 {
			urls = stringArrayValue(note["source_urls"])
		}
		if err := replaceNoteURLs(tx, newID, urls); err != nil {
			cleanupCreated()
			return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
		}
		importedCount++
	}

	if err := applyImportedParentsTx(tx, idMap, pendingParents); err != nil {
		cleanupCreated()
		return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
	}
	skippedAttachments, err := s.restoreImportedAttachments(tx, idMap, importData, &createdFiles)
	if err != nil {
		cleanupCreated()
		return http.StatusBadRequest, response{"status": "error", "message": err.Error()}
	}
	skippedUploads, err := s.restoreImportedUploads(importData, &createdFiles)
	if err != nil {
		cleanupCreated()
		return http.StatusBadRequest, response{"status": "error", "message": err.Error()}
	}
	if err := tx.Commit(); err != nil {
		cleanupCreated()
		return http.StatusInternalServerError, response{"status": "error", "message": err.Error()}
	}
	if len(duplicates) > 10 {
		duplicates = duplicates[:10]
	}
	return http.StatusOK, response{"status": "success", "data": response{
		"imported":            importedCount,
		"skipped":             skippedCount,
		"skipped_attachments": skippedAttachments,
		"skipped_uploads":     skippedUploads,
		"duplicates":          duplicates,
	}}
}

// applyImportedParentsTx sets parent_id on the notes this import created, after all of them exist,
// so a child may come before its parent in the file. A file parent id resolves only through idMap
// (a created note, or the existing note a skipped one matched); an id outside the file stays NULL
// and never reaches an unrelated target note with the same id. A link that would close a cycle
// stays NULL.
func applyImportedParentsTx(tx *sql.Tx, idMap map[int]int, pending [][2]int) error {
	for _, link := range pending {
		childID := link[0]
		parentID, ok := idMap[link[1]]
		if !ok {
			continue
		}
		cycle, err := parentChainReaches(tx, parentID, childID)
		if err != nil {
			return err
		}
		if cycle {
			continue
		}
		if _, err := tx.Exec("UPDATE Notes SET parent_id = ? WHERE id = ?", parentID, childID); err != nil {
			return err
		}
	}
	return nil
}

// parentChainReaches reports whether target is startID or one of its ancestors.
func parentChainReaches(tx *sql.Tx, startID, target int) (bool, error) {
	seen := map[int]bool{}
	for id := startID; !seen[id]; {
		if id == target {
			return true, nil
		}
		seen[id] = true
		var next sql.NullInt64
		err := tx.QueryRow("SELECT parent_id FROM Notes WHERE id = ?", id).Scan(&next)
		if errors.Is(err, sql.ErrNoRows) || (err == nil && !next.Valid) {
			return false, nil
		}
		if err != nil {
			return false, err
		}
		id = int(next.Int64)
	}
	return false, nil
}

func importJSONCategoriesTx(tx *sql.Tx, categories []map[string]any) error {
	for _, category := range categories {
		name := strings.TrimSpace(stringValue(category["name"]))
		icon := strings.TrimSpace(stringValue(category["icon"]))
		systemKey, ok := normalizeCategorySystemKey(stringValue(category["system_key"]))
		if !ok {
			return fmt.Errorf("invalid category system_key %q", stringValue(category["system_key"]))
		}
		nameOverride := strings.TrimSpace(stringValue(category["name_override"]))
		var nameOverrideArg any
		if nameOverride != "" {
			nameOverrideArg = nameOverride
		}
		sortOrder, hasSortOrder := intValue(category["sort_order"])
		isDefault := boolIntValue(category["is_default"])

		if systemKey != "" {
			seed, hasSeed := categorySeedForSystemKey(systemKey)
			if name == "" && hasSeed {
				name = seed.name
			}
			if icon == "" && hasSeed {
				icon = seed.icon
			}
			if !hasSortOrder && hasSeed {
				sortOrder = seed.sortOrder
			}
			if isDefault == 0 && hasSeed {
				isDefault = seed.isDefault
			}
			if name == "" {
				return errors.New("system category name is required")
			}
			if icon == "" {
				icon = "📁"
			}
			if err := upsertImportedSystemCategoryTx(tx, name, icon, systemKey, nameOverrideArg, sortOrder, isDefault); err != nil {
				return err
			}
			continue
		}

		if name == "" {
			continue
		}
		if icon == "" {
			icon = "📁"
		}
		if !hasSortOrder {
			if err := tx.QueryRow("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM Categories").Scan(&sortOrder); err != nil {
				return err
			}
		}
		var existingID int
		if err := tx.QueryRow("SELECT id FROM Categories WHERE name = ? LIMIT 1", name).Scan(&existingID); err == nil {
			if _, err := tx.Exec("UPDATE Categories SET icon = ?, sort_order = ? WHERE id = ?", icon, sortOrder, existingID); err != nil {
				return err
			}
		} else if errors.Is(err, sql.ErrNoRows) {
			if _, err := tx.Exec("INSERT INTO Categories (name, icon, sort_order, is_default, system_key, name_override) VALUES (?, ?, ?, 0, NULL, NULL)", name, icon, sortOrder); err != nil {
				return err
			}
		} else {
			return err
		}
	}
	return nil
}

func upsertImportedSystemCategoryTx(tx *sql.Tx, name, icon, systemKey string, nameOverrideArg any, sortOrder, isDefault int) error {
	var existingID int
	err := tx.QueryRow("SELECT id FROM Categories WHERE system_key = ? LIMIT 1", systemKey).Scan(&existingID)
	if err == nil {
		_, err = tx.Exec("UPDATE Categories SET icon = ?, sort_order = ?, is_default = ?, name_override = ? WHERE id = ?", icon, sortOrder, isDefault, nameOverrideArg, existingID)
		return err
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return err
	}
	if err := tx.QueryRow("SELECT id FROM Categories WHERE name = ? LIMIT 1", name).Scan(&existingID); err == nil {
		_, err = tx.Exec("UPDATE Categories SET icon = ?, sort_order = ?, is_default = ?, system_key = ?, name_override = ? WHERE id = ?", icon, sortOrder, isDefault, systemKey, nameOverrideArg, existingID)
		return err
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return err
	}
	_, err = tx.Exec("INSERT INTO Categories (name, icon, sort_order, is_default, system_key, name_override) VALUES (?, ?, ?, ?, ?, ?)", name, icon, sortOrder, isDefault, systemKey, nameOverrideArg)
	return err
}

func (s *server) restoreImportedAttachments(tx *sql.Tx, idMap map[int]int, importData map[string]any, createdFiles *[]string) (int, error) {
	skipped := 0
	for _, item := range objectArray(importData["attachments"]) {
		oldNoteID, ok := intValue(item["note_id"])
		if !ok {
			continue
		}
		newNoteID, ok := idMap[oldNoteID]
		if !ok || newNoteID == 0 {
			continue
		}
		filePath := strings.TrimSpace(strings.ReplaceAll(stringValue(item["file_path"]), "\\", "/"))
		if filePath == "" {
			continue
		}
		if isSeparatedNoteAttachmentPath(filePath) {
			skipped++
			continue
		}
		if _, ok := resolveAttachmentMutationPath(s.runtime.dataDir, filePath); !ok {
			return 0, fmt.Errorf("unsafe attachment path: %s", filePath)
		}
		rawPath := filePath
		filePath = path.Clean(filePath)
		// A note mapped onto an existing note (skip mode) may already carry this attachment.
		var existing int
		err := tx.QueryRow("SELECT 1 FROM Note_Attachments WHERE note_id = ? AND file_path IN (?, ?) LIMIT 1",
			newNoteID, filePath, rawPath).Scan(&existing)
		if err == nil {
			continue
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return 0, err
		}
		contentB64 := stringValue(item["content_b64"])
		if contentB64 == "" {
			contentB64 = stringValue(item["content_base64"])
		}
		var sizeBytes any = nil
		if contentB64 != "" {
			content, err := base64.StdEncoding.DecodeString(contentB64)
			if err != nil {
				return 0, fmt.Errorf("invalid attachment content_b64 for %s", filePath)
			}
			if int64(len(content)) > maxAttachmentFileBytes {
				return 0, fmt.Errorf("attachment too large: %s", filePath)
			}
			storedPath, created, err := createImportedAttachmentFile(s.runtime.dataDir, filePath, content)
			if err != nil {
				return 0, err
			}
			*createdFiles = append(*createdFiles, created)
			filePath = storedPath
			sizeBytes = len(content)
		} else if size, ok := intValue(item["size_bytes"]); ok {
			sizeBytes = size
		}
		fileType := strings.TrimPrefix(strings.ToLower(path.Ext(filePath)), ".")
		if typed := strings.TrimSpace(stringValue(item["file_type"])); typed != "" {
			fileType = typed
		}
		if _, err := tx.Exec(`
			INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
			VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`,
			newNoteID, filePath, fileType, stringValue(item["title"]), sizeBytes, boolIntValue(item["is_auto_extracted"])); err != nil {
			return 0, err
		}
	}
	return skipped, nil
}

// isSeparatedNoteAttachmentPath reports a separated-note row (docs/notes/...). The JSON export
// carries only the note preview, and the path names the exporting data dir's note_<old id>.md,
// which may be another note's file here, so the row is skipped instead of restored.
func isSeparatedNoteAttachmentPath(filePath string) bool {
	if filepath.IsAbs(filePath) || strings.Contains(filePath, ":") {
		return false
	}
	return strings.HasPrefix(path.Clean(filePath), "docs/notes/")
}

// createImportedAttachmentFile writes an imported attachment without replacing a file that exists:
// when relPath is taken it uses <name>_import_<n><ext> in the same directory. It returns the
// relative path to store and the absolute path it created.
func createImportedAttachmentFile(dataDir, relPath string, content []byte) (string, string, error) {
	dir := path.Dir(relPath)
	baseName, ext := splitAttachmentName(path.Base(relPath))
	for n := 0; n < 1000; n++ {
		candidate := relPath
		if n > 0 {
			candidate = path.Join(dir, fmt.Sprintf("%s_import_%d%s", baseName, n, ext))
		}
		resolved, ok := resolveAttachmentMutationPath(dataDir, candidate)
		if !ok {
			return "", "", fmt.Errorf("unsafe attachment path: %s", candidate)
		}
		err := createImportFile(resolved, content)
		if errors.Is(err, os.ErrExist) {
			continue
		}
		if err != nil {
			return "", "", err
		}
		return candidate, resolved, nil
	}
	return "", "", fmt.Errorf("no free attachment filename for %s", relPath)
}

// createImportFile creates absPath with content and returns an os.ErrExist error instead of
// replacing a file that is already there.
func createImportFile(absPath string, content []byte) error {
	if err := os.MkdirAll(filepath.Dir(absPath), 0755); err != nil {
		return err
	}
	file, err := os.OpenFile(absPath, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0644)
	if err != nil {
		return err
	}
	_, err = file.Write(content)
	if closeErr := file.Close(); err == nil {
		err = closeErr
	}
	if err != nil {
		_ = os.Remove(absPath)
	}
	return err
}

// restoreImportedUploads writes the uploads that carry content. An upload whose filename already
// exists is left as it is and counted: notes reference uploads by filename, so a renamed copy
// would not be reachable from the imported notes.
func (s *server) restoreImportedUploads(importData map[string]any, createdFiles *[]string) (int, error) {
	skipped := 0
	for _, item := range objectArray(importData["uploads"]) {
		filename := strings.TrimSpace(strings.ReplaceAll(stringValue(item["filename"]), "\\", "/"))
		if filename == "" {
			if rawURL := stringValue(item["url"]); rawURL != "" {
				if parsed, ok := uploadReferenceFilename(rawURL); ok {
					filename = parsed
				}
			}
		}
		if filename == "" {
			continue
		}
		resolved, ok := s.resolveUploadFile(filename)
		if !ok {
			return 0, fmt.Errorf("unsafe upload filename: %s", filename)
		}
		contentB64 := stringValue(item["content_b64"])
		if contentB64 == "" {
			contentB64 = stringValue(item["content_base64"])
		}
		if contentB64 == "" {
			continue
		}
		content, err := base64.StdEncoding.DecodeString(contentB64)
		if err != nil {
			return 0, fmt.Errorf("invalid upload content_b64 for %s", filename)
		}
		if int64(len(content)) > maxUploadFileBytes {
			return 0, fmt.Errorf("upload too large: %s", filename)
		}
		err = createImportFile(resolved, content)
		if errors.Is(err, os.ErrExist) {
			skipped++
			continue
		}
		if err != nil {
			return 0, err
		}
		*createdFiles = append(*createdFiles, resolved)
	}
	return skipped, nil
}

type markdownImportImage struct {
	filename string
	content  []byte
}

func markdownImportImageParts(form *multipart.Form) (map[string]markdownImportImage, error) {
	parts := map[string]markdownImportImage{}
	if form == nil {
		return parts, nil
	}
	for fieldName, headers := range form.File {
		if fieldName == "file" {
			continue
		}
		for _, header := range headers {
			if header == nil || strings.TrimSpace(header.Filename) == "" {
				continue
			}
			file, err := header.Open()
			if err != nil {
				return nil, err
			}
			content, readErr := io.ReadAll(io.LimitReader(file, maxUploadFileBytes+1))
			closeErr := file.Close()
			if readErr != nil {
				return nil, readErr
			}
			if closeErr != nil {
				return nil, closeErr
			}
			if int64(len(content)) > maxUploadFileBytes {
				return nil, fmt.Errorf("image too large: %s", header.Filename)
			}
			image := markdownImportImage{filename: header.Filename, content: content}
			normalized := strings.ReplaceAll(header.Filename, "\\", "/")
			parts[normalized] = image
			parts[path.Base(normalized)] = image
		}
	}
	return parts, nil
}

func parseMarkdownImport(content, filename string) (string, string, string, []string, []string) {
	title := strings.TrimSuffix(filepath.Base(filename), filepath.Ext(filename))
	heading := regexp.MustCompile(`(?m)^#\s+(.+)$`)
	if match := heading.FindStringSubmatchIndex(content); match != nil {
		title = strings.TrimSpace(content[match[2]:match[3]])
		content = content[:match[0]] + content[match[1]:]
	}

	categoryName := "筆記"
	tags := []string{}
	urls := []string{}
	frontmatter := regexp.MustCompile(`(?s)^---\s*\n(.*?)\n---\s*\n`)
	if match := frontmatter.FindStringSubmatchIndex(content); match != nil {
		values := parseSimpleFrontmatter(content[match[2]:match[3]])
		if value := strings.TrimSpace(values["type"]); value != "" {
			categoryName = value
		}
		if value := strings.TrimSpace(values["category"]); value != "" {
			categoryName = value
		}
		tags = parseFrontmatterArray(values["tags"])
		urls = parseFrontmatterArray(values["urls"])
		if len(urls) == 0 {
			urls = parseFrontmatterArray(values["source_urls"])
		}
		content = content[match[1]:]
	}
	if strings.TrimSpace(title) == "" {
		title = "無標題"
	}
	return title, content, categoryName, tags, urls
}

func parseSimpleFrontmatter(content string) map[string]string {
	values := map[string]string{}
	for _, line := range strings.Split(content, "\n") {
		key, value, ok := strings.Cut(line, ":")
		if !ok {
			continue
		}
		key = strings.TrimSpace(strings.ToLower(key))
		if key == "" {
			continue
		}
		values[key] = stripYAMLScalar(value)
	}
	return values
}

func stripYAMLScalar(value string) string {
	value = strings.TrimSpace(value)
	value = strings.Trim(value, "\"'")
	return value
}

func parseFrontmatterArray(value string) []string {
	value = strings.TrimSpace(value)
	if value == "" {
		return []string{}
	}
	if strings.HasPrefix(value, "[") && strings.HasSuffix(value, "]") {
		value = strings.TrimSpace(strings.TrimSuffix(strings.TrimPrefix(value, "["), "]"))
	}
	if value == "" {
		return []string{}
	}
	out := []string{}
	for _, item := range strings.Split(value, ",") {
		item = strings.TrimSpace(strings.Trim(item, "\"'"))
		if item != "" {
			out = append(out, item)
		}
	}
	return out
}

func (s *server) rewriteImportedMarkdownImages(ctx context.Context, content string, localImages map[string]markdownImportImage) (string, []string) {
	imagePattern := regexp.MustCompile(`!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)`)
	createdFiles := []string{}
	matches := imagePattern.FindAllStringSubmatchIndex(content, -1)
	if len(matches) == 0 {
		return content, createdFiles
	}
	var builder strings.Builder
	last := 0
	for _, match := range matches {
		builder.WriteString(content[last:match[0]])
		full := content[match[0]:match[1]]
		altText := content[match[2]:match[3]]
		ref := content[match[4]:match[5]]
		replacement := full
		switch {
		case strings.HasPrefix(ref, "/static/uploads/"):
			replacement = full
		case isHTTPURL(ref):
			if urlValue, files, ok := s.importRemoteMarkdownImage(ctx, ref); ok {
				replacement = fmt.Sprintf("![%s](%s)", altText, urlValue)
				createdFiles = append(createdFiles, files...)
			} else {
				replacement = markdownAltTextReplacement(altText)
			}
		default:
			if image, ok := localImages[strings.ReplaceAll(ref, "\\", "/")]; ok {
				if urlValue, files, ok := s.saveMarkdownImportImage(image.content, image.filename); ok {
					replacement = fmt.Sprintf("![%s](%s)", altText, urlValue)
					createdFiles = append(createdFiles, files...)
				} else {
					replacement = markdownAltTextReplacement(altText)
				}
			} else if image, ok := localImages[path.Base(strings.ReplaceAll(ref, "\\", "/"))]; ok {
				if urlValue, files, ok := s.saveMarkdownImportImage(image.content, image.filename); ok {
					replacement = fmt.Sprintf("![%s](%s)", altText, urlValue)
					createdFiles = append(createdFiles, files...)
				} else {
					replacement = markdownAltTextReplacement(altText)
				}
			} else {
				replacement = markdownAltTextReplacement(altText)
			}
		}
		builder.WriteString(replacement)
		last = match[1]
	}
	builder.WriteString(content[last:])
	return builder.String(), uniqueStrings(createdFiles)
}

func isHTTPURL(raw string) bool {
	parsed, err := url.Parse(raw)
	return err == nil && (parsed.Scheme == "http" || parsed.Scheme == "https") && parsed.Hostname() != ""
}

func markdownAltTextReplacement(altText string) string {
	altText = strings.TrimSpace(altText)
	if altText == "" {
		altText = "圖片"
	}
	return "[" + altText + "]"
}

func (s *server) importRemoteMarkdownImage(ctx context.Context, rawURL string) (string, []string, bool) {
	parsed, err := url.Parse(rawURL)
	if err != nil || parsed.Scheme == "" || parsed.Hostname() == "" {
		return "", nil, false
	}
	content, contentType, err := downloadUploadURLImage(ctx, parsed, rawURL)
	if err != nil {
		return "", nil, false
	}
	contentMIME := normalizeContentType(contentType)
	if !strings.HasPrefix(contentMIME, "image/") || int64(len(content)) > maxUploadFileBytes {
		return "", nil, false
	}
	if !allowedRemoteUploadMIME(detectUploadImageMIME(content)) {
		return "", nil, false
	}
	filename := timestampedUploadFilename(uploadURLBaseFilename(rawURL, parsed, contentMIME))
	data, err := s.saveDownloadedUpload(content, filename, rawURL, false)
	if err != nil {
		return "", nil, false
	}
	urlValue, _ := data["url"].(string)
	return urlValue, s.createdUploadPathsFromResponse(data), urlValue != ""
}

func (s *server) saveMarkdownImportImage(content []byte, sourceName string) (string, []string, bool) {
	detectedMIME := detectUploadImageMIME(content)
	if !allowedUploadMIME(detectedMIME) || int64(len(content)) > maxUploadFileBytes {
		return "", nil, false
	}
	filename := safeUploadFilename(sourceName)
	if filename == "" || !allowedUploadExtension(filename) {
		sum := md5.Sum([]byte(sourceName))
		filename = "imported_" + hex.EncodeToString(sum[:])[:8] + uploadExtensionForMIME(detectedMIME)
	}
	data, err := s.saveDownloadedUpload(content, timestampedUploadFilename(filename), sourceName, false)
	if err != nil {
		return "", nil, false
	}
	urlValue, _ := data["url"].(string)
	return urlValue, s.createdUploadPathsFromResponse(data), urlValue != ""
}

func (s *server) createdUploadPathsFromResponse(data response) []string {
	filenames := []string{}
	if raw, ok := data["filename"].(string); ok && raw != "" {
		filenames = append(filenames, uploadDeleteCandidates(raw)...)
	}
	if rawURL, ok := data["url"].(string); ok && rawURL != "" {
		if filename, ok := uploadReferenceFilename(rawURL); ok {
			filenames = append(filenames, uploadDeleteCandidates(filename)...)
		}
	}
	created := []string{}
	for _, filename := range uniqueStrings(filenames) {
		if absPath, ok := s.resolveUploadFile(filename); ok {
			if info, err := os.Stat(absPath); err == nil && info.Mode().IsRegular() {
				created = append(created, absPath)
			}
		}
	}
	return created
}

func cleanupImportFiles(paths []string) {
	for _, filePath := range uniqueStrings(paths) {
		_ = os.Remove(filePath)
	}
}

func objectField(payload map[string]any, key string) (map[string]any, bool) {
	raw, ok := payload[key]
	if !ok {
		return nil, false
	}
	obj, ok := raw.(map[string]any)
	return obj, ok
}

func objectArray(raw any) []map[string]any {
	items, ok := raw.([]any)
	if !ok {
		return nil
	}
	out := []map[string]any{}
	for _, item := range items {
		if obj, ok := item.(map[string]any); ok {
			out = append(out, obj)
		}
	}
	return out
}

func stringValue(raw any) string {
	if raw == nil {
		return ""
	}
	switch v := raw.(type) {
	case string:
		return v
	case fmt.Stringer:
		return v.String()
	default:
		return fmt.Sprint(v)
	}
}

func intValue(raw any) (int, bool) {
	switch v := raw.(type) {
	case int:
		return v, true
	case int64:
		return int(v), true
	case float64:
		if v == math.Trunc(v) {
			return int(v), true
		}
	}
	return 0, false
}

func boolIntValue(raw any) int {
	if value, ok := raw.(bool); ok && value {
		return 1
	}
	if value, ok := intValue(raw); ok && value != 0 {
		return 1
	}
	return 0
}

func stringArrayValue(raw any) []string {
	switch v := raw.(type) {
	case []string:
		return v
	case []any:
		out := []string{}
		for _, item := range v {
			text := strings.TrimSpace(stringValue(item))
			if text != "" {
				out = append(out, text)
			}
		}
		return out
	case string:
		if strings.TrimSpace(v) == "" {
			return nil
		}
		return []string{v}
	default:
		return nil
	}
}

func intArrayValue(raw any) ([]int, bool) {
	items, ok := raw.([]any)
	if !ok {
		return nil, false
	}
	out := []int{}
	for _, item := range items {
		if value, ok := intValue(item); ok {
			out = append(out, value)
		}
	}
	return out, true
}
