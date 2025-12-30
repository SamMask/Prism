# Prism V2 - Modernization & Intelligence Roadmap (TODO-V2)

**狀態**: 🟡 維護與優化 (Maintenance & Optimization)
**核心目標**: Headless Architecture + Local AI
**文件參照**: `docs/Prism-V2.md` (總體戰略), `docs/SCHEMA-V2.md` (資料庫規格), `1230-審核報告.md` (Linus Audit)
**最後更新**: 2024-12-31

---

## ✅ 已完成項目 (Completed Projects)

### 🟢 Phase 1: 現代化地基 (The Big Rewrite)
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

### 🟡 Phase 2: 功能復刻 (Feature Parity)
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
- [x] **2.4 Prompt Builder 移植**
    - [x] 移植 `usePromptBuilder` 邏輯為 React Hook (`hooks/usePromptBuilder.ts`)
    - [x] 重建結構化參數表單 UI (`components/prompt-builder/`)
    - [x] 權重滑桿與隨機靈感功能
    - [x] 確保 `prompt_options.json` 可被讀取

### 🚨 Phase 0: 架構淨化 (Architecture Purification)
> **來源**: Linus-style 審核報告 (`1230-審核報告.md`)

#### 0.1 🗑️ Step 1: 淨化資料結構 (Data Structure Purification)
- [x] **0.1.1 Migration v12: Kill Notes.type** ✅ 2024-12-30
  - [x] 執行一次性資料遷移: 確保所有 `Notes` 都有正確的 `category_id`
  - [x] `ALTER TABLE Notes DROP COLUMN type;` (移除 type 欄位)
  - [x] 移除 `idx_notes_type` 索引
- [x] **0.1.2 清理程式碼** ✅ 2024-12-30
  - [x] 刪除 `crud.py` 的 `get_category_id_by_name()`
  - [x] 移除所有引用 `Notes.type` 的程式碼
  - [x] 更新 API 端點: 不再接受 `type` 參數
- [x] **0.1.3 修復殘留引用 (Post-Audit)** ✅ 2024-12-30
  - [x] 修改 `crud.py`: `COALESCE(c.name, 'Uncategorized')`

#### 0.2 ⚙️ Step 2: 實作真正的任務隊列 (Proper Task Queue)
- [x] **0.2.1 修改 CRUD 邏輯** ✅ 2024-12-30
  - [x] `create_note()` / `update_note()` 改為寫入 `AI_Tasks` 表
  - [x] 移除 `ThreadPoolExecutor` 相關程式碼
- [x] **0.2.2 實作 Worker Process** ✅ 2024-12-30
  - [x] 建立 `workers/task_processor.py`
  - [x] 支援優雅中斷與失敗重試
- [x] **0.2.3 Migration v13** ✅ 2024-12-30
  - [x] 建立 `AI_Tasks` 表與索引

#### 0.3 🔨 Step 3: 重構查詢邏輯 (Query Logic Refactoring)
- [x] **0.3.1 提取 Query Builder** ✅ 2024-12-30
  - [x] 建立 `utils/query_builder.py`
- [x] **0.3.2 簡化 JSON 處理** ✅ 2024-12-30
  - [x] 利用 SQLite JSON 函式直接返回乾淨結構
- [x] **0.3.3 分離業務邏輯** ✅ 2024-12-30
  - [x] 獨立 `sanitize_fts_query()` 與 Filter 物件

#### 0.4 🔄 Step 4: V1 功能移植 (V1 Feature Porting)
- [x] **0.4.1 主題色彩系統 (Color Theme)** ✅ 2024-12-30
- [x] **0.4.2 卡片開啟模式 (Card Open Mode)** ✅ 2024-12-30
- [x] **0.4.3 圖片保存模式 (Image Save Mode)** ✅ 2024-12-30
- [x] **0.4.4 快速新增預設分類 (Quick Add Default Category)** ✅ 2024-12-30
- [x] **0.4.5 自動載入更多 (Auto Load More)** ✅ 2024-12-30

