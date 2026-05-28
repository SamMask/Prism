# Prism - Modernization & Intelligence Roadmap (TODO)

**狀態**: 🟢 穩定運行 (Stable)
**核心目標**: Headless KMS API + 純關鍵字 FTS 搜尋
**文件參照**: `docs/Prism.md` (歷史背景), `docs/SCHEMA.md` (資料庫規格), `docs/FRONTEND-REDESIGN-PLAN.md` (UI/Go 重構規劃), `Prism_Go_模組逐步重構計劃報告.md` (Go shadow backend), `garbage-can/1230-審核報告.md` (Linus Audit)
**最後更新**: 2026-05-28

---

## ✅ 已完成項目 (Completed Projects)

### 🚨 Phase 0: 架構淨化 (Architecture Purification) ✅ 2024-12-31
> **來源**: Linus-style 審核報告 (`1230-審核報告.md`)

- [x] **0.1 淨化資料結構** — Migration v12: 移除 `Notes.type` 雙重事實，統一用 `category_id`
- [x] **0.2 任務隊列** — Migration v13: `AI_Tasks` 表 + `workers/task_processor.py` 取代 ThreadPoolExecutor
- [x] **0.3 重構查詢** — 提取 `NoteQueryBuilder`，分離 `sanitize_fts_query()` 與 Filter
- [x] **0.4 V1 功能移植** — 主題色彩、卡片開啟模式、圖片保存模式、快速新增預設分類、自動載入更多
- [x] **0.5 殘留清理** — Schema 淨化、FTS5 安全性、拆分 NoteEditor/SettingsPage、VectorStore 執行緒安全

### 🟢 Phase 1: 現代化地基 (The Big Rewrite) ✅
> **目標**: 建立 Vite + React + Flask 的混合開發環境，打通 API 通訊。

- [x] **1.1 前端專案初始化** — Vite + React + TS + Tailwind + Zustand
- [x] **1.2 後端 API 改造** — `PRISM_V2` 模式切換，保留 V1 向後相容
- [x] **1.3 核心組件移植** — `Button`, `Input`, `Modal`, `Toast` 設計系統
- [x] **1.4 開發規範更新** — Versioning、Testing Philosophy、License Policy

### 🟡 Phase 2: 功能復刻 (Feature Parity) ✅
> **目標**: 讓 React 版本擁有 v1.x 的核心功能 (CRUD)。

- [x] **2.1 筆記管理** — MasonryGrid + NoteCard (懸停預覽、快速操作)
- [x] **2.2 編輯器 V2** — 貼上圖片、拖曳上傳
- [x] **2.3 標籤與分類** — TagInput 自動完成、DataManager 管理介面
- [x] **2.4 Prompt Builder** — React Hook 移植、結構化參數表單、權重滑桿

### 🔴 Phase 3: 本地智慧 (Local Intelligence) — ⚠️ AI 已拔除 (2026-04-04)
> **原目標**: 引入 PyTorch / Ollama / Sentence-Transformers。
> **現況**: AI 功能已全部拔除，Prism 轉型為純筆記 + Headless KMS。參見 `docs/20260404-重構評估報告.md`。

- [x] ~~**3.1 智慧標籤**~~ — 已拔除 (Ollama / NVIDIA NIM)
- [x] ~~**3.2 語意搜尋**~~ — 已拔除 (Embeddings / Vector Store / Hybrid Search)
- [x] **3.4 附件系統** — Note_Attachments 表 + 拖曳上傳 + 長文自動分離 (保留)
- [x] ~~**3.5 RAG Knowledge API**~~ — 已拔除
- [x] **3.7 卡片譜系** — 父子繼承 (`as_variant`) + 單表關聯 (保留)

### 🧪 Phase 6: 自動化測試 ✅
- [x] **6.0 安全性修復** — P0/P1/P2 問題
- [x] **6.1 後端 API 測試** — CRUD, Search, AI 服務
- [x] **6.2 前端 E2E** — Playwright 核心流程

### 📦 Phase 7: 打包與更新 ✅ (部分凍結)
- [x] **7.0 建置腳本** — `build_release.py` (Frontend Build + PyInstaller)
- [x] **7.1 下載更新 (Plan A)** ✅ 2026-03-15 — `check-update` API + `UpdateSection.tsx`
- [x] **7.3 啟動遷移** ✅ 2026-03-15 — `init_db()` 移入 `create_app()`，冪等遷移

### 🍓 Phase 8: 樹莓派與無頭部署 ✅ 2026-03-15
> **目標**: 無頭伺服器環境的連線、維運與遠端管理。

- [x] **8.1 反向代理與 mDNS** — avahi-daemon + Caddy (80→5000) + systemd + 一鍵安裝腳本
- [x] **8.2 伺服器管理面板** — 硬體監控 / 日誌檢視 / 服務重啟 / 備份管理 / 版本資訊

### 🖼️ v1.5.0 圖片管理增強 + 端口自選 ✅ 2026-02-27
- [x] **圖片管理** — 批次選取/刪除、設為封面、個別操作 (複製語法/移除引用/刪除檔案)
- [x] **端口自選** — Settings 端口設定 + `.port_config` + WinError 10013 處理 + 智能 fallback

### 🛡️ v1.5.1 未儲存變更防護 ✅ 2026-02-27
- [x] **Unsaved Changes Guard** — 原始快照 + 變更偵測 + 關閉攔截 (背景/ESC/X)

### 🎨 Phase 9: 前端 UX 強化 ✅ 2026-03-15
> **來源**: Claude 4.6 UI/UX 綜合檢閱報告
- [x] **9.1 全域錯誤攔截器** — axios interceptor 統一處理網路錯誤 / 5xx / 404
- [x] **9.2 ConfirmDialog** — 取代全部 11 處 `window.confirm()`，支援暗色主題 + danger/warning 變體
- [x] **9.3 標題 autoFocus** — NoteEditor 開啟時自動聚焦標題欄位
- [x] **9.4 標籤自動補全** — EditorSidebar 模糊匹配現有標籤 + 鍵盤導覽 + 使用次數顯示
- [x] **9.5 色彩對比度修正** — `--color-text-muted` 暗色 #6b7280→#848b98 (≈5.0:1)、亮色 #666→#525252 (≈4.7:1)，達 WCAG AA

---

## 🩹 Phase 10: 體檢報告修補 (cco audit) — ✅ 已完成 v2.4.2

> **來源**: [`docs/過期/20260412-cco-綜合分析報告.md`](./過期/20260412-cco-綜合分析報告.md) (Linus-mode 深度體檢, 2026-04-12)
> **目標**: 清理 v2.3.0 AI 拔除 + v12 `Notes.type` 移除後遺留的殭屍程式碼，補上 SSRF 防護，修正測試地基。
> **執行順序**: P0 → P1 → P2，禁止跳級。

### 🔴 P0 — Critical (上線即炸 / 殭屍欄位)

- [x] **10.1** `routes/system.py` — 移除 `type_category_mismatch` 殭屍 query，`issues` 計算與 response 同步清除
- [x] **10.2** `routes/export.py` — `export_json()` SELECT 改用 `LEFT JOIN Categories c` 取 `c.name as category`，移除 `n.type`

### 🟠 P1 — High (系統性風險)

