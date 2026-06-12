package main

import (
	"bytes"
	"context"
	"crypto/md5"
	"database/sql"
	"embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"image"
	"image/draw"
	_ "image/gif"
	_ "image/jpeg"
	_ "image/png"
	"io"
	"io/fs"
	"log"
	"math"
	"mime"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode"

	webp "github.com/skrashevich/go-webp"
	_ "modernc.org/sqlite"
)

const expectedSchemaVersion = 16
const sqliteBusyTimeoutMS = 5000
const sqlitePragmaQueryOnlyOn = "PRAGMA query_only = ON"
const sqlitePragmaQueryOnlyOff = "PRAGMA query_only = OFF"
const maxAttachmentFileBytes int64 = 1048576
const maxAttachmentScanFiles = 200
const maxAttachmentScanBytes int64 = 5242880
const maxAttachmentScanDuration = 250 * time.Millisecond
const maxUploadFileBytes int64 = 5 * 1024 * 1024
const thumbnailMaxWidth = 500
const thumbnailWebPQuality float32 = 80
const uploadURLTimeout = 30 * time.Second

//go:embed web/dist/*
var embeddedDist embed.FS

var (
	errUploadURLSSRF                               = errors.New("upload URL resolves to a private or reserved IP address")
	uploadURLResolveHost                           = defaultUploadURLResolveHost
	uploadURLTransport           http.RoundTripper = http.DefaultTransport
	encodeUploadThumbnail                          = encodeThumbnailWebP
	uploadNow                                      = time.Now
	staticUploadReferencePattern                   = regexp.MustCompile(`/static/uploads/([^[:space:])\]"'>]+)`)
)

type server struct {
	db      *sql.DB
	runtime runtimeConfig
}

type runtimeConfig struct {
	addr                     string
	dbPath                   string
	dataDir                  string
	uploadsDir               string
	attachmentsDir           string
	logsDir                  string
	backupsDir               string
	configDir                string
	enableTagWrite           bool
	enableCategoryWrite      bool
	enableNotesWrite         bool
	enableAttachmentTextRead bool
	enableAttachmentRawRead  bool
	enableAttachmentWrite    bool
	enableUploadWrite        bool
	enableThumbnailWrite     bool
	enableUploadURLWrite     bool
	freshDBInitNeeded        bool
	migrationsApplied        int
	migrationBackupPath      string
	sqliteQueryOnly          bool
}

type sqliteConnectionOwner struct {
	db            *sql.DB
	writeEnabled  bool
	journalMode   string
	busyTimeoutMS int
	queryOnly     bool
}

type response map[string]any

type tagRef struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

type noteImageReference struct {
	ID         int
	Content    sql.NullString
	CoverImage sql.NullString
}

func main() {
	dbPath := flag.String("db", os.Getenv("PRISM_GO_DB"), "path to a copied Prism SQLite database")
	addr := flag.String("addr", envDefault("PRISM_GO_ADDR", "127.0.0.1:5001"), "listen address")
	dataDir := flag.String("data-dir", os.Getenv("PRISM_GO_DATA_DIR"), "external Prism user data directory")
	enableTagWrite := flag.Bool("enable-tag-write", envBool("PRISM_GO_ENABLE_TAG_WRITE"), "enable local/copied-DB tags update/delete/merge parity candidate")
	enableCategoryWrite := flag.Bool("enable-category-write", envBool("PRISM_GO_ENABLE_CATEGORY_WRITE"), "enable local/copied-DB categories create/update/delete parity candidate")
	enableNotesWrite := flag.Bool("enable-notes-write", envBool("PRISM_GO_ENABLE_NOTES_WRITE"), "enable local/copied-DB notes write/actions/history/batch parity candidate")
	enableAttachmentTextRead := flag.Bool("enable-attachment-text-read", envBool("PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ"), "enable local/copied-DB GET /api/attachments/<id> text JSON parity candidate")
	enableAttachmentRawRead := flag.Bool("enable-attachment-raw-read", envBool("PRISM_GO_ENABLE_ATTACHMENT_RAW_READ"), "enable local/copied-files GET /api/attachments/<id>?raw=true raw/binary serving parity candidate")
	enableAttachmentWrite := flag.Bool("enable-attachment-write", envBool("PRISM_GO_ENABLE_ATTACHMENT_WRITE"), "enable local/copied-DB-and-files attachment metadata upload/delete parity candidate")
	enableUploadWrite := flag.Bool("enable-upload-write", envBool("PRISM_GO_ENABLE_UPLOAD_WRITE"), "enable local/copied-data POST /api/upload parity candidate")
	enableThumbnailWrite := flag.Bool("enable-thumbnail-write", envBool("PRISM_GO_ENABLE_THUMBNAIL_WRITE"), "enable local/copied-data POST /api/upload thumbnail parity candidate")
	enableUploadURLWrite := flag.Bool("enable-upload-url-write", envBool("PRISM_GO_ENABLE_UPLOAD_URL_WRITE"), "enable local/copied-data POST /api/upload/url parity candidate")
	thumbnailInput := flag.String("thumbnail-input", "", "encode this local image file as a Prism WebP thumbnail and exit")
	thumbnailOutput := flag.String("thumbnail-output", "", "thumbnail output path for --thumbnail-input")
	flag.Parse()

	if *thumbnailInput != "" || *thumbnailOutput != "" {
		if err := runThumbnailCLI(*thumbnailInput, *thumbnailOutput); err != nil {
			log.Fatal(err)
		}
		return
	}

	cfg, err := resolveRuntimeConfig(*addr, *dbPath, *dataDir, *enableTagWrite, *enableCategoryWrite, *enableNotesWrite, *enableAttachmentTextRead, *enableThumbnailWrite, *enableUploadURLWrite, *enableAttachmentWrite, *enableAttachmentRawRead, *enableUploadWrite)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("using data dir %s", cfg.dataDir)
	log.Printf("using database %s", cfg.dbPath)

	sqliteOwner, err := openRuntimeSQLite(&cfg)
	if err != nil {
		log.Fatal(err)
	}
	defer sqliteOwner.close()
	cfg.sqliteQueryOnly = sqliteOwner.queryOnly
	db := sqliteOwner.db
	if err := verifySchemaVersion(db, expectedSchemaVersion); err != nil {
		log.Fatal(err)
	}

	srv := &server{db: db, runtime: cfg}
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", srv.handleHealth)
	mux.HandleFunc("/api/test", srv.handleTest)
	mux.HandleFunc("/api/categories", srv.handleCategories)
	mux.HandleFunc("/api/categories/", srv.handleCategoryDetail)
	mux.HandleFunc("/api/tags", srv.handleTags)
	mux.HandleFunc("/api/tags/", srv.handleTagDetail)
	mux.HandleFunc("/api/notes", srv.handleNotes)
	mux.HandleFunc("/api/notes/", srv.handleNoteDetail)
	mux.HandleFunc("/api/attachments/", srv.handleAttachmentDetail)
	mux.HandleFunc("/api/system/migration-status", srv.handleMigrationStatus)
	mux.HandleFunc("/api/upload/url", srv.handleUploadURL)
	mux.HandleFunc("/api/upload", srv.handleUpload)
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

func runThumbnailCLI(inputPath, outputPath string) error {
	if strings.TrimSpace(inputPath) == "" || strings.TrimSpace(outputPath) == "" {
		return errors.New("--thumbnail-input and --thumbnail-output are required together")
	}
	file, err := os.Open(inputPath)
	if err != nil {
		return err
	}
	defer file.Close()
	content, err := io.ReadAll(io.LimitReader(file, maxUploadFileBytes+1))
	if err != nil {
		return err
	}
	if int64(len(content)) > maxUploadFileBytes {
		return fmt.Errorf("image too large: maximum size is %d bytes", maxUploadFileBytes)
	}
	img, _, err := image.Decode(bytes.NewReader(content))
	if err != nil {
		return err
	}
	thumb, err := encodeThumbnailWebP(img)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(outputPath), 0755); err != nil {
		return err
	}
	tmpPath := outputPath + ".tmp"
	if err := os.WriteFile(tmpPath, thumb, 0644); err != nil {
		return err
	}
	_ = os.Remove(outputPath)
	return os.Rename(tmpPath, outputPath)
}

func resolveRuntimeConfig(addr, dbPath, dataDir string, enableTagWrite, enableCategoryWrite, enableNotesWrite, enableAttachmentTextRead, enableThumbnailWrite, enableUploadURLWrite bool, optionalAttachmentWrite ...bool) (runtimeConfig, error) {
	if strings.TrimSpace(dbPath) == "" {
		return runtimeConfig{}, errors.New("database path is required; pass --db or PRISM_GO_DB")
	}
	if strings.TrimSpace(dataDir) == "" {
		return runtimeConfig{}, errors.New("data directory is required; pass --data-dir or PRISM_GO_DATA_DIR")
	}
	enableAttachmentWrite := len(optionalAttachmentWrite) > 0 && optionalAttachmentWrite[0]
	enableAttachmentRawRead := len(optionalAttachmentWrite) > 1 && optionalAttachmentWrite[1]
	enableUploadWrite := len(optionalAttachmentWrite) > 2 && optionalAttachmentWrite[2]
	absData, err := filepath.Abs(dataDir)
	if err != nil {
		return runtimeConfig{}, err
	}
	absData = filepath.Clean(absData)
	if err := os.MkdirAll(absData, 0755); err != nil {
		return runtimeConfig{}, err
	}

	absDB, err := resolveDataRootPath(absData, dbPath)
	if err != nil {
		return runtimeConfig{}, fmt.Errorf("database path escapes data directory: %w", err)
	}
	if filepath.Base(absDB) == "knowledge.db" && os.Getenv("PRISM_GO_ALLOW_PROD_DB") != "1" {
		return runtimeConfig{}, fmt.Errorf("refusing to open production-like database %s; use a copied *_test.db or *_dev.db", absDB)
	}
	if (enableUploadWrite || enableThumbnailWrite || enableUploadURLWrite) && filepath.Base(absDB) == "knowledge.db" && os.Getenv("PRISM_GO_ALLOW_PROD_UPLOADS") != "1" {
		return runtimeConfig{}, fmt.Errorf("refusing to enable upload writes with production-like database %s; use copied data or set PRISM_GO_ALLOW_PROD_UPLOADS=1", absDB)
	}
	freshDBInitNeeded := false
	if info, err := os.Stat(absDB); err != nil {
		if !os.IsNotExist(err) {
			return runtimeConfig{}, err
		}
		if !isSubpath(absDB, absData) {
			return runtimeConfig{}, fmt.Errorf("missing database path must be inside data directory for fresh init: %s", absDB)
		}
		if err := os.MkdirAll(filepath.Dir(absDB), 0755); err != nil {
			return runtimeConfig{}, err
		}
		freshDBInitNeeded = true
	} else if info.IsDir() {
		return runtimeConfig{}, fmt.Errorf("database path is a directory: %s", absDB)
	}

	uploadsDir, err := ensureDataSubdir(absData, "static", "uploads")
	if err != nil {
		return runtimeConfig{}, err
	}
	attachmentsDir, err := ensureDataSubdir(absData, "docs", "attachments")
	if err != nil {
		return runtimeConfig{}, err
	}
	logsDir, err := ensureDataSubdir(absData, "logs")
	if err != nil {
		return runtimeConfig{}, err
	}
	backupsDir, err := ensureDataSubdir(absData, "backups")
	if err != nil {
		return runtimeConfig{}, err
	}
	configDir, err := ensureDataSubdir(absData, "config")
	if err != nil {
		return runtimeConfig{}, err
	}

	return runtimeConfig{
		addr:                     addr,
		dbPath:                   absDB,
		dataDir:                  absData,
		uploadsDir:               uploadsDir,
		attachmentsDir:           attachmentsDir,
		logsDir:                  logsDir,
		backupsDir:               backupsDir,
		configDir:                configDir,
		enableTagWrite:           enableTagWrite,
		enableCategoryWrite:      enableCategoryWrite,
		enableNotesWrite:         enableNotesWrite,
		enableAttachmentTextRead: enableAttachmentTextRead,
		enableAttachmentRawRead:  enableAttachmentRawRead,
		enableAttachmentWrite:    enableAttachmentWrite,
		enableUploadWrite:        enableUploadWrite,
		enableThumbnailWrite:     enableThumbnailWrite,
		enableUploadURLWrite:     enableUploadURLWrite,
		freshDBInitNeeded:        freshDBInitNeeded,
		sqliteQueryOnly:          !(enableTagWrite || enableCategoryWrite || enableNotesWrite || enableAttachmentWrite),
	}, nil
}

