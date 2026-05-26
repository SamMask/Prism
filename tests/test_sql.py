"""
測試 SQL 邏輯 (使用安全測試環境)
驗證資料庫操作正確性，避免影響正式資料
"""

import sqlite3
import pytest

def test_reorder_notes(app):
    """
    測試筆記重新排序功能
    使用 app fixture 提供的 database
    """
    with app.app_context():
        from db import get_db
        db = get_db()
        
        # 1. 建立測試筆記 (ID will be 2, 3, 4 because Welcome note is id=1)
        note_ids = []
        for i in range(3):
            cursor = db.execute(
                'INSERT INTO Notes (title, content, sort_order) VALUES (?, ?, ?)',
                (f'ReorderTest {i}', 'Content', 100 + i)
            )
            note_ids.append(cursor.lastrowid)
        db.commit()
        
        # 2. 執行重排序 (模擬前端傳來的順序)
        # 用戶希望的順序: 反轉
        new_order_ids = list(reversed(note_ids))
        
        try:
            # 更新每個筆記的 sort_order
            for index, note_id in enumerate(new_order_ids):
                db.execute(
                    'UPDATE Notes SET sort_order = ? WHERE id = ?',
                    (index, note_id)
                )
            db.commit()
        except sqlite3.Error as e:
            pytest.fail(f"Database error during reorder: {e}")
            
        # 3. 驗證結果
        # 查詢我們建立的筆記
        placeholders = ','.join('?' * len(note_ids))
        cursor = db.execute(
            f'SELECT id, sort_order FROM Notes WHERE id IN ({placeholders}) ORDER BY sort_order ASC',
            note_ids
        )
        results = cursor.fetchall()
        
        # 檢查是否 matches new_order_ids
        sorted_ids = [row['id'] for row in results]
        assert sorted_ids == new_order_ids, f"Expected {new_order_ids}, got {sorted_ids}"
        
        # 檢查 sort_order 值是否為 0, 1, 2
        sort_values = [row['sort_order'] for row in results]
        assert sort_values == [0, 1, 2], f"Expected [0, 1, 2], got {sort_values}"
