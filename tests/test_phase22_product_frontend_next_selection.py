import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase22-product-frontend-next-selection.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
HOME_PATH = ROOT / "frontend" / "src" / "pages" / "HomePage.tsx"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_phase22_2_is_authorized_plan_only_selection_gate_with_plain_language():
    contract = _contract()
    summary = contract["plain_language_summary"]

    assert contract["phase"] == "22.2"
    assert contract["explicit_user_approval"] is True
    assert contract["plan_only"] is True
    assert contract["frontend_implementation_performed"] is False
    assert contract["runtime_change_performed"] is False
    assert summary["title"] == "> **白話說明**："
    assert "does not implement UI changes" in summary["what_changes"]
    assert "Users will not see a product difference" in summary["user_visible_difference"]


def test_phase22_2_browser_evidence_records_candidate_findings():
    contract = _contract()
    evidence = contract["browser_evidence"]

    assert evidence["browser_plugin"].startswith("iab unavailable")
    assert evidence["settings_tab_deep_linking"]["url_after_deploy_tab_click"].endswith("/settings")
    assert evidence["settings_tab_deep_linking"]["deploy_panel_visible_after_reload"] is False
    assert evidence["settings_tab_deep_linking"]["appearance_panel_visible_after_reload"] is True
    assert evidence["prompt_builder_mobile_action_bar"]["action_bar_initially_in_viewport"] is False
    assert evidence["home_search_empty_state"]["search_result_title_visible"] is True
    assert evidence["home_search_empty_state"]["generic_no_notes_text_visible"] is True


def test_phase22_2_selects_only_home_search_empty_state_context_copy():
    contract = _contract()
    candidates = {candidate["id"]: candidate for candidate in contract["candidate_matrix"]}
    selected = contract["selected_candidate"]

    assert selected["id"] == "home_search_empty_state_context_copy"
    assert selected["phase"] == "22.3"
    assert candidates["home_search_empty_state_context_copy"]["recommended"] is True
    assert candidates["settings_tab_deep_linking"]["recommended"] is False
    assert candidates["prompt_builder_mobile_action_bar_polish"]["recommended"] is False
    assert selected["scope"].startswith("Frontend-only implementation")


def test_phase22_2_selected_candidate_matches_current_home_empty_state_gap():
    contract = _contract()
    home = HOME_PATH.read_text(encoding="utf-8")

    assert "searchQuery" in home
    assert "搜尋結果" in home
    assert "還沒有任何筆記" in home
    assert "Searching for a term with zero matches no longer shows the generic" in (
        contract["selected_candidate"]["success_criteria"][0]
    )


def test_phase22_2_forbids_implementation_and_runtime_scope():
    contract = _contract()
    forbidden = contract["not_authorized_by_22_2"]

    assert "Frontend implementation" in forbidden
    assert "New backend API or DB schema" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Pi deploy or live service reload" in forbidden
    assert "Caddy route expansion or reload" in forbidden
    assert "Go write/file/migration implementation" in forbidden
    assert "Direct public internet exposure" in forbidden


def test_phase22_2_todo_records_selection_and_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")

    assert "22.2 Product Frontend Backlog Next Selection Gate" in todo
    assert "這一步只是決定/盤點/規劃，不會實作功能" in todo
    assert "docs/contracts/phase22-product-frontend-next-selection.json" in todo
    assert "home_search_empty_state_context_copy" in todo
    assert "22.3 Home Search Empty State Context Copy" in todo

