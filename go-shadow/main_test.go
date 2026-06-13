package main

import (
	"bytes"
	"context"
	"crypto/md5"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"hash/crc32"
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
			category_id INTEGER REFERENCES Categories(id),
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
		CREATE TRIGGER notes_ai AFTER INSERT ON Notes BEGIN
			INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
		END;
		CREATE TRIGGER notes_ad AFTER DELETE ON Notes BEGIN
			INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
		END;
		CREATE TRIGGER notes_au AFTER UPDATE ON Notes BEGIN
			INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
			INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
		END;
		INSERT INTO Categories (name, is_default) VALUES ('note', 1);
		INSERT INTO Notes (title, content, category_id) VALUES ('Welcome Note', 'Welcome to Prism', 1);
	`)
	if err != nil {
		t.Fatal(err)
	}
	return dbPath
}

func createLegacyMigrationDB(t *testing.T, dataDir string) string {
	t.Helper()
	dbPath := filepath.Join(dataDir, "legacy_runtime_dev.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	_, err = db.Exec(`
		CREATE TABLE Categories (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT UNIQUE NOT NULL,
			icon TEXT DEFAULT '📝',
			sort_order INTEGER DEFAULT 0,
			is_default INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		CREATE TABLE Notes (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT,
			content TEXT,
			type TEXT DEFAULT '筆記',
			remarks TEXT,
			cover_image TEXT,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		CREATE TABLE Tags (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT UNIQUE NOT NULL,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
		CREATE VIRTUAL TABLE Notes_FTS USING fts5(
			title, content,
			content='Notes',
			content_rowid='id'
		);
		INSERT INTO Categories (name, icon, is_default) VALUES ('筆記', '📝', 1);
		INSERT INTO Notes (title, content, type) VALUES ('Legacy Note', 'legacy body', '筆記');
	`)
	if err != nil {
		t.Fatal(err)
	}
	return dbPath
}

func createIdempotentMigrationDB(t *testing.T, dataDir string) string {
	t.Helper()
	dbPath := filepath.Join(dataDir, "idempotent_runtime_dev.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	_, err = db.Exec(`
		CREATE TABLE Schema_Meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
		INSERT INTO Schema_Meta (key, value) VALUES ('schema_version', '13');
		CREATE TABLE Categories (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT UNIQUE NOT NULL,
			icon TEXT DEFAULT '📝',
			sort_order INTEGER DEFAULT 0,
			is_default INTEGER DEFAULT 0
		);
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
			parent_id INTEGER,
			prompt_params TEXT,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		);
		INSERT INTO Categories (name, is_default) VALUES ('筆記', 1);
		INSERT INTO Notes (title, content, editor_layout, category_id) VALUES ('Needs Normalize', 'body', 'full', 1);
	`)
	if err != nil {
		t.Fatal(err)
	}
	return dbPath
}

func createVersion15MigrationDB(t *testing.T, dataDir string) string {
	t.Helper()
	dbPath := filepath.Join(dataDir, "version15_runtime_dev.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	_, err = db.Exec(`
		CREATE TABLE Schema_Meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
		INSERT INTO Schema_Meta (key, value) VALUES ('schema_version', '15');
		CREATE TABLE Notes (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			title TEXT,
			content TEXT,
			editor_layout TEXT DEFAULT 'single'
		);
		INSERT INTO Notes (title, content, editor_layout) VALUES ('Rollback Probe', 'body', 'full');
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
	if cfg.enableAttachmentWrite {
		t.Fatal("attachment write should be disabled by default")
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
	expectedDirs := map[string]string{
		"data":        dataDir,
		"uploads":     filepath.Join(dataDir, "static", "uploads"),
		"attachments": filepath.Join(dataDir, "docs", "attachments"),
		"logs":        filepath.Join(dataDir, "logs"),
		"backups":     filepath.Join(dataDir, "backups"),
		"config":      filepath.Join(dataDir, "config"),
	}
	gotDirs := map[string]string{
		"data":        cfg.dataDir,
		"uploads":     cfg.uploadsDir,
		"attachments": cfg.attachmentsDir,
		"logs":        cfg.logsDir,
		"backups":     cfg.backupsDir,
		"config":      cfg.configDir,
	}
	for name, expected := range expectedDirs {
		if gotDirs[name] != expected {
			t.Fatalf("%s dir mismatch: got %s want %s", name, gotDirs[name], expected)
		}
		if _, err := os.Stat(expected); err != nil {
			t.Fatalf("%s dir was not created: %v", name, err)
		}
	}
}

func TestRuntimeConfigRequiresExplicitDataDir(t *testing.T) {
	dbPath := createSpikeDB(t)

	_, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, "", false, false, false, false, false, false)
	if err == nil {
		t.Fatal("expected missing data directory refusal")
	}
	if !strings.Contains(err.Error(), "data directory is required") {
		t.Fatalf("unexpected data-dir error: %v", err)
	}
}

func TestRuntimeConfigResolvesRelativeDBInsideDataDirAndRejectsTraversal(t *testing.T) {
	dataDir := t.TempDir()
	dbPath := createSpikeDB(t)
	copiedDB := filepath.Join(dataDir, "runtime_dev.db")
	content, err := os.ReadFile(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(copiedDB, content, 0600); err != nil {
		t.Fatal(err)
	}

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", "runtime_dev.db", dataDir, false, false, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.dbPath != copiedDB {
		t.Fatalf("relative db path resolved outside data dir: got %s want %s", cfg.dbPath, copiedDB)
	}

	_, err = resolveRuntimeConfig("127.0.0.1:0", ".."+string(filepath.Separator)+"escape_dev.db", dataDir, false, false, false, false, false, false)
	if err == nil {
		t.Fatal("expected relative database traversal refusal")
	}
}

func TestRuntimeConfigMarksMissingRelativeDBForFreshInit(t *testing.T) {
	dataDir := t.TempDir()
	relativeDB := filepath.Join("fresh", "prism_runtime_dev.db")
	expectedDB := filepath.Join(dataDir, relativeDB)

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", relativeDB, dataDir, false, false, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.dbPath != expectedDB {
		t.Fatalf("fresh db path mismatch: got %s want %s", cfg.dbPath, expectedDB)
	}
	if !cfg.freshDBInitNeeded {
		t.Fatal("missing relative DB under data dir should require fresh init")
	}
	if _, err := os.Stat(expectedDB); !os.IsNotExist(err) {
		t.Fatalf("resolveRuntimeConfig should not create the DB file before SQLite opens it, got %v", err)
	}
	if _, err := os.Stat(filepath.Dir(expectedDB)); err != nil {
		t.Fatalf("fresh DB parent dir was not created: %v", err)
	}
}

func TestRuntimeConfigRejectsMissingAbsoluteDBOutsideDataDir(t *testing.T) {
	dataDir := t.TempDir()
	outsideDB := filepath.Join(t.TempDir(), "fresh_dev.db")

	_, err := resolveRuntimeConfig("127.0.0.1:0", outsideDB, dataDir, false, false, false, false, false, false)
	if err == nil {
		t.Fatal("expected missing absolute DB outside data-dir to be rejected")
	}
	if !strings.Contains(err.Error(), "missing database path must be inside data directory") {
		t.Fatalf("unexpected missing absolute DB error: %v", err)
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

func TestOpenRuntimeSQLiteInitializesFreshDBAndReturnsReadOnlyOwner(t *testing.T) {
	dataDir := t.TempDir()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", "fresh/prism_runtime_dev.db", dataDir, false, false, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.freshDBInitNeeded {
		t.Fatal("test setup should require fresh init")
	}
	owner, err := openRuntimeSQLite(&cfg)
	if err != nil {
		t.Fatal(err)
	}
	defer owner.close()

	if !cfg.sqliteQueryOnly {
		t.Fatal("fresh init should update runtime config back to query_only mode")
	}
	if owner.writeEnabled {
		t.Fatal("fresh init without write candidates must return to read-only mode")
	}
	assertSQLiteOwnerSettings(t, owner, true)
	if err := verifySchemaVersion(owner.db, expectedSchemaVersion); err != nil {
		t.Fatal(err)
	}
	if _, err := owner.db.Exec("INSERT INTO Tags (name) VALUES ('blocked-after-fresh-init')"); err == nil {
		t.Fatal("expected query_only mode to block writes after fresh init")
	}

	assertSQLiteTableExists(t, owner.db, "Notes")
	assertSQLiteTableExists(t, owner.db, "Categories")
	assertSQLiteTableExists(t, owner.db, "Tags")
	assertSQLiteTableExists(t, owner.db, "Note_Tags")
	assertSQLiteTableExists(t, owner.db, "Source_Urls")
	assertSQLiteTableExists(t, owner.db, "Note_History")
	assertSQLiteTableExists(t, owner.db, "Note_Attachments")
	assertSQLiteTableExists(t, owner.db, "Schema_Meta")
	assertSQLiteTableExists(t, owner.db, "Notes_FTS")

	assertSQLiteColumnExists(t, owner.db, "Notes", "editor_layout")
	assertSQLiteColumnExists(t, owner.db, "Notes", "parent_id")
	assertSQLiteColumnExists(t, owner.db, "Notes", "prompt_params")
	assertSQLiteColumnDefault(t, owner.db, "Notes", "editor_layout", "'single'")
	assertSQLiteIndexExists(t, owner.db, "idx_notes_updated_at")
	assertSQLiteIndexExists(t, owner.db, "idx_notes_category_id")
	assertSQLiteIndexExists(t, owner.db, "idx_notes_sort_order")
	assertSQLiteIndexExists(t, owner.db, "idx_notes_is_archived")
	assertSQLiteIndexExists(t, owner.db, "idx_notes_parent_id")
	assertSQLiteIndexExists(t, owner.db, "idx_tags_name")
	assertSQLiteIndexExists(t, owner.db, "idx_source_urls_note_id")
	assertSQLiteIndexExists(t, owner.db, "idx_note_history_note_id")
	assertSQLiteIndexExists(t, owner.db, "idx_attachments_note_id")
	assertSQLiteTriggerExists(t, owner.db, "notes_ai")
	assertSQLiteTriggerExists(t, owner.db, "notes_ad")
	assertSQLiteTriggerExists(t, owner.db, "notes_au")

	assertSeededCategory(t, owner.db, "提示詞 | Prompt", "🎨", 1, 0)
	assertSeededCategory(t, owner.db, "筆記 | Note", "📝", 2, 1)
	assertSeededCategory(t, owner.db, "教學 | Tutorial", "📚", 3, 0)
	assertSeededCategory(t, owner.db, "資料 | Data", "💾", 4, 0)
	assertSeededCategory(t, owner.db, "靈感 | Inspiration", "💡", 5, 0)
	assertTagCount(t, owner.db, "Welcome", 1)

	var welcomeNotes int
	if err := owner.db.QueryRow("SELECT COUNT(*) FROM Notes WHERE title = ? AND remarks = ?", welcomeNoteTitle, "系統自動生成").Scan(&welcomeNotes); err != nil {
		t.Fatal(err)
	}
	if welcomeNotes != 1 {
		t.Fatalf("expected one seeded welcome note, got %d", welcomeNotes)
	}
	var linkedWelcomeTags int
	if err := owner.db.QueryRow(`
		SELECT COUNT(*)
		FROM Note_Tags nt
		JOIN Notes n ON n.id = nt.note_id
		JOIN Tags t ON t.id = nt.tag_id
		WHERE n.title = ? AND t.name = 'Welcome'`, welcomeNoteTitle).Scan(&linkedWelcomeTags); err != nil {
		t.Fatal(err)
	}
	if linkedWelcomeTags != 1 {
		t.Fatalf("expected welcome note tag link, got %d", linkedWelcomeTags)
	}
	var ftsHits int
	if err := owner.db.QueryRow("SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", "Prism").Scan(&ftsHits); err != nil {
		t.Fatalf("FTS query failed after fresh init: %v", err)
	}
	if ftsHits != 1 {
		t.Fatalf("expected fresh welcome note to be indexed in FTS, got %d hits", ftsHits)
	}
}

func TestOpenRuntimeSQLiteMigratesLegacyDBCreatesBackupAndReturnsReadOnlyOwner(t *testing.T) {
	dataDir := t.TempDir()
	dbPath := createLegacyMigrationDB(t, dataDir)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false, false, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}

	owner, err := openRuntimeSQLite(&cfg)
	if err != nil {
		t.Fatal(err)
	}
	defer owner.close()

	if owner.writeEnabled {
		t.Fatal("migration without write candidates must return to read-only mode")
	}
	if !cfg.sqliteQueryOnly {
		t.Fatal("runtime config should return to query_only after migrations")
	}
	if cfg.migrationsApplied == 0 {
		t.Fatal("expected legacy DB migration to apply pending versions")
	}
	if cfg.migrationBackupPath == "" {
		t.Fatal("expected pre-migration backup path")
	}
	if _, err := os.Stat(cfg.migrationBackupPath); err != nil {
		t.Fatalf("expected migration backup to exist: %v", err)
	}
	if !isSubpath(cfg.migrationBackupPath, cfg.backupsDir) {
		t.Fatalf("backup escaped backups dir: %s not under %s", cfg.migrationBackupPath, cfg.backupsDir)
	}
	assertSQLiteOwnerSettings(t, owner, true)
	if err := verifySchemaVersion(owner.db, expectedSchemaVersion); err != nil {
		t.Fatal(err)
	}
	assertSQLiteColumnAbsent(t, owner.db, "Notes", "type")
	assertSQLiteColumnExists(t, owner.db, "Notes", "prompt_params")
	assertSQLiteColumnExists(t, owner.db, "Notes", "parent_id")
	assertSQLiteColumnExists(t, owner.db, "Notes", "category_id")
	assertSQLiteColumnAbsent(t, owner.db, "Notes", "text_embedding")
	assertSQLiteColumnAbsent(t, owner.db, "Notes", "embedding_updated_at")
	assertSQLiteTableExists(t, owner.db, "Note_Attachments")
	assertSQLiteIndexExists(t, owner.db, "idx_attachments_note_id")

	status, err := migrationStatus(owner.db)
	if err != nil {
		t.Fatal(err)
	}
	if status.CurrentVersion != expectedSchemaVersion || len(status.Pending) != 0 {
		t.Fatalf("unexpected migration status: current=%d pending=%d", status.CurrentVersion, len(status.Pending))
	}

	backupDB, err := sql.Open("sqlite", cfg.migrationBackupPath)
	if err != nil {
		t.Fatal(err)
	}
	defer backupDB.Close()
	assertSQLiteColumnExists(t, backupDB, "Notes", "type")

	backupCountBefore := countBackupDBFiles(t, cfg.backupsDir)
	cfgSecond, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false, false, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	ownerSecond, err := openRuntimeSQLite(&cfgSecond)
	if err != nil {
		t.Fatal(err)
	}
	defer ownerSecond.close()
	if cfgSecond.migrationsApplied != 0 {
		t.Fatalf("expected idempotent rerun to apply zero migrations, got %d", cfgSecond.migrationsApplied)
	}
	if cfgSecond.migrationBackupPath != "" {
		t.Fatalf("expected no new backup when no migrations are pending, got %s", cfgSecond.migrationBackupPath)
	}
	if got := countBackupDBFiles(t, cfg.backupsDir); got != backupCountBefore {
		t.Fatalf("expected backup count to stay %d on idempotent rerun, got %d", backupCountBefore, got)
	}
}

func TestRunExistingDBMigrationsSkipsDuplicateAndMissingColumns(t *testing.T) {
	dataDir := t.TempDir()
	dbPath := createIdempotentMigrationDB(t, dataDir)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false, false, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}

	owner, err := openRuntimeSQLite(&cfg)
	if err != nil {
		t.Fatal(err)
	}
	defer owner.close()

	if cfg.migrationsApplied != 3 {
		t.Fatalf("expected migrations 14-16 to be considered applied, got %d", cfg.migrationsApplied)
	}
	if err := verifySchemaVersion(owner.db, expectedSchemaVersion); err != nil {
		t.Fatal(err)
	}
	assertSQLiteColumnExists(t, owner.db, "Notes", "prompt_params")
	assertSQLiteColumnAbsent(t, owner.db, "Notes", "text_embedding")
	var layout string
	if err := owner.db.QueryRow("SELECT editor_layout FROM Notes WHERE title = 'Needs Normalize'").Scan(&layout); err != nil {
		t.Fatal(err)
	}
	if layout != "single" {
		t.Fatalf("expected migration 16 to normalize editor_layout, got %q", layout)
	}
}

