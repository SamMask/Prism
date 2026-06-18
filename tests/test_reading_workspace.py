from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "frontend" / "src" / "hooks" / "useReadingWorkspace.ts"
HEADER_PATH = ROOT / "frontend" / "src" / "components" / "Header.tsx"
READING_VIEW_PATH = ROOT / "frontend" / "src" / "components" / "ReadingView.tsx"
NOTE_CARD_PATH = ROOT / "frontend" / "src" / "components" / "NoteCard.tsx"
NOTE_EDITOR_PATH = ROOT / "frontend" / "src" / "components" / "NoteEditor.tsx"
EDITOR_TOOLBAR_PATH = ROOT / "frontend" / "src" / "components" / "editor" / "EditorToolbar.tsx"
APPEARANCE_PATH = ROOT / "frontend" / "src" / "components" / "settings" / "AppearanceSection.tsx"
MAIN_PATH = ROOT / "frontend" / "src" / "main.tsx"
I18N_PATH = ROOT / "frontend" / "src" / "i18n" / "index.ts"
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
TODO_PATH = ROOT / "docs" / "TODO.md"


def test_reading_workspace_state_contract_is_frontend_only_and_versioned():
    source = HOOK_PATH.read_text(encoding="utf-8")

    assert "READING_WORKSPACE_STORAGE_KEY = 'prism.readingWorkspace.v1'" in source
    assert "READING_WORKSPACE_CHANGED_EVENT = 'prism:reading-workspace-changed'" in source
    assert "noteIds: number[]" in source
    assert "activeId: number | null" in source
    assert "layout: ReadingWorkspaceLayout" in source
    assert "scrollPositions: Record<string, number>" in source
    assert "window.localStorage.getItem(READING_WORKSPACE_STORAGE_KEY)" in source
    assert "window.localStorage.setItem(READING_WORKSPACE_STORAGE_KEY, JSON.stringify(normalized))" in source
    assert "window.dispatchEvent(new CustomEvent(READING_WORKSPACE_CHANGED_EVENT))" in source
    assert "window.addEventListener('storage', sync)" in source
    assert "export function addNoteToReadingWorkspace" in source
    assert "export function isNoteInReadingWorkspace" in source
    assert "export type ReadingWorkspaceLayout = 'tabs' | 'sidebar'" in source
    assert "api." not in source


def test_reading_view_switcher_add_remove_clear_and_scroll_restore_are_locked():
    source = READING_VIEW_PATH.read_text(encoding="utf-8")

    assert "useReadingWorkspace()" in source
    assert "data-testid=\"reading-workspace-panel\"" in source
    assert "data-layout={workspace.layout}" in source
    assert "data-testid=\"reading-workspace-clear\"" in source
    assert "data-testid={`reading-workspace-item-${item.id}`}" in source
    assert "data-testid={`reading-workspace-remove-${item.id}`}" in source
    assert "data-testid=\"reading-workspace-add-current\"" in source
    assert "data-testid=\"reading-scroll-container\"" in source
    assert "saveScrollPosition(localNote.id, readingScrollRef.current?.scrollTop ?? 0)" in source
    assert "node.scrollTop = getScrollPosition(localNote.id)" in source
    assert "pendingScrollRestoreIdRef.current = noteId" in source
    assert "setWorkspaceUnavailableIds((current) => (" in source
    assert "t('reading.workspaceUnavailable')" in source
    assert "removeNote(noteId)" in source
    assert "clearWorkspace()" in source
    assert "setActiveNote(noteId)" in source
    assert "api.getNote(noteId)" in source


def test_note_card_adds_to_reading_workspace_without_forcing_reading_open():
    source = NOTE_CARD_PATH.read_text(encoding="utf-8")

    assert "addNoteToReadingWorkspace(note.id)" in source
    assert "isNoteInReadingWorkspace(note.id)" in source
    assert "data-testid={`note-card-add-reading-workspace-${note.id}`}" in source
    assert "t('noteCard.addToReadingWorkspace')" in source
    assert "t('noteCard.addedToReadingWorkspace')" in source
    assert "t('noteCard.inReadingWorkspace')" in source

    add_block = source.split("const handleAddToReadingWorkspace = () => {", 1)[1].split("const handleOpenVariants", 1)[0]
    assert "openReading(note)" not in add_block


def test_reading_workspace_can_open_from_header_and_editor_toolbar():
    header = HEADER_PATH.read_text(encoding="utf-8")
    editor = NOTE_EDITOR_PATH.read_text(encoding="utf-8")
    toolbar = EDITOR_TOOLBAR_PATH.read_text(encoding="utf-8")

    assert "useReadingWorkspace()" in header
    assert "data-testid=\"header-open-reading-workspace\"" in header
    assert "const noteId = workspace.activeId ?? workspace.noteIds[0]" in header
    assert "api.getNote(noteId)" in header
    assert "navigate('/')" in header
    assert "openReading(note)" in header
    assert "t('header.openReadingWorkspace'" in header

    assert "useReadingWorkspace()" in editor
    assert "addNote(note.id)" in editor
    assert "t('noteCard.addedToReadingWorkspace')" in editor
    assert "usePromptExtraction" not in editor

    assert "canAddToReadingWorkspace" in toolbar
    assert "onAddToReadingWorkspace" in toolbar
    assert "data-testid=\"editor-add-reading-workspace\"" in toolbar
    assert "t('noteCard.addToReadingWorkspace')" in toolbar
    assert "extractImagePrompt" not in toolbar


def test_sidebar_width_range_is_150_to_320():
    appearance = APPEARANCE_PATH.read_text(encoding="utf-8")
    main = MAIN_PATH.read_text(encoding="utf-8")

    assert "const SIDEBAR_WIDTH_MIN = 150" in appearance
    assert "const SIDEBAR_WIDTH_MAX = 320" in appearance
    assert "readNumberSetting('prism.sidebarWidth', 248, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX)" in appearance
    assert "clampNumber(value, SIDEBAR_WIDTH_MIN, SIDEBAR_WIDTH_MAX)" in appearance
    assert "min={SIDEBAR_WIDTH_MIN}" in appearance
    assert "max={SIDEBAR_WIDTH_MAX}" in appearance
    assert "readNumberSetting('prism.sidebarWidth', 248, 150, 320)" in main
    assert "readNumberSetting('prism.sidebarWidth', 248, 208, 320)" not in main


def test_reading_workspace_i18n_and_docs_record_frontend_only_scope():
    i18n = I18N_PATH.read_text(encoding="utf-8")
    contracts = CONTRACTS_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")

    for key in [
        "addToReadingWorkspace",
        "addedToReadingWorkspace",
        "inReadingWorkspace",
        "workspaceTitle",
        "workspaceAddCurrent",
        "workspaceClear",
        "workspaceRemove",
        "workspaceLoadFailed",
    ]:
        assert i18n.count(f"{key}:") == 4

    for key in [
        "readingWorkspace",
        "openReadingWorkspace",
    ]:
        assert i18n.count(f"{key}:") == 4

    assert "CONTRACT-READING-WORKSPACE" in contracts
    assert "`prism.readingWorkspace.v1`" in contracts
    assert "不得新增 DB schema" in contracts
    assert "改 note API" in contracts
    assert "server persistence" not in contracts

    assert "[x] **01A State contract**" in todo
    assert "[x] **01B Reading panel switcher**" in todo
    assert "[x] **01C Home/card entry points**" in todo
    assert "[x] **01D Scroll restore**" in todo
    assert "Pi delivery" in todo
