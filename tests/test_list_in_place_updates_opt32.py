"""PRISM-OPT-32 source locks; behavior is covered by e2e/test_list_in_place_updates.py."""

from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "frontend" / "src"


def _read(relative_path: str) -> str:
    return (SRC / relative_path).read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    return source[source.index(start):source.index(end, source.index(start))]


def test_store_refreshes_loaded_pages_under_the_latest_request_sequence():
    store = _read("stores/appStore.ts")
    refresh = _between(store, "refreshLoadedNotes: async () =>", "retryFetchNotes: () =>")
    assert "const NOTES_PAGE_SIZE = 20" in store
    assert "const requestId = ++notesRequestSequence" in refresh
    assert "requestId !== notesRequestSequence" in refresh
    assert "Math.max(1, state.currentPage - 1)" in refresh
    assert "currentPage: loadedPages + 1" in refresh
    # Search / filter / sort no longer re-read the Library total; only mutations that change it do.
    fetch_notes = _between(store, "fetchNotes: async (reset = false) =>", "refreshLoadedNotes: async () =>")
    assert "fetchLibraryTotal" not in fetch_notes
    library_total = _between(store, "fetchLibraryTotal: async () =>", "setLocale: (locale) =>")
    assert "requestId === libraryTotalRequestSequence" in library_total


def test_mutation_call_sites_refresh_in_place_instead_of_resetting():
    form = _read("hooks/editor/useNoteForm.ts")
    save = _between(form, "const save = useCallback", "const handleSave = useCallback")
    history = _read("hooks/editor/useNoteHistory.ts")
    restore = _between(history, "const restoreVersion = async", "return {")
    card = _read("components/NoteCard.tsx")
    reading = _read("components/ReadingView.tsx")
    for block in (
        save,
        restore,
        _between(card, "const handleCreateVariant = async", "// Handle toggle pin"),
        _between(card, "const handleTogglePin = async", "// Handle export images"),
        _between(card, "const handleToggleArchive = async", "const handleOpenReading"),
        _between(reading, "const handleTogglePin = async", "const workspaceItems"),
    ):
        assert "fetchNotes(true)" not in block
        assert "refreshLoadedNotes()" in block
    # The Library total follows create / variant / archive toggle, not edits, pins or restores.
    assert "void fetchLibraryTotal()" in _between(save, "await api.createNote(payload)", "originalSnapshot.current")
    assert "fetchLibraryTotal" not in _between(save, "if (isEditing) {", "} else {")
    assert "fetchLibraryTotal" not in restore
    assert "fetchLibraryTotal" not in _between(card, "const handleTogglePin = async", "// Handle export images")
    assert "fetchLibraryTotal()" in _between(card, "const handleCreateVariant = async", "// Handle toggle pin")
    assert "fetchLibraryTotal()" in _between(card, "const handleToggleArchive = async", "const handleOpenReading")
    prompt = _read("hooks/usePromptBuilder.ts")
    assert "fetchLibraryTotal()" in _between(prompt, "const saveToLibrary", "// Wizard Functions")


def test_notes_grid_opts_out_of_scroll_anchoring():
    home = _read("pages/HomePage.tsx")
    grid = _between(home, "const notesContent = (", 'data-testid="notes-grid"')
    assert "[overflow-anchor:none]" in grid
