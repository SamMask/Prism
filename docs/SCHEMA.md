# Prism — 資料庫綱要 (Database Schema)

> **用途**: 共享資料綱要 — 所有資料表的現行定義，開發時的唯一真實來源。
> **版本**: Migration v16 (Headless KMS)
> **最後更新**: 2026-06-18
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
-- key='schema_version', value='16'
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
> Go T009/T010 已在 local/copied DB 證明 existing DB migration runner、backup-before-migrate 與 rollback safety；這不新增資料表或欄位，且 does not touch production `knowledge.db`。
> Go T011/T012 已在 local/copied DB 證明 notes read/search/create/update parity，包含 `Notes_FTS` trigger 更新與 failed update rollback；這不等於 live/default notes write owner 已切換，notes delete/actions/batch/history restore/delete/media cleanup 仍是後續 gate。
> Go T013 已在 local/copied DB-and-data 證明 notes single delete 與 batch delete parity，包含 `Notes_FTS` delete trigger、Note_Tags / Source_Urls / Note_History / Note_Attachments 清理、referenced image preserve，以及 `static/uploads` original / `_thumb.webp` companion cleanup；這仍不等於 live/default notes write owner 或 general media cleanup owner 已切換。
> Go T014/T015 已在 local/copied DB 證明 notes pin/archive/duplicate/reorder 與現行 batch type/tags parity，涵蓋 `Notes.is_pinned`、`Notes.is_archived`、`Notes.sort_order`、variant `parent_id`、Note_Tags / Source_Urls 複製、batch category/tag 更新與 rollback/no partial write；沒有新增 schema 或 migration。`POST /api/notes/batch/archive` 目前不是 Python API route，因此不被寫成 Go-owned surface。
> Go T016/T017 已在 local/copied DB 證明 notes history list/restore/delete-history 與 categories create/update/delete/default-delete guard/sort_order parity，涵蓋 `Note_History` 備份/刪除、`Notes.content` restore、`Categories.name` / `icon` / `sort_order`、default category 保護，以及 in-use category 對 `Notes.category_id` 的 target migration；沒有新增 schema 或 migration，live/default notes/taxonomy owner 仍未切換。
> Go T018 已在 local/copied DB 證明 tags rename/delete/merge parity，涵蓋 `Tags.name` route-level `COLLATE NOCASE` lookup、`Note_Tags` delete-time cleanup、merge transfer `INSERT OR IGNORE`、source tag deletion、missing target rollback/no mutation，以及 notes tag assignment path 的 NOCASE auto-create guard；沒有新增 schema 或 migration，live/default taxonomy owner 仍未切換。
> Go T019 已在 local/copied DB-and-files 證明 attachments metadata list/upload/delete parity，涵蓋 `Note_Attachments` row create/delete、`docs/attachments` copied file write/delete、missing-file delete still removes DB row、missing-note validation order，以及 unsupported extension validation；沒有新增 schema 或 migration，live/default files owner 仍未切換，raw/binary serving 與 long-content separate/restore 仍是後續 gate。
> Go T020-T023 已在 local/copied DB/data fixtures 證明 attachment raw/text/binary serving、`POST /api/upload`、thumbnail `_thumb.webp` generation、`thumbnail_only`、以及 `POST /api/upload/url` remote fetch safety；這些 gate 不新增資料表或欄位，SQLite 仍維持 v16，live/default files/uploads owner 仍未切換，upload delete、cleanup、import/export、server/system 仍是後續 gate。
> Go T024-T027 已在 local/copied DB/data fixtures 證明 upload delete reference check、orphan images scan/delete、originals cleanup rewrite/delete、broken images scan/fix；Go T024-T027 不新增資料表或欄位，SQLite 仍維持 v16，live/default uploads/media cleanup owner 仍未切換，import/export、server/system 與 production/Pi cutover 仍是後續 gate。
> Go T028-T031 已在 local/copied DB/data fixtures 證明 Markdown/JSON import、JSON/Markdown export、DB download、images bundle 與 batch markdown/assets zip；這些 gate 不新增資料表或欄位，SQLite 仍維持 v16，live/default import/export owner 仍未切換，server/system、backup management、full workflow E2E 與 production/Pi cutover 仍是後續 gate。
> Go T032-T035 已在 local/copied DB/data fixtures 證明 server status/hardware/logs、backup list/download/rotate/delete、port/startup config、prompt options 與 wizard options runtime surface；這些 gate 不新增資料表或欄位，SQLite 仍維持 v16。`--enable-server-system` 可對 copied DB 執行 WAL checkpoint / VACUUM / clear-history 類維護，所以不是 default query-only 模式；live/default server/system owner、實際 host service restart、production/Pi cutover 仍未切換。
> Go T036/T037/T038 已在 local/copied DB/data fixtures 證明 embedded SPA/static uploads serving、安全邊界與 full workflow E2E；這些 gate 不新增資料表或欄位，SQLite 仍維持 v16。Full workflow 只驗證既有 Notes / Tags / Source_Urls / Note_History / uploads / backups / Schema_Meta 行為，live/default Go primary ownership、production/Pi cutover 與 Python removal 仍未切換。
> Go T039/T040/T041 已在 package/Pi staging 證明 Windows artifact fresh DB smoke、linux/arm64 artifact copied production DB/data staging smoke、以及 staging service active；這些 gate 不新增資料表或欄位，SQLite 仍維持 v16。Pi staging 使用 `knowledge_t041_staging.db` 與 copied uploads/attachments，live `knowledge.db` SHA256 必須不變；live/default Caddy/systemd ownership、rollback、soak 與 Python removal 仍未切換。
> Go T042/T043/T044 已在 Pi live/default 完成 Go primary cutover、rollback drill 與 bounded soak；這些 gate 不新增資料表或欄位，SQLite 仍維持 v16。T042/T044 使用 live `knowledge.db` 與 external data dir `/home/mask070924/prism`，T043 以 SQLite online backup artifact 與 uploads/attachments tar restore 作 rollback 證據；final state 是 Go primary active、Python `prism.service` inactive。
> Go T045 已移除 Python packaged runtime 與產品啟動路徑；這同樣不新增資料表或欄位，SQLite 仍維持 v16。Python backend source / `requirements*.txt` 只保留為 legacy source/dev/test context，最終刪除或封存留給 T053。
> Go T046-T050 補齊 frontend 實際呼叫的漏接 route：prompt metadata extraction、長文自動分離/還原、system check-update、wizard options API path 與 static config fallback guard。這些變更只使用既有 `Notes` / `Note_Attachments` / external data dir `docs/notes` contract，不新增資料表、欄位、索引或 migration，SQLite 仍維持 v16。
> Go T051 刷新 route ownership manifest、API reference 與部署/schema wording；這是 current-truth documentation gate，不新增資料表、欄位、索引或 migration。舊 T008-T041 段落中的「未切 live/default」語句是當時 gate 邊界；目前產品 runtime / Pi live default owner 已是 Go primary；Python backend source 已於 T053 移除。
> Go T052 清理 stale tracked packaging/root artifacts（embedded Python zip、Pillow wheel、root empty package-lock）；這不改 DB schema、不碰 `knowledge.db`、WAL/SHM、`static/uploads`、`docs/attachments`、`docs/notes` 或 backups。

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
| v16 | `normalize_editor_layout` | 將既有 `Notes.editor_layout` 的 `NULL` / 舊值 `full` 正規化為 `single` |
| v17+ | （預留） | 下一次 Schema 變更接續此版本號 |

> **v14 完整 SQL** 見 `migrations/__init__.py` 的 `strip_ai_features` tuple。