- [x] **10.3** `tests/conftest.py` — `temp_db()` 改為建立最小 pre-migration base schema，再呼叫 `migrations.run_migrations(conn)` 走真實遷移路徑；移除 `sample_note_data` 中的死欄位 `type`
- [x] **10.4** `routes/upload.py` — 新增 `_is_ssrf_target()` helper，`download_from_url()` 在 scheme 驗證後解析 hostname IP，拒絕 loopback/private/link-local/reserved 目標
- [x] **10.5** `routes/notes/crud.py` — 刪除 `_HAS_PARENT_ID` 模組全域快取，`get_note()` 直接設 `parent_cols`/`parent_join`（schema 已穩定）
- [x] **10.6** `routes/notes/crud.py` — 移除 `delete_note()` 手動 cascade DELETEs，依賴 `ON DELETE CASCADE`；更新過時註解

### 🟡 P2 — Medium (品質 / 一致性)

- [x] **10.7** `config.py` — `PRISM_VERSION` 同步為 `2.4.1`（將在本版完成後升 `2.4.2`）
- [x] **10.8** `frontend/src/services/api.ts` — `ConsistencyCheckResponse` 移除 `type_category_mismatch: number` 死碼
- [x] **10.9** `routes/notes/crud.py` — `update_note()` 內 `existing` 改名 `existing_note`
- [x] **10.10** `routes/upload.py` — `extract_prompt()` 改用 `with Image.open(...) as img` context manager，消除 file handle 洩漏
- [x] **10.11** `routes/server.py` — 新增 `@server_bp.before_request` localhost-only guard，非 `127.0.0.1/::1` 回傳 403
- [x] **10.12** `app.py` — `csrf_protect()` 在生產模式（`V2_MODE=true` + `not debug`）拒絕無 Origin 的 unsafe method

### 📋 補充

- [x] **10.13** 新增 `tests/test_schema_regression.py` — 4 個測試：`type` 欄位已移除、必要欄位存在、AI 欄位已清除、fixture schema 與 migration 輸出一致
- [x] **10.14** `docs/CONTRIBUTING.md` — 加上 Release Checklist（版本同步 / 測試 / build / migration 確認）

---

## 📘 Phase 11: 外部 Agent API 對接文件整理 ✅ 2026-04-24

> **目標**: 以目前實際後端契約為準，整理可直接提供外部 Agent（如 murmur厭世貓）使用的 API 對接文件，並順手清掉阻礙對接的 schema 漂移問題。

- [x] **11.1** 修正 `routes/notes/crud.py` 單筆讀取 `has_parent_id` 未定義造成的 500
- [x] **11.2** 修正 `routes/notes/actions.py` duplicate 仍引用已移除 `Notes.type` 欄位
- [x] **11.3** 修正 `routes/notes/import_.py` / `routes/notes/export.py` / `routes/export.py` 殘留 `Notes.type` 寫法，改回 `category_id` / `category` 相容層
- [x] **11.4** 更新 `docs/API_REFERENCE.md`，重寫為可直接交付外部 Agent 的對接文件，標明限制、回應格式、已知不建議端點

---

## 🔧 Phase 12: 前後端 API 契約修補 ✅ 2026-04-24

> **目標**: 修正前端 API wrapper 與 Flask 路由之間的實際落差，讓設定頁、分類管理、封存/置頂篩選與 migration 診斷都能對上後端契約。

- [x] **12.1** 補回 `GET /api/system/check-update`，支援環境設定、GitHub repository 推導與網路失敗降級回應
- [x] **12.2** 補回 `GET /api/system/migration-status`，直接回傳 `migrations.get_migration_status()`
- [x] **12.3** 修正前端 `deleteCategory()` 改送 `target_category_id`，DataManager 改用預設分類 ID 遷移筆記
- [x] **12.4** 修正 `GET /api/notes` 查詢契約，支援 `archived` / `include_archived` / `pinned_only` / `category_id`
- [x] **12.5** 擴充 note create/update 對 `is_pinned`、`is_archived` 的支援，並保持未傳欄位時不覆寫既有狀態
- [x] **12.6** 補測試覆蓋 system 缺路由、分類刪除遷移、封存/置頂篩選

---

## 🔎 Phase 13: 搜尋範圍擴充 ✅ 2026-05-05

> **目標**: 搜尋欄維持同一個 `GET /api/notes?q=...` 契約，但命中範圍從卡片標題 / 內文擴充到備註、附件、標籤。

- [x] **13.1** 擴充 `GET /api/notes` 搜尋條件，覆蓋 `Notes.title`、`Notes.content`、`Notes.remarks`、`Note_Attachments`、`Tags.name`
- [x] **13.2** 補 pytest 覆蓋標題、內文、備註、附件內容、標籤搜尋
- [x] **13.3** 同步更新 `AGENTS.md`、`docs/API_REFERENCE.md`、`docs/SCHEMA.md`、`docs/ARCHITECTURE.md`、`docs/Prism.md`
- [x] **13.4** 部署到 Raspberry Pi 並驗證 live API

---

## 🧭 Phase 17: Sidebar Filter Navigation — ✅ 已完成 v2.4.9 (2026-05-26)

> **觸發**: 分類/標籤本質是首頁卡片篩選器；在設定頁或其他非首頁頁面點擊時，篩選狀態會變但頁面不跳回首頁，看起來像按鈕失效。
> **目標**: 非首頁點分類/標籤時自動回到首頁並套用篩選；首頁上保留再次點擊同一分類/標籤可取消篩選的原互動。

- [x] **17.1** Sidebar filter routing — `Sidebar` 對分類/標籤 click 加上 route-aware handler；非首頁一律導回 `/` 並套用該篩選。
- [x] **17.2** Category query contract — notes 查詢改送 `category_id`，不再依賴分類名稱 `type` 相容層，避免分類改名後的篩選風險。
- [x] **17.3** 收尾驗證 — `cd frontend && npx tsc --noEmit` / `cd frontend && npm run build` / `pytest tests/ -v` / Browser flow 驗證。

---

## 🧱 Phase 18: UI Redesign + Go Shadow Backend Preparation — 📋 Planned

> **來源**: `docs/New_UI/Prism Redesign - standalone.html`、`Prism_Go_模組逐步重構計劃報告.md`、`docs/FRONTEND-REDESIGN-PLAN.md`
> **目標**: 把新 UI 參考與 Go 模組化重構收斂成可驗證、可回退的小步任務；先固定 API / UI contract，再做 read-only Go shadow backend 與前端 shell 改版。
> **原則**: 前端改版不得阻塞 Go Phase 0；Go Phase 0 不改前端 API contract；不新增 AI/ML、協作 wiki、timeline/social 或 prototype-only `collections` schema。

### 🔒 18.0 Contract Lock / Readiness — ✅ Completed (2026-05-27)

- [x] **18.0.1** Golden response fixtures — 固定 `GET /api/test`、`GET /api/categories`、`GET /api/tags`、`GET /api/notes`、`GET /api/notes/<id>` 的 Python baseline；見 `tests/fixtures/api_golden/` 與 `tests/test_phase18_api_golden.py`。
- [x] **18.0.2** Endpoint side-effect map — 標記 readonly / DB-write / file-write / server-local-only，作為 Go migration 與 LLM tool surface 邊界；見 `docs/contracts/phase18-readiness.md`。
- [x] **18.0.3** UI route/workflow map — 盤點 Home、Sidebar filters、Prompt Builder、Settings、NoteEditor、EditablePreview 的現有流程與 regression points；見 `docs/contracts/phase18-readiness.md`。
- [x] **18.0.4** API manifest draft — 先文件化 read-only tool surface，不改 runtime、不引入 AI；見 `docs/contracts/api-readonly-manifest.json`。
- **收尾驗證**：`pytest tests/test_phase18_api_golden.py -v` → 1 passed；`pytest tests/ -v` → 83 passed。

