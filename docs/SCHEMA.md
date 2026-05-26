# Prism — 資料庫綱要 (Database Schema)

> **用途**: 共享資料綱要 — 所有資料表的現行定義，開發時的唯一真實來源。
> **版本**: Migration v15 (Headless KMS)
> **最後更新**: 2026-05-05
> **改 DB 前必讀**: 新增欄位請在 `migrations/__init__.py` 追加 Migration，並更新本文件。

---

## 1. 現行資料表

### 1.1 Notes（筆記主體表）

```sql
CREATE TABLE Notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    remarks         TEXT,
    cover_image     TEXT,
    cover_position  TEXT    DEFAULT 'top',    -- 'top' | 'center' | 'bottom'
    editor_layout   TEXT    DEFAULT 'single', -- 'single' | 'dual'
    is_pinned       BOOLEAN NOT NULL DEFAULT 0,
    is_archived     BOOLEAN NOT NULL DEFAULT 0,
    sort_order      INTEGER,
    category_id     INTEGER REFERENCES Categories(id),
    parent_id       INTEGER REFERENCES Notes(id),  -- 卡片譜系 (Prompt Versioning)
    prompt_params   TEXT,                          -- JSON，SD/ComfyUI prompt 參數
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

| 欄位 | 說明 |
|------|------|
| `category_id` | FK → Categories，NULL 表示未分類 |
| `parent_id` | 自參照 FK，`NULL` = 原始卡片，有值 = 某卡片的變體 |
| `prompt_params` | JSON 字串，Prompt Builder 的結構化參數 |
| `cover_position` | 封面圖顯示位置 |
| `editor_layout` | `single`=單欄；`dual`=左圖右文 |
| `sort_order` | 自訂排序用整數（PUT /api/notes/reorder） |

**索引**:
```sql
CREATE INDEX idx_notes_updated_at  ON Notes(updated_at DESC);
CREATE INDEX idx_notes_category_id ON Notes(category_id);
CREATE INDEX idx_notes_sort_order  ON Notes(sort_order);
CREATE INDEX idx_notes_is_archived ON Notes(is_archived);
CREATE INDEX idx_notes_parent_id   ON Notes(parent_id);
```

---

### 1.2 Categories（分類表）

```sql
CREATE TABLE Categories (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    icon       TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_default BOOLEAN NOT NULL DEFAULT 0  -- 唯一預設分類
)
```

**預設種子資料**（init_db 時建立）:

| name | icon | is_default |
|------|------|------------|
| 提示詞 \| Prompt | 🎨 | 0 |
| 筆記 \| Note | 📝 | **1** |
| 教學 \| Tutorial | 📚 | 0 |
| 資料 \| Data | 💾 | 0 |
| 靈感 \| Inspiration | 💡 | 0 |

---

### 1.3 Tags（標籤表）

```sql
CREATE TABLE Tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL UNIQUE COLLATE NOCASE
)
```

```sql
CREATE UNIQUE INDEX idx_tags_name ON Tags(name COLLATE NOCASE);
```

---

### 1.4 Note_Tags（筆記-標籤中間表）

```sql
CREATE TABLE Note_Tags (
    note_id INTEGER NOT NULL,
    tag_id  INTEGER NOT NULL,
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)  REFERENCES Tags(id)  ON DELETE CASCADE
)
```

---

### 1.5 Source_Urls（來源連結表）

```sql
CREATE TABLE Source_Urls (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    url     TEXT    NOT NULL,
    FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
)
```

```sql
CREATE INDEX idx_source_urls_note_id ON Source_Urls(note_id);
```

> API 層以 JSON 陣列形式接收 `source_urls`，後端拆解後寫入此表。

---

### 1.6 Note_History（版本歷史表）

```sql
CREATE TABLE Note_History (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id      INTEGER  NOT NULL,
    content      TEXT     NOT NULL,
    diff_summary TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
)
```

```sql
CREATE INDEX idx_note_history_note_id ON Note_History(note_id);
```

> 每次 PUT /api/notes/:id 自動寫入，每筆最多保留 50 版（舊版自動刪除）。

---

### 1.7 Note_Attachments（附件表）

```sql
CREATE TABLE Note_Attachments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id          INTEGER  NOT NULL,
    file_path        TEXT     NOT NULL,
    file_type        TEXT     DEFAULT 'md',   -- 'md' | 'txt'
    title            TEXT,
    size_bytes       INTEGER,
    is_auto_extracted INTEGER  DEFAULT 0,     -- 1 = 長文自動分離產生
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
)
```

```sql
CREATE INDEX idx_attachments_note_id ON Note_Attachments(note_id);
```

---

### 1.8 Schema_Meta（版本追蹤表）

```sql
CREATE TABLE Schema_Meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
-- 目前唯一紀錄:
-- key='schema_version', value='15'
```

> 由 `migrations/__init__.py` 的 `run_migrations()` 管理，啟動時自動執行待處理遷移。

---

### 1.9 Notes_FTS（全文檢索虛擬表）

```sql
CREATE VIRTUAL TABLE Notes_FTS USING fts5(
    title,
    content,
    content='Notes',
    content_rowid='id'
);

