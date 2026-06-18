import os
import socket
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW = ROOT / "go-shadow"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
BUILD_SCRIPT = ROOT / "scripts" / "build_desktop_shell.ps1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_desktop_shell_phase1_3_source_boundaries():
    windows_source = _read(GO_SHADOW / "desktop_shell_windows.go")
    main_source = _read(GO_SHADOW / "main.go")
    go_mod = _read(GO_SHADOW / "go.mod")

    for required in [
        "github.com/jchv/go-webview2",
        "webview2.NewWithOptions",
        "Shell_NotifyIconW",
        "CreateMutexW",
        "FindWindowW",
        "SetForegroundWindow",
        "desktop-shell.log",
        "Shutdown(ctx)",
        "waitForDesktopHealth",
    ]:
        assert required in windows_source

    for required in [
        "desktop-shell",
        "desktop-webview-only",
        "desktop-shell-smoke",
        "desktop-self-test",
        "prism_desktop_dev.db",
        "go run . --desktop-shell",
    ]:
        assert required in main_source or required in _read(GO_SHADOW / "README.md")

    assert "github.com/jchv/go-webview2" in go_mod
    assert "webview/webview_go" not in go_mod


def test_desktop_shell_phase1_3_docs_are_closed_without_package_scope():
    todo = _read(TODO_PATH)
    handoff = _read(HANDOFF_PATH)
    contracts = _read(CONTRACTS_PATH)

    assert "Desktop Shell Phase 0-6、post-package follow-up 與 manual acceptance 已完成" in todo
    assert "Desktop Shell 目前沒有 active construction item" in todo
    assert "installer / updater 只有在明確需要" in handoff
    assert "Desktop Shell / Windows portable baseline 已完成並歸檔" in handoff
    assert "desktop-portable-release-handoff-20260618.md" in handoff
    assert "CONTRACT-DESKTOP-SHELL-RUNTIME-HOST" in contracts
    assert "CONTRACT-DESKTOP-SHELL-UX-HARDENING" in contracts


def test_desktop_shell_build_script_keeps_debug_and_gui_targets():
    script = _read(BUILD_SCRIPT)

    assert "PrismDesktop-debug.exe" in script
    assert "Prism.exe" in script
    assert "-H=windowsgui" in script
    assert "installer" not in script.lower()
    assert "msi" not in script.lower()
    assert "nsis" not in script.lower()


def test_desktop_shell_go_build_and_runtime_smoke(tmp_path):
    test_result = subprocess.run(
        ["go", "test", "./..."],
        cwd=GO_SHADOW,
        text=True,
        capture_output=True,
        timeout=120,
    )
    assert test_result.returncode == 0, test_result.stdout + test_result.stderr

    if os.name != "nt":
        return

    smoke_dir = tmp_path / "desktop-smoke"
    smoke_dir.mkdir()
    port = _free_port()
    smoke_result = subprocess.run(
        [
            "go",
            "run",
            ".",
            "--desktop-shell-smoke",
            "--data-dir",
            str(smoke_dir),
            "--addr",
            f"127.0.0.1:{port}",
        ],
        cwd=GO_SHADOW,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert smoke_result.returncode == 0, smoke_result.stdout + smoke_result.stderr
    assert (smoke_dir / "prism_desktop_dev.db").exists()
    assert (smoke_dir / "logs" / "desktop-shell.log").exists()
