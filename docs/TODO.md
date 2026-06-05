# Prism - Modernization & Intelligence Roadmap (TODO)

**狀態**: 🟢 穩定運行 (Stable)
**核心目標**: Headless KMS API + 純關鍵字 FTS 搜尋
**文件參照**: `docs/Prism.md` (歷史背景), `docs/SCHEMA.md` (資料庫規格), `docs/FRONTEND-REDESIGN-PLAN.md` (UI/Go 重構規劃), `Prism_Go_模組逐步重構計劃報告.md` (Go shadow backend), `docs/development-history/` (完成階段與完整 Changelog 歸檔), `garbage-can/1230-審核報告.md` (Linus Audit)
**最後更新**: 2026-06-06

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

## 🎛️ Phase 22: Product Frontend Backlog Intake — ✅ Closed

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

### ✅ Settings tab deep linking

> **白話說明**：
> 這一步會真的改 Settings 分頁的使用流程：切到「資料、搜尋、部署、關於」後，網址會記住目前分頁，重新整理或直接打開該網址時會回到同一個分頁。
> 要修這個，是因為原本分頁只存在 React 本地 state，reload 會回到外觀分頁；對部署/資料維護這類低頻但重要的設定頁，網址不能保存狀態會讓操作中斷。
> 使用者會感覺到的差異是：`/settings?tab=deploy` 會直接打開部署分頁，點分頁也會更新網址；既有分頁內容、設定控制項、Sidebar/Command Palette 進入 Settings 的預設外觀分頁都照舊。
> 這一步不新增 backend API、資料庫 schema、Pi/Caddy/service、Go runtime 或 public exposure，也不新增 server-side UI preference。
> Risk level: `P1 workflow-sensitive`。這類前端 workflow 修正最多 plan gate + implementation gate；本次已由使用者明確授權，直接做單一 implementation task 並以 browser reload/click flow 驗證。

- [x] **Settings tab deep linking** — 使用者明確授權後，讓 Settings tab 由 `tab` query param 決定；有效值包含 `appearance`、`data`、`search`、`deploy`、`about`，無效或缺省時回到 `appearance`。
- [x] **URL update behavior** — 點 Settings tab 時使用 `replace` 更新目前 URL 的 `tab` query，不新增 browser history spam，也保留其他 query param。
- [x] **Verification** — 新增 `tests/test_phase22_settings_tab_deep_linking.py`；需跑 targeted pytest、`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v`，並做 browser flow：直開 `/settings?tab=deploy`、reload 後仍顯示部署分頁、點資料/關於時 URL 與 panel 同步，不新增 console error。

### ✅ Prompt Builder mobile action bar polish

> **白話說明**：
> 這一步會真的改 Prompt Builder 手機版的操作動線：手機寬度下，「儲存至筆記庫 / 重置」不再只出現在控制項最底部，而是在標題下方就能看到並跟著頁面上方停留。
> 要修這個，是因為 Prompt Builder 表單很長，手機使用者填完主要描述或前幾個設定時，原本必須一路滑到底才找得到主要動作，容易中斷操作。
> 使用者會感覺到的差異是：手機版進入 Prompt Builder 後第一屏就能看到儲存/重置；桌面版仍保留原本左側設定區底部 sticky action bar，輸出預覽、複製、AI 優化、表單欄位與輸出格式都不改。
> 這一步不新增 backend API、資料庫 schema、Pi/Caddy/service、Go runtime 或 public exposure，也不新增 AI/ML dependency、server-side UI preference 或 prompt schema。
> Risk level: `P1 workflow-sensitive`。這類前端 workflow 修正最多 plan gate + implementation gate；本次已由使用者明確授權，直接做單一 implementation task 並以 mobile/desktop browser flow 驗證。

- [x] **Mobile action availability** — 使用者明確授權後，新增 mobile-only `prompt-builder-mobile-actions` action bar；手機寬度下在 Prompt Builder header 下方可見並 sticky top。
- [x] **Desktop behavior preservation** — desktop 仍使用既有 `prompt-builder-actions` bottom sticky bar；儲存與重置 handler 仍是既有 `saveToLibrary` / `resetForm`。
- [x] **Verification** — 新增 `tests/test_phase22_prompt_builder_mobile_action_bar.py`；需跑 targeted pytest、`cd frontend && npx tsc --noEmit`、`cd frontend && npm run build`、`pytest tests/ -v`，並做 browser flow：mobile first viewport action bar 可見、scroll 後仍可操作、desktop 仍顯示原 bottom action bar，不新增 console error。

### 📌 Product Frontend Backlog Parking Lot — Plan When Needed

> **白話說明**：
> P2 不再開下一個儀式化 phase。Settings 分頁網址保存與 Prompt Builder 手機動作列已完成；後續若要繼續前端小修，需先從實際使用或 browser evidence 找下一個具體候選。
> 目前沒有已選 active frontend item；下一步先做收斂盤點，不預設開新 phase。

---

## 🧭 Phase 23: Go Refactor Roadmap Consolidation — 🚦 Active

> **來源**: `Prism_Go_模組逐步重構計劃報告.md`、`docs/ARCHITECTURE.md` Phase 19-20 runtime truth、Phase 20.4 `closed_stabilized`、使用者明確要求「直接規劃好大項最後可以本機封裝執行；實際使用仍部署在樹莓派」。
> **目標**: 把主線從 product/frontend backlog 收回 Go 漸進重構；先固定大項 roadmap、最終本機封裝目標與 Pi deployment 不變的邊界，再進下一個 Go P0 gate。
> **原則**: Go ownership / runtime / DB / file system / migration / Caddy / Pi deploy 都視為 `P0 safety-critical`；不得用 P1/P2 小修節奏直接實作。Frontend backlog 已關閉，除非使用者另行指定，不再主動尋找前端小毛病。

### ✅ 23.0 Go Refactor Roadmap Consolidation

> **白話說明**：
> 這一步只是決定/盤點/規劃，不會實作功能。
> 這段是在把專案主線重新拉回 Go 重構：最後 Prism 要能有明確的本機封裝執行路徑，但使用者日常使用仍維持部署在樹莓派、由 systemd + Caddy 管理。
> 要修這個，是因為前面 frontend backlog 已完成幾個小修，但 Go 重構才是長線主軸；如果不寫回權威文檔，後續 agent 會繼續從小 UI 候選找事做。
> 使用者不會立刻看到功能差異，因為 23.0 只改文檔；它明確規定下一步回到 Go P0 gate，而不是繼續挖 frontend polish。
> 這一步不改 Go code、不改 Python route、不改資料庫、不改 Caddy、不部署 Pi、不改 frontend default、不移除 Python、不擴大 public exposure。
> Risk level: `P0 safety-critical`。這類工作只允許 strict phase gate、explicit approval、rollback、contract、pytest lock；23.0 本身是 plan-only consolidation，下一個 implementation 前必須另行授權。

- [x] **23.0.1** Final target architecture — 固定最終方向：本機可封裝執行（single binary / bundled frontend / external data dir / explicit config），但正式使用與部署仍以 Raspberry Pi + systemd + Caddy + existing data dir 為主。
- [x] **23.0.2** Go ownership roadmap — 固定大項順序：current runtime truth → read parity completion → write surface selection → first Go write route → file/attachment ownership → migration/DB ownership decision → local packaging track → Pi deployment track → Python reduction/removal。
- [x] **23.0.3** Active next gate — 下一個 active Go step 為 `23.1 Go file-read parity plan gate`，只做 plan/contract，不直接實作 attachment body scan；原因是文字附件 body 搜尋目前仍 Python-owned，涉及 file system、path traversal、data dir、large file/performance 與 rollback。
- [x] **23.0.4** No frontend drift — Phase 22 product/frontend backlog 關閉；目前沒有已選 active frontend item。除非使用者明確指定，後續 agent 不得繼續主動找 frontend polish 當下一步。
- [x] **23.0.5** Documentation sync — 同步 `Prism_Go_模組逐步重構計劃報告.md` 與 `docs/ARCHITECTURE.md`，讓未來 agent 從 AGENTS.md 指定文檔即可讀到 Go 主線、local packaging target 與 Pi deployment unchanged boundary。

### ✅ 23.1 Go file-read parity plan gate — ✅ Completed (2026-06-05)

> **白話說明**：
> 這一步只是決定/盤點/規劃，不會實作功能。
> 它要處理的是 Go read-only surface 目前還缺的「文字附件內容搜尋」：Python 現在會在 request 期間讀 `.md` / `.markdown` / `.txt` 附件內容，Go 目前只補齊 DB 裡的附件 title / file_path metadata。
> 使用者不會在 23.1 看到功能差異；23.1 只會把 data dir、可讀副檔名、檔案大小上限、路徑穿越防護、效能界線、Python vs Go diff fixture、Pi rollback 寫清楚。
> 23.1 明確不會寫 Go file scanner、不會改 Caddy route、不會改 production DB、不會改 frontend default、不會部署 Pi、不會移除 Python。
> Risk level: `P0 safety-critical`。因為會碰 file system ownership，必須先有 contract / rollback / pytest lock，再另行授權 implementation。

