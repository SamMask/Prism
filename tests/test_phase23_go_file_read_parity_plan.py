import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "contracts" / "phase23-go-file-read-parity-plan.json"
POLISH_PATH = ROOT / "docs" / "contracts" / "phase20-go-read-surface-polish.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"


def _plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def test_phase23_1_is_plan_only_with_explicit_approval():
    plan = _plan()

    assert plan["phase"] == "23.1"
    assert plan["explicit_user_approval"] is True
    assert plan["plan_only"] is True
    assert plan["risk_level"] == "P0 safety-critical"
    assert plan["runtime_change_performed"] is False
    assert plan["go_file_scanner_implemented"] is False
    assert plan["live_pi_change_performed"] is False
    assert plan["caddy_change_performed"] is False
    assert plan["frontend_default_change_performed"] is False
    assert plan["production_db_change_performed"] is False


def test_phase23_1_file_read_contract_locks_data_dir_and_path_safety():
    contract = _plan()["file_read_contract"]

    assert "--data-dir" in contract["data_dir_rule"]
    assert contract["attachment_path_source"].startswith("Use Note_Attachments.file_path")
    assert contract["allowed_relative_roots"] == ["docs/attachments"]
    assert contract["allowed_extensions"] == ["md", "markdown", "txt"]

    safety_text = " ".join(contract["path_canonicalization"])
    assert "Reject any path containing parent traversal" in safety_text
    assert "strictly inside the resolved data dir" in safety_text
    assert "Reject symlinks" in safety_text
    assert "Reject absolute external paths" in safety_text


def test_phase23_1_file_read_contract_bounds_size_encoding_and_performance():
    contract = _plan()["file_read_contract"]
    perf = contract["timeout_performance_boundary"]

    assert contract["file_size_limit_bytes"] == 1048576
    assert contract["oversized_file_behavior"].startswith("Skip the file")
    assert contract["missing_file_behavior"].startswith("Skip the file")
    assert contract["unsupported_extension_behavior"].startswith("Skip the file")
    assert "UTF-8" in contract["encoding_policy"]
    assert "external dependencies" in contract["encoding_policy"]
    assert perf["max_files_per_query"] == 200
    assert perf["max_total_bytes_per_query"] == 5242880
    assert perf["timeout_ms"] == 250
    assert perf["on_limit_or_timeout"].startswith("Stop scanning additional files")


def test_phase23_1_fixture_plan_covers_positive_and_negative_file_cases():
    cases = {case["id"]: case for case in _plan()["parity_fixture_plan"]["fixture_cases"]}

    assert "metadata_hit" in cases
    assert "body_hit_md" in cases
    assert "body_hit_markdown" in cases
    assert "body_hit_txt" in cases
    assert "missing_file" in cases
    assert "oversized_file" in cases
    assert "unsupported_extension" in cases
    assert "path_traversal_attempt" in cases
    assert "absolute_external_path" in cases
    assert "invalid_utf8" in cases
    assert "same Python and Go note list" in cases["body_hit_md"]["expectation"]
    assert "rejected before open" in cases["path_traversal_attempt"]["expectation"]


def test_phase23_1_runtime_boundary_forbids_live_and_write_expansion():
    plan = _plan()
    boundary = plan["runtime_boundary"]
    forbidden = plan["not_authorized_by_23_1"]

    assert boundary["prism_go_readonly_service_change_allowed"] is False
    assert boundary["sqlite_query_only_must_remain_enabled"] is True
    assert boundary["caddy_matcher_expansion_allowed"] is False
    assert boundary["production_knowledge_db_access_allowed"] is False
    assert boundary["frontend_default_api_target_change_allowed"] is False
    assert boundary["live_pi_deploy_allowed"] is False
    assert boundary["python_backend_removal_allowed"] is False
    assert boundary["direct_public_internet_exposure_allowed"] is False

    assert "Go attachment file body scanner implementation" in forbidden
    assert "Go write/file/migration implementation" in forbidden
    assert "Caddy route expansion or reload" in forbidden
    assert "Pi deploy or live service reload" in forbidden
    assert "Direct public internet exposure" in forbidden


def test_phase23_1_next_step_is_23_2_implementation_gate_with_approval():
    next_step = _plan()["allowed_next_step"]

    assert next_step["id"] == "23.2"
    assert next_step["status"] == "blocked_until_explicit_user_approval"
    assert next_step["requires_explicit_user_approval"] is True
    assert next_step["scope"].startswith("Implement a bounded read-only Go text attachment body scanner")
    assert "Go attachment file body scanner implementation" in next_step["not_authorized_without_approval"]
    assert "Production knowledge.db access or writes from Go" in next_step["not_authorized_without_approval"]
    assert "Pi deploy or live service reload" in next_step["not_authorized_without_approval"]


def test_phase20_gap_is_the_source_for_phase23_1_plan():
    polish = json.loads(POLISH_PATH.read_text(encoding="utf-8"))
    plan = _plan()
    gaps = {gap["id"]: gap for gap in polish["documented_gaps"]}

    assert "text_attachment_body_search" in gaps
    assert "separate file-read parity contract" in gaps["text_attachment_body_search"]["decision"]
    assert plan["current_runtime_truth"]["python_behavior"].startswith("Python GET /api/notes")
    assert "does not read attachment file bodies" in plan["current_runtime_truth"]["go_behavior_before_23_1"]


def test_phase23_1_docs_record_completion_and_23_2_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.1 Go file-read parity plan gate — ✅ Completed" in todo
    assert "23.2 Go file-read parity implementation gate — ✅ Completed" in todo
    assert "Phase 23.1 Go file-read parity plan gate" in architecture
    assert "23.2 Go file-read parity implementation gate" in architecture
    assert "23.1 Go file-read parity plan gate is complete" in go_report
    assert "23.2 Go file-read parity implementation gate" in go_report
