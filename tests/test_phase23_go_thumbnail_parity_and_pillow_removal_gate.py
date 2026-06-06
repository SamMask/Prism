import io
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PARITY_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-thumbnail-parity-fixtures.json"
REMOVAL_CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-go-pillow-removal-gate.json"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
REQUIREMENTS_PATH = ROOT / "requirements.txt"
START_BAT_PATH = ROOT / "scripts" / "start.bat"
API_REFERENCE_PATH = ROOT / "docs" / "API_REFERENCE.md"
SEQUENCE_UPLOAD_PATH = ROOT / "docs" / "SEQUENCE-UPLOAD.md"
UPLOAD_ROUTE_PATH = ROOT / "routes" / "upload.py"
IMPORT_ROUTE_PATH = ROOT / "routes" / "notes" / "import_.py"
GO_MOD_PATH = ROOT / "go-shadow" / "go.mod"
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"


pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _image_bytes(fmt, size=(720, 360)):
    mode = "RGB"
    image = Image.new(mode, size, (40, 120, 200))
    data = io.BytesIO()
    save_format = "JPEG" if fmt == "jpg" else fmt.upper()
    image.save(data, save_format)
    return data.getvalue()


@pytest.fixture()
def isolated_uploads(app, tmp_path, monkeypatch):
    root = tmp_path / "app-root"
    uploads = root / "static" / "uploads"
    uploads.mkdir(parents=True)
    monkeypatch.setattr(app, "root_path", str(root))
    app.config["UPLOAD_FOLDER"] = str(uploads)
    return uploads


def _assert_webp_thumb(path, expected_width=500):
    assert path.exists()
    with Image.open(path) as thumb:
        assert thumb.format == "WEBP"
        assert thumb.width <= 500
        assert thumb.width == expected_width


