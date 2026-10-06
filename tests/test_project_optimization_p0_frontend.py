import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"


def _read(relative_path: str) -> str:
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def test_mobile_navigation_is_a_named_off_canvas_drawer_with_focus_recovery():
    layout = _read("components/Layout.tsx")
    header = _read("components/Header.tsx")
    sidebar = _read("components/Sidebar.tsx")

    assert "isMobileNavOpen" in layout
    assert "onOpenMobileNav" in header
    assert "t('sidebar.openNavigation')" in header
    assert 'data-testid="app-sidebar"' in sidebar
    assert 'data-mobile-navigation-drawer="true"' in sidebar
    assert "fixed inset-y-0 left-0" in sidebar
    assert "isMobileOpen ? 'flex translate-x-0' : 'hidden -translate-x-full'" in sidebar
    assert "md:flex md:translate-x-0" in sidebar
    assert "event.key === 'Escape'" in sidebar
    assert "previouslyFocused?.focus()" in sidebar
    assert "aria-modal={isMobileOpen ? true : undefined}" in sidebar


def test_sidebar_and_header_icon_controls_have_accessible_names():
    header = _read("components/Header.tsx")
    sidebar = _read("components/Sidebar.tsx")

    assert "aria-label={t('header.addNote')}" in header
    assert "aria-label={t('header.clearSearch')}" in header
    assert "aria-label={t('sidebar.all')}" in sidebar
    assert "aria-label={t('sidebar.archive')}" in sidebar
    assert "aria-label={t('sidebar.settings')}" in sidebar
    assert "aria-label={categoryName}" in sidebar
    assert "aria-label={`#${tag.name}`}" in sidebar


def test_all_note_views_share_visible_selection_and_action_affordances():
    note_card = _read("components/NoteCard.tsx")

    assert "const renderSelectionControl" in note_card
    assert "const renderActionsMenu" in note_card
    assert note_card.count("{renderSelectionControl()}") == 3
    assert note_card.count("{renderActionsMenu()}") == 3
    assert 'data-testid={`note-card-select-${note.id}`}' in note_card
    assert 'data-testid={`note-card-actions-${note.id}`}' in note_card
    assert "aria-haspopup=\"menu\"" in note_card


def test_filter_changes_clear_selection_and_batch_delete_reuses_one_preview():
    store = _read("stores/appStore.ts")
    header = _read("components/Header.tsx")

    assert store.count("selectedNoteIds: []") >= 7
    assert "deleteSelectedNotes: (preview: BatchDeletePreview)" in store
    assert "api.previewBatchDeleteNotes" not in store
    assert "await deleteSelectedNotes(batchDeletePreview)" in header
    assert "t('header.selectLoaded', { count: notes.length })" in header


def test_search_diagnostics_are_typed_preserved_and_shown_in_both_search_surfaces():
    api = _read("services/api.ts")
    store = _read("stores/appStore.ts")
    home = _read("pages/HomePage.tsx")
    palette = _read("components/CommandPalette.tsx")
    notice = _read("components/SearchDiagnosticsNotice.tsx")

    assert "export interface SearchDiagnostics" in api
    assert "searchDiagnostics?: SearchDiagnostics" in api
    assert "searchDiagnostics: data.search_diagnostics" in api
    assert "searchDiagnostics: SearchDiagnostics | null" in store
    assert "searchDiagnostics: response.searchDiagnostics ?? null" in store
    assert "<SearchDiagnosticsNotice diagnostics={searchDiagnostics}" in home
    assert "<SearchDiagnosticsNotice diagnostics={serverSearchDiagnostics}" in palette
    assert "scanned_files" in notice
    assert "limits.files" in notice
    assert 'role="status"' in notice


def test_note_fetches_use_latest_request_sequence_and_expose_inline_retry():
    store = _read("stores/appStore.ts")
    home = _read("pages/HomePage.tsx")

    assert "let notesRequestSequence = 0" in store
    assert "if (state.isLoading) return" not in store
    assert "const requestId = ++notesRequestSequence" in store
    assert store.count("requestId !== notesRequestSequence") >= 2
    assert "notesError: string | null" in store
    assert "retryFetchNotes: () =>" in store
    assert 'data-testid="notes-load-error"' in home
    assert "onClick={retryFetchNotes}" in home


def test_attachment_popup_renders_content_as_text_not_html():
    hook = _read("hooks/editor/useNoteAttachments.ts")

    html_sink = re.compile(
        r"\.write(?:ln)?\(|innerHTML|outerHTML|insertAdjacentHTML|srcdoc|createContextualFragment|DOMParser"
    )
    assert not html_sink.search(hook)
    assert "${attachmentContent}" not in hook
    assert "window.open('', '_blank')" in hook
    assert "doc.title = t('editor.attachment.contentTitle')" in hook
    assert "doc.createElement('pre')" in hook
    assert "pre.textContent = attachmentContent" in hook


def test_attachment_items_are_keyboard_operable_buttons():
    panel = _read("components/editor/AttachmentPanel.tsx")
    start = panel.index("attachments.map((att) => (")
    item = panel[start:panel.index("{/* Upload Button */}", start)]

    assert 'data-testid={`attachment-item-${att.id}`}' in item
    row_start = item.index("<div")
    row_tag = item[row_start:item.index("<", row_start + 1)]
    assert "onClick" not in row_tag
    assert item.count('type="button"') == 2
    open_button = item[item.index("<button"):item.index("</button>")]
    assert 'type="button"' in open_button
    assert "onClick={() => onLoadAttachment(att.id, att.is_auto_extracted)}" in open_button
    assert "focus-visible:ring-2" in open_button
    delete_button = item[item.rindex("<button"):item.rindex("</button>")]
    assert 'type="button"' in delete_button
    assert "aria-label={t('editor.attachment.delete')}" in delete_button
    assert "group-focus-within:opacity-100" in delete_button or "focus-visible:opacity-100" in delete_button
    assert "focus-visible:ring-2" in delete_button


def test_header_new_note_and_search_submit_navigate_home_from_other_routes():
    header = _read("components/Header.tsx")
    nav = "if (location.pathname !== '/') navigate('/')"

    add_start = header.index("const handleAddNote = () => {")
    add_body = header[add_start:header.index("}\n", add_start)]
    assert nav in add_body
    assert add_body.index(nav) < add_body.index("openEditor(null)")
    assert "onClick={handleAddNote}" in header
    assert "onClick={() => openEditor(null)}" not in header

    submit_start = header.index("const handleSearchSubmit")
    submit_body = header[submit_start:header.index("\n  }\n", submit_start)]
    assert nav in submit_body
    assert submit_body.index(nav) < submit_body.index("setSearchQuery(inputValue)")
