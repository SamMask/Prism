package main

import (
	"bytes"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

// PRISM-OPT-20: one manual maintenance action that merges auto-extracted long notes (full text
// in docs/notes/note_<id>.md, a generated preview in Notes.content) back into the database.
// Dry-run by default; execution takes a consistent restore point first and moves files into
// backups/separated-notes-<ts>/ instead of deleting them. Anything it cannot prove safe is
// listed and left untouched.

const (
	inlineNotesBodyLimit   = 1 << 20
	inlineQuarantinePrefix = "separated-notes-"
	inlineHistorySummary   = "合併長文：保留附件全文"
)

var inlineStandardNoteName = regexp.MustCompile(`(?i)^note_([0-9]+)\.(md|markdown|txt)$`)

var inlineSkipReasons = []string{
	"missing_file", "dangling_row", "too_large", "preview_mismatch", "invalid_path", "unsafe_path",
	"nonstandard_path", "shared_file", "identity_unverified", "unreadable", "multiple_auto_rows",
	"note_missing", "media_unprotected", "changed_during_run",
}

// statOpenFile returns the identity of an open file. On Windows File.Stat reads the volume
// serial and file index from the handle right away, while os.Stat defers them until
// os.SameFile, which then reports false when it cannot load them. Tests replace it to inject
// identity failures.
var statOpenFile = func(f *os.File) (os.FileInfo, error) { return f.Stat() }

func openFileIdentity(path string) (os.FileInfo, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return statOpenFile(f)
}

type identityError struct{ err error }

func (e *identityError) Error() string { return "file identity unavailable: " + e.err.Error() }

// readFileWithIdentity reads at most limit+1 bytes and the identity from the same handle, so
// the identity describes exactly the bytes that were read.
func readFileWithIdentity(path string, limit int64) ([]byte, os.FileInfo, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()
	info, err := statOpenFile(f)
	if err != nil {
		return nil, nil, &identityError{err}
	}
	data, err := io.ReadAll(io.LimitReader(f, limit+1))
	if err != nil {
		return nil, nil, err
	}
	return data, info, nil
}

func (s *server) fireTestHook(stage string, noteID int) error {
	if s.testHook == nil {
		return nil
	}
	return s.testHook(stage, noteID)
}

type inlineRow struct {
	id, noteID       int
	filePath         string
	auto, noteExists bool
	title, content   string
}

type inlineIdentity struct {
	info os.FileInfo
	err  error
}

type inlineCandidate struct {
	noteID, attachmentID int
	title, filePath      string
	rel, source          string
	action, dbContent    string
	data                 []byte
	identity             os.FileInfo
}

type inlineSkip struct {
	noteID, attachmentID int
	title, filePath      string
	reason, detail       string
	size                 int64
}

type inlinePlan struct {
	dataRoot   string
	candidates []inlineCandidate
	skipped    []inlineSkip
	orphans    []response
	shared     []response
	unverified []response
	fileRefs   map[string][]string
}

func (s *server) handleInlineSeparatedNotes(w http.ResponseWriter, r *http.Request) {
	if !requireMethod(w, r, http.MethodPost) || !requireLocalhostRequest(w, r) || !s.requireServerSystem(w, r) {
		return
	}
	dryRun, err := parseInlineDryRun(r.Body)
	if err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	// The report is built under noteFilesMu; it is written only after the lock is released.
	status, payload := s.runInlineSeparatedNotes(dryRun)
	writeJSON(w, status, payload)
}

// parseInlineDryRun accepts an empty body or one JSON object. Only an explicit boolean false
// executes; a missing or null dry_run means a dry-run. Oversized bodies, duplicate dry_run
// keys and trailing data are rejected.
func parseInlineDryRun(body io.Reader) (bool, error) {
	data, err := io.ReadAll(io.LimitReader(body, inlineNotesBodyLimit+1))
	if err != nil {
		return true, errors.New("Invalid request body")
	}
	if len(data) > inlineNotesBodyLimit {
		return true, errors.New("Request body too large")
	}
	if len(bytes.TrimSpace(data)) == 0 {
		return true, nil
	}
	invalid := errors.New("Request body must be a JSON object")
	dec := json.NewDecoder(bytes.NewReader(data))
	if tok, err := dec.Token(); err != nil || tok != json.Delim('{') {
		return true, invalid
	}
	var raw json.RawMessage
	seen := false
	for dec.More() {
		tok, err := dec.Token()
		key, ok := tok.(string)
		if err != nil || !ok {
			return true, invalid
		}
		var value json.RawMessage
		if err := dec.Decode(&value); err != nil {
			return true, invalid
		}
		if key == "dry_run" {
			if seen {
				return true, errors.New("dry_run must appear only once")
			}
			seen, raw = true, value
		}
	}
	if tok, err := dec.Token(); err != nil || tok != json.Delim('}') {
		return true, invalid
	}
	if _, err := dec.Token(); err != io.EOF {
		return true, invalid
	}
	switch strings.TrimSpace(string(raw)) {
	case "", "null", "true":
		return true, nil
	case "false":
		return false, nil
	}
	return true, errors.New("dry_run must be a boolean")
}

func (s *server) runInlineSeparatedNotes(dryRun bool) (int, response) {
	s.noteFilesMu.Lock()
	defer s.noteFilesMu.Unlock()
	plan, err := s.classifySeparatedNotes()
	if err != nil {
		return inlineNothingChanged(err)
	}
	report := plan.report(dryRun)
	if dryRun || len(plan.candidates) == 0 {
		return http.StatusOK, response{"status": "success", "data": report}
	}
	return s.executeInlinePlan(plan, report)
}

func inlineNothingChanged(err error) (int, response) {
	return http.StatusInternalServerError, response{
		"status":        "error",
		"message":       "Inline separated notes stopped before changing any note; no notes were changed: " + err.Error(),
		"notes_changed": 0,
	}
}

// realDirChain reports whether every component below root is a real directory: no symlink,
// no junction (Lstat reports Windows junctions as ModeIrregular), nothing else.
func realDirChain(root string, parts ...string) bool {
	current := root
	for _, part := range parts {
		current = filepath.Join(current, part)
		info, err := os.Lstat(current)
		if err != nil || !info.IsDir() || info.Mode()&(os.ModeSymlink|os.ModeIrregular) != 0 {
			return false
		}
	}
	return true
}

func (s *server) inlineDataRoot() (string, error) {
	abs, err := filepath.Abs(s.runtime.dataDir)
	if err != nil {
		return "", err
	}
	return filepath.EvalSymlinks(abs)
}

type inlineSource struct {
	rel, source string
	data        []byte
	identity    os.FileInfo
}

// inspectSeparatedNoteSource checks one auto row against the conservative auto-processing
// boundary: docs/notes/note_<own id>.<md|markdown|txt>, real directories all the way, a regular
// file physically inside docs/notes, at most maxAttachmentFileBytes of UTF-8. It returns the
// bytes and the identity read from one handle, or a reason ("missing" for an absent file).
func (s *server) inspectSeparatedNoteSource(root string, noteID int, filePath string) (inlineSource, string, string) {
	var src inlineSource
	cleaned, ok := noteAttachmentCleanupRelativePath(filePath)
	if !ok || !strings.HasPrefix(cleaned, "docs/notes/") {
		return src, "invalid_path", ""
	}
	name := strings.TrimPrefix(cleaned, "docs/notes/")
	match := inlineStandardNoteName.FindStringSubmatch(name)
	if strings.Contains(name, "/") || match == nil || match[1] != strconv.Itoa(noteID) {
		return src, "nonstandard_path", "outside the automatic note_<id> naming; handle manually"
	}
	if !realDirChain(root, "docs", "notes") {
		return src, "unsafe_path", "docs/notes is not a real directory"
	}
	notesDir := filepath.Join(root, "docs", "notes")
	source := filepath.Join(notesDir, name)
	info, err := os.Lstat(source)
	if err != nil {
		if os.IsNotExist(err) {
			return src, "missing", ""
		}
		return src, "unreadable", err.Error()
	}
	if !info.Mode().IsRegular() {
		return src, "unsafe_path", "not a regular file"
	}
	if info.Size() > maxAttachmentFileBytes {
		return src, "too_large", ""
	}
	data, identity, err := readFileWithIdentity(source, maxAttachmentFileBytes)
	if err != nil {
		var idErr *identityError
		switch {
		case errors.As(err, &idErr):
			return src, "identity_unverified", err.Error()
		case os.IsNotExist(err):
			return src, "missing", ""
		}
		return src, "unreadable", err.Error()
	}
	if int64(len(data)) > maxAttachmentFileBytes {
		return src, "too_large", ""
	}
	if !utf8.Valid(data) {
		return src, "unreadable", "not UTF-8"
	}
	if resolved, err := filepath.EvalSymlinks(source); err != nil || !isSubpath(resolved, notesDir) {
		return src, "unsafe_path", "resolves outside docs/notes"
	}
	return inlineSource{rel: "docs/notes/" + name, source: source, data: data, identity: identity}, "", ""
}

// inlineAction decides what may happen to a readable, unshared split note: "merge" when the
// DB holds the file text or its generated preview (banner + non-empty strict prefix, a
// heuristic: the DB text is derivable from the file), "history" when the DB holds other text
// without the banner (keep it, save the file text as a version), "" when the banner is there
// but the prefix does not match the file.
func inlineAction(dbContent string, data []byte) string {
	file := string(data)
	if normalizeTextContent(dbContent) == normalizeTextContent(file) || isAutoSeparatedPreview(dbContent, file) {
		return "merge"
	}
	if strings.HasSuffix(normalizeTextContent(dbContent), separatedPreviewBanner) {
		return ""
	}
	return "history"
}

func (s *server) classifySeparatedNotes() (*inlinePlan, error) {
	root, err := s.inlineDataRoot()
	if err != nil {
		return nil, err
	}
	tx, err := s.db.Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	rows, err := s.inlineAttachmentRows(tx)
	if err != nil {
		return nil, err
	}
	plan := &inlinePlan{dataRoot: root, fileRefs: map[string][]string{}}
	idents := attachmentIdentities(root, rows)
	for _, row := range rows {
		if ident, ok := idents[row.id]; ok && ident.err != nil && !os.IsNotExist(ident.err) {
			plan.unverified = append(plan.unverified, response{
				"attachment_id": row.id, "note_id": row.noteID, "file_path": row.filePath, "error": ident.err.Error(),
			})
		}
	}
	autoPerNote := map[int]int{}
	for _, row := range rows {
		if row.auto {
			autoPerNote[row.noteID]++
		}
	}
	historyRows := map[int]bool{}
	var history []inlineCandidate
	for _, row := range rows {
		if !row.auto {
			continue
		}
		skip := func(reason, detail string, size int64) {
			plan.skipped = append(plan.skipped, inlineSkip{row.noteID, row.id, row.title, row.filePath, reason, detail, size})
		}
		if !row.noteExists {
			skip("note_missing", "", -1)
			continue
		}
		if autoPerNote[row.noteID] > 1 {
			skip("multiple_auto_rows", "", -1)
			continue
		}
		src, reason, detail := s.inspectSeparatedNoteSource(root, row.noteID, row.filePath)
		if reason == "missing" {
			if strings.HasSuffix(normalizeTextContent(row.content), separatedPreviewBanner) {
				skip("missing_file", "", -1)
			} else {
				skip("dangling_row", "", -1)
			}
			continue
		}
		if reason != "" {
			skip(reason, detail, -1)
			continue
		}
		size := int64(len(src.data))
		if reason, matches := inlineShareReason(row, src.identity, rows, idents); reason != "" {
			if reason == "shared_file" {
				noteIDs, attachmentIDs := []int{row.noteID}, []int{row.id}
				for _, m := range matches {
					noteIDs = append(noteIDs, m.noteID)
					attachmentIDs = append(attachmentIDs, m.id)
				}
				plan.shared = append(plan.shared, response{"file_path": row.filePath, "note_ids": noteIDs, "attachment_ids": attachmentIDs})
			}
			skip(reason, "", size)
			continue
		}
		action := inlineAction(row.content, src.data)
		if action == "" {
			skip("preview_mismatch", "", size)
			continue
		}
		cand := inlineCandidate{
			noteID: row.noteID, attachmentID: row.id, title: row.title, filePath: row.filePath,
			rel: src.rel, source: src.source, action: action, dbContent: row.content,
			data: src.data, identity: src.identity,
		}
		if action == "history" {
			historyRows[row.id] = true
			history = append(history, cand)
			continue
		}
		plan.candidates = append(plan.candidates, cand)
	}
	if len(history) > 0 {
		// Every history action removes an auto row, so none of them may protect another's media.
		protected, err := s.referencedUploadFilenamesFrom(tx, historyRows, plan.fileRefs)
		if err != nil {
			return nil, err
		}
		for _, c := range history {
			if !mediaProtected(c.data, protected) {
				plan.skipped = append(plan.skipped, inlineSkip{c.noteID, c.attachmentID, c.title, c.filePath, "media_unprotected", "", int64(len(c.data))})
				continue
			}
			plan.candidates = append(plan.candidates, c)
		}
	}
	sort.Slice(plan.candidates, func(i, j int) bool { return plan.candidates[i].noteID < plan.candidates[j].noteID })
	plan.orphans = orphanSeparatedNoteFiles(root, rows, idents)
	return plan, nil
}

func (s *server) inlineAttachmentRows(q sqlQueryer) ([]inlineRow, error) {
	result, err := q.Query(`
		SELECT a.id, a.note_id, COALESCE(a.file_path, ''), COALESCE(a.is_auto_extracted, 0) = 1,
		       n.id IS NOT NULL, COALESCE(n.title, ''), COALESCE(n.content, '')
		FROM Note_Attachments a LEFT JOIN Notes n ON n.id = a.note_id
		ORDER BY a.note_id, a.id`)
	if err != nil {
		return nil, err
	}
	defer result.Close()
	rows := []inlineRow{}
	for result.Next() {
		var row inlineRow
		if err := result.Scan(&row.id, &row.noteID, &row.filePath, &row.auto, &row.noteExists, &row.title, &row.content); err != nil {
			return nil, err
		}
		rows = append(rows, row)
	}
	return rows, result.Err()
}

// attachmentIdentities opens every attachment row's file once per scan (handle-based identity,
// no name prefilter). Rows whose path no Prism resolver accepts cannot name a file and are
// skipped; a missing file (os.IsNotExist) cannot be an alias of anything.
func attachmentIdentities(root string, rows []inlineRow) map[int]inlineIdentity {
	byPath := map[string]inlineIdentity{}
	out := map[int]inlineIdentity{}
	for _, row := range rows {
		cleaned, ok := noteAttachmentCleanupRelativePath(row.filePath)
		if !ok {
			continue
		}
		ident, seen := byPath[cleaned]
		if !seen {
			info, err := openFileIdentity(filepath.Join(root, filepath.FromSlash(cleaned)))
			ident = inlineIdentity{info: info, err: err}
			byPath[cleaned] = ident
		}
		out[row.id] = ident
	}
	return out
}

// inlineShareReason: "shared_file" when another row has the same normalized path or a known
// identity equal to the candidate's; "identity_unverified" when another row's identity could
// not be read for a reason other than the file not existing.
func inlineShareReason(row inlineRow, identity os.FileInfo, rows []inlineRow, idents map[int]inlineIdentity) (string, []inlineRow) {
	cleaned, _ := noteAttachmentCleanupRelativePath(row.filePath)
	var matches []inlineRow
	unknown := false
	for _, other := range rows {
		if other.id == row.id {
			continue
		}
		otherCleaned, ok := noteAttachmentCleanupRelativePath(other.filePath)
		if !ok {
			continue
		}
		ident := idents[other.id]
		switch {
		case otherCleaned == cleaned, ident.err == nil && os.SameFile(identity, ident.info):
			matches = append(matches, other)
		case ident.err != nil && !os.IsNotExist(ident.err):
			unknown = true
		}
	}
	if len(matches) > 0 {
		return "shared_file", matches
	}
	if unknown {
		return "identity_unverified", nil
	}
	return "", nil
}

func orphanSeparatedNoteFiles(root string, rows []inlineRow, idents map[int]inlineIdentity) []response {
	orphans := []response{}
	if !realDirChain(root, "docs", "notes") {
		return orphans
	}
	notesDir := filepath.Join(root, "docs", "notes")
	entries, err := os.ReadDir(notesDir)
	if err != nil {
		return orphans
	}
	referenced := map[string]bool{}
	for _, row := range rows {
		if cleaned, ok := noteAttachmentCleanupRelativePath(row.filePath); ok {
			referenced[cleaned] = true
		}
	}
	for _, entry := range entries {
		if entry.Type()&os.ModeType != 0 {
			continue
		}
		rel := "docs/notes/" + entry.Name()
		if referenced[rel] {
			continue
		}
		if info, err := openFileIdentity(filepath.Join(notesDir, entry.Name())); err == nil && identityReferenced(info, idents) {
			continue
		}
		item := response{"file_path": rel, "size_bytes": nil, "modified_at": nil}
		if info, err := entry.Info(); err == nil {
			item["size_bytes"] = info.Size()
			item["modified_at"] = info.ModTime().UTC().Format(time.RFC3339)
		}
		orphans = append(orphans, item)
	}
	return orphans
}

func identityReferenced(info os.FileInfo, idents map[int]inlineIdentity) bool {
	for _, ident := range idents {
		if ident.err == nil && os.SameFile(info, ident.info) {
			return true
		}
	}
	return false
}

func uploadReferencesInText(text string) []string {
	refs := []string{}
	for _, match := range staticUploadReferencePattern.FindAllStringSubmatch(text, -1) {
		if len(match) > 1 {
			refs = append(refs, match[1])
		}
	}
	return refs
}

// mediaProtected reports whether every local upload the text references would still be
// protected from orphan cleanup by the given reference set (same rule as orphanUploadImages).
func mediaProtected(data []byte, referenced map[string]bool) bool {
	expanded := expandedUploadReferences(referenced)
	// Every spelling (as written and percent-decoded) must stay protected: either may be the file.
	for _, raw := range uploadReferencesInText(string(data)) {
		for _, spelling := range uploadReferenceSpellings(raw) {
			if name, ok := uploadReferenceFilename(spelling); ok && !uploadProtected(name, referenced, expanded) {
				return false
			}
		}
	}
	return true
}

func (p *inlinePlan) report(dryRun bool) response {
	merge, history := []response{}, []response{}
	for _, c := range p.candidates {
		item := response{"note_id": c.noteID, "title": c.title, "attachment_id": c.attachmentID, "file_path": c.filePath, "size_bytes": len(c.data)}
		if c.action == "merge" {
			merge = append(merge, item)
		} else {
			history = append(history, item)
		}
	}
	byReason := response{}
	for _, reason := range inlineSkipReasons {
		byReason[reason] = 0
	}
	skipped := []response{}
	for _, item := range p.skipped {
		byReason[item.reason] = byReason[item.reason].(int) + 1
		var size any
		if item.size >= 0 {
			size = item.size
		}
		skipped = append(skipped, response{
			"note_id": item.noteID, "title": item.title, "attachment_id": item.attachmentID,
			"file_path": item.filePath, "size_bytes": size, "reason": item.reason, "detail": item.detail,
		})
	}
	nonNil := func(items []response) []response {
		if items == nil {
			return []response{}
		}
		return items
	}
	return response{
		"dry_run": dryRun,
		"counts": response{
			"actionable": len(p.candidates), "merge": len(merge), "history": len(history),
			"merged": 0, "historied": 0, "move_failed": 0, "failed": 0,
			"skipped": len(skipped), "skipped_by_reason": byReason,
			"orphan_files": len(p.orphans), "shared_files": len(p.shared), "unverified_rows": len(p.unverified),
		},
		"merge": merge, "history": history, "results": []response{}, "skipped": skipped,
		"orphan_files": nonNil(p.orphans), "shared_files": nonNil(p.shared), "unverified_rows": nonNil(p.unverified),
		"aborted": false, "audit_error": "", "restore_point": nil, "quarantine_dir": nil,
	}
}

// createInlineQuarantineDir makes a fresh backups/separated-notes-<ts>/ after checking that
// backups is a real directory inside the data dir. Retention only touches top-level
// prism_backup_*.db files, so this folder is never deleted automatically.
func (s *server) createInlineQuarantineDir(root string) (string, error) {
	absData, err := filepath.Abs(s.runtime.dataDir)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(absData, s.runtime.backupsDir)
	if err != nil || rel == "." || strings.HasPrefix(rel, "..") {
		return "", errors.New("backups directory is not inside the data directory")
	}
	if !realDirChain(root, strings.Split(rel, string(filepath.Separator))...) {
		return "", errors.New("backups is not a real directory inside the data directory")
	}
	now := time.Now()
	qdir := filepath.Join(root, rel, fmt.Sprintf("%s%s_%09d", inlineQuarantinePrefix, now.Format("20060102_150405"), now.Nanosecond()))
	if err := os.Mkdir(qdir, 0755); err != nil {
		return "", err
	}
	return qdir, nil
}

func writeExclusiveFile(path string, data []byte) error {
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0644)
	if err != nil {
		return err
	}
	if _, err := f.Write(data); err != nil {
		f.Close()
		return err
	}
	if err := f.Sync(); err != nil {
		f.Close()
		return err
	}
	return f.Close()
}

