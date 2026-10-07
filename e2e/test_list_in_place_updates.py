"""PRISM-OPT-32: mutations update the Home list in place instead of resetting it to page 1.

Loads three pages (60 cards), works on the 45th card and checks the list keeps its loaded pages
and scroll position after Save, Ctrl+S, pin, archive, create variant and history restore. A new
search must still start again from page 1. Test data is CJK on purpose and is deleted afterwards
so the shared isolated runtime stays as the other e2e files expect.
"""

import re
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, expect

PREFIX = "就地更新筆記 OPT32"
GRID_CARDS = '[data-testid="notes-grid"] > [data-testid^="note-card-"]'
LIST_SPINNER = "main > div > svg.animate-spin"


def _is_first_list_page(response) -> bool:
    url = urlparse(response.url)
    return (
        response.request.method == "GET"
        and url.path == "/api/notes"
        and parse_qs(url.query).get("page") == ["1"]
    )


def _mutate(page: Page, action) -> None:
    """Run a UI mutation and wait until the list has finished re-reading the server."""
    with page.expect_response(_is_first_list_page):
        action()
    expect(page.locator(LIST_SPINNER)).to_have_count(0)


def _scroll_top(page: Page) -> float:
    return page.evaluate("document.querySelector('main').scrollTop")


def _card_45(page: Page):
    card = page.locator(GRID_CARDS).nth(44)
    note_id = int(card.get_attribute("data-testid").rsplit("-", 1)[1])
    card.evaluate("el => el.scrollIntoView({ block: 'start' })")
    before = _scroll_top(page)
    assert before > 1000, f"card 45 should sit deep in the list, scrollTop={before}"
    return card, note_id, before


def _assert_list_kept(page: Page, before: float) -> None:
    count = page.locator(GRID_CARDS).count()
    assert count >= 60, f"list was reset: {count} cards left"
    after = _scroll_top(page)
    assert abs(after - before) < 60, f"scroll jumped from {before} to {after}"


def _library_total(page: Page) -> int:
    footer = page.locator("footer")
    expect(footer).to_contain_text(re.compile(r"\d+ notes"))
    return int(re.search(r"([\d,]+) notes", footer.inner_text()).group(1).replace(",", ""))


def _menu_action(page: Page, note_id: int, label: str) -> None:
    page.locator(f'[data-testid="note-card-actions-{note_id}"]').click()
    page.get_by_role("menu").get_by_role("button", name=label, exact=True).click()


