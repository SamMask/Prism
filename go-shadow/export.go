package main

import (
	"archive/zip"
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode"
)

func (s *server) handleExportJSON(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	if !s.runtime.enableImportExport {
		_, _ = io.Copy(io.Discard, r.Body)
		writeError(w, http.StatusMethodNotAllowed, "Import/export route is disabled")
		return
	}

	notes, err := s.exportJSONNotes()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	categories, err := s.exportJSONCategories()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	tags, err := s.exportJSONTags()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	attachments, err := s.exportJSONAttachments()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	uploads, err := s.exportJSONUploadReferences()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	payload := response{
		"export_info": response{
			"version":           "1.6-go",
			"exported_at":       time.Now().Format(time.RFC3339Nano),
			"notes_count":       len(notes),
			"tags_count":        len(tags),
			"categories_count":  len(categories),
			"attachments_count": len(attachments),
			"uploads_count":     len(uploads),
		},
		"notes":       notes,
		"categories":  categories,
		"tags":        tags,
		"attachments": attachments,
		"uploads":     uploads,
	}
	content, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	filename := "local_insight_export_" + time.Now().Format("20060102_150405") + ".json"
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Content-Disposition", "attachment; filename="+filename)
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(content)
}

func (s *server) handleExportMarkdown(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	if !s.runtime.enableImportExport {
		_, _ = io.Copy(io.Discard, r.Body)
		writeError(w, http.StatusMethodNotAllowed, "Import/export route is disabled")
		return
	}
	content, err := s.buildMarkdownExportZip(nil)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	filename := "prism_markdown_" + time.Now().Format("20060102_150405") + ".zip"
	writeZipResponse(w, filename, content)
}

