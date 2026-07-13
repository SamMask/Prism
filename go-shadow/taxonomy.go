package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"strings"
)

func defaultCategoryIDTx(tx *sql.Tx) (int, error) {
	var id int
	err := tx.QueryRow("SELECT id FROM Categories WHERE is_default = 1 LIMIT 1").Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, nil
	}
	return id, err
}

var errCategoryLabelConflict = errors.New("category label conflict")

func categoryLabelConflictTx(tx *sql.Tx, categoryID int, label string) error {
	label = strings.TrimSpace(label)
	if label == "" {
		return nil
	}
	var duplicateID int
	err := tx.QueryRow(`
		SELECT id FROM Categories
		WHERE id != ? AND (name = ? OR name_override = ?)
		LIMIT 1`, categoryID, label, label).Scan(&duplicateID)
	if err == nil {
		return errCategoryLabelConflict
	}
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	return err
}

func categoryIDForNameTx(tx *sql.Tx, name string) (int, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return 0, nil
	}
	var id int
	err := tx.QueryRow("SELECT id FROM Categories WHERE name = ? OR name_override = ? LIMIT 1", name, name).Scan(&id)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, nil
	}
	return id, err
}

func (s *server) handleCategories(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		if !s.runtime.enableCategoryWrite {
			writeError(w, http.StatusMethodNotAllowed, "Category write route is disabled")
			return
		}
		s.createCategory(w, r)
		return
	}
	if !requireGET(w, r) {
		return
	}
	rows, err := s.db.Query(`
		SELECT c.id, c.name, c.icon, c.sort_order, c.is_default, c.system_key, c.name_override,
		       (SELECT COUNT(*) FROM Notes n WHERE n.category_id = c.id) AS count
		FROM Categories c
		ORDER BY c.sort_order ASC`)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	items := []response{}
	for rows.Next() {
		var id, sortOrder, isDefault, count int
		var name, icon, systemKey, nameOverride sql.NullString
		if err := rows.Scan(&id, &name, &icon, &sortOrder, &isDefault, &systemKey, &nameOverride, &count); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		items = append(items, response{
			"id": id, "name": nullableString(name), "icon": nullableString(icon), "sort_order": sortOrder,
			"is_default": isDefault != 0, "system_key": nullableStringOrNil(systemKey),
			"name_override": nullableStringOrNil(nameOverride), "count": count,
		})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": items})
}

func (s *server) handleCategoryDetail(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/api/categories/")
	categoryID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if r.Method != http.MethodPut && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "PUT, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableCategoryWrite {
		writeError(w, http.StatusMethodNotAllowed, "Category write route is disabled")
		return
	}
	if r.Method == http.MethodDelete {
		s.deleteCategory(w, r, categoryID)
		return
	}
	s.updateCategory(w, r, categoryID)
}

func (s *server) createCategory(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "Category name is required")
	if !ok {
		return
	}
	rawName, ok := payload["name"].(string)
	if !ok || rawName == "" {
		writeError(w, http.StatusBadRequest, "Category name is required")
		return
	}
	name := strings.TrimSpace(rawName)
	icon, hasIcon := payload["icon"]
	if !hasIcon || icon == nil {
		icon = "📁"
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var duplicateID int
	if err := tx.QueryRow("SELECT id FROM Categories WHERE name = ? OR name_override = ? LIMIT 1", name, name).Scan(&duplicateID); err == nil {
		writeError(w, http.StatusConflict, "Category name already exists")
		return
	} else if !errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	var sortOrder any
	if value, ok := intField(payload, "sort_order"); ok {
		sortOrder = value
	} else {
		if err := tx.QueryRow("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM Categories").Scan(&sortOrder); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}

	result, err := tx.Exec("INSERT INTO Categories (name, icon, sort_order, is_default, system_key, name_override) VALUES (?, ?, ?, 0, NULL, NULL)", name, icon, sortOrder)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	newID, err := result.LastInsertId()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusCreated, response{"status": "success", "data": response{"id": int(newID)}})
}

