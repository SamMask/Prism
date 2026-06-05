package main

import (
	"database/sql"
	"embed"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io/fs"
	"log"
	"math"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

const expectedSchemaVersion = 16
const maxAttachmentFileBytes int64 = 1048576
const maxAttachmentScanFiles = 200
const maxAttachmentScanBytes int64 = 5242880
const maxAttachmentScanDuration = 250 * time.Millisecond

//go:embed web/dist/*
var embeddedDist embed.FS

type server struct {
	db      *sql.DB
	runtime runtimeConfig
}

type runtimeConfig struct {
	addr            string
	dbPath          string
	dataDir         string
	enableTagWrite  bool
	sqliteQueryOnly bool
}

type response map[string]any

type tagRef struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

func main() {
	dbPath := flag.String("db", os.Getenv("PRISM_GO_DB"), "path to a copied Prism SQLite database")
	addr := flag.String("addr", envDefault("PRISM_GO_ADDR", "127.0.0.1:5001"), "listen address")
	dataDir := flag.String("data-dir", envDefault("PRISM_GO_DATA_DIR", "."), "external Prism user data directory")
	enableTagWrite := flag.Bool("enable-tag-write", envBool("PRISM_GO_ENABLE_TAG_WRITE"), "enable local/copied-DB PUT /api/tags/<id> parity candidate")
	flag.Parse()

	cfg, err := resolveRuntimeConfig(*addr, *dbPath, *dataDir, *enableTagWrite)
	if err != nil {
		log.Fatal(err)
	}

	db, err := openDB(cfg.dbPath, cfg.enableTagWrite)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()
	if err := verifySchemaVersion(db, expectedSchemaVersion); err != nil {
		log.Fatal(err)
	}

	srv := &server{db: db, runtime: cfg}
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", srv.handleHealth)
	mux.HandleFunc("/api/test", srv.handleTest)
	mux.HandleFunc("/api/categories", srv.handleCategories)
	mux.HandleFunc("/api/tags", srv.handleTags)
	mux.HandleFunc("/api/tags/", srv.handleTagDetail)
	mux.HandleFunc("/api/notes", srv.handleNotes)
	mux.HandleFunc("/api/notes/", srv.handleNoteDetail)
	mux.Handle("/", staticHandler())

	log.Printf("Prism Go runtime proof listening on %s", cfg.addr)
	if err := http.ListenAndServe(cfg.addr, logRequests(mux)); err != nil {
		log.Fatal(err)
	}
}

func envDefault(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func envBool(key string) bool {
	value := strings.TrimSpace(os.Getenv(key))
	return value == "1" || strings.EqualFold(value, "true")
}

func resolveRuntimeConfig(addr, dbPath, dataDir string, enableTagWrite bool) (runtimeConfig, error) {
	if strings.TrimSpace(dbPath) == "" {
		return runtimeConfig{}, errors.New("database path is required; pass --db or PRISM_GO_DB")
	}
	absDB, err := filepath.Abs(dbPath)
	if err != nil {
		return runtimeConfig{}, err
	}
	if filepath.Base(absDB) == "knowledge.db" && os.Getenv("PRISM_GO_ALLOW_PROD_DB") != "1" {
		return runtimeConfig{}, fmt.Errorf("refusing to open production-like database %s; use a copied *_test.db or *_dev.db", absDB)
	}
	if _, err := os.Stat(absDB); err != nil {
		return runtimeConfig{}, err
	}

	absData, err := filepath.Abs(dataDir)
	if err != nil {
		return runtimeConfig{}, err
	}
	if err := os.MkdirAll(absData, 0755); err != nil {
		return runtimeConfig{}, err
	}

	return runtimeConfig{
		addr:            addr,
		dbPath:          absDB,
		dataDir:         absData,
		enableTagWrite:  enableTagWrite,
		sqliteQueryOnly: !enableTagWrite,
	}, nil
}

func openDB(dbPath string, enableWrites bool) (*sql.DB, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, err
	}
	if enableWrites {
		return db, nil
	}
	if _, err := db.Exec("PRAGMA query_only = ON"); err != nil {
		db.Close()
		return nil, err
	}
	var queryOnly int
	if err := db.QueryRow("PRAGMA query_only").Scan(&queryOnly); err != nil {
		db.Close()
		return nil, err
	}
	if queryOnly != 1 {
		db.Close()
		return nil, errors.New("failed to enable SQLite query_only mode")
	}
	return db, nil
}

func verifySchemaVersion(db *sql.DB, expected int) error {
	current, err := schemaVersion(db)
	if err != nil {
		return err
	}
	if current < expected {
		return fmt.Errorf("database schema version %d is older than expected %d", current, expected)
	}
	return nil
}

func schemaVersion(db *sql.DB) (int, error) {
	var raw string
	if err := db.QueryRow("SELECT value FROM Schema_Meta WHERE key = 'schema_version'").Scan(&raw); err != nil {
		return 0, fmt.Errorf("schema version check failed: %w", err)
	}
	version, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("invalid schema_version %q: %w", raw, err)
	}
	return version, nil
}

