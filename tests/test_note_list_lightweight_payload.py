from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
GO_TEST_PATH = ROOT / "go-shadow" / "main_test.go"
API_TS_PATH = ROOT / "frontend" / "src" / "services" / "api.ts"
NOTE_CARD_PATH = ROOT / "frontend" / "src" / "components" / "NoteCard.tsx"
API_REFERENCE_PATH = ROOT / "docs" / "API_REFERENCE.md"
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
TODO_PATH = ROOT / "docs" / "TODO.md"


def test_notes_list_backend_projects_preview_without_breaking_detail_or_search():
    go_main = GO_MAIN_PATH.read_text(encoding="utf-8")
    go_test = GO_TEST_PATH.read_text(encoding="utf-8")

    assert "const noteListContentPreviewLength = 500" in go_main
    assert "applyNoteListContentPreview(note)" in go_main
    assert '"content_preview"] = preview' in go_main
    assert '"content_truncated"] = truncated' in go_main
    assert '"content_length"] = contentLength' in go_main
    assert '"content_first_image"] = firstImage' in go_main
    assert "func firstNoteContentImage(content string) string" in go_main
    assert "func noteListContentPreview(content string) (string, bool, int)" in go_main

    assert "TestNotesListUsesLightweightContentPreviewAndDetailStaysFull" in go_test
    assert "tailpayloadlightweight" in go_test
    assert "late-cover.png" in go_test
    assert "content_first_image got" in go_test
    assert "legacy content should match content_preview in list response" in go_test
    assert "detail content should remain full" in go_test


def test_note_card_uses_preview_and_fetches_detail_for_full_content_actions():
    api_ts = API_TS_PATH.read_text(encoding="utf-8")
    note_card = NOTE_CARD_PATH.read_text(encoding="utf-8")

    assert "content_preview?: string;" in api_ts
    assert "content_truncated?: boolean;" in api_ts
    assert "content_length?: number;" in api_ts
    assert "content_first_image?: string;" in api_ts

    assert "const cardContent = note.content_preview ?? note.content ?? ''" in note_card
    assert "const noteContentLength = note.content_length ?? cardContent.length" in note_card
    assert "const coverImage = note.cover_image || note.content_first_image || extractFirstImage(cardContent)" in note_card
    assert "note.content_truncated ? api.getNote(note.id) : note" in note_card
    assert "openEditor(fullNote, preview ? { preview: true } : undefined)" in note_card
    assert "await navigator.clipboard.writeText(fullNote.content)" in note_card
    assert "const matches: string[] = fullNote.content?.match(imagePattern) || []" in note_card
    assert "getPreview(cardContent" in note_card


def test_note_list_lightweight_contract_is_documented():
    api_reference = API_REFERENCE_PATH.read_text(encoding="utf-8")
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "content_preview" in api_reference
    assert "content_truncated" in api_reference
    assert "content_length" in api_reference
    assert "content_first_image" in api_reference
    assert "`content` 為相容用 preview" in api_reference
    assert "單筆詳情不套用 list preview 截斷" in api_reference

    assert "CONTRACT-NOTE-LIST-LIGHTWEIGHT" in contracts
    assert "不得新增 schema migration、cache layer、server-side UI state" in contracts

    assert "[x] **01A Read contract inventory**" in todo
    assert "[x] **01B Backend list payload gate**" in todo
    assert "[x] **01C Frontend lazy detail gate**" in todo
