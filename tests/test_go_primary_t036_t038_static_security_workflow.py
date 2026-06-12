import io
import json
import os
import shutil
import socket
import sqlite3
import struct
import subprocess
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path

import pytest

from tests.go_primary_parity_harness import build_go_shadow_exe


ROOT = Path(__file__).resolve().parents[1]
GO_MAIN_PATH = ROOT / "go-shadow" / "main.go"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
DEPLOY_PI_PATH = ROOT / "DEPLOY-PI.md"
GO_README_PATH = ROOT / "go-shadow" / "README.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"
ROUTE_MANIFEST_PATH = ROOT / "docs" / "contracts" / "go-primary-route-ownership-manifest.json"
CONTRACTS = {
    "T036": ROOT / "docs" / "contracts" / "go-primary-static-serving-boundary.json",
    "T037": ROOT / "docs" / "contracts" / "go-primary-security-parity.json",
    "T038": ROOT / "docs" / "contracts" / "go-primary-full-workflow-e2e.json",
}


def _png_bytes(width=1, height=1):
    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + (b"\xff\x00\x00" * width) for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


PNG_1X1 = _png_bytes()
GO_FULL_WORKFLOW_FLAGS = (
    "--enable-notes-write",
    "--enable-upload-write",
    "--enable-thumbnail-write",
    "--enable-upload-url-write",
    "--enable-upload-delete",
    "--enable-media-cleanup",
    "--enable-import-export",
    "--enable-server-system",
)


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _tree_bytes(root):
    root = Path(root)
    if not root.exists():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


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
    pytest.fail(f"Go T036-T038 candidate did not start:\n{output}")


def _stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def _request_bytes(base, path, *, method="GET", data=None, headers=None):
    body = data
    request_headers = dict(headers or {})
    if isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base.rstrip("/") + path,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def _request_json(base, path, *, method="GET", data=None):
    status, headers, body = _request_bytes(base, path, method=method, data=data)
    try:
        payload = json.loads(body.decode("utf-8")) if body else None
    except json.JSONDecodeError:
        payload = body.decode("utf-8", errors="replace")
    return status, payload, headers