func (s *server) handleExportDB(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	if !s.runtime.enableImportExport {
		writeError(w, http.StatusMethodNotAllowed, "Import/export route is disabled")
		return
	}
	if _, err := os.Stat(s.runtime.dbPath); err != nil {
		if os.IsNotExist(err) {
			writeError(w, http.StatusNotFound, "Database file not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	filename := "local_insight_backup_" + time.Now().Format("20060102_150405") + ".db"
	w.Header().Set("Content-Type", "application/x-sqlite3")
	w.Header().Set("Content-Disposition", "attachment; filename="+filename)
	http.ServeFile(w, r, s.runtime.dbPath)
}

func (s *server) handleExportImages(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableImportExport {
		writeError(w, http.StatusMethodNotAllowed, "Import/export route is disabled")
		return
	}
	payload, ok := decodeJSONObject(w, r, "No images provided")
	if !ok {
		return
	}
	imageURLs := stringArrayValue(payload["images"])
	if len(imageURLs) == 0 {
		writeError(w, http.StatusBadRequest, "No images provided")
		return
	}
	if len(imageURLs) > maxExportImages {
		writeError(w, http.StatusBadRequest, "Maximum 100 images per export")
		return
	}

	var buf bytes.Buffer
	zipWriter := zip.NewWriter(&buf)
	for _, rawURL := range imageURLs {
		filename, ok := exportImageFilename(rawURL)
		if !ok {
			continue
		}
		absPath, ok := s.resolveUploadFile(filename)
		if !ok {
			continue
		}
		info, err := os.Stat(absPath)
		if err != nil || !info.Mode().IsRegular() {
			continue
		}
		if err := addFileToZip(zipWriter, absPath, filepath.ToSlash(filename)); err != nil {
			_ = zipWriter.Close()
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := zipWriter.Close(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	filename := sanitizeExportTitle(stringValue(payload["note_title"]))
	if filename == "" {
		filename = "images"
	}
	filename = filename + "_images_" + time.Now().Format("20060102_150405") + ".zip"
	w.Header().Set("Content-Type", "application/zip")
	w.Header().Set("Content-Disposition", "attachment; filename*=UTF-8''"+filename)
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(buf.Bytes())
}

func (s *server) importMarkdown(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseMultipartForm(maxMarkdownImportBytes + maxUploadFileBytes*4); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid multipart upload")
		return
	}
	file, header, err := r.FormFile("file")
	if err != nil {
		writeError(w, http.StatusBadRequest, "No file provided")
		return
	}
	defer file.Close()
	if strings.TrimSpace(header.Filename) == "" {
		writeError(w, http.StatusBadRequest, "No file selected")
		return
	}
	if !strings.HasSuffix(strings.ToLower(header.Filename), ".md") {
		writeError(w, http.StatusBadRequest, "Only .md files are supported")
		return
	}
	contentBytes, err := io.ReadAll(io.LimitReader(file, maxMarkdownImportBytes+1))
	if err != nil {
		writeError(w, http.StatusBadRequest, "Failed to read markdown file")
		return
	}
	if int64(len(contentBytes)) > maxMarkdownImportBytes {
		writeError(w, http.StatusBadRequest, "Markdown file too large")
		return
	}

	localImages, err := markdownImportImageParts(r.MultipartForm)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	title, body, categoryName, tags, urls := parseMarkdownImport(string(contentBytes), header.Filename)
	body, createdFiles := s.rewriteImportedMarkdownImages(r.Context(), body, localImages)
	body = strings.TrimSpace(body)

	tx, err := s.db.Begin()
	if err != nil {
		cleanupImportFiles(createdFiles)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	categoryID, _ := categoryIDForNameTx(tx, categoryName)
	if categoryID == 0 {
		categoryID, _ = defaultCategoryIDTx(tx)
	}
	result, err := tx.Exec(`
		INSERT INTO Notes (title, content, category_id, created_at, updated_at)
		VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
		title, body, nullableIntArg(categoryID, categoryID > 0))
	if err != nil {
		cleanupImportFiles(createdFiles)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	noteID64, err := result.LastInsertId()
	if err != nil {
		cleanupImportFiles(createdFiles)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	noteID := int(noteID64)
	if err := replaceNoteTags(tx, noteID, tags, false); err != nil {
		cleanupImportFiles(createdFiles)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteURLs(tx, noteID, urls); err != nil {
		cleanupImportFiles(createdFiles)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		cleanupImportFiles(createdFiles)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"note_id": noteID}})
}

func (s *server) exportBatchMarkdown(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "No notes selected")
	if !ok {
		return
	}
	noteIDs, ok := intArrayValue(payload["note_ids"])
	if !ok || len(noteIDs) == 0 {
		writeError(w, http.StatusBadRequest, "No notes selected")
		return
	}
	content, err := s.buildBatchMarkdownZip(noteIDs)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeZipResponse(w, "local_insight_export.zip", content)
}

func (s *server) exportJSONNotes() ([]response, error) {
	rows, err := s.db.Query(`
		SELECT
			n.id, n.title, n.content, COALESCE(c.name, 'Uncategorized') AS category,
			n.remarks, n.cover_image, n.created_at, n.updated_at,
			(SELECT GROUP_CONCAT(t2.name, '||')
			 FROM Note_Tags nt2 JOIN Tags t2 ON nt2.tag_id = t2.id
			 WHERE nt2.note_id = n.id) AS tags,
			(SELECT GROUP_CONCAT(s2.url, '||')
			 FROM Source_Urls s2
			 WHERE s2.note_id = n.id) AS urls
		FROM Notes n
		LEFT JOIN Categories c ON n.category_id = c.id
		ORDER BY n.updated_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	notes := []response{}
	for rows.Next() {
		var id int
		var title, content, category, remarks, coverImage, createdAt, updatedAt, tags, urls sql.NullString
		if err := rows.Scan(&id, &title, &content, &category, &remarks, &coverImage, &createdAt, &updatedAt, &tags, &urls); err != nil {
			return nil, err
		}
		notes = append(notes, response{
			"id":          id,
			"title":       nullableString(title),
			"content":     nullableString(content),
			"category":    nullableString(category),
			"remarks":     nullableStringOrNil(remarks),
			"cover_image": nullableStringOrNil(coverImage),
			"created_at":  nullableString(createdAt),
			"updated_at":  nullableString(updatedAt),
			"tags":        splitPipeList(tags),
			"urls":        splitPipeList(urls),
		})
	}
	return notes, rows.Err()
}

func (s *server) exportJSONCategories() ([]response, error) {
	rows, err := s.db.Query("SELECT id, name, icon, sort_order, is_default, system_key, name_override FROM Categories ORDER BY sort_order, id")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	categories := []response{}
	for rows.Next() {
		var id, sortOrder, isDefault int
		var name, icon, systemKey, nameOverride sql.NullString
		if err := rows.Scan(&id, &name, &icon, &sortOrder, &isDefault, &systemKey, &nameOverride); err != nil {
			return nil, err
		}
		categories = append(categories, response{
			"id": id, "name": nullableString(name), "icon": nullableStringOrNil(icon),
			"sort_order": sortOrder, "is_default": isDefault != 0,
			"system_key": nullableStringOrNil(systemKey), "name_override": nullableStringOrNil(nameOverride),
		})
	}
	return categories, rows.Err()
}

func (s *server) exportJSONTags() ([]response, error) {
	rows, err := s.db.Query("SELECT id, name FROM Tags ORDER BY name")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	tags := []response{}
	for rows.Next() {
		var id int
		var name sql.NullString
		if err := rows.Scan(&id, &name); err != nil {
			return nil, err
		}
		tags = append(tags, response{"id": id, "name": nullableString(name)})
	}
	return tags, rows.Err()
}

func (s *server) exportJSONAttachments() ([]response, error) {
	rows, err := s.db.Query(`
		SELECT id, note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at
		FROM Note_Attachments
		ORDER BY id`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	attachments := []response{}
	for rows.Next() {
		var id, noteID, isAuto int
		var filePath, fileType, title, createdAt sql.NullString
		var size sql.NullInt64
		if err := rows.Scan(&id, &noteID, &filePath, &fileType, &title, &size, &isAuto, &createdAt); err != nil {
			return nil, err
		}
		attachments = append(attachments, response{
			"id": id, "note_id": noteID, "file_path": nullableString(filePath),
			"file_type": nullableStringOrNil(fileType), "title": nullableStringOrNil(title),
			"size_bytes": nullableIntOrNil(size), "is_auto_extracted": isAuto != 0,
			"created_at": nullableStringOrNil(createdAt),
		})
	}
	return attachments, rows.Err()
}

func (s *server) exportJSONUploadReferences() ([]response, error) {
	referenced, err := s.referencedUploadFilenames()
	if err != nil {
		return nil, err
	}
	names := make([]string, 0, len(referenced))
	for name := range referenced {
		names = append(names, name)
	}
	sort.Strings(names)
	uploads := []response{}
	for _, name := range names {
		item := response{"filename": name, "url": "/static/uploads/" + name}
		if absPath, ok := s.resolveUploadFile(name); ok {
			if info, err := os.Stat(absPath); err == nil && info.Mode().IsRegular() {
				item["size_bytes"] = info.Size()
				item["exists"] = true
			} else {
				item["exists"] = false
			}
		}
		uploads = append(uploads, item)
	}
	return uploads, nil
}

func splitPipeList(value sql.NullString) []string {
	if !value.Valid || value.String == "" {
		return []string{}
	}
	out := []string{}
	for _, item := range strings.Split(value.String, "||") {
		item = strings.TrimSpace(item)
		if item != "" {
			out = append(out, item)
		}
	}
	return out
}

func (s *server) buildMarkdownExportZip(noteIDs []int) ([]byte, error) {
	where := ""
	args := []any{}
	if len(noteIDs) > 0 {
		where = "WHERE n.id IN (" + placeholders(len(noteIDs)) + ")"
		args = intsToAny(noteIDs)
	}
	rows, err := s.db.Query(`
		SELECT
			n.id, n.title, n.content, n.remarks, n.cover_image,
			COALESCE(n.is_pinned, 0), COALESCE(n.is_archived, 0),
			n.created_at, n.updated_at,
			COALESCE(c.name, 'Uncategorized') AS category,
			(SELECT GROUP_CONCAT(t.name, '||')
			 FROM Note_Tags nt JOIN Tags t ON nt.tag_id = t.id
			 WHERE nt.note_id = n.id) AS tags
		FROM Notes n
		LEFT JOIN Categories c ON n.category_id = c.id
		`+where+`
		ORDER BY n.id`, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var buf bytes.Buffer
	zipWriter := zip.NewWriter(&buf)
	includedImages := map[string]string{}
	usedArcNames := map[string]string{}
	writtenArcNames := map[string]bool{}
	notesCount := 0

	for rows.Next() {
		var id, isPinned, isArchived int
		var title, content, remarks, coverImage, createdAt, updatedAt, category, tags sql.NullString
		if err := rows.Scan(&id, &title, &content, &remarks, &coverImage, &isPinned, &isArchived, &createdAt, &updatedAt, &category, &tags); err != nil {
			_ = zipWriter.Close()
			return nil, err
		}
		notesCount++
		coverArc := s.addExportImage(zipWriter, includedImages, usedArcNames, writtenArcNames, nullableStringOrNil(coverImage))
		body := s.rewriteMarkdownExportRefs(zipWriter, includedImages, usedArcNames, writtenArcNames, nullableString(content))
		tagList := splitPipeList(tags)
		frontmatter := strings.Builder{}
		frontmatter.WriteString("---\n")
		frontmatter.WriteString(fmt.Sprintf("id: %d\n", id))
		frontmatter.WriteString("title: " + yamlEscape(nullableString(title)) + "\n")
		frontmatter.WriteString("category: " + yamlEscape(nullableString(category)) + "\n")
		frontmatter.WriteString("tags: " + yamlArray(tagList) + "\n")
		frontmatter.WriteString(fmt.Sprintf("is_pinned: %t\n", isPinned != 0))
		frontmatter.WriteString(fmt.Sprintf("is_archived: %t\n", isArchived != 0))
		frontmatter.WriteString("created_at: " + yamlEscape(nullableString(createdAt)) + "\n")
		frontmatter.WriteString("updated_at: " + yamlEscape(nullableString(updatedAt)) + "\n")
		if coverArc != "" {
			frontmatter.WriteString("cover_image: " + yamlEscape(coverArc) + "\n")
		}
		if remarks.Valid && remarks.String != "" {
			frontmatter.WriteString("remarks: " + yamlEscape(remarks.String) + "\n")
		}
		frontmatter.WriteString("---\n\n")
		filename := fmt.Sprintf("%04d-%s.md", id, markdownSlug(nullableString(title), 40))
		if err := writeZipString(zipWriter, filename, frontmatter.String()+body); err != nil {
			_ = zipWriter.Close()
			return nil, err
		}
	}
	if err := rows.Err(); err != nil {
		_ = zipWriter.Close()
		return nil, err
	}
	manifest := response{"export_info": response{
		"version": "1.0", "format": "markdown", "exported_at": time.Now().Format(time.RFC3339Nano),
		"notes_count": notesCount, "images_count": len(includedImages),
	}}
	manifestBytes, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		_ = zipWriter.Close()
		return nil, err
	}
	if err := writeZipString(zipWriter, "_manifest.json", string(manifestBytes)); err != nil {
		_ = zipWriter.Close()
		return nil, err
	}
	if err := zipWriter.Close(); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func (s *server) buildBatchMarkdownZip(noteIDs []int) ([]byte, error) {
	rows, err := s.db.Query(`
		SELECT n.id, n.title, n.content, COALESCE(c.name, 'Uncategorized') AS category, n.remarks
		FROM Notes n
		LEFT JOIN Categories c ON n.category_id = c.id
		WHERE n.id IN (`+placeholders(len(noteIDs))+`)
		ORDER BY n.id`, intsToAny(noteIDs)...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var buf bytes.Buffer
	zipWriter := zip.NewWriter(&buf)
	writtenAssets := map[string]bool{}
	for rows.Next() {
		var id int
		var title, content, category, remarks sql.NullString
		if err := rows.Scan(&id, &title, &content, &category, &remarks); err != nil {
			_ = zipWriter.Close()
			return nil, err
		}
		tags, err := s.noteTags(id)
		if err != nil {
			_ = zipWriter.Close()
			return nil, err
		}
		md := buildBatchMarkdownContent(nullableString(title), nullableString(category), tagNames(tags), nullableString(content), nullableStringOrNil(remarks))
		filename := fmt.Sprintf("notes/%s_%d.md", sanitizeBatchFilename(nullableString(title)), id)
		if err := writeZipString(zipWriter, filename, md); err != nil {
			_ = zipWriter.Close()
			return nil, err
		}
		for _, ref := range collectMarkdownImageRefs(nullableString(content)) {
			filename, ok := exportImageFilename(ref)
			if !ok || writtenAssets[filename] {
				continue
			}
			absPath, ok := s.resolveUploadFile(filename)
			if !ok {
				continue
			}
			if info, err := os.Stat(absPath); err != nil || !info.Mode().IsRegular() {
				continue
			}
			if err := addFileToZip(zipWriter, absPath, "assets/"+filepath.ToSlash(filename)); err != nil {
				_ = zipWriter.Close()
				return nil, err
			}
			writtenAssets[filename] = true
		}
	}
	if err := rows.Err(); err != nil {
		_ = zipWriter.Close()
		return nil, err
	}
	if err := zipWriter.Close(); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func (s *server) addExportImage(zipWriter *zip.Writer, included, used map[string]string, written map[string]bool, rawRef any) string {
	ref, ok := rawRef.(string)
	if !ok || strings.TrimSpace(ref) == "" {
		return ""
	}
	filename, ok := exportImageFilename(ref)
	if !ok {
		return ""
	}
	absPath, ok := s.resolveUploadFile(filename)
	if !ok {
		return ""
	}
	info, err := os.Stat(absPath)
	if err != nil || !info.Mode().IsRegular() {
		return ""
	}
	absPath = filepath.Clean(absPath)
	if arc, ok := included[absPath]; ok {
		return arc
	}
	base := path.Base(filepath.ToSlash(filename))
	stem := strings.TrimSuffix(base, path.Ext(base))
	ext := path.Ext(base)
	arc := "images/" + base
	index := 2
	for usedPath, exists := used[arc]; exists && usedPath != absPath; usedPath, exists = used[arc] {
		arc = fmt.Sprintf("images/%s-%d%s", stem, index, ext)
		index++
	}
	if !written[arc] {
		if err := addFileToZip(zipWriter, absPath, arc); err != nil {
			return ""
		}
		written[arc] = true
	}
	included[absPath] = arc
	used[arc] = absPath
	return arc
}

func (s *server) rewriteMarkdownExportRefs(zipWriter *zip.Writer, included, used map[string]string, written map[string]bool, body string) string {
	rewritten := body
	for _, ref := range collectMarkdownImageRefs(body) {
		arc := s.addExportImage(zipWriter, included, used, written, ref)
		if arc != "" {
			rewritten = strings.ReplaceAll(rewritten, ref, arc)
		}
	}
	return rewritten
}

func collectMarkdownImageRefs(body string) []string {
	refs := []string{}
	mdPattern := regexp.MustCompile(`!\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)`)
	for _, match := range mdPattern.FindAllStringSubmatch(body, -1) {
		if len(match) > 1 {
			refs = append(refs, match[1])
		}
	}
	htmlPattern := regexp.MustCompile(`(?i)<img\b[^>]*\bsrc=["']([^"']+)["']`)
	for _, match := range htmlPattern.FindAllStringSubmatch(body, -1) {
		if len(match) > 1 {
			refs = append(refs, match[1])
		}
	}
	return uniqueStrings(refs)
}

func exportImageFilename(raw string) (string, bool) {
	raw = strings.TrimSpace(strings.ReplaceAll(raw, "\\", "/"))
	if raw == "" {
		return "", false
	}
	if parsed, err := url.Parse(raw); err == nil {
		if parsed.Scheme != "" {
			raw = parsed.Path
		}
		if unescaped, err := url.PathUnescape(raw); err == nil {
			raw = unescaped
		}
	}
	switch {
	case strings.Contains(raw, "/static/uploads/"):
		raw = strings.Split(raw, "/static/uploads/")[1]
	case strings.HasPrefix(raw, "static/uploads/"):
		raw = strings.TrimPrefix(raw, "static/uploads/")
	case strings.HasPrefix(raw, "/uploads/"):
		raw = strings.TrimPrefix(raw, "/uploads/")
	default:
		raw = strings.TrimPrefix(raw, "/")
	}
	return uploadReferenceFilename(raw)
}

func addFileToZip(zipWriter *zip.Writer, absPath, arcName string) error {
	file, err := os.Open(absPath)
	if err != nil {
		return err
	}
	defer file.Close()
	writer, err := zipWriter.Create(filepath.ToSlash(arcName))
	if err != nil {
		return err
	}
	_, err = io.Copy(writer, file)
	return err
}

func writeZipString(zipWriter *zip.Writer, arcName, content string) error {
	writer, err := zipWriter.Create(filepath.ToSlash(arcName))
	if err != nil {
		return err
	}
	_, err = writer.Write([]byte(content))
	return err
}

func writeZipResponse(w http.ResponseWriter, filename string, content []byte) {
	w.Header().Set("Content-Type", "application/zip")
	w.Header().Set("Content-Disposition", "attachment; filename="+filename)
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(content)
}

func yamlEscape(value string) string {
	value = strings.ReplaceAll(value, "\\", "\\\\")
	value = strings.ReplaceAll(value, "\"", "\\\"")
	value = strings.ReplaceAll(value, "\n", " ")
	return "\"" + value + "\""
}

func yamlArray(values []string) string {
	if len(values) == 0 {
		return "[]"
	}
	items := make([]string, 0, len(values))
	for _, value := range values {
		items = append(items, yamlEscape(value))
	}
	return "[" + strings.Join(items, ", ") + "]"
}

func markdownSlug(value string, limit int) string {
	var builder strings.Builder
	lastDash := false
	for _, r := range strings.TrimSpace(value) {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' {
			builder.WriteRune(r)
			lastDash = false
			continue
		}
		if !lastDash {
			builder.WriteRune('-')
			lastDash = true
		}
	}
	slug := strings.Trim(builder.String(), "-")
	if slug == "" {
		slug = "untitled"
	}
	runes := []rune(slug)
	if len(runes) > limit {
		return string(runes[:limit])
	}
	return slug
}

func sanitizeBatchFilename(name string) string {
	cleaned := strings.Map(func(r rune) rune {
		switch r {
		case '<', '>', ':', '"', '/', '\\', '|', '?', '*':
			return -1
		default:
			return r
		}
	}, strings.TrimSpace(name))
	runes := []rune(cleaned)
	if len(runes) > 50 {
		cleaned = string(runes[:50])
	}
	if strings.TrimSpace(cleaned) == "" {
		return "untitled"
	}
	return strings.TrimSpace(cleaned)
}

func sanitizeExportTitle(name string) string {
	name = strings.TrimSpace(name)
	if name == "" {
		return ""
	}
	var builder strings.Builder
	for _, r := range name {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' {
			builder.WriteRune(r)
		} else {
			builder.WriteRune('_')
		}
	}
	runes := []rune(builder.String())
	if len(runes) > 50 {
		return string(runes[:50])
	}
	return builder.String()
}

func buildBatchMarkdownContent(title, category string, tags []string, content string, remarks any) string {
	var builder strings.Builder
	builder.WriteString("---\n")
	builder.WriteString("title: " + yamlEscape(title) + "\n")
	builder.WriteString("type: " + category + "\n")
	builder.WriteString("category: " + category + "\n")
	builder.WriteString("tags: [" + strings.Join(tags, ", ") + "]\n")
	builder.WriteString("---\n\n")
	builder.WriteString(content)
	if remark, ok := remarks.(string); ok && remark != "" {
		builder.WriteString("\n\n---\n\n> **備註**: " + remark)
	}
	return builder.String()
}

func tagNames(tags []tagRef) []string {
	names := make([]string, 0, len(tags))
	for _, tag := range tags {
		names = append(names, tag.Name)
	}
	return names
}