- [x] **23.1.1** File-read contract — 定義 Go 可讀 data dir、允許副檔名、路徑 canonicalization、禁止 `..` / symlink escape / absolute external path、file size limit、encoding fallback 與 timeout/performance boundary。見 `docs/contracts/phase23-go-file-read-parity-plan.json`。
- [x] **23.1.2** Parity fixture plan — 設計 Python vs Go diff fixture：同一 copied DB + controlled attachment files，覆蓋 title/file_path metadata hit、body hit、missing file、oversized file、unsupported extension、path traversal attempt。
- [x] **23.1.3** Runtime boundary — 23.1 不改 `prism-go-readonly.service` query_only、不擴 Caddy matcher、不碰 production `knowledge.db`、不改 frontend default、不部署 Pi；23.2 若被授權才可做 implementation。
- **收尾驗證**：`pytest tests/test_phase23_go_file_read_parity_plan.py -v`、`pytest tests/test_phase20_go_read_surface_polish.py -v`、`pytest tests/ -v`。

### ✅ 23.2 Go file-read parity implementation gate — ✅ Completed (2026-06-05)

> **白話說明**：
> 這一步會真的讓 Go 補上「文字附件內容搜尋」能力，但只限已定義安全邊界內的 read-only file scan。
> 要修這個，是因為目前 Go 已能搜尋 DB 裡的筆記與附件 metadata，但 `.md` / `.txt` 附件內容仍只有 Python 會讀，read parity 還沒完整。
> 使用者可能感覺到的差異是：走 Go read surface 時，搜尋文字附件內容也能命中；但 UI、API 參數、資料庫 schema、Pi 部署方式不應改變。
> 這一步不改 writes、不改 upload/attachment writes、不改 Caddy matcher、不改 frontend default、不移除 Python、不部署 Pi；只做 local/copy DB + controlled files 的 Go read parity implementation。
> Risk level: `P0 safety-critical`。因為會碰 file system read ownership，必須先通過 23.1 contract、path safety tests、Python vs Go diff fixtures，失敗即 rollback 到 Python-owned gap。

- [x] **23.2.1** Go file scanner — 在 Go read-only notes search 內加入受限文字附件 body scanner；只讀 23.1 contract 允許的 data dir / extension / size。
- [x] **23.2.2** Safety tests — 新增 `tests/test_phase23_go_file_read_parity_implementation.py`，鎖住 path traversal、missing file、oversized file、unsupported extension、encoding fallback、timeout/performance guard 與 forbidden live/write scope。
- [x] **23.2.3** Python vs Go parity — `tests/test_phase18_go_shadow_contract.py` 使用同一 copied DB + controlled temp attachment files，證明 `.md` / `.markdown` / `.txt` body-only hit 與 Python response 一致。
- [x] **23.2.4** No live route expansion — 不改 production Caddy、不 reload service、不切 Pi；23.2 只完成 local/copied-DB Go read parity，不進 live candidate。
- **收尾驗證**：`gofmt -w go-shadow/main.go`、`cd go-shadow && go test ./...`、`pytest tests/test_phase23_go_file_read_parity_implementation.py -v`、`pytest tests/test_phase23_go_file_read_parity_plan.py -v`、`pytest tests/test_phase18_go_shadow_contract.py -v`、`pytest tests/ -v`。

### ✅ 23.3 Go write surface selection gate — ✅ Completed (2026-06-05)

> **白話說明**：
> 這一步只是決定/盤點/規劃，不會實作功能。
> 它要從所有 DB 寫入功能中選第一個最小、可回滾、最不容易牽連檔案系統的 Go write route。
> 使用者不會看到功能差異；這一步只會決定第一個要交給 Go 的寫入候選，並把 transaction、CSRF/local-only、rollback、Python fallback 寫清楚。
> 這一步不會寫 Go write code、不會改 production DB、不會改 Caddy、不會部署 Pi、不會改 frontend default、不會移除 Python、不碰 upload/attachments/files。
> Risk level: `P0 safety-critical`。所有 write ownership 都必須先有 side-effect map、rollback、contract、pytest lock。

- [x] **23.3.1** Candidate matrix — 重新評估 notes create/update/delete、pin/archive、duplicate、reorder、categories CUD、tags CUD/merge、attachments/uploads/cleanup/import/export/system/server/config；拒絕 filesystem-coupled、cascade、bulk、process/config 或 route-expansion-heavy candidate。見 `docs/contracts/phase23-go-write-surface-selection.json`。
- [x] **23.3.2** First write recommendation — 選定 `PUT /api/tags/<tag_id>` (`tag_rename`) 作為 23.4 第一個 candidate：single-purpose、DB-only、只更新 `Tags.name`、transaction 清楚、Python parity 容易驗證。
- [x] **23.3.3** Write contract — 固定 request/response schema、transaction semantics、CSRF/local-only behavior、Python fallback/rollback、failure stop conditions；23.3 不授權 Go write implementation、production DB、Caddy/service、Pi deploy、frontend default、Python removal 或 public exposure。
- **收尾驗證**：`pytest tests/test_phase23_go_write_surface_selection.py -v`、`pytest tests/test_phase23_go_file_read_parity_implementation.py -v`、`pytest tests/ -v`。

### ✅ 23.4 First Go write route implementation gate — ✅ Completed (2026-06-05)

> **白話說明**：
> 這一步會真的讓 Go 接手第一個小型 DB 寫入 route。
> 要修這個，是因為 Go 不能永遠停在 read-only；但第一個 write 必須非常小，先證明 transaction、錯誤處理、rollback 與 Python parity 都可控。
> 使用者理論上不應感覺到 API 或 UI 差異；同一個操作只是後端 owner 逐步從 Python 轉到 Go。
> 這一步不碰 upload、attachments、cleanup、import/export、migrations、Caddy route expansion、frontend default、Python removal。
> Risk level: `P0 safety-critical`。只允許 23.3 選出的 single route；不得順手多搬其他 writes。

- [x] **23.4.1** Implement selected write — 在 Go local/copied-DB candidate 中實作 flag-gated `PUT /api/tags/<tag_id>`；需明確使用 `--enable-tag-write` / `PRISM_GO_ENABLE_TAG_WRITE=1` 才會進入 `get-read-only+local-tag-write`。預設 Go runtime 仍是 `get-read-only` + SQLite `query_only`。
- [x] **23.4.2** Transaction and rollback tests — 新增 `tests/test_phase23_go_first_write_route_implementation.py`，覆蓋 success/trimmed name、missing body/name、empty name、missing tag id 404、duplicate 409、rollback/no partial write、`Note_Tags` 不變、Python vs Go response + DB-state parity。Duplicate parity 依目前 Python `routes/tags.py` exact-name 查詢；`docs/SCHEMA.md` 的 NOCASE wording discrepancy 先記為 23.5 前需處理/明確延後的風險，不在 23.4 擴成 schema 修正。
- [x] **23.4.3** Local/Pi gate split — 23.4 未改 Caddy、未 reload service、未碰 production DB、未部署 Pi、未改 frontend default、未移除 Python；local parity 通過後，另開 Pi/live routing gate 才能討論 live route。見 `docs/contracts/phase23-go-first-write-route-implementation.json`。
- **收尾驗證**：`gofmt -w go-shadow/main.go go-shadow/main_test.go`、`cd go-shadow && go test ./...`、`pytest tests/test_phase23_go_first_write_route_implementation.py -v`、`pytest tests/test_phase23_go_write_surface_selection.py -v`、`pytest tests/test_phase18_go_shadow_contract.py -v`、`pytest tests/ -v`。

### ✅ 23.5 Go DB-only write expansion gate — ✅ Completed (2026-06-05)

> **白話說明**：
> 這一步先不實作新的 Go write，而是決定第一個 write 成功後怎麼安全擴張。
> 要處理的重點有三個：23.4 tag rename 只算 local/copied-DB proof、`Tags.name` NOCASE 文件/schema/runtime 差異不能混進 tag CUD、下一個 DB-only route class 只能選一個。
> 使用者不會看到功能差異；這一步只會把 live gate、schema discrepancy、下一個 candidate 與測試邊界寫清楚。
> 這一步不改 Go/Python runtime、不改 schema、不改 Caddy/service、不部署 Pi、不改 frontend default、不移除 Python。
> Risk level: `P0 safety-critical`。DB writes 只能一批一個 route class，且每批都要有 request/response parity、transaction rollback 與 stop conditions。

- [x] **23.5.1** Stabilization decision — 決議不在擴下一個 local/copied-DB DB-only write 前先做 live tag rename gate；23.4 `PUT /api/tags/<tag_id>` 仍只是 `--enable-tag-write` / copied-DB candidate，live owner 仍是 Python。
- [x] **23.5.2** Schema/doc discrepancy gate — `Tags.name` NOCASE discrepancy 本輪明確延後，不做 schema migration、不改 Python/Go duplicate semantics、不改 `docs/SCHEMA.md` 宣稱 runtime 已修正；tag delete / tag merge / broader tag CUD expansion 在 dedicated gate 前保持 blocked。
- [x] **23.5.3** Next DB-only candidate selection — 選定 `PUT /api/categories/<category_id>` 作為下一個 DB-only implementation subgate；它是 top-level DB-only 單列 update，避開 nested `/api/notes/...` matcher 與 tag NOCASE discrepancy。`POST /api/categories`、pin/archive、tag delete/merge、duplicate/reorder/batch 全部延後或拒絕。
- [x] **23.5.4** Contract locks — 新增 `docs/contracts/phase23-go-db-only-write-expansion-selection.json` 與 `tests/test_phase23_go_db_only_write_expansion_selection.py`，固定 plan-only、no live/schema/runtime change、下一步 category update scope、rollback/parity fixture plan。
- **收尾驗證**：`pytest tests/test_phase23_go_db_only_write_expansion_selection.py -v`、`pytest tests/test_phase23_go_first_write_route_implementation.py tests/test_phase23_go_write_surface_selection.py tests/test_phase23_go_file_read_parity_implementation.py -v`、`pytest tests/ -v`。

