# -*- coding: utf-8 -*-
"""
TEST-007: 系統維護功能測試
Fixed version - 移除重複的孤兒圖片測試
"""

import sqlite3
import os
import pytest


def get_db(app):
    """獲取測試資料庫連線"""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db


def test_vacuum_database(client, app):
    """
    驗證 VACUUM 正確執行並回傳空間變化
    """
    response = client.post('/api/system/vacuum')
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['status'] == 'success'
    assert 'data' in data
    
    result = data['data']
    assert 'size_before' in result
    assert 'size_after' in result
    assert 'freed_bytes' in result
    assert result['size_before'] >= result['size_after']


def test_consistency_check(client, app):
    """
    驗證資料一致性檢查 API
    """
    response = client.get('/api/system/check-consistency')
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['status'] == 'success'
    assert 'data' in data
    
    result = data['data']
    assert 'orphan_note_tags' in result
    assert 'unused_tags' in result
    assert 'fk_enabled' in result
    assert result['fk_enabled'] == True
    assert 'null_category_id' in result
    assert 'health' in result


def test_clear_history(client, app):
    """
    驗證清空歷史紀錄功能
    """
    # 先建立一些歷史紀錄
    with app.app_context():
        db = get_db(app)
        
        # 建立測試筆記
        default_category = db.execute(
            "SELECT id FROM Categories WHERE is_default = 1 LIMIT 1"
        ).fetchone()
        db.execute(
            "INSERT INTO Notes (title, content, category_id) VALUES (?, ?, ?)",
            ('HistoryTest', 'v1', default_category['id'])
        )
        db.commit()
        
        note = db.execute("SELECT id FROM Notes WHERE title = 'HistoryTest'").fetchone()
        note_id = note['id']
        
        # 建立歷史紀錄
        db.execute(
            "INSERT INTO Note_History (note_id, content) VALUES (?, ?)",
            (note_id, 'old content')
        )
        db.commit()
        
        # 確認有歷史紀錄
        count = db.execute("SELECT COUNT(*) as cnt FROM Note_History").fetchone()['cnt']
        assert count > 0, "應有歷史紀錄"
        db.close()
    
    # 清空歷史
    response = client.post('/api/system/clear-history')
    
    assert response.status_code == 200
    
    # 驗證歷史已清空
    with app.app_context():
        db = get_db(app)
        count = db.execute("SELECT COUNT(*) as cnt FROM Note_History").fetchone()['cnt']
        db.close()
        
        assert count == 0, "歷史紀錄應被清空"


def test_wal_checkpoint(client, app):
    """
    驗證 WAL checkpoint API
    """
    response = client.post('/api/system/wal-checkpoint')
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['status'] == 'success'


def test_migration_status(client):
    """驗證 migration status API 存在且回傳版本資訊"""
    response = client.get('/api/system/migration-status')

    assert response.status_code == 200
    data = response.get_json()

    assert data['status'] == 'success'
    assert data['data']['current_version'] >= 1
    assert data['data']['latest_version'] >= data['data']['current_version']
    assert isinstance(data['data']['completed'], list)
    assert isinstance(data['data']['pending'], list)


def test_check_update_without_configured_source(client, app):
    """未設定更新來源時，API 仍應回穩定 JSON 而不是 404"""
    app.config['PRISM_RELEASE_API_URL'] = ''

    response = client.get('/api/system/check-update')

    assert response.status_code == 200
    data = response.get_json()

    assert data['status'] == 'success'
    assert data['data']['has_update'] is False
    assert 'current_version' in data['data']
    assert 'message' in data['data']
