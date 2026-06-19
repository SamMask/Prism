from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
README_ZH_PATH = ROOT / "README.zh-TW.md"
DOCS_README_PATH = ROOT / "docs" / "README.md"
DOCS_INDEX_PATH = ROOT / "docs" / "INDEX.md"
CONTRIBUTING_PATH = ROOT / "docs" / "CONTRIBUTING.md"
RELEASE_CHECKLIST_PATH = ROOT / "docs" / "RELEASE_CHECKLIST.md"
TODO_PATH = ROOT / "docs" / "TODO.md"
HANDOFF_PATH = ROOT / "HANDOFF.md"
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
REQ_PATH = ROOT / "requirements.txt"
REQ_PI_PATH = ROOT / "requirements-pi.txt"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_project_review_hygiene_license_file_matches_readme_claim():
    license_path = ROOT / "LICENSE"
    assert license_path.exists()
    license_text = _text(license_path)

    assert "MIT License" in license_text
    assert "Copyright (c) 2026 SamMask" in license_text
    assert "Permission is hereby granted, free of charge" in license_text

    assert "MIT License. See [`LICENSE`](LICENSE)." in _text(README_PATH)
    assert "MIT License。見 [`LICENSE`](LICENSE)。" in _text(README_ZH_PATH)


def test_project_review_hygiene_ci_is_no_secret_no_pi_local_gate_baseline():
    ci = _text(CI_PATH)

    for required in (
        "windows-latest",
        "actions/checkout@v4",
        "actions/setup-go@v5",
        "go-version-file: go-shadow/go.mod",
        "actions/setup-node@v4",
        "node-version: 22.14.0",
        "actions/setup-python@v5",
        "python-version: \"3.11\"",
        "npm ci",
        "python -m pip install -r requirements.txt",
        "npm run build",
        "go-shadow/web/dist",
        "frontend/dist/*",
        ".loop/verify-gate.ps1",
    ):
        assert required in ci

    for forbidden in (
        "PI5Mask24",
        "DEPLOY-PI",
        "ssh ",
        "secrets.",
        "knowledge.db",
        "static/uploads",
        "docs/attachments",
        "PRISM_GO_ALLOW_PUBLIC_BIND",
    ):
        assert forbidden not in ci


def test_project_review_hygiene_verification_environment_is_aligned():
    assert "pytest==9.0.2" in _text(REQ_PATH)
    assert "pytest==9.0.2" in _text(REQ_PI_PATH)

    expected_fragments = (
        "Go 1.26.x",
        "Node.js 22.14.0",
        "npm 10.9.2",
        "Python 3.11.x",
        "pytest 9.0.2",
    )
    docs = "\n".join(
        [
            _text(README_PATH),
            _text(README_ZH_PATH),
            _text(CONTRIBUTING_PATH),
            _text(RELEASE_CHECKLIST_PATH),
        ]
    )
    for fragment in expected_fragments:
        assert fragment in docs

    assert "pytest==7.4.3" not in _text(REQ_PATH)
    assert "pytest==7.4.3" not in _text(REQ_PI_PATH)


def test_project_review_hygiene_release_checklist_requires_fresh_evidence():
    checklist = _text(RELEASE_CHECKLIST_PATH)

    for required in (
        "public GitHub release, tag, or portable package claim",
        "fresh date, result, and evidence pointer",
        "Not-tested",
        ".loop/verify-gate.ps1",
        "cd frontend && npm run build",
        "Local browser smoke",
        "Windows desktop portable smoke",
        "Release package privacy sweep",
        "AGENTS.md` / `CLAUDE.md` mirror check",
    ):
        assert required in checklist

    assert "docs/RELEASE_CHECKLIST.md" in _text(README_PATH)
    assert "docs/RELEASE_CHECKLIST.md" in _text(README_ZH_PATH)
    assert "RELEASE_CHECKLIST.md" in _text(DOCS_README_PATH)
    assert "RELEASE_CHECKLIST.md" in _text(DOCS_INDEX_PATH)


def test_project_review_hygiene_contributing_e2e_path_matches_repo_layout():
    contributing = _text(CONTRIBUTING_PATH)

    assert (ROOT / "e2e").is_dir()
    assert "位於 `e2e/`" in contributing
    assert "tests/e2e/" not in contributing


def test_project_review_hygiene_todo_and_handoff_close_01a_to_01e():
    todo = _text(TODO_PATH)
    handoff = _text(HANDOFF_PATH)

    for task_id in ("01A", "01B", "01C", "01D", "01E"):
        assert f"- [x] **{task_id} " in todo

    normalized_docs = "\n".join([todo, handoff]).replace("`", "")
    assert "PROJECT-REVIEW-HYGIENE-CANDIDATE-01 01A-01E 已完成 local gate" in normalized_docs
    assert "01H 仍是低優先維護 triage" in todo
