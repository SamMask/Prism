package main

import (
	"bytes"
	"database/sql"
	"embed"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"image"
	_ "image/gif"
	_ "image/jpeg"
	_ "image/png"
	"io"
	"io/fs"
	"log"
	"mime"
	_ "modernc.org/sqlite"
	"net"
	"net/http"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync/atomic"
	"time"
)

const expectedSchemaVersion = 17
const sqliteBusyTimeoutMS = 5000
const sqlitePragmaQueryOnlyOn = "PRAGMA query_only = ON"
const sqlitePragmaQueryOnlyOff = "PRAGMA query_only = OFF"
const maxAttachmentFileBytes int64 = 1048576
const separationThreshold = 5000
const separationPreviewLength = 500
const noteListContentPreviewLength = 500
const maxAttachmentScanFiles = 200
const maxAttachmentScanBytes int64 = 5242880
const maxAttachmentScanDuration = 250 * time.Millisecond
const maxUploadFileBytes int64 = 5 * 1024 * 1024
const attachmentUploadMultipartOverheadBytes int64 = 64 * 1024
const maxMarkdownImportBytes int64 = 2 * 1024 * 1024
const maxExportImages = 100
const defaultBackupKeepCount = 3
const maxBackupKeepCount = 10

// restartExitCode is returned when the process restarts itself to finish a DB
// restore. A supervisor (systemd Restart=, or a launcher loop) treats it as a
// signal to relaunch; standalone .exe builds re-exec themselves instead.
const restartExitCode = 42

// pendingRestoreMarker lives in the config dir. When present at startup, the
// named managed backup is swapped in for the live DB BEFORE any connection is
// opened — the only point where no connection holds the file, so it is a plain
// file copy with no live-swap risk.
const pendingRestoreMarker = "pending-restore.json"
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
	desktopShellDefault                            = "0"
)

type server struct {
	db          *sql.DB
	runtime     runtimeConfig
	csrfEnabled atomic.Bool
	httpServer  *http.Server
	// restart, when set, performs the process restart for a staged DB restore.
	// main wires it to triggerRestart; tests override it to avoid os.Exit.
	restart func()
}

// csrfDisabledMarker, when present in the data dir, turns CSRF protection off.
// Absence (the default) means CSRF is enabled.
const csrfDisabledMarker = ".csrf_disabled"