### 🖼️ 18.1 Frontend Shell Redesign

- [x] **18.1.1** Layout / Sidebar / Header refresh — 採納原型的資訊密度與 shell 層級，保留現有 React/Vite/Zustand/Tailwind stack；完成 shell token、Sidebar 導覽/分類/系統/標籤重排、Header topbar、Home section header、desktop/mobile icon rail 與底部狀態列。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 83 passed；Chrome headless desktop/mobile screenshot；CDP flow 驗證 Settings 點分類會回 Home 並套用 `category_id` filter。
- [x] **18.1.2** View modes — grid / list / compact list 先做 local UI state，不做 server persistence；完成 Header 三段 view toggle、Home grid/list/compact render、Settings 外觀同步入口與 `localStorage` 持久化。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 83 passed；Chrome headless/CDP 驗證 grid/list/compact DOM state、`prism.viewMode` reload persistence、Settings 外觀切換與 desktop/mobile screenshot。
- [x] **18.1.3** Command palette MVP — 新增全域 `Ctrl+K` / Header 入口，支援 navigation、recent notes、new note、theme/settings actions；新增筆記只開啟既有 editor，不直接寫入 DB，危險寫入仍走既有確認流程。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 83 passed；Playwright fallback 驗證 palette 開啟、鍵盤搜尋、最近筆記/新增筆記/設定導覽、Header 按鈕與 mobile viewport；console 僅有既有 React Router v7 future warnings。
- [x] **18.1.4** Filter strip — 新增 Layout 層水平 filter strip，提供全部、封存、分類、標籤 chip；Home 上重點同一分類/標籤可取消，非 Home 點分類/標籤/封存會導回 `/` 並套用篩選，分類查詢維持 `category_id` query contract。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 83 passed；Playwright fallback 驗證 desktop/mobile strip、Settings/Prompt Builder route-aware 導回 Home、分類 chip request 使用 `/api/notes?...&category_id=1&sort=updated`；console 僅有既有 React Router v7 future warnings。

### ✏️ 18.2 Reading / Editor Workflow

- [x] **18.2.1** Reading view — 新增專注閱讀面板，卡片預設 `reading` 模式會先開 read-only reading modal，並用既有 `GET /api/notes/<id>` 補 detail；快速動作提供編輯、複製、置頂/封存，編輯會轉回既有 NoteEditor，不改 note detail API。
- [x] **18.2.2** Editor modal/layout refinement — NoteEditor 改為更寬的 full modal、桌面編輯區 + 右側 metadata 欄、手機上下堆疊；`preview` 卡片開啟模式會直接進既有 EditablePreview，仍重用 `useNoteForm` / `EditorToolbar` / `EditorSidebar`，不換 editor stack、不新增 WYSIWYG dependency。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 83 passed；Playwright fallback 驗證 reading modal、`GET /api/notes/143` detail request、reading→edit、preview initial mode、desktop/mobile editor screenshot；console 僅有既有 React Router v7 future warnings。
- [x] **18.2.3** Preview Editing regression lock — 確認 Preview 內就地改文字、移除圖片引用、封面同步清空行為不退化；新增 Preview 文字/圖片操作的穩定測試標記，實測 Preview 內改文字後儲存、移除 Markdown 圖片引用並同步清空 matching cover。
- [x] **18.2.4** Attachment/Image UX pass — 沿用 `AttachmentPanel`、`ImageManagementPanel`、`imageReferences`，不提前碰 Go file phase；新增共用 `extractImageReferences()`，讓 ImageManagementPanel 同時列出 Markdown 與 HTML `<img>` 引用，並保留既有 `removeImageReferences()` 移除流程。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 83 passed；Playwright fallback 建立臨時筆記後驗證 Preview 就地改文字、Preview 移除圖片引用、cover 清空、ImageManagementPanel 偵測並移除 HTML image、AttachmentPanel / upload action 可見；console 僅有 Vite dev 訊息、React DevTools 提示與既有 React Router v7 future warnings。

### 🧰 18.3 Prompt Builder / Settings Re-layout

- [x] **18.3.1** Prompt Builder density pass — 改善表單層級、preview 與儲存動線，維持現有輸出 contract；改為 desktop 設定/預覽雙欄、mobile 上下堆疊，動作列固定在設定區底部。
- [x] **18.3.2** Settings tabs — 外觀 / 資料 / 搜尋 / 部署 / 關於只重排現有功能，不新增 server API；既有 Appearance、資料維護/備份/危險區、分類標籤、部署/更新/Server dashboard、About 依 tab 分組。
- [x] **18.3.3** Server dashboard safety check — 保留 `/api/server/*` localhost-only 邊界與既有錯誤處理；部署 tab 與 ServerDashboard 補 local-only 邊界提示，仍只呼叫既有 `/api/server/hardware`、`/api/server/version`、`/api/server/backup/list`。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 83 passed；Playwright fallback 驗證 Prompt Builder desktop/mobile、輸入描述後 preview 更新、Settings 五個 tabs 切換、部署 tab local-only guard 與 ServerDashboard；console 僅有 Vite dev 訊息、React DevTools 提示與既有 React Router v7 future warnings。
- [x] **18.3.4** Appearance aesthetic modes — 外觀 tab 新增 `Linear` / `Editorial` / `Studio` 三種本機美學方向，使用 `localStorage` + `data-aesthetic` 切換字體層級、卡片節奏與整體 palette；`data-accent` 主色、邊角圓潤度與側邊欄寬度皆為本機 UI 偏好，不新增 server API 或 schema。
- [x] **18.3.5** Filename-like search regression — `GET /api/notes?q=...` 將標點視為 token 分隔，修正 `todo.md` 這類卡片內容 / 檔名式查詢因 `todomd` 黏詞而查不到的問題。

### 🧪 18.4 Go Read Shadow Backend

- [x] **18.4.1** Go skeleton — `go mod init`、config、SQLite connection、React dist embed；開發期禁止連正式 `knowledge.db`。已建立 `go-shadow/` 獨立 Go module，需明確傳入 copied DB，預設拒絕 `knowledge.db`，SQLite 啟用 `PRAGMA query_only = ON`。
- [x] **18.4.2** Read-only endpoints — `/api/test`、categories、tags、notes list、note detail，response shape 對齊 Python。Go shadow 只註冊 GET read surface，寫入、檔案、maintenance、`/api/server/*` 仍排除。
- [x] **18.4.3** Python vs Go diff harness — 同一 DB 副本、同一 query set，比對 JSON response。新增 `tests/test_phase18_go_shadow_contract.py`：Go CLI 可用時會用 pytest `temp_db` 啟動 Go server，逐路徑比對 Flask client JSON；本機目前無 Go CLI 時 runtime diff 明確 skip。
- [x] **18.4.4** Closure gate — Go 端未實作任何 POST/PUT/DELETE，Python `pytest tests/ -v` 維持綠燈。**收尾驗證**：`go version` → go1.26.3 windows/amd64；`cd go-shadow && go mod tidy && go test ./...` → passed；`pytest tests/test_phase18_go_shadow_contract.py -v -s` → 2 passed（含 Python vs Go response diff，無 skip）；`pytest tests/ -v` → 87 passed；static gate 驗證 Go source 無 `http.MethodPost` / `http.MethodPut` / `http.MethodDelete`，且包含 query-only 與 production DB refusal。

