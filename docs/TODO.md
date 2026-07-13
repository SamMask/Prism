# Prism Active TODO

本檔只保留目前可施工的 active roadmap、候選 backlog 與下一步入口。完成紀錄、舊 phase 與長版 changelog 全部移到 `docs/development-history/`。

閱讀方式：

- `[x]` = 已完成，並且本檔保留必要驗證證據或歸檔入口。
- `[ ]` = 尚未施工、等待 promote、或 blocked/deferred；看括號內 `Todo` / `Blocked` 判斷能不能直接做。
- 狀態欄位固定使用：`Todo` / `Doing` / `Blocked` / `Review` / `Done`。未 promote 的候選項維持 `Todo`；缺少明確需求、決策 gate 或安全前提的項目標 `Blocked`；只有正在施工的單一 active item 才標 `Doing`。

---

## Current Truth（2026-07-14）

- Go primary 是唯一 current runtime owner；Python Flask backend source 已於 T053 移除。完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Prism V2.6.1 已依使用者明確決策完成同版顯示遺漏重發：annotated tag、GitHub Release與`PrismDesktopPortable-v2.6.1.zip`均對齊修正commit `7f5469c16cac2a8412bb5f2524cc4e9884256db3`；既有V2.6 tag/asset未改寫，沒有建立V2.6.2。
- Windows portable current path：`Prism.exe` GUI app + WebView2 + same-process Go runtime；預設資料在 exe 同層 `PrismData\`。`--data-dir` / `PRISM_GO_DATA_DIR` 只作進階/debug override。
- V2.6.1 release notes / README 已說明 unsigned portable、Windows SmartScreen、GitHub download Mark-of-the-Web (`Zone.Identifier`)、SHA256 驗證與 `Unblock-File` 流程。沒有購買或加入 code signing。
- Pi delivery 與 GitHub release package 是兩條流程。Pi live deploy 必須依 `DEPLOY-PI.md` 使用 Go primary live ops；GitHub Actions 只做 validation，不自動上傳 release asset。
- 2026-07-14 修正後V2.6.1已重新部署到`PI5Mask24`：Go primary active/enabled、legacy `prism.service` inactive/disabled、Caddy active，runtime `2.6.1`、schema v17 pending empty；full workflow、5-sample soak與Playwright title/sidebar/About live smoke通過。證據見`docs/development-history/v2.6.1-about-version-correction-20260714.md`。
- Prism 仍沒有內建 auth/token layer；safe boundary 是 localhost、trusted LAN、VPN、SSH tunnel，或外部 auth 保護的 reverse proxy。不得把 API 寫成可直接 public internet 暴露。
- V2.5 近期完成項已歸檔到 `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`，包含 Reading workspace、variant tracking、note-list preview、image lightbox/zoom、batch import、starred tags、category identity、deep scan 01A-01G、project review hygiene 01A-01E 與 release/package evidence。
- `build/` 只應保留最新 release 產物；不得把 DB、attachments、notes、uploads 等真資料當 build artifact 清理。
- `docs/GOVERNANCE.md` 是完成宣稱、狀態層級、驗證證據、委派與 UI/UX governance 的 current entry；新版治理素材已保留到 `docs/development-history/governance-source-20260705/`，正式文檔不依賴暫存素材目錄。

Current truth 仍以本檔、`HANDOFF.md`、`docs/ARCHITECTURE.md`, `docs/SCHEMA.md`, `docs/API_REFERENCE.md` 與實際 source/runtime 為準。不得因歷史報告曾討論過，就直接擴 scope 成 AI、semantic search、GraphRAG、auto-writing、schema/API/runtime 或 Pi deploy 變更。

---

## Progress At A Glance

- [x] `MARKDOWN-SYNTAX-CANDIDATE-01`（狀態：`Done`）：已完成低風險 Markdown renderer / preview slice，包含 GFM table/task list/code copy/heading anchor/ReadingView outline，以及 GitHub alert、footnote、`==highlight==`、MarkForge box/details prose extensions。
- [x] `KWF-01 Command Palette server-side search`（狀態：`Done`）：Command Palette 已能用既有 `/api/notes?q=...` 做全庫純關鍵字搜尋，且已完成 Pi live deploy evidence。
- [x] `KWF-02 Saved Search / Search Workspace`（狀態：`Done`）：Home 已能把目前 query/filter/sort view 保存成瀏覽器本機 Search Workspace，localStorage key `prism.savedSearchWorkspaces.v1`，不改 DB schema。
- [x] `NOTE-DELETE-MEDIA-UX-CANDIDATE-01`（狀態：`Done`）：已補刪卡片 / 批次刪除確認框與 Settings「清理未使用圖片」copy；runtime 已有 reference-counted cleanup，本輪未改 Go delete/media cleanup semantics。
- [x] `KWF-03` 到 `KWF-07`（狀態：`Done`）：full data snapshot script、batch delete dry-run write guard、import dry-run/collision preview、ReadingView source URL panel 已完成；knowledge quality metadata 已依個人筆記庫定位明確不採用。2026-07-08 已通過 local release validation並部署到 Pi live；未做 auth、semantic search 或 schema migration。
- [x] `GO-MAIN-SPLIT-CANDIDATE-01`（狀態：`Done`）：`GMS-00` 到 `GMS-10` 已完成同 package mechanical extraction；`main.go` 從 10,246 行降到 1,024 行，所有新 bounded-context 檔案均不超過 1,500 行，runtime/API/schema 行為未變。
- [x] `RELEASE-V2.6`（狀態：`Done`）：2026-07-08 KWF improvements 與 2026-07-13 Go source decomposition 已發布；local/full/browser/package/privacy/tag/push/Actions/asset/read-back gates 全部通過，並於 2026-07-14 另走 Pi live gate完成部署。
- [x] `PI-V2.6-LIVE`（狀態：`Done`）：V2.6 artifact、snapshot、service ownership、API/UI smoke與 bounded soak全部通過；唯一 non-blocking finding 是 browser title/sidebar brand仍顯示 V2.5。
- [x] `FRONTEND-LABEL-AND-RESEARCH-ARCHIVE-01`（狀態：`Done`）：browser title / sidebar brand 已對齊 V2.6；2026-07-01 深入研究報告已完成 current-truth resolution 並移至 development-history。本 gate 未重發 release、未部署 Pi。
- [x] `RELEASE-V2.6.1-LABEL-HOTFIX`（狀態：`Done`）：title/sidebar label修正版已發布為 immutable patch release `V2.6.1`並部署到 `PI5Mask24`；Actions、asset read-back、Pi full workflow、5-sample soak與live Playwright labels均通過，既有 `V2.6` tag/asset未重寫。
- [x] `V2.6.1-ABOUT-VERSION-CORRECTION`（狀態：`Done`）：Settings「關於」缺省版本已從`2.5`修正為`2.6.1`；title/sidebar/About三處一致性、同版GitHub Release重發、Pi重新部署與live smoke/soak均已驗證。
- [ ] Heavy renderer / installer / updater / AI 類項目（狀態：`Blocked`）：只有使用者明確重新開啟需求或 decision gate，才可施工。

目前沒有`Doing` item。下一個最低風險入口仍是test-only `main_test.go` bounded-context split candidate，不得延伸成runtime redesign。

---

## Remaining Work Summary

人類版：Prism 目前主線已經穩定在 Go primary、V2.6.1 portable / Pi live 與基本 Markdown / Command Palette / Saved Search / snapshot / import preview / source URL 工作流。完整資料快照已有本機 script可dry-run或輸出zip；批次刪除與匯入都有寫入前preview，ReadingView會顯示既有source URLs與重複標記。2026-07-14 V2.6.1 immutable tag、Actions、portable asset/read-back、Pi cutover/full workflow/5-sample soak與live label smoke均完成；browser title與sidebar brand均為V2.6.1。schema仍為v17，沒有migration。

LLM 接續版：先讀 `AGENTS.md`、`HANDOFF.md`、`docs/GOVERNANCE.md`、本檔、`docs/ARCHITECTURE.md`、`docs/SCHEMA.md`、`docs/API_REFERENCE.md`；V2.6.1 release/Pi live label hotfix、GMS與2026-07-01 research intake歸檔已完成。Go source assertion應檢查整個`go-shadow`非測試package source，不得再假設所有handler都位於`main.go`；route registration仍由`main.go`擁有。下一個maintenance候選是`main_test.go` test-only split；不得重開schema v18 review metadata，除非產品用途改變。

---

## Completed Items Kept In This Active File

### [x] MARKDOWN-SYNTAX-CANDIDATE-01 Port MarkForge-MD supported Markdown syntax into Prism

狀態：`Done`

來源：2026-07-05 使用者要求把 `D:\AI\MarkForge-MD` 支援的 md 語法支援到 Prism，且 Markdown 語法支援列優先。

實際對照：MarkForge-MD current renderer 已支援 CommonMark / GFM-like table、task list、fenced code、syntax highlighting、相對/本機圖片 preview、GitHub alert、footnote、code block copy、outline、Mermaid、KaTeX、白名單 HTML、`==highlight==`、MarkForge box/details 與 ABC 樂譜 fence。Prism current renderer 使用 `marked` (`gfm=true`, `breaks=true`) + `DOMPurify`，共用入口是 `frontend/src/utils/markdown.ts`；本輪只接低風險 preview fidelity，不搬 renderer stack。

目標：把高頻、可維護、低風險的 MarkForge-compatible Markdown 顯示能力帶進 Prism 的 ReadingView / editor preview；先做前端 preview fidelity，不改 note schema、import/export contract、search contract、DB migration 或 Go runtime storage semantics。

完成範圍：

- [x] `MDS-01 Renderer contract audit`（狀態：`Done`）：`tests/test_markdown_sanitization.py` 已鎖住 ReadingView / EditablePreview 只能走共用 `renderSafeMarkdown()` + DOMPurify sanitizer path，並保留 unsafe tag / unsafe protocol boundary regression。
- [x] `MDS-02 Low-risk GFM preview UX`（狀態：`Done`）：`marked` 產出的 table、task list、code fence、heading 以 render 後 DOM helper 補 responsive table wrapper、task list 視覺、code-copy button、heading id/anchor；ReadingView 右側補 TOC/outline。沒有改 Markdown source，也沒有新增 WYSIWYG。
- [x] `MDS-03 MarkForge prose extensions`（狀態：`Done`）：本地 parser helper 支援 GitHub alert、footnote、`==highlight==`、`:::markforge-box info|success|warning`、`:::markforge-details title`，仍走 DOMPurify allowlist；未允許任意 CSS、`style`、script、iframe/object/embed、遠端 renderer 或 plugin host。
- [x] `MDS-04 Code syntax highlighting`（狀態：`Done`）：本次評估後不導入 `highlight.js` 或新 dependency；只補 code block copy 與可讀樣式。若未來需要語法高亮，另開 bundle/security review。

未施工 / blocked：

- [ ] `MDS-05 Mermaid decision gate`（狀態：`Blocked`）：本次未導入。若未來要支援圖表渲染，必須離線渲染、可設定開關、錯誤只影響該 block、render timeout、有 sanitizer / protocol boundary regression，並明確處理 export/preview fidelity 差異。
- [ ] `MDS-06 KaTeX math / ABC score optional renderer freeze`（狀態：`Blocked`）：2026-07-05 使用者決策：數學公式與樂譜顯示暫時凍結為備選，不列入下一個 Markdown renderer 入口。只有使用者明確需要把公式或樂譜當知識卡片顯示時，才另開離線 renderer / bundle / safety gate。

驗證證據：

- `pytest tests/test_markdown_sanitization.py tests/test_image_viewer_lightbox.py::test_reading_view_collects_cover_and_markdown_images -v`：5 passed。
- `cd frontend && npm run build`：passed；僅有既有 Browserslist outdated 與 Vite chunk-size warning。
- `pytest tests/ -v`：已跑完整套件一次，該次結果為 344 passed / 20 failed；其中 ReadingView handler name regression 已在本 slice 修正並以 targeted test 驗過，其餘失敗集中在 TODO/HANDOFF 瘦身後仍期待舊 `[x]` 歷史條目的既有 docs regression。
- 未新增 dependency，未引入 AI/ML、CDN、背景服務、遠端 renderer、schema/API change 或 editor rewrite。
- 未跑 Playwright screenshot smoke；本 slice 以 targeted regression + TypeScript/Vite build 作為驗收證據。

不做：

- 不追「所有 Markdown dialect」；只做 MarkForge 已證明且 Prism 高頻可用的子集。
- 不把 MarkForge 的 Tauri local-file asset scope、desktop file association、installer behavior 搬進 Prism。
- 不把 Markdown syntax gate 順手擴成 import/export 重做、搜尋重做、schema 欄位新增或 Pi deploy。

### [x] KWF-01 Command Palette server-side search

狀態：`Done`

- [x] `KWF-01 Command Palette server-side search`（狀態：`Done`）：Command Palette 輸入 `? xxx` 或至少 3 個字元時，debounced 呼叫既有 `api.getNotes({ search: xxx, per_page: N })` 顯示全庫結果；保留 navigation / recent / new note / theme actions。這是最小搜尋工作流改良，不改後端搜尋引擎。
  - 完成：新增 `results` 分組、loading / empty / error / count 狀態、四語 i18n、server result 點開前依 `content_truncated` 補抓完整 note detail。
  - 邊界：沒有改 Go API、FTS/search contract、DB schema、Pi deploy、auth 或 public internet exposure policy。
  - 驗證：`pytest tests/test_command_palette_server_search.py tests/test_phase22_command_palette_entrypoint_reliability.py tests/test_frontend_i18n_settings.py::test_active_ui_final_i18n_namespaces_are_translated_for_four_locales tests/test_frontend_i18n_settings.py::test_active_ui_final_components_use_i18n_for_extracted_strings -v`：11 passed；`cd frontend && npm run build`：passed，僅既有 Browserslist / chunk-size warning；`git diff --check`：passed，僅 Windows CRLF warning；`pytest tests/ -v`：349 passed / 19 failed，失敗仍集中在 TODO 瘦身後舊測試期待歷史 `[x]` 條目的既有 docs regression，KWF-01 tests 皆通過。
  - Pi live deploy：2026-07-05 已用 `powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` 推到 `PI5Mask24`。Artifact sha256 `b1216cc1aefcc893db9b867e97960de3bb3e4689a739ee8227b5fd4738dcb871`；pre-cutover snapshot `/home/mask070924/prism/backups/go-primary-t042-20260705_012430`；`prism-go-primary.service` active、legacy `prism.service` inactive、Caddy active；`/api/system/migration-status` current/latest v17 且 pending empty；`/api/notes?q=prompt&per_page=1&include_archived=true` success；served JS contains `command-palette-server-search-status`；local evidence at `build/go-primary-live/pi/evidence.json`。

---

## Open TODO Items

### [x] V2.6.1-ABOUT-VERSION-CORRECTION Correct the missed Settings About version surface

狀態：`Done`

來源：2026-07-14 live 使用畫面顯示 browser title 與 sidebar 已是 V2.6.1，但 Settings「關於」仍顯示 2.5。Source 確認 `SettingsPage.tsx` 的 `stats?.version` 缺省值仍硬編碼為 `2.5`；先前 label smoke 只驗 title/sidebar，沒有覆蓋 About tab。

目標與停止條件：

- [x] `A261-00 Regression lock`：source regression已鎖定title `Prism V2.6.1`、sidebar `V2.6.1`、About fallback `2.6.1`，並禁止三處回退到V2.5/2.5；兩個targeted tests在product edit前如預期失敗，edit後通過。
- [x] `A261-01 Minimal UI correction`：只把Settings About缺省版本從`2.5`修正為`2.6.1`；沒有新增版本管理抽象、dependency、API、schema、migration或產品功能。
- [x] `A261-02 Fresh local release validation`：full gate 382 pytest + Go tests、frontend/Go build、9 Chromium e2e、Go artifact/package smoke、portable clean-unzip、packaged runtime version、三處Playwright、privacy gates全部通過。Zip 21,671,554 bytes，SHA256 `8705C5F5CBCC24A3EEFBBC02E02695B0103CB04E879770A488D2A4429D229F17`。
- [x] `A261-03 Same-version GitHub reissue`：V2.6.1 annotated tag已取代到修正commit`7f5469c`；Actions run `29276993209` success。Release asset 21,671,554 bytes，GitHub digest、local與fresh download SHA256均為`8705C5F5CBCC24A3EEFBBC02E02695B0103CB04E879770A488D2A4429D229F17`；既有V2.6未修改。
- [x] `A261-04 Pi redeploy and live verification`：依`DEPLOY-PI.md`完成Cutover與Soak；artifact SHA256 `1c1ff025f8653a48e97d87cbb29afa09d09e9ca8e020fef329d1e395e2fce01d`，latest snapshot `/home/mask070924/prism/backups/go-primary-t044-20260714_031146`。Go active/enabled、legacy inactive/disabled、Caddy active、schema v17 clean、full workflow與5-sample soak通過；live Playwright確認title/sidebar/About全為V2.6.1且console 0 errors/0 warnings。
- [x] `A261-05 Closure`：TODO/HANDOFF/release checklist/history與GitHub Release body已回寫；main/tag/release/asset/Pi runtime evidence一致，沒有建立V2.6.2。

邊界：這是同版顯示遺漏修正，不建立 V2.6.2；不改 API/schema/DB/search/auth/exposure boundary，也不動 Pi 上未接 Caddy live 流量的 readonly/staging輔助service。

### [x] RELEASE-V2.6.1-LABEL-HOTFIX Publish and deploy frontend label fix

狀態：`Done`

- [x] `R261-00 Release/live preflight`：Git/gh/remote原先對齊且gh已登入；Pi SSH alias、aarch64、磁碟、Go active/enabled、legacy inactive/disabled、Caddy active、runtime 2.6與migration v17 clean均確認。
- [x] `R261-01 Version and release evidence`：runtime/docs/package已對齊2.6.1；full gate 382 passed + Go tests、frontend build、9 e2e、Go smokes、portable clean-unzip、packaged version、Playwright labels與privacy sweep全部通過。Zip 21,671,433 bytes，SHA256 `7312213255770862BBFD057C568F70AC2F65DB7662CFDCAFC187552A298BD550`。
- [x] `R261-02 Commit/tag/push/release`：Lore commit `80aa35a`與annotated `V2.6.1` tag已push；Actions run `29274092387` success；Release https://github.com/SamMask/Prism/releases/tag/V2.6.1 已發布。GitHub digest、local hash與重新下載SHA256均為 `7312213255770862BBFD057C568F70AC2F65DB7662CFDCAFC187552A298BD550`。
- [x] `R261-03 Pi cutover`：`go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` passed；linux/arm64 artifact SHA256 `7612012cbeb336f15bf9c97d9b162b27541f8f308e31a84245f931e53d0a27e8`；pre-cutover snapshot `/home/mask070924/prism/backups/go-primary-t042-20260714_022829`，retention keep-5 passed。
- [x] `R261-04 Live verification`：Go primary active/enabled、legacy inactive/disabled、Caddy active、version 2.6.1、schema v17 clean、full workflow與5-sample soak passed；Playwright live確認title `Prism V2.6.1`、sidebar `V2.6.1`、console 0 errors/0 warnings。既有localhost-only read-only sidecar 5002與staging 5003不接Caddy流量，本gate未變更。
- [x] `R261-05 Closure`：TODO/HANDOFF/release validation已回寫；既有 `V2.6` tag/release asset未修改。

### [x] FRONTEND-LABEL-AND-RESEARCH-ARCHIVE-01 V2.6 顯示修正與研究 intake 歸檔

狀態：`Done`

來源：2026-07-14 Pi live smoke 發現 browser title 與 sidebar brand 仍顯示 V2.5；同輪使用者要求整理根目錄的 2026-07-01 深入研究報告，標記已完成與已歸納事項後移入歷史歸檔。

目標與停止條件：

- [x] `FLR-00 Regression lock`：source regression 已鎖住 `frontend/index.html` 與 `Sidebar.tsx` 均顯示 V2.6，並鎖住研究報告不再留在 repo root、歸檔檔含 current-truth resolution。
- [x] `FLR-01 Frontend label alignment`：只修正 browser title 與 sidebar brand；未新增 runtime version fetch、config layer 或 dependency。
- [x] `FLR-02 Research intake closure`：歸檔報告已加入 2026-07-14 resolution，分清已完成／已吸收、部分完成／候選、明確不採用／blocked；個人筆記庫不採 review metadata / workflow，除非用途改變。
- [x] `FLR-03 Archive and index`：已移至 `docs/development-history/2026-07-01-深入研究-deep-research-report-Prism.md`，並更新文檔索引、TODO 與 HANDOFF。
- [x] `FLR-04 Verification`：36 個相關 pytest與完整 `pytest tests/ -v` 381 passed；`scripts/build_go_runtime.ps1` passed（含 frontend production build與 `go test ./...`）；隔離 Go runtime 的 Playwright smoke確認 Page Title `Prism V2.6`、sidebar `V2.6`、console 0 errors / 0 warnings；`git diff --check` 與 AGENTS/CLAUDE mirror check通過。

邊界：本 gate 不改 API/schema/DB/search semantics，不重包或重發 V2.6 tag/release，不自動部署 Pi。Pi 現有 V2.6 artifact仍會顯示舊 label，直到另行 republish/redeploy。

### [x] GO-MAIN-SPLIT-CANDIDATE-01 Incremental `go-shadow/main.go` bounded-context decomposition

狀態：`Done`

來源：2026-07-13 使用者確認要把超過一萬行的 Go runtime 大檔正式規劃進 TODO 並細拆工作；此 candidate 將 `DEEP-SCAN-RISK-CANDIDATE-01` 01H 的 `route-local Go 小整理` 明確化，但不解除「一次性 Go runtime 大拆分」的 `Blocked` 邊界。

實際對照：

- `go-shadow/main.go` 拆分前 baseline 為 **10,246 physical lines / 312,452 bytes**；當時同檔包含 bootstrap、route registration、runtime config、SQLite owner/migrations、system/server、backup/restore、prompt/wizard config、import/export、uploads/media cleanup、taxonomy、attachments、notes/search/actions/history。
- `go-shadow/main.go:275-354` 的 runtime construction / mux registration 是 central wiring，本 candidate 全程保留在 `main.go`，避免拆檔變成 router/runtime redesign。
- 現有 `go-shadow/main_test.go` / `restore_test.go` 已覆蓋 migrations、categories/tags、attachments、uploads/SSRF、notes/search/actions/history、backup/WAL/restore、CSRF 與 static boundaries；每一刀先沿用既有 regression，只有發現實際缺口才先補 test。
- 詳細完成紀錄：`docs/development-history/go-main-split-completion-20260713.md`。

目標與停止條件：

- 只做同一個 `package main` 內的 declaration relocation；新增的是按既有 bounded context 命名的 `.go` 檔，不新增 package directory、service、repository、interface、manager、registry、adapter 或 dependency。
- 每個 gate 只搬一個可獨立驗收的責任群組；除 per-file imports / `gofmt` 外，不改函式名稱、signature、route registration、SQL、response/error 文字、feature flags、safety limits 或 side effects。
- 最終讓 `main.go` 只保留 bootstrap、runtime config/connection ownership、route registration、middleware 與真正 shared helpers；降到 **4,000 physical lines 以下即停止**，不得只為追求更低行數繼續碎片化。
- 任何 gate 若需要 API/schema/DB/data-dir/desktop/package/deploy 行為變更、新抽象或跨 package，立即停止並另開 decision gate；本 candidate 不部署 Pi、不重包 release。

施工順序（一次只 promote 一項）：

- [x] `GMS-00 Baseline and mechanical-split contract lock`（狀態：`Done`）：已新增 `CONTRACT-GO-MAIN-MECHANICAL-SPLIT`，鎖定 10,246 lines / 312,452 bytes baseline 與同 package/no-behavior-change 邊界；拆檔前 `cd go-shadow && go test ./...` passed。
- [x] `GMS-01 Attachment routes mechanical extraction`（狀態：`Done`）：新增 `go-shadow/attachments.go`（344 行），附件 metadata/text/raw/write 與 path safety declarations 純搬檔完成。
- [x] `GMS-02 Taxonomy routes mechanical extraction`（狀態：`Done`）：新增 `go-shadow/taxonomy.go`（647 行），categories/tags handlers 與 conflict helpers 純搬檔完成。
- [x] `GMS-03 Migration lifecycle mechanical extraction`（狀態：`Done`）：新增 `go-shadow/migrations.go`（692 行），ordered migrations、fresh init/seeds、status 與 backup-before-migrate 純搬檔完成；schema 仍為 v17，SQL 未改。
- [x] `GMS-04 Backup/restore mechanical extraction`（狀態：`Done`）：新增 `go-shadow/backups.go`（526 行），backup/restore/retention/path validation 純搬檔完成。
- [x] `GMS-05 System/runtime administration mechanical extraction`（狀態：`Done`）：新增 `go-shadow/system.go`（904 行），health/system/server/CSRF/FTS/port/log/restart/version handlers 純搬檔完成；mux registration 仍在 `main.go`。
- [x] `GMS-06 Prompt/wizard options mechanical extraction`（狀態：`Done`）：新增 `go-shadow/options.go`（532 行），prompt/wizard/data-dir JSON config helpers 純搬檔完成。
- [x] `GMS-07A Import mechanical extraction`（狀態：`Done`）：新增 `go-shadow/import.go`（750 行），JSON/Markdown import、frontmatter、image restore、rollback cleanup 與 category import helpers 純搬檔完成。
- [x] `GMS-07B Export mechanical extraction`（狀態：`Done`）：新增 `go-shadow/export.go`（816 行），JSON/Markdown/DB/images/batch export、ZIP 與 filename helpers 純搬檔完成。
- [x] `GMS-08A Image metadata extraction`（狀態：`Done`）：新增 `go-shadow/image_metadata.go`（243 行），prompt metadata / PNG text parsing 純搬檔完成。
- [x] `GMS-08B Upload/remote-fetch extraction`（狀態：`Done`）：新增 `go-shadow/uploads.go`（575 行），upload/delete/remote fetch、SSRF/DNS/redirect、MIME/size、thumbnail helpers 純搬檔完成。
- [x] `GMS-08C Media-cleanup extraction`（狀態：`Done`）：新增 `go-shadow/media_cleanup.go`（873 行），orphan/original/broken-image handlers 與 reference-counted cleanup helpers 純搬檔完成。
- [x] `GMS-09 Notes/search/actions decomposition decision gate`（狀態：`Done`）：重新依 symbol ownership 拆成 `notes_search.go`（642 行）、`notes_write.go`（478 行）、`notes_media.go`（205 行）、`notes_actions.go`（1,216 行）；每檔均低於 1,500 行，另保留真正 shared declarations 於 `main.go`。
- [x] `GMS-10 Structural closure and archive`（狀態：`Done`）：`main.go` 已降到 1,024 行；16 個本次 source 檔均 ≤1,500 行。425 個 top-level declarations 經 AST formatting 比對與拆檔前 `HEAD` 完全一致；full Go/Python verification、runtime build、local artifact/package smoke 與 package/privacy sweep 均通過。完成證據見 `docs/development-history/go-main-split-completion-20260713.md`。

每個 code-moving gate 的固定驗收：

- gate-specific targeted Go tests。
- `cd go-shadow && go test ./...`。
- `pytest tests/ -v`。
- `git diff --check`，並人工確認 route registration、handler signatures 與 moved function bodies 沒有邏輯 drift。
- `GMS-03`、`GMS-06`、`GMS-10` 加跑 `scripts/build_go_runtime.ps1`；本 candidate 不以 docs-only 或單次 compile 取代 runtime regression。

明確不做：

- 不把 Go monolith 改成 microservices、Clean Architecture 或多 package layering。
- 不新增功能、API、schema/migration、dependency、fallback、compat layer、logging/config/cache layer。
- 不順手整理 `main_test.go`、前端、i18n、bundle warning、Browserslist、installer/updater、release 或 Pi deploy。
- 不把「一次性 Go runtime 大拆分」從 `Blocked` 改成可施工；本 candidate 只授權上述依序的小 gate。

### [x] KNOWLEDGE-WORKFLOW-CANDIDATE-01 Local-first knowledge workspace improvements after Markdown candidate

狀態：`Done`

來源：2026-07-05 使用者貼上的 ChatGPT 優先序建議；依 Prism current docs/source 實際狀態評估後吸收到 TODO。Markdown syntax support 仍列優先，本 candidate 排在 Markdown 之後。

實際對照：

- `GET /api/notes?q=...` 已支援 title/content FTS5、remarks、tags、attachment metadata 與 bounded text attachment body scan，且仍是純關鍵字搜尋；API 也已有 category、tags、archived、pinned、sort 等條件。
- server backup/download 與 rotate 是 DB-only；`DEPLOY-PI.md` 與 API docs 已明確指出 DB backup 不包含 `static/uploads/` / `docs/attachments/`，不同於 deploy data snapshot。
- Prism 無內建 API token / Bearer token / 使用者認證；文件已要求 localhost、trusted LAN、VPN、SSH tunnel 或外部 auth reverse proxy。
- Settings 批次 Markdown/TXT 匯入仍是前端逐檔 wrapper，沒有 server-side batch import API，也沒有 dry-run / collision preview。

採納項目與施工順序：

- [x] `KWF-02 Saved Search / Search Workspace`（狀態：`Done`）：Home 已新增 Search Workspace bar，可保存 / 套用 / 刪除目前 query、category、tag、archived、sort view。保存資料只寫入瀏覽器 localStorage key `prism.savedSearchWorkspaces.v1`，沒有新增 DB migration、Go API、semantic search、auth 或 Pi deploy；若未來要跨裝置，再另開 schema gate。
- [x] `KWF-03 Full data snapshot export`（狀態：`Done`）：新增 `scripts/export_full_data_snapshot.ps1`，支援 `-DryRun` 與 zip export，明確打包 `knowledge.db`、`knowledge.db-wal`、`knowledge.db-shm`、`static/uploads/`、`docs/attachments/`、`docs/notes/`、`config/` 與 `snapshot-manifest.json` sha256 manifest。這是 full data snapshot，不是 DB-only backup；本輪只做 local script / fixture smoke，未碰 live Pi。
- [x] `KWF-04 Agent-safe write guards`（狀態：`Done`）：`POST /api/notes/batch/delete` 支援 `dry_run: true` destructive preview，回報 requested / deletable / missing / image / attachment counts 與 note title preview；前端批次刪除 confirm 先呼叫 dry-run，再執行真正 batch delete。這不是 auth，不得宣稱能安全 public exposure。
- [x] `KWF-05 Import dry-run / collision preview`（狀態：`Done`）：Settings 批次 Markdown/TXT 匯入在寫入前顯示本機 dry-run preview，回報 create / duplicate collision / unsupported counts；仍只用既有 `.md` 單檔 import endpoint 與 `.txt` 前端讀檔建立 note，不新增 watcher、sync daemon 或 server-side batch import API。
- [x] `KWF-06 Source URL panel`（狀態：`Done`）：ReadingView 右側欄利用既有 note `urls` 顯示 source URL panel，包含 domain 顯示、原 URL、duplicate URL detection；未做 web clipper、外網 title fetch 或 link health background check。
- [x] `KWF-07 Knowledge quality metadata decision gate`（狀態：`Done`）：2026-07-14 使用者決策為不採用 `status / review_state / last_verified_at` 與 schema v18 審核工作流。Prism 是個人筆記庫，不需要內容審核狀態干擾；除非產品用途明確改變，否則不得重新 promote 此 metadata/schema gate。`docs/SCHEMA.md` 維持 current Migration v17。

不採納 / deferred：

- [ ] 內建登入、多使用者、OAuth、RBAC、cloud sync、semantic search、embeddings、GraphRAG、directory watcher、background sync daemon、大型備份平台、一次性 editor rewrite、一次性 Go runtime 大拆分（狀態：`Blocked`）。
- [ ] Source URL 自動抓 title / link health 若需要外網或批次請求，必須另開 privacy / timeout / user-triggered boundary，不得在讀取 note 時背景追蹤遠端 URL（狀態：`Blocked`）。

驗收候選：

- KWF-02 已以 `pytest tests/test_kwf02_saved_search_workspace.py tests/test_note_delete_media_ux_copy.py -v`、相關 i18n/Home targeted tests、`cd frontend && npm run build` 與 Browser smoke 驗證 saved view persistence / filter restore 基本路徑；本輪未新增 backend/API/DB contract。Browser smoke 在 `http://127.0.0.1:5173/` 驗證 Home 可載入、Search Workspace bar 可見、保存後 chip 出現、刪除後回到 empty state；Go backend 5004 未啟動，因此 console 有既有 API fetch errors。
- KWF-03..07 驗收：`pytest tests/test_kwf03_to_kwf07_workflow.py -v`、`cd go-shadow && go test -run TestBatchDeleteDryRunPreviewsWithoutDeletingRowsOrFiles -count=1`、snapshot script fixture dry-run、frontend build、`git diff --check`。2026-07-08 local release validation / Pi deploy gate 已補跑：`.loop/verify-gate.ps1` passed（含 full `pytest tests/ -v` 379 passed、`cd go-shadow && go test ./...` passed、mirror check / `git diff --check` passed）、Go package smoke passed、local artifact smoke passed、desktop portable smoke passed、browser e2e 9 passed、privacy/package sweeps passed；Pi Cutover evidence `build/go-primary-live/pi/evidence.json`，live migration v17 no pending，batch delete dry-run API success，served JS contains batch preview / import preview / source URL panel hooks。

