
import pytest
from utils.query_builder import (
    NoteQueryBuilder,
    sanitize_fts_query,
    tokenize_search_terms,
)


def test_tokenize_search_terms_splits_filename_punctuation():
    """Filename-like queries should remain searchable as separate terms."""
    assert tokenize_search_terms("todo.md") == ["todo", "md"]
    assert tokenize_search_terms("foo-bar") == ["foo", "bar"]

def test_sanitize_fts_query_basic():
    """Test basic FTS query logic"""
    assert sanitize_fts_query("hello") == '"hello"*'
    assert sanitize_fts_query("hello world") == '"hello"* "world"*'
    assert sanitize_fts_query("foo-bar") == '"foo"* "bar"*'
    assert sanitize_fts_query("todo.md") == '"todo"* "md"*'
    assert sanitize_fts_query("") == ""
    assert sanitize_fts_query("   ") == ""

def test_sanitize_fts_query_max_tokens():
    """Test max_tokens limit preventing DoS"""
    # Create a long query string
    long_query = "a " * 30
    
    # Default limit is 20
    sanitized = sanitize_fts_query(long_query)
    assert len(sanitized.split()) == 20
    
    # Custom limit
    sanitized_custom = sanitize_fts_query(long_query, max_tokens=5)
    assert len(sanitized_custom.split()) == 5
    assert sanitized_custom == '"a"* "a"* "a"* "a"* "a"*'

def test_builder_filter_category():
    builder = NoteQueryBuilder()
    builder.filter_category(10)
    sql, params = builder.build()
    
    assert "n.category_id = ?" in sql
    assert params == [10]

def test_builder_filter_tags_and():
    builder = NoteQueryBuilder()
    builder.filter_tags([1, 2], mode='AND')
    sql, params = builder.build()
    
    # Should have two EXISTS clauses for AND mode
    assert sql.count("EXISTS (SELECT 1 FROM Note_Tags") == 2
    assert params == [1, 2]

def test_builder_filter_tags_or():
    builder = NoteQueryBuilder()
    builder.filter_tags([1, 2], mode='OR')
    sql, params = builder.build()
    
    # Should have one EXISTS clause with IN for OR mode
    assert "nt.tag_id IN (?,?)" in sql
    assert params == [1, 2]

def test_builder_filter_archived():
    builder = NoteQueryBuilder()
    
    # Default (include_archived=False) -> show checks for IS NULL OR 0
    builder.filter_archived(False)
    sql, _ = builder.build()
    assert "(n.is_archived IS NULL OR n.is_archived = 0)" in sql

def test_builder_search_fts():
    builder = NoteQueryBuilder()
    builder.search_fts("hello world")
    sql, params = builder.build()
    
    assert "n.id IN (SELECT rowid FROM Notes_FTS WHERE Notes_FTS MATCH ?)" in sql
    # It should use sanitize_fts_query internally
    assert params == ['"hello"* "world"*']

def test_builder_filter_pinned():
    builder = NoteQueryBuilder()
    builder.filter_pinned(True)
    sql, _ = builder.build()
    assert "n.is_pinned = 1" in sql

def test_builder_chaining():
    """Test method chaining works"""
    builder = NoteQueryBuilder()
    sql, params = builder.filter_category(1).filter_pinned(True).build()
    
    assert "n.category_id = ?" in sql
    assert "n.is_pinned = 1" in sql
    assert params == [1]
