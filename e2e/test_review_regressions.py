"""PRISM-OPT-26: browser guards for bugs found in the 2026-10-06 review.

Each test drives the isolated Go primary runtime from e2e/conftest.py. The source-lock tests in
tests/ stay as fast guards; these prove the behavior (OPT-16 attachment popup, OPT-17 header
New/search off Home, OPT-18 CJK search and palette threshold, OPT-19 long note stays inline and
shortened split note, OPT-21 Ctrl+S). Test data is CJK on purpose.
"""

import time

from playwright.sync_api import Page, expect

CJK_TITLE = "旅行紀錄 OPT26"
CJK_CONTENT = "昨天晚上在山上看台北夜景，風很大但非常漂亮。"
CJK_QUERY = "夜景"  # two CJK chars in the middle of a sentence


def _create_note(page: Page, runtime_url: str, title: str, content: str) -> int:
    created = page.request.post(f"{runtime_url}/api/notes", data={"title": title, "content": content})
    assert created.status == 201, created.text()
    return created.json()["data"]["note_id"]


def _ensure_cjk_note(page: Page, runtime_url: str) -> int:
    found = page.request.get(f"{runtime_url}/api/notes", params={"q": CJK_TITLE, "per_page": 5})
    for note in found.json()["data"]:
        if note["title"] == CJK_TITLE:
            return note["id"]
    return _create_note(page, runtime_url, CJK_TITLE, CJK_CONTENT)


def _notes_titled(page: Page, runtime_url: str, title: str) -> list[dict]:
    found = page.request.get(f"{runtime_url}/api/notes", params={"q": title, "per_page": 20})
    return [note for note in found.json()["data"] if note["title"] == title]


