"""
Prism - 本機端 AI 提示詞與知識管理中樞
Flask 應用入口與資料庫初始化 (Blueprint 架構)

V2: Headless API + React SPA 支援
"""

import os
import sys
import sqlite3
from flask import Flask, g, render_template, jsonify, send_from_directory, abort, current_app
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
    if isinstance(env_name, str):
        app.config.from_object(config[env_name])
    else:
        app.config.from_object(env_name)
    
    # [Fix] 強制重新讀取環境變數或偵測打包模式
    is_frozen = getattr(sys, 'frozen', False)  # PyInstaller 打包後
    v2_env = os.environ.get('PRISM_V2', '').lower().strip() in ('true', '1', 'yes')
    
    if is_frozen or v2_env:
        app.config['V2_MODE'] = True
        print("[INFO] V2 Mode enabled (React SPA)")

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
            
            # 無 Origin/Referer 的請求：生產模式下拒絕，開發模式放行 (curl/Postman)
            if not origin and not referer:
                is_prod = current_app.config.get('V2_MODE') and not current_app.debug
                if is_prod:
                    app.logger.warning('[CSRF] Blocked anonymous unsafe request in production mode')
                    abort(403, description='CSRF validation failed: Origin header required')
                return
            
            # 驗證 Origin 或 Referer 是否為本機
            host_url = request.host_url.rstrip('/')  # e.g., http://127.0.0.1:5000
            allowed_origins = [
                host_url,
                host_url.replace('http://', 'https://'),  # Caddy HTTPS termination
                host_url.replace('127.0.0.1', 'localhost'),
                host_url.replace('localhost', '127.0.0.1'),
                # V2: Allow Vite dev server (ports 5173-5174)
                'http://localhost:5173',
                'http://127.0.0.1:5173',
                'http://localhost:5174',
                'http://127.0.0.1:5174',
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
    # V2: React SPA 或 V1: Jinja2 模板
    # ===================================================================
    v2_mode = app.config.get('V2_MODE')
    
    if v2_mode:
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
    
    # ===================================================================
    from routes import register_blueprints
    register_blueprints(app)

    # V1 Fallback (Only if V2 is not enabled)
    if not v2_mode:
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

# [P1 Fix 2024-12-17] 刪除重複的 get_db()，統一使用 db.py 的版本
# 原因: db.py 的版本有 Foreign Keys 驗證，這裡的版本沒有
# 參見: Linus Analysis Report Bug #1 (Dual Source of Truth)

def init_db():
    """
    初始化資料庫結構
    
    v1.0: 使用版本化遷移系統，取代 if 分支堆疊
    """
    from db import get_db  # 使用統一的 get_db
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
                remarks TEXT,
                cover_image TEXT,
                cover_position TEXT DEFAULT 'top',
                is_pinned BOOLEAN NOT NULL DEFAULT 0,
                is_archived BOOLEAN NOT NULL DEFAULT 0,
                sort_order INTEGER,
                category_id INTEGER,
                prompt_params TEXT,
                editor_layout TEXT DEFAULT 'single',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Phase 0: idx_notes_type removed - Notes.type 欄位已在 Migration v12 中移除
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
            # 取得 '教學' 分類 ID
            cat_cursor = db.execute("SELECT id FROM Categories WHERE name LIKE '%教學%' LIMIT 1")
            cat_result = cat_cursor.fetchone()
            # 若找不到則使用 ID 3 (預設) 或 NULL
            welcome_cat_id = cat_result[0] if cat_result else 3

            db.execute('''
                INSERT INTO Notes (title, content, category_id, remarks, created_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (welcome_title, welcome_content, welcome_cat_id, '系統自動生成'))
            
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
    2. NULL category_id 設為預設分類
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
        
        # 2. (已移除) Notes.type 同步邏輯 - Phase 0 Step 5 移除
        
        # 3. NULL category_id 設為預設分類
        default_cat = db.execute('''
            SELECT id, name FROM Categories WHERE is_default = 1 LIMIT 1
        ''').fetchone()
        
        if default_cat:
            cursor = db.execute('''
                UPDATE Notes 
                SET category_id = ?
                WHERE category_id IS NULL
            ''', (default_cat[0],))
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
    R-01: 智能端口搜尋 (v1.5.0)
    1. 先讀取 .port_config 中的偏好端口
    2. 嘗試偏好端口，若被佔用則自動遞增嘗試
    3. 支援自訂 fallback 範圍
    """
    import socket
    import json
    
    # 讀取用戶端口設定
    config_path = os.path.join(os.path.dirname(__file__), '.port_config')
    fallback_enabled = True
    fallback_range = max_attempts
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                port_config = json.load(f)
            start_port = port_config.get('preferred_port', start_port)
            fallback_enabled = port_config.get('fallback_enabled', True)
            fallback_range = port_config.get('fallback_range', max_attempts)
            fb_status = '開' if fallback_enabled else '關'
            print(f"[INFO] 讀取端口設定: 偏好端口={start_port}, 自動備用={fb_status}, 備用範圍={fallback_range}")
        except Exception as e:
            print(f"[WARNING] 讀取端口設定失敗: {e}")
    
    # 嘗試綁定端口
    actual_range = fallback_range if fallback_enabled else 1
    for port in range(start_port, start_port + actual_range):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return port
        except OSError as e:
            error_code = getattr(e, 'winerror', None) or e.errno
            if error_code == 10013:
                print(f"[WARNING] Port {port} 被 Windows 保留或權限不足 (WinError 10013)，跳過")
            else:
                print(f"[WARNING] Port {port} 被佔用 (Error: {error_code})，跳過")
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

    # R-01: 智能端口搜尋 (v1.5.0: 讀取 .port_config)
    env_port = int(os.environ.get('PORT', 5000))
    port = find_available_port(env_port, max_attempts=20)
    
    if port is None:
        print(f"[ERROR] 無法找到可用端口，請在設定中調整端口範圍")
        app.logger.error(f"無法找到可用端口")
        exit(1)
    
    if port != env_port:
        print(f"[WARNING] Port {env_port} 不可用，自動切換至 Port {port}")
        app.logger.warning(f"Port {env_port} 不可用，自動切換至 Port {port}")
    
    # 讀取 Debug 設定
    debug = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    
    # 啟動訊息
    startup_msg = f"Prism 啟動 (Env: {env}, Port: {port}, Debug: {debug})"
    print(f"[INFO] {startup_msg}")
    print(f"[INFO] 日誌位置: {log_file}")
    print(f"[INFO] 訪問網址: http://127.0.0.1:{port}/")
    app.logger.info(startup_msg)
    
    # 啟動應用
    host = os.environ.get('HOST', '127.0.0.1')
    
    # PyWebView 桌面模式 (打包後自動啟用)
    is_frozen = getattr(sys, 'frozen', False)
    desktop_env = os.environ.get('PRISM_DESKTOP', '').lower() in ('1', 'true', 'yes')
    use_webview = is_frozen or desktop_env
    
    if use_webview:
        try:
            import webview
            import threading
            
            # 在背景線程啟動 Flask
            def start_flask():
                app.run(host=host, port=port, debug=False, use_reloader=False)
            
            flask_thread = threading.Thread(target=start_flask, daemon=True)
            flask_thread.start()
            
            # 等待 Flask 啟動
            import time
            time.sleep(1)
            
            # 建立 PyWebView 視窗
            print("[INFO] 啟動桌面模式 (PyWebView)")
            webview.create_window(
                'Prism - 知識管理中樞',
                f'http://127.0.0.1:{port}/',
                width=1280,
                height=800,
                min_size=(800, 600)
            )
            webview.start()
        except ImportError:
            print("[WARNING] pywebview 未安裝，使用瀏覽器模式")
            print("[INFO] 安裝方式: pip install pywebview")
            app.run(host=host, port=port, debug=debug)
    else:
        if host == '0.0.0.0':
            print(f"[WARNING] 綁定到所有網路介面 (0.0.0.0)。請確保您信任此網路環境！")
            app.logger.warning("Binding to all interfaces (0.0.0.0). Ensure you trust this network!")
        
        app.run(host=host, port=port, debug=debug)

