# -*- coding: utf-8 -*-
"""
Tests for /api/export/markdown — Phase 15 (v2.4.7)
"""

import io
import json
import zipfile
from pathlib import Path

from db import get_db


def _seed_three_notes(app):
    """Insert 3 notes with category, tags, pinned/archived flags."""
    with app.app_context():
        db = get_db()
        # Reuse default category (id=1, 筆記); add a custom one
        cur = db.execute("INSERT INTO Categories (name, icon) VALUES ('Tech', '🔧')")
        tech_cat_id = cur.lastrowid

        # Tags
        cur = db.execute("INSERT INTO Tags (name) VALUES ('python')")
        tag_python = cur.lastrowid
        cur = db.execute("INSERT INTO Tags (name) VALUES ('flask')")
        tag_flask = cur.lastrowid

        # Note A: pinned, with 2 tags, in Tech
        cur = db.execute(
            "INSERT INTO Notes (title, content, category_id, is_pinned, remarks) "
            "VALUES ('Hello 世界', '# Heading\\n\\nBody **markdown** content.', ?, 1, 'note remark')",
            (tech_cat_id,),
        )
        note_a = cur.lastrowid
        db.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (note_a, tag_python))
        db.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (note_a, tag_flask))

        # Note B: archived, no tags, default category
        db.execute(
            "INSERT INTO Notes (title, content, category_id, is_archived) "
            "VALUES ('Archived Item', 'archived body', 1, 1)"
        )

        # Note C: empty title, no content (edge case)
        db.execute(
            "INSERT INTO Notes (title, content, category_id) VALUES ('', '', 1)"
        )
        db.commit()


def test_export_markdown_returns_zip(client, app):
    _seed_three_notes(app)
    resp = client.get('/api/export/markdown')

    assert resp.status_code == 200
    assert resp.mimetype == 'application/zip'
    assert 'attachment' in resp.headers['Content-Disposition']
    assert 'prism_markdown_' in resp.headers['Content-Disposition']

    # Open the zip
    zf = zipfile.ZipFile(io.BytesIO(resp.data))
    names = zf.namelist()

    # Welcome note from conftest + 3 seeded = 4 notes + 1 manifest
    md_files = [n for n in names if n.endswith('.md')]
    assert len(md_files) == 4
    assert '_manifest.json' in names


def test_export_markdown_frontmatter_fields(client, app):
    _seed_three_notes(app)
    resp = client.get('/api/export/markdown')
    zf = zipfile.ZipFile(io.BytesIO(resp.data))

    # Find Hello 世界 note (note_a, pinned, with tags + remarks)
    hello_files = [n for n in zf.namelist() if 'Hello' in n or '世界' in n]
    assert len(hello_files) == 1
    content = zf.read(hello_files[0]).decode('utf-8')

    # Frontmatter present
    assert content.startswith('---\n')
    assert '\n---\n' in content
    head, body = content.split('\n---\n', 1)

    # Required frontmatter fields
    assert 'id:' in head
    assert 'title: "Hello 世界"' in head
    assert 'category: "Tech"' in head
    assert 'is_pinned: True' in head
    assert 'is_archived: False' in head
    assert 'created_at:' in head
    assert 'updated_at:' in head
    assert 'remarks: "note remark"' in head

    # Tags array contains both
    assert '"python"' in head
    assert '"flask"' in head

    # Body content preserved (markdown intact)
    assert 'Heading' in body
    assert '**markdown**' in body


def test_export_markdown_manifest_count(client, app):
    _seed_three_notes(app)
    resp = client.get('/api/export/markdown')
    zf = zipfile.ZipFile(io.BytesIO(resp.data))

    manifest = json.loads(zf.read('_manifest.json').decode('utf-8'))
    assert manifest['export_info']['format'] == 'markdown'
    assert manifest['export_info']['notes_count'] == 4  # Welcome + 3 seeded
    assert 'exported_at' in manifest['export_info']


def test_export_markdown_handles_empty_title(client, app):
    _seed_three_notes(app)
    resp = client.get('/api/export/markdown')
    zf = zipfile.ZipFile(io.BytesIO(resp.data))

    # Note C has empty title — should still produce a file (slug → "untitled")
    untitled_files = [n for n in zf.namelist() if 'untitled' in n.lower()]
    assert len(untitled_files) == 1


def test_export_markdown_includes_local_upload_images(client, app, tmp_path):
    upload_dir = tmp_path / 'uploads'
    app.config['UPLOAD_FOLDER'] = str(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = upload_dir / 'export-image.png'
    image_path.write_bytes(b'fake-png-bytes')

    with app.app_context():
        db = get_db()
        default_category = db.execute(
            "SELECT id FROM Categories WHERE is_default = 1 LIMIT 1"
        ).fetchone()
        db.execute(
            """
            INSERT INTO Notes (title, content, category_id, cover_image)
            VALUES (?, ?, ?, ?)
            """,
            (
                'Image Export',
                'Markdown image ![sample](/static/uploads/export-image.png)\n'
                '<img src="/static/uploads/export-image.png">',
                default_category['id'],
                '/static/uploads/export-image.png',
            ),
        )
        db.commit()

    resp = client.get('/api/export/markdown')
    zf = zipfile.ZipFile(io.BytesIO(resp.data))

    assert 'images/export-image.png' in zf.namelist()
    assert zf.read('images/export-image.png') == b'fake-png-bytes'

    md_files = [n for n in zf.namelist() if 'Image-Export' in n]
    assert len(md_files) == 1
    content = zf.read(md_files[0]).decode('utf-8')
    assert '/static/uploads/export-image.png' not in content
    assert 'images/export-image.png' in content

    manifest = json.loads(zf.read('_manifest.json').decode('utf-8'))
    assert manifest['export_info']['images_count'] >= 1
