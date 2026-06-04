# Prism - Modernization & Intelligence Roadmap (TODO)

**狀態**: 🟢 穩定運行 (Stable)
**核心目標**: Headless KMS API + 純關鍵字 FTS 搜尋
**文件參照**: `docs/Prism.md` (歷史背景), `docs/SCHEMA.md` (資料庫規格), `docs/FRONTEND-REDESIGN-PLAN.md` (UI/Go 重構規劃), `Prism_Go_模組逐步重構計劃報告.md` (Go shadow backend), `docs/development-history/` (完成階段與完整 Changelog 歸檔), `garbage-can/1230-審核報告.md` (Linus Audit)
**最後更新**: 2026-06-04

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

## 🚀 Phase 19: Go Runtime / Packaging Promotion — ✅ Closed (19.15 Read-only Promotion Stabilized)

> **來源**: `Prism_Go_模組逐步重構計劃報告.md`、`go-shadow/`、`docs/contracts/phase19-go-runtime-packaging.md`
> **目標**: 不是新增功能或抽象模組改寫，而是驗證 Go single binary runtime / packaging promotion：Windows 本機 exe、Pi Linux ARM64 binary、embedded React dist、external data dir、explicit DB path、schema check、health check。
> **原則**: Python backend 保留為 parity baseline 與 rollback path；Phase 19.0 只允許 GET/read-only API，不實作 POST/PUT/DELETE，不修改正式 DB，不碰 attachments/export/cleanup/server maintenance。

### 🔒 19.0 Runtime / Packaging Proof

- [x] **19.0.1** Python runtime inventory — 盤點 `app.py` 啟動、`frontend/dist`、`knowledge.db`、`.port_config`、`static/uploads`、Pi `prism.service` 與 exclude 規則；見 `docs/contracts/phase19-go-runtime-packaging.md`。
- [x] **19.0.2** Go runtime layout — `go-shadow` 支援 single binary proof、embedded frontend dist、`--data-dir` external data dir、mandatory `--db`、schema version >= 16 check、`GET /healthz`。
- [x] **19.0.3** SQLite driver spike — 保留 `modernc.org/sqlite` pure Go driver；新增 Go test 驗證現有 schema 代表子集、FTS5、`PRAGMA query_only` 與 schema check。CGO `mattn/go-sqlite3` 因需要 `CGO_ENABLED=1` + GCC / cross compiler，不作 Phase 19.0 首選。
- [x] **19.0.4** Build path proof — 新增 `scripts/build_go_runtime.ps1`，建置 React dist、同步 Go embed dist、跑 `go test ./...`，輸出 Windows exe 與 Linux ARM64 artifact。
- [x] **19.0.5** Regression gates — Python vs Go JSON response diff 仍覆蓋所有 Go read API；新增 Windows local binary smoke test 與 Pi Linux ARM64 cross-build artifact test。
- [x] **19.0.6** Schema version reconciliation — repo-local Python schema SSOT 為 migration v16 (`normalize_editor_layout`)，local `knowledge.db` 也為 v16；Pi live `/api/system/migration-status` 仍回 current/latest 15，表示 Pi 尚未部署 v16。Phase 19.0 不部署或替換 live `prism.service`，因此 2026-05-28 Pi deploy 摘要中的 v15 是當時 live 狀態，不代表 repo 最新 schema。
- [x] **19.0.7** Pi Python v16 deploy readiness — 建立 Pi timestamped DB backup `/home/mask070924/prism/backups/prism_pre_v16_20260601_025914.db`；部署最新 Python code / migrations / frontend dist 到既有 Pi runtime；重啟既有 `prism.service` 後由 Python migration flow 將 Pi DB 升到 v16。Live 驗證：`/api/system/migration-status` current/latest 16 且 pending `[]`、`/api/test` 200、首頁 200、notes list 200、note detail 200。未啟動 Go runtime、未替換 `prism.service`。

### 🐤 19.1 Go Real Data Read-only Canary Run

- [x] **19.1.1** V16 DB copy — 從 Pi v16 production DB 建立 timestamped copy `/home/mask070924/prism/backups/prism_go_canary_v16_20260601_030059.db`，再拉到本機 ignored path `build/go-canary/prism_go_canary_v16.db`；Go 不讀正式 production DB。
- [x] **19.1.2** Go read-only runtime canary — 使用 Go runtime 只讀 canary DB copy，`/healthz` 回 schema_version 16、expected_schema_version 16、sqlite_query_only true；`/api/test` 與 notes list 可讀真實資料 copy。
- [x] **19.1.3** Pi sidecar real-data smoke — 部署 `prism-go-runtime-linux-arm64` 到 `/home/mask070924/prism-go-canary/`，讀 v16 DB copy，未替換 Python `prism.service`。原要求 `127.0.0.1:5001` 已被 unrelated `fava` process 佔用，未停止該 process；canary 改綁 `127.0.0.1:5002` 完成 smoke：`/healthz`、`/api/test`、`/api/categories`、`/api/tags`、`/api/notes`、`/api/notes/114`、`/api/notes/999999`。
- [x] **19.1.4** Diff query expansion — 擴充 Python vs Go JSON response diff query set，新增 `q=todo.md`、中文搜尋、空結果、pagination edge、per_page edge、category+tag+sort 組合、note detail 404，以及既有 include_archived、pinned_only、sort、type、tag OR/AND cases。仍未實作 POST/PUT/DELETE，未做 Go migration，未碰 attachments/export/cleanup/server maintenance。
- [x] **19.1.5** Embedded frontend read-only smoke — Windows Go exe serve embedded React dist，Playwright 驗證首頁、搜尋、分類、標籤、notes list、note detail reading flow；request capture 僅有 GET API calls。
- [x] **19.1.6** Runtime metrics and log check — Windows：Python RSS 46,660 KB、Go RSS 11,104 KB API smoke / 19,748 KB frontend smoke、Python startup 538 ms、Go startup 513 ms。Pi：Python RSS 47,104 KB、Go RSS 13,488 KB、Python startup 422 ms、Go startup 278 ms。Pi canary log 只有 GET startup/request logs；Go manual POST `/api/test` 回 method not allowed，未觀察到 write attempt。

### 🧭 19.2 Go Read-only Promotion Gate

- [x] **19.2.1** Promotion decision gate — 新增 `docs/contracts/phase19-go-readonly-promotion-gate.json`，明確決議 Go 只升級為 controlled read-only candidate，不替換 Python `prism.service`、不讓前端預設改打 Go、不跑 Go migration。
- [x] **19.2.2** Read-only surface lock — 新增 `tests/test_phase19_go_readonly_promotion_gate.py`，測試 gate 與 `go-shadow/main.go` 註冊 surface 一致，只允許 `GET /healthz`、`GET /api/test`、categories、tags、notes list、note detail，並阻擋 POST/PUT/DELETE/PATCH 進入 Go runtime。
- [x] **19.2.3** Next-step planning — Phase 19.3 只規劃為 controlled read routing proof：local-only 或 sidecar-only，必須有 explicit reversible switch；仍不得包含 write routes、file routes、server maintenance、default frontend cutover 或 Python backend removal。

### 🔀 19.3 Controlled Read Routing Proof

- [x] **19.3.1** Routing switch contract — 新增 `docs/contracts/phase19-go-read-routing-proof.json`，定義 `PRISM_GO_READ_ROUTING=1` + `PRISM_GO_READ_BASE_URL` 為 explicit reversible switch；預設關閉，base URL 僅允許 `localhost` / `127.0.0.1` / `::1` 且必須帶 port。
- [x] **19.3.2** Minimal routing spike — Flask `before_request` 只在 opt-in 時代理已驗證 GET read surface：`/api/test`、categories、tags、notes list、note detail；POST/PUT/DELETE/PATCH、attachments/export/cleanup/server maintenance、migration 仍由 Python 擁有。
- [x] **19.3.3** Fallback and evidence gate — Go sidecar unreachable 或 base URL 無效時 fail-open 回 Python；proxied response 會加 `X-Prism-Go-Read-Routing: hit`，Python-owned `GET /api/system/go-read-routing` 回報 switch、base URL validity、owner/fallback 與 blocked methods。
- [x] **19.3.4** Verification gate — 新增 `tests/test_phase19_go_read_routing.py`，覆蓋預設關閉、白名單 GET proxy、非白名單不 proxy、非 localhost base URL 拒絕、sidecar unavailable fallback、19.3 contract 與 19.4 邊界。

