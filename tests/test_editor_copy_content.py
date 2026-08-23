from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTE_EDITOR_PATH = ROOT / "frontend" / "src" / "components" / "NoteEditor.tsx"
EDITOR_TOOLBAR_PATH = ROOT / "frontend" / "src" / "components" / "editor" / "EditorToolbar.tsx"


def test_note_editor_copies_current_form_content_with_existing_feedback():
    source = NOTE_EDITOR_PATH.read_text(encoding="utf-8")

    assert "await navigator.clipboard.writeText(form.content)" in source
    assert "toast.success(t('noteCard.copied'))" in source
    assert "toast.error(t('noteCard.copyFailed'))" in source
    assert "onCopyContent={handleCopyContent}" in source


def test_copy_button_is_between_history_and_preview_toggle():
    source = EDITOR_TOOLBAR_PATH.read_text(encoding="utf-8")

    history_position = source.index("{/* History Button")
    copy_position = source.index('data-testid="editor-copy-content"')
    preview_position = source.index("{/* Preview Toggle */}")

    assert history_position < copy_position < preview_position
    assert "onCopyContent: () => void" in source
    assert "aria-label={t('noteCard.copyContent')}" in source
    assert "title={t('noteCard.copyContent')}" in source
    assert 'className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6"' in source
    assert 'className="hidden sm:inline">{t(\'editor.toolbar.history\')}</span>' in source
    assert 'className="hidden sm:inline">' in source
