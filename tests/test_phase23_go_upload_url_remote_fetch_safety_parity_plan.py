import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-upload-url-remote-fetch-safety-parity-plan.json"
IMPLEMENTATION_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-upload-url-local-candidate.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
UPLOAD_ROUTE_PATH = ROOT / "routes" / "upload.py"
SECURITY_TEST_PATH = ROOT / "tests" / "test_security_guards.py"
THUMB_SURFACE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-thumbnail-surface-expansion-gate.json"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_23_8_thumb_6_is_plan_only_and_keeps_runtime_unchanged():
    contract = _contract()

    assert contract["phase"] == "23.8-thumb.6"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["scope_type"] == "plan_only_remote_fetch_safety_contract"
    assert contract["decision"] == "split_post_api_upload_url_into_a_separate_go_candidate_gate_before_any_runtime_change"
    assert all(changed is False for changed in contract["runtime_changes"].values())
    assert contract["allowed_next_step"]["id"] == "23.8-thumb.7"


def test_current_python_upload_url_contract_is_captured_from_source():
    contract = _contract()["current_python_contract"]
    upload_route = UPLOAD_ROUTE_PATH.read_text(encoding="utf-8")
    security_tests = SECURITY_TEST_PATH.read_text(encoding="utf-8")

    assert contract["owner"] == "routes/upload.py download_from_url"
    assert contract["route"] == "POST /api/upload/url"
    assert "url" in contract["request"]["required_fields"]
    assert "thumbnail_only" in contract["request"]["optional_fields"]
    assert "http or https scheme only" in contract["validation_order"]
    assert "_is_ssrf_target(hostname)" in " ".join(contract["validation_order"])
    assert "requests.get(url" in " ".join(contract["validation_order"])
    assert "Content-Type must start with image/" in contract["validation_order"]
    assert "magic.from_buffer" in " ".join(contract["validation_order"])
    assert contract["thumbnail_only_contract"]["thumbnail_success"].startswith("return _thumb.webp")
    assert "reads response.content before size rejection" in contract["known_python_runtime_detail_not_to_expand_in_23_8_thumb_6"]

    assert "@upload_bp.route('/upload/url', methods=['POST'])" in upload_route
    assert "parsed.scheme not in ('http', 'https')" in upload_route
    assert "_is_ssrf_target(parsed.hostname or '')" in upload_route
    assert "requests.get(image_url, headers=headers, timeout=30, stream=True)" in upload_route
    assert "content_type.startswith('image/')" in upload_route
    assert "magic.from_buffer(image_data[:2048], mime=True)" in upload_route
    assert "thumb_filename if thumbnail_only else new_filename" in upload_route
    assert "test_ssrf_blocks_loopback" in security_tests
    assert "test_ssrf_blocks_private_range" in security_tests


def test_go_candidate_plan_requires_separate_upload_url_flag_and_safety_fixtures():
    plan = _contract()["go_candidate_plan"]
    required = _contract()["required_23_8_thumb_7_fixtures"]

    assert plan["target_gate"] == "23.8-thumb.7"
    assert plan["route"] == "POST /api/upload/url"
    assert plan["default_state"] == "disabled_405"
    assert plan["flag"] == "--enable-upload-url-write"
    assert plan["env"] == "PRISM_GO_ENABLE_UPLOAD_URL_WRITE"
    assert plan["api_surface_when_enabled"] == "get-read-only+local-upload-url-write"
    assert plan["db_behavior"].startswith("sqlite_query_only remains true")
    assert "PRISM_GO_ALLOW_PROD_UPLOADS=1" in plan["production_guard"]
    assert "validate every redirect target before following it" in plan["network_policy"]
    assert "read at most MAX_CONTENT_LENGTH + 1 bytes" in " ".join(plan["network_policy"])
    assert "all validation failures leave data_dir/static/uploads unchanged" in plan["response_parity_policy"]
    assert "redirect to private host is rejected" in required["go_unit_tests"]
    assert "oversized response is capped while streaming and writes no files" in required["go_unit_tests"]
    assert "no-mutation checks on failure paths" in required["python_vs_go_diff_fixtures"]


def test_go_runtime_upload_url_implementation_is_separately_authorized_by_23_8_thumb_7():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    blocked = set(_contract()["not_authorized_by_23_8_thumb_6"])
    previous = json.loads(THUMB_SURFACE_CONTRACT_PATH.read_text(encoding="utf-8"))
    implementation = json.loads(IMPLEMENTATION_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert 'mux.HandleFunc("/api/upload", srv.handleUpload)' in main_go
    assert 'mux.HandleFunc("/api/upload/url", srv.handleUploadURL)' in main_go
    assert "enable-upload-url-write" in main_go
    assert "PRISM_GO_ENABLE_UPLOAD_URL_WRITE" in main_go
    assert implementation["phase"] == "23.8-thumb.7"
    assert implementation["source_contracts"][0] == "docs/contracts/phase23-go-upload-url-remote-fetch-safety-parity-plan.json"
    assert "Implement Go /api/upload/url" in blocked
    assert "Change SSRF behavior or remote request policy" in blocked
    assert "Remove Pillow from requirements.txt" in blocked
    assert previous["allowed_next_step"]["id"] == "23.8-thumb.6"


def test_docs_record_23_8_thumb_6_completion_and_23_8_thumb_7_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.8-thumb.6** Go upload-url remote-fetch safety parity plan" in todo
    assert "docs/contracts/phase23-go-upload-url-remote-fetch-safety-parity-plan.json" in todo
    assert "23.8-thumb.7** Go upload-url local implementation candidate" in todo
    assert "Phase 23.8-thumb.6 Go upload-url remote-fetch safety parity plan is complete" in architecture
    assert "`23.8-thumb.6 Go upload-url remote-fetch safety parity plan` is complete" in go_report