func TestOpenRuntimeSQLiteFailedMigrationRollsBackAndKeepsBackup(t *testing.T) {
	dataDir := t.TempDir()
	dbPath := createVersion15MigrationDB(t, dataDir)
	originalDefinitions := migrationDefinitions
	originalNow := migrationBackupNow
	migrationDefinitions = []migrationDefinition{
		{16, "failing_test_migration", []string{
			"ALTER TABLE Notes ADD COLUMN rollback_marker TEXT",
			"SELECT * FROM table_that_does_not_exist",
		}},
	}
	migrationBackupNow = func() time.Time {
		return time.Date(2026, 6, 12, 9, 30, 0, 0, time.UTC)
	}
	t.Cleanup(func() {
		migrationDefinitions = originalDefinitions
		migrationBackupNow = originalNow
	})

	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, dataDir, false, false, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	owner, err := openRuntimeSQLite(&cfg)
	if err == nil {
		_ = owner.close()
		t.Fatal("expected failing migration to abort startup")
	}
	if !strings.Contains(err.Error(), "migration failed after backup") {
		t.Fatalf("unexpected migration failure: %v", err)
	}
	if cfg.migrationBackupPath == "" {
		t.Fatal("expected backup path to be recorded before migration failure")
	}
	if _, err := os.Stat(cfg.migrationBackupPath); err != nil {
		t.Fatalf("expected migration backup to exist after failure: %v", err)
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	version, err := schemaVersion(db)
	if err != nil {
		t.Fatal(err)
	}
	if version != 15 {
		t.Fatalf("expected failed migration rollback to keep schema_version 15, got %d", version)
	}
	assertSQLiteColumnAbsent(t, db, "Notes", "rollback_marker")

	backupDB, err := sql.Open("sqlite", cfg.migrationBackupPath)
	if err != nil {
		t.Fatal(err)
	}
	defer backupDB.Close()
	backupVersion, err := schemaVersion(backupDB)
	if err != nil {
		t.Fatal(err)
	}
	if backupVersion != 15 {
		t.Fatalf("expected backup schema_version 15, got %d", backupVersion)
	}
	assertSQLiteColumnAbsent(t, backupDB, "Notes", "rollback_marker")
}

func assertSQLiteOwnerSettings(t *testing.T, owner *sqliteConnectionOwner, wantQueryOnly bool) {
	t.Helper()
	if owner.journalMode != "wal" {
		t.Fatalf("expected owner to record WAL mode, got %q", owner.journalMode)
	}
	if owner.busyTimeoutMS != sqliteBusyTimeoutMS {
		t.Fatalf("expected owner busy timeout %d, got %d", sqliteBusyTimeoutMS, owner.busyTimeoutMS)
	}
	if owner.queryOnly != wantQueryOnly {
		t.Fatalf("owner query_only mismatch: got %v want %v", owner.queryOnly, wantQueryOnly)
	}

	var journalMode string
	if err := owner.db.QueryRow("PRAGMA journal_mode").Scan(&journalMode); err != nil {
		t.Fatal(err)
	}
	if !strings.EqualFold(journalMode, "wal") {
		t.Fatalf("expected SQLite WAL mode, got %q", journalMode)
	}
	var busyTimeout int
	if err := owner.db.QueryRow("PRAGMA busy_timeout").Scan(&busyTimeout); err != nil {
		t.Fatal(err)
	}
	if busyTimeout != sqliteBusyTimeoutMS {
		t.Fatalf("expected SQLite busy timeout %d, got %d", sqliteBusyTimeoutMS, busyTimeout)
	}
	var queryOnly int
	if err := owner.db.QueryRow("PRAGMA query_only").Scan(&queryOnly); err != nil {
		t.Fatal(err)
	}
	expectedQueryOnly := 0
	if wantQueryOnly {
		expectedQueryOnly = 1
	}
	if queryOnly != expectedQueryOnly {
		t.Fatalf("expected SQLite query_only %d, got %d", expectedQueryOnly, queryOnly)
	}
}

func assertSQLiteConnSettings(t *testing.T, conn *sql.Conn, wantQueryOnly bool) {
	t.Helper()
	ctx := context.Background()
	var journalMode string
	if err := conn.QueryRowContext(ctx, "PRAGMA journal_mode").Scan(&journalMode); err != nil {
		t.Fatal(err)
	}
	if !strings.EqualFold(journalMode, "wal") {
		t.Fatalf("expected SQLite WAL mode, got %q", journalMode)
	}
	var busyTimeout int
	if err := conn.QueryRowContext(ctx, "PRAGMA busy_timeout").Scan(&busyTimeout); err != nil {
		t.Fatal(err)
	}
	if busyTimeout != sqliteBusyTimeoutMS {
		t.Fatalf("expected SQLite busy timeout %d, got %d", sqliteBusyTimeoutMS, busyTimeout)
	}
	var queryOnly int
	if err := conn.QueryRowContext(ctx, "PRAGMA query_only").Scan(&queryOnly); err != nil {
		t.Fatal(err)
	}
	expectedQueryOnly := 0
	if wantQueryOnly {
		expectedQueryOnly = 1
	}
	if queryOnly != expectedQueryOnly {
		t.Fatalf("expected SQLite query_only %d, got %d", expectedQueryOnly, queryOnly)
	}
}

func assertTagCount(t *testing.T, db *sql.DB, name string, want int) {
	t.Helper()
	var got int
	if err := db.QueryRow("SELECT COUNT(*) FROM Tags WHERE name = ?", name).Scan(&got); err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("tag %q count mismatch: got %d want %d", name, got, want)
	}
}

