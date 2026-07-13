package main

import (
	"database/sql"
	"math"
	"mime"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"
	"unicode"
)

func (s *server) handleNotes(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/api/notes" {
		http.NotFound(w, r)
		return
	}
	if r.Method == http.MethodPost {
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.createNote(w, r)
		return
	}
	if !requireGET(w, r) {
		return
	}

	page := intQuery(r, "page", 1)
	if page < 1 {
		page = 1
	}
	perPage := intQuery(r, "per_page", 20)
	if perPage < 1 {
		perPage = 1
	}
	if perPage > 100 {
		perPage = 100
	}

	where, args, searchDiagnostics := s.buildNotesWhere(r)
	var total int
	if err := s.db.QueryRow("SELECT COUNT(*) FROM Notes n LEFT JOIN Categories c ON n.category_id = c.id "+where, args...).Scan(&total); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	sortClause := "n.updated_at DESC"
	switch r.URL.Query().Get("sort") {
	case "custom":
		sortClause = "COALESCE(n.sort_order, n.id) ASC"
	case "created":
		sortClause = "n.created_at DESC"
	}
	offset := (page - 1) * perPage
	queryArgs := append(append([]any{}, args...), perPage, offset)
	rows, err := s.db.Query(`
		SELECT n.id, n.title, n.content, COALESCE(c.name, 'Uncategorized') AS category_name,
		       n.remarks, n.cover_image, COALESCE(n.cover_position, 'top') AS cover_position,
		       COALESCE(n.editor_layout, 'single') AS editor_layout,
		       COALESCE(n.is_pinned, 0) AS is_pinned, COALESCE(n.is_archived, 0) AS is_archived,
		       n.category_id, n.created_at, n.updated_at, n.parent_id, p.title AS parent_title,
		       (SELECT COUNT(*) FROM Notes child WHERE child.parent_id = n.id) AS variants_count
		FROM Notes n
		LEFT JOIN Categories c ON n.category_id = c.id
		LEFT JOIN Notes p ON n.parent_id = p.id
		`+where+`
		ORDER BY COALESCE(n.is_pinned, 0) DESC, `+sortClause+`
		LIMIT ? OFFSET ?`, queryArgs...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	items := []response{}
	for rows.Next() {
		note, err := s.scanNoteRow(rows)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		applyNoteListContentPreview(note)
		items = append(items, note)
	}
	payload := response{
		"status": "success",
		"data":   items,
		"pagination": response{
			"page": page, "per_page": perPage, "total": total,
			"total_pages": int(math.Ceil(float64(total) / float64(perPage))),
		},
	}
	if searchDiagnostics != nil && searchDiagnostics.Partial {
		payload["search_diagnostics"] = response{
			"attachment_body_scan": searchDiagnostics.toResponse(),
		}
	}
	writeJSON(w, http.StatusOK, payload)
}

func (s *server) buildNotesWhere(r *http.Request) (string, []any, *attachmentScanDiagnostics) {
	clauses := []string{"1 = 1"}
	args := []any{}
	var diagnostics *attachmentScanDiagnostics
	if boolString(r, "archived") {
		clauses = append(clauses, "COALESCE(n.is_archived, 0) = 1")
	} else if !boolString(r, "include_archived") {
		clauses = append(clauses, "COALESCE(n.is_archived, 0) = 0")
	}
	if boolString(r, "pinned_only") {
		clauses = append(clauses, "COALESCE(n.is_pinned, 0) = 1")
	}
	if categoryID := r.URL.Query().Get("category_id"); categoryID != "" {
		clauses = append(clauses, "n.category_id = ?")
		args = append(args, categoryID)
	}
	if parentID := r.URL.Query().Get("parent_id"); parentID != "" {
		clauses = append(clauses, "n.parent_id = ?")
		args = append(args, parentID)
	}
	if noteType := r.URL.Query().Get("type"); noteType != "" && !strings.EqualFold(noteType, "all") {
		var categoryID int
		if err := s.db.QueryRow("SELECT id FROM Categories WHERE name = ? OR name_override = ? LIMIT 1", noteType, noteType).Scan(&categoryID); err == nil {
			clauses = append(clauses, "n.category_id = ?")
			args = append(args, categoryID)
		}
	}
	if tags := parseCSVInts(r.URL.Query().Get("tags")); len(tags) > 0 {
		placeholders := strings.TrimRight(strings.Repeat("?,", len(tags)), ",")
		if strings.EqualFold(r.URL.Query().Get("tag_mode"), "OR") {
			clauses = append(clauses, "n.id IN (SELECT note_id FROM Note_Tags WHERE tag_id IN ("+placeholders+"))")
			for _, tag := range tags {
				args = append(args, tag)
			}
		} else {
			clauses = append(clauses, "n.id IN (SELECT note_id FROM Note_Tags WHERE tag_id IN ("+placeholders+") GROUP BY note_id HAVING COUNT(DISTINCT tag_id) = ?)")
			for _, tag := range tags {
				args = append(args, tag)
			}
			args = append(args, len(tags))
		}
	}
	if q := strings.TrimSpace(r.URL.Query().Get("q")); q != "" {
		q = truncateRunes(q, 200)
		searchClause, searchArgs, searchDiagnostics := s.buildNotesSearchClause(q)
		if searchClause != "" {
			clauses = append(clauses, searchClause)
			args = append(args, searchArgs...)
		}
		diagnostics = searchDiagnostics
	}
	return "WHERE " + strings.Join(clauses, " AND "), args, diagnostics
}