type runtimeConfig struct {
	addr                     string
	dbPath                   string
	dataDir                  string
	uploadsDir               string
	attachmentsDir           string
	notesDir                 string
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
	enableUploadDelete       bool
	enableMediaCleanup       bool
	enableImportExport       bool
	enableServerSystem       bool
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
	enableUploadDelete := flag.Bool("enable-upload-delete", envBool("PRISM_GO_ENABLE_UPLOAD_DELETE"), "enable local/copied-data POST /api/upload/delete parity candidate")
	enableMediaCleanup := flag.Bool("enable-media-cleanup", envBool("PRISM_GO_ENABLE_MEDIA_CLEANUP"), "enable local/copied-DB-and-data media cleanup parity candidate")
	enableImportExport := flag.Bool("enable-import-export", envBool("PRISM_GO_ENABLE_IMPORT_EXPORT"), "enable local/copied-DB-and-data import/export parity candidate")
	enableServerSystem := flag.Bool("enable-server-system", envBool("PRISM_GO_ENABLE_SERVER_SYSTEM"), "enable local/copied-DB-and-data server/system/config parity candidate")
	thumbnailInput := flag.String("thumbnail-input", "", "encode this local image file as a Prism WebP thumbnail and exit")
	thumbnailOutput := flag.String("thumbnail-output", "", "thumbnail output path for --thumbnail-input")
	desktopShell := flag.Bool("desktop-shell", desktopShellDefaultEnabled(), "run Prism as a Windows desktop shell with WebView2, tray, and an in-process Go runtime")
	desktopWebViewOnly := flag.Bool("desktop-webview-only", false, "run only the Windows WebView2/tray shell with a placeholder page")
	desktopShellSmoke := flag.Bool("desktop-shell-smoke", false, "start the desktop runtime host, wait for /healthz, then shut it down without opening WebView2")
	desktopSelfTest := flag.Bool("desktop-self-test", false, "close the desktop shell automatically after a bounded message-loop self-test")
	desktopDebug := flag.Bool("desktop-debug", false, "enable WebView2 developer tools/context menu for debug builds")
	desktopTitle := flag.String("desktop-title", "Prism", "desktop shell window title")
	desktopURL := flag.String("desktop-url", "", "desktop shell URL target; defaults to the in-process Go runtime")
	desktopLogPath := flag.String("desktop-log", "", "desktop shell log path; defaults to data-dir/logs/desktop-shell.log in --desktop-shell mode")
	desktopMutexName := flag.String("desktop-mutex", "Global\\PrismDesktopShell", "named mutex used to keep one desktop instance")
	flag.Parse()

	if *thumbnailInput != "" || *thumbnailOutput != "" {
		if err := runThumbnailCLI(*thumbnailInput, *thumbnailOutput); err != nil {
			log.Fatal(err)
		}
		return
	}

	desktopOpts := desktopShellOptions{
		title:     *desktopTitle,
		targetURL: *desktopURL,
		logPath:   *desktopLogPath,
		mutexName: *desktopMutexName,
		debug:     *desktopDebug,
		selfTest:  *desktopSelfTest,
	}
	if *desktopWebViewOnly {
		if err := runDesktopShellWebViewOnly(desktopOpts); err != nil {
			log.Fatal(err)
		}
		return
	}

	if (*desktopShell || *desktopShellSmoke) && strings.TrimSpace(*dataDir) == "" {
		defaultDataDir, err := resolveDesktopDataDir(*desktopShellSmoke)
		if err != nil {
			log.Fatal(err)
		}
		*dataDir = defaultDataDir
	}
	if (*desktopShell || *desktopShellSmoke) && strings.TrimSpace(*dbPath) == "" && strings.TrimSpace(*dataDir) != "" {
		*dbPath = filepath.Join(*dataDir, "prism_desktop_dev.db")
	}
	if *desktopShell || *desktopShellSmoke {
		*enableTagWrite = true
		*enableCategoryWrite = true
		*enableNotesWrite = true
		*enableAttachmentTextRead = true
		*enableAttachmentRawRead = true
		*enableAttachmentWrite = true
		*enableUploadWrite = true
		*enableThumbnailWrite = true
		*enableUploadURLWrite = true
		*enableUploadDelete = true
		*enableMediaCleanup = true
		*enableImportExport = true
		*enableServerSystem = true
	}

	cfg, err := resolveRuntimeConfig(*addr, *dbPath, *dataDir, *enableTagWrite, *enableCategoryWrite, *enableNotesWrite, *enableAttachmentTextRead, *enableThumbnailWrite, *enableUploadURLWrite, *enableAttachmentWrite, *enableAttachmentRawRead, *enableUploadWrite, *enableUploadDelete, *enableMediaCleanup, *enableImportExport, *enableServerSystem)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("using data dir %s", cfg.dataDir)
	log.Printf("using database %s", cfg.dbPath)

	if *desktopShellSmoke {
		if err := runDesktopShellSmoke(cfg, desktopOpts); err != nil {
			log.Fatal(err)
		}
		return
	}
	if *desktopShell {
		if err := runDesktopShellRuntime(cfg, desktopOpts); err != nil {
			log.Fatal(err)
		}
		return
	}

	srv, cleanup, err := newRuntimeServer(cfg)
	if err != nil {
		log.Fatal(err)
	}
	defer cleanup()

	log.Printf("Prism Go runtime proof listening on %s", cfg.addr)
	if err := srv.listenAndServe(); err != nil {
		log.Fatal(err)
	}
	// A clean return means triggerRestart called Shutdown and now owns process
	// termination (os.Exit with the restart code, or re-exec). Block here so main
	// does not fall through and exit 0 first, which would suppress the restart.
	select {}
}

func desktopShellDefaultEnabled() bool {
	return strings.TrimSpace(desktopShellDefault) == "1" || envBool("PRISM_DESKTOP_SHELL_DEFAULT")
}

