"""PRISM-OPT-69: deleting notes re-reads the loaded list pages so load-more keeps the right offset.

Without the refresh, the local filter leaves currentPage unchanged while the server offset moves
forward, so the note that crossed the page boundary is skipped by the next load-more. Test data is
CJK on purpose and removed afterwards so the shared isolated runtime stays as other e2e files expect.
"""

from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, expect

PREFIX = "刪除後載入 OPT69"
GRID_CARDS = '[data-testid="notes-grid"] > [data-testid^="note-card-"]'
LIST_SPINNER = "main > div > svg.animate-spin"


def _list_page(response, number: int) -> bool:
    url = urlparse(response.url)
    return (
        response.request.method == "GET"
        and url.path == "/api/notes"
        and parse_qs(url.query).get("page") == [str(number)]
    )


def _card_ids(page: Page) -> list[int]:
    testids = page.locator(GRID_CARDS).evaluate_all("els => els.map(el => el.dataset.testid)")
    return [int(t.rsplit("-", 1)[1]) for t in testids]


def _server_order(page: Page, runtime_url: str, pages: int = 5) -> list[int]:
    ids: list[int] = []
    for number in range(1, pages + 1):
        data = page.request.get(
            f"{runtime_url}/api/notes", params={"page": number, "per_page": 20, "sort": "updated"}
        ).json()["data"]
        ids += [note["id"] for note in data]
    return ids


def _create_notes(page: Page, runtime_url: str, count: int) -> list[int]:
    created = []
    for n in range(1, count + 1):
        response = page.request.post(
            f"{runtime_url}/api/notes",
            data={"title": f"{PREFIX} 第{n:02d}篇", "content": f"第{n:02d}篇：刪除後載入更多不可漏筆記。"},
        )
        assert response.status == 201, response.text()
        created.append(response.json()["data"]["note_id"])
    return created


def _open_two_pages(page: Page) -> None:
    page.evaluate(
        """() => {
            localStorage.setItem('prism.viewMode', 'compact')
            localStorage.setItem('autoLoadMore', 'false')
        }"""
    )
    page.reload()
    cards = page.locator(GRID_CARDS)
    expect(cards).to_have_count(20)
    page.get_by_text("Click to load more").click()
    expect(cards).to_have_count(40)


def _confirm(page: Page) -> None:
    page.get_by_role("alertdialog").get_by_role("button", name="Confirm").click()


def _delete_and_wait(page: Page, action) -> list[str]:
    """Run a delete and wait until both loaded pages were re-read; return the /api/ requests sent."""
    sent: list[str] = []

    def record(request) -> None:
        if "/api/" in request.url:
            parsed = urlparse(request.url)
            sent.append(f"{request.method} {parsed.path}?{parsed.query}")

    page.on("request", record)
    try:
        with page.expect_response(lambda r: _list_page(r, 1)), page.expect_response(lambda r: _list_page(r, 2)):
            action()
        expect(page.locator(LIST_SPINNER)).to_have_count(0)
    finally:
        page.remove_listener("request", record)
    return sent


def _assert_load_more_complete(page: Page, before: list[int], deleted: set[int]) -> None:
    cards = page.locator(GRID_CARDS)
    expect(cards).to_have_count(40)  # both loaded pages re-read, refilled from the next note
    page.get_by_text("Click to load more").click()
    expect(cards).to_have_count(60)
    ids = _card_ids(page)
    assert len(ids) == len(set(ids)), f"duplicate ids after load-more: {ids}"
    expected = [i for i in before if i not in deleted][:60]
    assert ids == expected, f"load-more skipped or reordered notes: {ids} != {expected}"


def test_single_delete_then_load_more_skips_nothing(app_page: Page, runtime_url: str):
    page = app_page
    created: list[int] = []
    try:
        created = _create_notes(page, runtime_url, 50)
        _open_two_pages(page)
        before = _server_order(page, runtime_url)
        assert len(before) >= 61
        victim = _card_ids(page)[4]
        assert victim == before[4]

        def delete():
            page.locator(f'[data-testid="note-card-actions-{victim}"]').click()
            page.get_by_role("menu").get_by_role("button", name="Delete", exact=True).click()
            _confirm(page)

        sent = _delete_and_wait(page, delete)
        note_requests = [r for r in sent if r.startswith("GET /api/notes?")]
        print("OPT-69 requests after single delete:", sent)
        assert len(note_requests) == 2, sent
        expect(page.locator(f'[data-testid="note-card-{victim}"]')).to_have_count(0)
        _assert_load_more_complete(page, before, {victim})
        assert before[40] in _card_ids(page)
    finally:
        page.request.post(f"{runtime_url}/api/notes/batch/delete", data={"note_ids": created})