func truncateRunes(value string, maxRunes int) string {
	if maxRunes <= 0 {
		return ""
	}
	count := 0
	for index := range value {
		if count == maxRunes {
			return value[:index]
		}
		count++
	}
	return value
}

func (s *server) buildNotesSearchClause(keyword string) (string, []any, *attachmentScanDiagnostics) {
	tokens := searchTokens(keyword)
	clauses := []string{}
	args := []any{}
	var diagnostics *attachmentScanDiagnostics
	if ftsQuery := sanitizeFTSQuery(keyword); ftsQuery != "" {
		clauses = append(clauses, "n.id IN (SELECT rowid FROM Notes_FTS WHERE Notes_FTS MATCH ?)")
		args = append(args, ftsQuery)
	}
	if len(tokens) > 0 {
		clauses = append(clauses, tokenAndClause("LOWER(COALESCE(n.remarks, '')) LIKE ?", tokens, &args))
		clauses = append(clauses, tagTokenSearchClause(tokens, &args))
		clauses = append(clauses, attachmentMetadataTokenSearchClause(tokens, &args))
	}
	attachmentNoteIDs, scanDiagnostics := s.attachmentContentNoteIDs(keyword)
	diagnostics = scanDiagnostics
	if len(attachmentNoteIDs) > 0 {
		clauses = append(clauses, "n.id IN ("+placeholders(len(attachmentNoteIDs))+")")
		for _, noteID := range attachmentNoteIDs {
			args = append(args, noteID)
		}
	}
	if len(clauses) == 0 {
		return "", nil, diagnostics
	}
	return "(" + strings.Join(clauses, " OR ") + ")", args, diagnostics
}

type attachmentScanDiagnostics struct {
	ScannedFiles int
	ScannedBytes int64
	Partial      bool
	Reason       string
}

func (d *attachmentScanDiagnostics) markPartial(reason string) {
	if d.Partial {
		return
	}
	d.Partial = true
	d.Reason = reason
}

func (d *attachmentScanDiagnostics) toResponse() response {
	out := response{
		"partial":       d.Partial,
		"reason":        d.Reason,
		"scanned_files": d.ScannedFiles,
		"scanned_bytes": d.ScannedBytes,
		"limits": response{
			"files":       maxAttachmentScanFiles,
			"bytes":       maxAttachmentScanBytes,
			"duration_ms": maxAttachmentScanDuration.Milliseconds(),
		},
	}
	if !d.Partial {
		out["reason"] = nil
	}
	return out
}

func tokenAndClause(condition string, tokens []string, args *[]any) string {
	parts := make([]string, 0, len(tokens))
	for _, token := range tokens {
		parts = append(parts, condition)
		*args = append(*args, "%"+token+"%")
	}
	return "(" + strings.Join(parts, " AND ") + ")"
}

func tagTokenSearchClause(tokens []string, args *[]any) string {
	parts := make([]string, 0, len(tokens))
	for _, token := range tokens {
		parts = append(parts, `EXISTS (
			SELECT 1 FROM Note_Tags nt
			JOIN Tags t ON nt.tag_id = t.id
			WHERE nt.note_id = n.id
			AND LOWER(t.name) LIKE ?
		)`)
		*args = append(*args, "%"+token+"%")
	}
	return "(" + strings.Join(parts, " AND ") + ")"
}

