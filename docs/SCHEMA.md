# Prism — 資料庫綱要 (Database Schema)

> **用途**: 共享資料綱要 — 所有資料表的現行定義，開發時的唯一真實來源。
> **版本**: Migration v17 (Default category identity)
> **最後更新**: 2026-07-05
> **改 DB 前必讀**: Go runtime 是唯一 migration owner；新增欄位請在 `go-shadow/main.go` 的 ordered migration list 追加 migration，並更新本文件與對應 regression tests。

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
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,
    icon          TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    is_default    BOOLEAN NOT NULL DEFAULT 0,
    system_key    TEXT UNIQUE,
    name_override TEXT,
    CHECK (system_key IS NULL OR system_key IN ('prompt', 'note', 'tutorial', 'data', 'inspiration'))
)
```

```sql
CREATE UNIQUE INDEX idx_categories_system_key
    ON Categories(system_key)
    WHERE system_key IS NOT NULL;
```

| 欄位 | 說明 |
|------|------|
| `name` | legacy canonical name；系統分類 seed 仍保留 `提示詞 \| Prompt` 等固定值，作匯入/舊資料相容，不是目前 UI 顯示名稱 |
| `system_key` | 五個系統分類身份：`prompt` / `note` / `tutorial` / `data` / `inspiration`；一般自訂分類為 `NULL`；前端以此欄位決定多語系預設顯示 |
| `name_override` | 使用者改名後的固定顯示文字；`NULL` / 空值代表依目前語系顯示系統分類預設名 |
| `is_default` | 只代表刪除分類時的搬移目標；不代表系統分類身份 |

**預設種子資料與顯示名稱**:

Fresh DB init 時由 `go-shadow/main.go` 的 `defaultCategorySeeds` 建立 DB seed；可見 UI 文字由 `frontend/src/utils/categoryDisplay.ts` 依 `system_key` 轉到 `categoryDefaults.*` 多語系字串。系統分類在沒有 `name_override` 時不直接顯示 `name` 的 `提示詞 | Prompt`。

| DB `name`（legacy canonical） | system_key | zh-TW display | en display | ja display | ko display | icon | sort_order | is_default |
|------|------------|---------------|------------|------------|------------|------|------------|------------|
| 提示詞 \| Prompt | `prompt` | 提示詞 | Prompt | プロンプト | 프롬프트 | 🎨 | 1 | 0 |
| 筆記 \| Note | `note` | 筆記 | Note | ノート | 노트 | 📝 | 2 | **1** |
| 教學 \| Tutorial | `tutorial` | 教學 | Tutorial | チュートリアル | 튜토리얼 | 📚 | 3 | 0 |
| 資料 \| Data | `data` | 資料 | Data | データ | 데이터 | 💾 | 4 | 0 |
| 靈感 \| Inspiration | `inspiration` | 靈感 | Inspiration | インスピレーション | 영감 | 💡 | 5 | 0 |

顯示規則：

- `system_key` 有值且 `name_override` 為空：依目前 locale 顯示 `categoryDefaults.*`，例如中文 `提示詞`、英文 `Prompt`、日文 `プロンプト`、韓文 `프롬프트`。
- `system_key` 有值且 `name_override` 有值：顯示 `name_override`，不再隨語系切換。
- 沒有 `system_key` 的自訂分類：顯示 `name`。
- `提示詞 | Prompt` 這類 legacy `name` 仍用於舊資料 / 匯入 / fallback matching，不應當成新版 UI label。

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
-- key='schema_version', value='17'
```

> T042-T044 後，live/default DB migration owner 已是 Go primary runtime。Python migration source 已於 T053 移除；Go runtime 為唯一 migration owner。

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

**Current schema status**:

- Fresh DB init 與 existing DB migration runner 皆由 Go primary runtime 擁有；`Schema_Meta schema_version` current value 為 `17`。
- v17 唯一 schema delta 是 `Categories.system_key` / `name_override` 與 `idx_categories_system_key`，用來固定五個系統分類 identity 與使用者改名語意。
- T008-T052 的長版 gate 歷史已歸檔到 `docs/development-history/` 與 `docs/contracts/`；其中早期 v16 / retained-Python / candidate-owner 語句只代表當時 gate 邊界，不是 current schema truth。
- Python backend source 與 Python migration runner 已於 T053 移除；不要再引用 Python `migrations/` 作為現行 schema source。

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

1. 在 `go-shadow/main.go` 的 ordered migration list 追加下一版 migration。
2. 遷移必須可安全重跑或可由 Go migration runner 明確 skip duplicate-column / no-such-column 類相容錯誤；不得依賴已移除的 Python migration source。
3. 更新本文件 Section 1 對應資料表、附錄 migration 歷程與必要的 API / contract 文件。
4. 更新 `docs/ER-DIAGRAM.md`（若關聯關係有變）。
5. 補 fresh DB、existing DB、rollback / idempotency regression tests。

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
| v16 | `normalize_editor_layout` | 將既有 `Notes.editor_layout` 的 `NULL` / 舊值 `full` 正規化為 `single` |
| v17 | `add_category_identity` | `Categories` 新增 `system_key` / `name_override` 與 `idx_categories_system_key`；只回填仍保留完整 legacy seed name 的五個系統分類 |
| v18+ | （預留） | 下一次 Schema 變更接續此版本號 |

> Migration SQL current source：`go-shadow/main.go` 的 `migrationDefinitions` 與 `freshSchemaStatements`。Python `migrations/` source 已於 T053 移除。
