"""
測試 API 分頁功能
建立 100+ 筆測試資料並驗證分頁正確性
"""

import pytest

@pytest.fixture

def populated_client(app):
    """
    建立一個包含許多測試筆記的 client fixture。
    scope="module" 意味著這個 setup 在此模組的所有測試中只會執行一次。
    """
    with app.app_context():
        # 直接使用 DB 插入會比 API 快很多，但為了整合測試，我們還是模擬 API 行為
        # 或者混合：大量數據用 DB，少量用 API
        # 這裡為了保證觸發所有 side effects (FTS, etc)，我們使用 client
        client = app.test_client()
        
        # 批量建立 105 筆筆記
        notes_count = 105
        print(f"Creating {notes_count} test notes...")
        
        # 為了效率，我們可以直接操作 DB，因為這只是測試分頁，不是測試創建
        from db import get_db
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default) VALUES (?, ?, ?, 0)",
            ("測試", "🧪", 999)
        )
        db.commit()
        test_category_id = db.execute(
            "SELECT id FROM Categories WHERE name = ? LIMIT 1",
            ("測試",)
        ).fetchone()[0]
        
        # 只有在資料為空時才建立 (避免重複)
        cursor = db.execute("SELECT COUNT(*) FROM Notes WHERE category_id = ?", (test_category_id,))
        if cursor.fetchone()[0] < notes_count:
            notes_data = []
            for i in range(1, notes_count + 1):
                notes_data.append((
                    f"Test Note {i:03d}",
                    f"# Test Content {i}\n\nThis is test note number {i}.",
                    test_category_id,
                    f"Test note {i}"
                ))
            
            # 使用 executemany 加速
            db.executemany('''
                INSERT INTO Notes (title, content, category_id, remarks, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', notes_data)
            db.commit()
            
            print(f"Created {notes_count} notes via SQL")
            
    return app.test_client()

def test_default_pagination(populated_client):
    """測試預設分頁參數"""
    response = populated_client.get('/api/notes?type=測試') # Filter by our test type
    assert response.status_code == 200
    
    result = response.json
    assert 'pagination' in result
    pagination = result['pagination']
    
    # 預設 page=1, per_page=20
    assert pagination['page'] == 1
    assert pagination['per_page'] == 20
    assert len(result['data']) <= 20
    assert pagination['total'] >= 105

def test_custom_pagination(populated_client):
    """測試自定義分頁參數"""
    response = populated_client.get('/api/notes?page=2&per_page=10&type=測試')
    assert response.status_code == 200
    
    result = response.json
    pagination = result['pagination']
    
    assert pagination['page'] == 2
    assert pagination['per_page'] == 10
    assert len(result['data']) == 10

def test_max_per_page(populated_client):
    """測試 per_page 最大值限制"""
    response = populated_client.get('/api/notes?per_page=150&type=測試')
    assert response.status_code == 200
    
    result = response.json
    pagination = result['pagination']
    
    # 應該被限制在 100
    assert pagination['per_page'] == 100

def test_invalid_page(populated_client):
    """測試無效頁碼處理"""
    # 測試 page=0
    response = populated_client.get('/api/notes?page=0&type=測試')
    result = response.json
    assert result['pagination']['page'] == 1
    
    # 測試 page=-5
    response = populated_client.get('/api/notes?page=-5&type=測試')
    result = response.json
    assert result['pagination']['page'] == 1

def test_last_page(populated_client):
    """測試最後一頁資料"""
    # 先取得總頁數
    response = populated_client.get('/api/notes?type=測試')
    result = response.json
    total = result['pagination']['total']
    total_pages = result['pagination']['total_pages']
    
    # 請求最後一頁
    response = populated_client.get(f'/api/notes?page={total_pages}&per_page=20&type=測試')
    result = response.json
    
    # 計算預期數量
    expected_count = total % 20
    if expected_count == 0: expected_count = 20
    
    assert len(result['data']) == expected_count

def test_beyond_last_page(populated_client):
    """測試超出最後一頁"""
    response = populated_client.get('/api/notes?type=測試')
    total_pages = response.json['pagination']['total_pages']
    
    response = populated_client.get(f'/api/notes?page={total_pages + 10}&type=測試')
    result = response.json
    
    assert len(result['data']) == 0