func attachmentMetadataTokenSearchClause(tokens []string, args *[]any) string {
	parts := make([]string, 0, len(tokens))
	for _, token := range tokens {
		parts = append(parts, `EXISTS (
			SELECT 1 FROM Note_Attachments a
			WHERE a.note_id = n.id
			AND (
				LOWER(COALESCE(a.title, '')) LIKE ?
				OR LOWER(COALESCE(a.file_path, '')) LIKE ?
			)
		)`)
		like := "%" + token + "%"
		*args = append(*args, like, like)
	}
	return "(" + strings.Join(parts, " AND ") + ")"
}

func placeholders(count int) string {
	if count <= 0 {
		return ""
	}
	return strings.TrimRight(strings.Repeat("?,", count), ",")
}

func searchTokens(keyword string) []string {
	keyword = strings.ToLower(keyword)
	var builder strings.Builder
	for _, r := range keyword {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			builder.WriteRune(r)
		} else {
			builder.WriteRune(' ')
		}
	}
	parts := strings.Fields(builder.String())
	if len(parts) > 20 {
		return parts[:20]
	}
	return parts
}

func sanitizeFTSQuery(keyword string) string {
	tokens := searchTokens(keyword)
	quoted := make([]string, 0, len(tokens))
	for _, token := range tokens {
		quoted = append(quoted, `"`+token+`"*`)
	}
	return strings.Join(quoted, " ")
}

func (s *server) attachmentContentNoteIDs(keyword string) ([]int, *attachmentScanDiagnostics) {
	tokens := searchTokens(keyword)
	if len(tokens) == 0 {
		return nil, nil
	}
	diagnostics := &attachmentScanDiagnostics{}
	rows, err := s.db.Query(`
		SELECT note_id, file_path, file_type
		FROM Note_Attachments
		WHERE LOWER(COALESCE(file_type, '')) IN ('md', 'markdown', 'txt')`)
	if err != nil {
		diagnostics.markPartial("query_error")
		return nil, diagnostics
	}
	defer rows.Close()

	deadline := time.Now().Add(maxAttachmentScanDuration)
	filesRead := 0
	var totalBytes int64
	noteIDs := map[int]bool{}
	for rows.Next() {
		if filesRead >= maxAttachmentScanFiles || totalBytes >= maxAttachmentScanBytes || time.Now().After(deadline) {
			switch {
			case filesRead >= maxAttachmentScanFiles:
				diagnostics.markPartial("file_limit")
			case totalBytes >= maxAttachmentScanBytes:
				diagnostics.markPartial("byte_limit")
			default:
				diagnostics.markPartial("time_limit")
			}
			break
		}
		var noteID int
		var filePath, fileType sql.NullString
		if err := rows.Scan(&noteID, &filePath, &fileType); err != nil {
			diagnostics.markPartial("scan_error")
			return sortedIntKeys(noteIDs), diagnostics
		}
		resolved, size, ok := resolveAttachmentFile(s.runtime.dataDir, nullableString(filePath), nullableString(fileType))
		if !ok {
			continue
		}
		if totalBytes+size > maxAttachmentScanBytes {
			diagnostics.markPartial("byte_limit")
			break
		}
		content, err := os.ReadFile(resolved)
		filesRead++
		totalBytes += size
		diagnostics.ScannedFiles = filesRead
		diagnostics.ScannedBytes = totalBytes
		if err != nil {
			continue
		}
		text := strings.ToLower(strings.TrimPrefix(string(content), "\ufeff"))
		if containsAllTokens(text, tokens) {
			noteIDs[noteID] = true
		}
	}
	if err := rows.Err(); err != nil {
		diagnostics.markPartial("scan_error")
	}
	return sortedIntKeys(noteIDs), diagnostics
}

