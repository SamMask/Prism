package main

import (
	"bytes"
	"compress/zlib"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

func (s *server) handleExtractPrompt(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) {
		return
	}
	if !s.runtime.enableUploadWrite {
		_, _ = io.Copy(io.Discard, r.Body)
		writeError(w, http.StatusMethodNotAllowed, "Upload route is disabled")
		return
	}
	payload, ok := decodeJSONObject(w, r, "image_path is required")
	if !ok {
		return
	}
	imagePath := strings.TrimSpace(stringField(payload, "image_path"))
	if imagePath == "" {
		writeError(w, http.StatusBadRequest, "image_path is required")
		return
	}
	resolved, ok := s.resolvePromptImagePath(imagePath)
	if !ok {
		writeError(w, http.StatusNotFound, "Image file not found")
		return
	}
	promptData, err := extractPromptMetadata(resolved)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to read image metadata: "+err.Error())
		return
	}
	if strings.TrimSpace(promptData.Prompt) == "" {
		writeJSON(w, http.StatusOK, response{
			"status": "success",
			"data": response{
				"prompt":          nil,
				"negative_prompt": nil,
				"source":          nil,
				"has_prompt":      false,
			},
		})
		return
	}
	writeJSON(w, http.StatusOK, response{
		"status": "success",
		"data": response{
			"prompt":          promptData.Prompt,
			"negative_prompt": nilIfEmpty(promptData.NegativePrompt),
			"source":          nilIfEmpty(promptData.Source),
			"has_prompt":      true,
		},
	})
}

func (s *server) resolvePromptImagePath(imagePath string) (string, bool) {
	cleaned := strings.TrimSpace(strings.ReplaceAll(imagePath, "\\", "/"))
	if strings.HasPrefix(cleaned, "/static/uploads/") {
		cleaned = strings.TrimPrefix(cleaned, "/static/uploads/")
	} else if strings.HasPrefix(cleaned, "static/uploads/") {
		cleaned = strings.TrimPrefix(cleaned, "static/uploads/")
	}
	if cleaned == "" || strings.Contains(cleaned, ":") || strings.HasPrefix(cleaned, "/") {
		return "", false
	}
	absPath, ok := s.resolveUploadFile(cleaned)
	if !ok {
		return "", false
	}
	info, err := os.Lstat(absPath)
	if err != nil || !info.Mode().IsRegular() || info.Size() > maxUploadFileBytes {
		return "", false
	}
	resolved, err := filepath.EvalSymlinks(absPath)
	evaluatedUploadsDir, rootErr := filepath.EvalSymlinks(s.runtime.uploadsDir)
	if err != nil || rootErr != nil || !isSubpath(resolved, evaluatedUploadsDir) {
		return "", false
	}
	return resolved, true
}

type promptMetadata struct {
	Prompt         string
	NegativePrompt string
	Source         string
}

func extractPromptMetadata(filename string) (promptMetadata, error) {
	content, err := os.ReadFile(filename)
	if err != nil {
		return promptMetadata{}, err
	}
	fields := readPNGTextFields(content)
	return promptMetadataFromFields(fields), nil
}

func readPNGTextFields(content []byte) map[string]string {
	fields := map[string]string{}
	if len(content) < 8 || !bytes.Equal(content[:8], []byte("\x89PNG\r\n\x1a\n")) {
		return fields
	}
	for offset := 8; offset+12 <= len(content); {
		length := int(content[offset])<<24 | int(content[offset+1])<<16 | int(content[offset+2])<<8 | int(content[offset+3])
		chunkType := string(content[offset+4 : offset+8])
		chunkStart := offset + 8
		chunkEnd := chunkStart + length
		if chunkEnd+4 > len(content) {
			return fields
		}
		chunk := content[chunkStart:chunkEnd]
		switch chunkType {
		case "tEXt":
			if key, value, ok := parsePNGTextChunk(chunk); ok {
				fields[key] = value
			}
		case "zTXt":
			if key, value, ok := parsePNGZTextChunk(chunk); ok {
				fields[key] = value
			}
		case "iTXt":
			if key, value, ok := parsePNGInternationalTextChunk(chunk); ok {
				fields[key] = value
			}
		case "IEND":
			return fields
		}
		offset = chunkEnd + 4
	}
	return fields
}

