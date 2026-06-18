# Prism: Headless Knowledge Management System

> ⚠️ **此文件為 V2 規劃期歷史記錄（2024–2026 重構過程）。現行戰略以 README.md 與 docs/TODO.md 為準，本檔不再更新。**

> **Vision**: 輕量、高速的本地知識管理中樞，同時作為外部 Agent 的 **Headless KMS API**。
> **Core Strategy**: **Headless Architecture** (Python 後端 + React 前端) + **純關鍵字卡片搜尋**。
> **2026-04-04**: AI 功能已拔除（NVIDIA NIM / Ollama / sentence-transformers），專注純筆記 + API 服務。

---

## 🏗️ 1. 架構現代化 (Architectural Shift)

為了支撐更復雜的互動（如畫布視圖、即時 AI 對話），我們必須償還技術債，轉向現代化前端架構。

### 1.1 前後端分離 (Headless)
*   **Backend**: `Flask` (Python)
    *   **角色轉變**: 不再渲染 HTML，轉型為純 API Server (JSON only)。
    *   **搜尋能力**: `GET /api/notes?q=...` 覆蓋卡片標題、內文、備註、附件、標籤；標題 / 內文使用 SQLite FTS5，其餘欄位走 SQL 關聯與文字附件檔案比對。
*   **Frontend**: `Vite` + `React` + `TypeScript` + `TailwindCSS`
    *   **優勢**: HMR 極速開發、生態系豐富 (React-Flow, DND-Kit)、組件化復用。
    *   **狀態管理**: `Zustand` (輕量級取代 Redux)。
    *   **路由**: `React Router v6`。

### 1.2 資料層升級 (Next-Gen Data) ~~（已凍結 / 不再規劃）~~
*   ~~**Vector Store**: 引入 `ChromaDB` (嵌入式) 或 `SQLite-VSS`。~~
    *   ~~用於儲存圖片特徵值 (Semantic Embeddings)。~~
*   ~~**Graph Relations**: 在 SQLite 中強化關聯 (Edges table)，支撐知識圖譜。~~

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

### 階段三：本地智慧 (Phase 3: Local Intelligence) ❌ 已拔除 (v2.3.0, 2026-04-04)

> **2026-04-04 決策**: AI 功能已全面移除。Prism 轉型為純筆記 + Headless KMS。
> AI 交由外部 Agent（如 Claude Code / MCP）呼叫 API 處理。
> 詳見 `docs/過期/20260404-重構評估報告.md`（私人文件，不在版本庫）。

1.  ~~**AI Tagging (Auto-Label)**~~ — 已移除（Ollama / LLaVA）
2.  ~~**Semantic Search**~~ — 已移除（CLIP / Sentence-Transformers / Embeddings）
3.  **Graph/Canvas View**: 🧊 凍結（bundle 體積大，ROI 低）
4.  **Prompt Lineage (Card Versioning)**: ✅ 保留
    *   `parent_id` 欄位支援卡片分支，記錄 Prompt 演變過程。
5.  ~~**AI Gateway / NVIDIA NIM**~~ — 已移除（v2.3.0）
6.  **Image Management Enhancement (v1.5.0)**: ✅ (2026-02-27)
    *   編輯器 Images tab 新增批次選取、設為封面 (cover_image)、批次刪除功能。
    *   每張圖片支援個別操作：設為封面、複製語法、移除引用、刪除檔案。
7.  **Port Configuration (v1.5.0)**: ✅ (2026-02-27)
    *   端口自選 UI (Settings Modal)，支援偏好端口、自動備用、備用範圍。
    *   智能端口搜尋 (`find_available_port`) 讀取 `.port_config`，處理 WinError 10013。
8.  **Unsaved Changes Guard (v1.5.1)**: ✅ (2026-02-27)
    *   V2 React 版 NoteEditor 新增未儲存變更偵測（與 V1 Vue 版行為對齊）。
    *   點擊背景、按 ESC、按 X 關閉時，若有變更則彈出確認對話框。