### ⏸️ 本階段暫緩

- `collections` / smart folder DB schema。
- server-side UI preference persistence。
- Wails / desktop mode rewrite。
- AI chat、embedding、semantic search、reranker、agent runner。
- collaboration、comments、permissions、realtime。
- upload / attachment / cleanup / export 的 Go 版。

---

## ✏️ Phase 16: Preview Editing UX — ✅ 已完成 v2.4.8 (2026-05-26)

> **觸發**: Preview 模式只能看渲染結果，實際修字或移除圖片仍要切回 Markdown 原始編輯 / 側欄圖片管理；日常編輯流程不夠順手。
> **目標**: 保持 Preview 的閱讀感，同時允許就地修改文字區塊與移除圖片引用；不新增後端 API、不改 DB schema。

- [x] **16.1** `EditablePreview` — Preview 模式改為可互動：文字區塊 hover 後可切入小型 Markdown textarea 直接修改內容，離焦回到預覽。
- [x] **16.2** Preview 圖片移除 — 對獨立 Markdown / HTML 圖片渲染刪除按鈕，直接從內容移除引用；若該圖是封面，同步清空 `cover_image`。
- [x] **16.3** 圖片移除 helper 共用 — 側欄 `ImageManagementPanel` 與 Preview 圖片刪除共用同一套 Markdown / HTML image reference 移除邏輯。
- [x] **16.4** 收尾驗證 — `cd frontend && npx tsc --noEmit` / `cd frontend && npm run build` / `pytest tests/ -v` 全通過；Browser flow 實測 Preview 內可改文字、刪圖片引用且 console 無 warn/error；`PRISM_VERSION` / README badge / TODO Changelog 同步至 v2.4.8。

### ⏸️ 本輪不處理

- 完整 WYSIWYG Markdown round-trip（例如直接在渲染後的 bold / table / list DOM 上保留所有 Markdown 語法細節）— 目前採用「預覽中就地切入小型 Markdown 區塊」以避免引入大型 editor 依賴。
- 實體圖片檔案刪除 — Preview 只移除內容引用；永久刪檔仍由既有側欄「圖片管理」與確認對話處理。

---

## 💾 Phase 15: 維護模式雜項 (Maintenance Sundries) — ✅ 已完成 v2.4.7 (2026-05-13)

> **觸發**: Phase 14 收尾後用戶確認啟動兩項：(a) 自動備份排程確認、(b) Markdown 匯出。
> **背景發現** (2026-05-13 重新驗證)：
> - 真正的備份位置是 `backups/`（不是中文 `資料庫備份/`）；Pi `backups/` 目前有 3 份：4/4、4/24、5/13，**用戶手動點 UI 觸發、間隔約 3 週**
> - 後端 `routes/server.py` 已有 `/api/server/backup/download` + `/rotate (keep=3)`，但**完全靠手動觸發**——crontab 空、systemd timer 空
> - 頂層中文資料夾 `資料庫備份/` 是 V1 殘留 dead folder（4/4 後就沒動），實際使用的是英文 `backups/`
> - **Pi 儲存媒介是 SSD 不是 SD 卡**（用戶 2026-05-13 確認）——失效機率比 SD 卡低一個量級，無寫入次數疲勞集中、無 SD 卡控制器悲劇
> **真實風險**（最終版）：SSD 仍是單點故障（控制器、檔案系統損毀、電源異常 / 雷擊）。手動備份 ~3 週習慣已覆蓋大部分情境；自動化純粹是「假期 / 出差 / 忘記時的便宜保險」。**整個 Phase 15 沒有 P0/P1**。

### 🟢 自動備份排程（便宜的保險）

- [x] **15.1** Pi 加 `prism-backup.timer` (每週日 03:00) + `prism-backup.service` 觸發 `/home/mask070924/prism/scripts/auto-backup.sh`
- [x] **15.2** 腳本內 `--http1.1 --fail` 下載 + `Origin: https://prism.local` POST rotate keep=8（**踩過的坑**：Caddy → Werkzeug HTTP/2 stream 收尾不乾淨會讓 curl exit 92，必須強制 HTTP/1.1）
- [x] **15.3** 手動 `systemctl start prism-backup.service` 驗證通過（產出完整 4MB 備份 + rotate 成功）
- [x] **15.4** `DEPLOY-PI.md` 補「自動備份排程」章節（含 service / timer / script 完整安裝指令 + 還原備份範例）

### 🟢 Dead folder 清理

- [x] **15.5** Windows + Pi 雙端 `git rm -r 資料庫備份/` / `rm -rf 資料庫備份/`，audit §4.5 path encoding 隱患同步清除

### 🟢 Markdown 匯出（可離線、跨工具可讀）

- [x] **15.6** `routes/export.py` 新增 `GET /api/export/markdown` — 回傳 zip：`{id:04d}-{slug(title)}.md` + YAML frontmatter (`id` / `title` / `category` / `tags` / `is_pinned` / `is_archived` / `created_at` / `updated_at` / 可選 `remarks`) + body + `_manifest.json`
- [x] **15.7** `tests/test_export_markdown.py` — 4 測試（zip 結構 / frontmatter 欄位 / manifest 計數 / 空標題 edge case），全綠
- [x] **15.8** `BackupImportSection.tsx` 加「下載 .zip」按鈕，呼叫 `api.exportMarkdown()`
- [x] **15.9** `docs/API_REFERENCE.md` §12 加 `/api/export/markdown` 端點說明（含 frontmatter 規格）

### 📋 收尾驗證

- [x] **15.10** `pytest tests/ -v` → **80 passed** (+4)，test_run.log 已覆寫
- [x] **15.11** `npx tsc --noEmit` 零錯誤；`npm run build` 1509 modules / 2.26s
- [x] **15.12** `PRISM_VERSION` → `2.4.7`；README badge 同步；Changelog v2.4.7 已加
- [x] **15.13** 部署到 Pi 驗證：timer next run = Sun 2026-05-17 03:00；markdown export 透過 Caddy 取得 178 檔 zip（177 筆 + manifest），中文檔名保留正確

### ⏸️ 本輪不處理

- 雙向 markdown 匯入（write-back）— 寫端是 1-way 比較安全，避免外部編輯造成 schema 漂移；若有需求再開 Phase 15.5
- markdown frontmatter 包含附件二進位 — 附件用獨立 `attachments/` 資料夾在 zip 內，若太複雜本輪先跳過、frontmatter 只記附件路徑

---

## 🧹 Phase 14: 深度審計修補 (Deep Audit Fixes) — ✅ 已完成 v2.4.6 (2026-05-13)

> **來源**: [`docs/20260513-deep-audit-report.md`](./20260513-deep-audit-report.md) (Claude Opus 4.7 read-only audit, 2026-05-13)
> **目標**: 修補 v2.4.5 後文件層的時差（README/INDEX/TODO/Prism 引用 404、雙頭真理、殭屍 docstring/腳本、測試文件脫節），補上 SSRF / localhost / production-CSRF 的回歸測試。**程式地基已乾淨，本輪以「修承諾對齊事實」為主。**
> **執行順序**: P1 文件閘門 → P1 回歸測試 → P2 殘留清理 → 收尾驗證。禁止跳級。

### 🔴 P1 — 文件導航閘門修補（純文件，不碰程式）

