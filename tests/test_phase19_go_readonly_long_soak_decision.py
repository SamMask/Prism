import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LONG_SOAK_PATH = ROOT / "docs" / "contracts" / "phase19-go-readonly-long-soak-decision.json"
SOAK_19_6_PATH = ROOT / "docs" / "contracts" / "phase19-go-readonly-soak-execution.json"


def _long_soak():
    return json.loads(LONG_SOAK_PATH.read_text(encoding="utf-8"))


def test_phase19_7_records_authorized_extended_soak_from_python_only_start():
    soak = _long_soak()

    assert soak["phase"] == "19.7"
    assert soak["live_execution_authorized"] is True
    assert soak["decision"].startswith("Execute a bounded extended")

    preflight = soak["preflight"]
    assert preflight["starting_state"] == "python_only"
    assert preflight["python_service_active"] is True
    assert preflight["routing_enabled"] is False
    assert preflight["go_sidecar_active"] is False
    assert preflight["port_5002_listening"] is False
    assert preflight["migration_status"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }


def test_phase19_7_requires_fresh_backup_and_query_only_sidecar():
    soak = _long_soak()

    backup = soak["fresh_backup"]
    assert backup["path"].endswith(".db")
    assert "long_soak" in backup["path"]
    assert backup["verified"] is True
    assert backup["schema_version"] == 16
    assert backup["notes_count"] == 196

    sidecar = soak["go_sidecar"]
    assert sidecar["bind"] == "127.0.0.1:5002"
    assert sidecar["healthz_status"] == 200
    assert sidecar["sqlite_query_only"] is True
    assert sidecar["schema_version"] == 16
    assert sidecar["localhost_only"] is True


def test_phase19_7_extended_soak_samples_gets_and_python_owned_routes():
    soak = _long_soak()
    extended = soak["extended_soak"]

    assert extended["sample_count"] == 10
    assert extended["sample_interval_seconds"] == 60
    assert extended["all_samples_passed"] is True
    assert extended["python_service_active_each_round"] is True
    assert extended["go_sidecar_active_each_round"] is True
    assert extended["go_write_method_logs_since_start"] == []

    routing = extended["routing_status_during_soak"]
    assert routing["enabled"] is True
    assert routing["base_url"] == "http://127.0.0.1:5002"
    assert routing["valid_base_url"] is True

    sampled = {item["path"]: item for item in extended["sampled_each_round"]}
    assert sampled["GET /api/test"]["required_header"] == "X-Prism-Go-Read-Routing: hit"
    assert sampled["GET /api/notes?per_page=1&page=1"]["required_header"] == "X-Prism-Go-Read-Routing: hit"
    assert sampled["GET /api/notes/114"]["required_header"] == "X-Prism-Go-Read-Routing: hit"
    assert sampled["GET /api/system/migration-status"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert sampled["POST /api/test"]["expected_status"] == 403
    assert sampled["POST /api/test"]["required_no_header"] == "X-Prism-Go-Read-Routing"


def test_phase19_7_rollback_final_state_is_python_only():
    soak = _long_soak()

    rollback = soak["rollback_drill"]
    assert rollback["completed"] is True
    final_state = rollback["final_state"]
    assert final_state["python_service_active"] is True
    assert final_state["routing_enabled"] is False
    assert final_state["routing_base_url"] is None
    assert final_state["representative_get_without_go_header"] is True
    assert final_state["go_sidecar_active"] is False
    assert final_state["port_5002_listening"] is False
    assert final_state["migration_current_version"] == 16
    assert final_state["migration_pending"] == []


def test_phase19_7_does_not_authorize_cutover_scope_and_gates_19_8():
    soak = _long_soak()

    assert soak["target_host"]["public_exposure_changed"] is False
    assert soak["target_host"]["caddy_route_changed"] is False
    assert soak["target_host"]["frontend_default_target_changed"] is False
    assert soak["result"]["not_a_cutover"] is True

    forbidden = soak["not_authorized_by_19_7"]
    assert "Caddy route changes" in forbidden
    assert "Frontend default API target changes" in forbidden
    assert "Go migrations" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden

    next_step = soak["allowed_next_step"]
    assert next_step["id"] == "19.8"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "plan-only" in next_step["first_step_if_approved"]


def test_phase19_6_points_to_19_7_gate_before_19_7_execution():
    phase19_6 = json.loads(SOAK_19_6_PATH.read_text(encoding="utf-8"))

    assert phase19_6["allowed_next_step"]["id"] == "19.7"
    assert phase19_6["allowed_next_step"]["requires_explicit_user_approval"] is True
