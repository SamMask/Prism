# -*- coding: utf-8 -*-
"""
TEST-001: 批量修改類型同步 category_id
對應 Bug: BUG-001
"""

import sqlite3
import pytest


def get_db(app):
    """獲取測試資料庫連線"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db


def test_batch_update_type_syncs_category_id(client, app):
    """
    驗證批量修改類型時 category_id 同步更新 (BUG-001 Fix)
    """
    with app.app_context():
        db = get_db(app)
        
        # 1. 取得預設分類 ID
        # 使用預設種子數據中的分類
        prompt_cat = db.execute(
            "SELECT id FROM Categories WHERE name LIKE '%提示詞%' OR name LIKE '%Prompt%'"
        ).fetchone()
        
        if not prompt_cat:
            # 如果不存在就建立
            db.execute("INSERT INTO Categories (name) VALUES ('提示詞')")
            db.commit()
            prompt_cat = db.execute("SELECT id FROM Categories WHERE name = '提示詞'").fetchone()
        
        prompt_category_id = prompt_cat['id']
        
        # 2. 建立測試筆記 (type = '筆記')
        db.execute("INSERT INTO Notes (title, content, type) VALUES ('TestNote', 'Content', '筆記')")
        db.commit()
        
        note = db.execute("SELECT id FROM Notes WHERE title = 'TestNote'").fetchone()
        note_id = note['id']
        db.close()
    
    # 3. 批量修改類型
    # 取得正確的分類名稱
    with app.app_context():
        db = get_db(app)
        cat = db.execute("SELECT name FROM Categories WHERE id = ?", (prompt_category_id,)).fetchone()
        target_type = cat['name']
        db.close()
    
    response = client.post('/api/notes/batch/type', json={
        'note_ids': [note_id],
        'type': target_type
    })
    
    assert response.status_code == 200
    
    # 4. 驗證 category_id 已同步
    with app.app_context():
        db = get_db(app)
        note = db.execute(
            "SELECT type, category_id FROM Notes WHERE id = ?", 
            (note_id,)
        ).fetchone()
        db.close()
        
        assert note['type'] == target_type
        assert note['category_id'] == prompt_category_id, \
            f"category_id 應為 {prompt_category_id}，實際為 {note['category_id']}"


def test_batch_update_type_with_multiple_notes(client, app):
    """
    驗證批量修改多個筆記時全部同步 category_id
    """
    with app.app_context():
        db = get_db(app)
        
        # 建立多個測試筆記
        for i in range(3):
            db.execute(
                "INSERT INTO Notes (title, content, type) VALUES (?, ?, ?)",
                (f'BatchTest{i}', 'Content', '筆記')
            )
        db.commit()
        
        notes = db.execute("SELECT id FROM Notes WHERE title LIKE 'BatchTest%'").fetchall()
        note_ids = [n['id'] for n in notes]
        
        # 取得目標分類
        cat = db.execute(
            "SELECT id, name FROM Categories WHERE name LIKE '%教學%' OR name LIKE '%Tutorial%'"
        ).fetchone()
        
        target_category_id = cat['id']
        target_type = cat['name']
        db.close()
    
    # 批量修改
    response = client.post('/api/notes/batch/type', json={
        'note_ids': note_ids,
        'type': target_type
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['updated_count'] == 3
    
    # 驗證所有筆記的 category_id 都已同步
    with app.app_context():
        db = get_db(app)
        for nid in note_ids:
            note = db.execute(
                "SELECT category_id FROM Notes WHERE id = ?", (nid,)
            ).fetchone()
            assert note['category_id'] == target_category_id
        db.close()