func resolveDataRootPath(dataDir, candidate string) (string, error) {
	if strings.TrimSpace(candidate) == "" {
		return "", errors.New("path is required")
	}
	if filepath.IsAbs(candidate) {
		abs, err := filepath.Abs(candidate)
		if err != nil {
			return "", err
		}
		return filepath.Clean(abs), nil
	}
	candidate = filepath.Clean(candidate)
	if candidate == "." || strings.HasPrefix(candidate, ".."+string(filepath.Separator)) || candidate == ".." {
		return "", fmt.Errorf("relative path %q is outside data directory", candidate)
	}
	abs := filepath.Join(dataDir, candidate)
	if !isSubpath(abs, dataDir) {
		return "", fmt.Errorf("resolved path %q is outside %q", abs, dataDir)
	}
	return filepath.Clean(abs), nil
}

func ensureDataSubdir(dataDir string, parts ...string) (string, error) {
	rel := filepath.Join(parts...)
	abs, err := resolveDataRootPath(dataDir, rel)
	if err != nil {
		return "", err
	}
	if !isSubpath(abs, dataDir) {
		return "", fmt.Errorf("resolved path %q is outside %q", abs, dataDir)
	}
	if err := os.MkdirAll(abs, 0755); err != nil {
		return "", err
	}
	return abs, nil
}

func (cfg runtimeConfig) hasWriteCandidate() bool {
	return cfg.enableTagWrite || cfg.enableCategoryWrite || cfg.enableNotesWrite || cfg.enableAttachmentWrite
}

func openRuntimeSQLite(cfg *runtimeConfig) (*sqliteConnectionOwner, error) {
	if cfg == nil {
		return nil, errors.New("runtime config is required")
	}
	enableWrites := cfg.hasWriteCandidate() || cfg.freshDBInitNeeded
	owner, err := openSQLiteOwner(cfg.dbPath, enableWrites)
	if err != nil {
		return nil, err
	}
	if !cfg.freshDBInitNeeded {
		status, err := migrationStatus(owner.db)
		if err != nil {
			_ = owner.close()
			return nil, err
		}
		if len(status.Pending) == 0 {
			cfg.sqliteQueryOnly = owner.queryOnly
			return owner, nil
		}
		if err := owner.close(); err != nil {
			return nil, err
		}
		backupPath, err := backupSQLiteBeforeMigration(*cfg, status.CurrentVersion, status.LatestVersion)
		if err != nil {
			return nil, err
		}
		cfg.migrationBackupPath = backupPath
		writeOwner, err := openSQLiteOwner(cfg.dbPath, true)
		if err != nil {
			return nil, err
		}
		result, err := runExistingDBMigrations(writeOwner, migrationDefinitions)
		if err != nil {
			_ = writeOwner.close()
			return nil, fmt.Errorf("migration failed after backup %s: %w", backupPath, err)
		}
		cfg.migrationsApplied = result.Applied
		if cfg.hasWriteCandidate() {
			cfg.sqliteQueryOnly = writeOwner.queryOnly
			return writeOwner, nil
		}
		if err := writeOwner.close(); err != nil {
			return nil, err
		}
		owner, err = openSQLiteOwner(cfg.dbPath, false)
		if err != nil {
			return nil, err
		}
		cfg.sqliteQueryOnly = owner.queryOnly
		return owner, nil
	}
	if err := initializeFreshDatabase(owner); err != nil {
		_ = owner.close()
		return nil, err
	}
	if cfg.hasWriteCandidate() {
		cfg.sqliteQueryOnly = owner.queryOnly
		return owner, nil
	}
	if err := owner.close(); err != nil {
		return nil, err
	}
	owner, err = openSQLiteOwner(cfg.dbPath, false)
	if err != nil {
		return nil, err
	}
	cfg.sqliteQueryOnly = owner.queryOnly
	return owner, nil
}

func openSQLiteOwner(dbPath string, enableWrites bool) (*sqliteConnectionOwner, error) {
	db, err := sql.Open("sqlite", sqliteDSN(dbPath, enableWrites))
	if err != nil {
		return nil, err
	}
	var busyTimeout int
	if err := db.QueryRow("PRAGMA busy_timeout").Scan(&busyTimeout); err != nil {
		db.Close()
		return nil, err
	}
	if busyTimeout != sqliteBusyTimeoutMS {
		db.Close()
		return nil, fmt.Errorf("failed to set SQLite busy_timeout: got %d want %d", busyTimeout, sqliteBusyTimeoutMS)
	}

	var journalMode string
	if err := db.QueryRow("PRAGMA journal_mode").Scan(&journalMode); err != nil {
		db.Close()
		return nil, err
	}
	journalMode = strings.ToLower(journalMode)
	if journalMode != "wal" {
		db.Close()
		return nil, fmt.Errorf("failed to enable SQLite WAL mode: got %q", journalMode)
	}

	queryOnly := !enableWrites
	var actualQueryOnly int
	if err := db.QueryRow("PRAGMA query_only").Scan(&actualQueryOnly); err != nil {
		db.Close()
		return nil, err
	}
	expectedQueryOnly := 0
	if queryOnly {
		expectedQueryOnly = 1
	}
	if actualQueryOnly != expectedQueryOnly {
		db.Close()
		return nil, fmt.Errorf("failed to set SQLite query_only mode: got %d want %d", actualQueryOnly, expectedQueryOnly)
	}

	return &sqliteConnectionOwner{
		db:            db,
		writeEnabled:  enableWrites,
		journalMode:   journalMode,
		busyTimeoutMS: busyTimeout,
		queryOnly:     queryOnly,
	}, nil
}

func sqliteDSN(dbPath string, enableWrites bool) string {
	values := url.Values{}
	values.Add("_pragma", fmt.Sprintf("busy_timeout(%d)", sqliteBusyTimeoutMS))
	values.Add("_pragma", "journal_mode(WAL)")
	values.Add("_pragma", "foreign_keys(1)")
	values.Add("_pragma", sqliteQueryOnlyDSNPragma(enableWrites))
	separator := "?"
	if strings.Contains(dbPath, "?") {
		separator = "&"
	}
	return dbPath + separator + values.Encode()
}

func sqliteQueryOnlyDSNPragma(enableWrites bool) string {
	if sqliteQueryOnlyPragma(enableWrites) == sqlitePragmaQueryOnlyOff {
		return "query_only(0)"
	}
	return "query_only(1)"
}

func sqliteQueryOnlyPragma(enableWrites bool) string {
	if enableWrites {
		return sqlitePragmaQueryOnlyOff
	}
	return sqlitePragmaQueryOnlyOn
}

func (owner *sqliteConnectionOwner) close() error {
	if owner == nil || owner.db == nil {
		return nil
	}
	return owner.db.Close()
}

func (owner *sqliteConnectionOwner) withTransaction(fn func(*sql.Tx) error) error {
	if owner == nil || owner.db == nil {
		return errors.New("SQLite connection owner is not open")
	}
	if !owner.writeEnabled {
		return errors.New("SQLite write transaction requires write mode")
	}
	tx, err := owner.db.Begin()
	if err != nil {
		return err
	}
	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback()
		}
	}()
	if err := fn(tx); err != nil {
		return err
	}
	if err := tx.Commit(); err != nil {
		return err
	}
	committed = true
	return nil
}

var migrationBackupNow = time.Now

type migrationRunResult struct {
	Applied      int
	FromVersion  int
	FinalVersion int
}

type migrationStatusSnapshot struct {
	CurrentVersion int
	LatestVersion  int
	Completed      []migrationDefinition
	Pending        []migrationDefinition
}

type sqlQueryer interface {
	Query(query string, args ...any) (*sql.Rows, error)
	QueryRow(query string, args ...any) *sql.Row
}

func backupSQLiteBeforeMigration(cfg runtimeConfig, currentVersion, latestVersion int) (string, error) {
	if strings.TrimSpace(cfg.backupsDir) == "" {
		return "", errors.New("backup directory is required before migration")
	}
	if err := os.MkdirAll(cfg.backupsDir, 0755); err != nil {
		return "", err
	}
	timestamp := migrationBackupNow().Format("20060102_150405_000000000")
	backupName := fmt.Sprintf("prism_go_pre_migrate_v%d_to_v%d_%s.db", currentVersion, latestVersion, timestamp)
	backupPath := filepath.Join(cfg.backupsDir, backupName)
	if !isSubpath(backupPath, cfg.backupsDir) {
		return "", fmt.Errorf("backup path %q escapes backup directory", backupPath)
	}
	if err := copyFileExclusive(cfg.dbPath, backupPath); err != nil {
		return "", err
	}
	for _, suffix := range []string{"-wal", "-shm"} {
		if err := copyFileIfExists(cfg.dbPath+suffix, backupPath+suffix); err != nil {
			return "", err
		}
	}
	return backupPath, nil
}

func copyFileIfExists(src, dst string) error {
	if _, err := os.Stat(src); err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	return copyFileExclusive(src, dst)
}

func copyFileExclusive(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	defer out.Close()
	if _, err := io.Copy(out, in); err != nil {
		return err
	}
	return out.Sync()
}

func runExistingDBMigrations(owner *sqliteConnectionOwner, definitions []migrationDefinition) (migrationRunResult, error) {
	result := migrationRunResult{}
	if owner == nil {
		return result, errors.New("SQLite connection owner is required for migrations")
	}
	if len(definitions) == 0 {
		return result, errors.New("migration definitions are required")
	}
	err := owner.withTransaction(func(tx *sql.Tx) error {
		if err := ensureSchemaMeta(tx); err != nil {
			return err
		}
		current, err := schemaMetaVersion(tx)
		if err != nil {
			return err
		}
		if current == 0 {
			detected, err := detectExistingSchemaVersion(tx)
			if err != nil {
				return err
			}
			if detected > 0 {
				if _, err := tx.Exec("UPDATE Schema_Meta SET value = ? WHERE key = 'schema_version'", strconv.Itoa(detected)); err != nil {
					return err
				}
				current = detected
			}
		}
		result.FromVersion = current
		result.FinalVersion = current
		for _, migration := range definitions {
			if migration.Version <= current {
				continue
			}
			for _, statement := range migration.Statements {
				sqlClean := strings.TrimSpace(statement)
				if sqlClean == "" {
					continue
				}
				if _, err := tx.Exec(sqlClean); err != nil {
					if skippableMigrationError(err) {
						continue
					}
					return fmt.Errorf("migration v%03d %s failed: %w", migration.Version, migration.Name, err)
				}
			}
			if _, err := tx.Exec("UPDATE Schema_Meta SET value = ? WHERE key = 'schema_version'", strconv.Itoa(migration.Version)); err != nil {
				return err
			}
			result.Applied++
			result.FinalVersion = migration.Version
			current = migration.Version
		}
		return nil
	})
	return result, err
}

func ensureSchemaMeta(tx *sql.Tx) error {
	if _, err := tx.Exec(`
		CREATE TABLE IF NOT EXISTS Schema_Meta (
			key TEXT PRIMARY KEY,
			value TEXT NOT NULL
		)`); err != nil {
		return err
	}
	_, err := tx.Exec("INSERT OR IGNORE INTO Schema_Meta (key, value) VALUES ('schema_version', '0')")
	return err
}

func migrationStatus(db *sql.DB) (migrationStatusSnapshot, error) {
	current, err := currentMigrationVersion(db)
	if err != nil {
		return migrationStatusSnapshot{}, err
	}
	status := migrationStatusSnapshot{
		CurrentVersion: current,
		LatestVersion:  latestMigrationVersion(),
		Completed:      []migrationDefinition{},
		Pending:        []migrationDefinition{},
	}
	for _, migration := range migrationDefinitions {
		if migration.Version > current {
			status.Pending = append(status.Pending, migration)
		} else {
			status.Completed = append(status.Completed, migration)
		}
	}
	return status, nil
}

func currentMigrationVersion(q sqlQueryer) (int, error) {
	current, err := schemaMetaVersion(q)
	if err != nil {
		if !missingSchemaMetaError(err) {
			return 0, err
		}
		current = 0
	}
	if current == 0 {
		detected, err := detectExistingSchemaVersion(q)
		if err != nil {
			return 0, err
		}
		if detected > 0 {
			return detected, nil
		}
	}
	return current, nil
}

func schemaMetaVersion(q sqlQueryer) (int, error) {
	var raw string
	if err := q.QueryRow("SELECT value FROM Schema_Meta WHERE key = 'schema_version'").Scan(&raw); err != nil {
		return 0, err
	}
	version, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("invalid schema_version %q: %w", raw, err)
	}
	return version, nil
}

