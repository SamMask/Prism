# Prism V2 - Modernization & Intelligence Roadmap (TODO-V2)

**狀態**: 🔴 架構淨化中 (Phase 0 in Progress)
**核心目標**: Headless Architecture + Local AI
**文件參照**: `docs/Prism-V2.md` (總體戰略), `docs/SCHEMA-V2.md` (資料庫規格), `1230-審核報告.md` (Linus Audit)
**最後更新**: 2024-12-30 (Phase 0: Architecture Purification)

---

## 🚨 Phase 0: 架構淨化 (Architecture Purification)

> **狀態**: 🔴 執行中 (Critical Priority)
> **來源**: Linus-style 審核報告 (`1230-審核報告.md`)
> **核心理念**: "Bad programmers worry about the code. Good programmers worry about data structures."

### 🎯 目標
在繼續堆砌功能之前，先花時間清理核心資料結構與非同步邏輯，避免「能跑但脆弱」的 V1.5 狀態。

### 0.1 🗑️ Step 1: 淨化資料結構 (Data Structure Purification)

> **問題**: `Notes` 表同時保留 `type` (字串) 和 `category_id` (外鍵)，造成雙重事實 (Double Truth) 災難。

- [x] **0.1.1 Migration v12: Kill Notes.type** ✅ 2024-12-30
  - [x] 執行一次性資料遷移: 確保所有 `Notes` 都有正確的 `category_id`
  - [x] 找不到對應分類的筆記 → 歸類到 `Default/Uncategorized`
  - [x] `ALTER TABLE Notes DROP COLUMN type;` (移除 type 欄位)
  - [x] 移除 `idx_notes_type` 索引 (app.py L235)
- [x] **0.1.2 清理程式碼** ✅ 2024-12-30
  - [x] 刪除 `crud.py` 的 `get_category_id_by_name()` (L23-41)
  - [x] 移除所有引用 `Notes.type` 的程式碼 (crud.py, batch.py)
  - [x] 更新 API 端點: 不再接受 `type` 參數，統一使用 `category_id`
  - [x] **Breaking Changes**:
    - `POST /api/notes` 現在只接受 `category_id`，不再接受 `type`
    - `PUT /api/notes/<id>` 現在只接受 `category_id`，不再接受 `type`
    - `POST /api/notes/batch/type` 現在只接受 `category_id`，不再接受 `type`

**實際結果**: ✅ 消除雙重事實，移除 ~60 行程式碼，所有測試通過

- [x] **0.1.3 修復殘留引用 (Post-Audit)** ✅ 2024-12-30
  > **來源**: Phase 0 審核 (Gemini) - 發現 `get_note()` 仍有 `COALESCE(c.name, n.type)` 引用
  - [x] 修改 `crud.py` L233, L261: `COALESCE(c.name, n.type)` → `COALESCE(c.name, 'Uncategorized')`
  - [x] 移除 `_queue_embedding_update()` 中重複的 import

**狀態**: ✅ Step 0.1 完成 (2024-12-30)

### 0.2 ⚙️ Step 2: 實作真正的任務隊列 (Proper Task Queue)

> **問題**: `_queue_embedding_update()` 在 WSGI 請求生命週期內啟動 `ThreadPoolExecutor`，伺服器重啟會丟失任務。

- [x] **0.2.1 修改 CRUD 邏輯** ✅ 2024-12-30
  - [x] `create_note()` / `update_note()` 不再 `submit()` 到 ThreadPool
  - [x] 改為 `INSERT INTO AI_Tasks (task_type, payload, status) VALUES ('embedding', json_object('note_id', ?), 'pending')`
  - [x] 移除 `_get_embedding_executor()` 和 `ThreadPoolExecutor` 相關程式碼
- [x] **0.2.2 實作 Worker Process** ✅ 2024-12-30
  - [x] 建立 `workers/task_processor.py` 獨立 Worker
  - [x] 消化 `AI_Tasks` 表中的待處理任務
  - [x] 支援優雅中斷 (Graceful Shutdown)
  - [x] 失敗重試機制 (max 3 retries)
  - [x] 單次執行模式 & 常駐模式
