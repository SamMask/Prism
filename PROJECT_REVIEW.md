# GitHub 專案評估報告

評估日期：2026-06-19  
評估範圍：本機 checkout `D:\AI\Prism`，未查詢 GitHub Issues / PR / Releases live 狀態。  
限制：依要求未修改既有專案檔；本輪只新增本報告。完整 runtime 啟動、瀏覽器操作、Pi live、`npm audit`、GitHub issue/PR 健康度未驗證。

## 0. 一句話結論

Prism 是一個實際可用、文件與測試基礎偏厚的 local-first 知識庫 / prompt 工具，不是單純展示型 prototype。  
但它目前最適合 localhost / trusted LAN / Windows portable / Pi 私有部署；若要導入到其他專案或暴露給不可信內容，必須先處理 markdown stored XSS、no-auth 邊界、LICENSE 缺失與 CI 缺口。

## 1. 最終建議

- 建議等級：可 fork 改造
- 總體分數：7.1/10
- 最大優點：Go primary 單一 runtime、React SPA、SQLite external data dir、文件與 contract/test evidence 很完整，`go test ./...` 與 TypeScript no-emit 在本輪通過。
- 最大風險：`frontend/src/components/ReadingView.tsx:27` / `:426` 與 `frontend/src/components/editor/EditablePreview.tsx:157` / `:139` 直接使用 `marked()` + `dangerouslySetInnerHTML`，未見 sanitizer；同時 Prism 明確沒有內建 auth。
- 最適合用途：個人本機知識庫、可信 LAN / VPN / SSH tunnel 工具、可 fork 的 Go + React + SQLite local-first app 參考。
- 不適合用途：public internet API、多使用者 SaaS、處理不可信 markdown / 外部匯入內容且未先補 sanitizer 的部署、需要現成 auth / RBAC / cloud sync 的產品。

## 2. 專案定位與實際成熟度

Prism 的實際定位是 local-first personal knowledge management and prompt tooling。README 宣稱它儲存 notes、prompts、attachments、tags、history 到 local SQLite，避免 built-in AI、cloud sync、telemetry 與 public-internet assumptions；這與 source / docs 大致一致。

主要證據：

- `README.md`：宣稱 Go primary runtime、Windows desktop portable、Pi deployment、no cloud / no telemetry / no AI dependency。
- `docs/API_REFERENCE.md`：API 以 Go primary live/default runtime 為基準，列出 notes、categories、tags、attachments、upload、cleanup、import/export、server/system。
- `docs/SCHEMA.md`：目前 schema 是 Migration v17，核心資料表包含 `Notes`、`Categories`、`Tags`、`Note_Tags`、`Source_Urls`、`Note_History`、`Note_Attachments`、`Schema_Meta`、`Notes_FTS`。
- `docs/TODO.md`：Current Truth 明確記錄 Go primary 是唯一 runtime owner，Python Flask backend source 已移除。
- `requirements.txt` / `requirements-pi.txt`：只剩 `pytest==7.4.3`，支持 Python 已不是產品 backend runtime 的宣稱。

成熟度判斷：功能面比一般個人 side project 成熟，尤其文件、contract、測試密度高；但安全產品化與導入包裝仍不到「拿來當公開服務」等級。README 的價值描述沒有明顯誇大，但 `README.md` 寫 MIT License 且說 See `LICENSE`，實際 `Test-Path LICENSE / LICENSE.md / COPYING` 都是 `False`，這是導入前必修缺口。

## 3. 安裝、啟動與可跑性

實際檢查過的命令與結果：