func newRuntimeServer(cfg runtimeConfig) (*server, func(), error) {
	// Apply any pending DB restore BEFORE opening the database. At this point no
	// connection holds the file, so swapping it in is a plain file copy.
	if err := applyPendingRestore(cfg); err != nil {
		return nil, nil, err
	}

	sqliteOwner, err := openRuntimeSQLite(&cfg)
	if err != nil {
		return nil, nil, err
	}
	cfg.sqliteQueryOnly = sqliteOwner.queryOnly
	db := sqliteOwner.db
	if err := verifySchemaVersion(db, expectedSchemaVersion); err != nil {
		sqliteOwner.close()
		return nil, nil, err
	}

	srv := &server{db: db, runtime: cfg}
	srv.restart = srv.triggerRestart
	srv.csrfEnabled.Store(!fileExists(filepath.Join(cfg.dataDir, csrfDisabledMarker)))
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
	mux.HandleFunc("/api/system/check-update", srv.handleCheckUpdate)
	mux.HandleFunc("/api/system/stats", srv.handleSystemStats)
	mux.HandleFunc("/api/system/vacuum", srv.handleSystemVacuum)
	mux.HandleFunc("/api/system/clear-history", srv.handleSystemClearHistory)
	mux.HandleFunc("/api/system/startup-preference", srv.handleStartupPreference)
	mux.HandleFunc("/api/system/csrf-protection", srv.handleCSRFProtection)
	mux.HandleFunc("/api/system/wal-checkpoint", srv.handleWALCheckpoint)
	mux.HandleFunc("/api/system/check-consistency", srv.handleCheckConsistency)
	mux.HandleFunc("/api/system/search-integrity/rebuild-fts", srv.handleSearchIntegrityRebuildFTS)
	mux.HandleFunc("/api/system/search-integrity", srv.handleSearchIntegrity)
	mux.HandleFunc("/api/system/port-config", srv.handlePortConfig)
	mux.HandleFunc("/api/server/hardware", srv.handleServerHardware)
	mux.HandleFunc("/api/server/logs", srv.handleServerLogs)
	mux.HandleFunc("/api/server/restart", srv.handleServerRestart)
	mux.HandleFunc("/api/server/backup/download", srv.handleBackupDownload)
	mux.HandleFunc("/api/server/backup/rotate", srv.handleBackupRotate)
	mux.HandleFunc("/api/server/backup/list", srv.handleBackupList)
	mux.HandleFunc("/api/server/backup/restore", srv.handleBackupRestore)
	mux.HandleFunc("/api/server/backup/", srv.handleBackupDelete)
	mux.HandleFunc("/api/server/version", srv.handleServerVersion)
	mux.HandleFunc("/api/prompt-options", srv.handlePromptOptions)
	mux.HandleFunc("/api/prompt-options/category/", srv.handlePromptOptionCategory)
	mux.HandleFunc("/api/prompt-options/template", srv.handlePromptOptionTemplate)
	mux.HandleFunc("/api/prompt-options/template/", srv.handlePromptOptionTemplateDelete)
	mux.HandleFunc("/api/wizard-options", srv.handleWizardOptions)
	mux.HandleFunc("/api/wizard-options/dimension/", srv.handleWizardOptionDimension)
	mux.HandleFunc("/api/cleanup/orphan-images", srv.handleCleanupOrphanImages)
	mux.HandleFunc("/api/cleanup/originals", srv.handleCleanupOriginals)
	mux.HandleFunc("/api/cleanup/broken-images", srv.handleCleanupBrokenImages)
	mux.HandleFunc("/api/export/json", srv.handleExportJSON)
	mux.HandleFunc("/api/export/markdown", srv.handleExportMarkdown)
	mux.HandleFunc("/api/export/db", srv.handleExportDB)
	mux.HandleFunc("/api/export/images", srv.handleExportImages)
	mux.HandleFunc("/api/import/json", srv.handleImportJSON)
	mux.HandleFunc("/api/upload/delete", srv.handleUploadDelete)
	mux.HandleFunc("/api/upload/extract-prompt", srv.handleExtractPrompt)
	mux.HandleFunc("/api/upload/url", srv.handleUploadURL)
	mux.HandleFunc("/api/upload", srv.handleUpload)
	mux.Handle("/", srv.staticHandler())

	srv.httpServer = &http.Server{
		Addr:    cfg.addr,
		Handler: logRequests(srv.csrfGate(mux)),
	}

	return srv, func() { _ = sqliteOwner.close() }, nil
}