func detectExistingSchemaVersion(q sqlQueryer) (int, error) {
	version := 0
	checks := []struct {
		column  string
		version int
	}{
		{"is_pinned", 1},
		{"cover_position", 2},
		{"editor_layout", 3},
		{"is_archived", 4},
		{"sort_order", 5},
		{"category_id", 7},
	}
	for _, check := range checks {
		exists, err := columnExists(q, "Notes", check.column)
		if err != nil {
			return 0, err
		}
		if exists && check.version > version {
			version = check.version
		}
	}
	return version, nil
}

func columnExists(q sqlQueryer, table, column string) (bool, error) {
	rows, err := q.Query("PRAGMA table_info(" + table + ")")
	if err != nil {
		if missingSchemaObjectError(err) {
			return false, nil
		}
		return false, err
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var name, columnType string
		var notNull int
		var defaultValue sql.NullString
		var pk int
		if err := rows.Scan(&cid, &name, &columnType, &notNull, &defaultValue, &pk); err != nil {
			return false, err
		}
		if name == column {
			return true, nil
		}
	}
	return false, rows.Err()
}

func latestMigrationVersion() int {
	latest := 0
	for _, migration := range migrationDefinitions {
		if migration.Version > latest {
			latest = migration.Version
		}
	}
	return latest
}

func skippableMigrationError(err error) bool {
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "duplicate column name") || strings.Contains(message, "no such column")
}

func missingSchemaMetaError(err error) bool {
	return errors.Is(err, sql.ErrNoRows) || missingSchemaObjectError(err)
}

func missingSchemaObjectError(err error) bool {
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "no such table") || strings.Contains(message, "no such column")
}

func initializeFreshDatabase(owner *sqliteConnectionOwner) error {
	if owner == nil {
		return errors.New("SQLite connection owner is required for fresh DB init")
	}
	return owner.withTransaction(func(tx *sql.Tx) error {
		for index, statement := range freshSchemaStatements {
			if _, err := tx.Exec(statement); err != nil {
				return fmt.Errorf("fresh schema statement %d failed: %w", index+1, err)
			}
		}
		if err := seedDefaultCategories(tx); err != nil {
			return err
		}
		if err := seedWelcomeNote(tx); err != nil {
			return err
		}
		return nil
	})
}

var freshSchemaStatements = []string{
	`CREATE TABLE Notes (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		content TEXT NOT NULL,
		remarks TEXT,
		cover_image TEXT,
		cover_position TEXT DEFAULT 'top',
		editor_layout TEXT DEFAULT 'single',
		is_pinned BOOLEAN NOT NULL DEFAULT 0,
		is_archived BOOLEAN NOT NULL DEFAULT 0,
		sort_order INTEGER,
		category_id INTEGER REFERENCES Categories(id),
		parent_id INTEGER REFERENCES Notes(id),
		prompt_params TEXT,
		created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
	)`,
	`CREATE INDEX idx_notes_updated_at ON Notes(updated_at DESC)`,
	`CREATE INDEX idx_notes_category_id ON Notes(category_id)`,
	`CREATE INDEX idx_notes_sort_order ON Notes(sort_order)`,
	`CREATE INDEX idx_notes_is_archived ON Notes(is_archived)`,
	`CREATE INDEX idx_notes_parent_id ON Notes(parent_id)`,
	`CREATE TABLE Categories (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL UNIQUE,
		icon TEXT,
		sort_order INTEGER NOT NULL DEFAULT 0,
		is_default BOOLEAN NOT NULL DEFAULT 0
	)`,
	`CREATE TABLE Tags (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL UNIQUE COLLATE NOCASE
	)`,
	`CREATE UNIQUE INDEX idx_tags_name ON Tags(name COLLATE NOCASE)`,
	`CREATE TABLE Note_Tags (
		note_id INTEGER NOT NULL,
		tag_id INTEGER NOT NULL,
		PRIMARY KEY (note_id, tag_id),
		FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE,
		FOREIGN KEY (tag_id) REFERENCES Tags(id) ON DELETE CASCADE
	)`,
	`CREATE TABLE Source_Urls (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		note_id INTEGER NOT NULL,
		url TEXT NOT NULL,
		FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
	)`,
	`CREATE INDEX idx_source_urls_note_id ON Source_Urls(note_id)`,
	`CREATE TABLE Note_History (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		note_id INTEGER NOT NULL,
		content TEXT NOT NULL,
		diff_summary TEXT,
		created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
	)`,
	`CREATE INDEX idx_note_history_note_id ON Note_History(note_id)`,
	`CREATE TABLE Note_Attachments (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		note_id INTEGER NOT NULL,
		file_path TEXT NOT NULL,
		file_type TEXT DEFAULT 'md',
		title TEXT,
		size_bytes INTEGER,
		is_auto_extracted INTEGER DEFAULT 0,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
	)`,
	`CREATE INDEX idx_attachments_note_id ON Note_Attachments(note_id)`,
	`CREATE TABLE Schema_Meta (
		key TEXT PRIMARY KEY,
		value TEXT NOT NULL
	)`,
	`INSERT INTO Schema_Meta (key, value) VALUES ('schema_version', '16')`,
	`CREATE VIRTUAL TABLE Notes_FTS USING fts5(
		title,
		content,
		content='Notes',
		content_rowid='id'
	)`,
	`CREATE TRIGGER notes_ai AFTER INSERT ON Notes BEGIN
		INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
	END`,
	`CREATE TRIGGER notes_ad AFTER DELETE ON Notes BEGIN
		INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
	END`,
	`CREATE TRIGGER notes_au AFTER UPDATE ON Notes BEGIN
		INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
		INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
	END`,
}

type categorySeed struct {
	name      string
	icon      string
	sortOrder int
	isDefault int
}

var defaultCategorySeeds = []categorySeed{
	{"提示詞 | Prompt", "🎨", 1, 0},
	{"筆記 | Note", "📝", 2, 1},
	{"教學 | Tutorial", "📚", 3, 0},
	{"資料 | Data", "💾", 4, 0},
	{"靈感 | Inspiration", "💡", 5, 0},
}

const welcomeNoteTitle = "👋 歡迎使用 Prism"

const welcomeNoteContent = `# 歡迎使用 Prism

這是一個本地運行的個人知識庫與 AI 提示詞管理工具。

## 快速上手

- **新增筆記**：點擊左上角「新增筆記」按鈕。
- **Prompt Builder**：點擊側邊欄「Prompt Builder」建立結構化提示詞。
- **搜尋**：支援全文檢索，輸入關鍵字即可快速找到筆記。

## Markdown 支援

支援標準 Markdown 語法，例如：

- **粗體**、*斜體*
- [連結](https://example.com)
- 程式碼區塊
- 引用

## 關於資料

所有資料皆儲存在本地端的 ` + "`knowledge.db`" + ` 資料庫中，您可以隨時備份此檔案。
`

func seedDefaultCategories(tx *sql.Tx) error {
	for _, seed := range defaultCategorySeeds {
		if _, err := tx.Exec(
			`INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES (?, ?, ?, ?)`,
			seed.name,
			seed.icon,
			seed.sortOrder,
			seed.isDefault,
		); err != nil {
			return fmt.Errorf("seed default category %q failed: %w", seed.name, err)
		}
	}
	return nil
}

func seedWelcomeNote(tx *sql.Tx) error {
	var count int
	if err := tx.QueryRow("SELECT COUNT(*) FROM Notes").Scan(&count); err != nil {
		return err
	}
	if count != 0 {
		return nil
	}
	var categoryID int
	if err := tx.QueryRow("SELECT id FROM Categories WHERE name LIKE '%教學%' LIMIT 1").Scan(&categoryID); err != nil {
		categoryID = 3
	}
	result, err := tx.Exec(
		`INSERT INTO Notes (title, content, category_id, remarks, created_at, updated_at)
		 VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)`,
		welcomeNoteTitle,
		welcomeNoteContent,
		categoryID,
		"系統自動生成",
	)
	if err != nil {
		return err
	}
	noteID, err := result.LastInsertId()
	if err != nil {
		return err
	}
	if _, err := tx.Exec("INSERT OR IGNORE INTO Tags (name) VALUES ('Welcome')"); err != nil {
		return err
	}
	var tagID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE name = 'Welcome'").Scan(&tagID); err != nil {
		return err
	}
	if _, err := tx.Exec("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", noteID, tagID); err != nil {
		return err
	}
	return nil
}

func openDB(dbPath string, enableWrites bool) (*sql.DB, error) {
	owner, err := openSQLiteOwner(dbPath, enableWrites)
	if err != nil {
		return nil, err
	}
	return owner.db, nil
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

type migrationDefinition struct {
	Version    int
	Name       string
	Statements []string
}

var migrationDefinitions = []migrationDefinition{
	{1, "add_is_pinned", []string{
		"ALTER TABLE Notes ADD COLUMN is_pinned INTEGER DEFAULT 0",
	}},
	{2, "add_cover_position", []string{
		"ALTER TABLE Notes ADD COLUMN cover_position TEXT DEFAULT 'top'",
	}},
	{3, "add_editor_layout", []string{
		"ALTER TABLE Notes ADD COLUMN editor_layout TEXT DEFAULT 'single'",
	}},
	{4, "add_is_archived", []string{
		"ALTER TABLE Notes ADD COLUMN is_archived INTEGER DEFAULT 0",
		"CREATE INDEX IF NOT EXISTS idx_notes_is_archived ON Notes(is_archived)",
	}},
	{5, "add_sort_order", []string{
		"ALTER TABLE Notes ADD COLUMN sort_order INTEGER DEFAULT 0",
		"CREATE INDEX IF NOT EXISTS idx_notes_sort_order ON Notes(sort_order)",
		"UPDATE Notes SET sort_order = id WHERE sort_order = 0 OR sort_order IS NULL",
	}},
	{6, "add_category_id", []string{
		"ALTER TABLE Notes ADD COLUMN category_id INTEGER REFERENCES Categories(id)",
		"CREATE INDEX IF NOT EXISTS idx_notes_category_id ON Notes(category_id)",
	}},
	{7, "populate_category_id", []string{
		`UPDATE Notes SET category_id = (
			SELECT id FROM Categories WHERE name = Notes.type LIMIT 1
		) WHERE category_id IS NULL`,
		`UPDATE Notes SET category_id = (
			SELECT id FROM Categories WHERE is_default = 1 LIMIT 1
		) WHERE category_id IS NULL`,
		`UPDATE Notes SET category_id = (
			SELECT id FROM Categories ORDER BY sort_order LIMIT 1
		) WHERE category_id IS NULL`,
	}},
	{8, "add_note_attachments", []string{
		`CREATE TABLE IF NOT EXISTS Note_Attachments (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			note_id INTEGER NOT NULL,
			file_path TEXT NOT NULL,
			file_type TEXT DEFAULT 'md',
			title TEXT,
			size_bytes INTEGER,
			is_auto_extracted INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
		)`,
		"CREATE INDEX IF NOT EXISTS idx_attachments_note_id ON Note_Attachments(note_id)",
	}},
	{9, "add_text_embedding", []string{
		"ALTER TABLE Notes ADD COLUMN text_embedding BLOB",
		"ALTER TABLE Notes ADD COLUMN embedding_updated_at DATETIME",
	}},
	{10, "add_ai_metadata_and_lineage", []string{
		"ALTER TABLE Notes ADD COLUMN ai_summary TEXT",
		"ALTER TABLE Notes ADD COLUMN ai_tags TEXT",
		"ALTER TABLE Notes ADD COLUMN embedding_status TEXT",
		"ALTER TABLE Notes ADD COLUMN parent_id INTEGER REFERENCES Notes(id)",
		"CREATE INDEX IF NOT EXISTS idx_notes_parent_id ON Notes(parent_id)",
	}},
	{11, "create_embeddings_table", []string{
		`CREATE TABLE IF NOT EXISTS Embeddings (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			resource_type TEXT NOT NULL,
			resource_id INTEGER NOT NULL,
			chunk_index INTEGER DEFAULT 0,
			model_name TEXT NOT NULL,
			vector BLOB NOT NULL,
			content_hash TEXT,
			dimensions INTEGER,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			UNIQUE(resource_type, resource_id, chunk_index)
		)`,
		"CREATE INDEX IF NOT EXISTS idx_embeddings_resource ON Embeddings(resource_type, resource_id)",
	}},
	{12, "kill_notes_type", []string{
		`UPDATE Notes
		SET category_id = (SELECT id FROM Categories WHERE is_default = 1 LIMIT 1)
		WHERE category_id IS NULL`,
		`UPDATE Notes
		SET category_id = (SELECT id FROM Categories ORDER BY sort_order LIMIT 1)
		WHERE category_id IS NULL`,
		"DROP INDEX IF EXISTS idx_notes_type",
		"ALTER TABLE Notes DROP COLUMN type",
	}},
	{13, "create_ai_tasks_table", []string{
		`CREATE TABLE IF NOT EXISTS AI_Tasks (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			task_type TEXT NOT NULL,
			status TEXT NOT NULL DEFAULT 'pending',
			payload TEXT NOT NULL,
			result TEXT,
			retry_count INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
		)`,
		"CREATE INDEX IF NOT EXISTS idx_ai_tasks_status ON AI_Tasks(status)",
		"CREATE INDEX IF NOT EXISTS idx_ai_tasks_type ON AI_Tasks(task_type)",
		"CREATE INDEX IF NOT EXISTS idx_ai_tasks_created ON AI_Tasks(created_at)",
	}},
	{14, "strip_ai_features", []string{
		"ALTER TABLE Notes DROP COLUMN text_embedding",
		"ALTER TABLE Notes DROP COLUMN embedding_updated_at",
		"ALTER TABLE Notes DROP COLUMN ai_summary",
		"ALTER TABLE Notes DROP COLUMN ai_tags",
		"ALTER TABLE Notes DROP COLUMN embedding_status",
		"DROP TABLE IF EXISTS AI_Tasks",
		"DROP TABLE IF EXISTS Embeddings",
		"DROP INDEX IF EXISTS idx_ai_tasks_status",
		"DROP INDEX IF EXISTS idx_ai_tasks_type",
		"DROP INDEX IF EXISTS idx_ai_tasks_created",
		"DROP INDEX IF EXISTS idx_embeddings_resource",
	}},
	{15, "add_prompt_params", []string{
		"ALTER TABLE Notes ADD COLUMN prompt_params TEXT",
	}},
	{16, "normalize_editor_layout", []string{
		"UPDATE Notes SET editor_layout = 'single' WHERE editor_layout IS NULL OR editor_layout = 'full'",
	}},
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
			"uploads_dir":             s.runtime.uploadsDir,
			"attachments_dir":         s.runtime.attachmentsDir,
			"logs_dir":                s.runtime.logsDir,
			"backups_dir":             s.runtime.backupsDir,
			"config_dir":              s.runtime.configDir,
			"schema_version":          version,
			"expected_schema_version": expectedSchemaVersion,
			"sqlite_query_only":       s.runtime.sqliteQueryOnly,
			"fresh_db_initialized":    s.runtime.freshDBInitNeeded,
			"migrations_applied":      s.runtime.migrationsApplied,
			"migration_backup_path":   s.runtime.migrationBackupPath,
			"api_surface":             s.apiSurface(),
		},
	})
}

