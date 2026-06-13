package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// writeProbeDB creates a minimal but valid Prism-shaped SQLite DB carrying a
// recognisable probe value so a restore can be proven by reading it back.
func writeProbeDB(t *testing.T, path, probe string) {
	t.Helper()
	db, err := sql.Open("sqlite", sqliteDSN(path, true))
	if err != nil {
		t.Fatalf("open probe db: %v", err)
	}
	defer db.Close()
	stmts := []string{
		"CREATE TABLE Schema_Meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
		"INSERT INTO Schema_Meta (key, value) VALUES ('schema_version', '16')",
		"CREATE TABLE Probe (tag TEXT)",
		fmt.Sprintf("INSERT INTO Probe (tag) VALUES ('%s')", probe),
	}
	for _, s := range stmts {
		if _, err := db.Exec(s); err != nil {
			t.Fatalf("seed probe db (%s): %v", s, err)
		}
	}
}

func readProbe(t *testing.T, path string) string {
	t.Helper()
	db, err := sql.Open("sqlite", sqliteDSN(path, false))
	if err != nil {
		t.Fatalf("open db for probe read: %v", err)
	}
	defer db.Close()
	var tag string
	if err := db.QueryRow("SELECT tag FROM Probe LIMIT 1").Scan(&tag); err != nil {
		t.Fatalf("read probe: %v", err)
	}
	return tag
}

func restoreTestConfig(t *testing.T) runtimeConfig {
	t.Helper()
	dataDir := t.TempDir()
	backups := filepath.Join(dataDir, "backups")
	config := filepath.Join(dataDir, "config")
	for _, d := range []string{backups, config} {
		if err := os.MkdirAll(d, 0755); err != nil {
			t.Fatalf("mkdir %s: %v", d, err)
		}
	}
	return runtimeConfig{
		dbPath:     filepath.Join(dataDir, "knowledge.db"),
		dataDir:    dataDir,
		backupsDir: backups,
		configDir:  config,
	}
}

func writeMarker(t *testing.T, cfg runtimeConfig, backup string) {
	t.Helper()
	data, _ := json.Marshal(pendingRestore{Backup: backup, RequestedAt: "now"})
	if err := os.WriteFile(filepath.Join(cfg.configDir, pendingRestoreMarker), data, 0600); err != nil {
		t.Fatalf("write marker: %v", err)
	}
}

func TestApplyPendingRestoreSwapsValidBackup(t *testing.T) {
	cfg := restoreTestConfig(t)
	writeProbeDB(t, cfg.dbPath, "LIVE")
	backupName := "prism_backup_20260101_000000_000000001.db"
	writeProbeDB(t, filepath.Join(cfg.backupsDir, backupName), "BACKUP")
	// Stray WAL/SHM that must be cleared after the swap.
	os.WriteFile(cfg.dbPath+"-wal", []byte("stale"), 0600)
	os.WriteFile(cfg.dbPath+"-shm", []byte("stale"), 0600)
	writeMarker(t, cfg, backupName)

	if err := applyPendingRestore(cfg); err != nil {
		t.Fatalf("applyPendingRestore: %v", err)
	}

	if got := readProbe(t, cfg.dbPath); got != "BACKUP" {
		t.Fatalf("live DB not restored: probe = %q, want BACKUP", got)
	}
	if fileExists(cfg.dbPath + "-wal") || fileExists(cfg.dbPath + "-shm") {
		t.Fatal("stale WAL/SHM not cleared after restore")
	}
	if fileExists(filepath.Join(cfg.configDir, pendingRestoreMarker)) {
		t.Fatal("pending-restore marker not removed after restore")
	}
	// A pre-restore safety copy of the old DB must exist and still read LIVE.
	matches, _ := filepath.Glob(filepath.Join(cfg.backupsDir, "prism_pre_restore_*.db"))
	if len(matches) != 1 {
		t.Fatalf("expected exactly one pre-restore safety copy, got %d", len(matches))
	}
	if got := readProbe(t, matches[0]); got != "LIVE" {
		t.Fatalf("safety copy lost old data: probe = %q, want LIVE", got)
	}
}

