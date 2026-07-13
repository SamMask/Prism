package main

import (
	"bytes"
	"context"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	webp "github.com/skrashevich/go-webp"
	"image"
	"image/draw"
	"io"
	"math"
	"mime"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"strings"
)

func (s *server) handleUpload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableUploadWrite && !s.runtime.enableThumbnailWrite {
		writeError(w, http.StatusMethodNotAllowed, "Thumbnail write route is disabled")
		return
	}

	if err := r.ParseMultipartForm(maxUploadFileBytes); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid multipart upload")
		return
	}
	file, header, err := r.FormFile("file")
	if err != nil {
		writeError(w, http.StatusBadRequest, "No file part in request")
		return
	}
	defer file.Close()

	filename := safeUploadFilename(header.Filename)
	if filename == "" {
		writeError(w, http.StatusBadRequest, "No file selected")
		return
	}
	if !allowedUploadExtension(filename) {
		writeError(w, http.StatusBadRequest, "Invalid file type. Allowed: jpg, jpeg, png, gif, webp")
		return
	}

	content, err := io.ReadAll(io.LimitReader(file, maxUploadFileBytes+1))
	if err != nil {
		writeError(w, http.StatusBadRequest, "Failed to read upload")
		return
	}
	if int64(len(content)) > maxUploadFileBytes {
		writeError(w, http.StatusBadRequest, "File too large. Maximum size: 5MB")
		return
	}
	detectedMIME := detectUploadImageMIME(content)
	if !allowedUploadMIME(detectedMIME) {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("File content validation failed. Detected MIME: %s", detectedMIME))
		return
	}

	img, _, err := image.Decode(bytes.NewReader(content))
	if err != nil {
		writeError(w, http.StatusBadRequest, "Thumbnail generation failed")
		return
	}
	thumbContent, err := encodeThumbnailWebP(img)
	if err != nil {
		writeError(w, http.StatusBadRequest, "Thumbnail generation failed")
		return
	}

	newFilename := timestampedUploadFilename(filename)
	nameWithoutExt := strings.TrimSuffix(newFilename, filepath.Ext(newFilename))
	thumbFilename := nameWithoutExt + "_thumb.webp"
	uploadsDir := s.runtime.uploadsDir
	if err := os.MkdirAll(uploadsDir, 0755); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	thumbnailOnly := strings.EqualFold(r.FormValue("thumbnail_only"), "true")
	thumbPath := filepath.Join(uploadsDir, thumbFilename)
	if thumbnailOnly {
		if err := os.WriteFile(thumbPath, thumbContent, 0644); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
			"url":            "/static/uploads/" + thumbFilename,
			"filename":       thumbFilename,
			"size":           len(content),
			"thumbnail_only": true,
		}})
		return
	}

	originalPath := filepath.Join(uploadsDir, newFilename)
	if err := os.WriteFile(originalPath, content, 0644); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := os.WriteFile(thumbPath, thumbContent, 0644); err != nil {
		_ = os.Remove(originalPath)
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"url":            "/static/uploads/" + newFilename,
		"filename":       newFilename,
		"size":           len(content),
		"thumbnail_only": false,
	}})
}