func (s *server) handleMigrationStatus(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	status, err := migrationStatus(s.db)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	completed := []response{}
	pending := []response{}
	for _, migration := range status.Completed {
		completed = append(completed, response{"version": migration.Version, "name": migration.Name})
	}
	for _, migration := range status.Pending {
		pending = append(pending, response{"version": migration.Version, "name": migration.Name})
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"current_version": status.CurrentVersion,
			"latest_version":  status.LatestVersion,
			"completed":       completed,
			"pending":         pending,
		},
	})
}

func (s *server) apiSurface() string {
	parts := []string{"get-read-only"}
	if s.runtime.enableTagWrite {
		parts = append(parts, "local-tag-write")
	}
	if s.runtime.enableCategoryWrite {
		parts = append(parts, "local-category-write")
	}
	if s.runtime.enableNotesWrite {
		parts = append(parts, "local-notes-write")
	}
	if s.runtime.enableAttachmentWrite {
		parts = append(parts, "local-attachment-write")
	}
	if s.runtime.enableAttachmentTextRead {
		parts = append(parts, "local-attachment-text-read")
	}
	if s.runtime.enableAttachmentRawRead {
		parts = append(parts, "local-attachment-raw-read")
	}
	if s.runtime.enableUploadWrite {
		parts = append(parts, "local-upload-write")
	}
	if s.runtime.enableThumbnailWrite {
		parts = append(parts, "local-thumbnail-write")
	}
	if s.runtime.enableUploadURLWrite {
		parts = append(parts, "local-upload-url-write")
	}
	return strings.Join(parts, "+")
}

func (s *server) handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableUploadWrite && !s.runtime.enableThumbnailWrite {
		writeError(w, http.StatusMethodNotAllowed, "Thumbnail write route is disabled")
		return
	}

	if err := r.ParseMultipartForm(maxUploadFileBytes); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid multipart upload")
		return
	}
	file, header, err := r.FormFile("file")
	if err != nil {
		writeError(w, http.StatusBadRequest, "No file part in request")
		return
	}
	defer file.Close()

	filename := safeUploadFilename(header.Filename)
	if filename == "" {
		writeError(w, http.StatusBadRequest, "No file selected")
		return
	}
	if !allowedUploadExtension(filename) {
		writeError(w, http.StatusBadRequest, "Invalid file type. Allowed: jpg, jpeg, png, gif, webp")
		return
	}

	content, err := io.ReadAll(io.LimitReader(file, maxUploadFileBytes+1))
	if err != nil {
		writeError(w, http.StatusBadRequest, "Failed to read upload")
		return
	}
	if int64(len(content)) > maxUploadFileBytes {
		writeError(w, http.StatusBadRequest, "File too large. Maximum size: 5MB")
		return
	}
	detectedMIME := detectUploadImageMIME(content)
	if !allowedUploadMIME(detectedMIME) {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("File content validation failed. Detected MIME: %s", detectedMIME))
		return
	}

	img, _, err := image.Decode(bytes.NewReader(content))
	if err != nil {
		writeError(w, http.StatusBadRequest, "Thumbnail generation failed")
		return
	}
	thumbContent, err := encodeThumbnailWebP(img)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Thumbnail generation failed")
		return
	}

	newFilename := timestampedUploadFilename(filename)
	nameWithoutExt := strings.TrimSuffix(newFilename, filepath.Ext(newFilename))
	thumbFilename := nameWithoutExt + "_thumb.webp"
	uploadsDir := s.runtime.uploadsDir
	if err := os.MkdirAll(uploadsDir, 0755); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	thumbnailOnly := strings.EqualFold(r.FormValue("thumbnail_only"), "true")
	thumbPath := filepath.Join(uploadsDir, thumbFilename)
	if thumbnailOnly {
		if err := os.WriteFile(thumbPath, thumbContent, 0644); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
			"url":            "/static/uploads/" + thumbFilename,
			"filename":       thumbFilename,
			"size":           len(content),
			"thumbnail_only": true,
		}})
		return
	}

	originalPath := filepath.Join(uploadsDir, newFilename)
	if err := os.WriteFile(originalPath, content, 0644); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := os.WriteFile(thumbPath, thumbContent, 0644); err != nil {
		_ = os.Remove(originalPath)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"url":            "/static/uploads/" + newFilename,
		"filename":       newFilename,
		"size":           len(content),
		"thumbnail_only": false,
	}})
}