### [x] NOTE-DELETE-MEDIA-UX-CANDIDATE-01 Deleting notes and unused images copy

狀態：`Done`

來源：2026-06-19 使用者回報，下載版新增有圖片的卡片後，單張刪除或批次刪除 note 時，體感上關聯 upload 圖片檔不一定會一起刪；使用者也指出「不要無條件一起刪」有安全上的好處，目前可用「清理未使用的圖片」事後處理。

目標：先把這個行為當成 UX / documentation candidate，不直接改 runtime deletion semantics。

已決定 / current truth：

- Go primary / API current behavior：刪除 note 時會嘗試清理從 note content / cover_image 偵測到、且未被其他 note 引用的 `/static/uploads/` 圖片；同時處理 original / `_thumb.webp` companion。
- 這不是「無條件 cascade 刪圖」。shared references 會保留；未被 delete handler 偵測到的 leftover/orphan 檔案仍由 Settings「清理未使用圖片」或圖片管理入口處理。
- 此 candidate 的決定是補 UX copy，避免使用者把「刪卡片」誤解成「所有相關圖片檔一定被刪乾淨」，同時不改現有 Go delete/media cleanup runtime。

完成範圍：

- [x] 可施工方向 A（狀態：`Done`）：在刪除 note/批次刪除確認框加一句短 copy，說明已偵測且無其他引用的圖片會被清理，但 shared/未偵測/orphan 圖片可到 Settings 清理未使用圖片檢查。
- [x] 可施工方向 B（狀態：`Done`）：在 Settings 清理未使用圖片區塊補說明，標明刪除 notes 後留下的未引用圖片會在這裡掃出。
- [ ] 可施工方向 C（狀態：`Blocked`）：若未來真的要新增更強的「跟著刪圖」行為，只能另開 opt-in decision gate，例如「同時刪除只被這些卡片使用的圖片」，且預設不勾。

