# -*- coding: utf-8 -*-
"""
TEST-001: 批量修改分類 (Phase 0 Step 0.1.2 更新)
原對應 Bug: BUG-001 (已修復 - Notes.type 已移除)
"""

import sqlite3
import pytest


def get_db(app):
    """獲取測試資料庫連線"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db


def test_batch_update_category_id(client, app):
    """
    Phase 0 Step 0.1.2: 驗證批量修改分類使用 category_id
    """
    with app.app_context():
        db = get_db(app)

        # 1. 取得兩個分類 ID
        default_cat = db.execute(
            "SELECT id FROM Categories WHERE is_default = 1"
        ).fetchone()

        prompt_cat = db.execute(
            "SELECT id FROM Categories WHERE name LIKE '%提示詞%' OR name LIKE '%Prompt%'"
        ).fetchone()

        if not prompt_cat:
            # 如果不存在就建立
            db.execute("INSERT INTO Categories (name) VALUES ('提示詞')")
            db.commit()
            prompt_cat = db.execute("SELECT id FROM Categories WHERE name = '提示詞'").fetchone()

        default_category_id = default_cat['id']
        prompt_category_id = prompt_cat['id']

        # 2. 建立測試筆記 (使用預設分類)
        db.execute(
            "INSERT INTO Notes (title, content, category_id) VALUES ('TestNote', 'Content', ?)",
            (default_category_id,)
        )
        db.commit()

        note = db.execute("SELECT id FROM Notes WHERE title = 'TestNote'").fetchone()
        note_id = note['id']
        db.close()

    # 3. 批量修改分類 (使用 category_id)
    response = client.post('/api/notes/batch/type', json={
        'note_ids': [note_id],
        'category_id': prompt_category_id
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['updated_count'] == 1

    # 4. 驗證 category_id 已更新
    with app.app_context():
        db = get_db(app)
        note = db.execute(
            "SELECT category_id FROM Notes WHERE id = ?",
            (note_id,)
        ).fetchone()
        db.close()

        assert note['category_id'] == prompt_category_id, \
            f"category_id 應為 {prompt_category_id}，實際為 {note['category_id']}"


def test_batch_update_category_with_multiple_notes(client, app):
    """
    Phase 0 Step 0.1.2: 驗證批量修改多個筆記的分類
    """
    with app.app_context():
        db = get_db(app)

        # 取得預設分類和目標分類
        default_cat = db.execute(
            "SELECT id FROM Categories WHERE is_default = 1"
        ).fetchone()

        target_cat = db.execute(
            "SELECT id FROM Categories WHERE name LIKE '%教學%' OR name LIKE '%Tutorial%'"
        ).fetchone()

        if not target_cat:
            # 如果不存在就建立
            db.execute("INSERT INTO Categories (name) VALUES ('教學')")
            db.commit()
            target_cat = db.execute("SELECT id FROM Categories WHERE name = '教學'").fetchone()

        default_category_id = default_cat['id']
        target_category_id = target_cat['id']

        # 建立多個測試筆記 (使用預設分類)
        for i in range(3):
            db.execute(
                "INSERT INTO Notes (title, content, category_id) VALUES (?, ?, ?)",
                (f'BatchTest{i}', 'Content', default_category_id)
            )
        db.commit()

        notes = db.execute("SELECT id FROM Notes WHERE title LIKE 'BatchTest%'").fetchall()
        note_ids = [n['id'] for n in notes]
        db.close()

    # 批量修改分類 (使用 category_id)
    response = client.post('/api/notes/batch/type', json={
        'note_ids': note_ids,
        'category_id': target_category_id
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['updated_count'] == 3

    # 驗證所有筆記的 category_id 都已更新
    with app.app_context():
        db = get_db(app)
        for nid in note_ids:
            note = db.execute(
                "SELECT category_id FROM Notes WHERE id = ?", (nid,)
            ).fetchone()
            assert note['category_id'] == target_category_id
        db.close()