func TestApplyPendingRestoreRejectsBrokenBackup(t *testing.T) {
	cfg := restoreTestConfig(t)
	writeProbeDB(t, cfg.dbPath, "LIVE")
	backupName := "prism_backup_20260101_000000_000000002.db"
	if err := os.WriteFile(filepath.Join(cfg.backupsDir, backupName), []byte("not a sqlite db"), 0600); err != nil {
		t.Fatalf("write garbage backup: %v", err)
	}
	writeMarker(t, cfg, backupName)

	if err := applyPendingRestore(cfg); err != nil {
		t.Fatalf("applyPendingRestore should skip a broken backup, got error: %v", err)
	}

	if got := readProbe(t, cfg.dbPath); got != "LIVE" {
		t.Fatalf("live DB must be untouched when backup is broken: probe = %q", got)
	}
	if fileExists(filepath.Join(cfg.configDir, pendingRestoreMarker)) {
		t.Fatal("marker must be cleared even when backup is rejected")
	}
	matches, _ := filepath.Glob(filepath.Join(cfg.backupsDir, "prism_pre_restore_*.db"))
	if len(matches) != 0 {
		t.Fatal("no safety copy should be made when the restore is skipped")
	}
}

func TestApplyPendingRestoreNoMarkerIsNoop(t *testing.T) {
	cfg := restoreTestConfig(t)
	writeProbeDB(t, cfg.dbPath, "LIVE")
	if err := applyPendingRestore(cfg); err != nil {
		t.Fatalf("applyPendingRestore with no marker: %v", err)
	}
	if got := readProbe(t, cfg.dbPath); got != "LIVE" {
		t.Fatalf("DB changed with no marker present: probe = %q", got)
	}
}

func TestHandleBackupRestoreStagesMarkerAndRestarts(t *testing.T) {
	cfg := restoreTestConfig(t)
	cfg.enableServerSystem = true
	writeProbeDB(t, cfg.dbPath, "LIVE")
	backupName := "prism_backup_20260101_000000_000000003.db"
	writeProbeDB(t, filepath.Join(cfg.backupsDir, backupName), "BACKUP")

	restarted := false
	srv := &server{runtime: cfg, restart: func() { restarted = true }}

	req := httptest.NewRequest(http.MethodPost, "/api/server/backup/restore", strings.NewReader(`{"backup":"`+backupName+`"}`))
	req.RemoteAddr = "127.0.0.1:5555"
	rec := httptest.NewRecorder()
	srv.handleBackupRestore(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
	}
	if !restarted {
		t.Fatal("restart hook was not invoked")
	}
	markerPath := filepath.Join(cfg.configDir, pendingRestoreMarker)
	raw, err := os.ReadFile(markerPath)
	if err != nil {
		t.Fatalf("marker not written: %v", err)
	}
	var m pendingRestore
	if err := json.Unmarshal(raw, &m); err != nil {
		t.Fatalf("marker not valid JSON: %v", err)
	}
	if m.Backup != backupName {
		t.Fatalf("marker backup = %q, want %q", m.Backup, backupName)
	}
}

func TestHandleBackupRestoreRejectsBadInput(t *testing.T) {
	cfg := restoreTestConfig(t)
	cfg.enableServerSystem = true
	writeProbeDB(t, cfg.dbPath, "LIVE")

	cases := []struct {
		name string
		body string
		want int
	}{
		{"invalid filename", `{"backup":"../escape.db"}`, http.StatusBadRequest},
		{"missing file", `{"backup":"prism_backup_20990101_000000_000000000.db"}`, http.StatusNotFound},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			restarted := false
			srv := &server{runtime: cfg, restart: func() { restarted = true }}
			req := httptest.NewRequest(http.MethodPost, "/api/server/backup/restore", strings.NewReader(tc.body))
			req.RemoteAddr = "127.0.0.1:5555"
			rec := httptest.NewRecorder()
			srv.handleBackupRestore(rec, req)
			if rec.Code != tc.want {
				t.Fatalf("status = %d, want %d (%s)", rec.Code, tc.want, rec.Body.String())
			}
			if restarted {
				t.Fatal("restart must not fire on rejected input")
			}
			if fileExists(filepath.Join(cfg.configDir, pendingRestoreMarker)) {
				t.Fatal("no marker should be written on rejected input")
			}
		})
	}
}

func TestValidateSQLiteBackup(t *testing.T) {
	dir := t.TempDir()
	good := filepath.Join(dir, "good.db")
	writeProbeDB(t, good, "OK")
	if err := validateSQLiteBackup(good); err != nil {
		t.Fatalf("valid DB rejected: %v", err)
	}
	bad := filepath.Join(dir, "bad.db")
	os.WriteFile(bad, []byte("garbage"), 0600)
	if err := validateSQLiteBackup(bad); err == nil {
		t.Fatal("garbage file accepted as valid backup")
	}
}
