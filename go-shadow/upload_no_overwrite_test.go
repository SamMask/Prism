package main

import (
	"bytes"
	"image"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// PRISM-OPT-75: an image upload never replaces an original or _thumb.webp that is already on
// disk, and the original and its thumbnail always share one name stem.

const noOverwriteImageStamp = "20261007_120000_"

func newNoOverwriteImageServer(t *testing.T) (*server, string) {
	t.Helper()
	original := uploadNow
	uploadNow = func() time.Time { return time.Date(2026, 10, 7, 12, 0, 0, 0, time.Local) }
	t.Cleanup(func() { uploadNow = original })

	dbPath := createSpikeDB(t)
	db, err := openDB(dbPath, false)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	cfg, err := resolveRuntimeConfig("127.0.0.1:0", dbPath, t.TempDir(), false, false, false, false, true, true)
	if err != nil {
		t.Fatal(err)
	}
	return &server{db: db, runtime: cfg}, cfg.uploadsDir
}

func uploadNoOverwriteImage(t *testing.T, srv *server, filename string, content []byte, thumbnailOnly string) map[string]any {
	t.Helper()
	body, contentType := multipartUploadBody(t, filename, content, thumbnailOnly)
	req := httptest.NewRequest(http.MethodPost, "/api/upload", body)
	req.Header.Set("Content-Type", contentType)
	rec := httptest.NewRecorder()
	srv.handleUpload(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("upload %q: status %d body=%s", filename, rec.Code, rec.Body.String())
	}
	return uploadResponseData(t, rec.Body.Bytes())
}

func uploadNoOverwriteImageURL(t *testing.T, srv *server, imageURL string, content []byte) map[string]any {
	t.Helper()
	withUploadURLHooks(t, publicUploadURLResolver, fakeUploadURLTransport(t, content, "image/png", nil))
	rec := httptest.NewRecorder()
	srv.handleUploadURL(rec, httptest.NewRequest(http.MethodPost, "/api/upload/url", uploadURLJSONBody(imageURL, false)))
	if rec.Code != http.StatusOK {
		t.Fatalf("upload-url %q: status %d body=%s", imageURL, rec.Code, rec.Body.String())
	}
	return uploadResponseData(t, rec.Body.Bytes())
}

// getStaticUpload reads a file back the way the browser does: GET /static/uploads/<escaped name>.
func getStaticUpload(t *testing.T, srv *server, name string) []byte {
	t.Helper()
	rec := httptest.NewRecorder()
	srv.serveStaticUpload(rec, httptest.NewRequest(http.MethodGet, "/static/uploads/"+url.PathEscape(name), nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /static/uploads/%s: status %d", name, rec.Code)
	}
	return rec.Body.Bytes()
}

func imageWidth(t *testing.T, content []byte) int {
	t.Helper()
	cfg, _, err := image.DecodeConfig(bytes.NewReader(content))
	if err != nil {
		t.Fatalf("decode image: %v", err)
	}
	return cfg.Width
}

func thumbNameFor(filename string) string {
	return strings.TrimSuffix(filename, filepath.Ext(filename)) + "_thumb.webp"
}

// assertImagePair checks that the response points at an original whose bytes are want and whose
// paired <stem>_thumb.webp exists with the original's width.
func assertImagePair(t *testing.T, srv *server, data map[string]any, want []byte) string {
	t.Helper()
	filename, _ := data["filename"].(string)
	if filename == "" || data["url"] != "/static/uploads/"+filename {
		t.Fatalf("response filename %v / url %v do not match", data["filename"], data["url"])
	}
	if got := getStaticUpload(t, srv, filename); !bytes.Equal(got, want) {
		t.Fatalf("%s: read back %d bytes, want the %d bytes that were uploaded", filename, len(got), len(want))
	}
	thumb := getStaticUpload(t, srv, thumbNameFor(filename))
	if got, wantWidth := imageWidth(t, thumb), imageWidth(t, want); got != wantWidth {
		t.Fatalf("%s: thumbnail width %d, want %d (thumbnail of another upload?)", thumbNameFor(filename), got, wantWidth)
	}
	return filename
}

func TestImageUploadSameSecondSameNameKeepsBothPairs(t *testing.T) {
	srv, uploadsDir := newNoOverwriteImageServer(t)
	first, second := fixturePNG(t, 64, 48), fixturePNG(t, 80, 60)

	firstData := uploadNoOverwriteImage(t, srv, "圖片.png", first, "false")
	secondData := uploadNoOverwriteImage(t, srv, "圖片.png", second, "false")

	if firstData["url"] == secondData["url"] {
		t.Fatalf("both uploads got the same url %v", firstData["url"])
	}
	firstName := assertImagePair(t, srv, firstData, first)
	secondName := assertImagePair(t, srv, secondData, second)
	if firstName != noOverwriteImageStamp+"圖片.png" || secondName != noOverwriteImageStamp+"圖片_2.png" {
		t.Fatalf("names %q, %q; want <ts>_圖片.png then <ts>_圖片_2.png", firstName, secondName)
	}
	entries, err := os.ReadDir(uploadsDir)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 4 {
		t.Fatalf("want 2 originals + 2 thumbnails, got %v", entries)
	}
}

func TestThumbnailOnlyUploadSameSecondSameNameKeepsBothThumbs(t *testing.T) {
	srv, _ := newNoOverwriteImageServer(t)
	first, second := fixturePNG(t, 64, 48), fixturePNG(t, 80, 60)

	firstData := uploadNoOverwriteImage(t, srv, "縮圖.png", first, "true")
	secondData := uploadNoOverwriteImage(t, srv, "縮圖.png", second, "true")

	firstName, _ := firstData["filename"].(string)
	secondName, _ := secondData["filename"].(string)
	if firstName == secondName || firstData["url"] != "/static/uploads/"+firstName || secondData["url"] != "/static/uploads/"+secondName {
		t.Fatalf("thumbnail-only responses %v / %v", firstData, secondData)
	}
	if imageWidth(t, getStaticUpload(t, srv, firstName)) != 64 || imageWidth(t, getStaticUpload(t, srv, secondName)) != 80 {
		t.Fatalf("thumbnail-only files %q / %q do not hold their own thumbnails", firstName, secondName)
	}
}

func TestImageUploadLeavesUnrelatedSameNameFileAlone(t *testing.T) {
	for _, taken := range []string{noOverwriteImageStamp + "圖片.png", noOverwriteImageStamp + "圖片_thumb.webp"} {
		t.Run(taken, func(t *testing.T) {
			srv, uploadsDir := newNoOverwriteImageServer(t)
			unrelated := []byte("不相關的檔案 unrelated")
			if err := os.WriteFile(filepath.Join(uploadsDir, taken), unrelated, 0644); err != nil {
				t.Fatal(err)
			}
			content := fixturePNG(t, 72, 40)

			name := assertImagePair(t, srv, uploadNoOverwriteImage(t, srv, "圖片.png", content, "false"), content)

			if name != noOverwriteImageStamp+"圖片_2.png" {
				t.Fatalf("filename %q, want <ts>_圖片_2.png", name)
			}
			assertFileContent(t, filepath.Join(uploadsDir, taken), string(unrelated))
			entries, err := os.ReadDir(uploadsDir)
			if err != nil {
				t.Fatal(err)
			}
			if len(entries) != 3 {
				t.Fatalf("want the unrelated file plus one new pair, got %v", entries)
			}
		})
	}
}

func TestUploadURLSameSecondSameNameKeepsBothPairs(t *testing.T) {
	srv, _ := newNoOverwriteImageServer(t)
	first, second := fixturePNG(t, 64, 48), fixturePNG(t, 80, 60)
	imageURL := "https://example.test/" + url.PathEscape("圖片.png")

	firstData := uploadNoOverwriteImageURL(t, srv, imageURL, first)
	secondData := uploadNoOverwriteImageURL(t, srv, imageURL, second)

	if firstData["url"] == secondData["url"] {
		t.Fatalf("both URL downloads got the same url %v", firstData["url"])
	}
	assertImagePair(t, srv, firstData, first)
	assertImagePair(t, srv, secondData, second)
}

// The writes stop at the first name stem whose original and thumbnail are both free, and a
// failed write removes only the file it created.
func TestCreateUploadFilesKeepsPairOnSharedStem(t *testing.T) {
	dir := t.TempDir()
	taken := filepath.Join(dir, "a_2_thumb.webp")
	if err := os.WriteFile(taken, []byte("keep 保留"), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "a.png"), []byte("keep"), 0644); err != nil {
		t.Fatal(err)
	}

	name, thumb, err := createUploadFiles(dir, "a.png", []byte("orig"), []byte("thumb"))
	if err != nil {
		t.Fatal(err)
	}
	if name != "a_3.png" || thumb != "a_3_thumb.webp" {
		t.Fatalf("got %q / %q, want a_3.png / a_3_thumb.webp", name, thumb)
	}
	assertFileContent(t, taken, "keep 保留")
	if _, err := os.Stat(filepath.Join(dir, "a_2.png")); !os.IsNotExist(err) {
		t.Fatalf("a_2.png should not be left behind when its thumbnail name was taken: %v", err)
	}
	f, err := os.Open(filepath.Join(dir, name))
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	if got, _ := io.ReadAll(f); string(got) != "orig" {
		t.Fatalf("original content %q", got)
	}
}
