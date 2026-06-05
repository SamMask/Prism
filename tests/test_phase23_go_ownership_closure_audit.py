import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-ownership-closure-audit.json"
SOURCE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-pi-deployment-rollout.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_23_10_1_is_plan_only_and_does_not_change_runtime_ownership():
    contract = _contract()
    source = json.loads(SOURCE_CONTRACT_PATH.read_text(encoding="utf-8"))
    runtime = contract["runtime_changes"]

    assert contract["phase"] == "23.10.1"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-pi-deployment-rollout.json"
    assert source["allowed_next_step"]["id"] == "23.10.1"
    assert contract["plan_only"] is True
    assert all(changed is False for changed in runtime.values())
    assert runtime["python_removed"] is False
    assert runtime["go_route_ownership_expanded"] is False
    assert runtime["pi_deploy"] is False
    assert runtime["caddy_config_changed"] is False
    assert runtime["prism_service_restarted"] is False


def test_live_runtime_truth_keeps_python_primary_after_23_9():
    live = _contract()["live_runtime_truth_after_23_9"]

    assert live["primary_runtime"] == "Python prism.service"
    assert live["public_tested_owner"] == "python"
    assert live["go_read_routing_enabled"] is False
    assert "GET /api/test" in live["tested_routes_without_go_header"]
    assert "GET /api/system/go-read-routing" in live["tested_routes_without_go_header"]
    assert live["go_sidecar"]["ownership_status"] == "not selected by tested Caddy routes in 23.9"


def test_go_candidate_matrix_distinguishes_implemented_from_live_owned():
    matrix = _contract()["ownership_matrix"]
    candidates = {entry["id"]: entry for entry in matrix["go_implemented_candidates"]}

    core = candidates["go_health_and_core_read"]
    assert "GET /api/test" in core["routes"]
    assert "GET /api/notes/<numeric id>" in core["routes"]
    assert core["live_status_after_23_9"] == "Python remains owner for tested public routes"

    db_writes = candidates["go_local_db_only_write_candidates"]
    assert db_writes["routes"] == ["PUT /api/tags/<id>", "PUT /api/categories/<id>"]
    assert "local/copied-DB" in db_writes["owner_status"]
    assert "not live-routed" in db_writes["live_status_after_23_9"]

    attachment = candidates["go_local_attachment_text_read_candidate"]
    assert attachment["routes"] == ["GET /api/attachments/<id> text JSON branch"]
    assert "--enable-attachment-text-read" in attachment["runtime_guard"]
    assert "raw=true/binary/send_file remain blocked" in attachment["runtime_guard"]

    spa = candidates["go_local_packaged_spa"]
    assert spa["owner_status"] == "local artifact capability only"
    assert "Pi production SPA serving remains Python/Flask" in spa["live_status_after_23_9"]


def test_retained_python_surfaces_cover_writes_files_system_migrations_and_static():
    retained = {entry["id"]: entry for entry in _contract()["ownership_matrix"]["retained_python_owned_surfaces"]}

    assert "POST /api/notes" in retained["notes_write_and_nested_actions"]["surfaces"]
    assert "POST /api/notes/<id>/pin" in retained["notes_write_and_nested_actions"]["surfaces"]
    assert "POST /api/categories" in retained["category_tag_live_writes"]["surfaces"]
    assert "PUT /api/tags/<id> live route" in retained["category_tag_live_writes"]["surfaces"]
    assert "POST /api/upload/url" in retained["files_uploads_attachments_cleanup_import_export"]["surfaces"]
    assert "GET /api/attachments/<id> raw/binary/send_file" in retained["files_uploads_attachments_cleanup_import_export"]["surfaces"]
    assert "GET /api/export/db" in retained["files_uploads_attachments_cleanup_import_export"]["surfaces"]
    assert "GET /api/system/migration-status" in retained["system_server_config_and_maintenance"]["surfaces"]
    assert "GET /api/server/logs" in retained["system_server_config_and_maintenance"]["surfaces"]
    assert "migrations.run_migrations()" in retained["migrations_and_schema_upgrade"]["surfaces"]
    assert "Flask V2 SPA serving" in retained["frontend_static_live_serving"]["surfaces"]


def test_python_removal_is_blocked_until_critical_surfaces_have_a_decision():
    readiness = _contract()["python_removal_readiness"]
    blocked = set(readiness["blocked_actions"])

    assert readiness["decision"] == "blocked"
    assert "Critical live writes, files, migrations" in readiness["reason"]
    assert "Remove Python from normal runtime path" in blocked
    assert "Disable Python prism.service" in blocked
    assert "Promote Go writes/files/migrations to live ownership" in blocked
    assert "Remove Pillow or Python thumbnail path" in blocked
    assert "Expose Prism directly to public internet" in blocked
    assert any("verified Go implementation or a signed retained-Python release strategy" in item for item in readiness["minimum_before_any_removal"])


def test_docs_record_23_10_1_completion_and_next_decision_gate():
    contract = _contract()
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert contract["allowed_next_step"]["id"] == "23.10.2"
    assert contract["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert contract["allowed_next_step"]["expected_decision"].startswith("retain Python unless")
    assert contract["parallel_deferred_track"]["id"] == "23.8-thumb.1"
    assert "23.10 Python reduction and final stabilization — Final Stage Only" in todo
    assert "23.10.1** Ownership closure audit" in todo
    assert "docs/contracts/phase23-go-ownership-closure-audit.json" in todo
    assert "23.10.2** Python removal decision" in todo
    assert "Phase 23.10.1 Ownership closure audit is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.10.1 Ownership closure audit` is complete" in go_report
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_report