func parsePNGTextChunk(chunk []byte) (string, string, bool) {
	parts := bytes.SplitN(chunk, []byte{0}, 2)
	if len(parts) != 2 {
		return "", "", false
	}
	return latin1String(parts[0]), string(parts[1]), true
}

func parsePNGZTextChunk(chunk []byte) (string, string, bool) {
	parts := bytes.SplitN(chunk, []byte{0}, 2)
	if len(parts) != 2 || len(parts[1]) == 0 || parts[1][0] != 0 {
		return "", "", false
	}
	reader, err := zlib.NewReader(bytes.NewReader(parts[1][1:]))
	if err != nil {
		return "", "", false
	}
	defer reader.Close()
	text, err := io.ReadAll(io.LimitReader(reader, maxUploadFileBytes+1))
	if err != nil || int64(len(text)) > maxUploadFileBytes {
		return "", "", false
	}
	return latin1String(parts[0]), string(text), true
}

func parsePNGInternationalTextChunk(chunk []byte) (string, string, bool) {
	parts := bytes.SplitN(chunk, []byte{0}, 6)
	if len(parts) != 6 {
		return "", "", false
	}
	text := parts[5]
	if len(parts[1]) > 0 && parts[1][0] == 1 {
		if len(parts[2]) == 0 || parts[2][0] != 0 {
			return "", "", false
		}
		reader, err := zlib.NewReader(bytes.NewReader(text))
		if err != nil {
			return "", "", false
		}
		defer reader.Close()
		decoded, err := io.ReadAll(io.LimitReader(reader, maxUploadFileBytes+1))
		if err != nil || int64(len(decoded)) > maxUploadFileBytes {
			return "", "", false
		}
		text = decoded
	}
	return latin1String(parts[0]), string(text), true
}

func promptMetadataFromFields(fields map[string]string) promptMetadata {
	if value := strings.TrimSpace(fields["parameters"]); value != "" {
		prompt, negative := splitStableDiffusionPrompt(value)
		return promptMetadata{Prompt: prompt, NegativePrompt: negative, Source: "stable_diffusion"}
	}
	if value := strings.TrimSpace(fields["prompt"]); value != "" {
		return promptMetadata{Prompt: value, Source: "comfyui"}
	}
	if value := strings.TrimSpace(fields["Comment"]); value != "" {
		payload := map[string]any{}
		if err := json.Unmarshal([]byte(value), &payload); err == nil {
			if prompt := strings.TrimSpace(stringField(payload, "prompt")); prompt != "" {
				return promptMetadata{Prompt: prompt, NegativePrompt: stringField(payload, "uc"), Source: "novelai"}
			}
		}
	}
	if value := strings.TrimSpace(fields["Description"]); value != "" {
		return promptMetadata{Prompt: value, Source: "description"}
	}
	return promptMetadata{}
}

func splitStableDiffusionPrompt(parameters string) (string, string) {
	lines := strings.Split(parameters, "\n")
	promptLines := []string{}
	negative := ""
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "Negative prompt:") {
			negative = strings.TrimSpace(strings.TrimPrefix(trimmed, "Negative prompt:"))
			continue
		}
		if strings.HasPrefix(trimmed, "Steps:") || strings.HasPrefix(trimmed, "Size:") || strings.HasPrefix(trimmed, "Sampler:") {
			break
		}
		promptLines = append(promptLines, line)
	}
	return strings.TrimSpace(strings.Join(promptLines, "\n")), negative
}

func latin1String(raw []byte) string {
	var builder strings.Builder
	for _, b := range raw {
		builder.WriteRune(rune(b))
	}
	return builder.String()
}

func nilIfEmpty(value string) any {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	return value
}
