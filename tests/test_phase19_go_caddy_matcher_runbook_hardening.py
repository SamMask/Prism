import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARDENING_PATH = ROOT / "docs" / "contracts" / "phase19-go-caddy-matcher-runbook-hardening.json"
STABILIZATION_19_13_PATH = ROOT / "docs" / "contracts" / "phase19-go-post-permanent-caddy-stabilization.json"


def _hardening():
    return json.loads(HARDENING_PATH.read_text(encoding="utf-8"))


def test_phase19_14_records_authorized_matcher_hardening():
    hardening = _hardening()

    assert hardening["phase"] == "19.14"
    assert hardening["live_execution_authorized"] is True
    assert hardening["runtime_change_performed"] is True
    assert hardening["decision"].startswith("Narrow the retained permanent Caddy matcher")
    assert hardening["target_host"]["public_exposure_changed"] is False
    assert hardening["target_host"]["frontend_default_target_changed"] is False
    assert hardening["target_host"]["direct_public_internet_exposure_allowed"] is False


def test_phase19_14_has_preflight_backup_validate_and_reload_evidence():
    hardening = _hardening()

    preflight = hardening["preflight"]
    assert preflight["candidate_caddyfile_validated_before_live_edit"] is True
    assert preflight["current_caddyfile_validated_before_live_edit"] is True
    assert preflight["prism_service_active"] is True
    assert preflight["caddy_service_active"] is True
    assert preflight["go_sidecar_active"] is True
    assert preflight["go_sidecar_enabled"] is True

    backup = hardening["backups"]["caddy_backup"]
    assert backup["path"].endswith(".bak")
    assert "matcher-hardening" in backup["path"]
    assert backup["created"] is True
    assert backup["retained_for_rollback"] is True

    matcher = hardening["matcher_hardening"]
    assert matcher["caddy_validate_after_edit"] is True
    assert matcher["caddy_reload_completed"] is True
    assert matcher["caddy_validate_after_reload"] is True
    assert matcher["murmur_site_changed"] is False


def test_phase19_14_narrows_notes_wildcard_to_exact_and_numeric_detail():
    hardening = _hardening()
    matcher = hardening["matcher_hardening"]

    assert "/api/notes/*" in matcher["old_matcher"]["path"]
    assert "future unreviewed GET paths" in matcher["old_matcher"]["risk"]

    exact, note_detail = matcher["new_matchers"]
    assert exact == {
        "name": "prismGoReadExact",
        "method": "GET",
        "path": [
            "/api/test",
            "/api/categories",
            "/api/tags",
            "/api/notes",
        ],
    }
    assert note_detail == {
        "name": "prismGoReadNoteDetail",
        "method": "GET",
        "path_regexp": "^/api/notes/[0-9]+$",
    }
    assert matcher["route_expansion"] is False


def test_phase19_14_live_verification_preserves_allowed_gets_and_blocks_unreviewed_notes_paths():
    hardening = _hardening()
    verification = hardening["live_verification"]

    assert verification["sample_count"] == 3
    assert verification["all_samples_passed"] is True
    assert verification["go_sidecar"]["bind"] == "127.0.0.1:5002"
    assert verification["go_sidecar"]["active"] is True
    assert verification["go_sidecar"]["enabled"] is True
    assert verification["go_sidecar"]["sqlite_query_only"] is True

    for check in verification["go_routed_each_sample"]:
        assert check["required_header"] == "X-Prism-Go-Read-Routing: hit"

    python_owned = {check["path"]: check for check in verification["python_owned_each_sample"]}
    assert python_owned["GET /api/notes/not-a-number"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["GET /api/notes/114/extra"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["GET /api/system/migration-status"]["expected_status"] == 200
    assert python_owned["GET /api/system/go-read-routing"]["required_body_fragment"] == "\"enabled\":false"
    assert python_owned["GET /api/server/version"]["required_no_header"] == "X-Prism-Go-Read-Routing"
    assert python_owned["POST /api/test"]["expected_status"] == 403

    assert verification["migration_status"] == {
        "current_version": 16,
        "latest_version": 16,
        "pending": [],
    }
    assert verification["go_write_method_logs_since_hardening_start"] == []
    assert verification["go_error_logs_since_hardening_start"] == []
    assert verification["caddy_validate_final"] is True


def test_phase19_14_final_state_and_forbidden_scope():
    hardening = _hardening()
    final_state = hardening["final_state"]

    assert final_state["permanent_readonly_caddy_route_active"] is True
    assert final_state["matcher_narrowed"] is True
    assert final_state["python_service_active"] is True
    assert final_state["caddy_service_active"] is True
    assert final_state["go_sidecar_active"] is True
    assert final_state["go_sidecar_enabled"] is True
    assert final_state["routing_endpoint_enabled"] is False
    assert final_state["route_expansion"] is False

    forbidden = hardening["not_authorized_by_19_14"]
    assert "Route expansion beyond the validated GET read surface" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Go ownership of write/file/maintenance routes" in forbidden
    assert "Go migrations" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden


def test_phase19_14_retains_rollback_and_gates_19_15():
    hardening = _hardening()

    rollback = " ".join(hardening["rollback_plan_retained"]["steps"]).lower()
    assert "restore the chosen timestamped caddyfile backup" in rollback
    assert "caddy validate" in rollback
    assert "python-owned routes do not carry x-prism-go-read-routing" in rollback

    next_step = hardening["allowed_next_step"]
    assert next_step["id"] == "19.15"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert "Route expansion beyond the validated GET read surface" in next_step["not_authorized_without_approval"]
    assert "Go writes/files/migrations" in next_step["not_authorized_without_approval"]


def test_phase19_13_points_to_19_14_matcher_hardening_gate():
    phase19_13 = json.loads(STABILIZATION_19_13_PATH.read_text(encoding="utf-8"))

    assert phase19_13["allowed_next_step"]["id"] == "19.14"
    assert phase19_13["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert "Caddy route edit or reload" in phase19_13["allowed_next_step"]["not_authorized_without_approval"]
