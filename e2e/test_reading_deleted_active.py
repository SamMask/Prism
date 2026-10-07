"""PRISM-OPT-73: a deleted active note must not make the reading list unopenable.

Test data is CJK on purpose; every note is deleted afterwards so the shared isolated runtime
stays as the other e2e files expect.
"""

import json
import re

from playwright.sync_api import Page, expect

PREFIX = "閱讀中刪除 OPT73"
STORAGE_KEY = "prism.readingWorkspace.v1"
NOTE_URL = "**/api/notes/{id}"


def _make_notes(page: Page, runtime_url: str, count: int = 3) -> list[int]:
    ids = []
    for n in range(1, count + 1):
        response = page.request.post(
            f"{runtime_url}/api/notes",
            data={"title": f"{PREFIX} 第{n}篇", "content": f"第{n}篇：被刪除的閱讀項目。"},
        )
        assert response.status == 201, response.text()
        ids.append(response.json()["data"]["note_id"])
    return ids


def _set_workspace(page: Page, ids: list[int], active: int) -> None:
    page.evaluate(
        """([key, ids, activeId]) => localStorage.setItem(key, JSON.stringify({
            noteIds: ids, activeId, layout: 'sidebar', scrollPositions: {},
        }))""",
        [STORAGE_KEY, ids, active],
    )
    page.reload()
    page.locator('[data-testid="app-container"]').wait_for(state="visible", timeout=15_000)


def _stored_ids(page: Page) -> list[int]:
    return json.loads(page.evaluate(f"localStorage.getItem('{STORAGE_KEY}')"))["noteIds"]


def _cleanup(page: Page, runtime_url: str, ids: list[int]) -> None:
    page.unroute_all()
    for note_id in ids:
        page.request.delete(f"{runtime_url}/api/notes/{note_id}")
    page.evaluate(f"localStorage.removeItem('{STORAGE_KEY}')")


def _open_from_header(page: Page) -> None:
    page.locator('[data-testid="header-open-reading-workspace"]').click()


def test_header_skips_deleted_active_and_opens_next(app_page: Page, runtime_url: str):
    page = app_page
    ids = _make_notes(page, runtime_url)
    try:
        _set_workspace(page, ids, ids[0])
        assert page.request.delete(f"{runtime_url}/api/notes/{ids[0]}").ok

        _open_from_header(page)
        reading = page.locator('[data-testid="reading-view"]')
        expect(reading).to_be_visible(timeout=10_000)
        expect(reading.locator("h1")).to_have_text(f"{PREFIX} 第2篇")
        expect(page.locator(f'[data-testid="reading-workspace-item-{ids[0]}"]')).to_have_count(0)
        expect(page.locator(f'[data-testid="reading-workspace-item-{ids[1]}"]')).to_be_visible()
        assert _stored_ids(page) == ids[1:]
        expect(page.locator('[role="status"]')).to_have_count(0)
    finally:
        _cleanup(page, runtime_url, ids)


def test_header_all_deleted_prompts_once_without_console_errors(app_page: Page, runtime_url: str):
    page = app_page
    ids = _make_notes(page, runtime_url)
    console_errors: list[str] = []
    # The 404 itself is logged by the browser as "Failed to load resource"; that is expected.
    page.on(
        "console",
        lambda msg: msg.type == "error"
        and "Failed to load resource" not in msg.text
        and console_errors.append(msg.text),
    )
    try:
        _set_workspace(page, ids, ids[0])
        for note_id in ids:
            assert page.request.delete(f"{runtime_url}/api/notes/{note_id}").ok

        detail_requests: list[str] = []
        page.on(
            "request",
            lambda req: req.method == "GET"
            and re.search(r"/api/notes/\d+(\?.*)?$", req.url)
            and detail_requests.append(req.url),
        )
        _open_from_header(page)
        expect(page.locator('[role="status"]')).to_have_count(1, timeout=10_000)
        expect(page.locator('[data-testid="header-open-reading-workspace"]')).to_have_count(0)
        expect(page.locator('[data-testid="reading-view"]')).to_have_count(0)
        assert _stored_ids(page) == []
        assert len(detail_requests) == 3, detail_requests  # one attempt per entry, no retry loop
        assert console_errors == []
    finally:
        _cleanup(page, runtime_url, ids)


def test_reading_view_drops_deleted_current_and_switches(app_page: Page, runtime_url: str):
    page = app_page
    ids = _make_notes(page, runtime_url)
    try:
        _set_workspace(page, ids, ids[1])
        real = page.request.get(f"{runtime_url}/api/notes/{ids[1]}").text()
        assert page.request.delete(f"{runtime_url}/api/notes/{ids[1]}").ok
        # The Header lookup is served from before the delete; the ReadingView re-read then
        # hits the (now real) 404.
        served = {"n": 0}

        def handler(route):
            served["n"] += 1
            if served["n"] == 1:
                route.fulfill(status=200, content_type="application/json", body=real)
            else:
                route.continue_()

        page.route(re.compile(rf"/api/notes/{ids[1]}(\?.*)?$"), handler)
        _open_from_header(page)
        reading = page.locator('[data-testid="reading-view"]')
        expect(reading.locator("h1")).to_have_text(f"{PREFIX} 第3篇", timeout=10_000)
        expect(page.locator(f'[data-testid="reading-workspace-item-{ids[1]}"]')).to_have_count(0)
        assert _stored_ids(page) == [ids[0], ids[2]]
    finally:
        _cleanup(page, runtime_url, ids)


def test_server_error_on_active_keeps_item_and_shows_error(app_page: Page, runtime_url: str):
    page = app_page
    ids = _make_notes(page, runtime_url)
    try:
        _set_workspace(page, ids, ids[0])
        page.route(
            re.compile(rf"/api/notes/{ids[0]}(\?.*)?$"),
            lambda route: route.fulfill(status=500, json={"error": "boom"}),
        )
        _open_from_header(page)
        expect(page.get_by_text("Failed to load reading list note").first).to_be_visible(timeout=10_000)
        expect(page.locator('[data-testid="reading-view"]')).to_have_count(0)
        assert _stored_ids(page) == ids
    finally:
        _cleanup(page, runtime_url, ids)
