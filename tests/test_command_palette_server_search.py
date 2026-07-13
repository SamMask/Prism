from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PALETTE_PATH = ROOT / "frontend" / "src" / "components" / "CommandPalette.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"


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


def test_kwf_01_docs_record_completion_and_next_entry():
    todo = TODO_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    assert "`KWF-01 Command Palette server-side search`（狀態：`Done`）" in todo
    assert "Command Palette 輸入 `? xxx` 或至少 3 個字元" in todo
    assert "不改後端搜尋引擎" in todo
    assert "`KWF-02 Saved Search / Search Workspace`（狀態：`Done`）" in todo
    assert "`KWF-03 Full data snapshot export`（狀態：`Done`）" in todo
    assert "KWF-01 Command Palette server-side search 已完成" in handoff
    assert "下一個低風險維護候選是另開 test-only gate" in handoff
