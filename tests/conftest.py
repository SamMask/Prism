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
    
    Each test function gets a fresh database.
    The database is deleted after the test completes.
    """
    # Create temp file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Initialize with basic schema
    conn = sqlite3.connect(db_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            icon TEXT DEFAULT '📝',
            sort_order INTEGER DEFAULT 0,
            is_default INTEGER DEFAULT 0,
            is_system INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS Notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            type TEXT DEFAULT '筆記',
            category_id INTEGER,
            remarks TEXT,
            cover_image TEXT,
            cover_position TEXT DEFAULT 'top',
            editor_layout TEXT DEFAULT 'single',
            prompt_params TEXT,
            is_pinned INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0,
            parent_id INTEGER,
            ai_summary TEXT,
            ai_tags TEXT,
            embedding_status TEXT,
            text_embedding BLOB,
            sort_order INTEGER DEFAULT 0,
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
        
        CREATE TABLE IF NOT EXISTS Embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_type TEXT NOT NULL,
            resource_id INTEGER NOT NULL,
            chunk_index INTEGER DEFAULT 0,
            model_name TEXT NOT NULL,
            vector BLOB NOT NULL,
            content_hash TEXT,
            dimensions INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(resource_type, resource_id, chunk_index)
        );
        
        -- FTS5 Full-Text Search (required for search tests)
        CREATE VIRTUAL TABLE IF NOT EXISTS Notes_FTS USING fts5(
            title, content,
            content='Notes',
            content_rowid='id'
        );
        
        -- FTS Triggers
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
        
        -- Insert default category
        INSERT OR IGNORE INTO Categories (name, icon, is_default, is_system)
        VALUES ('筆記', '📝', 1, 1);
        
        -- Insert default tag
        INSERT OR IGNORE INTO Tags (name) VALUES ('Welcome');
        
        -- Insert a Welcome note that uses the Welcome tag (for test_tags_filter)
        INSERT INTO Notes (title, content, type) VALUES ('Welcome Note', 'Welcome to Prism!', '筆記');
        INSERT INTO Note_Tags (note_id, tag_id) VALUES (1, 1);
    ''')
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
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
        'type': '筆記',
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
