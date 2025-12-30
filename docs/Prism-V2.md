# Prism V2: The "Local Intelligence" Upgrade Plan

> **Vision**: 將 Prism 從「靜態的圖片管理工具」升級為「**具備視覺感知能力的本地第二大腦**」。
> **Core Strategy**: **Headless Architecture** (Python 後端 + React 前端) + **Heavy Local AI** (Ollama, CLIP, Local Vector DB)。

---

## 🏗️ 1. 架構現代化 (Architectural Shift)

為了支撐更復雜的互動（如畫布視圖、即時 AI 對話），我們必須償還技術債，轉向現代化前端架構。

### 1.1 前後端分離 (Headless)
*   **Backend**: `Flask` (Python)
    *   **角色轉變**: 不再渲染 HTML，轉型為純 API Server (JSON only)。
    *   **新增能力**: WebSocket 支援 (用於即時 AI 串流)、向量資料庫介面。
*   **Frontend**: `Vite` + `React` + `TypeScript` + `TailwindCSS`
    *   **優勢**: HMR 極速開發、生態系豐富 (React-Flow, DND-Kit)、組件化復用。
    *   **狀態管理**: `Zustand` (輕量級取代 Redux)。
    *   **路由**: `React Router v6`。

### 1.2 資料層升級 (Next-Gen Data)
*   **Vector Store**: 引入 `ChromaDB` (嵌入式) 或 `SQLite-VSS`。
    *   用於儲存圖片特徵值 (Semantic Embeddings)。
*   **Graph Relations**: 在 SQLite 中強化關聯 (Edges table)，支撐知識圖譜。

---

## 🗺️ 2. 三階段升級路線圖 (Phased Roadmap)

按照「基礎架構 -> 核心功能 -> 智慧增強」的順序執行。

### 階段一：地基重塑 (Phase 1: Foundation)
> **目標**: 建立現代化開發環境，完成 "Hello World" 級別的 React App 跑在 Flask 上。

1.  **Init Core**: 初始化 `frontend/` 目錄 (Vite + React + TS)。
2.  **API Migration**: 將 `app.py` 的 `/` 路由改為 Serving Static Files，並建立 `/api/health` 測試端點。
3.  **Components System**: 移植 Tailwind 設定，建立基礎元件 (`Button`, `Card`, `Modal`)。

### 階段二：功能奇偶校驗 (Phase 2: Parity)
> **目標**: 讓 V2 擁有 V1 的所有功能 (Notes, Gallery, Search)。

1.  **Auth/Config**: 前端讀取後端設定 (Config API)。
2.  **Note CRUD**: 移植筆記列表、編輯、刪除功能。
3.  **Masonry Gallery**: 使用 `react-masonry-css` 重寫瀑布流佈局。
4.  **Editor V2**: 引入 `TipTap` 或保留純 Markdown Editor，但在 React 中實現。

### 階段三：本地智慧 (Phase 3: Local Intelligence) 🧠
> **目標**: 引入 "Heavy" 功能，讓 Prism 變聰明。

1.  **AI Tagging (Auto-Label)**: ✅ 完成
    *   整合 `Ollama` API。
    *   前端上傳圖片 -> 後端呼叫 `LLaVA`/`BakLLaVA` -> 回傳建議標籤。
2.  **Semantic Search (The "Killer Feature")**: ✅ 完成
    *   後端整合 `CLIP` 或 `Sentence-Transformers`。
    *   對舊圖庫進行 "Embedding Indexing" (背景任務)。
    *   前端搜尋框支援自然語言：「找一張有紅色跑車的圖」。
3.  **Graph/Canvas View**: 🧊 (Deferred)
    *   新增「畫布模式」，允許自由拖曳筆記與圖片，建立視覺化連結。
4.  **Prompt Lineage (Card Versioning)**: ✅ (Phase 2 Integrated)
    *   實作「卡片分支」，記錄 Prompt 的演變過程 (v1 -> v1.1)。
    *   解決 AI 算圖過程中的版本迷失問題。
