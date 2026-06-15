import json
import os
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tests.go_primary_parity_harness import build_go_shadow_exe


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
GO_MAIN_PATH = GO_SHADOW_DIR / "main.go"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
GO_README_PATH = GO_SHADOW_DIR / "README.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"
ROUTE_MANIFEST_PATH = ROOT / "docs" / "contracts" / "go-primary-route-ownership-manifest.json"
CONTRACTS = {
    "T024": ROOT / "docs" / "contracts" / "go-primary-upload-delete-parity.json",
    "T025": ROOT / "docs" / "contracts" / "go-primary-orphan-images-cleanup-parity.json",
    "T026": ROOT / "docs" / "contracts" / "go-primary-originals-cleanup-parity.json",
    "T027": ROOT / "docs" / "contracts" / "go-primary-broken-images-cleanup-parity.json",
}


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_go(db_path, data_dir, tmp_path, *flags):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; contract/static checks still run.")

    port = _free_port()
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db",
            db_path,
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            str(data_dir),
            *flags,
        ],
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            _request_json(base, "/api/test")
            return proc, base
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.25)

    output = proc.stdout.read() if proc.stdout else ""
    proc.terminate()
    pytest.fail(f"Go T024-T027 candidate did not start:\n{output}")


def _request_json(base, path, *, method="GET", data=None):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base.rstrip("/") + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            parsed = json.loads(payload) if payload else None
        except json.JSONDecodeError:
            parsed = payload
        return exc.code, parsed


def _stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _write_upload(data_dir, filename, content=b"fixture"):
    uploads = Path(data_dir) / "static" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    target = uploads / filename
    target.write_bytes(content)
    return target


def _note_content(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT content, cover_image FROM Notes WHERE id = 1").fetchone()
    finally:
        conn.close()


def _set_note_media(db_path, content, cover_image=""):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE Notes SET content = ?, cover_image = ? WHERE id = 1",
            (content, cover_image),
        )
        conn.commit()
    finally:
        conn.close()