### ✅ 23.5 Next DB-only write implementation subgate — ✅ Completed (2026-06-05)

> **白話說明**：
> 這一步才會真的實作第二個 Go DB-only write candidate。
> 選定的是 `PUT /api/categories/<category_id>`，因為它只更新既有分類 row，不建立新 identity、不碰檔案、不牽涉 tag NOCASE 差異，也不需要先擴 nested `/api/notes/...` live matcher。
> 使用者不應看到功能差異；同一個分類更新 API 只是在 local/copied-DB candidate 中補 Go parity。
> 這一步仍不授權 live route、production DB、Caddy/service、Pi deploy、schema migration、tag CUD、notes actions 或 file ownership。
> Risk level: `P0 safety-critical`。實作必須 flag-gated，預設 Go runtime 保持 GET read-only + SQLite `query_only`。

- [x] **23.5-next.1** Implement selected write — 只做 local/copied-DB `PUT /api/categories/<category_id>`，以 `--enable-category-write` / `PRISM_GO_ENABLE_CATEGORY_WRITE=1` 啟用；預設 Go runtime 仍是 GET read-only + SQLite `query_only`，且未授權 live route。見 `docs/contracts/phase23-go-category-update-write-implementation.json`。
- [x] **23.5-next.2** Category update parity hardening and empty-name contract decision — 決議修正 Python + Go：`name: "   "` 現在回 400 `Category name cannot be empty`，避免分類名稱寫成空字串；不保留 23.5-next.1 發現的舊 runtime gap。
- [x] **23.5-next.3** Transaction / rollback lock — 驗證每次成功只更新目標 `Categories` row，`Notes.category_id` 不變；missing body、missing category、duplicate name、empty name、disabled Go flag 都不改 `Categories` snapshot。
- [x] **23.5-next.4** Boundary lock — 不改 live Caddy/systemd/frontend default、不碰 production DB、不部署 Pi、不做 schema migration、不處理 tag CUD、不擴 nested `/api/notes/...` action route；見 `docs/contracts/phase23-go-category-update-closure.json`。
- **收尾驗證**：`gofmt -w go-shadow/main.go go-shadow/main_test.go`、`cd go-shadow && go test ./...`、`pytest tests/test_categories.py::TestCategoriesAPI::test_update_category_rejects_empty_trimmed_name -v`、`pytest tests/test_phase23_go_category_update_write_implementation.py -v`、`pytest tests/test_phase23_go_db_only_write_expansion_selection.py -v`、`pytest tests/ -v`。

### ✅ 23.5-next.2 Category update parity hardening and empty-name contract decision — ✅ Completed (2026-06-05)

> **白話說明**：
> 這一步不是擴更多 route，而是處理 23.5-next.1 實作時發現的 contract 差異。
> Python 目前的分類更新沒有禁止空白名稱；如果送 `name: "   "`，會 trim 成空字串並寫入 DB。23.5 原本計劃文字期待 empty name 400，但那不是目前 runtime truth。
> 決議是同時修改 Python + Go validation，讓 empty name 回 400。
> 這一步仍不授權 live route、Caddy/service、production DB、Pi deploy、tag CUD、notes actions 或 file ownership。

- [x] **23.5-next.2.1** Runtime truth decision — 不保留 current empty-name behavior；修 Python + Go 一起禁止 empty category name。
- [x] **23.5-next.2.2** Contract/doc sync — 已同步 `docs/contracts/phase23-go-db-only-write-expansion-selection.json`、`docs/contracts/phase23-go-category-update-write-implementation.json`、`docs/TODO.md` 與相關 pytest 斷言。
- [x] **23.5-next.2.3** Regression lock — 新增 Python category update regression，Go parity fixture 也覆蓋 empty name 400 與 DB snapshot 不變。
- [x] **23.5-next.2.4** No scope expansion — 未新增 category create/delete、notes actions、tag CUD、file routes 或 live routing。

### ✅ 23.6 File / attachment ownership gate — ✅ Completed (2026-06-06)

> **白話說明**：
> 這一步已先完成 ownership inventory 和第一個候選 selection，沒有實作 Go file route。
> Inventory 分拆 attachments metadata/body、upload、cleanup、notes delete image cleanup、export/import、server backup/logs，逐一標出 DB/file side effects、data root、defer reason。
> 第一個候選選定 `GET /api/attachments/<attachment_id>` 的 text JSON branch：只讀 copied DB + copied `docs/attachments` 文字附件，不處理 raw/binary、upload、delete、cleanup、import/export。
> Backup/restore contract 明確規定：read-only candidate 必須證明 DB bytes 與 attachment file bytes 不變；任何 file write/delete candidate 都要另開 dedicated DB + filesystem backup/restore + partial failure rollback gate。
> Risk level: `P0 safety-critical`。這是整個 Go 重構最高風險群之一。

- [x] **23.6.1** File ownership inventory — 已分拆 upload、attachments metadata/body、cleanup、notes delete image cleanup、export/import、server backup/logs；逐一標 side effects、data-dir、rollback/defer reason。見 `docs/contracts/phase23-go-file-attachment-ownership-gate.json`。
- [x] **23.6.2** First file route selection — 已選 `attachment_text_content_read` 作為唯一 23.6-next candidate；不得同時處理 upload + cleanup + export。
- [x] **23.6.3** Backup/restore proof — 已定義 read-only candidate 的 copied DB/files no-mutation proof；file write/delete candidates 在 dedicated backup/restore/partial-failure rollback gate 前 blocked。

### ✅ 23.6-next First Go file-read route implementation candidate — ✅ Completed (2026-06-06)

> **白話說明**：
> 這一步已實作第一個 Go file-read candidate，但 scope 很窄。
> 只完成 local/copied-DB-and-files parity for `GET /api/attachments/<attachment_id>` text JSON branch；Go 需用 `--enable-attachment-text-read` / `PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ=1` 才啟用，且仍維持 SQLite `query_only`。
> Python vs Go fixture 已覆蓋 UTF-8 text attachment、missing attachment id；Go safety fixture 另覆蓋 missing file、unsafe path、unsupported extension、raw branch blocked、default disabled。
> 不處理 `raw=true`、binary response、attachment upload/delete、separate/restore、upload images、cleanup、import/export、server backup/logs、live routing、production DB/files、Pi deploy、schema、Python removal 或 public exposure。
> Risk level: `P0 safety-critical`。

- [x] **23.6-next.1** Fixture setup — 建 copied DB + copied `docs/attachments` fixture，覆蓋 UTF-8 text attachment、missing attachment id、missing file、unsafe path、unsupported extension。
- [x] **23.6-next.2** Go local candidate — 只在 explicit local flag/env 下啟用 text JSON branch；default Go runtime 不變。見 `docs/contracts/phase23-go-attachment-text-read-implementation.json`。
- [x] **23.6-next.3** No-mutation proof — 成功/失敗 cases 都證明 DB bytes、attachment file bytes、uploads tree 不變。
- [x] **23.6-next.4** Boundary lock — `raw=true`、binary/send_file、upload/delete、cleanup、import/export、server backup/logs、live route、Pi deploy、Python removal 全部保持 blocked。
- **收尾驗證**：`gofmt -w go-shadow/main.go go-shadow/main_test.go`、`cd go-shadow && go test ./...`、`pytest tests/test_phase23_go_attachment_text_read_implementation.py -v`、`pytest tests/test_phase23_go_file_attachment_ownership_gate.py -v`、`pytest tests/test_phase23_go_file_read_parity_implementation.py -v`、`pytest tests/ -v`。

### ✅ 23.7 Migration / DB ownership decision gate — ✅ Completed (2026-06-06)

> **白話說明**：
> 這一步只是決定 migration 最後由誰負責，沒有改 production migration。
> 決策是：normal/live migration runner 繼續 Python-owned；Go 目前只讀 `Schema_Meta` 做 health/schema version check。
> `go_status_only` 可以成為未來本機封裝 / copied DB readiness candidate，但只能讀狀態，不寫 `Schema_Meta`、不跑 DDL/DML。
> `go_full_migration_runner` 延後，直到 idempotency、fresh/upgraded DB fixture、failed migration rollback、backup/restore、Pi preflight 全部有 dedicated proof。
> 使用者不會看到功能差異；這是啟動與升級安全邊界。
> 這一步未直接跑 production migration、未改正式 DB、未移除 Python migration。
> Risk level: `P0 safety-critical`。migration 只能在 idempotent tests、fresh backup、rollback 與 Pi preflight 完整後才可 implementation。

