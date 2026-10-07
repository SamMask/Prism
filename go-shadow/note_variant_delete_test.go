package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// PRISM-OPT-68: Notes.parent_id is a self-referencing FK with no ON DELETE action, so deleting
// a note that still has variants failed with "FOREIGN KEY constraint failed (787)". Deleting
// now moves the variants up to the deleted note's own parent (NULL for a root note).

var variantNoteDeletes = map[string]func(e *inlineEnv, ids ...int) *httptest.ResponseRecorder{
	"single": func(e *inlineEnv, ids ...int) *httptest.ResponseRecorder {
		var rec *httptest.ResponseRecorder
		for _, id := range ids {
			if rec = e.do(http.MethodDelete, fmt.Sprintf("/api/notes/%d", id), ""); rec.Code != http.StatusOK {
				return rec
			}
		}
		return rec
	},
	"batch": func(e *inlineEnv, ids ...int) *httptest.ResponseRecorder {
		body, _ := json.Marshal(map[string]any{"note_ids": ids})
		return e.do(http.MethodPost, "/api/notes/batch/delete", string(body))
	},
}

func createVariant(t *testing.T, e *inlineEnv, parentID int) int {
	t.Helper()
	rec := e.do(http.MethodPost, fmt.Sprintf("/api/notes/%d/duplicate", parentID), `{"as_variant":true}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("duplicate %d as variant: %d %s", parentID, rec.Code, rec.Body.String())
	}
	var out struct {
		Data struct {
			NoteID int `json:"note_id"`
		} `json:"data"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil || out.Data.NoteID == 0 {
		t.Fatalf("duplicate response: %v %s", err, rec.Body.String())
	}
	return out.Data.NoteID
}

// noteParent returns the note's parent_id; 0 means NULL.
func noteParent(t *testing.T, e *inlineEnv, id int) int {
	t.Helper()
	var parent sql.NullInt64
	if err := e.srv.db.QueryRow("SELECT parent_id FROM Notes WHERE id = ?", id).Scan(&parent); err != nil {
		t.Fatalf("note %d should survive the delete: %v", id, err)
	}
	return int(parent.Int64)
}

func assertParent(t *testing.T, e *inlineEnv, id, want int) {
	t.Helper()
	if got := noteParent(t, e, id); got != want {
		t.Fatalf("note %d parent_id = %d, want %d (0 = NULL)", id, got, want)
	}
}

func assertNoteGone(t *testing.T, e *inlineEnv, id int) {
	t.Helper()
	var n int
	if err := e.srv.db.QueryRow("SELECT COUNT(*) FROM Notes WHERE id = ?", id).Scan(&n); err != nil || n != 0 {
		t.Fatalf("note %d should be deleted (count %d, err %v)", id, n, err)
	}
}

func assertForeignKeysClean(t *testing.T, e *inlineEnv) {
	t.Helper()
	rows, err := e.srv.db.Query("PRAGMA foreign_key_check")
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	if rows.Next() {
		t.Fatal("PRAGMA foreign_key_check reports violations after delete")
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	var dangling int
	if err := e.srv.db.QueryRow(`SELECT COUNT(*) FROM Notes c
		WHERE c.parent_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Notes p WHERE p.id = c.parent_id)`).Scan(&dangling); err != nil {
		t.Fatal(err)
	}
	if dangling != 0 {
		t.Fatalf("%d notes still point at a deleted parent", dangling)
	}
}

func mustDelete(t *testing.T, rec *httptest.ResponseRecorder) {
	t.Helper()
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"success"`) {
		t.Fatalf("delete: %d %s", rec.Code, rec.Body.String())
	}
}

func TestDeleteRootNoteDetachesVariants(t *testing.T) {
	for name, deleteNotes := range variantNoteDeletes {
		t.Run(name, func(t *testing.T) {
			e := newInlineEnv(t)
			root := e.createNote("原始提示詞", "根筆記的中文內容")
			v1 := createVariant(t, e, root)
			v2 := createVariant(t, e, root)

			mustDelete(t, deleteNotes(e, root))
			assertNoteGone(t, e, root)
			assertParent(t, e, v1, 0)
			assertParent(t, e, v2, 0)
			assertForeignKeysClean(t, e)
		})
	}
}

func TestDeleteMiddleVariantMovesChildrenToGrandparent(t *testing.T) {
	for name, deleteNotes := range variantNoteDeletes {
		t.Run(name, func(t *testing.T) {
			e := newInlineEnv(t)
			a := e.createNote("祖父筆記", "第一代的中文內容")
			b := createVariant(t, e, a)
			c := createVariant(t, e, b)

			mustDelete(t, deleteNotes(e, b))
			assertNoteGone(t, e, b)
			assertParent(t, e, a, 0)
			assertParent(t, e, c, a)
			assertForeignKeysClean(t, e)
		})
	}
}

// Deleting a parent and its child together must not leave survivors pointing at either one,
// whatever order the ids arrive in: each survivor ends under its nearest surviving ancestor.
func TestDeleteParentAndChildTogetherLeavesNoDanglingParent(t *testing.T) {
	for name, deleteNotes := range variantNoteDeletes {
		for _, reversed := range []bool{false, true} {
			t.Run(fmt.Sprintf("%s/reversed=%v", name, reversed), func(t *testing.T) {
				e := newInlineEnv(t)
				r := e.createNote("保留的根", "不會被刪除的中文根筆記")
				a := createVariant(t, e, r)
				b := createVariant(t, e, a)
				c := createVariant(t, e, b)
				d := createVariant(t, e, b)
				lone := e.createNote("獨立根", "沒有祖先的中文筆記")
				x := createVariant(t, e, lone)
				y := createVariant(t, e, x)

				ids := []int{a, b, lone, x}
				if reversed {
					ids = []int{x, lone, b, a}
				}
				mustDelete(t, deleteNotes(e, ids...))
				for _, id := range ids {
					assertNoteGone(t, e, id)
				}
				assertParent(t, e, c, r)
				assertParent(t, e, d, r)
				assertParent(t, e, y, 0)
				assertForeignKeysClean(t, e)
			})
		}
	}
}
