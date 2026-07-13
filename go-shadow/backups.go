package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

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
	tmp.Close()
	defer os.Remove(tmpPath)
	if err := s.writeConsistentDBBackup(tmpPath); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
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
	if err := s.writeConsistentDBBackup(backupPath); err != nil {
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

func (s *server) writeConsistentDBBackup(destination string) error {
	if strings.TrimSpace(destination) == "" {
		return errors.New("backup destination is required")
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0755); err != nil {
		return err
	}
	tmp := destination + ".tmp"
	_ = os.Remove(tmp)
	if _, err := s.db.Exec("VACUUM INTO " + sqliteStringLiteral(tmp)); err != nil {
		_ = os.Remove(tmp)
		return err
	}
	if err := validateSQLiteBackup(tmp); err != nil {
		_ = os.Remove(tmp)
		return err
	}
	_ = os.Remove(destination)
	return os.Rename(tmp, destination)
}

func sqliteStringLiteral(value string) string {
	return "'" + strings.ReplaceAll(value, "'", "''") + "'"
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
