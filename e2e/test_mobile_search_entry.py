"""PRISM-OPT-53: mobile search entry on non-Library pages (390px)."""

import json
from urllib.request import Request, urlopen

import pytest
from playwright.sync_api import expect

KEYWORD = "行動搜尋入口錨點"


@pytest.fixture(scope="module", autouse=True)
def _seed_cjk_note(runtime_url: str):
    payload = json.dumps({"title": KEYWORD, "content": "手機版從設定頁開始搜尋"}).encode("utf-8")
    req = Request(f"{runtime_url}/api/notes", data=payload,
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=5) as response:
        assert response.status == 201


@pytest.mark.parametrize("path", ["/settings", "/prompt-builder"])
def test_mobile_search_icon_returns_to_library_and_focuses_input(browser, runtime_url: str, path: str):
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="en-US")
    page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    try:
        page.goto(runtime_url + path)
        button = page.get_by_test_id("mobile-search-entry")
        expect(button).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        button.click()
        expect(page).to_have_url(runtime_url + "/")
        search = page.get_by_test_id("mobile-search-input")
        expect(search).to_be_focused()
        page.keyboard.type(KEYWORD)
        page.keyboard.press("Enter")
        expect(page.get_by_test_id("notes-grid").get_by_text(KEYWORD).first).to_be_visible()
        assert errors == []
    finally:
        context.close()


def test_desktop_hides_mobile_search_entry(browser, runtime_url: str):
    context = browser.new_context(viewport={"width": 1280, "height": 800}, locale="en-US")
    page = context.new_page()
    try:
        page.goto(runtime_url + "/settings")
        expect(page.get_by_test_id("search-input")).to_be_visible()
        expect(page.get_by_test_id("mobile-search-entry")).to_be_hidden()
    finally:
        context.close()
