import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-python-runtime-ownership-closure.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_b_runtime_ownership_closure_is_final_retained_python_without_runtime_mutation():
    contract = _contract()
    runtime = contract["runtime_changes"]

    assert contract["phase"] == "python-packaging-removal-B"
    assert contract["status"] == "completed_final_retained_python_closure"
    assert contract["explicit_user_approval"] is True
    assert contract["closure_decision"]["python_removal_ready"] is False
    assert contract["closure_decision"]["b_completion_standard_met"] is False
    assert contract["closure_decision"]["b_closed"] is True
    assert contract["closure_decision"]["no_python_packaging_track_closed"] is True
    assert contract["final_closure"]["no_auto_next_detail"] is True
    assert contract["final_closure"]["no_b_next"] is True
    assert contract["final_closure"]["no_start_c_d_e"] is True
    assert "phase23-go-ownership-closure-audit.json" in contract["source_contracts"][0]
    assert all(changed is False for changed in runtime.values())
    assert runtime["python_removed"] is False
    assert runtime["go_route_ownership_expanded"] is False
    assert runtime["pi_deploy"] is False


def test_b_classification_distinguishes_go_owned_external_and_blocking_surfaces():
    surfaces = _contract()["surface_classification"]
    go_owned = {entry["id"]: entry for entry in surfaces["go_owned_or_package_ready"]}
    external = {entry["id"]: entry for entry in surfaces["external_maintenance_candidates"]}
    blockers = {entry["id"]: entry for entry in surfaces["request_time_python_blockers"]}

    assert go_owned["thumbnail_generation_helper"]["classification"] == "go_owned"
    assert "not_package_ready" == go_owned["core_get_read_candidate"]["classification"]
    assert external["server_dashboard_process_controls"]["classification"] == "external_maintenance_candidate"
    assert "GET /api/server/logs" in external["server_dashboard_process_controls"]["surfaces"]
    assert "POST /api/notes" in blockers["notes_write_actions_history_batch"]["surfaces"]
    assert "PUT /api/tags/<id>" in blockers["category_tag_live_writes"]["surfaces"]
    assert "POST /api/upload/url" in blockers["files_uploads_attachments_cleanup"]["surfaces"]
    assert "GET /api/export/db" in blockers["import_export_and_long_content"]["surfaces"]
    assert "GET/POST/PUT/DELETE /api/prompt-options*" in blockers["prompt_wizard_options"]["surfaces"]
    assert "migrations.run_migrations() startup path" in blockers["migrations_schema_status_and_db_maintenance"]["surfaces"]
    assert "Python prism.service rollback owner" in blockers["frontend_static_and_rollback_owner"]["surfaces"]


def test_b_blocks_c_d_e_until_request_time_python_surfaces_are_closed():
    contract = _contract()
    blocked = set(contract["not_authorized_by_B_assessment"])
    remaining = contract["unmet_no_python_completion_criteria_closed_as_retained_python"]

    assert "Start C. Go packaged runtime release candidate" in blocked
    assert "Start D. Live cutover and rollback proof" in blocked
    assert "Start E. Python package deletion" in blocked
    assert "Remove Python backend" in blocked
    assert "Declare no-Python packaged runtime complete" in blocked
    assert any("Every request_time_python_blocker" in item for item in remaining)
    assert any("normal packaged runtime does not call Python" in item for item in remaining)


def test_b_records_executed_notes_work_without_active_next_detail():
    contract = _contract()
    next_detail = contract["executed_notes_bundle_candidate"]
    promotion = contract["executed_notes_promotion_decision"]

    assert "recommended_next_detail" not in contract
    assert "recommended_next_detail_after_b_next_1" not in contract
    assert next_detail["id"] == "B-next.1"
    assert next_detail["title"] == "Notes write/actions/history/batch packaged-runtime ownership bundle"
    assert "primary request-time blocker" in next_detail["why_first"]
    assert "copied DB fixtures first" in " ".join(next_detail["scope"])
    assert next_detail["status_after_execution"] == "completed_local_candidate"
    assert next_detail["result_contract"] == "docs/contracts/phase23-b-next-notes-write-bundle.json"
    assert "historical local candidate only" in next_detail["final_role"]
    assert promotion["id"] == "B-next.2"
    assert promotion["status_after_execution"] == "completed_decision_no_promotion"
    assert promotion["no_auto_next_detail"] is True


def test_docs_record_b_final_closure_without_active_next_detail():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "B. Runtime ownership closure for Python removal — final retained-Python closure" in todo
    assert "docs/contracts/phase23-python-runtime-ownership-closure.json" in todo
    assert "B-next.1 Notes write/actions/history/batch packaged-runtime ownership bundle" in todo
    assert "不再新增或自動排 `B-next.*`" in todo
    assert "C/D/E 不啟動" in todo
    assert "Phase 23 Python packaging removal roadmap B runtime ownership closure is complete as `completed_final_retained_python_closure`" in architecture
    assert "no further B-next item is created automatically" in architecture
    assert "`B. Runtime ownership closure for Python removal` is complete as `completed_final_retained_python_closure`" in go_report
    assert "B-next.1 Notes write/actions/history/batch packaged-runtime ownership bundle" in go_report
