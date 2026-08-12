"""Current product browser smoke against an isolated Go primary runtime."""

from playwright.sync_api import Page, expect


def test_home_loads(app_page: Page):
    expect(app_page.locator('[data-testid="app-container"]')).to_be_visible()
    expect(app_page.locator('[data-testid="notes-grid"]')).to_be_visible()


def test_home_search_and_open_note(app_page: Page, runtime_url: str):
    search = app_page.locator('[data-testid="search-input"]')
    search.fill("E2E Search Anchor")
    search.press("Enter")
    card = app_page.get_by_role("heading", name="E2E Search Anchor")
    expect(card).to_be_visible()
    card.click()
    expect(app_page.locator('[data-testid="note-editor"]')).to_be_visible()
    app_page.goto(runtime_url)
    app_page.get_by_role("button", name="Sort notes").click()
    app_page.get_by_role("button", name="Custom order").click()
    expect(app_page.locator('[data-testid="custom-reorder-disabled-reason"]')).to_be_visible()


def test_prompt_builder_direct_load(page: Page, runtime_url: str):
    page.goto(f"{runtime_url}/prompt-builder")
    expect(page.locator('[data-testid="prompt-builder-page"]')).to_be_visible(timeout=15_000)
    expect(page.locator('[data-testid="filter-strip"]')).to_have_count(0)


def test_prompt_save_and_open_note(page: Page, runtime_url: str):
    page.goto(f"{runtime_url}/prompt-builder")
    controls = page.locator('[data-testid="prompt-builder-controls"]')
    expect(controls).to_be_visible(timeout=15_000)
    controls.locator("textarea").first.fill("E2E Prompt Continuation")
    page.get_by_role("button", name="Save to note library").click()
    page.get_by_role("button", name="Open note").click()
    expect(page.locator('[data-testid="reading-view"]')).to_be_visible(timeout=10_000)


def test_data_recovery_direct_load(page: Page, runtime_url: str, tmp_path):
    page.goto(f"{runtime_url}/settings?tab=backup")
    expect(page.locator('[data-testid="data-recovery-section"]')).to_be_visible(timeout=15_000)
    expect(page.locator('[data-testid="full-data-snapshot-export"]')).to_be_visible()
    expect(page.locator('[data-testid="filter-strip"]')).to_have_count(0)
    page.screenshot(path=str(tmp_path / "data-recovery-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.reload()
    expect(page.locator('[data-testid="data-recovery-section"]')).to_be_visible(timeout=15_000)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(tmp_path / "data-recovery-390.png"), full_page=True)