### 🧾 19.4 Cutover Readiness Audit

- [x] **19.4.1** Read-routing stability audit — 新增 `docs/contracts/phase19-go-cutover-readiness-audit.json`，彙整 19.0 runtime packaging、19.1 real-data canary、19.2 promotion gate、19.3 read routing proof 的 evidence。
- [x] **19.4.2** Gap list before any cutover — 明確列出 cutover 前 blocking gaps：沒有 production service-level plan、沒有 long-running soak、沒有 Caddy/systemd deployment contract、沒有 rollback drill；Go 仍不擁有 writes、files、maintenance、migrations 或 production DB writes。
- [x] **19.4.3** Decision checkpoint — 19.4 結論只允許另開「19.5 Read-only Service-level Cutover Plan」；19.4 本身不授權替換 `prism.service`、改 frontend default、寫 production DB、跑 Go migration、移除 Python 或推 Go file/write routes。
- [x] **19.4.4** Audit regression lock — 新增 `tests/test_phase19_go_cutover_readiness_audit.py`，固定 19.4 是 audit-only、`runtime_change=false`、下一步需要 user approval，並保留所有 cutover blocking gaps。

### 📋 19.5 Read-only Service-level Cutover Plan

- [x] **19.5.1** Service-level plan draft — 新增 `docs/contracts/phase19-go-readonly-service-cutover-plan.json`，規劃 read-only sidecar / soak test 的 topology：Python `prism.service` 仍是 primary runtime / write-file-maintenance owner / rollback target，Go sidecar `prism-go-readonly.service` 只綁 `127.0.0.1:5002` 且只處理已驗證 GET read surface。
- [x] **19.5.2** Runtime safety checklist — 計畫要求 production DB timestamped backup、Python health preflight、Go `/healthz` schema/query_only evidence、localhost-only bind、GET-only route check、trusted LAN/VPN/SSH tunnel/protected reverse proxy exposure boundary；明確禁止 direct public internet exposure。
- [x] **19.5.3** Rollback / monitoring / criteria — 計畫定義 stage 0 no-routing sidecar smoke、stage 1 Python opt-in read routing soak、stage 2 future reverse-proxy option；每階段有 rollback，並定義 `X-Prism-Go-Read-Routing: hit`、`/api/system/go-read-routing`、systemctl/logs、success/failure criteria。
- [x] **19.5.4** Approval checkpoint lock — 新增 `tests/test_phase19_go_readonly_service_cutover_plan.py`，固定 19.5 是 plan-only、`live_execution_authorized=false`、19.6 `blocked_until_explicit_user_approval`；任何 live Pi service change、Caddy route change、frontend default API target change 或 production DB access 前都必須另行明確授權。

### ✅ 19.6 Approved Read-only Soak Execution

- [x] **19.6.1** Approval gate — 使用者明確授權後，依 19.5 plan 執行 Pi live stage 0 / stage 1；新增 `docs/contracts/phase19-go-readonly-soak-execution.json` 記錄 authorized scope 與 live evidence。
- [x] **19.6.2** Live evidence capture — Pi preflight：`prism.service` active、`/api/test` 200、migration current/latest 16、pending `[]`、notes/categories/tags counts 196/6/122；建立並驗證 backup `/home/mask070924/prism/backups/prism_pre_go_readonly_soak_20260604_032653.db`。Go sidecar `prism-go-readonly.service` 綁 `127.0.0.1:5002`，`/healthz` 回 schema_version 16、`sqlite_query_only=true`；stage 1 白名單 GET 皆有 `X-Prism-Go-Read-Routing: hit`，`/api/system/migration-status` 與 `POST /api/test` 未 proxy 到 Go。
- [x] **19.6.3** Rollback drill — 移除 `/etc/systemd/system/prism.service.d/go-read-routing.conf`、重啟 `prism.service`，`/api/system/go-read-routing` 回 `enabled=false`，代表性 GET 不含 `X-Prism-Go-Read-Routing`；停止 `prism-go-readonly.service`，確認 5002 無 listener。未改 Caddy、未改 frontend default、未新增 Go writes/files/migrations。
- [x] **19.6.4** Regression lock — 新增 `tests/test_phase19_go_readonly_soak_execution.py`，固定 19.6 live evidence、rollback final state、Go localhost/query_only/read-only 邊界，以及 19.7 必須另行授權。

### ✅ 19.7 Post-soak Decision Gate

- [x] **19.7.1** Decision checkpoint — 使用者明確授權後，選擇執行 bounded extended Python-switch read-only soak；新增 `docs/contracts/phase19-go-readonly-long-soak-decision.json` 記錄 decision、live evidence 與 19.8 gate。
- [x] **19.7.2** Extended soak execution — 從 Python-only 起點開始：routing off、Go sidecar inactive、5002 無 listener；建立 fresh backup `/home/mask070924/prism/backups/prism_pre_go_readonly_long_soak_20260604_034124.db` 並驗 schema v16 / notes 196。啟用 Go sidecar 後，Python opt-in routing 跑 10 輪、每輪間隔 60 秒；每輪驗 `/api/test`、notes list、note detail 皆有 `X-Prism-Go-Read-Routing: hit`，migration 與 `POST /api/test` 無 Go header，兩個 service 均 active。
- [x] **19.7.3** Rollback / boundary lock — 本輪完成後移除 drop-in、重啟 `prism.service`、停止 sidecar，最終 routing `enabled=false`、`/api/test` 無 Go header、5002 無 listener、migration current/latest 16 pending `[]`。Caddy、frontend default、Go writes/files/migrations、Python removal 均未授權也未執行。
- [x] **19.7.4** Regression lock — 新增 `tests/test_phase19_go_readonly_long_soak_decision.py`，固定 10-sample soak evidence、fresh backup、query_only sidecar、rollback final state、19.8 必須另行授權。

### ✅ 19.8 Reverse-proxy / Service Cutover Planning Gate

- [x] **19.8.1** Plan-only cutover design — 新增 `docs/contracts/phase19-go-reverse-proxy-service-cutover-plan.json`，定義 Caddy/service read-only routing plan：只有已驗證 GET read surface 可規劃到 Go sidecar，Python `prism.service` 仍是 write/file/maintenance/migration owner 與 rollback target；19.8 不改 live Caddy、不 reload Caddy、不改 frontend default。
- [x] **19.8.2** Exposure / auth boundary — plan 固定 localhost/trusted LAN/VPN/SSH tunnel/protected reverse proxy 邊界；Prism 仍沒有 built-in API token / Bearer token / user auth，禁止 direct public internet exposure、unprotected Caddy public endpoint、public Go sidecar bind。
- [x] **19.8.3** Rollback / failure criteria — plan 定義 19.9 前置 gate：explicit approval、Caddy active + `caddy validate`、Caddy config backup、fresh DB backup、Go sidecar localhost/query_only/schema health、header/status/log monitoring、rollback commands；Go writes/files/migrations、frontend default、Python removal 仍不在 scope。
- [x] **19.8.4** Regression lock — 新增 `tests/test_phase19_go_reverse_proxy_service_cutover_plan.py`，固定 19.8 plan-only、route policy、exposure/auth boundary、rollback/failure criteria，以及 19.9 必須另行授權。

### ✅ 19.9 Approved Caddy Read-only Routing Drill