驗證證據：`tests/test_note_delete_media_ux_copy.py` 鎖定 confirmation / Settings copy 與 docs closure；`cd frontend && npm run build` passed（僅既有 Browserslist / chunk-size warning）。本輪只補 confirmation / Settings copy，未改 Go delete/media cleanup runtime。

不做：

- 預設無條件 cascade 刪 upload 檔。
- 繞過引用掃描。
- 刪仍被其他 note / attachment / cover 引用的圖片。
- 在 V2.5 封版後只為此重包 release。

驗收候選：copy 或 opt-in 行為需有 frontend regression；若涉及刪檔 runtime，必須補 Go/API tests 證明 shared references、cover image、Markdown/HTML image、thumbnail companion 與 batch delete order 都不誤刪。

---

## Deferred Candidates

- [ ] `DEEP-SCAN-RISK-CANDIDATE-01` 01H 仍是低優先維護 triage（狀態：`Blocked`）：剩餘 frontend bundle/Browserslist warning、歷史 frozen docs/test wording仍需另行 promote；其中 `go-shadow/main.go` route-local 小整理已明確化為 `GO-MAIN-SPLIT-CANDIDATE-01`，但一次性 runtime 大拆分仍 `Blocked`。
- [ ] Desktop installer/updater/WebView2 bootstrap/shortcut automation（狀態：`Blocked`；需使用者明確需要 installer/updater 類能力）。
- [ ] Hidden/deferred i18n UI（`PortConfigSection`、`UpdateSection`、`TagInput`）（狀態：`Blocked`；只有日後恢復 render，才於該 gate 同步補四語 key）。
- [ ] Mermaid 圖表渲染（狀態：`Blocked`；只有 `MARKDOWN-SYNTAX-CANDIDATE-01` 的 `MDS-05` 被明確 promote 後才可施工；不得順手導入 heavy renderer）。
- [ ] KaTeX 數學公式 / ABC 樂譜渲染（狀態：`Blocked`；目前凍結為備選，只有使用者明確重新開啟需求時才可施工）。
- [ ] AI / semantic search / embeddings / GraphRAG / auto-writing（狀態：`Blocked`；仍不在 active roadmap）。

