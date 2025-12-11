"""
Local Insight - 本機端 AI 提示詞與知識管理中樞
Flask 應用入口與資料庫初始化 (Blueprint 架構)
"""

import os
import sqlite3
from flask import Flask, g, render_template, jsonify
from config import config

from werkzeug.exceptions import HTTPException

# ===================================================================
# Flask App 設定
# ===================================================================

# 修改 Jinja2 分隔符以避免與 Vue.js 的 {{ }} 衝突
class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        variable_start_string='[{',
        variable_end_string='}]',
    ))

def create_app(env_name='default'):
    """
    Application Factory 模式
    """
    app = CustomFlask(__name__)
    
    # 載入配置
    app.config.from_object(config[env_name])
    
    # 確保上傳目錄存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 開發環境：禁用緩存
    @app.after_request
    def after_request(response):
        if app.config.get('DEBUG') or os.getenv('FLASK_DEBUG', 'False').lower() == 'true':
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    # 註冊資料庫關閉事件 (v0.8.9: 使用統一資料庫層)
    from db import close_db
    app.teardown_appcontext(close_db)

    # 全局錯誤處理
    @app.errorhandler(Exception)
    def handle_exception(e):
        # 處理 HTTP 錯誤 (如 404, 403 等) - 避免被轉為 500
        if isinstance(e, HTTPException):
            return jsonify({'status': 'error', 'message': e.description}), e.code

        # 即使在非 DEBUG 模式下，也將錯誤記錄到控制台以供診斷
        if not app.config.get('DEBUG'):
            import traceback
            print(f"[ERROR] Internal Server Error: {traceback.format_exc()}")
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
        
        # DEBUG 模式下返回詳細錯誤
        return jsonify({'status': 'error', 'message': str(e)}), 500

    # ===================================================================
    # 註冊 Blueprints
    # ===================================================================
    from routes import register_blueprints
    register_blueprints(app)

    # ===================================================================
    # 首頁路由 (Frontend Entry Points)
    # ===================================================================
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/prompt-builder')
    def prompt_builder():
        return render_template('prompt-builder.html')
    
    @app.route('/favicon.ico')
    def favicon():
        return '', 204
    
    @app.route('/api/test')
    def test_api():
        return jsonify({'status': 'success', 'message': 'Local Insight API is running!'})

    return app

# ===================================================================
# 資料庫連線與初始化 (供 Application Context 使用)
# ===================================================================

