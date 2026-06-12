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
READ_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-notes-read-search-parity.json"
WRITE_CONTRACT_PATH = ROOT / "docs" / "contracts" / "go-primary-notes-create-update-parity.json"
TODO_PATH = ROOT / "docs" / "TODO.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
SCHEMA_PATH = ROOT / "docs" / "SCHEMA.md"
GO_README_PATH = GO_SHADOW_DIR / "README.md"
GO_REPORT_PATH = ROOT / "Prism_Go_模組逐步重構計劃報告.md"
GO_MAIN_PATH = GO_SHADOW_DIR / "main.go"
VOLATILE_KEYS = {"created_at", "updated_at"}


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_db(src, dst):
    shutil.copyfile(src, dst)
    return str(dst)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _request_json(base, path, *, data=None, method="GET"):
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(base.rstrip("/") + path, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = response.read().decode("utf-8")
            return response.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        return exc.code, json.loads(payload) if payload else None


def _start_go(db_path, data_dir, tmp_path, *, enable_notes_write=False):
    go_bin = shutil.which("go")
    if not go_bin:
        pytest.skip("Go CLI is not installed; contract/static checks still run.")

    port = _free_port()
    exe_path = build_go_shadow_exe(go_bin, tmp_path)
    command = [
        str(exe_path),
        "--db",
        db_path,
        "--addr",
        f"127.0.0.1:{port}",
        "--data-dir",
        str(data_dir),
    ]
    env = os.environ.copy()
    if enable_notes_write:
        command.append("--enable-notes-write")
        env["PRISM_GO_ENABLE_NOTES_WRITE"] = "1"

    proc = subprocess.Popen(
        command,
        env=env,
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
    pytest.fail(f"Go notes candidate did not start:\n{output}")


def _flask_client(db_path, data_dir):
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
    app.root_path = str(data_dir)
    ctx = app.app_context()
    ctx.push()
    return app.test_client(), ctx


def _normalize(value):
    if isinstance(value, dict):
        return {
            key: "<timestamp>" if key in VOLATILE_KEYS and item is not None else _normalize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value


def _seed_t011_read_fixture(db_path, data_dir):
    attachments_dir = Path(data_dir) / "docs" / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES ('t011-alpha', 'A', 901, 0)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES ('t011-beta', 'B', 902, 0)"
        )
        alpha = conn.execute("SELECT id FROM Categories WHERE name = 't011-alpha'").fetchone()[0]
        beta = conn.execute("SELECT id FROM Categories WHERE name = 't011-beta'").fetchone()[0]
        for tag in ("t011-tagaa", "t011-tagbb"):
            conn.execute("INSERT OR IGNORE INTO Tags (name) VALUES (?)", (tag,))
        tagaa = conn.execute("SELECT id FROM Tags WHERE name = 't011-tagaa'").fetchone()[0]
        tagbb = conn.execute("SELECT id FROM Tags WHERE name = 't011-tagbb'").fetchone()[0]

        def note(title, content, remarks, category_id, sort_order):
            cursor = conn.execute(
                """
                INSERT INTO Notes (title, content, remarks, category_id, sort_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, content, remarks, category_id, sort_order),
            )
            return cursor.lastrowid

        fts = note("T011 FTS", "ftsa appears before ftsb", "", alpha, 10)
        remarks = note("T011 Remarks", "ordinary body", "remarkaa appears before remarkbb", beta, 20)
        tags = note("T011 Tags", "ordinary body", "", alpha, 30)
        metadata = note("T011 Metadata", "ordinary body", "", alpha, 40)
        body = note("T011 Body", "ordinary body", "", beta, 50)
        pager = note("T011 Pager", "ordinary body", "", alpha, 60)

        conn.executemany(
            "INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)",
            [(tags, tagaa), (tags, tagbb), (pager, tagaa)],
        )
        conn.execute(
            """
            INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes)
            VALUES (?, 'docs/attachments/t011-meta.md', 'md', 'metaaa appears before metabb', 12)
            """,
            (metadata,),
        )
        body_path = attachments_dir / "t011-body.md"
        body_content = "bodyaa appears before bodybb"
        body_path.write_text(body_content, encoding="utf-8")
        conn.execute(
            """
            INSERT INTO Note_Attachments (note_id, file_path, file_type, title, size_bytes)
            VALUES (?, 'docs/attachments/t011-body.md', 'md', 'body fixture', ?)
            """,
            (body, body_path.stat().st_size),
        )
        conn.commit()
        return {
            "alpha": alpha,
            "beta": beta,
            "tagaa": tagaa,
            "tagbb": tagbb,
            "notes": {
                "fts": fts,
                "remarks": remarks,
                "tags": tags,
                "metadata": metadata,
                "body": body,
                "pager": pager,
            },
        }
    finally:
        conn.close()


def _notes_write_snapshot(db_path):
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


def _scalar(db_path, query, args=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(query, args).fetchone()[0]
    finally:
        conn.close()


def _ensure_category(db_path, name):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES (?, 'T', 910, 0)",
            (name,),
        )
        category_id = conn.execute("SELECT id FROM Categories WHERE name = ?", (name,)).fetchone()[0]
        conn.commit()
        return category_id
    finally:
        conn.close()


def test_t011_t012_contract_files_record_completed_local_candidate_boundaries():
    read_contract = _load_json(READ_CONTRACT_PATH)
    write_contract = _load_json(WRITE_CONTRACT_PATH)
    main_go = GO_MAIN_PATH.read_text(encoding="utf-8")

    assert read_contract["task_id"] == "T011"
    assert read_contract["status"] == "completed"
    assert read_contract["production_runtime_owner"] == "python"
    assert read_contract["runtime_boundary"]["pi_deploy"] is False
    assert read_contract["parity_scope"] == [
        "empty/default list query",
        "tokenized FTS title/content search",
        "remarks token search",
        "tag token search",
        "attachment metadata token search",
        "text attachment body search",
        "category/tag filters",
        "pagination",
    ]

    assert write_contract["task_id"] == "T012"
    assert write_contract["status"] == "completed_local_candidate"
    assert write_contract["enable_flag"] == "--enable-notes-write"
    assert write_contract["covered_routes"] == ["POST /api/notes", "PUT /api/notes/<id>"]
    assert write_contract["not_covered_here"] == [
        "DELETE /api/notes/<id>",
        "notes actions",
        "notes batch actions",
        "notes history restore/delete",
        "media cleanup side effects",
    ]
    assert "sanitizeFTSQuery" in main_go
    assert "foreign_keys(1)" in main_go
    assert "Notes write route is disabled" in main_go


def test_t011_go_notes_read_search_matches_python_response(temp_db, tmp_path):
    py_db = _copy_db(temp_db, tmp_path / "python_t011_notes_read.db")
    go_db = _copy_db(temp_db, tmp_path / "go_t011_notes_read.db")
    py_data = tmp_path / "python_data"
    go_data = tmp_path / "go_data"
    py_ids = _seed_t011_read_fixture(py_db, py_data)
    go_ids = _seed_t011_read_fixture(go_db, go_data)
    assert py_ids == go_ids

    client, ctx = _flask_client(py_db, py_data)
    proc, base = _start_go(go_db, go_data, tmp_path)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only"
        assert health_json["runtime"]["sqlite_query_only"] is True

        cases = [
            "/api/notes?page=1&per_page=2&sort=custom",
            "/api/notes?q=ftsa%20ftsb&page=1&per_page=20",
            "/api/notes?q=remarkaa%20remarkbb&page=1&per_page=20",
            "/api/notes?q=t011-tagaa%20t011-tagbb&page=1&per_page=20",
            "/api/notes?q=metaaa%20metabb&page=1&per_page=20",
            "/api/notes?q=bodyaa%20bodybb&page=1&per_page=20",
            f"/api/notes?page=1&per_page=20&category_id={py_ids['alpha']}&tags={py_ids['tagaa']},{py_ids['tagbb']}&tag_mode=AND&sort=custom",
            f"/api/notes?page=1&per_page=20&category_id={py_ids['alpha']}&tags={py_ids['tagbb']}&tag_mode=OR&sort=custom",
            "/api/notes?type=not-a-real-category&page=1&per_page=100&sort=custom",
        ]
        for path in cases:
            py_response = client.get(path)
            go_status, go_json = _request_json(base, path)
            assert go_status == py_response.status_code, path
            assert _normalize(go_json) == _normalize(py_response.get_json()), path
    finally:
        ctx.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_t012_go_notes_create_update_matches_python_db_state_and_rollback(temp_db, tmp_path):
    py_db = _copy_db(temp_db, tmp_path / "python_t012_notes_write.db")
    go_db = _copy_db(temp_db, tmp_path / "go_t012_notes_write.db")
    py_beta = _ensure_category(py_db, "t012-beta")
    go_beta = _ensure_category(go_db, "t012-beta")
    assert py_beta == go_beta
    py_data = tmp_path / "python_data"
    go_data = tmp_path / "go_data"
    client, ctx = _flask_client(py_db, py_data)
    proc, base = _start_go(go_db, go_data, tmp_path, enable_notes_write=True)
    try:
        health_status, health_json = _request_json(base, "/healthz")
        assert health_status == 200
        assert health_json["runtime"]["api_surface"] == "get-read-only+local-notes-write"
        assert health_json["runtime"]["sqlite_query_only"] is False

        create_payload = {
            "title": "",
            "content": "t012 create ftscreatealpha content",
            "remarks": "created remarks",
            "tags": ["t012-created-tag"],
            "urls": ["https://t012.example/create"],
            "is_pinned": True,
            "prompt_params": {"sampler": "fixture"},
        }
        py_response = client.post("/api/notes", json=create_payload)
        go_status, go_json = _request_json(base, "/api/notes", data=create_payload, method="POST")
        assert go_status == py_response.status_code == 201
        assert go_json == py_response.get_json()
        note_id = go_json["data"]["note_id"]

        default_category = _scalar(py_db, "SELECT id FROM Categories WHERE is_default = 1 LIMIT 1")
        assert _scalar(go_db, "SELECT category_id FROM Notes WHERE id = ?", (note_id,)) == default_category
        assert _scalar(go_db, "SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", ("ftscreatealpha",)) == 1

        py_missing = client.post("/api/notes", json={"title": "missing content"})
        go_missing_status, go_missing_json = _request_json(
            base,
            "/api/notes",
            data={"title": "missing content"},
            method="POST",
        )
        assert go_missing_status == py_missing.status_code == 400
        assert go_missing_json == py_missing.get_json()

        update_payload = {
            "title": "T012 Updated",
            "content": "t012 update ftsupdatealpha content",
            "category_id": py_beta,
            "remarks": "updated remarks",
            "tags": ["t012-updated-tag"],
            "urls": ["https://t012.example/update"],
            "is_archived": True,
            "cover_position": "center",
            "editor_layout": "dual",
            "prompt_params": {"steps": 12},
        }
        py_response = client.put(f"/api/notes/{note_id}", json=update_payload)
        go_status, go_json = _request_json(base, f"/api/notes/{note_id}", data=update_payload, method="PUT")
        assert go_status == py_response.status_code == 200
        assert go_json == py_response.get_json()

        assert _scalar(go_db, "SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", ("ftsupdatealpha",)) == 1
        assert _scalar(go_db, "SELECT COUNT(*) FROM Notes_FTS WHERE Notes_FTS MATCH ?", ("ftscreatealpha",)) == 0
        assert _notes_write_snapshot(go_db) == _notes_write_snapshot(py_db)

        py_bad = client.put(f"/api/notes/{note_id}", json={"title": "broken"})
        go_bad_status, go_bad_json = _request_json(
            base,
            f"/api/notes/{note_id}",
            data={"title": "broken"},
            method="PUT",
        )
        assert go_bad_status == py_bad.status_code == 400
        assert go_bad_json == py_bad.get_json()

        before_py = _notes_write_snapshot(py_db)
        before_go = _notes_write_snapshot(go_db)
        invalid_payload = {
            "title": "Bad FK",
            "content": "bad fk should roll back",
            "category_id": 999999,
            "tags": ["should-not-stick"],
            "urls": ["https://rollback.example"],
        }
        py_invalid = client.put(f"/api/notes/{note_id}", json=invalid_payload)
        go_invalid_status, _ = _request_json(base, f"/api/notes/{note_id}", data=invalid_payload, method="PUT")
        assert go_invalid_status == py_invalid.status_code == 500
        assert _notes_write_snapshot(py_db) == before_py
        assert _notes_write_snapshot(go_db) == before_go
    finally:
        ctx.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_t011_t012_docs_mark_done_and_keep_runtime_boundaries():
    todo = TODO_PATH.read_text(encoding="utf-8")
    architecture = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    readme = GO_README_PATH.read_text(encoding="utf-8")
    go_report = GO_REPORT_PATH.read_text(encoding="utf-8")

    for task_id in ("T011", "T012"):
        row = next(line for line in todo.splitlines() if line.startswith(f"| {task_id} "))
        assert row.endswith("| Done |")

    assert "go-primary-notes-read-search-parity.json" in todo
    assert "go-primary-notes-create-update-parity.json" in todo
    assert "T011/T012 Go notes read/search/create/update parity gate is complete" in architecture
    assert "Go T011/T012" in schema
    assert "Notes Read/Search/Create/Update" in readme
    assert "T011/T012" in go_report
    assert "does not promote live/default notes write ownership" in architecture
