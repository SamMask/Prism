# Prism V2 - Modernization & Intelligence Roadmap (TODO-V2)

**狀態**: � 實作中 (In Progress)
**核心目標**: Headless Architecture + Local AI
**文件參照**: `docs/Prism-V2.md` (總體戰略), `docs/SCHEMA-V2.md` (資料庫規格)

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
    - [x] 設定 Flask Static Folder 指向 `frontend/dist` (Production Mode)
- [ ] **1.4 開發規範更新**
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

1.  **Phase 1 & 2** (必須先做，否則 V2 無法使用)
2.  **Phase 3.1** (Auto-Tagging 價性比高，易實作)
3.  **Phase 3.2** (Semantic Search 徹底改變體驗，但需處理模型下載問題)
4.  **Phase 3.3** (視需求而定，若無複雜整理需求可延後)
5.  **Phase 4** (大後期功能)

---

## 🧪 Phase 6: 自動化測試 (Automated Testing)

> **策略**: API 測試 + E2E 測試 (Playwright)，跳過前端單元測試
> **來源**: 009-自動化測試.txt 指南
> **原則**: 「廚房能做菜 (API 正確)」+「服務生端菜到桌上沒打翻 (前端呈現正確)」
> **狀態**: ✅ 完成 (2024-12-17)

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