#### 0.5 🧹 Step 5: 殘留清理 (Residual Cleanup)
- [x] **0.5.1 清理 `auto_fix_consistency()` 中的 type 同步** ✅ 2024-12-31
- [x] **0.5.2 修復 `init_db()` CREATE TABLE 語句** ✅ 2024-12-31
- [x] **0.5.3 快取 `has_parent_id` 欄位檢查** ✅ 2024-12-31
- [x] **0.5.4 新增 NoteQueryBuilder 單元測試** ✅ 2024-12-31
- [x] **0.5.5 FTS5 查詢安全性強化** ✅ 2024-12-31
- [x] **0.5.6 拆分 NoteEditor.tsx** ✅ 2024-12-31
  - [x] 提取 `EditorToolbar`, `EditorSidebar`, `AttachmentPanel`
- [x] **0.5.7 拆分 SettingsPage.tsx** ✅ 2024-12-31
  - [x] 提取 `AIConfigSection`, `SearchConfigSection`, `AppearanceSection`, `BackupImportSection`, `DangerZoneSection`
- [x] **0.5.8 消除 get_note() 重複 SQL** ✅ 2024-12-31
- [x] **0.5.9 VectorStore 執行緒安全** ✅ 2024-12-31

### 🔴 Phase 3: 本地智慧 (Local Intelligence) - 已完成功能
> **目標**: 引入 Python 生態系的 Heavy Libraries (PyTorch/Ollama)。

#### 3.1 🤖 智慧標籤 (Auto-Tagging)
- [x] **3.1.1 依賴整合**: 使用 Ollama HTTP API
- [x] **3.1.2 視覺標註 API**: 標註、分析、摘要
- [x] **3.1.3 前端整合**: NoteEditor AI 分析按鈕
- [x] **3.1.4 批次處理 (Batch Processing)**: 批次標籤功能與進度條

#### 3.2 🧠 語意搜尋 (Semantic Search)
- [x] **3.2.1 向量儲存**: `Embeddings` 表, `sentence-transformers`
- [x] **3.2.2 索引機制**: 增量更新, 重建索引
- [x] **3.2.3 搜尋 API**: 語意搜尋, 索引狀態
- [x] **3.2.4 前端整合**: 腦圖標切換, 下拉框顯示分數
- [x] **3.2.5 Hybrid Search**: RRF 演算法整合 FTS + Vector

#### 3.4 📎 附件系統 (Attachment System)
- [x] **3.4.1 資料結構**: `Note_Attachments` 表
- [x] **3.4.2 後端 API**: 附件 CRUD
- [x] **3.4.3 前端整合**: 拖曳上傳, 附件列表
- [x] **3.4.4 自動分離 (Auto-Separation)**: 長文自動分離為附件

#### 3.5 🧠 RAG Knowledge API (External Memory)
- [x] **3.5.1 Search/Context API**: Hybrid Search, JSON chunks output
- [x] **3.5.2 External Integration**: CORS 設定

#### 3.7 🧬 卡片譜系與版本控制 (Card Lineage)
- [x] **3.7.1 父子繼承**: `duplicate` with `as_variant`
- [x] **3.7.2 穩定簡化**: 單表關聯, 引用封面

### 🧪 Phase 6: 自動化測試 (Automated Testing)
- [x] **6.1 後端 API 測試**: CRUD, Search, AI 服務測試
- [x] **6.2 前端 E2E 測試**: Playwright 核心流程測試
- [x] **6.0 安全性與穩定性修復**: 修復 1217 報告中的 P0/P1/P2 問題

### 📦 Phase 7: 打包與更新 (Packaging & Updates)
- [ ] **7.1 下載更新機制 (Plan A)**:
  - [ ] 檢查 GitHub Release API
  - [ ] 前端顯示「發現新版本」Modal
  - [ ] 連結引導至 Release Page 下載
- [ ] **7.2 內建更新器 (Plan B)** 🧊 待實作:
  - [ ] 開發獨立 `updater.exe`
  - [ ] 實作下載/解壓/覆蓋流程
  - [ ] 對接後端 `/api/system/upgrade` 接口