| 命令 | 結果 | 說明 |
|---|---:|---|
| `git status --short --branch` | `## main...origin/main` | 本輪開始與驗證後 worktree 乾淨，直到新增本報告前沒有既有檔案變更。 |
| `rg --files -g '!venv/**' -g '!build/**' ...` | 成功列出 repo 結構 | 主要目錄包含 `go-shadow/`、`frontend/`、`tests/`、`docs/`、`scripts/`、`deploy/`、`resources/`。 |
| `go version` | `go version go1.26.3 windows/amd64` | 本機 Go 可用；`go-shadow/go.mod` 要求 `go 1.26.1`。 |
| `node --version; npm --version` | `v22.14.0`, `10.9.2` | 前端工具鏈可用。 |
| `python --version; pytest --version` | `Python 3.11.9`, `pytest 9.0.2` | 注意：實際 pytest 與 `requirements.txt` pin 的 `pytest==7.4.3` 不一致。 |
| `go test ./...` in `go-shadow` | `ok prism-go-shadow (cached)` | Go runtime test 在本輪通過。 |
| `npm exec tsc -- --noEmit` in `frontend` | exit 0 | TypeScript no-emit 檢查通過，未產生 build output。 |
| `pytest tests/ --collect-only -q -o log_file="$env:TEMP\..."` | `352 tests collected` | collect-only 通過；為避免寫入 repo 內 `test_run.log`，log file 指到 TEMP。 |
| `go list -m all` | 成功 | Go 依賴包含 `modernc.org/sqlite v1.33.1`、`jchv/go-webview2`、`skrashevich/go-webp` 等。 |
| `npm ls --depth=0` | 成功 | 實際安裝 React 18.3.1、Vite 5.4.21、axios 1.13.2、marked 17.0.1、zustand 4.5.7 等。 |
| `Test-Path .github; Test-Path .github\workflows` | `False`, `False` | 根目錄未見 GitHub Actions CI。 |
| `Test-Path LICENSE; Test-Path LICENSE.md; Test-Path COPYING` | `False`, `False`, `False` | README 的 MIT / LICENSE 宣稱缺實體檔支撐。 |

未執行或未驗證：

- 未跑 `npm run build`：會寫入 `frontend/dist`，與「不要修改既有專案檔」衝突；只跑 `tsc --noEmit`。
- 未跑 full `pytest tests/ -v`：`pytest.ini` 會寫 `test_run.log`，部分測試也可能建立 build/smoke artifacts；本輪改用 collect-only。
- 未啟動 Go runtime / Windows desktop / Pi service，也未做瀏覽器 smoke。
- 未跑 `npm audit` 或查 GitHub advisory：會對外送 dependency inventory；本輪依「不要外傳資料」保守略過。

可跑性評估：安裝流程清楚，但新使用者需要 Go 1.26、Node、npm、Python pytest、WebView2、Windows PowerShell scripts 等條件。對個人 Windows / Pi 使用者可接受；對一般 GitHub 使用者，缺 CI badge、缺 LICENSE、缺 release assets live 驗證會降低第一印象。

## 4. 架構分析

主要模組與責任邊界：

- `go-shadow/main.go`：Go primary runtime，約 9,441 行；集中 API route registration、SQLite owner/migrations、handlers、file I/O、backup、SSRF/CSRF/path safety、static SPA serving、desktop runtime hooks。
- `frontend/src/`：React 18 + TypeScript + Vite SPA。`App.tsx` 只掛三條 route：`/`、`/prompt-builder`、`/settings`；`Layout.tsx` 組合 Sidebar / Header / FilterStrip / CommandPalette。
- `frontend/src/services/api.ts`：axios API client，`API_BASE_URL = "/api"`，response interceptor 統一處理 network / 5xx toast。
- `docs/`：architecture、schema、API、contracts、TODO、deployment、development history。
- `scripts/`：build / start / smoke / Pi live ops / desktop portable scripts。
- `tests/`：pytest-based contract / static / smoke-oriented tests；`go-shadow/main_test.go` 也有大量 Go unit/integration tests。

資料流：

Browser 或 WebView2 -> React SPA -> `/api/*` -> Go handlers -> SQLite WAL / FTS5 + external data dir (`static/uploads`, `docs/attachments`, logs, backups, config)。Pi 部署再由 Caddy reverse proxy 到 `127.0.0.1:5004`。

架構優點：

- `docs/ARCHITECTURE.md` 與 `docs/CONTRACTS.md` 對 runtime、data-dir、security、deploy boundary 有明確契約。
- `go-shadow/main.go:295-344` 明確集中註冊 API routes；`go-shadow/main.go:346-349` 用 `logRequests(srv.csrfGate(mux))` 統一 middleware。
- `go-shadow/main.go:520-534` 預設拒絕 non-local bind，符合 no-auth local-first 定位。
- `scripts/build_go_runtime.ps1:13-38` 串起 frontend build、embed dist、`go test ./...`、Windows / linux-arm64 artifact build。

