import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-db-only-write-expansion-selection.json"
FIRST_WRITE_PATH = ROOT / "docs" / "contracts" / "phase23-go-first-write-route-implementation.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_ROADMAP_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _candidates():
    return {candidate["id"]: candidate for candidate in _contract()["candidate_matrix"]}


def test_phase23_5_is_plan_only_and_depends_on_23_4_contract():
    contract = _contract()
    prior = json.loads(FIRST_WRITE_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "23.5"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-first-write-route-implementation.json"
    assert prior["phase"] == "23.4"
    assert contract["plan_only"] is True
    assert contract["runtime_change"] is False
    assert contract["go_write_implementation"] is False
    assert contract["live_execution_authorized"] is False
    assert contract["production_db_write"] is False
    assert contract["caddy_or_service_change"] is False
    assert contract["pi_deploy"] is False


def test_tag_rename_live_gate_is_deferred_and_live_owner_stays_python():
    decision = _contract()["stabilization_decision"]
    boundary = decision["default_runtime_boundary"]

    assert decision["tag_rename_candidate_status"] == "local_copied_db_parity_complete_only"
    assert decision["live_tag_rename_gate_before_next_db_only_write"] == "deferred"
    assert boundary["live_go_owned_surface"] == "hardened GET read-only Caddy-routed surface"
    assert boundary["tag_rename_live_owner"] == "Python"
    assert "--enable-tag-write" in boundary["go_tag_rename_status"]


def test_tags_nocase_discrepancy_is_deferred_and_blocks_tag_cud_expansion():
    gate = _contract()["schema_doc_discrepancy_gate"]

    assert gate["subject"] == "Tags.name NOCASE schema/documentation discrepancy"
    assert "COLLATE NOCASE" in gate["docs_claim"]
    assert "routes/tags.py duplicate checks use exact" in gate["runtime_truth"][1]
    assert gate["decision"] == "defer_schema_or_runtime_correction"
    assert "Go expansion of tag delete" in gate["blocked_until_resolved"]
    assert "Go expansion of tag merge" in gate["blocked_until_resolved"]
    assert "Schema migration to enforce NOCASE" in gate["not_authorized_in_23_5"]
    assert "docs/SCHEMA.md rewrite that claims a runtime correction was performed" in gate["not_authorized_in_23_5"]


def test_next_db_only_candidate_selects_category_update_only():
    candidates = _candidates()
    selected = candidates["category_update"]

    assert selected["decision"] == "selected_for_next_db_only_implementation_subgate"
    assert selected["route"] == "PUT /api/categories/<category_id>"
    assert selected["source"] == "routes/categories.py"
    assert selected["db_side_effects"] == [
        "Categories.name update when provided",
        "Categories.icon update when provided",
        "Categories.sort_order update when provided",
    ]
    assert selected["file_side_effects"] == []
    assert selected["external_side_effects"] == []
    assert selected["process_side_effects"] == []
    assert "single Categories row" in selected["why_selected"][1]
    assert candidates["category_create"]["decision"] == "deferred_after_category_update"
    assert candidates["notes_pin_archive"]["decision"] == "deferred"
    assert candidates["tag_delete"]["decision"] == "blocked_by_tag_nocase_discrepancy_and_cascade"
    assert candidates["tag_merge"]["decision"] == "blocked_by_tag_nocase_discrepancy_and_multi_step_rewrite"


def test_23_5_next_implementation_contract_is_local_category_update_subgate():
    next_contract = _contract()["next_implementation_contract"]

    assert next_contract["id"] == "23.5-next"
    assert next_contract["status"] == "blocked_until_explicit_user_approval"
    assert next_contract["selected_route"] == "PUT /api/categories/<category_id>"
    assert "Local/copied-DB only" in next_contract["scope"]
    assert "--enable-category-write" in next_contract["expected_enablement"]
    assert "default Go runtime remains GET read-only" in next_contract["expected_enablement"]
    assert "success returns {\"status\":\"success\",\"data\":{\"updated_notes_count\":0}}" in next_contract["request_response_parity"]
    assert any(
        "trimmed empty name returns 400 Category name cannot be empty" in item
        for item in next_contract["request_response_parity"]
    )
    assert "Update exactly one Categories row on success" in next_contract["transaction_and_state_invariants"]
    assert "Rollback leaves Categories unchanged on validation or SQL failure" in next_contract["transaction_and_state_invariants"]
    assert "Default Go runtime rejects PUT without the explicit category-write flag" in next_contract["fixture_plan"]
    assert any("empty-name 400" in item for item in next_contract["fixture_plan"])
    assert "Any schema migration or Tags.name uniqueness semantics change" in next_contract["stop_conditions"]


def test_23_5_does_not_authorize_implementation_live_schema_or_file_scope():
    blocked = set(_contract()["not_authorized_by_23_5"])

    assert "Go implementation of PUT /api/categories/<category_id>" in blocked
    assert "Live tag rename routing gate" in blocked
    assert "Live category write routing gate" in blocked
    assert "Production knowledge.db write" in blocked
    assert "Pi deployment" in blocked
    assert "Caddy route edit or reload" in blocked
    assert "systemd service change" in blocked
    assert "Schema migration" in blocked
    assert "Tag delete or merge Go ownership" in blocked
    assert "File upload or attachment ownership" in blocked


def test_docs_record_23_5_completion_and_next_subgate_details():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_roadmap = GO_ROADMAP_PATH.read_text(encoding="utf-8")

    assert "23.5 Go DB-only write expansion gate — ✅ Completed (2026-06-05)" in todo
    assert "docs/contracts/phase23-go-db-only-write-expansion-selection.json" in todo
    assert "23.5 Next DB-only write implementation subgate — ✅ Completed (2026-06-05)" in todo
    assert "23.5-next.1" in todo
    assert "PUT /api/categories/<category_id>" in todo
    assert "Phase 23.5 Go DB-only write expansion gate is complete" in architecture
    assert "Phase 23.5-next.1 Second Go DB-only write implementation subgate is complete" in architecture
    assert "Phase 23.5-next.2-4 category update closure is complete" in architecture
    assert "Phase 23.6 File / attachment ownership gate is complete as a plan-only inventory and selection gate" in architecture
    assert "Phase 23.6-next First Go file-read route implementation candidate is complete" in architecture
    assert "Phase 23.7 Migration / DB ownership decision gate is complete as plan-only" in architecture
    assert "Phase 23.9 Pi deployment rollout is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.5 Go DB-only write expansion gate is complete`" in go_roadmap
    assert "`23.5-next.1 Second Go DB-only write implementation subgate is complete`" in go_roadmap
    assert "`23.5-next.2-4 Category update parity hardening, rollback lock, and boundary closure is complete`" in go_roadmap
    assert "`23.6 File / attachment ownership gate` is complete as a plan-only inventory and selection gate" in go_roadmap
    assert "`23.6-next First Go file-read route implementation candidate` is complete" in go_roadmap
    assert "`23.7 Migration / DB ownership decision gate` is complete as plan-only" in go_roadmap
    assert "`23.9 Pi deployment rollout` is complete" in go_roadmap
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_roadmap

