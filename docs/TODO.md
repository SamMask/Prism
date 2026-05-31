# Prism - Modernization & Intelligence Roadmap (TODO)

**狀態**: 🟢 穩定運行 (Stable)
**核心目標**: Headless KMS API + 純關鍵字 FTS 搜尋
**文件參照**: `docs/Prism.md` (歷史背景), `docs/SCHEMA.md` (資料庫規格), `docs/FRONTEND-REDESIGN-PLAN.md` (UI/Go 重構規劃), `Prism_Go_模組逐步重構計劃報告.md` (Go shadow backend), `docs/development-history/` (完成階段與完整 Changelog 歸檔), `garbage-can/1230-審核報告.md` (Linus Audit)
**最後更新**: 2026-06-01

---

## 文件瘦身與歷史保存

- Active roadmap 留在本檔，優先服務下一步開發與驗證。
- 已完成 phase 與歷史決議保存於 `docs/development-history/todo-completed-phases.md`。
- 完整 Changelog 長表保存於 `docs/development-history/todo-changelog.md`；本檔只保留近期摘要。

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
- [x] **18.3.4** Appearance baseline + background schemes — 外觀 tab 移除 `Linear` / `Editorial` / `Studio` 美學方向 UI，前台固定採 Editorial 閱讀基準且中文摘要不使用 italic；保留 Home `grid` / `list` / `compact` ViewMode；新增 `prism.backgroundScheme` + `data-bg` 背景色調，將 semantic background palette 與 `data-accent` 強調色拆開，不新增 server API 或 schema。
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

## 📝 近期更新摘要

> 完整版本歷程見 `docs/development-history/todo-changelog.md`。

| 版本 | 日期 | 內容 |
|------|------|------|
| **frontend-ui** | 2026-05-29 | Appearance settings 簡化 — 移除 `Linear` / `Editorial` / `Studio` 美學方向 UI，舊 `prism.aestheticMode` 僅讀取相容並正規化為 Editorial baseline；新增 `背景色調`（`prism.backgroundScheme` + `data-bg`）五組 semantic background palette，每組支援深色/淺色；`data-accent` 僅控制 primary/accent/focus/tag/active 類狀態，中文摘要維持 normal font-style。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build` passed；Playwright fallback 驗證 Settings 不再出現美學方向/Linear/Editorial/Studio，切換背景色調與強調色後背景 tokens 不被 accent 覆蓋，mobile 無水平溢出。 |
| **pi-deploy** | 2026-05-28 | 部署 Appearance controls follow-up 到 Raspberry Pi：同步 `frontend/dist` 與 `docs/TODO.md`，重啟 `prism.service` 後 live 驗證 `active`；`/api/test` status ok、`/api/server/version` v2.4.9 + V2 mode true、migration current/latest 15 且無 pending；首頁 HTML 指向 `assets/index-CKp_FqWr.css` / `assets/index-HYEMKfiU.js`，Pi dist CSS 內含 `data-accent`、`--prism-sidebar-width`、`--prism-corner-radius`。 |
| **frontend-ui** | 2026-05-28 | Appearance controls fidelity follow-up — `Linear` / `Editorial` / `Studio` 保留各自 dark/light 整體 palette，`主色` 改為 `data-accent` 強調色覆蓋，避免美學方向吃掉主題色彩；補入 prototype 的邊角圓潤度與側邊欄寬度 slider，使用 `localStorage` + CSS variables 套用到卡片、按鈕、輸入框與桌面 sidebar。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 87 passed；Playwright 驗證 Studio/light 背景維持 `#ebe6d8`、主色切夕陽橙後 `--color-primary=#f97316`、圓角 `18px`、sidebar `288px` 實際生效且無 console error。 |
| **frontend-ui** | 2026-05-28 | Appearance palette fidelity follow-up — 對齊 `Prism Redesign - standalone.html` 的 `Linear` / `Editorial` / `Studio` token，補齊 dark/light 六組整體 palette：Linear 冷灰藍、Editorial 暖紙色/棕金、Studio 暖米色/鼠尾草綠；初始化與切換同步 `data-mode`，避免只改 selected state 而未改整體色系。**收尾驗證**：`cd frontend && npm run build` passed；Playwright 驗證三種 aesthetic 點擊後 `--color-bg-base` / `--color-primary` 均不同，切到 light 後 Studio 套用 `#ebe6d8` / `#006c4e`。 |
| **pi-deploy** | 2026-05-28 | 部署 Phase 18.3 follow-up 到 Raspberry Pi：同步 `frontend/dist`、`utils/query_builder.py`、`docs/TODO.md`，重啟 `prism.service` 後 live 驗證 `active`；`/api/test` status ok、`/api/server/version` v2.4.9 + V2 mode true、`/api/system/migration-status` current/latest 15 且無 pending；dist assets 為 `index-5Z_Y_Vm1.js` / `index-BqlIPmnX.css`；建立臨時 Pi 筆記後 `/api/notes?q=todo.md&per_page=100` 命中並成功刪除臨時資料。 |
