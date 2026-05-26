# -*- coding: utf-8 -*-
"""
TEST-002: 批量刪除圖片清理
"""

import sqlite3
import os
import pytest


def get_db(app):
    """獲取測試資料庫連線"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db


def test_batch_delete_cleans_images(client, app):
    """
    驗證批量刪除時關聯圖片被正確清理
    """
    uploads_dir = app.config['UPLOAD_FOLDER']
    os.makedirs(uploads_dir, exist_ok=True)
    
    # 1. 建立測試圖片
    test_image = os.path.join(uploads_dir, 'batch_delete_test.jpg')
    with open(test_image, 'wb') as f:
        f.write(b'fake image content for batch delete test')
    
    # 2. 建立含圖片的筆記
    with app.app_context():
        db = get_db(app)
        default_category_id = db.execute(
            "SELECT id FROM Categories WHERE is_default = 1 LIMIT 1"
        ).fetchone()['id']
        db.execute("""
            INSERT INTO Notes (title, content, category_id) 
            VALUES (?, ?, ?)
        """, ('BatchDeleteWithImage', '![img](/static/uploads/batch_delete_test.jpg)', default_category_id))
        db.commit()
        
        note = db.execute("SELECT id FROM Notes WHERE title = 'BatchDeleteWithImage'").fetchone()
        note_id = note['id']
        db.close()
    
    # 確認圖片存在
    assert os.path.exists(test_image), "測試圖片應存在"
    
    # 3. 批量刪除
    response = client.post('/api/notes/batch/delete', json={
        'note_ids': [note_id]
    })
    
    assert response.status_code == 200
    
    # 4. 驗證圖片已刪除
    assert not os.path.exists(test_image), "關聯圖片應被刪除"


def test_batch_delete_preserves_shared_images(client, app):
    """
    驗證批量刪除時不會刪除被其他筆記引用的圖片
    """
    uploads_dir = app.config['UPLOAD_FOLDER']
    os.makedirs(uploads_dir, exist_ok=True)
    
    # 建立共用圖片
    shared_image = os.path.join(uploads_dir, 'shared_image.jpg')
    with open(shared_image, 'wb') as f:
        f.write(b'shared image content')
    
    with app.app_context():
        db = get_db(app)
        default_category_id = db.execute(
            "SELECT id FROM Categories WHERE is_default = 1 LIMIT 1"
        ).fetchone()['id']
        
        # 建立兩個引用同一圖片的筆記
        db.execute("""
            INSERT INTO Notes (title, content, category_id) 
            VALUES (?, ?, ?)
        """, ('SharedImageNote1', '![img](/static/uploads/shared_image.jpg)', default_category_id))
        db.execute("""
            INSERT INTO Notes (title, content, category_id) 
            VALUES (?, ?, ?)
        """, ('SharedImageNote2', '![img](/static/uploads/shared_image.jpg)', default_category_id))
        db.commit()
        
        note1 = db.execute("SELECT id FROM Notes WHERE title = 'SharedImageNote1'").fetchone()
        note1_id = note1['id']
        db.close()
    
    try:
        # 只刪除一個筆記
        response = client.post('/api/notes/batch/delete', json={
            'note_ids': [note1_id]
        })
        
        assert response.status_code == 200
        
        # 圖片應該仍存在 (被另一筆記引用)
        assert os.path.exists(shared_image), "共用圖片不應被刪除"
        
    finally:
        # 清理
        if os.path.exists(shared_image):
            os.remove(shared_image)


def test_batch_delete_empty_list(client, app):
    """
    驗證空列表批量刪除回傳錯誤
    """
    response = client.post('/api/notes/batch/delete', json={
        'note_ids': []
    })
    
    assert response.status_code == 400


def test_batch_delete_nonexistent_notes(client, app):
    """
    驗證刪除不存在的筆記 ID 不會崩潰
    """
    response = client.post('/api/notes/batch/delete', json={
        'note_ids': [99999, 99998, 99997]
    })
    
    # 應該成功但刪除數為 0
    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['deleted_count'] == 0