- [x] **14.1** `README.md` / `docs/INDEX.md` / `docs/CONTRIBUTING.md` — 把所有 `docs/20260412-cco-綜合分析報告.md` 引用統一為 `docs/過期/20260412-cco-綜合分析報告.md`（5 條死連結，見審計 §3.2）
- [x] **14.2** `docs/INDEX.md` — 修正維護狀態欄位：cco 報告改 ✅ 已完成 v2.4.2、`SEQUENCE-UPLOAD.md` 改 ✅ 已更新、`API_REFERENCE.md` 改 ✅ 已重寫 (2026-05-05)（見審計 §3.6）
- [x] **14.3** `docs/TODO.md` 頭部 — line 4 移除「Local AI」改為「Headless KMS API + 純關鍵字 FTS 搜尋」；line 5 `1230-審核報告.md` 補 `garbage-can/` prefix；line 6 日期改 `2026-05-13`；line 80 Phase 10 從 🔴 Pending 改 ✅ 已完成 v2.4.2（見審計 §3.3）
- [x] **14.4** `AGENTS.md` ↔ `CLAUDE.md` 雙份完整同步（2026-05-13 補做）：兩份內容對齊（合併 AGENTS 的 Search 欄位描述 + CLAUDE 的 DEPLOY-PI.md 列、Prism.md 標為已凍結、執行規則改為「兩份都要改」）；兩份頂部加 sync banner；`docs/CONTRIBUTING.md` Release Checklist 補 `diff AGENTS.md CLAUDE.md` 比對行；`diff` 驗證僅有 banner 互指對方檔名的差異
- [x] **14.5** `docs/Prism.md` — **明確標記為歷史檔案**（決議：用戶現處純使用模式，戰略路線圖維護不下去；保留 V1→V2 重構決策脈絡的歷史價值）
- [x] **14.6** `tests/README.md` — 刪除過期的 10 檔表格（實際 24+ 檔），改為 `pytest --collect-only` 自動導覽 + 「以 test_run.log 為實際參考」（見審計 §3.7）
- [x] **14.7** `docs/CONTRIBUTING.md` — line 49 `v1–v14` 改 `v1–v15`；line 115 `61 passed` 改「全綠（以 test_run.log 為準）」；Release Checklist 末尾加一行「文件版本 / 日期同步檢查」（見審計 §3.9）

### 🔴 P1 — 安全回歸測試（先加測試，不改程式）

- [x] **14.8** 新增 `tests/test_security_guards.py` — 4 個測試（`test_ssrf_blocks_loopback` / `test_ssrf_blocks_private_range` / `test_server_api_localhost_only` / `test_csrf_production_blocks_anonymous`）

### 🟡 P2 — 殭屍 / docstring 殘留清理（在 14.8 測試保護下動 code）

- [x] **14.9** `routes/system.py:284-296` — `check_consistency()` docstring 與 Response 範例移除 `type_category_mismatch` 殭屍描述，改寫為現況（v12 已移除 `Notes.type`）（見審計 §3.4）
- [x] **14.10** 刪除 `scripts/check_deps.py`（殭屍：仍 import 已拔除的 `numpy` / `sentence_transformers`）
- [x] **14.11** 刪除 `tests/test_offline_mode.py`（V1 Jinja2 遺物，不被 pytest 收集）

### 📋 收尾驗證 (Closure)

- [x] **14.12** 執行 `pytest tests/ -v 2>&1 | tee test_run.log` 重新留下證據（76 passed，2026-05-13 22:24）
- [x] **14.13** 執行 `cd frontend && npx tsc --noEmit && npm run build`，確認 tsc 零錯誤、build 成功
- [x] **14.14** `config.py` `PRISM_VERSION` 升 `2.4.6`；`README.md` 開頭 badge 同步
- [x] **14.15** TODO.md Changelog 新增 v2.4.6 條目（合併 14.1–14.16 摘要）

### 📁 目錄歸檔（依用戶決議）

- [x] **14.16** （2026-05-13 補做）`git mv demo docs/過期/demo`；`README.md` 「專案結構」章節新增 `garbage-can/`（個人歸檔）+ `docs/過期/` 註記，順手把 `migrations/ (v1 → v14)` 修為 `v15`、`tests/ (61+)` 改為「執行 pytest --collect-only 列出，全綠以 test_run.log 為準」

### 💡 未來功能候選（未承諾）

> 已決議啟動的見 Phase 15。其餘想法暫不列入。

- ~~**Prism MCP Server wrapper**~~ — 已評估排除（2026-05-13）：用戶日常工作流為「Web UI 查筆記 + Claude Code 寫程式」兩條線不交集；MCP 不省 token（response 內容照計），單次查詢僅省 ~50 token，需月呼叫 100+ 次才有感，使用模式不符。

---

### ⏸️ 本輪不處理（已評估，列入未來追蹤）

- **R10 / §4.2** `init_db()` 與 migrations 雙寫 schema（v9 ADD → v14 DROP `text_embedding` 對 fresh DB 是空操作）— 屬品味債，不是 bug，未來重寫 init_db 時一併處理
- **R11** `auto_fix_consistency()` 每次冷啟動掃全表 — cco 已決議「等規模到一萬筆再優化」
- **§5.3** `tests/test_batch_type_sync.py` 自定 `get_db()` 繞過 db.py — 雖違反 CLAUDE.md 精神但測試本身有效，列入未來重構
- **§4.3 / §4.4 / §4.5** `frontend/src/i18n/`、`services/` 空殼、`tools/` `build/` `資料庫備份/` 文件未涵蓋 — 待 Phase 15 目錄盤點

### ✅ 已決議（2026-05-13 用戶確認）

1. ✅ **體檢報告位置**：保留在 `docs/過期/`，所有引用統一指向該路徑（見 14.1）
2. ✅ **AGENTS.md / CLAUDE.md**：保留雙份完整內容並要求同步（理由：Codex 可作另一視角 debug）（見 14.4）
3. ✅ **garbage-can / demo**：garbage-can 保留為個人歸檔；demo 搬至 `docs/過期/`（見 14.16）
4. ✅ **Prism.md**：明確標記為歷史檔案，不再更新（見 14.5）
5. ✅ **新 epic**：v2.4.6 後仍維護模式；新功能候選暫列 backlog（見下方「未來功能候選」）

---

## 🧊 待辦 / 凍結項目 (Backlog / Icebox)

### ~~Phase 3: 本地智慧 (剩餘)~~ — ❌ 已全部拔除 (2026-04-04)

#### ~~3.6 🔌 AI Gateway (Pluggable AI Providers)~~ — 已拔除
> **結果**: v2.3.0 全面拔除 AI 功能。NVIDIA NIM、Ollama、sentence-transformers、numpy 等依賴已移除。
> **原因**: 參見 `docs/20260404-重構評估報告.md` — Prism 轉型為純 Headless KMS，AI 交由外部 Agent 處理。
- [x] ~~**3.6.1 NVIDIA NIM Provider**~~ — 已拔除
- [x] ~~**3.6.2 AI Prompt Optimizer**~~ — 已取消 (AI 全面移除)
- [x] ~~**3.6.3 OpenAI-Compatible Client**~~ — 已取消 (AI 全面移除)
- [x] ~~**3.6.4 AI 依賴剝離評估**~~ — 已完成 (numpy/sentence-transformers 已移除)

