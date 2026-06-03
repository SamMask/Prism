import json
from urllib.error import URLError

import pytest

from utils import go_read_routing


def test_phase19_3_contract_documents_reversible_read_routing():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    contract = json.loads(
        (root / "docs" / "contracts" / "phase19-go-read-routing-proof.json").read_text(
            encoding="utf-8"
        )
    )

    assert contract["phase"] == "19.3"
    assert contract["default_owner"] == "python"
    assert contract["fallback_owner"] == "python"
    assert contract["switch"]["default_state"] == "off"
    assert contract["switch"]["enabled_by"] == "PRISM_GO_READ_ROUTING=1"
    assert contract["failure_behavior"] == "fail_open_to_python"
    assert contract["response_evidence"]["proxied_header"] == "X-Prism-Go-Read-Routing: hit"

    assert set(contract["proxied_surface"]) == {
        "GET /api/test",
        "GET /api/categories",
        "GET /api/tags",
        "GET /api/notes",
        "GET /api/notes/<id>",
    }
    assert contract["next_phase"]["id"] == "19.4"
    assert "production cutover" in contract["next_phase"]["must_not_include"]


def test_go_read_routing_default_off_uses_python(client, monkeypatch):
    monkeypatch.delenv("PRISM_GO_READ_ROUTING", raising=False)
    monkeypatch.delenv("PRISM_GO_READ_BASE_URL", raising=False)

    response = client.get("/api/test")

    assert response.status_code == 200
    assert response.headers.get("X-Prism-Go-Read-Routing") is None
    assert response.json["message"] == "Prism API is running!"


def test_go_read_routing_proxies_allowed_get_surface(client, monkeypatch):
    captured = {}

    class FakeUpstream:
        status = 200
        headers = {"Content-Type": "application/json; charset=utf-8"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"status": "ok", "source": "go"}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeUpstream()

    monkeypatch.setenv("PRISM_GO_READ_ROUTING", "1")
    monkeypatch.setenv("PRISM_GO_READ_BASE_URL", "http://127.0.0.1:5002")
    monkeypatch.setattr(go_read_routing, "urlopen", fake_urlopen)

    response = client.get("/api/notes?page=1&per_page=1")

    assert response.status_code == 200
    assert response.headers["X-Prism-Go-Read-Routing"] == "hit"
    assert response.json == {"status": "ok", "source": "go"}
    assert captured["url"] == "http://127.0.0.1:5002/api/notes?page=1&per_page=1"
    assert captured["timeout"] == go_read_routing.READ_TIMEOUT_SECONDS


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/notes"),
        ("get", "/api/export/json"),
        ("get", "/api/system/go-read-routing"),
    ],
)
def test_go_read_routing_does_not_proxy_non_allowed_surface(client, monkeypatch, method, path):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise AssertionError("unexpected Go proxy call")

    monkeypatch.setenv("PRISM_GO_READ_ROUTING", "1")
    monkeypatch.setenv("PRISM_GO_READ_BASE_URL", "http://127.0.0.1:5002")
    monkeypatch.setattr(go_read_routing, "urlopen", fake_urlopen)

    response = getattr(client, method)(path)

    assert response.headers.get("X-Prism-Go-Read-Routing") is None
    assert calls == []


def test_go_read_routing_rejects_non_local_base_url(client, monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise AssertionError("unexpected Go proxy call")

    monkeypatch.setenv("PRISM_GO_READ_ROUTING", "1")
    monkeypatch.setenv("PRISM_GO_READ_BASE_URL", "http://example.com:5002")
    monkeypatch.setattr(go_read_routing, "urlopen", fake_urlopen)

    response = client.get("/api/test")
    status = client.get("/api/system/go-read-routing")

    assert response.status_code == 200
    assert response.headers.get("X-Prism-Go-Read-Routing") is None
    assert status.json["data"]["enabled"] is True
    assert status.json["data"]["valid_base_url"] is False
    assert calls == []


def test_go_read_routing_falls_back_to_python_when_sidecar_unavailable(client, monkeypatch):
    def fake_urlopen(request, timeout):
        raise URLError("connection refused")

    monkeypatch.setenv("PRISM_GO_READ_ROUTING", "1")
    monkeypatch.setenv("PRISM_GO_READ_BASE_URL", "http://127.0.0.1:5002")
    monkeypatch.setattr(go_read_routing, "urlopen", fake_urlopen)

    response = client.get("/api/test")

    assert response.status_code == 200
    assert response.headers.get("X-Prism-Go-Read-Routing") is None
    assert response.json["message"] == "Prism API is running!"
