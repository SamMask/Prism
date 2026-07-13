package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"net/http"
	"strings"
	"time"
)

func (s *server) createNote(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "Content is required")
	if !ok {
		return
	}
	content := stringField(payload, "content")
	if content == "" {
		writeError(w, http.StatusBadRequest, "Content is required")
		return
	}

	title := strings.TrimSpace(stringField(payload, "title"))
	if title == "" {
		title = autoNoteTitle(content)
	}
	categoryID, ok := intField(payload, "category_id")
	if !ok {
		var defaultID sql.NullInt64
		if err := s.db.QueryRow("SELECT id FROM Categories WHERE is_default = 1 LIMIT 1").Scan(&defaultID); err == nil && defaultID.Valid {
			categoryID = int(defaultID.Int64)
			ok = true
		}
	}
	promptParams, err := marshalJSONField(payload, "prompt_params")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	cursor, err := tx.Exec(`
		INSERT INTO Notes (
			title, content, category_id, remarks, cover_image,
			cover_position, editor_layout, prompt_params, is_pinned, is_archived
		)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		title, content, nullableIntArg(categoryID, ok),
		stringField(payload, "remarks"), nullableStringArg(payload, "cover_image"),
		defaultStringField(payload, "cover_position", "top"),
		defaultStringField(payload, "editor_layout", "single"),
		promptParams, boolIntField(payload, "is_pinned"), boolIntField(payload, "is_archived"))
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	noteID, err := cursor.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteTags(tx, int(noteID), stringArrayField(payload, "tags"), false); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteURLs(tx, int(noteID), stringArrayField(payload, "urls")); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"note_id": int(noteID)}})
}

func (s *server) updateNote(w http.ResponseWriter, r *http.Request, noteID int) {
	payload, ok := decodeJSONObject(w, r, "Title and content are required")
	if !ok {
		return
	}
	title := stringField(payload, "title")
	content := stringField(payload, "content")
	if title == "" || content == "" {
		writeError(w, http.StatusBadRequest, "Title and content are required")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var oldContent string
	var isPinned, isArchived int
	if err := tx.QueryRow("SELECT content, COALESCE(is_pinned, 0), COALESCE(is_archived, 0) FROM Notes WHERE id = ?", noteID).Scan(&oldContent, &isPinned, &isArchived); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	if oldContent != content {
		summary := fmt.Sprintf("字數變化: %d → %d", len([]rune(oldContent)), len([]rune(content)))
		if _, err := tx.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, ?, ?)", noteID, oldContent, summary); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}
	categoryID, hasCategoryID := intField(payload, "category_id")
	if !hasCategoryID {
		var existing sql.NullInt64
		if err := tx.QueryRow("SELECT category_id FROM Notes WHERE id = ?", noteID).Scan(&existing); err == nil && existing.Valid {
			categoryID = int(existing.Int64)
			hasCategoryID = true
		}
	}
	if _, ok := payload["is_pinned"]; ok {
		isPinned = boolIntField(payload, "is_pinned")
	}
	if _, ok := payload["is_archived"]; ok {
		isArchived = boolIntField(payload, "is_archived")
	}
	promptParams, err := marshalJSONField(payload, "prompt_params")
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	if _, err := tx.Exec(`
		UPDATE Notes
		SET title = ?, content = ?, category_id = ?, remarks = ?, cover_image = ?,
		    cover_position = ?, editor_layout = ?, prompt_params = ?,
		    is_pinned = ?, is_archived = ?, updated_at = CURRENT_TIMESTAMP
		WHERE id = ?`,
		title, content, nullableIntArg(categoryID, hasCategoryID),
		stringField(payload, "remarks"), nullableStringArg(payload, "cover_image"),
		defaultStringField(payload, "cover_position", "top"),
		defaultStringField(payload, "editor_layout", "single"),
		promptParams, isPinned, isArchived, noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("DELETE FROM Note_Tags WHERE note_id = ?", noteID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteTags(tx, noteID, stringArrayField(payload, "tags"), false); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := replaceNoteURLs(tx, noteID, stringArrayField(payload, "urls")); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func (s *server) deleteNote(w http.ResponseWriter, noteID int) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var ref noteImageReference
	if err := tx.QueryRow("SELECT id, content, cover_image FROM Notes WHERE id = ?", noteID).Scan(&ref.ID, &ref.Content, &ref.CoverImage); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Note not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	attachmentPaths, err := s.noteAttachmentCleanupPaths(tx, []int{noteID})
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	s.cleanupNoteImages(tx, ref)
	if _, err := deleteNotesByID(tx, []int{noteID}); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	cleanupNoteAttachmentFiles(attachmentPaths)
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func decodeJSONObject(w http.ResponseWriter, r *http.Request, message string) (map[string]any, bool) {
	var payload map[string]any
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil || payload == nil {
		writeError(w, http.StatusBadRequest, message)
		return nil, false
	}
	return payload, true
}

func stringField(payload map[string]any, key string) string {
	value, _ := payload[key].(string)
	return value
}

func defaultStringField(payload map[string]any, key, fallback string) string {
	if value, ok := payload[key].(string); ok {
		return value
	}
	return fallback
}

func nullableStringArg(payload map[string]any, key string) any {
	value, ok := payload[key]
	if !ok || value == nil {
		return nil
	}
	if text, ok := value.(string); ok {
		return text
	}
	return nil
}

func intField(payload map[string]any, key string) (int, bool) {
	value, ok := payload[key]
	if !ok || value == nil {
		return 0, false
	}
	switch v := value.(type) {
	case float64:
		if v == math.Trunc(v) {
			return int(v), true
		}
	case int:
		return v, true
	}
	return 0, false
}

func nullableIntArg(value int, ok bool) any {
	if !ok {
		return nil
	}
	return value
}

func boolIntField(payload map[string]any, key string) int {
	if value, ok := payload[key].(bool); ok && value {
		return 1
	}
	return 0
}

func boolField(payload map[string]any, key string) bool {
	value, _ := payload[key].(bool)
	return value
}

func stringArrayField(payload map[string]any, key string) []string {
	raw, ok := payload[key]
	if !ok || raw == nil {
		return nil
	}
	items, ok := raw.([]any)
	if !ok {
		return nil
	}
	out := []string{}
	for _, item := range items {
		if text, ok := item.(string); ok {
			out = append(out, text)
		}
	}
	return out
}

func intArrayField(payload map[string]any, key string) ([]int, bool) {
	raw, ok := payload[key]
	if !ok || raw == nil {
		return nil, false
	}
	items, ok := raw.([]any)
	if !ok {
		return nil, false
	}
	out := []int{}
	for _, item := range items {
		value, ok := item.(float64)
		if !ok || value != math.Trunc(value) {
			return nil, false
		}
		out = append(out, int(value))
	}
	return out, true
}

func requiredIntArrayField(w http.ResponseWriter, payload map[string]any, key, requiredMessage string) ([]int, bool) {
	raw, ok := payload[key]
	if !ok || raw == nil {
		writeError(w, http.StatusBadRequest, requiredMessage)
		return nil, false
	}
	items, ok := raw.([]any)
	if !ok {
		writeError(w, http.StatusBadRequest, key+" must be a non-empty array")
		return nil, false
	}
	if len(items) == 0 {
		writeError(w, http.StatusBadRequest, requiredMessage)
		return nil, false
	}
	out := make([]int, 0, len(items))
	for _, item := range items {
		value, ok := item.(float64)
		if !ok || value != math.Trunc(value) {
			writeError(w, http.StatusBadRequest, "All "+key+" must be integers")
			return nil, false
		}
		out = append(out, int(value))
	}
	return out, true
}

func marshalJSONField(payload map[string]any, key string) (any, error) {
	value, ok := payload[key]
	if !ok || value == nil {
		return nil, nil
	}
	if _, ok := value.(map[string]any); !ok {
		return nil, nil
	}
	encoded, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	return pythonStyleJSONSpacing(encoded), nil
}

func pythonStyleJSONSpacing(encoded []byte) string {
	var builder strings.Builder
	builder.Grow(len(encoded) + 8)
	inString := false
	escaped := false
	for _, b := range encoded {
		builder.WriteByte(b)
		if inString {
			if escaped {
				escaped = false
				continue
			}
			if b == '\\' {
				escaped = true
				continue
			}
			if b == '"' {
				inString = false
			}
			continue
		}
		if b == '"' {
			inString = true
			continue
		}
		if b == ':' || b == ',' {
			builder.WriteByte(' ')
		}
	}
	return builder.String()
}

func autoNoteTitle(content string) string {
	first := strings.TrimSpace(strings.Split(content, "\n")[0])
	first = strings.TrimSpace(strings.TrimLeft(first, "#>-*"))
	if first != "" {
		runes := []rune(first)
		if len(runes) > 50 {
			return string(runes[:50]) + "..."
		}
		return first
	}
	return "Note - " + time.Now().Format("2006/01/02 15:04")
}

func replaceNoteTags(tx *sql.Tx, noteID int, tags []string, clearExisting bool) error {
	if clearExisting {
		if _, err := tx.Exec("DELETE FROM Note_Tags WHERE note_id = ?", noteID); err != nil {
			return err
		}
	}
	_, err := appendNoteTags(tx, noteID, tags)
	return err
}

func appendNoteTags(tx *sql.Tx, noteID int, tags []string) (int, error) {
	added := 0
	for _, tagName := range tags {
		tagName = strings.TrimSpace(tagName)
		if tagName == "" {
			continue
		}
		var tagID int
		if err := tx.QueryRow("SELECT id FROM Tags WHERE name = ? COLLATE NOCASE", tagName).Scan(&tagID); err != nil {
			if !errors.Is(err, sql.ErrNoRows) {
				return added, err
			}
			result, err := tx.Exec("INSERT INTO Tags (name) VALUES (?)", tagName)
			if err != nil {
				return added, err
			}
			newID, err := result.LastInsertId()
			if err != nil {
				return added, err
			}
			tagID = int(newID)
		}
		result, err := tx.Exec("INSERT OR IGNORE INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", noteID, tagID)
		if err != nil {
			return added, err
		}
		if rows, _ := result.RowsAffected(); rows > 0 {
			added++
		}
	}
	return added, nil
}

func replaceNoteURLs(tx *sql.Tx, noteID int, urls []string) error {
	if _, err := tx.Exec("DELETE FROM Source_Urls WHERE note_id = ?", noteID); err != nil {
		return err
	}
	for _, sourceURL := range urls {
		sourceURL = strings.TrimSpace(sourceURL)
		if sourceURL == "" {
			continue
		}
		if _, err := tx.Exec("INSERT INTO Source_Urls (note_id, url) VALUES (?, ?)", noteID, sourceURL); err != nil {
			return err
		}
	}
	return nil
}

func deleteNotesByID(tx *sql.Tx, noteIDs []int) (int, error) {
	if len(noteIDs) == 0 {
		return 0, nil
	}
	ids := intsToAny(noteIDs)
	inClause := placeholders(len(noteIDs))
	for _, table := range []string{"Note_Tags", "Source_Urls", "Note_History", "Note_Attachments"} {
		if _, err := tx.Exec("DELETE FROM "+table+" WHERE note_id IN ("+inClause+")", ids...); err != nil {
			return 0, err
		}
	}
	result, err := tx.Exec("DELETE FROM Notes WHERE id IN ("+inClause+")", ids...)
	if err != nil {
		return 0, err
	}
	rows, _ := result.RowsAffected()
	return int(rows), nil
}