func resolveAttachmentFile(dataDir, relativePath, fileType string) (string, int64, bool) {
	if !isAllowedAttachmentPath(relativePath, fileType) {
		return "", 0, false
	}
	root, err := filepath.Abs(dataDir)
	if err != nil {
		return "", 0, false
	}
	evaluatedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return "", 0, false
	}
	candidate := filepath.Join(root, filepath.FromSlash(relativePath))
	absCandidate, err := filepath.Abs(candidate)
	if err != nil || !isSubpath(absCandidate, root) {
		return "", 0, false
	}
	info, err := os.Lstat(absCandidate)
	if err != nil || !info.Mode().IsRegular() || info.Size() > maxAttachmentFileBytes {
		return "", 0, false
	}
	resolved, err := filepath.EvalSymlinks(absCandidate)
	if err != nil || !isSubpath(resolved, evaluatedRoot) {
		return "", 0, false
	}
	return resolved, info.Size(), true
}

func resolveAttachmentRawFile(dataDir, relativePath, fileType string) (string, int64, bool) {
	if !isAllowedRawAttachmentPath(relativePath, fileType) {
		return "", 0, false
	}
	root, err := filepath.Abs(dataDir)
	if err != nil {
		return "", 0, false
	}
	evaluatedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return "", 0, false
	}
	candidate := filepath.Join(root, filepath.FromSlash(strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))))
	absCandidate, err := filepath.Abs(candidate)
	if err != nil || !isSubpath(absCandidate, root) {
		return "", 0, false
	}
	info, err := os.Lstat(absCandidate)
	if err != nil || !info.Mode().IsRegular() || info.Size() > maxUploadFileBytes {
		return "", 0, false
	}
	resolved, err := filepath.EvalSymlinks(absCandidate)
	if err != nil || !isSubpath(resolved, evaluatedRoot) {
		return "", 0, false
	}
	return resolved, info.Size(), true
}

func isAllowedAttachmentPath(relativePath, fileType string) bool {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	fileType = strings.TrimPrefix(strings.ToLower(strings.TrimSpace(fileType)), ".")
	if relativePath == "" || filepath.IsAbs(relativePath) || filepath.VolumeName(relativePath) != "" || strings.Contains(relativePath, ":") {
		return false
	}
	parts := strings.Split(relativePath, "/")
	for _, part := range parts {
		if part == ".." {
			return false
		}
	}
	cleaned := path.Clean(relativePath)
	if cleaned == "." || strings.HasPrefix(cleaned, "../") || cleaned == ".." {
		return false
	}
	if !strings.HasPrefix(cleaned, "docs/attachments/") && !strings.HasPrefix(cleaned, "docs/notes/") {
		return false
	}
	ext := strings.TrimPrefix(strings.ToLower(path.Ext(cleaned)), ".")
	return ext == fileType && (ext == "md" || ext == "markdown" || ext == "txt")
}

func isAllowedRawAttachmentPath(relativePath, fileType string) bool {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	fileType = strings.TrimPrefix(strings.ToLower(strings.TrimSpace(fileType)), ".")
	if relativePath == "" || filepath.IsAbs(relativePath) || filepath.VolumeName(relativePath) != "" || strings.Contains(relativePath, ":") {
		return false
	}
	for _, part := range strings.Split(relativePath, "/") {
		if part == ".." {
			return false
		}
	}
	cleaned := path.Clean(relativePath)
	if cleaned == "." || strings.HasPrefix(cleaned, "../") || cleaned == ".." || !strings.HasPrefix(cleaned, "docs/attachments/") {
		return false
	}
	ext := strings.TrimPrefix(strings.ToLower(path.Ext(cleaned)), ".")
	if ext != fileType {
		return false
	}
	switch ext {
	case "md", "markdown", "txt", "jpg", "jpeg", "png", "gif", "webp", "pdf":
		return true
	default:
		return false
	}
}

func attachmentRawContentType(filename string) string {
	switch strings.ToLower(filepath.Ext(filename)) {
	case ".md", ".markdown":
		return "text/markdown; charset=utf-8"
	case ".txt":
		return "text/plain; charset=utf-8"
	}
	if contentType := mime.TypeByExtension(filepath.Ext(filename)); contentType != "" {
		return contentType
	}
	return "application/octet-stream"
}

func safeAttachmentDownloadName(title, filename string) string {
	if cleaned := safeUploadFilename(title); cleaned != "" {
		return cleaned
	}
	return filepath.Base(filename)
}

func isSubpath(candidate, root string) bool {
	rel, err := filepath.Rel(filepath.Clean(root), filepath.Clean(candidate))
	if err != nil {
		return false
	}
	return rel == "." || (rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator)))
}

