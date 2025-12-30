# Prism V2 - Database Schema Specification (Draft)

**版本**: v2.0-Draft
**繼承自**: v1.3.0 (`docs/SCHEMA.md`)
**重點**: 支援向量搜尋 (Vector Search)、AI 元數據 (Metadata)、圖譜關聯 (Graph)
**Phase 0 淨化**: 2024-12-30 (移除 `Notes.type` 雙重事實)

---

## 0. Phase 0: 架構淨化記錄 (Architecture Purification Log)

> **更新**: 2024-12-30
> **參考**: `1230-審核報告.md` (Linus Audit), `docs/TODO-V2.md` Phase 0

### 0.1 移除 Notes.type 欄位 (Migration v12)

**問題**:
- `Notes` 表同時保留 `type` (字串) 和 `category_id` (外鍵)
- 造成雙重事實 (Double Truth) 災難
- `crud.py` 需要 `get_category_id_by_name()` 補丁同步兩者

**解決方案**:
```sql
-- Migration v12: Kill Notes.type
-- 1. 確保所有筆記都有 category_id
UPDATE Notes
SET category_id = (SELECT id FROM Categories WHERE name = 'Default' LIMIT 1)
WHERE category_id IS NULL;

-- 2. 移除 type 欄位
ALTER TABLE Notes DROP COLUMN type;
```

**影響範圍**:
- ✅ `crud.py`: 刪除 `get_category_id_by_name()` (L23-41) - **完成**
- ✅ `crud.py`: `create_note()` 改用 `category_id` 參數 - **完成**
- ✅ `crud.py`: `update_note()` 改用 `category_id` 參數 - **完成**
- ✅ `batch.py`: `batch_update_type()` 改用 `category_id` 參數 - **完成**
- ✅ API 端點: 不再接受 `type` 參數，統一使用 `category_id` - **完成**
- ✅ Migration v12: 資料庫層面完成 (type 欄位已移除)
- ✅ `crud.py` `get_note()`: 修復殘留的 `COALESCE(c.name, n.type)` → `COALESCE(c.name, 'Uncategorized')` - **完成 (Post-Audit)**

**Breaking Changes**:
- `POST /api/notes` 現在只接受 `category_id`，不再接受 `type`
- `PUT /api/notes/<id>` 現在只接受 `category_id`，不再接受 `type`
- `POST /api/notes/batch/type` 現在只接受 `category_id`，不再接受 `type`

**狀態**: ✅ Step 0.1 完成 (2024-12-30) - 所有子任務完成，測試通過，Post-Audit 修復完成

### 0.2 實作 AI_Tasks 任務隊列 (Migration v13)

**問題**:
- `_queue_embedding_update()` 在 WSGI 請求生命週期內啟動 `ThreadPoolExecutor`
- 伺服器重啟或 Worker 回收時，執行中的 Thread 被殺，任務丟失
- Schema V2 已定義 `AI_Tasks` 表但未使用 (過度設計了架構但實作懶惰)

**解決方案**:
```sql
-- Migration v13: Create AI_Tasks table
CREATE TABLE AI_Tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,              -- 'embedding', 'transcription', 'tagging'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    payload TEXT NOT NULL,                 -- JSON, 任務參數 (e.g., {"note_id": 123})
    result TEXT,                           -- JSON, 執行結果或錯誤訊息
    retry_count INTEGER DEFAULT 0,         -- 重試次數 (max 3)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_tasks_status ON AI_Tasks(status);
CREATE INDEX idx_ai_tasks_type ON AI_Tasks(task_type);
CREATE INDEX idx_ai_tasks_created ON AI_Tasks(created_at);
```

**實作變更**:

1. **crud.py** (`_queue_embedding_update`):
```python
# 舊版 (ThreadPoolExecutor)
_get_embedding_executor().submit(_do_embedding)

# 新版 (AI_Tasks 持久化)
db.execute("""
    INSERT INTO AI_Tasks (task_type, payload, status)
    VALUES ('embedding', ?, 'pending')
""", (json.dumps({'note_id': note_id, 'title': title, 'content': content}),))
```

2. **workers/task_processor.py** (獨立 Worker):
   - 單次執行模式: `python workers/task_processor.py`
   - 常駐模式: `python workers/task_processor.py --daemon`
   - 失敗重試: Max 3 次
   - 優雅中斷: 支援 SIGINT/SIGTERM

**預期效果**:
- ✅ 任務持久化 (伺服器崩潰不丟失)
- ✅ 可獨立部署 Worker (Docker/Systemd)
- ✅ 支援批次處理 (每次處理 10 個任務)

