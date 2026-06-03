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

## 🚀 Phase 19: Go Runtime / Packaging Promotion — ✅ 19.8 Reverse-proxy / Service Cutover Planning Gate

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

### ⛔ 19.9 Approved Caddy Read-only Routing Drill — Blocked Pending Explicit Approval

- [ ] **19.9.1** Live approval gate — 只有在另行明確授權後，才可依 19.8 plan 做短暫 Caddy-level read-only routing drill。
- [ ] **19.9.2** Fresh preflight and config backup — 執行前必須驗 Python service、Caddy active/validate、routing off、fresh DB backup、Go sidecar localhost/query_only/schema health、Caddy config rollback copy。
- [ ] **19.9.3** Short reversible Caddy drill — 若被授權，僅可把白名單 GET read surface 暫時路由到 Go，採集 header/status/log evidence 後立即 rollback 到 Python-only；不得改 frontend default、Go writes/files/migrations、Python removal 或 exposure boundary。

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
