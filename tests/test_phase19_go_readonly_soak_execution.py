import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOAK_PATH = ROOT / "docs" / "contracts" / "phase19-go-readonly-soak-execution.json"
PLAN_PATH = ROOT / "docs" / "contracts" / "phase19-go-readonly-service-cutover-plan.json"


def _soak():
    return json.loads(SOAK_PATH.read_text(encoding="utf-8"))


def test_phase19_6_records_authorized_live_execution_and_backup():
    soak = _soak()

    assert soak["phase"] == "19.6"
    assert soak["live_execution_authorized"] is True
    assert "stage_0" in soak["authorized_scope"]
    assert "stage_1" in soak["authorized_scope"]

    preflight = soak["preflight"]
    assert preflight["python_service_active"] is True
    assert preflight["migration_status"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }
    assert preflight["backup_path"].endswith(".db")
    assert preflight["backup_verified"] is True
    assert preflight["backup_schema_version"] == 16


def test_phase19_6_sidecar_is_localhost_query_only_and_get_only():
    soak = _soak()
    sidecar = soak["go_sidecar"]

    assert sidecar["service_name"] == "prism-go-readonly.service"
    assert sidecar["bind"] == "127.0.0.1:5002"
    assert sidecar["query_only"] is True
    assert sidecar["schema_version"] == 16
    assert sidecar["localhost_only"] is True

    direct_checks = {
        check["path"]: check["status"]
        for check in soak["stage_0_no_routing_smoke"]["direct_go_checks"]
    }
    assert direct_checks["GET /healthz"] == 200
    assert direct_checks["GET /api/test"] == 200
    assert direct_checks["GET /api/notes/114"] == 200
    assert direct_checks["GET /api/notes/999999"] == 404
    assert direct_checks["POST /api/test"] == 405


def test_phase19_6_opt_in_routing_only_proxies_allowed_gets():
    soak = _soak()
    stage_1 = soak["stage_1_python_opt_in_routing"]

    assert stage_1["python_status_endpoint"]["enabled"] is True
    assert stage_1["python_status_endpoint"]["base_url"] == "http://127.0.0.1:5002"
    assert stage_1["python_status_endpoint"]["valid_base_url"] is True

    proxied = {check["path"]: check for check in stage_1["proxied_gets"]}
    assert proxied["GET /api/test"]["header"] == "X-Prism-Go-Read-Routing: hit"
    assert proxied["GET /api/categories"]["status"] == 200
    assert proxied["GET /api/tags"]["status"] == 200
    assert proxied["GET /api/notes?per_page=1&page=1"]["status"] == 200
    assert proxied["GET /api/notes/114"]["status"] == 200
    assert proxied["GET /api/notes/999999"]["status"] == 404

    python_owned = {check["path"]: check for check in stage_1["python_owned_checks"]}
    assert python_owned["GET /api/system/migration-status"]["has_go_routing_header"] is False
    assert python_owned["POST /api/test"]["has_go_routing_header"] is False


def test_phase19_6_rollback_returns_pi_to_python_only():
    soak = _soak()
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


def test_phase19_6_does_not_authorize_cutover_or_write_scope():
    soak = _soak()

    assert soak["target_host"]["public_exposure_changed"] is False
    assert soak["target_host"]["caddy_route_changed"] is False
    assert soak["target_host"]["frontend_default_target_changed"] is False

    boundary = soak["write_and_migration_boundary"]
    assert boundary["go_write_routes_added"] is False
    assert boundary["go_file_routes_added"] is False
    assert boundary["go_migrations_added"] is False
    assert boundary["go_db_writes_performed"] is False
    assert boundary["python_remains_write_file_maintenance_owner"] is True

    next_step = soak["allowed_next_step"]
    assert next_step["id"] == "19.7"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "Caddy route changes" in next_step["not_authorized_without_approval"]


def test_phase19_5_plan_points_to_the_executed_19_6_stage():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    assert plan["allowed_next_step"]["id"] == "19.6"
    assert plan["allowed_next_step"]["requires_explicit_user_approval"] is True
