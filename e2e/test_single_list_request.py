"""PRISM-OPT-55: one /api/notes list request per search / filter action, from any page."""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from playwright.sync_api import expect

KEYWORD = "單次請求搜尋錨點"
CATEGORY = "單次請求分類"
LIST_URL = "/api/notes?"


def _post(runtime_url: str, path: str, payload: dict) -> dict:
    req = Request(runtime_url + path, data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=5) as response:
            return json.loads(response.read() or b"{}")
    except HTTPError as error:
        if error.code != 409:
            raise
        return {}


@pytest.fixture(scope="module", autouse=True)
def _seed(runtime_url: str):
    _post(runtime_url, "/api/categories", {"name": CATEGORY, "icon": "📚"})
    with urlopen(runtime_url + "/api/categories", timeout=5) as response:
        categories = json.loads(response.read())
    if isinstance(categories, dict):
        categories = next(v for v in categories.values() if isinstance(v, list))
    category_id = next(c["id"] for c in categories if c["name"] == CATEGORY)
    _post(runtime_url, "/api/notes", {"title": KEYWORD, "content": "從設定頁搜尋只送一次請求", "category_id": category_id})


@pytest.fixture()
def page(browser, runtime_url: str):
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="en-US")
    page = context.new_page()
    page.goto(runtime_url)
    page.get_by_test_id("notes-grid").wait_for(state="visible", timeout=15_000)
    yield page
    context.close()


def archive_button(page):
    return page.get_by_test_id("app-sidebar").get_by_role("button", name="Archive", exact=True)


def _count_list_requests(page, action, *, contains: str = "") -> int:
    urls: list[str] = []
    page.on("request", lambda r: urls.append(r.url) if LIST_URL in r.url else None)
    action()
    page.wait_for_load_state("networkidle")
    return len([u for u in urls if contains in u])


def _search(page, text: str):
    box = page.get_by_test_id("search-input")
    box.fill(text)
    box.press("Enter")


def test_search_on_library_sends_one_request(page):
    count = _count_list_requests(page, lambda: _search(page, KEYWORD), contains="q=")
    assert count == 1
    expect(page.get_by_test_id("notes-grid").get_by_text(KEYWORD).first).to_be_visible()


@pytest.mark.parametrize("path", ["/settings", "/prompt-builder"])
def test_search_from_other_page_sends_one_request(page, runtime_url: str, path: str):
    page.goto(runtime_url + path)
    expect(page.get_by_test_id("search-input")).to_be_visible()
    count = _count_list_requests(page, lambda: _search(page, KEYWORD), contains="q=")
    assert count == 1
    expect(page).to_have_url(runtime_url + "/")
    expect(page.get_by_test_id("notes-grid").get_by_text(KEYWORD).first).to_be_visible()


def test_sidebar_category_from_settings_sends_one_request(page, runtime_url: str):
    page.goto(runtime_url + "/settings")
    sidebar = page.get_by_test_id("app-sidebar")
    expect(sidebar.get_by_text(CATEGORY)).to_be_visible()
    count = _count_list_requests(page, lambda: sidebar.get_by_text(CATEGORY).click())
    assert count == 1
    expect(page).to_have_url(runtime_url + "/")
    expect(page.get_by_test_id("notes-grid").get_by_text(KEYWORD).first).to_be_visible()


def test_sidebar_archive_from_settings_sends_one_request(page, runtime_url: str):
    page.goto(runtime_url + "/settings")
    count = _count_list_requests(page, lambda: archive_button(page).click())
    assert count == 1
    expect(page).to_have_url(runtime_url + "/")


def test_library_filters_each_send_one_request(page):
    sidebar = page.get_by_test_id("app-sidebar")
    assert _count_list_requests(page, lambda: sidebar.get_by_text(CATEGORY).click()) == 1
    expect(page.get_by_test_id("notes-grid").get_by_text(KEYWORD).first).to_be_visible()

    assert _count_list_requests(page, lambda: archive_button(page).click(), contains="archived") == 1
    expect(page.get_by_test_id("notes-grid").get_by_text(KEYWORD)).to_have_count(0)

    assert _count_list_requests(page, lambda: archive_button(page).click()) == 1

    def sort():
        page.get_by_test_id("sort-menu-button").click()
        page.get_by_role("menuitemradio").nth(1).click()

    assert _count_list_requests(page, sort) == 1