9.  **UX 強化 (Phase 9)**: ✅ (2026-03-15)
    *   **來源**: `docs/20260315-claude4.6-綜合報告.md` (Claude 4.6 UI/UX 綜合檢閱)
    *   全域錯誤攔截器 — axios interceptor 統一處理網路錯誤 / 5xx / 404。
    *   ConfirmDialog — 取代全部 11 處 `window.confirm()`，支援暗色主題 + danger/warning 變體。
    *   標題 autoFocus — NoteEditor 開啟時自動聚焦標題欄位。
    *   標籤自動補全 — EditorSidebar 模糊匹配現有標籤 + 鍵盤導覽 + 使用次數顯示。
    *   色彩對比度修正 — `--color-text-muted` 暗色 #848b98 / 亮色 #525252，達 WCAG AA。
    *   **待辦（列入技術債）**: NoteEditor 拆分 hooks、`any` 型別清理、Toast Zustand 遷移、Light Theme glass border。

### 2.5 🧪 測試策略 (Testing Philosophy)
> **來源**: 經驗學 (V1.4.2 Legacy Analysis)
> **原則**: **Pragmatic Testing** (實用主義測試)。
> **狀態**: ✅ 基礎設施完成 (2024-12-17)

*   **✅ API 自動化 (pytest)**: 以 `test_run.log` 為準（70+）
    * 核心 CRUD API 測試 (`tests/test_notes_crud.py`, `test_tags.py`, etc.)
    * 批次操作測試、上傳安全性測試
*   **✅ E2E 自動化 (Playwright)**: 核心流程測試
*   **🟡 手動測試**: UI 互動與體驗驗證 (詳見 `TODO.md` Phase 6.4)

### 2.6 🔄 V1 功能移植 (V1 Feature Porting)
> **來源**: V1.4.2 功能對比分析 (2024-12-30)
> **原則**: 保持 V2 與 V1 功能對等，避免功能回歸

| 優先級 | 功能 | V1 位置 | V2 狀態 |
|--------|------|---------|---------|
| ✅ | **主題色彩 (Color Theme)** | `useSettings.js` L66-84 | ✅ 已完成 (Phase 0.4) |
| ✅ | 卡片開啟模式 (preview/reading/edit) | `useSettings.js` L63 | ✅ 已完成 (Phase 0.4) |
| ✅ | 圖片保存模式 (both/thumbnail_only) | `useSettings.js` L60 | ✅ 已完成 (Phase 0.4) |
| ✅ | 快速新增預設分類 | `useSettings.js` L52 | ✅ 已完成 (Phase 0.4) |
| ✅ | 自動載入更多 (無限滾動) | `useSettings.js` L49 | ✅ 已完成 (Phase 0.4) |
| 🧊 | i18n 多語系 | `useI18n.js` | 已預留架構 |
| 🧊 | 啟動時自動開啟瀏覽器 | `useSettings.js` L391 | EXE 打包時處理 |
| ✅ | **圖片管理增強 (v1.5.0)** | `useEditor.js` | ✅ 已完成 (2026-02-27) |
| ✅ | **端口自選 (v1.5.0)** | `useSettings.js` + `app.py` | ✅ 已完成 (2026-02-27) |

**實作順序**:
1. **主題色彩**: 新增 6 個 `data-theme` CSS 變體 + 設定 UI
2. **卡片開啟模式**: 新增 localStorage 偏好 + 套用到 NoteCard
3. **圖片保存模式**: 新增設定 + 傳遞給 upload API
4. **快速新增預設分類**: 新增設定 + 套用到 Header 新增按鈕
5. **無限滾動**: 新增設定 + 實作 scroll 監聽
6. **圖片管理**: ✅ 編輯器 Images tab 批次選取/刪除/設封面
7. **端口自選**: ✅ Settings 端口設定 + 智能 fallback

---

## 🎒 3. 技術堆疊清單 (Tech Stack)

