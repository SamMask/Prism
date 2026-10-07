"""PRISM-OPT-33: Library navigation shows each category / title / count once."""

import json
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from playwright.sync_api import expect

CATEGORY = "導覽去重分類"
TAG = "非星標標籤"


def _ensure_category(runtime_url: str) -> None:
    request = Request(
        f"{runtime_url}/api/categories",
        data=json.dumps({"name": CATEGORY, "icon": "📚"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urlopen(request, timeout=5).close()
    except HTTPError as error:
        if error.code != 409:  # already created by an earlier test
            raise


_tagged_note_created = False


def _ensure_tagged_note(runtime_url: str) -> None:
    """Tags are created through notes; this one is never starred."""
    global _tagged_note_created
    if _tagged_note_created:
        return
    request = Request(
        f"{runtime_url}/api/notes",
        data=json.dumps({"title": "E2E Tagged 標籤筆記", "content": "tag fixture", "tags": [TAG]}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urlopen(request, timeout=5).close()
    _tagged_note_created = True


def _open(browser, runtime_url: str, width: int):
    _ensure_category(runtime_url)
    _ensure_tagged_note(runtime_url)
    context = browser.new_context(viewport={"width": width, "height": 900}, locale="en-US")
    page = context.new_page()
    page.goto(runtime_url)
    page.locator('[data-testid="notes-grid"]').wait_for(state="visible", timeout=15_000)
    return context, page


def test_desktop_categories_only_in_sidebar(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, 1280)
    try:
        strip = page.get_by_test_id("filter-strip")
        expect(strip.get_by_test_id("filter-archive")).to_be_visible()
        expect(strip.get_by_test_id("filter-all")).to_be_hidden()
        assert strip.get_by_text(CATEGORY).locator("visible=true").count() == 0
        assert page.get_by_text(CATEGORY).locator("visible=true").count() == 1  # Sidebar only
        # Selecting it shows one clearable chip in the strip; the all-categories chips stay hidden.
        page.get_by_text(CATEGORY).locator("visible=true").first.click()
        chip = strip.get_by_test_id("filter-active-category")
        expect(chip).to_be_visible()
        chip.click()
        expect(chip).to_have_count(0)
    finally:
        context.close()


def test_mobile_strip_keeps_category_chips(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, 390)
    try:
        strip = page.get_by_test_id("filter-strip")
        expect(strip.get_by_test_id("filter-all")).to_be_visible()
        expect(strip.get_by_text(CATEGORY)).to_be_visible()
    finally:
        context.close()


def test_home_title_and_count_not_duplicated(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, 1280)
    try:
        expect(page.get_by_role("heading", level=1)).to_have_count(1)
        header_text = page.get_by_test_id("header").inner_text()
        assert not re.search(r"\d+\s+items", header_text), header_text
        assert "All" not in header_text.split()
    finally:
        context.close()


def test_collapsed_sidebar_brings_category_chips_back_on_desktop(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, 1280)
    try:
        strip = page.get_by_test_id("filter-strip")
        expect(strip.get_by_test_id("filter-all")).to_be_hidden()
        page.get_by_role("button", name="Collapse sidebar").click()
        expect(strip.get_by_test_id("filter-all")).to_be_visible()
        chip = strip.get_by_text(CATEGORY)
        expect(chip).to_be_visible()
        chip.click()
        expect(page.get_by_role("heading", level=1)).to_have_text(CATEGORY)
        expect(strip.get_by_test_id("filter-active-category")).to_have_count(0)
    finally:
        context.close()


def test_desktop_search_plus_unstarred_tag_shows_active_tag_chip(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, 1280)
    try:
        page.get_by_test_id("search-input").fill("E2E")
        page.keyboard.press("Enter")
        page.get_by_role("button", name=f"#{TAG}").click()
        chip = page.get_by_test_id("filter-strip").get_by_test_id("filter-active-tag")
        expect(chip).to_be_visible()
        expect(chip).to_contain_text(TAG)
        expect(chip).to_have_attribute("aria-label", f"Clear tag filter: {TAG}")
        chip.click()
        expect(chip).to_have_count(0)
    finally:
        context.close()
