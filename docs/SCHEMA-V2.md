# Prism V2 - Database Schema Specification (Draft)

**版本**: v2.0-Draft
**繼承自**: v1.3.0 (`docs/SCHEMA.md`)
**重點**: 支援向量搜尋 (Vector Search)、AI 元數據 (Metadata)、圖譜關聯 (Graph)。

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

| 欄位名 | 類型 | 說明 |
| :--- | :--- | :--- |
| `id` | INTEGER PK | |
| `task_type` | TEXT | 'embedding', 'transcription', 'tagging' |
| `status` | TEXT | 'pending', 'processing', 'completed', 'failed' |
| `payload` | TEXT | JSON, 任務參數 (target_ids, settings) |
| `result` | TEXT | JSON, 執行結果或錯誤訊息 |
| `created_at` | DATETIME | |

### 1.4 AI API 端點 (已實作)

> **實作位置**: `services/ai_service.py`, `routes/ai.py`
> **前置需求**: Ollama 服務運行中 (http://localhost:11434)

| 端點 | 方法 | 說明 |
| :--- | :--- | :--- |
| `/api/ai/status` | GET | 檢查 Ollama 服務狀態與已安裝模型 |
| `/api/ai/tag_image` | POST | 分析圖片並回傳建議標籤 (LLaVA) |
| `/api/ai/summarize` | POST | 生成文字摘要 (Llama) |
| `/api/ai/analyze_note` | POST | 分析整個筆記內容與圖片 |

### 1.5 Note_Attachments (筆記附件表)

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

