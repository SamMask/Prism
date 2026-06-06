package main

import (
	"bytes"
	"context"
	"crypto/md5"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"image"
	"image/color"
	"image/png"
	"io"
	"mime/multipart"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

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
			sort_order INTEGER DEFAULT 0,
			category_id INTEGER,
			prompt_params TEXT,
			parent_id INTEGER,
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
		CREATE TABLE Source_Urls (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			note_id INTEGER,
			url TEXT
		);
		CREATE TABLE Note_History (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			note_id INTEGER,
			content TEXT,
			diff_summary TEXT,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false, false, false, false, false, false)
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
	if cfg.enableNotesWrite {
		t.Fatal("notes write should be disabled by default")
	}
	if cfg.enableAttachmentTextRead {
		t.Fatal("attachment text read should be disabled by default")
	}
	if cfg.enableThumbnailWrite {
		t.Fatal("thumbnail write should be disabled by default")
	}
	if cfg.enableUploadURLWrite {
		t.Fatal("upload-url write should be disabled by default")
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

	_, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, false)
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
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), true, false, false, false, false, false)
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
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, true, false, false, false, false)
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

func TestNotesWriteModeUsesWritableCopiedDBOnlyWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, true, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.enableNotesWrite {
		t.Fatal("notes write should be enabled by explicit flag")
	}
	if cfg.sqliteQueryOnly {
		t.Fatal("notes write mode must report SQLite query_only disabled")
	}
	srv := &server{runtime: cfg}
	if got := srv.apiSurface(); got != "get-read-only+local-notes-write" {
		t.Fatalf("unexpected api surface: %s", got)
	}

	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if _, err := db.Exec("INSERT INTO Notes (title, content) VALUES ('writable', 'copied db')"); err != nil {
		t.Fatalf("expected explicit notes write mode to allow copied-DB writes: %v", err)
	}
}

func TestAttachmentTextReadKeepsQueryOnlyWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	dataDir := t.TempDir()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false, false, false, true, false, false)
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

func TestNotesWriteHandlerRejectsWhenFlagDisabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	srv := &server{db: db, runtime: runtimeConfig{sqliteQueryOnly: true}}
	request := httptest.NewRequest(http.MethodPost, "/api/notes", strings.NewReader(`{"title":"blocked","content":"blocked"}`))
	recorder := httptest.NewRecorder()
	srv.handleNotes(recorder, request)

	if recorder.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected disabled notes write to return 405, got %d", recorder.Code)
	}
	if !strings.Contains(recorder.Body.String(), "Notes write route is disabled") {
		t.Fatalf("unexpected disabled response: %s", recorder.Body.String())
	}
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM Notes WHERE title = 'blocked'").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Fatalf("disabled handler wrote notes: %d", count)
	}
}

func TestNotesRestoreHandlerReturnsJSONWhenEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if _, err := db.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (1, 'previous content', 'seed')"); err != nil {
		t.Fatal(err)
	}

	srv := &server{db: db, runtime: runtimeConfig{enableNotesWrite: true}}
	request := httptest.NewRequest(http.MethodPost, "/api/notes/1/restore/1", strings.NewReader(`{}`))
	recorder := httptest.NewRecorder()
	srv.handleNoteDetail(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected restore to return 200, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatalf("expected JSON response: %v", err)
	}
	if payload["message"] != "Note restored successfully" {
		t.Fatalf("unexpected restore response: %#v", payload)
	}
}

func TestThumbnailWriteKeepsDBQueryOnlyAndUpdatesSurfaceWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, true, false)
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

	_, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, true, false)
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

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, true, false)
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

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, true, false)
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

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, true, false)
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

func TestUploadURLWriteKeepsDBQueryOnlyAndUpdatesSurfaceWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.enableUploadURLWrite {
		t.Fatal("upload-url write should be enabled by explicit flag")
	}
	if !cfg.sqliteQueryOnly {
		t.Fatal("upload-url file writes must keep SQLite query_only enabled")
	}
	srv := &server{runtime: cfg}
	if got := srv.apiSurface(); got != "get-read-only+local-upload-url-write" {
		t.Fatalf("unexpected api surface: %s", got)
	}

	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if _, err := db.Exec("INSERT INTO Notes (title, content) VALUES ('blocked', 'query only')"); err == nil {
		t.Fatal("upload-url mode must keep DB writes blocked")
	}
}

