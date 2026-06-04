import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRILL_PATH = ROOT / "docs" / "contracts" / "phase19-go-caddy-readonly-routing-drill.json"
PLAN_19_8_PATH = ROOT / "docs" / "contracts" / "phase19-go-reverse-proxy-service-cutover-plan.json"


def _drill():
    return json.loads(DRILL_PATH.read_text(encoding="utf-8"))


def test_phase19_9_records_authorized_caddy_drill_and_preflight():
    drill = _drill()

    assert drill["phase"] == "19.9"
    assert drill["live_execution_authorized"] is True
    assert "Caddy-level read-only routing drill" in drill["authorized_scope"]

    preflight = drill["preflight"]
    assert preflight["python_service_active"] is True
    assert preflight["caddy_service_active"] is True
    assert preflight["routing_enabled"] is False
    assert preflight["caddy_validate_before_change"] is True
    assert preflight["migration_status"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }


def test_phase19_9_has_db_and_caddy_backups_and_query_only_sidecar():
    drill = _drill()

    db_backup = drill["backups"]["db_backup"]
    assert db_backup["path"].endswith(".db")
    assert "caddy_readonly_drill" in db_backup["path"]
    assert db_backup["verified"] is True
    assert db_backup["schema_version"] == 16
    assert db_backup["notes_count"] == 196

    caddy_backup = drill["backups"]["caddy_backup"]
    assert caddy_backup["path"].endswith(".bak")
    assert caddy_backup["created"] is True
    assert caddy_backup["used_for_rollback"] is True

    sidecar = drill["go_sidecar"]
    assert sidecar["bind"] == "127.0.0.1:5002"
    assert sidecar["sqlite_query_only"] is True
    assert sidecar["schema_version"] == 16
    assert sidecar["public_bind_allowed"] is False


def test_phase19_9_caddy_policy_routes_only_validated_get_surface():
    drill = _drill()
    policy = drill["caddy_drill_config"]["route_policy"]

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
    assert drill["caddy_drill_config"]["go_response_header_added_by_caddy"] == "X-Prism-Go-Read-Routing: hit"


def test_phase19_9_samples_go_headers_and_python_owned_no_headers():
    drill = _drill()
    samples = drill["drill_samples"]

    assert samples["sample_count"] == 3
    assert samples["sample_interval_seconds"] == 30
    assert samples["all_samples_passed"] is True
    assert samples["services_active_each_round"] == {
        "prism": True,
        "caddy": True,
        "prism_go_readonly": True,
    }
    assert samples["go_write_method_logs_since_start"] == []

    for check in samples["go_routed_each_round"]:
        assert check["required_header"] == "X-Prism-Go-Read-Routing: hit"

    python_owned = {check["path"]: check for check in samples["python_owned_each_round"]}
    assert python_owned["GET /api/system/migration-status"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["GET /api/system/go-read-routing"]["required_body_fragment"] == "\"enabled\":false"
    assert python_owned["POST /api/test"]["expected_status"] == 403


def test_phase19_9_rollback_restores_python_only_final_state():
    drill = _drill()

    rollback = drill["rollback_drill"]
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


def test_phase19_9_does_not_authorize_permanent_cutover_and_gates_19_10():
    drill = _drill()

    assert drill["target_host"]["public_exposure_changed"] is False
    assert drill["target_host"]["frontend_default_target_changed"] is False
    assert drill["result"]["not_a_permanent_cutover"] is True

    forbidden = drill["not_authorized_by_19_9"]
    assert "Permanent Caddy route change" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Go migrations" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden

    next_step = drill["allowed_next_step"]
    assert next_step["id"] == "19.10"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True


def test_phase19_8_plan_points_to_19_9_gate_before_execution():
    phase19_8 = json.loads(PLAN_19_8_PATH.read_text(encoding="utf-8"))

    assert phase19_8["allowed_next_step"]["id"] == "19.9"
    assert phase19_8["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "Caddy route change" in phase19_8["allowed_next_step"]["not_authorized_without_approval"]
