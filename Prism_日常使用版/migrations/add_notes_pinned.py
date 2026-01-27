# -*- coding: utf-8 -*-
"""
資料庫遷移腳本：新增 Notes.is_pinned 欄位
用於實現筆記置頂功能

執行方式：
    python migrations/add_notes_pinned.py
"""

import sqlite3
import os

# 資料庫路徑
DB_PATH = 'local_insight.db'


def migrate():
    """執行遷移"""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] 資料庫檔案不存在: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 檢查欄位是否已存在
        cursor.execute("PRAGMA table_info(Notes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_pinned' in columns:
            print("[INFO] is_pinned 欄位已存在，跳過遷移")
            return True
        
        # 新增 is_pinned 欄位
        print("[INFO] 正在新增 Notes.is_pinned 欄位...")
        cursor.execute("""
            ALTER TABLE Notes ADD COLUMN is_pinned INTEGER DEFAULT 0
        """)
        
        conn.commit()
        print("[SUCCESS] 遷移完成！已新增 is_pinned 欄位")
        
        # 驗證
        cursor.execute("PRAGMA table_info(Notes)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"[INFO] Notes 表欄位: {columns}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] 遷移失敗: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
