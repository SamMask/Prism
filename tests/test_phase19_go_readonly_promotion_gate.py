import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "docs" / "contracts" / "phase19-go-readonly-promotion-gate.json"
MAIN_GO = ROOT / "go-shadow" / "main.go"


def test_phase19_2_gate_keeps_go_readonly_and_reversible():
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))

    assert gate["phase"] == "19.2"
    assert gate["decision"] == "promote_to_controlled_readonly_candidate"
    assert gate["current_runtime_owner"] == "Python Flask prism.service"
    assert "read-only" in gate["go_runtime_role"]

    constraints = gate["promotion_constraints"]
    assert constraints["python_remains_rollback_path"] is True
    assert constraints["go_replaces_prism_service"] is False
    assert constraints["frontend_default_points_to_go"] is False
    assert constraints["go_runs_migrations"] is False

    blocked = " ".join(gate["blocked_until_future_phase"]).lower()
    assert "post / put / delete" in blocked
    assert "attachments" in blocked
    assert "production cutover" in blocked


def test_phase19_2_gate_matches_go_runtime_surface():
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    main_go = MAIN_GO.read_text(encoding="utf-8")

    registered = set(re.findall(r'mux\.HandleFunc\("([^"]+)"', main_go))
    registered.discard("/")
    registered.discard("/api/notes/")
    registered.discard("/api/tags/")
    registered.discard("/api/categories/")
    registered.add("/api/notes/<id>")

    expected = {entry.removeprefix("GET ") for entry in gate["allowed_api_surface"]}
    assert registered == expected

    assert "enableTagWrite" in main_go
    assert '"enable-tag-write"' in main_go
    forbidden_methods = ["http.MethodPost", "http.MethodDelete", "http.MethodPatch"]
    for method in forbidden_methods:
        assert method not in main_go


def test_phase19_2_next_step_is_controlled_read_routing_only():
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    next_phase = gate["next_phase"]

    assert next_phase["id"] == "19.3"
    assert "Read Routing" in next_phase["title"]
    assert "explicit reversible switch" in next_phase["scope"]

    forbidden_next_scope = " ".join(next_phase["must_not_include"]).lower()
    assert "write routes" in forbidden_next_scope
    assert "python backend removal" in forbidden_next_scope
