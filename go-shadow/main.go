package main

import (
	"archive/zip"
	"bytes"
	"compress/zlib"
	"context"
	"crypto/md5"
	"database/sql"
	"embed"
	"encoding/base64"
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
	"mime/multipart"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync/atomic"
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
const separationThreshold = 5000
const separationPreviewLength = 500
const maxAttachmentScanFiles = 200
const maxAttachmentScanBytes int64 = 5242880
const maxAttachmentScanDuration = 250 * time.Millisecond
const maxUploadFileBytes int64 = 5 * 1024 * 1024
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
		defaultDataDir, err := defaultDesktopDataDir()
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
		log.Printf("request method=%s path=%s status=%d duration_ms=%d", r.Method, r.URL.RequestURI(), recorder.status, time.Since(started).Milliseconds())
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
			if !originPrefixAllowed(origin, allowed) && !originPrefixAllowed(referer, allowed) {
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

func originPrefixAllowed(value string, allowed []string) bool {
	if value == "" {
		return false
	}
	for _, a := range allowed {
		if strings.HasPrefix(value, a) {
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
			"security": response{
				"auth":                "none",
				"public_bind_default": "blocked",
				"public_bind_env":     "PRISM_GO_ALLOW_PUBLIC_BIND=1",
				"exposure_policy":     "trusted LAN/VPN/proxy-auth only; do not expose Prism directly to the public internet",
			},
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

func (s *server) handleCheckUpdate(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	if !s.runtime.enableServerSystem {
		writeError(w, http.StatusMethodNotAllowed, "Server/system route is disabled")
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"current_version": prismVersion(),
			"latest_version":  nil,
			"has_update":      false,
			"release_url":     "",
			"release_notes":   "",
			"message":         "未設定更新來源",
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
	if s.runtime.enableUploadDelete {
		parts = append(parts, "local-upload-delete")
	}
	if s.runtime.enableMediaCleanup {
		parts = append(parts, "local-media-cleanup")
	}
	if s.runtime.enableImportExport {
		parts = append(parts, "local-import-export")
	}
	if s.runtime.enableServerSystem {
		parts = append(parts, "local-server-system")
	}
	return strings.Join(parts, "+")
}

func (s *server) requireServerSystem(w http.ResponseWriter, r *http.Request) bool {
	if !s.runtime.enableServerSystem {
		_, _ = io.Copy(io.Discard, r.Body)
		writeError(w, http.StatusMethodNotAllowed, "Server/system route is disabled")
		return false
	}
	return true
}

func requireMethod(w http.ResponseWriter, r *http.Request, method string) bool {
	if r.Method == method {
		return true
	}
	w.Header().Set("Allow", method)
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	return false
}

func requireLocalhostRequest(w http.ResponseWriter, r *http.Request) bool {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		host = r.RemoteAddr
	}
	if host == "127.0.0.1" || host == "::1" || host == "localhost" {
		return true
	}
	writeError(w, http.StatusForbidden, "Server management API is accessible from localhost only")
	return false
}

func (s *server) handleSystemStats(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	dbSize := fileSizeOrZero(s.runtime.dbPath)
	notesCount, err := s.countRows("Notes", "")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	tagsCount, err := s.countRows("Tags", "")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	historyCount, err := s.countRows("Note_History", "")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	archivedCount, _ := s.countRows("Notes", "WHERE is_archived = 1")
	uploadSize, err := directorySize(s.runtime.uploadsDir)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"database": response{
				"size_bytes":     dbSize,
				"size_mb":        roundMB(dbSize),
				"notes_count":    notesCount,
				"archived_count": archivedCount,
				"tags_count":     tagsCount,
				"history_count":  historyCount,
			},
			"uploads": response{
				"size_bytes": uploadSize,
				"size_mb":    roundMB(uploadSize),
			},
		},
	})
}

func (s *server) handleSystemVacuum(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !s.requireServerSystem(w, r) {
		return
	}
	sizeBefore := fileSizeOrZero(s.runtime.dbPath)
	_, _ = s.db.Exec("PRAGMA wal_checkpoint(TRUNCATE)")
	_, _ = s.db.Exec("INSERT INTO Notes_FTS(Notes_FTS) VALUES('rebuild')")
	if _, err := s.db.Exec("VACUUM"); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	sizeAfter := fileSizeOrZero(s.runtime.dbPath)
	freed := sizeBefore - sizeAfter
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"size_before":    sizeBefore,
			"size_after":     sizeAfter,
			"freed_bytes":    freed,
			"size_before_mb": roundMB(sizeBefore),
			"size_after_mb":  roundMB(sizeAfter),
			"freed_mb":       roundMB(freed),
		},
	})
}

func (s *server) handleSystemClearHistory(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !s.requireServerSystem(w, r) {
		return
	}
	count, err := s.countRows("Note_History", "")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := s.db.Exec("DELETE FROM Note_History"); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data":   response{"deleted_count": count},
	})
}

func (s *server) handleStartupPreference(w http.ResponseWriter, r *http.Request) {
	if !s.requireServerSystem(w, r) {
		return
	}
	yesFile := filepath.Join(s.runtime.dataDir, ".auto_open_yes")
	noFile := filepath.Join(s.runtime.dataDir, ".auto_open_no")
	switch r.Method {
	case http.MethodGet:
		var value any
		if fileExists(yesFile) {
			value = true
		} else if fileExists(noFile) {
			value = false
		}
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"auto_open_browser": value}})
	case http.MethodPost:
		payload, ok := decodeJSONObject(w, r, "Request body is required")
		if !ok {
			return
		}
		raw, exists := payload["auto_open_browser"]
		autoOpen, ok := raw.(bool)
		if !exists || !ok {
			writeError(w, http.StatusBadRequest, "auto_open_browser is required")
			return
		}
		_ = os.Remove(yesFile)
		_ = os.Remove(noFile)
		target := noFile
		content := []byte("0")
		if autoOpen {
			target = yesFile
			content = []byte("1")
		}
		if err := os.WriteFile(target, content, 0644); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"auto_open_browser": autoOpen}})
	default:
		w.Header().Set("Allow", "GET, POST")
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) handleCSRFProtection(w http.ResponseWriter, r *http.Request) {
	if !s.requireServerSystem(w, r) {
		return
	}
	markerPath := filepath.Join(s.runtime.dataDir, csrfDisabledMarker)
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"csrf_protection": s.csrfEnabled.Load()}})
	case http.MethodPost:
		payload, ok := decodeJSONObject(w, r, "csrf_protection is required")
		if !ok {
			return
		}
		raw, exists := payload["csrf_protection"]
		enabled, ok := raw.(bool)
		if !exists || !ok {
			writeError(w, http.StatusBadRequest, "csrf_protection is required")
			return
		}
		if enabled {
			if err := os.Remove(markerPath); err != nil && !os.IsNotExist(err) {
				writeError(w, http.StatusInternalServerError, err.Error())
				return
			}
		} else if err := os.WriteFile(markerPath, []byte("1"), 0644); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		s.csrfEnabled.Store(enabled)
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"csrf_protection": enabled}})
	default:
		w.Header().Set("Allow", "GET, POST")
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) handleWALCheckpoint(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !s.requireServerSystem(w, r) {
		return
	}
	walPath := s.runtime.dbPath + "-wal"
	walSizeBefore := fileSizeOrZero(walPath)
	var blocked, pagesCheckpointed, pagesMoved int
	if err := s.db.QueryRow("PRAGMA wal_checkpoint(TRUNCATE)").Scan(&blocked, &pagesCheckpointed, &pagesMoved); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"wal_size_before":    walSizeBefore,
			"wal_size_before_kb": roundKB(walSizeBefore),
			"wal_size_after":     fileSizeOrZero(walPath),
			"pages_checkpointed": pagesCheckpointed,
			"pages_moved":        pagesMoved,
			"blocked":            blocked,
			"message":            "WAL 日誌已合併至主資料庫",
		},
	})
}

func (s *server) handleCheckConsistency(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	orphanNoteTags, err := s.scalarInt(`
		SELECT COUNT(*) FROM Note_Tags nt
		LEFT JOIN Notes n ON nt.note_id = n.id
		WHERE n.id IS NULL`)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	unusedTags, err := s.scalarInt(`
		SELECT COUNT(*) FROM Tags t
		LEFT JOIN Note_Tags nt ON t.id = nt.tag_id
		WHERE nt.tag_id IS NULL`)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	nullCategoryID, err := s.scalarInt("SELECT COUNT(*) FROM Notes WHERE category_id IS NULL")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	fkStatus, err := s.scalarInt("PRAGMA foreign_keys")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	health := "healthy"
	if orphanNoteTags >= 5 {
		health = "critical"
	} else if orphanNoteTags > 0 {
		health = "warning"
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"orphan_note_tags": orphanNoteTags,
			"unused_tags":      unusedTags,
			"null_category_id": nullCategoryID,
			"fk_status":        fkStatus,
			"fk_enabled":       fkStatus == 1,
			"health":           health,
		},
	})
}

func (s *server) handleSearchIntegrity(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	notesCount, err := s.scalarInt("SELECT COUNT(*) FROM Notes")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	integrityStatus := "ok"
	integrityMessage := ""
	ftsRows, err := s.scalarInt("SELECT COUNT(*) FROM Notes_FTS")
	if err != nil {
		ftsRows = -1
		integrityStatus = "needs_rebuild"
		integrityMessage = err.Error()
	}
	missingFTSRows := -1
	if integrityMessage == "" {
		missingFTSRows, err = s.scalarInt(`
		SELECT COUNT(*) FROM Notes n
		LEFT JOIN Notes_FTS fts ON fts.rowid = n.id
		WHERE fts.rowid IS NULL`)
		if err != nil {
			integrityStatus = "needs_rebuild"
			integrityMessage = err.Error()
		}
	}
	orphanFTSRows := -1
	if integrityMessage == "" {
		orphanFTSRows, err = s.scalarInt(`
		SELECT COUNT(*) FROM Notes_FTS fts
		LEFT JOIN Notes n ON n.id = fts.rowid
		WHERE n.id IS NULL`)
		if err != nil {
			integrityStatus = "needs_rebuild"
			integrityMessage = err.Error()
		}
	}
	if integrityMessage == "" {
		err = s.checkNotesFTSIntegrity()
	}
	if err != nil {
		integrityStatus = "needs_rebuild"
		integrityMessage = err.Error()
	} else if missingFTSRows > 0 || orphanFTSRows > 0 || notesCount != ftsRows {
		integrityStatus = "needs_rebuild"
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"status":           integrityStatus,
			"notes_count":      notesCount,
			"fts_rows":         ftsRows,
			"missing_fts_rows": missingFTSRows,
			"orphan_fts_rows":  orphanFTSRows,
			"rebuild_route":    "/api/system/search-integrity/rebuild-fts",
			"auto_repair":      false,
			"integrity_error":  integrityMessage,
		},
	})
}

