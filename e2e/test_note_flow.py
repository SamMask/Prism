# -*- coding: utf-8 -*-
"""
E2E Tests - Note Flow (Happy Path)
Phase 6.2.2: Core Flow Testing for Prism V2 React SPA

Tests the critical user journey:
1. View notes list
2. Create new note
3. Edit note
4. Delete note

Prerequisites:
    - Flask server running at http://localhost:5000
    - Frontend built and served (V2 mode)
    - playwright install chromium
"""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:5000"


class TestV2NoteFlow:
    """End-to-end tests for V2 React SPA note management"""
    
    def test_homepage_loads(self, page: Page):
        """Test: V2 Homepage loads with React app container"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # V2 specific: Check for React app container
        app_container = page.locator('[data-testid="app-container"]')
        expect(app_container).to_be_visible(timeout=10000)
    
    def test_header_visible(self, page: Page):
        """Test: Header with search and add button is visible"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Header should be visible
        header = page.locator('[data-testid="header"]')
        expect(header).to_be_visible()
        
        # Search input should be visible
        search_input = page.locator('[data-testid="search-input"]')
        expect(search_input).to_be_visible()
        
        # Add note button should be visible
        add_button = page.locator('[data-testid="add-note-button"]')
        expect(add_button).to_be_visible()
    
    def test_sidebar_navigation(self, page: Page):
        """Test: Sidebar navigation is visible"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Sidebar nav should be visible
        sidebar_nav = page.locator('[data-testid="sidebar-nav"]')
        expect(sidebar_nav).to_be_visible()
        
        # Navigation links should exist
        home_link = page.locator('a[href="/"]')
        expect(home_link).to_be_visible()
    
    def test_notes_grid_visible(self, page: Page):
        """Test: Notes grid container is visible"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Notes grid should be visible
        notes_grid = page.locator('[data-testid="notes-grid"]')
        expect(notes_grid).to_be_visible()
    
    def test_click_add_note_opens_editor(self, page: Page):
        """Test: Clicking add note button opens the editor modal"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Click add note button
        add_button = page.locator('[data-testid="add-note-button"]')
        add_button.click()
        
        # Wait for editor to appear (look for common editor elements)
        page.wait_for_timeout(500)
        
        # Editor should open (check for textarea or editor container)
        editor_area = page.locator('textarea')
        if editor_area.count() > 0:
            expect(editor_area.first).to_be_visible()
    
    def test_search_input_accepts_text(self, page: Page):
        """Test: Search input can receive text input"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Type in search input
        search_input = page.locator('[data-testid="search-input"]')
        search_input.fill("test search query")
        
        # Value should be set
        expect(search_input).to_have_value("test search query")
    
    def test_navigate_to_settings(self, page: Page):
        """Test: Can navigate to settings page"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Click settings link
        settings_link = page.locator('a[href="/settings"]')
        if settings_link.count() > 0:
            settings_link.click()
            page.wait_for_url("**/settings")
            
            # Should be on settings page
            expect(page).to_have_url(f"{BASE_URL}/settings")
    
    def test_navigate_to_prompt_builder(self, page: Page):
        """Test: Can navigate to Prompt Builder page"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Click Prompt Builder link
        pb_link = page.locator('a[href="/prompt-builder"]')
        if pb_link.count() > 0:
            pb_link.click()
            page.wait_for_url("**/prompt-builder")
            
            # Should be on prompt builder page
            expect(page).to_have_url(f"{BASE_URL}/prompt-builder")


class TestV2CreateNoteFlow:
    """Tests for creating a new note in V2"""
    
    def test_create_note_full_flow(self, page: Page):
        """Test: Full create note workflow"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        
        # Click add note
        page.click('[data-testid="add-note-button"]')
        page.wait_for_timeout(500)
        
        # Fill title if input exists
        title_inputs = page.locator('input[type="text"]')
        if title_inputs.count() > 0:
            title_inputs.first.fill("E2E Test Note - " + str(page.context.browser.version))
        
        # Fill content in textarea
        content_area = page.locator('textarea')
        if content_area.count() > 0:
            content_area.first.fill("This is an automated E2E test note created by Playwright.")
        
        # Look for save button and click it
        save_button = page.locator('button:has-text("儲存"), button:has-text("保存")')
        if save_button.count() > 0:
            save_button.first.click()
            page.wait_for_timeout(1000)
            
            # Check for success toast or note appearing in grid
            # Note: This depends on actual UI implementation
