# -*- coding: utf-8 -*-
"""
Demo Database Generator for Prism
Creates demo_db/knowledge_demo.db with sample data for quick start.

Usage:
    python tools/create_demo_db.py
"""

import os
import sys
import sqlite3
import random
from datetime import datetime, timedelta

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Output path
DEMO_DB_DIR = os.path.join(PROJECT_ROOT, 'demo_db')
DEMO_DB_PATH = os.path.join(DEMO_DB_DIR, 'knowledge_demo.db')

# Sample data
SAMPLE_TITLES = [
    "Cyberpunk 街道場景構圖技巧",
    "人物肖像光影設定",
    "奇幻風格背景生成",
    "動漫風格角色設計",
    "建築攝影構圖靈感",
    "未來城市夜景 Prompt",
    "自然風景調色參數",
    "復古電影風格模板",
    "科幻機械細節描述",
    "時尚攝影姿態參考",
    "水彩風格轉換技巧",
    "油畫質感後製流程",
    "極簡主義設計原則",
    "夢幻場景合成技法",
    "角色動態姿態庫",
    "材質紋理描述詞彙",
    "環境氛圍營造手法",
    "多角色互動場景",
    "光線方向與情緒",
    "色彩心理學應用",
]

SAMPLE_CONTENTS = [
    """# {title}

這是一則關於 AI 圖像生成的筆記。

## 重點摘要

- 使用強烈的對比色彩
- 注意構圖的黃金比例
- 適當加入環境細節

## Prompt 範例

```
{prompt}
```

## 參考資料

記得根據實際需求調整參數。
""",
    """# {title}

## 快速筆記

{prompt}

### 備註

這是自動生成的示範筆記，用於展示 Prism 的功能。
""",
    """# {title}

## 核心概念

{prompt}

## 延伸思考

- 可以嘗試不同的風格組合
- 調整權重獲得更精確的結果
- 記錄成功的參數組合供日後參考
""",
]

SAMPLE_PROMPTS = [
    "A cyberpunk street scene, neon lights, rain reflections, cinematic composition",
    "Portrait photography, dramatic lighting, chiaroscuro, professional studio",
    "Fantasy landscape, magical forest, ethereal atmosphere, detailed foliage",
    "Anime character design, expressive eyes, dynamic pose, vibrant colors",
    "Architectural photography, leading lines, symmetry, golden hour",
    "Futuristic cityscape at night, holographic billboards, flying vehicles",
    "Natural scenery, mountain lake, autumn colors, misty morning",
    "Vintage film aesthetic, grain texture, warm tones, 35mm photography",
    "Sci-fi mechanical details, intricate gears, chrome surfaces, close-up",
    "Fashion photography, elegant pose, minimalist background, studio lighting",
]

SAMPLE_TAGS = [
    "Cyberpunk", "Portrait", "Landscape", "Anime", "Architecture",
    "Sci-Fi", "Fantasy", "Vintage", "Minimalist", "Fashion",
    "Tutorial", "Template", "Reference", "Workflow", "Inspiration",
]


