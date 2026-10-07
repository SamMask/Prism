package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"sort"
	"testing"
)

func searchNoteIDs(t *testing.T, srv *server, query string) []int {
	t.Helper()
	recorder := httptest.NewRecorder()
	srv.handleNotes(recorder, httptest.NewRequest(http.MethodGet, "/api/notes?per_page=100&q="+url.QueryEscape(query), nil))
	if recorder.Code != http.StatusOK {
		t.Fatalf("%q returned %d body=%s", query, recorder.Code, recorder.Body.String())
	}
	var payload struct {
		Data []map[string]any `json:"data"`
	}
	if err := json.Unmarshal(recorder.Body.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	ids := []int{}
	for _, note := range payload.Data {
		ids = append(ids, int(note["id"].(float64)))
	}
	sort.Ints(ids)
	return ids
}

func equalIDs(a, b []int) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func TestNotesSearchHangulSubstring(t *testing.T) {
	db, err := openDB(createSpikeDB(t), true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	koID := insertSearchNote(t, db, "기록", "오늘 회의록을 정리했습니다", "", 1)
	srv := &server{db: db, runtime: runtimeConfig{dataDir: t.TempDir()}}

	if got := searchNoteIDs(t, srv, "회의"); !equalIDs(got, []int{koID}) {
		t.Fatalf("Hangul mid-sentence word: got %v want [%d]", got, koID)
	}
	if got := searchNoteIDs(t, srv, "의록"); !equalIDs(got, []int{koID}) {
		t.Fatalf("Hangul mid-run substring: got %v want [%d]", got, koID)
	}
}

func TestNotesSearchFullwidthFold(t *testing.T) {
	db, err := openDB(createSpikeDB(t), true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	promptID := insertSearchNote(t, db, "學習", "learning prompt engineering 提示詞工程", "", 1)
	insertSearchNote(t, db, "其他", "沒有相關內容", "", 1)
	srv := &server{db: db, runtime: runtimeConfig{dataDir: t.TempDir()}}
	half := searchNoteIDs(t, srv, "prompt")
	full := searchNoteIDs(t, srv, "ＰＲＯＭＰＴ")
	if !equalIDs(half, []int{promptID}) || !equalIDs(full, half) {
		t.Fatalf("fullwidth fold: half=%v full=%v want [%d]", half, full, promptID)
	}
	// Mixed query: one CJK token switches ASCII tokens to substring match.
	if got := searchNoteIDs(t, srv, "ｒｏｍ　工程"); !equalIDs(got, []int{promptID}) {
		t.Fatalf("mixed fullwidth query: got %v want [%d]", got, promptID)
	}
}

func TestNotesSearchASCIIQuerySQLUnchanged(t *testing.T) {
	db, err := openDB(createSpikeDB(t), true)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	srv := &server{db: db, runtime: runtimeConfig{dataDir: t.TempDir()}}
	// Hashes and args captured before PRISM-OPT-56.
	cases := []struct {
		query string
		hash  string
		args  []any
	}{
		{"prompt", "ef4b2536f7a11cc653d92a2082b2ae42c3ffc7cb4097666de11c13400be8c1dc",
			[]any{`"prompt"*`, "%prompt%", "%prompt%", "%prompt%", "%prompt%"}},
		{"a b", "81974293c7b803f29e6cd26e231a681b3edbdb4d68f9918d6877b9df8f44607f",
			[]any{`"a"* "b"*`, "%a%", "%b%", "%a%", "%b%", "%a%", "%a%", "%b%", "%b%"}},
		{"foo-bar", "81974293c7b803f29e6cd26e231a681b3edbdb4d68f9918d6877b9df8f44607f",
			[]any{`"foo"* "bar"*`, "%foo%", "%bar%", "%foo%", "%bar%", "%foo%", "%foo%", "%bar%", "%bar%"}},
	}
	for _, tc := range cases {
		clause, args, _ := srv.buildNotesSearchClause(tc.query)
		sum := sha256.Sum256([]byte(clause))
		if hex.EncodeToString(sum[:]) != tc.hash {
			t.Fatalf("%q SQL changed: %s", tc.query, clause)
		}
		if len(args) != len(tc.args) {
			t.Fatalf("%q args changed: %#v", tc.query, args)
		}
		for i := range args {
			if args[i] != tc.args[i] {
				t.Fatalf("%q arg %d changed: %#v", tc.query, i, args)
			}
		}
	}
}
