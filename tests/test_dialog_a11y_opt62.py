"""PRISM-OPT-62 source locks; behavior is covered by e2e/test_dialog_a11y.py."""

from pathlib import Path

UI = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "ui"


def test_modal_is_a_labelled_modal_dialog_with_a_focus_layer():
    source = (UI / "Modal.tsx").read_text(encoding="utf-8")
    assert 'role="dialog"' in source and 'aria-modal="true"' in source
    assert "aria-labelledby" in source
    assert "export function useDialogLayer" in source
    assert "useDialogLayer(isOpen" in source
    assert "'Escape'" not in source.split("export function Modal")[1]


def test_confirm_dialog_uses_the_shared_layer_and_has_no_own_escape_listener():
    source = (UI / "ConfirmDialog.tsx").read_text(encoding="utf-8")
    assert 'role="alertdialog"' in source and 'aria-modal="true"' in source
    assert "useDialogLayer(" in source
    assert "addEventListener" not in source
    assert "pendingResolve.current?.(false)" in source
