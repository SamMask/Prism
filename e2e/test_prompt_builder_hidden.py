"""PRISM-OPT-80: the built-in Prompt Builder has no navigation entry, but its route still works.

The user builds prompts in a separate tool, so the Sidebar link and the Command Palette command are
hidden. The /prompt-builder page and API stay so the entry can be restored without other changes.
"""

from playwright.sync_api import Page, expect


def test_prompt_builder_has_no_sidebar_or_palette_entry(app_page: Page):
    expect(app_page.locator('a[href="/prompt-builder"]')).to_have_count(0)

    app_page.keyboard.press("Control+k")
    palette_input = app_page.locator('[data-testid="command-palette-input"]')
    expect(palette_input).to_be_focused()
    expect(app_page.locator('[data-testid="command-item-nav-settings"]')).to_be_visible()
    expect(app_page.locator('[data-testid="command-item-nav-prompt-builder"]')).to_have_count(0)
    palette_input.fill("Prompt Builder")
    expect(app_page.locator('[data-testid="command-item-nav-prompt-builder"]')).to_have_count(0)


def test_prompt_builder_route_still_opens_by_url(page: Page, runtime_url: str):
    page.goto(f"{runtime_url}/prompt-builder")
    expect(page.locator('[data-testid="prompt-builder-page"]')).to_be_visible(timeout=15_000)
