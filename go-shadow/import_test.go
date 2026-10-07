package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
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

// PRISM-OPT-64: a JSON import never deletes or silently replaces a file that already exists in the
// target. Attachments land under a new name, uploads that already exist are skipped and counted,
// a skip-mode re-import adds no attachment rows, and rows store the normalized path.

const existingAttachmentRel = "docs/attachments/共用說明.md"

var existingAttachmentBytes = []byte("# 既有附件\n目標端原本的中文內容")

type importJSONFilesResult struct {
	Data struct {
		SkippedUploads int `json:"skipped_uploads"`
	} `json:"data"`
}

func b64(s string) string { return base64.StdEncoding.EncodeToString([]byte(s)) }

// targetWithExistingFiles returns a runtime whose note owns existingAttachmentRel and whose uploads
// directory holds 封面圖.png.
func targetWithExistingFiles(t *testing.T) (*inlineEnv, string) {
	t.Helper()
	dst := newInlineEnv(t)
	owner := dst.createNote("既有附件筆記", "目標端的中文筆記")
	dst.write(existingAttachmentRel, existingAttachmentBytes)
	dst.insertRow(owner, existingAttachmentRel, 0)
	uploadPath := filepath.Join(dst.srv.runtime.uploadsDir, "封面圖.png")
	if err := os.MkdirAll(filepath.Dir(uploadPath), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(uploadPath, []byte("既有圖片位元組"), 0644); err != nil {
		t.Fatal(err)
	}
	return dst, uploadPath
}

func assertFileBytes(t *testing.T, absPath string, want []byte) {
	t.Helper()
	got, err := os.ReadFile(absPath)
	if err != nil {
		t.Fatalf("existing file gone: %v", err)
	}
	if string(got) != string(want) {
		t.Fatalf("existing file changed: %q", got)
	}
}

func dirNames(t *testing.T, dir string) []string {
	t.Helper()
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	names := []string{}
	for _, entry := range entries {
		names = append(names, entry.Name())
	}
	return names
}

func TestImportJSONFailureKeepsExistingFiles(t *testing.T) {
	cases := map[string]map[string]any{
		// the attachment write succeeds, then the uploads step fails
		"attachment": {
			"attachments": []any{map[string]any{"note_id": 1, "file_path": existingAttachmentRel, "content_b64": b64("匯入的新內容")}},
			"uploads":     []any{map[string]any{"filename": "../evil.png", "content_b64": b64("x")}},
		},
		// the first upload write succeeds, then the next upload fails
		"upload": {
			"uploads": []any{
				map[string]any{"filename": "封面圖.png", "content_b64": b64("匯入的圖片")},
				map[string]any{"filename": "../evil.png", "content_b64": b64("x")},
			},
		},
	}
	for name, fields := range cases {
		t.Run(name, func(t *testing.T) {
			dst, uploadPath := targetWithExistingFiles(t)
			data := map[string]any{"notes": []any{map[string]any{"id": 1, "title": "匯入筆記", "content": "匯入的中文內容"}}}
			for key, value := range fields {
				data[key] = value
			}
			code, out := postImportJSON(t, dst, data, "skip")
			if code != http.StatusBadRequest || !strings.Contains(out.Message, "unsafe upload filename") {
				t.Fatalf("import: %d %+v", code, out)
			}
			assertFileBytes(t, filepath.Join(dst.dataDir, filepath.FromSlash(existingAttachmentRel)), existingAttachmentBytes)
			assertFileBytes(t, uploadPath, []byte("既有圖片位元組"))
			if names := dirNames(t, filepath.Join(dst.dataDir, "docs", "attachments")); len(names) != 1 {
				t.Fatalf("attachments dir after failed import: %v", names)
			}
			if names := dirNames(t, dst.srv.runtime.uploadsDir); len(names) != 1 {
				t.Fatalf("uploads dir after failed import: %v", names)
			}
		})
	}
}

func TestImportJSONDoesNotOverwriteExistingFiles(t *testing.T) {
	dst, uploadPath := targetWithExistingFiles(t)
	data := map[string]any{
		"notes": []any{map[string]any{"id": 1, "title": "匯入筆記", "content": "匯入的中文內容"}},
		"attachments": []any{map[string]any{"note_id": 1, "file_path": existingAttachmentRel,
			"content_b64": b64("# 匯入附件\n匯入端的中文內容"), "title": "匯入附件"}},
		"uploads": []any{
			map[string]any{"filename": "封面圖.png", "content_b64": b64("匯入的圖片")},
			map[string]any{"filename": "新圖片.png", "content_b64": b64("新的圖片位元組")},
		},
	}
	body, _ := json.Marshal(map[string]any{"data": data, "mode": "skip"})
	rec := dst.do(http.MethodPost, "/api/import/json", string(body))
	if rec.Code != http.StatusOK {
		t.Fatalf("import: %d %s", rec.Code, rec.Body.String())
	}
	var out importJSONFilesResult
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	assertFileBytes(t, filepath.Join(dst.dataDir, filepath.FromSlash(existingAttachmentRel)), existingAttachmentBytes)
	assertFileBytes(t, uploadPath, []byte("既有圖片位元組"))
	if out.Data.SkippedUploads != 1 {
		t.Fatalf("skipped_uploads = %d, want 1: %s", out.Data.SkippedUploads, rec.Body.String())
	}
	assertFileBytes(t, filepath.Join(dst.srv.runtime.uploadsDir, "新圖片.png"), []byte("新的圖片位元組"))

	var attachmentID int
	var storedPath string
	if err := dst.srv.db.QueryRow(`SELECT a.id, a.file_path FROM Note_Attachments a JOIN Notes n ON n.id = a.note_id
		WHERE n.title = '匯入筆記'`).Scan(&attachmentID, &storedPath); err != nil {
		t.Fatal(err)
	}
	if storedPath == existingAttachmentRel || !strings.HasPrefix(storedPath, "docs/attachments/") {
		t.Fatalf("imported attachment stored at %q", storedPath)
	}
	read := dst.do(http.MethodGet, fmt.Sprintf("/api/attachments/%d", attachmentID), "")
	if read.Code != http.StatusOK || !strings.Contains(read.Body.String(), "匯入端的中文內容") {
		t.Fatalf("imported attachment not readable: %d %s", read.Code, read.Body.String())
	}
}

func TestImportJSONSkipReimportKeepsAttachmentRows(t *testing.T) {
	src, _, exported := exportWithSeparatedNote(t)
	normalRel := ""
	for _, raw := range exported["attachments"].([]any) {
		row := raw.(map[string]any)
		if p := row["file_path"].(string); strings.HasPrefix(p, "docs/attachments/") {
			normalRel = p
			row["content_b64"] = b64("匯入端不同的中文內容")
		}
	}
	if normalRel == "" {
		t.Fatal("export has no docs/attachments row")
	}
	normalAbs := filepath.Join(src.dataDir, filepath.FromSlash(normalRel))
	original, err := os.ReadFile(normalAbs)
	if err != nil {
		t.Fatal(err)
	}
	before := countRows(t, src, "SELECT COUNT(*) FROM Note_Attachments")
	filesBefore := dirNames(t, filepath.Join(src.dataDir, "docs", "attachments"))
	code, out := postImportJSON(t, src, exported, "skip")
	if code != http.StatusOK || out.Data.Imported != 0 {
		t.Fatalf("re-import: %d %+v", code, out)
	}
	if after := countRows(t, src, "SELECT COUNT(*) FROM Note_Attachments"); after != before {
		t.Fatalf("attachment rows %d -> %d after skip re-import", before, after)
	}
	assertFileBytes(t, normalAbs, original)
	if filesAfter := dirNames(t, filepath.Join(src.dataDir, "docs", "attachments")); len(filesAfter) != len(filesBefore) {
		t.Fatalf("attachment files %v -> %v", filesBefore, filesAfter)
	}
}

func TestImportJSONStoresNormalizedAttachmentPath(t *testing.T) {
	dst := newInlineEnv(t)
	data := map[string]any{
		"notes": []any{map[string]any{"id": 1, "title": "正規化筆記", "content": "路徑正規化的中文內容"}},
		"attachments": []any{map[string]any{"note_id": 1, "file_path": "docs/attachments/./子目錄/../正規化.md",
			"content_b64": b64("正規化附件內容")}},
	}
	code, out := postImportJSON(t, dst, data, "skip")
	if code != http.StatusOK {
		t.Fatalf("import: %d %+v", code, out)
	}
	var stored string
	if err := dst.srv.db.QueryRow("SELECT file_path FROM Note_Attachments").Scan(&stored); err != nil {
		t.Fatal(err)
	}
	if stored != "docs/attachments/正規化.md" {
		t.Fatalf("stored path %q, want docs/attachments/正規化.md", stored)
	}
	assertFileBytes(t, filepath.Join(dst.dataDir, "docs", "attachments", "正規化.md"), []byte("正規化附件內容"))
}

func TestImportJSONStillRejectsUnsafeUploadFilenames(t *testing.T) {
	for _, name := range []string{"../evil.png", "子目錄/../../evil.png", "..\\evil.png", "/../evil.png"} {
		dst := newInlineEnv(t)
		before := countRows(t, dst, "SELECT COUNT(*) FROM Notes")
		data := map[string]any{
			"notes":   []any{map[string]any{"id": 1, "title": "上傳路徑測試", "content": "上傳路徑內容"}},
			"uploads": []any{map[string]any{"filename": name, "content_b64": b64("惡意內容")}},
		}
		code, out := postImportJSON(t, dst, data, "skip")
		if code != http.StatusBadRequest || !strings.Contains(out.Message, "unsafe upload filename") {
			t.Fatalf("filename %q: %d %+v", name, code, out)
		}
		if after := countRows(t, dst, "SELECT COUNT(*) FROM Notes"); after != before {
			t.Fatalf("filename %q: notes %d -> %d, import not rolled back", name, before, after)
		}
		if _, err := os.Stat(filepath.Join(filepath.Dir(dst.srv.runtime.uploadsDir), "evil.png")); err == nil {
			t.Fatalf("filename %q escaped the uploads dir", name)
		}
	}
}
