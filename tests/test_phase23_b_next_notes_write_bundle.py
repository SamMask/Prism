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
CONTRACT_PATH = ROOT / "docs" / "contracts" / "phase23-b-next-notes-write-bundle.json"
RUNTIME_CLOSURE_PATH = ROOT / "docs" / "contracts" / "phase23-python-runtime-ownership-closure.json"
GO_MAIN_PATH = GO_SHADOW_DIR / "main.go"
TODO_PATH = ROOT / "docs" / "development-history" / "todo-archive-pre-go-primary-runtime-migration-20260606.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
GO_REPORT_PATH = ROOT / "docs" / "development-history" / "Prism_Go_模組逐步重構計劃報告.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _read_json(url, *, data=None, method="GET"):
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _start_go_candidate(go_bin, db_path, port, tmp_path):
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    proc = subprocess.Popen(
        [
            str(exe_path),
            "--db",
            db_path,
            "--addr",
            f"127.0.0.1:{port}",
            "--data-dir",
            str(tmp_path),
            "--enable-notes-write",
        ],
        env={**os.environ, "PRISM_GO_ENABLE_NOTES_WRITE": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            _read_json(base + "/api/test")
            return proc, base
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.25)
    output = proc.stdout.read() if proc.stdout else ""
    proc.terminate()
    pytest.fail(f"Go notes-write candidate did not start:\n{output}")


def _flask_client(db_path):
    from app import create_app

    app = create_app("testing")
    app.config.update(
        {
            "TESTING": True,
            "DATABASE": db_path,
            "WTF_CSRF_ENABLED": False,
            "PROPAGATE_EXCEPTIONS": True,
        }
    )
    ctx = app.app_context()
    ctx.push()
    return app.test_client(), ctx


def _seed_notes_bundle_fixture(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES ('alpha-notes', 'A', 40, 0)")
        conn.execute("INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES ('beta-notes', 'B', 50, 0)")
        alpha = conn.execute("SELECT id FROM Categories WHERE name = 'alpha-notes'").fetchone()[0]
        beta = conn.execute("SELECT id FROM Categories WHERE name = 'beta-notes'").fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('seed-tag')")
        tag_id = conn.execute("SELECT id FROM Tags WHERE name = 'seed-tag'").fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO Notes (title, content, remarks, category_id, sort_order)
            VALUES ('Bundle Seed', 'original bundle content', 'seed remarks', ?, 10)
            """,
            (alpha,),
        )
        seed_id = cursor.lastrowid
        cursor = conn.execute(
            """
            INSERT INTO Notes (title, content, remarks, category_id, sort_order)
            VALUES ('Bundle Delete', 'delete target content', 'delete remarks', ?, 20)
            """,
            (alpha,),
        )
        delete_id = cursor.lastrowid
        conn.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (seed_id, tag_id))
        conn.execute("INSERT INTO Source_Urls (note_id, url) VALUES (?, 'https://seed.example')", (seed_id,))
        conn.execute("INSERT INTO Note_History (note_id, content, diff_summary) VALUES (?, 'older bundle content', 'seed history')", (seed_id,))
        conn.commit()
        return {"alpha": alpha, "beta": beta, "seed": seed_id, "delete": delete_id}
    finally:
        conn.close()


def _snapshot(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {
            "notes": conn.execute(
                """
                SELECT id, title, content, remarks, cover_image, cover_position, editor_layout,
                       category_id, prompt_params, parent_id, COALESCE(is_pinned, 0),
                       COALESCE(is_archived, 0), COALESCE(sort_order, 0)
                FROM Notes ORDER BY id
                """
            ).fetchall(),
            "tags": conn.execute("SELECT id, name FROM Tags ORDER BY id").fetchall(),
            "note_tags": conn.execute("SELECT note_id, tag_id FROM Note_Tags ORDER BY note_id, tag_id").fetchall(),
            "urls": conn.execute("SELECT note_id, url FROM Source_Urls ORDER BY note_id, id").fetchall(),
            "history": conn.execute(
                "SELECT note_id, content, diff_summary FROM Note_History ORDER BY note_id, id"
            ).fetchall(),
        }
    finally:
        conn.close()


def _normalize_history(payload):
    data = payload["data"]
    return {
        "note_id": data["note_id"],
        "note_title": data["note_title"],
        "total": data["total"],
        "history": [
            {
                "content": row["content"],
                "diff_summary": row["diff_summary"],
            }
            for row in data["history"]
        ],
    }


def _go_call(base, path, *, data=None, method="GET"):
    return _read_json(base + path, data=data, method=method)


def test_b_next_1_contract_records_local_copied_db_notes_bundle():
    contract = _contract()
    runtime_closure = json.loads(RUNTIME_CLOSURE_PATH.read_text(encoding="utf-8"))

    assert contract["phase"] == "B-next.1"
    assert contract["status"] == "completed_local_candidate"
    assert contract["explicit_user_approval"] is True
    assert contract["source_contract"] == "docs/contracts/phase23-python-runtime-ownership-closure.json"
    assert runtime_closure["status"] == "completed_final_retained_python_closure"
    assert runtime_closure["executed_notes_bundle_candidate"]["id"] == "B-next.1"
    assert runtime_closure["final_closure"]["no_b_next"] is True
    assert contract["runtime_change"] == "local_copied_db_only"
    assert contract["live_execution_authorized"] is False
    assert contract["production_db_write"] is False
    assert contract["pi_deploy"] is False
    assert contract["caddy_or_service_change"] is False
    assert contract["frontend_default_change"] is False


def test_go_notes_write_is_flag_gated_and_default_runtime_stays_read_only():
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")
    implementation = _contract()["implementation"]

    assert implementation["enable_flag"] == "--enable-notes-write"
    assert implementation["enable_env"] == "PRISM_GO_ENABLE_NOTES_WRITE=1"
    assert implementation["default_runtime_mode"]["sqlite_query_only"] is True
    assert implementation["explicit_local_candidate_mode"]["sqlite_query_only"] is False
    assert "enableNotesWrite" in main_go
    assert '"enable-notes-write"' in main_go
    assert '"PRISM_GO_ENABLE_NOTES_WRITE"' in main_go
    assert "Notes write route is disabled" in main_go
    assert "PRAGMA query_only = ON" in main_go


def test_go_notes_write_actions_history_batch_match_python_response_and_db_state(temp_db, tmp_path):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; static contract checks still run.")

    py_db = _copy_db(temp_db, tmp_path / "python_notes_bundle_test.db")
    go_db = _copy_db(temp_db, tmp_path / "go_notes_bundle_test.db")
    py_ids = _seed_notes_bundle_fixture(py_db)
    go_ids = _seed_notes_bundle_fixture(go_db)
    assert py_ids == go_ids

    py_client, ctx = _flask_client(py_db)
    port = _free_port()
    proc, base = _start_go_candidate(go_bin, go_db, port, tmp_path)
    try:
        health_status, health_json = _go_call(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-notes-write"
        assert health_json["runtime"]["sqlite_query_only"] is False

        create_payload = {
            "title": "Created Bundle",
            "content": "created bundle content",
            "category_id": py_ids["alpha"],
            "remarks": "created remarks",
            "tags": ["bundle-tag", "extra-tag"],
            "urls": ["https://created.example"],
            "is_pinned": True,
        }
        py_response = py_client.post("/api/notes", json=create_payload)
        go_status, go_json = _go_call(base, "/api/notes", data=create_payload, method="POST")
        assert go_status == py_response.status_code == 201
        assert go_json == py_response.get_json()
        created_id = go_json["data"]["note_id"]

        update_payload = {
            "title": "Updated Bundle",
            "content": "updated bundle content",
            "category_id": py_ids["beta"],
            "remarks": "updated remarks",
            "tags": ["updated-tag"],
            "urls": ["https://updated.example"],
            "is_archived": True,
        }
        py_response = py_client.put(f"/api/notes/{created_id}", json=update_payload)
        go_status, go_json = _go_call(base, f"/api/notes/{created_id}", data=update_payload, method="PUT")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        for path, payload in [
            (f"/api/notes/{created_id}/pin", {"pinned": False}),
            (f"/api/notes/{created_id}/archive", {"archived": False}),
        ]:
            py_response = py_client.post(path, json=payload)
            go_status, go_json = _go_call(base, path, data=payload, method="POST")
            assert go_status == py_response.status_code == 200
            assert go_json == py_response.get_json()

        duplicate_payload = {"as_variant": True, "title_suffix": " (Variant)"}
        py_response = py_client.post(f"/api/notes/{created_id}/duplicate", json=duplicate_payload)
        go_status, go_json = _go_call(base, f"/api/notes/{created_id}/duplicate", data=duplicate_payload, method="POST")
        assert go_status == py_response.status_code == 201
        assert go_json == py_response.get_json()
        variant_id = go_json["data"]["note_id"]

        reorder_payload = {"note_ids": [variant_id, created_id, py_ids["seed"]]}
        py_response = py_client.put("/api/notes/reorder", json=reorder_payload)
        go_status, go_json = _go_call(base, "/api/notes/reorder", data=reorder_payload, method="PUT")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        type_payload = {"note_ids": [created_id, variant_id], "category_id": py_ids["alpha"]}
        py_response = py_client.post("/api/notes/batch/type", json=type_payload)
        go_status, go_json = _go_call(base, "/api/notes/batch/type", data=type_payload, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        tags_payload = {"note_ids": [created_id, variant_id], "tags": ["batch-tag"], "mode": "append"}
        py_response = py_client.post("/api/notes/batch/tags", json=tags_payload)
        go_status, go_json = _go_call(base, "/api/notes/batch/tags", data=tags_payload, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        py_response = py_client.get(f"/api/notes/{created_id}/history")
        go_status, go_json = _go_call(base, f"/api/notes/{created_id}/history")
        assert go_status == py_response.status_code == 200
        assert _normalize_history(go_json) == _normalize_history(py_response.get_json())
        history_id = py_response.get_json()["data"]["history"][0]["id"]

        py_response = py_client.post(f"/api/notes/{created_id}/restore/{history_id}")
        try:
            go_status, go_json = _go_call(base, f"/api/notes/{created_id}/restore/{history_id}", data={}, method="POST")
        except Exception as exc:
            proc.terminate()
            try:
                output, _ = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                output, _ = proc.communicate(timeout=5)
            pytest.fail(f"Go restore request failed: {exc}\n{output}")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        py_response = py_client.delete(f"/api/notes/{created_id}/history")
        go_status, go_json = _go_call(base, f"/api/notes/{created_id}/history", method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        delete_payload = {"note_ids": [py_ids["delete"]]}
        py_response = py_client.post("/api/notes/batch/delete", json=delete_payload)
        go_status, go_json = _go_call(base, "/api/notes/batch/delete", data=delete_payload, method="POST")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        py_response = py_client.delete(f"/api/notes/{variant_id}")
        go_status, go_json = _go_call(base, f"/api/notes/{variant_id}", method="DELETE")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()
    finally:
        ctx.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    assert _snapshot(go_db) == _snapshot(py_db)


def test_b_next_1_keeps_live_python_removal_and_later_release_steps_blocked():
    blocked = set(_contract()["not_authorized_by_b_next_1"])

    assert "Production knowledge.db write" in blocked
    assert "Pi deployment" in blocked
    assert "Caddy route edit or reload" in blocked
    assert "systemd service change" in blocked
    assert "Frontend default API target change" in blocked
    assert "Python backend removal" in blocked
    assert "Start C. Go packaged runtime release candidate" in blocked
    assert "Start D. Live cutover and rollback proof" in blocked
    assert "Start E. Python package deletion" in blocked
    assert "Declare B complete" in blocked


def test_docs_record_b_next_1_completion_and_next_detail():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    assert "B-next.1 Notes write/actions/history/batch packaged-runtime ownership bundle" in todo
    assert "docs/contracts/phase23-b-next-notes-write-bundle.json" in todo
    assert "completed_local_candidate" in todo
    assert "此項保留為證據，不再導向新的 B-next 細項" in todo
    assert "Phase 23 B-next.1 Notes write/actions/history/batch packaged-runtime ownership bundle is complete as a local/copied-DB candidate" in architecture
    assert "`B-next.1 Notes write/actions/history/batch packaged-runtime ownership bundle` is complete as a local/copied-DB candidate" in go_report

