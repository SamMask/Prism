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

// PRISM-OPT-74: an attachment write never replaces a file that is already on disk.

func newNoOverwriteAttachmentServer(t *testing.T) (*server, *sql.DB, string) {
	t.Helper()
	original := uploadNow
	uploadNow = func() time.Time { return time.Date(2026, 10, 7, 12, 0, 0, 0, time.Local) }
	t.Cleanup(func() { uploadNow = original })

	db, err := openDB(createSpikeDB(t), true)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	dataDir := t.TempDir()
	srv := &server{db: db, runtime: runtimeConfig{
		dataDir:                  dataDir,
		attachmentsDir:           filepath.Join(dataDir, "docs", "attachments"),
		notesDir:                 filepath.Join(dataDir, "docs", "notes"),
		enableNotesWrite:         true,
		enableAttachmentWrite:    true,
		enableAttachmentTextRead: true,
	}}
	return srv, db, srv.runtime.attachmentsDir
}

func uploadNoOverwriteAttachment(t *testing.T, srv *server, noteID int, filename, content string) (int, map[string]any) {
	t.Helper()
	rec := httptest.NewRecorder()
	srv.handleNoteDetail(rec, newAttachmentUploadRequest(t, noteID, filename, []byte(content), ""))
	var payload struct {
		Data map[string]any `json:"data"`
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &payload)
	return rec.Code, payload.Data
}

