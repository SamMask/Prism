# -*- coding: utf-8 -*-
"""
TEST-005: 分類刪除遷移
"""

import sqlite3
import pytest


def get_db(app):
    """獲取測試資料庫連線"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db


def test_delete_category_migrates_notes(client, app):
    """
    驗證刪除分類時筆記正確遷移到目標分類
    """
    with app.app_context():
        db = get_db(app)
        
        # 建立來源分類
        db.execute("INSERT INTO Categories (name, sort_order) VALUES ('ToDeleteCat', 99)")
        db.commit()
        
        source_cat = db.execute("SELECT id FROM Categories WHERE name = 'ToDeleteCat'").fetchone()
        source_cat_id = source_cat['id']
        
        # 取得目標分類 (預設分類)
        target_cat = db.execute("SELECT id, name FROM Categories WHERE is_default = 1").fetchone()
        if not target_cat:
            target_cat = db.execute("SELECT id, name FROM Categories LIMIT 1").fetchone()
        target_cat_name = target_cat['name']
        
        # 建立屬於該分類的筆記
        db.execute(
            "INSERT INTO Notes (title, content, type, category_id) VALUES (?, ?, ?, ?)",
            ('CatDeleteTest', 'Content', 'ToDeleteCat', source_cat_id)
        )
        db.commit()
        db.close()
    
    # 刪除分類並遷移筆記 - 使用 target_category (name) 而非 target_category_id
    response = client.delete(
        f'/api/categories/{source_cat_id}',
        json={'target_category': target_cat_name}
    )
    
    assert response.status_code == 200
    
    # 驗證筆記已遷移
    with app.app_context():
        db = get_db(app)
        note = db.execute(
            "SELECT type FROM Notes WHERE title = 'CatDeleteTest'"
        ).fetchone()
        db.close()
        
        assert note['type'] == target_cat_name, f"筆記應遷移到 {target_cat_name}"


def test_cannot_delete_default_category(client, app):
    """
    驗證無法刪除預設分類
    """
    with app.app_context():
        db = get_db(app)
        default_cat = db.execute("SELECT id FROM Categories WHERE is_default = 1").fetchone()
        db.close()
    
    if default_cat:
        response = client.delete(f'/api/categories/{default_cat["id"]}')
        # 應該被拒絕 (400 或 403)
        assert response.status_code in [400, 403]


def test_create_category(client, app):
    """
    驗證新增分類功能
    """
    response = client.post('/api/categories', json={
        'name': 'NewTestCategory',
        'icon': '🆕'
    })
    
    assert response.status_code in [200, 201]
    
    # 驗證分類已建立
    with app.app_context():
        db = get_db(app)
        cat = db.execute("SELECT * FROM Categories WHERE name = 'NewTestCategory'").fetchone()
        db.close()
        
        assert cat is not None
        assert cat['icon'] == '🆕'


def test_rename_category(client, app):
    """
    驗證重命名分類功能
    """
    with app.app_context():
        db = get_db(app)
        db.execute("INSERT INTO Categories (name, sort_order) VALUES ('OldName', 50)")
        db.commit()
        
        cat = db.execute("SELECT id FROM Categories WHERE name = 'OldName'").fetchone()
        cat_id = cat['id']
        db.close()
    
    response = client.put(f'/api/categories/{cat_id}', json={
        'name': 'NewName'
    })
    
    assert response.status_code == 200
    
    # 驗證名稱已更新
    with app.app_context():
        db = get_db(app)
        cat = db.execute("SELECT name FROM Categories WHERE id = ?", (cat_id,)).fetchone()
        db.close()
        
        assert cat['name'] == 'NewName'