func (srv *server) listenAndServe() error {
	if err := srv.httpServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
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
	if err := validateListenAddress(addr); err != nil {
		return runtimeConfig{}, err
	}
	enableAttachmentWrite := len(optionalAttachmentWrite) > 0 && optionalAttachmentWrite[0]
	enableAttachmentRawRead := len(optionalAttachmentWrite) > 1 && optionalAttachmentWrite[1]
	enableUploadWrite := len(optionalAttachmentWrite) > 2 && optionalAttachmentWrite[2]
	enableUploadDelete := len(optionalAttachmentWrite) > 3 && optionalAttachmentWrite[3]
	enableMediaCleanup := len(optionalAttachmentWrite) > 4 && optionalAttachmentWrite[4]
	enableImportExport := len(optionalAttachmentWrite) > 5 && optionalAttachmentWrite[5]
	enableServerSystem := len(optionalAttachmentWrite) > 6 && optionalAttachmentWrite[6]
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
	if (enableUploadWrite || enableThumbnailWrite || enableUploadURLWrite || enableUploadDelete || enableMediaCleanup) && filepath.Base(absDB) == "knowledge.db" && os.Getenv("PRISM_GO_ALLOW_PROD_UPLOADS") != "1" {
		return runtimeConfig{}, fmt.Errorf("refusing to enable upload writes with production-like database %s; use copied data or set PRISM_GO_ALLOW_PROD_UPLOADS=1", absDB)
	}
	if enableImportExport && filepath.Base(absDB) == "knowledge.db" && os.Getenv("PRISM_GO_ALLOW_PROD_IMPORT_EXPORT") != "1" {
		return runtimeConfig{}, fmt.Errorf("refusing to enable import/export with production-like database %s; use copied data or set PRISM_GO_ALLOW_PROD_IMPORT_EXPORT=1", absDB)
	}
	if enableServerSystem && filepath.Base(absDB) == "knowledge.db" && os.Getenv("PRISM_GO_ALLOW_PROD_SERVER_SYSTEM") != "1" {
		return runtimeConfig{}, fmt.Errorf("refusing to enable server/system routes with production-like database %s; use copied data or set PRISM_GO_ALLOW_PROD_SERVER_SYSTEM=1", absDB)
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
	notesDir, err := ensureDataSubdir(absData, "docs", "notes")
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
		notesDir:                 notesDir,
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
		enableUploadDelete:       enableUploadDelete,
		enableMediaCleanup:       enableMediaCleanup,
		enableImportExport:       enableImportExport,
		enableServerSystem:       enableServerSystem,
		freshDBInitNeeded:        freshDBInitNeeded,
		sqliteQueryOnly:          !(enableTagWrite || enableCategoryWrite || enableNotesWrite || enableAttachmentWrite || enableMediaCleanup || enableImportExport || enableServerSystem),
	}, nil
}

func validateListenAddress(addr string) error {
	addr = strings.TrimSpace(addr)
	if addr == "" {
		return errors.New("listen address is required")
	}
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return fmt.Errorf("invalid listen address %q: %w", addr, err)
	}
	if isLocalListenHost(host) {
		return nil
	}
	if os.Getenv("PRISM_GO_ALLOW_PUBLIC_BIND") == "1" {
		return nil
	}
	return fmt.Errorf("refusing non-local Go bind %q; Prism has no built-in auth/token layer, so use 127.0.0.1 or set PRISM_GO_ALLOW_PUBLIC_BIND=1 only behind trusted LAN/VPN/proxy auth", addr)
}

