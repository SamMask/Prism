package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"testing"
)

// PRISM-OPT-39: the JSON export carries is_pinned, is_archived, parent_id, cover_position,
// editor_layout and sort_order, and the import restores them. parent_id is remapped through the
// file's old id -> new id map, never pointed at an unrelated target note that has the same id.

type importedNoteFields struct {
	ID        int
	Pinned    int
	Archived  int
	SortOrder sql.NullInt64
	Cover     string
	Layout    string
	Parent    sql.NullInt64
}

func noteFieldsByTitle(t *testing.T, e *inlineEnv, title string) importedNoteFields {
	t.Helper()
	var f importedNoteFields
	var cover, layout sql.NullString
	if err := e.srv.db.QueryRow(`SELECT id, is_pinned, is_archived, sort_order, cover_position, editor_layout, parent_id
		FROM Notes WHERE title = ?`, title).Scan(&f.ID, &f.Pinned, &f.Archived, &f.SortOrder, &cover, &layout, &f.Parent); err != nil {
		t.Fatalf("note %q: %v", title, err)
	}
	f.Cover, f.Layout = cover.String, layout.String
	return f
}

func assertNoForeignKeyViolations(t *testing.T, e *inlineEnv) {
	t.Helper()
	rows, err := e.srv.db.Query("PRAGMA foreign_key_check")
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	if rows.Next() {
		t.Fatal("PRAGMA foreign_key_check reports violations")
	}
}

func assertImportedParent(t *testing.T, got importedNoteFields, want int, label string) {
	t.Helper()
	if want == 0 {
		if got.Parent.Valid {
			t.Fatalf("%s parent_id = %d, want NULL", label, got.Parent.Int64)
		}
		return
	}
	if !got.Parent.Valid || int(got.Parent.Int64) != want {
		t.Fatalf("%s parent_id = %v, want %d", label, got.Parent, want)
	}
}

func assertScalarFields(t *testing.T, got, want importedNoteFields, title string) {
	t.Helper()
	if got.Pinned != want.Pinned || got.Archived != want.Archived || got.SortOrder != want.SortOrder ||
		got.Cover != want.Cover || got.Layout != want.Layout {
		t.Fatalf("%s fields = %+v, want %+v", title, got, want)
	}
}

