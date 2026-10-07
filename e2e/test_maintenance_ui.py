"""PRISM-OPT-81: maintenance actions that only existed as APIs now have UI entry points.

Settings > Maintenance: compact database, clear all version history (confirm first, optional restore point).
Multi-select toolbar (More menu): batch category, batch tags, export selected notes.
Test data is CJK on purpose; notes and the category are removed afterwards so the shared isolated
runtime stays as the other e2e files expect.
"""

import io
import zipfile

from playwright.sync_api import Page, expect

PREFIX = "管理功能 OPT81"
MAINTENANCE = "/settings?tab=maintenance"


def _create_note(page: Page, base: str, title: str, content: str = "第一版內容") -> int:
    response = page.request.post(f"{base}/api/notes", data={"title": title, "content": content})
    assert response.status == 201, response.text()
    return response.json()["data"]["note_id"]


def _delete_notes(page: Page, base: str, ids: list[int]) -> None:
    for note_id in ids:
        page.request.delete(f"{base}/api/notes/{note_id}")


def _history(page: Page, base: str, note_id: int) -> list:
    response = page.request.get(f"{base}/api/notes/{note_id}/history")
    assert response.ok, response.text()
    return response.json()["data"]["history"]


def _backup_names(page: Page, base: str) -> set[str]:
    data = page.request.get(f"{base}/api/server/backup/list").json()["data"]
    return {item["filename"] for item in data["backups"]}


def _select(page: Page, ids: list[int]) -> None:
    for note_id in ids:
        page.locator(f'[data-testid="note-card-select-{note_id}"]').click()


def _open_library(page: Page, base: str) -> None:
    page.goto(base)
    page.locator('[data-testid="notes-grid"]').wait_for(state="visible", timeout=15_000)


def _footer_total(page: Page) -> str:
    return page.locator("footer").inner_text()


def _cleanup_category(page: Page, base: str, category_id: int) -> None:
    page.request.delete(f"{base}/api/categories/{category_id}")


def test_vacuum_button_calls_api_once_and_shows_result(app_page: Page, runtime_url: str):
    page = app_page
    calls: list[str] = []
    page.on("request", lambda r: calls.append(r.url) if r.url.endswith("/api/system/vacuum") else None)

    page.goto(f"{runtime_url}{MAINTENANCE}")
    button = page.locator('[data-testid="vacuum-button"]')
    expect(button).to_be_visible()
    button.click()

    expect(page.locator('[data-testid="vacuum-result"]')).to_contain_text("KB")
    expect(button).to_be_enabled()
    assert len(calls) == 1, calls


def test_clear_history_cancel_keeps_history_and_confirm_clears_with_restore_point(app_page: Page, runtime_url: str):
    page = app_page
    note_id = _create_note(page, runtime_url, f"{PREFIX} 歷史筆記")
    try:
        for version in ("第二版內容", "第三版內容"):
            response = page.request.put(
                f"{runtime_url}/api/notes/{note_id}", data={"title": f"{PREFIX} 歷史筆記", "content": version}
            )
            assert response.ok, response.text()
        assert len(_history(page, runtime_url, note_id)) == 2

        calls: list[str] = []
        page.on("request", lambda r: calls.append(r.url) if r.url.endswith("/api/system/clear-history") else None)
        page.goto(f"{runtime_url}{MAINTENANCE}")

        # Cancel: nothing is sent and the history stays.
        page.locator('[data-testid="clear-history-button"]').click()
        dialog = page.get_by_role("alertdialog")
        expect(dialog).to_contain_text("cannot be undone")
        expect(dialog).to_contain_text("restore point")
        dialog.get_by_role("button", name="Cancel").click()
        expect(dialog).to_have_count(0)
        assert calls == []
        assert len(_history(page, runtime_url, note_id)) == 2

        # Confirm with the default "create a restore point first": one more restore point, history gone.
        expect(page.locator('[data-testid="clear-history-snapshot"]')).to_be_checked()
        before = _backup_names(page, runtime_url)
        page.locator('[data-testid="clear-history-button"]').click()
        page.get_by_role("alertdialog").get_by_role("button", name="Clear history").click()
        expect(page.get_by_text("Cleared")).to_be_visible()
        assert len(calls) == 1, calls
        assert _history(page, runtime_url, note_id) == []
        assert _backup_names(page, runtime_url) - before, "a new restore point should exist"
    finally:
        _delete_notes(page, runtime_url, [note_id])