func (s *server) checkNotesFTSIntegrity() error {
	_, err := s.db.Exec("INSERT INTO Notes_FTS(Notes_FTS, rank) VALUES('integrity-check', 1)")
	return err
}

func (s *server) handleSearchIntegrityRebuildFTS(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !s.requireServerSystem(w, r) {
		return
	}
	notesCountBefore, err := s.scalarInt("SELECT COUNT(*) FROM Notes")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := s.db.Exec("INSERT INTO Notes_FTS(Notes_FTS) VALUES('rebuild')"); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	ftsRowsAfter, err := s.scalarInt("SELECT COUNT(*) FROM Notes_FTS")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"notes_count": notesCountBefore,
			"fts_rows":    ftsRowsAfter,
			"message":     "FTS index rebuilt",
		},
	})
}

func (s *server) handlePortConfig(w http.ResponseWriter, r *http.Request) {
	if !s.requireServerSystem(w, r) {
		return
	}
	configPath := filepath.Join(s.runtime.dataDir, ".port_config")
	config, err := loadPortConfig(configPath)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	switch r.Method {
	case http.MethodGet:
		config["current_port"] = currentRequestPort(r)
		writeJSON(w, http.StatusOK, response{"status": "success", "data": config})
	case http.MethodPost:
		payload, ok := decodeJSONObject(w, r, "Request body is required")
		if !ok {
			return
		}
		if raw, exists := payload["preferred_port"]; exists {
			port, ok := intValue(raw)
			if !ok || port < 1024 || port > 65535 {
				writeError(w, http.StatusBadRequest, "端口必須在 1024-65535 之間")
				return
			}
			config["preferred_port"] = port
		}
		if raw, exists := payload["fallback_enabled"]; exists {
			config["fallback_enabled"] = boolValue(raw)
		}
		if raw, exists := payload["fallback_range"]; exists {
			fallbackRange, ok := intValue(raw)
			if !ok || fallbackRange < 1 || fallbackRange > 100 {
				writeError(w, http.StatusBadRequest, "備用範圍必須在 1-100 之間")
				return
			}
			config["fallback_range"] = fallbackRange
		}
		if err := writeIndentedJSON(configPath, config); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, response{"status": "success", "data": config, "message": "端口設定已儲存，下次啟動時生效"})
	default:
		w.Header().Set("Allow", "GET, POST")
		writeError(w, http.StatusMethodNotAllowed, "method not allowed")
	}
}

func (s *server) handleServerHardware(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	hostname, _ := os.Hostname()
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"cpu_temp": readCPUTempC(),
			"memory":   readMemoryInfo(),
			"disk":     readDiskInfo(s.runtime.dataDir),
			"database": response{
				"size_mb":     roundMB(fileSizeOrZero(s.runtime.dbPath)),
				"wal_size_mb": roundMB(fileSizeOrZero(s.runtime.dbPath + "-wal")),
			},
			"platform": response{
				"system":     runtime.GOOS,
				"machine":    runtime.GOARCH,
				"hostname":   hostname,
				"go_version": runtime.Version(),
			},
			"service_management": response{
				"available": false,
				"reason":    "Go local server-system candidate does not restart host services",
			},
			"uptime_seconds": readUptimeSeconds(),
		},
	})
}

func (s *server) handleServerLogs(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	linesCount := 100
	if raw := strings.TrimSpace(r.URL.Query().Get("lines")); raw != "" {
		if parsed, err := strconv.Atoi(raw); err == nil {
			linesCount = parsed
		}
	}
	if linesCount < 1 {
		linesCount = 1
	}
	if linesCount > 500 {
		linesCount = 500
	}
	levelFilter := strings.ToUpper(strings.TrimSpace(r.URL.Query().Get("level")))
	if levelFilter == "" {
		levelFilter = "ALL"
	}
	logPath := s.serverLogPath()
	if logPath == "" {
		writeJSON(w, http.StatusOK, response{
			"status": "success",
			"data": response{
				"lines":       []string{},
				"total_lines": 0,
				"log_file":    "app.log",
				"message":     "日誌檔案尚未建立",
			},
		})
		return
	}
	lines, err := readTextLines(logPath)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	filtered := lines
	if levelFilter != "ALL" {
		filtered = []string{}
		token := "[" + levelFilter + "]"
		for _, line := range lines {
			if strings.Contains(line, token) {
				filtered = append(filtered, line)
			}
		}
	}
	tail := filtered
	if len(tail) > linesCount {
		tail = tail[len(tail)-linesCount:]
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"lines":          tail,
			"total_lines":    len(lines),
			"filtered_lines": len(filtered),
			"log_file":       filepath.Base(logPath),
			"log_size_kb":    roundKB(fileSizeOrZero(logPath)),
		},
	})
}

func (s *server) handleServerRestart(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status":  "success",
		"message": "Go local server-system candidate acknowledged restart request without restarting host services",
		"data": response{
			"service_management": response{
				"available": false,
				"reason":    "systemd restart is intentionally disabled in the local Go candidate",
			},
		},
	})
}

func (s *server) handleBackupDownload(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	if !fileExists(s.runtime.dbPath) {
		writeError(w, http.StatusNotFound, "資料庫檔案不存在")
		return
	}
	// Download hands the user a consistent snapshot to store wherever they like.
	// It intentionally does NOT leave a retained managed backup on the server —
	// server-side retention is the job of /api/server/backup/rotate. The snapshot
	// is a transient temp file, removed after it is served.
	tmp, err := os.CreateTemp("", "prism-download-*.db")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	tmpPath := tmp.Name()
	defer os.Remove(tmpPath)
	in, err := os.Open(s.runtime.dbPath)
	if err != nil {
		tmp.Close()
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	_, copyErr := io.Copy(tmp, in)
	in.Close()
	if copyErr == nil {
		copyErr = tmp.Sync()
	}
	tmp.Close()
	if copyErr != nil {
		writeError(w, http.StatusInternalServerError, copyErr.Error())
		return
	}
	w.Header().Set("Content-Type", "application/x-sqlite3")
	w.Header().Set("Content-Disposition", "attachment; filename="+managedBackupName())
	http.ServeFile(w, r, tmpPath)
}

func (s *server) handleBackupRotate(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	payload, err := decodeOptionalJSONObject(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}
	keepCount := parseBackupKeepCount(payload, defaultBackupKeepCount)
	backupName := managedBackupName()
	backupPath := filepath.Join(s.runtime.backupsDir, backupName)
	if err := copyFileExclusive(s.runtime.dbPath, backupPath); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	kept, deleted, totalSize, err := enforceBackupRetention(s.runtime.backupsDir, keepCount, backupName)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"new_backup":      backupName,
			"kept_backups":    backupResponseItems(kept),
			"deleted_backups": deleted,
			"total_size_mb":   roundMB(totalSize),
		},
	})
}

type pendingRestore struct {
	Backup      string `json:"backup"`
	RequestedAt string `json:"requested_at"`
}

// handleBackupRestore stages a managed backup to replace the live DB and then
// restarts the process. The actual file swap happens at the next startup
// (applyPendingRestore), when no connection holds the DB — so there is no
// live-swap risk. The chosen backup is validated here so a broken file is
// rejected before we agree to restart.
func (s *server) handleBackupRestore(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	payload, err := decodeOptionalJSONObject(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}
	filename, _ := payload["backup"].(string)
	filename = strings.TrimSpace(filename)
	if !isManagedBackupFilename(filename) {
		writeError(w, http.StatusBadRequest, "無效的備份檔名")
		return
	}
	backupPath := filepath.Join(s.runtime.backupsDir, filename)
	if !isSubpath(backupPath, s.runtime.backupsDir) || !fileExists(backupPath) {
		writeError(w, http.StatusNotFound, "備份檔不存在")
		return
	}
	if err := validateSQLiteBackup(backupPath); err != nil {
		writeError(w, http.StatusUnprocessableEntity, "備份檔無法還原："+err.Error())
		return
	}
	marker := pendingRestore{Backup: filename, RequestedAt: time.Now().UTC().Format(time.RFC3339)}
	data, err := json.MarshalIndent(marker, "", "  ")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	markerPath := filepath.Join(s.runtime.configDir, pendingRestoreMarker)
	if err := os.WriteFile(markerPath, data, 0600); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"restarting": true,
			"backup":     filename,
			"supervised": isSupervised(),
		},
	})
	if s.restart != nil {
		s.restart()
	} else {
		s.triggerRestart()
	}
}

