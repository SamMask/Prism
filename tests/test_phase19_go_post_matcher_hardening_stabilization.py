import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STABILIZATION_PATH = ROOT / "docs" / "contracts" / "phase19-go-post-matcher-hardening-stabilization.json"
HARDENING_19_14_PATH = ROOT / "docs" / "contracts" / "phase19-go-caddy-matcher-runbook-hardening.json"


def _stabilization():
    return json.loads(STABILIZATION_PATH.read_text(encoding="utf-8"))


def test_phase19_15_records_authorized_stabilization_without_runtime_change():
    stabilization = _stabilization()

    assert stabilization["phase"] == "19.15"
    assert stabilization["live_execution_authorized"] is True
    assert stabilization["runtime_change_performed"] is False
    assert stabilization["decision"].startswith("Keep the narrowed permanent Caddy matcher")
    assert stabilization["target_host"]["public_exposure_changed"] is False
    assert stabilization["target_host"]["frontend_default_target_changed"] is False
    assert stabilization["target_host"]["direct_public_internet_exposure_allowed"] is False


def test_phase19_15_stabilization_window_kept_caddy_unchanged():
    stabilization = _stabilization()
    window = stabilization["stabilization_window"]

    assert window["sample_count"] == 5
    assert window["sample_interval_seconds"] == 10
    assert window["all_samples_passed"] is True
    assert window["no_caddy_reload_or_route_edit"] is True


def test_phase19_15_keeps_localhost_query_only_sidecar_and_hardened_matcher():
    stabilization = _stabilization()
    services = stabilization["service_state"]

    assert services["prism_service_active"] is True
    assert services["caddy_service_active"] is True
    assert services["go_sidecar_active"] is True
    assert services["go_sidecar_enabled"] is True
    assert services["go_sidecar_bind"] == "127.0.0.1:5002"
    assert services["go_healthz"]["schema_version"] == 16
    assert services["go_healthz"]["sqlite_query_only"] is True

    matcher = stabilization["matcher_state"]
    assert matcher["hardened_matcher_kept"] is True
    assert matcher["exact_paths"] == [
        "/api/test",
        "/api/categories",
        "/api/tags",
        "/api/notes",
    ]
    assert matcher["numeric_note_detail_regexp"] == "^/api/notes/[0-9]+$"
    assert matcher["wildcard_notes_matcher_restored"] is False
    assert matcher["route_expansion"] is False


def test_phase19_15_route_evidence_preserves_go_and_python_boundaries():
    stabilization = _stabilization()
    evidence = stabilization["route_evidence"]

    for check in evidence["go_routed_each_sample"]:
        assert check["required_header"] == "X-Prism-Go-Read-Routing: hit"

    python_owned = {check["path"]: check for check in evidence["python_owned_each_sample"]}
    assert python_owned["GET /api/notes/not-a-number"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["GET /api/notes/114/extra"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["GET /api/system/migration-status"]["expected_status"] == 200
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


def test_phase19_15_closes_readonly_promotion_without_expanding_go_scope():
    stabilization = _stabilization()
    closure = stabilization["closure_decision"]

    assert closure["phase19_readonly_promotion_status"] == "closed_stabilized"
    assert closure["keep_hardened_permanent_readonly_caddy_route"] is True
    assert closure["rollback_plan_retained"] is True
    assert len(closure["rollback_references"]) == 2

    ownership = closure["production_ownership"]
    assert ownership["go"] == [
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<numeric id>",
    ]
    python_owned = " ".join(ownership["python"])
    assert "POST / PUT / DELETE / PATCH" in python_owned
    assert "Unreviewed or nonnumeric /api/notes/... GET paths" in python_owned
    assert "GET /api/system/*" in python_owned
    assert "GET /api/server/*" in python_owned
    assert "database migrations" in python_owned

    forbidden = stabilization["not_authorized_by_19_15"]
    assert "Route expansion beyond the validated GET read surface" in forbidden
    assert "Go ownership of write/file/maintenance routes" in forbidden
    assert "Go migrations" in forbidden
    assert "Python backend removal" in forbidden


def test_phase19_15_gates_20_0_plan_only_scope_assessment():
    stabilization = _stabilization()
    next_step = stabilization["allowed_next_step"]

    assert next_step["id"] == "20.0"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "Plan-only assessment" in next_step["scope"]
    assert "Go write/file/migration implementation" in next_step["not_authorized_without_approval"]
    assert "Route expansion beyond the validated GET read surface" in next_step["not_authorized_without_approval"]


def test_phase19_14_points_to_19_15_stabilization_gate():
    phase19_14 = json.loads(HARDENING_19_14_PATH.read_text(encoding="utf-8"))

    assert phase19_14["allowed_next_step"]["id"] == "19.15"
    assert phase19_14["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "Route expansion beyond the validated GET read surface" in phase19_14["allowed_next_step"]["not_authorized_without_approval"]