@pytest.mark.parametrize(
    ("ext", "mime"),
    [
        ("jpg", "image/jpeg"),
        ("png", "image/png"),
        ("webp", "image/webp"),
        ("gif", "image/gif"),
    ],
)
def test_upload_generates_webp_thumbnail_for_supported_input_mimes(client, isolated_uploads, ext, mime):
    payload = _image_bytes(ext)
    response = client.post(
        "/api/upload",
        data={"file": (io.BytesIO(payload), f"phase23_parity.{ext}")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.json["data"]
    assert data["thumbnail_only"] is False
    assert data["filename"].endswith(f".{ext}")

    original = isolated_uploads / data["filename"]
    thumb = isolated_uploads / f"{Path(data['filename']).stem}_thumb.webp"
    assert original.exists()
    assert data["url"] == f"/static/uploads/{data['filename']}"
    _assert_webp_thumb(thumb)


def test_upload_thumbnail_only_returns_thumb_and_does_not_keep_original(client, isolated_uploads):
    response = client.post(
        "/api/upload",
        data={
            "file": (io.BytesIO(_image_bytes("png")), "thumb_only.png"),
            "thumbnail_only": "true",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.json["data"]
    assert data["thumbnail_only"] is True
    assert data["filename"].endswith("_thumb.webp")
    assert data["url"].endswith("_thumb.webp")
    _assert_webp_thumb(isolated_uploads / data["filename"])
    assert not list(isolated_uploads.glob("*thumb_only.png"))


def test_upload_thumbnail_unavailable_keeps_original_as_safe_fallback(
    client,
    isolated_uploads,
    monkeypatch,
):
    import routes.upload as upload_route

    monkeypatch.setattr(upload_route, "generate_webp_thumbnail", lambda *args, **kwargs: False)

    response = client.post(
        "/api/upload",
        data={
            "file": (io.BytesIO(_image_bytes("png")), "fallback.png"),
            "thumbnail_only": "true",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    data = response.json["data"]
    assert data["thumbnail_only"] is True
    assert data["filename"] is None
    assert data["url"].endswith(".png")
    assert not data["url"].endswith("_thumb.webp")
    fallback_name = data["url"].split("/static/uploads/")[-1]
    assert (isolated_uploads / fallback_name).exists()
    assert not list(isolated_uploads.glob("*fallback*_thumb.webp"))


class _FakeResponse:
    def __init__(self, content, content_type="image/png"):
        self.content = content
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        yield self.content


def test_upload_url_thumbnail_only_generates_thumb_without_original(
    client,
    isolated_uploads,
    monkeypatch,
):
    import routes.upload as upload_route

    payload = _image_bytes("png")
    monkeypatch.setattr(upload_route, "_is_ssrf_target", lambda hostname: False)
    monkeypatch.setattr(upload_route.requests, "get", lambda *args, **kwargs: _FakeResponse(payload))

    response = client.post(
        "/api/upload/url",
        json={"url": "https://example.test/remote.png", "thumbnail_only": True},
    )

    assert response.status_code == 200
    data = response.json["data"]
    assert data["thumbnail_only"] is True
    assert data["filename"].endswith("_thumb.webp")
    assert data["url"].endswith("_thumb.webp")
    _assert_webp_thumb(isolated_uploads / data["filename"])
    assert not list(isolated_uploads.glob("*remote.png"))


def test_import_image_helper_thumbnail_only_success_and_failure_fallback(
    isolated_uploads,
    monkeypatch,
):
    import routes.notes.import_ as import_route

    payload = _image_bytes("png")
    monkeypatch.setattr(import_route.requests, "get", lambda *args, **kwargs: _FakeResponse(payload))

    thumb_url, thumb_success = import_route.download_and_save_image(
        "https://example.test/imported.png",
        str(isolated_uploads),
        thumbnail_only=True,
    )

    assert thumb_success is True
    assert thumb_url.endswith("_thumb.webp")
    thumb_name = thumb_url.split("/static/uploads/")[-1]
    _assert_webp_thumb(isolated_uploads / thumb_name)
    assert not [path for path in isolated_uploads.glob("imported_*.png") if not path.name.endswith("_thumb.webp")]

    monkeypatch.setattr(import_route, "generate_webp_thumbnail", lambda *args, **kwargs: False)
    fallback_url, fallback_success = import_route.download_and_save_image(
        "https://example.test/fallback.png",
        str(isolated_uploads),
        thumbnail_only=True,
    )

    assert fallback_success is True
    assert fallback_url.endswith(".png")
    fallback_name = fallback_url.split("/static/uploads/")[-1]
    assert (isolated_uploads / fallback_name).exists()
    assert not (isolated_uploads / f"{Path(fallback_name).stem}_thumb.webp").exists()


def test_upload_delete_and_cleanup_discover_webp_thumb_companions(
    client,
    app,
    isolated_uploads,
):
    from db import get_db

    original = isolated_uploads / "cleanup_original.png"
    thumb = isolated_uploads / "cleanup_original_thumb.webp"
    original.write_bytes(_image_bytes("png"))
    thumb.write_bytes(_image_bytes("webp"))

    delete_response = client.post(
        "/api/upload/delete",
        json={"url": "/static/uploads/cleanup_original.png"},
    )
    assert delete_response.status_code == 200
    assert set(delete_response.json["data"]["deleted"]) == {
        "cleanup_original.png",
        "cleanup_original_thumb.webp",
    }
    assert not original.exists()
    assert not thumb.exists()

    referenced_original = isolated_uploads / "referenced.png"
    referenced_thumb = isolated_uploads / "referenced_thumb.webp"
    referenced_original.write_bytes(_image_bytes("png"))
    referenced_thumb.write_bytes(_image_bytes("webp"))

    with app.app_context():
        db = get_db()
        category = db.execute("SELECT id FROM Categories WHERE is_default = 1 LIMIT 1").fetchone()
        db.execute(
            "INSERT INTO Notes (title, content, category_id) VALUES (?, ?, ?)",
            (
                "Referenced thumbnail",
                "![img](/static/uploads/referenced.png)",
                category["id"],
            ),
        )
        db.commit()

    orphan_response = client.get("/api/cleanup/orphan-images")
    assert orphan_response.status_code == 200
    orphan_names = {
        item["filename"]
        for item in orphan_response.json["data"]["orphan_images"]
    }
    assert "referenced.png" not in orphan_names
    assert "referenced_thumb.webp" not in orphan_names


def test_thumbnail_contracts_are_completed_and_pillow_removal_is_blocked():
    parity = _load(PARITY_CONTRACT_PATH)
    removal = _load(REMOVAL_CONTRACT_PATH)

    assert parity["phase"] == "23.8-thumb.2"
    assert parity["status"] == "completed"
    assert parity["scope_type"] == "fixture_lock_only"
    assert all(changed is False for changed in parity["runtime_changes"].values())
    assert parity["allowed_next_step"]["id"] == "23.8-thumb.3"
    assert "image/jpeg" in parity["fixture_coverage"]["post_api_upload_standard"]
    assert "image/gif" in parity["fixture_coverage"]["post_api_upload_standard"]
    assert "thumbnail_only=true returns _thumb.webp" in parity["fixture_coverage"]["post_api_upload_thumbnail_only_success"]

    assert removal["phase"] == "23.8-thumb.3"
    assert removal["status"] == "completed_blocked_removal"
    assert removal["decision"] == "retain_pillow_until_go_thumbnail_candidate_exists_and_passes_packaging_smoke"
    assert removal["removal_allowed"] is False
    assert removal["gate_criteria"]["go_encoder_dependency_decision_complete"] is True
    assert removal["gate_criteria"]["thumbnail_parity_fixtures_complete"] is True
    assert removal["gate_criteria"]["go_thumbnail_candidate_implemented"] is False
    assert removal["gate_criteria"]["go_thumbnail_candidate_packaging_smoke_passed"] is False
    assert removal["allowed_next_step"]["id"] == "23.8-thumb.4"


def test_pillow_runtime_files_are_removed_after_dependency_closure():
    removal = json.loads(REMOVAL_CONTRACT_PATH.read_text(encoding="utf-8"))
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    start_bat = START_BAT_PATH.read_text(encoding="utf-8")
    api_reference = API_REFERENCE_PATH.read_text(encoding="utf-8")
    sequence_upload = SEQUENCE_UPLOAD_PATH.read_text(encoding="utf-8")
    upload_route = UPLOAD_ROUTE_PATH.read_text(encoding="utf-8")
    import_route = IMPORT_ROUTE_PATH.read_text(encoding="utf-8")
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert removal["runtime_changes"]["go_mod_changed"] is False
    assert removal["runtime_changes"]["go_webp_encoder_added"] is False
    assert "Pillow" not in requirements
    assert "import PIL" not in start_bat
    assert "Pillow install failed, thumbnails will be disabled" not in start_bat
    assert "thumbnail_only" in api_reference
    assert "Pillow" not in sequence_upload
    assert "from PIL import Image" not in upload_route
    assert "from PIL import Image" not in import_route
    assert "generate_webp_thumbnail" in upload_route
    assert "generate_webp_thumbnail" in import_route
    assert "--thumbnail-input" in main_go
    assert "thumbnailWebPQuality float32 = 80" in main_go


def test_docs_record_thumbnail_fixture_completion_blocked_removal_and_next_gate():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "23.8-thumb Go WebP thumbnail ownership / Pillow removal track" in todo
    assert "23.8-thumb.2** Thumbnail parity fixtures" in todo
    assert "docs/contracts/phase23-go-thumbnail-parity-fixtures.json" in todo
    assert "23.8-thumb.3** Pillow removal gate" in todo
    assert "docs/contracts/phase23-go-pillow-removal-gate.json" in todo
    assert "23.8-thumb.4** Go thumbnail local implementation candidate" in todo
    assert "Phase 23.8-thumb.2 Thumbnail parity fixtures is complete" in architecture
    assert "Phase 23.8-thumb.3 Pillow removal gate is complete as blocked-removal" in architecture
    assert "`23.8-thumb.2 Thumbnail parity fixtures` is complete" in go_report
    assert "`23.8-thumb.3 Pillow removal gate` is complete as blocked-removal" in go_report

