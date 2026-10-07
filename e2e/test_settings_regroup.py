"""PRISM-OPT-34: Settings regroup, tab aliases, and image settings under Maintenance."""

from playwright.sync_api import expect


def _open(browser, runtime_url: str, path: str, width: int = 1280):
    context = browser.new_context(viewport={"width": width, "height": 900}, locale="en-US")
    page = context.new_page()
    page.goto(f"{runtime_url}{path}")
    page.locator('[data-testid="settings-page"]').wait_for(state="visible", timeout=15_000)
    return context, page


def test_data_alias_lands_on_backup_panel_and_old_ids_still_work(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, "/settings?tab=data")
    try:
        expect(page.locator('[data-testid="settings-panel-backup"]')).to_be_visible()
        expect(page.locator('[data-testid="settings-tab-backup"]')).to_have_attribute("aria-selected", "true")
        for tab in ("appearance", "organization", "backup", "maintenance", "access", "about"):
            page.goto(f"{runtime_url}/settings?tab={tab}")
            expect(page.locator(f'[data-testid="settings-panel-{tab}"]')).to_be_visible()
        page.goto(f"{runtime_url}/settings?tab=bogus")
        expect(page.locator('[data-testid="settings-panel-appearance"]')).to_be_visible()
    finally:
        context.close()


def test_image_settings_live_under_maintenance_images_storage(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, "/settings?tab=maintenance")
    try:
        panel = page.locator('[data-testid="settings-images-storage"]')
        expect(panel).to_be_visible()
        expect(panel.get_by_role("heading", name="Images & storage")).to_be_visible()
        expect(panel.locator('[data-testid="image-save-mode-select"]')).to_be_visible()
        expect(panel.get_by_text("Clean unused images")).to_be_visible()
        expect(panel.get_by_text("Delete originals (keep thumbnails)")).to_be_visible()
        expect(panel.get_by_text("Fix broken image paths")).to_be_visible()
        assert panel.get_by_role("button", name="Scan").count() == 3
        # They no longer live under Appearance or Access.
        page.goto(f"{runtime_url}/settings?tab=access")
        expect(page.locator('[data-testid="settings-panel-access"]')).to_be_visible()
        expect(page.locator('[data-testid="orphan-image-cleanup-description"]')).to_have_count(0)
        page.goto(f"{runtime_url}/settings?tab=appearance")
        expect(page.locator('[data-testid="image-save-mode-select"]')).to_have_count(0)
    finally:
        context.close()


def test_image_save_mode_persists_after_reload(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, "/settings?tab=maintenance")
    try:
        select = page.locator('[data-testid="image-save-mode-select"]')
        select.select_option("thumbnail_only")
        expect(select).to_have_value("thumbnail_only")
        assert page.evaluate("localStorage.getItem('imageSaveMode')") == "thumbnail_only"
        page.reload()
        expect(page.locator('[data-testid="image-save-mode-select"]')).to_have_value("thumbnail_only")
    finally:
        context.close()


def test_appearance_library_editor_group_has_moved_settings(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, "/settings?tab=appearance")
    try:
        heading = page.locator('[data-testid="appearance-group-library-editor"]')
        expect(heading).to_have_text("Library & editor")
        expect(page.locator('[data-testid="appearance-group-display"]')).to_have_text("Display")
        panel = page.locator('[data-testid="settings-panel-appearance"]')
        for label in ("Card open mode", "Quick add default category", "Auto load more"):
            expect(panel.get_by_text(label, exact=False).first).to_be_visible()
        # The group heading sits above all three settings.
        top = heading.bounding_box()["y"]
        for label in ("Card open mode", "Quick add default category", "Auto load more"):
            assert panel.get_by_text(label, exact=False).first.bounding_box()["y"] > top
    finally:
        context.close()


def test_settings_have_no_horizontal_overflow_at_390(browser, runtime_url: str):
    context, page = _open(browser, runtime_url, "/settings?tab=maintenance", width=390)
    try:
        for tab in ("maintenance", "appearance", "access", "backup"):
            page.goto(f"{runtime_url}/settings?tab={tab}")
            expect(page.locator(f'[data-testid="settings-panel-{tab}"]')).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), tab
    finally:
        context.close()
