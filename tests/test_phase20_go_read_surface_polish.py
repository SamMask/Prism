import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLISH_PATH = ROOT / "docs" / "contracts" / "phase20-go-read-surface-polish.json"
PLAN_PATH = ROOT / "docs" / "contracts" / "phase20-go-candidate-fixture-planning.json"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
GO_DIFF_TEST_PATH = ROOT / "tests" / "test_phase18_go_shadow_contract.py"
API_REFERENCE_PATH = ROOT / "docs" / "API_REFERENCE.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"


def _polish():
    return json.loads(POLISH_PATH.read_text(encoding="utf-8"))


def test_phase20_3_records_authorized_read_only_polish_scope():
    polish = _polish()

    assert polish["phase"] == "20.3"
    assert polish["explicit_user_approval"] is True
    assert polish["source_candidate_plan"] == "docs/contracts/phase20-go-candidate-fixture-planning.json"
    assert polish["selected_candidate"] == "read_surface_polish"
    assert polish["runtime_change_performed"] is False
    assert polish["live_pi_change_performed"] is False
    assert polish["caddy_change_performed"] is False
    assert polish["frontend_default_change_performed"] is False
    assert polish["go_implementation_scope"] == "read-only DB parity only"


def test_phase20_3_go_search_includes_attachment_metadata_without_write_methods():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert "FROM Note_Attachments a" in main_go
    assert "a.title LIKE ?" in main_go
    assert "a.file_path LIKE ?" in main_go
    assert "PRAGMA query_only = ON" in main_go
    assert "http.MethodGet" in main_go
    assert "enableTagWrite" in main_go
    assert "http.MethodPost" not in main_go
    assert "http.MethodDelete" not in main_go


def test_phase20_3_diff_fixture_covers_attachment_metadata_search():
    diff_test = GO_DIFF_TEST_PATH.read_text(encoding="utf-8")

    assert "attachment-meta-canary" in diff_test
    assert "INSERT INTO Note_Attachments" in diff_test
    assert "/api/notes?q=attachment-meta-canary&page=1&per_page=20" in diff_test


def test_phase20_3_documents_text_attachment_body_search_as_python_owned_gap():
    polish = _polish()
    gaps = {gap["id"]: gap for gap in polish["documented_gaps"]}

    assert "text_attachment_body_search" in gaps
    assert "Python GET /api/notes" in gaps["text_attachment_body_search"]["python_behavior"]
    assert "Go does not scan attachment file bodies" in gaps["text_attachment_body_search"]["go_behavior_after_20_3"]
    assert "separate file-read parity contract" in gaps["text_attachment_body_search"]["decision"]

    api_docs = API_REFERENCE_PATH.read_text(encoding="utf-8")
    arch_docs = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    assert "Go read-only route parity" in api_docs
    assert "text attachment body search remains Python-owned" in api_docs
    assert "Phase 20.3" in arch_docs
    assert "文字附件 body 搜尋仍是 Python-owned gap" in arch_docs


def test_phase20_3_forbids_runtime_expansion_and_file_body_scanning():
    polish = _polish()
    forbidden = polish["not_authorized_by_20_3"]

    assert "Go write/file/migration implementation" in forbidden
    assert "Caddy route expansion beyond the validated GET read surface" in forbidden
    assert "Changing prism-go-readonly.service away from SQLite query_only" in forbidden
    assert "Frontend default API target change" in forbidden
    assert "Python backend removal" in forbidden
    assert "Direct public internet exposure" in forbidden
    assert "Live Pi service or Caddy reload" in forbidden
    assert "Go attachment file body scanning" in forbidden


def test_phase20_3_next_step_is_plan_only_stabilization_gate():
    polish = _polish()
    next_step = polish["allowed_next_step"]

    assert next_step["id"] == "20.4"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("Plan-only stabilization review")
    assert "Go attachment file body scanning" in next_step["not_authorized_without_approval"]
    assert "Live Pi service or Caddy reload" in next_step["not_authorized_without_approval"]


def test_phase20_2_authorized_20_3_read_surface_polish_gate():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    polish = _polish()

    assert plan["allowed_next_step"]["id"] == "20.3"
    assert plan["allowed_next_step"]["requires_explicit_user_approval"] is True
    assert polish["source_candidate_plan"] == "docs/contracts/phase20-go-candidate-fixture-planning.json"