架構風險：

- `go-shadow/main.go` 單檔過大，handler、migration、server/system、security、file operations 混在同一檔，review / merge / blame 成本高。
- 文件歷史很完整但也很重；`docs/ARCHITECTURE.md` 有大量歷史 phase，雖有 current-truth 警告，新貢獻者仍可能誤讀舊 Python/sidecar 描述。
- 沒有 root CI workflow，導入者無法靠 GitHub 狀態快速判斷測試是否在乾淨環境通過。

## 5. Code 品質分析

正面觀察：

- Go handler 多處有明確 method guard、JSON error response 與 file cleanup。例如 `go-shadow/main.go:5546-5614` 的 `handleUploadURL` 對 method、feature flag、URL scheme、content type、size、magic MIME 都有檢查。
- SSRF 防護不只查 literal IP，也查 DNS resolution 與 redirect target：`validateUploadURLTarget` 在 `go-shadow/main.go:5662-5682`，blocked ranges 在 `go-shadow/main.go:5707-5725` 起。
- CSRF gate 有實作且可 runtime toggle：`go-shadow/main.go:1606-1630`、`go-shadow/main.go:1668-1680`；測試存在於 `go-shadow/main_test.go:3310` 與 `:3402` 附近。
- API client 有集中 error interceptor：`frontend/src/services/api.ts:197-229`。
- UI component 有明確 route/flow 拆分：`frontend/src/App.tsx`、`Layout.tsx`、`HomePage.tsx`、`CommandPalette.tsx`。

具體問題：

- 巨型檔案：`go-shadow/main.go` 約 9,441 行，`frontend/src/i18n/index.ts` 約 156 KB，`frontend/src/services/api.ts` 約 806 行。這不一定代表行為錯，但長期可維護性與 review 成本高。
- Markdown rendering unsafe：`ReadingView.tsx:27-31` 和 `EditablePreview.tsx:157-161` 直接回傳 `marked(markdown)`；`ReadingView.tsx:426`、`EditablePreview.tsx:139` 直接 `dangerouslySetInnerHTML`。掃描未見 DOMPurify 或等效 sanitizer。
- Attachment upload size gate 不一致：`maxAttachmentFileBytes` 是 1 MiB (`go-shadow/main.go:52`)，但 `POST /api/notes/<id>/attachments` 用 `ParseMultipartForm(maxUploadFileBytes)` 後 `io.Copy` 到檔案（`go-shadow/main.go:7083-7121`），沒有像 image upload 一樣 `LimitReader` 明確阻擋超限內容；此點也已列入 `docs/TODO.md:106-110`。
- Backup download 用 copy live `.db` 到 temp file (`go-shadow/main.go:2359-2384`)；在 WAL active write 情境是否最新一致，本輪未驗證，且 `docs/TODO.md:112-116` 已列為待確認風險。
- Category invalid input hardening 已列入 `docs/TODO.md:118-122`，表示錯誤型別 / target validation 仍有改善空間。

## 6. UI / UX 或使用流程分析

此專案有 UI：React SPA + Windows WebView2 desktop shell + Pi browser flow。

優點：

- `Layout.tsx:14-38` 有穩定 app shell：Sidebar、Header、FilterStrip、main、footer、CommandPalette。
- `HomePage.tsx:76-260` 支援 notes grid/list/compact、DnD reorder、infinite scroll、recent searches、filter context、empty state。
- `CommandPalette.tsx:47-220` 提供 navigation、recent notes、new note、theme toggle 等鍵盤式入口。
- `frontend/src/i18n/index.ts` 與測試 `tests/test_frontend_i18n_settings.py` 顯示多語系覆蓋是刻意維護的，不是後補。
- `docs/TODO.md` 記錄多個已完成 UX gate：image lightbox、reading workspace、starred tag shortcuts、batch markdown/txt import、note list lightweight payload。

風險與未驗證：

