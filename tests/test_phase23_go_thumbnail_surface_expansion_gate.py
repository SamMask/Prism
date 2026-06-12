import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-thumbnail-surface-expansion-gate.json"
UPLOAD_URL_IMPLEMENTATION_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-upload-url-local-candidate.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
UPLOAD_ROUTE_PATH = ROOT / "routes" / "upload.py"
IMPORT_ROUTE_PATH = ROOT / "routes" / "notes" / "import_.py"
REQUIREMENTS_PATH = ROOT / "requirements.txt"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_23_8_thumb_5_is_decision_gate_and_blocks_runtime_expansion():
    contract = _contract()
    runtime = contract["runtime_changes"]

    assert contract["phase"] == "23.8-thumb.5"
    assert contract["status"] == "completed_blocked_expansion"
    assert contract["explicit_user_approval"] is True
    assert contract["scope_type"] == "decision_gate_only"
    assert contract["removal_allowed"] is False
    assert contract["expansion_allowed_in_this_gate"] is False
    assert contract["decision"].startswith("retain_python_upload_url_and_import_helper")
    assert all(changed is False for changed in runtime.values())
    assert contract["allowed_next_step"]["id"] == "23.8-thumb.6"


def test_surface_matrix_keeps_only_post_upload_as_go_local_candidate():
    surfaces = _contract()["surface_readiness"]

    assert surfaces["post_api_upload"]["status"] == "local_candidate_exists"
    assert "--enable-thumbnail-write" in surfaces["post_api_upload"]["go_candidate"]
    assert surfaces["post_api_upload_url"]["status"] == "retain_python"
    assert surfaces["post_api_upload_url"]["go_candidate"] is None
    assert "SSRF guard parity" in surfaces["post_api_upload_url"]["required_before_go_candidate"]
    assert "download size cap before file writes" in surfaces["post_api_upload_url"]["required_before_go_candidate"]
    assert surfaces["import_image_helper"]["status"] == "retain_python"
    assert surfaces["import_image_helper"]["go_candidate"] is None
    assert "Markdown import workflow boundary decision" in surfaces["import_image_helper"]["required_before_go_candidate"]
    assert surfaces["delete_cleanup"]["status"] == "retain_python"


def test_current_source_keeps_23_8_thumb_5_live_owner_boundary_after_later_candidate():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    upload_route = UPLOAD_ROUTE_PATH.read_text(encoding="utf-8")
    import_route = IMPORT_ROUTE_PATH.read_text(encoding="utf-8")
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    implementation = json.loads(UPLOAD_URL_IMPLEMENTATION_CONTRACT_PATH.read_text(encoding="utf-8"))

    assert 'mux.HandleFunc("/api/upload", srv.handleUpload)' in main_go
    assert 'mux.HandleFunc("/api/upload/url", srv.handleUploadURL)' in main_go
    assert "enable-upload-url-write" in main_go
    assert implementation["phase"] == "23.8-thumb.7"
    assert implementation["retained_python_owner"]["live_upload_url_owner"] == "routes/upload.py download_from_url"
    assert "downloadAndSaveImage" not in main_go
    assert "_is_ssrf_target" in upload_route
    assert "@upload_bp.route('/upload/url', methods=['POST'])" in upload_route
    assert "requests.get(image_url" in upload_route
    assert "magic.from_buffer" in upload_route
    assert "thumbnail_only" in upload_route
    assert "def download_and_save_image" in import_route
    assert "requests.get(image_url" in import_route
    assert "thumbnail_only" in import_route
    assert "from PIL import Image" not in upload_route
    assert "from PIL import Image" not in import_route
    assert "generate_webp_thumbnail" in upload_route
    assert "generate_webp_thumbnail" in import_route
    assert "Pillow" not in requirements


def test_not_authorized_scope_blocks_pillow_removal_pi_and_remote_fetch_changes():
    blocked = set(_contract()["not_authorized_by_23_8_thumb_5"])

    assert "Remove Pillow from requirements.txt" in blocked
    assert "Implement Go /api/upload/url in this gate" in blocked
    assert "Replace routes/notes/import_.py download_and_save_image" in blocked
    assert "Change SSRF behavior or remote request policy" in blocked
    assert "Deploy to Pi" in blocked
    assert "Route frontend or Caddy upload traffic to Go" in blocked


def test_docs_record_23_8_thumb_5_completion_and_23_8_thumb_6_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.8-thumb.5** Go thumbnail surface expansion or removal-readiness gate" in todo
    assert "docs/contracts/phase23-go-thumbnail-surface-expansion-gate.json" in todo
    assert "23.8-thumb.6** Go upload-url remote-fetch safety parity plan" in todo
    assert "Phase 23.8-thumb.5 Go thumbnail surface expansion gate is complete" in architecture
    assert "`23.8-thumb.5 Go thumbnail surface expansion or removal-readiness gate` is complete" in go_report

