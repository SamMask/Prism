import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STABILIZATION_PATH = ROOT / "docs" / "contracts" / "phase20-go-post-polish-stabilization.json"
POLISH_PATH = ROOT / "docs" / "contracts" / "phase20-go-read-surface-polish.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"


def _stabilization():
    return json.loads(STABILIZATION_PATH.read_text(encoding="utf-8"))


def test_phase20_4_is_plan_only_stabilization_with_explicit_approval():
    stabilization = _stabilization()

    assert stabilization["phase"] == "20.4"
    assert stabilization["explicit_user_approval"] is True
    assert stabilization["plan_only"] is True
    assert stabilization["runtime_change_performed"] is False
    assert stabilization["live_pi_change_performed"] is False
    assert stabilization["caddy_change_performed"] is False
    assert stabilization["frontend_default_change_performed"] is False
    assert stabilization["source_polish"] == "docs/contracts/phase20-go-read-surface-polish.json"


def test_phase20_4_closes_phase20_without_expanding_go_ownership():
    stabilization = _stabilization()

    assert stabilization["closure_status"] == "closed_stabilized"
    assert stabilization["result"]["status"] == "phase20_closed_stabilized"
    assert stabilization["ownership_after_20_4"]["go"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<numeric id>",
    ]

    python_owned = " ".join(stabilization["ownership_after_20_4"]["python"])
    assert "All POST / PUT / DELETE / PATCH routes" in python_owned
    assert "Text attachment body search" in python_owned
    assert "migrations" in python_owned


def test_phase20_4_does_not_promote_file_read_parity_or_runtime_change():
    stabilization = _stabilization()
    not_selected = {item["id"]: item for item in stabilization["not_selected_next"]}

    assert "go_text_attachment_body_search" in not_selected
    assert "separate file-read safety contract" in not_selected["go_text_attachment_body_search"]["reason"]
    assert "go_write_or_file_routes" in not_selected
    assert "caddy_or_service_change" in not_selected

    forbidden = stabilization["not_authorized_by_20_4"]
    assert "Go attachment file body scanning" in forbidden
    assert "Go write/file/migration implementation" in forbidden
    assert "Caddy route expansion beyond the validated GET read surface" in forbidden
    assert "Live Pi service or Caddy reload" in forbidden


def test_phase20_4_next_step_is_21_0_delivery_and_queue_selection_gate():
    stabilization = _stabilization()
    next_step = stabilization["allowed_next_step"]

    assert next_step["id"] == "21.0"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("Plan-only selection of the next branch")
    assert "Git commit or push" in next_step["not_authorized_without_approval"]
    assert "Pi deploy or live service reload" in next_step["not_authorized_without_approval"]
    assert "Go attachment file body scanning" in next_step["not_authorized_without_approval"]


def test_phase20_3_authorized_20_4_stabilization_gate():
    polish = json.loads(POLISH_PATH.read_text(encoding="utf-8"))
    stabilization = _stabilization()

    assert polish["allowed_next_step"]["id"] == "20.4"
    assert polish["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert stabilization["source_polish"] == "docs/contracts/phase20-go-read-surface-polish.json"


def test_phase20_4_docs_record_closure_and_21_0_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")

    assert "Phase 20: Post-readonly Go Scope Assessment — ✅ Closed" in todo
    assert "20.4 Post-polish Stabilization and Candidate Closure Gate" in todo
    assert "21.0 Delivery and Queue Selection Gate" in todo
    assert "Phase 20.4" in architecture
    assert "closed_stabilized" in architecture