- [x] **0.2.3 Migration v13** ✅ 2024-12-30
  - [x] 建立 `AI_Tasks` 表 (task_type, status, payload, result, retry_count)
  - [x] 建立索引 (status, type, created_at)
- [ ] **0.2.4 部署方案** 🧊 待部署時實作
  - [ ] 簡單方案: Cron job 每 5 分鐘執行一次
  - [ ] 進階方案: Systemd service 常駐執行

**預期結果**: ✅ 任務持久化，伺服器崩潰也不會丟失 Embedding 請求

**狀態**: ✅ Step 0.2 核心功能完成 (2024-12-30)

### 0.3 🔨 Step 3: 重構查詢邏輯 (Query Logic Refactoring)

> **問題**: `crud.py` 的 `get_notes()` 長達 160 行，混合參數解析、SQL 動態組裝、業務邏輯。

- [x] **0.3.1 提取 Query Builder** ✅ 2024-12-30
  - [x] 建立 `utils/query_builder.py` 或 `NoteQueryBuilder` 類別
  - [x] 將 SQL 組裝邏輯從 `get_notes()` 提取出來
- [x] **0.3.2 簡化 JSON 處理** ✅ 2024-12-30
  - [x] 不要在 Python 中做 `parse_tags_json()`
  - [x] 利用 SQLite JSON 函式直接返回乾淨結構
- [x] **0.3.3 分離業務邏輯** ✅ 2024-12-30
  - [x] 將 FTS5 清洗邏輯獨立為 `sanitize_fts_query()`
  - [x] 將封存過濾邏輯獨立為 Filter 物件

**預期結果**: `get_notes()` 從 160 行減少到 ~150 行 (邏輯更清晰，易於維護)

**狀態**: ✅ Step 0.3 完成 (2024-12-30)

### 0.4 🔄 Step 4: V1 功能移植 (V1 Feature Porting)

> **目標**: 保持 V2 與 V1 功能對等，避免使用者升級後功能回歸
> **來源**: V1.4.2 功能對比分析 (2024-12-30)

- [x] **0.4.1 主題色彩系統 (Color Theme)** 🟡 P1 ✅ 2024-12-30
  > V1 位置: `static/js/composables/useSettings.js` L66-84
  - [x] 新增 CSS 變數 (`index.css`) 支援 6 個主題: default, cyberpunk, eye-care, elegant, ocean, sunset
  - [x] 實作 `data-theme` 屬性切換機制
  - [x] 在 `SettingsPage.tsx` 新增主題色彩選擇器 UI
  - [x] localStorage 持久化 (`colorTheme` key)
  - [x] 在 `main.tsx` 初始化時載入儲存的主題
  
- [x] **0.4.2 卡片開啟模式 (Card Open Mode)** 🟢 P2 ✅ 2024-12-30
  > V1 位置: `static/js/composables/useSettings.js` L63
  - [x] 新增設定: preview (預覽) / reading (閱讀) / edit (編輯)
  - [x] 在 `SettingsPage.tsx` 新增下拉選擇器
  - [x] `NoteCard.tsx` 讀取設定（預留擴充接口）
  - [x] localStorage 持久化 (`cardOpenMode` key)
  - ⚠️ **備註**: 目前三種模式都開啟編輯器，Preview/Reading 模式的 UI 實作延後（需要新增 Modal 或 ReadOnly 狀態）
  
- [x] **0.4.3 圖片保存模式 (Image Save Mode)** 🟢 P3 ✅ 2024-12-30
  > V1 位置: `static/js/composables/useSettings.js` L60
  - [x] 新增設定: both (原圖+縮圖) / thumbnail_only (僅縮圖)
  - [x] 在 `SettingsPage.tsx` 新增下拉選擇器
  - [x] 圖片上傳 API (`api.ts uploadImage`) 讀取 localStorage 並傳遞 `thumbnail_only` 參數
  - [x] localStorage 持久化 (`imageSaveMode` key)
  - [x] 後端已支援 (`routes/upload.py` L59, L267)
  
