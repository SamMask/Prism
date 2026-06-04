import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "contracts" / "phase20-go-candidate-fixture-planning.json"
INVENTORY_PATH = ROOT / "docs" / "contracts" / "phase20-go-write-surface-contract-inventory.json"


def _plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def test_phase20_2_is_plan_only_with_explicit_approval():
    plan = _plan()

    assert plan["phase"] == "20.2"
    assert plan["explicit_user_approval"] is True
    assert plan["plan_only"] is True
    assert plan["runtime_change_performed"] is False
    assert plan["go_implementation_authorized"] is False
    assert plan["source_inventory"] == "docs/contracts/phase20-go-write-surface-contract-inventory.json"


def test_phase20_2_selects_only_read_surface_polish():
    plan = _plan()
    selected = plan["selected_candidate"]

    assert selected["id"] == "read_surface_polish"
    assert selected["candidate_type"] == "read_only_polish"
    assert selected["risk"] == "low"
    assert selected["owner_after_20_2"]["go"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<numeric id>",
    ]

    rejected = {candidate["id"] for candidate in plan["rejected_candidates"]}
    assert {
        "notes_core_writes",
        "notes_actions_and_batch",
        "history_restore",
        "category_tag_writes",
        "attachments_and_long_content",
        "uploads_and_remote_fetch",
        "cleanup_and_media_maintenance",
        "import_export",
        "system_maintenance",
        "server_local_operations",
        "prompt_and_wizard_config",
    }.issubset(rejected)


def test_phase20_2_fixture_plan_locks_read_parity_and_boundaries():
    plan = _plan()
    fixtures = {item["id"]: item for item in plan["fixture_plan"]["required_fixtures_before_any_20_3_edit"]}

    assert "hardened_read_surface_matrix" in fixtures
    assert "search_parity_matrix" in fixtures
    assert "ownership_boundary_matrix" in fixtures
    assert "runtime_invariant_matrix" in fixtures

    read_routes = fixtures["hardened_read_surface_matrix"]["routes"]
    assert "GET /api/notes/<numeric id>" in read_routes
    assert "numeric note detail 404" in fixtures["hardened_read_surface_matrix"]["cases"]

    search_cases = " ".join(fixtures["search_parity_matrix"]["cases"])
    assert "todo.md" in search_cases
    assert "Chinese keyword query" in search_cases
    assert "attachment metadata and text-file body search" in search_cases

    boundary_routes = fixtures["ownership_boundary_matrix"]["routes"]
    assert "GET /api/notes/<id>/history" in boundary_routes
    assert "GET /api/system/go-read-routing" in boundary_routes
    assert "POST /api/notes" in boundary_routes


def test_phase20_2_forbids_runtime_expansion_and_live_changes():
    plan = _plan()
    forbidden = plan["not_authorized_by_20_2"]

    assert "Go write/file/migration implementation" in forbidden
    assert "Caddy route expansion beyond the validated GET read surface" in forbidden
    assert "Changing prism-go-readonly.service away from SQLite query_only" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden
    assert "Live Pi service or Caddy reload" in forbidden


def test_phase20_2_stop_conditions_block_write_or_route_expansion():
    plan = _plan()
    stop_conditions = " ".join(plan["stop_conditions_for_20_3"])

    assert "POST/PUT/DELETE/PATCH" in stop_conditions
    assert "production DB writes" in stop_conditions
    assert "file writes/deletes" in stop_conditions
    assert "Caddy route expansion" in stop_conditions
    assert "sqlite_query_only" in stop_conditions
    assert "Frontend default API target" in stop_conditions


def test_phase20_2_next_step_is_separately_approved_read_surface_polish():
    plan = _plan()
    next_step = plan["allowed_next_step"]

    assert next_step["id"] == "20.3"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("Plan and execute only read-only parity")
    assert "Go write/file/migration implementation" in next_step["not_authorized_without_approval"]
    assert "Live Pi service or Caddy reload" in next_step["not_authorized_without_approval"]


def test_phase20_1_authorized_20_2_candidate_selection_gate():
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    plan = _plan()

    assert inventory["allowed_next_step"]["id"] == "20.2"
    assert inventory["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert plan["source_inventory"] == "docs/contracts/phase20-go-write-surface-contract-inventory.json"
