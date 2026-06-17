import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPIKE_DIR = ROOT / "desktop-spike"
TODO_PATH = ROOT / "docs" / "TODO.md"
CONTRACTS_PATH = ROOT / "docs" / "CONTRACTS.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_desktop_shell_phase0_scope_is_isolated_and_documented():
    assert (SPIKE_DIR / "go.mod").exists()
    assert (SPIKE_DIR / "main.go").exists()
    assert (SPIKE_DIR / "main_other.go").exists()
    assert (SPIKE_DIR / "README.md").exists()

    go_mod = _read(SPIKE_DIR / "go.mod")
    readme = _read(SPIKE_DIR / "README.md")
    contracts = _read(CONTRACTS_PATH)

    assert "module prism-desktop-spike" in go_mod
    assert "golang.org/x/sys v" in go_mod
    assert "webview" not in go_mod.lower()
    assert "WebView2" in readme
    assert "Out of scope" in readme
    assert "CONTRACT-DESKTOP-SHELL-SPIKE" in contracts


def test_desktop_shell_phase0_win32_surface_matches_contract():
    source = _read(SPIKE_DIR / "main.go")

    for required in [
        "CreateWindowExW",
        "Shell_NotifyIconW",
        "GetMessageW",
        "TrackPopupMenu",
        "PostQuitMessage",
        "cmdShow",
        "cmdQuit",
        "runtime.LockOSThread()",
    ]:
        assert required in source

    forbidden = [
        "go-webview2",
        "webview",
        "start_go_primary",
        "http.ListenAndServe",
        "knowledge.db",
        "PRISM_GO_DATA_DIR",
    ]
    lowered = source.lower()
    for term in forbidden:
        assert term.lower() not in lowered


def test_desktop_shell_phase0_docs_close_current_entry_without_expanding_scope():
    todo = _read(TODO_PATH)
    handoff = _read(HANDOFF_PATH)

    assert "[x] 建立獨立 `desktop-spike/`" in todo
    assert "[x] 僅使用 `golang.org/x/sys/windows` syscall" in todo
    assert "[x] 空 Win32 視窗 + tray icon" in todo
    assert "[x] 關閉視窗預設直接結束行程" in todo
    assert "[x] 驗收：tray 選單有反應、關視窗正常退出、message loop 不卡住" in todo
    assert "Desktop Shell Phase 1 — WebView2 spike" in todo
    assert "Phase 0 完成" in handoff
    assert "Phase 1" in handoff


def test_desktop_shell_phase0_go_build_and_self_test():
    env = os.environ.copy()
    env.setdefault("GOFLAGS", "")

    test_result = subprocess.run(
        ["go", "test", "./..."],
        cwd=SPIKE_DIR,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert test_result.returncode == 0, test_result.stdout + test_result.stderr

    if os.name != "nt":
        return

    run_result = subprocess.run(
        ["go", "run", ".", "--self-test"],
        cwd=SPIKE_DIR,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr
