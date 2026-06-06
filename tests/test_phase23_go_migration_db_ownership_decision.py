import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-migration-db-ownership-decision.json"
SOURCE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-attachment-text-read-implementation.json"
MIGRATIONS_PATH = ROOT / "migrations" / "__init__.py"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
SYSTEM_ROUTE_PATH = ROOT / "routes" / "system.py"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_phase23_7_contract_is_plan_only_and_keeps_live_migrations_python_owned():
    contract = _contract()
    source = json.loads(SOURCE_CONTRACT_PATH.read_text(encoding="utf-8"))
    truth = contract["current_runtime_truth"]

    assert contract["phase"] == "23.7"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-go-attachment-text-read-implementation.json"
    assert source["allowed_next_step"]["id"] == "23.7"
    assert contract["plan_only"] is True
    assert contract["runtime_change"] == "none"
    assert contract["migration_runner_implemented"] is False
    assert contract["production_db_write"] is False
    assert contract["schema_migration_performed"] is False
    assert contract["caddy_or_service_change"] is False
    assert contract["pi_deploy"] is False
    assert truth["normal_migration_owner"] == "Python migrations.run_migrations"
    assert truth["status_endpoint_owner"] == "Python GET /api/system/migration-status"
    assert truth["version_table"] == "Schema_Meta"
    assert truth["latest_schema_version"] == 16
    assert truth["go_query_only_default"] is True


def test_phase23_7_compares_three_options_and_selects_retained_python_migrations():
    options = {item["id"]: item for item in _contract()["ownership_options"]}

    assert set(options) == {
        "retained_python_migrations",
        "go_status_only",
        "go_full_migration_runner",
    }
    assert options["retained_python_migrations"]["decision"] == "selected_for_normal_and_live_runtime"
    assert "Python remains the migration runner" in options["retained_python_migrations"]["scope"]
    assert "idempotent duplicate-column/no-such-column handling" in options["retained_python_migrations"]["reason"]
    assert options["go_status_only"]["decision"] == "allowed_future_candidate_after_23_7"
    assert "No Schema_Meta update" in options["go_status_only"]["required_guards"]
    assert "Response parity with Python current/latest/pending semantics" in options["go_status_only"]["required_guards"]
    assert options["go_full_migration_runner"]["decision"] == "deferred"
    assert "Failed migration rollback leaves Schema_Meta and affected tables consistent" in options["go_full_migration_runner"]["blocked_until"]
    assert "Python fallback owner is explicitly retained until live proof passes" in options["go_full_migration_runner"]["blocked_until"]


def test_phase23_7_schema_safety_contract_locks_idempotency_pending_and_recovery():
    safety = _contract()["schema_safety_contract"]
    checkpoint = _contract()["decision_checkpoint"]

    assert "duplicate columns" in safety["idempotency"]
    assert "already-dropped columns" in safety["idempotency"]
    assert safety["version_table"] == "Schema_Meta key=schema_version remains the single schema version source of truth."
    assert safety["pending_detection"] == "pending = migrations with version > current_version; latest_version = highest declared migration version."
    assert safety["backup_required_before_live"] is True
    assert safety["rollback_required_before_live"] is True
    assert "Failed migration must rollback the current transaction" in safety["failed_migration_recovery"]
    assert "Schema_Meta must not advance past the failed version" in safety["failed_migration_recovery"]
    assert checkpoint["normal_runtime_owner"] == "Python"
    assert checkpoint["live_pi_owner"] == "Python"
    assert checkpoint["go_status_only_next_candidate"] is True
    assert checkpoint["go_full_runner_next_candidate"] is False
    assert checkpoint["python_removal_blocked"] is True


def test_current_python_migration_runtime_has_required_status_and_idempotency_anchors():
    migrations = MIGRATIONS_PATH.read_text(encoding="utf-8")
    system_route = SYSTEM_ROUTE_PATH.read_text(encoding="utf-8")

    assert "def run_migrations(db) -> int:" in migrations
    assert "def get_migration_status(db) -> dict:" in migrations
    assert "Schema_Meta" in migrations
    assert "schema_version" in migrations
    assert "duplicate column name" in migrations
    assert "no such column" in migrations
    assert "db.rollback()" in migrations
    assert "'current_version': current" in migrations
    assert "'latest_version': MIGRATIONS[-1][0]" in migrations
    assert "'pending': pending" in migrations
    assert "@system_bp.route('/system/migration-status', methods=['GET'])" in system_route
    assert "get_migration_status(db)" in system_route


def test_go_runtime_remains_schema_status_reader_not_migration_runner():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert "func verifySchemaVersion" in main_go
    assert "func schemaVersion" in main_go
    assert "SELECT value FROM Schema_Meta WHERE key = 'schema_version'" in main_go
    assert '"schema_version":' in main_go
    assert '"expected_schema_version":' in main_go
    assert "PRAGMA query_only = ON" in main_go
    assert "CREATE TABLE Schema_Meta" not in main_go
    assert "UPDATE Schema_Meta" not in main_go
    assert "ALTER TABLE" not in main_go
    assert "DROP TABLE" not in main_go
    assert "runMigrations" not in main_go


def test_phase23_7_does_not_authorize_runtime_schema_live_or_python_removal_scope():
    blocked = set(_contract()["not_authorized_by_23_7"])

    assert "Go migration runner implementation" in blocked
    assert "Go DDL or migration DML execution" in blocked
    assert "Schema_Meta writes from Go" in blocked
    assert "Production knowledge.db migration" in blocked
    assert "Production DB write" in blocked
    assert "Caddy route edit or reload" in blocked
    assert "systemd service change" in blocked
    assert "Pi deployment" in blocked
    assert "Frontend default API target change" in blocked
    assert "Python migration removal" in blocked
    assert "Python route removal" in blocked
    assert "Schema migration" in blocked
    assert "Public exposure expansion" in blocked


def test_docs_record_23_7_completion_and_23_8_next_gate():
    contract = _contract()
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert contract["allowed_next_step"]["id"] == "23.8"
    assert contract["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert contract["allowed_next_step"]["recommended_first_subgate"] == "23.8.1 Packaging contract"
    assert "23.7 Migration / DB ownership decision gate — ✅ Completed (2026-06-06)" in todo
    assert "docs/contracts/phase23-go-migration-db-ownership-decision.json" in todo
    assert "23.8 Local packaging execution track — ✅ Completed (2026-06-06)" in todo
    assert "23.8.2** Local smoke artifact" in todo
    assert "Phase 23.7 Migration / DB ownership decision gate is complete as plan-only" in architecture
    assert "Phase 23.9 Pi deployment rollout is complete" in architecture
    assert "Phase 23 Go runtime reduction track is closed with retained-Python normal path" in architecture
    assert "`23.7 Migration / DB ownership decision gate` is complete as plan-only" in go_report
    assert "`23.9 Pi deployment rollout` is complete" in go_report
    assert "Phase 23 closes with retained Python as the normal runtime path" in go_report

