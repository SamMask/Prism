#!/usr/bin/env python3
"""HTTP-only live smoke for the retained Python runtime.

The script talks to the deployed Prism HTTP surface only. It does not import
Flask app code, so it can verify a Caddy/systemd rollback from Go primary back
to the Python service.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


class SmokeError(RuntimeError):
    pass


def request_bytes(base_url, path, method="GET", data=None, headers=None, timeout=20, context=None):
    body = data
    request_headers = dict(headers or {})
    if isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    if method in {"POST", "PUT", "DELETE", "PATCH"}:
        request_headers.setdefault("Origin", base_url.rstrip("/"))
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def request_json(base_url, path, method="GET", data=None, timeout=20, context=None):
    status, headers, body = request_bytes(base_url, path, method=method, data=data, timeout=timeout, context=context)
    if body:
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SmokeError(f"{method} {path} returned non-JSON HTTP {status}: {body[:200]!r}") from exc
    else:
        payload = None
    return status, payload, headers


def request_multipart(base_url, path, files, fields=None, timeout=30, context=None):
    boundary = f"----prism-python-live-smoke-{time.time_ns()}"
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
    status, headers, payload = request_bytes(
        base_url,
        path,
        method="POST",
        data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Origin": base_url.rstrip("/")},
        timeout=timeout,
        context=context,
    )
    parsed = json.loads(payload.decode("utf-8")) if payload else None
    return status, parsed, headers


def assert_status(step, status, expected, payload=None):
    if status != expected:
        raise SmokeError(f"{step} expected HTTP {expected}, got {status}: {payload!r}")


def search_matches(base_url, token, context=None):
    status, payload, _ = request_json(base_url, f"/api/notes?q={urllib.parse.quote(token)}&per_page=50", context=context)
    assert_status(f"search {token}", status, 200, payload)
    return payload.get("data") or []


def filename_from_content_disposition(value):
    if not value:
        return None
    for part in value.split(";"):
        part = part.strip()
        if part.lower().startswith("filename="):
            return part.split("=", 1)[1].strip().strip('"')
    return None


def run_smoke(base_url, label, expected_header=None, forbidden_header=None, insecure=False):
    context = ssl._create_unverified_context() if insecure else None
    stamp = str(time.time_ns())
    token = f"{label}-python-rollback-{stamp}"
    evidence = {
        "status": "running",
        "label": label,
        "base_url": base_url,
        "workflow": [
            "system stats",
            "server version",
            "create note",
            "upload image",
            "serve uploaded image",
            "update note",
            "search note",
            "export JSON",
            "download backup",
            "delete smoke backup",
            "migration status",
            "delete note",
        ],
    }

    status, stats, headers = request_json(base_url, "/api/system/stats", context=context)
    assert_status("system stats", status, 200, stats)
    if expected_header:
        name, expected = expected_header.split("=", 1)
        actual = headers.get(name) or headers.get(name.lower()) or headers.get(name.title())
        if actual != expected:
            raise SmokeError(f"expected response header {name}={expected}, got {actual!r}")
    if forbidden_header:
        lowered = {key.lower() for key in headers}
        if forbidden_header.lower() in lowered:
            raise SmokeError(f"forbidden response header present: {forbidden_header}")

    status, version, _ = request_json(base_url, "/api/server/version", context=context)
    assert_status("server version", status, 200, version)

    create_payload = {
        "title": f"{label} python rollback smoke",
        "content": f"{token} initial content",
        "tags": [f"{label}-python-rollback"],
        "urls": [f"https://example.test/{label}/{stamp}"],
        "remarks": "python rollback smoke",
    }
    status, created, _ = request_json(base_url, "/api/notes", method="POST", data=create_payload, context=context)
    assert_status("create note", status, 201, created)
    note_id = created["data"]["note_id"]

    status, upload, _ = request_multipart(
        base_url,
        "/api/upload",
        [("file", f"{label}-python-rollback.png", PNG_1X1, "image/png")],
        {"thumbnail_only": "false"},
        context=context,
    )
    assert_status("upload image", status, 200, upload)
    image_url = upload["data"]["url"]

    status, _, image_body = request_bytes(base_url, image_url, context=context)
    assert_status("serve uploaded image", status, 200, image_body)
    if image_body != PNG_1X1:
        raise SmokeError("served uploaded image bytes differ from uploaded PNG")

    update_payload = {
        "title": f"{label} python rollback smoke updated",
        "content": f"{token} updated image {image_url}",
        "cover_image": image_url,
        "tags": [f"{label}-python-rollback-updated"],
        "urls": [f"https://example.test/{label}/{stamp}/updated"],
    }
    status, updated, _ = request_json(base_url, f"/api/notes/{note_id}", method="PUT", data=update_payload, context=context)
    assert_status("update note", status, 200, updated)
    if not any(item.get("id") == note_id for item in search_matches(base_url, token, context=context)):
        raise SmokeError("updated note was not searchable by workflow token")

    status, _, export_body = request_bytes(base_url, "/api/export/json", context=context)
    assert_status("export JSON", status, 200, export_body)
    exported = json.loads(export_body.decode("utf-8"))
    if not any(note.get("id") == note_id for note in exported.get("notes", [])):
        raise SmokeError("export JSON did not contain the workflow note")

    status, backup_headers, backup_body = request_bytes(base_url, "/api/server/backup/download", timeout=60, context=context)
    assert_status("download backup", status, 200, backup_body)
    if not backup_body.startswith(b"SQLite format 3"):
        raise SmokeError("backup download is not a SQLite database")
    backup_filename = filename_from_content_disposition(backup_headers.get("Content-Disposition"))
    backup_deleted = False
    if backup_filename:
        status, backup_delete, _ = request_json(
            base_url,
            f"/api/server/backup/{urllib.parse.quote(backup_filename)}",
            method="DELETE",
            context=context,
        )
        assert_status("delete smoke backup", status, 200, backup_delete)
        backup_deleted = True

    status, migration, _ = request_json(base_url, "/api/system/migration-status", context=context)
    assert_status("migration status", status, 200, migration)
    migration_data = migration["data"]
    if migration_data["current_version"] != migration_data["latest_version"] or migration_data["pending"] != []:
        raise SmokeError(f"migration status is not clean: {migration_data!r}")

    status, deleted, _ = request_json(base_url, f"/api/notes/{note_id}", method="DELETE", context=context)
    assert_status("delete workflow note", status, 200, deleted)
    if any(item.get("id") == note_id for item in search_matches(base_url, token, context=context)):
        raise SmokeError("deleted workflow note remained searchable")

    evidence.update(
        {
            "status": "passed",
            "note_id": note_id,
            "workflow_token": token,
            "upload_url": image_url,
            "backup": {
                "content_type": backup_headers.get("Content-Type"),
                "filename": backup_filename,
                "deleted_after_download": backup_deleted,
                "starts_with_sqlite_header": True,
            },
            "migration": migration_data,
            "server_version": version.get("data") if isinstance(version, dict) else version,
        }
    )
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--label", default="python-live-smoke")
    parser.add_argument("--evidence-out", required=True)
    parser.add_argument("--expected-header")
    parser.add_argument("--forbidden-header")
    parser.add_argument("--insecure", action="store_true", help="skip TLS verification for Caddy internal certificates")
    args = parser.parse_args()

    evidence = run_smoke(
        args.base_url,
        args.label,
        expected_header=args.expected_header,
        forbidden_header=args.forbidden_header,
        insecure=args.insecure,
    )
    out_path = Path(args.evidence_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Python live workflow smoke passed. Evidence: {out_path}")


if __name__ == "__main__":
    main()