- [x] **0.4.4 快速新增預設分類 (Quick Add Default Category)** 🟢 P4 ✅ 2024-12-30
  > V1 位置: `static/js/composables/useSettings.js` L52
  - [x] 新增設定: 選擇預設快速新增的分類
  - [x] 在 `SettingsPage.tsx` 新增分類下拉選擇器（使用 appStore categories）
  - [x] localStorage 持久化 (`quickAddDefaultCategory` key)
  - ⚠️ **備註**: Header 新增按鈕套用預設分類的邏輯尚未實作（需要找到 Header 組件並修改）
  
- [ ] **0.4.5 自動載入更多 (Auto Load More / Infinite Scroll)** 🟢 P5
  > V1 位置: `static/js/composables/useSettings.js` L49
  - [ ] 新增設定: 開啟/關閉無限滾動
  - [ ] 在 `SettingsPage.tsx` 新增切換開關
  - [ ] `HomePage.tsx` 根據設定決定是否啟用 scroll 監聽
  - [ ] localStorage 持久化 (`autoLoadMore` key)

**延遲項目 (Deferred)**:
- 🧊 **i18n 多語系**: 已預留架構 (`i18n/index.ts`)，正式版本再啟用
- 🧊 **啟動時自動開啟瀏覽器**: EXE 打包時再處理

**狀態**: 🔴 待執行 (Next Priority)

---

## 📝 更新記錄 (2024-12-30)

### ✅ 今日完成 (第二批)

**設定頁面 - 資料管理**
- **分類管理 (CategoryManager)**: 新增/編輯/刪除分類，支援自訂圖示
- **標籤管理 (TagManager)**: 重命名/刪除/合併標籤
- **API 新增**: `createCategory`, `updateCategory`, `deleteCategory`, `renameTag`, `deleteTag`, `mergeTags`

