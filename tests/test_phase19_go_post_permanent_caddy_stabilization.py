import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STABILIZATION_PATH = ROOT / "docs" / "contracts" / "phase19-go-post-permanent-caddy-stabilization.json"
CUTOVER_19_12_PATH = ROOT / "docs" / "contracts" / "phase19-go-permanent-caddy-readonly-cutover.json"


def _stabilization():
    return json.loads(STABILIZATION_PATH.read_text(encoding="utf-8"))


def test_phase19_13_records_authorized_stabilization_without_runtime_change():
    stabilization = _stabilization()

    assert stabilization["phase"] == "19.13"
    assert stabilization["live_execution_authorized"] is True
    assert stabilization["runtime_change_performed"] is False
    assert stabilization["decision"].startswith("Keep the Phase 19.12 permanent read-only Caddy route")
    assert stabilization["target_host"]["public_exposure_changed"] is False
    assert stabilization["target_host"]["frontend_default_target_changed"] is False
    assert stabilization["target_host"]["direct_public_internet_exposure_allowed"] is False


def test_phase19_13_stabilization_window_samples_are_bounded_and_clean():
    stabilization = _stabilization()
    window = stabilization["stabilization_window"]

    assert window["sample_count"] == 5
    assert window["sample_interval_seconds"] == 10
    assert window["all_samples_passed"] is True
    assert window["no_caddy_reload_or_route_edit"] is True


def test_phase19_13_service_state_keeps_localhost_query_only_sidecar():
    stabilization = _stabilization()
    services = stabilization["service_state"]

    assert services["prism_service_active"] is True
    assert services["caddy_service_active"] is True
    assert services["go_sidecar_active"] is True
    assert services["go_sidecar_enabled"] is True
    assert services["go_sidecar_bind"] == "127.0.0.1:5002"

    healthz = services["go_healthz"]
    assert healthz["status"] == "ok"
    assert healthz["api_surface"] == "get-read-only"
    assert healthz["schema_version"] == 16
    assert healthz["expected_schema_version"] == 16
    assert healthz["sqlite_query_only"] is True


def test_phase19_13_live_route_evidence_preserves_go_and_python_boundaries():
    stabilization = _stabilization()
    evidence = stabilization["route_evidence"]

    for check in evidence["go_routed_each_sample"]:
        assert check["required_header"] == "X-Prism-Go-Read-Routing: hit"

    python_owned = {check["path"]: check for check in evidence["python_owned_each_sample"]}
    assert python_owned["GET /api/system/migration-status"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["GET /api/system/go-read-routing"]["required_body_fragment"] == "\"enabled\":false"
    assert python_owned["GET /api/server/version"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["POST /api/test"]["expected_status"] == 403

    assert evidence["migration_status"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }
    assert evidence["routing_endpoint"] == {
        "enabled": False,
        "base_url": None,
        "default_owner": "python",
        "fallback_owner": "python",
    }
    assert evidence["caddy_validate"] is True
    assert evidence["go_write_method_logs_since_window_start"] == []
    assert evidence["go_error_logs_since_window_start"] == []


def test_phase19_13_keeps_route_and_does_not_authorize_expansion():
    stabilization = _stabilization()

    keep = stabilization["keep_decision"]
    assert keep["status"] == "keep_permanent_readonly_caddy_route"
    assert keep["rollback_plan_retained"] is True
    assert keep["rollback_reference"].endswith("Caddyfile.prism-pre-permanent-go-readonly-cutover-20260604_180157.bak")

    forbidden = stabilization["not_authorized_by_19_13"]
    assert "Route expansion beyond the validated GET read surface" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Go ownership of write/file/maintenance routes" in forbidden
    assert "Go migrations" in forbidden
    assert "Python backend removal" in forbidden
    assert "Caddy route edit or reload during stabilization review" in forbidden


def test_phase19_13_gates_19_14_matcher_and_runbook_hardening():
    stabilization = _stabilization()
    next_step = stabilization["allowed_next_step"]

    assert next_step["id"] == "19.14"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "Caddy route edit or reload" in next_step["not_authorized_without_approval"]
    assert "Route expansion beyond the validated GET read surface" in next_step["not_authorized_without_approval"]
    assert "Go writes/files/migrations" in next_step["not_authorized_without_approval"]


def test_phase19_12_points_to_19_13_stabilization_gate():
    phase19_12 = json.loads(CUTOVER_19_12_PATH.read_text(encoding="utf-8"))

    assert phase19_12["allowed_next_step"]["id"] == "19.13"
    assert phase19_12["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "Route expansion beyond the validated GET read surface" in phase19_12["allowed_next_step"]["not_authorized_without_approval"]
