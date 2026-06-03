import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "contracts" / "phase19-go-reverse-proxy-service-cutover-plan.json"
LONG_SOAK_PATH = ROOT / "docs" / "contracts" / "phase19-go-readonly-long-soak-decision.json"


def _plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def test_phase19_8_is_plan_only_and_gates_live_caddy_changes():
    plan = _plan()

    assert plan["phase"] == "19.8"
    assert plan["plan_only"] is True
    assert plan["live_execution_authorized"] is False
    assert plan["requires_explicit_user_approval_before_live_execution"] is True
    assert plan["caddy_plan_shape"]["not_authorized_in_19_8"] is True

    next_step = plan["allowed_next_step"]
    assert next_step["id"] == "19.9"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "Caddy route change" in next_step["not_authorized_without_approval"]


def test_phase19_8_preserves_exposure_and_auth_boundaries():
    plan = _plan()

    exposure = plan["exposure_boundary"]
    assert "localhost" in exposure["allowed"]
    assert "trusted LAN" in exposure["allowed"]
    assert "VPN" in exposure["allowed"]
    assert "SSH tunnel" in exposure["allowed"]
    assert "reverse proxy protected by external auth" in exposure["allowed"]
    assert "direct public internet exposure" in exposure["not_allowed"]
    assert "unprotected Caddy public endpoint" in exposure["not_allowed"]
    assert "no built-in API token" in exposure["auth_note"]


def test_phase19_8_topology_keeps_python_owner_and_go_localhost_readonly():
    plan = _plan()
    topology = plan["planned_topology"]

    python = topology["python_service"]
    assert python["name"] == "prism.service"
    assert python["required_final_fallback"] is True
    assert "write/file/maintenance/migration owner" in python["role"]

    go = topology["go_sidecar_service"]
    assert go["name"] == "prism-go-readonly.service"
    assert go["bind"] == "127.0.0.1:5002"
    assert go["db_mode"] == "SQLite query_only, schema >= 16"
    assert go["public_bind_allowed"] is False

    reverse_proxy = topology["reverse_proxy"]
    assert reverse_proxy["name"] == "Caddy"
    assert reverse_proxy["must_preserve_external_access_policy"] is True
    assert reverse_proxy["must_not_change_frontend_default_api_target"] is True


def test_phase19_8_route_policy_allows_only_validated_get_surface():
    plan = _plan()
    route_policy = plan["route_policy"]

    go_allowed = {(route["method"], route["path"]) for route in route_policy["go_allowed"]}
    assert go_allowed == {
        ("GET", "/api/test"),
        ("GET", "/api/categories"),
        ("GET", "/api/tags"),
        ("GET", "/api/notes"),
        ("GET", "/api/notes/<id>"),
    }

    python_required = " ".join(route_policy["python_required"])
    assert "POST / PUT / DELETE / PATCH" in python_required
    assert "/api/system/*" in python_required
    assert "/api/server/*" in python_required
    assert "frontend SPA assets" in python_required
    assert "database migrations" in python_required

    assert route_policy["header_evidence"]["required_for_go_routed_reads"] == "X-Prism-Go-Read-Routing: hit"
    assert route_policy["header_evidence"]["must_be_absent_for_python_owned_routes"] is True


def test_phase19_8_requires_preflight_monitoring_and_rollback_for_19_9():
    plan = _plan()

    preflight = " ".join(plan["preflight_required_before_19_9_execution"]).lower()
    monitoring = " ".join(plan["monitoring_evidence_required_for_19_9"]).lower()
    rollback = " ".join(plan["rollback_drill"]["primary"]).lower()

    assert "explicit user approval" in preflight
    assert "caddy is active" in preflight
    assert "caddy config backup" in preflight
    assert "fresh timestamped production db backup" in preflight
    assert "localhost" in preflight

    assert "caddy validate" in monitoring
    assert "x-prism-go-read-routing" in monitoring
    assert "post" in monitoring
    assert "rollback verification" in monitoring

    assert "caddy validate" in rollback
    assert "reload caddy" in rollback
    assert "without x-prism-go-read-routing" in rollback


def test_phase19_8_blocks_write_migration_frontend_and_python_removal_scope():
    plan = _plan()
    forbidden = " ".join(plan["not_in_scope"])
    failure = " ".join(plan["failure_criteria"]).lower()

    assert "Live Caddy config changes" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Go write/file/maintenance routes" in forbidden
    assert "Go migrations" in forbidden
    assert "Go production DB writes" in forbidden
    assert "Python backend removal" in forbidden

    assert "any post/put/delete/patch request reaches go" in failure
    assert "python-owned route carries x-prism-go-read-routing" in failure
    assert "rollback cannot return to python-only behavior" in failure


def test_phase19_7_points_to_19_8_gate_before_plan_creation():
    phase19_7 = json.loads(LONG_SOAK_PATH.read_text(encoding="utf-8"))

    assert phase19_7["allowed_next_step"]["id"] == "19.8"
    assert phase19_7["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "plan-only" in phase19_7["allowed_next_step"]["first_step_if_approved"]