---

## Release / GitHub / Pi Maintenance

- [x] `RELEASE-V2.6`（狀態：`Done`）：使用者已明確授權並完成 GMS commit 與 V2.6 release/tag/package/push。
  - [x] `R26-00 GMS closure commit`（狀態：`Done`）：GMS mechanical split 已提交為 `b9955c6`；非本次 scope 的既有 TODO checkbox 保留到 release docs normalization。
  - [x] `R26-01 Version and release wording`（狀態：`Done`）：current runtime fallback、tests、README、portable README、docs index/API/packaging wording與 changelog已更新到 2.6；歷史 v2.5 evidence/contracts 未改寫。
  - [x] `R26-02 Full local verification`（狀態：`Done`）：`.loop/verify-gate.ps1` passed（pytest 379 passed、Go tests passed、mirror/diff passed）；frontend build passed with existing warnings；隔離 Go runtime 下 browser e2e 9 passed。
  - [x] `R26-03 Portable/package/privacy gate`（狀態：`Done`）：local artifact、Go full-workflow package、desktop clean-unzip smoke passed；zip 7 entries、21,671,334 bytes、privacy sweep passed，SHA256 `33A23644F664EEE74B9449A19EAA54AEBA758CDE199D2A8E6D22182240D24F74`。
  - [x] `R26-04 Release commit/tag/push`（狀態：`Done`）：release commit `461421d` 與 annotated `V2.6` tag 已 push；remote main/tag read-back通過，未 force push。
  - [x] `R26-05 GitHub validation and asset`（狀態：`Done`）：GitHub Actions run `29266735767` success；Release https://github.com/SamMask/Prism/releases/tag/V2.6 已發布，asset size/digest與重新下載 SHA256一致。
  - [x] `R26-06 Evidence closure`（狀態：`Done`）：Actions/release URL、final evidence與 product boundary已寫回 HANDOFF/TODO/history；本輪未做 Pi deploy。
