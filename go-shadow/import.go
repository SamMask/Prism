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

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	if err := importJSONCategoriesTx(tx, objectArray(importData["categories"])); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	defaultCategoryID, _ := defaultCategoryIDTx(tx)
	idMap := map[int]int{}
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
			writeError(w, http.StatusInternalServerError, err.Error())
			return
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
				writeError(w, http.StatusInternalServerError, err.Error())
				return
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

		result, err := tx.Exec(`
			INSERT INTO Notes (title, content, category_id, remarks, cover_image, created_at, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, ?)`,
			title,
			content,
			nullableIntArg(categoryID, categoryID > 0),
			stringValue(note["remarks"]),
			stringValue(note["cover_image"]),
			createdAt,
			updatedAt,
		)
		if err != nil {
			cleanupCreated()
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		newID64, err := result.LastInsertId()
		if err != nil {
			cleanupCreated()
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		newID := int(newID64)
		if hasOldID {
			idMap[oldID] = newID
		}
		if err := replaceNoteTags(tx, newID, stringArrayValue(note["tags"]), false); err != nil {
			cleanupCreated()
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		urls := stringArrayValue(note["urls"])
		if len(urls) == 0 {
			urls = stringArrayValue(note["source_urls"])
		}
		if err := replaceNoteURLs(tx, newID, urls); err != nil {
			cleanupCreated()
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		importedCount++
	}

	if err := s.restoreImportedAttachments(tx, idMap, importData, &createdFiles); err != nil {
		cleanupCreated()
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := s.restoreImportedUploads(importData, &createdFiles); err != nil {
		cleanupCreated()
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		cleanupCreated()
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if len(duplicates) > 10 {
		duplicates = duplicates[:10]
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"imported":   importedCount,
		"skipped":    skippedCount,
		"duplicates": duplicates,
	}})
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

func (s *server) restoreImportedAttachments(tx *sql.Tx, idMap map[int]int, importData map[string]any, createdFiles *[]string) error {
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
		resolved, ok := resolveAttachmentMutationPath(s.runtime.dataDir, filePath)
		if !ok {
			return fmt.Errorf("unsafe attachment path: %s", filePath)
		}
		contentB64 := stringValue(item["content_b64"])
		if contentB64 == "" {
			contentB64 = stringValue(item["content_base64"])
		}
		var sizeBytes any = nil
		if contentB64 != "" {
			content, err := base64.StdEncoding.DecodeString(contentB64)
			if err != nil {
				return fmt.Errorf("invalid attachment content_b64 for %s", filePath)
			}
			if int64(len(content)) > maxAttachmentFileBytes {
				return fmt.Errorf("attachment too large: %s", filePath)
			}
			if err := os.MkdirAll(filepath.Dir(resolved), 0755); err != nil {
				return err
			}
			if err := os.WriteFile(resolved, content, 0644); err != nil {
				return err
			}
			*createdFiles = append(*createdFiles, resolved)
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
			return err
		}
	}
	return nil
}

func (s *server) restoreImportedUploads(importData map[string]any, createdFiles *[]string) error {
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
			return fmt.Errorf("unsafe upload filename: %s", filename)
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
			return fmt.Errorf("invalid upload content_b64 for %s", filename)
		}
		if int64(len(content)) > maxUploadFileBytes {
			return fmt.Errorf("upload too large: %s", filename)
		}
		if err := os.MkdirAll(filepath.Dir(resolved), 0755); err != nil {
			return err
		}
		if err := os.WriteFile(resolved, content, 0644); err != nil {
			return err
		}
		*createdFiles = append(*createdFiles, resolved)
	}
	return nil
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
