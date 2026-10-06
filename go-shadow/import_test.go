package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// PRISM-OPT-58: a JSON export that contains a separated note imports. The docs/notes row is
// skipped and counted, the note keeps its exported preview, and other paths keep the safety check.

type importJSONResult struct {
	Data struct {
		Imported           int `json:"imported"`
		Skipped            int `json:"skipped"`
		SkippedAttachments int `json:"skipped_attachments"`
	} `json:"data"`
	Message string `json:"message"`
}

// exportWithSeparatedNote builds a source runtime with one separated note, one note with a normal
// attachment and one plain note, and returns its GET /api/export/json payload.
func exportWithSeparatedNote(t *testing.T) (*inlineEnv, int, map[string]any) {
	t.Helper()
	src := newInlineEnv(t)
	split := src.splitNote("拆分長文筆記", longCJK("龍眼乾全文尾", "fulltailopt58"))
	normal := src.createNote("一般附件筆記", "這是有一般附件的筆記內容")
	src.createNote("純文字筆記", "沒有附件的中文筆記")
	req := newAttachmentUploadRequest(t, normal, "說明.md", []byte("# 附件\n一般附件的中文內容"), "一般附件")
	req.RemoteAddr = "127.0.0.1:5555"
	rec := httptest.NewRecorder()
	src.srv.httpServer.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("upload: %d %s", rec.Code, rec.Body.String())
	}
	exp := src.do(http.MethodGet, "/api/export/json", "")
	if exp.Code != http.StatusOK {
		t.Fatalf("export: %d %s", exp.Code, exp.Body.String())
	}
	if strings.Contains(exp.Body.String(), "fulltailopt58") {
		t.Fatal("export unexpectedly carries the separated note's full text; revisit the skip rule")
	}
	var payload map[string]any
	if err := json.Unmarshal(exp.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	return src, split, payload
}

func postImportJSON(t *testing.T, e *inlineEnv, data map[string]any, mode string) (int, importJSONResult) {
	t.Helper()
	body, _ := json.Marshal(map[string]any{"data": data, "mode": mode})
	rec := e.do(http.MethodPost, "/api/import/json", string(body))
	var out importJSONResult
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatalf("import response: %d %s", rec.Code, rec.Body.String())
	}
	return rec.Code, out
}

func countRows(t *testing.T, e *inlineEnv, query string, args ...any) int {
	t.Helper()
	var n int
	if err := e.srv.db.QueryRow(query, args...).Scan(&n); err != nil {
		t.Fatal(err)
	}
	return n
}

func TestImportJSONSkipsSeparatedNoteAttachment(t *testing.T) {
	_, _, exported := exportWithSeparatedNote(t)
	preview := ""
	for _, n := range exported["notes"].([]any) {
		if m := n.(map[string]any); m["title"] == "拆分長文筆記" {
			preview = m["content"].(string)
		}
	}
	if !strings.HasSuffix(preview, separatedPreviewBanner) {
		t.Fatalf("exported split note is not the separated preview: %q", preview)
	}
	for _, mode := range []string{"skip", "duplicate"} {
		t.Run(mode, func(t *testing.T) {
			dst := newInlineEnv(t)
			code, out := postImportJSON(t, dst, exported, mode)
			if code != http.StatusOK {
				t.Fatalf("import: %d %+v", code, out)
			}
			if out.Data.SkippedAttachments != 1 {
				t.Fatalf("skipped_attachments = %d, want 1", out.Data.SkippedAttachments)
			}
			for _, title := range []string{"拆分長文筆記", "一般附件筆記", "純文字筆記"} {
				if n := countRows(t, dst, "SELECT COUNT(*) FROM Notes WHERE title = ?", title); n != 1 {
					t.Fatalf("note %q imported %d times, want 1", title, n)
				}
			}
			var content string
			if err := dst.srv.db.QueryRow("SELECT content FROM Notes WHERE title = '拆分長文筆記'").Scan(&content); err != nil {
				t.Fatal(err)
			}
			if content != strings.TrimSpace(preview) {
				t.Fatalf("split note content is not the exported preview: %q", content)
			}
			if n := countRows(t, dst, "SELECT COUNT(*) FROM Note_Attachments WHERE file_path LIKE 'docs/notes/%'"); n != 0 {
				t.Fatalf("docs/notes rows restored: %d", n)
			}
			if n := countRows(t, dst, `SELECT COUNT(*) FROM Note_Attachments a JOIN Notes n ON n.id = a.note_id
				WHERE n.title = '一般附件筆記' AND a.file_path LIKE 'docs/attachments/%' AND a.is_auto_extracted = 0`); n != 1 {
				t.Fatalf("normal attachment rows = %d, want 1", n)
			}
			if entries, _ := os.ReadDir(filepath.Join(dst.dataDir, "docs", "notes")); len(entries) != 0 {
				t.Fatalf("import wrote docs/notes files: %v", entries)
			}
		})
	}
}

func TestImportJSONIntoSourceKeepsSingleAutoRow(t *testing.T) {
	src, split, exported := exportWithSeparatedNote(t)
	code, out := postImportJSON(t, src, exported, "skip")
	if code != http.StatusOK || out.Data.SkippedAttachments != 1 {
		t.Fatalf("re-import: %d %+v", code, out)
	}
	if n := src.autoRows(split); n != 1 {
		t.Fatalf("split note auto rows = %d, want 1", n)
	}
}

func TestImportJSONStillRejectsUnsafeAttachmentPaths(t *testing.T) {
	paths := []string{"../evil.md", "docs/attachments/../../evil.md", "docs/notes/../../evil.md",
		"/etc/passwd", "C:/Windows/evil.md", "docs/other/evil.md", "/docs/notes/note_1.md"}
	for _, p := range paths {
		for _, auto := range []bool{true, false} {
			dst := newInlineEnv(t)
			before := countRows(t, dst, "SELECT COUNT(*) FROM Notes")
			data := map[string]any{
				"notes":       []any{map[string]any{"id": 1, "title": "路徑測試", "content": "路徑內容"}},
				"attachments": []any{map[string]any{"note_id": 1, "file_path": p, "is_auto_extracted": auto}},
			}
			code, out := postImportJSON(t, dst, data, "skip")
			if code != http.StatusBadRequest || !strings.Contains(out.Message, "unsafe attachment path") {
				t.Fatalf("path %q auto=%v: %d %+v", p, auto, code, out)
			}
			if after := countRows(t, dst, "SELECT COUNT(*) FROM Notes"); after != before {
				t.Fatalf("path %q auto=%v: notes %d -> %d, import not rolled back", p, auto, before, after)
			}
		}
	}
}