- [x] **19.9.1** Live approval gate — 使用者明確授權後，依 19.8 plan 執行短暫 Caddy-level read-only routing drill；新增 `docs/contracts/phase19-go-caddy-readonly-routing-drill.json` 記錄 live evidence。
- [x] **19.9.2** Fresh preflight and config backup — 驗證 Python/Caddy active、routing off、Caddy validate；建立 DB backup `/home/mask070924/prism/backups/prism_pre_caddy_readonly_drill_20260604_040342.db` 與 Caddy backup `/etc/caddy/Caddyfile.prism-pre-go-readonly-drill-20260604_040342.bak`；Go sidecar `127.0.0.1:5002` `/healthz` 回 schema v16 + `sqlite_query_only=true`。
- [x] **19.9.3** Short reversible Caddy drill — Caddy route block validate + reload 後，3 輪、每輪 30 秒驗白名單 GET (`/api/test`、categories、tags、notes list/detail、note 404) 都有 `X-Prism-Go-Read-Routing: hit`；`/api/system/migration-status`、`/api/system/go-read-routing`、`POST /api/test` 均無 Go header；Go journal 自 drill start 起無 POST/PUT/DELETE/PATCH。
- [x] **19.9.4** Rollback and regression lock — 使用 Caddy backup 還原、validate、reload，停止 Go sidecar；最終 `prism.service` / Caddy active、routing `enabled=false`、`/api/test` 無 Go header、migration v16 pending `[]`、sidecar inactive、5002 無 listener。新增 `tests/test_phase19_go_caddy_readonly_routing_drill.py` 固定 evidence 與 19.10 gate。

### ✅ 19.10 Post-Caddy Drill Decision Gate

- [x] **19.10.1** Decision checkpoint — 使用者明確授權後，選擇執行 bounded extended Caddy-level read-only soak；新增 `docs/contracts/phase19-go-caddy-extended-readonly-soak.json` 記錄 live evidence。
- [x] **19.10.2** Extended Caddy soak execution — 從 Python-only 起點建立 DB backup `/home/mask070924/prism/backups/prism_pre_caddy_extended_soak_20260604_173527.db` 與 Caddy backup `/etc/caddy/Caddyfile.prism-pre-go-caddy-extended-soak-20260604_173527.bak`；Go sidecar `127.0.0.1:5002` `/healthz` 回 schema v16 + `sqlite_query_only=true`。Caddy route validate + reload 後跑 10 輪、每輪 60 秒，白名單 GET 皆有 `X-Prism-Go-Read-Routing: hit`，system/routing/POST 仍無 Go header。
- [x] **19.10.3** Rollback and boundary lock — 使用本輪 Caddy backup 還原、validate、reload，停止 Go sidecar；最終 `prism.service` / Caddy active、routing `enabled=false`、`/api/test` 無 Go header、migration v16 pending `[]`、sidecar inactive、5002 無 listener。Permanent Caddy route、frontend default API target、Go writes/files/migrations、Python backend removal、direct public exposure 均未授權也未保留。
- [x] **19.10.4** Regression lock — 新增 `tests/test_phase19_go_caddy_extended_readonly_soak.py`，固定 10-sample Caddy-level soak evidence、fresh backups、rollback final state、19.11 必須另行授權。

### ✅ 19.11 Caddy Cutover Candidate Decision Gate

- [x] **19.11.1** Candidate decision — 使用者明確授權後，決議保留 Go 為 verified Caddy-routable read-only sidecar candidate，並撰寫 proposal-only permanent-cutover contract；新增 `docs/contracts/phase19-go-caddy-cutover-candidate-decision.json`。
- [x] **19.11.2** Permanent-cutover proposal — Proposal 固定 operation window、external auth/exposure boundary、fresh DB/Caddy backups、Caddy validate、monitoring、rollback owner、rollback triggers、revert plan；只允許白名單 GET read surface 規劃到 Go，Python 仍擁有 writes/files/system/server/import/export/cleanup/static/frontend/migrations。
- [x] **19.11.3** Production ownership stays Python — 19.11 不授權 live Caddy config change、Caddy reload、permanent Caddy route、frontend default API target、Go writes/files/migrations、Python removal、direct public exposure。
- [x] **19.11.4** Regression lock — 新增 `tests/test_phase19_go_caddy_cutover_candidate_decision.py`，固定 proposal-only、candidate status、route boundary、fresh preflight/monitoring/rollback requirements、exposure/auth boundary，以及 19.12 必須另行授權。

### ✅ 19.12 Permanent Read-only Caddy Cutover

- [x] **19.12.1** Live permanent-cutover approval — 使用者明確授權後，依 19.11 proposal 在 Pi 執行 permanent read-only Caddy cutover；新增 `docs/contracts/phase19-go-permanent-caddy-readonly-cutover.json`。
- [x] **19.12.2** Fresh preflight and backups — 從 Python-only Caddy route 起點驗證 `prism.service` / Caddy active、routing disabled、Caddy validate；建立 DB backup `/home/mask070924/prism/backups/prism_pre_permanent_caddy_readonly_cutover_20260604_180157.db`（schema v16、notes 196）與 Caddy backup `/etc/caddy/Caddyfile.prism-pre-permanent-go-readonly-cutover-20260604_180157.bak`。
- [x] **19.12.3** Permanent Caddy read-only route — 啟用並保留 `prism-go-readonly.service`（active + enabled，`127.0.0.1:5002`，`/healthz` schema v16 + `sqlite_query_only=true`），Caddy validate + reload 後只把白名單 GET read surface 導向 Go 並加 `X-Prism-Go-Read-Routing: hit`。
- [x] **19.12.4** Boundary and regression lock — 3 輪 live sample 驗證 `/api/test`、categories、tags、notes list/detail/404 都有 Go header；`/api/system/migration-status`、`/api/system/go-read-routing`、`POST /api/test` 無 Go header；migration current/latest v16 pending `[]`，Go journal 無 POST/PUT/DELETE/PATCH。新增 `tests/test_phase19_go_permanent_caddy_readonly_cutover.py`。
- [x] **19.12.5** Still not a Go full backend replacement — 19.12 未改 frontend default target、未授權 Go writes/files/migrations、未移除 Python、未擴大 public exposure；Python 仍是非白名單 route owner 與 rollback target。

### ✅ 19.13 Post-permanent Read-only Cutover Stabilization Gate

- [x] **19.13.1** Stabilization review approval — 使用者明確授權後，執行 post-permanent route monitoring / keep-or-rollback decision；新增 `docs/contracts/phase19-go-post-permanent-caddy-stabilization.json`。
- [x] **19.13.2** Fresh live monitoring evidence — 5 輪、每輪間隔 10 秒驗證 `prism.service` / Caddy / `prism-go-readonly.service` active、sidecar enabled 且只綁 `127.0.0.1:5002`、`/healthz` schema v16 + `sqlite_query_only=true`、Caddy validate 通過。
- [x] **19.13.3** Route and ownership stability — 白名單 GET (`/api/test`、categories、tags、notes list/detail/404) 每輪皆有 `X-Prism-Go-Read-Routing: hit`；`/api/system/migration-status`、`/api/system/go-read-routing`、`/api/server/version`、`POST /api/test` 無 Go header；migration current/latest v16 pending `[]`，Go journal 無 write methods 或 error。
- [x] **19.13.4** Keep decision and regression lock — 19.13 決議保留 permanent read-only Caddy route，未改 Caddy、未 reload、未擴 route、未改 frontend default、未加入 Go writes/files/migrations、未移除 Python。新增 `tests/test_phase19_go_post_permanent_caddy_stabilization.py`。

### ✅ 19.14 Permanent Route Matcher and Runbook Hardening Gate

- [x] **19.14.1** Matcher/runbook review approval — 使用者明確授權後，檢查 retained Caddy matcher 與 rollback/runbook 文檔；新增 `docs/contracts/phase19-go-caddy-matcher-runbook-hardening.json`。
- [x] **19.14.2** Matcher narrowing with fresh checks — 發現 19.12 retained `/api/notes/*` wildcard 會涵蓋未來未審核 GET path；先以暫存 Caddyfile 驗證新 matcher，再建立 backup `/etc/caddy/Caddyfile.prism-pre-matcher-hardening-20260604_182035.bak`，將 route 縮窄為 exact `/api/notes` + numeric `^/api/notes/[0-9]+$`，Caddy validate/reload 後仍 active。
- [x] **19.14.3** Live boundary verification — 3 輪 sample 驗證白名單 GET 仍有 `X-Prism-Go-Read-Routing: hit`；`/api/notes/not-a-number`、`/api/notes/114/extra`、system/routing/server/version/POST 均無 Go header；migration v16 pending `[]`，Go journal 無 write methods/error。
- [x] **19.14.4** Still not a Go full backend replacement — 未擴 route、未改 frontend default、未加入 Go writes/files/migrations、未移除 Python、未擴大 public exposure。新增 `tests/test_phase19_go_caddy_matcher_runbook_hardening.py`。

