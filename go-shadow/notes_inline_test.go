package main

import (
	"archive/zip"
	"bytes"
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"testing"
	"time"
)

// PRISM-OPT-20: POST /api/system/inline-separated-notes merges auto-extracted long notes back
// into Notes.content. These tests drive the real runtime (fresh v17 DB, mux, csrfGate).

type inlineEnv struct {
	t       *testing.T
	srv     *server
	dataDir string
}

type inlineItemT struct {
	NoteID       int    `json:"note_id"`
	AttachmentID int    `json:"attachment_id"`
	FilePath     string `json:"file_path"`
	Reason       string `json:"reason"`
	Detail       string `json:"detail"`
	Action       string `json:"action"`
	Status       string `json:"status"`
	MovedTo      string `json:"moved_to"`
	MoveError    string `json:"move_error"`
	Error        string `json:"error"`
}

type inlineReportT struct {
	DryRun bool `json:"dry_run"`
	Counts struct {
		Actionable      int            `json:"actionable"`
		Merge           int            `json:"merge"`
		History         int            `json:"history"`
		Merged          int            `json:"merged"`
		Historied       int            `json:"historied"`
		MoveFailed      int            `json:"move_failed"`
		Failed          int            `json:"failed"`
		Skipped         int            `json:"skipped"`
		SkippedByReason map[string]int `json:"skipped_by_reason"`
		OrphanFiles     int            `json:"orphan_files"`
		SharedFiles     int            `json:"shared_files"`
		UnverifiedRows  int            `json:"unverified_rows"`
	} `json:"counts"`
	Merge       []inlineItemT `json:"merge"`
	History     []inlineItemT `json:"history"`
	Results     []inlineItemT `json:"results"`
	Skipped     []inlineItemT `json:"skipped"`
	OrphanFiles []struct {
		FilePath string `json:"file_path"`
	} `json:"orphan_files"`
	SharedFiles []struct {
		FilePath string `json:"file_path"`
		NoteIDs  []int  `json:"note_ids"`
	} `json:"shared_files"`
	UnverifiedRows []struct {
		AttachmentID int    `json:"attachment_id"`
		FilePath     string `json:"file_path"`
	} `json:"unverified_rows"`
	Aborted       bool    `json:"aborted"`
	AuditError    string  `json:"audit_error"`
	RestorePoint  *string `json:"restore_point"`
	QuarantineDir *string `json:"quarantine_dir"`
}

func newInlineEnv(t *testing.T) *inlineEnv {
	return newInlineEnvWith(t, true)
}

func newInlineEnvWith(t *testing.T, serverSystem bool) *inlineEnv {
	t.Helper()
	dataDir := t.TempDir()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", "prism_inline_test.db", dataDir,
		false, false, true, true, false, false,
		true, true, false, false, true, true, serverSystem)
	if err != nil {
		t.Fatal(err)
	}
	srv, cleanup, err := newRuntimeServer(cfg)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(cleanup)
	return &inlineEnv{t: t, srv: srv, dataDir: cfg.dataDir}
}

func (e *inlineEnv) do(method, target, body string, mutate ...func(*http.Request)) *httptest.ResponseRecorder {
	e.t.Helper()
	req := httptest.NewRequest(method, target, strings.NewReader(body))
	req.RemoteAddr = "127.0.0.1:5555"
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	for _, m := range mutate {
		m(req)
	}
	rec := httptest.NewRecorder()
	e.srv.httpServer.Handler.ServeHTTP(rec, req)
	return rec
}

func (e *inlineEnv) createNote(title, content string) int {
	e.t.Helper()
	body, _ := json.Marshal(map[string]any{"title": title, "content": content})
	rec := e.do(http.MethodPost, "/api/notes", string(body))
	if rec.Code != http.StatusCreated {
		e.t.Fatalf("create note: %d %s", rec.Code, rec.Body.String())
	}
	return noteIDFromResponse(e.t, rec.Body.Bytes())
}

