"""Go build helper for the post-T053 runtime tests.

Before T053 this module was the Python-vs-Go parity harness. The Python oracle
(`observe_flask_fixture` / `compare_observations`) was removed together with the
retained Flask backend; Go is now verified independently by the GO-ONLY runtime
tests, `go-shadow/main_test.go`, and the pure-Go acceptance net. What remains is
the single helper that builds the Go runtime binary those tests drive.
"""

import os
import subprocess
from pathlib import Path

GO_SHADOW_DIR = Path(__file__).resolve().parents[1] / "go-shadow"


def build_go_shadow_exe(go_bin: str, tmp_path: Path) -> Path:
    exe_path = Path(tmp_path) / ("prism-go-shadow.exe" if os.name == "nt" else "prism-go-shadow")
    subprocess.run(
        [go_bin, "build", "-o", str(exe_path), "."],
        cwd=GO_SHADOW_DIR,
        check=True,
    )
    return exe_path
