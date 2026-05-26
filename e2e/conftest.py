# -*- coding: utf-8 -*-
"""
Prism V2 - E2E Test Configuration (Playwright)
Phase 6.2: Frontend E2E Testing

Usage:
    pytest e2e/ -v --headed  # 有頭模式 (可視化)
    pytest e2e/ -v           # 無頭模式 (CI/CD)

Prerequisites:
    pip install pytest-playwright
    playwright install
"""

import pytest
from playwright.sync_api import Page


# Base URL for the application
BASE_URL = "http://localhost:5000"


@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser context"""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="function")
def app_page(page: Page):
    """
    Navigate to app and wait for initial load.
    
    This fixture provides a page that's already navigated to the app.
    """
    page.goto(BASE_URL)
    
    # Wait for React to hydrate (look for main content)
    page.wait_for_selector('[data-testid="app-container"]', timeout=10000)
    
    yield page


@pytest.fixture(scope="function")
def logged_in_page(page: Page):
    """
    Provide a page with any authentication setup.
    
    For Prism (no auth), this is same as app_page.
    Can be extended if auth is added later.
    """
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    
    yield page


# Helper functions for common actions
def wait_for_toast(page: Page, text: str, timeout: int = 5000):
    """Wait for a toast notification with specific text"""
    toast = page.locator(f'text="{text}"')
    toast.wait_for(state="visible", timeout=timeout)
    return toast


def click_and_wait(page: Page, selector: str, wait_selector: str = None):
    """Click an element and optionally wait for another"""
    page.click(selector)
    if wait_selector:
        page.wait_for_selector(wait_selector)
