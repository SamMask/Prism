import sqlite3
import time
import sys

def force_update():
    db_path = 'knowledge.db'
    
    # Target Note Title the user currently sees
    target_title_query = "歡迎使用 Local Insight"
    
    # New Content
    new_title = "👋 歡迎使用 Local Insight v1.0"
    new_content = """# 👋 歡迎使用 Local Insight v1.0

感謝您使用 **Local Insight**！這是一個專為開發者與知識工作者打造的**本機端 AI 提示詞與知識管理中樞**。

## 🚀 v1.0 新功能亮點

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
        print("Connecting to database...", flush=True)
        conn = sqlite3.connect(db_path, timeout=10) # 10s timeout
        cursor = conn.cursor()

        print(f"Searching for note with title like '{target_title_query}'...", flush=True)
        cursor.execute("SELECT id, title FROM Notes WHERE title LIKE ?", (f'%{target_title_query}%',))
        rows = cursor.fetchall()
        
        if not rows:
            print("No matching notes found. Creating new one...", flush=True)
            # Insert logic...
            cursor.execute("INSERT INTO Notes (title, content, type) VALUES (?, ?, ?)", (new_title, new_content, '教學'))
            print("Created new note.", flush=True)
        else:
            for row in rows:
                nid, title = row
                print(f"Updating Note ID: {nid} (Title: {title})...", flush=True)
                cursor.execute("UPDATE Notes SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_title, new_content, nid))
                print("Update executed.", flush=True)

        conn.commit()
        print("Commit successful.", flush=True)
        conn.close()
        
    except sqlite3.OperationalError as e:
        print(f"Database Locked or Error: {e}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    force_update()