5.  **AI Gateway & Prompt Optimizer**: 🟡 (Partial)
    *   整合多模型 (Local/Cloud) 並提供「AI 提示詞最佳化」功能 (Prompt Builder 已整合 AI Optimize)。
    *   讓 Prism 成為 Prompt Engineering 的實驗台。

### 2.5 🧪 測試策略 (Testing Philosophy)
> **來源**: 經驗學 (V1.4.2 Legacy Analysis)
> **原則**: **Pragmatic Testing** (實用主義測試)。
> **狀態**: ✅ 基礎設施完成 (2024-12-17)

*   **✅ API 自動化 (pytest)**: 68/73 測試通過
    * 核心 CRUD API 測試 (`tests/test_notes_crud.py`, `test_tags.py`, etc.)
    * AI 服務狀態測試 (Graceful Degradation)
    * 批次操作測試
*   **✅ E2E 自動化 (Playwright)**: 核心流程測試
*   **🟡 手動測試**: UI 互動與體驗驗證 (詳見 `TODO-V2.md` Phase 6.4)

### 2.6 🔄 V1 功能移植 (V1 Feature Porting)
> **來源**: V1.4.2 功能對比分析 (2024-12-30)
> **原則**: 保持 V2 與 V1 功能對等，避免功能回歸

| 優先級 | 功能 | V1 位置 | V2 狀態 |
|--------|------|---------|---------|
| 🟡 P1 | **主題色彩 (Color Theme)** | `useSettings.js` L66-84 | 待實作 |
| 🟢 P2 | 卡片開啟模式 (preview/reading/edit) | `useSettings.js` L63 | 待實作 |
| 🟢 P3 | 圖片保存模式 (both/thumbnail_only) | `useSettings.js` L60 | 待實作 |
| 🟢 P4 | 快速新增預設分類 | `useSettings.js` L52 | 待實作 |
| 🟢 P5 | 自動載入更多 (無限滾動) | `useSettings.js` L49 | 待實作 |
| 🧊 | i18n 多語系 | `useI18n.js` | 已預留架構 |
| 🧊 | 啟動時自動開啟瀏覽器 | `useSettings.js` L391 | EXE 打包時處理 |

**實作順序**:
1. **主題色彩**: 新增 6 個 `data-theme` CSS 變體 + 設定 UI
2. **卡片開啟模式**: 新增 localStorage 偏好 + 套用到 NoteCard
3. **圖片保存模式**: 新增設定 + 傳遞給 upload API
4. **快速新增預設分類**: 新增設定 + 套用到 Header 新增按鈕
5. **無限滾動**: 新增設定 + 實作 scroll 監聽

---

## 🎒 3. 技術堆疊清單 (Tech Stack)

| 領域 | 技術選型 | 理由 |
| :--- | :--- | :--- |
| **Backend** | **Python 3.10+** / **Flask** | 現有資產，Python 是 AI 原生語言。 |
| **Frontend** | **React 18** / **TypeScript** | 複雜 UI 標準，型別安全。 |
| **Build Tool**| **Vite** | 開發體驗極佳，秒級啟動。 |
| **UI Framework**| **TailwindCSS** / **Radix UI** | 原子化 CSS + 無障礙原語。 |
| **Local LLM** | **Ollama** | 最簡單的本地模型管理 (API 相容)。 |
| **Embeddings** | **HuggingFace Transformers** | 離線執行 CLIP/BERT，無費用的關鍵。 |
| **Vector DB** | **ChromaDB** (Local Persist) | 輕量、Python 原生，無需 Docker。 |

---

## ⚠️ 風險評估 (Risk Assessment)

1.  **安裝門檻變高**: 使用者除了 Python，可能需要安裝 Node.js (開發者) 或我們需提供預編譯好的 `dist/`。
    *   *對策*: CI/CD 自動編譯前端，Release 只釋出包含 `dist/` 的 Python 包。
