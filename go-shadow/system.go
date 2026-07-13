package main

import (
	"encoding/json"
	"io"
	"io/fs"
	"math"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
)

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
			"data_dir": s.runtime.dataDir,
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

func prismVersion() string {
	if value := strings.TrimSpace(os.Getenv("PRISM_VERSION")); value != "" {
		return value
	}
	return "2.6.1"
}