// applyPendingRestore swaps in a staged backup before the DB is opened. Any
// problem (missing/invalid marker or backup) is logged and skipped so the
// process always starts on a usable DB rather than refusing to boot.
func applyPendingRestore(cfg runtimeConfig) error {
	markerPath := filepath.Join(cfg.configDir, pendingRestoreMarker)
	raw, err := os.ReadFile(markerPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	// Always drop the marker so a bad one can never loop the restore forever.
	defer os.Remove(markerPath)

	var m pendingRestore
	if err := json.Unmarshal(raw, &m); err != nil {
		log.Printf("pending restore marker unreadable, skipping: %v", err)
		return nil
	}
	if !isManagedBackupFilename(m.Backup) {
		log.Printf("pending restore names invalid backup %q, skipping", m.Backup)
		return nil
	}
	backupPath := filepath.Join(cfg.backupsDir, m.Backup)
	if !isSubpath(backupPath, cfg.backupsDir) || !fileExists(backupPath) {
		log.Printf("pending restore backup %q not found, skipping", m.Backup)
		return nil
	}
	if err := validateSQLiteBackup(backupPath); err != nil {
		log.Printf("pending restore backup %q failed validation (%v), keeping current DB", m.Backup, err)
		return nil
	}
	// Keep an undo copy of the current DB before overwriting it. The
	// prism_pre_restore_ prefix is intentionally NOT a managed-backup name, so
	// rotation never deletes the user's safety net.
	if fileExists(cfg.dbPath) {
		safety := filepath.Join(cfg.backupsDir, fmt.Sprintf("prism_pre_restore_%s.db", time.Now().Format("20060102_150405")))
		if err := copyFileExclusive(cfg.dbPath, safety); err != nil {
			return fmt.Errorf("could not safety-copy current DB before restore: %w", err)
		}
	}
	if err := copyFileReplace(backupPath, cfg.dbPath); err != nil {
		return fmt.Errorf("restore copy failed: %w", err)
	}
	_ = os.Remove(cfg.dbPath + "-wal")
	_ = os.Remove(cfg.dbPath + "-shm")
	log.Printf("restored database from backup %s", m.Backup)
	return nil
}

// validateSQLiteBackup confirms a file is an intact Prism SQLite database. The
// schema version may be older than current; startup migrations handle that.
func validateSQLiteBackup(path string) error {
	db, err := sql.Open("sqlite", sqliteDSN(path, false))
	if err != nil {
		return err
	}
	defer db.Close()
	var result string
	if err := db.QueryRow("PRAGMA integrity_check").Scan(&result); err != nil {
		return fmt.Errorf("無法開啟資料庫：%w", err)
	}
	if result != "ok" {
		return fmt.Errorf("資料庫完整性檢查未通過：%s", result)
	}
	var version string
	if err := db.QueryRow("SELECT value FROM Schema_Meta WHERE key = 'schema_version'").Scan(&version); err != nil {
		return fmt.Errorf("不是有效的 Prism 資料庫：%w", err)
	}
	return nil
}

// copyFileReplace atomically replaces dst with a copy of src (temp file + rename).
func copyFileReplace(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	tmp := dst + ".restore.tmp"
	out, err := os.OpenFile(tmp, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0600)
	if err != nil {
		return err
	}
	if _, err := io.Copy(out, in); err != nil {
		out.Close()
		os.Remove(tmp)
		return err
	}
	if err := out.Sync(); err != nil {
		out.Close()
		os.Remove(tmp)
		return err
	}
	if err := out.Close(); err != nil {
		os.Remove(tmp)
		return err
	}
	return os.Rename(tmp, dst)
}

// isSupervised reports whether an external supervisor (systemd, a launcher loop)
// will relaunch the process on exit. systemd always sets INVOCATION_ID.
func isSupervised() bool {
	return os.Getenv("PRISM_GO_SUPERVISED") == "1" || os.Getenv("INVOCATION_ID") != ""
}

// triggerRestart drains the server, closes the DB, and restarts the process so
// the staged restore is applied at startup. Supervised processes exit with
// restartExitCode; standalone .exe builds re-exec themselves.
func (s *server) triggerRestart() {
	go func() {
		time.Sleep(250 * time.Millisecond) // let the HTTP response flush first
		if s.httpServer != nil {
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			_ = s.httpServer.Shutdown(ctx)
			cancel()
		}
		if s.db != nil {
			_, _ = s.db.Exec("PRAGMA wal_checkpoint(TRUNCATE)")
			_ = s.db.Close()
		}
		if isSupervised() {
			os.Exit(restartExitCode)
		}
		if err := reexecSelf(); err != nil {
			log.Printf("self re-exec failed (%v); exiting with restart code", err)
			os.Exit(restartExitCode)
		}
		os.Exit(0)
	}()
}

func reexecSelf() error {
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	argv := append([]string{exe}, os.Args[1:]...)
	proc, err := os.StartProcess(exe, argv, &os.ProcAttr{
		Files: []*os.File{os.Stdin, os.Stdout, os.Stderr},
		Env:   os.Environ(),
	})
	if err != nil {
		return err
	}
	return proc.Release()
}

func (s *server) handleBackupList(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	backups, err := listManagedBackups(s.runtime.backupsDir)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	var totalSize int64
	for _, backup := range backups {
		totalSize += backup.SizeBytes
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"backups":       backupResponseItems(backups),
			"count":         len(backups),
			"total_size_mb": roundMB(totalSize),
		},
	})
}

func (s *server) handleBackupDelete(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodDelete) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	filename, err := url.PathUnescape(strings.TrimPrefix(r.URL.Path, "/api/server/backup/"))
	if err != nil || !isManagedBackupFilename(filename) {
		writeError(w, http.StatusBadRequest, "無效的備份檔名")
		return
	}
	backupPath := filepath.Join(s.runtime.backupsDir, filename)
	if !isSubpath(backupPath, s.runtime.backupsDir) {
		writeError(w, http.StatusBadRequest, "無效的備份檔名")
		return
	}
	if !fileExists(backupPath) {
		writeError(w, http.StatusNotFound, "備份檔案不存在")
		return
	}
	if err := os.Remove(backupPath); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted": filename}})
}

func (s *server) handleServerVersion(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"version":   prismVersion(),
			"changelog": []response{},
			"is_frozen": false,
			"v2_mode":   envBool("PRISM_V2"),
			"platform":  runtime.GOOS,
			"go_runtime": response{
				"api_surface": s.apiSurface(),
				"query_only":  s.runtime.sqliteQueryOnly,
			},
		},
	})
}

func (s *server) handlePromptOptions(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": config})
}

func (s *server) handlePromptOptionCategory(w http.ResponseWriter, r *http.Request) {
	if !s.requireServerSystem(w, r) {
		return
	}
	parts := routeParts(strings.TrimPrefix(r.URL.Path, "/api/prompt-options/category/"))
	if len(parts) == 1 && r.Method == http.MethodPost {
		s.addPromptOption(w, r, parts[0])
		return
	}
	if len(parts) == 2 && r.Method == http.MethodPut {
		s.updatePromptOption(w, r, parts[0], parts[1])
		return
	}
	if len(parts) == 2 && r.Method == http.MethodDelete {
		s.deletePromptOption(w, r, parts[0], parts[1])
		return
	}
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func (s *server) handlePromptOptionTemplate(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !s.requireServerSystem(w, r) {
		return
	}
	payload, ok := decodeJSONObject(w, r, "Request body is required")
	if !ok {
		return
	}
	name := strings.TrimSpace(stringField(payload, "name"))
	if name == "" {
		writeError(w, http.StatusBadRequest, "name is required")
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	templateID := strings.TrimSpace(stringField(payload, "id"))
	if templateID == "" {
		templateID = strings.ReplaceAll(strings.ReplaceAll(strings.ToLower(name), " ", "-"), ":", "")
	}
	template := map[string]any{
		"id":       templateID,
		"name":     name,
		"preset":   payload["preset"],
		"isCustom": true,
	}
	if template["preset"] == nil {
		template["preset"] = map[string]any{}
	}
	templates, _ := config["quickTemplates"].([]any)
	action := "created"
	index := len(templates)
	for i, item := range templates {
		if obj, ok := item.(map[string]any); ok && stringValue(obj["id"]) == templateID {
			templates[i] = template
			action = "updated"
			index = i
			break
		}
	}
	if action == "created" {
		templates = append(templates, template)
	}
	config["quickTemplates"] = templates
	status := http.StatusCreated
	if action == "updated" {
		status = http.StatusOK
	}
	if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, status, response{"status": "success", "data": response{"action": action, "template": template, "index": index}})
}

func (s *server) handlePromptOptionTemplateDelete(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodDelete) || !s.requireServerSystem(w, r) {
		return
	}
	parts := routeParts(strings.TrimPrefix(r.URL.Path, "/api/prompt-options/template/"))
	if len(parts) != 1 {
		writeError(w, http.StatusNotFound, "Template not found")
		return
	}
	templateID := parts[0]
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	templates, _ := config["quickTemplates"].([]any)
	for i, item := range templates {
		if obj, ok := item.(map[string]any); ok && stringValue(obj["id"]) == templateID {
			deleted := item
			config["quickTemplates"] = append(templates[:i], templates[i+1:]...)
			if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
				writeError(w, http.StatusInternalServerError, err.Error())
				return
			}
			writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted": deleted}})
			return
		}
	}
	writeError(w, http.StatusNotFound, fmt.Sprintf("Template %q not found", templateID))
}

func (s *server) handleWizardOptions(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	config, err := s.loadOptionConfig("wizard_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": config})
}

func (s *server) handleWizardOptionDimension(w http.ResponseWriter, r *http.Request) {
	if !s.requireServerSystem(w, r) {
		return
	}
	parts := routeParts(strings.TrimPrefix(r.URL.Path, "/api/wizard-options/dimension/"))
	if len(parts) == 1 && r.Method == http.MethodPost {
		s.addWizardOption(w, r, parts[0])
		return
	}
	if len(parts) == 2 && r.Method == http.MethodDelete {
		s.deleteWizardOption(w, r, parts[0], parts[1])
		return
	}
	writeError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func fileSizeOrZero(path string) int64 {
	info, err := os.Stat(path)
	if err != nil || info.IsDir() {
		return 0
	}
	return info.Size()
}

func roundMB(bytes int64) float64 {
	return math.Round((float64(bytes)/1024/1024)*100) / 100
}

func roundKB(bytes int64) float64 {
	return math.Round((float64(bytes)/1024)*10) / 10
}

func directorySize(root string) (int64, error) {
	var total int64
	if _, err := os.Stat(root); os.IsNotExist(err) {
		return 0, nil
	}
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			return nil
		}
		info, err := entry.Info()
		if err != nil {
			return err
		}
		total += info.Size()
		return nil
	})
	return total, err
}

func (s *server) countRows(table, where string) (int, error) {
	return s.scalarInt("SELECT COUNT(*) FROM " + table + " " + where)
}

func (s *server) scalarInt(query string, args ...any) (int, error) {
	var value int
	if err := s.db.QueryRow(query, args...).Scan(&value); err != nil {
		return 0, err
	}
	return value, nil
}