func assertSQLiteTableExists(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var got string
	if err := db.QueryRow("SELECT name FROM sqlite_master WHERE name = ?", name).Scan(&got); err != nil {
		t.Fatalf("expected SQLite object %q to exist: %v", name, err)
	}
}

func assertSQLiteIndexExists(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var got string
	if err := db.QueryRow("SELECT name FROM sqlite_master WHERE type = 'index' AND name = ?", name).Scan(&got); err != nil {
		t.Fatalf("expected SQLite index %q to exist: %v", name, err)
	}
}

func assertSQLiteTriggerExists(t *testing.T, db *sql.DB, name string) {
	t.Helper()
	var got string
	if err := db.QueryRow("SELECT name FROM sqlite_master WHERE type = 'trigger' AND name = ?", name).Scan(&got); err != nil {
		t.Fatalf("expected SQLite trigger %q to exist: %v", name, err)
	}
}

func assertSQLiteColumnExists(t *testing.T, db *sql.DB, table, column string) {
	t.Helper()
	rows, err := db.Query("PRAGMA table_info(" + table + ")")
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var name, columnType string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &columnType, &notNull, &defaultValue, &pk); err != nil {
			t.Fatal(err)
		}
		if name == column {
			return
		}
	}
	t.Fatalf("expected %s.%s to exist", table, column)
}

func assertSQLiteColumnAbsent(t *testing.T, db *sql.DB, table, column string) {
	t.Helper()
	rows, err := db.Query("PRAGMA table_info(" + table + ")")
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var name, columnType string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &columnType, &notNull, &defaultValue, &pk); err != nil {
			t.Fatal(err)
		}
		if name == column {
			t.Fatalf("expected %s.%s to be absent", table, column)
		}
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
}

func assertSQLiteColumnDefault(t *testing.T, db *sql.DB, table, column, want string) {
	t.Helper()
	rows, err := db.Query("PRAGMA table_info(" + table + ")")
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var name, columnType string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &columnType, &notNull, &defaultValue, &pk); err != nil {
			t.Fatal(err)
		}
		if name == column {
			if !defaultValue.Valid || defaultValue.String != want {
				t.Fatalf("default mismatch for %s.%s: got %q valid=%v want %q", table, column, defaultValue.String, defaultValue.Valid, want)
			}
			return
		}
	}
	t.Fatalf("expected %s.%s to exist", table, column)
}

func assertSeededCategory(t *testing.T, db *sql.DB, name, icon string, sortOrder, isDefault int) {
	t.Helper()
	var gotIcon string
	var gotSortOrder int
	var gotDefault int
	if err := db.QueryRow("SELECT icon, sort_order, is_default FROM Categories WHERE name = ?", name).Scan(&gotIcon, &gotSortOrder, &gotDefault); err != nil {
		t.Fatalf("expected seeded category %q: %v", name, err)
	}
	if gotIcon != icon || gotSortOrder != sortOrder || gotDefault != isDefault {
		t.Fatalf("category %q mismatch: got icon=%q sort=%d default=%d", name, gotIcon, gotSortOrder, gotDefault)
	}
}

func countBackupDBFiles(t *testing.T, backupsDir string) int {
	t.Helper()
	entries, err := os.ReadDir(backupsDir)
	if err != nil {
		t.Fatal(err)
	}
	count := 0
	for _, entry := range entries {
		if !entry.IsDir() && strings.HasPrefix(entry.Name(), "prism_go_pre_migrate_") && strings.HasSuffix(entry.Name(), ".db") {
			count++
		}
	}
	return count
}

