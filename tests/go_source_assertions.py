from pathlib import Path


def read_go_package_source(package_dir: Path) -> str:
    """Return non-test Go source as one assertion surface."""
    paths = sorted(
        path for path in package_dir.glob("*.go") if not path.name.endswith("_test.go")
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)
