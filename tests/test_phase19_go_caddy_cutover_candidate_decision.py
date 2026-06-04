import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "docs" / "contracts" / "phase19-go-caddy-cutover-candidate-decision.json"
SOAK_19_10_PATH = ROOT / "docs" / "contracts" / "phase19-go-caddy-extended-readonly-soak.json"


def _decision():
    return json.loads(DECISION_PATH.read_text(encoding="utf-8"))


def test_phase19_11_is_proposal_only_without_live_cutover():
    decision = _decision()

    assert decision["phase"] == "19.11"
    assert decision["plan_only"] is True
    assert decision["live_execution_authorized"] is False
    assert decision["decision"].startswith("Write a permanent-cutover proposal")
    assert decision["result"]["status"] == "proposal_ready"

    forbidden = decision["not_authorized_by_19_11"]
    assert "Live Caddy config change" in forbidden
    assert "Caddy reload" in forbidden
    assert "Permanent Caddy route change" in forbidden
    assert "Python backend removal" in forbidden


def test_phase19_11_keeps_go_as_readonly_sidecar_candidate():
    decision = _decision()
    candidate = decision["candidate_status"]

    assert candidate["go_status"] == "verified_caddy_routable_readonly_sidecar_candidate"
    assert candidate["validated_surface"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<id>",
    ]
    assert "Caddy-level route block with X-Prism-Go-Read-Routing header evidence" in candidate["validated_routing_controls"]
    assert candidate["required_runtime_shape"]["python_service"] == "primary runtime and rollback target"
    assert candidate["required_runtime_shape"]["go_sidecar"] == "localhost-only read-only sidecar on 127.0.0.1:5002"


def test_phase19_11_permanent_cutover_proposal_preserves_route_boundaries():
    decision = _decision()
    proposal = decision["permanent_cutover_proposal"]

    assert proposal["proposal_only"] is True
    assert proposal["operation_window_required"] is True
    assert "manual attended" in proposal["recommended_operation_window"]

    policy = proposal["permanent_route_policy"]
    assert policy["go_allowed"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<id>",
    ]
    python_required = " ".join(policy["python_required"])
    assert "POST / PUT / DELETE / PATCH" in python_required
    assert "GET /api/system/*" in python_required
    assert "GET /api/server/*" in python_required
    assert "frontend SPA assets" in python_required
    assert "database migrations" in python_required
    assert policy["required_go_header"] == "X-Prism-Go-Read-Routing: hit"


def test_phase19_11_requires_fresh_preflight_monitoring_and_rollback():
    decision = _decision()
    proposal = decision["permanent_cutover_proposal"]

    preflight = " ".join(proposal["fresh_preflight_required"]).lower()
    monitoring = " ".join(proposal["monitoring_required"]).lower()
    rollback = " ".join(proposal["rollback_plan"]).lower()
    triggers = " ".join(proposal["rollback_trigger"]).lower()

    assert "explicit user approval" in preflight
    assert "external auth" in preflight
    assert "timestamped db backup" in preflight
    assert "timestamped caddyfile backup" in preflight
    assert "sqlite_query_only=true" in preflight

    assert "caddy validate" in monitoring
    assert "x-prism-go-read-routing" in monitoring
    assert "no post/put/delete/patch" in monitoring
    assert "migration status" in monitoring

    assert "restore timestamped caddyfile backup" in rollback
    assert "without x-prism-go-read-routing" in rollback
    assert "pending []" in rollback

    assert "any post/put/delete/patch reaches go" in triggers
    assert "python-owned route carries x-prism-go-read-routing" in triggers


def test_phase19_11_preserves_exposure_auth_and_ownership_boundaries():
    decision = _decision()

    exposure = decision["exposure_boundary"]
    assert "localhost" in exposure["allowed"]
    assert "trusted LAN" in exposure["allowed"]
    assert "VPN" in exposure["allowed"]
    assert "SSH tunnel" in exposure["allowed"]
    assert "reverse proxy protected by external auth" in exposure["allowed"]
    assert "direct public internet exposure" in exposure["not_allowed"]
    assert "unprotected Caddy public endpoint" in exposure["not_allowed"]
    assert "no built-in API token" in exposure["auth_note"]

    forbidden = decision["not_authorized_by_19_11"]
    assert "Frontend default API target change" in forbidden
    assert "Go ownership of write/file/maintenance routes" in forbidden
    assert "Go migrations" in forbidden
    assert "Direct public internet exposure" in forbidden


def test_phase19_11_gates_19_12_for_any_permanent_cutover():
    decision = _decision()
    next_step = decision["allowed_next_step"]

    assert next_step["id"] == "19.12"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "Permanent Caddy route change" in next_step["not_authorized_without_approval"]
    assert "Caddy reload" in next_step["not_authorized_without_approval"]
    assert "Go writes/files/migrations" in next_step["not_authorized_without_approval"]


def test_phase19_10_points_to_19_11_gate_before_decision():
    phase19_10 = json.loads(SOAK_19_10_PATH.read_text(encoding="utf-8"))

    assert phase19_10["allowed_next_step"]["id"] == "19.11"
    assert phase19_10["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "Permanent Caddy route change" in phase19_10["allowed_next_step"]["not_authorized_without_approval"]
