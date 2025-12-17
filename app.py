"""
Prism - 本機端 AI 提示詞與知識管理中樞
Flask 應用入口與資料庫初始化 (Blueprint 架構)

V2: Headless API + React SPA 支援
"""

import os
import sqlite3
from flask import Flask, g, render_template, jsonify, send_from_directory, abort
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
    # CSRF 防護 (v1.3: MVP Audit 2025-12-13)
    # ===================================================================
    @app.before_request
    def csrf_protect():
        """
        簡易 CSRF 防護：驗證 Origin/Referer 標頭
        - 僅對 POST/PUT/DELETE 等狀態變更請求生效
        - 允許同源請求 (localhost/127.0.0.1)
        - 允許無 Origin 的本機請求 (如 curl)
        """
        from flask import request, abort
        
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            origin = request.headers.get('Origin')
            referer = request.headers.get('Referer')
            
            # 無 Origin/Referer 的請求 (如 curl/Postman) 放行
            if not origin and not referer:
                return
            
            # 驗證 Origin 或 Referer 是否為本機
            host_url = request.host_url.rstrip('/')  # e.g., http://127.0.0.1:5000
            allowed_origins = [
                host_url,
                host_url.replace('127.0.0.1', 'localhost'),
                host_url.replace('localhost', '127.0.0.1'),
                # V2: Allow Vite dev server (port 5173)
                'http://localhost:5173',
                'http://127.0.0.1:5173',
            ]
            
            origin_valid = origin and any(origin.startswith(o) for o in allowed_origins)
            referer_valid = referer and any(referer.startswith(o) for o in allowed_origins)
            
            if not origin_valid and not referer_valid:
                app.logger.warning(f"[CSRF] Blocked request: Origin={origin}, Referer={referer}")
                abort(403, description='CSRF validation failed: Origin mismatch')


    # Global Template Variables
    @app.context_processor
    def inject_global_vars():
        return dict(
            version=app.config.get('PRISM_VERSION', '2.0.0-dev'),
            is_v2=app.config.get('V2_MODE', False)
        )

    # ===================================================================
    from routes import register_blueprints
    register_blueprints(app)

    # ===================================================================
    # V2: React SPA 或 V1: Jinja2 模板
    # ===================================================================
    if app.config.get('V2_MODE'):
        # V2 Mode: Serve React SPA from frontend/dist
        frontend_dist = app.config.get('FRONTEND_DIST')
        
        # V1 Prompt Builder page (still served via Jinja2 for now)
        @app.route('/prompt-builder.html')
        def prompt_builder_v1():
            return render_template('prompt-builder.html')
        
        @app.route('/')
        @app.route('/<path:path>')
        def serve_spa(path=''):
            # Skip API routes (handled by blueprints)
            if path.startswith('api/'):
                abort(404)
            # Serve static files if they exist
            if path and os.path.exists(os.path.join(frontend_dist, path)):
                return send_from_directory(frontend_dist, path)
            # Otherwise serve index.html for client-side routing
            return send_from_directory(frontend_dist, 'index.html')
        
        print("[V2] React SPA 模式已啟用")
    else:
        # V1 Mode: Traditional Jinja2 templates
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
        """Health check with database statistics"""
        from db import get_db
        try:
            db = get_db()
            notes_count = db.execute('SELECT COUNT(*) FROM Notes').fetchone()[0]
            categories_count = db.execute('SELECT COUNT(*) FROM Categories').fetchone()[0]
            tags_count = db.execute('SELECT COUNT(*) FROM Tags').fetchone()[0]
            return jsonify({
                'status': 'ok',
                'message': 'Prism API is running!',
                'stats': {
                    'notes_count': notes_count,
                    'categories_count': categories_count,
                    'tags_count': tags_count
                }
            })
        except Exception as e:
            return jsonify({'status': 'ok', 'message': 'Prism API is running!', 'error': str(e)})

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

        # 9. 預設分類種子數據 (格式: 中文|English)
        default_categories = [
            ('提示詞 | Prompt', '🎨', 1, 0),
            ('筆記 | Note', '📝', 2, 1),   # 筆記為預設分類
            ('教學 | Tutorial', '📚', 3, 0),
            ('資料 | Data', '💾', 4, 0),
            ('靈感 | Inspiration', '💡', 5, 0)
        ]
        db.executemany('''
            INSERT OR IGNORE INTO Categories (name, icon, sort_order, is_default)
            VALUES (?, ?, ?, ?)
        ''', default_categories)

        # 10. 預設歡迎筆記 (Seed Note)
        cursor = db.execute('SELECT COUNT(*) FROM Notes')
        if cursor.fetchone()[0] == 0:
            welcome_title = "👋 歡迎使用 Prism"
            welcome_content = """# 歡迎使用 Prism

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
        
        # ===================================================================
        # 資料一致性自動修復 (v1.2: 15.3 啟動時靜默修復)
        # ===================================================================
        auto_fix_consistency(db)
        
        print("[INFO] 資料庫初始化完成")

    except sqlite3.Error as e:
        print(f"[ERROR] 資料庫初始化失敗: {e}")


def auto_fix_consistency(db):
    """
    啟動時自動檢查並修復資料一致性問題 (v1.2)
    
    修復項目:
    1. 孤兒 Note_Tags (引用不存在的 Notes)
    2. type 與 category_id 不一致
    3. NULL category_id 設為預設分類
    """
    fixes = []
    
    try:
        # 1. 刪除孤兒 Note_Tags
        cursor = db.execute('''
            DELETE FROM Note_Tags 
            WHERE note_id NOT IN (SELECT id FROM Notes)
        ''')
        if cursor.rowcount > 0:
            fixes.append(f"刪除 {cursor.rowcount} 個孤兒標籤關聯")
        
        # 2. 同步 type 與 category_id
        # 如果 category_id 有值但 type 不匹配，更新 type
        cursor = db.execute('''
            UPDATE Notes 
            SET type = (SELECT name FROM Categories WHERE id = Notes.category_id)
            WHERE category_id IS NOT NULL 
              AND type != (SELECT name FROM Categories WHERE id = Notes.category_id)
        ''')
        if cursor.rowcount > 0:
            fixes.append(f"同步 {cursor.rowcount} 則筆記的 type 欄位")
        
        # 3. NULL category_id 設為預設分類
        default_cat = db.execute('''
            SELECT id, name FROM Categories WHERE is_default = 1 LIMIT 1
        ''').fetchone()
        
        if default_cat:
            cursor = db.execute('''
                UPDATE Notes 
                SET category_id = ?, type = ?
                WHERE category_id IS NULL
            ''', (default_cat[0], default_cat[1]))
            if cursor.rowcount > 0:
                fixes.append(f"修復 {cursor.rowcount} 則筆記的空分類")
        
        if fixes:
            db.commit()
            print(f"[AUTO-FIX] 資料一致性修復: {', '.join(fixes)}")
        
    except Exception as e:
        print(f"[WARNING] 資料一致性檢查失敗: {e}")

# ===================================================================
# 程式進入點
# ===================================================================

def find_available_port(start_port=5000, max_attempts=10):
    """
    R-01: 自動端口搜尋
    如果 start_port 被佔用，自動遞增嘗試直到找到可用端口
    """
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None


def setup_logging(app):
    """
    R-02: 設定檔案日誌
    將錯誤和警告寫入 app.log
    
    v1.4.1: 簡化日誌 - 只記錄 WARNING 以上，移除 HTTP 請求記錄
    """
    import logging
    from logging.handlers import RotatingFileHandler
    
    # 建立日誌 handler（最大 1MB，保留 3 個備份）
    log_file = os.path.join(os.path.dirname(__file__), 'app.log')
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    # v1.4.1: 只記錄 WARNING 以上 (警告、錯誤、嚴重錯誤)
    file_handler.setLevel(logging.WARNING)
    
    # 設定 Flask app logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.WARNING)
    
    # v1.4.1: 移除 werkzeug logger，不記錄每個 HTTP 請求
    # 若需要除錯，可設定環境變數 FLASK_DEBUG=True
    
    return log_file


if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'default')
    app = create_app(env)
    
    # R-02: 設定日誌
    log_file = setup_logging(app)
    
    # 初始化資料庫
    with app.app_context():
        init_db()

    # R-01: 自動尋找可用端口
    preferred_port = int(os.environ.get('PORT', 5000))
    port = find_available_port(preferred_port)
    
    if port is None:
        print(f"[ERROR] 無法找到可用端口 ({preferred_port}-{preferred_port+9})")
        app.logger.error(f"無法找到可用端口 ({preferred_port}-{preferred_port+9})")
        exit(1)
    
    if port != preferred_port:
        print(f"[WARNING] Port {preferred_port} 被佔用，改用 Port {port}")
        app.logger.warning(f"Port {preferred_port} 被佔用，改用 Port {port}")
    
    # 讀取 Debug 設定
    debug = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    
    # 啟動訊息
    startup_msg = f"Prism 啟動 (Env: {env}, Port: {port}, Debug: {debug})"
    print(f"[INFO] {startup_msg}")
    print(f"[INFO] 日誌位置: {log_file}")
    print(f"[INFO] 訪問網址: http://127.0.0.1:{port}/")
    app.logger.info(startup_msg)
    
    # 啟動應用
    # v1.3: 預設綁定 127.0.0.1 (僅本機訪問)，可透過 HOST 環境變數覆蓋
    host = os.environ.get('HOST', '127.0.0.1')
    if host == '0.0.0.0':
        print(f"[WARNING] 綁定到所有網路介面 (0.0.0.0)。請確保您信任此網路環境！")
        app.logger.warning("Binding to all interfaces (0.0.0.0). Ensure you trust this network!")
    
    app.run(host=host, port=port, debug=debug)
