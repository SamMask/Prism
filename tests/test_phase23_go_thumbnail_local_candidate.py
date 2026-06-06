import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-thumbnail-local-candidate.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
GO_MOD_PATH = ROOT / "go-shadow" / "go.mod"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
UPLOAD_ROUTE_PATH = ROOT / "routes" / "upload.py"
IMPORT_ROUTE_PATH = ROOT / "routes" / "notes" / "import_.py"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_23_8_thumb_4_contract_locks_local_candidate_boundary():
    contract = _contract()
    runtime = contract["runtime_changes"]

    assert contract["phase"] == "23.8-thumb.4"
    assert contract["status"] == "completed"
    assert contract["explicit_user_approval"] is True
    assert contract["scope_type"] == "flag_gated_local_copied_data_candidate"
    assert contract["implementation"]["route"] == "POST /api/upload"
    assert contract["implementation"]["default_state"] == "disabled_405"
    assert contract["implementation"]["db_behavior"].startswith("sqlite_query_only remains true")
    assert runtime["go_code_changed"] is True
    assert runtime["go_mod_changed"] is True
    assert runtime["go_webp_encoder_added"] is True
    assert runtime["python_runtime_changed"] is False
    assert runtime["pillow_removed"] is False
    assert runtime["pi_deployed"] is False
    assert runtime["caddy_changed"] is False
    assert runtime["systemd_changed"] is False
    assert runtime["frontend_default_changed"] is False
    assert contract["pillow_removal_status_after_gate"].startswith("still_blocked")
    assert contract["allowed_next_step"]["id"] == "23.8-thumb.5"


def test_go_thumbnail_candidate_source_is_flag_gated_and_query_only_safe():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    go_mod = GO_MOD_PATH.read_text(encoding="utf-8")

    assert "go 1.26.1" in go_mod
    assert "github.com/skrashevich/go-webp v0.1.0" in go_mod
    assert '"enable-thumbnail-write"' in main_go
    assert "PRISM_GO_ENABLE_THUMBNAIL_WRITE" in main_go
    assert "local-thumbnail-write" in main_go
    assert 'mux.HandleFunc("/api/upload", srv.handleUpload)' in main_go
    assert "Thumbnail write route is disabled" in main_go
    assert "PRISM_GO_ALLOW_PROD_UPLOADS" in main_go
    assert "sqliteQueryOnly:          !(enableTagWrite || enableCategoryWrite || enableNotesWrite)" in main_go
    assert "webp.Options{Lossy: true, Quality: thumbnailWebPQuality}" in main_go
    assert "thumbnailMaxWidth = 500" in main_go


def test_pillow_and_python_thumbnail_owner_are_retained_after_23_8_thumb_4():
    contract = _contract()
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    upload_route = UPLOAD_ROUTE_PATH.read_text(encoding="utf-8")
    import_route = IMPORT_ROUTE_PATH.read_text(encoding="utf-8")

    assert contract["retained_python_owner"]["normal_upload_owner"] == "routes/upload.py"
    assert contract["retained_python_owner"]["upload_url_owner"] == "routes/upload.py"
    assert contract["retained_python_owner"]["import_helper_owner"] == "routes/notes/import_.py"
    assert contract["retained_python_owner"]["pillow_status"] == "retained"
    assert "Pillow" not in requirements
    assert "from PIL import Image" not in upload_route
    assert "from PIL import Image" not in import_route
    assert "generate_webp_thumbnail" in upload_route
    assert "generate_webp_thumbnail" in import_route
    assert "@upload_bp.route('/upload/url', methods=['POST'])" in upload_route
    assert "def download_and_save_image" in import_route


def test_go_thumbnail_candidate_build_and_unit_evidence_is_current():
    contract = _contract()
    verification = contract["verification"]

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


def test_docs_record_23_8_thumb_4_completion_and_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.8-thumb Go WebP thumbnail ownership / Pillow removal track" in todo
    assert "23.8-thumb.4** Go thumbnail local implementation candidate" in todo
    assert "docs/contracts/phase23-go-thumbnail-local-candidate.json" in todo
    assert "23.8-thumb.5** Go thumbnail surface expansion or removal-readiness gate" in todo
    assert "Phase 23.8-thumb.4 Go thumbnail local implementation candidate is complete" in architecture
    assert "`23.8-thumb.4 Go thumbnail local implementation candidate` is complete" in go_report
