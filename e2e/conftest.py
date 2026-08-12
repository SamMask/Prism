"""Hermetic Playwright fixtures for the current Go primary artifact."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest
from playwright.sync_api import Page


ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_runtime(base_url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Go runtime exited early with code {process.returncode}")
        try:
            with urlopen(f"{base_url}/healthz", timeout=1) as response:
                if response.status == 200:
                    return
        except URLError:
            time.sleep(0.1)
    raise RuntimeError("Timed out waiting for isolated Go runtime")


def _seed_note(base_url: str) -> None:
    payload = json.dumps({
        "title": "E2E Search Anchor",
        "content": "Current isolated Go primary browser smoke fixture.",
    }).encode("utf-8")
    request = Request(
        f"{base_url}/api/notes",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        if response.status != 201:
            raise RuntimeError(f"Unable to seed E2E note: HTTP {response.status}")
    for index in range(25):
        extra_payload = json.dumps({
            "title": f"E2E Pagination Fixture {index + 1:02d}",
            "content": "Isolated fixture used to keep the first Home page partial.",
        }).encode("utf-8")
        extra_request = Request(
            f"{base_url}/api/notes",
            data=extra_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(extra_request, timeout=5) as response:
            if response.status != 201:
                raise RuntimeError(f"Unable to seed pagination note: HTTP {response.status}")


@pytest.fixture(scope="session")
def runtime_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "build_go_runtime.ps1"),
        ],
        cwd=ROOT,
        check=True,
    )

    artifact = ROOT / "build" / "go-runtime" / "prism-go-runtime.exe"
    data_dir = tmp_path_factory.mktemp("prism-go-e2e")
    config_dir = data_dir / "config"
    config_dir.mkdir()
    for config_name in ("prompt_options.json", "wizard_options.json"):
        shutil.copy2(ROOT / "static" / "config" / config_name, config_dir / config_name)

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    log_path = data_dir / "runtime.log"
    command = [
        str(artifact),
        "--db", str(data_dir / "prism_e2e_test.db"),
        "--data-dir", str(data_dir),
        "--addr", f"127.0.0.1:{port}",
        "--enable-tag-write",
        "--enable-category-write",
        "--enable-notes-write",
        "--enable-attachment-text-read",
        "--enable-attachment-raw-read",
        "--enable-attachment-write",
        "--enable-upload-write",
        "--enable-thumbnail-write",
        "--enable-upload-url-write",
        "--enable-upload-delete",
        "--enable-media-cleanup",
        "--enable-import-export",
        "--enable-server-system",
    ]
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with log_path.open("wb") as runtime_log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=runtime_log,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        try:
            _wait_for_runtime(base_url, process)
            _seed_note(base_url)
            yield base_url
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.fixture(scope="session")
def browser_context_args():
    return {
        "viewport": {"width": 1280, "height": 800},
        "ignore_https_errors": True,
        "locale": "en-US",
    }


@pytest.fixture
def app_page(page: Page, runtime_url: str):
    page.goto(runtime_url)
    page.locator('[data-testid="app-container"]').wait_for(state="visible", timeout=15_000)
    yield page