- [x] `PI-V2.6-LIVE`（狀態：`Done`）：將已驗證的 V2.6 Go primary artifact 部署到 `PI5Mask24`，重啟 live service 並做 bounded live smoke；未改 schema、API、Caddy exposure boundary 或 Pi data-dir。長版證據：`docs/development-history/v2.6-pi-live-deploy-20260714.md`。
  - [x] `PI26-00 Live preflight`（狀態：`Done`）：SSH / sudo / aarch64 / 磁碟 / live DB / Caddy / version / migration / read API 已檢查；部署前 live version `2.5`、schema current/latest v17、pending empty、Caddy route header `X-Prism-Go-Primary: hit`。發現 legacy `prism.service` 意外為 active/enabled，納入本次收斂條件。
  - [x] `PI26-01 Snapshot and artifact cutover`（狀態：`Done`）：`scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` passed；artifact SHA256 `e650c5a0990d4ed36308d83a06c453b545cb50bb1da7a05b7c42986989685a36`，snapshot `/home/mask070924/prism/backups/go-primary-t042-20260714_010616`，retention keep-5 passed。
  - [x] `PI26-02 Service ownership normalization`（狀態：`Done`）：T042 full workflow通過後，`prism-go-primary.service` active/enabled、Caddy active，legacy `prism.service` 已 disabled/inactive；只有 5004 保留 Prism listener。
  - [x] `PI26-03 Live API/UI smoke and bounded soak`（狀態：`Done`）：version 2.6、migration v17 clean、consistency healthy、FTS 255/255、notes/search/categories與 JS hooks通過；5 samples均穩定，Playwright Command Palette server search 52 results，console 0 error/0 warning，Go/Caddy journal無 error。
  - [x] `PI26-04 Evidence closure`（狀態：`Done`）：machine-readable evidence已回收到 `build/go-primary-live/pi/`，長版證據已歸檔。唯一 non-blocking finding：`frontend/index.html` / sidebar brand仍顯示 V2.5；未在部署中臨時改 code，避免 Pi偏離已發布 artifact。