func (s *server) updateCategory(w http.ResponseWriter, r *http.Request, categoryID int) {
	var payload map[string]any
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil || len(payload) == 0 {
		writeError(w, http.StatusBadRequest, "Request body is required")
		return
	}
	if _, ok := payload["system_key"]; ok {
		writeError(w, http.StatusBadRequest, "Category system_key cannot be changed")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var oldName string
	var systemKey, oldNameOverride sql.NullString
	if err := tx.QueryRow("SELECT name, system_key, name_override FROM Categories WHERE id = ?", categoryID).Scan(&oldName, &systemKey, &oldNameOverride); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Category not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	newName := oldName
	hasName := false
	if rawName, ok := payload["name"]; ok {
		hasName = true
		name, ok := rawName.(string)
		if !ok {
			writeError(w, http.StatusBadRequest, "category name must be a string")
			return
		}
		newName = strings.TrimSpace(name)
	}

	icon, hasIcon := payload["icon"]
	if hasIcon && icon == nil {
		hasIcon = false
	}
	sortOrder, hasSortOrder := payload["sort_order"]
	if value, ok := intField(payload, "sort_order"); ok {
		sortOrder = value
		hasSortOrder = true
	}
	if hasSortOrder && sortOrder == nil {
		hasSortOrder = false
	}

	assignments := []string{}
	args := []any{}

	if strings.TrimSpace(systemKey.String) == "" {
		if hasName {
			if newName == "" {
				writeError(w, http.StatusBadRequest, "Category name cannot be empty")
				return
			}
			if newName != oldName {
				if err := categoryLabelConflictTx(tx, categoryID, newName); err != nil {
					if errors.Is(err, errCategoryLabelConflict) {
						writeError(w, http.StatusConflict, "Category name already exists")
						return
					}
					writeError(w, http.StatusInternalServerError, err.Error())
					return
				}
				assignments = append(assignments, "name = ?")
				args = append(args, newName)
			}
		}
	} else {
		overrideChanged := false
		var overrideArg any
		if rawOverride, ok := payload["name_override"]; ok {
			overrideChanged = true
			if rawOverride != nil {
				overrideText, ok := rawOverride.(string)
				if !ok {
					writeError(w, http.StatusBadRequest, "category name_override must be a string or null")
					return
				}
				overrideText = strings.TrimSpace(overrideText)
				if overrideText != "" {
					overrideArg = overrideText
				}
			}
		} else if hasName && newName != oldName {
			if newName == "" {
				writeError(w, http.StatusBadRequest, "Category name cannot be empty")
				return
			}
			overrideChanged = true
			overrideArg = newName
		}
		if overrideChanged {
			if overrideText, ok := overrideArg.(string); ok {
				if err := categoryLabelConflictTx(tx, categoryID, overrideText); err != nil {
					if errors.Is(err, errCategoryLabelConflict) {
						writeError(w, http.StatusConflict, "Category name already exists")
						return
					}
					writeError(w, http.StatusInternalServerError, err.Error())
					return
				}
			}
			currentOverride := any(nil)
			if oldNameOverride.Valid && strings.TrimSpace(oldNameOverride.String) != "" {
				currentOverride = strings.TrimSpace(oldNameOverride.String)
			}
			if currentOverride != overrideArg {
				assignments = append(assignments, "name_override = ?")
				args = append(args, overrideArg)
			}
		}
	}
	if hasIcon {
		assignments = append(assignments, "icon = ?")
		args = append(args, icon)
	}
	if hasSortOrder {
		assignments = append(assignments, "sort_order = ?")
		args = append(args, sortOrder)
	}
	if len(assignments) == 0 {
		writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"updated_notes_count": 0}})
		return
	}
	args = append(args, categoryID)
	_, err = tx.Exec("UPDATE Categories SET "+strings.Join(assignments, ", ")+" WHERE id = ?", args...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"updated_notes_count": 0}})
}

func (s *server) deleteCategory(w http.ResponseWriter, r *http.Request, categoryID int) {
	payload := map[string]any{}
	if r.Body != nil {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if strings.TrimSpace(string(body)) != "" {
			if err := json.Unmarshal(body, &payload); err != nil {
				writeError(w, http.StatusBadRequest, "Invalid JSON body")
				return
			}
		}
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var isDefault int
	if err := tx.QueryRow("SELECT COALESCE(is_default, 0) FROM Categories WHERE id = ?", categoryID).Scan(&isDefault); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Category not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if isDefault != 0 {
		writeError(w, http.StatusBadRequest, "Cannot delete the default category")
		return
	}

	var notesCount int
	if err := tx.QueryRow("SELECT COUNT(*) FROM Notes WHERE category_id = ?", categoryID).Scan(&notesCount); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	targetCategoryID, hasTargetCategoryID := intField(payload, "target_category_id")
	if _, ok := payload["target_category_id"]; ok && !hasTargetCategoryID {
		writeError(w, http.StatusBadRequest, "target_category_id must be an integer")
		return
	}
	if notesCount > 0 && (!hasTargetCategoryID || targetCategoryID == 0) {
		writeJSON(w, http.StatusBadRequest, response{
			"status":      "error",
			"message":     "Target category required",
			"notes_count": notesCount,
		})
		return
	}
	if hasTargetCategoryID && targetCategoryID == categoryID {
		writeError(w, http.StatusBadRequest, "Target category cannot be the category being deleted")
		return
	}
	if hasTargetCategoryID && targetCategoryID != 0 {
		var targetExists int
		if err := tx.QueryRow("SELECT id FROM Categories WHERE id = ?", targetCategoryID).Scan(&targetExists); err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				writeError(w, http.StatusNotFound, "Target category not found")
				return
			}
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
	}

	migratedCount := int64(0)
	if notesCount > 0 && targetCategoryID != 0 {
		result, err := tx.Exec("UPDATE Notes SET category_id = ? WHERE category_id = ?", targetCategoryID, categoryID)
		if err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		migratedCount, _ = result.RowsAffected()
	}
	if _, err := tx.Exec("DELETE FROM Categories WHERE id = ?", categoryID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"migrated_notes_count": int(migratedCount)}})
}

