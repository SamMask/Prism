import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase22-command-palette-entrypoint-reliability.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
HEADER_PATH = ROOT / "frontend" / "src" / "components" / "Header.tsx"
PALETTE_PATH = ROOT / "frontend" / "src" / "components" / "CommandPalette.tsx"
STORE_PATH = ROOT / "frontend" / "src" / "stores" / "appStore.ts"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_phase22_1_contract_records_implementation_scope_and_plain_language_summary():
    contract = _contract()
    summary = contract["plain_language_summary"]

    assert contract["phase"] == "22.1"
    assert contract["explicit_user_approval"] is True
    assert contract["plan_only"] is False
    assert contract["frontend_implementation_performed"] is True
    assert contract["backend_api_change_performed"] is False
    assert contract["schema_change_performed"] is False
    assert contract["go_runtime_change_performed"] is False
    assert summary["title"] == "> **白話說明**："
    assert "pretending the user pressed Ctrl+K" in summary["what_changes"]
    assert "Users should not see a feature change" in summary["user_visible_difference"]
    assert "backend APIs" in summary["does_not_change"]


def test_header_button_uses_explicit_palette_open_action_not_synthetic_keyboard_event():
    header = HEADER_PATH.read_text(encoding="utf-8")

    assert "openCommandPalette" in header
    assert "onClick={openCommandPalette}" in header
    assert "window.dispatchEvent(new KeyboardEvent('keydown'" not in header
    assert "data-testid=\"command-palette-button\"" in header


def test_command_palette_keyboard_shortcut_uses_shared_store_toggle_state():
    palette = PALETTE_PATH.read_text(encoding="utf-8")
    store = STORE_PATH.read_text(encoding="utf-8")

    assert "isCommandPaletteOpen: isOpen" in palette
    assert "closeCommandPalette" in palette
    assert "toggleCommandPalette" in palette
    assert "window.addEventListener('keydown'" in palette
    assert "toggleCommandPalette()" in palette
    assert "setIsOpen" not in palette

    assert "isCommandPaletteOpen: boolean" in store
    assert "openCommandPalette: () => void" in store
    assert "closeCommandPalette: () => void" in store
    assert "toggleCommandPalette: () => void" in store
    assert "isCommandPaletteOpen: false" in store


def test_phase22_1_todo_records_plain_language_and_completion():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "22.1 Command Palette Entrypoint Reliability" in todo
    assert "> **白話說明**：" in todo
    assert "這一步會真的改 Command Palette 的開啟流程" in todo
    assert "docs/contracts/phase22-command-palette-entrypoint-reliability.json" in todo
    assert "- [x] **22.1.1** Explicit palette open path" in todo
    assert "22.2 Product Frontend Backlog Next Selection Gate" in todo


def test_phase22_1_forbids_runtime_and_scope_expansion():
    contract = _contract()
    forbidden = contract["not_changed"]

    assert "Backend API" in forbidden
    assert "DB schema or migrations" in forbidden
    assert "Frontend default API target" in forbidden
    assert "Pi deploy or live service reload" in forbidden
    assert "Caddy route expansion or reload" in forbidden
    assert "Go write/file/migration implementation" in forbidden
    assert "Direct public internet exposure" in forbidden

