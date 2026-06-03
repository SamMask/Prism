import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Response, current_app, request


TRUE_VALUES = {"1", "true", "yes", "on"}
READ_TIMEOUT_SECONDS = 2
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
ALLOWED_EXACT_PATHS = {
    "/api/test",
    "/api/categories",
    "/api/tags",
    "/api/notes",
}
NOTE_DETAIL_RE = re.compile(r"^/api/notes/[0-9]+$")


def go_read_routing_enabled(environ):
    return environ.get("PRISM_GO_READ_ROUTING", "").strip().lower() in TRUE_VALUES


def allowed_go_read_path(method, path):
    if method != "GET":
        return False
    return path in ALLOWED_EXACT_PATHS or bool(NOTE_DETAIL_RE.match(path))


def normalize_go_base_url(raw_url):
    parsed = urlparse((raw_url or "").strip())
    if parsed.scheme != "http":
        raise ValueError("Go read routing requires an http localhost base URL")
    if parsed.username or parsed.password:
        raise ValueError("Go read routing base URL must not include credentials")
    if parsed.path not in ("", "/"):
        raise ValueError("Go read routing base URL must not include a path")

    host = parsed.hostname
    if host not in LOCAL_HOSTS:
        raise ValueError("Go read routing is restricted to localhost, 127.0.0.1, or ::1")
    if parsed.port is None:
        raise ValueError("Go read routing requires an explicit sidecar port")

    if host == "::1":
        netloc = f"[::1]:{parsed.port}"
    else:
        netloc = f"{host}:{parsed.port}"
    return f"http://{netloc}"


def _target_url(base_url, path, query_string):
    if query_string:
        return f"{base_url}{path}?{query_string.decode('utf-8')}"
    return f"{base_url}{path}"


def _proxy_response(status, body, content_type):
    response = Response(body, status=status, content_type=content_type or "application/json; charset=utf-8")
    response.headers["X-Prism-Go-Read-Routing"] = "hit"
    return response


def proxy_go_read_request(environ):
    if not go_read_routing_enabled(environ):
        return None
    if not allowed_go_read_path(request.method, request.path):
        return None

    try:
        base_url = normalize_go_base_url(environ.get("PRISM_GO_READ_BASE_URL", ""))
    except ValueError as exc:
        current_app.logger.warning("[GoReadRouting] disabled: %s", exc)
        return None

    target = _target_url(base_url, request.path, request.query_string)
    proxied = Request(target, headers={"Accept": request.headers.get("Accept", "application/json")}, method="GET")
    try:
        with urlopen(proxied, timeout=READ_TIMEOUT_SECONDS) as upstream:
            return _proxy_response(upstream.status, upstream.read(), upstream.headers.get("Content-Type"))
    except HTTPError as exc:
        return _proxy_response(exc.code, exc.read(), exc.headers.get("Content-Type"))
    except (URLError, TimeoutError, socket.timeout) as exc:
        current_app.logger.warning("[GoReadRouting] fallback to Python for %s: %s", request.full_path, exc)
        return None


def routing_status(environ):
    enabled = go_read_routing_enabled(environ)
    base_url = environ.get("PRISM_GO_READ_BASE_URL", "")
    try:
        normalized_base_url = normalize_go_base_url(base_url) if enabled else None
        valid_base_url = True if enabled else None
        error = None
    except ValueError as exc:
        normalized_base_url = None
        valid_base_url = False
        error = str(exc)

    return {
        "status": "success",
        "data": {
            "phase": "19.3",
            "enabled": enabled,
            "base_url": normalized_base_url,
            "valid_base_url": valid_base_url,
            "mode": "controlled-read-routing-proof",
            "default_owner": "python",
            "fallback_owner": "python",
            "allowed_api_surface": sorted(ALLOWED_EXACT_PATHS) + ["/api/notes/<id>"],
            "blocked_methods": ["POST", "PUT", "DELETE", "PATCH"],
            "error": error,
        },
    }
