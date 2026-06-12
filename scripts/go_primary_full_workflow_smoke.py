#!/usr/bin/env python3
"""HTTP-only Go primary full workflow smoke.

This script intentionally imports only Python standard-library modules and never
imports Prism Flask code. Python is the smoke harness; the runtime under test is
the already-built Go binary listening at --base-url.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
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


def request_bytes(base_url, path, method="GET", data=None, headers=None, timeout=20):
    body = data
    request_headers = dict(headers or {})
    if isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def request_json(base_url, path, method="GET", data=None, timeout=20):
    status, headers, body = request_bytes(base_url, path, method=method, data=data, timeout=timeout)
    if body:
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SmokeError(f"{method} {path} returned non-JSON HTTP {status}: {body[:200]!r}") from exc
    else:
        payload = None
    return status, payload, headers


def request_multipart(base_url, path, files, fields=None, timeout=30):
    boundary = f"----prism-go-primary-smoke-{time.time_ns()}"
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
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=timeout,
    )
    parsed = json.loads(payload.decode("utf-8")) if payload else None
    return status, parsed, headers


def assert_status(step, status, expected, payload=None):
    if status != expected:
        preview = payload
        if isinstance(preview, bytes):
            preview = preview[:200]
        raise SmokeError(f"{step} expected HTTP {expected}, got {status}: {preview!r}")


def filename_from_upload_url(upload_url):
    return upload_url.rstrip("/").split("/")[-1]


def search_matches(base_url, token):
    status, payload, _ = request_json(base_url, f"/api/notes?q={urllib.parse.quote(token)}&per_page=50")
    assert_status(f"search {token}", status, 200, payload)
    return payload.get("data") or []


def run_smoke(base_url, label):
    stamp = str(time.time_ns())
    workflow_token = f"{label}-workflow-{stamp}"
    import_token = f"{label}-imported-{stamp}"
    evidence = {
        "status": "running",
        "label": label,
        "base_url": base_url,
        "workflow": [
            "healthz",
            "create note",
            "upload image",
            "serve uploaded image",
            "update note with upload reference",
            "search updated note",
            "export JSON",
            "import JSON",
            "delete workflow note",
            "upload orphan image",
            "scan/delete orphan image",
            "download backup",
            "check migration status",
        ],
    }

    status, health, _ = request_json(base_url, "/healthz")
    assert_status("healthz", status, 200, health)
    api_surface = health.get("runtime", {}).get("api_surface", "")
    for marker in (
        "local-notes-write",
        "local-upload-write",
        "local-thumbnail-write",
        "local-upload-url-write",
        "local-upload-delete",
        "local-media-cleanup",
        "local-import-export",
        "local-server-system",
    ):
        if marker not in api_surface:
            raise SmokeError(f"/healthz api_surface missing {marker}: {api_surface}")
    evidence["healthz"] = {
        "api_surface": api_surface,
        "auth": health.get("runtime", {}).get("security", {}).get("auth"),
        "sqlite_query_only": health.get("runtime", {}).get("sqlite_query_only"),
    }

    create_payload = {
        "title": f"{label} workflow",
        "content": f"{workflow_token} initial content",
        "tags": [f"{label}-go-primary"],
        "urls": [f"https://example.test/{label}/{stamp}"],
        "remarks": "go primary package smoke",
    }
    status, created, _ = request_json(base_url, "/api/notes", method="POST", data=create_payload)
    assert_status("create note", status, 201, created)
    note_id = created["data"]["note_id"]

    status, upload, _ = request_multipart(
        base_url,
        "/api/upload",
        [("file", f"{label}-workflow.png", PNG_1X1, "image/png")],
        {"thumbnail_only": "false"},
    )
    assert_status("upload image", status, 200, upload)
    image_url = upload["data"]["url"]
    status, headers, image_body = request_bytes(base_url, image_url)
    assert_status("serve uploaded image", status, 200, image_body)
    if image_body != PNG_1X1:
        raise SmokeError("served uploaded image bytes differ from uploaded PNG")

    update_payload = {
        "title": f"{label} workflow updated",
        "content": f"{workflow_token} updated image {image_url}",
        "cover_image": image_url,
        "tags": [f"{label}-go-primary-updated"],
        "urls": [f"https://example.test/{label}/{stamp}/updated"],
    }
    status, updated, _ = request_json(base_url, f"/api/notes/{note_id}", method="PUT", data=update_payload)
    assert_status("update note", status, 200, updated)
    if not any(item.get("id") == note_id for item in search_matches(base_url, workflow_token)):
        raise SmokeError("updated note was not searchable by workflow token")

    status, _, export_body = request_bytes(base_url, "/api/export/json")
    assert_status("export JSON", status, 200, export_body)
    exported = json.loads(export_body.decode("utf-8"))
    if not any(note.get("id") == note_id for note in exported.get("notes", [])):
        raise SmokeError("export JSON did not contain the workflow note")

    import_payload = {
        "mode": "duplicate",
        "data": {
            "notes": [
                {
                    "id": 93941,
                    "title": f"{label} imported",
                    "content": import_token,
                    "category": "smoke",
                    "tags": [f"{label}-imported"],
                    "urls": [f"https://example.test/{label}/{stamp}/imported"],
                }
            ],
            "tags": [{"name": f"{label}-imported"}],
        },
    }
    status, imported, _ = request_json(base_url, "/api/import/json", method="POST", data=import_payload)
    assert_status("import JSON", status, 200, imported)
    if imported["data"]["imported"] != 1:
        raise SmokeError(f"import JSON imported unexpected count: {imported!r}")
    if not search_matches(base_url, import_token):
        raise SmokeError("imported note was not searchable by import token")

    status, deleted, _ = request_json(base_url, f"/api/notes/{note_id}", method="DELETE")
    assert_status("delete workflow note", status, 200, deleted)
    if any(item.get("id") == note_id for item in search_matches(base_url, workflow_token)):
        raise SmokeError("deleted workflow note remained searchable")

    status, orphan_upload, _ = request_multipart(
        base_url,
        "/api/upload",
        [("file", f"{label}-orphan.png", PNG_1X1, "image/png")],
        {"thumbnail_only": "false"},
    )
    assert_status("upload orphan image", status, 200, orphan_upload)
    orphan_url = orphan_upload["data"]["url"]
    orphan_filename = filename_from_upload_url(orphan_url)
    status, orphans, _ = request_json(base_url, "/api/cleanup/orphan-images")
    assert_status("scan orphan images", status, 200, orphans)
    orphan_names = {item["filename"] for item in orphans["data"]["orphan_images"]}
    if orphan_filename not in orphan_names:
        raise SmokeError(f"uploaded orphan {orphan_filename} was not reported in orphan scan")
    status, cleanup, _ = request_json(
        base_url,
        "/api/cleanup/orphan-images",
        method="DELETE",
        data={"filenames": [orphan_filename]},
    )
    assert_status("delete orphan image", status, 200, cleanup)
    if orphan_filename not in cleanup["data"]["deleted"]:
        raise SmokeError(f"uploaded orphan {orphan_filename} was not deleted: {cleanup!r}")

    status, headers, backup_body = request_bytes(base_url, "/api/server/backup/download", timeout=60)
    assert_status("download backup", status, 200, backup_body)
    if not backup_body.startswith(b"SQLite format 3"):
        raise SmokeError("backup download is not a SQLite database")

    status, migration, _ = request_json(base_url, "/api/system/migration-status")
    assert_status("migration status", status, 200, migration)
    migration_data = migration["data"]
    if migration_data["current_version"] != migration_data["latest_version"] or migration_data["pending"] != []:
        raise SmokeError(f"migration status is not clean: {migration_data!r}")

    evidence.update(
        {
            "status": "passed",
            "note_id": note_id,
            "workflow_token": workflow_token,
            "import_token": import_token,
            "upload_url": image_url,
            "orphan_filename": orphan_filename,
            "backup": {
                "content_type": headers.get("Content-Type"),
                "starts_with_sqlite_header": True,
            },
            "migration": migration_data,
        }
    )
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--label", default="go-primary-smoke")
    parser.add_argument("--evidence-out", required=True)
    args = parser.parse_args()

    evidence = run_smoke(args.base_url, args.label)
    out_path = Path(args.evidence_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Go primary full workflow smoke passed. Evidence: {out_path}")


if __name__ == "__main__":
    main()