- [x] Pi delivery（狀態：`Done`）：2026-07-08 已依 `DEPLOY-PI.md` 使用 Go primary live ops Cutover 部署到 `PI5Mask24`。驗證：`prism-go-primary.service` active、legacy `prism.service` inactive、migration current/latest v17 pending empty、`/api/server/version` version `2.5`、batch delete dry-run API success、served JS contains batch preview / import preview / source URL panel hooks。Pi delivery 不是 release notes / GitHub asset 的自動副作用；未來任何 Pi 上線仍需另開 gate 重跑 service / migration / changed endpoint / UI evidence。

---

## Windows Desktop vs Pi Deployment 差異表

| 面向 | Windows desktop | Raspberry Pi |
|---|---|---|
| 入口 | `Prism.exe` GUI app；正式 build 不出現終端機 | systemd service 啟動 Go primary binary |
| UI | WebView2 內嵌本機 Web UI + tray | 使用瀏覽器連 `https://prism.local` / Caddy |
| Runtime | 同一行程內 desktop shell + Go server goroutine | headless Go primary service |
| 網路 | 綁 `127.0.0.1:<port>`，只給本機 WebView2 | Caddy reverse proxy 到 local service port |
| 資料 | 預設 exe 同層 `PrismData\`；`--data-dir` / env 僅作進階 override | Pi 上既有 production data dir |
| Log | 檔案 log + debug console build | journald / service log / Go runtime log |
| 打包 | portable zip / folder；installer deferred | artifact deploy + systemd + rollback / soak |
| 相依 | WebView2 Runtime、Win32 shell APIs | Linux/arm64、systemd、Caddy |
| 不共用項 | tray、window、mutex、`-H=windowsgui` | Caddy live routing、systemd enable/restart |

---

## Archive Index

- `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`：2026-06-19 TODO/HANDOFF 瘦身時移出的 V2.5 收尾、完成 gate、release/package evidence 與 deferred notes。
- `docs/development-history/go-primary-runtime-completion-20260617.md`：T001-T053 Go primary migration 完成敘事、artifact 與完整任務表。
- `docs/development-history/desktop-backup-i18n-handoff-20260617.md`：2026-06-14 local desktop / backup / dashboard handoff、2026-06-17 Core UX 與 i18n 詳細完成記錄。
- `docs/development-history/desktop-portable-release-handoff-20260618.md`：Desktop Shell Phase 0-6、portable baseline、manual acceptance、README split 與 release packaging 邊界。
- `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`：Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。
- `docs/development-history/todo-changelog.md`：長版版本歷程。
- `docs/development-history/todo-completed-phases.md`：更早期完成 phase 與歷史工作清單。