func (s *server) handleUploadDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableUploadDelete {
		writeError(w, http.StatusMethodNotAllowed, "Upload delete route is disabled")
		return
	}

	var payload struct {
		URL string `json:"url"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil && !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "Invalid JSON request")
		return
	}
	if strings.TrimSpace(payload.URL) == "" {
		writeError(w, http.StatusBadRequest, "No URL provided")
		return
	}
	filename, ok := uploadDeleteFilename(payload.URL)
	if !ok {
		writeError(w, http.StatusBadRequest, "Invalid filename")
		return
	}

	referenced, err := s.expandedReferencedUploadFilenames()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	deleted := []string{}
	for _, candidate := range uploadDeleteCandidates(filename) {
		if referenced[candidate] {
			continue
		}
		absPath, ok := s.resolveUploadFile(candidate)
		if !ok {
			continue
		}
		info, err := os.Stat(absPath)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if !info.Mode().IsRegular() {
			continue
		}
		if err := os.Remove(absPath); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		deleted = append(deleted, candidate)
	}

	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{
		"deleted": deleted,
		"count":   len(deleted),
	}})
}

func (s *server) handleUploadURL(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		w.Header().Set("Allow", http.MethodPost)
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableUploadURLWrite {
		writeError(w, http.StatusMethodNotAllowed, "Upload-url write route is disabled")
		return
	}

	var payload struct {
		URL           string `json:"url"`
		ThumbnailOnly bool   `json:"thumbnail_only"`
	}
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil && !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "Invalid JSON request")
		return
	}
	imageURL := strings.TrimSpace(payload.URL)
	if imageURL == "" {
		writeError(w, http.StatusBadRequest, "No URL provided")
		return
	}

	parsed, err := url.Parse(imageURL)
	if err != nil || parsed.Scheme == "" || parsed.Hostname() == "" {
		writeError(w, http.StatusBadRequest, "Invalid URL scheme. Only http/https allowed.")
		return
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		writeError(w, http.StatusBadRequest, "Invalid URL scheme. Only http/https allowed.")
		return
	}

	content, contentType, err := downloadUploadURLImage(r.Context(), parsed, imageURL)
	if err != nil {
		if errors.Is(err, errUploadURLSSRF) {
			writeError(w, http.StatusBadRequest, "URL resolves to a private or reserved IP address.")
			return
		}
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	contentMIME := normalizeContentType(contentType)
	if !strings.HasPrefix(contentMIME, "image/") {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("URL does not point to an image. Content-Type: %s", contentType))
		return
	}
	if int64(len(content)) > maxUploadFileBytes {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("Image too large. Maximum size: %dMB", maxUploadFileBytes/(1024*1024)))
		return
	}
	detectedMIME := detectUploadImageMIME(content)
	if !allowedRemoteUploadMIME(detectedMIME) {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("Invalid image type. Detected: %s", detectedMIME))
		return
	}

	baseName := uploadURLBaseFilename(imageURL, parsed, contentMIME)
	newFilename := timestampedUploadFilename(baseName)
	data, err := s.saveDownloadedUpload(content, newFilename, imageURL, payload.ThumbnailOnly)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": data})
}

func downloadUploadURLImage(ctx context.Context, parsed *url.URL, imageURL string) ([]byte, string, error) {
	if err := validateUploadURLTarget(ctx, parsed); err != nil {
		return nil, "", err
	}
	client := &http.Client{
		Timeout:   uploadURLTimeout,
		Transport: uploadURLTransport,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 10 {
				return errors.New("too many redirects")
			}
			return validateUploadURLTarget(req.Context(), req.URL)
		},
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, imageURL, nil)
	if err != nil {
		return nil, "", fmt.Errorf("Failed to download image: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
	req.Header.Set("Referer", parsed.Scheme+"://"+parsed.Host+"/")

	resp, err := client.Do(req)
	if err != nil {
		if errors.Is(err, errUploadURLSSRF) {
			return nil, "", err
		}
		return nil, "", fmt.Errorf("Failed to download image: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, "", fmt.Errorf("Failed to download image: HTTP %d", resp.StatusCode)
	}
	contentType := resp.Header.Get("Content-Type")
	if !strings.HasPrefix(normalizeContentType(contentType), "image/") {
		return nil, "", fmt.Errorf("URL does not point to an image. Content-Type: %s", contentType)
	}
	content, err := io.ReadAll(io.LimitReader(resp.Body, maxUploadFileBytes+1))
	if err != nil {
		return nil, "", fmt.Errorf("Failed to download image: %w", err)
	}
	if int64(len(content)) > maxUploadFileBytes {
		return nil, "", fmt.Errorf("Image too large. Maximum size: %dMB", maxUploadFileBytes/(1024*1024))
	}
	return content, contentType, nil
}

func validateUploadURLTarget(ctx context.Context, parsed *url.URL) error {
	if parsed == nil || parsed.Hostname() == "" {
		return errUploadURLSSRF
	}
	hostname := parsed.Hostname()
	if addr, err := netip.ParseAddr(hostname); err == nil {
		if blockedUploadAddr(addr) {
			return errUploadURLSSRF
		}
		return nil
	}
	ips, err := uploadURLResolveHost(ctx, hostname)
	if err != nil || len(ips) == 0 {
		return errUploadURLSSRF
	}
	for _, ip := range ips {
		if blockedUploadIP(ip) {
			return errUploadURLSSRF
		}
	}
	return nil
}

func defaultUploadURLResolveHost(ctx context.Context, hostname string) ([]net.IP, error) {
	return net.DefaultResolver.LookupIP(ctx, "ip", hostname)
}

func blockedUploadIP(ip net.IP) bool {
	if ip == nil {
		return true
	}
	raw := ip
	if v4 := ip.To4(); v4 != nil {
		raw = v4
	} else {
		raw = ip.To16()
	}
	addr, ok := netip.AddrFromSlice(raw)
	if !ok {
		return true
	}
	addr = addr.Unmap()
	return blockedUploadAddr(addr)
}

func blockedUploadAddr(addr netip.Addr) bool {
	if addr.IsLoopback() || addr.IsPrivate() || addr.IsLinkLocalUnicast() ||
		addr.IsLinkLocalMulticast() || addr.IsMulticast() || addr.IsUnspecified() {
		return true
	}
	for _, prefix := range blockedUploadIPPrefixes {
		if prefix.Contains(addr) {
			return true
		}
	}
	return false
}

var blockedUploadIPPrefixes = []netip.Prefix{
	netip.MustParsePrefix("0.0.0.0/8"),
	netip.MustParsePrefix("100.64.0.0/10"),
	netip.MustParsePrefix("192.0.0.0/24"),
	netip.MustParsePrefix("192.0.2.0/24"),
	netip.MustParsePrefix("198.18.0.0/15"),
	netip.MustParsePrefix("198.51.100.0/24"),
	netip.MustParsePrefix("203.0.113.0/24"),
	netip.MustParsePrefix("240.0.0.0/4"),
	netip.MustParsePrefix("2001:db8::/32"),
}

func normalizeContentType(value string) string {
	mediaType, _, err := mime.ParseMediaType(value)
	if err == nil {
		return strings.ToLower(mediaType)
	}
	return strings.ToLower(strings.TrimSpace(strings.Split(value, ";")[0]))
}

func detectUploadImageMIME(content []byte) string {
	switch {
	case len(content) >= 3 && content[0] == 0xff && content[1] == 0xd8 && content[2] == 0xff:
		return "image/jpeg"
	case len(content) >= 8 && bytes.Equal(content[:8], []byte{0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'}):
		return "image/png"
	case len(content) >= 6 && (bytes.Equal(content[:6], []byte("GIF87a")) || bytes.Equal(content[:6], []byte("GIF89a"))):
		return "image/gif"
	case len(content) >= 12 && bytes.Equal(content[:4], []byte("RIFF")) && bytes.Equal(content[8:12], []byte("WEBP")):
		return "image/webp"
	default:
		return normalizeContentType(http.DetectContentType(content))
	}
}

func allowedRemoteUploadMIME(mimeType string) bool {
	switch mimeType {
	case "image/jpeg", "image/png", "image/gif", "image/webp":
		return true
	default:
		return false
	}
}

func uploadURLBaseFilename(imageURL string, parsed *url.URL, contentType string) string {
	urlPath, err := url.PathUnescape(parsed.EscapedPath())
	if err != nil {
		urlPath = parsed.Path
	}
	originalName := path.Base(urlPath)
	if originalName == "." || originalName == "/" {
		originalName = ""
	}
	if originalName != "" && strings.Contains(originalName, ".") {
		if safeName := safeUploadFilename(originalName); safeName != "" {
			return safeName
		}
	}
	sum := md5.Sum([]byte(imageURL))
	hash := hex.EncodeToString(sum[:])[:8]
	return "remote_" + hash + uploadExtensionForMIME(contentType)
}

func uploadExtensionForMIME(mimeType string) string {
	switch normalizeContentType(mimeType) {
	case "image/jpeg":
		return ".jpg"
	case "image/png":
		return ".png"
	case "image/webp":
		return ".webp"
	case "image/gif":
		return ".gif"
	default:
		return ".jpg"
	}
}

func timestampedUploadFilename(filename string) string {
	return uploadNow().Format("20060102_150405") + "_" + filename
}

func (s *server) saveDownloadedUpload(content []byte, newFilename, originalURL string, thumbnailOnly bool) (response, error) {
	uploadsDir := s.runtime.uploadsDir
	if err := os.MkdirAll(uploadsDir, 0755); err != nil {
		return nil, err
	}

	var thumbFilename string
	var thumbContent []byte
	if img, _, err := image.Decode(bytes.NewReader(content)); err == nil {
		if encoded, err := encodeUploadThumbnail(img); err == nil {
			nameWithoutExt := strings.TrimSuffix(newFilename, filepath.Ext(newFilename))
			thumbFilename = nameWithoutExt + "_thumb.webp"
			thumbContent = encoded
		}
	}

	if thumbnailOnly && thumbFilename != "" {
		if err := os.WriteFile(filepath.Join(uploadsDir, thumbFilename), thumbContent, 0644); err != nil {
			return nil, err
		}
		return response{
			"url":            "/static/uploads/" + thumbFilename,
			"filename":       thumbFilename,
			"size":           len(content),
			"original_url":   originalURL,
			"thumbnail_only": true,
		}, nil
	}

	originalPath := filepath.Join(uploadsDir, newFilename)
	if err := os.WriteFile(originalPath, content, 0644); err != nil {
		return nil, err
	}
	if thumbFilename != "" {
		if err := os.WriteFile(filepath.Join(uploadsDir, thumbFilename), thumbContent, 0644); err != nil {
			_ = os.Remove(originalPath)
			return nil, err
		}
	}
	var returnedFilename any = newFilename
	if thumbnailOnly {
		returnedFilename = nil
	}
	return response{
		"url":            "/static/uploads/" + newFilename,
		"filename":       returnedFilename,
		"size":           len(content),
		"original_url":   originalURL,
		"thumbnail_only": thumbnailOnly,
	}, nil
}

func safeUploadFilename(filename string) string {
	base := filepath.Base(strings.ReplaceAll(strings.TrimSpace(filename), "\\", "/"))
	base = strings.Trim(base, ".")
	if base == "" {
		return ""
	}
	cleaned := strings.Map(func(r rune) rune {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' {
			return r
		}
		switch r {
		case '.', '_', '-':
			return r
		default:
			return '_'
		}
	}, base)
	return strings.Trim(cleaned, "._-")
}

func allowedUploadExtension(filename string) bool {
	switch strings.ToLower(filepath.Ext(filename)) {
	case ".jpg", ".jpeg", ".png", ".gif", ".webp":
		return true
	default:
		return false
	}
}

func allowedUploadMIME(mime string) bool {
	switch mime {
	case "image/jpeg", "image/png", "image/gif", "image/webp":
		return true
	default:
		return false
	}
}

func encodeThumbnailWebP(img image.Image) ([]byte, error) {
	resized := resizeToMaxWidth(img, thumbnailMaxWidth)
	var out bytes.Buffer
	if err := webp.Encode(&out, resized, &webp.Options{Lossy: true, Quality: thumbnailWebPQuality}); err != nil {
		return nil, err
	}
	return out.Bytes(), nil
}

func resizeToMaxWidth(img image.Image, maxWidth int) image.Image {
	bounds := img.Bounds()
	width := bounds.Dx()
	height := bounds.Dy()
	if width <= 0 || height <= 0 {
		return image.NewRGBA(image.Rect(0, 0, 1, 1))
	}
	if width <= maxWidth {
		dst := image.NewRGBA(image.Rect(0, 0, width, height))
		draw.Draw(dst, dst.Bounds(), img, bounds.Min, draw.Src)
		return dst
	}

	newHeight := int(math.Round(float64(height) * float64(maxWidth) / float64(width)))
	if newHeight < 1 {
		newHeight = 1
	}
	dst := image.NewRGBA(image.Rect(0, 0, maxWidth, newHeight))
	for y := 0; y < newHeight; y++ {
		srcY := bounds.Min.Y + y*height/newHeight
		for x := 0; x < maxWidth; x++ {
			srcX := bounds.Min.X + x*width/maxWidth
			dst.Set(x, y, img.At(srcX, srcY))
		}
	}
	return dst
}