- [ ] **7.3 啟動遷移邏輯 (Startup Migration)**:
  - [ ] 確保 `init_db()` 為冪等操作
  - [ ] 測試從 V1 到 V2, V2.0 到 V2.1 的升級路徑

---

## 📝 更新記錄 (Update Log)

### ✅ 2024-12-31: Phase 0.5 Frontend Refactoring (P2 Completed)
**前端重構 (Frontend Refactoring)**:
- **拆分 SettingsPage.tsx**: 拆分為 `AIConfigSection`, `SearchConfigSection`, `AppearanceSection`, `BackupImportSection`, `DangerZoneSection`, `SystemStatsSection`。
- **拆分 NoteEditor.tsx**: 拆分為 `EditorToolbar`, `EditorSidebar`, `AttachmentPanel`。

### ✅ 2024-12-31: Phase 0.5 Residual Cleanup (P0 Completed)
**核心修復 (Critical Fixes)**:
- **Schema 淨化**: `init_db()` 與 `auto_fix_consistency()` 不再引用 `type` 欄位。

### ✅ 2024-12-30: Phase 0 Architecture Purification (Core)
**功能增強**:
- **分類/標籤管理**: 新增完整的 CRUD API 與管理介面。
- **NoteEditor**: 新增來源連結管理、Markdown 快捷鍵、AI 提示詞提取。
- **Prompt Builder**: 新增快捷鍵、Chaos 模式、儲存模板。
- **System**: 改善 WAL Checkpoint 與資料一致性檢查 UI。

**V1 功能移植完成**:
- 主題色彩、卡片開啟模式、圖片保存模式、快速新增預設分類、自動載入更多。

**圖片管理升級**:
- 危險區域新增：孤兒圖片清理、原圖刪除(留縮圖)、失效路徑修復。

---

## 🧊 待辦 / 凍結 / 延遲項目 (Backlog / Icebox)

### Phase 0 剩餘
- [ ] **0.2.4 部署方案**: Cron job 或 Systemd service (待部署時實作)

### Phase 3: 本地智慧 (剩餘)
#### 3.3 🗺️ 知識畫布 (Canvas / Graph View) 🧊 凍結
> **複雜度**: ⭐⭐⭐⭐ (High) -> 暫不開發，優先列表與搜尋體驗
- [ ] **3.3.1 關聯資料結構**: `Note_Edges` 表
- [ ] **3.3.2 畫布前端**: reactflow/force-graph

#### 3.6 🔌 AI Gateway (Pluggable AI Providers)
> **複雜度**: ⭐⭐⭐ (Mid) -> 尚未開始
- [ ] **3.6.1 Provider 設定**: `BaseLLMService`, `OllamaService`, `GeminiService`
- [ ] **3.6.2 AI Prompt Optimizer**: 編輯器內的 AI 最佳化按鈕
- [ ] **3.6.3 OpenAI-Compatible Client**: 統一介面

#### 3.7.3 階段三：參數差異比對 (Diff View) 🧊 凍結
- [ ] Frontend: 比較父子卡片內容差異

### 🟣 Phase 4: 進階多媒體 (Advanced Multimedia) 🧊 凍結
- [ ] **4.1 影片智慧分析**: ffmpeg, Whisper (檔案過大，暫緩)
- [ ] **4.2 生成式編輯 (Generative Edit)**: In-App Inpainting (暫緩)

### 🧩 Phase 5: 生態系擴充 (Plugin Ecosystem) 🧊 待規劃
- [ ] **5.1 資訊源外掛**: RSS, Civitai 爬蟲, Web Clipper
- [ ] **5.2 編輯器外掛**: Prompt Lego Blocks
- [ ] **5.3 媒體外掛**: Youtube Whisper

### 延遲項目 (Deferred from Phase 0.4)
- 🧊 **i18n 多語系**: 已預留架構 (`i18n/index.ts`)，正式版本再啟用
- 🧊 **啟動時自動開啟瀏覽器**: EXE 打包時再處理

### 🧪 Phase 6.4: 手動測試清單 (Manual Testing Checklist)
> **狀態**: 🟡 待驗證 (Pending Manual Test)