- 本輪未啟動 dev server / desktop shell / Pi live，也未截圖或做 browser smoke；UI 流暢度只做 source/docs 層評估。
- Markdown XSS 會直接影響 ReadingView / EditablePreview 的使用安全。
- `CommandPalette.tsx:150` 把 `note.content` 納入 keywords；配合 list payload preview 策略通常可接受，但 command palette 搜尋可能不是全文搜尋，外部導入時要理解它不是 server-side full search。
- 無障礙與 RWD 有元件跡象與測試，但本輪未做實機/瀏覽器驗證，標示為未驗證。

## 7. 測試與穩定性

測試現況強於一般個人 repo：

- 本輪 `pytest tests/ --collect-only` 收到 352 tests。
- 本輪 `go test ./...` 通過。
- 本輪 `npm exec tsc -- --noEmit` 通過。
- `tests/` 覆蓋 Go migration、fresh DB、uploads、media cleanup、import/export、server/system、desktop portable、i18n、frontend static contracts、release/deploy boundaries。
- `go-shadow/main_test.go` 包含 CSRF、upload URL、backup restore、FTS、delete cleanup 等 Go tests。
- `.loop/verify-gate.ps1` 明確 gate：`git diff --check`、AGENTS/CLAUDE mirror、`pytest tests/ -v`、`go test ./...`。

缺口：

- 沒有 root `.github/workflows`，CI 未建立或未納入 repo。
- 本輪沒有跑 full pytest / frontend build / browser smoke，因此「全套目前綠燈」未驗證。
- `requirements.txt` pin `pytest==7.4.3`，但本機實際 `pytest 9.0.2`；collect-only 通過不代表 pinned env 完整一致。
- `docs/TODO.md:136-140` 已列出 stability test-gap pack：空資料庫、中文/emoji、大量文件、search sync、missing file、Windows path、port occupied、DB lock/concurrent request、壞 DB / restore marker。
- E2E 目錄存在於 `e2e/`，但 `docs/CONTRIBUTING.md` 寫「位於 `tests/e2e/`」，文件路徑有小不一致。

最可能在真實使用中壞掉的地方：

- 不可信 markdown/import/attachment 造成 stored XSS。
- 大 attachment upload 與 1 MiB read limit 不一致。
- WAL active write 下的 DB backup snapshot 語意。
- 大量附件 / 大量 note 搜尋時 bounded scan 造成漏結果且不透明。
- Windows portable / WebView2 缺 runtime 時的使用者引導，本輪未實機驗證。

## 8. 安全風險分析

### 低風險

- Secret 掃描未發現明顯 key/token：本輪 `rg` 掃 `api_key/token/secret/password/private key/Bearer` 主要命中安全邊界文字與 package-lock 套件名，未見真實 secret。
- tracked private/runtime path 檢查：`git ls-files -- knowledge.db app.log test_run.log logs static/uploads docs/attachments docs/notes build .omx .env frontend/dist` 無輸出，表示這些高風險 runtime/private path 未被 tracked。
- Public bind guard：`go-shadow/main.go:520-534` 預設拒絕 non-local bind，除非 `PRISM_GO_ALLOW_PUBLIC_BIND=1`。
- SSRF guard：`go-shadow/main.go:5662-5682` 驗證 DNS / literal IP；`go-shadow/main.go:5707-5725` 擋 loopback/private/link-local/multicast/unspecified/reserved ranges。
- Log privacy 有近期修補證據：`20260619_Prism_深度掃描報告.md` 記錄 request log 不再記 query string。

### 中風險

- No built-in auth 是設計選擇但也是導入風險：`README.md:110`、`DEPLOY-PI.md:8`、`docs/API_REFERENCE.md:38` 都明確說沒有 API Token / Bearer Token / 使用者認證。localhost / trusted LAN 可接受；public internet 不可接受。
- CSRF 保護是 Origin/Referer based，且無 Origin/Referer 的 curl / MCP / agent 請求放行：`go-shadow/main.go:1606-1630`。這符合工具定位，但不是多使用者 Web app 的完整防線。
- `/healthz` 回傳 data dir、db path、uploads/logs/backups paths (`go-shadow/main.go:1694-1718`)；在本機診斷有價值，但若 exposure boundary 失守會泄漏本機路徑。
- Backup download 只複製 DB，不含 uploads/attachments；且 WAL 最新一致性未驗證 (`go-shadow/main.go:2359-2384`)。
- Attachment upload hard limit 未明確對齊 read limit (`go-shadow/main.go:7083-7121`)。

