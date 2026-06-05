import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-upload-url-local-candidate.json"
SOURCE_PLAN_PATH = ROOT / "docs" / "contracts" / "phase23-go-upload-url-remote-fetch-safety-parity-plan.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
UPLOAD_ROUTE_PATH = ROOT / "routes" / "upload.py"
IMPORT_ROUTE_PATH = ROOT / "routes" / "notes" / "import_.py"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_23_8_thumb_7_contract_locks_local_upload_url_candidate_boundary():
    contract = _contract()
    runtime = contract["runtime_changes"]

    assert contract["phase"] == "23.8-thumb.7"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["scope_type"] == "flag_gated_local_copied_data_candidate"
    assert contract["implementation"]["route"] == "POST /api/upload/url"
    assert contract["implementation"]["default_state"] == "disabled_405"
    assert contract["implementation"]["flag"] == "--enable-upload-url-write"
    assert contract["implementation"]["env"] == "PRISM_GO_ENABLE_UPLOAD_URL_WRITE"
    assert contract["implementation"]["db_behavior"].startswith("sqlite_query_only remains true")
    assert runtime["go_code_changed"] is True
    assert runtime["go_upload_url_route_added"] is True
    assert runtime["python_runtime_changed"] is False
    assert runtime["go_mod_changed"] is False
    assert runtime["pillow_removed"] is False
    assert runtime["pi_deployed"] is False
    assert runtime["caddy_changed"] is False
    assert runtime["systemd_changed"] is False
    assert runtime["frontend_default_changed"] is False
    assert contract["allowed_next_step"]["id"] == "Pillow dependency removal closure"
    assert "Do not create 23.8-thumb.8/9/10" in contract["allowed_next_step"]["summary"]


def test_go_upload_url_candidate_source_is_flag_gated_and_safety_checked():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    guards = " ".join(_contract()["safety_guards"])

    assert '"enable-upload-url-write"' in main_go
    assert "PRISM_GO_ENABLE_UPLOAD_URL_WRITE" in main_go
    assert "local-upload-url-write" in main_go
    assert 'mux.HandleFunc("/api/upload/url", srv.handleUploadURL)' in main_go
    assert "Upload-url write route is disabled" in main_go
    assert "PRISM_GO_ALLOW_PROD_UPLOADS" in main_go
    assert "sqliteQueryOnly:          !(enableTagWrite || enableCategoryWrite)" in main_go
    assert "validateUploadURLTarget" in main_go
    assert "uploadURLResolveHost" in main_go
    assert "CheckRedirect" in main_go
    assert "io.LimitReader(resp.Body, maxUploadFileBytes+1)" in main_go
    assert "detectUploadImageMIME" in main_go
    assert "safeUploadFilename" in main_go
    assert "md5.Sum" in main_go
    assert "encodeUploadThumbnail" in main_go

    assert "redirect target validation" in guards
    assert "validation failures leave" in guards
    assert "thumbnail_only thumbnail failure keeps original image" in guards


def test_python_live_upload_owner_uses_go_thumbnail_helper_after_closure():
    contract = _contract()
    retained = contract["retained_python_owner"]
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    upload_route = UPLOAD_ROUTE_PATH.read_text(encoding="utf-8")
    import_route = IMPORT_ROUTE_PATH.read_text(encoding="utf-8")

    assert retained["live_upload_url_owner"] == "routes/upload.py download_from_url"
    assert retained["import_helper_owner"] == "routes/notes/import_.py download_and_save_image"
    assert retained["delete_cleanup_owner"] == "routes/upload.py and routes/cleanup.py"
    assert retained["pillow_status"] == "retained"
    assert "Pillow" not in requirements
    assert "@upload_bp.route('/upload/url', methods=['POST'])" in upload_route
    assert "def download_from_url" in upload_route
    assert "def download_and_save_image" in import_route
    assert "from PIL import Image" not in upload_route
    assert "from PIL import Image" not in import_route
    assert "generate_webp_thumbnail" in upload_route
    assert "generate_webp_thumbnail" in import_route


def test_upload_url_candidate_source_plan_is_satisfied_by_23_8_thumb_7_contract():
    source = json.loads(SOURCE_PLAN_PATH.read_text(encoding="utf-8"))
    contract = _contract()
    implementation = contract["implementation"]
    safety = " ".join(contract["safety_guards"])

    assert source["allowed_next_step"]["id"] == "23.8-thumb.7"
    assert implementation["route"] == source["go_candidate_plan"]["route"]
    assert implementation["flag"] == source["go_candidate_plan"]["flag"]
    assert implementation["env"] == source["go_candidate_plan"]["env"]
    assert implementation["api_surface_when_enabled"] == source["go_candidate_plan"]["api_surface_when_enabled"]
    assert implementation["data_root"] == source["go_candidate_plan"]["data_root"]
    assert "read at most MAX_CONTENT_LENGTH + 1 bytes" in " ".join(source["go_candidate_plan"]["network_policy"])
    assert "MAX_CONTENT_LENGTH + 1 streaming read" in safety
    assert "redirect target validation" in safety
    assert "validation failures leave PRISM_GO_DATA_DIR/static/uploads unchanged" in safety


def test_go_upload_url_candidate_unit_and_build_evidence_is_current():
    verification = _contract()["verification"]

    assert verification["go_test"]["result"] == "passed"
    assert verification["windows_build"]["artifact_bytes"] > 0
    assert verification["linux_arm64_cgo0_build"]["artifact_bytes"] > 0
    result = subprocess.run(
        ["go", "test", "./..."],
        cwd=ROOT / "go-shadow",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_docs_record_23_8_thumb_7_completion_and_closure():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.8-thumb.7** Go upload-url local implementation candidate" in todo
    assert "docs/contracts/phase23-go-upload-url-local-candidate.json" in todo
    assert "Pillow dependency removal closure" in todo
    assert "Python packaging removal roadmap" in todo
    assert "不得再新增 `23.8-thumb.8`" in todo
    assert "23.8-thumb.8** Import helper and delete-cleanup ownership decision gate" not in todo
    assert "Phase 23.8-thumb.7 Go upload-url local implementation candidate is complete" in architecture
    assert "no automatic next thumbnail gate" in architecture
    assert "`23.8-thumb.7 Go upload-url local implementation candidate` is complete" in go_report
    assert "no automatic `23.8-thumb.*` gate" in go_report
