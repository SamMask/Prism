"""PRISM-OPT-62: dialogs are real modal dialogs (role, focus trap, topmost-only Escape, focus return)."""

import re
import struct
import zlib

from playwright.sync_api import Page, expect

INSIDE_TOPMOST = """() => {
  const d = [...document.querySelectorAll('[role="dialog"],[role="alertdialog"]')].pop()
  return !!d && d.contains(document.activeElement)
}"""


def _open_anchor(page: Page):
    # Search first: the anchor must not depend on Home's first page, which other e2e files fill up.
    search = page.locator('[data-testid="search-input"]')
    search.fill("E2E Search Anchor")
    search.press("Enter")
    page.get_by_role("heading", name="E2E Search Anchor").click()


def _open_dirty_editor(page: Page):
    page.evaluate("localStorage.setItem('cardOpenMode', 'edit')")
    page.reload()
    _open_anchor(page)
    editor = page.locator('[data-testid="note-editor"]')
    expect(editor).to_be_visible()
    textarea = editor.locator("textarea").first
    textarea.click()
    textarea.type(" 草稿 dirty")
    return textarea


def test_editor_is_modal_and_tab_never_reaches_background(app_page: Page):
    _open_anchor(app_page)
    dialog = app_page.get_by_role("dialog")
    expect(dialog).to_have_attribute("aria-modal", "true")
    expect(dialog).to_have_attribute("aria-labelledby", re.compile(r".+"))
    for key in ("Tab", "Shift+Tab"):
        for _ in range(30):
            app_page.keyboard.press(key)
            assert app_page.evaluate(INSIDE_TOPMOST), f"{key} left the editor dialog"


def test_escape_on_confirm_only_cancels_the_confirm(app_page: Page):
    textarea = _open_dirty_editor(app_page)
    app_page.keyboard.press("Escape")
    confirm = app_page.get_by_role("alertdialog")
    expect(confirm).to_have_count(1)
    assert app_page.evaluate(INSIDE_TOPMOST)
    for _ in range(10):
        app_page.keyboard.press("Tab")
        assert app_page.evaluate(INSIDE_TOPMOST), "Tab left the confirm"
    app_page.keyboard.press("Escape")
    expect(confirm).to_have_count(0)
    expect(app_page.locator('[data-testid="note-editor"]')).to_be_visible()
    assert "dirty" in textarea.input_value()


def test_focus_returns_to_opener_on_close(app_page: Page):
    button = app_page.locator('[data-testid="add-note-button"]')
    button.focus()
    app_page.keyboard.press("Enter")
    expect(app_page.locator('[data-testid="note-editor"]')).to_be_visible()
    app_page.keyboard.press("Escape")
    expect(app_page.locator('[data-testid="note-editor"]')).to_have_count(0)
    expect(button).to_be_focused()


def _png(size: int = 16) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    rows = b"".join(bytes([0]) + bytes([64, 128, 192]) * size for _ in range(size))
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return bytes([137, 80, 78, 71, 13, 10, 26, 10]) + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def _note_with_image(page: Page, runtime_url: str) -> str:
    upload = page.request.post(
        f"{runtime_url}/api/upload",
        multipart={"file": {"name": "dot.png", "mimeType": "image/png", "buffer": _png()}},
    )
    assert upload.ok, upload.text()
    url = upload.json()["data"]["url"]
    title = "Lightbox 圖片 note"
    created = page.request.post(
        f"{runtime_url}/api/notes",
        data={"title": title, "content": f"![圖](<{url}>)\n\n內容"},
    )
    assert created.status == 201
    return title


def test_image_lightbox_over_reading_view_is_its_own_layer(app_page: Page, runtime_url: str):
    title = _note_with_image(app_page, runtime_url)
    app_page.reload()
    card = app_page.locator('[data-testid^="note-card-"]').filter(has_text=title).first
    card.locator('[data-testid^="note-card-actions-"]').click()
    app_page.get_by_role("button", name="Read", exact=True).click()
    expect(app_page.locator('[data-testid="reading-view"]')).to_be_visible()
    opener = app_page.locator('[data-testid="reading-view"] button[aria-label]').filter(
        has=app_page.locator('[data-testid="reading-cover-image"]')
    )
    opener.focus()
    app_page.keyboard.press("Enter")
    lightbox = app_page.locator('[data-testid="image-lightbox"]')
    expect(lightbox).to_be_visible()
    inside_lightbox = "() => document.querySelector('[data-testid=\"image-lightbox\"]').contains(document.activeElement)"
    assert app_page.evaluate(inside_lightbox)
    seen = set()
    for key in ("Tab", "Shift+Tab"):
        for _ in range(12):
            app_page.keyboard.press(key)
            assert app_page.evaluate(inside_lightbox), f"{key} left the lightbox"
            seen.add(app_page.evaluate("document.activeElement.getAttribute('aria-label')"))
    assert len(seen) >= 4  # zoom/copy/open/close controls are reachable
    app_page.keyboard.press("Escape")
    expect(lightbox).to_have_count(0)
    expect(app_page.locator('[data-testid="reading-view"]')).to_be_visible()
    expect(opener).to_be_focused()


def test_history_modal_close_keeps_focus_in_editor(app_page: Page, runtime_url: str):
    _open_anchor(app_page)
    editor = app_page.locator('[data-testid="note-editor"]')
    expect(editor).to_be_visible()
    app_page.get_by_role("button", name=re.compile("History")).click()
    expect(app_page.get_by_role("dialog")).to_have_count(2)
    app_page.keyboard.press("Escape")
    expect(app_page.get_by_role("dialog")).to_have_count(1)
    assert app_page.evaluate("document.querySelector('[data-testid=\"note-editor\"]').closest('[role=dialog]').contains(document.activeElement)")