- [x] **23.7.1** Migration ownership options — 已比較 retained Python migrations、Go status-only、Go full migration runner 三種方案；選定 retained Python migrations 作為 normal/live owner。
- [x] **23.7.2** Schema safety contract — 已固定 idempotency、`Schema_Meta` version table、pending detection、backup、rollback、failed migration recovery。見 `docs/contracts/phase23-go-migration-db-ownership-decision.json`。
- [x] **23.7.3** Decision checkpoint — 未達成 full safety proof 前，migrations 保持 Python-owned；Go full runner blocked，Python removal blocked。
- **收尾驗證**：`pytest tests/test_phase23_go_migration_db_ownership_decision.py -v`、`pytest tests/test_schema_regression.py -v`、`pytest tests/test_system.py::test_migration_status -v`、`pytest tests/ -v`。

### ✅ 23.8 Local packaging execution track — ✅ Completed (2026-06-06)

> **白話說明**：
> 這一步會建立本機封裝執行路徑：讓 Windows / local dev 可以用明確 artifact 跑 Prism。
> 要修這個，是因為最後你希望能本機封裝執行；但它不是取代 Pi 使用方式，而是讓 runtime 更完整、更容易測試與發布。
> 使用者會看到的差異是本機啟動方式更清楚；Pi 日常部署仍不變。
> 這一步不改 Pi deployment default、不改 production Caddy、不改資料位置、不把本機 artifact 當正式 Pi rollout。
> Risk level: `P1 workflow-sensitive` for local launcher/build flow；若封裝碰 DB/data-dir/runtime ownership，該部分升級為 `P0 safety-critical`。

- [x] **23.8.1** Packaging contract + thumbnail ownership plan — 已定義 Go binary、bundled frontend `dist`、external data dir、config file/env、logs、uploads path、SQLite WAL behavior；migration owner 依 23.7 保持 Python-owned，Go status-only 只能作 local/readiness candidate。另把「去掉 Pillow、改由 Go 引入 WebP encoder 接管縮圖」納入 `23.8-thumb` 後續規劃：本輪不移除 Pillow、不新增 Go encoder、不改 upload/import runtime。見 `docs/contracts/phase23-go-local-packaging-thumbnail-plan.json`。
- [x] **23.8.2** Local smoke artifact — 已新增 `scripts/smoke_go_local_artifact.ps1`，建立 Windows/local Go artifact smoke：執行 `scripts/build_go_runtime.ps1` 產生 `build/go-runtime/prism-go-runtime.exe`，用 `build/go-local-smoke/data/` 內的 copied DB 啟動本機 runtime，驗 `/healthz`、embedded SPA、`/api/test`、categories、tags、notes read smoke，並確認預設 runtime 維持 `sqlite_query_only=true` 且 write candidate route 預設 405；另以 copied write DB 啟用 `--enable-tag-write` / `--enable-category-write` 驗 DB-only write smoke，source `knowledge.db` SHA256 不變。見 `docs/contracts/phase23-go-local-smoke-artifact-release-boundary.json`。
- [x] **23.8.3** Release boundary — 已固定本機封裝可用不代表 Pi 已更新；本輪未部署 Pi、未改 Caddy/systemd、未寫 production DB/files、未改 frontend default、未移除 Python。Pi rollout 仍走 23.9，下一步只能先做 23.9.1 Pi preflight 並需另行明確授權。
- **收尾驗證**：`powershell -ExecutionPolicy Bypass -File scripts/smoke_go_local_artifact.ps1`、`pytest tests/test_phase23_go_local_smoke_artifact_release_boundary.py -v`、`pytest tests/test_phase23_go_local_packaging_thumbnail_plan.py -v`、`pytest tests/ -v`。

### ⏭️ 23.8-thumb Go WebP thumbnail ownership / Pillow removal track — Local Candidate Complete, Removal Still Blocked

> **白話說明**：
> 這一步處理縮圖 owner：目前 Python upload / upload-url / import helper 以可選 Pillow 產生 `_thumb.webp`。
> 目標是未來改由 Go thumbnail candidate 接管 WebP encoding，最後才移除 Pillow。
> 使用者看到的行為必須維持：支援 jpg/png/webp/gif 上傳、縮圖最大寬 500px、`_thumb.webp` 命名、`thumbnail_only` 成功時只回縮圖 URL、刪除/cleanup 仍能找到對應縮圖。
> 這一步不是 23.8.1 的實作內容；移除 Pillow 前必須先做 encoder dependency 決策、parity fixtures、docs/start script/requirements 一次同步。
> Risk level: `P0 safety-critical` for file mutation and dependency/runtime packaging compatibility。

- [x] **23.8-thumb.1** WebP encoder dependency decision — 已選 `github.com/skrashevich/go-webp` 作為 first spike candidate only：純 Go、Apache-2.0、支援 lossy/lossless 與 quality 0-100，符合目前 Pillow `quality=80` 縮圖語意的第一候選；local probe 驗 Windows `go run` / Windows build / `GOOS=linux GOARCH=arm64 CGO_ENABLED=0` cross-build 皆通過。拒絕 `golang.org/x/image/webp`（decode-only）、`github.com/chai2010/webp` 與 `github.com/kolesa-team/go-webp`（cgo/libwebp/GCC/MinGW/toolchain 風險）；`github.com/HugoSmits86/nativewebp` 保留為 fallback/secondary spike，因其目前偏 lossless-only，不是 `quality=80` lossy parity 第一選。見 `docs/contracts/phase23-go-webp-encoder-dependency-decision.json`。本輪未把 dependency 加進 `go-shadow/go.mod`、未移除 Pillow、未改 upload/import runtime、未部署 Pi。
- [x] **23.8-thumb.2** Thumbnail parity fixtures — 已新增 runtime parity fixtures，鎖住 `POST /api/upload` 對 jpg/png/webp/gif 產生 `_thumb.webp`、縮圖 WebP/max-width 500、`thumbnail_only=true` 成功時只保留縮圖、Pillow/thumbnail unavailable 時保留原圖 fallback；鎖 `POST /api/upload/url` remote image thumbnail-only 成功行為；鎖 import image helper 成功產生縮圖與失敗保留原圖；鎖 `/api/upload/delete` 刪原圖時同步刪 `_thumb.webp`、orphan cleanup 視被引用原圖的 `_thumb.webp` 為 referenced companion。見 `docs/contracts/phase23-go-thumbnail-parity-fixtures.json` 與 `tests/test_phase23_go_thumbnail_parity_and_pillow_removal_gate.py`。
- [x] **23.8-thumb.3** Pillow removal gate — 已執行 removal gate，結論為 blocked-removal / retain Pillow：dependency decision 與 parity fixtures 已完成，但尚無 Go thumbnail implementation candidate、尚無含 `github.com/skrashevich/go-webp` 的 real `go-shadow` packaging smoke、也尚未證明 Python fallback/removal strategy。因此本輪未移除 `requirements.txt` Pillow、未改 `scripts/start.bat` Pillow check、未移除 Python PIL import/fallback wording、未改 `docs/API_REFERENCE.md` 或 `docs/SEQUENCE-UPLOAD.md` 的 runtime owner。見 `docs/contracts/phase23-go-pillow-removal-gate.json`。
- [x] **23.8-thumb.4** Go thumbnail local implementation candidate — 已把 `github.com/skrashevich/go-webp v0.1.0` 加入 `go-shadow`，新增 `--enable-thumbnail-write` / `PRISM_GO_ENABLE_THUMBNAIL_WRITE` 的 local/copied-data `POST /api/upload` candidate；預設仍 405 disabled，啟用後只寫 `PRISM_GO_DATA_DIR/static/uploads`，DB 維持 `sqlite_query_only=true`，`thumbnail_only=true` 成功時只落 `_thumb.webp`，標準 upload 落原圖與 `_thumb.webp`。本輪未移除 Pillow、未改 Python upload-url/import helper/delete/cleanup owner、未部署 Pi、未改 Caddy/systemd/frontend default。`go-shadow` 現需 Go `1.26.1+` build。見 `docs/contracts/phase23-go-thumbnail-local-candidate.json`。
- [x] **23.8-thumb.5** Go thumbnail surface expansion or removal-readiness gate — 已完成 decision gate，結論為 blocked-expansion / retain Python：23.8-thumb.4 只證明 local/copied-data multipart `POST /api/upload` candidate；`POST /api/upload/url` 涉及 SSRF、remote request timeout/header、Content-Type/magic、下載大小上限與 thumbnail fallback，import helper 又牽涉 Markdown import workflow 與 tuple compatibility，因此本輪不新增 Go `upload/url` 或 import helper、不移除 Pillow、不改 SSRF/remote fetch policy、不部署 Pi。見 `docs/contracts/phase23-go-thumbnail-surface-expansion-gate.json`。
- [x] **23.8-thumb.6** Go upload-url remote-fetch safety parity plan — 已完成 plan-only safety/parity contract：未改 runtime，先鎖 `POST /api/upload/url` 現行 Python contract（JSON `url`/`thumbnail_only`、http/https、SSRF、timeout/header、Content-Type、magic、size cap、filename、thumbnail_only 成功/失敗 fallback）與未來 Go candidate 必備條件。Go candidate 必須另用 `--enable-upload-url-write` / `PRISM_GO_ENABLE_UPLOAD_URL_WRITE`，預設 405 disabled，只寫 copied data dir，DB 維持 `sqlite_query_only=true`，並驗 redirect target、streaming size cap、failure no-mutation。見 `docs/contracts/phase23-go-upload-url-remote-fetch-safety-parity-plan.json`。
- [ ] **23.8-thumb.7** Go upload-url local implementation candidate — 下一步若授權，才可依 23.8-thumb.6 實作 disabled-by-default copied-data `POST /api/upload/url` Go candidate；仍不得移除 Pillow、不得接 Pi/Caddy/frontend default、不得改 import helper/delete/cleanup owner。
- **收尾驗證**：`cd go-shadow && go test ./...`、`pytest tests/test_phase23_go_upload_url_remote_fetch_safety_parity_plan.py -v`、`pytest tests/test_phase23_go_thumbnail_surface_expansion_gate.py tests/test_security_guards.py -v`、Phase 23 regression set、`pytest tests/ -v`。

