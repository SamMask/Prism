import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "contracts" / "phase19-go-readonly-service-cutover-plan.json"
AUDIT_PATH = ROOT / "docs" / "contracts" / "phase19-go-cutover-readiness-audit.json"


def _plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def test_phase19_5_is_plan_only_without_live_authorization():
    plan = _plan()

    assert plan["phase"] == "19.5"
    assert plan["plan_only"] is True
    assert plan["live_execution_authorized"] is False
    assert plan["requires_explicit_user_approval_before_live_execution"] is True

    next_step = plan["allowed_next_step"]
    assert next_step["id"] == "19.6"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True


def test_phase19_5_preserves_runtime_and_security_boundaries():
    plan = _plan()

    assert "direct public internet exposure" in plan["exposure_boundary"]["not_allowed"]
    assert "trusted LAN" in plan["exposure_boundary"]["allowed"]
    assert "no built-in API token" in plan["exposure_boundary"]["auth_note"]

    topology = plan["planned_topology"]
    assert topology["python_service"]["role"].startswith("primary runtime")
    assert topology["python_service"]["status"] == "unchanged by this plan"
    assert topology["go_sidecar_service"]["bind"] == "127.0.0.1:5002"
    assert topology["go_sidecar_service"]["db_mode"] == "SQLite query_only, schema >= 16"


def test_phase19_5_requires_backup_health_and_rollback_before_execution():
    plan = _plan()
    preflight = " ".join(plan["preflight_required_before_execution"]).lower()
    rollback = " ".join(plan["rollback_drill"]["primary"]).lower()

    assert "timestamped production db backup" in preflight
    assert "python prism.service is active" in preflight
    assert "localhost only" in preflight
    assert "no post / put / delete / patch routes" in preflight

    assert "disable prism_go_read_routing" in rollback
    assert "restart python prism.service" in rollback
    assert "enabled=false" in rollback


def test_phase19_5_blocks_go_write_file_migration_scope():
    plan = _plan()
    forbidden = " ".join(plan["not_in_scope"]).lower()
    failure = " ".join(plan["failure_criteria"]).lower()

    assert "post / put / delete / patch" in forbidden
    assert "attachments, export, cleanup, server maintenance" in forbidden
    assert "go migrations" in forbidden
    assert "production db writes from go" in forbidden
    assert "python backend removal" in forbidden

    assert "any write/file/maintenance route is routed to go" in failure
    assert "sqlite_query_only=false" in failure
    assert "without explicit approval" in failure


def test_phase19_4_audit_points_to_19_5_plan():
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    assert audit["allowed_next_step"]["id"] == "19.5"
    assert audit["allowed_next_step"]["requires_user_approval_before_execution"] is True
    assert "read-only service-level cutover" in audit["allowed_next_step"]["title"].lower()