func TestUploadURLWriteRefusesProductionUploadsUnlessExplicitlyAllowed(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "knowledge.db")
	if err := os.WriteFile(dbPath, []byte("not a real db"), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PRISM_GO_ALLOW_PROD_DB", "1")
	t.Setenv("PRISM_GO_ALLOW_PROD_UPLOADS", "")

	_, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
	if err == nil {
		t.Fatal("expected upload-url production upload refusal")
	}
}

func TestUploadURLRejectsWhenFlagDisabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	dataDir := t.TempDir()
	srv := &server{db: db, runtime: runtimeConfig{dataDir: dataDir, sqliteQueryOnly: true}}
	request := httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody("https://example.test/image.png", false))
	recorder := httptest.NewRecorder()

	srv.handleUploadURL(recorder, request)

	if recorder.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected disabled upload-url to return 405, got %d", recorder.Code)
	}
	assertUploadsEmpty(t, dataDir)
}

func TestUploadURLRejectsInvalidTargetsWithoutWritingFiles(t *testing.T) {
	tests := []struct {
		name     string
		imageURL string
		resolver func(context.Context, string) ([]net.IP, error)
	}{
		{
			name:     "empty URL",
			imageURL: "",
			resolver: publicUploadURLResolver,
		},
		{
			name:     "bad scheme",
			imageURL: "file:///tmp/image.png",
			resolver: publicUploadURLResolver,
		},
		{
			name:     "numeric loopback",
			imageURL: "http://127.0.0.1/image.png",
			resolver: publicUploadURLResolver,
		},
		{
			name:     "DNS private",
			imageURL: "https://private.example.test/image.png",
			resolver: func(context.Context, string) ([]net.IP, error) {
				return []net.IP{net.ParseIP("10.0.0.5")}, nil
			},
		},
		{
			name:     "unresolvable",
			imageURL: "https://missing.example.test/image.png",
			resolver: func(context.Context, string) ([]net.IP, error) {
				return nil, errors.New("no such host")
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dbPath := createSpikeDB(t)
			db, err := openDB(dbPath, false)
			if err != nil {
				t.Fatal(err)
			}
			defer db.Close()
			cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
			if err != nil {
				t.Fatal(err)
			}
			withUploadURLHooks(t, tt.resolver, fakeUploadURLTransport(t, fixturePNG(t, 32, 32), "image/png", nil))
			srv := &server{db: db, runtime: cfg}
			request := httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody(tt.imageURL, false))
			recorder := httptest.NewRecorder()

			srv.handleUploadURL(recorder, request)

			if recorder.Code != http.StatusBadRequest {
				t.Fatalf("expected invalid target to return 400, got %d body=%s", recorder.Code, recorder.Body.String())
			}
			assertUploadsEmpty(t, cfg.dataDir)
		})
	}
}

func TestUploadURLRejectsRedirectToPrivateHostWithoutWritingFiles(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	resolver := func(_ context.Context, host string) ([]net.IP, error) {
		if host == "example.test" {
			return []net.IP{net.ParseIP("93.184.216.34")}, nil
		}
		return []net.IP{net.ParseIP("127.0.0.1")}, nil
	}
	transport := roundTripFunc(func(req *http.Request) (*http.Response, error) {
		return &http.Response{
			StatusCode: http.StatusFound,
			Header:     http.Header{"Location": []string{"http://127.0.0.1/private.png"}, "Content-Type": []string{"text/plain"}},
			Body:       io.NopCloser(strings.NewReader("redirect")),
			Request:    req,
		}, nil
	})
	withUploadURLHooks(t, resolver, transport)

	srv := &server{db: db, runtime: cfg}
	request := httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody("https://example.test/remote.png", false))
	recorder := httptest.NewRecorder()

	srv.handleUploadURL(recorder, request)

	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("expected private redirect to return 400, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	assertUploadsEmpty(t, cfg.dataDir)
}