func (s *server) handleUploadURL(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableUploadURLWrite {
		writeError(w, http.StatusMethodNotAllowed, "Upload-url write route is disabled")
		return
	}

	var payload struct {
		URL           string `json:"url"`
		ThumbnailOnly bool   `json:"thumbnail_only"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil && !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "Invalid JSON request")
		return
	}
	imageURL := strings.TrimSpace(payload.URL)
	if imageURL == "" {
		writeError(w, http.StatusBadRequest, "No URL provided")
		return
	}

	parsed, err := url.Parse(imageURL)
	if err != nil || parsed.Scheme == "" || parsed.Hostname() == "" {
		writeError(w, http.StatusBadRequest, "Invalid URL scheme. Only http/https allowed.")
		return
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		writeError(w, http.StatusBadRequest, "Invalid URL scheme. Only http/https allowed.")
		return
	}

	content, contentType, err := downloadUploadURLImage(r.Context(), parsed, imageURL)
	if err != nil {
		if errors.Is(err, errUploadURLSSRF) {
			writeError(w, http.StatusBadRequest, "URL resolves to a private or reserved IP address.")
			return
		}
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	contentMIME := normalizeContentType(contentType)
	if !strings.HasPrefix(contentMIME, "image/") {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("URL does not point to an image. Content-Type: %s", contentType))
		return
	}
	if int64(len(content)) > maxUploadFileBytes {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("Image too large. Maximum size: %dMB", maxUploadFileBytes/(1024*1024)))
		return
	}
	detectedMIME := detectUploadImageMIME(content)
	if !allowedRemoteUploadMIME(detectedMIME) {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("Invalid image type. Detected: %s", detectedMIME))
		return
	}

	baseName := uploadURLBaseFilename(imageURL, parsed, contentMIME)
	newFilename := timestampedUploadFilename(baseName)
	data, err := s.saveDownloadedUpload(content, newFilename, imageURL, payload.ThumbnailOnly)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": data})
}

func downloadUploadURLImage(ctx context.Context, parsed *url.URL, imageURL string) ([]byte, string, error) {
	if err := validateUploadURLTarget(ctx, parsed); err != nil {
		return nil, "", err
	}
	client := &http.Client{
		Timeout:   uploadURLTimeout,
		Transport: uploadURLTransport,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 10 {
				return errors.New("too many redirects")
			}
			return validateUploadURLTarget(req.Context(), req.URL)
		},
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, imageURL, nil)
	if err != nil {
		return nil, "", fmt.Errorf("Failed to download image: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	req.Header.Set("Referer", parsed.Scheme+"://"+parsed.Host+"/")

	resp, err := client.Do(req)
	if err != nil {
		if errors.Is(err, errUploadURLSSRF) {
			return nil, "", err
		}
		return nil, "", fmt.Errorf("Failed to download image: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, "", fmt.Errorf("Failed to download image: HTTP %d", resp.StatusCode)
	}
	contentType := resp.Header.Get("Content-Type")
	if !strings.HasPrefix(normalizeContentType(contentType), "image/") {
		return nil, "", fmt.Errorf("URL does not point to an image. Content-Type: %s", contentType)
	}
	content, err := io.ReadAll(io.LimitReader(resp.Body, maxUploadFileBytes+1))
	if err != nil {
		return nil, "", fmt.Errorf("Failed to download image: %w", err)
	}
	if int64(len(content)) > maxUploadFileBytes {
		return nil, "", fmt.Errorf("Image too large. Maximum size: %dMB", maxUploadFileBytes/(1024*1024))
	}
	return content, contentType, nil
}

func validateUploadURLTarget(ctx context.Context, parsed *url.URL) error {
	if parsed == nil || parsed.Hostname() == "" {
		return errUploadURLSSRF
	}
	hostname := parsed.Hostname()
	if addr, err := netip.ParseAddr(hostname); err == nil {
		if blockedUploadAddr(addr) {
			return errUploadURLSSRF
		}
		return nil
	}
	ips, err := uploadURLResolveHost(ctx, hostname)
	if err != nil || len(ips) == 0 {
		return errUploadURLSSRF
	}
	for _, ip := range ips {
		if blockedUploadIP(ip) {
			return errUploadURLSSRF
		}
	}
	return nil
}

func defaultUploadURLResolveHost(ctx context.Context, hostname string) ([]net.IP, error) {
	return net.DefaultResolver.LookupIP(ctx, "ip", hostname)
}

func blockedUploadIP(ip net.IP) bool {
	if ip == nil {
		return true
	}
	raw := ip
	if v4 := ip.To4(); v4 != nil {
		raw = v4
	} else {
		raw = ip.To16()
	}
	addr, ok := netip.AddrFromSlice(raw)
	if !ok {
		return true
	}
	addr = addr.Unmap()
	return blockedUploadAddr(addr)
}

func blockedUploadAddr(addr netip.Addr) bool {
	if addr.IsLoopback() || addr.IsPrivate() || addr.IsLinkLocalUnicast() ||
		addr.IsLinkLocalMulticast() || addr.IsMulticast() || addr.IsUnspecified() {
		return true
	}
	for _, prefix := range blockedUploadIPPrefixes {
		if prefix.Contains(addr) {
			return true
		}
	}
	return false
}

var blockedUploadIPPrefixes = []netip.Prefix{
	netip.MustParsePrefix("0.0.0.0/8"),
	netip.MustParsePrefix("100.64.0.0/10"),
	netip.MustParsePrefix("192.0.0.0/24"),
	netip.MustParsePrefix("192.0.2.0/24"),
	netip.MustParsePrefix("198.18.0.0/15"),
	netip.MustParsePrefix("198.51.100.0/24"),
	netip.MustParsePrefix("203.0.113.0/24"),
	netip.MustParsePrefix("240.0.0.0/4"),
	netip.MustParsePrefix("2001:db8::/32"),
}

func normalizeContentType(value string) string {
	mediaType, _, err := mime.ParseMediaType(value)
	if err == nil {
		return strings.ToLower(mediaType)
	}
	return strings.ToLower(strings.TrimSpace(strings.Split(value, ";")[0]))
}

func detectUploadImageMIME(content []byte) string {
	switch {
	case len(content) >= 3 && content[0] == 0xff && content[1] == 0xd8 && content[2] == 0xff:
		return "image/jpeg"
	case len(content) >= 8 && bytes.Equal(content[:8], []byte{0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'}):
		return "image/png"
	case len(content) >= 6 && (bytes.Equal(content[:6], []byte("GIF87a")) || bytes.Equal(content[:6], []byte("GIF89a"))):
		return "image/gif"
	case len(content) >= 12 && bytes.Equal(content[:4], []byte("RIFF")) && bytes.Equal(content[8:12], []byte("WEBP")):
		return "image/webp"
	default:
		return normalizeContentType(http.DetectContentType(content))
	}
}

func allowedRemoteUploadMIME(mimeType string) bool {
	switch mimeType {
	case "image/jpeg", "image/png", "image/gif", "image/webp":
		return true
	default:
		return false
	}
}

func uploadURLBaseFilename(imageURL string, parsed *url.URL, contentType string) string {
	urlPath, err := url.PathUnescape(parsed.EscapedPath())
	if err != nil {
		urlPath = parsed.Path
	}
	originalName := path.Base(urlPath)
	if originalName == "." || originalName == "/" {
		originalName = ""
	}
	if originalName != "" && strings.Contains(originalName, ".") {
		if safeName := safeUploadFilename(originalName); safeName != "" {
			return safeName
		}
	}
	sum := md5.Sum([]byte(imageURL))
	hash := hex.EncodeToString(sum[:])[:8]
	return "remote_" + hash + uploadExtensionForMIME(contentType)
}

func uploadExtensionForMIME(mimeType string) string {
	switch normalizeContentType(mimeType) {
	case "image/jpeg":
		return ".jpg"
	case "image/png":
		return ".png"
	case "image/webp":
		return ".webp"
	case "image/gif":
		return ".gif"
	default:
		return ".jpg"
	}
}

func timestampedUploadFilename(filename string) string {
	return uploadNow().Format("20060102_150405") + "_" + filename
}

func (s *server) saveDownloadedUpload(content []byte, newFilename, originalURL string, thumbnailOnly bool) (response, error) {
	uploadsDir := s.runtime.uploadsDir
	if err := os.MkdirAll(uploadsDir, 0755); err != nil {
		return nil, err
	}

	var thumbFilename string
	var thumbContent []byte
	if img, _, err := image.Decode(bytes.NewReader(content)); err == nil {
		if encoded, err := encodeUploadThumbnail(img); err == nil {
			nameWithoutExt := strings.TrimSuffix(newFilename, filepath.Ext(newFilename))
			thumbFilename = nameWithoutExt + "_thumb.webp"
			thumbContent = encoded
		}
	}

	if thumbnailOnly && thumbFilename != "" {
		if err := os.WriteFile(filepath.Join(uploadsDir, thumbFilename), thumbContent, 0644); err != nil {
			return nil, err
		}
		return response{
			"url":            "/static/uploads/" + thumbFilename,
			"filename":       thumbFilename,
			"size":           len(content),
			"original_url":   originalURL,
			"thumbnail_only": true,
		}, nil
	}

	originalPath := filepath.Join(uploadsDir, newFilename)
	if err := os.WriteFile(originalPath, content, 0644); err != nil {
		return nil, err
	}
	if thumbFilename != "" {
		if err := os.WriteFile(filepath.Join(uploadsDir, thumbFilename), thumbContent, 0644); err != nil {
			_ = os.Remove(originalPath)
			return nil, err
		}
	}
	var returnedFilename any = newFilename
	if thumbnailOnly {
		returnedFilename = nil
	}
	return response{
		"url":            "/static/uploads/" + newFilename,
		"filename":       returnedFilename,
		"size":           len(content),
		"original_url":   originalURL,
		"thumbnail_only": thumbnailOnly,
	}, nil
}

func safeUploadFilename(filename string) string {
	base := filepath.Base(strings.ReplaceAll(strings.TrimSpace(filename), "\\", "/"))
	base = strings.Trim(base, ".")
	if base == "" {
		return ""
	}
	cleaned := strings.Map(func(r rune) rune {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' {
			return r
		}
		switch r {
		case '.', '_', '-':
			return r
		default:
			return '_'
		}
	}, base)
	return strings.Trim(cleaned, "._-")
}

func allowedUploadExtension(filename string) bool {
	switch strings.ToLower(filepath.Ext(filename)) {
	case ".jpg", ".jpeg", ".png", ".gif", ".webp":
		return true
	default:
		return false
	}
}

func allowedUploadMIME(mime string) bool {
	switch mime {
	case "image/jpeg", "image/png", "image/gif", "image/webp":
		return true
	default:
		return false
	}
}

func encodeThumbnailWebP(img image.Image) ([]byte, error) {
	resized := resizeToMaxWidth(img, thumbnailMaxWidth)
	var out bytes.Buffer
	if err := webp.Encode(&out, resized, &webp.Options{Lossy: true, Quality: thumbnailWebPQuality}); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}

func resizeToMaxWidth(img image.Image, maxWidth int) image.Image {
	bounds := img.Bounds()
	width := bounds.Dx()
	height := bounds.Dy()
	if width <= 0 || height <= 0 {
		return image.NewRGBA(image.Rect(0, 0, 1, 1))
	}
	if width <= maxWidth {
		dst := image.NewRGBA(image.Rect(0, 0, width, height))
		draw.Draw(dst, dst.Bounds(), img, bounds.Min, draw.Src)
		return dst
	}

	newHeight := int(math.Round(float64(height) * float64(maxWidth) / float64(width)))
	if newHeight < 1 {
		newHeight = 1
	}
	dst := image.NewRGBA(image.Rect(0, 0, maxWidth, newHeight))
	for y := 0; y < newHeight; y++ {
		srcY := bounds.Min.Y + y*height/newHeight
		for x := 0; x < maxWidth; x++ {
			srcX := bounds.Min.X + x*width/maxWidth
			dst.Set(x, y, img.At(srcX, srcY))
		}
	}
	return dst
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
	if r.Method == http.MethodPost {
		if !s.runtime.enableCategoryWrite {
			writeError(w, http.StatusMethodNotAllowed, "Category write route is disabled")
			return
		}
		s.createCategory(w, r)
		return
	}
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

func (s *server) handleCategoryDetail(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/api/categories/")
	categoryID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if r.Method != http.MethodPut && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "PUT, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableCategoryWrite {
		writeError(w, http.StatusMethodNotAllowed, "Category write route is disabled")
		return
	}
	if r.Method == http.MethodDelete {
		s.deleteCategory(w, r, categoryID)
		return
	}
	s.updateCategory(w, r, categoryID)
}

func (s *server) createCategory(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "Category name is required")
	if !ok {
		return
	}
	rawName, ok := payload["name"].(string)
	if !ok || rawName == "" {
		writeError(w, http.StatusBadRequest, "Category name is required")
		return
	}
	name := strings.TrimSpace(rawName)
	icon, hasIcon := payload["icon"]
	if !hasIcon || icon == nil {
		icon = "📁"
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var duplicateID int
	if err := tx.QueryRow("SELECT id FROM Categories WHERE name = ?", name).Scan(&duplicateID); err == nil {
		writeError(w, http.StatusConflict, "Category name already exists")
		return
	} else if !errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	var sortOrder any
	if value, ok := intField(payload, "sort_order"); ok {
		sortOrder = value
	} else {
		if err := tx.QueryRow("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM Categories").Scan(&sortOrder); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}

	result, err := tx.Exec("INSERT INTO Categories (name, icon, sort_order, is_default) VALUES (?, ?, ?, 0)", name, icon, sortOrder)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	newID, err := result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"id": int(newID)}})
}

func (s *server) updateCategory(w http.ResponseWriter, r *http.Request, categoryID int) {
	var payload map[string]any
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil || len(payload) == 0 {
		writeError(w, http.StatusBadRequest, "Request body is required")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var oldName string
	if err := tx.QueryRow("SELECT name FROM Categories WHERE id = ?", categoryID).Scan(&oldName); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Category not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	newName := oldName
	if rawName, ok := payload["name"]; ok {
		name, ok := rawName.(string)
		if !ok {
			writeError(w, http.StatusInternalServerError, "category name must be a string")
			return
		}
		newName = strings.TrimSpace(name)
	}
	if newName == "" {
		writeError(w, http.StatusBadRequest, "Category name cannot be empty")
		return
	}
	if newName != oldName {
		var duplicateID int
		if err := tx.QueryRow("SELECT id FROM Categories WHERE name = ? AND id != ?", newName, categoryID).Scan(&duplicateID); err == nil {
			writeError(w, http.StatusConflict, "Category name already exists")
			return
		} else if !errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}

	icon, hasIcon := payload["icon"]
	if hasIcon && icon == nil {
		hasIcon = false
	}
	sortOrder, hasSortOrder := payload["sort_order"]
	if value, ok := intField(payload, "sort_order"); ok {
		sortOrder = value
		hasSortOrder = true
	}
	if hasSortOrder && sortOrder == nil {
		hasSortOrder = false
	}

	if hasIcon && hasSortOrder {
		_, err = tx.Exec("UPDATE Categories SET name = ?, icon = ?, sort_order = ? WHERE id = ?", newName, icon, sortOrder, categoryID)
	} else if hasIcon {
		_, err = tx.Exec("UPDATE Categories SET name = ?, icon = ? WHERE id = ?", newName, icon, categoryID)
	} else if hasSortOrder {
		_, err = tx.Exec("UPDATE Categories SET name = ?, sort_order = ? WHERE id = ?", newName, sortOrder, categoryID)
	} else {
		_, err = tx.Exec("UPDATE Categories SET name = ? WHERE id = ?", newName, categoryID)
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"updated_notes_count": 0}})
}

func (s *server) deleteCategory(w http.ResponseWriter, r *http.Request, categoryID int) {
	payload := map[string]any{}
	if r.Body != nil {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if strings.TrimSpace(string(body)) != "" {
			if err := json.Unmarshal(body, &payload); err != nil {
				writeError(w, http.StatusInternalServerError, err.Error())
				return
			}
		}
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var isDefault int
	if err := tx.QueryRow("SELECT COALESCE(is_default, 0) FROM Categories WHERE id = ?", categoryID).Scan(&isDefault); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Category not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if isDefault != 0 {
		writeError(w, http.StatusBadRequest, "Cannot delete the default category")
		return
	}

	var notesCount int
	if err := tx.QueryRow("SELECT COUNT(*) FROM Notes WHERE category_id = ?", categoryID).Scan(&notesCount); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	targetCategoryID, hasTargetCategoryID := intField(payload, "target_category_id")
	if notesCount > 0 && (!hasTargetCategoryID || targetCategoryID == 0) {
		writeJSON(w, http.StatusBadRequest, response{
			"status":      "error",
			"message":     "Target category required",
			"notes_count": notesCount,
		})
		return
	}

	migratedCount := int64(0)
	if notesCount > 0 && targetCategoryID != 0 {
		result, err := tx.Exec("UPDATE Notes SET category_id = ? WHERE category_id = ?", targetCategoryID, categoryID)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		migratedCount, _ = result.RowsAffected()
	}
	if _, err := tx.Exec("DELETE FROM Categories WHERE id = ?", categoryID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"migrated_notes_count": int(migratedCount)}})
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
	if idText == "merge" {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableTagWrite {
			writeError(w, http.StatusMethodNotAllowed, "Tag write route is disabled")
			return
		}
		s.mergeTags(w, r)
		return
	}
	tagID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if r.Method != http.MethodPut && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "PUT, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableTagWrite {
		writeError(w, http.StatusMethodNotAllowed, "Tag write route is disabled")
		return
	}
	if r.Method == http.MethodDelete {
		s.deleteTag(w, tagID)
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
	if err := tx.QueryRow("SELECT id FROM Tags WHERE name = ? COLLATE NOCASE AND id != ?", newName, tagID).Scan(&duplicateID); err == nil {
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

func (s *server) deleteTag(w http.ResponseWriter, tagID int) {
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
	if _, err := tx.Exec("DELETE FROM Note_Tags WHERE tag_id = ?", tagID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("DELETE FROM Tags WHERE id = ?", tagID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func (s *server) mergeTags(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "source_tag_ids and target_tag_id are required")
	if !ok {
		return
	}
	sourceRaw, hasSourceIDs := payload["source_tag_ids"]
	targetTagID, hasTargetTagID := intField(payload, "target_tag_id")
	if !hasSourceIDs || sourceRaw == nil || !hasTargetTagID || targetTagID == 0 {
		writeError(w, http.StatusBadRequest, "source_tag_ids and target_tag_id are required")
		return
	}
	if rawList, ok := sourceRaw.([]any); ok && len(rawList) == 0 {
		writeError(w, http.StatusBadRequest, "source_tag_ids and target_tag_id are required")
		return
	}
	sourceTagIDs, ok := intArrayField(payload, "source_tag_ids")
	if !ok || len(sourceTagIDs) == 0 {
		writeError(w, http.StatusBadRequest, "source_tag_ids must be a non-empty array")
		return
	}
	for _, sourceTagID := range sourceTagIDs {
		if sourceTagID == targetTagID {
			writeError(w, http.StatusBadRequest, "target_tag_id cannot be in source_tag_ids")
			return
		}
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var targetID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE id = ?", targetTagID).Scan(&targetID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Target tag not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	mergedCount := 0
	for _, sourceTagID := range sourceTagIDs {
		var sourceID int
		if err := tx.QueryRow("SELECT id FROM Tags WHERE id = ?", sourceTagID).Scan(&sourceID); err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				continue
			}
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if _, err := tx.Exec(`
			INSERT OR IGNORE INTO Note_Tags (note_id, tag_id)
			SELECT note_id, ? FROM Note_Tags WHERE tag_id = ?`, targetTagID, sourceTagID); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if _, err := tx.Exec("DELETE FROM Tags WHERE id = ?", sourceTagID); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		mergedCount++
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"merged_count": mergedCount}})
}

func (s *server) handleAttachmentDetail(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/api/attachments/")
	attachmentID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}

	if r.Method == http.MethodDelete {
		if !s.runtime.enableAttachmentWrite {
			writeError(w, http.StatusMethodNotAllowed, "Attachment write route is disabled")
			return
		}
		s.deleteAttachment(w, attachmentID)
		return
	}
	if r.Method != http.MethodGet {
		w.Header().Set("Allow", "GET, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if boolString(r, "raw") {
		if !s.runtime.enableAttachmentRawRead {
			if s.runtime.enableAttachmentTextRead {
				writeError(w, http.StatusMethodNotAllowed, "Raw attachment responses remain Python-owned")
				return
			}
			writeError(w, http.StatusMethodNotAllowed, "Attachment raw read route is disabled")
			return
		}
		s.serveAttachmentRaw(w, r, attachmentID)
		return
	}
	if !s.runtime.enableAttachmentTextRead && !s.runtime.enableAttachmentRawRead {
		writeError(w, http.StatusMethodNotAllowed, "Attachment text read route is disabled")
		return
	}
	s.readAttachmentText(w, attachmentID)
}

func (s *server) serveAttachmentRaw(w http.ResponseWriter, r *http.Request, attachmentID int) {
	row := s.db.QueryRow(`
		SELECT id, file_path, file_type, title
		FROM Note_Attachments
		WHERE id = ?`, attachmentID)

	var id int
	var filePath, fileType, title sql.NullString
	if err := row.Scan(&id, &filePath, &fileType, &title); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Attachment not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	resolved, _, ok := resolveAttachmentRawFile(s.runtime.dataDir, nullableString(filePath), nullableString(fileType))
	if !ok {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}
	file, err := os.Open(resolved)
	if err != nil {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}

	if contentType := attachmentRawContentType(resolved); contentType != "" {
		w.Header().Set("Content-Type", contentType)
	}
	http.ServeContent(w, r, safeAttachmentDownloadName(nullableString(title), resolved), info.ModTime(), file)
}

func (s *server) readAttachmentText(w http.ResponseWriter, attachmentID int) {
	row := s.db.QueryRow(`
		SELECT id, file_path, file_type, title
		FROM Note_Attachments
		WHERE id = ?`, attachmentID)

	var id int
	var filePath, fileType, title sql.NullString
	if err := row.Scan(&id, &filePath, &fileType, &title); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Attachment not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	resolved, _, ok := resolveAttachmentFile(s.runtime.dataDir, nullableString(filePath), nullableString(fileType))
	if !ok {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}
	content, err := os.ReadFile(resolved)
	if err != nil {
		writeError(w, http.StatusNotFound, "File not found on disk")
		return
	}

	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"id":        id,
			"title":     nullableString(title),
			"file_type": nullableString(fileType),
			"content":   normalizeTextContent(string(content)),
		},
	})
}

func normalizeTextContent(content string) string {
	content = strings.ReplaceAll(content, "\r\n", "\n")
	return strings.ReplaceAll(content, "\r", "\n")
}

func (s *server) listNoteAttachments(w http.ResponseWriter, noteID int) {
	var existing int
	if err := s.db.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existing); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	rows, err := s.db.Query(`
		SELECT id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at
		FROM Note_Attachments
		WHERE note_id = ?
		ORDER BY created_at DESC`, noteID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	items := []response{}
	for rows.Next() {
		var id int
		var filePath, fileType, title, createdAt sql.NullString
		var sizeBytes, isAutoExtracted sql.NullInt64
		if err := rows.Scan(&id, &filePath, &fileType, &title, &sizeBytes, &isAutoExtracted, &createdAt); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		items = append(items, response{
			"id":                id,
			"file_path":         nullableString(filePath),
			"file_type":         nullableString(fileType),
			"title":             nullableStringOrNil(title),
			"size_bytes":        nullableIntOrNil(sizeBytes),
			"is_auto_extracted": isAutoExtracted.Valid && isAutoExtracted.Int64 != 0,
			"created_at":        sqliteDateTimeString(createdAt),
		})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": items})
}

func (s *server) uploadAttachment(w http.ResponseWriter, r *http.Request, noteID int) {
	var existing int
	if err := s.db.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existing); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := r.ParseMultipartForm(maxUploadFileBytes); err != nil {
		writeError(w, http.StatusBadRequest, "No file provided")
		return
	}
	file, header, err := r.FormFile("file")
	if err != nil {
		writeError(w, http.StatusBadRequest, "No file provided")
		return
	}
	defer file.Close()
	if header.Filename == "" {
		writeError(w, http.StatusBadRequest, "No file selected")
		return
	}
	if !allowedAttachmentFilename(header.Filename) {
		writeError(w, http.StatusBadRequest, "File type not allowed. Allowed types: markdown, md, txt")
		return
	}

	originalName := sanitizeAttachmentFilename(header.Filename)
	baseName, ext := splitAttachmentName(originalName)
	uniqueFilename := fmt.Sprintf("%s_%s%s", baseName, time.Now().Format("20060102_150405"), ext)
	if uniqueFilename == "" || uniqueFilename == "." {
		writeError(w, http.StatusBadRequest, "No file selected")
		return
	}

	if err := os.MkdirAll(s.runtime.attachmentsDir, 0755); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	targetPath := filepath.Join(s.runtime.attachmentsDir, uniqueFilename)
	target, err := os.OpenFile(targetPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	sizeBytes, copyErr := io.Copy(target, file)
	closeErr := target.Close()
	if copyErr != nil {
		_ = os.Remove(targetPath)
		writeError(w, http.StatusInternalServerError, copyErr.Error())
		return
	}
	if closeErr != nil {
		_ = os.Remove(targetPath)
		writeError(w, http.StatusInternalServerError, closeErr.Error())
		return
	}

	title := r.FormValue("title")
	if title == "" {
		title = baseName
	}
	relativePath := path.Join("docs/attachments", filepath.ToSlash(uniqueFilename))
	cursor, err := s.db.Exec(`
		INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
		VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)`,
		noteID, relativePath, strings.TrimPrefix(ext, "."), title, sizeBytes)
	if err != nil {
		_ = os.Remove(targetPath)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	attachmentID, err := cursor.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"id": attachmentID, "file_path": relativePath, "title": title, "size_bytes": sizeBytes,
	}})
}

func (s *server) deleteAttachment(w http.ResponseWriter, attachmentID int) {
	var filePath sql.NullString
	if err := s.db.QueryRow("SELECT file_path FROM Note_Attachments WHERE id = ?", attachmentID).Scan(&filePath); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Attachment not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if resolved, ok := resolveAttachmentMutationPath(s.runtime.dataDir, nullableString(filePath)); ok {
		if err := os.Remove(resolved); err != nil && !os.IsNotExist(err) {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if _, err := s.db.Exec("DELETE FROM Note_Attachments WHERE id = ?", attachmentID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func allowedAttachmentFilename(filename string) bool {
	name := filepath.Base(filename)
	ext := strings.TrimPrefix(strings.ToLower(filepath.Ext(name)), ".")
	return ext == "md" || ext == "txt" || ext == "markdown"
}

func sanitizeAttachmentFilename(filename string) string {
	name := filepath.Base(filename)
	return regexp.MustCompile(`[^\w\-_\. ]`).ReplaceAllString(name, "")
}

func splitAttachmentName(filename string) (string, string) {
	ext := filepath.Ext(filename)
	return strings.TrimSuffix(filename, ext), ext
}

func resolveAttachmentMutationPath(dataDir, relativePath string) (string, bool) {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	if relativePath == "" || filepath.IsAbs(relativePath) || filepath.VolumeName(relativePath) != "" || strings.Contains(relativePath, ":") {
		return "", false
	}
	cleaned := path.Clean(relativePath)
	if cleaned == "." || strings.HasPrefix(cleaned, "../") || cleaned == ".." || !strings.HasPrefix(cleaned, "docs/attachments/") {
		return "", false
	}
	root, err := filepath.Abs(dataDir)
	if err != nil {
		return "", false
	}
	candidate := filepath.Join(root, filepath.FromSlash(cleaned))
	absCandidate, err := filepath.Abs(candidate)
	if err != nil || !isSubpath(absCandidate, root) {
		return "", false
	}
	return absCandidate, true
}

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

func (s *server) createNote(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "Content is required")
	if !ok {
		return
	}
	content := stringField(payload, "content")
	if content == "" {
		writeError(w, http.StatusBadRequest, "Content is required")
		return
	}

	title := strings.TrimSpace(stringField(payload, "title"))
	if title == "" {
		title = autoNoteTitle(content)
	}
	categoryID, ok := intField(payload, "category_id")
	if !ok {
		var defaultID sql.NullInt64
		if err := s.db.QueryRow("SELECT id FROM Categories WHERE is_default = 1 LIMIT 1").Scan(&defaultID); err == nil && defaultID.Valid {
			categoryID = int(defaultID.Int64)
			ok = true
		}
	}
	promptParams, err := marshalJSONField(payload, "prompt_params")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	cursor, err := tx.Exec(`
		INSERT INTO Notes (
			title, content, category_id, remarks, cover_image,
			cover_position, editor_layout, prompt_params, is_pinned, is_archived
		)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		title, content, nullableIntArg(categoryID, ok),
		stringField(payload, "remarks"), nullableStringArg(payload, "cover_image"),
		defaultStringField(payload, "cover_position", "top"),
		defaultStringField(payload, "editor_layout", "single"),
		promptParams, boolIntField(payload, "is_pinned"), boolIntField(payload, "is_archived"))
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	noteID, err := cursor.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteTags(tx, int(noteID), stringArrayField(payload, "tags"), false); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteURLs(tx, int(noteID), stringArrayField(payload, "urls")); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"note_id": int(noteID)}})
}

