package main

import (
	"database/sql"
	"os"
	"path/filepath"
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

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false)
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

	_, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false)
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
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), true)
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