**狀態**: ✅ Step 0.2 完成 (2024-12-30)

### 0.3 重構查詢邏輯 (get_notes Refactoring)

**問題**:
- `crud.py` 的 `get_notes()` 長達 160 行，混合多種職責
- SQL 動態組裝邏輯散落在函數中，難以維護
- Python 層做 `parse_tags_json()` 和 `parse_urls_json()`，SQLite JSON 功能未充分利用
- FTS5 查詢字串處理 (L135-140) 比較原始

**解決方案**:

1. **建立 NoteQueryBuilder** (`utils/query_builder.py`):
   - Fluent API 設計
   - 每個方法 < 20 行
   - 職責分離: 過濾邏輯獨立

2. **優化 SQL 查詢** - 讓 SQLite 直接返回乾淨的 JSON
3. **FTS5 查詢清洗** - 獨立為 `sanitize_fts_query()` 函數

**實作成果**:

1. **建立 NoteQueryBuilder** (`utils/query_builder.py`):
   - Fluent API 設計 (method chaining)
   - 每個方法 < 20 行
   - 方法: `filter_category()`, `filter_tags()`, `filter_archived()`, `search_fts()`, `filter_pinned()`

2. **優化 SQL 查詢**:
   - 使用 `COALESCE` + `json_array()` 確保乾淨 JSON 輸出
   - 移除 Python 層 `parse_tags_json()` 和 `parse_urls_json()`
   - 改用 `json.loads()` 直接解析 SQLite 返回的 JSON

3. **FTS5 查詢清洗**:
   - 獨立為 `sanitize_fts_query()` 函數
   - 防止 FTS5 注入攻擊
   - 支援多關鍵字模糊搜尋 (`"keyword"*`)

**實際效果**:
- ✅ `get_notes()` 從 160 行重構為 ~150 行 (但邏輯更清晰)
- ✅ 新增過濾條件只需在 QueryBuilder 中改一處
- ✅ 移除 Python 層 JSON 解析，提升性能
- ✅ 保持向後相容 (支援舊版 `type` 參數轉換為 `category_id`)

**狀態**: ✅ Step 0.3 完成 (2024-12-30)

---

## 1. 新增資料表 (New Tables)

### 1.1 Embeddings (向量特徵表)

用於儲存圖片或文字的 CLIP/BERT Embeddings，支撐語意搜尋。
> **Note**: 若使用 ChromaDB，此表可能不需要，但若堅持 Pure SQLite (使用 sqlite-vss)，則需此結構。
> **2024-12 更新**: 根據 Gemini 建議，新增 `chunk_index` 和 `content_hash` 欄位。

| 欄位名 | 類型 | 說明 |
| :--- | :--- | :--- |
| `id` | INTEGER PK | |
| `resource_type` | TEXT | 'note', 'image', 'attachment' |
| `resource_id` | INTEGER | 對應 Notes.id / Attachment.id |
| `chunk_index` | INTEGER | 0=全文/整圖, 1,2,3...=長文切塊 (RAG) |
| `model_name` | TEXT | 使用的模型 (e.g., 'all-MiniLM-L6-v2') |
| `vector` | BLOB | 二進位儲存的向量數據 (numpy array bytes) |
| `content_hash` | TEXT | 內容 Hash，用於判斷是否需重算向量 |
| `dimensions` | INTEGER | 向量維度 (e.g., 384, 512, 768) |
| `created_at` | DATETIME | |

**設計理由**:
- `chunk_index`: 為 RAG 長文切塊預留，長附件可拆成多段向量
- `content_hash`: 避免每次重建索引都重新計算，節省 90% 運算

### 1.2 Note_Edges (知識圖譜關聯表)
用於儲存筆記之間的連接關係 (Graph View)。

| 欄位名 | 類型 | 說明 |
| :--- | :--- | :--- |
| `id` | INTEGER PK | |
| `source_id` | INTEGER FK | 起點筆記 ID |
| `target_id` | INTEGER FK | 終點筆記 ID |
| `relation_type` | TEXT | 關係類型 (e.g., 'relates_to', 'blocks', 'parent_of') |
| `properties` | TEXT | JSON, 儲存線條屬性 (顏色、註解) |

### 1.3 AI_Tasks (AI 任務隊列)

用於管理耗時的 AI 任務 (如影片轉檔、批量 Embedding)。