func (s *server) updateNote(w http.ResponseWriter, r *http.Request, noteID int) {
	payload, ok := decodeJSONObject(w, r, "Title and content are required")
	if !ok {
		return
	}
	title := stringField(payload, "title")
	content := stringField(payload, "content")
	if title == "" || content == "" {
		writeError(w, http.StatusBadRequest, "Title and content are required")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var oldContent string
	var isPinned, isArchived int
	if err := tx.QueryRow("SELECT content, COALESCE(is_pinned, 0), COALESCE(is_archived, 0) FROM Notes WHERE id = ?", noteID).Scan(&oldContent, &isPinned, &isArchived); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	if oldContent != content {
		summary := fmt.Sprintf("字數變化: %d → %d", len([]rune(oldContent)), len([]rune(content)))
		if _, err := tx.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, ?, ?)", noteID, oldContent, summary); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	categoryID, hasCategoryID := intField(payload, "category_id")
	if !hasCategoryID {
		var existing sql.NullInt64
		if err := tx.QueryRow("SELECT category_id FROM Notes WHERE id = ?", noteID).Scan(&existing); err == nil && existing.Valid {
			categoryID = int(existing.Int64)
			hasCategoryID = true
		}
	}
	if _, ok := payload["is_pinned"]; ok {
		isPinned = boolIntField(payload, "is_pinned")
	}
	if _, ok := payload["is_archived"]; ok {
		isArchived = boolIntField(payload, "is_archived")
	}
	promptParams, err := marshalJSONField(payload, "prompt_params")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	if _, err := tx.Exec(`
		UPDATE Notes
		SET title = ?, content = ?, category_id = ?, remarks = ?, cover_image = ?,
		    cover_position = ?, editor_layout = ?, prompt_params = ?,
		    is_pinned = ?, is_archived = ?, updated_at = CURRENT_TIMESTAMP
		WHERE id = ?`,
		title, content, nullableIntArg(categoryID, hasCategoryID),
		stringField(payload, "remarks"), nullableStringArg(payload, "cover_image"),
		defaultStringField(payload, "cover_position", "top"),
		defaultStringField(payload, "editor_layout", "single"),
		promptParams, isPinned, isArchived, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("DELETE FROM Note_Tags WHERE note_id = ?", noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteTags(tx, noteID, stringArrayField(payload, "tags"), false); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteURLs(tx, noteID, stringArrayField(payload, "urls")); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func (s *server) deleteNote(w http.ResponseWriter, noteID int) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var ref noteImageReference
	if err := tx.QueryRow("SELECT id, content, cover_image FROM Notes WHERE id = ?", noteID).Scan(&ref.ID, &ref.Content, &ref.CoverImage); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	s.cleanupNoteImages(tx, ref)
	if _, err := deleteNotesByID(tx, []int{noteID}); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
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
		var categoryID int
		if err := s.db.QueryRow("SELECT id FROM Categories WHERE name = ? LIMIT 1", noteType).Scan(&categoryID); err == nil {
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
		if len(q) > 200 {
			q = q[:200]
		}
		searchClause, searchArgs := s.buildNotesSearchClause(q)
		if searchClause != "" {
			clauses = append(clauses, searchClause)
			args = append(args, searchArgs...)
		}
	}
	return "WHERE " + strings.Join(clauses, " AND "), args
}

func (s *server) buildNotesSearchClause(keyword string) (string, []any) {
	tokens := searchTokens(keyword)
	clauses := []string{}
	args := []any{}
	if ftsQuery := sanitizeFTSQuery(keyword); ftsQuery != "" {
		clauses = append(clauses, "n.id IN (SELECT rowid FROM Notes_FTS WHERE Notes_FTS MATCH ?)")
		args = append(args, ftsQuery)
	}
	if len(tokens) > 0 {
		clauses = append(clauses, tokenAndClause("LOWER(COALESCE(n.remarks, '')) LIKE ?", tokens, &args))
		clauses = append(clauses, tagTokenSearchClause(tokens, &args))
		clauses = append(clauses, attachmentMetadataTokenSearchClause(tokens, &args))
	}
	if attachmentNoteIDs := s.attachmentContentNoteIDs(keyword); len(attachmentNoteIDs) > 0 {
		clauses = append(clauses, "n.id IN ("+placeholders(len(attachmentNoteIDs))+")")
		for _, noteID := range attachmentNoteIDs {
			args = append(args, noteID)
		}
	}
	if len(clauses) == 0 {
		return "", nil
	}
	return "(" + strings.Join(clauses, " OR ") + ")", args
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

func resolveAttachmentRawFile(dataDir, relativePath, fileType string) (string, int64, bool) {
	if !isAllowedRawAttachmentPath(relativePath, fileType) {
		return "", 0, false
	}
	root, err := filepath.Abs(dataDir)
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

func decodeJSONObject(w http.ResponseWriter, r *http.Request, message string) (map[string]any, bool) {
	var payload map[string]any
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil || payload == nil {
		writeError(w, http.StatusBadRequest, message)
		return nil, false
	}
	return payload, true
}

func stringField(payload map[string]any, key string) string {
	value, _ := payload[key].(string)
	return value
}

func defaultStringField(payload map[string]any, key, fallback string) string {
	if value, ok := payload[key].(string); ok {
		return value
	}
	return fallback
}

func nullableStringArg(payload map[string]any, key string) any {
	value, ok := payload[key]
	if !ok || value == nil {
		return nil
	}
	if text, ok := value.(string); ok {
		return text
	}
	return nil
}

func intField(payload map[string]any, key string) (int, bool) {
	value, ok := payload[key]
	if !ok || value == nil {
		return 0, false
	}
	switch v := value.(type) {
	case float64:
		if v == math.Trunc(v) {
			return int(v), true
		}
	case int:
		return v, true
	}
	return 0, false
}

func nullableIntArg(value int, ok bool) any {
	if !ok {
		return nil
	}
	return value
}

func boolIntField(payload map[string]any, key string) int {
	if value, ok := payload[key].(bool); ok && value {
		return 1
	}
	return 0
}

func stringArrayField(payload map[string]any, key string) []string {
	raw, ok := payload[key]
	if !ok || raw == nil {
		return nil
	}
	items, ok := raw.([]any)
	if !ok {
		return nil
	}
	out := []string{}
	for _, item := range items {
		if text, ok := item.(string); ok {
			out = append(out, text)
		}
	}
	return out
}

func intArrayField(payload map[string]any, key string) ([]int, bool) {
	raw, ok := payload[key]
	if !ok || raw == nil {
		return nil, false
	}
	items, ok := raw.([]any)
	if !ok {
		return nil, false
	}
	out := []int{}
	for _, item := range items {
		value, ok := item.(float64)
		if !ok || value != math.Trunc(value) {
			return nil, false
		}
		out = append(out, int(value))
	}
	return out, true
}

func requiredIntArrayField(w http.ResponseWriter, payload map[string]any, key, requiredMessage string) ([]int, bool) {
	raw, ok := payload[key]
	if !ok || raw == nil {
		writeError(w, http.StatusBadRequest, requiredMessage)
		return nil, false
	}
	items, ok := raw.([]any)
	if !ok {
		writeError(w, http.StatusBadRequest, key+" must be a non-empty array")
		return nil, false
	}
	if len(items) == 0 {
		writeError(w, http.StatusBadRequest, requiredMessage)
		return nil, false
	}
	out := make([]int, 0, len(items))
	for _, item := range items {
		value, ok := item.(float64)
		if !ok || value != math.Trunc(value) {
			writeError(w, http.StatusBadRequest, "All "+key+" must be integers")
			return nil, false
		}
		out = append(out, int(value))
	}
	return out, true
}

func marshalJSONField(payload map[string]any, key string) (any, error) {
	value, ok := payload[key]
	if !ok || value == nil {
		return nil, nil
	}
	if _, ok := value.(map[string]any); !ok {
		return nil, nil
	}
	encoded, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	return pythonStyleJSONSpacing(encoded), nil
}

func pythonStyleJSONSpacing(encoded []byte) string {
	var builder strings.Builder
	builder.Grow(len(encoded) + 8)
	inString := false
	escaped := false
	for _, b := range encoded {
		builder.WriteByte(b)
		if inString {
			if escaped {
				escaped = false
				continue
			}
			if b == '\\' {
				escaped = true
				continue
			}
			if b == '"' {
				inString = false
			}
			continue
		}
		if b == '"' {
			inString = true
			continue
		}
		if b == ':' || b == ',' {
			builder.WriteByte(' ')
		}
	}
	return builder.String()
}

func autoNoteTitle(content string) string {
	first := strings.TrimSpace(strings.Split(content, "\n")[0])
	first = strings.TrimSpace(strings.TrimLeft(first, "#>-*"))
	if first != "" {
		runes := []rune(first)
		if len(runes) > 50 {
			return string(runes[:50]) + "..."
		}
		return first
	}
	return "Note - " + time.Now().Format("2006/01/02 15:04")
}

func replaceNoteTags(tx *sql.Tx, noteID int, tags []string, clearExisting bool) error {
	if clearExisting {
		if _, err := tx.Exec("DELETE FROM Note_Tags WHERE note_id = ?", noteID); err != nil {
			return err
		}
	}
	_, err := appendNoteTags(tx, noteID, tags)
	return err
}

func appendNoteTags(tx *sql.Tx, noteID int, tags []string) (int, error) {
	added := 0
	for _, tagName := range tags {
		tagName = strings.TrimSpace(tagName)
		if tagName == "" {
			continue
		}
		var tagID int
		if err := tx.QueryRow("SELECT id FROM Tags WHERE name = ? COLLATE NOCASE", tagName).Scan(&tagID); err != nil {
			if !errors.Is(err, sql.ErrNoRows) {
				return added, err
			}
			result, err := tx.Exec("INSERT INTO Tags (name) VALUES (?)", tagName)
			if err != nil {
				return added, err
			}
			newID, err := result.LastInsertId()
			if err != nil {
				return added, err
			}
			tagID = int(newID)
		}
		result, err := tx.Exec("INSERT OR IGNORE INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", noteID, tagID)
		if err != nil {
			return added, err
		}
		if rows, _ := result.RowsAffected(); rows > 0 {
			added++
		}
	}
	return added, nil
}

func replaceNoteURLs(tx *sql.Tx, noteID int, urls []string) error {
	if _, err := tx.Exec("DELETE FROM Source_Urls WHERE note_id = ?", noteID); err != nil {
		return err
	}
	for _, sourceURL := range urls {
		sourceURL = strings.TrimSpace(sourceURL)
		if sourceURL == "" {
			continue
		}
		if _, err := tx.Exec("INSERT INTO Source_Urls (note_id, url) VALUES (?, ?)", noteID, sourceURL); err != nil {
			return err
		}
	}
	return nil
}

func deleteNotesByID(tx *sql.Tx, noteIDs []int) (int, error) {
	if len(noteIDs) == 0 {
		return 0, nil
	}
	ids := intsToAny(noteIDs)
	inClause := placeholders(len(noteIDs))
	for _, table := range []string{"Note_Tags", "Source_Urls", "Note_History", "Note_Attachments"} {
		if _, err := tx.Exec("DELETE FROM "+table+" WHERE note_id IN ("+inClause+")", ids...); err != nil {
			return 0, err
		}
	}
	result, err := tx.Exec("DELETE FROM Notes WHERE id IN ("+inClause+")", ids...)
	if err != nil {
		return 0, err
	}
	rows, _ := result.RowsAffected()
	return int(rows), nil
}

func noteImageReferences(tx *sql.Tx, noteIDs []int) ([]noteImageReference, error) {
	if len(noteIDs) == 0 {
		return nil, nil
	}
	rows, err := tx.Query("SELECT id, content, cover_image FROM Notes WHERE id IN ("+placeholders(len(noteIDs))+") ORDER BY id", intsToAny(noteIDs)...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	refs := []noteImageReference{}
	for rows.Next() {
		var ref noteImageReference
		if err := rows.Scan(&ref.ID, &ref.Content, &ref.CoverImage); err != nil {
			return nil, err
		}
		refs = append(refs, ref)
	}
	return refs, rows.Err()
}

func (s *server) cleanupNoteImages(tx *sql.Tx, ref noteImageReference) {
	for _, imagePath := range staticUploadReferences(ref.Content, ref.CoverImage) {
		var refCount int
		err := tx.QueryRow(`
			SELECT COUNT(*) FROM Notes
			WHERE id != ? AND (cover_image = ? OR content LIKE ?)
		`, ref.ID, imagePath, "%"+imagePath+"%").Scan(&refCount)
		if err != nil {
			log.Printf("note image cleanup skipped reference count for note %d path %s: %v", ref.ID, imagePath, err)
			continue
		}
		if refCount > 0 {
			continue
		}
		for _, filename := range cleanupUploadFilenames(imagePath) {
			absPath, ok := s.resolveUploadFile(filename)
			if !ok {
				continue
			}
			if err := os.Remove(absPath); err != nil && !os.IsNotExist(err) {
				log.Printf("note image cleanup skipped file %s: %v", absPath, err)
			}
		}
	}
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

func nullableVariantParent(noteID int, asVariant bool) any {
	if !asVariant {
		return nil
	}
	return noteID
}

func (s *server) handleNoteDetail(w http.ResponseWriter, r *http.Request) {
	rel := strings.TrimPrefix(r.URL.Path, "/api/notes/")
	if rel == "reorder" {
		if r.Method != http.MethodPut {
			w.Header().Set("Allow", http.MethodPut)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.reorderNotes(w, r)
		return
	}
	if strings.HasPrefix(rel, "batch/") {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.handleNoteBatch(w, r, strings.TrimPrefix(rel, "batch/"))
		return
	}

	parts := strings.Split(rel, "/")
	if len(parts) == 0 {
		http.NotFound(w, r)
		return
	}
	noteID, err := strconv.Atoi(parts[0])
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if len(parts) == 2 && parts[1] == "attachments" {
		if r.Method != http.MethodGet && r.Method != http.MethodPost {
			w.Header().Set("Allow", "GET, POST")
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableAttachmentWrite {
			if r.Method == http.MethodPost {
				_, _ = io.Copy(io.Discard, r.Body)
			}
			writeError(w, http.StatusMethodNotAllowed, "Attachment write route is disabled")
			return
		}
		if r.Method == http.MethodGet {
			s.listNoteAttachments(w, noteID)
			return
		}
		s.uploadAttachment(w, r, noteID)
		return
	}
	if len(parts) > 1 {
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.handleNoteAction(w, r, noteID, parts[1:])
		return
	}
	if r.Method == http.MethodPut {
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.updateNote(w, r, noteID)
		return
	}
	if r.Method == http.MethodDelete {
		if !s.runtime.enableNotesWrite {
			writeError(w, http.StatusMethodNotAllowed, "Notes write route is disabled")
			return
		}
		s.deleteNote(w, noteID)
		return
	}
	if !requireGET(w, r) {
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

func (s *server) handleNoteAction(w http.ResponseWriter, r *http.Request, noteID int, parts []string) {
	switch parts[0] {
	case "pin":
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.toggleNoteBool(w, r, noteID, "is_pinned", "pinned")
	case "archive":
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.toggleNoteBool(w, r, noteID, "is_archived", "archived")
	case "duplicate":
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.duplicateNote(w, r, noteID)
	case "history":
		if len(parts) != 1 {
			http.NotFound(w, r)
			return
		}
		if r.Method == http.MethodGet {
			s.getNoteHistory(w, noteID)
			return
		}
		if r.Method == http.MethodDelete {
			s.deleteNoteHistory(w, noteID)
			return
		}
		w.Header().Set("Allow", "GET, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	case "restore":
		if r.Method != http.MethodPost || len(parts) != 2 {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		historyID, err := strconv.Atoi(parts[1])
		if err != nil {
			http.NotFound(w, r)
			return
		}
		_, _ = io.Copy(io.Discard, r.Body)
		s.restoreNoteVersion(w, noteID, historyID)
	default:
		http.NotFound(w, r)
	}
}

func (s *server) toggleNoteBool(w http.ResponseWriter, r *http.Request, noteID int, column, payloadKey string) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var current int
	if err := tx.QueryRow("SELECT COALESCE("+column+", 0) FROM Notes WHERE id = ?", noteID).Scan(&current); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	payload := map[string]any{}
	_ = json.NewDecoder(r.Body).Decode(&payload)
	next := 0
	if raw, ok := payload[payloadKey]; ok {
		if truthy, ok := raw.(bool); ok && truthy {
			next = 1
		}
	} else if current == 0 {
		next = 1
	}
	query := "UPDATE Notes SET " + column + " = ?"
	if column == "is_archived" {
		query += ", updated_at = CURRENT_TIMESTAMP"
	}
	query += " WHERE id = ?"
	if _, err := tx.Exec(query, next, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"id": noteID, column: next != 0}})
}

func (s *server) duplicateNote(w http.ResponseWriter, r *http.Request, noteID int) {
	payload := map[string]any{}
	_ = json.NewDecoder(r.Body).Decode(&payload)
	asVariant, _ := payload["as_variant"].(bool)
	titleSuffix := stringField(payload, "title_suffix")
	if titleSuffix == "" {
		if asVariant {
			titleSuffix = " (Variant)"
		} else {
			titleSuffix = " (Copy)"
		}
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var title, content, remarks, coverImage, coverPosition, editorLayout, promptParams sql.NullString
	var categoryID sql.NullInt64
	if err := tx.QueryRow(`
		SELECT title, content, remarks, cover_image, cover_position, editor_layout, category_id, prompt_params
		FROM Notes WHERE id = ?`, noteID).Scan(&title, &content, &remarks, &coverImage, &coverPosition, &editorLayout, &categoryID, &promptParams); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	var result sql.Result
	if asVariant {
		result, err = tx.Exec(`
			INSERT INTO Notes (title, content, remarks, cover_image, cover_position, editor_layout, category_id, prompt_params, parent_id)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			nullableString(title)+titleSuffix, nullableString(content), nullableStringOrNil(remarks), nullableStringOrNil(coverImage),
			nullableString(coverPosition), nullableString(editorLayout), nullableIntOrNil(categoryID), nullableStringOrNil(promptParams), noteID)
	} else {
		result, err = tx.Exec(`
			INSERT INTO Notes (title, content, remarks, cover_image, cover_position, editor_layout, category_id, prompt_params)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
			nullableString(title)+titleSuffix, nullableString(content), nullableStringOrNil(remarks), nullableStringOrNil(coverImage),
			nullableString(coverPosition), nullableString(editorLayout), nullableIntOrNil(categoryID), nullableStringOrNil(promptParams))
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	newID, err := result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("INSERT INTO Note_Tags (note_id, tag_id) SELECT ?, tag_id FROM Note_Tags WHERE note_id = ?", newID, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("INSERT INTO Source_Urls (note_id, url) SELECT ?, url FROM Source_Urls WHERE note_id = ?", newID, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{
		"note_id": int(newID), "parent_id": nullableVariantParent(noteID, asVariant), "is_variant": asVariant,
	}})
}

func (s *server) reorderNotes(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "note_ids is required")
	if !ok {
		return
	}
	noteIDs, ok := requiredIntArrayField(w, payload, "note_ids", "note_ids is required")
	if !ok {
		return
	}
	if len(noteIDs) == 0 {
		writeError(w, http.StatusBadRequest, "note_ids must be a non-empty array")
		return
	}
	if len(noteIDs) > 500 {
		writeError(w, http.StatusBadRequest, "Maximum 500 notes per reorder")
		return
	}
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	for index, id := range noteIDs {
		if _, err := tx.Exec("UPDATE Notes SET sort_order = ? WHERE id = ?", index, id); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"reordered_count": len(noteIDs)}})
}

func (s *server) handleNoteBatch(w http.ResponseWriter, r *http.Request, action string) {
	switch action {
	case "type":
		s.batchUpdateType(w, r)
	case "tags":
		s.batchUpdateTags(w, r)
	case "delete":
		s.batchDeleteNotes(w, r)
	default:
		http.NotFound(w, r)
	}
}

func (s *server) batchUpdateType(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "note_ids and category_id are required")
	if !ok {
		return
	}
	categoryID, hasCategory := intField(payload, "category_id")
	if !hasCategory || categoryID == 0 {
		writeError(w, http.StatusBadRequest, "note_ids and category_id are required")
		return
	}
	noteIDs, ok := requiredIntArrayField(w, payload, "note_ids", "note_ids and category_id are required")
	if !ok {
		return
	}
	if len(noteIDs) > 500 {
		writeError(w, http.StatusBadRequest, "Maximum 500 notes per batch")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	var existingCategory int
	if err := tx.QueryRow("SELECT id FROM Categories WHERE id = ?", categoryID).Scan(&existingCategory); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusBadRequest, fmt.Sprintf("Category %d does not exist", categoryID))
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	result, err := tx.Exec("UPDATE Notes SET category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id IN ("+placeholders(len(noteIDs))+")", append([]any{categoryID}, intsToAny(noteIDs)...)...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	affected, _ := result.RowsAffected()
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"updated_count": int(affected)}})
}

func (s *server) batchUpdateTags(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "note_ids and tags are required")
	if !ok {
		return
	}
	tags := stringArrayField(payload, "tags")
	if len(tags) == 0 {
		writeError(w, http.StatusBadRequest, "note_ids and tags are required")
		return
	}
	noteIDs, ok := requiredIntArrayField(w, payload, "note_ids", "note_ids and tags are required")
	if !ok {
		return
	}
	if len(noteIDs) > 500 {
		writeError(w, http.StatusBadRequest, "Maximum 500 notes per batch")
		return
	}
	mode := defaultStringField(payload, "mode", "append")
	if mode != "append" && mode != "replace" {
		writeError(w, http.StatusBadRequest, `mode must be "append" or "replace"`)
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	tagsAdded := 0
	affectedNotes := 0
	for _, noteID := range noteIDs {
		var existing int
		if err := tx.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existing); err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				continue
			}
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		affectedNotes++
		if mode == "replace" {
			if _, err := tx.Exec("DELETE FROM Note_Tags WHERE note_id = ?", noteID); err != nil {
				writeError(w, http.StatusInternalServerError, err.Error())
				return
			}
		}
		added, err := appendNoteTags(tx, noteID, tags)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		tagsAdded += added
		if _, err := tx.Exec("UPDATE Notes SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", noteID); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"affected_notes": affectedNotes, "tags_added": tagsAdded, "mode": mode,
	}})
}

func (s *server) batchDeleteNotes(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "note_ids is required")
	if !ok {
		return
	}
	rawNoteIDs, hasNoteIDs := payload["note_ids"]
	if !hasNoteIDs || rawNoteIDs == nil {
		writeError(w, http.StatusBadRequest, "note_ids is required")
		return
	}
	if rawList, ok := rawNoteIDs.([]any); ok && len(rawList) == 0 {
		writeError(w, http.StatusBadRequest, "note_ids is required")
		return
	}
	noteIDs, ok := requiredIntArrayField(w, payload, "note_ids", "note_ids is required")
	if !ok {
		return
	}
	if len(noteIDs) > 500 {
		writeError(w, http.StatusBadRequest, "Maximum 500 notes per batch")
		return
	}
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	refs, err := noteImageReferences(tx, noteIDs)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	for _, ref := range refs {
		s.cleanupNoteImages(tx, ref)
	}
	deleted, err := deleteNotesByID(tx, noteIDs)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted_count": deleted}})
}

func (s *server) getNoteHistory(w http.ResponseWriter, noteID int) {
	var title string
	if err := s.db.QueryRow("SELECT title FROM Notes WHERE id = ?", noteID).Scan(&title); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	rows, err := s.db.Query(`
		SELECT id, content, diff_summary, created_at
		FROM Note_History
		WHERE note_id = ?
		ORDER BY created_at DESC
		LIMIT 50`, noteID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()
	history := []response{}
	for rows.Next() {
		var id int
		var content, diffSummary, createdAt sql.NullString
		if err := rows.Scan(&id, &content, &diffSummary, &createdAt); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		history = append(history, response{
			"id": id, "content": nullableString(content), "diff_summary": nullableString(diffSummary), "created_at": sqliteDateTimeString(createdAt),
		})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"note_id": noteID, "note_title": title, "history": history, "total": len(history),
	}})
}

