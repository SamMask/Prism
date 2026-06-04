import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = ROOT / "docs" / "contracts" / "phase20-go-post-readonly-scope-assessment.json"
PHASE19_CLOSURE_PATH = ROOT / "docs" / "contracts" / "phase19-go-post-matcher-hardening-stabilization.json"


def _assessment():
    return json.loads(ASSESSMENT_PATH.read_text(encoding="utf-8"))


def test_phase20_0_is_plan_only_without_runtime_change():
    assessment = _assessment()

    assert assessment["phase"] == "20.0"
    assert assessment["live_execution_authorized"] is True
    assert assessment["plan_only"] is True
    assert assessment["runtime_change_performed"] is False
    assert assessment["decision"].startswith("Do not implement any new Go ownership")


def test_phase20_0_preserves_closed_phase19_ownership():
    assessment = _assessment()
    state = assessment["current_production_state"]

    assert state["go_owns"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<numeric id>",
    ]
    python_owned = " ".join(state["python_owns"])
    assert "POST / PUT / DELETE / PATCH" in python_owned
    assert "Unreviewed or nonnumeric /api/notes/... GET paths" in python_owned
    assert "GET /api/system/*" in python_owned
    assert "GET /api/server/*" in python_owned
    assert "database migrations" in python_owned

    assert state["go_sidecar"]["bind"] == "127.0.0.1:5002"
    assert state["go_sidecar"]["sqlite_query_only"] is True
    assert state["caddy_matcher"]["numeric_note_detail_regexp"] == "^/api/notes/[0-9]+$"


def test_phase20_0_ranks_candidates_without_selecting_implementation():
    assessment = _assessment()
    candidates = {item["id"]: item for item in assessment["scope_candidates"]}

    assert candidates["read_surface_polish"]["recommended_next"] is True
    assert candidates["read_surface_polish"]["risk"] == "low"

    for candidate_id in [
        "note_write_routes",
        "category_tag_writes",
        "file_attachment_routes",
        "system_server_migrations",
    ]:
        assert candidates[candidate_id]["recommended_next"] is False
        assert candidates[candidate_id]["blockers"]

    assert candidates["note_write_routes"]["risk"] == "high"
    assert candidates["file_attachment_routes"]["risk"] == "very_high"
    assert candidates["system_server_migrations"]["risk"] == "very_high"


def test_phase20_0_next_step_is_write_surface_inventory_not_go_implementation():
    assessment = _assessment()
    recommended = assessment["recommended_path"]

    assert recommended["next_step_id"] == "20.1"
    assert recommended["type"] == "plan_only"
    assert "Before any Go write/file/migration implementation" in recommended["reason"]
    outputs = " ".join(recommended["minimum_outputs"]).lower()
    assert "machine-readable route inventory" in outputs
    assert "side-effect map" in outputs
    assert "backup and rollback" in outputs
    assert "no-implementation gate" in outputs


def test_phase20_0_forbids_runtime_expansion_and_public_exposure():
    assessment = _assessment()
    forbidden = assessment["not_authorized_by_20_0"]

    assert "Go write/file/migration implementation" in forbidden
    assert "Caddy route expansion beyond the validated GET read surface" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden
    assert "Changing prism-go-readonly.service mode away from SQLite query_only" in forbidden


def test_phase20_0_gates_20_1_as_plan_only_inventory():
    assessment = _assessment()
    next_step = assessment["allowed_next_step"]

    assert next_step["id"] == "20.1"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "Plan-only inventory" in next_step["scope"]
    assert "Go write/file/migration implementation" in next_step["not_authorized_without_approval"]
    assert "Caddy route expansion beyond the validated GET read surface" in next_step["not_authorized_without_approval"]


def test_phase19_15_points_to_20_0_scope_assessment_gate():
    phase19 = json.loads(PHASE19_CLOSURE_PATH.read_text(encoding="utf-8"))

    assert phase19["allowed_next_step"]["id"] == "20.0"
    assert phase19["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "Plan-only assessment" in phase19["allowed_next_step"]["scope"]