def _wait_until(check, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value or time.monotonic() > deadline:
            return value
        time.sleep(0.2)


def _open_in_editor(page: Page, title: str):
    page.evaluate("localStorage.setItem('cardOpenMode', 'edit')")
    page.reload()
    search = page.locator('[data-testid="search-input"]')
    search.fill(title)
    search.press("Enter")
    page.get_by_role("heading", name=title).click()
    editor = page.locator('[data-testid="note-editor"]')
    expect(editor).to_be_visible()
    return editor


def test_header_new_from_settings_opens_editor_in_library(page: Page, runtime_url: str):
    page.goto(f"{runtime_url}/settings")
    page.locator('[data-testid="add-note-button"]').click()
    expect(page.locator('[data-testid="note-editor"]')).to_be_visible(timeout=10_000)
    assert page.evaluate("location.pathname") == "/"


def test_header_cjk_search_from_prompt_builder_finds_mid_sentence_word(page: Page, runtime_url: str):
    _ensure_cjk_note(page, runtime_url)
    page.goto(f"{runtime_url}/prompt-builder")
    expect(page.locator('[data-testid="prompt-builder-page"]')).to_be_visible(timeout=15_000)
    search = page.locator('[data-testid="search-input"]')
    search.fill(CJK_QUERY)
    search.press("Enter")
    expect(page.get_by_role("heading", name=CJK_TITLE)).to_be_visible(timeout=10_000)
    expect(page.get_by_role("heading", name="E2E Search Anchor")).to_have_count(0)
    assert page.evaluate("location.pathname") == "/"


def test_command_palette_queries_server_after_two_cjk_chars(app_page: Page, runtime_url: str):
    note_id = _ensure_cjk_note(app_page, runtime_url)
    app_page.keyboard.press("Control+k")
    palette_input = app_page.locator('[data-testid="command-palette-input"]')
    expect(palette_input).to_be_focused()
    palette_input.fill(CJK_QUERY)
    expect(app_page.locator('[data-testid="command-palette-server-search-status"]')).to_be_visible()
    expect(app_page.locator(f'[data-testid="command-item-search-note-{note_id}"]')).to_be_visible(timeout=10_000)


def test_ctrl_s_saves_new_note_keeps_editor_open_and_updates_same_note(app_page: Page, runtime_url: str):
    title = "Ctrl+S 存檔 OPT26"
    app_page.locator('[data-testid="add-note-button"]').click()
    editor = app_page.locator('[data-testid="note-editor"]')
    expect(editor).to_be_visible()
    editor.get_by_placeholder("Title", exact=True).fill(title)
    textarea = editor.locator("textarea").first
    textarea.fill("第一版內容")
    app_page.keyboard.press("Control+s")
    assert _wait_until(lambda: _notes_titled(app_page, runtime_url, title)), "Ctrl+S did not create the note"
    expect(editor).to_be_visible()

    textarea.fill("第二版內容")
    app_page.keyboard.press("Control+s")

    def saved_second_version():
        notes = _notes_titled(app_page, runtime_url, title)
        return len(notes) == 1 and "第二版內容" in notes[0]["content"]

    assert _wait_until(saved_second_version), _notes_titled(app_page, runtime_url, title)
    expect(editor).to_be_visible()


def test_text_attachment_popup_shows_markup_as_text(app_page: Page, runtime_url: str):
    title = "附件 popup OPT26"
    note_id = _create_note(app_page, runtime_url, title, "附件測試")
    payload = "</pre><img src=x onerror=\"document.title='PWNED'\"><b id=\"injected\">粗體</b> 純文字"
    uploaded = app_page.request.post(
        f"{runtime_url}/api/notes/{note_id}/attachments",
        multipart={"file": {"name": "payload.txt", "mimeType": "text/plain", "buffer": payload.encode("utf-8")}},
    )
    assert uploaded.ok, uploaded.text()
    attachment_id = uploaded.json()["data"]["id"]

    editor = _open_in_editor(app_page, title)
    item = editor.locator(f'[data-testid="attachment-item-{attachment_id}"]')
    with app_page.expect_popup() as popup_info:
        item.get_by_role("button").first.click()
    popup = popup_info.value
    expect(popup.locator("pre")).to_have_text(payload)
    expect(popup.locator("img")).to_have_count(0)
    expect(popup.locator("#injected")).to_have_count(0)
    assert popup.title() != "PWNED"
    popup.close()


def test_saving_a_long_note_keeps_the_full_text_in_the_note(app_page: Page, runtime_url: str):
    title = "長文存檔 OPT26"
    long_content = ("今天整理長文存檔的步驟，確認不會再被拆成附件。" * 300) + "尾段關鍵字 tailopt26"
    app_page.locator('[data-testid="add-note-button"]').click()
    editor = app_page.locator('[data-testid="note-editor"]')
    editor.get_by_placeholder("Title", exact=True).fill(title)
    editor.locator("textarea").first.fill(long_content)
    app_page.keyboard.press("Control+s")
    notes = _wait_until(lambda: _notes_titled(app_page, runtime_url, title))
    assert notes, "Ctrl+S did not create the long note"
    note_id = notes[0]["id"]
    assert app_page.request.get(f"{runtime_url}/api/notes/{note_id}").json()["data"]["content"] == long_content
    assert app_page.request.get(f"{runtime_url}/api/notes/{note_id}/attachments").json()["data"] == []


def test_shortened_split_note_keeps_the_new_text_after_reopen(app_page: Page, runtime_url: str):
    title = "長文縮短 OPT26"
    long_content = "長文開頭。" + ("這是一段很長的中文內容，用來觸發舊的自動分離。" * 300) + "尾段關鍵字"
    note_id = _create_note(app_page, runtime_url, title, long_content)
    separated = app_page.request.post(f"{runtime_url}/api/notes/{note_id}/separate", data={})
    assert separated.ok, separated.text()

    editor = _open_in_editor(app_page, title)
    textarea = editor.locator("textarea").first
    expect(textarea).to_have_value(long_content)
    textarea.fill("縮短後的新內容")
    app_page.keyboard.press("Control+s")

    def saved_short():
        note = app_page.request.get(f"{runtime_url}/api/notes/{note_id}").json()["data"]
        return note["content"] == "縮短後的新內容"

    assert _wait_until(saved_short), "shortened content was not saved"
    attachments = app_page.request.get(f"{runtime_url}/api/notes/{note_id}/attachments").json()["data"]
    assert not [att for att in attachments if att["is_auto_extracted"]]

    app_page.keyboard.press("Escape")
    expect(editor).to_have_count(0)
    editor = _open_in_editor(app_page, title)
    expect(editor.locator("textarea").first).to_have_value("縮短後的新內容")
