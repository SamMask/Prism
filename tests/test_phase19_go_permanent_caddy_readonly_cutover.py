import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUTOVER_PATH = ROOT / "docs" / "contracts" / "phase19-go-permanent-caddy-readonly-cutover.json"
DECISION_19_11_PATH = ROOT / "docs" / "contracts" / "phase19-go-caddy-cutover-candidate-decision.json"


def _cutover():
    return json.loads(CUTOVER_PATH.read_text(encoding="utf-8"))


def test_phase19_12_records_authorized_permanent_readonly_caddy_cutover():
    cutover = _cutover()

    assert cutover["phase"] == "19.12"
    assert cutover["live_execution_authorized"] is True
    assert cutover["decision"].startswith("Execute the approved permanent read-only Caddy cutover")
    assert cutover["target_host"]["public_exposure_changed"] is False
    assert cutover["target_host"]["frontend_default_target_changed"] is False
    assert cutover["target_host"]["direct_public_internet_exposure_allowed"] is False


def test_phase19_12_has_fresh_backups_and_localhost_query_only_sidecar():
    cutover = _cutover()

    db_backup = cutover["backups"]["db_backup"]
    assert db_backup["path"].endswith(".db")
    assert "permanent_caddy_readonly_cutover" in db_backup["path"]
    assert db_backup["verified"] is True
    assert db_backup["schema_version"] == 16
    assert db_backup["notes_count"] == 196

    caddy_backup = cutover["backups"]["caddy_backup"]
    assert caddy_backup["path"].endswith(".bak")
    assert caddy_backup["created"] is True
    assert caddy_backup["retained_for_rollback"] is True

    sidecar = cutover["go_sidecar"]
    assert sidecar["bind"] == "127.0.0.1:5002"
    assert sidecar["active_after_cutover"] is True
    assert sidecar["enabled_after_cutover"] is True
    assert sidecar["sqlite_query_only"] is True
    assert sidecar["schema_version"] == 16
    assert sidecar["public_bind_allowed"] is False


def test_phase19_12_permanent_caddy_route_stays_readonly_and_bounded():
    cutover = _cutover()
    route = cutover["caddy_cutover_config"]
    policy = route["route_policy"]

    assert route["permanent_route_retained"] is True
    assert route["caddy_validate_after_edit"] is True
    assert route["caddy_reload_completed"] is True
    assert route["caddy_validate_after_reload"] is True
    assert route["murmur_site_changed"] is False
    assert route["go_response_header_added_by_caddy"] == "X-Prism-Go-Read-Routing: hit"

    assert policy["go_routed"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<id>",
    ]
    python_owned = " ".join(policy["python_owned"])
    assert "POST / PUT / DELETE / PATCH" in python_owned
    assert "GET /api/system/*" in python_owned
    assert "GET /api/server/*" in python_owned
    assert "frontend SPA assets" in python_owned
    assert "database migrations" in python_owned
    assert "future GET route under /api/notes/* must be reviewed" in policy["caddy_path_matcher_note"]


def test_phase19_12_live_samples_prove_headers_and_python_owned_boundaries():
    cutover = _cutover()
    verification = cutover["verification"]

    assert verification["sample_count"] == 3
    assert verification["all_samples_passed"] is True
    assert verification["services_active_each_round"] == {
        "prism": True,
        "caddy": True,
        "prism_go_readonly": True,
    }
    assert verification["go_write_method_logs_since_cutover_start"] == []
    assert verification["migration_status_after_cutover"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }
    assert verification["caddy_validate_final"] is True

    for check in verification["go_routed_each_round"]:
        assert check["required_header"] == "X-Prism-Go-Read-Routing: hit"

    python_owned = {check["path"]: check for check in verification["python_owned_each_round"]}
    assert python_owned["GET /api/system/migration-status"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["GET /api/system/go-read-routing"]["required_body_fragment"] == "\"enabled\":false"
    assert python_owned["POST /api/test"]["expected_status"] == 403


def test_phase19_12_final_state_is_permanent_readonly_route_not_full_go_backend():
    cutover = _cutover()
    final_state = cutover["final_state"]

    assert final_state["python_service_active"] is True
    assert final_state["caddy_service_active"] is True
    assert final_state["go_sidecar_active"] is True
    assert final_state["go_sidecar_enabled"] is True
    assert final_state["port_5002_listening"] is True
    assert final_state["routing_endpoint_enabled"] is False
    assert final_state["routing_endpoint_base_url"] is None
    assert final_state["permanent_caddy_readonly_route_active"] is True
    assert final_state["representative_get_with_go_header"] is True
    assert final_state["python_owned_routes_without_go_header"] is True
    assert final_state["migration_current_version"] == 16
    assert final_state["migration_pending"] == []

    forbidden = cutover["not_authorized_by_19_12"]
    assert "Frontend default API target change" in forbidden
    assert "Go ownership of write/file/maintenance routes" in forbidden
    assert "Go migrations" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden


def test_phase19_12_retains_rollback_and_gates_19_13():
    cutover = _cutover()

    rollback = " ".join(cutover["rollback_plan_retained"]["steps"]).lower()
    assert "restore the timestamped caddyfile backup" in rollback
    assert "caddy validate" in rollback
    assert "without x-prism-go-read-routing" in rollback
    assert "pending []" in rollback

    next_step = cutover["allowed_next_step"]
    assert next_step["id"] == "19.13"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "Route expansion beyond the validated GET read surface" in next_step["not_authorized_without_approval"]
    assert "Go writes/files/migrations" in next_step["not_authorized_without_approval"]


def test_phase19_11_points_to_19_12_gate_before_execution():
    phase19_11 = json.loads(DECISION_19_11_PATH.read_text(encoding="utf-8"))

    assert phase19_11["allowed_next_step"]["id"] == "19.12"
    assert phase19_11["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "Permanent Caddy route change" in phase19_11["allowed_next_step"]["not_authorized_without_approval"]
