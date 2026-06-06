import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-file-attachment-ownership-gate.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
ATTACHMENTS_ROUTE_PATH = ROOT / "routes" / "attachments.py"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_phase23_6_contract_is_plan_only_and_does_not_authorize_file_runtime_changes():
    contract = _contract()

    assert contract["phase"] == "23.6"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-category-update-closure.json"
    assert contract["plan_only"] is True
    assert contract["runtime_change"] == "none"
    assert contract["go_file_route_implemented"] is False
    assert contract["live_execution_authorized"] is False
    assert contract["production_db_write"] is False
    assert contract["filesystem_write_authorized"] is False
    assert contract["filesystem_delete_authorized"] is False
    assert contract["caddy_or_service_change"] is False
    assert contract["pi_deploy"] is False


def test_phase23_6_inventory_splits_file_surfaces_and_rejects_broad_first_route_scope():
    inventory = {item["id"]: item for item in _contract()["file_ownership_inventory"]}

    expected = {
        "attachments_metadata_list",
        "attachment_text_content_read",
        "attachment_raw_or_binary_read",
        "attachment_upload",
        "attachment_delete",
        "attachment_separate_restore",
        "upload_images",
        "notes_image_cleanup_on_delete",
        "cleanup_routes",
        "export_routes",
        "import_routes",
        "server_backup_logs",
    }
    assert expected <= set(inventory)
    assert inventory["attachment_text_content_read"]["decision"] == "selected_for_23_6_next"
    assert inventory["attachments_metadata_list"]["decision"] == "defer_as_db_only_precursor"
    assert inventory["upload_images"]["decision"] == "defer"
    assert inventory["cleanup_routes"]["decision"] == "defer"
    assert inventory["export_routes"]["decision"] == "defer"
    assert inventory["import_routes"]["decision"] == "defer"
    assert "filesystem_write" not in inventory["attachment_text_content_read"]["side_effects"]
    assert "filesystem_delete" not in inventory["attachment_text_content_read"]["side_effects"]
    assert "bulk_filesystem_scan" in inventory["cleanup_routes"]["side_effects"]
    assert "remote_fetch" in inventory["upload_images"]["side_effects"]
    assert "zip_response" in inventory["export_routes"]["side_effects"]


def test_phase23_6_selects_only_text_attachment_content_for_next_candidate():
    selected = _contract()["selected_first_file_candidate"]

    assert selected["id"] == "attachment_text_content_read"
    assert selected["phase"] == "23.6-next"
    assert selected["route"] == "GET /api/attachments/<attachment_id>"
    assert selected["required_gate"] == "local_copied_db_and_copied_files_only"
    assert "Text JSON branch only" in selected["scope"]
    assert "default Go runtime remains get-read-only" in selected["required_enablement"]
    assert "raw=true send_file behavior" in selected["deferred_branches"]
    assert "attachment upload" in selected["deferred_branches"]
    assert "cleanup routes" in selected["deferred_branches"]
    assert "import/export routes" in selected["deferred_branches"]


def test_phase23_6_locks_backup_restore_and_path_safety_before_file_write_candidates():
    contract = _contract()
    backup = contract["backup_restore_contract"]
    path_safety = contract["path_safety_contract"]

    assert backup["read_only_candidate"]["db_backup_required"] == "copied DB fixture only; no production DB and no live Pi DB"
    assert backup["read_only_candidate"]["filesystem_backup_required"] == "copied docs/attachments fixture only; no production attachment tree mutation"
    assert "remain unchanged" in backup["read_only_candidate"]["rollback_expectation"]
    assert backup["future_file_write_candidates"]["db_backup_required"] is True
    assert backup["future_file_write_candidates"]["filesystem_backup_required"] is True
    assert backup["future_file_write_candidates"]["partial_failure_rollback_required"] is True
    assert path_safety["selected_allowed_root"] == "docs/attachments"
    assert path_safety["reserved_later_root"] == "static/uploads"
    for rejected in [
        ".. traversal",
        "absolute path",
        "Windows drive or volume path",
        "UNC path",
        "symlink escape outside data dir",
        "unsupported extension for text branch",
    ]:
        assert rejected in path_safety["must_reject"]
    assert "raw=true remains Python-owned until widened" in path_safety["must_match_python_for"]


def test_phase23_6_does_not_authorize_live_broad_file_or_python_removal_scope():
    blocked = set(_contract()["not_authorized_by_23_6"])

    assert "Go file route implementation in this gate" in blocked
    assert "Attachment upload Go ownership" in blocked
    assert "Attachment delete Go ownership" in blocked
    assert "Raw or binary attachment response Go ownership" in blocked
    assert "Upload image Go ownership" in blocked
    assert "Cleanup route Go ownership" in blocked
    assert "Import or export Go ownership" in blocked
    assert "Server backup or log route Go ownership" in blocked
    assert "Production knowledge.db write" in blocked
    assert "Production attachment or upload filesystem mutation" in blocked
    assert "Pi deployment" in blocked
    assert "Caddy route edit or reload" in blocked
    assert "Python route removal" in blocked
    assert "Python packaging removal" in blocked
    assert "Public exposure expansion" in blocked


def test_phase23_6_selected_candidate_matches_existing_python_text_branch_anchor():
    source = ATTACHMENTS_ROUTE_PATH.read_text(encoding="utf-8")

    assert "@attachments_bp.route('/attachments/<int:attachment_id>', methods=['GET'])" in source
    assert "def get_attachment_content(attachment_id):" in source
    assert "request.args.get('raw', 'false').lower() == 'true'" in source
    assert "send_file(full_path, as_attachment=False)" in source
    assert "with open(full_path, 'r', encoding='utf-8') as f:" in source
    assert "'content': content" in source


def test_phase23_6_docs_record_completion_and_next_subgate():
    contract = _contract()
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert contract["allowed_next_step"]["id"] == "23.6-next"
    assert contract["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "23.6 File / attachment ownership gate — ✅ Completed (2026-06-06)" in todo
    assert "docs/contracts/phase23-go-file-attachment-ownership-gate.json" in todo
    assert "23.6-next First Go file-read route implementation candidate — ✅ Completed (2026-06-06)" in todo
    assert "Phase 23.6 File / attachment ownership gate is complete as a plan-only inventory and selection gate" in architecture
    assert "Phase 23.6-next First Go file-read route implementation candidate is complete" in architecture
    assert "Phase 23.7 Migration / DB ownership decision gate is complete as plan-only" in architecture
    assert "Phase 23.9 Pi deployment rollout is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.6 File / attachment ownership gate` is complete as a plan-only inventory and selection gate" in go_report
    assert "`23.6-next First Go file-read route implementation candidate` is complete" in go_report
    assert "`23.7 Migration / DB ownership decision gate` is complete as plan-only" in go_report
    assert "`23.9 Pi deployment rollout` is complete" in go_report
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_report