### ✅ 19.15 Post-matcher Hardening Stabilization Gate

- [x] **19.15.1** Post-hardening monitoring approval — 使用者明確授權後，監測 narrowed matcher 並決定 keep / rollback / close Phase 19 read-only promotion；新增 `docs/contracts/phase19-go-post-matcher-hardening-stabilization.json`。
- [x] **19.15.2** Fresh live monitoring evidence — 5 輪、每輪 10 秒驗證 exact read list 與 numeric note detail 仍走 Go；非 numeric/nested `/api/notes/...`、system/routing/server/version/POST 仍 Python-owned 且無 Go header；Caddy validate 通過，migration v16 pending `[]`，Go journal 無 write/error。
- [x] **19.15.3** Read-only promotion closure — 決議保留 hardened permanent read-only Caddy route，Phase 19 Go read-only promotion 關閉為 `closed_stabilized`。Go 只擁有已驗證 GET read surface；Python 仍擁有 writes/files/system/server/import/export/cleanup/frontend/static/migrations。
- [x] **19.15.4** No route expansion by default — 未擴大 Go route、未改 frontend default、未加入 Go writes/files/migrations、未移除 Python、未擴大 public exposure。新增 `tests/test_phase19_go_post_matcher_hardening_stabilization.py`。

## 🚦 Phase 20: Post-readonly Go Scope Assessment — ✅ Closed (20.4 Stabilized)

> **來源**: Phase 19 `closed_stabilized` read-only promotion、`docs/API_REFERENCE.md`、`docs/SCHEMA.md`、`routes/`、`go-shadow/`。
> **目標**: 在不擴 runtime ownership 的前提下，評估 read-only 之後是否還有必要讓 Go 承接更多 surface；先鎖 contract、side effects、rollback 與測試，不直接實作 writes/files/migrations。
> **原則**: Go 目前只擁有 hardened Caddy matcher 下的已驗證 GET read surface；Python 仍是 writes/files/system/server/import/export/cleanup/frontend/static/migration owner 與 rollback baseline。

### ✅ 20.0 Post-readonly Go Scope Assessment Gate

- [x] **20.0.1** Plan-only scope approval — 使用者明確授權後完成 read-only 之外的 Go ownership 評估；新增 `docs/contracts/phase20-go-post-readonly-scope-assessment.json`。
- [x] **20.0.2** Boundary-first assessment — 盤點 write/file/system/migration 類候選：notes writes、category/tag writes、upload/attachments/cleanup/import/export、system/server/migrations 全部仍有 transaction、file side effects、CSRF/local-only、backup/rollback、parity fixtures 等 blocker。
- [x] **20.0.3** Recommended next gate — 20.0 不推薦直接實作任何 Go write/file/migration；下一步只允許 20.1 `Write Surface Contract Inventory Gate`，先做 machine-readable route inventory、side-effect map、backup/rollback requirements、future parity fixture plan。
- [x] **20.0.4** No implementation by default — 未加入 Go writes/files/migrations、未擴 Caddy route、未改 frontend default、未移除 Python、未擴大 public exposure。新增 `tests/test_phase20_go_post_readonly_scope_assessment.py`。

### ✅ 20.1 Write Surface Contract Inventory Gate

- [x] **20.1.1** Inventory approval — 使用者明確授權後，建立 Python-owned mutation/file/system/import/export/cleanup/migration surface 的 machine-readable inventory；見 `docs/contracts/phase20-go-write-surface-contract-inventory.json`。
- [x] **20.1.2** Side-effect and rollback map — 依 route class 文件化 DB writes、file writes/deletes、external fetches、service/process actions、security boundary、backup/rollback 與 future parity fixture requirements。
- [x] **20.1.3** No Go implementation — 20.1 未實作 Go write/file/migration、未擴 Caddy route、未改 frontend default、未移除 Python、未擴大 public exposure。新增 `tests/test_phase20_go_write_surface_contract_inventory.py`。

### ✅ 20.2 Candidate Selection and Fixture Planning Gate

- [x] **20.2.1** Candidate decision — 使用者明確授權後，plan-only 選擇唯一 candidate：`read_surface_polish`。決議先強化已 promoted 的 Go read-only surface parity / 文件 / fixture，不選 notes writes、batch/actions、history restore、category/tag writes、attachments、uploads、cleanup、import/export、system/server、prompt/wizard config。
- [x] **20.2.2** Fixture and rollback plan — 新增 `docs/contracts/phase20-go-candidate-fixture-planning.json`，定義 Python baseline fixtures、future Go comparison owner、hardened read surface matrix、search parity matrix、ownership boundary matrix、runtime invariant matrix、rollback evidence 與 20.3 stop conditions。
- [x] **20.2.3** No implementation by default — 20.2 未實作 Go write/file/migration、未擴 Caddy route、未改 `prism-go-readonly.service` query-only 模式、未改 frontend default、未移除 Python、未擴大 public exposure、未做 live Pi service 或 Caddy reload。新增 `tests/test_phase20_go_candidate_fixture_planning.py`。

### ✅ 20.3 Read Surface Parity and Documentation Polish Gate

- [x] **20.3.1** Read parity fixture execution — 使用者明確授權後，針對 20.2 選定的 `read_surface_polish` 補強 Python vs Go read-only parity：Go `GET /api/notes?q=...` 補齊 DB-only `Note_Attachments.title` / `file_path` metadata 搜尋，並在 `tests/test_phase18_go_shadow_contract.py` 加入 `attachment-meta-canary` Python vs Go response diff fixture。
- [x] **20.3.2** Documentation alignment — 新增 `docs/contracts/phase20-go-read-surface-polish.json`，並同步 `docs/API_REFERENCE.md` / `docs/ARCHITECTURE.md`：文字附件 body 搜尋仍是 Python-owned gap，未偷擴 Go file body scan / route ownership。
- [x] **20.3.3** No runtime expansion — 20.3 未實作 Go write/file/migration、未擴 Caddy route、未關閉 SQLite `query_only`、未改 frontend default、未移除 Python、未擴大 public exposure、未做 live Pi service 或 Caddy reload。新增 `tests/test_phase20_go_read_surface_polish.py`。

### ✅ 20.4 Post-polish Stabilization and Candidate Closure Gate

- [x] **20.4.1** Stabilization review — 使用者明確授權後，plan-only 回顧 20.3 read-surface polish 結果；決議 Phase 20 關閉為 `closed_stabilized`，不把 file-read parity 升格為下一個 active implementation。
- [x] **20.4.2** File-read parity decision — 新增 `docs/contracts/phase20-go-post-polish-stabilization.json`：Go 文字附件 body 搜尋仍需另行 file-read safety / data-dir / path traversal / performance / rollback contract，20.4 不直接實作。
- [x] **20.4.3** No runtime expansion — 20.4 未實作 Go writes/files/migrations、未擴 Caddy route、未關閉 SQLite `query_only`、未改 frontend default、未移除 Python、未擴大 public exposure、未做 live Pi service 或 Caddy reload。新增 `tests/test_phase20_go_post_polish_stabilization.py`。

---

## 🧭 Phase 21: Delivery and Queue Selection — ✅ Closed to Product/Frontend Backlog

> **來源**: Phase 20 `closed_stabilized`、未部署/未推送的本機 Phase 20.2-20.4 changes、`DEPLOY-PI.md`、GitHub publish hygiene。
> **目標**: 在 Phase 20 關閉後，先選下一個分支：local commit/push、Pi delivery planning、file-read parity assessment，或回到 product/frontend backlog；不得把 delivery、deploy、file-read implementation 混成同一步。
> **原則**: 未另行授權前，不做 git commit/push、不部署 Pi、不 reload Caddy/service、不新增 Go file-read/body scan、不擴 Go writes/files/migrations、不改 frontend default、不移除 Python、不擴大 public exposure。

### ✅ 21.0 Delivery and Queue Selection Gate

