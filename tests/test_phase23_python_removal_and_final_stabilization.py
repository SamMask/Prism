import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "docs" / "contracts" / "phase23-python-removal-decision.json"
STABILIZATION_PATH = ROOT / "docs" / "contracts" / "phase23-final-stabilization.json"
AUDIT_PATH = ROOT / "docs" / "contracts" / "phase23-go-ownership-closure-audit.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"


def _decision():
    return json.loads(DECISION_PATH.read_text(encoding="utf-8"))


def _stabilization():
    return json.loads(STABILIZATION_PATH.read_text(encoding="utf-8"))


def test_23_10_2_decides_to_retain_python_normal_path_without_runtime_change():
    decision = _decision()
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    assert decision["phase"] == "23.10.2"
    assert decision["status"] == "completed"
    assert decision["explicit_user_approval"] is True
    assert decision["source_contract"] == "docs/contracts/phase23-go-ownership-closure-audit.json"
    assert audit["allowed_next_step"]["id"] == "23.10.2"
    assert decision["plan_only"] is True
    assert decision["decision"] == "retain_python_normal_path"
    assert decision["decision_basis"]["python_removal_readiness_from_23_10_1"] == "blocked"
    assert all(changed is False for changed in decision["runtime_changes"].values())
    assert decision["runtime_changes"]["python_removed"] is False
    assert decision["normal_runtime_strategy"]["primary_runtime"] == "Python prism.service"
    assert decision["normal_runtime_strategy"]["migrations_owner"] == "Python migrations.run_migrations() remains live migration owner"


def test_23_10_2_blocks_python_removal_go_expansion_and_public_exposure():
    blocked = set(_decision()["blocked_actions_after_decision"])

    assert "Remove Python backend, venv, or prism.service from the normal path" in blocked
    assert "Route production writes to Go" in blocked
    assert "Route production file/upload/import/export/cleanup/server maintenance to Go" in blocked
    assert "Replace Python migration runner with Go migration runner" in blocked
    assert "Change frontend default API target to Go" in blocked
    assert "Remove Pillow or Python thumbnail path through this gate" in blocked
    assert "Expose Prism directly to public internet" in blocked


def test_23_10_3_records_local_build_artifact_api_and_browser_stabilization():
    stabilization = _stabilization()
    local = stabilization["local_stabilization"]

    assert stabilization["phase"] == "23.10.3"
    assert stabilization["status"] == "completed"
    assert stabilization["source_contract"] == "docs/contracts/phase23-python-removal-decision.json"
    assert local["frontend_typecheck"]["status"] == "passed"
    assert local["frontend_build"]["status"] == "passed"
    assert "dist/index.html" in local["frontend_build"]["dist_assets_seen"]
    assert local["go_local_artifact_smoke"]["status"] == "passed"
    assert local["go_local_artifact_smoke"]["source_db_hash_guard"] == "passed"
    assert local["local_api_smoke"]["api_test"]["status"] == "ok"
    assert local["local_api_smoke"]["server_version"] == {
        "version": "2.4.9",
        "platform": "Windows",
        "v2_mode": True,
    }
    assert local["local_api_smoke"]["migration_status"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }
    assert local["browser_smoke"]["status"] == "passed"
    assert local["browser_smoke"]["screenshot"] == "build/phase23_10_browser/home.png"


def test_23_10_3_records_pi_backup_sync_restart_and_live_python_ownership():
    stabilization = _stabilization()
    runtime = stabilization["runtime_changes"]
    preflight = stabilization["pi_preflight"]
    live = stabilization["pi_live_verification"]

    assert runtime["files_synced_to_pi"] is True
    assert runtime["frontend_dist_synced"] is True
    assert runtime["prism_service_restarted"] is True
    assert runtime["caddy_config_changed"] is False
    assert runtime["caddy_reloaded"] is False
    assert runtime["systemd_unit_changed"] is False
    assert runtime["go_route_ownership_expanded"] is False
    assert runtime["python_removed"] is False
    assert runtime["production_db_written_by_sync"] is False
    assert preflight["ssh_alias"] == "PI5Mask24"
    assert preflight["prism_service"] == {"active": True, "enabled": True}
    assert preflight["caddy_service"] == {"active": True, "enabled": True, "validate": "passed"}
    assert preflight["backups"]["db_backup"].endswith("prism_pre_23_10_3_stabilization_20260606_022312.db")
    assert len(preflight["backups"]["db_backup_sha256"]) == 64
    assert live["prism_service"] == {"active": True, "enabled": True}
    assert live["caddy_service"] == {"active": True, "enabled": True, "validate": "passed"}
    assert live["api_test"]["status"] == "ok"
    assert live["api_test"]["notes_count"] == 198
    assert live["api_test"]["header"] == "no X-Prism-Go-Read-Routing header"
    assert live["server_version"] == {
        "version": "2.4.9",
        "platform": "Linux",
        "v2_mode": True,
    }
    assert live["migration_status_after_sync"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }
    assert live["go_read_routing_status"]["enabled"] is False
    assert live["go_read_routing_status"]["default_owner"] == "python"
    assert live["notes_smoke"]["total"] == 198
    assert live["notes_smoke"]["header"] == "no X-Prism-Go-Read-Routing header"
    assert live["journal_window"]["service_restart_seen"] is True
    assert live["journal_window"]["new_errors_seen"] is False


def test_23_10_3_keeps_forbidden_scope_and_closes_phase23_with_retained_python():
    stabilization = _stabilization()
    blocked = set(stabilization["not_authorized_by_23_10_3"])
    next_steps = {step["id"]: step for step in stabilization["allowed_next_steps"]}

    assert stabilization["rollback"]["owner"] == "Python prism.service remains primary runtime and rollback owner"
    assert "Python runtime removal" in blocked
    assert "Caddy route expansion" in blocked
    assert "Go write route live ownership" in blocked
    assert "Go migration runner live ownership" in blocked
    assert "Frontend default API target change" in blocked
    assert "Direct public internet exposure" in blocked
    assert stabilization["phase23_closure"]["status"] == "closed_with_retained_python_normal_path"
    assert next_steps["python-packaging-removal-roadmap-A-E"]["requires_explicit_user_approval"] is True
    assert "Do not add decision gates" in next_steps["python-packaging-removal-roadmap-A-E"]["scope"]
    assert next_steps["post-23-release-hygiene"]["requires_explicit_user_approval"] is True


def test_docs_record_23_10_2_23_10_3_completion_and_phase23_closure():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.10.2** Python removal decision" in todo
    assert "docs/contracts/phase23-python-removal-decision.json" in todo
    assert "23.10.3** Final stabilization window" in todo
    assert "docs/contracts/phase23-final-stabilization.json" in todo
    assert "Phase 23.10.2 Python removal decision is complete" in architecture
    assert "Phase 23.10.3 Final stabilization window is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.10.2 Python removal decision` is complete" in go_report
    assert "`23.10.3 Final stabilization window` is complete" in go_report
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_report

