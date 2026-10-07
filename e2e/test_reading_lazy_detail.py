"""PRISM-OPT-38: Reading view only fetches the open note and its two neighbours.

A 50-note reading workspace used to fire ~50 GET /api/notes/<id> requests on open. Test data is
CJK on purpose and is deleted afterwards so the shared isolated runtime stays as the other e2e
files expect.
"""

import json
import re

from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, expect

PREFIX = "閱讀清單懶載入 OPT38"
DETAIL_URL = re.compile(r"/api/notes/\d+(\?.*)?$")
STORAGE_KEY = "prism.readingWorkspace.v1"


def _open_reading(page: Page, note_id: int) -> None:
    page.locator(f'[data-testid="note-card-actions-{note_id}"]').click()
    page.get_by_role("menu").get_by_role("button", name="Read", exact=True).click()


def _freeze_list_after_page_one(route) -> None:
    """Keep list metadata fixed: pages >= 2 come back empty (real pagination, no rows)."""
    page_no = parse_qs(urlparse(route.request.url).query).get("page", ["1"])[0]
    if page_no == "1":
        route.continue_()
        return
    body = route.fetch().json()
    body["data"] = []
    route.fulfill(json=body)


def _stored_ids(page: Page) -> list[int]:
    raw = page.evaluate(f"localStorage.getItem('{STORAGE_KEY}')")
    return json.loads(raw)["noteIds"]


def test_reading_workspace_prefetches_only_neighbours(app_page: Page, runtime_url: str):
    page = app_page
    created: list[int] = []
    page.route(re.compile(r"/api/notes\?"), _freeze_list_after_page_one)
    try:
        for n in range(1, 51):
            response = page.request.post(
                f"{runtime_url}/api/notes",
                data={"title": f"{PREFIX} 第{n:02d}篇", "content": f"第{n:02d}篇：閱讀清單只抓相鄰項目。"},
            )
            assert response.status == 201, response.text()
            created.append(response.json()["data"]["note_id"])

        page.reload()
        page.locator('[data-testid="app-container"]').wait_for(state="visible", timeout=15_000)
        shown = page.locator('[data-testid^="note-card-actions-"]').evaluate_all(
            "els => els.map(el => Number(el.dataset.testid.split('-').pop()))"
        )
        # Pick a visible note in the middle of the workspace so it has two neighbours.
        pos = next(i for i in range(10, 40) if created[i] in shown)
        current = created[pos]
        far = next(i for i in range(50) if created[i] not in shown and abs(i - pos) > 2)
        page.evaluate(
            """([key, ids, activeId]) => {
                localStorage.setItem(key, JSON.stringify({
                    noteIds: ids, activeId, layout: 'sidebar', scrollPositions: {},
                }))
            }""",
            [STORAGE_KEY, created, current],
        )

        detail_ids: list[str] = []
        page.on(
            "request",
            lambda req: req.method == "GET" and DETAIL_URL.search(req.url) and detail_ids.append(req.url),
        )

        # 1. Opening the reading view: current + previous + next only.
        _open_reading(page, current)
        reading = page.locator('[data-testid="reading-view"]')
        expect(reading).to_be_visible(timeout=10_000)
        page.wait_for_load_state("networkidle")
        assert len(detail_ids) <= 3, f"opening fetched {len(detail_ids)} details: {detail_ids}"

        # 4. The list stays usable: loaded titles show, unloaded ones get a neutral placeholder.
        item = lambda note_id: page.locator(f'[data-testid="reading-workspace-item-{note_id}"]')
        expect(item(created[pos + 1])).to_contain_text(f"{PREFIX} 第{pos + 2:02d}篇")
        expect(item(created[far])).to_contain_text(f"#{created[far]}")
        # Unloaded entries must not sit on a "Loading" label forever.
        expect(reading).not_to_contain_text(re.compile("Loading|讀取中"))

        # 2. Switching to the next note fetches at most its new neighbour.
        before = len(detail_ids)
        item(created[pos + 1]).locator("button").first.click()
        expect(item(created[pos + 1])).to_have_attribute("data-active", "true")
        page.wait_for_load_state("networkidle")
        assert len(detail_ids) - before <= 2, f"switching fetched {len(detail_ids) - before} details"

        # Clicking a far-away entry loads it on demand.
        item(created[far]).locator("button").first.click()
        expect(item(created[far])).to_have_attribute("data-active", "true")
        expect(item(created[far])).to_contain_text(f"{PREFIX} 第{far + 1:02d}篇")

        # 3. A deleted note is dropped from the list and from localStorage when its turn comes.
        victim = created[pos + 2]
        assert page.request.delete(f"{runtime_url}/api/notes/{victim}").ok
        page.reload()
        page.locator('[data-testid="app-container"]').wait_for(state="visible", timeout=15_000)
        page.evaluate(
            """([key, ids, activeId]) => {
                localStorage.setItem(key, JSON.stringify({
                    noteIds: ids, activeId, layout: 'sidebar', scrollPositions: {},
                }))
            }""",
            [STORAGE_KEY, created, created[pos + 1]],
        )
        page.reload()
        _open_reading(page, created[pos + 1])
        expect(reading).to_be_visible(timeout=10_000)
        expect(item(victim)).to_have_count(0)
        assert victim not in _stored_ids(page)
        assert len(_stored_ids(page)) == 49
        expect(item(created[pos + 1])).to_be_visible()
    finally:
        for note_id in created:
            page.request.delete(f"{runtime_url}/api/notes/{note_id}")
        page.evaluate(f"localStorage.removeItem('{STORAGE_KEY}')")