func readAttachmentContentViaAPI(t *testing.T, srv *server, attachmentID int) string {
	t.Helper()
	rec := httptest.NewRecorder()
	srv.handleAttachmentDetail(rec, httptest.NewRequest(http.MethodGet, fmt.Sprintf("/api/attachments/%d", attachmentID), nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/attachments/%d: %d body=%s", attachmentID, rec.Code, rec.Body.String())
	}
	var payload struct {
		Data struct {
			Content string `json:"content"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	return payload.Data.Content
}

func assertFileContent(t *testing.T, path, want string) {
	t.Helper()
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	if string(got) != want {
		t.Fatalf("%s content %q, want %q", filepath.Base(path), got, want)
	}
}

func TestAttachmentUploadSameSecondSameNameKeepsBothFiles(t *testing.T) {
	srv, db, attachmentsDir := newNoOverwriteAttachmentServer(t)
	noteID := insertSearchNote(t, db, "同名附件", "內容", "", 1)

	// a/b.md and a\b.md both sanitize to the same name; so does a plain repeat upload.
	uploads := []struct{ name, content string }{
		{"會議紀錄.md", "第一版"},
		{"會議紀錄.md", "第二版"},
		{"a/會議紀錄.md", "第三版"},
	}
	ids := map[int]string{}
	paths := map[string]bool{}
	for _, upload := range uploads {
		code, data := uploadNoOverwriteAttachment(t, srv, noteID, upload.name, upload.content)
		if code != http.StatusOK {
			t.Fatalf("upload %q: status %d data=%v", upload.name, code, data)
		}
		filePath, _ := data["file_path"].(string)
		if paths[filePath] {
			t.Fatalf("upload %q reused file_path %q", upload.name, filePath)
		}
		paths[filePath] = true
		ids[int(data["id"].(float64))] = upload.content
	}

	entries, err := os.ReadDir(attachmentsDir)
	if err != nil || len(entries) != len(uploads) {
		t.Fatalf("attachments dir %v (err %v), want %d files", entries, err, len(uploads))
	}
	for id, want := range ids {
		if got := readAttachmentContentViaAPI(t, srv, id); got != want {
			t.Errorf("attachment %d reads %q, want %q", id, got, want)
		}
		var filePath string
		if err := db.QueryRow("SELECT file_path FROM Note_Attachments WHERE id = ?", id).Scan(&filePath); err != nil {
			t.Fatal(err)
		}
		assertFileContent(t, filepath.Join(srv.runtime.dataDir, filepath.FromSlash(filePath)), want)
	}
}

func TestAttachmentUploadLeavesUnrelatedSameNameFileAlone(t *testing.T) {
	srv, db, attachmentsDir := newNoOverwriteAttachmentServer(t)
	noteID := insertSearchNote(t, db, "無關檔案", "內容", "", 1)
	taken := filepath.Join(attachmentsDir, "會議紀錄_20261007_120000.md")
	if err := os.MkdirAll(attachmentsDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(taken, []byte("無關內容"), 0644); err != nil {
		t.Fatal(err)
	}

	code, data := uploadNoOverwriteAttachment(t, srv, noteID, "會議紀錄.md", "新上傳")
	if code != http.StatusOK {
		t.Fatalf("upload status %d data=%v", code, data)
	}
	assertFileContent(t, taken, "無關內容")
	filePath, _ := data["file_path"].(string)
	if filePath == "docs/attachments/會議紀錄_20261007_120000.md" {
		t.Fatalf("upload stored the taken name %q", filePath)
	}
	if got := readAttachmentContentViaAPI(t, srv, int(data["id"].(float64))); got != "新上傳" {
		t.Fatalf("new attachment reads %q", got)
	}
}

func TestAttachmentUploadInsertFailureRemovesOnlyItsOwnFile(t *testing.T) {
	srv, db, attachmentsDir := newNoOverwriteAttachmentServer(t)
	noteID := insertSearchNote(t, db, "寫入失敗", "內容", "", 1)
	taken := filepath.Join(attachmentsDir, "會議紀錄_20261007_120000.md")
	if err := os.MkdirAll(attachmentsDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(taken, []byte("既有內容"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec(`CREATE TRIGGER block_attachment_insert BEFORE INSERT ON Note_Attachments
		BEGIN SELECT RAISE(ABORT, 'blocked by test'); END`); err != nil {
		t.Fatal(err)
	}

	code, data := uploadNoOverwriteAttachment(t, srv, noteID, "會議紀錄.md", "不該留下")
	if code != http.StatusInternalServerError {
		t.Fatalf("upload with failing insert: status %d data=%v", code, data)
	}
	assertFileContent(t, taken, "既有內容")
	entries, err := os.ReadDir(attachmentsDir)
	if err != nil || len(entries) != 1 {
		t.Fatalf("attachments dir %v (err %v), want only the existing file", entries, err)
	}
}

func TestDuplicateNoteAttachmentCopyLeavesExistingSameNameFileAlone(t *testing.T) {
	srv, db, attachmentsDir := newNoOverwriteAttachmentServer(t)
	parentID := insertSearchNote(t, db, "複製來源", "內容", "", 1)
	if err := os.MkdirAll(attachmentsDir, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(attachmentsDir, "會議紀錄.md"), []byte("來源內容"), 0644); err != nil {
		t.Fatal(err)
	}
	result, err := db.Exec(`INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
		VALUES (?, 'docs/attachments/會議紀錄.md', 'md', '會議紀錄', 12, 0)`, parentID)
	if err != nil {
		t.Fatal(err)
	}
	sourceAttachmentID, _ := result.LastInsertId()
	var nextNoteID int64
	if err := db.QueryRow("SELECT seq + 1 FROM sqlite_sequence WHERE name = 'Notes'").Scan(&nextNoteID); err != nil {
		t.Fatal(err)
	}
	// A file another row may own (e.g. restored by a JSON import from another data dir) sits at
	// the name the copy would pick.
	taken := filepath.Join(attachmentsDir, fmt.Sprintf("會議紀錄_copy_%d_%d.md", nextNoteID, sourceAttachmentID))
	if err := os.WriteFile(taken, []byte("別人的檔案"), 0644); err != nil {
		t.Fatal(err)
	}

	rec := httptest.NewRecorder()
	srv.handleNoteDetail(rec, httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/notes/%d/duplicate", parentID), strings.NewReader(`{}`)))
	if rec.Code != http.StatusCreated {
		t.Fatalf("duplicate: %d body=%s", rec.Code, rec.Body.String())
	}
	copyID := noteIDFromResponse(t, rec.Body.Bytes())
	if int64(copyID) != nextNoteID {
		t.Fatalf("copy got note id %d, test expected %d", copyID, nextNoteID)
	}
	assertFileContent(t, taken, "別人的檔案")
	var copiedAttachmentID int
	if err := db.QueryRow("SELECT id FROM Note_Attachments WHERE note_id = ?", copyID).Scan(&copiedAttachmentID); err != nil {
		t.Fatal(err)
	}
	if got := readAttachmentContentViaAPI(t, srv, copiedAttachmentID); got != "來源內容" {
		t.Fatalf("copied attachment reads %q", got)
	}
}