func writeExclusiveJSON(path string, payload any) error {
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	return writeExclusiveFile(path, append(data, '\n'))
}

func sha256File(path string) (string, int64, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", 0, err
	}
	defer f.Close()
	h := sha256.New()
	n, err := io.Copy(h, f)
	if err != nil {
		return "", 0, err
	}
	return hex.EncodeToString(h.Sum(nil)), n, nil
}

func sha256Hex(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func (p *inlinePlan) relative(path string) string {
	rel, err := filepath.Rel(p.dataRoot, path)
	if err != nil {
		return filepath.ToSlash(path)
	}
	return filepath.ToSlash(rel)
}

func (s *server) executeInlinePlan(plan *inlinePlan, report response) (int, response) {
	qdir, err := s.createInlineQuarantineDir(plan.dataRoot)
	if err != nil {
		return inlineNothingChanged(err)
	}
	restorePoint := filepath.Join(qdir, "restore_point.db")
	if err := s.fireTestHook("before_restore_point", 0); err != nil {
		return inlineNothingChanged(err)
	}
	if err := s.writeConsistentDBBackup(restorePoint); err != nil {
		_ = os.Remove(qdir)
		return inlineNothingChanged(err)
	}
	restoreSHA, restoreSize, err := sha256File(restorePoint)
	if err != nil {
		return inlineNothingChanged(err)
	}
	if err := s.writeInlineManifests(plan, qdir, restoreSHA, restoreSize); err != nil {
		return inlineNothingChanged(err)
	}

	// Only history actions that are still pending can drop protecting references.
	historyRows := map[int]bool{}
	for _, c := range plan.candidates {
		if c.action == "history" {
			historyRows[c.attachmentID] = true
		}
	}
	counts := report["counts"].(response)
	byReason := counts["skipped_by_reason"].(response)
	results := []response{}
	aborted := false
	for _, c := range plan.candidates {
		var result response
		stop := false
		if err := s.fireTestHook("before_note", c.noteID); err != nil {
			result, stop = inlineResult(c), true
			result["status"], result["error"] = "failed", err.Error()
		} else {
			result, stop = s.inlineOneSeparatedNote(plan, qdir, c, historyRows)
		}
		results = append(results, result)
		switch result["status"] {
		case "merged":
			counts["merged"] = counts["merged"].(int) + 1
		case "historied":
			counts["historied"] = counts["historied"].(int) + 1
		case "failed":
			counts["failed"] = counts["failed"].(int) + 1
		case "skipped":
			reason := result["reason"].(string)
			byReason[reason] = byReason[reason].(int) + 1
			counts["skipped"] = counts["skipped"].(int) + 1
		}
		if result["move_error"] != "" {
			counts["move_failed"] = counts["move_failed"].(int) + 1
		}
		if stop {
			aborted = true
			break
		}
	}
	auditErr := ""
	if err := s.fireTestHook("before_result", 0); err != nil {
		auditErr = err.Error()
	} else if err := writeExclusiveJSON(filepath.Join(qdir, "result.json"), response{
		"format": "prism.separated_notes_inline.v1", "finished_at": time.Now().UTC().Format(time.RFC3339Nano),
		"aborted": aborted, "counts": counts, "items": results,
	}); err != nil {
		auditErr = err.Error()
	}
	report["dry_run"] = false
	report["results"] = results
	report["aborted"] = aborted
	report["audit_error"] = auditErr
	report["restore_point"] = plan.relative(restorePoint)
	report["quarantine_dir"] = plan.relative(qdir)
	return http.StatusOK, response{"status": "success", "data": report}
}

// writeInlineManifests writes the immutable plan.json and moves.tsv (tab-separated, for
// rollback checks with plain PowerShell or bash). Source and destination paths are always
// docs/notes/note_<id>.<ext>, so they never contain tabs, newlines or quotes.
func (s *server) writeInlineManifests(plan *inlinePlan, qdir, restoreSHA string, restoreSize int64) error {
	items := []response{}
	var tsv strings.Builder
	fmt.Fprintf(&tsv, "restore_point\t-\t%s\t-\trestore_point.db\n", restoreSHA)
	for _, c := range plan.candidates {
		row := response{}
		var noteID, auto int
		var filePath, fileType, title, createdAt sql.NullString
		var size sql.NullInt64
		var id int
		if err := s.db.QueryRow(`SELECT id, note_id, file_path, file_type, title, size_bytes, COALESCE(is_auto_extracted, 0), created_at
			FROM Note_Attachments WHERE id = ?`, c.attachmentID).Scan(&id, &noteID, &filePath, &fileType, &title, &size, &auto, &createdAt); err == nil {
			row = response{
				"id": id, "note_id": noteID, "file_path": nullableString(filePath), "file_type": nullableStringOrNil(fileType),
				"title": nullableStringOrNil(title), "size_bytes": nullableIntOrNil(size), "is_auto_extracted": auto,
				"created_at": nullableStringOrNil(createdAt),
			}
		}
		sum := sha256Hex(c.data)
		items = append(items, response{
			"action": c.action, "note_id": c.noteID, "attachment": row, "source": c.rel, "destination": c.rel,
			"sha256": sum, "size": len(c.data), "db_content_sha256": sha256Hex([]byte(c.dbContent)),
		})
		fmt.Fprintf(&tsv, "%s\t%d\t%s\t%s\t%s\n", c.action, c.noteID, sum, c.rel, c.rel)
	}
	if err := writeExclusiveJSON(filepath.Join(qdir, "plan.json"), response{
		"format": "prism.separated_notes_inline.v1", "created_at": time.Now().UTC().Format(time.RFC3339Nano),
		"restore_point": response{"file": "restore_point.db", "sha256": restoreSHA, "size": restoreSize},
		"items":         items,
	}); err != nil {
		return err
	}
	return writeExclusiveFile(filepath.Join(qdir, "moves.tsv"), []byte(tsv.String()))
}

func inlineResult(c inlineCandidate) response {
	return response{
		"note_id": c.noteID, "title": c.title, "attachment_id": c.attachmentID, "action": c.action,
		"file_path": c.filePath, "status": "", "reason": "", "moved_to": nil, "move_error": "", "error": "",
	}
}

// inlineOneSeparatedNote re-verifies the source, applies one note in its own transaction and
// moves the file after the commit. The bool asks the caller to stop (DB error or abort).
func (s *server) inlineOneSeparatedNote(plan *inlinePlan, qdir string, c inlineCandidate, historyRows map[int]bool) (response, bool) {
	result := inlineResult(c)
	if !s.inlineSourceUnchanged(plan.dataRoot, c) {
		result["status"], result["reason"] = "skipped", "changed_during_run"
		return result, false
	}
	committed, reason, err := s.inlineNoteTx(plan, c, historyRows)
	if err != nil {
		result["status"], result["error"] = "failed", err.Error()
		return result, true
	}
	if !committed {
		result["status"], result["reason"] = "skipped", reason
		return result, false
	}
	result["status"] = "merged"
	if c.action == "history" {
		result["status"] = "historied"
	}
	if err := s.fireTestHook("after_commit", c.noteID); err != nil {
		result["move_error"] = "aborted after commit: " + err.Error()
		return result, true
	}
	moved, err := s.quarantineSeparatedNote(plan, qdir, c)
	if err != nil {
		result["move_error"] = err.Error()
		return result, false
	}
	result["moved_to"] = moved
	return result, false
}

func (s *server) inlineSourceUnchanged(root string, c inlineCandidate) bool {
	src, reason, _ := s.inspectSeparatedNoteSource(root, c.noteID, c.filePath)
	return reason == "" && os.SameFile(src.identity, c.identity) && bytes.Equal(src.data, c.data)
}

// inlineNoteTx starts with a write (the DELETE) so the transaction holds the write lock from
// the first statement, then re-checks every precondition against the current DB.
func (s *server) inlineNoteTx(plan *inlinePlan, c inlineCandidate, historyRows map[int]bool) (bool, string, error) {
	tx, err := s.db.Begin()
	if err != nil {
		return false, "", err
	}
	defer tx.Rollback()
	deleted, err := tx.Exec("DELETE FROM Note_Attachments WHERE id = ? AND note_id = ? AND file_path = ? AND is_auto_extracted = 1", c.attachmentID, c.noteID, c.filePath)
	if err != nil {
		return false, "", err
	}
	if n, err := deleted.RowsAffected(); err != nil {
		return false, "", err
	} else if n != 1 {
		return false, "changed_during_run", nil
	}
	var others int
	if err := tx.QueryRow("SELECT COUNT(*) FROM Note_Attachments WHERE note_id = ? AND is_auto_extracted = 1", c.noteID).Scan(&others); err != nil {
		return false, "", err
	}
	var current string
	err = tx.QueryRow("SELECT COALESCE(content, '') FROM Notes WHERE id = ?", c.noteID).Scan(&current)
	if errors.Is(err, sql.ErrNoRows) || (err == nil && (others > 0 || current != c.dbContent)) {
		return false, "changed_during_run", nil
	}
	if err != nil {
		return false, "", err
	}
	shared, err := noteFileSharedByOtherRow(tx, s.runtime.dataDir, c.attachmentID, c.filePath, c.source)
	if err != nil {
		return false, "", err
	}
	if shared {
		return false, "changed_during_run", nil
	}
	text := normalizeTextContent(string(c.data))
	if c.action == "merge" {
		if _, err := tx.Exec("UPDATE Notes SET content = ? WHERE id = ?", text, c.noteID); err != nil {
			return false, "", err
		}
	} else {
		// Re-check media protection from the current DB inside this transaction: a PUT after
		// classification may have removed the last protecting reference.
		protected, err := s.referencedUploadFilenamesFrom(tx, historyRows, plan.fileRefs)
		if err != nil {
			return false, "", err
		}
		if !mediaProtected(c.data, protected) {
			return false, "media_unprotected", nil
		}
		if _, err := tx.Exec("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, ?, ?)", c.noteID, text, inlineHistorySummary); err != nil {
			return false, "", err
		}
	}
	if err := tx.Commit(); err != nil {
		return false, "", err
	}
	return true, "", nil
}

// quarantineSeparatedNote moves the committed note's file into <qdir>/docs/notes/ after
// re-checking path, identity and bytes. It never overwrites, never falls back to copy+delete:
// on any failure the file stays where it is (an orphan the next dry-run lists).
func (s *server) quarantineSeparatedNote(plan *inlinePlan, qdir string, c inlineCandidate) (string, error) {
	if !s.inlineSourceUnchanged(plan.dataRoot, c) {
		return "", errors.New("source changed")
	}
	for _, dir := range []string{filepath.Join(qdir, "docs"), filepath.Join(qdir, "docs", "notes")} {
		if err := os.Mkdir(dir, 0755); err != nil && !os.IsExist(err) {
			return "", err
		}
	}
	if !realDirChain(qdir, "docs", "notes") {
		return "", errors.New("quarantine directory is not a real directory")
	}
	dest := filepath.Join(qdir, filepath.FromSlash(c.rel))
	if !isSubpath(dest, qdir) {
		return "", errors.New("unsafe quarantine destination")
	}
	if err := s.fireTestHook("before_move", c.noteID); err != nil {
		return "", err
	}
	// Reserve the destination exclusively: the rename below can then only replace our own empty
	// placeholder, never a file that already exists in the quarantine folder.
	placeholder, err := os.OpenFile(dest, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		if os.IsExist(err) {
			return "", errors.New("destination exists")
		}
		return "", err
	}
	placeholder.Close()
	if err := os.Rename(c.source, dest); err != nil {
		_ = os.Remove(dest)
		var linkErr *os.LinkError
		if errors.As(err, &linkErr) {
			return "", fmt.Errorf("rename failed: %v", linkErr.Err)
		}
		return "", err
	}
	return plan.relative(dest), nil
}
