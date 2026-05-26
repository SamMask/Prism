# -*- coding: utf-8 -*-
"""
Prism V2 - Test Configuration (conftest.py)
Phase 6.1: Automated Testing Infrastructure

Provides:
- Flask test client fixture
- Temporary SQLite database for isolation
- Common test utilities
"""

import os
import sys
import pytest
import tempfile
import sqlite3

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='function')
def app_with_db(temp_db):
    """
    Create Flask application with isolated temp database for each test.
    This replaces the session-scoped app fixture.
    """
    from app import create_app
    
    flask_app = create_app('testing')
    
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': temp_db,  # Point to the temp SQLite file
        'WTF_CSRF_ENABLED': False,
        'PROPAGATE_EXCEPTIONS': True
    })
    
    # Ensure app context is pushed for g.db to work properly
    with flask_app.app_context():
        yield flask_app


@pytest.fixture(scope='function')
def client(app_with_db):
    """Create test client for each test function"""
    return app_with_db.test_client()


@pytest.fixture(scope='function')
def app(app_with_db):
    """Alias for app_with_db for backwards compatibility"""
    return app_with_db


@pytest.fixture(scope='function')
def temp_db():
    """
    Create a temporary SQLite database for isolated testing.

    Uses the real migration chain (migrations.run_migrations) so that schema
    regressions — like re-introducing a dropped column — are caught by tests.
    Each test function gets a fresh database; the file is deleted afterwards.
    """
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(db_path)

    # Minimal pre-migration base schema (the state before any migration runs).
    # Migrations will add/transform columns from here to the current version.
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT DEFAULT '📝',
            sort_order INTEGER DEFAULT 0,
            is_default INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS Notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            type TEXT DEFAULT '筆記',
            remarks TEXT,
            cover_image TEXT,
            prompt_params TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS Tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS Note_Tags (
            note_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (note_id, tag_id)
        );

        CREATE TABLE IF NOT EXISTS Source_Urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER,
            url TEXT
        );

        CREATE TABLE IF NOT EXISTS Note_History (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER,
            content TEXT,
            diff_summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS Notes_FTS USING fts5(
            title, content,
            content='Notes',
            content_rowid='id'
        );

        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON Notes BEGIN
            INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON Notes BEGIN
            INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
        END;
        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON Notes BEGIN
            INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
            INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
        END;

        -- Default category required for migration 7 (populate_category_id)
        INSERT OR IGNORE INTO Categories (name, icon, is_default)
        VALUES ('筆記', '📝', 1);
    ''')
    conn.commit()

    # Walk the real migration chain — this is the whole point of the fixture.
    # Any schema regression (e.g. re-adding a dropped column) will surface here.
    from migrations import run_migrations
    run_migrations(conn)

    # Seed minimal test data (after migrations; 'type' column is gone)
    conn.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('Welcome')")
    conn.execute(
        "INSERT INTO Notes (title, content, category_id) "
        "VALUES ('Welcome Note', 'Welcome to Prism!', "
        "(SELECT id FROM Categories WHERE is_default = 1 LIMIT 1))"
    )
    conn.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (1, 1)")
    conn.commit()
    conn.close()

    yield db_path

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope='function')
def sample_note_data():
    """Sample note data for testing"""
    return {
        'title': 'Test Note',
        'content': 'This is test content for unit testing.',
        'tags': ['test', 'automation'],
        'urls': ['https://example.com']
    }


@pytest.fixture(scope='function')
def sample_category_data():
    """Sample category data for testing"""
    return {
        'name': 'Test Category',
        'icon': '🧪'
    }
