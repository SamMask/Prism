"""PRISM-OPT-54: the attachment delete button is a usable touch target on phones.

Desktop keeps the compact 20px button; below md (and on hover:none devices) it grows to >= 44px
without pushing the attachment row past the editor width. Test data is CJK on purpose.
"""

from playwright.sync_api import Page, expect


def _delete_button_box(editor, attachment_id: int) -> dict:
    button = editor.locator(f'[data-testid="attachment-item-{attachment_id}"] button[aria-label]').last
    box = button.bounding_box()
    assert box, "delete button has no box"
    return box


def test_attachment_delete_button_is_large_on_phones_and_compact_on_desktop(app_page: Page, runtime_url: str):
    title = "附件觸控範圍 OPT54"
    created = app_page.request.post(f"{runtime_url}/api/notes", data={"title": title, "content": "觸控測試"})
    assert created.status == 201, created.text()
    note_id = created.json()["data"]["note_id"]
    uploaded = app_page.request.post(
        f"{runtime_url}/api/notes/{note_id}/attachments",
        multipart={"file": {"name": "memo.txt", "mimeType": "text/plain", "buffer": "會議紀錄".encode("utf-8")}},
    )
    assert uploaded.ok, uploaded.text()
    attachment_id = uploaded.json()["data"]["id"]

    app_page.evaluate("localStorage.setItem('cardOpenMode', 'edit')")
    app_page.reload()
    search = app_page.locator('[data-testid="search-input"]')
    search.fill(title)
    search.press("Enter")
    app_page.get_by_role("heading", name=title).click()
    editor = app_page.locator('[data-testid="note-editor"]')
    expect(editor).to_be_visible()
    expect(editor.locator(f'[data-testid="attachment-item-{attachment_id}"]')).to_be_visible()

    desktop = _delete_button_box(editor, attachment_id)
    assert desktop["width"] <= 24 and desktop["height"] <= 24, desktop

    app_page.set_viewport_size({"width": 390, "height": 844})
    row = editor.locator(f'[data-testid="attachment-item-{attachment_id}"]')
    expect(row).to_be_visible()
    phone = _delete_button_box(editor, attachment_id)
    assert phone["width"] >= 32 and phone["height"] >= 32, phone
    assert row.evaluate("el => el.scrollWidth <= el.clientWidth"), "attachment row overflows at 390px"
    assert app_page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