def test_mutations_keep_loaded_pages_and_scroll_position(app_page: Page, runtime_url: str):
    page = app_page
    created: list[int] = []
    try:
        for n in range(1, 73):
            response = page.request.post(
                f"{runtime_url}/api/notes",
                data={"title": f"{PREFIX} 第{n:02d}篇", "content": f"第{n:02d}篇：測試存檔後列表不跳回頂端。"},
            )
            assert response.status == 201, response.text()
            created.append(response.json()["data"]["note_id"])

        page.evaluate(
            """() => {
                localStorage.setItem('cardOpenMode', 'edit')
                localStorage.setItem('prism.viewMode', 'compact')
                localStorage.setItem('autoLoadMore', 'false')
            }"""
        )
        page.reload()
        cards = page.locator(GRID_CARDS)
        expect(cards).to_have_count(20)
        for expected in (40, 60):
            page.get_by_text("Click to load more").click()
            expect(cards).to_have_count(expected)
        editor = page.locator('[data-testid="note-editor"]')

        # Save button: saves and closes; the list keeps 3 pages and its scroll position.
        card, note_id, before = _card_45(page)
        card.locator("h3").click()
        expect(editor).to_be_visible()
        editor.get_by_placeholder("Title", exact=True).fill(f"{PREFIX} 按鈕存檔")
        _mutate(page, lambda: editor.get_by_role("button", name="Save", exact=True).click())
        expect(editor).to_have_count(0)
        _assert_list_kept(page, before)
        expect(page.locator(f'[data-testid="note-card-{note_id}"] h3')).to_have_text(f"{PREFIX} 按鈕存檔")

        # Ctrl+S: saves and stays in the editor (PRISM-OPT-21); the list behind it is not reset.
        card, note_id, before = _card_45(page)
        card.locator("h3").click()
        expect(editor).to_be_visible()
        editor.get_by_placeholder("Title", exact=True).fill(f"{PREFIX} 快捷鍵存檔")
        _mutate(page, lambda: page.keyboard.press("Control+s"))
        expect(editor).to_be_visible()
        _assert_list_kept(page, before)
        expect(page.locator(f'[data-testid="note-card-{note_id}"] h3')).to_have_text(f"{PREFIX} 快捷鍵存檔")
        page.keyboard.press("Escape")
        expect(editor).to_have_count(0)
        _assert_list_kept(page, before)

        # Pin: the note joins the pinned group at the top without a reset.
        card, note_id, before = _card_45(page)
        _mutate(page, lambda: _menu_action(page, note_id, "Pin"))
        _assert_list_kept(page, before)
        expect(page.locator(f'[data-testid="note-card-{note_id}"] svg.lucide-pin')).to_have_count(1)
        pinned_flags = cards.evaluate_all("els => els.map(el => !!el.querySelector('svg.lucide-pin'))")
        ids = cards.evaluate_all("els => els.map(el => el.dataset.testid)")
        position = ids.index(f"note-card-{note_id}")
        assert all(pinned_flags[: position + 1]), "pinned note must sit inside the pinned group at the top"

        # Archive: the note leaves the list in place and the Library total drops by one.
        total = _library_total(page)
        card, note_id, before = _card_45(page)
        _mutate(page, lambda: _menu_action(page, note_id, "Archive"))
        expect(page.locator(f'[data-testid="note-card-{note_id}"]')).to_have_count(0)
        _assert_list_kept(page, before)
        expect(page.locator("footer")).to_contain_text(f"{total - 1} notes")

        # Create variant: the new note shows up, the list is not reset, the Library total grows.
        total = _library_total(page)
        card, note_id, before = _card_45(page)
        _mutate(page, lambda: _menu_action(page, note_id, "Create variant"))
        variants = page.request.get(f"{runtime_url}/api/notes", params={"parent_id": note_id}).json()["data"]
        assert len(variants) == 1, variants
        created.append(variants[0]["id"])
        expect(page.locator(f'[data-testid="note-card-{variants[0]["id"]}"]')).to_have_count(1)
        _assert_list_kept(page, before)
        expect(page.locator("footer")).to_contain_text(f"{total + 1} notes")

        # History restore: give card 45 a history version, restore it from the editor.
        card, note_id, before = _card_45(page)
        note = page.request.get(f"{runtime_url}/api/notes/{note_id}").json()["data"]
        updated = page.request.put(
            f"{runtime_url}/api/notes/{note_id}",
            data={"title": note["title"], "content": "改過的內容，之後要還原。"},
        )
        assert updated.ok, updated.text()
        card.locator("h3").click()
        expect(editor).to_be_visible()
        editor.get_by_role("button", name=re.compile("History")).click()
        page.get_by_role("button", name="Restore", exact=True).first.click()
        _mutate(page, lambda: page.get_by_role("alertdialog").get_by_role("button", name="Confirm").click())
        _assert_list_kept(page, before)
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('[data-testid=note-editor]') || document.querySelector('[role=alertdialog]')"
        )
        if page.get_by_role("alertdialog").count():
            page.get_by_role("alertdialog").get_by_role("button", name="Discard changes").click()
        expect(editor).to_have_count(0)
        _assert_list_kept(page, before)

        # A new search still starts from page 1.
        search = page.locator('[data-testid="search-input"]')
        search.fill("就地更新筆記")
        with page.expect_response(_is_first_list_page):
            search.press("Enter")
        expect(cards).to_have_count(20)
        expect(page.get_by_text("Click to load more")).to_be_visible()
    finally:
        if created:
            page.request.post(f"{runtime_url}/api/notes/batch/delete", data={"note_ids": created})
