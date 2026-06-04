import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOAK_PATH = ROOT / "docs" / "contracts" / "phase19-go-caddy-extended-readonly-soak.json"
DRILL_19_9_PATH = ROOT / "docs" / "contracts" / "phase19-go-caddy-readonly-routing-drill.json"


def _soak():
    return json.loads(SOAK_PATH.read_text(encoding="utf-8"))


def test_phase19_10_records_authorized_extended_caddy_soak_from_python_only():
    soak = _soak()

    assert soak["phase"] == "19.10"
    assert soak["live_execution_authorized"] is True
    assert soak["decision"].startswith("Execute a bounded extended Caddy-level")

    preflight = soak["preflight"]
    assert preflight["starting_state"] == "python_only"
    assert preflight["python_service_active"] is True
    assert preflight["caddy_service_active"] is True
    assert preflight["go_sidecar_active"] is False
    assert preflight["routing_enabled"] is False
    assert preflight["representative_get_without_go_header"] is True
    assert preflight["port_5002_listening"] is False
    assert preflight["caddy_validate_before_change"] is True
    assert preflight["migration_status"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }


def test_phase19_10_has_fresh_backups_and_localhost_query_only_sidecar():
    soak = _soak()

    db_backup = soak["backups"]["db_backup"]
    assert db_backup["path"].endswith(".db")
    assert "caddy_extended_soak" in db_backup["path"]
    assert db_backup["verified"] is True
    assert db_backup["schema_version"] == 16
    assert db_backup["notes_count"] == 196

    caddy_backup = soak["backups"]["caddy_backup"]
    assert caddy_backup["path"].endswith(".bak")
    assert caddy_backup["created"] is True
    assert caddy_backup["used_for_rollback"] is True

    sidecar = soak["go_sidecar"]
    assert sidecar["bind"] == "127.0.0.1:5002"
    assert sidecar["sqlite_query_only"] is True
    assert sidecar["schema_version"] == 16
    assert sidecar["public_bind_allowed"] is False


def test_phase19_10_caddy_policy_remains_get_only_and_python_owned_elsewhere():
    soak = _soak()
    policy = soak["caddy_soak_config"]["route_policy"]

    assert policy["go_routed"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<id>",
    ]

    python_owned = " ".join(policy["python_owned"])
    assert "POST / PUT / DELETE / PATCH" in python_owned
    assert "GET /api/system/migration-status" in python_owned
    assert "GET /api/system/go-read-routing" in python_owned
    assert "frontend SPA assets" in python_owned
    assert "database migrations" in python_owned
    assert soak["caddy_soak_config"]["go_response_header_added_by_caddy"] == "X-Prism-Go-Read-Routing: hit"
    assert soak["caddy_soak_config"]["murmur_site_changed"] is False


def test_phase19_10_extended_soak_samples_are_bounded_and_clean():
    soak = _soak()
    extended = soak["extended_soak"]

    assert extended["sample_count"] == 10
    assert extended["sample_interval_seconds"] == 60
    assert extended["all_samples_passed"] is True
    assert extended["services_active_each_round"] == {
        "prism": True,
        "caddy": True,
        "prism_go_readonly": True,
    }
    assert extended["go_write_method_logs_since_start"] == []

    for check in extended["go_routed_each_round"]:
        assert check["required_header"] == "X-Prism-Go-Read-Routing: hit"

    python_owned = {check["path"]: check for check in extended["python_owned_each_round"]}
    assert python_owned["GET /api/system/migration-status"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["GET /api/system/go-read-routing"]["required_body_fragment"] == "\"enabled\":false"
    assert python_owned["POST /api/test"]["expected_status"] == 403


def test_phase19_10_rollback_final_state_is_python_only():
    soak = _soak()

    rollback = soak["rollback_drill"]
    assert rollback["completed"] is True
    final_state = rollback["final_state"]
    assert final_state["python_service_active"] is True
    assert final_state["caddy_service_active"] is True
    assert final_state["routing_enabled"] is False
    assert final_state["routing_base_url"] is None
    assert final_state["representative_get_without_go_header"] is True
    assert final_state["go_sidecar_active"] is False
    assert final_state["port_5002_listening"] is False
    assert final_state["migration_current_version"] == 16
    assert final_state["migration_pending"] == []


def test_phase19_10_does_not_authorize_permanent_cutover_and_gates_19_11():
    soak = _soak()

    assert soak["target_host"]["public_exposure_changed"] is False
    assert soak["target_host"]["frontend_default_target_changed"] is False
    assert soak["result"]["not_a_permanent_cutover"] is True

    forbidden = soak["not_authorized_by_19_10"]
    assert "Permanent Caddy route change" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Go migrations" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden

    next_step = soak["allowed_next_step"]
    assert next_step["id"] == "19.11"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True


def test_phase19_9_points_to_19_10_gate_before_execution():
    phase19_9 = json.loads(DRILL_19_9_PATH.read_text(encoding="utf-8"))

    assert phase19_9["allowed_next_step"]["id"] == "19.10"
    assert phase19_9["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "Long-running Caddy-level production routing" in phase19_9["allowed_next_step"]["not_authorized_without_approval"]