def create_demo_db():
    """Create the demo database with sample data."""
    
    # Ensure demo_db directory exists
    os.makedirs(DEMO_DB_DIR, exist_ok=True)
    
    # Remove existing demo db if exists
    if os.path.exists(DEMO_DB_PATH):
        os.remove(DEMO_DB_PATH)
    
    # Connect and create schema
    conn = sqlite3.connect(DEMO_DB_PATH)
    conn.row_factory = sqlite3.Row
    db = conn.cursor()
    
    print(f"[INFO] Creating demo database at: {DEMO_DB_PATH}")
    
    # Enable WAL mode
    db.execute('PRAGMA journal_mode = WAL')
    db.execute('PRAGMA foreign_keys = ON')
    
    # Create tables (simplified schema)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS Notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT '筆記',
            remarks TEXT,
            cover_image TEXT,
            cover_position TEXT DEFAULT 'top',
            is_pinned BOOLEAN NOT NULL DEFAULT 0,
            is_archived BOOLEAN NOT NULL DEFAULT 0,
            sort_order INTEGER,
            category_id INTEGER,
            prompt_params TEXT,
            editor_layout TEXT DEFAULT 'full',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS Tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE
        );
        
        CREATE TABLE IF NOT EXISTS Note_Tags (
            note_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES Tags(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS Source_Urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            icon TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_default BOOLEAN NOT NULL DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS Note_History (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            diff_summary TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS Schema_Meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        
        -- FTS5
        CREATE VIRTUAL TABLE IF NOT EXISTS Notes_FTS USING fts5(
            title, content,
            content='Notes',
            content_rowid='id'
        );
        
        -- FTS Triggers
        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON Notes BEGIN
            INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
        END;
        
        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON Notes BEGIN
            INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
        END;
        
        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON Notes BEGIN
            INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
            INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
        END;
    ''')
    
    # Insert default categories
    categories = [
        ('提示詞 | Prompt', '🎨', 1, 0),
        ('筆記 | Note', '📝', 2, 1),
        ('教學 | Tutorial', '📚', 3, 0),
        ('資料 | Data', '💾', 4, 0),
        ('靈感 | Inspiration', '💡', 5, 0),
    ]
    db.executemany('''
        INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default)
        VALUES (?, ?, ?, ?)
    ''', categories)
    
    # Get category mapping
    db.execute('SELECT id, name FROM Categories')
    cat_map = {row[1]: row[0] for row in db.fetchall()}
    
    # Insert tags
    for tag in SAMPLE_TAGS:
        db.execute('INSERT OR IGNORE INTO Tags (name) VALUES (?)', (tag,))
    
    # Get tag mapping
    db.execute('SELECT id, name FROM Tags')
    tag_map = {row[1]: row[0] for row in db.fetchall()}
    
    # Generate 50 sample notes
    print("[INFO] Generating 50 sample notes...")
    
    category_names = list(cat_map.keys())
    base_time = datetime.now()
    
    for i in range(50):
        title = random.choice(SAMPLE_TITLES) + f" #{i+1}"
        prompt = random.choice(SAMPLE_PROMPTS)
        template = random.choice(SAMPLE_CONTENTS)
        content = template.format(title=title, prompt=prompt)
        
        category_name = random.choice(category_names)
        category_id = cat_map[category_name]
        
        # Randomize timestamps
        days_ago = random.randint(0, 90)
        created = base_time - timedelta(days=days_ago, hours=random.randint(0, 23))
        updated = created + timedelta(hours=random.randint(0, 48))
        
        is_pinned = 1 if i < 3 else 0  # Pin first 3
        
        db.execute('''
            INSERT INTO Notes (title, content, type, category_id, is_pinned, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, category_name, category_id, is_pinned, 
              created.isoformat(), updated.isoformat()))
        
        note_id = db.lastrowid
        
        # Add random tags (2-4 per note)
        selected_tags = random.sample(SAMPLE_TAGS, random.randint(2, 4))
        for tag_name in selected_tags:
            db.execute('INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)',
                      (note_id, tag_map[tag_name]))
    
    # Insert welcome note
    welcome_content = """# 👋 歡迎使用 Prism

這是一個**示範資料庫**，包含 50 則預先生成的筆記，讓你快速體驗 Prism 的功能。

## 快速開始

- **瀏覽筆記**: 使用左側分類過濾，或使用搜尋欄位
- **編輯筆記**: 點擊任何卡片進入編輯模式
- **Prompt Builder**: 點擊頂部選單進入結構化提示詞組裝器

## 使用此 Demo

這個資料庫僅供體驗用途。當你準備好開始使用自己的資料時：

1. 將 `demo_db/knowledge_demo.db` 複製到專案根目錄
2. 重新命名為 `knowledge.db`
3. 重新啟動應用程式

> 💡 提示：在編輯器中按 **Ctrl+V** 可直接貼上螢幕截圖或圖片！
"""
    
    db.execute('''
        INSERT INTO Notes (title, content, type, category_id, is_pinned, remarks)
        VALUES (?, ?, ?, ?, 1, ?)
    ''', ('👋 歡迎使用 Prism', welcome_content, '教學 | Tutorial', cat_map['教學 | Tutorial'], '必讀！'))
    
    welcome_id = db.lastrowid
    db.execute('INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)', (welcome_id, tag_map['Tutorial']))
    
    conn.commit()
    
    # Verify
    db.execute('SELECT COUNT(*) FROM Notes')
    note_count = db.fetchone()[0]
    
    db.execute('SELECT COUNT(*) FROM Tags')
    tag_count = db.fetchone()[0]
    
    print(f"[SUCCESS] Demo database created!")
    print(f"  - Notes: {note_count}")
    print(f"  - Tags: {tag_count}")
    print(f"  - Path: {DEMO_DB_PATH}")
    
    conn.close()
    
    return DEMO_DB_PATH


if __name__ == '__main__':
    create_demo_db()