### ✅ 23.9 Pi deployment rollout track — ✅ Completed (2026-06-06)

> **白話說明**：
> 這一步處理真正使用環境：樹莓派部署。
> 要修這個，是因為你日常使用仍維持 Pi + systemd + Caddy；任何 Go ownership 擴大後，都要能在 Pi 上用實際 service、Caddy、DB、uploads 驗證。
> 使用者會看到的差異應該是服務仍照常可用；若出問題必須能快速 rollback 到前一個 Python/Go ownership 狀態。
> 這一步不會跳過 local parity，也不會把未驗證的 Go writes/files/migrations 直接推到 Pi。
> Risk level: `P0 safety-critical`。

- [x] **23.9.1** Pi preflight — 已在 `PI5Mask24` 驗 `prism.service` / Caddy active+enabled、`caddy validate` passed、migration current/latest v16 pending `[]`、route ownership 仍 Python default；建立 rollback evidence：DB backup `/home/mask070924/prism/backups/prism_pre_23_9_rollout_20260606_015426.db`、data snapshot `/home/mask070924/prism/backups/prism_pre_23_9_data_snapshot_20260606_015426.tar.gz`、Caddy backup `/home/mask070924/prism/backups/Caddyfile.prism-pre-23-9-rollout-20260606_015426.bak`。見 `docs/contracts/phase23-go-pi-deployment-rollout.json`。
- [x] **23.9.2** Caddy/systemd rollout — 以 tar-over-SSH 同步目前 worktree 到 `/home/mask070924/prism/`，排除 `knowledge.db`、WAL/SHM、`static/uploads`、`docs/attachments`、`.port_config`、`.env*`、logs、build/local artifacts；重啟既有 `prism.service`。本輪沒有改 Caddyfile、沒有 reload Caddy、沒有改 systemd unit、沒有啟用新的 Go route ownership。
- [x] **23.9.3** Live verification — live 驗 `/api/test` status ok notes 198 / categories 6 / tags 128、`/api/server/version` v2.4.9 Linux V2 mode true、migration current/latest v16 pending `[]`、`/api/system/go-read-routing` enabled false / default_owner python、`/api/notes?per_page=1` success total 198；headers 無 `X-Prism-Go-Read-Routing`，journal 顯示 v16 最新與 port 5000，未見新 write/error。
- **收尾驗證**：Pi live preflight + backup/snapshot + tar sync + service restart + live API/header/journal checks；local `pytest tests/test_phase23_go_pi_deployment_rollout.py -v`、`pytest tests/ -v`、`git diff --check`。

### ⏭️ 23.10 Python reduction and final stabilization — Final Stage Only

> **白話說明**：
> 這一步才是最後收尾：決定 Python 還剩什麼、能不能移除、以及最終 Go runtime 是否完整。
> 要最後才做，是因為 Python 現在仍是很多高風險功能的 owner；過早移除會讓 rollback 和資料安全都失去保護。
> 使用者最後會看到的是更單純的 runtime / packaging / Pi deployment，但功能與資料必須保持一致。
> 這一步不會在 writes/files/migrations/import/export 全部有 Go ownership 或明確 retained-Python 決策前開始。
> Risk level: `P0 safety-critical`。

- [x] **23.10.1** Ownership closure audit — 已完成 plan-only ownership closure audit；列出 Go implemented/local candidates、retained Python-owned live surfaces、deprecated/removed surfaces。結論：23.9 後 live primary runtime 仍是 Python `prism.service`；Go 只有 bounded read/local candidate/local artifact 能力；writes、files/uploads/attachments/cleanup/import/export、system/server/config、migrations、live static serving 與 rollback owner 仍 retained Python-owned。Python removal 仍 blocked。見 `docs/contracts/phase23-go-ownership-closure-audit.json`。
- [x] **23.10.2** Python removal decision — 已完成 plan-only decision：不移除 Python，normal runtime path 明確保留 Python `prism.service`。23.10.1 顯示 critical surfaces 尚未全數 Go-owned；因此 retained Python 是正式 release strategy，不是暫時遺漏。見 `docs/contracts/phase23-python-removal-decision.json`。
- [x] **23.10.3** Final stabilization window — 已完成 retained-Python final state stabilization：本機通過 frontend typecheck/build、Go local artifact smoke、local API smoke、Playwright browser screenshot smoke；Pi 在 `PI5Mask24` 建立 DB/data/Caddy backups 後，以 tar-over-SSH 同步 current worktree（排除 production DB/uploads/attachments/env/log/build），重啟既有 `prism.service`，live 驗 service/Caddy active、Caddy validate、version 2.4.9、migration v16 clean、Go routing disabled/Python owner、notes total 198、headers 無 Go routing header、journal restart 後無新錯誤。見 `docs/contracts/phase23-final-stabilization.json`。

### ⏸️ Phase 19.0 不處理

- 正式替換 Flask route 或讓前端改打 Go。
- POST / PUT / DELETE。
- Production `knowledge.db` 寫入、migration 執行或自動修復。
- Attachments、export、cleanup、`/api/server/*`。
- 移除 Python backend、venv 或現有 Pi `prism.service`。

---

## ✅ Phase 24: Settings and Home Maintenance Follow-up

> **白話說明**：
> 這一步回應使用者實際檢查 Settings / Home 後列出的 9 個小問題。
> 目標不是重開前端改版或 Go runtime，而是把已存在的資料維護、匯出、備份、部署設定、關於與首頁文字擺位修到符合目前 runtime truth。
> 使用者會看到的差異是：Markdown zip 會連本機圖片一起打包、分類數字對齊、端口/更新/維護區文案更清楚、備份可單筆刪除、本機封裝/非 systemd 環境隱藏服務管理、About 顯示目前版本與資料保留邊界、首頁「所有筆記，依更新時間排序」移到「全部」右側。
> 24.0.1-24.0.8 不改 Go runtime、不改 Pi/Caddy/systemd、不改 production DB/schema、不改 frontend default API target、不移除 Python、不擴大 public exposure；24.0.9 只把已驗證的 UI/API 修補同步到既有 Pi Python `prism.service`，不改 Caddy route、systemd unit、Go route ownership、production data 或 public exposure。
> Risk level: `P1 workflow-sensitive`，因為含匯出 zip 與備份刪除 API；以 targeted backend tests、frontend typecheck/build、full pytest 收尾。

