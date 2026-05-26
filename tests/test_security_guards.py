# -*- coding: utf-8 -*-
"""
Security regression tests — Phase 14 (v2.4.6)

Covers three guards added / hardened in v2.4.2 that previously had no
automated tests:

  1. SSRF guard          — _is_ssrf_target() in routes/upload.py
  2. Server localhost    — _require_localhost() before_request in routes/server.py
  3. Production CSRF     — csrf_protect() in app.py (V2_MODE=True + debug=False branch)

Each test targets exactly one guard so a future regression is easy to
pinpoint.  No real HTTP is made; no mocks are needed for SSRF because
socket.getaddrinfo() handles numeric IPs directly without DNS lookup.
"""

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: production-like client (V2_MODE=True, debug=False)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def prod_client(temp_db):
    """
    Flask test client configured as production (V2_MODE=True, DEBUG=False).

    TestingConfig does not override DEBUG, so Flask's default (False) applies.
    Only V2_MODE needs to be forced True to activate the CSRF production branch.
    """
    from app import create_app

    flask_app = create_app('testing')
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': temp_db,
        'V2_MODE': True,
    })
    # flask_app.debug is already False — TestingConfig inherits Config which
    # does not set DEBUG, so Flask defaults to False.
    with flask_app.app_context():
        yield flask_app.test_client()


# ─────────────────────────────────────────────────────────────────────────────
# 1. SSRF guard — /api/upload/url
# ─────────────────────────────────────────────────────────────────────────────

def test_ssrf_blocks_loopback(client):
    """
    POST /api/upload/url with a loopback target must return 400.

    socket.getaddrinfo('127.0.0.1') resolves directly (no DNS) and
    ipaddress.ip_address('127.0.0.1').is_loopback == True, so
    _is_ssrf_target() returns True before any HTTP request is made.

    Origin header is included to bypass the CSRF before_request guard
    regardless of the test-environment V2_MODE setting.
    """
    response = client.post(
        '/api/upload/url',
        json={'url': 'http://127.0.0.1/x.png'},
        headers={'Origin': 'http://localhost'},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'private or reserved' in data['message']


def test_ssrf_blocks_private_range(client):
    """
    POST /api/upload/url with an RFC-1918 address must return 400.

    192.168.1.1 is a numeric IP; getaddrinfo returns it directly and
    ipaddress detects is_private == True.
    """
    response = client.post(
        '/api/upload/url',
        json={'url': 'http://192.168.1.1/x.png'},
        headers={'Origin': 'http://localhost'},
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'private or reserved' in data['message']


# ─────────────────────────────────────────────────────────────────────────────
# 2. Server API localhost-only guard — routes/server.py
# ─────────────────────────────────────────────────────────────────────────────

def test_server_api_localhost_only(client):
    """
    GET /api/server/hardware from a non-localhost IP must return 403.

    _require_localhost() is a before_request on server_bp; it checks
    request.remote_addr against ('127.0.0.1', '::1').  The test client
    defaults to REMOTE_ADDR=127.0.0.1, so environ_base is used to override.
    """
    response = client.get(
        '/api/server/hardware',
        environ_base={'REMOTE_ADDR': '10.0.0.5'},
    )
    assert response.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 3. Production CSRF guard — app.py csrf_protect()
# ─────────────────────────────────────────────────────────────────────────────

def test_csrf_production_blocks_anonymous(prod_client):
    """
    POST without Origin or Referer in V2_MODE + non-debug must return 403.

    csrf_protect() fires in before_request:
        is_prod = config['V2_MODE'] and not app.debug   # True and True → True
        → abort(403)

    The request never reaches the notes route or the database, so the
    response body / DB state are irrelevant to this assertion.
    """
    response = prod_client.post(
        '/api/notes',
        json={'title': 'probe', 'content': 'probe'},
        # Deliberately no Origin and no Referer headers
    )
    assert response.status_code == 403
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'CSRF' in data['message']