func (e *inlineEnv) separate(id int) {
	e.t.Helper()
	rec := e.do(http.MethodPost, fmt.Sprintf("/api/notes/%d/separate", id), "{}")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"success"`) {
		e.t.Fatalf("separate %d: %d %s", id, rec.Code, rec.Body.String())
	}
}

func (e *inlineEnv) splitNote(title, content string) int {
	e.t.Helper()
	id := e.createNote(title, content)
	e.separate(id)
	return id
}

func (e *inlineEnv) notePath(id int) string {
	return filepath.Join(e.dataDir, "docs", "notes", fmt.Sprintf("note_%d.md", id))
}

func (e *inlineEnv) exec(query string, args ...any) {
	e.t.Helper()
	if _, err := e.srv.db.Exec(query, args...); err != nil {
		e.t.Fatalf("%s: %v", query, err)
	}
}

func (e *inlineEnv) content(id int) string {
	e.t.Helper()
	return noteContent(e.t, e.srv.db, id)
}

func (e *inlineEnv) autoRows(id int) int {
	e.t.Helper()
	var n int
	if err := e.srv.db.QueryRow("SELECT COUNT(*) FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1", id).Scan(&n); err != nil {
		e.t.Fatal(err)
	}
	return n
}

func (e *inlineEnv) insertRow(noteID int, filePath string, auto int) int {
	e.t.Helper()
	res, err := e.srv.db.Exec(`INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
		VALUES (?, ?, 'md', 'fixture', 1, ?)`, noteID, filePath, auto)
	if err != nil {
		e.t.Fatal(err)
	}
	id, _ := res.LastInsertId()
	return int(id)
}

func (e *inlineEnv) write(rel string, data []byte) {
	e.t.Helper()
	abs := filepath.Join(e.dataDir, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(abs), 0755); err != nil {
		e.t.Fatal(err)
	}
	if err := os.WriteFile(abs, data, 0644); err != nil {
		e.t.Fatal(err)
	}
}

func (e *inlineEnv) inline(body string) (int, inlineReportT, string) {
	e.t.Helper()
	rec := e.do(http.MethodPost, "/api/system/inline-separated-notes", body)
	var payload struct {
		Data inlineReportT `json:"data"`
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &payload)
	return rec.Code, payload.Data, rec.Body.String()
}

func (e *inlineEnv) mustInline(body string) inlineReportT {
	e.t.Helper()
	code, report, raw := e.inline(body)
	if code != http.StatusOK {
		e.t.Fatalf("inline-separated-notes %s: %d %s", body, code, raw)
	}
	return report
}

// fullSnapshot captures every row that matters plus a hash of every file under docs/notes and
// backups, so "nothing changed" claims compare more than title/content.
func (e *inlineEnv) fullSnapshot() string {
	e.t.Helper()
	var b strings.Builder
	dump := func(query string) {
		rows, err := e.srv.db.Query(query)
		if err != nil {
			e.t.Fatal(err)
		}
		defer rows.Close()
		cols, _ := rows.Columns()
		for rows.Next() {
			vals := make([]any, len(cols))
			ptrs := make([]any, len(cols))
			for i := range vals {
				ptrs[i] = &vals[i]
			}
			if err := rows.Scan(ptrs...); err != nil {
				e.t.Fatal(err)
			}
			for _, v := range vals {
				if raw, ok := v.([]byte); ok {
					v = string(raw)
				}
				fmt.Fprintf(&b, "%v|", v)
			}
			b.WriteString("\n")
		}
	}
	dump("SELECT id, title, content, updated_at, category_id, remarks, cover_image, is_pinned, is_archived FROM Notes ORDER BY id")
	dump("SELECT * FROM Note_Attachments ORDER BY id")
	dump("SELECT id, note_id, content, diff_summary FROM Note_History ORDER BY id")
	for _, root := range []string{"docs/notes", "backups", "docs/attachments"} {
		for _, line := range treeHashes(e.t, filepath.Join(e.dataDir, filepath.FromSlash(root))) {
			b.WriteString(root + "/" + line + "\n")
		}
	}
	return b.String()
}

func treeHashes(t *testing.T, root string) []string {
	t.Helper()
	lines := []string{}
	_ = filepath.WalkDir(root, func(p string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() || d.Type()&os.ModeSymlink != 0 || d.Type()&os.ModeIrregular != 0 {
			return nil
		}
		data, readErr := os.ReadFile(p)
		if readErr != nil {
			return nil
		}
		rel, _ := filepath.Rel(root, p)
		lines = append(lines, fmt.Sprintf("%s %x", filepath.ToSlash(rel), sha256.Sum256(data)))
		return nil
	})
	sort.Strings(lines)
	return lines
}

func quarantineDirs(t *testing.T, dataDir string) []string {
	t.Helper()
	entries, _ := os.ReadDir(filepath.Join(dataDir, "backups"))
	dirs := []string{}
	for _, entry := range entries {
		if entry.IsDir() && strings.HasPrefix(entry.Name(), "separated-notes-") {
			dirs = append(dirs, entry.Name())
		}
	}
	return dirs
}

func longCJK(cjkTail, asciiTail string) string {
	return strings.Repeat("今天整理長文合併的步驟與檢查清單，確認搜尋與匯出都完整。\n", 200) + "尾段" + cjkTail + " " + asciiTail
}

func reasonCount(r inlineReportT, reason string) int {
	return r.Counts.SkippedByReason[reason]
}

func skippedReason(r inlineReportT, attachmentID int) string {
	for _, item := range r.Skipped {
		if item.AttachmentID == attachmentID {
			return item.Reason
		}
	}
	return ""
}

func autoRowID(t *testing.T, db *sql.DB, noteID int) int {
	t.Helper()
	var id int
	if err := db.QueryRow("SELECT id FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1 ORDER BY id LIMIT 1", noteID).Scan(&id); err != nil {
		t.Fatal(err)
	}
	return id
}

func historyCount(t *testing.T, db *sql.DB, noteID int) int {
	t.Helper()
	var n int
	if err := db.QueryRow("SELECT COUNT(*) FROM Note_History WHERE note_id = ?", noteID).Scan(&n); err != nil {
		t.Fatal(err)
	}
	return n
}

func updatedAt(t *testing.T, db *sql.DB, noteID int) string {
	t.Helper()
	var v string
	if err := db.QueryRow("SELECT updated_at FROM Notes WHERE id = ?", noteID).Scan(&v); err != nil {
		t.Fatal(err)
	}
	return v
}

// specFixture: two split notes, one split note whose file is gone, one normal note.
func specFixture(t *testing.T) (*inlineEnv, int, int, int, int, string, string) {
	t.Helper()
	e := newInlineEnv(t)
	contentA := longCJK("龍眼乾", "tailalphaopt20")
	contentB := longCJK("鳳梨酥", "tailbetaopt20")
	a := e.splitNote("長文 A", contentA)
	b := e.splitNote("長文 B", contentB)
	c := e.splitNote("長文 C", longCJK("杏仁茶", "tailgammaopt20"))
	if err := os.Remove(e.notePath(c)); err != nil {
		t.Fatal(err)
	}
	d := e.createNote("一般筆記", "短短的一般筆記內容")
	return e, a, b, c, d, contentA, contentB
}

func TestInlineSeparatedNotesDryRunCountsSpecFixture(t *testing.T) {
	e, a, b, c, _, _, _ := specFixture(t)
	before := e.fullSnapshot()

	report := e.mustInline(`{"dry_run":true}`)
	if !report.DryRun || report.Counts.Merge != 2 || report.Counts.History != 0 || report.Counts.Actionable != 2 {
		t.Fatalf("unexpected counts: %+v", report.Counts)
	}
	if reasonCount(report, "missing_file") != 1 || report.Counts.Skipped != 1 {
		t.Fatalf("missing file should be the only skip: %+v", report.Counts)
	}
	ids := map[int]bool{}
	for _, item := range report.Merge {
		ids[item.NoteID] = true
	}
	if !ids[a] || !ids[b] {
		t.Fatalf("merge list should hold %d and %d: %+v", a, b, report.Merge)
	}
	if skippedReason(report, autoRowID(t, e.srv.db, c)) != "missing_file" {
		t.Fatalf("note %d should be missing_file: %+v", c, report.Skipped)
	}
	if report.RestorePoint != nil || report.QuarantineDir != nil {
		t.Fatal("dry-run must not create a restore point")
	}
	if after := e.fullSnapshot(); after != before {
		t.Fatalf("dry-run changed data:\n%s\n---\n%s", before, after)
	}
	if dirs := quarantineDirs(t, e.dataDir); len(dirs) != 0 {
		t.Fatalf("dry-run created %v", dirs)
	}
}

func TestInlineSeparatedNotesExecuteMergesMovesAndKeepsRestorePoint(t *testing.T) {
	e, a, b, c, d, contentA, contentB := specFixture(t)
	fileA, err := os.ReadFile(e.notePath(a))
	if err != nil {
		t.Fatal(err)
	}
	previewC := e.content(c)
	stampA, stampB := updatedAt(t, e.srv.db, a), updatedAt(t, e.srv.db, b)

	// A write that is still only in the WAL must reach the restore point.
	marker := "walmarkeropt20"
	if rec := e.do(http.MethodPut, fmt.Sprintf("/api/notes/%d", d), `{"title":"`+marker+`","content":"短短的一般筆記內容"}`); rec.Code != http.StatusOK {
		t.Fatalf("put: %d %s", rec.Code, rec.Body.String())
	}
	dbPath := e.srv.runtime.dbPath
	mainBytes, _ := os.ReadFile(dbPath)
	walBytes, _ := os.ReadFile(dbPath + "-wal")
	if bytes.Contains(mainBytes, []byte(marker)) || !bytes.Contains(walBytes, []byte(marker)) {
		t.Fatalf("fixture must keep the marker in the WAL only (main=%v wal=%v)", bytes.Contains(mainBytes, []byte(marker)), bytes.Contains(walBytes, []byte(marker)))
	}

	report := e.mustInline(`{"dry_run":false}`)
	if report.DryRun || report.Counts.Merged != 2 || report.Counts.Failed != 0 || report.Aborted || report.AuditError != "" {
		t.Fatalf("unexpected execute report: %+v", report)
	}
	if e.content(a) != contentA || e.content(b) != contentB {
		t.Fatal("merged notes must hold the full text")
	}
	if e.autoRows(a) != 0 || e.autoRows(b) != 0 || e.autoRows(c) != 1 || e.content(c) != previewC {
		t.Fatal("only the mergeable notes may change")
	}
	if historyCount(t, e.srv.db, a) != 0 || historyCount(t, e.srv.db, b) != 0 {
		t.Fatal("merging a generated preview must not write history")
	}
	if updatedAt(t, e.srv.db, a) != stampA || updatedAt(t, e.srv.db, b) != stampB {
		t.Fatal("merge must keep updated_at")
	}
	assertFTSCount(t, e.srv.db, "tailalphaopt20", 1)
	assertFTSCount(t, e.srv.db, "tailbetaopt20", 1)
	for _, q := range []string{"龍眼乾", "tailalphaopt20"} {
		rec := e.do(http.MethodGet, "/api/notes?per_page=50&q="+url.QueryEscape(q), "")
		if rec.Code != http.StatusOK || strings.Contains(rec.Body.String(), "search_diagnostics") {
			t.Fatalf("search %q: %d %s", q, rec.Code, rec.Body.String())
		}
		assertNotesSearchIncludes(t, e.srv, "/api/notes?per_page=50&q="+url.QueryEscape(q), a)
	}

	jsonExport := e.do(http.MethodGet, "/api/export/json", "")
	if jsonExport.Code != http.StatusOK || !strings.Contains(jsonExport.Body.String(), "tailalphaopt20") || !strings.Contains(jsonExport.Body.String(), "鳳梨酥") {
		t.Fatalf("JSON export must hold the tails: %d", jsonExport.Code)
	}
	mdExport := e.do(http.MethodGet, "/api/export/markdown", "")
	zr, err := zip.NewReader(bytes.NewReader(mdExport.Body.Bytes()), int64(mdExport.Body.Len()))
	if err != nil {
		t.Fatal(err)
	}
	found := 0
	for _, f := range zr.File {
		rc, _ := f.Open()
		data, _ := io.ReadAll(rc)
		rc.Close()
		if bytes.Contains(data, []byte("tailalphaopt20")) || bytes.Contains(data, []byte("tailbetaopt20")) {
			found++
		}
	}
	if found != 2 {
		t.Fatalf("markdown export should hold both tails, found %d", found)
	}

	if report.QuarantineDir == nil || report.RestorePoint == nil {
		t.Fatalf("execute must report quarantine dir and restore point: %+v", report)
	}
	qdir := filepath.Join(e.dataDir, filepath.FromSlash(*report.QuarantineDir))
	if _, err := os.Stat(e.notePath(a)); !os.IsNotExist(err) {
		t.Fatalf("source file should be moved, got %v", err)
	}
	moved, err := os.ReadFile(filepath.Join(qdir, "docs", "notes", fmt.Sprintf("note_%d.md", a)))
	if err != nil || !bytes.Equal(moved, fileA) {
		t.Fatalf("quarantined file must match the original bytes: %v", err)
	}
	for _, name := range []string{"plan.json", "moves.tsv", "result.json"} {
		if _, err := os.Stat(filepath.Join(qdir, name)); err != nil {
			t.Fatalf("missing %s: %v", name, err)
		}
	}
	restorePoint := filepath.Join(e.dataDir, filepath.FromSlash(*report.RestorePoint))
	if err := validateSQLiteBackup(restorePoint); err != nil {
		t.Fatal(err)
	}
	snap, err := sql.Open("sqlite", sqliteDSN(restorePoint, false))
	if err != nil {
		t.Fatal(err)
	}
	defer snap.Close()
	var oldA, titleD string
	if err := snap.QueryRow("SELECT content FROM Notes WHERE id = ?", a).Scan(&oldA); err != nil {
		t.Fatal(err)
	}
	if !strings.HasSuffix(oldA, separatedPreviewBanner) {
		t.Fatal("restore point must hold the pre-merge preview")
	}
	if err := snap.QueryRow("SELECT title FROM Notes WHERE id = ?", d).Scan(&titleD); err != nil || titleD != marker {
		t.Fatalf("restore point must include the WAL-only write, got %q %v", titleD, err)
	}
}

func TestInlineSeparatedNotesSecondRunChangesNothing(t *testing.T) {
	e, _, _, _, _, _, _ := specFixture(t)
	e.mustInline(`{"dry_run":false}`)
	before := e.fullSnapshot()
	report := e.mustInline(`{"dry_run":false}`)
	if report.Counts.Actionable != 0 || report.Counts.Merged != 0 || report.RestorePoint != nil || report.QuarantineDir != nil || len(report.Results) != 0 {
		t.Fatalf("second run must be a no-op: %+v", report)
	}
	if after := e.fullSnapshot(); after != before {
		t.Fatalf("second run changed data:\n%s\n---\n%s", before, after)
	}
	if dirs := quarantineDirs(t, e.dataDir); len(dirs) != 1 {
		t.Fatalf("expected exactly one quarantine dir, got %v", dirs)
	}
}

func TestInlineSeparatedNotesHistoryKeepsDBTextAndStoresFileText(t *testing.T) {
	e := newInlineEnv(t)
	full := longCJK("芋頭酥", "tailhistoryopt20")
	x := e.splitNote("改短過的長文", full)
	fileX, _ := os.ReadFile(e.notePath(x))
	short := "使用者在 OPT-19 之前改短的內容 shortsavedopt20"
	e.exec("UPDATE Notes SET content = ? WHERE id = ?", short, x)

	dry := e.mustInline("")
	if dry.Counts.History != 1 || dry.Counts.Actionable != 1 || dry.Counts.Merge != 0 {
		t.Fatalf("divergent note should be one history action: %+v", dry.Counts)
	}
	report := e.mustInline(`{"dry_run":false}`)
	if report.Counts.Historied != 1 || report.RestorePoint == nil {
		t.Fatalf("history action should run with a restore point: %+v", report)
	}
	if e.content(x) != short {
		t.Fatal("D2 keeps the DB text")
	}
	var hist string
	if err := e.srv.db.QueryRow("SELECT content FROM Note_History WHERE note_id = ?", x).Scan(&hist); err != nil || hist != full {
		t.Fatalf("history must hold the file text: %v", err)
	}
	if e.autoRows(x) != 0 {
		t.Fatal("auto row must be removed")
	}
	moved, err := os.ReadFile(filepath.Join(e.dataDir, filepath.FromSlash(*report.QuarantineDir), "docs", "notes", fmt.Sprintf("note_%d.md", x)))
	if err != nil || !bytes.Equal(moved, fileX) {
		t.Fatalf("file must be quarantined: %v", err)
	}
	if again := e.mustInline(`{"dry_run":false}`); again.Counts.Actionable != 0 || again.RestorePoint != nil {
		t.Fatalf("second run must be a no-op: %+v", again.Counts)
	}
}

func TestInlineSeparatedNotesDanglingRowsAreListedNeverDeleted(t *testing.T) {
	e := newInlineEnv(t)
	n := e.splitNote("懸空列", longCJK("綠豆糕", "taildanglingopt20"))
	full := longCJK("綠豆糕", "taildanglingopt20")
	e.exec("UPDATE Notes SET content = ? WHERE id = ?", full, n)
	if err := os.Remove(e.notePath(n)); err != nil {
		t.Fatal(err)
	}
	before := e.fullSnapshot()
	report := e.mustInline(`{"dry_run":false}`)
	if report.Counts.Actionable != 0 || reasonCount(report, "dangling_row") != 1 || report.RestorePoint != nil {
		t.Fatalf("dangling row must be listed only: %+v", report.Counts)
	}
	if after := e.fullSnapshot(); after != before {
		t.Fatal("dangling-only run must not change anything")
	}
}

func TestInlineSeparatedNotesMediaProtectionForHistoryActions(t *testing.T) {
	e := newInlineEnv(t)
	png := []byte("\x89PNG\r\n\x1a\nfixture")
	for _, name := range []string{"img_only_file.png", "img_shared.png", "img_two_d2.png", "img_merge.png"} {
		e.write("static/uploads/"+name, png)
	}
	divergent := func(title, tail string) int {
		full := longCJK(title, tail)
		id := e.splitNote(title, full)
		e.exec("UPDATE Notes SET content = ? WHERE id = ?", "改短 "+title, id)
		return id
	}
	// (a) image referenced only by the D2 file text.
	onlyFile := e.splitNote("媒體甲", longCJK("媒體甲", "![a](/static/uploads/img_only_file.png)"))
	e.exec("UPDATE Notes SET content = ? WHERE id = ?", "改短 媒體甲", onlyFile)
	// (b) also referenced by another note's content.
	shared := e.splitNote("媒體乙", longCJK("媒體乙", "![b](/static/uploads/img_shared.png)"))
	e.exec("UPDATE Notes SET content = ? WHERE id = ?", "改短 媒體乙", shared)
	e.createNote("保護者", "![p](/static/uploads/img_shared.png)")
	// (c) two D2 candidates referencing an image no one else references.
	twoA := divergent("媒體丙", "![c](/static/uploads/img_two_d2.png)")
	twoB := divergent("媒體丁", "![c](/static/uploads/img_two_d2.png)")
	// (d) a merge candidate referencing an image only in its file.
	merge := e.splitNote("媒體戊", longCJK("媒體戊", "![d](/static/uploads/img_merge.png)"))

	report := e.mustInline(`{"dry_run":false}`)
	for _, id := range []int{onlyFile, twoA, twoB} {
		if skippedReason(report, autoRowID(t, e.srv.db, id)) != "media_unprotected" {
			t.Fatalf("note %d should be media_unprotected: %+v", id, report.Skipped)
		}
	}
	if e.autoRows(shared) != 0 || e.autoRows(merge) != 0 {
		t.Fatal("protected D2 and the merge candidate should be processed")
	}
	orphans := e.do(http.MethodGet, "/api/cleanup/orphan-images", "")
	for _, name := range []string{"img_only_file.png", "img_shared.png", "img_two_d2.png", "img_merge.png"} {
		if strings.Contains(orphans.Body.String(), name) {
			t.Fatalf("%s must stay protected after the run: %s", name, orphans.Body.String())
		}
	}
}

func TestInlineSeparatedNotesSharedAndAliasedFilesAreListed(t *testing.T) {
	e := newInlineEnv(t)
	other := e.createNote("其他筆記", "其他")

	same := e.splitNote("同路徑", longCJK("同路徑", "tailsameopt20"))
	e.insertRow(other, fmt.Sprintf("docs/notes/note_%d.md", same), 0)

	sameNote := e.splitNote("同筆記一般附件", longCJK("同筆記", "tailsamenoteopt20"))
	e.insertRow(sameNote, fmt.Sprintf("docs/notes/note_%d.md", sameNote), 0)

	hard := e.splitNote("硬連結", longCJK("硬連結", "tailhardopt20"))
	alias := filepath.Join(e.dataDir, "docs", "attachments", "alias.md")
	if err := os.Link(e.notePath(hard), alias); err != nil {
		t.Fatalf("hard link fixture: %v", err)
	}
	e.insertRow(other, "docs/attachments/alias.md", 0)

	caseNote := e.splitNote("大小寫", longCJK("大小寫", "tailcaseopt20"))
	caseInsensitive := false
	if _, err := os.Stat(strings.Replace(e.notePath(caseNote), "note_", "NOTE_", 1)); err == nil {
		caseInsensitive = true
		e.insertRow(other, fmt.Sprintf("docs/notes/NOTE_%d.md", caseNote), 0)
	}

	before := e.fullSnapshot()
	report := e.mustInline(`{"dry_run":false}`)
	expect := []int{same, sameNote, hard}
	if caseInsensitive {
		expect = append(expect, caseNote)
	}
	for _, id := range expect {
		if skippedReason(report, autoRowID(t, e.srv.db, id)) != "shared_file" {
			t.Fatalf("note %d should be shared_file: %+v", id, report.Skipped)
		}
	}
	if caseInsensitive {
		if report.Counts.Actionable != 0 || e.fullSnapshot() != before {
			t.Fatal("only shared notes exist; nothing may change")
		}
	}
}

func TestInlineSeparatedNotesSkipsJunctionedNotesDirAndBackups(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip("junction fixtures use mklink /J")
	}
	t.Run("notes dir is a junction", func(t *testing.T) {
		e := newInlineEnv(t)
		a := e.splitNote("連結", longCJK("連結", "tailjunctionopt20"))
		notes := filepath.Join(e.dataDir, "docs", "notes")
		real := filepath.Join(e.dataDir, "realnotes")
		if err := os.Rename(notes, real); err != nil {
			t.Fatal(err)
		}
		mklinkJunction(t, notes, real)
		report := e.mustInline(`{"dry_run":false}`)
		if skippedReason(report, autoRowID(t, e.srv.db, a)) != "unsafe_path" || report.Counts.Actionable != 0 {
			t.Fatalf("junctioned docs/notes must be unsafe_path: %+v", report)
		}
		if _, err := os.Stat(filepath.Join(real, fmt.Sprintf("note_%d.md", a))); err != nil {
			t.Fatal("file behind the junction must stay")
		}
	})
	t.Run("subdirectory junction into attachments", func(t *testing.T) {
		e := newInlineEnv(t)
		n := e.createNote("附件連結", "附件連結")
		e.write("docs/attachments/user.md", []byte("使用者附件"))
		mklinkJunction(t, filepath.Join(e.dataDir, "docs", "notes", "link"), filepath.Join(e.dataDir, "docs", "attachments"))
		row := e.insertRow(n, "docs/notes/link/user.md", 1)
		report := e.mustInline(`{"dry_run":false}`)
		if reason := skippedReason(report, row); reason != "nonstandard_path" && reason != "unsafe_path" {
			t.Fatalf("link path must be skipped, got %q", reason)
		}
		if data, err := os.ReadFile(filepath.Join(e.dataDir, "docs", "attachments", "user.md")); err != nil || string(data) != "使用者附件" {
			t.Fatal("user attachment must stay untouched")
		}
	})
	t.Run("backups is a junction", func(t *testing.T) {
		e := newInlineEnv(t)
		a := e.splitNote("備份連結", longCJK("備份連結", "tailbackupsopt20"))
		backups := filepath.Join(e.dataDir, "backups")
		elsewhere := filepath.Join(e.dataDir, "elsewhere")
		if err := os.Rename(backups, elsewhere); err != nil {
			t.Fatal(err)
		}
		mklinkJunction(t, backups, elsewhere)
		code, _, raw := e.inline(`{"dry_run":false}`)
		if code != http.StatusInternalServerError || !strings.Contains(raw, `"notes_changed":0`) {
			t.Fatalf("junctioned backups must refuse with notes_changed 0: %d %s", code, raw)
		}
		if e.autoRows(a) != 1 {
			t.Fatal("nothing may change")
		}
	})
}

func mklinkJunction(t *testing.T, link, target string) {
	t.Helper()
	if out, err := exec.Command("cmd", "/c", "mklink", "/J", link, target).CombinedOutput(); err != nil {
		t.Skipf("mklink /J unavailable: %v %s", err, out)
	}
	t.Cleanup(func() { _ = os.Remove(link) })
}

func TestInlineSeparatedNotesParsesRequestStrictly(t *testing.T) {
	e, a, _, _, _, _, _ := specFixture(t)
	before := e.fullSnapshot()
	for _, body := range []string{"", "  ", "{}", `{"dry_run":null}`, `{"dry_run":true}`, `{"other":[1,{"x":2}]}`} {
		code, report, raw := e.inline(body)
		if code != http.StatusOK || !report.DryRun {
			t.Fatalf("%q should be a dry-run: %d %s", body, code, raw)
		}
	}
	bad := []string{
		"[]", "null", `"x"`, "{", `{"dry_run":"no"}`, `{"dry_run":0}`,
		`{"dry_run":false} x`, `{"dry_run":false}{}`, `{"dry_run":true,"dry_run":false}`,
		`{"dry_run":false,"pad":"` + strings.Repeat("x", 1<<20) + `"}`,
	}
	for _, body := range bad {
		if code, _, raw := e.inline(body); code != http.StatusBadRequest {
			t.Fatalf("%.40q should be rejected: %d %.200s", body, code, raw)
		}
	}
	if after := e.fullSnapshot(); after != before {
		t.Fatal("rejected or dry-run requests must not change data")
	}
	if report := e.mustInline(`{"dry_run":false}`); report.Counts.Merged != 2 || e.autoRows(a) != 0 {
		t.Fatalf("explicit false executes: %+v", report.Counts)
	}
}

func TestInlineSeparatedNotesGates(t *testing.T) {
	disabled := newInlineEnvWith(t, false)
	if rec := disabled.do(http.MethodPost, "/api/system/inline-separated-notes", "{}"); rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("disabled server-system should be 405, got %d", rec.Code)
	}
	e := newInlineEnv(t)
	if rec := e.do(http.MethodGet, "/api/system/inline-separated-notes", ""); rec.Code != http.StatusMethodNotAllowed || rec.Header().Get("Allow") != http.MethodPost {
		t.Fatalf("GET should be 405 with Allow: POST, got %d %q", rec.Code, rec.Header().Get("Allow"))
	}
	remote := e.do(http.MethodPost, "/api/system/inline-separated-notes", "{}", func(r *http.Request) { r.RemoteAddr = "192.0.2.10:4000" })
	if remote.Code != http.StatusForbidden {
		t.Fatalf("non-loopback peer should be 403, got %d", remote.Code)
	}
	crossOrigin := func(r *http.Request) { r.Header.Set("Origin", "http://evil.example") }
	if rec := e.do(http.MethodPost, "/api/system/inline-separated-notes", "{}", crossOrigin); rec.Code != http.StatusForbidden {
		t.Fatalf("cross-origin should be blocked by csrfGate, got %d", rec.Code)
	}
	// Documented current behavior: the gate checks only the direct peer, so a loopback reverse
	// proxy (Pi Caddy) forwards LAN requests; X-Forwarded-For is not trusted either way.
	proxied := e.do(http.MethodPost, "/api/system/inline-separated-notes", "{}", func(r *http.Request) { r.Header.Set("X-Forwarded-For", "192.168.1.20") })
	if proxied.Code != http.StatusOK {
		t.Fatalf("loopback peer with X-Forwarded-For is allowed today, got %d", proxied.Code)
	}
	if rec := e.do(http.MethodPost, "/api/system/csrf-protection", `{"csrf_protection":false}`); rec.Code != http.StatusOK {
		t.Fatalf("disable csrf: %d", rec.Code)
	}
	if rec := e.do(http.MethodPost, "/api/system/inline-separated-notes", "{}", crossOrigin); rec.Code != http.StatusOK {
		t.Fatalf("with CSRF protection off a cross-origin request passes, got %d", rec.Code)
	}
}

func TestInlineSeparatedNotesDBFailureRollsBackAndAborts(t *testing.T) {
	e := newInlineEnv(t)
	first := e.splitNote("第一篇", longCJK("第一篇", "tailfirstopt20"))
	divergent := e.splitNote("分歧", longCJK("分歧", "taildivergentopt20"))
	e.exec("UPDATE Notes SET content = ? WHERE id = ?", "改短的分歧內容", divergent)
	last := e.splitNote("最後一篇", longCJK("最後一篇", "taillastopt20"))
	e.exec("CREATE TRIGGER inline_fail_history BEFORE INSERT ON Note_History BEGIN SELECT RAISE(ABORT, 'boom'); END")

	report := e.mustInline(`{"dry_run":false}`)
	if !report.Aborted || report.Counts.Failed != 1 || report.Counts.Merged != 1 {
		t.Fatalf("history failure should abort after one merge: %+v", report)
	}
	if e.autoRows(first) != 0 {
		t.Fatal("note before the failure stays merged")
	}
	if e.autoRows(divergent) != 1 || e.content(divergent) != "改短的分歧內容" {
		t.Fatal("failed D2 note must roll back fully")
	}
	if _, err := os.Stat(e.notePath(divergent)); err != nil {
		t.Fatal("failed note keeps its file")
	}
	if e.autoRows(last) != 1 {
		t.Fatal("notes after an abort are not processed")
	}

	e.exec("DROP TRIGGER inline_fail_history")
	e.exec(fmt.Sprintf("CREATE TRIGGER inline_fail_update BEFORE UPDATE OF content ON Notes WHEN NEW.id = %d BEGIN SELECT RAISE(ABORT, 'boom'); END", last))
	again := e.mustInline(`{"dry_run":false}`)
	if !again.Aborted || e.autoRows(last) != 1 {
		t.Fatalf("merge UPDATE failure must roll back the DELETE: %+v", again)
	}
}

func TestInlineSeparatedNotesTextEdgeCases(t *testing.T) {
	e := newInlineEnv(t)
	base := longCJK("邊角", "tailedgeopt20")

	crlf := e.splitNote("CRLF", base)
	e.write(fmt.Sprintf("docs/notes/note_%d.md", crlf), []byte(strings.ReplaceAll(base, "\n", "\r\n")))
	loneCR := e.splitNote("CR", base)
	e.write(fmt.Sprintf("docs/notes/note_%d.md", loneCR), []byte(strings.ReplaceAll(base, "\n", "\r")))
	bomBoth := e.splitNote("BOM 兩邊", "\ufeff"+base)
	bomFile := e.splitNote("BOM 檔案", base)
	e.write(fmt.Sprintf("docs/notes/note_%d.md", bomFile), []byte("\ufeff"+base))
	fullBanner := e.splitNote("全文加橫幅", base)
	e.exec("UPDATE Notes SET content = ? WHERE id = ?", base+separatedPreviewBanner, fullBanner)
	badUTF8 := e.splitNote("非 UTF-8", base)
	e.write(fmt.Sprintf("docs/notes/note_%d.md", badUTF8), []byte(base+"\xff\xfe"))

	line := "abcdefghij" + string(rune(10))
	exact := strings.Repeat(line, (int(maxAttachmentFileBytes)-len("tailexactopt20"))/len(line)) + "tailexactopt20"
	exact += strings.Repeat("z", int(maxAttachmentFileBytes)-len(exact))
	exactID := e.splitNote("剛好 1 MiB", exact)
	overID := e.splitNote("超過 1 MiB", exact+"!")

	report := e.mustInline(`{"dry_run":false}`)
	for _, id := range []int{crlf, loneCR, bomBoth, exactID} {
		if e.autoRows(id) != 0 {
			t.Fatalf("note %d should merge: %+v", id, report.Skipped)
		}
	}
	if e.content(crlf) != base || e.content(loneCR) != base || e.content(bomBoth) != "\ufeff"+base || e.content(exactID) != exact {
		t.Fatal("merged text must be the normalized file text")
	}
	want := map[int]string{bomFile: "preview_mismatch", fullBanner: "preview_mismatch", badUTF8: "unreadable", overID: "too_large"}
	for id, reason := range want {
		if got := skippedReason(report, autoRowID(t, e.srv.db, id)); got != reason {
			t.Fatalf("note %d: got %q want %q", id, got, reason)
		}
	}
}

func TestInlineSeparatedNotesListsOtherClasses(t *testing.T) {
	e := newInlineEnv(t)
	n := e.createNote("其他", "其他")
	e.write("docs/attachments/x.md", []byte("x"))
	attachmentsRow := e.insertRow(n, "docs/attachments/x.md", 1)
	traversal := e.insertRow(e.createNote("路徑穿越", "路徑穿越"), "../x.md", 1)

	foreign := e.splitNote("外來", longCJK("外來", "tailforeignopt20"))
	borrower := e.createNote("借用者", "借用")
	if err := os.Rename(e.notePath(foreign), filepath.Join(e.dataDir, "docs", "notes", "note_999999.md")); err != nil {
		t.Fatal(err)
	}
	e.exec("UPDATE Note_Attachments SET file_path = 'docs/notes/note_999999.md' WHERE note_id = ?", foreign)
	e.write(fmt.Sprintf("docs/notes/sub/note_%d.md", borrower), []byte("子目錄"))
	subdirRow := e.insertRow(borrower, fmt.Sprintf("docs/notes/sub/note_%d.md", borrower), 1)

	multi := e.splitNote("多個自動附件", longCJK("多個", "tailmultiopt20"))
	extra := e.insertRow(multi, fmt.Sprintf("docs/notes/note_%d.md", multi), 1)

	conn, err := e.srv.db.Conn(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	_, _ = conn.ExecContext(context.Background(), "PRAGMA foreign_keys = OFF")
	if _, err := conn.ExecContext(context.Background(), `INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
		VALUES (987654, 'docs/notes/note_987654.md', 'md', 'ghost', 1, 1)`); err != nil {
		t.Fatal(err)
	}
	_, _ = conn.ExecContext(context.Background(), "PRAGMA foreign_keys = ON")
	conn.Close()

	e.write("docs/notes/stray.md", []byte("沒有人引用"))
	// A dangling row (missing file) elsewhere can't alias anything and must not block candidates.
	dangling := e.createNote("懸空", "懸空")
	e.insertRow(dangling, "docs/notes/gone.md", 0)
	ok := e.splitNote("可合併", longCJK("可合併", "tailokopt20"))

	report := e.mustInline(`{"dry_run":false}`)
	checks := map[int]string{
		attachmentsRow:                  "invalid_path",
		traversal:                       "invalid_path",
		autoRowID(t, e.srv.db, foreign): "nonstandard_path",
		subdirRow:                       "nonstandard_path",
		autoRowID(t, e.srv.db, multi):   "multiple_auto_rows",
		extra:                           "multiple_auto_rows",
	}
	for row, reason := range checks {
		if got := skippedReason(report, row); got != reason {
			t.Fatalf("row %d: got %q want %q (%+v)", row, got, reason, report.Skipped)
		}
	}
	if reasonCount(report, "note_missing") != 1 {
		t.Fatalf("ghost row should be note_missing: %+v", report.Counts)
	}
	if report.Counts.OrphanFiles == 0 || !strings.Contains(fmt.Sprint(report.OrphanFiles), "docs/notes/stray.md") {
		t.Fatalf("stray file should be an orphan: %+v", report.OrphanFiles)
	}
	if report.Counts.Merged != 1 || e.autoRows(ok) != 0 || report.Counts.UnverifiedRows != 0 {
		t.Fatalf("the mergeable note must not be blocked by listed rows: %+v", report.Counts)
	}
	if _, err := os.Stat(filepath.Join(e.dataDir, "docs", "notes", "stray.md")); err != nil {
		t.Fatal("orphan files stay in place")
	}
	if _, err := os.Stat(filepath.Join(e.dataDir, "docs", "attachments", "x.md")); err != nil {
		t.Fatal("user attachments stay in place")
	}
}

func resultFor(t *testing.T, r inlineReportT, noteID int) inlineItemT {
	t.Helper()
	for _, item := range r.Results {
		if item.NoteID == noteID {
			return item
		}
	}
	t.Fatalf("no result for note %d: %+v", noteID, r.Results)
	return inlineItemT{}
}

func TestInlineSeparatedNotesSkipsSourceChangedAfterClassification(t *testing.T) {
	mutations := map[string]func(t *testing.T, path string){
		"rewritten": func(t *testing.T, path string) {
			if err := os.WriteFile(path, []byte(longCJK("改寫", "tailrewrittenopt20")), 0644); err != nil {
				t.Fatal(err)
			}
		},
		"same bytes, new file": func(t *testing.T, path string) {
			data, _ := os.ReadFile(path)
			if err := os.WriteFile(path+".swap", data, 0644); err != nil {
				t.Fatal(err)
			}
			if err := os.Rename(path+".swap", path); err != nil {
				t.Fatal(err)
			}
		},
		"grew past 1 MiB": func(t *testing.T, path string) {
			if err := os.WriteFile(path, bytes.Repeat([]byte("x"), int(maxAttachmentFileBytes)+10), 0644); err != nil {
				t.Fatal(err)
			}
		},
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			e := newInlineEnv(t)
			a := e.splitNote("被換掉", longCJK("被換掉", "tailswapopt20"))
			b := e.splitNote("正常", longCJK("正常", "tailnormalopt20"))
			e.srv.testHook = func(stage string, id int) error {
				if stage == "before_note" && id == a {
					mutate(t, e.notePath(a))
				}
				return nil
			}
			report := e.mustInline(`{"dry_run":false}`)
			if got := resultFor(t, report, a); got.Status != "skipped" || got.Reason != "changed_during_run" {
				t.Fatalf("changed source must be skipped: %+v", got)
			}
			if e.autoRows(a) != 1 || e.autoRows(b) != 0 {
				t.Fatal("only the unchanged note may merge")
			}
			if _, err := os.Stat(e.notePath(a)); err != nil {
				t.Fatal("changed source must stay in docs/notes")
			}
		})
	}
}

// waitBriefly gives a goroutine a chance to finish; a result means it was not blocked.
func waitBriefly(ch chan int) (int, bool) {
	select {
	case code := <-ch:
		return code, true
	case <-time.After(300 * time.Millisecond):
		return 0, false
	}
}

func TestInlineSeparatedNotesBlocksRestoreUntilRunEnds(t *testing.T) {
	e := newInlineEnv(t)
	e.splitNote("先處理", longCJK("先處理", "tailfirstnoteopt20"))
	b := e.splitNote("被存檔", longCJK("被存檔", "tailsavedopt20"))
	fileB, _ := os.ReadFile(e.notePath(b))
	restoreDone := make(chan int, 1)
	finishedEarly := false
	e.srv.testHook = func(stage string, id int) error {
		if stage == "before_note" && id == b {
			go func() {
				restoreDone <- e.do(http.MethodPost, fmt.Sprintf("/api/notes/%d/restore", b), "{}").Code
			}()
			if code, done := waitBriefly(restoreDone); done {
				finishedEarly = true
				restoreDone <- code
			}
		}
		return nil
	}
	report := e.mustInline(`{"dry_run":false}`)
	if finishedEarly {
		t.Fatal("restore finished while the maintenance run held noteFilesMu")
	}
	var code int
	select {
	case code = <-restoreDone:
	case <-time.After(10 * time.Second):
		t.Fatal("restore never finished")
	}
	if code != http.StatusNotFound {
		t.Fatalf("restore after the merge finds no auto row: got %d", code)
	}
	got := resultFor(t, report, b)
	if got.Status != "merged" || got.MovedTo == "" {
		t.Fatalf("note B must be merged and moved: %+v", got)
	}
	moved, err := os.ReadFile(filepath.Join(e.dataDir, filepath.FromSlash(got.MovedTo)))
	if err != nil || !bytes.Equal(moved, fileB) {
		t.Fatalf("quarantine must hold B's original file: %v", err)
	}
	snap, err := sql.Open("sqlite", sqliteDSN(filepath.Join(e.dataDir, filepath.FromSlash(*report.RestorePoint)), false))
	if err != nil {
		t.Fatal(err)
	}
	defer snap.Close()
	var rows int
	if err := snap.QueryRow("SELECT COUNT(*) FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1", b).Scan(&rows); err != nil || rows != 1 {
		t.Fatalf("restore point must pair with the quarantine: rows=%d err=%v", rows, err)
	}
}

func TestInlineSeparatedNotesBlocksNoteDeleteUntilRunEnds(t *testing.T) {
	e := newInlineEnv(t)
	e.splitNote("先處理", longCJK("先處理", "tailfirstdelopt20"))
	b := e.splitNote("被刪除", longCJK("被刪除", "taildeletedopt20"))
	deleteDone := make(chan int, 1)
	finishedEarly := false
	e.srv.testHook = func(stage string, id int) error {
		if stage == "before_note" && id == b {
			go func() { deleteDone <- e.do(http.MethodDelete, fmt.Sprintf("/api/notes/%d", b), "").Code }()
			if code, done := waitBriefly(deleteDone); done {
				finishedEarly = true
				deleteDone <- code
			}
		}
		return nil
	}
	report := e.mustInline(`{"dry_run":false}`)
	if finishedEarly {
		t.Fatal("note delete finished while the maintenance run held noteFilesMu")
	}
	if code := <-deleteDone; code != http.StatusOK {
		t.Fatalf("delete after the run: %d", code)
	}
	got := resultFor(t, report, b)
	if got.Status != "merged" || got.MovedTo == "" {
		t.Fatalf("note B must be merged before the delete: %+v", got)
	}
	if _, err := os.Stat(filepath.Join(e.dataDir, filepath.FromSlash(got.MovedTo))); err != nil {
		t.Fatal("quarantined file must survive the later delete")
	}
}

func TestInlineSeparatedNotesRestorePointFailureChangesNothing(t *testing.T) {
	e, _, _, _, _, _, _ := specFixture(t)
	before := e.fullSnapshot()
	e.srv.testHook = func(stage string, id int) error {
		if stage == "before_restore_point" {
			for _, dir := range quarantineDirs(t, e.dataDir) {
				e.write("backups/"+dir+"/restore_point.db.tmp/obstruction", []byte("x"))
			}
		}
		return nil
	}
	code, _, raw := e.inline(`{"dry_run":false}`)
	if code != http.StatusInternalServerError || !strings.Contains(raw, `"notes_changed":0`) {
		t.Fatalf("restore point failure must be a 500 with notes_changed 0: %d %s", code, raw)
	}
	for _, dir := range quarantineDirs(t, e.dataDir) {
		_ = os.RemoveAll(filepath.Join(e.dataDir, "backups", dir))
	}
	if after := e.fullSnapshot(); after != before {
		t.Fatal("nothing may change when the restore point fails")
	}
}

func TestInlineSeparatedNotesReportsAuditErrorWhenResultWriteFails(t *testing.T) {
	e, _, _, _, _, _, _ := specFixture(t)
	e.srv.testHook = func(stage string, id int) error {
		if stage == "before_result" {
			for _, dir := range quarantineDirs(t, e.dataDir) {
				if err := os.Mkdir(filepath.Join(e.dataDir, "backups", dir, "result.json"), 0755); err != nil {
					t.Fatal(err)
				}
			}
		}
		return nil
	}
	report := e.mustInline(`{"dry_run":false}`)
	if report.AuditError == "" || report.Counts.Merged != 2 {
		t.Fatalf("a failed result.json must be reported with the real counts: %+v", report)
	}
}

func TestInlineSeparatedNotesMoveFailureAndAbortAfterCommit(t *testing.T) {
	t.Run("move fails", func(t *testing.T) {
		e := newInlineEnv(t)
		a := e.splitNote("搬不動", longCJK("搬不動", "tailstuckopt20"))
		e.srv.testHook = func(stage string, id int) error {
			if stage == "before_move" && id == a {
				return fmt.Errorf("injected move failure")
			}
			return nil
		}
		report := e.mustInline(`{"dry_run":false}`)
		got := resultFor(t, report, a)
		if got.Status != "merged" || got.MoveError == "" || got.MovedTo != "" || report.Counts.MoveFailed != 1 {
			t.Fatalf("move failure keeps the merge and reports it: %+v", got)
		}
		if e.autoRows(a) != 0 {
			t.Fatal("DB stays merged")
		}
		if _, err := os.Stat(e.notePath(a)); err != nil {
			t.Fatal("file stays in docs/notes")
		}
		e.srv.testHook = nil
		dry := e.mustInline("")
		if !strings.Contains(fmt.Sprint(dry.OrphanFiles), fmt.Sprintf("note_%d.md", a)) {
			t.Fatalf("leftover file must be listed as an orphan: %+v", dry.OrphanFiles)
		}
		if again := e.mustInline(`{"dry_run":false}`); again.Counts.Actionable != 0 {
			t.Fatal("orphans are never processed")
		}
	})
	t.Run("abort after commit", func(t *testing.T) {
		e := newInlineEnv(t)
		a := e.splitNote("中止", longCJK("中止", "tailabortopt20"))
		b := e.splitNote("未處理", longCJK("未處理", "tailpendingopt20"))
		e.srv.testHook = func(stage string, id int) error {
			if stage == "after_commit" && id == a {
				return fmt.Errorf("injected abort")
			}
			return nil
		}
		report := e.mustInline(`{"dry_run":false}`)
		got := resultFor(t, report, a)
		if !report.Aborted || got.Status != "merged" || got.MovedTo != "" || !strings.Contains(got.MoveError, "aborted") {
			t.Fatalf("abort after commit is reported as committed and not moved: %+v", report)
		}
		if e.autoRows(a) != 0 || e.autoRows(b) != 1 {
			t.Fatal("A committed, B not processed")
		}
		result, err := os.ReadFile(filepath.Join(e.dataDir, filepath.FromSlash(*report.QuarantineDir), "result.json"))
		if err != nil || !strings.Contains(string(result), `"moved_to": null`) {
			t.Fatalf("result.json must record the unmoved commit: %v %s", err, result)
		}
	})
}

func TestInlineSeparatedNotesRechecksMediaInsideTransaction(t *testing.T) {
	for _, variant := range []string{"content", "cover"} {
		t.Run(variant, func(t *testing.T) {
			e := newInlineEnv(t)
			e.write("static/uploads/img_last.png", []byte("\x89PNG\r\n\x1a\nfixture"))
			x := e.splitNote("D2 候選", longCJK("D2 候選", "![x](/static/uploads/img_last.png)"))
			e.exec("UPDATE Notes SET content = ? WHERE id = ?", "改短的 D2 候選", x)
			protector := e.createNote("保護者", "保護者內容")
			if variant == "content" {
				e.exec("UPDATE Notes SET content = ? WHERE id = ?", "![p](/static/uploads/img_last.png)", protector)
			} else {
				e.exec("UPDATE Notes SET cover_image = ? WHERE id = ?", "/static/uploads/img_last.png", protector)
			}
			if dry := e.mustInline(""); dry.Counts.History != 1 {
				t.Fatalf("protected D2 candidate should be actionable at classification: %+v", dry.Counts)
			}
			e.srv.testHook = func(stage string, id int) error {
				if stage == "before_note" && id == x {
					rec := e.do(http.MethodPut, fmt.Sprintf("/api/notes/%d", protector), `{"title":"保護者","content":"不再引用圖片","cover_image":""}`)
					if rec.Code != http.StatusOK {
						t.Fatalf("put protector: %d %s", rec.Code, rec.Body.String())
					}
				}
				return nil
			}
			report := e.mustInline(`{"dry_run":false}`)
			if got := resultFor(t, report, x); got.Status != "skipped" || got.Reason != "media_unprotected" {
				t.Fatalf("D2 must stop when the last protecting reference is gone: %+v", got)
			}
			if e.autoRows(x) != 1 {
				t.Fatal("auto row keeps protecting the image")
			}
			if orphans := e.do(http.MethodGet, "/api/cleanup/orphan-images", ""); strings.Contains(orphans.Body.String(), "img_last.png") {
				t.Fatal("image must stay protected")
			}
		})
	}
}

func injectIdentityFailure(t *testing.T, suffix string) {
	t.Helper()
	original := statOpenFile
	statOpenFile = func(f *os.File) (os.FileInfo, error) {
		if strings.HasSuffix(strings.ToLower(filepath.ToSlash(f.Name())), strings.ToLower(suffix)) {
			return nil, fmt.Errorf("injected identity failure")
		}
		return original(f)
	}
	t.Cleanup(func() { statOpenFile = original })
}

func TestInlineSeparatedNotesUnknownIdentityBlocksCandidates(t *testing.T) {
	t.Run("another row's identity unknown", func(t *testing.T) {
		e := newInlineEnv(t)
		a := e.splitNote("候選", longCJK("候選", "tailunknownopt20"))
		other := e.createNote("其他", "其他")
		e.write("docs/attachments/locked.md", []byte("讀不到身分"))
		locked := e.insertRow(other, "docs/attachments/locked.md", 0)
		injectIdentityFailure(t, "docs/attachments/locked.md")
		report := e.mustInline(`{"dry_run":false}`)
		if skippedReason(report, autoRowID(t, e.srv.db, a)) != "identity_unverified" || e.autoRows(a) != 1 {
			t.Fatalf("unknown identity elsewhere must list the candidate: %+v", report.Skipped)
		}
		if report.Counts.UnverifiedRows != 1 || report.UnverifiedRows[0].AttachmentID != locked {
			t.Fatalf("unverified row must be reported: %+v", report.UnverifiedRows)
		}
	})
	t.Run("candidate identity unknown", func(t *testing.T) {
		e := newInlineEnv(t)
		a := e.splitNote("自己讀不到", longCJK("自己讀不到", "tailselfopt20"))
		injectIdentityFailure(t, fmt.Sprintf("docs/notes/note_%d.md", a))
		report := e.mustInline(`{"dry_run":false}`)
		if skippedReason(report, autoRowID(t, e.srv.db, a)) != "identity_unverified" || e.autoRows(a) != 1 {
			t.Fatalf("candidate identity failure must list it: %+v", report.Skipped)
		}
	})
	t.Run("missing file elsewhere does not block", func(t *testing.T) {
		e := newInlineEnv(t)
		a := e.splitNote("不受影響", longCJK("不受影響", "tailunblockedopt20"))
		ghost := e.createNote("懸空", "懸空")
		e.insertRow(ghost, "docs/attachments/missing.md", 0)
		e.insertRow(ghost, "docs/notes/also_missing.md", 1)
		report := e.mustInline(`{"dry_run":false}`)
		if e.autoRows(a) != 0 || report.Counts.UnverifiedRows != 0 {
			t.Fatalf("missing files cannot alias anything: %+v", report)
		}
	})
}

// blockingWriter stalls on the first body write so a test can check which locks are held
// while a response is being transferred.
type blockingWriter struct {
	header  http.Header
	status  int
	started chan struct{}
	release chan struct{}
	once    sync.Once
	body    bytes.Buffer
}

func newBlockingWriter() *blockingWriter {
	return &blockingWriter{header: http.Header{}, started: make(chan struct{}), release: make(chan struct{})}
}

func (w *blockingWriter) Header() http.Header { return w.header }

func (w *blockingWriter) WriteHeader(code int) {
	if w.status == 0 {
		w.status = code
	}
}

func (w *blockingWriter) Write(p []byte) (int, error) {
	if w.status == 0 {
		w.status = http.StatusOK
	}
	w.once.Do(func() {
		close(w.started)
		<-w.release
	})
	return w.body.Write(p)
}

func assertUnlockedWhileWriting(t *testing.T, e *inlineEnv, req *http.Request) *blockingWriter {
	t.Helper()
	req.RemoteAddr = "127.0.0.1:5555"
	w := newBlockingWriter()
	done := make(chan struct{})
	go func() {
		e.srv.httpServer.Handler.ServeHTTP(w, req)
		close(done)
	}()
	select {
	case <-w.started:
	case <-done:
		t.Fatal("handler finished without writing a body")
	case <-time.After(10 * time.Second):
		t.Fatal("handler never started writing")
	}
	if !e.srv.noteFilesMu.TryLock() {
		close(w.release)
		<-done
		t.Fatalf("%s %s holds noteFilesMu while writing its response", req.Method, req.URL.Path)
	}
	e.srv.noteFilesMu.Unlock()
	close(w.release)
	<-done
	return w
}

func TestInlineSeparatedNotesLockIsNotHeldAcrossNetworkIO(t *testing.T) {
	e, _, _, _, _, _, _ := specFixture(t)

	t.Run("import waits for its body outside the lock", func(t *testing.T) {
		pr, pw := io.Pipe()
		req := httptest.NewRequest(http.MethodPost, "/api/import/json", pr)
		req.RemoteAddr = "127.0.0.1:5555"
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()
		done := make(chan struct{})
		go func() {
			e.srv.httpServer.Handler.ServeHTTP(rec, req)
			close(done)
		}()
		if _, err := pw.Write([]byte(`{"mode":"duplicate","data":{"notes":[`)); err != nil {
			t.Fatal(err)
		}
		if !e.srv.noteFilesMu.TryLock() {
			pw.Close()
			<-done
			t.Fatal("import holds noteFilesMu while its request body is still arriving")
		}
		e.srv.noteFilesMu.Unlock()
		_, _ = pw.Write([]byte(`{"title":"匯入","content":"匯入內容"}]}}`))
		pw.Close()
		<-done
		if rec.Code != http.StatusOK {
			t.Fatalf("import: %d %s", rec.Code, rec.Body.String())
		}
	})
	t.Run("import result is written outside the lock", func(t *testing.T) {
		body := `{"mode":"duplicate","data":{"notes":[{"title":"` + strings.Repeat("長", 4000) + `","content":"匯入"}]}}`
		req := httptest.NewRequest(http.MethodPost, "/api/import/json", strings.NewReader(body))
		if w := assertUnlockedWhileWriting(t, e, req); w.status != http.StatusOK {
			t.Fatalf("import status %d %s", w.status, w.body.String())
		}
	})
	t.Run("full snapshot streams outside the lock", func(t *testing.T) {
		w := assertUnlockedWhileWriting(t, e, httptest.NewRequest(http.MethodGet, "/api/export/full-snapshot", nil))
		if w.status != http.StatusOK {
			t.Fatalf("snapshot status %d", w.status)
		}
	})
	t.Run("maintenance report is written outside the lock", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/system/inline-separated-notes", strings.NewReader(`{"dry_run":false}`))
		if w := assertUnlockedWhileWriting(t, e, req); w.status != http.StatusOK {
			t.Fatalf("maintenance status %d %s", w.status, w.body.String())
		}
	})
	t.Run("attachment upload with an unbounded title replies outside the lock", func(t *testing.T) {
		n := e.createNote("附件", "附件")
		req := newAttachmentUploadRequest(t, n, "doc.md", []byte("附件內容"), strings.Repeat("長標題", 3000))
		if w := assertUnlockedWhileWriting(t, e, req); w.status != http.StatusOK {
			t.Fatalf("upload status %d %s", w.status, w.body.String())
		}
	})
}

func TestRestoreSeparatedContentClaimsRowWithFirstStatement(t *testing.T) {
	e := newInlineEnv(t)
	full := longCJK("還原", "tailrestoreclaimopt20")
	a := e.splitNote("還原", full)
	other := e.createNote("其他", "其他")
	fired, early := false, false
	writeDone := make(chan int, 1)
	e.srv.testHook = func(stage string, id int) error {
		if stage == "restore_after_claim" && id == a {
			fired = true
			go func() {
				// A write-first statement from another connection: it must wait for restore's
				// write lock instead of committing inside restore's transaction window.
				if _, err := e.srv.db.Exec("UPDATE Notes SET title = 'concurrent' WHERE id = ?", other); err != nil {
					writeDone <- http.StatusInternalServerError
					return
				}
				writeDone <- http.StatusOK
			}()
			if code, done := waitBriefly(writeDone); done {
				early = true
				writeDone <- code
			}
		}
		return nil
	}
	rec := e.do(http.MethodPost, fmt.Sprintf("/api/notes/%d/restore", a), "{}")
	if !fired {
		t.Fatal("restore must reach restore_after_claim after claiming its row")
	}
	if rec.Code != http.StatusOK {
		t.Fatalf("restore with a concurrent writer: %d %s", rec.Code, rec.Body.String())
	}
	if early {
		t.Fatal("a concurrent write committed while restore held its claimed row")
	}
	if code := <-writeDone; code != http.StatusOK {
		t.Fatal("the concurrent write must succeed after restore commits")
	}
	if e.content(a) != full || e.autoRows(a) != 0 {
		t.Fatal("restore must complete")
	}
}

func TestRestoreKeepsFileWhenAliasIdentityIsUnknown(t *testing.T) {
	e := newInlineEnv(t)
	full := longCJK("別名", "tailaliasopt20")
	a := e.splitNote("別名", full)
	upper := strings.Replace(e.notePath(a), "note_", "NOTE_", 1)
	if _, err := os.Stat(upper); err != nil {
		t.Skip("needs a case-insensitive filesystem for the case-variant alias")
	}
	other := e.createNote("大小寫別名", "別名")
	e.insertRow(other, fmt.Sprintf("docs/notes/NOTE_%d.md", a), 1)
	// The helper opens the restored file first, then each case-variant alias. On Windows both
	// names resolve to the same path, so the failing open is picked by order.
	for name, failOn := range map[string]int{"target identity unknown": 1, "alias identity unknown": 2} {
		t.Run(name, func(t *testing.T) {
			e.exec("DELETE FROM Note_Attachments WHERE note_id = ?", a)
			e.exec("INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted) VALUES (?, ?, 'md', 'auto', 1, 1)", a, fmt.Sprintf("docs/notes/note_%d.md", a))
			if _, err := os.Stat(e.notePath(a)); err != nil {
				e.write(fmt.Sprintf("docs/notes/note_%d.md", a), []byte(full))
			}
			original := statOpenFile
			opens := 0
			statOpenFile = func(f *os.File) (os.FileInfo, error) {
				if strings.HasSuffix(strings.ToLower(f.Name()), fmt.Sprintf("note_%d.md", a)) {
					opens++
					if opens == failOn {
						return nil, fmt.Errorf("injected identity failure")
					}
				}
				return original(f)
			}
			defer func() { statOpenFile = original }()
			if rec := e.do(http.MethodPost, fmt.Sprintf("/api/notes/%d/restore", a), "{}"); rec.Code != http.StatusOK {
				t.Fatalf("restore: %d %s", rec.Code, rec.Body.String())
			}
			if opens < failOn {
				t.Fatalf("the injected open #%d never happened (opens=%d)", failOn, opens)
			}
			if _, err := os.Stat(e.notePath(a)); err != nil {
				t.Fatal("restore must keep a file whose alias identity cannot be verified")
			}
		})
	}
}

func TestInlineSeparatedNotesBlocksSeparateUntilRunEnds(t *testing.T) {
	e := newInlineEnv(t)
	b := e.splitNote("又被拆分", longCJK("又被拆分", "tailresplitopt20"))
	separateDone := make(chan int, 1)
	finishedEarly := false
	e.srv.testHook = func(stage string, id int) error {
		// After the merge commit and before the move: a separate here would rewrite the very
		// file the run is about to quarantine and leave B with a row pointing nowhere.
		if stage == "after_commit" && id == b {
			go func() { separateDone <- e.do(http.MethodPost, fmt.Sprintf("/api/notes/%d/separate", b), "{}").Code }()
			if code, done := waitBriefly(separateDone); done {
				finishedEarly = true
				separateDone <- code
			}
		}
		return nil
	}
	report := e.mustInline(`{"dry_run":false}`)
	if code := <-separateDone; code != http.StatusOK {
		t.Fatalf("separate after the run: %d", code)
	}
	if finishedEarly {
		t.Fatal("separate finished while the maintenance run held noteFilesMu")
	}
	if got := resultFor(t, report, b); got.Status != "merged" || got.MovedTo == "" {
		t.Fatalf("B must be merged and moved: %+v", got)
	}
	var filePath string
	if err := e.srv.db.QueryRow("SELECT file_path FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1", b).Scan(&filePath); err != nil {
		t.Fatalf("the later separate re-splits B: %v", err)
	}
	if _, err := os.Stat(filepath.Join(e.dataDir, filepath.FromSlash(filePath))); err != nil {
		t.Fatalf("B's new auto row must point at an existing file: %v", err)
	}
}

func TestInlineSeparatedNotesNeverOverwritesExistingQuarantineFile(t *testing.T) {
	e := newInlineEnv(t)
	a := e.splitNote("目的地已存在", longCJK("目的地已存在", "taildestopt20"))
	original, err := os.ReadFile(e.notePath(a))
	if err != nil {
		t.Fatal(err)
	}
	squatter := []byte("已經在隔離區的另一個檔案")
	var dest string
	e.srv.testHook = func(stage string, id int) error {
		if stage == "before_move" && id == a {
			dirs := quarantineDirs(t, e.dataDir)
			dest = filepath.Join(e.dataDir, "backups", dirs[len(dirs)-1], "docs", "notes", fmt.Sprintf("note_%d.md", a))
			if err := os.WriteFile(dest, squatter, 0644); err != nil {
				t.Fatal(err)
			}
		}
		return nil
	}
	report := e.mustInline(`{"dry_run":false}`)
	got := resultFor(t, report, a)
	if got.Status != "merged" || got.MoveError != "destination exists" || got.MovedTo != "" {
		t.Fatalf("an existing destination must be reported, not overwritten: %+v", got)
	}
	if data, err := os.ReadFile(dest); err != nil || !bytes.Equal(data, squatter) {
		t.Fatalf("the pre-existing destination must keep its bytes: %v", err)
	}
	if data, err := os.ReadFile(e.notePath(a)); err != nil || !bytes.Equal(data, original) {
		t.Fatalf("the source must stay in docs/notes with its original bytes: %v", err)
	}
	if e.autoRows(a) != 0 || e.content(a) != longCJK("目的地已存在", "taildestopt20") {
		t.Fatal("the note stays merged (the DB commit happened before the move)")
	}
	e.srv.testHook = nil
	dry := e.mustInline("")
	if !strings.Contains(fmt.Sprint(dry.OrphanFiles), fmt.Sprintf("docs/notes/note_%d.md", a)) {
		t.Fatalf("the unmoved source must be listed as an orphan: %+v", dry.OrphanFiles)
	}
}

func TestInlineSeparatedNotesSkipsNoteSavedAfterClassification(t *testing.T) {
	for _, kind := range []string{"merge", "history"} {
		t.Run(kind, func(t *testing.T) {
			e := newInlineEnv(t)
			full := longCJK("存檔競爭", "tailsaveraceopt20")
			n := e.splitNote("存檔競爭", full)
			if kind == "history" {
				e.exec("UPDATE Notes SET content = ? WHERE id = ?", "分類時的短版內容", n)
			}
			fileBefore, _ := os.ReadFile(e.notePath(n))
			saved := "使用者在維護執行中剛存的新內容 savedduringrunopt20"
			historyBefore := historyCount(t, e.srv.db, n)
			e.srv.testHook = func(stage string, id int) error {
				if stage == "before_note" && id == n {
					rec := e.do(http.MethodPut, fmt.Sprintf("/api/notes/%d", n), `{"title":"存檔競爭","content":"`+saved+`"}`)
					if rec.Code != http.StatusOK {
						t.Fatalf("put: %d %s", rec.Code, rec.Body.String())
					}
				}
				return nil
			}
			report := e.mustInline(`{"dry_run":false}`)
			if got := resultFor(t, report, n); got.Status != "skipped" || got.Reason != "changed_during_run" {
				t.Fatalf("a note saved after classification must be skipped: %+v", got)
			}
			if e.content(n) != saved {
				t.Fatal("the user's newly saved content must be kept")
			}
			if e.autoRows(n) != 1 {
				t.Fatal("the auto row must stay")
			}
			if data, err := os.ReadFile(e.notePath(n)); err != nil || !bytes.Equal(data, fileBefore) {
				t.Fatalf("the file must stay untouched: %v", err)
			}
			var maintenanceRows int
			if err := e.srv.db.QueryRow("SELECT COUNT(*) FROM Note_History WHERE note_id = ? AND diff_summary = ?", n, inlineHistorySummary).Scan(&maintenanceRows); err != nil {
				t.Fatal(err)
			}
			if maintenanceRows != 0 || historyCount(t, e.srv.db, n) != historyBefore+1 {
				t.Fatalf("only the user's PUT may add history (maintenance rows=%d)", maintenanceRows)
			}
		})
	}
}
