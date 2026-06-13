# -*- coding: utf-8 -*-
"""
Database Migration: Add prompt_params column to Notes table
Local Insight v1.6.5 - Prompt Builder Advanced Features

Run this script once to add the prompt_params column:
    python migrations/add_prompt_params.py
"""

import sqlite3
import os
import sys

# 確定資料庫路徑
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge.db')


def migrate():
    """新增 prompt_params 欄位到 Notes 表"""
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] 資料庫不存在: {DB_PATH}")
        print("請先啟動應用程式以建立資料庫。")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 檢查欄位是否已存在
        cursor.execute("PRAGMA table_info(Notes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'prompt_params' in columns:
            print("[INFO] prompt_params 欄位已存在，無需遷移。")
            return True
        
        # 新增欄位
        print("[MIGRATE] 新增 Notes.prompt_params 欄位...")
        cursor.execute("""
            ALTER TABLE Notes 
            ADD COLUMN prompt_params TEXT DEFAULT NULL
        """)
        
        conn.commit()
        print("[SUCCESS] 遷移完成！")
        print("  - 新增欄位: Notes.prompt_params (TEXT, 可為 NULL)")
        print("  - 用途: 儲存 Prompt Builder 的結構化參數 (JSON)")
        
        # 驗證
        cursor.execute("PRAGMA table_info(Notes)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'prompt_params' in columns:
            print("[VERIFY] 欄位驗證成功 ✓")
            return True
        else:
            print("[ERROR] 欄位驗證失敗！")
            return False
            
    except Exception as e:
        print(f"[ERROR] 遷移失敗: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 50)
    print("Local Insight - Database Migration")
    print("Add prompt_params column (v1.6.5)")
    print("=" * 50)
    
    success = migrate()
    sys.exit(0 if success else 1)
