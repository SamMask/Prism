# -*- coding: utf-8 -*-
"""
Search helpers for Prism notes.

The SQLite FTS table indexes note title/content. Attachments are stored as
text files, so attachment body search is handled as a small read-only pass and
merged back into the SQL query by note id.
"""

from pathlib import Path
from typing import Iterable, List, Optional

from .query_builder import tokenize_search_terms


TEXT_ATTACHMENT_TYPES = {'md', 'markdown', 'txt'}


def find_attachment_content_note_ids(db, keyword: str, root_path: str) -> List[int]:
    """Return note ids whose text attachment file content matches all tokens."""
    tokens = tokenize_search_terms(keyword)
    if not tokens:
        return []

    root = Path(root_path).resolve()
    note_ids = set()

    rows = db.execute(
        """
        SELECT note_id, file_path, file_type
        FROM Note_Attachments
        WHERE LOWER(COALESCE(file_type, '')) IN ('md', 'markdown', 'txt')
        """
    ).fetchall()

    for row in rows:
        file_path = _resolve_relative_file(root, row['file_path'])
        if not file_path:
            continue

        content = _read_text_file(file_path)
        if content and _contains_all_tokens(content.lower(), tokens):
            note_ids.add(row['note_id'])

    return sorted(note_ids)


def _resolve_relative_file(root: Path, relative_path: str) -> Optional[Path]:
    if not relative_path:
        return None

    candidate = (root / relative_path).resolve()
    if not _is_relative_to(candidate, root):
        return None
    if not candidate.is_file():
        return None

    return candidate


def _is_relative_to(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return ''


def _contains_all_tokens(text: str, tokens: Iterable[str]) -> bool:
    return all(token in text for token in tokens)