#### 3.3 🗺️ 知識畫布 (Canvas / Graph View) ❌ 已廢棄 (2026-05-13)
> **廢棄原因**: 個人 KMS（規模 ~200 筆）視覺化價值近零——你早知道自己有什麼；Obsidian graph view 公認雞肋。Bundle 500KB 增量無法回收。

#### 3.7.3 參數差異比對 (Diff View) ❌ 已廢棄 (2026-05-13)
> **廢棄原因**: 個人不會回頭比對 prompt 變體；Parent/Child 連結 + git log 已覆蓋實際需求。

### Phase 7: 打包 (剩餘)

#### 7.2 內建更新器 (Plan B) ❌ 已廢棄 (2026-05-13)
> **廢棄原因**: Plan A（download + UpdateSection）已可用；Windows EXE 自覆蓋 + SmartScreen + updater.exe 自我更新三重悖論，個人工具不該背這成本。

### Phase 4: 進階多媒體 ❌ 已廢棄 (2026-05-13)
> **廢棄原因**: Whisper >1GB + SD 需 GPU 與 v2.3.0「拔除 AI / 轉型 Headless KMS」核心戰略直接矛盾。

### Phase 5: 外掛生態 ❌ 已廢棄 (2026-05-13)
> **廢棄原因**: 個人工具沒有外部開發者，外掛市場成立前提不存在。

### 前端技術債 🧊
> **來源**: `docs/20260315-claude4.6-綜合報告.md` — 決策日期 2026-03-16

#### 待實作 (📋 Backlog)
*(已清空)*

#### 已完成 (✅ 2026-04-04)
- [x] **[2.1-IconButton]** — 建立 `ui/IconButton.tsx`（4 variants × 3 sizes），替換 10 個檔案共 29 處 icon button；涵蓋 `DataManager` / `Header` / `NoteCard` / `EditorToolbar` / `Modal` / `Toast` / `PortConfigSection` / `EditorSidebar`
- [x] **[2.4] NoteEditor 拆分** — 拆為 5 個 custom hooks: `useNoteForm` / `usePasteHandler` / `useDragDrop` / `useNoteAttachments` / `useNoteHistory` / `usePromptExtraction`；位於 `hooks/editor/`
- [x] **[5.1] Toast 狀態管理** — 模組級變數遷移至 `stores/toastStore.ts` (Zustand)，對外介面不變
- [x] **[5.2] TypeScript `any` 清理** — `api.ts` 新增 `HardwareStatus` / `VersionInfo` / `BackupItem` / `ServerLogsResponse` / `RotateBackupsResponse` / `RestartServiceResponse` 完整型別
- [x] **[5.3] Light Theme glass border** — `index.css` `.light .glass` 補 `border-color: rgba(0,0,0,0.1)`

#### 刻意略過 (⏭️ Won't Do — 個人工具，無對應需求)
- **[1.2] 載入狀態 Skeleton** — 本地/區網延遲極低，體感無差
- **[1.3] Empty State 不一致** — 低頻場景，不影響使用
- **[1.5] 批次刪除進度回饋** — 筆記量少，批次操作罕見
- **[2.1] 共用 UI 元件庫不完整 (Dropdown/Badge/Select)** — 功能穩定後再統一，目前不影響使用
- **[2.2] Tailwind class 重複** — 不影響功能，維護時順手整理
- **[2.3] Heading 語意錯誤** — 非公開網站，無 SEO 需求
- **[3.1] 搜尋即時篩選 (Debounce)** — Enter 觸發已習慣，且語意搜尋已移除，需求消失
- **[3.4] 404 頁面** — 3 條路由，觸發機率趨近零
- **[3.5] PromptBuilder 響應式** — 僅桌面端使用
- **[3.6] 快捷鍵指南** — 個人使用已熟悉
- **[4.1] ARIA 標籤缺失** — 個人工具，無外部使用者，無 WCAG 合規需求
- **[4.2] 鍵盤導覽** — 同上
- **[4.3] 側邊欄響應式** — 固定桌面端使用，無 mobile/tablet 場景
- **[4.4] 圖片 alt 文字** — 非公開網站，無 a11y/SEO 需求

### 其他延遲項目 🧊
- **可選 API token / auth layer** — 未實作；目前 Prism API 適用 `localhost` / trusted LAN / VPN / SSH tunnel / 受認證保護的 reverse proxy。只有需要遠端公網存取時才重新評估，不列為目前 P0。
- **i18n 多語系** — 目前唯一語系繁中，待用戶群擴大再啟動
- **啟動時自動開瀏覽器** — PyInstaller 打包後行為不穩定，等 7.0 穩定後處理

### 🧪 Phase 6.4: 手動測試
> **狀態**: 遇到問題再修 (Issue-Driven)

---

## 📝 更新記錄 (Changelog)

