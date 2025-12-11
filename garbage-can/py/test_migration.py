# -*- coding: utf-8 -*-
"""測試遷移系統"""
import sys
sys.path.insert(0, '.')

from app import create_app, init_db

print("建立應用程式...")
app = create_app()

print("進入應用程式上下文...")
with app.app_context():
    print("執行資料庫初始化...")
    init_db()
    
    # 檢查遷移狀態
    from migrations import get_migration_status, get_current_version
    from app import get_db
    
    db = get_db()
    version = get_current_version(db)
    status = get_migration_status(db)
    
    print(f"\n=== 遷移狀態 ===")
    print(f"當前版本: v{version}")
    print(f"最新版本: v{status['latest_version']}")
    print(f"已完成: {len(status['completed'])} 個")
    print(f"待處理: {len(status['pending'])} 個")
    
    if status['pending']:
        print("\n待處理遷移:")
        for m in status['pending']:
            print(f"  - v{m['version']}: {m['name']}")
    
    # 檢查 category_id 欄位
    cursor = db.execute("PRAGMA table_info(Notes)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"\nNotes 表欄位: {columns}")
    
    if 'category_id' in columns:
        print("✅ category_id 欄位已建立")
        
        # 檢查填充狀態
        result = db.execute("SELECT COUNT(*) FROM Notes WHERE category_id IS NULL").fetchone()
        null_count = result[0]
        if null_count == 0:
            print("✅ 所有筆記都已關聯分類")
        else:
            print(f"⚠️ 還有 {null_count} 筆筆記沒有 category_id")
    else:
        print("❌ category_id 欄位尚未建立")

print("\n完成!")