func loadPortConfig(configPath string) (response, error) {
	config := response{
		"preferred_port":   5000,
		"fallback_enabled": true,
		"fallback_range":   20,
	}
	if !fileExists(configPath) {
		return config, nil
	}
	file, err := os.Open(configPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	var saved map[string]any
	if err := json.NewDecoder(file).Decode(&saved); err != nil {
		return nil, err
	}
	for key, value := range saved {
		config[key] = value
	}
	return config, nil
}

func currentRequestPort(r *http.Request) int {
	host := r.Host
	if _, port, err := net.SplitHostPort(host); err == nil {
		if value, err := strconv.Atoi(port); err == nil {
			return value
		}
	}
	if idx := strings.LastIndex(host, ":"); idx >= 0 {
		if value, err := strconv.Atoi(host[idx+1:]); err == nil {
			return value
		}
	}
	return 80
}

func boolValue(raw any) bool {
	switch value := raw.(type) {
	case bool:
		return value
	case string:
		return strings.EqualFold(value, "true") || value == "1"
	default:
		if intValue, ok := intValue(raw); ok {
			return intValue != 0
		}
	}
	return false
}

// processMemoryInfo reports Go process memory; used as the non-Linux fallback
// when system RAM is unavailable.
func processMemoryInfo() response {
	var stats runtime.MemStats
	runtime.ReadMemStats(&stats)
	total := int64(stats.Sys)
	used := int64(stats.Alloc)
	percent := 0.0
	if total > 0 {
		percent = math.Round((float64(used)/float64(total))*1000) / 10
	}
	return response{
		"total_mb":     roundMB(total),
		"used_mb":      roundMB(used),
		"available_mb": roundMB(total - used),
		"percent":      percent,
	}
}

// diskFallback reports only measured data-dir usage; used on non-Linux where a
// statfs-based total/free is unavailable.
func diskFallback(dataDir string) response {
	used, _ := directorySize(dataDir)
	return response{
		"total_gb": 0,
		"used_gb":  math.Round((float64(used)/1024/1024/1024)*100) / 100,
		"free_gb":  0,
		"percent":  0,
	}
}

func gbFromBytes(bytes uint64) float64 {
	return math.Round(float64(bytes)/1024/1024/1024*100) / 100
}

func mbFromKB(kb uint64) float64 {
	return math.Round(float64(kb)/1024*10) / 10
}

// parseCPUTempMilliC parses a kernel thermal_zone temperature (millidegrees C)
// into degrees C rounded to 0.1.
func parseCPUTempMilliC(raw string) (float64, bool) {
	milli, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil {
		return 0, false
	}
	return math.Round(float64(milli)/1000.0*10) / 10, true
}

// parseUptimeSeconds parses the first field of /proc/uptime (seconds, float).
func parseUptimeSeconds(raw string) (float64, bool) {
	fields := strings.Fields(raw)
	if len(fields) == 0 {
		return 0, false
	}
	secs, err := strconv.ParseFloat(fields[0], 64)
	if err != nil {
		return 0, false
	}
	return math.Round(secs), true
}

// parseMeminfoKB pulls MemTotal / MemAvailable (kB) out of /proc/meminfo.
func parseMeminfoKB(raw string) (total, avail uint64, ok bool) {
	var gotTotal, gotAvail bool
	for _, line := range strings.Split(raw, "\n") {
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		val, err := strconv.ParseUint(fields[1], 10, 64)
		if err != nil {
			continue
		}
		switch fields[0] {
		case "MemTotal:":
			total, gotTotal = val, true
		case "MemAvailable:":
			avail, gotAvail = val, true
		}
	}
	return total, avail, gotTotal && gotAvail
}

func (s *server) serverLogPath() string {
	candidates := []string{
		filepath.Join(s.runtime.dataDir, "app.log"),
		filepath.Join(s.runtime.logsDir, "app.log"),
	}
	for _, candidate := range candidates {
		if fileExists(candidate) {
			return candidate
		}
	}
	return ""
}

func readTextLines(path string) ([]string, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	text := strings.ReplaceAll(string(content), "\r\n", "\n")
	text = strings.TrimRight(text, "\n\r")
	if text == "" {
		return []string{}, nil
	}
	return strings.Split(text, "\n"), nil
}

func decodeOptionalJSONObject(r *http.Request) (map[string]any, error) {
	defer r.Body.Close()
	content, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(string(content)) == "" {
		return map[string]any{}, nil
	}
	var payload map[string]any
	if err := json.Unmarshal(content, &payload); err != nil {
		return nil, err
	}
	if payload == nil {
		payload = map[string]any{}
	}
	return payload, nil
}

func parseBackupKeepCountFromQuery(r *http.Request, fallback int) int {
	if raw := r.URL.Query().Get("keep_count"); raw != "" {
		if value, err := strconv.Atoi(raw); err == nil {
			return clampBackupKeepCount(value)
		}
	}
	if raw := r.URL.Query().Get("keep"); raw != "" {
		if value, err := strconv.Atoi(raw); err == nil {
			return clampBackupKeepCount(value)
		}
	}
	return clampBackupKeepCount(fallback)
}

func parseBackupKeepCount(payload map[string]any, fallback int) int {
	if value, ok := intValue(payload["keep_count"]); ok {
		return clampBackupKeepCount(value)
	}
	if value, ok := intValue(payload["keep"]); ok {
		return clampBackupKeepCount(value)
	}
	return clampBackupKeepCount(fallback)
}

func clampBackupKeepCount(value int) int {
	if value < 1 {
		return 1
	}
	if value > maxBackupKeepCount {
		return maxBackupKeepCount
	}
	return value
}

type backupInfo struct {
	Filename   string
	Path       string
	SizeBytes  int64
	CreatedAt  string
	ModifiedAt int64
}

func managedBackupName() string {
	now := time.Now()
	return fmt.Sprintf("prism_backup_%s_%09d.db", now.Format("20060102_150405"), now.Nanosecond())
}

func isManagedBackupFilename(filename string) bool {
	return filename != "" &&
		filename == filepath.Base(filename) &&
		!strings.ContainsAny(filename, `/\`) &&
		strings.HasPrefix(filename, "prism_backup_") &&
		strings.HasSuffix(filename, ".db")
}

func listManagedBackups(backupDir string) ([]backupInfo, error) {
	entries, err := os.ReadDir(backupDir)
	if err != nil {
		return nil, err
	}
	backups := []backupInfo{}
	for _, entry := range entries {
		filename := entry.Name()
		if entry.IsDir() || !isManagedBackupFilename(filename) {
			continue
		}
		path := filepath.Join(backupDir, filename)
		info, err := entry.Info()
		if err != nil {
			return nil, err
		}
		backups = append(backups, backupInfo{
			Filename:   filename,
			Path:       path,
			SizeBytes:  info.Size(),
			CreatedAt:  info.ModTime().Format(time.RFC3339),
			ModifiedAt: info.ModTime().UnixNano(),
		})
	}
	sort.Slice(backups, func(i, j int) bool {
		if backups[i].ModifiedAt == backups[j].ModifiedAt {
			return backups[i].Filename > backups[j].Filename
		}
		return backups[i].ModifiedAt > backups[j].ModifiedAt
	})
	return backups, nil
}

func enforceBackupRetention(backupDir string, keepCount int, protectedFilename string) ([]backupInfo, []string, int64, error) {
	backups, err := listManagedBackups(backupDir)
	if err != nil {
		return nil, nil, 0, err
	}
	keepCount = clampBackupKeepCount(keepCount)
	kept := []backupInfo{}
	if protectedFilename != "" {
		for _, backup := range backups {
			if backup.Filename == protectedFilename {
				kept = append(kept, backup)
				break
			}
		}
	}
	for _, backup := range backups {
		if len(kept) >= keepCount {
			break
		}
		if backup.Filename == protectedFilename {
			continue
		}
		kept = append(kept, backup)
	}
	keptNames := map[string]bool{}
	var totalSize int64
	for _, backup := range kept {
		keptNames[backup.Filename] = true
		totalSize += backup.SizeBytes
	}
	deleted := []string{}
	for _, backup := range backups {
		if keptNames[backup.Filename] {
			continue
		}
		if err := os.Remove(backup.Path); err != nil {
			return nil, nil, 0, err
		}
		deleted = append(deleted, backup.Filename)
	}
	return kept, deleted, totalSize, nil
}

func backupResponseItems(backups []backupInfo) []response {
	items := []response{}
	for _, backup := range backups {
		items = append(items, response{
			"filename":   backup.Filename,
			"size_bytes": backup.SizeBytes,
			"size_mb":    roundMB(backup.SizeBytes),
			"created_at": backup.CreatedAt,
		})
	}
	return items
}

func prismVersion() string {
	if value := strings.TrimSpace(os.Getenv("PRISM_VERSION")); value != "" {
		return value
	}
	pattern := regexp.MustCompile(`PRISM_VERSION\s*=\s*["']([^"']+)["']`)
	candidates := []string{}
	if cwd, err := os.Getwd(); err == nil {
		candidates = append(candidates, filepath.Join(cwd, "config.py"))
		candidates = append(candidates, filepath.Join(cwd, "..", "config.py"))
	}
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		candidates = append(candidates, filepath.Join(exeDir, "config.py"))
		candidates = append(candidates, filepath.Join(exeDir, "..", "config.py"))
	}
	for _, candidate := range candidates {
		content, err := os.ReadFile(candidate)
		if err != nil {
			continue
		}
		if match := pattern.FindStringSubmatch(string(content)); len(match) == 2 {
			return match[1]
		}
	}
	return "2.4.9"
}

func routeParts(raw string) []string {
	raw = strings.Trim(raw, "/")
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, "/")
	out := []string{}
	for _, part := range parts {
		decoded, err := url.PathUnescape(part)
		if err != nil || decoded == "" {
			return nil
		}
		out = append(out, decoded)
	}
	return out
}

func (s *server) optionConfigPath(filename string) (string, error) {
	if filename != "prompt_options.json" && filename != "wizard_options.json" {
		return "", fmt.Errorf("unsupported config file %q", filename)
	}
	target := filepath.Join(s.runtime.configDir, filename)
	if !isSubpath(target, s.runtime.configDir) {
		return "", fmt.Errorf("config path escapes config dir: %s", filename)
	}
	return target, nil
}

func (s *server) loadOptionConfig(filename string) (map[string]any, error) {
	target, err := s.optionConfigPath(filename)
	if err != nil {
		return nil, err
	}
	if !fileExists(target) {
		if err := s.seedOptionConfig(filename, target); err != nil {
			return nil, err
		}
	}
	file, err := os.Open(target)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	var config map[string]any
	if err := json.NewDecoder(file).Decode(&config); err != nil {
		return nil, err
	}
	if config == nil {
		return nil, errors.New("configuration file is empty")
	}
	return config, nil
}

func (s *server) seedOptionConfig(filename, target string) error {
	sourceCandidates := []string{filepath.Join(s.runtime.dataDir, "static", "config", filename)}
	if cwd, err := os.Getwd(); err == nil {
		sourceCandidates = append(sourceCandidates,
			filepath.Join(cwd, "static", "config", filename),
			filepath.Join(cwd, "..", "static", "config", filename),
		)
	}
	for _, source := range sourceCandidates {
		if !fileExists(source) {
			continue
		}
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return err
		}
		return copyFileExclusive(source, target)
	}
	return fmt.Errorf("configuration file not found: %s", filename)
}

func (s *server) saveOptionConfig(filename string, config map[string]any) error {
	target, err := s.optionConfigPath(filename)
	if err != nil {
		return err
	}
	config["lastUpdated"] = time.Now().Format("2006-01-02")
	return writeIndentedJSON(target, config)
}

func writeIndentedJSON(target string, payload any) error {
	if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
		return err
	}
	content, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	content = append(content, '\n')
	tmp := target + ".tmp"
	if err := os.WriteFile(tmp, content, 0644); err != nil {
		return err
	}
	_ = os.Remove(target)
	return os.Rename(tmp, target)
}

func (s *server) promptCategory(config map[string]any, categoryKey string) (map[string]any, []any, error) {
	categories, ok := config["categories"].(map[string]any)
	if !ok {
		return nil, nil, errors.New("categories not found")
	}
	category, ok := categories[categoryKey].(map[string]any)
	if !ok {
		return nil, nil, fmt.Errorf("Category %q not found", categoryKey)
	}
	options, _ := category["options"].([]any)
	return category, options, nil
}

func (s *server) addPromptOption(w http.ResponseWriter, r *http.Request, categoryKey string) {
	payload, ok := decodeJSONObject(w, r, "Request body is required")
	if !ok {
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	category, options, err := s.promptCategory(config, categoryKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	newOption, err := promptOptionFromPayload(payload, false)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if text, ok := newOption.(string); ok {
		for _, option := range options {
			if existing, ok := option.(string); ok && existing == text {
				writeError(w, http.StatusBadRequest, "Option already exists")
				return
			}
		}
	}
	options = append(options, newOption)
	category["options"] = options
	if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"index": len(options) - 1, "option": newOption}})
}

func (s *server) updatePromptOption(w http.ResponseWriter, r *http.Request, categoryKey, indexText string) {
	index, err := strconv.Atoi(indexText)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid index")
		return
	}
	payload, ok := decodeJSONObject(w, r, "Request body is required")
	if !ok {
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	category, options, err := s.promptCategory(config, categoryKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if index < 0 || index >= len(options) {
		writeError(w, http.StatusBadRequest, "Index out of range")
		return
	}
	current := map[string]any{}
	if existing, ok := options[index].(map[string]any); ok {
		current = existing
	}
	newOption, err := promptOptionFromPayloadWithCurrent(payload, current)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	options[index] = newOption
	category["options"] = options
	if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"option": newOption}})
}

func (s *server) deletePromptOption(w http.ResponseWriter, r *http.Request, categoryKey, indexText string) {
	index, err := strconv.Atoi(indexText)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid index")
		return
	}
	config, err := s.loadOptionConfig("prompt_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	category, options, err := s.promptCategory(config, categoryKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if index < 0 || index >= len(options) {
		writeError(w, http.StatusBadRequest, "Index out of range")
		return
	}
	deleted := options[index]
	category["options"] = append(options[:index], options[index+1:]...)
	if err := s.saveOptionConfig("prompt_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted": deleted}})
}

func promptOptionFromPayload(payload map[string]any, allowPartial bool) (any, error) {
	if raw, exists := payload["value"]; exists {
		value := strings.TrimSpace(stringValue(raw))
		if value == "" {
			return nil, errors.New("Option value cannot be empty")
		}
		return value, nil
	}
	display := strings.TrimSpace(stringValue(payload["display"]))
	output := strings.TrimSpace(stringValue(payload["output"]))
	if display == "" || output == "" {
		return nil, errors.New("Display and output are required")
	}
	key := strings.TrimSpace(stringValue(payload["key"]))
	if key == "" {
		key = strings.ReplaceAll(strings.ToLower(output), " ", "_")
	}
	return map[string]any{"key": key, "display": display, "output": output}, nil
}

func promptOptionFromPayloadWithCurrent(payload map[string]any, current map[string]any) (any, error) {
	if _, exists := payload["value"]; exists {
		return promptOptionFromPayload(payload, false)
	}
	if _, hasDisplay := payload["display"]; hasDisplay || payload["output"] != nil || payload["key"] != nil {
		key := strings.TrimSpace(stringValue(payload["key"]))
		if key == "" {
			key = strings.TrimSpace(stringValue(current["key"]))
		}
		display := strings.TrimSpace(stringValue(payload["display"]))
		if display == "" {
			display = strings.TrimSpace(stringValue(current["display"]))
		}
		output := strings.TrimSpace(stringValue(payload["output"]))
		if output == "" {
			output = strings.TrimSpace(stringValue(current["output"]))
		}
		if display == "" || output == "" {
			return nil, errors.New("Invalid format")
		}
		return map[string]any{"key": key, "display": display, "output": output}, nil
	}
	return nil, errors.New("Invalid format")
}

func (s *server) wizardDimension(config map[string]any, dimensionKey string) (map[string]any, []any, error) {
	dimensions, ok := config["dimensions"].(map[string]any)
	if !ok {
		return nil, nil, errors.New("dimensions not found")
	}
	dimension, ok := dimensions[dimensionKey].(map[string]any)
	if !ok {
		return nil, nil, fmt.Errorf("Dimension %q not found", dimensionKey)
	}
	options, _ := dimension["options"].([]any)
	return dimension, options, nil
}

func (s *server) addWizardOption(w http.ResponseWriter, r *http.Request, dimensionKey string) {
	payload, ok := decodeJSONObject(w, r, "Request body is required")
	if !ok {
		return
	}
	value := strings.TrimSpace(stringField(payload, "value"))
	if value == "" {
		writeError(w, http.StatusBadRequest, "value is required")
		return
	}
	config, err := s.loadOptionConfig("wizard_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	dimension, options, err := s.wizardDimension(config, dimensionKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	for _, option := range options {
		if existing, ok := option.(string); ok && existing == value {
			writeError(w, http.StatusBadRequest, "This option already exists")
			return
		}
	}
	options = append(options, value)
	dimension["options"] = options
	if err := s.saveOptionConfig("wizard_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"index": len(options) - 1, "option": value}})
}

func (s *server) deleteWizardOption(w http.ResponseWriter, r *http.Request, dimensionKey, indexText string) {
	index, err := strconv.Atoi(indexText)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Invalid index")
		return
	}
	config, err := s.loadOptionConfig("wizard_options.json")
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	dimension, options, err := s.wizardDimension(config, dimensionKey)
	if err != nil {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if index < 0 || index >= len(options) {
		writeError(w, http.StatusBadRequest, "Index out of range")
		return
	}
	deleted := options[index]
	dimension["options"] = append(options[:index], options[index+1:]...)
	if err := s.saveOptionConfig("wizard_options.json", config); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"deleted": deleted}})
}

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
			var found int
			if err := tx.QueryRow("SELECT id FROM Categories WHERE name = ? LIMIT 1", categoryName).Scan(&found); err == nil {
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
	rows, err := s.db.Query("SELECT id, name, icon, sort_order, is_default FROM Categories ORDER BY sort_order, id")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	categories := []response{}
	for rows.Next() {
		var id, sortOrder, isDefault int
		var name, icon sql.NullString
		if err := rows.Scan(&id, &name, &icon, &sortOrder, &isDefault); err != nil {
			return nil, err
		}
		categories = append(categories, response{
			"id": id, "name": nullableString(name), "icon": nullableStringOrNil(icon),
			"sort_order": sortOrder, "is_default": isDefault != 0,
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

func defaultCategoryIDTx(tx *sql.Tx) (int, error) {
	var id int
	err := tx.QueryRow("SELECT id FROM Categories WHERE is_default = 1 LIMIT 1").Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, nil
	}
	return id, err
}

func categoryIDForNameTx(tx *sql.Tx, name string) (int, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return 0, nil
	}
	var id int
	err := tx.QueryRow("SELECT id FROM Categories WHERE name = ? LIMIT 1", name).Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, nil
	}
	return id, err
}

func (s *server) handleExtractPrompt(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) {
		return
	}
	if !s.runtime.enableUploadWrite {
		_, _ = io.Copy(io.Discard, r.Body)
		writeError(w, http.StatusMethodNotAllowed, "Upload route is disabled")
		return
	}
	payload, ok := decodeJSONObject(w, r, "image_path is required")
	if !ok {
		return
	}
	imagePath := strings.TrimSpace(stringField(payload, "image_path"))
	if imagePath == "" {
		writeError(w, http.StatusBadRequest, "image_path is required")
		return
	}
	resolved, ok := s.resolvePromptImagePath(imagePath)
	if !ok {
		writeError(w, http.StatusNotFound, "Image file not found")
		return
	}
	promptData, err := extractPromptMetadata(resolved)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to read image metadata: "+err.Error())
		return
	}
	if strings.TrimSpace(promptData.Prompt) == "" {
		writeJSON(w, http.StatusOK, response{
			"status": "success",
			"data": response{
				"prompt":          nil,
				"negative_prompt": nil,
				"source":          nil,
				"has_prompt":      false,
			},
		})
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"prompt":          promptData.Prompt,
			"negative_prompt": nilIfEmpty(promptData.NegativePrompt),
			"source":          nilIfEmpty(promptData.Source),
			"has_prompt":      true,
		},
	})
}

func (s *server) resolvePromptImagePath(imagePath string) (string, bool) {
	cleaned := strings.TrimSpace(strings.ReplaceAll(imagePath, "\\", "/"))
	if strings.HasPrefix(cleaned, "/static/uploads/") {
		cleaned = strings.TrimPrefix(cleaned, "/static/uploads/")
	} else if strings.HasPrefix(cleaned, "static/uploads/") {
		cleaned = strings.TrimPrefix(cleaned, "static/uploads/")
	}
	if cleaned == "" || strings.Contains(cleaned, ":") || strings.HasPrefix(cleaned, "/") {
		return "", false
	}
	absPath, ok := s.resolveUploadFile(cleaned)
	if !ok {
		return "", false
	}
	info, err := os.Lstat(absPath)
	if err != nil || !info.Mode().IsRegular() || info.Size() > maxUploadFileBytes {
		return "", false
	}
	resolved, err := filepath.EvalSymlinks(absPath)
	if err != nil || filepath.Clean(resolved) != filepath.Clean(absPath) || !isSubpath(resolved, s.runtime.uploadsDir) {
		return "", false
	}
	return resolved, true
}

type promptMetadata struct {
	Prompt         string
	NegativePrompt string
	Source         string
}

func extractPromptMetadata(filename string) (promptMetadata, error) {
	content, err := os.ReadFile(filename)
	if err != nil {
		return promptMetadata{}, err
	}
	fields := readPNGTextFields(content)
	return promptMetadataFromFields(fields), nil
}

func readPNGTextFields(content []byte) map[string]string {
	fields := map[string]string{}
	if len(content) < 8 || !bytes.Equal(content[:8], []byte("\x89PNG\r\n\x1a\n")) {
		return fields
	}
	for offset := 8; offset+12 <= len(content); {
		length := int(content[offset])<<24 | int(content[offset+1])<<16 | int(content[offset+2])<<8 | int(content[offset+3])
		chunkType := string(content[offset+4 : offset+8])
		chunkStart := offset + 8
		chunkEnd := chunkStart + length
		if chunkEnd+4 > len(content) {
			return fields
		}
		chunk := content[chunkStart:chunkEnd]
		switch chunkType {
		case "tEXt":
			if key, value, ok := parsePNGTextChunk(chunk); ok {
				fields[key] = value
			}
		case "zTXt":
			if key, value, ok := parsePNGZTextChunk(chunk); ok {
				fields[key] = value
			}
		case "iTXt":
			if key, value, ok := parsePNGInternationalTextChunk(chunk); ok {
				fields[key] = value
			}
		case "IEND":
			return fields
		}
		offset = chunkEnd + 4
	}
	return fields
}

func parsePNGTextChunk(chunk []byte) (string, string, bool) {
	parts := bytes.SplitN(chunk, []byte{0}, 2)
	if len(parts) != 2 {
		return "", "", false
	}
	return latin1String(parts[0]), string(parts[1]), true
}

func parsePNGZTextChunk(chunk []byte) (string, string, bool) {
	parts := bytes.SplitN(chunk, []byte{0}, 2)
	if len(parts) != 2 || len(parts[1]) == 0 || parts[1][0] != 0 {
		return "", "", false
	}
	reader, err := zlib.NewReader(bytes.NewReader(parts[1][1:]))
	if err != nil {
		return "", "", false
	}
	defer reader.Close()
	text, err := io.ReadAll(io.LimitReader(reader, maxUploadFileBytes+1))
	if err != nil || int64(len(text)) > maxUploadFileBytes {
		return "", "", false
	}
	return latin1String(parts[0]), string(text), true
}

func parsePNGInternationalTextChunk(chunk []byte) (string, string, bool) {
	parts := bytes.SplitN(chunk, []byte{0}, 6)
	if len(parts) != 6 {
		return "", "", false
	}
	text := parts[5]
	if len(parts[1]) > 0 && parts[1][0] == 1 {
		if len(parts[2]) == 0 || parts[2][0] != 0 {
			return "", "", false
		}
		reader, err := zlib.NewReader(bytes.NewReader(text))
		if err != nil {
			return "", "", false
		}
		defer reader.Close()
		decoded, err := io.ReadAll(io.LimitReader(reader, maxUploadFileBytes+1))
		if err != nil || int64(len(decoded)) > maxUploadFileBytes {
			return "", "", false
		}
		text = decoded
	}
	return latin1String(parts[0]), string(text), true
}

func promptMetadataFromFields(fields map[string]string) promptMetadata {
	if value := strings.TrimSpace(fields["parameters"]); value != "" {
		prompt, negative := splitStableDiffusionPrompt(value)
		return promptMetadata{Prompt: prompt, NegativePrompt: negative, Source: "stable_diffusion"}
	}
	if value := strings.TrimSpace(fields["prompt"]); value != "" {
		return promptMetadata{Prompt: value, Source: "comfyui"}
	}
	if value := strings.TrimSpace(fields["Comment"]); value != "" {
		payload := map[string]any{}
		if err := json.Unmarshal([]byte(value), &payload); err == nil {
			if prompt := strings.TrimSpace(stringField(payload, "prompt")); prompt != "" {
				return promptMetadata{Prompt: prompt, NegativePrompt: stringField(payload, "uc"), Source: "novelai"}
			}
		}
	}
	if value := strings.TrimSpace(fields["Description"]); value != "" {
		return promptMetadata{Prompt: value, Source: "description"}
	}
	return promptMetadata{}
}

func splitStableDiffusionPrompt(parameters string) (string, string) {
	lines := strings.Split(parameters, "\n")
	promptLines := []string{}
	negative := ""
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "Negative prompt:") {
			negative = strings.TrimSpace(strings.TrimPrefix(trimmed, "Negative prompt:"))
			continue
		}
		if strings.HasPrefix(trimmed, "Steps:") || strings.HasPrefix(trimmed, "Size:") || strings.HasPrefix(trimmed, "Sampler:") {
			break
		}
		promptLines = append(promptLines, line)
	}
	return strings.TrimSpace(strings.Join(promptLines, "\n")), negative
}

func latin1String(raw []byte) string {
	var builder strings.Builder
	for _, b := range raw {
		builder.WriteRune(rune(b))
	}
	return builder.String()
}

func nilIfEmpty(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return value
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

func (s *server) handleUploadDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableUploadDelete {
		writeError(w, http.StatusMethodNotAllowed, "Upload delete route is disabled")
		return
	}

	var payload struct {
		URL string `json:"url"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil && !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "Invalid JSON request")
		return
	}
	if strings.TrimSpace(payload.URL) == "" {
		writeError(w, http.StatusBadRequest, "No URL provided")
		return
	}
	filename, ok := uploadDeleteFilename(payload.URL)
	if !ok {
		writeError(w, http.StatusBadRequest, "Invalid filename")
		return
	}

	referenced, err := s.expandedReferencedUploadFilenames()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	deleted := []string{}
	for _, candidate := range uploadDeleteCandidates(filename) {
		if referenced[candidate] {
			continue
		}
		absPath, ok := s.resolveUploadFile(candidate)
		if !ok {
			continue
		}
		info, err := os.Stat(absPath)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if !info.Mode().IsRegular() {
			continue
		}
		if err := os.Remove(absPath); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		deleted = append(deleted, candidate)
	}

	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"deleted": deleted,
		"count":   len(deleted),
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

func (s *server) handleCleanupOrphanImages(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "GET, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableMediaCleanup {
		writeError(w, http.StatusMethodNotAllowed, "Media cleanup route is disabled")
		return
	}
	if r.Method == http.MethodGet {
		s.getOrphanImages(w)
		return
	}
	s.deleteOrphanImages(w, r)
}