func TestUploadURLRejectsInvalidRemoteContentWithoutWritingFiles(t *testing.T) {
	tests := []struct {
		name        string
		content     []byte
		contentType string
	}{
		{name: "non-image content type", content: []byte("hello"), contentType: "text/plain"},
		{name: "oversized image", content: append(fixturePNG(t, 32, 32), bytes.Repeat([]byte{0}, int(maxUploadFileBytes))...), contentType: "image/png"},
		{name: "magic mismatch", content: []byte("not an image"), contentType: "image/png"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dbPath := createSpikeDB(t)
			db, err := openDB(dbPath, false)
			if err != nil {
				t.Fatal(err)
			}
			defer db.Close()
			cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
			if err != nil {
				t.Fatal(err)
			}
			withUploadURLHooks(t, publicUploadURLResolver, fakeUploadURLTransport(t, tt.content, tt.contentType, nil))
			srv := &server{db: db, runtime: cfg}
			request := httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody("https://example.test/remote.png", false))
			recorder := httptest.NewRecorder()

			srv.handleUploadURL(recorder, request)

			if recorder.Code != http.StatusBadRequest {
				t.Fatalf("expected invalid content to return 400, got %d body=%s", recorder.Code, recorder.Body.String())
			}
			assertUploadsEmpty(t, cfg.dataDir)
		})
	}
}

func TestUploadURLStandardWritesOriginalAndThumbWithExpectedHeaders(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	var gotUserAgent, gotReferer string
	transport := fakeUploadURLTransport(t, fixturePNG(t, 640, 480), "image/png", func(req *http.Request) {
		gotUserAgent = req.Header.Get("User-Agent")
		gotReferer = req.Header.Get("Referer")
	})
	withUploadURLHooks(t, publicUploadURLResolver, transport)
	srv := &server{db: db, runtime: cfg}
	request := httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody("https://example.test/weird%20name.png", false))
	recorder := httptest.NewRecorder()

	srv.handleUploadURL(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected upload-url success, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	data := uploadResponseData(t, recorder.Body.Bytes())
	filename := data["filename"].(string)
	if !strings.HasSuffix(filename, "_name.png") {
		t.Fatalf("expected sanitized URL basename, got %q", filename)
	}
	if data["original_url"] != "https://example.test/weird%20name.png" {
		t.Fatalf("unexpected original_url: %#v", data)
	}
	if data["thumbnail_only"] != false {
		t.Fatalf("unexpected thumbnail_only: %#v", data)
	}
	if !strings.Contains(gotUserAgent, "Mozilla/5.0") || gotReferer != "https://example.test/" {
		t.Fatalf("unexpected download headers user_agent=%q referer=%q", gotUserAgent, gotReferer)
	}
	uploadsDir := filepath.Join(cfg.dataDir, "static", "uploads")
	if _, err := os.Stat(filepath.Join(uploadsDir, filename)); err != nil {
		t.Fatalf("expected original file: %v", err)
	}
	thumb := strings.TrimSuffix(filename, filepath.Ext(filename)) + "_thumb.webp"
	if _, err := os.Stat(filepath.Join(uploadsDir, thumb)); err != nil {
		t.Fatalf("expected thumbnail file: %v", err)
	}
	assertWebPWidth(t, filepath.Join(uploadsDir, thumb), 500)
}

func TestUploadURLThumbnailOnlyWritesWebPThumbWithoutOriginal(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	withUploadURLHooks(t, publicUploadURLResolver, fakeUploadURLTransport(t, fixturePNG(t, 800, 320), "image/png", nil))
	srv := &server{db: db, runtime: cfg}
	request := httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody("https://example.test/remote.png", true))
	recorder := httptest.NewRecorder()

	srv.handleUploadURL(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected thumbnail-only upload-url success, got %d body=%s", recorder.Code, recorder.Body.String())
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
		t.Fatalf("thumbnail-only upload-url wrote originals: %v", originals)
	}
	assertWebPWidth(t, filepath.Join(uploadsDir, filename), 500)
}