-- 同步 Triggers（INSERT / DELETE / UPDATE 自動維護）
CREATE TRIGGER notes_ai AFTER INSERT ON Notes ...
CREATE TRIGGER notes_ad AFTER DELETE ON Notes ...
CREATE TRIGGER notes_au AFTER UPDATE ON Notes ...
```

> FTS5 純關鍵字全文檢索，無 AI / 向量搜尋。
> `Notes_FTS` 僅索引 `Notes.title` / `Notes.content`。`GET /api/notes?q=...` 的使用者搜尋範圍另由 API 層擴充到 `Notes.remarks`、`Tags.name`、`Note_Attachments.title` / `file_path` 與文字附件檔案內容；此行為不需要新增 DB 欄位或 migration。

---

## 2. 外鍵關係速查

```
Notes ──── category_id ──→ Categories
Notes ──── parent_id ───→ Notes (自參照)
Notes ←─── Note_Tags ───→ Tags
Notes ←─── Note_History
Notes ←─── Note_Attachments
Notes ←─── Source_Urls
Notes ←─── Notes_FTS (虛擬，trigger 同步)
Schema_Meta (獨立，無 FK)
```

---

## 3. 新增欄位流程

1. 在 `migrations/__init__.py` 的 `MIGRATIONS` 列表追加 tuple：
   ```python
   (15, "your_migration_name", [
       "ALTER TABLE Notes ADD COLUMN new_col TEXT",
   ]),
   ```
2. 遷移必須**冪等**（使用 `IF NOT EXISTS` / `IF EXISTS`）
3. 更新本文件 Section 1 對應資料表
4. 更新 `docs/ER-DIAGRAM.md`（若關聯關係有變）

---

## 附錄：Migration 歷程

| 版本 | 名稱 | 說明 |
|------|------|------|
| v1 | `add_is_pinned` | Notes 新增置頂欄位 |
| v2 | `add_cover_position` | Notes 新增封面位置 |
| v3 | `add_editor_layout` | Notes 新增編輯版面 |
| v4 | `add_is_archived` | Notes 新增封存欄位 |
| v5 | `add_sort_order` | Notes 新增自訂排序 |
| v6 | `add_category_id` | Notes 新增分類 FK |
| v7 | `populate_category_id` | 依舊 type 欄位填充 category_id |
| v8 | `add_note_attachments` | 新增 Note_Attachments 表 |
| v9 | `add_text_embedding` | Notes 新增 Embedding 欄位（⚠️ v14 移除）|
| v10 | `add_ai_metadata_and_lineage` | Notes 新增 ai_summary / parent_id 等（⚠️ v14 部分移除）|
| v11 | `create_embeddings_table` | 新增 Embeddings 表（⚠️ v14 DROP）|
| v12 | `kill_notes_type` | 移除 Notes.type 雙重事實欄位 |
| v13 | `create_ai_tasks_table` | 新增 AI_Tasks 表（⚠️ v14 DROP）|
| v14 | `strip_ai_features` | **拔除 AI** — DROP Embeddings / AI_Tasks 表，DROP 5 個 AI 欄位 |
| v15 | `add_prompt_params` | 補上 `Notes.prompt_params` 遷移，修正舊 DB 升級漏欄位問題 |
| v16+ | （預留） | 下一次 Schema 變更接續此版本號 |

> **v14 完整 SQL** 見 `migrations/__init__.py` 的 `strip_ai_features` tuple。