func (s *server) restoreNoteVersion(w http.ResponseWriter, noteID, historyID int) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	var currentContent string
	if err := tx.QueryRow("SELECT content FROM Notes WHERE id = ?", noteID).Scan(&currentContent); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	var historyContent string
	if err := tx.QueryRow("SELECT content FROM Note_History WHERE id = ? AND note_id = ?", historyID, noteID).Scan(&historyContent); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "History version not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, ?, ?)", noteID, currentContent, "還原前自動備份"); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("UPDATE Notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", historyContent, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "message": "Note restored successfully"})
}

func (s *server) deleteNoteHistory(w http.ResponseWriter, noteID int) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	var existing int
	if err := tx.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existing); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	result, err := tx.Exec("DELETE FROM Note_History WHERE note_id = ?", noteID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	deleted, _ := result.RowsAffected()
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "message": fmt.Sprintf("Deleted %d history records", deleted), "data": response{"deleted_count": int(deleted)}})
}

func nullableString(value sql.NullString) string {
	if !value.Valid {
		return ""
	}
	return value.String
}

func sqliteDateTimeString(value sql.NullString) string {
	text := nullableString(value)
	if text == "" || !strings.Contains(text, "T") {
		return text
	}
	parsed, err := time.Parse(time.RFC3339Nano, text)
	if err != nil {
		return text
	}
	return parsed.Format("2006-01-02 15:04:05")
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
