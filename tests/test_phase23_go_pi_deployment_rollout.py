import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-pi-deployment-rollout.json"
SOURCE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-local-smoke-artifact-release-boundary.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_phase23_9_records_authorized_pi_rollout_without_route_expansion():
    contract = _contract()
    source = json.loads(SOURCE_CONTRACT_PATH.read_text(encoding="utf-8"))
    runtime = contract["runtime_changes"]

    assert contract["phase"] == "23.9"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-local-smoke-artifact-release-boundary.json"
    assert source["allowed_next_step"]["id"] == "23.9.1"
    assert runtime["files_synced_to_pi"] is True
    assert runtime["frontend_dist_synced"] is True
    assert runtime["prism_service_restarted"] is True
    assert runtime["caddy_config_changed"] is False
    assert runtime["caddy_reloaded"] is False
    assert runtime["systemd_unit_changed"] is False
    assert runtime["go_route_ownership_expanded"] is False
    assert runtime["production_db_written_by_sync"] is False
    assert runtime["python_removed"] is False


def test_phase23_9_preflight_has_backups_and_route_ownership_evidence():
    preflight = _contract()["preflight"]
    backups = preflight["backups"]

    assert preflight["ssh_alias"] == "PI5Mask24"
    assert preflight["remote_path"] == "/home/mask070924/prism"
    assert preflight["prism_service"] == {"active": True, "enabled": True}
    assert preflight["caddy_service"] == {"active": True, "enabled": True, "validate": "passed"}
    assert preflight["migration_status_before_rollout"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }
    assert preflight["route_ownership_before_rollout"]["go_read_routing_enabled"] is False
    assert preflight["route_ownership_before_rollout"]["default_owner"] == "python"
    assert backups["db_backup"].endswith("prism_pre_23_9_rollout_20260606_015426.db")
    assert backups["data_snapshot"].endswith("prism_pre_23_9_data_snapshot_20260606_015426.tar.gz")
    assert backups["caddy_backup"].endswith("Caddyfile.prism-pre-23-9-rollout-20260606_015426.bak")
    assert len(backups["db_backup_sha256"]) == 64
    assert len(backups["data_snapshot_sha256"]) == 64
    assert len(backups["caddy_backup_sha256"]) == 64
    assert backups["db_counts"] == {
        "schema_version": 16,
        "notes": 198,
        "categories": 6,
        "tags": 128,
    }


def test_phase23_9_rollout_sync_excludes_production_data_and_keeps_caddy_validate_only():
    rollout = _contract()["rollout"]
    excludes = set(rollout["excluded_from_sync"])

    assert rollout["sync_method"] == "tar stream over SSH"
    assert rollout["remote_extract"] == "EXTRACT_OK"
    assert rollout["service_action"] == "sudo systemctl restart prism"
    assert rollout["caddy_action"] == "validate only; no config edit and no reload"
    assert rollout["systemd_action"] == "restart existing prism.service only; no unit file change"
    for excluded in [
        "knowledge.db",
        "knowledge.db-wal",
        "knowledge.db-shm",
        "static/uploads",
        "docs/attachments",
        "docs/notes",
        ".port_config",
        ".env",
        "app.log",
        "build",
    ]:
        assert excluded in excludes


def test_phase23_9_live_verification_keeps_python_primary_and_migrations_clean():
    live = _contract()["live_verification"]

    assert live["prism_service"] == {"active": True, "enabled": True}
    assert live["caddy_service"] == {"active": True, "enabled": True, "validate": "passed"}
    assert live["listening_ports"]["5000"] == "127.0.0.1 Python Flask prism.service"
    assert live["listening_ports"]["5002"].endswith("not selected by tested Caddy routes")
    assert live["api_test"]["status"] == "ok"
    assert live["api_test"]["notes_count"] == 198
    assert live["api_test"]["header"] == "no X-Prism-Go-Read-Routing header"
    assert live["server_version"]["version"] == "2.5"
    assert live["server_version"]["platform"] == "Linux"
    assert live["server_version"]["v2_mode"] is True
    assert live["migration_status_after_rollout"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }
    assert live["go_read_routing_status"]["enabled"] is False
    assert live["go_read_routing_status"]["default_owner"] == "python"
    assert live["notes_smoke"] == {
        "endpoint": "GET /api/notes?per_page=1",
        "status": "success",
        "total": 198,
    }
    assert live["journal_window"]["migration_log"] == "資料庫已是最新版本 (v16)"
    assert live["journal_window"]["port"] == 5000
    assert live["journal_window"]["new_errors_seen"] is False
    assert live["remote_file_checks"]["smoke_script_exists"] is True
    assert live["remote_file_checks"]["23_8_contract_exists"] is True


def test_phase23_9_boundaries_and_next_steps_are_locked():
    contract = _contract()
    blocked = set(contract["not_authorized_by_23_9"])

    assert contract["rollback"]["owner"] == "Python prism.service remains primary runtime and rollback owner"
    assert "Caddy route expansion" in blocked
    assert "systemd unit rewrite" in blocked
    assert "Go write route live ownership" in blocked
    assert "Go file/upload/import/export/cleanup/server maintenance ownership" in blocked
    assert "Frontend default API target change" in blocked
    assert "Python runtime removal" in blocked
    assert "Pillow removal" in blocked
    assert "Direct public internet exposure" in blocked
    assert contract["allowed_next_step"]["id"] == "23.10.1"
    assert contract["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert contract["parallel_deferred_track"]["id"] == "23.8-thumb.1"
    assert contract["parallel_deferred_track"]["requires_explicit_user_approval"] is True


def test_docs_record_23_9_completion_and_next_planning_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.9 Pi deployment rollout track — ✅ Completed (2026-06-06)" in todo
    assert "23.9.1** Pi preflight" in todo
    assert "docs/contracts/phase23-go-pi-deployment-rollout.json" in todo
    assert "23.9.2** Caddy/systemd rollout" in todo
    assert "23.9.3** Live verification" in todo
    assert "Phase 23.9 Pi deployment rollout is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.9 Pi deployment rollout` is complete" in go_report
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_report

