package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path"
	"path/filepath"
	"strings"
	"testing"
)

// PRISM-OPT-66: deleting an attachment row, or a note, keeps the file while another note's
// attachment row still points at it. A JSON export carries metadata-only rows, so importing it
// into a data dir that already holds a file of the same name makes two rows share one file.

const sharedAttachmentText = "# 共用指南\n原始筆記的中文附件內容"

// uploadSharedAttachment creates a note with one uploaded attachment and returns the note id,
// the attachment id and its stored relative path.
func uploadSharedAttachment(t *testing.T, e *inlineEnv) (int, int, string) {
	t.Helper()
	noteID := e.createNote("原始筆記", "擁有實體附件檔的中文筆記")
	req := newAttachmentUploadRequest(t, noteID, "Shared-Guide.md", []byte(sharedAttachmentText), "共用指南")
	req.RemoteAddr = "127.0.0.1:5555"
	rec := httptest.NewRecorder()
	e.srv.httpServer.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("upload: %d %s", rec.Code, rec.Body.String())
	}
	var out struct {
		Data struct {
			ID       int    `json:"id"`
			FilePath string `json:"file_path"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	return noteID, out.Data.ID, out.Data.FilePath
}

// importMetadataOnlyRow imports a note whose attachment row has no content, as GET
// /api/export/json produces, and returns the new note id and attachment id.
func importMetadataOnlyRow(t *testing.T, e *inlineEnv, filePath string) (int, int) {
	t.Helper()
	data := map[string]any{
		"notes":       []any{map[string]any{"id": 1, "title": "匯入筆記", "content": "從另一個資料庫匯入的中文內容"}},
		"attachments": []any{map[string]any{"note_id": 1, "file_path": filePath, "title": "匯入附件"}},
	}
	if code, out := postImportJSON(t, e, data, "skip"); code != http.StatusOK || out.Data.Imported != 1 {
		t.Fatalf("import: %d %+v", code, out)
	}
	var noteID, attachmentID int
	if err := e.srv.db.QueryRow(`SELECT n.id, a.id FROM Note_Attachments a JOIN Notes n ON n.id = a.note_id
		WHERE n.title = '匯入筆記'`).Scan(&noteID, &attachmentID); err != nil {
		t.Fatal(err)
	}
	return noteID, attachmentID
}

// caseVariantPath returns rel with an upper-cased file name, skipping the test when the data
// dir's filesystem is case-sensitive (the variant then names a different file).
func caseVariantPath(t *testing.T, e *inlineEnv, rel string) string {
	t.Helper()
	variant := path.Join(path.Dir(rel), strings.ToUpper(path.Base(rel)))
	if variant == rel {
		t.Fatalf("no case variant for %q", rel)
	}
	if _, err := os.Stat(filepath.Join(e.dataDir, filepath.FromSlash(variant))); err != nil {
		t.Skipf("case-sensitive filesystem: %v", err)
	}
	return variant
}

func deleteAttachmentOK(t *testing.T, e *inlineEnv, attachmentID int) {
	t.Helper()
	rec := e.do(http.MethodDelete, fmt.Sprintf("/api/attachments/%d", attachmentID), "")
	if rec.Code != http.StatusOK {
		t.Fatalf("delete attachment %d: %d %s", attachmentID, rec.Code, rec.Body.String())
	}
}

func assertAttachmentReadable(t *testing.T, e *inlineEnv, attachmentID int) {
	t.Helper()
	rec := e.do(http.MethodGet, fmt.Sprintf("/api/attachments/%d", attachmentID), "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "原始筆記的中文附件內容") {
		t.Fatalf("attachment %d not readable: %d %s", attachmentID, rec.Code, rec.Body.String())
	}
}

func assertFileGone(t *testing.T, abs string) {
	t.Helper()
	if _, err := os.Stat(abs); !os.IsNotExist(err) {
		t.Fatalf("file %s still present after its last row was deleted (stat err %v)", abs, err)
	}
}

func TestDeleteAttachmentKeepsFileSharedWithImportedRow(t *testing.T) {
	e := newInlineEnv(t)
	_, originalID, rel := uploadSharedAttachment(t, e)
	abs := filepath.Join(e.dataDir, filepath.FromSlash(rel))
	_, importedID := importMetadataOnlyRow(t, e, rel)

	deleteAttachmentOK(t, e, importedID)
	assertFileBytes(t, abs, []byte(sharedAttachmentText))
	assertAttachmentReadable(t, e, originalID)

	deleteAttachmentOK(t, e, originalID)
	assertFileGone(t, abs)
}

func TestDeleteAttachmentKeepsFileSharedByCaseVariantRow(t *testing.T) {
	for _, deleteImportedFirst := range []bool{true, false} {
		t.Run(fmt.Sprintf("imported_first=%v", deleteImportedFirst), func(t *testing.T) {
			e := newInlineEnv(t)
			_, originalID, rel := uploadSharedAttachment(t, e)
			abs := filepath.Join(e.dataDir, filepath.FromSlash(rel))
			_, importedID := importMetadataOnlyRow(t, e, caseVariantPath(t, e, rel))

			first, second := importedID, originalID
			if !deleteImportedFirst {
				first, second = originalID, importedID
			}
			deleteAttachmentOK(t, e, first)
			assertFileBytes(t, abs, []byte(sharedAttachmentText))
			assertAttachmentReadable(t, e, second)

			deleteAttachmentOK(t, e, second)
			assertFileGone(t, abs)
		})
	}
}

func TestDeleteNoteKeepsAttachmentFileSharedByCaseVariantRow(t *testing.T) {
	deletes := map[string]func(e *inlineEnv, noteID int) *httptest.ResponseRecorder{
		"single": func(e *inlineEnv, noteID int) *httptest.ResponseRecorder {
			return e.do(http.MethodDelete, fmt.Sprintf("/api/notes/%d", noteID), "")
		},
		"batch": func(e *inlineEnv, noteID int) *httptest.ResponseRecorder {
			return e.do(http.MethodPost, "/api/notes/batch/delete", fmt.Sprintf(`{"note_ids":[%d]}`, noteID))
		},
	}
	for name, deleteNote := range deletes {
		t.Run(name, func(t *testing.T) {
			e := newInlineEnv(t)
			originalNote, originalID, rel := uploadSharedAttachment(t, e)
			abs := filepath.Join(e.dataDir, filepath.FromSlash(rel))
			importedNote, _ := importMetadataOnlyRow(t, e, caseVariantPath(t, e, rel))

			if rec := deleteNote(e, importedNote); rec.Code != http.StatusOK {
				t.Fatalf("delete imported note: %d %s", rec.Code, rec.Body.String())
			}
			assertFileBytes(t, abs, []byte(sharedAttachmentText))
			assertAttachmentReadable(t, e, originalID)

			if rec := deleteNote(e, originalNote); rec.Code != http.StatusOK {
				t.Fatalf("delete original note: %d %s", rec.Code, rec.Body.String())
			}
			assertFileGone(t, abs)
		})
	}
}