def test_batch_delete_then_load_more_skips_nothing_and_keeps_scroll(app_page: Page, runtime_url: str):
    page = app_page
    created: list[int] = []
    try:
        created = _create_notes(page, runtime_url, 50)
        _open_two_pages(page)
        before = _server_order(page, runtime_url)
        shown = _card_ids(page)
        victims = {shown[37], shown[38]}  # below the viewport once we scroll back up
        for victim in victims:
            card = page.locator(f'[data-testid="note-card-{victim}"]')
            card.evaluate("el => el.scrollIntoView({ block: 'center' })")
            page.locator(f'[data-testid="note-card-select-{victim}"]').click()
        anchor = page.locator(f'[data-testid="note-card-{shown[29]}"]')
        anchor.evaluate("el => el.scrollIntoView({ block: 'start' })")
        scroll_before = page.evaluate("document.querySelector('main').scrollTop")
        assert scroll_before > 1000, scroll_before

        def delete():
            page.get_by_role("button", name="Delete", exact=True).first.click()
            _confirm(page)

        sent = _delete_and_wait(page, delete)
        print("OPT-69 requests after batch delete:", sent)
        scroll_after = page.evaluate("document.querySelector('main').scrollTop")
        assert abs(scroll_after - scroll_before) < 60, f"scroll jumped from {scroll_before} to {scroll_after}"
        _assert_load_more_complete(page, before, victims)
    finally:
        page.request.post(f"{runtime_url}/api/notes/batch/delete", data={"note_ids": created})


def test_delete_parent_updates_variant_card_lineage(app_page: Page, runtime_url: str):
    page = app_page
    created: list[int] = []
    try:
        root = page.request.post(
            f"{runtime_url}/api/notes", data={"title": "根筆記OPT69", "content": "變體鏈的根。"}
        ).json()["data"]["note_id"]
        created.append(root)
        ids = [root]
        for title in ("子筆記OPT69", "孫筆記OPT69"):
            result = page.request.post(f"{runtime_url}/api/notes/{ids[-1]}/duplicate", data={"as_variant": True})
            assert result.ok, result.text()
            ids.append(result.json()["data"]["note_id"])
            created.append(ids[-1])
            renamed = page.request.put(f"{runtime_url}/api/notes/{ids[-1]}", data={"title": title, "content": "變體。"})
            assert renamed.ok, renamed.text()
        root, child, grand = ids
        page.evaluate("() => { localStorage.setItem('prism.viewMode', 'compact') }")
        page.reload()
        grand_card = page.locator(f'[data-testid="note-card-{grand}"]')
        expect(grand_card).to_have_count(1)
        assert "子筆記OPT69" in grand_card.text_content()

        def delete_card(note_id: int):
            page.locator(f'[data-testid="note-card-actions-{note_id}"]').click()
            page.get_by_role("menu").get_by_role("button", name="Delete", exact=True).click()
            _confirm(page)

        # Delete the middle generation: the grandchild now hangs under the root.
        with page.expect_response(lambda r: _list_page(r, 1)):
            delete_card(child)
        expect(page.locator(f'[data-testid="note-card-{child}"]')).to_have_count(0)
        expect(grand_card).to_contain_text("根筆記OPT69")
        assert "子筆記OPT69" not in grand_card.text_content(), grand_card.text_content()
        root_card = page.locator(f'[data-testid="note-card-{root}"]')
        expect(root_card).to_contain_text("1 variants")

        # Delete the root: the grandchild is a root note now, so no lineage and no stale title.
        with page.expect_response(lambda r: _list_page(r, 1)):
            delete_card(root)
        expect(page.locator(f'[data-testid="note-card-{root}"]')).to_have_count(0)
        expect(grand_card).to_have_count(1)
        assert "根筆記OPT69" not in grand_card.text_content(), grand_card.text_content()
    finally:
        page.request.post(f"{runtime_url}/api/notes/batch/delete", data={"note_ids": created})
