package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
	"unicode/utf8"
)

var attachmentTimestampSuffix = regexp.MustCompile(`_\d{8}_\d{6}(\.[A-Za-z]+)$`)

func TestSanitizeAttachmentFilenameKeepsUnicodeAndStaysSafe(t *testing.T) {
	longCJK := strings.Repeat("漢", 300)
	cases := []struct{ in, want string }{
		// ASCII results are the same as before the Unicode change.
		{"report v2.md", "report v2.md"},
		{"my-file_(1).md", "my-file_1.md"},
		{"notes.final.txt", "notes.final.txt"},
		{"a&b#c.md", "abc.md"},
		// Unicode letters and digits are kept.
		{"說明.md", "說明.md"},
		{"メモ.txt", "メモ.txt"},
		{"메모.md", "메모.md"},
		{"會議紀錄_附件.md", "會議紀錄_附件.md"},
		{"が.md", "が.md"}, // decomposed kana + combining mark (macOS NFD)
		// Unsafe input.
		{"../x.md", "x.md"},
		{"a/b.md", "b.md"},
		{`a\b.md`, "b.md"},
		{`..\..\x.md`, "x.md"},
		{"..", ""},
		{"CON.md", "_CON.md"},
		{"nul.txt", "_nul.txt"},
		{"com1.md", "_com1.md"},
		{"Lpt9.tar.md", "_Lpt9.tar.md"},
		{"console.md", "console.md"},
		{`<>:"|?*.md`, ".md"},
		{"ctl\x01\x1f\x7f名‮.md", "ctl名.md"},
		{"結尾. . ", "結尾"},
		{longCJK + ".md", strings.Repeat("漢", 59) + ".md"},
	}
	for _, tc := range cases {
		if got := sanitizeAttachmentFilename(tc.in); got != tc.want {
			t.Errorf("sanitizeAttachmentFilename(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

func TestSafeUploadFilenameKeepsUnicodeAndStaysSafe(t *testing.T) {
	longCJK := strings.Repeat("圖", 300)
	cases := []struct{ in, want string }{
		// ASCII results are the same as before the Unicode change.
		{"fixture.png", "fixture.png"},
		{"My Photo (1).PNG", "My_Photo__1_.PNG"},
		{".hidden.png", "hidden.png"},
		{"__x__.jpg", "x__.jpg"},
		{"a+b.webp", "a_b.webp"},
		// Unicode letters and digits are kept.
		{"圖片測試.png", "圖片測試.png"},
		{"写真 1.jpg", "写真_1.jpg"},
		{"사진.webp", "사진.webp"},
		// Unsafe input.
		{"../evil.png", "evil.png"},
		{`a\b.png`, "b.png"},
		{"CON.png", "_CON.png"},
		{"aux", "_aux"},
		{`<>:"|?*.png`, "png"},
		{"ctl\x01\x7f名.gif", "ctl__名.gif"},
		{longCJK + ".png", strings.Repeat("圖", 58) + ".png"},
	}
	for _, tc := range cases {
		if got := safeUploadFilename(tc.in); got != tc.want {
			t.Errorf("safeUploadFilename(%q) = %q, want %q", tc.in, got, tc.want)
		}
		if got := safeUploadFilename(tc.in); len(got) > maxSafeFilenameBytes || !utf8.ValidString(got) {
			t.Errorf("safeUploadFilename(%q) = %q: %d bytes, valid UTF-8 %v", tc.in, got, len(got), utf8.ValidString(got))
		}
	}
}

func TestAttachmentUploadKeepsReadableUnicodeFilenameAndTitle(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	noteID := insertSearchNote(t, db, "附件檔名", "內容", "", 1)

	cases := []struct{ upload, diskBase, title string }{
		{"說明.md", "說明", "說明"},
		{"メモ.txt", "メモ", "メモ"},
		{"메모.md", "메모", "메모"},
		{"會議紀錄_附件.md", "會議紀錄_附件", "會議紀錄_附件"},
		{"report v2.md", "report v2", "report v2"},
		{"../x.md", "x", "x"},
		{"a/b.md", "b", "b"},
		{`a\b.md`, "b", "b"},
		{"CON.md", "_CON", "_CON"},
		{"nul.txt", "_nul", "_nul"},
		{`<>:"|?*.md`, "", ""},
		{strings.Repeat("漢", 300) + ".md", strings.Repeat("漢", 59), strings.Repeat("漢", 59)},
	}
	for _, tc := range cases {
		dataDir := t.TempDir()
		attachmentsDir := filepath.Join(dataDir, "docs", "attachments")
		srv := &server{db: db, runtime: runtimeConfig{
			dataDir: dataDir, attachmentsDir: attachmentsDir, enableAttachmentWrite: true,
		}}
		rec := httptest.NewRecorder()
		srv.handleNoteDetail(rec, newAttachmentUploadRequest(t, noteID, tc.upload, []byte("附件內容"), ""))
		if rec.Code != http.StatusOK {
			t.Fatalf("%q: status %d body=%s", tc.upload, rec.Code, rec.Body.String())
		}
		data := uploadResponseData(t, rec.Body.Bytes())
		filePath, _ := data["file_path"].(string)
		if title, _ := data["title"].(string); title != tc.title {
			t.Errorf("%q: title %q, want %q", tc.upload, title, tc.title)
		}
		name := strings.TrimPrefix(filePath, "docs/attachments/")
		if name == filePath || strings.ContainsAny(name, `/\`) {
			t.Fatalf("%q: file_path %q is not directly under docs/attachments", tc.upload, filePath)
		}
		if got := attachmentTimestampSuffix.ReplaceAllString(name, ""); got != tc.diskBase {
			t.Errorf("%q: disk name %q, want base %q + timestamp", tc.upload, name, tc.diskBase)
		}
		entries, err := os.ReadDir(attachmentsDir)
		if err != nil || len(entries) != 1 || entries[0].Name() != name {
			t.Fatalf("%q: attachments dir %v (err %v), want only %q", tc.upload, entries, err, name)
		}
		top, _ := os.ReadDir(dataDir)
		if len(top) != 1 || top[0].Name() != "docs" {
			t.Fatalf("%q: files escaped into data dir: %v", tc.upload, top)
		}
	}
}

func TestImageUploadAcceptsUnicodeFilename(t *testing.T) {
	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, true, false)
	if err != nil {
		t.Fatal(err)
	}
	srv := &server{db: db, runtime: cfg}
	uploadsDir := filepath.Join(cfg.dataDir, "static", "uploads")

	for _, upload := range []string{"圖片測試.png", "../圖片測試.png", "CON.png"} {
		body, contentType := multipartUploadBody(t, upload, fixturePNG(t, 64, 48), "false")
		req := httptest.NewRequest(http.MethodPost, "/api/upload", body)
		req.Header.Set("Content-Type", contentType)
		rec := httptest.NewRecorder()
		srv.handleUpload(rec, req)
		if rec.Code != http.StatusOK {
			t.Fatalf("%q: status %d body=%s", upload, rec.Code, rec.Body.String())
		}
		data := uploadResponseData(t, rec.Body.Bytes())
		filename := data["filename"].(string)
		want := safeUploadFilename(upload)
		if !strings.HasSuffix(filename, "_"+want) || strings.ContainsAny(filename, `/\`) {
			t.Fatalf("%q: filename %q, want <timestamp>_%s", upload, filename, want)
		}
		if data["url"] != "/static/uploads/"+filename {
			t.Fatalf("%q: url %v", upload, data["url"])
		}
		thumb := strings.TrimSuffix(filename, filepath.Ext(filename)) + "_thumb.webp"
		for _, name := range []string{filename, thumb} {
			if _, err := os.Stat(filepath.Join(uploadsDir, name)); err != nil {
				t.Fatalf("%q: expected %s in uploads dir: %v", upload, name, err)
			}
			// Free the name again: a same-second upload of the same name gets a _2 suffix
			// (PRISM-OPT-75), and this test checks the plain sanitized name.
			if err := os.Remove(filepath.Join(uploadsDir, name)); err != nil {
				t.Fatal(err)
			}
		}
	}
	if !strings.Contains(safeUploadFilename("圖片測試.png"), "圖片測試") {
		t.Fatal("upload filename lost its CJK stem")
	}
}

// newUploadRefEnv runs the real router with image upload, upload delete and media cleanup on.
func newUploadRefEnv(t *testing.T) *inlineEnv {
	t.Helper()
	dataDir := t.TempDir()
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", "prism_upload_ref_test.db", dataDir,
		false, false, true, false, false, false,
		false, false, true, true, true, false, false)
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

func uploadFixtureImage(t *testing.T, e *inlineEnv, name string) string {
	t.Helper()
	body, contentType := multipartUploadBody(t, name, fixturePNG(t, 32, 24), "false")
	req := httptest.NewRequest(http.MethodPost, "/api/upload", body)
	req.Header.Set("Content-Type", contentType)
	req.RemoteAddr = "127.0.0.1:5555"
	rec := httptest.NewRecorder()
	e.srv.httpServer.Handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("upload %q: %d %s", name, rec.Code, rec.Body.String())
	}
	return uploadResponseData(t, rec.Body.Bytes())["filename"].(string)
}

func encodedUploadURL(filename string) string {
	return (&url.URL{Path: "/static/uploads/" + filename}).EscapedPath()
}

func (e *inlineEnv) uploadExists(filename string) bool {
	_, err := os.Stat(filepath.Join(e.srv.runtime.uploadsDir, filename))
	return err == nil
}

func (e *inlineEnv) orphanList() string {
	e.t.Helper()
	rec := e.do(http.MethodGet, "/api/cleanup/orphan-images", "")
	if rec.Code != http.StatusOK {
		e.t.Fatalf("orphan scan: %d %s", rec.Code, rec.Body.String())
	}
	return rec.Body.String()
}

func TestPercentEncodedReferenceProtectsUnicodeUpload(t *testing.T) {
	e := newUploadRefEnv(t)
	filename := uploadFixtureImage(t, e, "圖片測試.png")
	thumb := strings.TrimSuffix(filename, ".png") + "_thumb.webp"
	encoded := encodedUploadURL(filename)
	if !strings.Contains(encoded, "%E5%9C%96") {
		t.Fatalf("fixture URL is not percent-encoded: %s", encoded)
	}
	encodedNote := e.createNote("編碼引用", fmt.Sprintf("![](%s)", encoded))

	if list := e.orphanList(); strings.Contains(list, filename) || strings.Contains(list, thumb) {
		t.Errorf("referenced CJK upload listed as orphan: %s", list)
	}

	if rec := e.do(http.MethodGet, "/api/cleanup/broken-images", ""); rec.Code != http.StatusOK || strings.Contains(rec.Body.String(), "%E5") {
		t.Errorf("percent-encoded reference to an existing upload reported broken: %d %s", rec.Code, rec.Body.String())
	}

	for _, target := range []string{"/static/uploads/" + filename, encoded} {
		payload, _ := json.Marshal(map[string]string{"url": target})
		rec := e.do(http.MethodPost, "/api/upload/delete", string(payload))
		if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"count":0`) {
			t.Fatalf("upload delete %s: %d %s", target, rec.Code, rec.Body.String())
		}
		if !e.uploadExists(filename) || !e.uploadExists(thumb) {
			t.Errorf("upload delete %s removed a referenced image", target)
		}
	}

	// Deleting the note with the raw spelling must keep the image the encoded note still shows.
	rawNote := e.createNote("原始引用", fmt.Sprintf("![](/static/uploads/%s)", filename))
	if rec := e.do(http.MethodDelete, fmt.Sprintf("/api/notes/%d", rawNote), ""); rec.Code != http.StatusOK {
		t.Fatalf("delete raw note: %d %s", rec.Code, rec.Body.String())
	}
	if !e.uploadExists(filename) || !e.uploadExists(thumb) {
		t.Fatal("deleting one note removed an image another note references percent-encoded")
	}
	if list := e.orphanList(); strings.Contains(list, filename) {
		t.Fatalf("image referenced only percent-encoded listed as orphan: %s", list)
	}

	// The last reference goes: the image becomes an orphan again (no false protection).
	if rec := e.do(http.MethodDelete, fmt.Sprintf("/api/notes/%d", encodedNote), ""); rec.Code != http.StatusOK {
		t.Fatalf("delete encoded note: %d %s", rec.Code, rec.Body.String())
	}
	if list := e.orphanList(); !strings.Contains(list, filename) {
		t.Fatalf("unreferenced image should be an orphan: %s", list)
	}
}

func TestEncodedNoteDeleteKeepsImageReferencedRaw(t *testing.T) {
	e := newUploadRefEnv(t)
	filename := uploadFixtureImage(t, e, "會議照片.png")
	encodedNote := e.createNote("編碼引用", fmt.Sprintf("![](%s)", encodedUploadURL(filename)))
	e.createNote("原始引用", fmt.Sprintf("封面 ![](/static/uploads/%s)", filename))
	if rec := e.do(http.MethodDelete, fmt.Sprintf("/api/notes/%d", encodedNote), ""); rec.Code != http.StatusOK {
		t.Fatalf("delete encoded note: %d %s", rec.Code, rec.Body.String())
	}
	if !e.uploadExists(filename) {
		t.Fatal("image still referenced raw was deleted")
	}
	if list := e.orphanList(); strings.Contains(list, filename) {
		t.Fatalf("raw-referenced image listed as orphan: %s", list)
	}
}

// A cover stored with lowercase hex escapes still counts as another note's reference when a
// note that shows the same image raw is deleted (cover_image is compared with LIKE, not =).
func TestLowercaseHexCoverKeepsImageWhenOtherNoteDeleted(t *testing.T) {
	e := newUploadRefEnv(t)
	filename := uploadFixtureImage(t, e, "封面小寫.png")
	coverNote := e.createNote("封面筆記", "內容")
	lowerCover := strings.ToLower(encodedUploadURL(filename))
	if _, err := e.srv.db.Exec("UPDATE Notes SET cover_image = ? WHERE id = ?", lowerCover, coverNote); err != nil {
		t.Fatal(err)
	}
	rawNote := e.createNote("原始引用", fmt.Sprintf("![](/static/uploads/%s)", filename))
	if rec := e.do(http.MethodDelete, fmt.Sprintf("/api/notes/%d", rawNote), ""); rec.Code != http.StatusOK {
		t.Fatalf("delete raw note: %d %s", rec.Code, rec.Body.String())
	}
	if !e.uploadExists(filename) {
		t.Fatal("image still used as a lowercase-hex cover was deleted")
	}
}

func TestASCIIUploadReferencesUnchanged(t *testing.T) {
	e := newUploadRefEnv(t)
	kept := uploadFixtureImage(t, e, "kept.png")
	gone := uploadFixtureImage(t, e, "gone.png")
	e.createNote("ascii", fmt.Sprintf("![](/static/uploads/%s)", kept))
	list := e.orphanList()
	if strings.Contains(list, kept) || !strings.Contains(list, gone) {
		t.Fatalf("ASCII orphan scan changed: %s", list)
	}
}

func TestMediaProtectedReadsPercentEncodedReferences(t *testing.T) {
	name := "20261007_120000_圖片.png"
	encoded := encodedUploadURL(name)
	raw := "/static/uploads/" + name
	refsFrom := func(text string) map[string]bool {
		set := map[string]bool{}
		for _, ref := range uploadReferencesInText(text) {
			addReferencedUploadFilename(set, ref)
		}
		return set
	}
	if !refsFrom("![](" + encoded + ")")[name] {
		t.Fatal("percent-encoded reference must protect the decoded filename")
	}
	if !mediaProtected([]byte("![]("+raw+")"), refsFrom("![]("+encoded+")")) {
		t.Fatal("raw text protected by an encoded reference elsewhere")
	}
	if mediaProtected([]byte("![]("+raw+")"), refsFrom("無引用")) {
		t.Fatal("unreferenced image must not count as protected")
	}
	if !refsFrom("![](/static/uploads/bad%zz.png)")["bad%zz.png"] {
		t.Fatal("undecodable reference must still protect its literal spelling")
	}
}