### 高風險

- Stored XSS：`marked()` + `dangerouslySetInnerHTML` 未見 sanitizer。證據：`frontend/src/components/ReadingView.tsx:27-31`、`:426`；`frontend/src/components/editor/EditablePreview.tsx:157-161`、`:139`。在 Prism 的同源 localhost / WebView2 情境，惡意 markdown 可嘗試呼叫 `/api/*`。
- Public exposure with no auth：若使用者把 raw Go runtime 或 Caddy 直接對 public internet 開放，notes、uploads、server/system 操作面會變成不可接受風險。文件有警告，但技術上 `PRISM_GO_ALLOW_PUBLIC_BIND=1` 是 escape hatch。

### 需要立刻確認的風險

- P1：修 markdown sanitization 並補 regression，這是導入前最重要修補。
- P2：用測試確認 WAL active write 下 `/api/server/backup/download` / rotate 的一致性。
- P2：確認文字 attachment upload 超限時不留下 DB row 或 partial file。
- P2：確認 no-auth boundary 在 Pi / desktop / local artifact 的實際啟動設定沒有被 release packaging 誤放寬。
- License：補上實體 `LICENSE`，否則外部 fork / commercial / OSS reuse 都有法律不確定性。

## 9. 依賴、license 與維護風險

依賴狀態：

- Frontend `package.json` 有 `package-lock.json`，實際安裝版本由 `npm ls --depth=0` 驗證。
- Go 有 `go.mod` / `go.sum`，`go list -m all` 成功。
- Python requirements 已簡化到 pytest-only，產品 runtime 不依 Python backend。
- 前端主要依賴數量合理：React、Vite、axios、marked、Zustand、Tailwind、dnd-kit、lucide。
- Go 依賴不多但有幾個導入者需注意：`jchv/go-webview2` 是 pseudo-version，`skrashevich/go-webp v0.1.0` 較小眾，`modernc.org/sqlite` 供 pure-Go SQLite。

維護證據：

- `git log -5` 顯示近期 commit 包含 `Update documentation and implement security improvements`、category identity、snapshot retention、V2.5 等，代表本機 repo 近期活躍。
- `git remote -v` 指向 `https://github.com/SamMask/Prism.git`。
- tag 只有 `V2.5` 與 `v1.4.1`；release/tag 節奏看起來不密集。
- 根目錄沒有 `.github/workflows`，CI 健康度未建立。
- README 宣稱 MIT，但缺 `LICENSE` / `LICENSE.md` / `COPYING`，這是導入風險。

未驗證：

- 未查 GitHub live Issues / PR / Releases。
- 未跑 `npm audit` / `govulncheck` / Dependabot / OSV。
- 未確認 release asset `PrismDesktopPortable-v2.5.zip` 是否真的存在於 GitHub release。

## 10. 導入建議

### 可以直接使用的部分

- 個人本機 / Windows portable / trusted LAN 使用流程，前提是只處理可信內容。
- Go primary + SQLite + external data dir 的 local-first runtime 方向。
- REST API 作為本機 agent / automation integration，使用 `docs/API_REFERENCE.md` 建議的 notes/categories/tags/attachments subset。

### 適合 fork 改造的部分

- `go-shadow` 的 SQLite migration / backup / FTS / upload / import-export / server-system handlers。
- React shell、FilterStrip、CommandPalette、ReadingWorkspace、Settings maintenance 等 workflow-first UI。
- `docs/CONTRACTS.md` + `docs/TODO.md` 的 contract-driven development 模式。
- Pi deployment scripts / rollback / snapshot retention 概念。

### 只適合參考的部分

- `go-shadow/main.go` 單檔集成方式：可參考行為，但不建議在新專案直接沿用單檔 9k 行結構。
- 歷史 phase contracts：可參考 governance，但不應把所有歷史 evidence 搬到新專案。
- no-auth local-only boundary：只適合 private local tools，不適合公開產品。