func isLocalListenHost(host string) bool {
	host = strings.Trim(strings.TrimSpace(host), "[]")
	if host == "" {
		return false
	}
	if strings.EqualFold(host, "localhost") {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
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
	return cfg.enableTagWrite || cfg.enableCategoryWrite || cfg.enableNotesWrite || cfg.enableAttachmentWrite || cfg.enableMediaCleanup || cfg.enableImportExport || cfg.enableServerSystem
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

func (s *server) staticHandler() http.Handler {
	sub, err := fs.Sub(embeddedDist, "web/dist")
	if err != nil {
		return http.NotFoundHandler()
	}
	files := http.FS(sub)
	fileServer := http.FileServer(files)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/api/") {
			writeError(w, http.StatusNotFound, "API route not found")
			return
		}
		if strings.HasPrefix(r.URL.Path, "/static/config/") {
			writeError(w, http.StatusNotFound, "Static config is available through API options routes")
			return
		}
		if r.URL.Path == "/static/uploads" {
			writeError(w, http.StatusNotFound, "File not found")
			return
		}
		if strings.HasPrefix(r.URL.Path, "/static/uploads/") {
			s.serveStaticUpload(w, r)
			return
		}
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

func (s *server) serveStaticUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		w.Header().Set("Allow", "GET, HEAD")
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		return
	}
	escapedName := strings.TrimPrefix(r.URL.EscapedPath(), "/static/uploads/")
	if strings.TrimSpace(escapedName) == "" {
		writeError(w, http.StatusNotFound, "File not found")
		return
	}
	name, err := url.PathUnescape(escapedName)
	if err != nil {
		writeError(w, http.StatusNotFound, "File not found")
		return
	}
	absPath, ok := s.resolveUploadFile(name)
	if !ok || staticUploadEscapesRoot(absPath, s.runtime.uploadsDir) {
		writeError(w, http.StatusNotFound, "File not found")
		return
	}
	file, err := os.Open(absPath)
	if err != nil {
		writeError(w, http.StatusNotFound, "File not found")
		return
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() {
		writeError(w, http.StatusNotFound, "File not found")
		return
	}
	if contentType := mime.TypeByExtension(filepath.Ext(absPath)); contentType != "" {
		w.Header().Set("Content-Type", contentType)
	}
	http.ServeContent(w, r, filepath.Base(absPath), info.ModTime(), file)
}

func staticUploadEscapesRoot(absPath, uploadsDir string) bool {
	root, err := filepath.Abs(uploadsDir)
	if err != nil {
		return true
	}
	target, err := filepath.Abs(absPath)
	if err != nil || !isSubpath(target, root) {
		return true
	}
	evaluatedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return true
	}
	evaluatedTarget, err := filepath.EvalSymlinks(target)
	if err != nil {
		return true
	}
	return !isSubpath(evaluatedTarget, evaluatedRoot)
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
		logPath := r.URL.EscapedPath()
		if logPath == "" {
			logPath = r.URL.Path
		}
		log.Printf("request method=%s path=%s status=%d duration_ms=%d", r.Method, logPath, recorder.status, time.Since(started).Milliseconds())
	})
}

// csrfProtect mirrors the legacy Flask Origin/Referer CSRF guard (app.py
// csrf_protect): for state-changing methods it requires that a present
// Origin/Referer be same-origin. Requests with neither header (curl, MCP and
// other non-browser API clients, which cannot be used for browser CSRF) pass
// through — only browser cross-site writes, which always carry an Origin, are
// blocked.
func csrfProtect(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// PATCH is intentionally omitted: the runtime exposes no PATCH route,
		// so a cross-origin PATCH 404s at the mux and never reaches a writer.
		switch r.Method {
		case http.MethodPost, http.MethodPut, http.MethodDelete:
			origin := r.Header.Get("Origin")
			referer := r.Header.Get("Referer")
			if origin == "" && referer == "" {
				break
			}
			allowed := csrfAllowedOrigins(r.Host)
			if !originAllowed(origin, allowed) && !originAllowed(referer, allowed) {
				writeError(w, http.StatusForbidden, "CSRF validation failed: Origin mismatch")
				return
			}
		}
		next.ServeHTTP(w, r)
	})
}

func csrfAllowedOrigins(host string) []string {
	if host == "" {
		host = "127.0.0.1"
	}
	allowed := []string{"http://" + host, "https://" + host}
	for _, o := range []string{"http://" + host, "https://" + host} {
		if strings.Contains(o, "127.0.0.1") {
			allowed = append(allowed, strings.Replace(o, "127.0.0.1", "localhost", 1))
		} else if strings.Contains(o, "localhost") {
			allowed = append(allowed, strings.Replace(o, "localhost", "127.0.0.1", 1))
		}
	}
	return append(allowed,
		"http://localhost:5173", "http://127.0.0.1:5173",
		"http://localhost:5174", "http://127.0.0.1:5174",
	)
}

func originAllowed(value string, allowed []string) bool {
	if value == "" {
		return false
	}
	parsed, err := url.Parse(value)
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return false
	}
	origin := parsed.Scheme + "://" + parsed.Host
	for _, a := range allowed {
		if origin == a {
			return true
		}
	}
	return false
}

// csrfGate applies csrfProtect only while CSRF protection is enabled (the
// default). The flag is toggled at runtime via /api/system/csrf-protection and
// persisted with the csrfDisabledMarker file, so changes take effect without a
// restart.
func (s *server) csrfGate(next http.Handler) http.Handler {
	protected := csrfProtect(next)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if s.csrfEnabled.Load() {
			protected.ServeHTTP(w, r)
			return
		}
		next.ServeHTTP(w, r)
	})
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