def test_t024_upload_delete_preserves_references_and_deletes_companions(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t024.db")
    go_data = tmp_path / "go_data"
    _set_note_media(go_db, "![ref](/static/uploads/referenced.png)")
    for name in ("referenced.png", "referenced_thumb.webp", "delete_me.png", "delete_me_thumb.webp"):
        _write_upload(go_data, name)

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-upload-delete")
    try:
        status, health = _request_json(base, "/healthz")
        assert status == 200
        assert health["runtime"]["api_surface"] == "get-read-only+local-upload-delete"
        assert health["runtime"]["sqlite_query_only"] is True

        status, payload = _request_json(
            base,
            "/api/upload/delete",
            method="POST",
            data={"url": "/static/uploads/referenced.png"},
        )
        assert status == 200
        assert payload["data"]["deleted"] == []
        assert (go_data / "static" / "uploads" / "referenced.png").exists()
        assert (go_data / "static" / "uploads" / "referenced_thumb.webp").exists()

        status, payload = _request_json(
            base,
            "/api/upload/delete",
            method="POST",
            data={"url": "/static/uploads/delete_me.png"},
        )
        assert status == 200
        assert set(payload["data"]["deleted"]) == {"delete_me.png", "delete_me_thumb.webp"}
        assert not (go_data / "static" / "uploads" / "delete_me.png").exists()
        assert not (go_data / "static" / "uploads" / "delete_me_thumb.webp").exists()
    finally:
        _stop(proc)


def test_t025_orphan_scan_and_delete_only_true_orphans(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t025.db")
    go_data = tmp_path / "go_data"
    attachments_dir = go_data / "docs" / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    (attachments_dir / "refs.md").write_text("![a](/static/uploads/attachment_ref.png)", encoding="utf-8")
    _set_note_media(
        go_db,
        "\n".join(
            [
                "![ref](/static/uploads/referenced.png)",
                "![thumb](/static/uploads/thumb_only_ref_thumb.webp)",
            ]
        ),
    )
    conn = sqlite3.connect(go_db)
    try:
        conn.execute(
            """
            INSERT INTO Note_Attachments
                (note_id, file_path, file_type, title, size_bytes, is_auto_extracted)
            VALUES (1, 'docs/attachments/refs.md', 'md', 'refs', 34, 0)
            """
        )
        conn.commit()
    finally:
        conn.close()

    for name in (
        "referenced.png",
        "referenced_thumb.webp",
        "attachment_ref.png",
        "thumb_only_ref.png",
        "thumb_only_ref_thumb.webp",
        "orphan.png",
        "orphan_thumb.webp",
    ):
        _write_upload(go_data, name)

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-media-cleanup")
    try:
        status, health = _request_json(base, "/healthz")
        assert status == 200
        assert health["runtime"]["api_surface"] == "get-read-only+local-media-cleanup"
        assert health["runtime"]["sqlite_query_only"] is False

        status, payload = _request_json(base, "/api/cleanup/orphan-images")
        assert status == 200
        orphan_names = {item["filename"] for item in payload["data"]["orphan_images"]}
        assert {"orphan.png", "orphan_thumb.webp"} <= orphan_names
        assert "referenced.png" not in orphan_names
        assert "referenced_thumb.webp" not in orphan_names
        assert "attachment_ref.png" not in orphan_names
        assert "thumb_only_ref.png" in orphan_names
        assert "thumb_only_ref_thumb.webp" not in orphan_names

        status, payload = _request_json(
            base,
            "/api/cleanup/orphan-images",
            method="DELETE",
            data={"filenames": ["orphan.png", "thumb_only_ref.png", "referenced.png"]},
        )
        assert status == 200
        assert set(payload["data"]["deleted"]) == {"orphan.png", "orphan_thumb.webp", "thumb_only_ref.png"}
        assert payload["data"]["errors"] == [{"filename": "referenced.png", "error": "File is not orphan"}]
        assert not (go_data / "static" / "uploads" / "orphan.png").exists()
        assert not (go_data / "static" / "uploads" / "orphan_thumb.webp").exists()
        assert not (go_data / "static" / "uploads" / "thumb_only_ref.png").exists()
        assert (go_data / "static" / "uploads" / "thumb_only_ref_thumb.webp").exists()
        assert (go_data / "static" / "uploads" / "referenced.png").exists()
    finally:
        _stop(proc)


def test_t026_originals_cleanup_rewrites_references_and_keeps_thumbnail_only(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t026.db")
    go_data = tmp_path / "go_data"
    _set_note_media(
        go_db,
        "![original](/static/uploads/original.png)",
        "/static/uploads/cover.jpg",
    )
    for name in (
        "original.png",
        "original_thumb.webp",
        "cover.jpg",
        "cover_thumb.webp",
        "unused.png",
        "unused_thumb.webp",
        "thumb_only_thumb.webp",
    ):
        _write_upload(go_data, name)

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-media-cleanup")
    try:
        status, payload = _request_json(base, "/api/cleanup/originals")
        assert status == 200
        assert payload["data"]["original_count"] == 3
        assert payload["data"]["thumbnail_count"] == 4

        status, payload = _request_json(base, "/api/cleanup/originals", method="DELETE")
        assert status == 200
        assert payload["data"]["deleted_count"] == 3
        assert payload["data"]["updated_notes"] == 1

        uploads = go_data / "static" / "uploads"
        for name in ("original.png", "cover.jpg", "unused.png"):
            assert not (uploads / name).exists()
        for name in ("original_thumb.webp", "cover_thumb.webp", "unused_thumb.webp", "thumb_only_thumb.webp"):
            assert (uploads / name).exists()
        content, cover = _note_content(go_db)
        assert "/static/uploads/original_thumb.webp" in content
        assert cover == "/static/uploads/cover_thumb.webp"
    finally:
        _stop(proc)


def test_t027_broken_images_scan_and_fix_updates_markdown_and_cover(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t027.db")
    go_data = tmp_path / "go_data"
    _set_note_media(
        go_db,
        " ".join(
            [
                "![missing](/static/uploads/missing.png)",
                "![broken-thumb](/static/uploads/broken_thumb.webp)",
                "![nofix](/static/uploads/nofix.png)",
            ]
        ),
        "/static/uploads/cover.jpg",
    )
    for name in ("missing_thumb.webp", "cover_thumb.webp"):
        _write_upload(go_data, name)

    proc, base = _start_go(go_db, go_data, tmp_path, "--enable-media-cleanup")
    try:
        status, payload = _request_json(base, "/api/cleanup/broken-images")
        assert status == 200
        data = payload["data"]
        assert data["total_count"] == 4
        assert data["fixable_count"] == 2
        by_path = {item["original_path"]: item for item in data["broken_paths"]}
        assert by_path["/static/uploads/missing.png"]["thumbnail_path"] == "/static/uploads/missing_thumb.webp"
        assert by_path["/static/uploads/missing.png"]["can_fix"] is True
        assert by_path["/static/uploads/broken_thumb.webp"]["reason"] == "thumbnail_missing"
        assert by_path["/static/uploads/nofix.png"]["can_fix"] is False
        assert by_path["/static/uploads/cover.jpg"]["is_cover"] is True

        status, payload = _request_json(base, "/api/cleanup/broken-images", method="POST")
        assert status == 200
        assert payload["data"] == {"fixed_count": 2, "updated_notes": 1}
        content, cover = _note_content(go_db)
        assert "/static/uploads/missing_thumb.webp" in content
        assert "/static/uploads/nofix.png" in content
        assert "/static/uploads/broken_thumb.webp" in content
        assert cover == "/static/uploads/cover_thumb.webp"
    finally:
        _stop(proc)


def _load_contract(task_id):
    return json.loads(CONTRACTS[task_id].read_text(encoding="utf-8"))


def test_t024_t027_contracts_docs_and_route_manifest_are_closed():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")
    manifest = ROUTE_MANIFEST_PATH.read_text(encoding="utf-8")

    expected = {
        "T024": ("CONTRACT-GO-PRIMARY-UPLOADS", "--enable-upload-delete"),
        "T025": ("CONTRACT-GO-PRIMARY-MEDIA-CLEANUP", "--enable-media-cleanup"),
        "T026": ("CONTRACT-GO-PRIMARY-MEDIA-CLEANUP", "--enable-media-cleanup"),
        "T027": ("CONTRACT-GO-PRIMARY-MEDIA-CLEANUP", "--enable-media-cleanup"),
    }
    for task_id, (contract_name, flag) in expected.items():
        contract = _load_contract(task_id)
        assert contract["task_id"] == task_id
        assert contract["contract"] == contract_name
        assert contract["status"] == "completed_local_candidate"
        assert contract["enable_flag"] == flag
        assert contract["runtime_boundary"]["production_db_write"] is False
        assert contract["runtime_boundary"]["production_filesystem_mutation"] is False
        assert contract["runtime_boundary"]["pi_deploy"] is False
        assert Path(contract["validation"]["targeted_tests"][0]).name == Path(__file__).name
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")

    assert '"enable-upload-delete"' in main_go
    assert "PRISM_GO_ENABLE_UPLOAD_DELETE" in main_go
    assert '"enable-media-cleanup"' in main_go
    assert "PRISM_GO_ENABLE_MEDIA_CLEANUP" in main_go
    assert "referencedUploadFilenames" in main_go
    assert "orphanUploadImages" in main_go
    assert "brokenImageReferences" in main_go

    assert "T024-T027 Go upload delete/media cleanup gates 已完成" in todo
    assert "T024-T027 Go upload delete/media cleanup local candidates are complete" in architecture
    assert "Go T024-T027" in schema
    assert "Upload Delete And Media Cleanup" in readme
    assert "T024-T027" in go_report
    assert "implemented local copied-data upload delete candidate only" in manifest
    assert "implemented local copied-DB-and-data media cleanup candidate only" in manifest
    assert _load_contract("T027")["allowed_next_step"]["id"] == "T028"
