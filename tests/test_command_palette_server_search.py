from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PALETTE_PATH = ROOT / "frontend" / "src" / "components" / "CommandPalette.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"
TODO_HANDOFF_ARCHIVE_20261006_PATH = ROOT / "docs" / "development-history" / "todo-handoff-archive-20261006.md"


def test_command_palette_server_search_uses_existing_notes_api_contract():
    source = PALETTE_PATH.read_text(encoding="utf-8")

    assert "const SERVER_SEARCH_MIN_CHARS = 3" in source
    assert "const SERVER_SEARCH_DEBOUNCE_MS = 250" in source
    assert "function getServerSearchTerm(query: string): string" in source
    assert "trimmed.startsWith('?')" in source
    assert "api.getNotes({" in source
    assert "search: serverSearchTerm" in source
    assert "per_page: SERVER_SEARCH_LIMIT" in source
    assert "include_archived: true" in source
    assert "sort: 'updated'" in source
    assert "CommandGroup = 'navigation' | 'results' | 'recent' | 'actions'" in source
    assert "group: 'results' as const" in source
    assert "data-testid=\"command-palette-server-search-status\"" in source


def test_command_palette_server_search_uses_two_char_threshold_for_cjk():
    source = PALETTE_PATH.read_text(encoding="utf-8")

    assert "const SERVER_SEARCH_MIN_CHARS = 3" in source
    assert "const SERVER_SEARCH_MIN_CHARS_CJK = 2" in source
    assert "const CJK_CHAR_PATTERN = /[\\p{Script=Han}\\p{Script=Hiragana}\\p{Script=Katakana}]/u" in source
    assert (
        "const minChars = CJK_CHAR_PATTERN.test(trimmed) ? SERVER_SEARCH_MIN_CHARS_CJK : SERVER_SEARCH_MIN_CHARS"
        in source
    )
    assert "return trimmed.length >= minChars ? trimmed : ''" in source


def test_command_palette_server_search_results_open_full_note_detail():
    source = PALETTE_PATH.read_text(encoding="utf-8")

    assert "const openNoteFromPalette = useCallback(async (note: Note) =>" in source
    assert "note.content_truncated ? await api.getNote(note.id) : note" in source
    assert "openEditor(noteForEditor)" in source
    assert "content_preview ?? note.content" in source
    assert "action: () => openNoteFromPalette(note)" in source


def test_command_palette_server_search_i18n_exists_for_four_locales():
    i18n = I18N_PATH.read_text(encoding="utf-8")

    assert i18n.count("serverSearch: {") >= 4
    for key in ["searching:", "failed:", "empty:", "count:"]:
        assert i18n.count(key) >= 4
    for phrase in ["全庫搜尋", "Full search", "全体検索", "전체 검색"]:
        assert phrase in i18n


def test_kwf_01_docs_record_completion_and_current_handoff():
    archive = TODO_HANDOFF_ARCHIVE_20261006_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    assert "`KWF-01 Command Palette server-side search`（狀態：`Done`）" in archive
    assert "Command Palette 輸入 `? xxx` 或至少 3 個字元" in archive
    assert "不改後端搜尋引擎" in archive
    assert "`KWF-02 Saved Search / Search Workspace`（狀態：`Done`）" in archive
    assert "`KWF-03 Full data snapshot export`（狀態：`Done`）" in archive
    assert "KWF-01 Command Palette server-side search 已完成" in archive
    assert "## Next Entry" in handoff
    assert "todo-handoff-archive-20261006.md" in todo