def test_batch_change_category_updates_list_in_place(app_page: Page, runtime_url: str):
    page = app_page
    category = page.request.post(f"{runtime_url}/api/categories", data={"name": f"{PREFIX} 分類"})
    assert category.status == 201, category.text()
    category_id = category.json()["data"]["id"]
    ids = [_create_note(page, runtime_url, f"{PREFIX} 改分類{n}") for n in (1, 2)]
    try:
        _open_library(page, runtime_url)
        cards_before = page.locator('[data-testid="notes-grid"] > [data-testid^="note-card-"]').count()
        total_before = _footer_total(page)
        _select(page, ids)

        page.locator('[data-testid="selection-more-menu"]').click()
        page.locator('[data-testid="selection-change-category"]').click()
        page.locator('[data-testid="batch-category-select"]').select_option(str(category_id))
        with page.expect_response(lambda r: r.url.endswith("/api/notes/batch/type")) as batch:
            page.locator('[data-testid="batch-category-apply"]').click()
        assert batch.value.ok

        expect(page.locator('[data-testid="selection-more-menu"]')).to_have_count(0)  # selection cleared
        for note_id in ids:
            note = page.request.get(f"{runtime_url}/api/notes/{note_id}").json()["data"]
            assert note["category_id"] == category_id
        assert page.locator('[data-testid="notes-grid"] > [data-testid^="note-card-"]').count() == cards_before
        assert _footer_total(page) == total_before
    finally:
        _delete_notes(page, runtime_url, ids)
        _cleanup_category(page, runtime_url, category_id)


def test_batch_add_tags_reads_back_cjk_tags(app_page: Page, runtime_url: str):
    page = app_page
    ids = [_create_note(page, runtime_url, f"{PREFIX} 加標籤{n}") for n in (1, 2)]
    try:
        _open_library(page, runtime_url)
        _select(page, ids)
        page.locator('[data-testid="selection-more-menu"]').click()
        page.locator('[data-testid="selection-edit-tags"]').click()
        page.locator('[data-testid="batch-tags-input"]').fill("批次標籤甲，批次標籤乙")
        with page.expect_response(lambda r: r.url.endswith("/api/notes/batch/tags")) as batch:
            page.locator('[data-testid="batch-tags-apply"]').click()
        assert batch.value.ok

        expect(page.locator('[data-testid="selection-more-menu"]')).to_have_count(0)
        for note_id in ids:
            note = page.request.get(f"{runtime_url}/api/notes/{note_id}").json()["data"]
            names = {tag["name"] for tag in note["tags"]}
            assert {"批次標籤甲", "批次標籤乙"} <= names, names
    finally:
        _delete_notes(page, runtime_url, ids)


def test_export_selected_notes_downloads_zip_with_titles(app_page: Page, runtime_url: str, tmp_path):
    page = app_page
    titles = [f"{PREFIX} 匯出{n}" for n in (1, 2)]
    ids = [_create_note(page, runtime_url, title, f"{title} 的內文") for title in titles]
    try:
        _open_library(page, runtime_url)
        _select(page, ids)
        page.locator('[data-testid="selection-more-menu"]').click()
        with page.expect_download() as download_info:
            page.locator('[data-testid="selection-export"]').click()
        target = tmp_path / "export.zip"
        download_info.value.save_as(target)

        assert target.stat().st_size > 0
        with zipfile.ZipFile(io.BytesIO(target.read_bytes())) as archive:
            text = "\n".join(archive.read(name).decode("utf-8") for name in archive.namelist() if name.endswith(".md"))
        for title in titles:
            assert title in text
    finally:
        _delete_notes(page, runtime_url, ids)


def test_selection_toolbar_fits_390px(browser, runtime_url: str):
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="en-US")
    page = context.new_page()
    note_id = _create_note(page, runtime_url, f"{PREFIX} 手機選取")
    try:
        _open_library(page, runtime_url)
        _select(page, [note_id])
        more = page.locator('[data-testid="selection-more-menu"]')
        expect(more).to_be_visible()

        def assert_fits() -> None:
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            for locator in (page.locator("header button:visible"), page.get_by_role("menu").locator("button")):
                for box in locator.evaluate_all("els => els.map(el => el.getBoundingClientRect().toJSON())"):
                    assert box["left"] >= 0 and box["right"] <= 390, box

        assert_fits()
        more.click()
        expect(page.get_by_role("menu").get_by_role("menuitem")).to_have_count(3)
        assert_fits()
        page.keyboard.press("Escape")
        expect(page.get_by_role("menu")).to_have_count(0)
        expect(more).to_be_focused()
    finally:
        _delete_notes(page, runtime_url, [note_id])
        context.close()
