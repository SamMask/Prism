"""PRISM-OPT-30: mobile sort control and first-screen density (390px)."""

from playwright.sync_api import Page, expect


def _open_mobile(browser, runtime_url: str, width: int = 390):
    context = browser.new_context(viewport={"width": width, "height": 844}, locale="en-US")
    page = context.new_page()
    page.goto(runtime_url)
    page.locator('[data-testid="notes-grid"]').wait_for(state="visible", timeout=15_000)
    return context, page


def test_mobile_sort_menu_changes_sort_and_escape_closes(browser, runtime_url: str):
    context, page = _open_mobile(browser, runtime_url)
    try:
        button = page.get_by_role("button", name="Sort notes")
        expect(button).to_be_visible()
        for label, sort in (("Created", "created"), ("Custom", "custom"), ("Updated", "updated")):
            button.click()
            with page.expect_request(lambda r: "/api/notes" in r.url and f"sort={sort}" in r.url):
                page.get_by_role("menuitemradio", name=label).click()
            button.click()
            expect(page.get_by_role("menuitemradio", name=label)).to_have_attribute("aria-checked", "true")
            page.keyboard.press("Escape")
            expect(page.get_by_role("menu")).to_have_count(0)
            expect(button).to_be_focused()
        button.click()
        page.get_by_role("menuitemradio", name="Created").focus()
        page.keyboard.press("Enter")
        expect(page.get_by_role("menu")).to_have_count(0)
        expect(button).to_be_focused()
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    finally:
        context.close()


def test_mobile_default_list_shows_two_full_cards_and_respects_saved_mode(browser, runtime_url: str):
    context, page = _open_mobile(browser, runtime_url, 375)
    try:
        grid = page.locator('[data-testid="notes-grid"]')
        assert grid.get_attribute("data-view-mode") == "list"
        visible = page.evaluate(
            """() => [...document.querySelector('[data-testid=notes-grid]').children]
                 .filter(c => { const r = c.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight }).length"""
        )
        assert visible >= 2
        page.evaluate("localStorage.setItem('prism.viewMode', 'grid')")
        page.reload()
        expect(page.locator('[data-testid="notes-grid"]')).to_have_attribute("data-view-mode", "grid")
    finally:
        context.close()


def test_escape_with_sort_menu_open_keeps_focus_in_the_top_dialog(browser, runtime_url: str):
    """Closing the sort menu must not pull focus out of a dialog opened on top (PRISM-OPT-62)."""
    context, page = _open_mobile(browser, runtime_url)
    try:
        page.get_by_role("button", name="Sort notes").click()
        expect(page.get_by_role("menu")).to_be_visible()
        page.keyboard.press("Control+k")
        page.get_by_test_id("command-palette-input").fill("New note")
        page.keyboard.press("Enter")
        editor = page.get_by_role("dialog")
        expect(editor).to_be_visible()
        page.keyboard.type("未存的內容")
        page.keyboard.press("Escape")
        confirm = page.get_by_role("alertdialog")
        expect(confirm).to_be_visible()
        assert page.evaluate(
            "document.querySelector('[role=alertdialog]').contains(document.activeElement)"
        ), "focus must stay inside the unsaved-changes confirm"
        expect(page.get_by_role("menu")).to_have_count(0)
    finally:
        context.close()
