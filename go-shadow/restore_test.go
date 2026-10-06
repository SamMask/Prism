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
	"time"
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

// seedManagedBackups writes n fake managed backups whose mtimes start at age
// and get one minute older per file.
func seedManagedBackups(t *testing.T, dir string, n int, age time.Duration) {
	t.Helper()
	for i := 0; i < n; i++ {
		path := filepath.Join(dir, fmt.Sprintf("prism_backup_20250101_0000%02d_000000000.db", i))
		if err := os.WriteFile(path, []byte("old"), 0600); err != nil {
			t.Fatal(err)
		}
		mtime := time.Now().Add(-age - time.Duration(i)*time.Minute)
		if err := os.Chtimes(path, mtime, mtime); err != nil {
			t.Fatal(err)
		}
	}
}

func countManagedBackups(t *testing.T, dir string) int {
	t.Helper()
	backups, err := listManagedBackups(dir)
	if err != nil {
		t.Fatal(err)
	}
	return len(backups)
}

func backdateManagedBackups(t *testing.T, dir string, age time.Duration) {
	t.Helper()
	backups, err := listManagedBackups(dir)
	if err != nil {
		t.Fatal(err)
	}
	for _, b := range backups {
		mtime := time.Unix(0, b.ModifiedAt).Add(-age)
		if err := os.Chtimes(b.Path, mtime, mtime); err != nil {
			t.Fatal(err)
		}
	}
}

func openRestorePointTestServer(t *testing.T, probe string) *server {
	t.Helper()
	cfg := restoreTestConfig(t)
	cfg.enableServerSystem = true
	writeProbeDB(t, cfg.dbPath, probe)
	db, err := sql.Open("sqlite", sqliteDSN(cfg.dbPath, true))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return &server{db: db, runtime: cfg}
}

func getBackupList(t *testing.T, srv *server) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, "/api/server/backup/list", nil)
	req.RemoteAddr = "127.0.0.1:5555"
	rec := httptest.NewRecorder()
	srv.handleBackupList(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("backup list status = %d (%s)", rec.Code, rec.Body.String())
	}
	return rec
}

func TestShouldCreateAutoRestorePoint(t *testing.T) {
	cases := []struct {
		name  string
		setup func(t *testing.T, dir string)
		want  bool
	}{
		{"no backups", func(t *testing.T, dir string) {}, true},
		{"newest under 24h", func(t *testing.T, dir string) { seedManagedBackups(t, dir, 1, time.Hour) }, false},
		{"newest over 24h", func(t *testing.T, dir string) { seedManagedBackups(t, dir, 2, 25*time.Hour) }, true},
		{"only non-managed files are recent", func(t *testing.T, dir string) {
			seedManagedBackups(t, dir, 1, 48*time.Hour)
			for _, name := range []string{
				"prism_go_pre_migrate_v16_to_v17_20261007_000000_000000000.db",
				"prism_pre_restore_20261007_000000.db",
				"prism_backup_20261007_000000_000000000.db.tmp",
				"筆記備份.db",
			} {
				if err := os.WriteFile(filepath.Join(dir, name), []byte("x"), 0600); err != nil {
					t.Fatal(err)
				}
			}
		}, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			tc.setup(t, dir)
			got, err := shouldCreateAutoRestorePoint(dir, time.Now())
			if err != nil {
				t.Fatal(err)
			}
			if got != tc.want {
				t.Fatalf("shouldCreateAutoRestorePoint = %v, want %v", got, tc.want)
			}
		})
	}
}