func staticHandler() http.Handler {
	sub, err := fs.Sub(embeddedDist, "web/dist")
	if err != nil {
		return http.NotFoundHandler()
	}
	files := http.FS(sub)
	fileServer := http.FileServer(files)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" {
			serveIndex(w, r, files)
			return
		}
		cleanPath := strings.TrimPrefix(path.Clean(r.URL.Path), "/")
		if cleanPath == "." || cleanPath == "" {
			cleanPath = "index.html"
		}
		if file, err := files.Open(cleanPath); err == nil {
			_ = file.Close()
			fileServer.ServeHTTP(w, r)
			return
		}
		serveIndex(w, r, files)
	})
}

func serveIndex(w http.ResponseWriter, r *http.Request, files http.FileSystem) {
	index, err := files.Open("index.html")
	if err != nil {
		http.NotFound(w, r)
		return
	}
	defer index.Close()
	stat, err := index.Stat()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	http.ServeContent(w, r, "index.html", stat.ModTime(), index)
}

func requireGET(w http.ResponseWriter, r *http.Request) bool {
	if r.Method == http.MethodGet {
		return true
	}
	w.Header().Set("Allow", http.MethodGet)
	http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	return false
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, response{"status": "error", "message": message})
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(status int) {
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		recorder := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(recorder, r)
		log.Printf("request method=%s path=%s status=%d duration_ms=%d", r.Method, r.URL.RequestURI(), recorder.status, time.Since(started).Milliseconds())
	})
}

func (s *server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	version, err := schemaVersion(s.db)
	if err != nil {
		writeJSON(w, http.StatusServiceUnavailable, response{
			"status": "error", "message": err.Error(),
		})
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "ok",
		"runtime": response{
			"mode":                    "go-runtime-proof",
			"addr":                    s.runtime.addr,
			"data_dir":                s.runtime.dataDir,
			"db_path":                 s.runtime.dbPath,
			"schema_version":          version,
			"expected_schema_version": expectedSchemaVersion,
			"sqlite_query_only":       s.runtime.sqliteQueryOnly,
			"api_surface":             s.apiSurface(),
		},
	})
}

func (s *server) apiSurface() string {
	if s.runtime.enableTagWrite {
		return "get-read-only+local-tag-write"
	}
	return "get-read-only"
}

func boolString(r *http.Request, key string) bool {
	return strings.EqualFold(r.URL.Query().Get(key), "true")
}

func intQuery(r *http.Request, key string, fallback int) int {
	value, err := strconv.Atoi(r.URL.Query().Get(key))
	if err != nil {
		return fallback
	}
	return value
}

func (s *server) handleTest(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	counts := map[string]int{}
	for key, table := range map[string]string{
		"notes_count":      "Notes",
		"categories_count": "Categories",
		"tags_count":       "Tags",
	} {
		var count int
		if err := s.db.QueryRow("SELECT COUNT(*) FROM " + table).Scan(&count); err != nil {
			writeJSON(w, http.StatusOK, response{"status": "ok", "message": "Prism API is running!", "error": err.Error()})
			return
		}
		counts[key] = count
	}
	writeJSON(w, http.StatusOK, response{
		"status":  "ok",
		"message": "Prism API is running!",
		"stats":   counts,
	})
}

