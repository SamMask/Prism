import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GO_SHADOW = ROOT / "go-shadow"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
ARCHITECTURE_PATH = ROOT / "docs" / "ARCHITECTURE.md"
README_PATH = ROOT / "go-shadow" / "README.md"
PORTABLE_README = ROOT / "docs" / "desktop" / "README-PORTABLE.md"
BUILD_SCRIPT = ROOT / "scripts" / "build_desktop_portable.ps1"
SMOKE_SCRIPT = ROOT / "scripts" / "smoke_desktop_portable.ps1"
DEPLOY_PI = ROOT / "DEPLOY-PI.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_desktop_shell_phase4_portable_scripts_lock_release_shape():
    build_script = _read(BUILD_SCRIPT)
    smoke_script = _read(SMOKE_SCRIPT)
    shell_build = _read(ROOT / "scripts" / "build_desktop_shell.ps1")
    readme = _read(PORTABLE_README)
    main_source = _read(GO_SHADOW / "main.go")
    windows_source = _read(GO_SHADOW / "desktop_shell_windows.go")

    for required in [
        "Prism.exe",
        "PrismDesktop-debug.exe",
        "Compress-Archive",
        "README-PORTABLE.md",
        "main.desktopShellDefault=1",
        "-H=windowsgui",
    ]:
        assert required in build_script

    for required in [
        "--desktop-shell-smoke",
        "--data-dir",
        "external-data",
        "*.db",
        "evidence.json",
        "prism_desktop_dev.db",
    ]:
        assert required in smoke_script

    assert "main.desktopShellDefault=1" in shell_build
    assert "desktopShellDefaultEnabled" in main_source
    assert "resolveDesktopDataDir" in windows_source
    assert "PrismPortable.json" in windows_source
    assert "PrismData" in windows_source
    assert "runDesktopDataDirPicker" in windows_source
    assert "runDesktopSmokeNoteWorkflow" in windows_source
    assert "%LOCALAPPDATA%\\Prism\\DesktopData" in readme
    assert "PrismPortable.json" in readme
    assert "PrismData" in readme

    lowered = build_script.lower() + smoke_script.lower()
    for forbidden in ["nsis", "wix", ".msi", "autoupdater", "auto updater"]:
        assert forbidden not in lowered


def test_desktop_shell_phase4_6_docs_close_package_decision_and_pi_boundary():
    todo = _read(TODO_PATH)
    handoff = _read(HANDOFF_PATH)
    contracts = _read(CONTRACTS_PATH)
    architecture = _read(ARCHITECTURE_PATH)
    readme = _read(README_PATH)
    deploy_pi = _read(DEPLOY_PI)

    for required in [
        "#### Phase 4 — Portable Windows package（2026-06-17 完成）",
        "#### Phase 5 — Installer / updater decision gate（2026-06-17 完成）",
        "#### Phase 6 — Pi deployment boundary check（2026-06-17 完成）",
        "portable zip 是 Windows release 主路徑",
        "不做 MSI/NSIS/WiX installer、不做 auto updater",
        "Pi 仍使用 linux/arm64 Go primary artifact",
        "Desktop Shell post-package manual acceptance",
        "第一次啟動選擇器",
    ]:
        assert required in todo

    for required in [
        "CONTRACT-DESKTOP-SHELL-PORTABLE-PACKAGE",
        "CONTRACT-DESKTOP-SHELL-INSTALLER-DECISION",
        "CONTRACT-DESKTOP-SHELL-PI-BOUNDARY",
    ]:
        assert required in contracts

    assert "Desktop Shell Phase 4-6 完成" in handoff
    assert "第一次啟動 data-dir 選擇" in handoff
    assert "build_desktop_portable.ps1" in architecture
    assert "PrismPortable.json" in architecture
    assert "smoke_desktop_portable.ps1" in readme
    assert "WebView2" not in deploy_pi
    assert "Prism.exe" not in deploy_pi
    assert "desktop_shell_windows.go" in architecture


def test_desktop_shell_phase4_portable_smoke_script():
    if os.name != "nt":
        return

    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SMOKE_SCRIPT),
            "-SmokeRoot",
            "build/pytest-desktop-portable-smoke",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
