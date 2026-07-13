package main

import (
	"database/sql"
	"log"
	"os"
	"path"
	"path/filepath"
	"strings"
)

func (s *server) noteAttachmentCleanupPaths(tx *sql.Tx, noteIDs []int) ([]string, error) {
	if len(noteIDs) == 0 || strings.TrimSpace(s.runtime.dataDir) == "" {
		return nil, nil
	}
	rows, err := tx.Query("SELECT file_path FROM Note_Attachments WHERE note_id IN ("+placeholders(len(noteIDs))+")", intsToAny(noteIDs)...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	candidates := []string{}
	for rows.Next() {
		var filePath sql.NullString
		if err := rows.Scan(&filePath); err != nil {
			return nil, err
		}
		if cleaned, ok := noteAttachmentCleanupRelativePath(nullableString(filePath)); ok {
			candidates = append(candidates, cleaned)
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	referenced, err := noteAttachmentReferenceCounts(tx, noteIDs)
	if err != nil {
		return nil, err
	}
	paths := []string{}
	for _, relativePath := range uniqueStrings(candidates) {
		if referenced[relativePath] > 0 {
			continue
		}
		if resolved, ok := resolveNoteAttachmentCleanupPath(s.runtime.dataDir, relativePath); ok {
			paths = append(paths, resolved)
		}
	}
	return uniqueStrings(paths), nil
}

func noteAttachmentReferenceCounts(tx *sql.Tx, excludedNoteIDs []int) (map[string]int, error) {
	referenced := map[string]int{}
	if len(excludedNoteIDs) == 0 {
		return referenced, nil
	}
	rows, err := tx.Query("SELECT file_path FROM Note_Attachments WHERE note_id NOT IN ("+placeholders(len(excludedNoteIDs))+")", intsToAny(excludedNoteIDs)...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var filePath sql.NullString
		if err := rows.Scan(&filePath); err != nil {
			return nil, err
		}
		if cleaned, ok := noteAttachmentCleanupRelativePath(nullableString(filePath)); ok {
			referenced[cleaned]++
		}
	}
	return referenced, rows.Err()
}

func noteAttachmentCleanupRelativePath(relativePath string) (string, bool) {
	relativePath = strings.TrimSpace(strings.ReplaceAll(relativePath, "\\", "/"))
	if relativePath == "" || filepath.IsAbs(relativePath) || filepath.VolumeName(relativePath) != "" || strings.Contains(relativePath, ":") {
		return "", false
	}
	cleaned := path.Clean(relativePath)
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return "", false
	}
	if strings.HasPrefix(cleaned, "docs/attachments/") || strings.HasPrefix(cleaned, "docs/notes/") {
		return cleaned, true
	}
	return "", false
}

func resolveNoteAttachmentCleanupPath(dataDir, relativePath string) (string, bool) {
	if strings.TrimSpace(dataDir) == "" {
		return "", false
	}
	cleaned, ok := noteAttachmentCleanupRelativePath(relativePath)
	if !ok {
		return "", false
	}
	if strings.HasPrefix(cleaned, "docs/notes/") {
		return resolveAutoExtractedNotePath(dataDir, cleaned)
	}
	root, err := filepath.Abs(dataDir)
	if err != nil {
		return "", false
	}
	evaluatedRoot, err := filepath.EvalSymlinks(root)
	if err != nil {
		return "", false
	}
	candidate := filepath.Join(root, filepath.FromSlash(cleaned))
	absCandidate, err := filepath.Abs(candidate)
	if err != nil || !isSubpath(absCandidate, root) {
		return "", false
	}
	info, err := os.Lstat(absCandidate)
	if err != nil || !info.Mode().IsRegular() {
		return "", false
	}
	resolved, err := filepath.EvalSymlinks(absCandidate)
	if err != nil || !isSubpath(resolved, evaluatedRoot) {
		return "", false
	}
	return resolved, true
}

func cleanupNoteAttachmentFiles(paths []string) {
	for _, filePath := range uniqueStrings(paths) {
		if err := os.Remove(filePath); err != nil && !os.IsNotExist(err) {
			log.Printf("note attachment cleanup skipped file %s: %v", filePath, err)
		}
	}
}

func noteImageReferences(tx *sql.Tx, noteIDs []int) ([]noteImageReference, error) {
	if len(noteIDs) == 0 {
		return nil, nil
	}
	rows, err := tx.Query("SELECT id, content, cover_image FROM Notes WHERE id IN ("+placeholders(len(noteIDs))+") ORDER BY id", intsToAny(noteIDs)...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	refs := []noteImageReference{}
	for rows.Next() {
		var ref noteImageReference
		if err := rows.Scan(&ref.ID, &ref.Content, &ref.CoverImage); err != nil {
			return nil, err
		}
		refs = append(refs, ref)
	}
	return refs, rows.Err()
}

func (s *server) cleanupNoteImages(tx *sql.Tx, ref noteImageReference) {
	for _, imagePath := range staticUploadReferences(ref.Content, ref.CoverImage) {
		var refCount int
		err := tx.QueryRow(`
			SELECT COUNT(*) FROM Notes
			WHERE id != ? AND (cover_image = ? OR content LIKE ?)
		`, ref.ID, imagePath, "%"+imagePath+"%").Scan(&refCount)
		if err != nil {
			log.Printf("note image cleanup skipped reference count for note %d path %s: %v", ref.ID, imagePath, err)
			continue
		}
		if refCount > 0 {
			continue
		}
		for _, filename := range cleanupUploadFilenames(imagePath) {
			absPath, ok := s.resolveUploadFile(filename)
			if !ok {
				continue
			}
			if err := os.Remove(absPath); err != nil && !os.IsNotExist(err) {
				log.Printf("note image cleanup skipped file %s: %v", absPath, err)
			}
		}
	}
}

func (s *server) previewNoteImageCleanupFiles(tx *sql.Tx, refs []noteImageReference) ([]string, error) {
	files := []string{}
	for _, ref := range refs {
		for _, imagePath := range staticUploadReferences(ref.Content, ref.CoverImage) {
			var refCount int
			err := tx.QueryRow(`
				SELECT COUNT(*) FROM Notes
				WHERE id != ? AND (cover_image = ? OR content LIKE ?)
			`, ref.ID, imagePath, "%"+imagePath+"%").Scan(&refCount)
			if err != nil {
				return nil, err
			}
			if refCount > 0 {
				continue
			}
			for _, filename := range cleanupUploadFilenames(imagePath) {
				absPath, ok := s.resolveUploadFile(filename)
				if !ok {
					continue
				}
				if fileExists(absPath) {
					files = append(files, absPath)
				}
			}
		}
	}
	return uniqueStrings(files), nil
}
