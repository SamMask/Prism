"""PRISM-OPT-65: JSON import tells the user when separated notes / uploads were not fully restored."""

import base64
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _payload(tag: str, *, separated: int = 0, uploads: list[str] | None = None) -> dict:
    notes = [{"id": 1, "title": f"{tag} 匯入筆記", "content": f"{tag} 中文內容"}]
    attachments = []
    for index in range(separated):
        notes.append({"id": 10 + index, "title": f"{tag} 拆分筆記{index}", "content": "預覽內容\n\n..."})
        attachments.append({
            "note_id": 10 + index,
            "file_path": f"docs/notes/note_{900 + index}.md",
            "is_auto_extracted": True,
        })
    data = {"notes": notes, "attachments": attachments}
    if uploads:
        data["uploads"] = [{"filename": name, "content_b64": _b64("圖片位元組")} for name in uploads]
    return data


def _import(browser, runtime_url: str, tmp_path: Path, width: int, data: dict):
    context = browser.new_context(viewport={"width": width, "height": 900}, locale="en-US")
    page = context.new_page()
    page.goto(f"{runtime_url}/settings?tab=backup")
    page.locator('[data-testid="settings-page"]').wait_for(state="visible", timeout=15_000)
    source = tmp_path / f"import_{width}.json"
    source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    page.locator('input[type="file"][accept=".json"]').set_input_files(str(source))
    page.get_by_role("button", name="Start import").click()
    return context, page


@pytest.mark.parametrize("width", [1280, 390])
def test_separated_note_import_shows_preview_only_notice(browser, runtime_url: str, tmp_path, width: int):
    context, page = _import(browser, runtime_url, tmp_path, width, _payload(f"w{width}sep", separated=2))
    try:
        notice = page.locator('[data-testid="import-lossy-notice"]')
        expect(notice).to_be_visible()
        expect(page.locator('[data-testid="import-notice-attachments"]')).to_contain_text("2 separated long note(s)")
        expect(page.locator('[data-testid="import-notice-attachments"]')).to_contain_text("Full snapshot")
        expect(page.locator('[data-testid="import-notice-uploads"]')).to_have_count(0)
    finally:
        context.close()


@pytest.mark.parametrize("width", [1280, 390])
def test_plain_import_shows_no_notice(browser, runtime_url: str, tmp_path, width: int):
    context, page = _import(browser, runtime_url, tmp_path, width, _payload(f"w{width}plain"))
    try:
        expect(page.get_by_text("Imported 1 notes")).to_be_visible()
        expect(page.locator('[data-testid="import-lossy-notice"]')).to_have_count(0)
    finally:
        context.close()


def test_existing_upload_name_import_shows_notice(browser, runtime_url: str, tmp_path):
    name = "opt65封面圖.png"
    first, first_page = _import(browser, runtime_url, tmp_path, 1280, _payload("up1", uploads=[name]))
    try:
        expect(first_page.get_by_text("Imported 1 notes")).to_be_visible()
        expect(first_page.locator('[data-testid="import-lossy-notice"]')).to_have_count(0)
    finally:
        first.close()
    context, page = _import(browser, runtime_url, tmp_path, 390, _payload("up2", uploads=[name]))
    try:
        expect(page.locator('[data-testid="import-notice-uploads"]')).to_contain_text("1 image(s)")
        expect(page.locator('[data-testid="import-notice-attachments"]')).to_have_count(0)
    finally:
        context.close()