func containsAllTokens(text string, tokens []string) bool {
	for _, token := range tokens {
		if !strings.Contains(text, token) {
			return false
		}
	}
	return true
}

func sortedIntKeys(values map[int]bool) []int {
	out := []int{}
	for value := range values {
		out = append(out, value)
	}
	for i := 1; i < len(out); i++ {
		current := out[i]
		j := i - 1
		for j >= 0 && out[j] > current {
			out[j+1] = out[j]
			j--
		}
		out[j+1] = current
	}
	return out
}

func parseCSVInts(value string) []int {
	var out []int
	for _, part := range strings.Split(value, ",") {
		if parsed, err := strconv.Atoi(strings.TrimSpace(part)); err == nil {
			out = append(out, parsed)
		}
	}
	return out
}

type noteScanner interface {
	Scan(dest ...any) error
}

func (s *server) scanNoteRow(row noteScanner) (response, error) {
	var id, isPinned, isArchived, variantsCount int
	var title, content, categoryName, coverPosition, editorLayout, createdAt, updatedAt sql.NullString
	var remarks, coverImage, parentTitle sql.NullString
	var categoryID, parentID sql.NullInt64
	if err := row.Scan(&id, &title, &content, &categoryName, &remarks, &coverImage, &coverPosition, &editorLayout, &isPinned, &isArchived, &categoryID, &createdAt, &updatedAt, &parentID, &parentTitle, &variantsCount); err != nil {
		return nil, err
	}
	tags, err := s.noteTags(id)
	if err != nil {
		return nil, err
	}
	urls, err := s.noteURLs(id)
	if err != nil {
		return nil, err
	}
	note := response{
		"id": id, "title": nullableString(title), "content": nullableString(content),
		"type": nullableString(categoryName), "category_name": nullableString(categoryName),
		"remarks": nullableStringOrNil(remarks), "cover_image": nullableStringOrNil(coverImage),
		"cover_position": nullableString(coverPosition), "editor_layout": nullableString(editorLayout),
		"is_pinned": isPinned != 0, "is_archived": isArchived != 0,
		"category_id": nullableIntOrNil(categoryID), "created_at": nullableString(createdAt),
		"updated_at": nullableString(updatedAt), "tags": tags, "urls": urls,
		"parent_id": nullableIntOrNil(parentID), "parent_title": nullableStringOrNil(parentTitle),
		"variants_count": variantsCount,
	}
	return note, nil
}

func applyNoteListContentPreview(note response) {
	fullContent, _ := note["content"].(string)
	preview, truncated, contentLength := noteListContentPreview(fullContent)
	note["content"] = preview
	note["content_preview"] = preview
	note["content_truncated"] = truncated
	note["content_length"] = contentLength
	if firstImage := firstNoteContentImage(fullContent); firstImage != "" {
		note["content_first_image"] = firstImage
	}
}

func noteListContentPreview(content string) (string, bool, int) {
	runes := []rune(content)
	if len(runes) <= noteListContentPreviewLength {
		return content, false, len(runes)
	}
	return string(runes[:noteListContentPreviewLength]) + "...", true, len(runes)
}

func firstNoteContentImage(content string) string {
	refs := collectMarkdownImageRefs(content)
	if len(refs) == 0 {
		return ""
	}
	return refs[0]
}

func (s *server) noteTags(noteID int) ([]tagRef, error) {
	rows, err := s.db.Query(`
		SELECT t.id, t.name
		FROM Note_Tags nt JOIN Tags t ON nt.tag_id = t.id
		WHERE nt.note_id = ?
		ORDER BY t.id`, noteID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	tags := []tagRef{}
	for rows.Next() {
		var tag tagRef
		if err := rows.Scan(&tag.ID, &tag.Name); err != nil {
			return nil, err
		}
		tags = append(tags, tag)
	}
	return tags, nil
}

func (s *server) noteURLs(noteID int) ([]string, error) {
	rows, err := s.db.Query("SELECT url FROM Source_Urls WHERE note_id = ? ORDER BY id", noteID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	urls := []string{}
	for rows.Next() {
		var url string
		if err := rows.Scan(&url); err != nil {
			return nil, err
		}
		urls = append(urls, url)
	}
	return urls, nil
}
