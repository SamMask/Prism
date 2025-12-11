import sqlite3
import datetime

def update_welcome_note():
    db_path = 'knowledge.db'
    
    # 新的範例筆記內容 (Markdown)
    new_title = "👋 歡迎使用 Local Insight v2.0"
    new_content = """# 👋 歡迎使用 Local Insight v2.0

感謝您使用 **Local Insight**！這是一個專為開發者與知識工作者打造的**本機端 AI 提示詞與知識管理中樞**。

## 🚀 v2.0 新功能亮點

### 1. 🎨 全新 Prompt Builder
我們新增了強大的提示詞建構器 (點擊頂部導航列「提示詞建構」進入)，支援：
- **參數化模版**：透過 JSON 定義變數，快速生成複雜 Prompt。
- **快捷鍵支援**：`Ctrl+Enter` 複製，`Ctrl+S` 存為筆記。
- **即時預覽**：左側調整參數，右側即時看到結果。

### 2. 🗂️ 分類與標籤系統升級
- **版本化遷移**：資料庫結構更穩固，升級無痛。
- **分類管理**：在設定中支援分類拖曳排序與圖示自訂。
- **標籤管理**：支援標籤合併與重新命名。
- **複選操作**：點擊筆記卡片右上角 ✅ 可進入批次模式。

### 3. ✨ 視覺與體驗優化
- **多彩主題**：在設定中選擇「賽博龐克」、「護眼綠」等多種主題。
- **更順暢的 UI**：優化了 Modal 動畫與無障礙焦點顯示。
- **圖片管理**：支援貼上圖片 (Ctrl+V) 與封面位置調整。

## 💡 快速上手指南

1. **新增筆記**：點擊右上角的 `+ 新增卡片`。
2. **搜尋與過濾**：使用頂部搜尋框或左側側邊欄進行篩選（支援多關鍵字）。
3. **Markdown 編輯**：支援即時預覽、程式碼高亮與 Mermaid 圖表。
4. **管理分類**：點擊左側齒輪圖示 ⚙️ 進入設定。

---

*本筆記由系統自動生成，您可以自由編輯或刪除。*"""

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 嘗試尋找現有的歡迎筆記
        cursor.execute("SELECT id FROM Notes WHERE title LIKE '%歡迎使用%' OR title LIKE '%Welcome%' LIMIT 1")
        row = cursor.fetchone()

        if row:
            note_id = row[0]
            print(f"✅ 找到現有的歡迎筆記 (ID: {note_id})，正在更新內容...")
            cursor.execute("""
                UPDATE Notes 
                SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (new_title, new_content, note_id))
        else:
            print("🆕 未找到歡迎筆記，正在建立新筆記...")
            # 嘗試取得 '教學' 分類 ID (如果是 v2.0) 或直接用 type 字串
            # 先檢查是否有 Categories 表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Categories'")
            has_categories = cursor.fetchone()
            
            category_id = None
            type_name = '教學'
            
            if has_categories:
                cursor.execute("SELECT id FROM Categories WHERE name = ?", (type_name,))
                cat_row = cursor.fetchone()
                if cat_row:
                    category_id = cat_row[0]
                else:
                    # Fallback to default
                     cursor.execute("SELECT id FROM Categories WHERE is_default = 1")
                     cat_default = cursor.fetchone()
                     if cat_default:
                         category_id = cat_default[0]

            cursor.execute("""
                INSERT INTO Notes (title, content, type, category_id) 
                VALUES (?, ?, ?, ?)
            """, (new_title, new_content, type_name, category_id))
            
            note_id = cursor.lastrowid
            
            # 插入標籤 '教學', 'v2.0'
            tags = ['教學', 'v2.0', '入門']
            for tag in tags:
                # 確保 Tag 存在
                cursor.execute("INSERT OR IGNORE INTO Tags (name) VALUES (?)", (tag,))
                cursor.execute("SELECT id FROM Tags WHERE name = ?", (tag,))
                tag_id = cursor.fetchone()[0]
                
                # 建立關聯
                cursor.execute("INSERT OR IGNORE INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))

        conn.commit()
        print("🎉 系統預設範例筆記更新完成！")
        
    except Exception as e:
        print(f"❌ 更新失敗: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_welcome_note()
