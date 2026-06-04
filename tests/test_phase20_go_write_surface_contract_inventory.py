import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs" / "contracts" / "phase20-go-write-surface-contract-inventory.json"
ASSESSMENT_PATH = ROOT / "docs" / "contracts" / "phase20-go-post-readonly-scope-assessment.json"


def _inventory():
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def test_phase20_1_is_plan_only_inventory_without_runtime_change():
    inventory = _inventory()

    assert inventory["phase"] == "20.1"
    assert inventory["explicit_user_approval"] is True
    assert inventory["plan_only"] is True
    assert inventory["runtime_change_performed"] is False
    assert inventory["go_implementation_authorized"] is False
    assert inventory["decision"].startswith("Inventory Python-owned mutation")


def test_phase20_1_preserves_current_go_read_only_ownership():
    inventory = _inventory()
    ownership = inventory["current_go_ownership"]

    assert ownership["caddy_hardened_read_surface"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<numeric id>",
    ]
    assert ownership["sidecar"]["service"] == "prism-go-readonly.service"
    assert ownership["sidecar"]["bind"] == "127.0.0.1:5002"
    assert ownership["sidecar"]["sqlite_query_only"] is True
    assert ownership["sidecar"]["schema_version"] == 16


def test_phase20_1_inventory_covers_python_owned_surface_classes():
    inventory = _inventory()
    route_classes = {item["id"]: item for item in inventory["route_classes"]}

    expected = {
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
    }
    assert expected.issubset(route_classes)

    for route_class in route_classes.values():
        assert route_class["owner"] == "python"
        assert route_class["routes"]
        assert route_class["rollback_requirements"]
        assert route_class["fixture_requirements"]
        assert route_class["go_candidate_priority"] == "not_selected"
        assert route_class["go_implementation_authorized"] is False


def test_phase20_1_records_side_effect_types_for_high_risk_classes():
    inventory = _inventory()
    route_classes = {item["id"]: item for item in inventory["route_classes"]}

    notes = route_classes["notes_core_writes"]
    assert "Notes insert/update/delete" in notes["db_side_effects"]
    assert any("image" in effect for effect in notes["file_side_effects"])

    uploads = route_classes["uploads_and_remote_fetch"]
    assert any("static/uploads" in effect for effect in uploads["file_side_effects"])
    assert uploads["external_side_effects"] == [
        "Fetches remote URL content for upload/url"
    ]

    server = route_classes["server_local_operations"]
    assert server["service_process_side_effects"] == [
        "Restart endpoint can invoke local service/process controls"
    ]
    assert any("localhost-only" in item for item in server["security_boundary"])


def test_phase20_1_forbids_runtime_expansion_and_non_readonly_sidecar_mode():
    inventory = _inventory()
    forbidden = inventory["not_authorized_by_20_1"]

    assert "Go write/file/migration implementation" in forbidden
    assert "Caddy route expansion beyond the validated GET read surface" in forbidden
    assert "Changing prism-go-readonly.service away from SQLite query_only" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden
    assert "Production DB writes from Go" in forbidden
    assert "Go migration framework" in forbidden


def test_phase20_1_next_step_is_candidate_selection_plan_only():
    inventory = _inventory()
    next_step = inventory["allowed_next_step"]

    assert next_step["id"] == "20.2"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("Plan-only selection")
    assert "Go write/file/migration implementation" in next_step["not_authorized_without_approval"]
    assert "Caddy route expansion beyond the validated GET read surface" in next_step["not_authorized_without_approval"]


def test_phase20_0_authorized_20_1_inventory_gate():
    assessment = json.loads(ASSESSMENT_PATH.read_text(encoding="utf-8"))
    inventory = _inventory()

    assert assessment["allowed_next_step"]["id"] == "20.1"
    assert assessment["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert inventory["source_assessment"] == "docs/contracts/phase20-go-post-readonly-scope-assessment.json"
