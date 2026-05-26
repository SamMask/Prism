# -*- coding: utf-8 -*-
"""
TEST-004: 標籤合併交易完整性
對應 Bug: BUG-002
"""

import sqlite3
import pytest


def get_db(app):
    """獲取測試資料庫連線"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db


def test_merge_tags_transaction(client, app):
    """
    驗證標籤合併時交易完整性
    若中途失敗應回滾所有變更
    """
    with app.app_context():
        db = get_db(app)
        
        # 建立測試標籤
        db.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('source1')")
        db.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('source2')")
        db.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('target')")
        db.commit()
        
        source1 = db.execute("SELECT id FROM Tags WHERE name = 'source1'").fetchone()
        source2 = db.execute("SELECT id FROM Tags WHERE name = 'source2'").fetchone()
        target = db.execute("SELECT id FROM Tags WHERE name = 'target'").fetchone()
        
        source1_id = source1['id']
        source2_id = source2['id']
        target_id = target['id']
        db.close()
    
    # 合併標籤
    response = client.post('/api/tags/merge', json={
        'source_tag_ids': [source1_id, source2_id],
        'target_tag_id': target_id
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['merged_count'] == 2
    
    # 驗證: source 標籤應被刪除
    with app.app_context():
        db = get_db(app)
        remaining = db.execute(
            "SELECT COUNT(*) as cnt FROM Tags WHERE name IN ('source1', 'source2')"
        ).fetchone()
        db.close()
        
        assert remaining['cnt'] == 0, "來源標籤應被刪除"


def test_merge_tags_transfers_notes(client, app):
    """
    驗證標籤合併時筆記關聯正確轉移
    """
    with app.app_context():
        db = get_db(app)
        
        # 建立測試標籤
        db.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('merge_source')")
        db.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('merge_target')")
        
        # 建立測試筆記
        default_category_id = db.execute(
            "SELECT id FROM Categories WHERE is_default = 1 LIMIT 1"
        ).fetchone()['id']
        db.execute(
            "INSERT INTO Notes (title, content, category_id) VALUES (?, ?, ?)",
            ('MergeTestNote', 'Content', default_category_id)
        )
        db.commit()
        
        source_tag = db.execute("SELECT id FROM Tags WHERE name = 'merge_source'").fetchone()
        target_tag = db.execute("SELECT id FROM Tags WHERE name = 'merge_target'").fetchone()
        note = db.execute("SELECT id FROM Notes WHERE title = 'MergeTestNote'").fetchone()
        
        source_id = source_tag['id']
        target_id = target_tag['id']
        note_id = note['id']
        
        # 將筆記關聯到 source 標籤
        db.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (note_id, source_id))
        db.commit()
        db.close()
    
    # 合併標籤
    response = client.post('/api/tags/merge', json={
        'source_tag_ids': [source_id],
        'target_tag_id': target_id
    })
    
    assert response.status_code == 200
    
    # 驗證筆記現在關聯到 target 標籤
    with app.app_context():
        db = get_db(app)
        note_tag = db.execute(
            "SELECT * FROM Note_Tags WHERE note_id = ? AND tag_id = ?",
            (note_id, target_id)
        ).fetchone()
        db.close()
        
        assert note_tag is not None, "筆記應關聯到目標標籤"


def test_merge_to_nonexistent_target_fails(client, app):
    """
    驗證合併到不存在的目標標籤會失敗
    """
    with app.app_context():
        db = get_db(app)
        db.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('orphan_source')")
        db.commit()
        
        source = db.execute("SELECT id FROM Tags WHERE name = 'orphan_source'").fetchone()
        source_id = source['id']
        db.close()
    
    # 嘗試合併到不存在的標籤
    response = client.post('/api/tags/merge', json={
        'source_tag_ids': [source_id],
        'target_tag_id': 99999  # 不存在
    })
    
    assert response.status_code == 404