func (s *server) getOrphanImages(w http.ResponseWriter) {
	orphans, totalSize, err := s.orphanUploadImages()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	items := make([]response, 0, len(orphans))
	for _, orphan := range orphans {
		items = append(items, response{
			"filename": orphan.Filename,
			"size":     orphan.Size,
			"path":     "/static/uploads/" + orphan.Filename,
		})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"orphan_images":    items,
		"total_count":      len(items),
		"total_size_bytes": totalSize,
		"total_size_mb":    roundedMB(totalSize),
	}})
}

func (s *server) deleteOrphanImages(w http.ResponseWriter, r *http.Request) {
	var payload struct {
		Filenames []string `json:"filenames"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil && !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "Invalid JSON request")
		return
	}
	if len(payload.Filenames) == 0 {
		writeError(w, http.StatusBadRequest, "No filenames provided")
		return
	}

	orphans, _, err := s.orphanUploadImages()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	orphanSet := map[string]bool{}
	for _, orphan := range orphans {
		orphanSet[orphan.Filename] = true
	}

	deleted := []string{}
	deletedSet := map[string]bool{}
	errorsOut := []response{}
	for _, rawFilename := range payload.Filenames {
		filename, ok := uploadReferenceFilename(rawFilename)
		if !ok {
			errorsOut = append(errorsOut, response{"filename": rawFilename, "error": "Invalid path"})
			continue
		}
		if !orphanSet[filename] {
			errorsOut = append(errorsOut, response{"filename": filename, "error": "File is not orphan"})
			continue
		}
		deletedAny := false
		for _, candidate := range uploadDeleteCandidates(filename) {
			if deletedSet[candidate] {
				continue
			}
			if candidate != filename && !orphanSet[candidate] {
				continue
			}
			absPath, ok := s.resolveUploadFile(candidate)
			if !ok {
				continue
			}
			info, err := os.Stat(absPath)
			if err != nil {
				if os.IsNotExist(err) {
					continue
				}
				errorsOut = append(errorsOut, response{"filename": candidate, "error": err.Error()})
				continue
			}
			if !info.Mode().IsRegular() {
				continue
			}
			if err := os.Remove(absPath); err != nil {
				errorsOut = append(errorsOut, response{"filename": candidate, "error": err.Error()})
				continue
			}
			deleted = append(deleted, candidate)
			deletedSet[candidate] = true
			deletedAny = true
		}
		if !deletedAny {
			errorsOut = append(errorsOut, response{"filename": filename, "error": "File not found"})
		}
	}

	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"deleted":       deleted,
		"deleted_count": len(deleted),
		"errors":        errorsOut,
	}})
}

func (s *server) handleCleanupOriginals(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "GET, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableMediaCleanup {
		writeError(w, http.StatusMethodNotAllowed, "Media cleanup route is disabled")
		return
	}
	if r.Method == http.MethodGet {
		s.getOriginalImages(w)
		return
	}
	s.deleteAllOriginals(w)
}

func (s *server) getOriginalImages(w http.ResponseWriter) {
	originals, thumbnailCount, err := s.originalUploadImages()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	var originalSize int64
	for _, item := range originals {
		originalSize += item.Size
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"original_count":      len(originals),
		"original_size_bytes": originalSize,
		"original_size_mb":    roundedMB(originalSize),
		"thumbnail_count":     thumbnailCount,
	}})
}

func (s *server) deleteAllOriginals(w http.ResponseWriter) {
	originals, _, err := s.originalUploadImages()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if len(originals) == 0 {
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
			"deleted_count": 0,
			"saved_bytes":   0,
			"saved_mb":      0,
			"updated_notes": 0,
		}})
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	updatedNotes := 0
	for _, item := range originals {
		originalURL := "/static/uploads/" + item.Filename
		thumbnailURL := "/static/uploads/" + item.Thumbnail
		result, err := tx.Exec(`
			UPDATE Notes
			SET content = REPLACE(content, ?, ?),
			    updated_at = CURRENT_TIMESTAMP
			WHERE content LIKE ?`,
			originalURL, thumbnailURL, "%"+originalURL+"%")
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		rows, _ := result.RowsAffected()
		updatedNotes += int(rows)
		if _, err := tx.Exec(`
			UPDATE Notes
			SET cover_image = ?
			WHERE cover_image = ?`,
			thumbnailURL, originalURL); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	deletedCount := 0
	var savedBytes int64
	for _, item := range originals {
		absPath, ok := s.resolveUploadFile(item.Filename)
		if !ok {
			continue
		}
		if err := os.Remove(absPath); err != nil {
			if !os.IsNotExist(err) {
				log.Printf("original cleanup skipped file %s: %v", absPath, err)
			}
			continue
		}
		deletedCount++
		savedBytes += item.Size
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"deleted_count": deletedCount,
		"saved_bytes":   savedBytes,
		"saved_mb":      roundedMB(savedBytes),
		"updated_notes": updatedNotes,
	}})
}

func (s *server) handleCleanupBrokenImages(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodPost {
		w.Header().Set("Allow", "GET, POST")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableMediaCleanup {
		writeError(w, http.StatusMethodNotAllowed, "Media cleanup route is disabled")
		return
	}
	if r.Method == http.MethodGet {
		s.getBrokenImages(w)
		return
	}
	s.fixBrokenImages(w)
}

func (s *server) getBrokenImages(w http.ResponseWriter) {
	broken, err := s.brokenImageReferences()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	items := make([]response, 0, len(broken))
	fixableCount := 0
	for _, item := range broken {
		if item.CanFix {
			fixableCount++
		}
		entry := response{
			"note_id":        item.NoteID,
			"original_path":  item.OriginalPath,
			"thumbnail_path": item.ThumbnailPath,
			"can_fix":        item.CanFix,
			"reason":         item.Reason,
		}
		if item.IsCover {
			entry["is_cover"] = true
		}
		items = append(items, entry)
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"broken_paths":  items,
		"total_count":   len(items),
		"fixable_count": fixableCount,
	}})
}

func (s *server) fixBrokenImages(w http.ResponseWriter) {
	rows, err := s.db.Query("SELECT id, content, cover_image FROM Notes")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	type update struct {
		id      int
		content string
		cover   string
	}
	updates := []update{}
	fixedCount := 0
	for rows.Next() {
		var noteID int
		var content, cover sql.NullString
		if err := rows.Scan(&noteID, &content, &cover); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		newContent := nullableString(content)
		newCover := nullableString(cover)
		contentChanged := false
		coverChanged := false
		for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(newContent, -1) {
			if len(match) < 2 {
				continue
			}
			filename := match[1]
			if strings.Contains(filename, "_thumb") {
				continue
			}
			if s.uploadFileExists(filename) {
				continue
			}
			if thumb := s.findThumbnailForOriginal(filename); thumb != "" {
				oldPath := "/static/uploads/" + filename
				newPath := "/static/uploads/" + thumb
				newContent = strings.ReplaceAll(newContent, oldPath, newPath)
				fixedCount++
				contentChanged = true
			}
		}
		if newCover != "" && strings.Contains(newCover, "/static/uploads/") {
			filename, ok := uploadReferenceFilename(newCover)
			if ok && !strings.Contains(filename, "_thumb") && !s.uploadFileExists(filename) {
				if thumb := s.findThumbnailForOriginal(filename); thumb != "" {
					newCover = "/static/uploads/" + thumb
					fixedCount++
					coverChanged = true
				}
			}
		}
		if contentChanged || coverChanged {
			updates = append(updates, update{id: noteID, content: newContent, cover: newCover})
		}
	}
	if err := rows.Err(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	for _, update := range updates {
		if _, err := tx.Exec(`
			UPDATE Notes
			SET content = ?, cover_image = ?, updated_at = CURRENT_TIMESTAMP
			WHERE id = ?`, update.content, update.cover, update.id); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"fixed_count":   fixedCount,
		"updated_notes": len(updates),
	}})
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
		       n.category_id, n.created_at, n.updated_at, n.parent_id, p.title AS parent_title
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
	var id, isPinned, isArchived int
	var title, content, categoryName, coverPosition, editorLayout, createdAt, updatedAt sql.NullString
	var remarks, coverImage, parentTitle sql.NullString
	var categoryID, parentID sql.NullInt64
	if err := row.Scan(&id, &title, &content, &categoryName, &remarks, &coverImage, &coverPosition, &editorLayout, &isPinned, &isArchived, &categoryID, &createdAt, &updatedAt, &parentID, &parentTitle); err != nil {
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

func uploadDeleteFilename(rawURL string) (string, bool) {
	raw := strings.TrimSpace(strings.ReplaceAll(rawURL, "\\", "/"))
	if raw == "" {
		return "", false
	}
	if idx := strings.LastIndex(raw, "/static/uploads/"); idx >= 0 {
		raw = raw[idx+len("/static/uploads/"):]
	}
	filename := path.Base(raw)
	if filename == "." || filename == "/" || filename == "" || strings.Contains(filename, "..") || strings.HasPrefix(filename, ".") {
		return "", false
	}
	return filename, true
}

func uploadDeleteCandidates(filename string) []string {
	filename = strings.ReplaceAll(strings.TrimSpace(filename), "\\", "/")
	if filename == "" {
		return nil
	}
	ext := path.Ext(filename)
	nameWithoutExt := strings.TrimSuffix(filename, ext)
	candidates := []string{filename}
	if !strings.HasSuffix(nameWithoutExt, "_thumb") {
		candidates = append(candidates, nameWithoutExt+"_thumb.webp")
		if ext != "" {
			candidates = append(candidates, nameWithoutExt+"_thumb"+ext)
		}
	}
	return uniqueStrings(candidates)
}

func uploadReferenceFilename(raw string) (string, bool) {
	raw = strings.TrimSpace(strings.ReplaceAll(raw, "\\", "/"))
	if raw == "" {
		return "", false
	}
	if idx := strings.LastIndex(raw, "/static/uploads/"); idx >= 0 {
		raw = raw[idx+len("/static/uploads/"):]
	}
	raw = strings.TrimPrefix(raw, "/")
	cleaned := path.Clean(raw)
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return "", false
	}
	for _, part := range strings.Split(cleaned, "/") {
		if part == "" || part == "." || part == ".." {
			return "", false
		}
	}
	return cleaned, true
}

func addReferencedUploadFilename(referenced map[string]bool, raw string) {
	if filename, ok := uploadReferenceFilename(raw); ok {
		referenced[filename] = true
	}
}

func expandedUploadReferences(referenced map[string]bool) map[string]bool {
	expanded := map[string]bool{}
	for ref := range referenced {
		expanded[ref] = true
		base := strings.TrimSuffix(ref, path.Ext(ref))
		if !strings.HasSuffix(base, "_thumb") {
			ext := path.Ext(ref)
			if ext != "" {
				expanded[base+"_thumb"+ext] = true
			}
			expanded[base+"_thumb.webp"] = true
		}
	}
	return expanded
}

func possibleOriginalsForThumb(filename string) []string {
	baseName := strings.ReplaceAll(filename, "_thumb", "")
	baseNoExt := strings.TrimSuffix(baseName, path.Ext(baseName))
	candidates := []string{baseName}
	for _, ext := range []string{".jpg", ".jpeg", ".png", ".gif", ".webp"} {
		candidates = append(candidates, baseNoExt+ext)
	}
	return uniqueStrings(candidates)
}

func isCleanupImageFilename(filename string, includeSVG bool) bool {
	switch strings.ToLower(path.Ext(filename)) {
	case ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp":
		return true
	case ".svg":
		return includeSVG
	default:
		return false
	}
}

type uploadImageFile struct {
	Filename string
	Size     int64
}

type originalUploadImage struct {
	Filename  string
	Thumbnail string
	Size      int64
}

type brokenImageReference struct {
	NoteID        int
	OriginalPath  string
	ThumbnailPath any
	CanFix        bool
	IsCover       bool
	Reason        string
}

func (s *server) referencedUploadFilenames() (map[string]bool, error) {
	referenced := map[string]bool{}
	rows, err := s.db.Query("SELECT content, cover_image FROM Notes")
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var content, cover sql.NullString
		if err := rows.Scan(&content, &cover); err != nil {
			rows.Close()
			return nil, err
		}
		if content.Valid {
			for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(content.String, -1) {
				if len(match) > 1 {
					addReferencedUploadFilename(referenced, match[1])
				}
			}
		}
		if cover.Valid && cover.String != "" {
			addReferencedUploadFilename(referenced, cover.String)
		}
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()

	attachmentRows, err := s.db.Query("SELECT file_path FROM Note_Attachments")
	if err != nil {
		return referenced, nil
	}
	defer attachmentRows.Close()
	for attachmentRows.Next() {
		var filePath sql.NullString
		if err := attachmentRows.Scan(&filePath); err != nil {
			return nil, err
		}
		if !filePath.Valid || filePath.String == "" {
			continue
		}
		if strings.Contains(filePath.String, "/static/uploads/") {
			addReferencedUploadFilename(referenced, filePath.String)
			continue
		}
		resolved, ok := resolveAttachmentReferenceScanFile(s.runtime.dataDir, filePath.String)
		if !ok {
			continue
		}
		content, err := os.ReadFile(resolved)
		if err != nil {
			continue
		}
		for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(string(content), -1) {
			if len(match) > 1 {
				addReferencedUploadFilename(referenced, match[1])
			}
		}
	}
	return referenced, attachmentRows.Err()
}

func (s *server) expandedReferencedUploadFilenames() (map[string]bool, error) {
	referenced, err := s.referencedUploadFilenames()
	if err != nil {
		return nil, err
	}
	return expandedUploadReferences(referenced), nil
}

func (s *server) uploadImageFiles(includeSVG bool) ([]uploadImageFile, error) {
	entries, err := os.ReadDir(s.runtime.uploadsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	files := []uploadImageFile{}
	for _, entry := range entries {
		if entry.IsDir() || !isCleanupImageFilename(entry.Name(), includeSVG) {
			continue
		}
		info, err := entry.Info()
		if err != nil || !info.Mode().IsRegular() {
			continue
		}
		files = append(files, uploadImageFile{Filename: entry.Name(), Size: info.Size()})
	}
	return files, nil
}

func (s *server) orphanUploadImages() ([]uploadImageFile, int64, error) {
	files, err := s.uploadImageFiles(true)
	if err != nil {
		return nil, 0, err
	}
	referenced, err := s.referencedUploadFilenames()
	if err != nil {
		return nil, 0, err
	}
	expandedReferenced := expandedUploadReferences(referenced)
	orphans := []uploadImageFile{}
	var totalSize int64
	for _, file := range files {
		if expandedReferenced[file.Filename] {
			continue
		}
		if strings.Contains(file.Filename, "_thumb") {
			protected := false
			for _, original := range possibleOriginalsForThumb(file.Filename) {
				if referenced[original] {
					protected = true
					break
				}
			}
			if protected {
				continue
			}
		}
		orphans = append(orphans, file)
		totalSize += file.Size
	}
	return orphans, totalSize, nil
}

func (s *server) originalUploadImages() ([]originalUploadImage, int, error) {
	files, err := s.uploadImageFiles(false)
	if err != nil {
		return nil, 0, err
	}
	originals := []originalUploadImage{}
	thumbnailCount := 0
	for _, file := range files {
		base := strings.TrimSuffix(file.Filename, path.Ext(file.Filename))
		if strings.HasSuffix(base, "_thumb") {
			thumbnailCount++
			continue
		}
		if thumb := s.findThumbnailForOriginal(file.Filename); thumb != "" {
			originals = append(originals, originalUploadImage{
				Filename:  file.Filename,
				Thumbnail: thumb,
				Size:      file.Size,
			})
		}
	}
	return originals, thumbnailCount, nil
}

func (s *server) brokenImageReferences() ([]brokenImageReference, error) {
	rows, err := s.db.Query("SELECT id, content, cover_image FROM Notes")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	broken := []brokenImageReference{}
	for rows.Next() {
		var noteID int
		var content, cover sql.NullString
		if err := rows.Scan(&noteID, &content, &cover); err != nil {
			return nil, err
		}
		if content.Valid {
			for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(content.String, -1) {
				if len(match) < 2 {
					continue
				}
				filename := match[1]
				if strings.Contains(filename, "_thumb") {
					if !s.uploadFileExists(filename) {
						broken = append(broken, brokenImageReference{
							NoteID:       noteID,
							OriginalPath: "/static/uploads/" + filename,
							CanFix:       false,
							Reason:       "thumbnail_missing",
						})
					}
					continue
				}
				if !s.uploadFileExists(filename) {
					thumb := s.findThumbnailForOriginal(filename)
					broken = append(broken, brokenReference(noteID, "/static/uploads/"+filename, thumb, false))
				}
			}
		}
		if cover.Valid && strings.Contains(cover.String, "/static/uploads/") {
			filename, ok := uploadReferenceFilename(cover.String)
			if !ok || s.uploadFileExists(filename) {
				continue
			}
			if strings.Contains(filename, "_thumb") {
				broken = append(broken, brokenImageReference{
					NoteID:       noteID,
					OriginalPath: cover.String,
					CanFix:       false,
					IsCover:      true,
					Reason:       "thumbnail_missing",
				})
			} else {
				thumb := s.findThumbnailForOriginal(filename)
				broken = append(broken, brokenReference(noteID, cover.String, thumb, true))
			}
		}
	}
	return broken, rows.Err()
}

func brokenReference(noteID int, originalPath, thumbnail string, isCover bool) brokenImageReference {
	item := brokenImageReference{
		NoteID:       noteID,
		OriginalPath: originalPath,
		CanFix:       thumbnail != "",
		IsCover:      isCover,
		Reason:       "original_missing",
	}
	if thumbnail != "" {
		item.ThumbnailPath = "/static/uploads/" + thumbnail
	}
	return item
}

func (s *server) uploadFileExists(filename string) bool {
	absPath, ok := s.resolveUploadFile(filename)
	if !ok {
		return false
	}
	info, err := os.Stat(absPath)
	return err == nil && info.Mode().IsRegular()
}

func (s *server) findThumbnailForOriginal(filename string) string {
	ext := path.Ext(filename)
	base := strings.TrimSuffix(filename, ext)
	for _, candidate := range []string{base + "_thumb.webp", base + "_thumb" + ext} {
		if candidate == base+"_thumb" {
			continue
		}
		if s.uploadFileExists(candidate) {
			return candidate
		}
	}
	return ""
}

func roundedMB(size int64) float64 {
	if size <= 0 {
		return 0
	}
	return math.Round((float64(size)/(1024*1024))*100) / 100
}

func resolveAttachmentReferenceScanFile(dataDir, relativePath string) (string, bool) {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	ext := strings.ToLower(path.Ext(relativePath))
	if ext != ".md" && ext != ".txt" && ext != ".html" {
		return "", false
	}
	resolved, ok := resolveAttachmentMutationPath(dataDir, relativePath)
	if !ok {
		return "", false
	}
	info, err := os.Lstat(resolved)
	if err != nil || !info.Mode().IsRegular() || info.Size() > maxUploadFileBytes {
		return "", false
	}
	evaluated, err := filepath.EvalSymlinks(resolved)
	if err != nil || filepath.Clean(evaluated) != filepath.Clean(resolved) {
		return "", false
	}
	root, err := filepath.Abs(dataDir)
	if err != nil || !isSubpath(evaluated, root) {
		return "", false
	}
	return evaluated, true
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
	if rel == "import/md" {
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
		s.importMarkdown(w, r)
		return
	}
	if rel == "export/batch" {
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
		s.exportBatchMarkdown(w, r)
		return
	}
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
	case "check_separation":
		if r.Method != http.MethodGet || len(parts) != 1 {
			w.Header().Set("Allow", http.MethodGet)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.checkSeparation(w, noteID)
	case "separate":
		if r.Method != http.MethodPost || len(parts) != 1 {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.separateContent(w, r, noteID)
	case "restore":
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if len(parts) == 1 {
			s.restoreSeparatedContent(w, noteID)
			return
		}
		if len(parts) != 2 {
			http.NotFound(w, r)
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

func (s *server) checkSeparation(w http.ResponseWriter, noteID int) {
	var content sql.NullString
	if err := s.db.QueryRow("SELECT content FROM Notes WHERE id = ?", noteID).Scan(&content); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	contentLength := len([]rune(nullableString(content)))
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"should_separate": contentLength > separationThreshold,
			"content_length":  contentLength,
			"threshold":       separationThreshold,
		},
	})
}

func (s *server) separateContent(w http.ResponseWriter, r *http.Request, noteID int) {
	payload := map[string]any{}
	_ = json.NewDecoder(r.Body).Decode(&payload)
	previewLen, ok := intField(payload, "preview_length")
	if !ok || previewLen <= 0 {
		previewLen = separationPreviewLength
	}

	var title, content sql.NullString
	if err := s.db.QueryRow("SELECT title, content FROM Notes WHERE id = ?", noteID).Scan(&title, &content); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	fullContent := nullableString(content)
	originalLength := len([]rune(fullContent))
	if originalLength <= separationThreshold {
		writeJSON(w, http.StatusOK, response{
			"status":  "info",
			"message": fmt.Sprintf("Content length (%d) is under threshold (%d), no separation needed", originalLength, separationThreshold),
		})
		return
	}

	if err := os.MkdirAll(s.notesDirectory(), 0755); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	filename := fmt.Sprintf("note_%d.md", noteID)
	absPath := filepath.Join(s.notesDirectory(), filename)
	if !isSubpath(absPath, s.runtime.dataDir) {
		writeError(w, http.StatusInternalServerError, "unsafe notes path")
		return
	}
	if err := os.WriteFile(absPath, []byte(fullContent), 0644); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	info, err := os.Stat(absPath)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	relativePath := path.Join("docs", "notes", filename)
	attachmentTitle := nullableString(title) + " (完整內容)"
	preview := separatedPreview(fullContent, previewLen)

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var attachmentID int
	err = tx.QueryRow("SELECT id FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1", noteID).Scan(&attachmentID)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if attachmentID != 0 {
		if _, err := tx.Exec("UPDATE Note_Attachments SET size_bytes = ?, title = ?, file_path = ?, file_type = 'md' WHERE id = ?", info.Size(), attachmentTitle, relativePath, attachmentID); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	} else {
		result, err := tx.Exec(`
			INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted, created_at)
			VALUES (?, ?, 'md', ?, ?, 1, CURRENT_TIMESTAMP)`, noteID, relativePath, attachmentTitle, info.Size())
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		newID, err := result.LastInsertId()
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		attachmentID = int(newID)
	}
	if _, err := tx.Exec("UPDATE Notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", preview, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status":  "success",
		"message": "內容已成功分離為附件",
		"data": response{
			"attachment_id":   attachmentID,
			"file_path":       relativePath,
			"original_length": originalLength,
			"preview_length":  len([]rune(preview)),
		},
	})
}

func (s *server) restoreSeparatedContent(w http.ResponseWriter, noteID int) {
	var attachmentID int
	var filePath sql.NullString
	if err := s.db.QueryRow("SELECT id, file_path FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1", noteID).Scan(&attachmentID, &filePath); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "No auto-extracted attachment found for this note")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	resolved, ok := resolveAutoExtractedNotePath(s.runtime.dataDir, nullableString(filePath))
	if !ok {
		writeError(w, http.StatusNotFound, "Attachment file not found on disk")
		return
	}
	content, err := os.ReadFile(resolved)
	if err != nil {
		writeError(w, http.StatusNotFound, "Attachment file not found on disk")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()
	if _, err := tx.Exec("UPDATE Notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", normalizeTextContent(string(content)), noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("DELETE FROM Note_Attachments WHERE id = ?", attachmentID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	_ = os.Remove(resolved)
	writeJSON(w, http.StatusOK, response{"status": "success", "message": "內容已成功還原至筆記"})
}

func (s *server) notesDirectory() string {
	if s.runtime.notesDir != "" {
		return s.runtime.notesDir
	}
	return filepath.Join(s.runtime.dataDir, "docs", "notes")
}

func separatedPreview(content string, previewLen int) string {
	runes := []rune(content)
	if len(runes) <= previewLen {
		return content
	}
	return string(runes[:previewLen]) + "\n\n---\n📎 **[完整內容已分離為附件]**\n\n> 此筆記內容過長，已自動分離為附件。點擊附件可查看完整內容。"
}

func resolveAutoExtractedNotePath(dataDir, relativePath string) (string, bool) {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	if relativePath == "" || filepath.IsAbs(relativePath) || filepath.VolumeName(relativePath) != "" || strings.Contains(relativePath, ":") {
		return "", false
	}
	cleaned := path.Clean(relativePath)
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") || !strings.HasPrefix(cleaned, "docs/notes/") {
		return "", false
	}
	ext := strings.ToLower(path.Ext(cleaned))
	if ext != ".md" && ext != ".markdown" && ext != ".txt" {
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
	info, err := os.Lstat(absCandidate)
	if err != nil || !info.Mode().IsRegular() || info.Size() > maxAttachmentFileBytes {
		return "", false
	}
	resolved, err := filepath.EvalSymlinks(absCandidate)
	if err != nil || filepath.Clean(resolved) != filepath.Clean(absCandidate) || !isSubpath(resolved, root) {
		return "", false
	}
	return resolved, true
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