func TestUploadURLThumbnailFailureKeepsOriginalForThumbnailOnly(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	withUploadURLHooks(t, publicUploadURLResolver, fakeUploadURLTransport(t, fixturePNG(t, 32, 32), "image/png", nil))
	originalEncoder := encodeUploadThumbnail
	encodeUploadThumbnail = func(image.Image) ([]byte, error) {
		return nil, errors.New("thumbnail unavailable")
	}
	t.Cleanup(func() { encodeUploadThumbnail = originalEncoder })

	srv := &server{db: db, runtime: cfg}
	request := httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody("https://example.test/fallback.png", true))
	recorder := httptest.NewRecorder()

	srv.handleUploadURL(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected thumbnail failure fallback success, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	data := uploadResponseData(t, recorder.Body.Bytes())
	if data["filename"] != nil {
		t.Fatalf("expected nil filename on thumbnail-only fallback, got %#v", data["filename"])
	}
	if data["thumbnail_only"] != true {
		t.Fatalf("unexpected thumbnail_only: %#v", data)
	}
	uploadsDir := filepath.Join(cfg.dataDir, "static", "uploads")
	url := data["url"].(string)
	if strings.HasSuffix(url, "_thumb.webp") {
		t.Fatalf("fallback should return original URL, got %q", url)
	}
	originalName := strings.TrimPrefix(url, "/static/uploads/")
	if _, err := os.Stat(filepath.Join(uploadsDir, originalName)); err != nil {
		t.Fatalf("expected fallback original file: %v", err)
	}
	if thumbs, err := filepath.Glob(filepath.Join(uploadsDir, "*_thumb.webp")); err == nil && len(thumbs) != 0 {
		t.Fatalf("fallback wrote thumbnail files: %v", thumbs)
	}
}

func TestUploadURLHashFallbackFilenameIsDeterministic(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	originalNow := uploadNow
	uploadNow = func() time.Time {
		return time.Date(2026, 6, 6, 12, 0, 0, 0, time.UTC)
	}
	t.Cleanup(func() { uploadNow = originalNow })
	withUploadURLHooks(t, publicUploadURLResolver, fakeUploadURLTransport(t, fixturePNG(t, 32, 32), "image/png", nil))

	imageURL := "https://example.test/no-extension"
	sum := md5.Sum([]byte(imageURL))
	expectedName := "20260606_120000_remote_" + hex.EncodeToString(sum[:])[:8] + ".png"
	srv := &server{db: db, runtime: cfg}
	request := httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody(imageURL, false))
	recorder := httptest.NewRecorder()

	srv.handleUploadURL(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected hash fallback success, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	data := uploadResponseData(t, recorder.Body.Bytes())
	if data["filename"] != expectedName {
		t.Fatalf("expected deterministic fallback filename %q, got %#v", expectedName, data["filename"])
	}
}

func TestThumbnailCLIGeneratesBoundedWebP(t *testing.T) {
	tmp := t.TempDir()
	input := filepath.Join(tmp, "source.png")
	output := filepath.Join(tmp, "thumb.webp")
	if err := os.WriteFile(input, fixturePNG(t, 720, 360), 0644); err != nil {
		t.Fatal(err)
	}

	if err := runThumbnailCLI(input, output); err != nil {
		t.Fatal(err)
	}

	assertWebPWidth(t, output, thumbnailMaxWidth)
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

func uploadURLJSONBody(imageURL string, thumbnailOnly bool) io.Reader {
	payload := map[string]any{"url": imageURL, "thumbnail_only": thumbnailOnly}
	body, _ := json.Marshal(payload)
	return bytes.NewReader(body)
}

func publicUploadURLResolver(context.Context, string) ([]net.IP, error) {
	return []net.IP{net.ParseIP("93.184.216.34")}, nil
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req)
}

func fakeUploadURLTransport(t *testing.T, content []byte, contentType string, inspect func(*http.Request)) http.RoundTripper {
	t.Helper()
	return roundTripFunc(func(req *http.Request) (*http.Response, error) {
		if inspect != nil {
			inspect(req)
		}
		return &http.Response{
			StatusCode: http.StatusOK,
			Header:     http.Header{"Content-Type": []string{contentType}},
			Body:       io.NopCloser(bytes.NewReader(content)),
			Request:    req,
		}, nil
	})
}

func withUploadURLHooks(t *testing.T, resolver func(context.Context, string) ([]net.IP, error), transport http.RoundTripper) {
	t.Helper()
	originalResolver := uploadURLResolveHost
	originalTransport := uploadURLTransport
	uploadURLResolveHost = resolver
	uploadURLTransport = transport
	t.Cleanup(func() {
		uploadURLResolveHost = originalResolver
		uploadURLTransport = originalTransport
	})
}

func assertUploadsEmpty(t *testing.T, dataDir string) {
	t.Helper()
	entries, err := os.ReadDir(filepath.Join(dataDir, "static", "uploads"))
	if err != nil {
		if os.IsNotExist(err) {
			return
		}
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("expected no upload files, got %v", entries)
	}
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