- [x] **21.0.1** Branch selection — 使用者明確要求 plan-only delivery sweep 後，建議下一分支選 `local commit/push`，但若 dirty tree / privacy / runtime truth sweep 有 blocker 則停止。
- [x] **21.0.2** Delivery boundary — 已完成 dirty tree / privacy / runtime truth sweep：`main` 與 `origin/main` 同步、pre-21.1 無 tracked diff / non-ignored untracked；`.omx/`、`knowledge.db`、`app.log`、uploads、attachments、build 等為 ignored local artifacts。Pi / Caddy / systemd live state 未驗證且未宣稱更新。
- [x] **21.0.3** No implementation by default — 21.0 未授權也未做 git commit/push、Pi deploy、Caddy/service reload、Go attachment body scan、Go writes/files/migrations、frontend default change、Python removal 或 public exposure。

### ✅ 21.1 Local Commit and Push Readiness Gate

- [x] **21.1.1** Recommended branch lock — 使用者明確授權後，新增 `docs/contracts/phase21-local-commit-push-readiness.json`，將下一分支鎖為 `local_commit_push`，但 commit/push 仍需 21.2 另行明確授權。
- [x] **21.1.2** Commit scope and exclusions — 21.1 proposed commit 僅包含 `docs/contracts/phase21-local-commit-push-readiness.json`、`tests/test_phase21_local_commit_push_readiness.py`、`docs/TODO.md`；明確排除 `.omx/`、`knowledge.db`、`app.log`、uploads、attachments、notes、build、`.env*`、local DB/log/backup/runtime artifact 與非必要 dependency/vendor churn。
- [x] **21.1.3** No delivery side effects — 21.1 未做 git commit/push、未部署 Pi、未 reload Caddy/service、未實作 Go file-read/body scan、未擴 Go writes/files/migrations、未改 frontend default、未移除 Python、未擴大 public exposure。新增 `tests/test_phase21_local_commit_push_readiness.py`。

### ✅ 21.2 Explicit Local Commit and Push Approval Gate

- [x] **21.2.1** Final pre-stage sweep — 使用者明確授權後，commit 前重跑 dirty tree / privacy / runtime artifact sweep；staged scope 僅限 Phase 21 docs/test delivery payload，排除 ignored local DB/log/upload/attachment/build/runtime artifacts。
- [x] **21.2.2** Verification before commit — 依 21.1 contract 跑 `git diff --check`、targeted pytest、Phase 20 closure pytest、full `pytest tests/ -v`；失敗即停止。
- [x] **21.2.3** Lore commit / push boundary — 依 Lore Commit Protocol stage/commit/push Phase 21 local delivery payload；未部署 Pi、未 reload Caddy/service、未實作 Go file-read/body scan、未擴 Go writes/files/migrations、未改 frontend default、未移除 Python、未擴大 public exposure。

### ✅ 21.3 Post-push Delivery Decision Gate

- [x] **21.3.1** Post-push truth selection — 使用者明確授權後，選擇下一分支為 `product/frontend backlog`；新增 `docs/contracts/phase21-post-push-product-frontend-selection.json`，不進 Pi delivery planning、file-read parity assessment 或 Go ownership expansion。
- [x] **21.3.2** Runtime boundary — 21.3 未做 Pi deploy、未 reload Caddy/service、未改 public exposure；repo-local ignored `.omx/` runtime/cache 目錄已依使用者要求刪除一次，未動全域 Codex / oh-my-codex 安裝，且無 tracked git effect；後續工具呼叫顯示 active native hooks 仍可能重建 ignored `.omx/` state，若要 durable removal 需另行停用/解除全域 hook。
- [x] **21.3.3** Implementation boundary — 21.3 未實作 Go file-read/body scan、未擴 Go writes/files/migrations、未改 frontend default、未移除 Python、未新增 backend API/schema、未做 frontend implementation。新增 `tests/test_phase21_post_push_product_frontend_selection.py`。

---

## 🎛️ Phase 22: Product Frontend Backlog Intake — 🚦 Active

> **來源**: Phase 21.3 `product_frontend_backlog` branch selection、`docs/FRONTEND-REDESIGN-PLAN.md`、`docs/New_UI/Prism Redesign - standalone.html`、現有 React/Vite frontend。
> **目標**: 先 read-only 盤點 product/frontend backlog candidate，再只 promote 一個最小、workflow-safe、可驗證的 frontend/product item；不得把 backlog intake 直接變成大改版。
> **原則**: 保留現有 API/schema、React/Vite/Zustand/Tailwind stack、Preview Editing UX 與本地優先定位；不新增 AI/ML、協作、realtime、plugin platform、collections schema、server-side UI preference persistence 或 Go/runtime scope。

### ✅ 22.0 Product Frontend Backlog Intake Gate

- [x] **22.0.1** Read-only backlog audit — 使用者明確授權後，盤點 Home/search/filter/navigation、reading/editor workflow、Prompt Builder、Settings 與 frontend docs/prototype 差距；Phase 18.1-18.3 已完成大部分 redesign，不重開大改版。
- [x] **22.0.2** Candidate selection — 新增 `docs/contracts/phase22-product-frontend-backlog-intake.json`，只選一個 smallest workflow-safe item：`command_palette_entrypoint_reliability`。現況 finding：Header command palette button 以 synthetic `KeyboardEvent('keydown', { ctrlKey: true, key: 'k' })` 間接開啟 palette；22.1 可改為 explicit open/toggle path，同時保留 Ctrl+K / Cmd+K。
- [x] **22.0.3** Implementation boundary — 22.0 未做 frontend implementation、新 backend API/schema、frontend default API target change、Pi deploy、Caddy/service reload、Go file-read/body scan、Go writes/files/migrations、Python removal 或 public exposure。新增 `tests/test_phase22_product_frontend_backlog_intake.py`。

### ✅ 22.1 Command Palette Entrypoint Reliability

> **白話說明**：
> 這一步會真的改 Command Palette 的開啟流程：Header 上的命令面板按鈕不再用「假裝按下 Ctrl+K」的方式開啟，而是直接呼叫一個明確的開啟動作。
> 要修這個，是因為舊做法雖然能用，但把滑鼠按鈕綁到鍵盤事件上，之後維護時容易搞不清楚到底誰負責開關面板。
> 使用者應該不會感覺到功能差異：點 Header 按鈕仍會開啟面板，Ctrl+K / Cmd+K 仍能開關，Esc 仍能關閉，搜尋、去設定頁、開最近筆記、新增筆記、切換明暗主題都照舊。
> 這一步不改後端 API、資料庫、路由、筆記資料、Pi/Caddy/service、Go runtime、公開暴露範圍，也不新增 AI、collections 或 server-side UI preference。

- [x] **22.1.1** Explicit palette open path — 使用者明確授權後，僅修 Header / CommandPalette 的開啟狀態 ownership（也就是「誰負責開關命令面板」），移除 Header synthetic keyboard event dispatch（也就是「假裝送出鍵盤快捷鍵」）；保留既有 Ctrl+K / Cmd+K keyboard shortcut。
- [x] **22.1.2** Behavior preservation — palette search、Esc close、Settings navigation、recent note open、new note action、theme toggle 均維持現有行為；未新增 backend/API/schema/storage。
- [x] **22.1.3** Verification — 新增 `docs/contracts/phase22-command-palette-entrypoint-reliability.json` 與 `tests/test_phase22_command_palette_entrypoint_reliability.py`；需跑 `cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v`，並做 browser flow：點 Header palette button、搜尋/導覽 Settings、Ctrl+K/Cmd+K 開關、Esc 關閉、New Note action、console clean。

### ✅ 22.2 Product Frontend Backlog Next Selection Gate

> **白話說明**：
> 這一步只是決定/盤點/規劃，不會實作功能。
> 這次是在 22.1 修完後，重新看目前前端還有哪些小而明確的改善點，最後選出下一個候選：搜尋沒有結果時，Home 不應該還說「還沒有任何筆記」。
> 使用者在 22.2 本身不會感覺到產品差異，因為這一步只產出下一個 frontend backlog gate 的選擇與驗證計畫。
> 這一步不改 UI 程式、不改後端 API、不改資料庫、不改 Pi/Caddy/service、不改 Go runtime，也不擴大公開暴露。