> **✅ Phase 0 Step 2 已完成 (2024-12-30)**: Migration v13 已建立此表，`_queue_embedding_update` 已改用 AI_Tasks 持久化隊列，取代 ThreadPoolExecutor。詳見 [Section 0.2](#02-實作-ai_tasks-任務隊列-migration-v13)。

| 欄位名 | 類型 | 說明 |
| :--- | :--- | :--- |
| `id` | INTEGER PK | |
| `task_type` | TEXT | 'embedding', 'transcription', 'tagging' |
| `status` | TEXT | 'pending', 'processing', 'completed', 'failed' |
| `payload` | TEXT | JSON, 任務參數 (e.g., `{"note_id": 123}`) |
| `result` | TEXT | JSON, 執行結果或錯誤訊息 |
| `retry_count` | INTEGER | 重試次數 (max 3) |
| `created_at` | DATETIME | 任務建立時間 |
| `updated_at` | DATETIME | 最後處理時間 |

**實作狀態** (Migration v13):
- ✅ 已在 `migrations/__init__.py` 中定義
- ✅ `crud.py` 的 `_queue_embedding_update()` 已使用此表
- ✅ 獨立 Worker (`workers/task_processor.py`) 已實作

**使用方式**:
```bash
# 單次執行 (處理所有待處理任務)
python workers/task_processor.py

# 常駐模式 (持續監控)
python workers/task_processor.py --daemon
```

### 1.4 AI API 端點 (已實作)

> **實作位置**: `services/ai_service.py`, `routes/ai.py`
> **前置需求**: Ollama 服務運行中 (http://localhost:11434)

| 端點 | 方法 | 說明 |
| :--- | :--- | :--- |
| `/api/ai/status` | GET | 檢查 Ollama 服務狀態與已安裝模型 |
| `/api/ai/tag_image` | POST | 分析圖片並回傳建議標籤 (LLaVA) |
| `/api/ai/summarize` | POST | 生成文字摘要 (Llama) |
| `/api/ai/analyze_note` | POST | 分析整個筆記內容與圖片 |
| `/api/ai/batch_tag` | POST | 批次分析筆記標籤 (Async Task) |
| `/api/ai/batch_status/<id>` | GET | 取得批次任務狀態 |
| `/api/ai/batch_stop/<id>` | POST | 停止批次任務 |

### 1.5 圖片清理 API 端點 (已實作)

> **實作位置**: `routes/cleanup.py`
> **前端整合**: `SettingsPage.tsx` 設定頁面「危險區域」

| 端點 | 方法 | 說明 |
| :--- | :--- | :--- |
| `/api/cleanup/orphan-images` | GET | 取得孤兒圖片列表 (未被引用) |
| `/api/cleanup/orphan-images` | DELETE | 刪除指定孤兒圖片 |
| `/api/cleanup/originals` | GET | 取得原圖統計 (有縮圖的原圖) |
| `/api/cleanup/originals` | DELETE | 刪除所有原圖 (保留縮圖) |
| `/api/cleanup/broken-images` | GET | 掃描失效圖片路徑 |
| `/api/cleanup/broken-images` | POST | 修復失效圖片路徑 |

### 1.5.1 系統維護 API 端點 (已實作)

> **實作位置**: `routes/system.py`
> **前端整合**: `SettingsPage.tsx` 設定頁面

| 端點 | 方法 | 說明 |
| :--- | :--- | :--- |
| `/api/system/stats` | GET | 取得系統統計資訊 |
| `/api/system/vacuum` | POST | 執行 VACUUM 壓縮資料庫 |
| `/api/system/wal-checkpoint` | POST | WAL 日誌合併至主資料庫 |
| `/api/system/check-consistency` | GET | 資料一致性檢查 |
| `/api/system/clear-history` | POST | 清空所有歷史版本記錄 |

**check-consistency 回傳格式**:
```json
{
  "orphan_note_tags": 0,      // 孤兒標籤關聯數
  "unused_tags": 0,           // 未使用標籤數
  "type_category_mismatch": 0,// type 與 category_id 不一致
  "null_category_id": 0,      // 缺少 category_id 的筆記
  "fk_enabled": true,         // Foreign Keys 是否啟用
  "health": "healthy"         // 整體健康狀態
}
```


### 1.5.2 Prompt Options API (已實作)

> **實作位置**: `routes/prompt_options.py`
> **儲存方式**: JSON 檔案 (`static/config/prompt_options.json`)

| 端點 | 方法 | 說明 |
| :--- | :--- | :--- |
| `/api/prompt-options` | GET | 讀取完整配置 (Categories, Templates) |
| `/api/prompt-options/category/{key}` | POST | 新增選項至指定類別 |
| `/api/prompt-options/template` | POST | 儲存當前設定為模板 |
| `/api/prompt-options/template/{id}` | DELETE | 刪除模板 |

### 1.6 Note_Attachments (筆記附件表)

> **目的**: 支援大型 .md 文件作為筆記附件，不存入 DB 避免膨脹。
> **RAG 優勢**: 文件可直接被 LangChain/LlamaIndex 載入進行向量化。

| 欄位名 | 類型 | 說明 |
| :--- | :--- | :--- |
| `id` | INTEGER PK | |
| `note_id` | INTEGER FK | 關聯的筆記 ID |
| `file_path` | TEXT NOT NULL | 相對路徑 (e.g., `docs/attachments/xxx.md`) |
| `file_type` | TEXT | 'md', 'txt', 'pdf' |
| `title` | TEXT | 顯示名稱 |
| `size_bytes` | INTEGER | 檔案大小 |
| `is_auto_extracted` | BOOLEAN | 是否為自動分離的長內容 |
| `created_at` | DATETIME | |

**索引**:
```sql
CREATE INDEX idx_attachments_note_id ON Note_Attachments(note_id);
```

**檔案結構**:
```
Prism/
├── docs/
│   ├── notes/           # 自動分離的長筆記
│   │   └── note_{id}.md
│   └── attachments/     # 用戶上傳的附件
│       └── {filename}.md
└── static/uploads/      # 圖片 (現有)
```

### 1.6 Attachment API 端點 (規劃中)

| 端點 | 方法 | 說明 |
| :--- | :--- | :--- |
| `/api/notes/{id}/attachments` | GET | 取得筆記的所有附件 |
| `/api/notes/{id}/attachments` | POST | 上傳附件 (multipart/form-data) |
| `/api/attachments/{id}` | GET | 讀取附件內容 |
| `/api/attachments/{id}` | DELETE | 刪除附件 |
| `/api/notes/{id}/separate` | POST | 自動分離長內容為附件 |

**前端交互**:
- 拖曳 .md 檔案到編輯區自動上傳
- 附件區塊顯示已關聯的文件
- 點擊「+」可瀏覽選擇檔案

### 1.7 自動分離 (Auto-Separation)

> **觸發條件**: 筆記內容超過 5000 字元
> **行為**: 儲存時自動分離 (無彈窗提示)
> **更新日期**: 2024-12-17

| 參數 | 類型 | 說明 |
| :--- | :--- | :--- |
| `threshold` | INTEGER | 分離閾值 (預設 5000 字元) |
| `preview_length` | INTEGER | DB 保留預覽長度 (預設 500 字元) |

**分離流程 (v2 精緻化)**:
1. 使用者儲存筆記時，內容先完整存入 DB
2. 前端檢查 `content.length > threshold`
3. **自動**呼叫 `POST /api/notes/{id}/separate` (無彈窗)
4. 後端執行：
   - 若已存在 `is_auto_extracted=1` 附件 → **更新**檔案內容
   - 若不存在 → 建立 `docs/notes/note_{id}.md` 儲存完整內容
   - 更新 `Notes.content` 為前 500 字 + `\n\n---\n📎 [完整內容已分離為附件]`
5. 前端刷新附件列表 (靜默)

**載入流程 (v2 精緻化)**:
1. 使用者開啟筆記編輯器
2. 前端呼叫 `GET /api/notes/{id}/attachments`
3. 若發現 `is_auto_extracted=1` 附件：
   - 自動呼叫 `GET /api/attachments/{id}` 取得完整內容
   - 將完整內容載入編輯器 (取代 DB 中的預覽)
   - **不刪除附件** (保留供下次儲存時更新)

---

## 2. 現有資料表變更 (Alterations)

### 2.0 🔴 Notes.type 欄位移除 (Phase 0 - The Purge)

> **來源**: `1230-審核報告.md` - Linus Report
> **問題**: `Notes.type` (字串) 與 `category_id` (外鍵) 並存造成「雙重事實」，需要 `get_category_id_by_name()` 這種醜陋的應用層同步補丁。
> **狀態**: 🔴 待執行

**遷移步驟**:

```sql
-- Step 1: 確保所有筆記都有 category_id
-- 找出 category_id 為 NULL 的筆記，根據 type 欄位設定對應 ID
UPDATE Notes
SET category_id = (SELECT id FROM Categories WHERE name = Notes.type)
WHERE category_id IS NULL AND type IS NOT NULL;

-- Step 2: 將剩餘沒有分類的筆記歸入 Default
UPDATE Notes
SET category_id = (SELECT id FROM Categories WHERE name = 'Default' LIMIT 1)
WHERE category_id IS NULL;

-- Step 3: 移除 type 欄位 (SQLite 需要重建表)
-- 建議使用 migrations/purge_notes_type.py 腳本執行
```

**程式碼清理清單**:

| 檔案 | 函式/行號 | 動作 |
|------|-----------|------|
| `routes/notes/crud.py` | `get_category_id_by_name()` L23-41 | 刪除 |
| `routes/notes/crud.py` | `create_note()` 中的 type 處理 | 移除 |
| `routes/notes/crud.py` | `update_note()` 中的 type 處理 | 移除 |
| `routes/notes/crud.py` | `get_notes()` 中的 type 篩選 | 改用 category_id |
| 前端 `api.ts` | 任何 `type` 欄位引用 | 移除 |

**預期效果**:

- 消除資料不一致風險
- 程式碼減少 ~50 行
- 移除應用層同步邏輯

### 2.1 Notes 表擴充

```sql
ALTER TABLE Notes ADD COLUMN ai_summary TEXT;       -- AI 生成的摘要
ALTER TABLE Notes ADD COLUMN ai_tags TEXT;          -- AI 建議的標籤 (JSON Array)
ALTER TABLE Notes ADD COLUMN embedding_status TEXT; -- 'pending', 'indexed'
ALTER TABLE Notes ADD COLUMN parent_id INTEGER REFERENCES Notes(id); -- 來源筆記 ID (Prompt Versioning)
```

### 2.2 Source_Urls 表擴充 (Optional)
若要對網頁進行爬蟲與 Embedding。

```sql
ALTER TABLE Source_Urls ADD COLUMN page_title TEXT;
ALTER TABLE Source_Urls ADD COLUMN page_content_extract TEXT; -- 爬蟲抓取的純文字
```

---

## 3. 虛擬表與全文檢索 (FTS)

升級 FTS5 設定，加入 `ai_summary` 進入搜尋索引。

```sql
-- 重建 FTS Table
DROP TABLE Notes_FTS;
CREATE VIRTUAL TABLE Notes_FTS USING fts5(
    title, 
    content, 
    ai_summary,  -- 新增
    ai_tags,     -- 新增
    content='Notes', 
    content_rowid='id'
);
```

---

## 4. 遷移策略 (Migration Strategy)

1.  **V1 -> V2 Script**: 
    *   Prism V2 首次啟動時，檢查 Schema 版本。
    *   執行 `ALTER TABLE` 語句。
    *   初始化 `Embeddings` 表。
2.  **Re-indexing**:
    *   背景執行緒啟動，掃描所有 `embedding_status IS NULL` 的筆記，進行計算並寫入。

---

**備註**: 對於 "Vector DB"，建議初期先使用 SQLite BLOB 儲存 + 暴力計算 (Cosine Similarity via Python/NumPy)，因為個人知識庫數據量 (通常 < 10萬) 完全撐得住，無需引入複雜的 Vector Index 引擎，保持 "Portable" 特性。

---

## 5. 自動化測試 (Automated Testing)

> **實作完成**: 2024-12-17

### 5.1 測試基礎設施

| 類型 | 目錄 | 工具 | 說明 |
|------|------|------|------|
| API 測試 | `tests/` | pytest | 後端 API 完整測試 |
| E2E 測試 | `e2e/` | Playwright | 前端使用者流程測試 |

### 5.2 測試用 data-testid 屬性

E2E 測試依賴以下 `data-testid` 屬性來定位元素：

| 元件 | data-testid | 位置 |
|------|-------------|------|
| 應用容器 | `app-container` | `Layout.tsx` |
| 頂部欄 | `header` | `Header.tsx` |
| 搜尋輸入框 | `search-input` | `Header.tsx` |
| 搜尋表單 | `search-form` | `Header.tsx` |
| 新增筆記按鈕 | `add-note-button` | `Header.tsx` |
| 側邊欄導航 | `sidebar-nav` | `Sidebar.tsx` |
| 筆記網格 | `notes-grid` | `HomePage.tsx` |
| 筆記卡片 | `note-card-{id}` | `NoteCard.tsx` |

### 5.3 測試執行

```bash
# API 測試 (不需要 Flask)
python -m pytest tests/ -v

# E2E 測試 (需要 V2 模式)
set PRISM_V2=true && python app.py  # 終端 1
python -m pytest e2e/ -v --headed   # 終端 2
```