func TestSQLiteOwnerDSNConfiguresPragmasForEachConnection(t *testing.T) {
	dbPath := createSpikeDB(t)
	owner, err := openSQLiteOwner(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer owner.close()

	ctx := context.Background()
	conn1, err := owner.db.Conn(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer conn1.Close()
	conn2, err := owner.db.Conn(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer conn2.Close()

	assertSQLiteConnSettings(t, conn1, true)
	assertSQLiteConnSettings(t, conn2, true)
}

func TestSQLiteOwnerConfiguresWALBusyTimeoutAndReadOnlyMode(t *testing.T) {
	dbPath := createSpikeDB(t)
	owner, err := openSQLiteOwner(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer owner.close()

	if owner.writeEnabled {
		t.Fatal("read-only owner must not report write mode")
	}
	assertSQLiteOwnerSettings(t, owner, true)

	if err := owner.withTransaction(func(tx *sql.Tx) error {
		_, err := tx.Exec("INSERT INTO Tags (name) VALUES ('blocked-by-owner')")
		return err
	}); err == nil || !strings.Contains(err.Error(), "requires write mode") {
		t.Fatalf("expected read-only transaction refusal, got %v", err)
	}
	if _, err := owner.db.Exec("INSERT INTO Tags (name) VALUES ('blocked-by-query-only')"); err == nil {
		t.Fatal("expected query_only mode to block direct DB writes")
	}
}

func TestSQLiteOwnerWriteModeTransactionCommitAndRollback(t *testing.T) {
	dbPath := createSpikeDB(t)
	owner, err := openSQLiteOwner(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer owner.close()

	if !owner.writeEnabled {
		t.Fatal("write owner must report write mode")
	}
	assertSQLiteOwnerSettings(t, owner, false)

	if err := owner.withTransaction(func(tx *sql.Tx) error {
		_, err := tx.Exec("INSERT INTO Tags (name) VALUES ('committed')")
		return err
	}); err != nil {
		t.Fatalf("expected transaction commit to succeed: %v", err)
	}
	assertTagCount(t, owner.db, "committed", 1)

	rollbackErr := errors.New("force rollback")
	err = owner.withTransaction(func(tx *sql.Tx) error {
		if _, err := tx.Exec("INSERT INTO Tags (name) VALUES ('rolled_back')"); err != nil {
			return err
		}
		return rollbackErr
	})
	if !errors.Is(err, rollbackErr) {
		t.Fatalf("expected rollback error to propagate, got %v", err)
	}
	assertTagCount(t, owner.db, "rolled_back", 0)
}

func TestMigrationStatusHandlerMatchesPythonShapeAndKeepsQueryOnly(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	srv := &server{db: db, runtime: runtimeConfig{sqliteQueryOnly: true}}
	request := httptest.NewRequest(http.MethodGet, "/api/system/migration-status", nil)
	recorder := httptest.NewRecorder()
	srv.handleMigrationStatus(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected migration status 200, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatalf("expected JSON response: %v", err)
	}
	if payload["status"] != "success" {
		t.Fatalf("unexpected status payload: %#v", payload)
	}
	data := payload["data"].(map[string]any)
	if data["current_version"].(float64) != 16 {
		t.Fatalf("unexpected current version: %#v", data)
	}
	if data["latest_version"].(float64) != 16 {
		t.Fatalf("unexpected latest version: %#v", data)
	}
	completed := data["completed"].([]any)
	pending := data["pending"].([]any)
	if len(completed) != 16 {
		t.Fatalf("expected 16 completed migrations, got %d", len(completed))
	}
	if len(pending) != 0 {
		t.Fatalf("expected no pending migrations, got %#v", pending)
	}
	last := completed[len(completed)-1].(map[string]any)
	if last["name"] != "normalize_editor_layout" {
		t.Fatalf("unexpected last migration: %#v", last)
	}

	_, err = db.Exec("INSERT INTO Notes (title, content) VALUES ('blocked', 'query only')")
	if err == nil {
		t.Fatal("migration status must keep DB writes blocked")
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

func TestAttachmentWriteDisablesQueryOnlyWhenExplicitlyEnabled(t *testing.T) {
	dbPath := createSpikeDB(t)
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, false, false, true)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.enableAttachmentWrite {
		t.Fatal("attachment write should be enabled by explicit flag")
	}
	if cfg.sqliteQueryOnly {
		t.Fatal("attachment metadata writes must disable SQLite query_only")
	}
	if got := (&server{runtime: cfg}).apiSurface(); got != "get-read-only+local-attachment-write" {
		t.Fatalf("api surface mismatch: %s", got)
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

func TestNotesSearchUsesTokenizedFTSAndCardFields(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	dataDir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dataDir, "docs", "attachments"), 0755); err != nil {
		t.Fatal(err)
	}

	ftsID := insertSearchNote(t, db, "FTS fixture", "ftsa appears before ftsb", "", 1)
	remarksID := insertSearchNote(t, db, "Remarks fixture", "plain body", "remarkaa appears before remarkbb", 1)
	tagsID := insertSearchNote(t, db, "Tags fixture", "plain body", "", 1)
	metaID := insertSearchNote(t, db, "Metadata fixture", "plain body", "", 1)
	bodyID := insertSearchNote(t, db, "Body fixture", "plain body", "", 1)

	if _, err := db.Exec("INSERT INTO Tags (name) VALUES ('tagaa'), ('tagbb')"); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Note_Tags (note_id, tag_id) SELECT ?, id FROM Tags WHERE name IN ('tagaa', 'tagbb')", tagsID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes) VALUES (?, 'docs/attachments/meta-fixture.md', 'md', 'metaaa appears before metabb', 10)", metaID); err != nil {
		t.Fatal(err)
	}
	bodyPath := filepath.Join(dataDir, "docs", "attachments", "body-fixture.md")
	if err := os.WriteFile(bodyPath, []byte("bodyaa appears before bodybb"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes) VALUES (?, 'docs/attachments/body-fixture.md', 'md', 'body fixture', ?)", bodyID, int64(len("bodyaa appears before bodybb"))); err != nil {
		t.Fatal(err)
	}

	srv := &server{db: db, runtime: runtimeConfig{dataDir: dataDir, sqliteQueryOnly: false}}
	assertNotesSearchIncludes(t, srv, "/api/notes?q=ftsa%20ftsb&per_page=100", ftsID)
	assertNotesSearchIncludes(t, srv, "/api/notes?q=remarkaa%20remarkbb&per_page=100", remarksID)
	assertNotesSearchIncludes(t, srv, "/api/notes?q=tagaa%20tagbb&per_page=100", tagsID)
	assertNotesSearchIncludes(t, srv, "/api/notes?q=metaaa%20metabb&per_page=100", metaID)
	assertNotesSearchIncludes(t, srv, "/api/notes?q=bodyaa%20bodybb&per_page=100", bodyID)

	recorder := httptest.NewRecorder()
	srv.handleNotes(recorder, httptest.NewRequest(http.MethodGet, "/api/notes?type=not-a-category&per_page=100", nil))
	if recorder.Code != http.StatusOK {
		t.Fatalf("expected unknown type compatibility query to succeed, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	pagination := payload["pagination"].(map[string]any)
	if int(pagination["total"].(float64)) < 6 {
		t.Fatalf("unknown type should not add an empty filter, payload=%#v", payload)
	}
}

func TestNotesCreateAndUpdateDefaultCategoryFTSAndRollback(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	srv := &server{db: db, runtime: runtimeConfig{enableNotesWrite: true}}
	createBody := `{"content":"defaultcategorytoken content","title":"","tags":["created-tag"],"urls":["https://created.example"]}`
	createRecorder := httptest.NewRecorder()
	srv.handleNotes(createRecorder, httptest.NewRequest(http.MethodPost, "/api/notes", strings.NewReader(createBody)))
	if createRecorder.Code != http.StatusCreated {
		t.Fatalf("expected create 201, got %d body=%s", createRecorder.Code, createRecorder.Body.String())
	}
	noteID := noteIDFromResponse(t, createRecorder.Body.Bytes())
	var categoryID int
	if err := db.QueryRow("SELECT category_id FROM Notes WHERE id = ?", noteID).Scan(&categoryID); err != nil {
		t.Fatal(err)
	}
	if categoryID != 1 {
		t.Fatalf("create without category_id should use default category 1, got %d", categoryID)
	}
	assertFTSCount(t, db, "defaultcategorytoken", 1)

	updateBody := `{"title":"Updated note","content":"updatedftstoken content","category_id":1,"remarks":"updated remarks","tags":["updated-tag"],"urls":["https://updated.example"]}`
	updateRecorder := httptest.NewRecorder()
	srv.handleNoteDetail(updateRecorder, httptest.NewRequest(http.MethodPut, fmt.Sprintf("/api/notes/%d", noteID), strings.NewReader(updateBody)))
	if updateRecorder.Code != http.StatusOK {
		t.Fatalf("expected update 200, got %d body=%s", updateRecorder.Code, updateRecorder.Body.String())
	}
	assertFTSCount(t, db, "updatedftstoken", 1)
	assertFTSCount(t, db, "defaultcategorytoken", 0)
	var historyCount int
	if err := db.QueryRow("SELECT COUNT(*) FROM Note_History WHERE note_id = ?", noteID).Scan(&historyCount); err != nil {
		t.Fatal(err)
	}
	if historyCount != 1 {
		t.Fatalf("expected one history row after content update, got %d", historyCount)
	}

	before := noteSnapshot(t, db, noteID)
	badBody := `{"title":"Broken update","content":"broken rollback content","category_id":999999}`
	badRecorder := httptest.NewRecorder()
	srv.handleNoteDetail(badRecorder, httptest.NewRequest(http.MethodPut, fmt.Sprintf("/api/notes/%d", noteID), strings.NewReader(badBody)))
	if badRecorder.Code != http.StatusInternalServerError {
		t.Fatalf("expected FK failure to return 500, got %d body=%s", badRecorder.Code, badRecorder.Body.String())
	}
	after := noteSnapshot(t, db, noteID)
	if before != after {
		t.Fatalf("failed update should roll back note row\nbefore=%s\nafter=%s", before, after)
	}
	if err := db.QueryRow("SELECT COUNT(*) FROM Note_History WHERE note_id = ?", noteID).Scan(&historyCount); err != nil {
		t.Fatal(err)
	}
	if historyCount != 1 {
		t.Fatalf("failed update should roll back inserted history, got %d rows", historyCount)
	}
}

func TestNotesDeleteCleansImagesFTSAndAssociations(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	dataDir := t.TempDir()
	uploadsDir := filepath.Join(dataDir, "static", "uploads")
	if err := os.MkdirAll(uploadsDir, 0755); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{
		"delete.jpg", "delete_thumb.webp", "cover.jpg", "cover_thumb.webp",
		"shared.jpg", "shared_thumb.webp", "batch-a.jpg", "batch-a_thumb.webp",
		"batch-thumb_thumb.webp", "batch-thumb.jpg",
	} {
		if err := os.WriteFile(filepath.Join(uploadsDir, name), []byte(name), 0644); err != nil {
			t.Fatal(err)
		}
	}

	deleteID := insertSearchNote(t, db, "Delete Fixture", "deleteftstoken ![](/static/uploads/delete.jpg)", "", 1)
	sharedDeleteID := insertSearchNote(t, db, "Shared Delete", "sharedtoken ![](/static/uploads/shared.jpg)", "", 1)
	sharedKeepID := insertSearchNote(t, db, "Shared Keep", "sharedtoken ![](/static/uploads/shared.jpg)", "", 1)
	batchAID := insertSearchNote(t, db, "Batch A", "batchatoken ![](/static/uploads/batch-a.jpg)", "", 1)
	batchBID := insertSearchNote(t, db, "Batch B", "batchbtoken", "", 1)
	if _, err := db.Exec("UPDATE Notes SET cover_image = '/static/uploads/cover.jpg' WHERE id = ?", deleteID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("UPDATE Notes SET cover_image = '/static/uploads/batch-thumb_thumb.webp' WHERE id = ?", batchBID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Tags (name) VALUES ('delete-tag')"); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Note_Tags (note_id, tag_id) SELECT ?, id FROM Tags WHERE name = 'delete-tag'", deleteID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Source_Urls (note_id, url) VALUES (?, 'https://delete.example')", deleteID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, 'old delete content', 'delete history')", deleteID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Note_Attachments (note_id, file_path, file_type, title) VALUES (?, 'docs/attachments/delete.md', 'md', 'delete attachment')", deleteID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, 'batch old content', 'batch history')", batchAID); err != nil {
		t.Fatal(err)
	}

	srv := &server{db: db, runtime: runtimeConfig{enableNotesWrite: true, uploadsDir: uploadsDir}}
	deleteRecorder := httptest.NewRecorder()
	srv.handleNoteDetail(deleteRecorder, httptest.NewRequest(http.MethodDelete, fmt.Sprintf("/api/notes/%d", deleteID), nil))
	if deleteRecorder.Code != http.StatusOK {
		t.Fatalf("expected delete 200, got %d body=%s", deleteRecorder.Code, deleteRecorder.Body.String())
	}
	for _, name := range []string{"delete.jpg", "delete_thumb.webp", "cover.jpg", "cover_thumb.webp"} {
		if _, err := os.Stat(filepath.Join(uploadsDir, name)); !os.IsNotExist(err) {
			t.Fatalf("expected %s to be deleted, stat err=%v", name, err)
		}
	}
	assertTableCount(t, db, "Notes", deleteID, 0)
	assertTableCount(t, db, "Note_Tags", deleteID, 0)
	assertTableCount(t, db, "Source_Urls", deleteID, 0)
	assertTableCount(t, db, "Note_History", deleteID, 0)
	assertTableCount(t, db, "Note_Attachments", deleteID, 0)
	assertFTSCount(t, db, "deleteftstoken", 0)

	sharedRecorder := httptest.NewRecorder()
	srv.handleNoteDetail(sharedRecorder, httptest.NewRequest(http.MethodDelete, fmt.Sprintf("/api/notes/%d", sharedDeleteID), nil))
	if sharedRecorder.Code != http.StatusOK {
		t.Fatalf("expected shared delete 200, got %d body=%s", sharedRecorder.Code, sharedRecorder.Body.String())
	}
	for _, name := range []string{"shared.jpg", "shared_thumb.webp"} {
		if _, err := os.Stat(filepath.Join(uploadsDir, name)); err != nil {
			t.Fatalf("expected shared file %s to remain, err=%v", name, err)
		}
	}
	assertTableCount(t, db, "Notes", sharedKeepID, 1)

	batchRecorder := httptest.NewRecorder()
	batchBody := fmt.Sprintf(`{"note_ids":[%d,%d,999999]}`, batchAID, batchBID)
	srv.handleNoteDetail(batchRecorder, httptest.NewRequest(http.MethodPost, "/api/notes/batch/delete", strings.NewReader(batchBody)))
	if batchRecorder.Code != http.StatusOK {
		t.Fatalf("expected batch delete 200, got %d body=%s", batchRecorder.Code, batchRecorder.Body.String())
	}
	var payload struct {
		Data struct {
			DeletedCount int `json:"deleted_count"`
		} `json:"data"`
	}
	if err := json.Unmarshal(batchRecorder.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload.Data.DeletedCount != 2 {
		t.Fatalf("expected batch deleted_count 2, got %d", payload.Data.DeletedCount)
	}
	for _, name := range []string{"batch-a.jpg", "batch-a_thumb.webp", "batch-thumb_thumb.webp", "batch-thumb.jpg"} {
		if _, err := os.Stat(filepath.Join(uploadsDir, name)); !os.IsNotExist(err) {
			t.Fatalf("expected %s to be deleted by batch cleanup, stat err=%v", name, err)
		}
	}
	assertTableCount(t, db, "Notes", batchAID, 0)
	assertTableCount(t, db, "Note_History", batchAID, 0)
	assertFTSCount(t, db, "batchatoken", 0)
	assertFTSCount(t, db, "batchbtoken", 0)
}

func insertSearchNote(t *testing.T, db *sql.DB, title, content, remarks string, categoryID int) int {
	t.Helper()
	result, err := db.Exec(
		"INSERT INTO Notes (title, content, remarks, category_id, sort_order) VALUES (?, ?, ?, ?, ?)",
		title, content, remarks, categoryID, 100,
	)
	if err != nil {
		t.Fatal(err)
	}
	id, err := result.LastInsertId()
	if err != nil {
		t.Fatal(err)
	}
	return int(id)
}

func assertNotesSearchIncludes(t *testing.T, srv *server, path string, wantID int) {
	t.Helper()
	recorder := httptest.NewRecorder()
	srv.handleNotes(recorder, httptest.NewRequest(http.MethodGet, path, nil))
	if recorder.Code != http.StatusOK {
		t.Fatalf("%s returned %d body=%s", path, recorder.Code, recorder.Body.String())
	}
	var payload struct {
		Data []map[string]any `json:"data"`
	}
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	for _, note := range payload.Data {
		if int(note["id"].(float64)) == wantID {
			return
		}
	}
	t.Fatalf("%s did not include note id %d; payload=%s", path, wantID, recorder.Body.String())
}

func noteIDFromResponse(t *testing.T, body []byte) int {
	t.Helper()
	var payload struct {
		Data struct {
			NoteID int `json:"note_id"`
		} `json:"data"`
	}
	if err := json.Unmarshal(body, &payload); err != nil {
		t.Fatal(err)
	}
	if payload.Data.NoteID == 0 {
		t.Fatalf("missing note_id in response: %s", string(body))
	}
	return payload.Data.NoteID
}

func assertFTSCount(t *testing.T, db *sql.DB, query string, want int) {
	t.Helper()
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", query).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != want {
		t.Fatalf("FTS query %q got %d hits, want %d", query, count, want)
	}
}

func assertTableCount(t *testing.T, db *sql.DB, table string, noteID int, want int) {
	t.Helper()
	column := "note_id"
	if table == "Notes" {
		column = "id"
	}
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM "+table+" WHERE "+column+" = ?", noteID).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != want {
		t.Fatalf("%s rows for note %d got %d, want %d", table, noteID, count, want)
	}
}

func noteSnapshot(t *testing.T, db *sql.DB, noteID int) string {
	t.Helper()
	var title, content string
	var categoryID sql.NullInt64
	if err := db.QueryRow("SELECT title, content, category_id FROM Notes WHERE id = ?", noteID).Scan(&title, &content, &categoryID); err != nil {
		t.Fatal(err)
	}
	return fmt.Sprintf("%s|%s|%v", title, content, nullableIntOrNil(categoryID))
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

func TestExtractPromptHandlerReadsStableDiffusionPNGMetadata(t *testing.T) {
	dataDir := t.TempDir()
	uploadsDir := filepath.Join(dataDir, "static", "uploads")
	if err := os.MkdirAll(uploadsDir, 0755); err != nil {
		t.Fatal(err)
	}
	imagePath := filepath.Join(uploadsDir, "prompt.png")
	metadata := "beautiful forest\nNegative prompt: blurry\nSteps: 20, Sampler: Euler"
	if err := os.WriteFile(imagePath, pngWithTextChunk("parameters", metadata), 0644); err != nil {
		t.Fatal(err)
	}

	srv := &server{runtime: runtimeConfig{dataDir: dataDir, uploadsDir: uploadsDir, enableUploadWrite: true}}
	request := httptest.NewRequest(http.MethodPost, "/api/upload/extract-prompt", strings.NewReader(`{"image_path":"/static/uploads/prompt.png"}`))
	recorder := httptest.NewRecorder()
	srv.handleExtractPrompt(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected prompt extraction 200, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	var payload struct {
		Status string `json:"status"`
		Data   struct {
			Prompt         string `json:"prompt"`
			NegativePrompt string `json:"negative_prompt"`
			Source         string `json:"source"`
			HasPrompt      bool   `json:"has_prompt"`
		} `json:"data"`
	}
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload.Status != "success" || !payload.Data.HasPrompt {
		t.Fatalf("unexpected payload: %#v", payload)
	}
	if payload.Data.Prompt != "beautiful forest" || payload.Data.NegativePrompt != "blurry" || payload.Data.Source != "stable_diffusion" {
		t.Fatalf("unexpected prompt data: %#v", payload.Data)
	}
}

func TestExtractPromptHandlerHasControlledFailures(t *testing.T) {
	dataDir := t.TempDir()
	uploadsDir := filepath.Join(dataDir, "static", "uploads")
	if err := os.MkdirAll(uploadsDir, 0755); err != nil {
		t.Fatal(err)
	}

	disabled := &server{runtime: runtimeConfig{dataDir: dataDir, uploadsDir: uploadsDir}}
	disabledRequest := httptest.NewRequest(http.MethodPost, "/api/upload/extract-prompt", strings.NewReader(`{"image_path":"/static/uploads/missing.png"}`))
	disabledRecorder := httptest.NewRecorder()
	disabled.handleExtractPrompt(disabledRecorder, disabledRequest)
	if disabledRecorder.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected disabled prompt extraction 405, got %d", disabledRecorder.Code)
	}

	enabled := &server{runtime: runtimeConfig{dataDir: dataDir, uploadsDir: uploadsDir, enableUploadWrite: true}}
	missingRequest := httptest.NewRequest(http.MethodPost, "/api/upload/extract-prompt", strings.NewReader(`{"image_path":"/static/uploads/missing.png"}`))
	missingRecorder := httptest.NewRecorder()
	enabled.handleExtractPrompt(missingRecorder, missingRequest)
	if missingRecorder.Code != http.StatusNotFound {
		t.Fatalf("expected missing prompt image 404, got %d body=%s", missingRecorder.Code, missingRecorder.Body.String())
	}
}

func TestLongContentSeparationAndRestoreHandlers(t *testing.T) {
	dataDir := t.TempDir()
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	longContent := strings.Repeat("長文內容", 1500)
	if _, err := db.Exec("UPDATE Notes SET title = 'Long Note', content = ? WHERE id = 1", longContent); err != nil {
		t.Fatal(err)
	}
	notesDir := filepath.Join(dataDir, "docs", "notes")
	srv := &server{db: db, runtime: runtimeConfig{dataDir: dataDir, notesDir: notesDir, enableNotesWrite: true, enableAttachmentTextRead: true}}

	checkRecorder := httptest.NewRecorder()
	srv.handleNoteDetail(checkRecorder, httptest.NewRequest(http.MethodGet, "/api/notes/1/check_separation", nil))
	if checkRecorder.Code != http.StatusOK || !strings.Contains(checkRecorder.Body.String(), `"should_separate":true`) {
		t.Fatalf("unexpected check_separation response: %d %s", checkRecorder.Code, checkRecorder.Body.String())
	}

	separateRecorder := httptest.NewRecorder()
	srv.handleNoteDetail(separateRecorder, httptest.NewRequest(http.MethodPost, "/api/notes/1/separate", strings.NewReader(`{"preview_length":120}`)))
	if separateRecorder.Code != http.StatusOK {
		t.Fatalf("expected separate 200, got %d body=%s", separateRecorder.Code, separateRecorder.Body.String())
	}
	var separatePayload struct {
		Data struct {
			AttachmentID int    `json:"attachment_id"`
			FilePath     string `json:"file_path"`
		} `json:"data"`
	}
	if err := json.Unmarshal(separateRecorder.Body.Bytes(), &separatePayload); err != nil {
		t.Fatal(err)
	}
	if separatePayload.Data.AttachmentID == 0 || separatePayload.Data.FilePath != "docs/notes/note_1.md" {
		t.Fatalf("unexpected separation payload: %#v", separatePayload)
	}
	if _, err := os.Stat(filepath.Join(notesDir, "note_1.md")); err != nil {
		t.Fatalf("expected separated note file: %v", err)
	}

	readRecorder := httptest.NewRecorder()
	srv.handleAttachmentDetail(readRecorder, httptest.NewRequest(http.MethodGet, fmt.Sprintf("/api/attachments/%d", separatePayload.Data.AttachmentID), nil))
	if readRecorder.Code != http.StatusOK || !strings.Contains(readRecorder.Body.String(), "長文內容") {
		t.Fatalf("expected auto-extracted attachment text, got %d %s", readRecorder.Code, readRecorder.Body.String())
	}

	restoreRecorder := httptest.NewRecorder()
	srv.handleNoteDetail(restoreRecorder, httptest.NewRequest(http.MethodPost, "/api/notes/1/restore", strings.NewReader(`{}`)))
	if restoreRecorder.Code != http.StatusOK {
		t.Fatalf("expected restore 200, got %d body=%s", restoreRecorder.Code, restoreRecorder.Body.String())
	}
	var restoredContent string
	if err := db.QueryRow("SELECT content FROM Notes WHERE id = 1").Scan(&restoredContent); err != nil {
		t.Fatal(err)
	}
	if restoredContent != longContent {
		t.Fatal("expected full content restored to note")
	}
	var attachmentCount int
	if err := db.QueryRow("SELECT COUNT(*) FROM Note_Attachments WHERE note_id = 1 AND is_auto_extracted = 1").Scan(&attachmentCount); err != nil {
		t.Fatal(err)
	}
	if attachmentCount != 0 {
		t.Fatalf("expected auto attachment row deleted, got %d", attachmentCount)
	}
	if _, err := os.Stat(filepath.Join(notesDir, "note_1.md")); !os.IsNotExist(err) {
		t.Fatalf("expected separated file removed, got %v", err)
	}
}

func TestCheckUpdateReturnsControlledGoPrimaryStatus(t *testing.T) {
	srv := &server{runtime: runtimeConfig{enableServerSystem: true}}
	request := httptest.NewRequest(http.MethodGet, "/api/system/check-update", nil)
	recorder := httptest.NewRecorder()
	srv.handleCheckUpdate(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("expected check-update 200, got %d body=%s", recorder.Code, recorder.Body.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	data := payload["data"].(map[string]any)
	if data["current_version"] == "" || data["has_update"] != false || data["message"] != "未設定更新來源" {
		t.Fatalf("unexpected check-update payload: %#v", payload)
	}
}

func TestStaticConfigDoesNotFallBackToSPAHTML(t *testing.T) {
	srv := &server{}
	request := httptest.NewRequest(http.MethodGet, "/static/config/wizard_options.json", nil)
	recorder := httptest.NewRecorder()
	srv.staticHandler().ServeHTTP(recorder, request)

	if recorder.Code != http.StatusNotFound {
		t.Fatalf("expected static config 404, got %d", recorder.Code)
	}
	if contentType := recorder.Header().Get("Content-Type"); !strings.Contains(contentType, "application/json") {
		t.Fatalf("expected JSON response, got content-type %q body=%s", contentType, recorder.Body.String())
	}
	if strings.Contains(recorder.Body.String(), "<html") {
		t.Fatalf("static config fallback returned HTML: %s", recorder.Body.String())
	}
}

func pngWithTextChunk(keyword, text string) []byte {
	chunk := func(kind, payload []byte) []byte {
		out := bytes.Buffer{}
		out.Write([]byte{byte(len(payload) >> 24), byte(len(payload) >> 16), byte(len(payload) >> 8), byte(len(payload))})
		out.Write(kind)
		out.Write(payload)
		crc := crc32.ChecksumIEEE(append(kind, payload...))
		out.Write([]byte{byte(crc >> 24), byte(crc >> 16), byte(crc >> 8), byte(crc)})
		return out.Bytes()
	}
	out := bytes.Buffer{}
	out.Write([]byte("\x89PNG\r\n\x1a\n"))
	out.Write(chunk([]byte("tEXt"), append(append([]byte(keyword), 0), []byte(text)...)))
	out.Write(chunk([]byte("IEND"), nil))
	return out.Bytes()
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

func assertNoteIntColumn(t *testing.T, db *sql.DB, noteID int, column string, want int) {
	t.Helper()
	var got int
	if err := db.QueryRow("SELECT COALESCE("+column+", -1) FROM Notes WHERE id = ?", noteID).Scan(&got); err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("note %d column %s got %d, want %d", noteID, column, got, want)
	}
}

func tagIDByName(t *testing.T, db *sql.DB, name string) int {
	t.Helper()
	var id int
	if err := db.QueryRow("SELECT id FROM Tags WHERE name = ?", name).Scan(&id); err != nil {
		t.Fatal(err)
	}
	return id
}

// TestNotesPinArchiveDuplicateReorderHandlers locks the notes action surface that
// previously had no Go unit coverage (only Python-oracle parity). See
// docs/T053-test-disposition-plan.md §E.
func TestNotesPinArchiveDuplicateReorderHandlers(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	srv := &server{db: db, runtime: runtimeConfig{enableNotesWrite: true}}
	firstID := insertSearchNote(t, db, "Pin Fixture", "pincontent", "", 1)
	secondID := insertSearchNote(t, db, "Reorder Fixture", "reordercontent", "", 1)

	// pin with empty body toggles 0 -> 1
	pinRec := httptest.NewRecorder()
	srv.handleNoteDetail(pinRec, httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/notes/%d/pin", firstID), nil))
	if pinRec.Code != http.StatusOK {
		t.Fatalf("expected pin 200, got %d body=%s", pinRec.Code, pinRec.Body.String())
	}
	var pinResp struct {
		Data struct {
			IsPinned bool `json:"is_pinned"`
		} `json:"data"`
	}
	if err := json.Unmarshal(pinRec.Body.Bytes(), &pinResp); err != nil {
		t.Fatal(err)
	}
	if !pinResp.Data.IsPinned {
		t.Fatalf("expected is_pinned true after pin, body=%s", pinRec.Body.String())
	}
	assertNoteIntColumn(t, db, firstID, "is_pinned", 1)

	// pin again toggles 1 -> 0
	pinAgain := httptest.NewRecorder()
	srv.handleNoteDetail(pinAgain, httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/notes/%d/pin", firstID), nil))
	if pinAgain.Code != http.StatusOK {
		t.Fatalf("expected second pin 200, got %d", pinAgain.Code)
	}
	assertNoteIntColumn(t, db, firstID, "is_pinned", 0)

	// archive with explicit body
	archiveRec := httptest.NewRecorder()
	srv.handleNoteDetail(archiveRec, httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/notes/%d/archive", firstID), strings.NewReader(`{"archived":true}`)))
	if archiveRec.Code != http.StatusOK {
		t.Fatalf("expected archive 200, got %d body=%s", archiveRec.Code, archiveRec.Body.String())
	}
	assertNoteIntColumn(t, db, firstID, "is_archived", 1)

	// duplicate creates a new note with the copy suffix
	dupRec := httptest.NewRecorder()
	srv.handleNoteDetail(dupRec, httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/notes/%d/duplicate", firstID), strings.NewReader(`{}`)))
	if dupRec.Code != http.StatusCreated {
		t.Fatalf("expected duplicate 201, got %d body=%s", dupRec.Code, dupRec.Body.String())
	}
	newID := noteIDFromResponse(t, dupRec.Body.Bytes())
	if newID == firstID {
		t.Fatalf("duplicate should create a new note id, got original %d", newID)
	}
	var dupTitle string
	if err := db.QueryRow("SELECT title FROM Notes WHERE id = ?", newID).Scan(&dupTitle); err != nil {
		t.Fatal(err)
	}
	if !strings.HasSuffix(dupTitle, " (Copy)") {
		t.Fatalf("duplicate title should carry copy suffix, got %q", dupTitle)
	}

	// reorder [second, first] sets sort_order second=0, first=1
	reorderRec := httptest.NewRecorder()
	reorderBody := fmt.Sprintf(`{"note_ids":[%d,%d]}`, secondID, firstID)
	srv.handleNoteDetail(reorderRec, httptest.NewRequest(http.MethodPut, "/api/notes/reorder", strings.NewReader(reorderBody)))
	if reorderRec.Code != http.StatusOK {
		t.Fatalf("expected reorder 200, got %d body=%s", reorderRec.Code, reorderRec.Body.String())
	}
	assertNoteIntColumn(t, db, secondID, "sort_order", 0)
	assertNoteIntColumn(t, db, firstID, "sort_order", 1)
}

// TestNotesBatchTypeAndTagsHandlers locks batch/type and batch/tags, previously
// only covered by Python-oracle parity. See docs/T053-test-disposition-plan.md §E.
func TestNotesBatchTypeAndTagsHandlers(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	if _, err := db.Exec("INSERT INTO Categories (name) VALUES ('Batch Target Cat')"); err != nil {
		t.Fatal(err)
	}
	var targetCat int
	if err := db.QueryRow("SELECT id FROM Categories WHERE name = 'Batch Target Cat'").Scan(&targetCat); err != nil {
		t.Fatal(err)
	}

	srv := &server{db: db, runtime: runtimeConfig{enableNotesWrite: true}}
	aID := insertSearchNote(t, db, "Batch One", "batchone", "", 1)
	bID := insertSearchNote(t, db, "Batch Two", "batchtwo", "", 1)

	typeRec := httptest.NewRecorder()
	typeBody := fmt.Sprintf(`{"note_ids":[%d,%d],"category_id":%d}`, aID, bID, targetCat)
	srv.handleNoteDetail(typeRec, httptest.NewRequest(http.MethodPost, "/api/notes/batch/type", strings.NewReader(typeBody)))
	if typeRec.Code != http.StatusOK {
		t.Fatalf("expected batch/type 200, got %d body=%s", typeRec.Code, typeRec.Body.String())
	}
	var typeResp struct {
		Data struct {
			UpdatedCount int `json:"updated_count"`
		} `json:"data"`
	}
	if err := json.Unmarshal(typeRec.Body.Bytes(), &typeResp); err != nil {
		t.Fatal(err)
	}
	if typeResp.Data.UpdatedCount != 2 {
		t.Fatalf("expected updated_count 2, got %d", typeResp.Data.UpdatedCount)
	}
	assertNoteIntColumn(t, db, aID, "category_id", targetCat)
	assertNoteIntColumn(t, db, bID, "category_id", targetCat)

	tagsRec := httptest.NewRecorder()
	tagsBody := fmt.Sprintf(`{"note_ids":[%d,%d],"tags":["batchx","batchy"],"mode":"append"}`, aID, bID)
	srv.handleNoteDetail(tagsRec, httptest.NewRequest(http.MethodPost, "/api/notes/batch/tags", strings.NewReader(tagsBody)))
	if tagsRec.Code != http.StatusOK {
		t.Fatalf("expected batch/tags 200, got %d body=%s", tagsRec.Code, tagsRec.Body.String())
	}
	var tagsResp struct {
		Data struct {
			AffectedNotes int    `json:"affected_notes"`
			TagsAdded     int    `json:"tags_added"`
			Mode          string `json:"mode"`
		} `json:"data"`
	}
	if err := json.Unmarshal(tagsRec.Body.Bytes(), &tagsResp); err != nil {
		t.Fatal(err)
	}
	if tagsResp.Data.AffectedNotes != 2 || tagsResp.Data.Mode != "append" || tagsResp.Data.TagsAdded == 0 {
		t.Fatalf("unexpected batch/tags response: %+v", tagsResp.Data)
	}
	assertTableCount(t, db, "Note_Tags", aID, 2)
	assertTableCount(t, db, "Note_Tags", bID, 2)
}

// TestTagsMergeHandlerTransfersNotesAndDeletesSourceTags locks tags/merge,
// previously only covered by Python-oracle parity. See
// docs/T053-test-disposition-plan.md §E.
func TestTagsMergeHandlerTransfersNotesAndDeletesSourceTags(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	srv := &server{db: db, runtime: runtimeConfig{enableTagWrite: true}}
	noteID := insertSearchNote(t, db, "Merge Note", "mergecontent", "", 1)
	for _, name := range []string{"src-one", "src-two", "merge-target"} {
		if _, err := db.Exec("INSERT INTO Tags (name) VALUES (?)", name); err != nil {
			t.Fatal(err)
		}
	}
	srcOne := tagIDByName(t, db, "src-one")
	srcTwo := tagIDByName(t, db, "src-two")
	target := tagIDByName(t, db, "merge-target")
	if _, err := db.Exec("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", noteID, srcOne); err != nil {
		t.Fatal(err)
	}

	mergeRec := httptest.NewRecorder()
	mergeBody := fmt.Sprintf(`{"source_tag_ids":[%d,%d],"target_tag_id":%d}`, srcOne, srcTwo, target)
	srv.handleTagDetail(mergeRec, httptest.NewRequest(http.MethodPost, "/api/tags/merge", strings.NewReader(mergeBody)))
	if mergeRec.Code != http.StatusOK {
		t.Fatalf("expected merge 200, got %d body=%s", mergeRec.Code, mergeRec.Body.String())
	}
	var mergeResp struct {
		Data struct {
			MergedCount int `json:"merged_count"`
		} `json:"data"`
	}
	if err := json.Unmarshal(mergeRec.Body.Bytes(), &mergeResp); err != nil {
		t.Fatal(err)
	}
	if mergeResp.Data.MergedCount != 2 {
		t.Fatalf("expected merged_count 2, got %d", mergeResp.Data.MergedCount)
	}
	for _, id := range []int{srcOne, srcTwo} {
		var count int
		if err := db.QueryRow("SELECT COUNT(*) FROM Tags WHERE id = ?", id).Scan(&count); err != nil {
			t.Fatal(err)
		}
		if count != 0 {
			t.Fatalf("source tag %d should be deleted after merge", id)
		}
	}
	var hasTarget int
	if err := db.QueryRow("SELECT COUNT(*) FROM Note_Tags WHERE note_id = ? AND tag_id = ?", noteID, target).Scan(&hasTarget); err != nil {
		t.Fatal(err)
	}
	if hasTarget != 1 {
		t.Fatalf("note should carry target tag after merge, got %d", hasTarget)
	}
}

// TestNotesHistoryListAndDeleteHandlers locks history list/delete, previously
// only covered by Python-oracle parity. See docs/T053-test-disposition-plan.md §E.
func TestNotesHistoryListAndDeleteHandlers(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	srv := &server{db: db, runtime: runtimeConfig{enableNotesWrite: true}}
	noteID := insertSearchNote(t, db, "History Note", "historycontent", "", 1)
	for i := 0; i < 2; i++ {
		if _, err := db.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, ?, ?)", noteID, fmt.Sprintf("old %d", i), "history"); err != nil {
			t.Fatal(err)
		}
	}

	listRec := httptest.NewRecorder()
	srv.handleNoteDetail(listRec, httptest.NewRequest(http.MethodGet, fmt.Sprintf("/api/notes/%d/history", noteID), nil))
	if listRec.Code != http.StatusOK {
		t.Fatalf("expected history list 200, got %d body=%s", listRec.Code, listRec.Body.String())
	}
	var listResp struct {
		Data struct {
			Total   int              `json:"total"`
			History []map[string]any `json:"history"`
		} `json:"data"`
	}
	if err := json.Unmarshal(listRec.Body.Bytes(), &listResp); err != nil {
		t.Fatal(err)
	}
	if listResp.Data.Total != 2 || len(listResp.Data.History) != 2 {
		t.Fatalf("expected 2 history rows, got total=%d len=%d", listResp.Data.Total, len(listResp.Data.History))
	}

	delRec := httptest.NewRecorder()
	srv.handleNoteDetail(delRec, httptest.NewRequest(http.MethodDelete, fmt.Sprintf("/api/notes/%d/history", noteID), nil))
	if delRec.Code != http.StatusOK {
		t.Fatalf("expected history delete 200, got %d body=%s", delRec.Code, delRec.Body.String())
	}
	var delResp struct {
		Data struct {
			DeletedCount int `json:"deleted_count"`
		} `json:"data"`
	}
	if err := json.Unmarshal(delRec.Body.Bytes(), &delResp); err != nil {
		t.Fatal(err)
	}
	if delResp.Data.DeletedCount != 2 {
		t.Fatalf("expected deleted_count 2, got %d", delResp.Data.DeletedCount)
	}
	assertTableCount(t, db, "Note_History", noteID, 0)
}

// TestCSRFProtectMiddleware locks the Go Origin/Referer CSRF guard ported from
// the legacy Flask csrf_protect. Closes the 5th audited security-parity gap.
func TestCSRFProtectMiddleware(t *testing.T) {
	called := false
	handler := csrfProtect(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	}))
	do := func(method, host, origin, referer string) *httptest.ResponseRecorder {
		called = false
		req := httptest.NewRequest(method, "/api/notes", nil)
		req.Host = host
		if origin != "" {
			req.Header.Set("Origin", origin)
		}
		if referer != "" {
			req.Header.Set("Referer", referer)
		}
		rec := httptest.NewRecorder()
		handler.ServeHTTP(rec, req)
		return rec
	}

	cases := []struct {
		name              string
		method, host      string
		origin, referer   string
		wantCode          int
		wantHandlerCalled bool
	}{
		{"same-origin POST", http.MethodPost, "127.0.0.1:5004", "http://127.0.0.1:5004", "", http.StatusOK, true},
		{"localhost<->127 swap", http.MethodPost, "127.0.0.1:5004", "http://localhost:5004", "", http.StatusOK, true},
		{"cross-origin POST blocked", http.MethodPost, "127.0.0.1:5004", "http://evil.example", "", http.StatusForbidden, false},
		{"anonymous POST (curl/MCP)", http.MethodPost, "127.0.0.1:5004", "", "", http.StatusOK, true},
		{"cross-origin GET is safe", http.MethodGet, "127.0.0.1:5004", "http://evil.example", "", http.StatusOK, true},
		{"same-origin referer DELETE", http.MethodDelete, "prism.local", "", "https://prism.local/app", http.StatusOK, true},
		{"cross-origin referer DELETE blocked", http.MethodDelete, "prism.local", "", "https://evil.example/x", http.StatusForbidden, false},
		{"vite dev origin", http.MethodPost, "127.0.0.1:5004", "http://localhost:5173", "", http.StatusOK, true},
	}
	for _, tc := range cases {
		rec := do(tc.method, tc.host, tc.origin, tc.referer)
		if rec.Code != tc.wantCode {
			t.Fatalf("%s: code=%d want %d body=%s", tc.name, rec.Code, tc.wantCode, rec.Body.String())
		}
		if called != tc.wantHandlerCalled {
			t.Fatalf("%s: handler called=%v want %v", tc.name, called, tc.wantHandlerCalled)
		}
	}
}