| 領域 | 技術選型 | 說明 |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+ / Flask | 純 JSON API Server，Blueprint 模組化 |
| **Frontend** | React 18 / TypeScript / Vite | SPA，Zustand 狀態管理，HMR 開發 |
| **UI** | TailwindCSS + CSS 變數 | `--color-*` 主題系統，6 套色盤 |
| **Search** | SQLite FTS5 + SQL 關聯 + 文字附件檔案比對 | 純關鍵字卡片搜尋，零額外依賴，無 AI |
| **Database** | SQLite (WAL Mode) | 單檔、高效、可攜，Migration v1–v14 |
| **Deploy** | Source / Dev mode、Raspberry Pi；PyInstaller 為歷史規劃 / 內部打包方向 | systemd + Caddy 無頭伺服器；EXE / Portable 非目前穩定主線 |

---

## ⚠️ 風險評估 (Risk Assessment)

1.  **前端建置門檻**: 使用者需 Node.js 才能重新建置前端。
    *   *對策*: Release 版本附帶預建置的 `frontend/dist/`，一般使用者無需 Node.js。
2.  **SQLite 單檔並發限制**: WAL 模式已緩解，但高並發寫入仍有限制。
    *   *對策*: 個人工具定位，單使用者場景，WAL 已足夠。
3.  **PyInstaller EXE 更新**: Windows 不能自覆蓋執行中 EXE。
    *   *對策*: Plan A（check-update API + 手動下載）已完成；自動更新器（Plan B）凍結。

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

**Next Step**: 請參考 `docs/TODO.md` 查看詳細執行清單。

---

## 🚀 7. 部署與更新策略 (Deployment & Updates)

> **目標**: 確保本地應用程式 (Local App) 能夠平滑升級，且不丟失使用者數據。
> **原則**: 程式與數據分離 (Code/Data Separation)。
> **現況補註 (2026-05-26)**: 以下安裝包 / Portable / PyInstaller 內容屬 V2 規劃期歷史與內部打包方向，不代表 v2.5 已有正式「零依賴、一鍵啟動」發佈。現行穩定使用方式以 README.md 的 Source / Dev mode 與 DEPLOY-PI.md 的 Pi 部署為準。

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
*   **Plan A (簡易版)** ✅ 已實作 (v2.1.0): 檢查 GitHub Release -> 提示下載 -> 使用者手動執行安裝包。
    *   後端 `GET /api/system/check-update` 查詢 GitHub Releases API。
    *   前端 `UpdateSection.tsx` 顯示版本狀態與下載連結。
*   **Plan B (體驗版)** 🧊 凍結: 內建 `updater.exe` -> 下載 ZIP -> 關閉主程式 -> 解壓覆蓋 -> 重啟。
    *   凍結原因見 `TODO.md` Phase 7.2。

---

## 🍓 8. 樹莓派與無頭部署 (Raspberry Pi & Headless) ✅ v2.1.1

> **目標**: 在區域網路內以無頭伺服器 (無顯示器) 模式運行，透過簡潔網址存取。
> **狀態**: ✅ 完成 (2026-03-15)
> **詳細部署指南**: `docs/DEPLOYMENT.md` § 樹莓派章節

### 8.1 架構

```
[Windows Browser]
      │ http://prism.local
      ▼
[Raspberry Pi]
  avahi-daemon  →  mDNS 廣播 prism.local
  Caddy :80     →  reverse_proxy localhost:5000
  prism.service →  python3 app.py (PRISM_V2=true)
```

### 8.2 核心元件

| 元件 | 功能 | 狀態 |
|------|------|------|
| `avahi-daemon` | mDNS 廣播 `prism.local` | ✅ |
| `Caddy` | port 80 → 5000 反向代理 | ✅ |
| `systemd prism.service` | 開機自動啟動，`PRISM_V2=true` | ✅ |
| `deploy/raspberry_pi/setup.sh` | 一鍵安裝腳本（冪等） | ✅ |

### 8.3 Windows 客戶端設定

Windows 無原生 mDNS 客戶端，需擇一設定：
*   **方案 A (永久)**: 安裝 Apple Bonjour for Windows。
*   **方案 B (快速)**: 管理員 PowerShell 加入 hosts 記錄：
    ```powershell
    Add-Content 'C:\Windows\System32\drivers\etc\hosts' "`n192.168.0.7 prism.local"
    ```
