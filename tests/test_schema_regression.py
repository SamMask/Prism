# -*- coding: utf-8 -*-
"""
Schema Regression Test (10.13)

Ensures that the temp_db fixture produced by conftest.py (which now runs the real
migration chain) matches the authoritative final schema defined in migrations/__init__.py.

If a column is accidentally re-added, or a DROP COLUMN migration is skipped, this
test will catch it.  Add this to CI so the problem surfaces before it reaches prod.
"""

import sqlite3
import tempfile
import os
import pytest


def _get_table_columns(conn: sqlite3.Connection, table: str) -> set:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def _get_tables(conn: sqlite3.Connection) -> set:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return {row[0] for row in cursor.fetchall()}


def _get_column_default(conn: sqlite3.Connection, table: str, column: str) -> str | None:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    for row in cursor.fetchall():
        if row[1] == column:
            return row[4]
    return None


def _build_migrated_db() -> sqlite3.Connection:
    """Create a fresh in-memory DB and run the full migration chain."""
    conn = sqlite3.connect(':memory:')

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
        INSERT OR IGNORE INTO Categories (name, icon, is_default)
        VALUES ('筆記', '📝', 1);
    ''')
    conn.commit()

    from migrations import run_migrations
    run_migrations(conn)
    return conn


def test_init_db_editor_layout_default_is_single(tmp_path):
    """Fresh init_db() databases must use the current editor_layout default."""
    from app import create_app, init_db

    db_path = tmp_path / 'fresh.db'
    flask_app = create_app('testing')
    flask_app.config['DATABASE'] = str(db_path)

    with flask_app.app_context():
        init_db()
        conn = sqlite3.connect(db_path)
        try:
            default = _get_column_default(conn, 'Notes', 'editor_layout')
            assert default == "'single'"
            assert default != "'full'"
        finally:
            conn.close()


def test_notes_type_column_absent():
    """Notes.type must be gone after migration v12 (kill_notes_type)."""
    conn = _build_migrated_db()
    cols = _get_table_columns(conn, 'Notes')
    assert 'type' not in cols, (
        "Notes.type column still exists — migration v12 (kill_notes_type) may have failed. "
        "This column was the root cause of 10.1 / 10.2."
    )
    conn.close()


def test_notes_required_columns_present():
    """Core columns added by migrations must all be present."""
    conn = _build_migrated_db()
    cols = _get_table_columns(conn, 'Notes')
    required = {
        'id', 'title', 'content', 'remarks', 'cover_image',
        'cover_position', 'editor_layout', 'is_pinned', 'is_archived',
        'sort_order', 'category_id', 'prompt_params', 'parent_id',
        'created_at', 'updated_at',
    }
    missing = required - cols
    assert not missing, f"Notes is missing columns after migrations: {missing}"
    conn.close()


def test_editor_layout_legacy_values_normalized():
    """Migration v16 normalizes legacy editor_layout values without rebuilding Notes."""
    conn = sqlite3.connect(':memory:')
    conn.executescript('''
        CREATE TABLE Notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            editor_layout TEXT DEFAULT 'full'
        );
        CREATE TABLE Schema_Meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT INTO Schema_Meta (key, value) VALUES ('schema_version', '15');
        INSERT INTO Notes (title, content, editor_layout) VALUES ('legacy full', 'body', 'full');
        INSERT INTO Notes (title, content, editor_layout) VALUES ('legacy null', 'body', NULL);
        INSERT INTO Notes (title, content, editor_layout) VALUES ('valid dual', 'body', 'dual');
    ''')

    from migrations import run_migrations
    run_migrations(conn)

    values = [row[0] for row in conn.execute('SELECT editor_layout FROM Notes ORDER BY id')]
    version = conn.execute("SELECT value FROM Schema_Meta WHERE key = 'schema_version'").fetchone()[0]

    assert values == ['single', 'single', 'dual']
    assert 'full' not in values
    assert version == '16'
    conn.close()


def test_ai_columns_stripped():
    """AI columns removed in migration v14 must not exist."""
    conn = _build_migrated_db()
    cols = _get_table_columns(conn, 'Notes')
    dead = {'text_embedding', 'embedding_updated_at', 'ai_summary', 'ai_tags',
            'embedding_status'}
    present = dead & cols
    assert not present, f"Stripped AI columns still present in Notes: {present}"
    conn.close()


def test_fixture_schema_matches_migration(temp_db):
    """temp_db fixture must produce the same Notes columns as the migration chain."""
    ref_conn = _build_migrated_db()
    ref_cols = _get_table_columns(ref_conn, 'Notes')
    ref_conn.close()

    fix_conn = sqlite3.connect(temp_db)
    fix_cols = _get_table_columns(fix_conn, 'Notes')
    fix_conn.close()

    assert fix_cols == ref_cols, (
        f"temp_db schema diverges from migration output.\n"
        f"  Extra in fixture : {fix_cols - ref_cols}\n"
        f"  Missing in fixture: {ref_cols - fix_cols}"
    )