| 版本 | 日期 | 內容 |
|------|------|------|
| **pi-deploy** | 2026-05-28 | 部署 Appearance controls follow-up 到 Raspberry Pi：同步 `frontend/dist` 與 `docs/TODO.md`，重啟 `prism.service` 後 live 驗證 `active`；`/api/test` status ok、`/api/server/version` v2.4.9 + V2 mode true、migration current/latest 15 且無 pending；首頁 HTML 指向 `assets/index-CKp_FqWr.css` / `assets/index-HYEMKfiU.js`，Pi dist CSS 內含 `data-accent`、`--prism-sidebar-width`、`--prism-corner-radius`。 |
| **frontend-ui** | 2026-05-28 | Appearance controls fidelity follow-up — `Linear` / `Editorial` / `Studio` 保留各自 dark/light 整體 palette，`主色` 改為 `data-accent` 強調色覆蓋，避免美學方向吃掉主題色彩；補入 prototype 的邊角圓潤度與側邊欄寬度 slider，使用 `localStorage` + CSS variables 套用到卡片、按鈕、輸入框與桌面 sidebar。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 87 passed；Playwright 驗證 Studio/light 背景維持 `#ebe6d8`、主色切夕陽橙後 `--color-primary=#f97316`、圓角 `18px`、sidebar `288px` 實際生效且無 console error。 |
| **frontend-ui** | 2026-05-28 | Appearance palette fidelity follow-up — 對齊 `Prism Redesign - standalone.html` 的 `Linear` / `Editorial` / `Studio` token，補齊 dark/light 六組整體 palette：Linear 冷灰藍、Editorial 暖紙色/棕金、Studio 暖米色/鼠尾草綠；初始化與切換同步 `data-mode`，避免只改 selected state 而未改整體色系。**收尾驗證**：`cd frontend && npm run build` passed；Playwright 驗證三種 aesthetic 點擊後 `--color-bg-base` / `--color-primary` 均不同，切到 light 後 Studio 套用 `#ebe6d8` / `#006c4e`。 |
| **pi-deploy** | 2026-05-28 | 部署 Phase 18.3 follow-up 到 Raspberry Pi：同步 `frontend/dist`、`utils/query_builder.py`、`docs/TODO.md`，重啟 `prism.service` 後 live 驗證 `active`；`/api/test` status ok、`/api/server/version` v2.4.9 + V2 mode true、`/api/system/migration-status` current/latest 15 且無 pending；dist assets 為 `index-5Z_Y_Vm1.js` / `index-BqlIPmnX.css`；建立臨時 Pi 筆記後 `/api/notes?q=todo.md&per_page=100` 命中並成功刪除臨時資料。 |
| **backend-go-shadow** | 2026-05-28 | Phase 18.4 Go CLI verification refresh — 本機 Go CLI 已可用，重新跑 `go version`、`cd go-shadow && go mod tidy && go test ./...`、`pytest tests/test_phase18_go_shadow_contract.py -v -s`，Go shadow Python diff harness 由 skipped 更新為 2 passed。 |
| **frontend-ui** | 2026-05-28 | Phase 18.3 follow-up — Settings 外觀新增 `Linear` / `Editorial` / `Studio` 本機美學方向，透過 `data-aesthetic` 調整字體層級、卡片節奏與圓角密度；搜尋 tokenizer 改為把標點視為分隔，修正 `todo.md` 類檔名式查詢查不到卡片內容。未新增 API/schema/server persistence。 |
| **frontend-ui** | 2026-05-28 | Phase 18.3 Prompt Builder / Settings re-layout — Prompt Builder 改為 desktop 雙欄、mobile 上下堆疊與固定動作列，輸出 contract 不變；Settings 改成外觀、資料、搜尋、部署、關於 tabs，只搬既有 section；部署 tab 與 ServerDashboard 補 `/api/server/*` local-only 邊界提示，不新增 API/schema。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` 83 passed；Playwright fallback 驗證 Prompt Builder desktop/mobile、preview 更新、Settings 五 tab、部署 local-only guard 與既有 server requests；console 僅有 Vite dev 訊息、React DevTools 提示與既有 React Router v7 future warnings。 |
| **backend-go-shadow** | 2026-05-28 | Phase 18.4 Go Read Shadow Backend — 新增 `go-shadow/` 獨立 Go module，實作 read-only `/api/test`、categories、tags、notes list、note detail；預設拒絕正式 `knowledge.db`，SQLite 啟用 `PRAGMA query_only = ON`，並 embed module-local React dist placeholder。新增 pytest diff harness，Go CLI 可用時會以同一 `temp_db` 啟動 Go server 對 Flask client 做 JSON diff；本機無 Go CLI 時明確 skip runtime diff。未新增任何 Go write route、file route、maintenance route 或 `/api/server/*`。**收尾驗證**：`pytest tests/test_phase18_go_shadow_contract.py -v` 1 passed / 1 skipped；`pytest tests/ -v` 84 passed / 1 skipped；skip 原因是目前環境 `go` 不在 PATH。 |
| **frontend-ui** | 2026-05-28 | Phase 18.2.3 / 18.2.4 Preview + Attachment/Image UX — 鎖定 EditablePreview regression：Preview 內可就地改文字、移除圖片引用並清空 matching cover；ImageManagementPanel 改用共用 imageReferences helper 同時偵測 Markdown 與 HTML `<img>` 引用，Attachment/Image panels 補穩定測試標記。未改 API/schema、未碰 Go file phase、未新增 editor dependency。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` 83 passed；Playwright fallback 驗證 Preview 編輯/移圖/cover clear、HTML image panel remove、AttachmentPanel/upload button；console 僅有 Vite dev 訊息、React DevTools 提示與既有 React Router v7 future warnings。 |
| **frontend-ui** | 2026-05-28 | Phase 18.2.1 / 18.2.2 Reading + Editor workflow — 新增卡片預設 reading modal，開啟後用既有 `GET /api/notes/<id>` 補 detail，快速動作可編輯、複製、置頂/封存；NoteEditor 改為更寬 full modal、桌面右側 metadata 欄、手機上下堆疊，`preview` 卡片模式直接進 EditablePreview。重用既有 hooks/components，不改 API/schema、不新增 WYSIWYG dependency。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` 83 passed；Playwright fallback 驗證 reading modal、`GET /api/notes/143`、reading→edit、preview initial mode、desktop/mobile editor；console 僅有既有 React Router v7 future warnings。 |
| **frontend-ui** | 2026-05-28 | Phase 18.1.4 Filter strip — 新增 Layout 層水平 chip bar，提供全部、封存、分類、標籤快速篩選；Home 上保留同一 filter toggle-off，非 Home 點分類/標籤/封存會導回 `/` 並套用篩選，分類查詢維持 `category_id` 而非分類名稱相容層。不改 API/schema/server persistence。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` 83 passed；Playwright fallback 驗證 desktop/mobile strip、route-aware flow、`/api/notes?...&category_id=1&sort=updated` request；console 僅有既有 React Router v7 future warnings。 |
| **frontend-ui** | 2026-05-27 | Phase 18.1.2 View modes — 新增 `grid` / `list` / `compact` 三種 Home 顯示模式，使用 Zustand + `localStorage` 保存本機 UI 偏好；Header view toggle 與 Settings 外觀入口共用同一狀態，compact list 使用 48px row 呈現，手機寬度收起 sort 以避免 Header 擁擠。不改 API/schema/server persistence。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` 83 passed；Chrome headless/CDP 驗證切換、reload persistence、Settings 外觀切換與 desktop/mobile screenshot。 |
| **frontend-ui** | 2026-05-28 | Phase 18.1.3 Command palette MVP — 新增全域 `Ctrl+K` / Header 入口，提供 Home / Prompt Builder / Settings / Archive 導覽、最近筆記開啟、新增筆記、明暗主題切換與外觀設定入口；所有寫入仍交給既有 editor / confirm 流程，不新增 API/schema/server persistence。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` 83 passed；Playwright fallback 驗證 palette 開啟、鍵盤搜尋、最近筆記/新增筆記/設定導覽、Header 按鈕與 mobile viewport；console 僅有既有 React Router v7 future warnings。 |
| **frontend-ui** | 2026-05-27 | Phase 18.1.1 Layout / Sidebar / Header refresh — 對齊 `Prism Redesign - standalone.html` 的 shell 密度與層級：Sidebar 改為 Prism brand + 導覽/分類/系統/標籤區塊，Header 改 topbar title/search/sort/view/new action，Home 加目前篩選 section header，底部加入本地狀態列，mobile 自動收斂為 64px icon rail。保留 React/Vite/Zustand/Tailwind，不改 API/schema/editor。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` 83 passed；Chrome headless desktop/mobile screenshot；CDP flow 驗證 Settings 點分類會回 Home 並套用篩選。 |
| **docs/tests** | 2026-05-27 | Phase 18.0 Contract Lock / Readiness — 新增 core API golden fixtures 與 `tests/test_phase18_api_golden.py`，固定 Python baseline；新增 `docs/contracts/phase18-readiness.md` 與 `docs/contracts/api-readonly-manifest.json`，文件化 endpoint side-effect map、UI workflow map 與 Go read shadow acceptance；同步 API_REFERENCE/INDEX。**收尾驗證**：`pytest tests/test_phase18_api_golden.py -v` 1 passed；`pytest tests/ -v` 83 passed。 |
| **docs-only** | 2026-05-27 | 整合新 UI 前端參考檔與 Go 模組逐步重構報告：新增 `docs/FRONTEND-REDESIGN-PLAN.md`，把 Phase 18 拆成 contract lock、frontend shell、reading/editor、settings/prompt builder、Go read shadow backend；明確暫緩 `collections` schema、AI、協作、Wails 與 Go file-write phases。 |
| **docs-only** | 2026-05-26 | 明確標示 Prism API 安全邊界：目前沒有內建 API Token / Bearer Token / 使用者認證機制，適用 `localhost`、trusted LAN、VPN、SSH tunnel 或受認證保護的 reverse proxy；不建議直接暴露到 public internet / 公網。新增 future item「可選 API token / auth layer」，未實作且非目前 P0。 |
| **docs-only** | 2026-05-26 | 同步 `CHANGELOG-since-v1.4.1.md` 的 V1.4.1 → V2 演進追溯到 v2.4.9：更新標題、時間範圍、摘要與對照表，補入 v2.4.8 Preview Editing UX 與 v2.4.9 Sidebar Filter Navigation 條目，對齊 README 最近版本敘述。 |
| **docs-only** | 2026-05-26 | 修正 README / DEPLOYMENT / docs 索引與演進摘要中 Portable、PyInstaller、零依賴、一鍵啟動的過度承諾：目前推薦使用 Source / Dev mode 或既有本機 / Raspberry Pi 部署；Portable / PyInstaller 標為實驗性、內部打包流程或後續發佈目標。 |
| **v2.4.9** | 2026-05-26 | Phase 17 Sidebar Filter Navigation — 非首頁點擊側邊欄分類/標籤會導回首頁並套用該篩選；首頁維持再次點擊同一篩選可取消；`GET /api/notes` 前端查詢改送 `category_id`，降低分類改名後依賴 `type` 名稱相容層的風險。**收尾驗證**：`cd frontend && npx tsc --noEmit` / `cd frontend && npm run build` / `pytest tests/ -v` / Browser flow |
| **v2.4.8** | 2026-05-26 | Phase 16 Preview Editing UX — Preview 模式改為可互動：文字區塊可在預覽中切入小型 Markdown textarea 直接修改，獨立 Markdown / HTML 圖片可在預覽中移除引用，封面圖被移除時同步清空 `cover_image`；側欄 `ImageManagementPanel` 與 Preview 共用圖片引用移除 helper。**收尾驗證**：`cd frontend && npx tsc --noEmit` / `cd frontend && npm run build` / `pytest tests/ -v` 全通過；Browser flow 實測 Preview 內可改文字、刪圖片引用且 console 無 warn/error；PRISM_VERSION → 2.4.8 |
| **v2.4.7** | 2026-05-13 | Phase 15 維護模式雜項 — **Markdown 匯出**：`GET /api/export/markdown` 回傳 zip（每筆記一個 `.md` + YAML frontmatter + `_manifest.json`），Settings 加「下載 .zip」按鈕；補 4 個 pytest（zip 結構 / frontmatter 欄位 / manifest 計數 / 空標題 edge case）；API_REFERENCE.md 補端點說明。**自動備份**：Pi 加 `prism-backup.timer`（每週日 03:00）+ `prism-backup.service` 觸發既有 `/api/server/backup/download` + `/rotate?keep=8`；DEPLOY-PI.md 補章節。**Dead folder 清理**：`git rm -r 資料庫備份/`（V1 殘留中文資料夾，實際備份都在 `backups/`）。**收尾**：80 passed (+4) / tsc 零錯誤 / build 成功 / PRISM_VERSION → 2.4.7 |
| **v2.4.6** | 2026-05-13 | Phase 14 深度審計修補 (v2.4.5 後文件 / 測試 / 殭屍清理) — **文件對齊**：修補 5 條 404 cco 報告連結（README / INDEX / CONTRIBUTING）；修正 INDEX 三處維護狀態欄位；TODO 頭部移除「Local AI」/ 日期更新 / Phase 10 已完成標記；Prism.md 加歷史 banner + §1.2 刪除線；CONTRIBUTING 補 v1–v15 / 全綠期望 / 文件同步 checklist；tests/README 改 `--collect-only` 自動導覽。**安全回歸測試**：新增 `tests/test_security_guards.py`（`test_ssrf_blocks_loopback` / `test_ssrf_blocks_private_range` / `test_server_api_localhost_only` / `test_csrf_production_blocks_anonymous`）。**P2 殭屍清理**：`check_consistency` docstring 移除 `type_category_mismatch`；刪除 `scripts/check_deps.py`；刪除 `tests/test_offline_mode.py`。**收尾驗證**：76 passed / tsc 零錯誤 / Vite build 成功 / PRISM_VERSION → 2.4.6。**補做（2026-05-13 第二輪）**：`AGENTS.md` ↔ `CLAUDE.md` 還原為雙份完整鏡像 + sync banner + Release Checklist diff 比對行（修正初版誤改為 stub）；`git mv demo docs/過期/demo`；README「專案結構」補 `garbage-can/` 與 `migrations v15` / `tests` 自動導覽 |
| **v2.4.5** | 2026-05-05 | Phase 13 搜尋範圍擴充 — `GET /api/notes?q=...` 覆蓋標題、內文、備註、附件標題/路徑/文字內容、標籤；補 pytest 回歸測試並同步 API / 架構 / schema 文件 |
| **v2.4.4** | 2026-04-24 | Phase 12 前後端 API 契約修補 — 補回 check-update / migration-status；修正分類刪除 target_category_id；補齊 notes archived/include_archived/pinned_only/category_id 查詢；create/update 支援 pin/archive 狀態 |
| **v2.4.3** | 2026-04-24 | Phase 11 外部 Agent API 對接整理 — 修正單筆讀取/duplicate/import-export 的 `Notes.type` schema 漂移，重寫 API 對接文件供外部 Agent 使用 |
| **v2.4.2** | 2026-04-12 | Phase 10 體檢報告修補 — P0: 殭屍 `n.type` query 清除 (system/export)；P1: SSRF 防護 + real migration fixture + `_HAS_PARENT_ID` 刪除 + 手動 cascade 清除；P2: 版本同步 + api.ts 死碼 + file handle 修復 + server localhost-only + prod CSRF 收緊；補: schema regression 測試 + release checklist |
| **v2.4.1** | 2026-04-04 | [2.1-IconButton] — 建立 `ui/IconButton.tsx`，統一 10 個檔案 29 處 icon button，tsc 零錯誤 |
| **v2.4.0** | 2026-04-04 | 前端技術債清償 — NoteEditor 拆分 hooks、Toast → Zustand、api.ts 完整型別、glass border 修正 |
| **v2.3.0** | 2026-04-04 | AI 全面拔除 — 移除 NVIDIA NIM / Ollama / Embeddings / Vector Store / AI Tagging / Semantic Search，Migration v14，轉型 Headless KMS |
| **v2.2.0** | 2026-03-15 | Phase 9 UX 強化 — 全域錯誤攔截器 + ConfirmDialog + 標題 autoFocus + 標籤自動補全 |
| **v2.1.2** | 2026-03-15 | Phase 8.2 Server Dashboard — 硬體監控、日誌檢視、備份管理、服務重啟、版本資訊 |
| **v2.1.1** | 2026-03-15 | Phase 8.1 Raspberry Pi — avahi mDNS + Caddy 反向代理 + systemd 自啟 + 一鍵腳本 |
| **v2.1.0** | 2026-03-15 | Phase 7.1/7.3 — check-update API + UpdateSection + init_db 移入 create_app |
| **v1.5.1** | 2026-02-27 | Unsaved Changes Guard — 未儲存變更偵測與關閉攔截 |
| **v1.5.0** | 2026-02-27 | 圖片管理增強 + 端口自選 — 批次操作、封面設定、WinError 10013 處理 |
| **v0.5** | 2024-12-31 | Phase 0.5 — 拆分 NoteEditor/SettingsPage、Schema 淨化 |
| **v0.1** | 2024-12-30 | Phase 0 — 架構淨化 (Kill Notes.type、AI_Tasks、QueryBuilder、V1 移植) |
