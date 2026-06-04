import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTAKE_PATH = ROOT / "docs" / "contracts" / "phase22-product-frontend-backlog-intake.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
HEADER_PATH = ROOT / "frontend" / "src" / "components" / "Header.tsx"
PALETTE_PATH = ROOT / "frontend" / "src" / "components" / "CommandPalette.tsx"


def _intake():
    return json.loads(INTAKE_PATH.read_text(encoding="utf-8"))


def test_phase22_0_is_authorized_plan_only_product_frontend_intake():
    intake = _intake()

    assert intake["phase"] == "22.0"
    assert intake["explicit_user_approval"] is True
    assert intake["plan_only"] is True
    assert intake["selected_branch"] == "product_frontend_backlog"
    assert intake["runtime_change_performed"] is False
    assert intake["frontend_implementation_performed"] is False
    assert intake["backend_api_change_performed"] is False
    assert intake["schema_change_performed"] is False
    assert intake["live_pi_change_performed"] is False
    assert intake["caddy_change_performed"] is False
    assert intake["go_runtime_change_performed"] is False


def test_phase22_0_audit_covers_existing_frontend_workflows_without_reopening_redesign():
    intake = _intake()
    summary = intake["audit_summary"]

    assert "Phase 18.1 already completed" in summary["home_search_filter_navigation"]
    assert "Phase 18.2 already completed" in summary["reading_editor_workflow"]
    assert "Phase 18.3 already completed" in summary["prompt_builder_settings"]
    assert "Do not reopen Phase 18 as a broad redesign" in summary["not_reopened"]
    assert "frontend/src/components/Header.tsx" in intake["audit_sources"]
    assert "frontend/src/components/CommandPalette.tsx" in intake["audit_sources"]


def test_phase22_0_selects_only_command_palette_entrypoint_reliability():
    intake = _intake()
    candidates = {candidate["id"]: candidate for candidate in intake["candidate_matrix"]}
    selected = intake["selected_candidate"]

    assert selected["id"] == "command_palette_entrypoint_reliability"
    assert selected["phase"] == "22.1"
    assert candidates["command_palette_entrypoint_reliability"]["recommended"] is True
    assert candidates["settings_tab_deep_linking"]["recommended"] is False
    assert candidates["prompt_builder_mobile_action_bar_polish"]["recommended"] is False
    assert candidates["home_empty_state_context_actions"]["recommended"] is False


def test_phase22_0_selected_candidate_records_historical_frontend_finding():
    intake = _intake()
    selected = intake["selected_candidate"]
    header = HEADER_PATH.read_text(encoding="utf-8")
    palette = PALETTE_PATH.read_text(encoding="utf-8")

    assert "The Header command palette button currently dispatches a synthetic Ctrl+K KeyboardEvent" in (
        intake["candidate_matrix"][0]["finding"]
    )
    assert "window.dispatchEvent(new KeyboardEvent('keydown'" not in header
    assert "window.addEventListener('keydown'" in palette
    assert "Header command palette button opens the palette without dispatching a synthetic KeyboardEvent." in selected["success_criteria"]
    assert "Ctrl+K / Cmd+K still toggles the palette." in selected["success_criteria"]
    assert "frontend/src/components/Header.tsx" in selected["files_likely_touched"]
    assert "frontend/src/components/CommandPalette.tsx" in selected["files_likely_touched"]


def test_phase22_0_forbids_implementation_and_runtime_scope():
    intake = _intake()
    forbidden = intake["not_authorized_by_22_0"]

    assert "Frontend implementation" in forbidden
    assert "New backend API or DB schema" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Pi deploy or live service reload" in forbidden
    assert "Caddy route expansion or reload" in forbidden
    assert "Go attachment file body scanning" in forbidden
    assert "Go write/file/migration implementation" in forbidden
    assert "Direct public internet exposure" in forbidden


def test_phase22_0_next_step_is_22_1_explicit_implementation_gate():
    intake = _intake()
    next_step = intake["allowed_next_step"]

    assert next_step["id"] == "22.1"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("Implement only the selected frontend-only")
    assert "Frontend implementation" in next_step["not_authorized_without_approval"]
    assert "New backend API or DB schema" in next_step["not_authorized_without_approval"]


def test_phase22_0_todo_records_audit_selection_and_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "22.0 Product Frontend Backlog Intake Gate" in todo
    assert "docs/contracts/phase22-product-frontend-backlog-intake.json" in todo
    assert "command_palette_entrypoint_reliability" in todo
    assert "22.1 Command Palette Entrypoint Reliability" in todo