- [x] **22.2.1** Next candidate sweep — 使用者明確授權後，重新盤點 Settings deep linking、Prompt Builder mobile action bar、Home empty state context actions 與 browser-evidenced frontend follow-up；新增 `docs/contracts/phase22-product-frontend-next-selection.json`，只選一個 smallest workflow-safe item：`home_search_empty_state_context_copy`。
- [x] **22.2.2** Browser evidence and rejection log — in-app Browser 回報 unavailable，改用本機 Chrome + Playwright fallback 做 read-only evidence：Settings tab reload 會回外觀、Prompt Builder mobile action bar 首屏不可見、Home 搜尋無結果仍顯示 generic no-notes text；Settings / Prompt Builder 因 URL-state / visual layout 範圍較大，未選為 22.3。
- [x] **22.2.3** Plan-only boundary — 22.2 未做 frontend implementation、新 backend API/schema、frontend default API target change、Pi deploy、Caddy/service reload、Go file-read/body scan、Go writes/files/migrations、Python removal 或 public exposure。新增 `tests/test_phase22_product_frontend_next_selection.py`。

### ✅ 22.3 Home Search Empty State Context Copy

> **白話說明**：
> 這一步會真的改 Home 搜尋沒有結果時看到的文字：現在頁面標題已經是「搜尋結果」，但空狀態還說「還沒有任何筆記」，容易讓人以為整個資料庫是空的。
> 要修這個，是因為搜尋沒有命中和資料庫真的沒有筆記是兩種不同情境，畫面文字應該說清楚。
> 使用者會感覺到的差異是：搜尋沒有結果時會看到更貼近情境的說明；正常有結果、真的沒有任何筆記、閱讀/編輯/篩選/API 都不應改變。
> 這一步不改後端 API、資料庫、路由、筆記資料、Pi/Caddy/service、Go runtime、公開暴露範圍，也不新增 AI、collections 或 server-side UI preference。
> Risk level: `P2 low-risk polish`。這是純 UI 文案 / 低風險整理，所以直接作為同一 task 的 small patch，不新增 22.3 contract、不再拆多層 approval gate。

- [x] **22.3.1** Search no-result copy — 使用者明確授權後，只在 Home empty state 依 `searchQuery` 顯示搜尋無結果文案，不再把搜尋無命中寫成「還沒有任何筆記」。
- [x] **22.3.2** Preserve default empty library state — 真正沒有任何筆記且沒有搜尋/篩選時，仍保留目前「還沒有任何筆記」語意。
- [x] **22.3.3** Verification — 新增 `tests/test_phase22_home_search_empty_state_context_copy.py`；需跑 `cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v`，並做 browser flow：輸入 guaranteed no-match 搜尋詞後，空狀態顯示 no-result context，不新增 console error。

### 📌 Product Frontend Backlog Parking Lot — Plan When Needed

> **白話說明**：
> P2 不再開下一個儀式化 phase。22.3 後若要繼續前端小修，直接從下面候選挑一個小 patch；只有 workflow-sensitive 的改動才最多拆成 plan gate + implementation gate。
> 目前保留兩個候選：Settings 分頁網址保存、Prompt Builder 手機動作列位置。它們都比 22.3 稍大，之後要做時先重新看 browser evidence。

- [ ] **Settings tab deep linking** — `P1 workflow-sensitive`；讓 Settings tab 可被 URL 保存 / reload 回同一 tab，需避免破壞既有 tab 操作。
- [ ] **Prompt Builder mobile action bar polish** — `P1 workflow-sensitive`；手機寬度下調整 action bar 可見性，需 visual/browser iteration。

### ⏸️ Phase 19.0 不處理