func (s *server) handleCategories(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	rows, err := s.db.Query(`
		SELECT c.id, c.name, c.icon, c.sort_order, c.is_default,
		       (SELECT COUNT(*) FROM Notes n WHERE n.category_id = c.id) AS count
		FROM Categories c
		ORDER BY c.sort_order ASC`)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	items := []response{}
	for rows.Next() {
		var id, sortOrder, isDefault, count int
		var name, icon string
		if err := rows.Scan(&id, &name, &icon, &sortOrder, &isDefault, &count); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		items = append(items, response{
			"id": id, "name": name, "icon": icon, "sort_order": sortOrder,
			"is_default": isDefault != 0, "count": count,
		})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": items})
}

func (s *server) handleTags(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	rows, err := s.db.Query(`
		SELECT t.id, t.name, COUNT(nt.note_id) AS count
		FROM Tags t
		LEFT JOIN Note_Tags nt ON t.id = nt.tag_id
		GROUP BY t.id
		ORDER BY t.name`)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	items := []response{}
	for rows.Next() {
		var id, count int
		var name string
		if err := rows.Scan(&id, &name, &count); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		items = append(items, response{"id": id, "name": name, "count": count})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": items})
}

func (s *server) handleTagDetail(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/api/tags/")
	tagID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if r.Method != http.MethodPut {
		w.Header().Set("Allow", http.MethodPut)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableTagWrite {
		writeError(w, http.StatusMethodNotAllowed, "Tag write route is disabled")
		return
	}
	s.renameTag(w, r, tagID)
}

func (s *server) renameTag(w http.ResponseWriter, r *http.Request, tagID int) {
	var payload map[string]any
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, "Tag name is required")
		return
	}
	rawName, ok := payload["name"].(string)
	if !ok || rawName == "" {
		writeError(w, http.StatusBadRequest, "Tag name is required")
		return
	}
	newName := strings.TrimSpace(rawName)
	if newName == "" {
		writeError(w, http.StatusBadRequest, "Tag name cannot be empty")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var existingID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE id = ?", tagID).Scan(&existingID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Tag not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	var duplicateID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE name = ? AND id != ?", newName, tagID).Scan(&duplicateID); err == nil {
		writeError(w, http.StatusConflict, "Tag name already exists")
		return
	} else if !errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	result, err := tx.Exec("UPDATE Tags SET name = ? WHERE id = ?", newName, tagID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	affected, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if affected != 1 {
		writeError(w, http.StatusNotFound, "Tag not found")
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func (s *server) handleNotes(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	if r.URL.Path != "/api/notes" {
		http.NotFound(w, r)
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

	where, args := s.buildNotesWhere(r)
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
		       n.category_id, n.created_at, n.updated_at
		FROM Notes n
		LEFT JOIN Categories c ON n.category_id = c.id
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
		items = append(items, note)
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data":   items,
		"pagination": response{
			"page": page, "per_page": perPage, "total": total,
			"total_pages": int(math.Ceil(float64(total) / float64(perPage))),
		},
	})
}

func (s *server) buildNotesWhere(r *http.Request) (string, []any) {
	clauses := []string{"1 = 1"}
	args := []any{}
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
	if noteType := r.URL.Query().Get("type"); noteType != "" && !strings.EqualFold(noteType, "all") {
		clauses = append(clauses, "c.name = ?")
		args = append(args, noteType)
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
		if len(q) > 200 {
			q = q[:200]
		}
		attachmentNoteIDs := s.attachmentContentNoteIDs(q)
		like := "%" + q + "%"
		searchClause := `(n.title LIKE ? OR n.content LIKE ? OR n.remarks LIKE ? OR n.id IN (
			SELECT nt.note_id FROM Note_Tags nt JOIN Tags t ON nt.tag_id = t.id WHERE t.name LIKE ?
		) OR n.id IN (
			SELECT a.note_id FROM Note_Attachments a
			WHERE a.title LIKE ? OR a.file_path LIKE ?
		)`
		if len(attachmentNoteIDs) > 0 {
			searchClause += " OR n.id IN (" + placeholders(len(attachmentNoteIDs)) + ")"
		}
		searchClause += ")"
		clauses = append(clauses, searchClause)
		args = append(args, like, like, like, like, like, like)
		for _, noteID := range attachmentNoteIDs {
			args = append(args, noteID)
		}
	}
	return "WHERE " + strings.Join(clauses, " AND "), args
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
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r > 127 {
			builder.WriteRune(r)
		} else {
			builder.WriteRune(' ')
		}
	}
	parts := strings.Fields(builder.String())
	if len(parts) > 10 {
		return parts[:10]
	}
	return parts
}

func (s *server) attachmentContentNoteIDs(keyword string) []int {
	tokens := searchTokens(keyword)
	if len(tokens) == 0 {
		return nil
	}
	rows, err := s.db.Query(`
		SELECT note_id, file_path, file_type
		FROM Note_Attachments
		WHERE LOWER(COALESCE(file_type, '')) IN ('md', 'markdown', 'txt')`)
	if err != nil {
		return nil
	}
	defer rows.Close()

	deadline := time.Now().Add(maxAttachmentScanDuration)
	filesRead := 0
	var totalBytes int64
	noteIDs := map[int]bool{}
	for rows.Next() {
		if filesRead >= maxAttachmentScanFiles || totalBytes >= maxAttachmentScanBytes || time.Now().After(deadline) {
			break
		}
		var noteID int
		var filePath, fileType sql.NullString
		if err := rows.Scan(&noteID, &filePath, &fileType); err != nil {
			return sortedIntKeys(noteIDs)
		}
		resolved, size, ok := resolveAttachmentFile(s.runtime.dataDir, nullableString(filePath), nullableString(fileType))
		if !ok {
			continue
		}
		if totalBytes+size > maxAttachmentScanBytes {
			break
		}
		content, err := os.ReadFile(resolved)
		filesRead++
		totalBytes += size
		if err != nil {
			continue
		}
		text := strings.ToLower(strings.TrimPrefix(string(content), "\ufeff"))
		if containsAllTokens(text, tokens) {
			noteIDs[noteID] = true
		}
	}
	return sortedIntKeys(noteIDs)
}

func resolveAttachmentFile(dataDir, relativePath, fileType string) (string, int64, bool) {
	if !isAllowedAttachmentPath(relativePath, fileType) {
		return "", 0, false
	}
	root, err := filepath.Abs(dataDir)
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
	if err != nil || filepath.Clean(resolved) != filepath.Clean(absCandidate) || !isSubpath(resolved, root) {
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
	if cleaned == "." || strings.HasPrefix(cleaned, "../") || cleaned == ".." || !strings.HasPrefix(cleaned, "docs/attachments/") {
		return false
	}
	ext := strings.TrimPrefix(strings.ToLower(path.Ext(cleaned)), ".")
	return ext == fileType && (ext == "md" || ext == "markdown" || ext == "txt")
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
	var id, isPinned, isArchived int
	var title, content, categoryName, coverPosition, editorLayout, createdAt, updatedAt sql.NullString
	var remarks, coverImage sql.NullString
	var categoryID sql.NullInt64
	if err := row.Scan(&id, &title, &content, &categoryName, &remarks, &coverImage, &coverPosition, &editorLayout, &isPinned, &isArchived, &categoryID, &createdAt, &updatedAt); err != nil {
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
	}
	return note, nil
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

func (s *server) handleNoteDetail(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	idText := strings.TrimPrefix(r.URL.Path, "/api/notes/")
	noteID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	row := s.db.QueryRow(`
		SELECT n.id, n.title, n.content, COALESCE(c.name, 'Uncategorized') AS category_name,
		       n.remarks, n.cover_image, COALESCE(n.cover_position, 'top') AS cover_position,
		       COALESCE(n.editor_layout, 'single') AS editor_layout,
		       COALESCE(n.is_pinned, 0) AS is_pinned, COALESCE(n.is_archived, 0) AS is_archived,
		       n.category_id, n.created_at, n.updated_at, n.prompt_params, n.parent_id, p.title AS parent_title
		FROM Notes n
		LEFT JOIN Categories c ON n.category_id = c.id
		LEFT JOIN Notes p ON n.parent_id = p.id
		WHERE n.id = ?`, noteID)

	var id, isPinned, isArchived int
	var title, content, categoryName, coverPosition, editorLayout, createdAt, updatedAt sql.NullString
	var remarks, coverImage, promptParams, parentTitle sql.NullString
	var categoryID, parentID sql.NullInt64
	if err := row.Scan(&id, &title, &content, &categoryName, &remarks, &coverImage, &coverPosition, &editorLayout, &isPinned, &isArchived, &categoryID, &createdAt, &updatedAt, &promptParams, &parentID, &parentTitle); err != nil {
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
	}})
}

func nullableString(value sql.NullString) string {
	if !value.Valid {
		return ""
	}
	return value.String
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