### 不建議引入的部分

- 未 sanitization 的 markdown render path。
- 直接公開 raw Go runtime / Caddy entrypoint。
- 沒補 LICENSE 前直接納入商業或開源再發布流程。
- 未建立 CI 前直接把它當穩定 upstream dependency。

## 11. 修復與改善優先級

### P0

- 問題：本輪未驗證到 P0。
- 影響：沒有發現已知無法啟動、核心功能必壞、資料立即遺失的 current evidence。
- 建議修法：仍需在 release 前跑 full `pytest tests/ -v`、`npm run build`、browser smoke、desktop smoke。
- 涉及檔案：全 repo verification。
- 預估修改成本：低到中，取決於驗證結果。

### P1

- 問題：Markdown rendering 未 sanitization。
- 影響：stored XSS，可在同源 localhost/WebView2 context 呼叫 `/api/*`。
- 建議修法：加入 DOMPurify 或等效 sanitizer，或在 `marked` renderer 禁 raw HTML / unsafe URL；補 `<script>`、`onerror`、`javascript:`、iframe/svg regression。
- 涉及檔案：`frontend/src/components/ReadingView.tsx`、`frontend/src/components/editor/EditablePreview.tsx`、frontend tests。
- 預估修改成本：中。

### P2

- 問題：Attachment upload size gate 與 read limit 不一致。
- 影響：大 `.md/.txt/.markdown` 可能寫入後不可讀或造成磁碟壓力。
- 建議修法：用 `MaxBytesReader` / `LimitReader` 對齊 1 MiB contract，超限時不留下 partial file / DB row。
- 涉及檔案：`go-shadow/main.go` attachment upload path、Go tests、`docs/API_REFERENCE.md` 如需同步限額。
- 預估修改成本：中。

- 問題：Backup WAL snapshot proof 未確認。
- 影響：使用者可能下載到不含最新 WAL transaction 的 DB snapshot，或誤以為 DB backup 包含 uploads/attachments。
- 建議修法：補 WAL active write test；必要時改 SQLite online backup 或 checkpoint strategy，docs 明確區分 DB backup 與 data snapshot。
- 涉及檔案：`go-shadow/main.go` backup handlers、`DEPLOY-PI.md`、server backup tests。
- 預估修改成本：中。

- 問題：Category API invalid input / target validation。
- 影響：外部 Agent 傳錯 payload 可能得到 500，不利診斷。
- 建議修法：wrong type 回 400，invalid/missing/self target 回 400/404，補 tests。
- 涉及檔案：`go-shadow/main.go` category handlers、Go tests。
- 預估修改成本：低到中。

- 問題：No-auth boundary 對外部導入很硬。
- 影響：任何 public exposure 都不可接受。
- 建議修法：短期保持 local/trusted LAN/VPN/proxy auth 文件與 startup guard；不要偷加半套 auth。若要公開使用，另開 auth/RBAC design。
- 涉及檔案：README、DEPLOY-PI、API docs、startup guard tests。
- 預估修改成本：低（維持警告）到高（真的做 auth）。

### P3

- 問題：`go-shadow/main.go` 單檔過大。
- 影響：review / onboarding / regression isolation 成本高。
- 建議修法：不要一次大拆；在修特定 route group 時逐步抽出 migrations、backup、upload、attachments、server/system。
- 涉及檔案：`go-shadow/main.go` 及新 package files。
- 預估修改成本：高。

- 問題：缺 root CI workflow。
- 影響：GitHub 導入者無法看到自動化驗證狀態。
- 建議修法：新增 GitHub Actions，至少跑 Go test、TypeScript no-emit/build、pytest targeted/full 分層。
- 涉及檔案：`.github/workflows/*`。
- 預估修改成本：中。

- 問題：README 宣稱 MIT 但缺 LICENSE。
- 影響：法律可用性不清楚。
- 建議修法：補 MIT LICENSE 檔並確認第三方 license notice。
- 涉及檔案：`LICENSE`、README、release package。
- 預估修改成本：低。

## 12. 評分表