- 正式替換 Flask route 或讓前端改打 Go。
- POST / PUT / DELETE。
- Production `knowledge.db` 寫入、migration 執行或自動修復。
- Attachments、export、cleanup、`/api/server/*`。
- 移除 Python backend、venv 或現有 Pi `prism.service`。

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
| **frontend-product** | 2026-06-05 | Phase 22.3 home search empty state context copy — Risk level `P2 low-risk polish`。依新規劃粒度規則，直接做 small patch：Home 搜尋無結果時改顯示「找不到符合的筆記」與搜尋詞說明，保留真正空資料庫時的「還沒有任何筆記」。不新增 22.3 contract、不開下一個儀式化 phase；僅補 targeted source regression test、frontend typecheck/build、full pytest 與 browser flow。未新增 backend API/schema/storage、未改 Pi/Caddy/service、Go runtime 或 public exposure。 |
| **frontend-product** | 2026-06-05 | Phase 22.2 product/frontend next selection gate — 在明確授權後完成 plan-only 下一候選選擇；in-app Browser unavailable，改用本機 Chrome + Playwright fallback 觀察 Settings tab deep link、Prompt Builder mobile action bar、Home search empty state。選定 `home_search_empty_state_context_copy` 作為 22.3，因搜尋無結果時目前仍顯示 generic「還沒有任何筆記」文案；Settings deep link 與 Prompt Builder mobile polish 因 URL-state / visual layout 範圍較大暫不選。22.2 未做 frontend implementation、新 backend API/schema、Pi deploy、Caddy/service reload、Go file-read/body scan、Go writes/files/migrations、Python removal 或 public exposure。 |
| **frontend-product** | 2026-06-05 | Phase 22.1 command palette entrypoint reliability — 在明確授權後將 Header 命令面板按鈕改為直接呼叫 `openCommandPalette`，不再用 synthetic keyboard event 假裝按下 Ctrl+K；CommandPalette 仍保留 Ctrl+K / Cmd+K toggle、Esc close、搜尋、Settings navigation、recent note、new note 與 theme toggle。新增 22.1 contract / pytest lock，並依新要求在 22.1 / 22.2 區塊補 `> **白話說明**：`。未新增 backend API/schema/storage、未改 frontend default API target、未部署 Pi、未 reload Caddy/service、未擴 Go runtime 或 public exposure。 |
| **frontend-product** | 2026-06-05 | Phase 22.0 product/frontend backlog intake — 在明確授權後完成 read-only audit：Phase 18.1 shell/filter/command palette、18.2 reading/editor、18.3 Prompt Builder/Settings 已完成，不重開大改版；只選一個最小候選 `command_palette_entrypoint_reliability` 作為 22.1 gate。22.0 未做 frontend implementation、新 backend API/schema、frontend default API target change、Pi deploy、Caddy/service reload、Go file-read/body scan、Go writes/files/migrations、Python removal 或 public exposure。 |
| **frontend-product** | 2026-06-05 | Phase 21.3 post-push delivery decision gate — 在明確授權後選擇下一分支為 `product/frontend backlog`，新增 21.3 selection contract / pytest lock，將 22.0 設為 product/frontend backlog intake gate。21.3 未進 Pi delivery planning、未評估/實作 Go file-read parity、未擴 Go writes/files/migrations、未改 frontend default、未移除 Python、未擴大 public exposure；repo-local ignored `.omx/` runtime/cache 目錄已依使用者要求刪除一次，未動全域 Codex / oh-my-codex 安裝且無 tracked git effect；active native hooks 後續仍可能重建 ignored `.omx/` state，durable removal 需另行停用/解除全域 hook。 |
| **backend-go-runtime** | 2026-06-05 | Phase 21.2 explicit local commit and push approval gate — 在明確授權後重跑 pre-stage dirty tree / privacy / runtime artifact sweep，僅 stage Phase 21 docs/test delivery payload，依 Lore Commit Protocol commit/push。驗證要求包含 `git diff --check`、21.1 targeted pytest、Phase 20 closure pytest、full `pytest tests/ -v`；未部署 Pi、未 reload Caddy/service、未實作 Go attachment body scan、未擴 Go writes/files/migrations、未改 frontend default、未移除 Python、未擴大 public exposure；21.3 為需另行授權的 post-push delivery decision gate。 |
| **backend-go-runtime** | 2026-06-05 | Phase 21.1 local commit and push readiness gate — 在明確授權後選定下一分支為 `local_commit_push`，但 commit/push 仍保留給 21.2 explicit approval gate；新增 readiness contract / pytest lock，固定 dirty tree、privacy artifact、runtime truth、proposed include/exclude、tests-before-commit 與 stop conditions。未做 git commit/push、未部署 Pi、未 reload Caddy/service、未實作 Go attachment body scan、未擴 Go writes/files/migrations、未改 frontend default、未移除 Python、未擴大 public exposure。 |
| **backend-go-runtime** | 2026-06-05 | Phase 20.4 post-polish stabilization and candidate closure — 在明確授權後完成 plan-only stabilization review：Phase 20 關閉為 `closed_stabilized`；20.3 已補齊 DB-only attachment metadata read parity，剩餘文字附件 body 搜尋仍 Python-owned，若未來要評估 Go file-read parity，必須另開 file-read safety / data-dir / path traversal / performance / rollback contract。未實作 Go attachment body scan、Go writes/files/migrations、未擴 Caddy route、未關閉 sidecar SQLite `query_only`、未改 frontend default、未移除 Python、未做 live Pi service 或 Caddy reload；21.0 為需另行授權的 delivery and queue selection gate。 |
| **backend-go-runtime** | 2026-06-05 | Phase 20.3 read surface parity and documentation polish — 在明確授權後完成既有 hardened Go read-only surface polish：Go `/api/notes?q=...` 補齊 DB-only `Note_Attachments.title` / `file_path` metadata 搜尋，Python vs Go diff fixture 新增 `attachment-meta-canary`；新增 20.3 contract / pytest lock，並同步 API / architecture docs 明確標示文字附件 body 搜尋仍是 Python-owned gap，未擴 Go file body scan。未實作 Go writes/files/migrations、未擴 Caddy route、未關閉 sidecar SQLite `query_only`、未改 frontend default、未移除 Python、未做 live Pi service 或 Caddy reload；20.4 為需另行授權的 post-polish stabilization and candidate closure gate。 |
| **backend-go-runtime** | 2026-06-05 | Phase 20.2 candidate selection and fixture planning — 在明確授權後完成 plan-only candidate decision：唯一選擇 `read_surface_polish`，先強化既有 hardened Go read-only surface 的 parity / docs / fixtures；拒絕 notes writes、batch/actions、history restore、category/tag writes、attachments/uploads/cleanup/import/export/system/server/config 等 ownership candidate。新增 fixture / rollback / stop-condition contract 與 pytest lock；未實作 Go writes/files/migrations、未擴 Caddy route、未改 sidecar query-only 模式、未改 frontend default、未移除 Python、未做 live Pi service 或 Caddy reload；20.3 為需另行授權的 read surface parity and documentation polish gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 20.1 write surface contract inventory — 在明確授權後完成 plan-only route class 盤點：notes core writes、batch/actions、history restore、category/tag writes、attachments/long content、uploads/remote fetch、cleanup/media maintenance、import/export、system maintenance、server local operations、prompt/wizard config 全部仍 Python-owned。新增 side-effect / rollback / fixture requirements 與 pytest lock；未實作 Go writes/files/migrations、未擴 Caddy route、未改 sidecar query-only 模式、未改 frontend default、未移除 Python；20.2 為需另行授權的 candidate selection and fixture planning gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 20.0 post-readonly Go scope assessment — 在明確授權後完成 plan-only 評估：Phase 19 已 `closed_stabilized`，Go 只擁有 hardened Caddy matcher 下的 GET read surface；notes writes、category/tag writes、upload/attachments/cleanup/import/export、system/server/migrations 全部仍有 transaction、file side effects、CSRF/local-only、backup/rollback、parity fixture blocker。20.0 不實作任何 Go write/file/migration、不擴 Caddy route、不改 frontend default、不移除 Python；20.1 為需另行授權的 write surface contract inventory gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.15 post-matcher hardening stabilization — 在明確授權後不改 Caddy、不 reload，只做 narrowed matcher monitoring：5 輪、每輪 10 秒驗 exact read list 與 numeric note detail 仍有 `X-Prism-Go-Read-Routing: hit`，非 numeric/nested `/api/notes/...`、system/routing/server/version/POST 無 Go header；Caddy validate 通過，migration v16 pending `[]`，Go journal 無 write/error。決議保留 hardened permanent read-only Caddy route，Phase 19 Go read-only promotion 關閉為 `closed_stabilized`。20.0 為需另行授權的 plan-only post-readonly Go scope assessment。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.14 permanent route matcher/runbook hardening — 在明確授權後檢查 19.12 retained Caddy matcher，將 `/api/notes/*` wildcard 縮窄為 exact `/api/notes` + numeric `^/api/notes/[0-9]+$`；先以暫存 Caddyfile validate，再建立 backup `Caddyfile.prism-pre-matcher-hardening-20260604_182035.bak`、套用、validate/reload。3 輪 live sample 驗白名單 GET 仍有 Go header，`/api/notes/not-a-number`、`/api/notes/114/extra`、system/routing/server/version/POST 無 Go header；migration v16 pending `[]`，Go journal 無 write/error。未擴 route、未改 frontend default、未加入 Go writes/files/migrations；19.15 為需另行授權的 post-hardening stabilization gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.13 post-permanent read-only cutover stabilization — 在明確授權後不改 Caddy、不 reload，只做 live monitoring / keep-or-rollback decision：5 輪、每輪 10 秒驗 `prism.service` / Caddy / `prism-go-readonly.service` active、sidecar enabled、localhost bind、schema v16、`sqlite_query_only=true`；白名單 GET 皆有 `X-Prism-Go-Read-Routing: hit`，system/routing/server/version/POST 無 Go header，migration v16 pending `[]`，Go journal 無 write methods/error，Caddy validate 通過。決議保留 permanent read-only route；19.14 為需另行授權的 matcher/runbook hardening gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.12 permanent read-only Caddy cutover — 在明確授權後從 Python-only Caddy route 起點建立 DB backup `prism_pre_permanent_caddy_readonly_cutover_20260604_180157.db` 與 Caddy backup `Caddyfile.prism-pre-permanent-go-readonly-cutover-20260604_180157.bak`，啟用 `prism-go-readonly.service` active+enabled (`127.0.0.1:5002`, schema v16, `sqlite_query_only=true`)，Caddy validate/reload 後保留 permanent read-only route。3 輪 live sample 驗白名單 GET 皆有 `X-Prism-Go-Read-Routing: hit`，system/routing/POST 無 Go header，migration v16 pending `[]`，Go journal 無 write methods。未改 frontend default、未授權 Go writes/files/migrations、未移除 Python；19.13 為需另行授權的 post-permanent stabilization gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.11 Caddy cutover candidate decision gate — 在明確授權後新增 proposal-only permanent-cutover contract：Go 保留為 verified Caddy-routable read-only sidecar candidate；proposal 固定 operation window、external auth/exposure boundary、fresh DB/Caddy backups、Caddy validate、monitoring、rollback owner/triggers/revert plan。未改 live Caddy、未 reload、未 permanent route、未改 frontend default；Go writes/files/migrations、Python removal、direct public exposure 仍未授權。19.12 為需另行授權的 permanent read-only Caddy cutover approval gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.10 post-Caddy drill decision gate — 在明確授權後執行 bounded extended Caddy-level read-only soak：從 Python-only 起點建立 DB backup `prism_pre_caddy_extended_soak_20260604_173527.db` 與 Caddy backup `Caddyfile.prism-pre-go-caddy-extended-soak-20260604_173527.bak`，Caddy route validate/reload 後 10 輪、每輪 60 秒驗白名單 GET 皆有 `X-Prism-Go-Read-Routing: hit`，system/routing/POST 無 Go header，Go journal 無 POST/PUT/DELETE/PATCH。Rollback 後 routing false、sidecar inactive、5002 無 listener。新增 19.10 contract/test；19.11 為需另行授權的 Caddy cutover candidate decision gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.9 approved Caddy read-only routing drill — 依 19.8 plan 與明確授權執行短暫 Caddy-level route drill：建立 DB backup `prism_pre_caddy_readonly_drill_20260604_040342.db` 與 Caddy backup `Caddyfile.prism-pre-go-readonly-drill-20260604_040342.bak`，Go sidecar localhost/query_only/schema v16，Caddy route block validate + reload 後 3 輪、每輪 30 秒驗白名單 GET 皆有 `X-Prism-Go-Read-Routing: hit`，system/routing/POST 仍 Python-owned 且無 Go header。Rollback 已用備份還原 Caddy、validate/reload、停止 sidecar；最終 routing false、sidecar inactive、5002 無 listener。19.10 為需另行授權的 post-Caddy drill decision gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.8 reverse-proxy/service cutover planning gate — 新增 plan-only machine-readable contract，補上 Caddy/service routing gap：只允許已驗證 GET read surface 規劃到 localhost Go sidecar；Python 仍是 write/file/maintenance/migration owner 與 rollback target。Plan 固定 Caddy validate、config backup、fresh DB backup、header/status/log monitoring、rollback/failure criteria，以及 localhost/trusted LAN/VPN/SSH tunnel/protected reverse proxy exposure boundary。未改 live Caddy、未 reload Caddy、未改 frontend default；19.9 為需另行授權的 approved Caddy read-only routing drill。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.7 post-soak decision gate — 在明確授權後執行 bounded extended Python-switch read-only soak：從 Python-only 起點建立 fresh backup `prism_pre_go_readonly_long_soak_20260604_034124.db`，啟動 Go sidecar `127.0.0.1:5002` 且 `/healthz` schema v16 / `sqlite_query_only=true`，Python opt-in routing 連續 10 輪、每輪 60 秒驗白名單 GET header 與 Python-owned migration/POST boundary；Go journal 自本輪 start 起無 POST/PUT/DELETE/PATCH。Rollback 後 `routing=false`、sidecar inactive、5002 無 listener。新增 19.7 contract/test；19.8 為需另行授權的 reverse-proxy/service cutover plan gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.6 approved read-only soak execution — 依使用者授權在 Pi 執行 19.5 stage 0/1：建立 production DB backup `prism_pre_go_readonly_soak_20260604_032653.db`，部署 Go sidecar `prism-go-readonly.service` 綁 `127.0.0.1:5002`，驗證 `/healthz` schema v16 + `sqlite_query_only=true`，短暫啟用 Python `PRISM_GO_READ_ROUTING` 後白名單 GET 皆有 `X-Prism-Go-Read-Routing: hit`；非白名單 / write method 仍 Python-owned。Rollback drill 已移除 drop-in、routing 回 `enabled=false`、停止 sidecar、5002 無 listener。未改 Caddy、未改 frontend default、未新增 Go writes/files/migrations；19.7 為需另行授權的 post-soak decision gate。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.5 read-only service-level cutover plan — 新增 plan-only machine-readable contract，定義 Python primary + Go localhost read-only sidecar topology、preflight、backup、monitoring evidence、rollback drill、success/failure criteria 與 exposure boundary。未執行 live Pi/service/Caddy/frontend/production DB 變更；19.6 被標記為 blocked pending explicit approval。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.4 cutover readiness audit — 新增 machine-readable audit，彙整 19.0-19.3 evidence 與 blocking gaps；結論是可另開 19.5 read-only service-level cutover plan，但 19.4 不授權替換 `prism.service`、改 frontend default、寫 production DB、跑 Go migration、移除 Python 或加入 Go writes/files。新增 pytest lock 固定 audit-only / runtime_change=false / next step requires approval。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.3 controlled read routing proof — 新增 opt-in Flask routing switch：`PRISM_GO_READ_ROUTING=1` + localhost-only `PRISM_GO_READ_BASE_URL` 時，僅代理已驗證 GET read surface 到 Go sidecar；預設關閉，Go unavailable / invalid base URL fail-open 回 Python。新增 `GET /api/system/go-read-routing` 狀態 endpoint、proxied header `X-Prism-Go-Read-Routing: hit`、19.3 contract 與 pytest coverage。下一步 Phase 19.4 只做 cutover readiness audit，不直接替換 service。 |
| **backend-go-runtime** | 2026-06-04 | Phase 19.2 Go read-only promotion gate — 新增 machine-readable promotion gate 與 pytest lock，決議 Go runtime 只升級為 controlled read-only candidate；Python `prism.service` 仍是主 runtime / rollback path，Go 不跑 migration、不替換 service、不讓前端預設改打 Go。下一步規劃為 Phase 19.3 controlled read routing proof，僅允許 local-only 或 sidecar-only explicit reversible switch。 |
| **backend-go-runtime** | 2026-06-01 | Phase 19.0/19.1 Go Runtime / Packaging Promotion proof + real-data read-only canary run — Pi 先以既有 Python `prism.service` 完成 v16 deploy readiness：backup `prism_pre_v16_20260601_025914.db`，migration status current/latest 16、pending []，`/api/test`、首頁、notes list、note detail live 皆 200。Go runtime 仍不替換 service；只讀 Pi v16 DB copy `prism_go_canary_v16_20260601_030059.db`，sidecar 因 5001 被 unrelated `fava` 佔用改綁 `127.0.0.1:5002` 完成 `/healthz`、read-only API、embedded frontend smoke 與 log check。量測 RSS / startup：Windows Python 46,660 KB / 538 ms、Go 11,104 KB API smoke / 513 ms；Pi Python 47,104 KB / 422 ms、Go 13,488 KB / 278 ms。未新增 POST/PUT/DELETE，未做 Go migration，未讀寫正式 production DB，未碰 attachments/export/cleanup/server maintenance。 |
| **frontend-ui** | 2026-05-29 | Appearance settings 簡化 — 移除 `Linear` / `Editorial` / `Studio` 美學方向 UI，舊 `prism.aestheticMode` 僅讀取相容並正規化為 Editorial baseline；新增 `背景色調`（`prism.backgroundScheme` + `data-bg`）五組 semantic background palette，每組支援深色/淺色；`data-accent` 僅控制 primary/accent/focus/tag/active 類狀態，中文摘要維持 normal font-style。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build` passed；Playwright fallback 驗證 Settings 不再出現美學方向/Linear/Editorial/Studio，切換背景色調與強調色後背景 tokens 不被 accent 覆蓋，mobile 無水平溢出。 |
| **pi-deploy** | 2026-05-28 | 部署 Appearance controls follow-up 到 Raspberry Pi：同步 `frontend/dist` 與 `docs/TODO.md`，重啟 `prism.service` 後 live 驗證 `active`；`/api/test` status ok、`/api/server/version` v2.4.9 + V2 mode true、migration current/latest 15 且無 pending；首頁 HTML 指向 `assets/index-CKp_FqWr.css` / `assets/index-HYEMKfiU.js`，Pi dist CSS 內含 `data-accent`、`--prism-sidebar-width`、`--prism-corner-radius`。 |
| **frontend-ui** | 2026-05-28 | Appearance controls fidelity follow-up — `Linear` / `Editorial` / `Studio` 保留各自 dark/light 整體 palette，`主色` 改為 `data-accent` 強調色覆蓋，避免美學方向吃掉主題色彩；補入 prototype 的邊角圓潤度與側邊欄寬度 slider，使用 `localStorage` + CSS variables 套用到卡片、按鈕、輸入框與桌面 sidebar。**收尾驗證**：`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v` → 87 passed；Playwright 驗證 Studio/light 背景維持 `#ebe6d8`、主色切夕陽橙後 `--color-primary=#f97316`、圓角 `18px`、sidebar `288px` 實際生效且無 console error。 |
| **frontend-ui** | 2026-05-28 | Appearance palette fidelity follow-up — 對齊 `Prism Redesign - standalone.html` 的 `Linear` / `Editorial` / `Studio` token，補齊 dark/light 六組整體 palette：Linear 冷灰藍、Editorial 暖紙色/棕金、Studio 暖米色/鼠尾草綠；初始化與切換同步 `data-mode`，避免只改 selected state 而未改整體色系。**收尾驗證**：`cd frontend && npm run build` passed；Playwright 驗證三種 aesthetic 點擊後 `--color-bg-base` / `--color-primary` 均不同，切到 light 後 Studio 套用 `#ebe6d8` / `#006c4e`。 |
| **pi-deploy** | 2026-05-28 | 部署 Phase 18.3 follow-up 到 Raspberry Pi：同步 `frontend/dist`、`utils/query_builder.py`、`docs/TODO.md`，重啟 `prism.service` 後 live 驗證 `active`；`/api/test` status ok、`/api/server/version` v2.4.9 + V2 mode true、`/api/system/migration-status` current/latest 15 且無 pending；dist assets 為 `index-5Z_Y_Vm1.js` / `index-BqlIPmnX.css`；建立臨時 Pi 筆記後 `/api/notes?q=todo.md&per_page=100` 命中並成功刪除臨時資料。 |