2.  **硬體需求上升**: 跑 Embedding 和 LLM 需要 RAM/VRAM。
    *   *對策*: 功能模組化開關。低配機器可關閉 AI 功能，只用 React 前端。

---

## 🔴 技術債清償 (Technical Debt - Linus Report 2024-12-30)

> **來源**: `1230-審核報告.md`
> **核心判斷**: 專案處於「能跑但脆弱」的 V1.5 狀態。Schema V2 有正確的想法，但程式碼還停留在 V1 的補丁思維。

### The Linus Way: 三步驟修正

| 步驟 | 問題 | 解法 | 預期效果 |
|------|------|------|----------|
| **1. 淨化資料結構** | `Notes.type` 與 `category_id` 雙重事實 | 刪除 `Notes.type`，移除 `get_category_id_by_name` | 程式碼 -50 行，Bug -50% |
| **2. 真正的任務隊列** | `ThreadPoolExecutor` 在 WSGI 中啟動，重啟丟失任務 | 使用 `AI_Tasks` 表 + 獨立 Worker Process | 任務持久化，崩潰不丟失 |
| **3. 重構查詢邏輯** | `get_notes` 160 行義大利麵條 | 提取 `NoteQueryBuilder` 類別 | 新增過濾條件只需改一處 |

### 程式碼審查摘要 (crud.py)

| 項目 | 評分 | 評論 |
|------|------|------|
| **品味** | 🟡 | 用 `get_category_id_by_name` 掩蓋架構錯誤是壞品味；使用 SQLite JSON 功能是好品味 |
| **結構** | 🔴 | `get_notes` 太過龐大，`_do_embedding` 定義在函式內部很醜陋 |
| **安全** | 🟡 | FTS5 字串處理較原始，但有意識到 DoS 風險 |

> **Linus 觀點**: "Design the architecture, create the data structures, and then write the code."
> 別再寫 Python 補丁了。修好你的 Database Schema，程式碼自然會變簡單。

---

**Next Step**: 請參考 `docs/TODO-V2.md` 查看詳細執行清單。**Phase 0 現為最高優先級**。

---

## 🚀 7. 部署與更新策略 (Deployment & Updates)

> **目標**: 確保本地應用程式 (Local App) 能夠平滑升級，且不丟失使用者數據。
> **原則**: 程式與數據分離 (Code/Data Separation)。

### 7.1 資料庫遷移 (Startup Migration)
*   **機制**: 每次應用啟動時 (`create_app()`)，自動檢查資料庫版本。
*   **實作**: 在 `init_db()` 中比對當前 Schema 與程式碼期望的版本，若落後則自動執行 `ALTER TABLE`。
*   **優勢**: 安裝包只需替換 `.exe`，無需額外的 SQL 腳本工具，實現「無痛升級」。

### 7.2 安裝包邏輯 (Installer Logic)
*   **強制覆蓋 (Overwrite)**: 程式本體 (`Prism.exe`, `dist/`, `.pyd`)。
*   **絕對保留 (Keep)**:
    *   `prism.db` (資料庫)
    *   `config.json` (設定檔)
    *   `uploads/` & `docs/attachments/` (使用者檔案)
*   **路徑建議**: 
    *   **Portable Mode**: DB 在安裝目錄 (需設定 Installer `onlyifdoesntexist`)。
    *   **Standard Mode**: DB 在 `%APPDATA%/Prism` (最安全，強烈建議未來採用)。

### 7.3 在線升級 (Online Update)
*   **Plan A (簡易版)**: 檢查 GitHub Release -> 提示下載 -> 使用者手動執行安裝包。
*   **Plan B (體驗版)**: 內建 `updater.exe` -> 下載 ZIP -> 關閉主程式 -> 解壓覆蓋 -> 重啟。