// exportLineageFixture builds pinned/archived notes with custom fields and the lineage
// A -> B -> C, and returns the export with C ordered before B and A, plus the source fields.
func exportLineageFixture(t *testing.T) (map[string]any, map[string]importedNoteFields) {
	t.Helper()
	src := newInlineEnv(t)
	a := src.createNote("譜系祖先 A", "祖先筆記的中文內容")
	b := src.createNote("譜系變體 B", "第二代變體的中文內容")
	c := src.createNote("譜系孫代 C", "第三代變體的中文內容")
	archived := src.createNote("封存筆記", "已封存的中文筆記")
	src.exec("UPDATE Notes SET is_pinned = 1, cover_position = 'bottom', editor_layout = 'dual', sort_order = 7 WHERE id = ?", a)
	src.exec("UPDATE Notes SET parent_id = ?, sort_order = 0 WHERE id = ?", a, b)
	src.exec("UPDATE Notes SET parent_id = ?, cover_position = 'center' WHERE id = ?", b, c)
	src.exec("UPDATE Notes SET is_archived = 1, sort_order = 3 WHERE id = ?", archived)

	exp := src.do(http.MethodGet, "/api/export/json", "")
	if exp.Code != http.StatusOK {
		t.Fatalf("export: %d %s", exp.Code, exp.Body.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(exp.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if v := payload["export_info"].(map[string]any)["version"]; v != "1.7-go" {
		t.Errorf("export_info.version = %v, want 1.7-go", v)
	}
	rank := map[string]int{"譜系孫代 C": 0, "譜系變體 B": 1, "譜系祖先 A": 2}
	notes := payload["notes"].([]any)
	sorted := make([]any, 3, len(notes))
	for _, n := range notes {
		if r, ok := rank[n.(map[string]any)["title"].(string)]; ok {
			sorted[r] = n
		} else {
			sorted = append(sorted, n)
		}
	}
	payload["notes"] = sorted
	want := map[string]importedNoteFields{}
	for _, title := range []string{"譜系祖先 A", "譜系變體 B", "譜系孫代 C", "封存筆記"} {
		want[title] = noteFieldsByTitle(t, src, title)
	}
	return payload, want
}

func TestImportJSONRoundTripsNoteFieldsAndLineage(t *testing.T) {
	exported, want := exportLineageFixture(t)
	for name, unrelated := range map[string]int{"fresh": 0, "occupied-ids": 8} {
		t.Run(name, func(t *testing.T) {
			dst := newInlineEnv(t)
			for i := 0; i < unrelated; i++ {
				dst.createNote(fmt.Sprintf("無關筆記 %d", i), fmt.Sprintf("目標端既有的無關內容 %d", i))
			}
			code, out := postImportJSON(t, dst, exported, "skip")
			if code != http.StatusOK || out.Data.Imported != len(want) {
				t.Fatalf("import: %d %+v", code, out)
			}
			got := map[string]importedNoteFields{}
			for title, w := range want {
				got[title] = noteFieldsByTitle(t, dst, title)
				assertScalarFields(t, got[title], w, title)
			}
			assertImportedParent(t, got["譜系祖先 A"], 0, "A")
			assertImportedParent(t, got["譜系變體 B"], got["譜系祖先 A"].ID, "B")
			assertImportedParent(t, got["譜系孫代 C"], got["譜系變體 B"].ID, "C")
			assertImportedParent(t, got["封存筆記"], 0, "archived")
			assertNoForeignKeyViolations(t, dst)
		})
	}
}

func TestImportJSONParentOutsideFileIsNull(t *testing.T) {
	dst := newInlineEnv(t)
	unrelated := dst.createNote("目標端無關筆記", "碰巧同 id 的無關內容")
	data := map[string]any{"notes": []any{
		map[string]any{"id": 50, "title": "孤兒變體", "content": "parent 不在檔中的中文筆記", "parent_id": unrelated},
		map[string]any{"id": 51, "title": "遠端孤兒", "content": "parent 完全不存在的中文筆記", "parent_id": 999},
	}}
	code, out := postImportJSON(t, dst, data, "skip")
	if code != http.StatusOK || out.Data.Imported != 2 {
		t.Fatalf("import: %d %+v", code, out)
	}
	assertImportedParent(t, noteFieldsByTitle(t, dst, "孤兒變體"), 0, "parent with an unrelated same-id target note")
	assertImportedParent(t, noteFieldsByTitle(t, dst, "遠端孤兒"), 0, "missing parent")
	assertNoForeignKeyViolations(t, dst)
}

func TestImportJSONLegacyNotesKeepDefaults(t *testing.T) {
	dst := newInlineEnv(t)
	data := map[string]any{"notes": []any{
		map[string]any{"id": 1, "title": "舊版匯出筆記", "content": "沒有新欄位的中文筆記", "category": "Uncategorized",
			"tags": []any{"舊版"}, "urls": []any{}, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"},
	}}
	code, out := postImportJSON(t, dst, data, "skip")
	if code != http.StatusOK || out.Data.Imported != 1 {
		t.Fatalf("import: %d %+v", code, out)
	}
	got := noteFieldsByTitle(t, dst, "舊版匯出筆記")
	assertScalarFields(t, got, importedNoteFields{Cover: "top", Layout: "single"}, "legacy")
	assertImportedParent(t, got, 0, "legacy")
}

func TestImportJSONInvalidFieldValuesFallBackToDefaults(t *testing.T) {
	dst := newInlineEnv(t)
	data := map[string]any{"notes": []any{
		map[string]any{"id": 1, "title": "不合法欄位", "content": "欄位型別錯誤的中文筆記",
			"is_pinned": "是", "is_archived": map[string]any{}, "sort_order": "第一", "cover_position": 5,
			"editor_layout": []any{"dual"}, "parent_id": "祖先"},
		map[string]any{"id": 2, "title": "小數排序", "content": "排序是小數的中文筆記", "sort_order": 1.5, "parent_id": 1.5},
	}}
	code, out := postImportJSON(t, dst, data, "skip")
	if code != http.StatusOK || out.Data.Imported != 2 {
		t.Fatalf("import: %d %+v", code, out)
	}
	for _, title := range []string{"不合法欄位", "小數排序"} {
		got := noteFieldsByTitle(t, dst, title)
		assertScalarFields(t, got, importedNoteFields{Cover: "top", Layout: "single"}, title)
		assertImportedParent(t, got, 0, title)
	}
}

func TestImportJSONSkipModeMapsParentToExistingNote(t *testing.T) {
	exported, _ := exportLineageFixture(t)
	dst := newInlineEnv(t)
	dst.createNote("無關筆記", "佔用 id 的無關中文內容")
	existingA := dst.createNote("譜系祖先 A", "祖先筆記的中文內容")
	total := len(exported["notes"].([]any))
	code, out := postImportJSON(t, dst, exported, "skip")
	if code != http.StatusOK || out.Data.Imported != 3 || out.Data.Skipped != total-3 {
		t.Fatalf("import: %d %+v", code, out)
	}
	if n := countRows(t, dst, "SELECT COUNT(*) FROM Notes WHERE title = '譜系祖先 A'"); n != 1 {
		t.Fatalf("A rows = %d, want 1 (skipped)", n)
	}
	a := noteFieldsByTitle(t, dst, "譜系祖先 A")
	if a.ID != existingA || a.Pinned != 0 || a.Parent.Valid {
		t.Fatalf("skipped note was modified: %+v", a)
	}
	b := noteFieldsByTitle(t, dst, "譜系變體 B")
	assertImportedParent(t, b, existingA, "B")
	assertImportedParent(t, noteFieldsByTitle(t, dst, "譜系孫代 C"), b.ID, "C")

	// Re-importing the same file skips every note and leaves the lineage unchanged.
	code, out = postImportJSON(t, dst, exported, "skip")
	if code != http.StatusOK || out.Data.Imported != 0 || out.Data.Skipped != total {
		t.Fatalf("re-import: %d %+v", code, out)
	}
	assertImportedParent(t, noteFieldsByTitle(t, dst, "譜系變體 B"), existingA, "B after re-import")
	assertImportedParent(t, noteFieldsByTitle(t, dst, "譜系孫代 C"), b.ID, "C after re-import")
	assertNoForeignKeyViolations(t, dst)
}

func TestImportJSONParentCycleIsBroken(t *testing.T) {
	dst := newInlineEnv(t)
	data := map[string]any{"notes": []any{
		map[string]any{"id": 1, "title": "環狀甲", "content": "互相指向的中文筆記甲", "parent_id": 2},
		map[string]any{"id": 2, "title": "環狀乙", "content": "互相指向的中文筆記乙", "parent_id": 1},
		map[string]any{"id": 3, "title": "自我指向", "content": "指向自己的中文筆記", "parent_id": 3},
	}}
	code, out := postImportJSON(t, dst, data, "skip")
	if code != http.StatusOK || out.Data.Imported != 3 {
		t.Fatalf("import: %d %+v", code, out)
	}
	first, second := noteFieldsByTitle(t, dst, "環狀甲"), noteFieldsByTitle(t, dst, "環狀乙")
	if first.Parent.Valid == second.Parent.Valid {
		t.Fatalf("cycle not broken exactly once: 甲 %v, 乙 %v", first.Parent, second.Parent)
	}
	assertImportedParent(t, noteFieldsByTitle(t, dst, "自我指向"), 0, "self")
	assertNoForeignKeyViolations(t, dst)
}