**NoteEditor 功能增強**
- **來源連結管理**: 側邊欄新增「來源連結」區塊，支援 URL 自動補全 (https://)
- **Markdown 快捷鍵**: Ctrl+B (粗體), Ctrl+I (斜體), Ctrl+K (連結)
- **AI 提示詞提取**: 新增 📋 按鈕，可讀取圖片 AI metadata 並複製到剪貼簿

**系統維護 (System Maintenance)**
- **WAL Checkpoint UI**: 設定頁面新增按鈕，說明文字優化 (強調手動備份用途)
- **資料一致性檢查 UI**: 設定頁面新增檢查按鈕，顯示孤兒標籤/分類不一致等健康狀態

**Prompt Builder**
- **快捷鍵支援**: Ctrl+S (儲存至筆記庫), Ctrl+Enter (複製輸出)
- **UI 優化**: 暫時隱藏權重模式，新增「混沌系統」(隨機) 與「AI 優化」(LLM 指令)
- **功能補強**: 新增「儲存為模板」功能 (自訂模板)

### ✅ 今日完成 (第一批)

**AI 功能增強**
- **AI 模型選擇**: 設定頁面新增視覺/文字模型下拉選擇器，支援 localStorage 持久化
- **AI 文字模型自動偵測**: `get_available_text_model()` 自動選擇可用模型

**圖片管理**
- **圖片清理功能升級**: 危險區域新增三大功能：
  - 清理未使用圖片 (孤兒圖片)
  - 刪除原圖 (保留縮圖)
  - 修復失效圖片路徑
- **從網頁貼上圖片**: 支援從網頁複製帶圖片的 HTML 內容，自動下載遠端圖片

**V1 功能升級 (高優先)**
- **匯出備份**: 設定頁面新增「匯出 JSON」和「匯出資料庫」按鈕
- **匯入備份**: 設定頁面新增「匯入 JSON」功能，支援略過/建立副本兩種模式
- **置頂功能**: NoteCard 選單新增「置頂/取消置頂」按鈕
- **歷史版本還原**: NoteEditor 新增「歷史」按鈕，可查看並還原到過去的版本

**V1 功能升級 (中優先)**
- **列表模式視圖**: Header 已有 Grid/List 切換按鈕
- **封面位置選項**: NoteEditor 側邊欄新增「頂部/中間/底部」選項
- **圖片匯出 ZIP**: NoteCard 選單新增「匯出圖片」按鈕

**架構預留**
- **i18n 預留架構**: 建立 `frontend/src/i18n/index.ts`，預設繁體中文/英文翻譯結構

---

## 🟢 Phase 1: 現代化地基 (The Big Rewrite)
> **目標**: 建立 Vite + React + Flask 的混合開發環境，打通 API 通訊。

- [x] **1.1 前端專案初始化**
    - [x] 建立 `frontend/` 目錄結構 (手動配置取代 create-vite)
    - [x] 設定 `vite.config.ts` (Proxy to Flask:5000)
    - [x] 安裝核心依賴: `axios`, `zustand`, `react-router-dom`
    - [x] 安裝 UI 依賴: `tailwindcss`, `lucide-react` (Icons)
- [x] **1.2 後端 API 改造 (Backend Refactor)**
    - [x] 新增 V2 模式切換 (`PRISM_V2` 環境變數)
    - [x] 保留 V1 Jinja2 路由 (向後相容)
    - [x] 設定 Flask Static Folder 指向 `frontend/dist` (Production Mode)
- [x] **1.4 開發規範更新**
    - [x] Update `CONTRIBUTING.md`: 加入 "Testing Philosophy" (No UI Test, Unit Test Only) 政策
    - [x] **Versioning**: 實作 `config.py` Single Source of Truth (`PRISM_VERSION`) + Template Injection
    - [x] **License Policy**: 加入綠/黃/紅燈開源引用規則 (`CONTRIBUTING.md`)
- [x] **1.3 核心組件移植 (Component Porting)**
    - [x] 設計系統實作 (`tailwind.config.js` 定義 Theme Colors)
    - [x] 基礎元件: `Button`, `Input`, `Modal`, `Toast`

## 🟡 Phase 2: 功能復刻 (Feature Parity)
> **目標**: 讓 React 版本擁有 v1.x 的核心功能 (CRUD)。

- [x] **2.1 筆記管理 (Note Manager)**
    - [x] API: 確保 `GET /api/notes` 支援所有篩選參數 (已存在)
    - [x] Frontend: 實作 `MasonryGrid` (瀑布流) 視圖 (簡易 Grid)
    - [x] Frontend: 實作 `NoteCard` (支援懸停預覽、快速操作)
- [x] **2.2 編輯器升級 (Editor V2)**
    - [x] 使用優化過的 `Textarea` (Auto-resize 待補)
    - [x] 支援貼上圖片 (Paste Image)
    - [x] 支援拖曳上傳圖片 (Drag & Drop Upload)
- [x] **2.3 標籤與分類系統**
    - [x] API: 標籤 CRUD 與合併功能 (已存在)
    - [x] Frontend: 標籤自動完成 (TagInput Component)
    - [x] Settings: 分類與標籤管理介面 (DataManager)
- [x] **2.4 Prompt Builder 移植** ✅ 完成
  > **來源**: V1 核心功能，Gemini 建議優先移植
  - [x] 移植 `usePromptBuilder` 邏輯為 React Hook (`hooks/usePromptBuilder.ts`)
  - [x] 重建結構化參數表單 UI (`components/prompt-builder/`)
  - [x] 權重滑桿與隨機靈感功能
  - [x] 確保 `prompt_options.json` 可被讀取

## 🔴 Phase 3: 本地智慧 (Local Intelligence) - "Heavy" Features
> **目標**: 引入 Python 生態系的 Heavy Libraries (PyTorch/Ollama)。
> **注意**: 此階段開始引入重型依賴。

### 3.1 🤖 智慧標籤 (Auto-Tagging)

> **複雜度**: ⭐⭐ (Low-Mid)
> **狀態**: 🟡 基礎版完成，批次處理規劃中

- [x] **3.1.1 依賴整合**
  - [x] 使用 Ollama HTTP API (無需 Python client)
  - [x] 後端新增 `services/ai_service.py`
- [x] **3.1.2 視覺標註 API**
  - [x] `GET /api/ai/status`: 檢查 Ollama 狀態與已安裝模型
  - [x] `POST /api/ai/tag_image`: 接收圖片 -> LLaVA -> 回傳 Tags
  - [x] `POST /api/ai/analyze_note`: 分析整個筆記 (含圖片)
  - [x] `POST /api/ai/summarize`: 文字摘要 (Llama)
- [x] **3.1.3 前端整合 (單張)**
  - [x] NoteEditor 新增 "✨ AI 分析" 按鈕
  - [x] 顯示 AI 建議標籤，點擊即可添加
  - [x] 設定頁面顯示 AI 服務狀態
- [x] **3.1.4 批次處理 (Batch Processing)** ✅ 完成
  - [x] 設定頁面新增「批次 AI 分析」功能
  - [x] 選擇範圍：全部筆記 / 指定分類 / 無標籤筆記
  - [x] **UI 組件**: Progress Bar (顯示進度 x/N), Stop 按鈕
  - [x] 後端新增 `POST /api/ai/batch_tag` (Async Task)
  - [x] 支援中斷機制 (Stop Task)
  - [x] 結果報告：成功 x 筆，失敗 x 筆


### 3.2 🧠 語意搜尋 (Semantic Search)

> **複雜度**: ⭐⭐⭐ (Mid-High)
> **策略**: 使用 SQLite BLOB 儲存向量 + NumPy 暴力計算 (保持輕量)
> **狀態**: ✅ 完成

- [x] **3.2.1 向量儲存**
  - [x] 使用 Notes 表新增 `text_embedding BLOB` 欄位 (migrations v9)
  - [x] 獨立 `Embeddings` 表 (migrations v11, SCHEMA-V2 compliant)
  - [x] 使用 `sentence-transformers` (all-MiniLM-L6-v2) 產生向量
  - [x] 向量維度: 384 (輕量高效)
- [x] **3.2.2 索引機制**
  - [x] 筆記儲存時自動產生 Embedding (背景執行，不阻塞)
  - [x] 設定頁面「重建索引」按鈕
  - [x] `content_hash` 增量更新 - 只重算有變更的筆記
- [x] **3.2.3 搜尋 API**
  - [x] `GET /api/search/semantic?q=...` - 語意搜尋
  - [x] `GET /api/search/status` - 索引狀態
  - [x] `POST /api/index/rebuild` - 重建索引
  - [x] Python 層計算 Cosine Similarity
  - [x] 返回相似度 Top-K 筆記
- [x] **3.2.4 前端整合** ✅ 完成
  - [x] 搜尋模式切換：🧠 腦圖標 Toggle
  - [x] 語意搜尋結果下拉框 (含相似度分數)
- [x] **3.2.5 Hybrid Search (FTS + Vector)** ✅ 完成
  > **演算法**: RRF (Reciprocal Rank Fusion), k=60
  - [x] VectorStore 單例模式 (RAM 駐留)
  - [x] `GET /api/search/hybrid?q=...&mode=hybrid|fts|vector`
  - [x] L2 Normalization → Dot Product = Cosine Similarity


### 3.3 🗺️ 知識畫布 (Canvas / Graph View) 🧊 已凍結 (Icebox)
> **複雜度**: ⭐⭐⭐⭐ (High) -> 建議延後
> **狀態**: 暫不開發，優先列表與搜尋體驗
- [ ] **3.3.1 關聯資料結構**
  - [ ] 資料庫新增 `Note_Edges` 表 (Source -> Target, Type)
- [ ] **3.3.2 畫布前端**
  - [ ] 引入 `reactflow` 或 `react-force-graph`
  - [ ] 實作節點拖曳、連線、群組化

### 3.4 📎 附件系統 (Attachment System)

> **複雜度**: ⭐⭐⭐ (Mid)
> **目的**: 支援大型 .md 文件作為筆記附件，為 RAG 知識庫做準備。
> **狀態**: ✅ 基礎版完成

- [x] **3.4.1 資料結構**
  - [x] 建立 `Note_Attachments` 表 (migrations v8)
  - [x] 建立 `docs/notes/` 及 `docs/attachments/` 目錄
- [x] **3.4.2 後端 API**
  - [x] `GET /api/notes/{id}/attachments` - 取得附件列表
  - [x] `POST /api/notes/{id}/attachments` - 上傳附件
  - [x] `GET /api/attachments/{id}` - 讀取附件內容
  - [x] `DELETE /api/attachments/{id}` - 刪除附件
- [x] **3.4.3 前端整合**
  - [x] NoteEditor 新增附件區塊
  - [x] 拖曳 .md 檔案自動上傳
  - [x] 瀏覽選擇檔案上傳
  - [ ] 附件預覽/編輯功能 (待做)
- [x] **3.4.4 自動分離 (Auto-Separation)** ✅ 完成 (2024-12-17 精緻化)
  - [x] `GET /api/notes/{id}/check_separation` - 檢查是否需要分離
  - [x] `POST /api/notes/{id}/separate` - 執行分離 (支援更新現有附件)
  - [x] `POST /api/notes/{id}/restore` - 還原分離內容
  - [x] 前端整合：
    - [x] 儲存時自動分離 (>5000 字元，無提示)
    - [x] 開啟編輯器時自動載入附件內容 (不刪除附件)
    - [x] 點擊附件自動載入內容到編輯器 (無彈窗)
    - [x] 後端支援「更新」現有附件而非報錯

### 3.5 🧠 RAG Knowledge API (External Memory)

> **複雜度**: ⭐⭐⭐ (Mid)
> **目的**: 將 Prism 打造為外部 AI (如 Antigravity, Trading Bot) 的知識庫/長期記憶，而非在 Prism 內建聊天機器人。
> **來源**: User Request 2025-12-16 (Downgrade In-App Chat, Upgrade API)

- [ ] **3.5.1 Search/Context API**
  - [ ] `POST /api/rag/search` (Input: query, params; Output: JSON chunks)
  - [ ] 支援 Hybrid Search (Vector + FTS)
  - [ ] 回傳格式包含: content, source_id, distance/score
- [ ] **3.5.2 External Integration**
  - [ ] CORS 設定: 允許外部 Agent 呼叫
  - [ ] (Optional) API Key 機制

### 3.6 🔌 AI Gateway (Pluggable AI Providers)

> **複雜度**: ⭐⭐⭐ (Mid)
> **目的**: 支援多種 AI 後端 (本地/雲端切換) 並提供 Prompt 最佳化服務。

- [ ] **3.6.1 Provider 設定 (Service Interface)**
  - [ ] **Interface**: 定義 `BaseLLMService` (Absract Class)，解耦具體實作
  - [ ] **Pluggable**: 實作 `OllamaService` 與 `GeminiService`，可無縫切換
  - [ ] 設定頁面 AI Provider 配置 UI (Local/Cloud 切換)
  - [ ] 本地儲存 `config/ai_config.json` (加密儲存 API Key)
- [ ] **3.6.2 ✨ AI Prompt Optimizer (最佳化)**
  - [ ] UI: 編輯器新增「✨ AI 最佳化」按鈕
  - [ ] Modal: 輸入最佳化指令 (e.g., "Make it cyberpunk style")
  - [ ] Logic: 呼叫 configured Chat Model (e.g., GPT-4 or Llama3)
  - [ ] Result: 顯示 Diff 或是直接取代原 Prompt
- [ ] **3.6.3 OpenAI-Compatible Client**
  - [ ] 統一 API 呼叫介面 (Base URL + Key)


### 3.7 🧬 卡片譜系與版本控制 (Card Lineage / Prompt Versioning)

> **複雜度**: ⭐⭐ (Low-Mid)
> **目的**: 解決 Prompt 修改過程中的版本追朔問題 (v1 -> v1.1 -> v2)。
> **來源**: User Request 2025-12-15

- [x] **3.7.1 階段一：父子繼承 (Simple Inheritance)** ✅ 完成
  - [x] DB: Notes 表新增 `parent_id` (Migration v10)
  - [x] API: 筆記複製 (Fork) 邏輯，繼承 content/tags 但重置 ID
  - [x] API: `POST /api/notes/:id/duplicate` 支援 `as_variant` 參數
  - [x] Frontend: 卡片選單新增「建立變體 (Create Variant)」按鈕
  - [x] Frontend: 卡片顯示「來自: [父標題]」標記
- [x] **3.7.2 階段二：穩定簡化 (Stable & Simple)** ✅ 完成
  - [x] **輕量化原則**: 不做 Deep Copy 圖片，僅引用 cover_image
  - [x] DB: 保持單表關聯 (`parent_id`)，不做額外 Graph 表
  - [x] Frontend: 僅顯示「父節點連結」標籤，不做複雜樹狀圖 UI
- [ ] **3.7.3 階段三：參數差異比對 (Diff View)** 🧊 Icebox
  - [ ] Frontend: 比較父子卡片內容，高亮顯示修改的 Prompt 關鍵字


## 🟣 Phase 4: 進階多媒體 (Advanced Multimedia)
> **複雜度**: ⭐⭐⭐⭐⭐ (Very High)

- [ ] **4.1 影片智慧分析** //影片不做 太麻煩了 檔案也太大
  - [ ] 引入 `ffmpeg-python`
  - [ ] 自動產生 GIF 預覽
  - [ ] Whisper 字幕生成 (本地轉錄)
- [ ] **4.2 生成式編輯 (Generative Edit)** //也不作 好象沒啥用
  - [ ] 整合 Stable Diffusion WebUI API
  - [ ] 實作 In-App Inpainting (在筆記圖片上直接塗抹修圖)

## 🧩 Phase 5: 生態系擴充 (Plugin Ecosystem)
> **狀態**: 🧊 待規劃 (Pending)
> **策略**: 基於 API-First 架構的外部掛件，不影響核心輕量化。

- [ ] **5.1 資訊源外掛 (Data Source Plugins)**
  - [ ] **RSS 智慧閱讀器**: 抓取 RSS -> Ollama 摘要/去重 -> 僅存入 Insight 筆記
  - [ ] **Civitai 爬蟲**: 自動抓取 Civitai 圖片 Metadata 並建立 Prompt 筆記
  - [ ] **Web Clipper**: 瀏覽器擴充功能，一鍵存網頁到 Prism
- [ ] **5.2 編輯器外掛 (Editor Plugins)**
  - [ ] **Prompt 模組積木**: 視覺化拖拉 Prompt 詞塊 (Lego Blocks)
- [ ] **5.3 媒體外掛 (Media Plugins)**
  - [ ] **Youtube Whisper 轉錄**: 下載影片 -> 轉錄字幕 -> 存為筆記

---

## 📅 優先級建議 (Priority)

> **2024-12-30 更新**: 根據 Linus Report，Phase 0 現為最高優先。

0.  **🔴 Phase 0** (架構淨化 - **必須先做**，否則繼續堆砌功能只會累積技術債)
1.  **Phase 1 & 2** (必須先做，否則 V2 無法使用) ✅ 已完成
2.  **Phase 3.1** (Auto-Tagging 價性比高，易實作) ✅ 已完成
3.  **Phase 3.2** (Semantic Search 徹底改變體驗，但需處理模型下載問題) ✅ 已完成
4.  **Phase 3.3** (視需求而定，若無複雜整理需求可延後) 🧊 已凍結
5.  **Phase 4** (大後期功能)

---

## 🧪 Phase 6: 自動化測試 (Automated Testing)

> **策略**: API 測試 + E2E 測試 (Playwright)，跳過前端單元測試
> **來源**: 009-自動化測試.txt 指南
> **原則**: 「廚房能做菜 (API 正確)」+「服務生端菜到桌上沒打翻 (前端呈現正確)」
> **狀態**: ✅ 完成 (2024-12-17)

### 6.0 🔧 安全性與穩定性修復 (Linus Report Fixes)

> **來源**: `docs/1217-L分析報告.md`
> **日期**: 2024-12-17

| 優先級 | Bug | 修復內容 | 狀態 |
|--------|-----|----------|------|
| P0 | #3 Embedding 線程無限產生 | 使用 `ThreadPoolExecutor(max_workers=2)` | ✅ 已修復 |
| P0 | #4 `_batch_tasks` 記憶體洩漏 | 加入 TTL(1hr) + Max(100) 限制 | ✅ 已修復 |
| P1 | #1 重複的 `get_db()` | 刪除 `app.py` 版本，統一使用 `db.py` | ✅ 已修復 |
| P2 | #5 `type/category_id` 冗餘 | 已記錄於 SCHEMA.md，屬向後相容設計 | ⏳ 長期計劃 |

### 6.1 🔧 後端 API 測試 (pytest)

> **工具**: pytest + Flask test client
> **範圍**: 核心 CRUD API 與 AI 服務

- [x] **6.1.1 測試基礎設施**
  - [x] 建立 `tests/` 目錄結構
  - [x] 配置 pytest fixtures (test client, temp DB)
  - [x] `conftest.py` 共用設定
- [x] **6.1.2 核心 API 測試**
  - [x] `test_notes_crud.py` - Notes CRUD 操作
  - [x] `test_categories.py` - 分類 API
  - [x] `test_tags.py` - 標籤 API
  - [x] `test_search.py` - 搜尋 API (FTS + Semantic)
- [x] **6.1.3 AI 服務測試** (Graceful Degradation)
  - [x] `test_ai_status.py` - AI 狀態檢查
  - [x] `test_batch_tag.py` - 批次標籤 API

### 6.2 🎭 前端 E2E 測試 (Playwright)

> **工具**: Playwright (Python 版)
> **範圍**: 核心使用者流程 (Happy Path)
> **原則**: 只測「絕對不能壞」的流程

- [x] **6.2.1 測試環境**
  - [x] 安裝 playwright + pytest-playwright
  - [x] `e2e/` 目錄結構
- [x] **6.2.2 核心流程測試**
  - [x] `test_note_flow.py` - V2 頁面載入、元件可見性、筆記建立流程
  - [x] 導航測試 (首頁 → Settings → Prompt Builder)
  - [x] 搜尋輸入框測試
- [x] **6.2.3 data-testid 屬性**
  - [x] Layout: `app-container`
  - [x] Header: `header`, `search-input`, `search-form`, `add-note-button`
  - [x] Sidebar: `sidebar-nav`
  - [x] HomePage: `notes-grid`
  - [x] NoteCard: `note-card-{id}`

### 6.3 📋 測試執行指令

```bash
# 後端 API 測試 (不需要 Flask 運行)
python -m pytest tests/ -v

# 前端 E2E 測試 (需要 V2 模式 Flask 運行)
# 終端 1: 啟動 V2 模式
set PRISM_V2=true
python app.py

# 終端 2: 執行 E2E 測試
python -m pytest e2e/ -v --headed  # 有頭模式 (可視化)
python -m pytest e2e/ -v           # 無頭模式 (CI/CD)
```

**決策臨界值**:
| 測試類型 | 適用場景 | 執行者 |
|----------|----------|--------|
| 自動化 API | 所有 API 端點 (Data Flow) | pytest |
| 自動化 E2E | 核心路徑 (Happy Path) | Playwright |
| 手動測試 | 體驗與美感 (動畫/顏色/排版) | Human |
| 探索性測試 | 亂按破壞 (Edge Cases) | Human |

---

## 🧪 Phase 6.4: 手動測試清單 (Manual Testing Checklist)

> **狀態**: 🟡 待驗證 (Pending Manual Test)
> **更新**: 2024-12-17

以下功能需要人工測試驗證：

| # | 功能 | 測試步驟 | 狀態 |
|---|------|----------|------|
| 1 | 預覽模式 | 開啟筆記 → 點擊 👁️ → 確認圖片顯示 | ⏳ |
| 2 | 語意搜尋 | 點擊 🧠 腦圖標 → 輸入關鍵字 → 看結果 | ⏳ |
| 3 | AI 分析 | 編輯筆記 → 點「✨ AI 分析」| ⏳ |
| 4 | 附件上傳 | 編輯筆記 → 拖曳 .md 檔案 | ⏳ |
| 5 | 設定頁面 | 檢查「語意搜尋」區塊 + 重建索引 | ⏳ |
| 6 | 自動分離載入 | 開啟已分離筆記 → 確認完整內容自動載入 | ⏳ |
| 7 | 自動分離儲存 | 儲存長內容筆記 → 確認附件自動更新 | ⏳ |
| 8 | 附件點擊載入 | 點擊附件 → 確認內容載入編輯器 (無彈窗) | ⏳ |
| 9 | 卡片刪除按鈕 | 新建卡片 → 點擊 ⋯ → 確認刪除選項存在 | ⏳ |
| 10 | 字數顯示 | 確認卡片 Footer 顯示字數 | ⏳ |