- [x] **24.0.1** Database maintenance copy — 保留 WAL checkpoint 與資料一致性檢查，改標示為進階維護/疑難排解工具；日常使用不需手動操作。
- [x] **24.0.2** Markdown zip image bundle — `GET /api/export/markdown` 會把筆記內容與封面引用的本機 `/static/uploads/...` 圖片包進 `images/`，並改寫 Markdown/HTML image references。
- [x] **24.0.3** Category count alignment — 分類管理的 count 使用固定寬度、右對齊與 tabular numbers，避免右側數字漂移。
- [x] **24.0.4** Port and update guidance — 端口設定顯示目前可用 URL，說明 UI 已連不上時需改 `.port_config` / 啟動參數後重啟；版本更新說明本機以覆蓋程式檔為主、保留資料目錄，不使用補丁檔流程。
- [x] **24.0.5** Specific backup delete — 新增 `DELETE /api/server/backup/<filename>`，只允許 managed `prism_backup_*.db`，Settings 備份列表可單筆刪除；輪換備份文案改為只承諾「輪換」會保留最近 3 份。
- [x] **24.0.6** Local service management visibility — `/api/server/hardware` 回報 `service_management.available`；前端只有 Linux/systemd 且非 packaged executable 時顯示「服務管理」。
- [x] **24.0.7** About and Home polish — About 更新為目前版本與資料保留邊界；Home section subtitle 與 title 同列，降低卡片區上方空白。
- [x] **24.0.8** No Go/Pi runtime expansion — 24.0.1-24.0.8 local work 未部署 Pi、未 reload Caddy/systemd、未擴 Go route ownership、未寫 production DB/files、未改 frontend default、未移除 Python；授權後的 Pi sync/live verification 另列於 24.0.9。
- [x] **24.0.9** Pi sync + live verification — 已將 24.0 UI/API 修補同步到 `PI5Mask24` 既有 Python `prism.service`，payload 只含 `routes/export.py`、`routes/server.py`、`frontend/dist` 與 `docs/TODO.md`，保守排除 production DB/uploads/attachments/env/log/build artifacts。Pi live 驗證：pre-sync DB backup `backups/prism_pre_phase24_ui_api_sync_20260606_040042.db`；`prism.service` active/enabled，Caddy active/enabled 且 validate OK；`/api/test` OK；`/api/server/version` 回報 `2.4.9` / Linux / V2；migration current/latest `16` 且 pending 空；Markdown export zip 回傳 198 份 Markdown、707 張 images；同源 `DELETE /api/server/backup/<filename>` 200 且 probe 檔案已刪；served SPA asset 為 `/assets/index-Yr66qWVs.js` 且包含 Phase 24 copy。本輪未改 Caddy route、systemd unit、Go route ownership、production data 或 public exposure。
- [x] **24.0.10** Category count column alignment follow-up — 使用者截圖確認 24.0.3 仍未真正對齊：預設分類少一個刪除按鈕時，count badge 會被 action button 欄位寬度差異推動。修正為固定 `category-count` 欄 (`w-12 shrink-0`) 與固定 `category-actions` 欄 (`w-16 shrink-0`)，預設分類補 invisible action slot，讓每列 count badge 的左右座標一致；本機 Playwright 驗證 Settings 搜尋頁所有 count badge `left=933`、`right=981`。已同步 `frontend/dist` 與 `docs/TODO.md` 到 `PI5Mask24`，Pi live Playwright 於 `https://prism.local/settings?tab=search` 量到使用者截圖資料列 `33/49/6/35/1/74` 的 count badge 全部 `left=933`、`right=981`，console 無 error/warning。

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
| **frontend-product** | 2026-06-06 | Phase 24 category count alignment follow-up — 使用者截圖指出分類 count 還沒對齊後，將分類列改成固定 count 欄與固定 actions 欄；預設分類缺少刪除按鈕時保留 invisible action slot，避免 badge 因 action width 不同左右漂移。本機驗證 `npx tsc --noEmit`、`npm run build`、Phase 24 targeted tests passed；Playwright rendered check 於 `http://127.0.0.1:5000/settings?tab=search` 量到所有 `[data-testid="category-count"]` left/right 完全一致 (`933`/`981`)。已同步 `frontend/dist` 與 `docs/TODO.md` 到 `PI5Mask24`；Pi live Playwright 於 `https://prism.local/settings?tab=search` 量到使用者截圖資料列 `33/49/6/35/1/74` 全部 count badge left/right 一致 (`933`/`981`)，console 無 error/warning，`prism.service` 與 Caddy 仍 active/enabled。本輪未改 backend、Caddy route、systemd unit、Go route ownership、production data 或 public exposure。 |
| **pi-deploy** | 2026-06-06 | Phase 24 Pi sync + live verification — 將 Settings/Home UI/API 修補以最小 payload 同步到 `PI5Mask24` 既有 Python `prism.service`：只更新 `routes/export.py`、`routes/server.py`、`frontend/dist` 與 `docs/TODO.md`，先備份 live DB 到 `backups/prism_pre_phase24_ui_api_sync_20260606_040042.db`，排除 production DB/uploads/attachments/env/log/build artifacts。重啟後驗 `prism.service` active/enabled、Caddy active/enabled 與 validate OK、`/api/test` OK、`/api/server/version` = `2.4.9` / Linux / V2、migration v16 pending 空、Markdown export zip 含 198 份 Markdown 與 707 張 `images/`、同源 backup delete 200 且 probe 已刪、SPA asset `/assets/index-Yr66qWVs.js` 含 Phase 24 port/About copy。本輪未改 Caddy route、systemd unit、Go route ownership、production data 或 public exposure。 |
| **frontend-product** | 2026-06-06 | Phase 24 Settings/Home maintenance follow-up — 完成 Settings / Home 使用檢查後的 9 點修補：資料庫維護標示為進階工具；Markdown zip 匯出會連本機 `/static/uploads/...` 圖片一起打包到 `images/` 並改寫引用；分類 count 右對齊；端口設定顯示目前 URL 並說明 `.port_config` / 自動備用限制；版本更新改成覆蓋程式檔、保留資料目錄的說明；備份列表新增 specific backup delete，並修正文案避免把一鍵下載誤寫成會自動清理；服務管理只在 Linux/systemd 非 packaged executable 可用時顯示；About 更新目前版本與資料保留邊界；Home subtitle 移到 title 右側。24.0.1-24.0.8 local work 未部署 Pi、未 reload Caddy/systemd、未擴 Go route ownership、未寫 production DB/files、未改 frontend default、未移除 Python或擴 public exposure；Pi sync/live verification 另見上方 `pi-deploy` 摘要。 |
| **go-roadmap** | 2026-06-06 | Phase 23.8-thumb.4 Go thumbnail local implementation candidate — 在明確授權後新增 flag-gated local/copied-data Go thumbnail candidate：`go-shadow` 加入 `github.com/skrashevich/go-webp v0.1.0`，`go.mod` Go directive 升至 `1.26.1`，新增 `--enable-thumbnail-write` / `PRISM_GO_ENABLE_THUMBNAIL_WRITE` 的 `POST /api/upload`；預設 disabled 405，啟用後寫 `PRISM_GO_DATA_DIR/static/uploads`，保留 DB `sqlite_query_only=true`，支援 `_thumb.webp`、max-width 500、`quality=80`、`thumbnail_only` 只保留縮圖，以及標準 upload 原圖加縮圖。Go unit tests、Windows build、linux/arm64 `CGO_ENABLED=0` build 已通過。本輪未移除 Pillow、未改 Python upload-url/import/delete/cleanup owner、未部署 Pi、未改 Caddy/systemd/frontend default。下一步為需另行明確授權的 23.8-thumb.5 Go thumbnail surface expansion or removal-readiness gate。 |
| **go-roadmap** | 2026-06-06 | Phase 23.8-thumb.5 Go thumbnail surface expansion or removal-readiness gate — 在明確授權後完成 decision gate，結論為 blocked-expansion / retain Python：23.8-thumb.4 只證明 local/copied-data multipart `POST /api/upload` candidate；`POST /api/upload/url` 涉及 SSRF、remote request timeout/header、Content-Type/magic、download size cap、thumbnail_only/fallback parity，import helper 又牽涉 Markdown import workflow 與 tuple compatibility，因此本輪不新增 Go upload-url/import helper、不改 Python runtime、不移除 Pillow、不改 SSRF/remote fetch policy、不部署 Pi、不改 Caddy/systemd/frontend default。下一步為需另行明確授權的 23.8-thumb.6 Go upload-url remote-fetch safety parity plan。 |
| **go-roadmap** | 2026-06-06 | Phase 23.8-thumb.6 Go upload-url remote-fetch safety parity plan — 在明確授權後完成 plan-only contract：鎖定 `POST /api/upload/url` 現行 Python 行為（JSON `url`/`thumbnail_only`、http/https scheme、SSRF guard、requests timeout/header、Content-Type、magic number、size cap、filename/hash fallback、thumbnail_only 成功只保留 `_thumb.webp`、thumbnail 失敗保留原圖）與未來 Go candidate 的安全條件。Go candidate 必須獨立 flag `--enable-upload-url-write` / `PRISM_GO_ENABLE_UPLOAD_URL_WRITE`，預設 405 disabled，只寫 copied data dir，DB 保持 `sqlite_query_only=true`，驗 redirect target、streaming size cap、failure no-mutation。本輪未改 Go/Python runtime、未移除 Pillow、未部署 Pi、未改 Caddy/systemd/frontend default。下一步為需另行明確授權的 23.8-thumb.7 Go upload-url local implementation candidate。 |
| **go-roadmap** | 2026-06-06 | Phase 23.8-thumb.2-23.8-thumb.3 Thumbnail parity fixtures and Pillow removal gate — 在明確授權後完成縮圖線 fixture lock 與 removal gate。23.8-thumb.2 新增 runtime parity fixtures，覆蓋 `POST /api/upload` jpg/png/webp/gif 產生 `_thumb.webp`、max-width 500、`thumbnail_only` 成功只保留縮圖、thumbnail unavailable 保留原圖 fallback、`POST /api/upload/url` remote thumbnail-only、import image helper 成功/失敗 fallback、`/api/upload/delete` 刪 `_thumb.webp` companion、orphan cleanup 將被引用原圖的 `_thumb.webp` 視為 referenced。23.8-thumb.3 判定目前不能移除 Pillow：尚無 Go thumbnail implementation candidate、尚無含 `github.com/skrashevich/go-webp` 的 real `go-shadow` packaging smoke、尚未證明 Python fallback/removal strategy。本輪未新增 Go WebP dependency、未改 Go/Python runtime、未移除 Pillow、未改 requirements/start/API/sequence docs runtime owner、未部署 Pi、未改 Caddy/systemd/frontend default。下一步為需另行明確授權的 23.8-thumb.4 Go thumbnail local implementation candidate。 |
| **go-roadmap** | 2026-06-06 | Phase 23.8-thumb.1 WebP encoder dependency decision — 在明確授權後完成 plan-only dependency decision：選 `github.com/skrashevich/go-webp` 作為 first spike candidate only，因其 pure Go、Apache-2.0、支援 lossy/lossless 與 quality 0-100，能對齊目前 Pillow `quality=80` 縮圖語意；local probe 驗 Windows `go run` / Windows build / linux arm64 `CGO_ENABLED=0` cross-build 通過。拒絕 `golang.org/x/image/webp` decode-only，拒絕 `github.com/chai2010/webp` 與 `github.com/kolesa-team/go-webp` 作為第一候選因 cgo/libwebp/GCC/MinGW/toolchain 包裝風險，`github.com/HugoSmits86/nativewebp` 保留 secondary/fallback 因 lossless-only 不貼近現行 lossy parity。新增 `docs/contracts/phase23-go-webp-encoder-dependency-decision.json` 與 `tests/test_phase23_go_webp_encoder_dependency_decision.py`；本輪未新增 `go-shadow/go.mod` dependency、未移除 Pillow、未改 upload/import runtime、未部署 Pi、未改 Caddy/systemd/frontend default。下一步為需另行明確授權的 23.8-thumb.2 Thumbnail parity fixtures。 |
| **go-roadmap** | 2026-06-06 | Phase 23.10.2-23.10.3 Python removal decision and final stabilization — 在明確授權後完成最終決策與穩定化：23.10.2 決定不移除 Python，normal path 保留 Python `prism.service`，Go 維持 bounded read/local candidates/local artifact；23.10.3 以 retained-Python final state 驗證本機與 Pi。Local 通過 `npx tsc --noEmit`、`npm run build`、`scripts/smoke_go_local_artifact.ps1`、local API smoke、Playwright screenshot smoke。Pi preflight 建立 DB/data/Caddy backups (`prism_pre_23_10_3_stabilization_20260606_022312.db` 等)，tar-over-SSH 同步 current worktree 並重啟既有 `prism.service`；live 驗 service/Caddy active+enabled、Caddy validate passed、version 2.4.9 Linux V2、migration v16 pending 空、Go routing disabled/Python owner、notes total 198、headers 無 Go routing header、journal restart 後 v16 最新/port 5000/無新錯誤。本輪未移除 Python、未改 Caddyfile/reload Caddy、未改 systemd unit、未擴 Go route ownership、未寫 production DB/files、未改 frontend default、未做 Pillow removal 或 public exposure。Phase 23 以 retained-Python normal path 關閉；下一個仍可做的獨立線是 23.8-thumb.1 WebP encoder dependency decision，或另行授權 commit/release hygiene。 |
| **go-roadmap** | 2026-06-06 | Phase 23.10.1 Ownership closure audit — 在明確授權後完成 plan-only ownership closure：23.9 後 live primary runtime 與 tested public route owner 仍是 Python `prism.service`；Go 目前只具備 bounded read、flag-gated local DB write candidates、flag-gated attachment text JSON candidate、local embedded-SPA artifact。Notes writes/actions/batch/history、live category/tag writes、files/uploads/attachments raw/delete/cleanup/import/export、system/server/config、migrations、live static serving 與 rollback owner 仍 retained Python-owned。Python removal 維持 blocked，直到每個 critical surface 有 verified Go implementation 或明確 retained-Python release strategy。新增 `docs/contracts/phase23-go-ownership-closure-audit.json` 與 `tests/test_phase23_go_ownership_closure_audit.py`。下一個 Go runtime gate 為需另行明確授權的 23.10.2 Python removal decision，預期預設為 retain Python unless gaps are closed or accepted。 |
| **go-roadmap** | 2026-06-06 | Phase 23.9 Pi deployment rollout — 在明確授權後完成 Pi preflight、受控同步與 live verification：`prism.service` / Caddy active+enabled、Caddy validate passed、migration current/latest v16 pending `[]`；建立 DB backup `prism_pre_23_9_rollout_20260606_015426.db`、data snapshot `prism_pre_23_9_data_snapshot_20260606_015426.tar.gz`、Caddy backup `Caddyfile.prism-pre-23-9-rollout-20260606_015426.bak`。用 tar-over-SSH 同步目前 worktree，排除 production DB/WAL/SHM、uploads、attachments、`.port_config`、env/log/build artifacts，重啟既有 `prism.service`。Live 驗 `/api/test` notes 198 / categories 6 / tags 128、`/api/server/version` v2.4.9 Linux V2 mode true、migration v16 pending 空、`/api/system/go-read-routing` enabled false / Python owner、`/api/notes?per_page=1` total 198；headers 無 Go routing header，journal 無新 write/error。本輪未改 Caddyfile、未 reload Caddy、未改 systemd unit、未擴 Go route ownership、未寫 production DB/files、未移除 Python、未做 Pillow removal 或 Go WebP encoder。下一個 Go runtime gate 為需另行明確授權的 23.10.1 ownership closure audit；縮圖線仍是獨立的 23.8-thumb.1。 |
| **go-roadmap** | 2026-06-06 | Phase 23.8.2-23.8.3 Local smoke artifact and release boundary — 在明確授權後新增 Windows/local Go artifact smoke 腳本與 contract：`scripts/smoke_go_local_artifact.ps1` 會 build `prism-go-runtime.exe`、複製 `knowledge.db` 到 `build/go-local-smoke/data/`、驗 default `sqlite_query_only` read surface、embedded SPA、核心 read APIs、write candidate 預設 disabled，並在 copied write DB 上啟用 tag/category write smoke；source DB SHA256 保持不變。本機封裝成功只代表 local artifact 可用，不代表 Pi 已更新；本輪未部署 Pi、未改 Caddy/systemd、未寫 production DB/files、未改 frontend default、未移除 Python、未新增 Pillow removal 或 Go WebP encoder。下一個 Go runtime gate 為需另行明確授權的 23.9.1 Pi preflight；縮圖線仍是 23.8-thumb.1 encoder dependency decision。 |
| **go-roadmap** | 2026-06-06 | Phase 23.8.1 Local packaging contract and thumbnail ownership plan — 在明確授權後完成 plan-only packaging/data-dir/migration boundary：Go local artifact candidate 必須使用 external data dir，資料含 `knowledge.db`、WAL/SHM、`static/uploads`、`docs/attachments`、logs/backups/config/env；migration owner 依 23.7 保持 Python-owned，Go 只能作 status-only local/readiness candidate。另把「去掉 Pillow、改由 Go 引入 WebP encoder 接管縮圖」納入 `23.8-thumb` 後續規劃：必須先驗 WebP encode support、Windows/Pi arm64 build、license、cgo/pure-Go、jpg/png/webp/gif input 覆蓋，再做 upload/upload-url/import parity fixtures；本輪未移除 Pillow、未新增 Go encoder、未實作 Go upload/thumbnail route、未建立 packaged artifact、未碰 production files、未部署 Pi、未改 Caddy/service/frontend default。下一步 packaging 為 23.8.2 local smoke artifact；下一步縮圖為 23.8-thumb.1 encoder dependency decision。 |
| **go-roadmap** | 2026-06-06 | Phase 23.7 Migration / DB ownership decision gate — 在明確授權後完成 plan-only migration ownership 決策：normal/live migration runner 保持 Python-owned，`migrations.run_migrations()` 與 Python `/api/system/migration-status` 繼續是正式 owner；Go 目前只讀 `Schema_Meta` 做 health/schema version check。`go_status_only` 可作未來 local/copied DB readiness candidate，但必須保持 SQLite `query_only`、不更新 `Schema_Meta`、不跑 DDL/DML，並與 Python current/latest/pending semantics parity。`go_full_migration_runner` deferred，直到 ordered migration list、idempotent skip semantics、fresh/upgraded DB fixtures、failed migration rollback、backup/restore、Pi preflight 與 Python fallback owner 全部有 dedicated proof。未實作 Go migration runner、未改 schema、未碰 production DB、未改 Caddy/service、未部署 Pi、未移除 Python、未擴 public exposure。下一步 23.8 只可先做 local packaging execution track / packaging contract。 |
| **go-roadmap** | 2026-06-06 | Phase 23.6-next First Go file-read route implementation candidate — 在明確授權後完成 local/copied-DB-and-files `GET /api/attachments/<attachment_id>` text JSON branch Go candidate：新增 `--enable-attachment-text-read` / `PRISM_GO_ENABLE_ATTACHMENT_TEXT_READ=1`，啟用後 API surface 為 `get-read-only+local-attachment-text-read`，SQLite 仍保持 `query_only`。Python vs Go fixture 覆蓋 UTF-8 text attachment 與 missing attachment id；Go safety fixture 覆蓋 missing file、unsafe path、unsupported extension、`raw=true` blocked、default disabled，並證明 success/failure 後 DB bytes、copied `docs/attachments` bytes、copied `static/uploads` bytes 不變。未處理 raw/binary/send_file、upload/delete、cleanup、import/export、server backup/logs、live routing、production DB/files、Pi deploy、schema migration、Python removal 或 public exposure。下一步 23.7 只可先做 migration / DB ownership decision gate。 |
| **go-roadmap** | 2026-06-06 | Phase 23.6 File / attachment ownership gate — 在明確授權後完成 plan-only ownership inventory / selection / backup-restore gate：分拆 attachments metadata/body、upload、cleanup、notes image cleanup、export/import、server backup/logs，逐一標 data root、DB/file side effects、rollback/defer reason。第一個候選只選 `GET /api/attachments/<attachment_id>` text JSON branch，限定 local/copied DB + copied `docs/attachments`，不處理 `raw=true`、binary/send_file、upload/delete、cleanup、import/export、server backup/logs。Read-only candidate 必須證明 DB bytes 與 attachment file bytes 不變；任何 file write/delete candidate 都需另開 DB + filesystem backup/restore + partial failure rollback gate。未實作 Go file route、未改 live routing、未碰 production DB/files、未部署 Pi、未改 schema、未移除 Python、未擴 public exposure。下一步 23.6-next 需另行明確授權。 |
| **go-roadmap** | 2026-06-05 | Phase 23.5-next.2-4 category update closure — 在明確授權後完成 category update parity hardening / rollback / boundary 收尾：Python + Go 現在都拒絕 trimmed empty category name，回 400 `Category name cannot be empty`，避免分類名稱寫成空字串。Rollback lock 覆蓋 missing body、missing category、duplicate name、empty name、disabled Go flag 皆不改 `Categories` snapshot，success 只更新目標分類 row 且 `Notes.category_id` 不變。未新增 category create/delete、notes actions、tag CUD、file routes、live routing、Caddy/service、production DB、Pi deploy、schema migration、Python removal 或 public exposure。下一步 23.6 只可先做 file / attachment ownership plan-only inventory。 |
| **go-roadmap** | 2026-06-05 | Phase 23.5-next.1 Second Go DB-only write implementation subgate — 在明確授權後完成 local/copied-DB `PUT /api/categories/<category_id>` Go candidate：新增 `--enable-category-write` / `PRISM_GO_ENABLE_CATEGORY_WRITE=1`，預設 Go runtime 仍是 GET read-only + SQLite `query_only`。Python vs Go copied DB fixture 覆蓋 name-only、icon-only、sort_order-only、combined update、missing body 400、missing category 404、duplicate exact-name 409、disabled flag 405、`Notes.category_id` 不變。實作時發現 Python 當時允許 empty trimmed category name 寫入；該 gap 已於 23.5-next.2-4 修成 Python + Go 皆回 400。未改 live Caddy/service/frontend default、未碰 production DB、未部署 Pi、未改 schema、未移除 Python、未擴 public exposure。 |
| **go-roadmap** | 2026-06-05 | Phase 23.5 Go DB-only write expansion gate — 在明確授權後完成 plan-only stabilization / selection：23.4 `PUT /api/tags/<tag_id>` 維持 local/copied-DB candidate，不升 live Go ownership；`Tags.name` NOCASE schema/documentation/runtime discrepancy 本輪明確延後，tag delete / tag merge / broader tag CUD 在 dedicated gate 前 blocked。下一個 DB-only implementation subgate 選定 `PUT /api/categories/<category_id>`，只允許 local/copied-DB flag-gated parity；未實作 Go category write、未改 schema、未改 Caddy/service/frontend default、未碰 production DB、未部署 Pi、未移除 Python、未擴 public exposure。 |
| **go-roadmap** | 2026-06-05 | Phase 23.4 First Go write route implementation gate — 在明確授權後完成 local/copied-DB first write parity：Go 新增 flag-gated `PUT /api/tags/<tag_id>`，只有 `--enable-tag-write` / `PRISM_GO_ENABLE_TAG_WRITE=1` 才會進入 `get-read-only+local-tag-write`；預設 runtime 仍是 `get-read-only` + SQLite `query_only`。Python vs Go copied DB fixture 覆蓋 success/trim、missing name、empty name、missing tag 404、duplicate 409、rollback/no partial write、`Note_Tags` 不變。未改 Caddy/service/frontend default、未碰 production DB、未部署 Pi、未移除 Python、未擴 public exposure。下一步 23.5 pending explicit approval：先決定 tag rename live/local gate、處理或延後 `Tags.name` NOCASE docs/schema discrepancy，再選下一個 DB-only candidate。 |
| **go-roadmap** | 2026-06-05 | Phase 23.3 Go write surface selection gate — 在明確授權後完成 plan-only first write candidate selection：選定 `PUT /api/tags/<tag_id>` (`tag_rename`) 作為 23.4 唯一 candidate，因為它是 single-purpose、DB-only、只更新 `Tags.name`、無檔案/cascade/bulk/process side effects，且 Python vs Go response + DB-state parity 容易鎖定。拒絕或暫緩 notes core writes、pin/archive、duplicate/reorder/batch、category delete、tag delete/merge、attachments/uploads/cleanup/import/export/system/server/config。23.3 未實作 Go write、未改 production DB、未改 Caddy/service/frontend default、未部署 Pi、未移除 Python、未擴 public exposure。下一步為需另行授權的 23.4 First Go write route implementation gate，限 local/copied-DB `PUT /api/tags/<tag_id>`。 |
| **go-roadmap** | 2026-06-05 | Phase 23.2 Go file-read parity implementation gate — 在明確授權後完成 local/copied-DB Go read-only 文字附件 body search parity：`GET /api/notes?q=...` 會在既有 DB search 外，受限掃描 explicit `--data-dir` 內 `docs/attachments` 的 `md/markdown/txt` 相對路徑，命中 note ids 合回原查詢。安全邊界沿用 23.1：拒絕 `..`、absolute/UNC/volume/colon path、symlink escape、非 `docs/attachments`、unsupported extension，單檔 1 MiB，單 query 200 files / 5 MiB / 250 ms。新增 Python vs Go controlled files diff fixture 與 implementation pytest lock；未改 Caddy/service/frontend default、未碰 production DB、未部署 Pi、未新增 writes/files/migrations、未移除 Python、未擴 public exposure。下一步為需另行授權的 23.3 Go write surface selection gate。 |
| **go-roadmap** | 2026-06-05 | Phase 23.1 Go file-read parity plan gate — 在明確授權後完成 plan-only file-read safety contract：Go 若於 23.2 補文字附件 body 搜尋，只能讀 explicit `--data-dir` 內 `docs/attachments` 的 `md/markdown/txt` 相對路徑，需拒絕 `..`、symlink escape、absolute/UNC/external path，單檔上限 1 MiB，單 query 上限 200 files / 5 MiB / 250 ms，missing / oversized / unsupported extension 均只當 non-match。新增 Python vs Go copied DB + controlled files fixture plan 與 pytest lock；未實作 Go scanner、未改 Caddy/service/frontend default、未碰 production DB、未部署 Pi、未移除 Python、未擴 public exposure。下一步為需另行授權的 23.2 Go file-read parity implementation gate。 |
| **go-roadmap** | 2026-06-05 | Phase 23 full Go roadmap expansion — 依使用者要求直接把幾個大項到最終完成寫入 `docs/TODO.md`，不再只停在 23.1 或轉回 frontend polish。Phase 23 現在完整列出：23.1 file-read parity plan、23.2 file-read implementation、23.3 write surface selection、23.4 first Go write route、23.5 DB-only write expansion、23.6 file/attachment ownership、23.7 migration/DB ownership decision、23.8 local packaging execution、23.9 Pi deployment rollout、23.10 Python reduction/final stabilization。每段標明 `P0/P1` risk、白話說明、完成條件與不做邊界；正式使用仍維持 Raspberry Pi + systemd + Caddy，local packaging 是 artifact path，不取代 Pi deployment。 |
| **go-roadmap** | 2026-06-05 | Phase 23.0 Go refactor roadmap consolidation — Risk level `P0 safety-critical`，plan-only。依使用者要求停止 frontend polish drift，直接把 Go 重構主線寫回 `docs/TODO.md`、`Prism_Go_模組逐步重構計劃報告.md`、`docs/ARCHITECTURE.md`：最終目標是本機可封裝執行，但日常/正式使用仍部署在 Raspberry Pi + systemd + Caddy + existing data dir。下一個 active Go gate 固定為 `23.1 Go file-read parity plan gate`，只規劃文字附件 body search parity 的 data-dir / path traversal / file type / performance / rollback / Python vs Go diff fixtures，不實作 Go file scanner、不改 Caddy、不部署 Pi、不改 production DB、不改 frontend default、不移除 Python、不擴 public exposure。 |
| **frontend-product** | 2026-06-05 | Prompt Builder mobile action bar polish — Risk level `P1 workflow-sensitive`。在明確授權後完成單一 implementation task：mobile 寬度下新增 header 下方 sticky action bar，讓「儲存至筆記庫 / 重置」第一屏可見且 scroll 後仍可操作；desktop 保留既有左側設定區底部 sticky action bar。新增 targeted source regression test、frontend typecheck/build、full pytest 與 mobile/desktop browser flow。未新增 backend API、DB schema、Pi/Caddy/service、Go runtime、AI/ML dependency、server-side UI preference 或 public exposure。 |
| **frontend-product** | 2026-06-05 | Settings tab deep linking — Risk level `P1 workflow-sensitive`。在明確授權後完成單一 implementation task：Settings 分頁改由 `tab` query param 保存與還原，`/settings?tab=deploy` reload 後仍停在部署分頁，點分頁會用 `replace` 更新 URL 並保留其他 query param；無效/缺省 tab 回到外觀。新增 targeted source regression test、frontend typecheck/build、full pytest 與 browser reload/click flow。未新增 backend API、DB schema、Pi/Caddy/service、Go runtime、server-side UI preference 或 public exposure。 |
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
