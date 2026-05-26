# -*- coding: utf-8 -*-
"""
Schema Migration System - Local Insight v2.0
版本化遷移系統，消除 if 分支堆疊

用法:
    from migrations import run_migrations
    run_migrations(db)

設計原則:
- 聲明式遷移 (資料驅動，非程式邏輯)
- 冪等操作 (可重複執行不會重複遷移)
- 交易隔離 (單一遷移失敗會回滾)
- 向後相容 (不破壞現有資料)
"""

import sqlite3
from typing import List, Tuple

# ===================================================================
# 遷移定義 (聲明式)
# 格式: (版本號, 遷移名稱, SQL 語句列表)
# ===================================================================

MIGRATIONS: List[Tuple[int, str, List[str]]] = [
    # v0.6.6: 新增置頂功能
    (1, "add_is_pinned", [
        "ALTER TABLE Notes ADD COLUMN is_pinned INTEGER DEFAULT 0",
    ]),
    
    # v0.8.4: 新增封面位置
    (2, "add_cover_position", [
        "ALTER TABLE Notes ADD COLUMN cover_position TEXT DEFAULT 'top'",
    ]),
    
    # v0.8.5: 新增編輯器佈局
    (3, "add_editor_layout", [
        "ALTER TABLE Notes ADD COLUMN editor_layout TEXT DEFAULT 'single'",
    ]),
    
    # v0.8.9: 新增封存功能
    (4, "add_is_archived", [
        "ALTER TABLE Notes ADD COLUMN is_archived INTEGER DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_notes_is_archived ON Notes(is_archived)",
    ]),
    
    # v0.9.0: 新增自訂排序
    (5, "add_sort_order", [
        "ALTER TABLE Notes ADD COLUMN sort_order INTEGER DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_notes_sort_order ON Notes(sort_order)",
        "UPDATE Notes SET sort_order = id WHERE sort_order = 0 OR sort_order IS NULL",
    ]),
    
    # v1.0.0: 新增分類 FK (Phase A)
    (6, "add_category_id", [
        "ALTER TABLE Notes ADD COLUMN category_id INTEGER REFERENCES Categories(id)",
        "CREATE INDEX IF NOT EXISTS idx_notes_category_id ON Notes(category_id)",
    ]),
    
    # v1.0.0: 填充 category_id (根據現有 type 值)
    (7, "populate_category_id", [
        # 根據 type 名稱匹配 category_id
        """
        UPDATE Notes SET category_id = (
            SELECT id FROM Categories WHERE name = Notes.type LIMIT 1
        ) WHERE category_id IS NULL
        """,
        # 為沒有匹配的筆記設定預設分類
        """
        UPDATE Notes SET category_id = (
            SELECT id FROM Categories WHERE is_default = 1 LIMIT 1
        ) WHERE category_id IS NULL
        """,
        # 如果還有 NULL，使用任意分類 (fallback)
        """
        UPDATE Notes SET category_id = (
            SELECT id FROM Categories ORDER BY sort_order LIMIT 1
        ) WHERE category_id IS NULL
        """,
    ]),
    
    # v2.0.0 Phase 3.4: 新增附件系統
    (8, "add_note_attachments", [
        """
        CREATE TABLE IF NOT EXISTS Note_Attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT DEFAULT 'md',
            title TEXT,
            size_bytes INTEGER,
            is_auto_extracted INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_attachments_note_id ON Note_Attachments(note_id)",
    ]),
    
    # v2.0.0 Phase 3.2: 語意搜尋 - Embedding 欄位
    (9, "add_text_embedding", [
        "ALTER TABLE Notes ADD COLUMN text_embedding BLOB",
        "ALTER TABLE Notes ADD COLUMN embedding_updated_at DATETIME",
    ]),

    # v2.1.0: AI Metadata & Lineage (SCHEMA-V2 Section 2.1)
    (10, "add_ai_metadata_and_lineage", [
        "ALTER TABLE Notes ADD COLUMN ai_summary TEXT",       # AI 生成的摘要
        "ALTER TABLE Notes ADD COLUMN ai_tags TEXT",          # AI 建議的標籤 (JSON Array)
        "ALTER TABLE Notes ADD COLUMN embedding_status TEXT", # 'pending', 'indexed'
        "ALTER TABLE Notes ADD COLUMN parent_id INTEGER REFERENCES Notes(id)", # Prompt Versioning
        "CREATE INDEX IF NOT EXISTS idx_notes_parent_id ON Notes(parent_id)",
    ]),
    
    # v2.2.0: Embeddings Table (SCHEMA-V2 Section 1.1)
    # 獨立的向量表，支援多資源類型 (notes, images, attachments)
    (11, "create_embeddings_table", [
        """
        CREATE TABLE IF NOT EXISTS Embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_type TEXT NOT NULL,      -- 'note', 'image', 'attachment'
            resource_id INTEGER NOT NULL,     -- 對應 Notes.id / Attachment.id
            chunk_index INTEGER DEFAULT 0,    -- 0=全文, 1,2,3...=長文切塊 (RAG 預留)
            model_name TEXT NOT NULL,         -- e.g., 'all-MiniLM-L6-v2'
            vector BLOB NOT NULL,             -- 二進位向量數據
            content_hash TEXT,                -- MD5 Hash 用於增量更新
            dimensions INTEGER,               -- 向量維度 (e.g., 384)
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(resource_type, resource_id, chunk_index)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_embeddings_resource ON Embeddings(resource_type, resource_id)",
    ]),

    # Phase 0: Kill Notes.type (Architecture Purification)
    # 移除雙重事實 (Double Truth) - type 欄位已由 category_id 取代
    (12, "kill_notes_type", [
        # 1. 最後檢查：確保所有筆記都有 category_id
        """
        UPDATE Notes
        SET category_id = (SELECT id FROM Categories WHERE is_default = 1 LIMIT 1)
        WHERE category_id IS NULL
        """,
        # 2. 如果預設分類不存在，使用第一個分類
        """
        UPDATE Notes
        SET category_id = (SELECT id FROM Categories ORDER BY sort_order LIMIT 1)
        WHERE category_id IS NULL
        """,
        # 3. 移除相關索引與欄位
        "DROP INDEX IF EXISTS idx_notes_type",
        "ALTER TABLE Notes DROP COLUMN type",
    ]),

    # Phase 0 Step 2: Create AI_Tasks table (Proper Task Queue)
    # 取代 ThreadPoolExecutor，實現任務持久化
    (13, "create_ai_tasks_table", [
        """
        CREATE TABLE IF NOT EXISTS AI_Tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,              -- 'embedding', 'transcription', 'tagging'
            status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
            payload TEXT NOT NULL,                 -- JSON, 任務參數 (e.g., {"note_id": 123})
            result TEXT,                           -- JSON, 執行結果或錯誤訊息
            retry_count INTEGER DEFAULT 0,         -- 重試次數 (max 3)
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_ai_tasks_status ON AI_Tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_ai_tasks_type ON AI_Tasks(task_type)",
        "CREATE INDEX IF NOT EXISTS idx_ai_tasks_created ON AI_Tasks(created_at)",
    ]),

    # v2.3.0: Strip AI features — drop AI columns and tables
    # Prism 轉型為純筆記 + Headless KMS，移除所有 AI/Embedding 依賴
    (14, "strip_ai_features", [
        # 1. Drop AI columns from Notes
        "ALTER TABLE Notes DROP COLUMN text_embedding",
        "ALTER TABLE Notes DROP COLUMN embedding_updated_at",
        "ALTER TABLE Notes DROP COLUMN ai_summary",
        "ALTER TABLE Notes DROP COLUMN ai_tags",
        "ALTER TABLE Notes DROP COLUMN embedding_status",
        # 2. Drop AI-related tables
        "DROP TABLE IF EXISTS AI_Tasks",
        "DROP TABLE IF EXISTS Embeddings",
        # 3. Drop related indexes (safe even if already gone)
        "DROP INDEX IF EXISTS idx_ai_tasks_status",
        "DROP INDEX IF EXISTS idx_ai_tasks_type",
        "DROP INDEX IF EXISTS idx_ai_tasks_created",
        "DROP INDEX IF EXISTS idx_embeddings_resource",
    ]),

    # v2.4.3: prompt_params was created in init_db but never backfilled via migration.
    # Existing upgraded databases could therefore miss this column.
    (15, "add_prompt_params", [
        "ALTER TABLE Notes ADD COLUMN prompt_params TEXT",
    ]),
]


# ===================================================================
# 遷移執行器
# ===================================================================

def _ensure_schema_meta(db) -> None:
    """確保 Schema_Meta 表存在"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS Schema_Meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    db.execute(
        "INSERT OR IGNORE INTO Schema_Meta (key, value) VALUES ('schema_version', '0')"
    )
    db.commit()


def get_current_version(db) -> int:
    """取得當前 schema 版本號"""
    try:
        row = db.execute(
            "SELECT value FROM Schema_Meta WHERE key = 'schema_version'"
        ).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.OperationalError:
        # Schema_Meta 表不存在
        return 0


def _column_exists(db, table: str, column: str) -> bool:
    """檢查資料表欄位是否存在"""
    try:
        cursor = db.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        return column in columns
    except sqlite3.OperationalError:
        return False


def _detect_existing_schema(db) -> int:
    """
    偵測現有資料庫已有的欄位，推斷已完成的遷移版本。
    用於首次從 if 分支系統遷移到版本化系統。
    """
    version = 0
    
    # 檢查各個欄位，推斷版本
    if _column_exists(db, 'Notes', 'is_pinned'):
        version = max(version, 1)
    if _column_exists(db, 'Notes', 'cover_position'):
        version = max(version, 2)
    if _column_exists(db, 'Notes', 'editor_layout'):
        version = max(version, 3)
    if _column_exists(db, 'Notes', 'is_archived'):
        version = max(version, 4)
    if _column_exists(db, 'Notes', 'sort_order'):
        version = max(version, 5)
    if _column_exists(db, 'Notes', 'category_id'):
        version = max(version, 7)  # 包含填充
    
    return version


def run_migrations(db) -> int:
    """
    執行所有待處理的遷移
    
    返回: 最終的 schema 版本號
    """
    # 1. 確保 Schema_Meta 表存在
    _ensure_schema_meta(db)
    
    # 2. 取得當前版本
    current = get_current_version(db)
    
    # 3. 首次遷移: 偵測已有欄位，設定初始版本
    if current == 0:
        detected = _detect_existing_schema(db)
        if detected > 0:
            print(f"[Migration] 偵測到現有欄位，設定初始版本為 v{detected}")
            db.execute(
                "UPDATE Schema_Meta SET value = ? WHERE key = 'schema_version'",
                (str(detected),)
            )
            db.commit()
            current = detected
    
    # 4. 執行待處理的遷移
    applied = 0
    for version, name, statements in MIGRATIONS:
        if version > current:
            print(f"[Migration] 執行 v{version:03d}: {name}")
            try:
                for sql in statements:
                    # 跳過空白 SQL
                    sql_clean = sql.strip()
                    if not sql_clean:
                        continue
                    
                    # 執行 SQL
                    try:
                        db.execute(sql_clean)
                    except sqlite3.OperationalError as e:
                        err_msg = str(e).lower()
                        # 欄位已存在的錯誤可以忽略 (冪等性)
                        if "duplicate column name" in err_msg:
                            print(f"  [SKIP] 欄位已存在，跳過")
                            continue
                        # 欄位不存在的錯誤也可以忽略 (DROP COLUMN 冪等性)
                        if "no such column" in err_msg:
                            print(f"  [SKIP] 欄位已不存在，跳過")
                            continue
                        raise
                
                # 更新版本號
                db.execute(
                    "UPDATE Schema_Meta SET value = ? WHERE key = 'schema_version'",
                    (str(version),)
                )
                db.commit()
                applied += 1
                
            except Exception as e:
                db.rollback()
                print(f"[Migration] v{version:03d} 失敗: {e}")
                raise
    
    # 5. 輸出結果
    final = get_current_version(db)
    if applied > 0:
        print(f"[Migration] 完成！執行了 {applied} 個遷移，版本 {current} → {final}")
    else:
        print(f"[Migration] 資料庫已是最新版本 (v{final})")
    
    return final


def get_migration_status(db) -> dict:
    """取得遷移狀態 (用於診斷)"""
    _ensure_schema_meta(db)
    current = get_current_version(db)
    
    pending = []
    completed = []
    
    for version, name, _ in MIGRATIONS:
        if version > current:
            pending.append({'version': version, 'name': name})
        else:
            completed.append({'version': version, 'name': name})
    
    return {
        'current_version': current,
        'latest_version': MIGRATIONS[-1][0] if MIGRATIONS else 0,
        'completed': completed,
        'pending': pending,
    }
