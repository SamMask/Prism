"""Governance check: subagent definitions, the dispatch guide and the ticket
dispatch table stay consistent (docs/AGENT_DISPATCH.md, PRISM-OPT-52).

This is a configuration/document consistency check, not behavior evidence
(docs/GOVERNANCE.md §3).
"""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / ".claude" / "agents"
DISPATCH_PATH = ROOT / "docs" / "AGENT_DISPATCH.md"
WORK_ORDERS_PATH = ROOT / "docs" / "WORK_ORDERS.md"
TODO_PATH = ROOT / "docs" / "TODO.md"

VALID_MODELS = {"haiku", "sonnet", "opus", "fable", "inherit"}
VALID_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
READ_ONLY_AGENTS = {"prism-scout", "prism-verifier"}


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, f"{path.name} has no frontmatter"
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith(" "):
            fields[key.strip()] = value.strip().strip('"')
    return fields


def _agents() -> dict:
    return {path.stem: _frontmatter(path) for path in sorted(AGENTS_DIR.glob("prism-*.md"))}


def _table_cells(text: str, first_cell: str):
    for line in text.replace("\r\n", "\n").splitlines():
        if line.startswith(f"| {first_cell} |"):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    return None


def test_agent_definitions_use_valid_model_and_effort():
    agents = _agents()
    assert set(agents) == {
        "prism-scout",
        "prism-docs",
        "prism-builder",
        "prism-engineer",
        "prism-critical",
        "prism-verifier",
    }
    for stem, fields in agents.items():
        assert fields.get("name") == stem
        assert fields.get("description")
        assert fields.get("model") in VALID_MODELS, stem
        if fields["model"] == "haiku":
            assert "effort" not in fields, f"{stem}: Haiku 4.5 does not support effort"
        else:
            assert fields.get("effort") in VALID_EFFORTS, stem
    for stem in READ_ONLY_AGENTS:
        disallowed = agents[stem].get("disallowedTools", "")
        for tool in ("Edit", "Write"):
            assert tool in disallowed, f"{stem} must not be able to {tool}"


def test_dispatch_guide_matches_agent_definitions():
    guide = DISPATCH_PATH.read_text(encoding="utf-8")
    for stem, fields in _agents().items():
        cells = _table_cells(guide, stem)
        assert cells, f"{stem} is missing from the agent table in docs/AGENT_DISPATCH.md"
        assert cells[1] == fields["model"], stem
        if "effort" in fields:
            assert cells[2] == fields["effort"], stem
        else:
            assert cells[2].startswith("（不設定"), stem


def test_every_board_ticket_has_a_dispatch_assignment_with_known_agents():
    agents = set(_agents())
    todo = TODO_PATH.read_text(encoding="utf-8")
    work_orders = WORK_ORDERS_PATH.read_text(encoding="utf-8")
    board_ids = set(re.findall(r"^\| (PRISM-OPT-\d+) \|", todo, re.M))
    assert board_ids

    for ticket in sorted(board_ids):
        cells = _table_cells(work_orders, ticket)
        assert cells and len(cells) == 5, f"{ticket} is missing from the dispatch table"
        category, difficulty, worker, reviewer = cells[1:]
        assert category in {"R", "D", "F", "B", "T", "X", "V"}, ticket
        assert difficulty in {"S", "M", "L", "XL"}, ticket
        assignment = f"{worker} {reviewer}"
        named = set(re.findall(r"prism-[a-z]+", assignment))
        assert named <= agents, (ticket, named - agents)
        assert named or "主代理" in assignment, ticket