func (s *server) handleTags(w http.ResponseWriter, r *http.Request) {
	if !requireGET(w, r) {
		return
	}
	rows, err := s.db.Query(`
		SELECT t.id, t.name, COUNT(nt.note_id) AS count
		FROM Tags t
		LEFT JOIN Note_Tags nt ON t.id = nt.tag_id
		GROUP BY t.id
		ORDER BY t.name`)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer rows.Close()

	items := []response{}
	for rows.Next() {
		var id, count int
		var name string
		if err := rows.Scan(&id, &name, &count); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		items = append(items, response{"id": id, "name": name, "count": count})
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": items})
}

func (s *server) handleTagDetail(w http.ResponseWriter, r *http.Request) {
	idText := strings.TrimPrefix(r.URL.Path, "/api/tags/")
	if idText == "merge" {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !s.runtime.enableTagWrite {
			writeError(w, http.StatusMethodNotAllowed, "Tag write route is disabled")
			return
		}
		s.mergeTags(w, r)
		return
	}
	tagID, err := strconv.Atoi(idText)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	if r.Method != http.MethodPut && r.Method != http.MethodDelete {
		w.Header().Set("Allow", "PUT, DELETE")
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !s.runtime.enableTagWrite {
		writeError(w, http.StatusMethodNotAllowed, "Tag write route is disabled")
		return
	}
	if r.Method == http.MethodDelete {
		s.deleteTag(w, tagID)
		return
	}
	s.renameTag(w, r, tagID)
}

func (s *server) renameTag(w http.ResponseWriter, r *http.Request, tagID int) {
	var payload map[string]any
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		writeError(w, http.StatusBadRequest, "Tag name is required")
		return
	}
	rawName, ok := payload["name"].(string)
	if !ok || rawName == "" {
		writeError(w, http.StatusBadRequest, "Tag name is required")
		return
	}
	newName := strings.TrimSpace(rawName)
	if newName == "" {
		writeError(w, http.StatusBadRequest, "Tag name cannot be empty")
		return
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var existingID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE id = ?", tagID).Scan(&existingID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Tag not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	var duplicateID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE name = ? COLLATE NOCASE AND id != ?", newName, tagID).Scan(&duplicateID); err == nil {
		writeError(w, http.StatusConflict, "Tag name already exists")
		return
	} else if !errors.Is(err, sql.ErrNoRows) {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	result, err := tx.Exec("UPDATE Tags SET name = ? WHERE id = ?", newName, tagID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	affected, err := result.RowsAffected()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if affected != 1 {
		writeError(w, http.StatusNotFound, "Tag not found")
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func (s *server) deleteTag(w http.ResponseWriter, tagID int) {
	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var existingID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE id = ?", tagID).Scan(&existingID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Tag not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("DELETE FROM Note_Tags WHERE tag_id = ?", tagID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if _, err := tx.Exec("DELETE FROM Tags WHERE id = ?", tagID); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success"})
}

func (s *server) mergeTags(w http.ResponseWriter, r *http.Request) {
	payload, ok := decodeJSONObject(w, r, "source_tag_ids and target_tag_id are required")
	if !ok {
		return
	}
	sourceRaw, hasSourceIDs := payload["source_tag_ids"]
	targetTagID, hasTargetTagID := intField(payload, "target_tag_id")
	if !hasSourceIDs || sourceRaw == nil || !hasTargetTagID || targetTagID == 0 {
		writeError(w, http.StatusBadRequest, "source_tag_ids and target_tag_id are required")
		return
	}
	if rawList, ok := sourceRaw.([]any); ok && len(rawList) == 0 {
		writeError(w, http.StatusBadRequest, "source_tag_ids and target_tag_id are required")
		return
	}
	sourceTagIDs, ok := intArrayField(payload, "source_tag_ids")
	if !ok || len(sourceTagIDs) == 0 {
		writeError(w, http.StatusBadRequest, "source_tag_ids must be a non-empty array")
		return
	}
	for _, sourceTagID := range sourceTagIDs {
		if sourceTagID == targetTagID {
			writeError(w, http.StatusBadRequest, "target_tag_id cannot be in source_tag_ids")
			return
		}
	}

	tx, err := s.db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer tx.Rollback()

	var targetID int
	if err := tx.QueryRow("SELECT id FROM Tags WHERE id = ?", targetTagID).Scan(&targetID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			writeError(w, http.StatusNotFound, "Target tag not found")
			return
		}
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	mergedCount := 0
	for _, sourceTagID := range sourceTagIDs {
		var sourceID int
		if err := tx.QueryRow("SELECT id FROM Tags WHERE id = ?", sourceTagID).Scan(&sourceID); err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				continue
			}
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if _, err := tx.Exec(`
			INSERT OR IGNORE INTO Note_Tags (note_id, tag_id)
			SELECT note_id, ? FROM Note_Tags WHERE tag_id = ?`, targetTagID, sourceTagID); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		if _, err := tx.Exec("DELETE FROM Tags WHERE id = ?", sourceTagID); err != nil {
			writeError(w, http.StatusInternalServerError, err.Error())
			return
		}
		mergedCount++
	}
	if err := tx.Commit(); err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, response{"status": "success", "data": response{"merged_count": mergedCount}})
}