def _request_multipart(base, path, files, fields=None):
    boundary = f"----prism-t036-{time.time_ns()}"
    body = io.BytesIO()
    for name, value in (fields or {}).items():
        body.write(f"--{boundary}\r\n".encode("ascii"))
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.write(str(value).encode("utf-8"))
        body.write(b"\r\n")
    for field, filename, content, content_type in files:
        body.write(f"--{boundary}\r\n".encode("ascii"))
        body.write(
            (
                f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        body.write(content)
        body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode("ascii"))
    status, headers, payload = _request_bytes(
        base,
        path,
        method="POST",
        data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        parsed = json.loads(payload.decode("utf-8")) if payload else None
    except json.JSONDecodeError:
        parsed = payload.decode("utf-8", errors="replace")
    return status, parsed, headers


def _query_scalar(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchone()[0]
    finally:
        conn.close()


def _go_workflow(db_path, data_dir, tmp_path):
    proc, base = _start_go(db_path, data_dir, tmp_path, *GO_FULL_WORKFLOW_FLAGS)
    try:
        status, health, _ = _request_json(base, "/healthz")
        assert status == 200
        assert "local-server-system" in health["runtime"]["api_surface"]
        assert health["runtime"]["security"]["auth"] == "none"

        create_payload = {
            "title": "T038 Workflow",
            "content": "t038-workflow-alpha seed",
            "tags": ["t038-go"],
            "urls": ["https://example.test/t038"],
            "remarks": "workflow",
        }
        status, payload, _ = _request_json(base, "/api/notes", method="POST", data=create_payload)
        assert status == 201
        note_id = payload["data"]["note_id"]

        status, upload, _ = _request_multipart(
            base,
            "/api/upload",
            [("file", "workflow.png", PNG_1X1, "image/png")],
            {"thumbnail_only": "false"},
        )
        assert status == 200
        image_url = upload["data"]["url"]

        status, _, body = _request_bytes(base, image_url)
        assert status == 200
        assert body == PNG_1X1

        update_payload = {
            "title": "T038 Workflow Updated",
            "content": f"t038-workflow-search-token image {image_url}",
            "cover_image": image_url,
            "tags": ["t038-go-updated"],
            "urls": ["https://example.test/t038-updated"],
        }
        status, payload, _ = _request_json(base, f"/api/notes/{note_id}", method="PUT", data=update_payload)
        assert status == 200
        assert payload["status"] == "success"

        status, search, _ = _request_json(base, "/api/notes?q=t038-workflow-search-token&per_page=20")
        assert status == 200
        assert any(item["id"] == note_id for item in search["data"])

        status, _, export_body = _request_bytes(base, "/api/export/json")
        assert status == 200
        exported = json.loads(export_body.decode("utf-8"))
        assert any(note["id"] == note_id for note in exported["notes"])

        import_payload = {
            "mode": "duplicate",
            "data": {
                "notes": [
                    {
                        "id": 3838,
                        "title": "T038 Imported",
                        "content": "t038-imported-token",
                        "category": "筆記",
                        "tags": ["t038-imported"],
                        "urls": ["https://example.test/imported"],
                    }
                ],
                "tags": [{"name": "t038-imported"}],
            },
        }
        status, imported, _ = _request_json(base, "/api/import/json", method="POST", data=import_payload)
        assert status == 200
        assert imported["data"]["imported"] == 1

        status, payload, _ = _request_json(base, f"/api/notes/{note_id}", method="DELETE")
        assert status == 200
        assert payload["status"] == "success"

        orphan = Path(data_dir) / "static" / "uploads" / "t038-orphan.png"
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_bytes(PNG_1X1)
        status, orphans, _ = _request_json(base, "/api/cleanup/orphan-images")
        assert status == 200
        assert "t038-orphan.png" in {item["filename"] for item in orphans["data"]["orphan_images"]}
        status, cleanup, _ = _request_json(
            base,
            "/api/cleanup/orphan-images",
            method="DELETE",
            data={"filenames": ["t038-orphan.png"]},
        )
        assert status == 200
        assert "t038-orphan.png" in cleanup["data"]["deleted"]
        assert not orphan.exists()

        status, headers, backup_body = _request_bytes(base, "/api/server/backup/download")
        assert status == 200
        assert "application/x-sqlite3" in headers["Content-Type"]
        assert backup_body.startswith(b"SQLite format 3")

        status, migration, _ = _request_json(base, "/api/system/migration-status")
        assert status == 200
        assert migration["data"]["current_version"] == migration["data"]["latest_version"]
        assert migration["data"]["pending"] == []
    finally:
        _stop(proc)

    return {
        "workflow_notes": _query_scalar(db_path, "SELECT COUNT(*) FROM Notes WHERE content LIKE '%t038-workflow-search-token%'"),
        "imported_notes": _query_scalar(db_path, "SELECT COUNT(*) FROM Notes WHERE content LIKE '%t038-imported-token%'"),
        "orphan_exists": (Path(data_dir) / "static" / "uploads" / "t038-orphan.png").exists(),
    }


def _flask_client(db_path, data_dir):
    from app import create_app

    app = create_app("testing")
    app.config.update(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "UPLOAD_FOLDER": str(Path(data_dir) / "static" / "uploads"),
            "PRISM_BACKUP_DIR": str(Path(data_dir) / "backups"),
            "WTF_CSRF_ENABLED": False,
            "PROPAGATE_EXCEPTIONS": True,
        }
    )
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["PRISM_BACKUP_DIR"]).mkdir(parents=True, exist_ok=True)
    app.root_path = str(data_dir)
    ctx = app.app_context()
    ctx.push()
    return app.test_client(), ctx


def _python_workflow(db_path, data_dir):
    client, ctx = _flask_client(db_path, data_dir)
    try:
        create_payload = {
            "title": "T038 Workflow",
            "content": "t038-workflow-alpha seed",
            "tags": ["t038-python"],
            "urls": ["https://example.test/t038"],
            "remarks": "workflow",
        }
        response = client.post("/api/notes", json=create_payload)
        assert response.status_code == 201
        note_id = response.get_json()["data"]["note_id"]

        response = client.post(
            "/api/upload",
            data={"file": (io.BytesIO(PNG_1X1), "workflow.png"), "thumbnail_only": "false"},
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        image_url = response.get_json()["data"]["url"]

        update_payload = {
            "title": "T038 Workflow Updated",
            "content": f"t038-workflow-search-token image {image_url}",
            "cover_image": image_url,
            "tags": ["t038-python-updated"],
            "urls": ["https://example.test/t038-updated"],
        }
        response = client.put(f"/api/notes/{note_id}", json=update_payload)
        assert response.status_code == 200

        response = client.get("/api/notes?q=t038-workflow-search-token&per_page=20")
        assert response.status_code == 200
        assert any(item["id"] == note_id for item in response.get_json()["data"])

        response = client.get("/api/export/json")
        assert response.status_code == 200
        exported = json.loads(response.get_data(as_text=True))
        assert any(note["id"] == note_id for note in exported["notes"])

        import_payload = {
            "mode": "duplicate",
            "data": {
                "notes": [
                    {
                        "id": 3838,
                        "title": "T038 Imported",
                        "content": "t038-imported-token",
                        "category": "筆記",
                        "tags": ["t038-imported"],
                        "urls": ["https://example.test/imported"],
                    }
                ],
                "tags": [{"name": "t038-imported"}],
            },
        }
        response = client.post("/api/import/json", json=import_payload)
        assert response.status_code == 200
        assert response.get_json()["data"]["imported"] == 1

        response = client.delete(f"/api/notes/{note_id}")
        assert response.status_code == 200

        orphan = Path(data_dir) / "static" / "uploads" / "t038-orphan.png"
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_bytes(PNG_1X1)
        response = client.get("/api/cleanup/orphan-images")
        assert response.status_code == 200
        assert "t038-orphan.png" in {item["filename"] for item in response.get_json()["data"]["orphan_images"]}
        response = client.delete("/api/cleanup/orphan-images", json={"filenames": ["t038-orphan.png"]})
        assert response.status_code == 200
        assert "t038-orphan.png" in response.get_json()["data"]["deleted"]
        assert not orphan.exists()

        response = client.get("/api/server/backup/download")
        assert response.status_code == 200
        assert response.data.startswith(b"SQLite format 3")

        response = client.get("/api/system/migration-status")
        assert response.status_code == 200
        migration = response.get_json()["data"]
        assert migration["current_version"] == migration["latest_version"]
        assert migration["pending"] == []
    finally:
        ctx.pop()

    return {
        "workflow_notes": _query_scalar(db_path, "SELECT COUNT(*) FROM Notes WHERE content LIKE '%t038-workflow-search-token%'"),
        "imported_notes": _query_scalar(db_path, "SELECT COUNT(*) FROM Notes WHERE content LIKE '%t038-imported-token%'"),
        "orphan_exists": (Path(data_dir) / "static" / "uploads" / "t038-orphan.png").exists(),
    }


def test_t036_static_uploads_spa_and_api_fallback_boundaries(temp_db, tmp_path):
    go_db = _copy_db(temp_db, tmp_path / "go_t036.db")
    go_data = tmp_path / "go_data"
    upload = go_data / "static" / "uploads" / "t036.png"
    upload.parent.mkdir(parents=True, exist_ok=True)
    upload.write_bytes(PNG_1X1)
    secret = go_data / "static" / "secret.txt"
    secret.write_text("do-not-serve", encoding="utf-8")

    proc, base = _start_go(go_db, go_data, tmp_path)
    try:
        for spa_path in ("/", "/notes/123"):
            status, headers, body = _request_bytes(base, spa_path)
            assert status == 200
            assert headers["Content-Type"].startswith("text/html")
            assert b'<div id="root"></div>' in body

        status, headers, body = _request_bytes(base, "/static/uploads/t036.png")
        assert status == 200
        assert headers["Content-Type"].startswith("image/png")
        assert body == PNG_1X1

        status, payload, headers = _request_json(base, "/api/not-real")
        assert status == 404
        assert headers["Content-Type"].startswith("application/json")
        assert payload == {"status": "error", "message": "API route not found"}

        for unsafe_path in ("/static/uploads", "/static/uploads/", "/static/uploads/..%2Fsecret.txt"):
            status, headers, body = _request_bytes(base, unsafe_path)
            assert status == 404
            assert b"do-not-serve" not in body
    finally:
        _stop(proc)


def test_t037_security_public_bind_and_dangerous_inputs_do_not_mutate_files(temp_db, tmp_path):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; static checks still run.")
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    data_dir = tmp_path / "public_bind_data"
    env = dict(os.environ)
    env.pop("PRISM_GO_ALLOW_PUBLIC_BIND", None)
    result = subprocess.run(
        [
            str(exe_path),
            "--db",
            str(data_dir / "go_t037.db"),
            "--addr",
            "0.0.0.0:0",
            "--data-dir",
            str(data_dir),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "refusing non-local Go bind" in result.stdout
    assert "no built-in auth/token layer" in result.stdout

    go_db = _copy_db(temp_db, tmp_path / "go_t037.db")
    go_data = tmp_path / "go_data"
    proc, base = _start_go(
        go_db,
        go_data,
        tmp_path,
        "--enable-upload-write",
        "--enable-thumbnail-write",
        "--enable-upload-url-write",
    )
    try:
        status, health, _ = _request_json(base, "/healthz")
        assert status == 200
        assert health["runtime"]["security"]["exposure_policy"].startswith("trusted LAN/VPN")

        uploads_before = _tree_bytes(go_data / "static" / "uploads")
        status, payload, _ = _request_json(
            base,
            "/api/upload/url",
            method="POST",
            data={"url": "http://127.0.0.1/private.png"},
        )
        assert status == 400
        assert "private or reserved IP" in payload["message"]
        assert _tree_bytes(go_data / "static" / "uploads") == uploads_before

        status, payload, _ = _request_multipart(
            base,
            "/api/upload",
            [("file", "not-an-image.png", b"<html>nope</html>", "image/png")],
            {"thumbnail_only": "false"},
        )
        assert status == 400
        assert payload["status"] == "error"
        assert _tree_bytes(go_data / "static" / "uploads") == uploads_before
    finally:
        _stop(proc)


def test_t038_full_workflow_python_and_go_core_invariants_match(temp_db, tmp_path):
    py_db = _copy_db(temp_db, tmp_path / "python_t038.db")
    go_db = _copy_db(temp_db, tmp_path / "go_t038.db")
    py_data = tmp_path / "python_data"
    go_data = tmp_path / "go_data"

    python_result = _python_workflow(py_db, py_data)
    go_result = _go_workflow(go_db, go_data, tmp_path)

    assert python_result == {
        "workflow_notes": 0,
        "imported_notes": 1,
        "orphan_exists": False,
    }
    assert go_result == python_result


def test_t036_t037_t038_contracts_docs_and_route_manifest_are_current():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    deploy_pi = DEPLOY_PI_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    route_manifest = json.loads(ROUTE_MANIFEST_PATH.read_text(encoding="utf-8"))

    for task_id, path in CONTRACTS.items():
        contract = json.loads(path.read_text(encoding="utf-8"))
        assert contract["task_id"] == task_id
        assert contract["status"] == "completed_local_candidate"
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")

    assert "go-primary-static-serving-boundary.json" in todo
    assert "go-primary-security-parity.json" in todo
    assert "go-primary-full-workflow-e2e.json" in todo
    assert "T036/T037/T038 Go static/security/full workflow gate is complete" in architecture
    assert "Go T036/T037/T038" in schema
    assert "no built-in auth/token layer" in deploy_pi
    assert "Static Serving, Security, Full Workflow" in readme
    assert "T036/T037/T038" in go_report
    assert "serveStaticUpload" in main_go
    assert "PRISM_GO_ALLOW_PUBLIC_BIND" in main_go

    routes = {(item["rule"], tuple(item["methods"])): item for item in route_manifest["routes"]}
    assert routes[("/", ("GET",))]["go_candidate"] == "implemented local embedded SPA candidate only"
    assert routes[("/<path:path>", ("GET",))]["go_candidate"] == "implemented local embedded SPA candidate only"
    assert routes[("/static/<path:filename>", ("GET",))]["go_candidate"] == "implemented local static/uploads candidate only"