def get_db():
    """取得資料庫連線"""
    if 'db' not in g:
        from flask import current_app
        try:
            g.db = sqlite3.connect(
                current_app.config['DATABASE'],
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys = ON')
            g.db.execute('PRAGMA journal_mode = WAL')  # v0.8.9: 啟用 WAL 模式提升效能
        except sqlite3.Error as e:
            print(f"[ERROR] 資料庫連線失敗: {e}")
            raise
    return g.db

def init_db():
    """
    初始化資料庫結構
    
    v1.0: 使用版本化遷移系統，取代 if 分支堆疊
    """
    db = get_db()
    try:
        # ===================================================================
        # 核心資料表建立 (冪等操作)
        # ===================================================================
        
        # 1. Notes 表 (完整欄位 - v1.0)
        db.execute('''
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
            )
        ''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_notes_type ON Notes(type)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON Notes(updated_at DESC)')

        # 2. Source_Urls 表
        db.execute('''
            CREATE TABLE IF NOT EXISTS Source_Urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
            )
        ''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_source_urls_note_id ON Source_Urls(note_id)')

        # 3. Tags 表
        db.execute('''
            CREATE TABLE IF NOT EXISTS Tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
            )
        ''')
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_name ON Tags(name COLLATE NOCASE)')

        # 4. Note_Tags 表
        db.execute('''
            CREATE TABLE IF NOT EXISTS Note_Tags (
                note_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (note_id, tag_id),
                FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES Tags(id) ON DELETE CASCADE
            )
        ''')

        # 5. Categories 表 (v0.6)
        db.execute('''
            CREATE TABLE IF NOT EXISTS Categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_default BOOLEAN NOT NULL DEFAULT 0
            )
        ''')

        # 6. Note_History 表 (v0.6)
        db.execute('''
            CREATE TABLE IF NOT EXISTS Note_History (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                diff_summary TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
            )
        ''')
        db.execute('CREATE INDEX IF NOT EXISTS idx_note_history_note_id ON Note_History(note_id)')

        # 7. FTS5 全文檢索
        db.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS Notes_FTS USING fts5(
                title, content,
                content='Notes',
                content_rowid='id'
            )
        ''')

        # 8. FTS Triggers
        db.execute('''
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON Notes BEGIN
                INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
            END;
        ''')
        db.execute('''
            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON Notes BEGIN
                INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
            END;
        ''')
        db.execute('''
            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON Notes BEGIN
                INSERT INTO Notes_FTS(Notes_FTS, rowid, title, content) VALUES('delete', old.id, old.title, old.content);
                INSERT INTO Notes_FTS(rowid, title, content) VALUES (new.id, new.title, new.content);
            END;
        ''')

        # 9. 預設分類種子數據
        default_categories = [
            ('提示詞', '🎨', 1, 0),
            ('筆記', '📝', 2, 1),   # 筆記為預設分類
            ('教學', '📚', 3, 0),
            ('資料', '💾', 4, 0),
            ('靈感', '💡', 5, 0)
        ]
        db.executemany('''
            INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default)
            VALUES (?, ?, ?, ?)
        ''', default_categories)

        # 10. 預設歡迎筆記 (Seed Note)
        cursor = db.execute('SELECT COUNT(*) FROM Notes')
        if cursor.fetchone()[0] == 0:
            welcome_title = "👋 歡迎使用 Local Insight"
            welcome_content = """# 歡迎使用 Local Insight

這是一個本地運行的個人知識庫與 AI 提示詞管理工具。

## 快速上手

- **新增筆記**：點擊左上角「新增筆記」按鈕。
- **Prompt Builder**：點擊側邊欄「Prompt Builder」建立結構化提示詞。
- **搜尋**：支援全文檢索，輸入關鍵字即可快速找到筆記。

## Markdown 支援

支援標準 Markdown 語法，例如：

- **粗體**、*斜體*
- [連結](https://example.com)
- 程式碼區塊
- 引用

## 關於資料

所有資料皆儲存在本地端的 `knowledge.db` 資料庫中，您可以隨時備份此檔案。
"""
            db.execute('''
                INSERT INTO Notes (title, content, type, remarks, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (welcome_title, welcome_content, '教學', '系統自動生成'))
            
            # 取得剛插入的 Note ID
            cursor = db.execute('SELECT last_insert_rowid()')
            note_id = cursor.fetchone()[0]

            # 自動加上 'Welcome' 標籤
            db.execute("INSERT OR IGNORE INTO Tags (name) VALUES ('Welcome')")
            cursor = db.execute("SELECT id FROM Tags WHERE name = 'Welcome'")
            tag_id = cursor.fetchone()[0]
            db.execute("INSERT INTO Note_Tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id))

            print("[INFO] 已建立預設歡迎筆記")

        db.commit()
        
        # ===================================================================
        # 版本化遷移 (v1.0: 取代 if 分支堆疊)
        # ===================================================================
        from migrations import run_migrations
        run_migrations(db)
        
        print("[INFO] 資料庫初始化完成")

    except sqlite3.Error as e:
        print(f"[ERROR] 資料庫初始化失敗: {e}")

# ===================================================================
# 程式進入點
# ===================================================================

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'default')
    app = create_app(env)
    
    # 初始化資料庫
    with app.app_context():
        init_db()

    # 讀取環境變數 'PORT'，如果沒有設定，預設就用 5000
    port = int(os.environ.get('PORT', 5000))
    
    # 讀取 Debug 設定
    debug = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    
    # 啟動應用
    print(f"[INFO] 啟動 Local Insight (Environment: {env}, Port: {port}, Debug: {debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)