| 評分項目 | 分數 | 理由 | 主要證據 |
|---|---:|---|---|
| 專案定位清晰度 | 8.5/10 | Local-first KMS / prompt tooling 定位清楚，no-AI/no-cloud/no-auth 邊界明確。 | `README.md`、`docs/API_REFERENCE.md`、`docs/TODO.md` |
| 可跑性與開發體驗 | 7.0/10 | 文件與 scripts 清楚，本輪 Go/TS/pytest collect 可跑；但工具鏈新、WebView2/Pi/PowerShell 條件多，full build 未跑。 | `scripts/start_go_primary.ps1`、`scripts/build_go_runtime.ps1`、本輪命令結果 |
| 架構設計 | 7.0/10 | Data flow 與 contracts 清楚；最大扣分是 Go runtime 單檔過大。 | `docs/ARCHITECTURE.md`、`docs/CONTRACTS.md`、`go-shadow/main.go` |
| Code 品質 | 6.5/10 | 錯誤處理與 safety helper 不少；但 monolith、XSS path、attachment/backup TODO 顯示仍有負債。 | `go-shadow/main.go:5546-5725`、`ReadingView.tsx:27-31` |
| UI / UX 或使用流程 | 7.5/10 | Shell、command palette、filters、reading workspace、settings 完整；本輪未做 browser smoke，且 markdown XSS 影響信任。 | `Layout.tsx`、`HomePage.tsx`、`CommandPalette.tsx`、`docs/TODO.md` |
| 測試與穩定性 | 8.0/10 | 352 tests collected，Go tests 通過，contract tests 很厚；缺 CI、full suite 本輪未跑，仍有明列缺口。 | `pytest collect-only`、`go test ./...`、`.loop/verify-gate.ps1` |
| 安全性 | 5.8/10 | Public bind、SSRF、CSRF 有 guard；但 stored XSS + no-auth 是導入阻礙。 | `go-shadow/main.go:520-534`、`:1606-1630`、`ReadingView.tsx` |
| 依賴與維護風險 | 6.5/10 | lockfiles 存在、依賴量合理、近期 commits 活躍；缺 LICENSE、缺 CI、未做 live audit。 | `package.json`、`go.mod`、`git log -5`、`Test-Path LICENSE=False` |
| 文件品質 | 8.0/10 | 文件非常完整且 current truth 明確；但歷史 docs 過多、新人可能迷路，且 CONTRIBUTING 有 e2e 路徑小落差。 | `docs/README.md`、`docs/API_REFERENCE.md`、`docs/TODO.md` |
| 導入適配度 | 6.8/10 | 作為 local-first fork 很有價值；作為直接 dependency / public service 不適合。 | no-auth docs、LICENSE 缺失、monolith、tests |

總體分數：7.1/10。這不是平均值；安全與導入風險被加權提高，因此雖然文件/測試分數高，整體仍不建議無修改直接導入到公開或多使用者產品。

## 13. 總結

這專案是不是看起來比實際成熟？  
部分是。文件、contract 與測試讓它看起來很成熟，而且核心 local-first runtime 也確實可用；但安全產品化、license、CI、monolith 維護性還沒到可無痛外部導入的水準。

它最大的價值是什麼？  
一套已落地的 Go + React + SQLite local-first knowledge tool：有 REST API、Windows portable、Pi deployment、external data dir、FTS/search、import/export、backup、maintenance UI 與大量 regression/contract evidence。

它最大的坑是什麼？  
安全邊界高度依賴「本機可信環境」。一旦處理不可信 markdown 或暴露到公網，`marked()` + `dangerouslySetInnerHTML` 與 no-auth surface 會讓風險立刻升高。

如果我要拿來接進自己的工具鏈，建議怎麼做？  
先 fork，不要直接當 upstream dependency。第一步補 LICENSE 與 CI；第二步修 markdown sanitizer；第三步針對你的部署方式確認 auth/exposure boundary；第四步只接 `docs/API_REFERENCE.md` 建議的 notes/categories/tags/attachments 最小 API subset。若只是本機私人工具，可以先用；若要多人或 public access，先另開完整 auth / permission / audit design。