func TestEnsureDailyRestorePointCreatesOnceAndKeepsSeven(t *testing.T) {
	srv := openRestorePointTestServer(t, "每日還原點")
	dir := srv.runtime.backupsDir
	seedManagedBackups(t, dir, 8, 48*time.Hour)
	safetyNet := filepath.Join(dir, "prism_pre_restore_20250101_000000.db")
	if err := os.WriteFile(safetyNet, []byte("keep me"), 0600); err != nil {
		t.Fatal(err)
	}

	first := srv.ensureDailyRestorePoint(time.Now())
	if first.Status != "created" || first.Backup == "" {
		t.Fatalf("first check = %+v, want created", first)
	}
	if got := countManagedBackups(t, dir); got != 7 {
		t.Fatalf("managed backups after first check = %d, want 7", got)
	}
	if got := readProbe(t, filepath.Join(dir, first.Backup)); got != "每日還原點" {
		t.Fatalf("restore point probe = %q", got)
	}
	if !fileExists(safetyNet) {
		t.Fatal("retention must not delete non-managed files")
	}

	second := srv.ensureDailyRestorePoint(time.Now())
	if second.Status != "skipped" {
		t.Fatalf("second check = %+v, want skipped", second)
	}
	if got := countManagedBackups(t, dir); got != 7 {
		t.Fatalf("managed backups after second check = %d, want 7", got)
	}

	backdateManagedBackups(t, dir, 25*time.Hour)
	third := srv.ensureDailyRestorePoint(time.Now())
	if third.Status != "created" || third.Backup == first.Backup {
		t.Fatalf("third check = %+v, want a new restore point", third)
	}
	if got := countManagedBackups(t, dir); got != 7 {
		t.Fatalf("managed backups after third check = %d, want 7", got)
	}

	var payload struct {
		Data struct {
			AutoRestorePoint *autoRestorePointResult `json:"auto_restore_point"`
		} `json:"data"`
	}
	if err := json.Unmarshal(getBackupList(t, srv).Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload.Data.AutoRestorePoint == nil || payload.Data.AutoRestorePoint.Backup != third.Backup {
		t.Fatalf("backup list auto_restore_point = %+v, want %s", payload.Data.AutoRestorePoint, third.Backup)
	}
}

func TestEnsureDailyRestorePointFailureIsVisibleInBackupList(t *testing.T) {
	srv := openRestorePointTestServer(t, "LIVE")
	srv.db.Close() // a closed DB makes VACUUM INTO fail

	result := srv.ensureDailyRestorePoint(time.Now())
	if result.Status != "failed" || result.Error == "" {
		t.Fatalf("check = %+v, want failed with error", result)
	}
	if got := countManagedBackups(t, srv.runtime.backupsDir); got != 0 {
		t.Fatalf("failed check left %d managed backups", got)
	}
	if body := getBackupList(t, srv).Body.String(); !strings.Contains(body, `"status":"failed"`) {
		t.Fatalf("backup list must report the failed auto restore point: %s", body)
	}
}

func TestBackupListOmitsAutoRestorePointWhenCheckNeverRan(t *testing.T) {
	srv := openRestorePointTestServer(t, "LIVE")
	if body := getBackupList(t, srv).Body.String(); strings.Contains(body, "auto_restore_point") {
		t.Fatalf("backup list must not report a check that never ran: %s", body)
	}
}

func TestBackupRotateDefaultKeepsSeven(t *testing.T) {
	srv := openRestorePointTestServer(t, "LIVE")
	seedManagedBackups(t, srv.runtime.backupsDir, 9, 48*time.Hour)

	req := httptest.NewRequest(http.MethodPost, "/api/server/backup/rotate", strings.NewReader(`{}`))
	req.RemoteAddr = "127.0.0.1:5555"
	rec := httptest.NewRecorder()
	srv.handleBackupRotate(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("rotate status = %d (%s)", rec.Code, rec.Body.String())
	}
	if got := countManagedBackups(t, srv.runtime.backupsDir); got != 7 {
		t.Fatalf("managed backups after default rotate = %d, want 7", got)
	}
}

func TestDailyRestorePointAndManualRotatesRunConcurrently(t *testing.T) {
	srv := openRestorePointTestServer(t, "LIVE")
	dir := srv.runtime.backupsDir
	seedManagedBackups(t, dir, 8, 48*time.Hour)

	const rotates = 8
	errs := make(chan string, rotates+1)
	start := make(chan struct{})
	for i := 0; i < rotates; i++ {
		go func() {
			<-start
			req := httptest.NewRequest(http.MethodPost, "/api/server/backup/rotate", strings.NewReader(`{}`))
			req.RemoteAddr = "127.0.0.1:5555"
			rec := httptest.NewRecorder()
			srv.handleBackupRotate(rec, req)
			if rec.Code != http.StatusOK {
				errs <- fmt.Sprintf("rotate %d: %s", rec.Code, rec.Body.String())
				return
			}
			errs <- ""
		}()
	}
	go func() {
		<-start
		if result := srv.ensureDailyRestorePoint(time.Now()); result.Status == "failed" {
			errs <- "daily restore point: " + result.Error
			return
		}
		errs <- ""
	}()
	close(start)
	for i := 0; i < rotates+1; i++ {
		if msg := <-errs; msg != "" {
			t.Error(msg)
		}
	}
	if got := countManagedBackups(t, dir); got < 1 || got > rotates+1 {
		t.Fatalf("managed backups after concurrent run = %d", got)
	}
	if srv.ensureDailyRestorePoint(time.Now()).Status != "skipped" {
		t.Fatal("a fresh restore point exists, the next startup check must skip")
	}
}

func TestPlainRuntimeServerDoesNotCreateRestorePoint(t *testing.T) {
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", "prism_runtime_dev.db", t.TempDir(), false, false, false, false, false, false)
	if err != nil {
		t.Fatal(err)
	}
	cfg.enableServerSystem = true
	srv, cleanup, err := newRuntimeServer(cfg)
	if err != nil {
		t.Fatal(err)
	}
	defer cleanup()
	time.Sleep(200 * time.Millisecond) // give any stray background check time to run
	if got := countManagedBackups(t, srv.runtime.backupsDir); got != 0 {
		t.Fatalf("plain runtime created %d managed backups; the daily restore point is desktop-only", got)
	}
	if srv.autoRestorePoint.Load() != nil {
		t.Fatal("plain runtime must not run the daily restore point check")
	}
}
