import hashlib
import json
import os
import sqlite3
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW_DIR = ROOT / "go-shadow"
DEFAULT_VOLATILE_KEYS = ("created_at", "updated_at")


@dataclass(frozen=True)
class RouteParityFixture:
    id: str
    method: str
    path: str
    json_body: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    db_tables: tuple[str, ...] = ()
    file_roots: tuple[str, ...] = ()
    normalize_json_keys: tuple[str, ...] = DEFAULT_VOLATILE_KEYS


@dataclass(frozen=True)
class RouteObservation:
    target: str
    status_code: int
    json_body: Any
    db_before: dict[str, Any]
    db_after: dict[str, Any]
    files_before: dict[str, Any]
    files_after: dict[str, Any]


def observe_flask_fixture(
    target: str,
    client: Any,
    fixture: RouteParityFixture,
    db_path: str | None = None,
    data_dir: str | None = None,
) -> RouteObservation:
    db_before = snapshot_sqlite(db_path, fixture.db_tables)
    files_before = snapshot_files(data_dir, fixture.file_roots)
    response = client.open(
        fixture.path,
        method=fixture.method,
        json=fixture.json_body,
        headers=fixture.headers,
    )
    json_body = response.get_json(silent=True)
    return RouteObservation(
        target=target,
        status_code=response.status_code,
        json_body=_normalize_json(json_body, fixture.normalize_json_keys),
        db_before=db_before,
        db_after=snapshot_sqlite(db_path, fixture.db_tables),
        files_before=files_before,
        files_after=snapshot_files(data_dir, fixture.file_roots),
    )


def observe_http_fixture(
    target: str,
    base_url: str,
    fixture: RouteParityFixture,
    db_path: str | None = None,
    data_dir: str | None = None,
) -> RouteObservation:
    db_before = snapshot_sqlite(db_path, fixture.db_tables)
    files_before = snapshot_files(data_dir, fixture.file_roots)
    body = None
    headers = dict(fixture.headers)
    if fixture.json_body is not None:
        body = json.dumps(fixture.json_body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(
        base_url.rstrip("/") + fixture.path,
        data=body,
        headers=headers,
        method=fixture.method,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status_code = response.status
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        payload = exc.read().decode("utf-8")

    try:
        json_body = json.loads(payload) if payload else None
    except json.JSONDecodeError:
        json_body = payload

    return RouteObservation(
        target=target,
        status_code=status_code,
        json_body=_normalize_json(json_body, fixture.normalize_json_keys),
        db_before=db_before,
        db_after=snapshot_sqlite(db_path, fixture.db_tables),
        files_before=files_before,
        files_after=snapshot_files(data_dir, fixture.file_roots),
    )


def run_python_go_fixture(
    client: Any,
    go_base_url: str,
    fixture: RouteParityFixture,
    python_db_path: str | None = None,
    go_db_path: str | None = None,
    python_data_dir: str | None = None,
    go_data_dir: str | None = None,
) -> dict[str, Any]:
    python = observe_flask_fixture(
        "python",
        client,
        fixture,
        db_path=python_db_path,
        data_dir=python_data_dir,
    )
    go = observe_http_fixture(
        "go",
        go_base_url,
        fixture,
        db_path=go_db_path,
        data_dir=go_data_dir,
    )
    return compare_observations(python, go)


def build_go_shadow_exe(go_bin: str, tmp_path: Path) -> Path:
    exe_path = Path(tmp_path) / ("prism-go-shadow.exe" if os.name == "nt" else "prism-go-shadow")
    subprocess.run(
        [go_bin, "build", "-o", str(exe_path), "."],
        cwd=GO_SHADOW_DIR,
        check=True,
    )
    return exe_path


def compare_observations(python: RouteObservation, go: RouteObservation) -> dict[str, Any]:
    diffs: dict[str, Any] = {}
    if python.status_code != go.status_code:
        diffs["status_code"] = {"python": python.status_code, "go": go.status_code}
    if python.json_body != go.json_body:
        diffs["json_body"] = {"python": python.json_body, "go": go.json_body}

    python_db_delta = _state_delta(python.db_before, python.db_after)
    go_db_delta = _state_delta(go.db_before, go.db_after)
    if python_db_delta != go_db_delta:
        diffs["db_mutation"] = {"python": python_db_delta, "go": go_db_delta}

    python_file_delta = _state_delta(python.files_before, python.files_after)
    go_file_delta = _state_delta(go.files_before, go.files_after)
    if python_file_delta != go_file_delta:
        diffs["file_mutation"] = {"python": python_file_delta, "go": go_file_delta}

    return {
        "ok": not diffs,
        "diffs": diffs,
        "python": _observation_payload(python),
        "go": _observation_payload(go),
    }


def snapshot_sqlite(db_path: str | None, tables: tuple[str, ...]) -> dict[str, Any]:
    if not db_path or not tables:
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        snapshot: dict[str, Any] = {}
        for table in tables:
            columns = [
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            if not columns:
                snapshot[table] = []
                continue
            order_column = "id" if "id" in columns else columns[0]
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY {order_column}").fetchall()
            snapshot[table] = [dict(row) for row in rows]
        return snapshot
    finally:
        conn.close()


def snapshot_files(data_dir: str | None, roots: tuple[str, ...]) -> dict[str, Any]:
    if not data_dir or not roots:
        return {}
    base = Path(data_dir)
    snapshot: dict[str, Any] = {}
    for root in roots:
        root_path = base / root
        if not root_path.exists():
            snapshot[root] = {}
            continue
        files: dict[str, Any] = {}
        for path in sorted(p for p in root_path.rglob("*") if p.is_file()):
            relative = path.relative_to(base).as_posix()
            files[relative] = {
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        snapshot[root] = files
    return snapshot


def _normalize_json(value: Any, volatile_keys: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        return {
            key: "<volatile>" if key in volatile_keys and item is not None else _normalize_json(item, volatile_keys)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_json(item, volatile_keys) for item in value]
    return value


def _state_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    if before == after:
        return {}
    return {"before": before, "after": after}


def _observation_payload(observation: RouteObservation) -> dict[str, Any]:
    return {
        "target": observation.target,
        "status_code": observation.status_code,
        "json_body": observation.json_body,
        "db_delta": _state_delta(observation.db_before, observation.db_after),
        "file_delta": _state_delta(observation.files_before, observation.files_after),
    }
