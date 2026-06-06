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
	"strconv"
	"strings"
	"time"

	webp "github.com/skrashevich/go-webp"
	_ "modernc.org/sqlite"
)

const expectedSchemaVersion = 16
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
	errUploadURLSSRF                        = errors.New("upload URL resolves to a private or reserved IP address")
	uploadURLResolveHost                    = defaultUploadURLResolveHost
	uploadURLTransport    http.RoundTripper = http.DefaultTransport
	encodeUploadThumbnail                   = encodeThumbnailWebP
	uploadNow                               = time.Now
)

type server struct {
	db      *sql.DB
	runtime runtimeConfig
}

type runtimeConfig struct {
	addr                     string
	dbPath                   string
	dataDir                  string
	enableTagWrite           bool
	enableCategoryWrite      bool
	enableNotesWrite         bool
	enableAttachmentTextRead bool
	enableThumbnailWrite     bool
	enableUploadURLWrite     bool
	sqliteQueryOnly          bool
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
	enableCategoryWrite := flag.Bool("enable-category-write", envBool("PRISM_GO_ENABLE_CATEGORY_WRITE"), "enable local/copied-DB PUT /api/categories/<id> parity candidate")
	enableNotesWrite := flag.Bool("enable-notes-write", envBool("PRISM_GO_ENABLE_NOTES_WRITE"), "enable local/copied-DB notes write/actions/history/batch parity candidate")
	enableAttachmentTextRead := flag.Bool("enable-attachment-text-read", envBool("PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ"), "enable local/copied-DB GET /api/attachments/<id> text JSON parity candidate")
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

	cfg, err := resolveRuntimeConfig(*addr, *dbPath, *dataDir, *enableTagWrite, *enableCategoryWrite, *enableNotesWrite, *enableAttachmentTextRead, *enableThumbnailWrite, *enableUploadURLWrite)
	if err != nil {
		log.Fatal(err)
	}

	db, err := openDB(cfg.dbPath, cfg.hasWriteCandidate())
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
	mux.HandleFunc("/api/categories/", srv.handleCategoryDetail)
	mux.HandleFunc("/api/tags", srv.handleTags)
	mux.HandleFunc("/api/tags/", srv.handleTagDetail)
	mux.HandleFunc("/api/notes", srv.handleNotes)
	mux.HandleFunc("/api/notes/", srv.handleNoteDetail)
	mux.HandleFunc("/api/attachments/", srv.handleAttachmentDetail)
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

func resolveRuntimeConfig(addr, dbPath, dataDir string, enableTagWrite, enableCategoryWrite, enableNotesWrite, enableAttachmentTextRead, enableThumbnailWrite, enableUploadURLWrite bool) (runtimeConfig, error) {
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
	if (enableThumbnailWrite || enableUploadURLWrite) && filepath.Base(absDB) == "knowledge.db" && os.Getenv("PRISM_GO_ALLOW_PROD_UPLOADS") != "1" {
		return runtimeConfig{}, fmt.Errorf("refusing to enable upload writes with production-like database %s; use copied data or set PRISM_GO_ALLOW_PROD_UPLOADS=1", absDB)
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
		addr:                     addr,
		dbPath:                   absDB,
		dataDir:                  absData,
		enableTagWrite:           enableTagWrite,
		enableCategoryWrite:      enableCategoryWrite,
		enableNotesWrite:         enableNotesWrite,
		enableAttachmentTextRead: enableAttachmentTextRead,
		enableThumbnailWrite:     enableThumbnailWrite,
		enableUploadURLWrite:     enableUploadURLWrite,
		sqliteQueryOnly:          !(enableTagWrite || enableCategoryWrite || enableNotesWrite),
	}, nil
}

func (cfg runtimeConfig) hasWriteCandidate() bool {
	return cfg.enableTagWrite || cfg.enableCategoryWrite || cfg.enableNotesWrite
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
	if s.runtime.enableAttachmentTextRead {
		parts = append(parts, "local-attachment-text-read")
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
	if !s.runtime.enableThumbnailWrite {
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
	if !allowedUploadMIME(http.DetectContentType(content)) {
		writeError(w, http.StatusBadRequest, "File content validation failed")
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
	uploadsDir := filepath.Join(s.runtime.dataDir, "static", "uploads")
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
	uploadsDir := filepath.Join(s.runtime.dataDir, "static", "uploads")
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
	case "image/jpeg", "image/png", "image/gif", "image/webp", "application/octet-stream":
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
	if r.Method != http.MethodPut {
		w.Header().Set("Allow", http.MethodPut)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableCategoryWrite {
		writeError(w, http.StatusMethodNotAllowed, "Category write route is disabled")
		return
	}
	s.updateCategory(w, r, categoryID)
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

func (s *server) handleAttachmentDetail(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	if !s.runtime.enableAttachmentTextRead {
		writeError(w, http.StatusMethodNotAllowed, "Attachment text read route is disabled")
		return
	}
	if boolString(r, "raw") {
		writeError(w, http.StatusMethodNotAllowed, "Raw attachment responses remain Python-owned")
		return
	}

	idText := strings.TrimPrefix(r.URL.Path, "/api/attachments/")
	attachmentID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	s.readAttachmentText(w, attachmentID)
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

	var existingID int
	if err := tx.QueryRow("SELECT id FROM Notes WHERE id = ?", noteID).Scan(&existingID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
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
	return string(encoded), nil
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
		if _, err := tx.Exec("INSERT OR IGNORE INTO Tags (name) VALUES (?)", tagName); err != nil {
			return added, err
		}
		var tagID int
		if err := tx.QueryRow("SELECT id FROM Tags WHERE name = ?", tagName).Scan(&tagID); err != nil {
			return added, err
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
	result, err := tx.Exec("DELETE FROM Notes WHERE id IN ("+inClause+")", ids...)
	if err != nil {
		return 0, err
	}
	rows, _ := result.RowsAffected()
	return int(rows), nil
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
	noteIDs, ok := intArrayField(payload, "note_ids")
	if !ok || len(noteIDs) == 0 {
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
	noteIDs, valid := intArrayField(payload, "note_ids")
	categoryID, hasCategory := intField(payload, "category_id")
	if !valid || len(noteIDs) == 0 || !hasCategory {
		writeError(w, http.StatusBadRequest, "note_ids and category_id are required")
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
	noteIDs, valid := intArrayField(payload, "note_ids")
	tags := stringArrayField(payload, "tags")
	if !valid || len(noteIDs) == 0 || len(tags) == 0 {
		writeError(w, http.StatusBadRequest, "note_ids and tags are required")
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
	noteIDs, valid := intArrayField(payload, "note_ids")
	if !valid || len(noteIDs) == 0 {
		writeError(w, http.StatusBadRequest, "note_ids must be a non-empty array")
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
			"id": id, "content": nullableString(content), "diff_summary": nullableString(diffSummary), "created_at": nullableString(createdAt),
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
