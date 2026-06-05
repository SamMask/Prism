package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"image"
	"image/color"
	"image/png"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

func createSpikeDB(t *testing.T) string {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "prism_runtime_test.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	_, err = db.Exec(`
		CREATE TABLE Schema_Meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
		INSERT INTO Schema_Meta (key, value) VALUES ('schema_version', '16');
		CREATE TABLE Notes (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT,
			content TEXT,
			remarks TEXT,
			cover_image TEXT,
			cover_position TEXT DEFAULT 'top',
			editor_layout TEXT DEFAULT 'single',
			is_pinned INTEGER DEFAULT 0,
			is_archived INTEGER DEFAULT 0,
			category_id INTEGER,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		CREATE TABLE Categories (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT UNIQUE NOT NULL,
			icon TEXT DEFAULT 'note',
			sort_order INTEGER DEFAULT 0,
			is_default INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		CREATE TABLE Tags (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT UNIQUE NOT NULL COLLATE NOCASE
		);
		CREATE TABLE Note_Tags (
			note_id INTEGER,
			tag_id INTEGER,
			PRIMARY KEY (note_id, tag_id)
		);
		CREATE TABLE Note_Attachments (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			note_id INTEGER NOT NULL,
			file_path TEXT NOT NULL,
			file_type TEXT,
			title TEXT,
			size_bytes INTEGER,
			is_auto_extracted INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		CREATE VIRTUAL TABLE Notes_FTS USING fts5(
			title, content,
			content='Notes',
			content_rowid='id'
		);
		INSERT INTO Categories (name, is_default) VALUES ('note', 1);
		INSERT INTO Notes (title, content, category_id) VALUES ('Welcome Note', 'Welcome to Prism', 1);
		INSERT INTO Notes_FTS(rowid, title, content) VALUES (1, 'Welcome Note', 'Welcome to Prism');
	`)
	if err != nil {
		t.Fatal(err)
	}
	return dbPath
}

func TestRuntimeConfigUsesExternalDataDirAndExplicitDB(t *testing.T) {
	dbPath := createSpikeDB(t)
	dataDir := filepath.Join(t.TempDir(), "data")

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.dbPath != dbPath {
		t.Fatalf("db path mismatch: %s", cfg.dbPath)
	}
	if cfg.dataDir != dataDir {
		t.Fatalf("data dir mismatch: %s", cfg.dataDir)
	}
	if cfg.enableTagWrite {
		t.Fatal("tag write should be disabled by default")
	}
	if cfg.enableCategoryWrite {
		t.Fatal("category write should be disabled by default")
	}
	if cfg.enableAttachmentTextRead {
		t.Fatal("attachment text read should be disabled by default")
	}
	if cfg.enableThumbnailWrite {
		t.Fatal("thumbnail write should be disabled by default")
	}
	if !cfg.sqliteQueryOnly {
		t.Fatal("default runtime must keep SQLite query_only enabled")
	}
	if _, err := os.Stat(dataDir); err != nil {
		t.Fatalf("data dir was not created: %v", err)
	}
}

func TestRuntimeRefusesProductionNamedDB(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "knowledge.db")
	if err := os.WriteFile(dbPath, []byte("not a real db"), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PRISM_GO_ALLOW_PROD_DB", "")

	_, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false)
	if err == nil {
		t.Fatal("expected production-like database refusal")
	}
}

func TestPureGoSQLiteDriverSupportsSchemaFTSAndQueryOnly(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	if err := verifySchemaVersion(db, 16); err != nil {
		t.Fatal(err)
	}

	var hits int
	if err := db.QueryRow("SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", "Welcome").Scan(&hits); err != nil {
		t.Fatalf("FTS5 query failed: %v", err)
	}
	if hits != 1 {
		t.Fatalf("expected one FTS hit, got %d", hits)
	}

	_, err = db.Exec("INSERT INTO Notes (title, content) VALUES ('blocked', 'query only')")
	if err == nil {
		t.Fatal("expected query_only mode to block writes")
	}
}

func TestTagWriteModeUsesWritableCopiedDBOnlyWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), true, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.enableTagWrite {
		t.Fatal("tag write should be enabled by explicit flag")
	}
	if cfg.sqliteQueryOnly {
		t.Fatal("tag write mode must report SQLite query_only disabled")
	}

	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	if _, err := db.Exec("INSERT INTO Tags (name) VALUES ('writable')"); err != nil {
		t.Fatalf("expected explicit tag write mode to allow copied-DB writes: %v", err)
	}
}

func TestCategoryWriteModeUsesWritableCopiedDBOnlyWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, true, false, false)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.enableCategoryWrite {
		t.Fatal("category write should be enabled by explicit flag")
	}
	if cfg.sqliteQueryOnly {
		t.Fatal("category write mode must report SQLite query_only disabled")
	}

	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	if _, err := db.Exec("UPDATE Categories SET name = ? WHERE id = 1", "renamed"); err != nil {
		t.Fatalf("expected explicit category write mode to allow copied-DB writes: %v", err)
	}
}

func TestAttachmentTextReadKeepsQueryOnlyWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	dataDir := t.TempDir()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false, false, true, false)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.enableAttachmentTextRead {
		t.Fatal("attachment text read should be enabled by explicit flag")
	}
	if !cfg.sqliteQueryOnly {
		t.Fatal("attachment text read must keep SQLite query_only enabled")
	}

	attachmentDir := filepath.Join(dataDir, "docs", "attachments")
	if err := os.MkdirAll(attachmentDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(attachmentDir, "fixture.md"), []byte("hello attachment"), 0644); err != nil {
		t.Fatal(err)
	}

	writableDB, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := writableDB.Exec("INSERT INTO Note_Attachments (note_id, file_path, file_type, title) VALUES (1, 'docs/attachments/fixture.md', 'md', 'Fixture')"); err != nil {
		t.Fatal(err)
	}
	writableDB.Close()

	readDB, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer readDB.Close()

	srv := &server{db: readDB, runtime: cfg}
	request := httptest.NewRequest(http.MethodGet, "/api/attachments/1", nil)
	recorder := httptest.NewRecorder()
	srv.handleAttachmentDetail(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected attachment text read to return 200, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatalf("expected JSON response: %v", err)
	}
	data := payload["data"].(map[string]any)
	if data["content"] != "hello attachment" {
		t.Fatalf("unexpected content: %#v", data)
	}

	_, err = readDB.Exec("INSERT INTO Notes (title, content) VALUES ('blocked', 'query only')")
	if err == nil {
		t.Fatal("attachment text read mode must keep DB writes blocked")
	}
}

func TestAttachmentTextReadRejectsWhenFlagDisabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	srv := &server{db: db, runtime: runtimeConfig{sqliteQueryOnly: true}}
	request := httptest.NewRequest(http.MethodGet, "/api/attachments/1", nil)
	recorder := httptest.NewRecorder()
	srv.handleAttachmentDetail(recorder, request)

	if recorder.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected disabled attachment text read to return 405, got %d", recorder.Code)
	}
	if !strings.Contains(recorder.Body.String(), "Attachment text read route is disabled") {
		t.Fatalf("unexpected disabled response: %s", recorder.Body.String())
	}
}

func TestCategoryWriteHandlerRejectsWhenFlagDisabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	srv := &server{db: db, runtime: runtimeConfig{sqliteQueryOnly: true}}
	request := httptest.NewRequest(http.MethodPut, "/api/categories/1", strings.NewReader(`{"name":"blocked"}`))
	recorder := httptest.NewRecorder()
	srv.handleCategoryDetail(recorder, request)

	if recorder.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected disabled category write to return 405, got %d", recorder.Code)
	}
	var payload map[string]string
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatalf("expected JSON error response: %v", err)
	}
	if payload["message"] != "Category write route is disabled" {
		t.Fatalf("unexpected disabled message: %#v", payload)
	}
	var name string
	if err := db.QueryRow("SELECT name FROM Categories WHERE id = 1").Scan(&name); err != nil {
		t.Fatal(err)
	}
	if name != "note" {
		t.Fatalf("disabled handler changed category name: %q", name)
	}
}

func TestThumbnailWriteKeepsDBQueryOnlyAndUpdatesSurfaceWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.enableThumbnailWrite {
		t.Fatal("thumbnail write should be enabled by explicit flag")
	}
	if !cfg.sqliteQueryOnly {
		t.Fatal("thumbnail file writes must keep SQLite query_only enabled")
	}
	srv := &server{runtime: cfg}
	if got := srv.apiSurface(); got != "get-read-only+local-thumbnail-write" {
		t.Fatalf("unexpected api surface: %s", got)
	}
}

func TestThumbnailWriteRefusesProductionUploadsUnlessExplicitlyAllowed(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "knowledge.db")
	if err := os.WriteFile(dbPath, []byte("not a real db"), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PRISM_GO_ALLOW_PROD_DB", "1")
	t.Setenv("PRISM_GO_ALLOW_PROD_UPLOADS", "")

	_, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, true)
	if err == nil {
		t.Fatal("expected thumbnail production upload refusal")
	}
}

func TestThumbnailUploadRejectsWhenFlagDisabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	dataDir := t.TempDir()
	srv := &server{db: db, runtime: runtimeConfig{dataDir: dataDir, sqliteQueryOnly: true}}
	body, contentType := multipartUploadBody(t, "fixture.png", fixturePNG(t, 600, 240), "false")
	request := httptest.NewRequest(http.MethodPost, "/api/upload", body)
	request.Header.Set("Content-Type", contentType)
	recorder := httptest.NewRecorder()

	srv.handleUpload(recorder, request)

	if recorder.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected disabled upload to return 405, got %d", recorder.Code)
	}
	if entries, err := os.ReadDir(filepath.Join(dataDir, "static", "uploads")); err == nil && len(entries) != 0 {
		t.Fatalf("disabled upload wrote files: %v", entries)
	}
}

func TestThumbnailOnlyUploadWritesWebPThumbWithoutOriginal(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	srv := &server{db: db, runtime: cfg}
	body, contentType := multipartUploadBody(t, "fixture.png", fixturePNG(t, 800, 320), "true")
	request := httptest.NewRequest(http.MethodPost, "/api/upload", body)
	request.Header.Set("Content-Type", contentType)
	recorder := httptest.NewRecorder()

	srv.handleUpload(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected thumbnail-only upload to return 200, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	data := uploadResponseData(t, recorder.Body.Bytes())
	filename := data["filename"].(string)
	if !strings.HasSuffix(filename, "_thumb.webp") {
		t.Fatalf("expected thumbnail filename, got %q", filename)
	}
	uploadsDir := filepath.Join(cfg.dataDir, "static", "uploads")
	if _, err := os.Stat(filepath.Join(uploadsDir, filename)); err != nil {
		t.Fatalf("expected thumbnail file: %v", err)
	}
	if originals := globNonThumbs(t, uploadsDir); len(originals) != 0 {
		t.Fatalf("thumbnail-only upload wrote originals: %v", originals)
	}
	assertWebPWidth(t, filepath.Join(uploadsDir, filename), 500)
}

func TestStandardThumbnailUploadWritesOriginalAndThumb(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	srv := &server{db: db, runtime: cfg}
	body, contentType := multipartUploadBody(t, "fixture.png", fixturePNG(t, 640, 480), "false")
	request := httptest.NewRequest(http.MethodPost, "/api/upload", body)
	request.Header.Set("Content-Type", contentType)
	recorder := httptest.NewRecorder()

	srv.handleUpload(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected standard upload to return 200, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	data := uploadResponseData(t, recorder.Body.Bytes())
	filename := data["filename"].(string)
	if strings.HasSuffix(filename, "_thumb.webp") {
		t.Fatalf("standard upload should return original filename, got %q", filename)
	}
	uploadsDir := filepath.Join(cfg.dataDir, "static", "uploads")
	thumb := strings.TrimSuffix(filename, filepath.Ext(filename)) + "_thumb.webp"
	if _, err := os.Stat(filepath.Join(uploadsDir, filename)); err != nil {
		t.Fatalf("expected original file: %v", err)
	}
	if _, err := os.Stat(filepath.Join(uploadsDir, thumb)); err != nil {
		t.Fatalf("expected thumbnail file: %v", err)
	}
	assertWebPWidth(t, filepath.Join(uploadsDir, thumb), 500)
}

func TestThumbnailUploadRejectsInvalidContentWithoutWritingFiles(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	srv := &server{db: db, runtime: cfg}
	body, contentType := multipartUploadBody(t, "fixture.png", []byte("not an image"), "false")
	request := httptest.NewRequest(http.MethodPost, "/api/upload", body)
	request.Header.Set("Content-Type", contentType)
	recorder := httptest.NewRecorder()

	srv.handleUpload(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("expected invalid upload to return 400, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	if entries, err := os.ReadDir(filepath.Join(cfg.dataDir, "static", "uploads")); err == nil && len(entries) != 0 {
		t.Fatalf("invalid upload wrote files: %v", entries)
	}
}

func multipartUploadBody(t *testing.T, filename string, content []byte, thumbnailOnly string) (io.Reader, string) {
	t.Helper()
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := part.Write(content); err != nil {
		t.Fatal(err)
	}
	if err := writer.WriteField("thumbnail_only", thumbnailOnly); err != nil {
		t.Fatal(err)
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	return body, writer.FormDataContentType()
}

func fixturePNG(t *testing.T, width, height int) []byte {
	t.Helper()
	img := image.NewRGBA(image.Rect(0, 0, width, height))
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			img.Set(x, y, color.RGBA{R: uint8(x % 255), G: uint8(y % 255), B: 120, A: 255})
		}
	}
	var out bytes.Buffer
	if err := png.Encode(&out, img); err != nil {
		t.Fatal(err)
	}
	return out.Bytes()
}

func uploadResponseData(t *testing.T, body []byte) map[string]any {
	t.Helper()
	var payload map[string]any
	if err := json.Unmarshal(body, &payload); err != nil {
		t.Fatalf("expected JSON response: %v", err)
	}
	data, ok := payload["data"].(map[string]any)
	if !ok {
		t.Fatalf("missing response data: %#v", payload)
	}
	return data
}

func globNonThumbs(t *testing.T, uploadsDir string) []string {
	t.Helper()
	entries, err := os.ReadDir(uploadsDir)
	if err != nil {
		return nil
	}
	var originals []string
	for _, entry := range entries {
		if !strings.HasSuffix(entry.Name(), "_thumb.webp") {
			originals = append(originals, entry.Name())
		}
	}
	return originals
}

func assertWebPWidth(t *testing.T, path string, width int) {
	t.Helper()
	file, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	cfg, _, err := image.DecodeConfig(file)
	if err != nil {
		t.Fatalf("expected decodable WebP: %v", err)
	}
	if cfg.Width != width {
		t.Fatalf("expected thumbnail width %d, got %d", width, cfg.Width)
	}
}
