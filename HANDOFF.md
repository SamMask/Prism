# HANDOFF - Prism active entry（2026-08-30）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/`；最新 TODO/HANDOFF 瘦身歸檔見 `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`。

## Current State

- Go primary 是唯一 current runtime owner；Python Flask backend source 已移除，T001-T053 完整紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Prism V2.6.1已依使用者明確決策完成同版About顯示遺漏重發；release / annotated tag / portable asset對齊修正commit`7f5469c16cac2a8412bb5f2524cc4e9884256db3`：https://github.com/SamMask/Prism/releases/tag/V2.6.1。Asset 21,671,554 bytes，SHA256 `8705C5F5CBCC24A3EEFBBC02E02695B0103CB04E879770A488D2A4429D229F17`；既有V2.6未改寫，沒有V2.6.2。
- Windows desktop current path 是 `Prism.exe` GUI app + WebView2 + same-process Go runtime，預設資料在 exe 同層 `PrismData\`。Installer/updater/WebView2 bootstrap/shortcut automation 仍 deferred。
- Recent V2.5 UX/runtime gates 已完成並歸檔：Reading workspace、variant tracking、note-list preview、image lightbox/zoom、batch import、starred tags、category identity、deep scan 01A-01G、project review hygiene 01A-01E。
- Pi delivery 與 GitHub release packaging 分開處理；Pi 上線必須讀 `DEPLOY-PI.md` 並驗 service/migration/API/UI live evidence。
- 2026-08-17 `PI-PATH-MIGRATION-01` 已完成：Pi live root/service user 已收斂為 `/home/mask0709/prism` / `mask0709`；Go primary active+enabled 且唯一監聽 5004，legacy `prism.service` 與 `prism-go-readonly.service` inactive+disabled，weekly backup 改依賴 Go primary。pre-change config backup 在 `/home/mask0709/prism/backups/pi-path-migration-20260817T061420/` 且 checksum 全綠；手動 DB backup、reboot、同 artifact Go cutover→previous-Go rollback→2-sample soak均通過。Caddy原 hash已還原，Prism/Vespera/Murmur均正常。Local deployment tests 13 passed、full pytest 397 passed；未跑 frontend build/browser，因本輪未改 UI。
- Prism 沒有內建 auth/token layer；safe boundary 是 localhost、trusted LAN、VPN、SSH tunnel 或外部 auth 保護的 reverse proxy。
- Note deletion media behavior 已校正到 TODO：Go primary 目前會在刪 note 時嘗試清理已偵測且未被其他 note 引用的 `static/uploads` 圖片與縮圖；Settings「清理未使用圖片」仍是孤兒圖片的明確補救/清理入口。未做的是 UX copy 或未來 opt-in decision gate；不要改 runtime deletion semantics。
- 2026-07-05 governance intake 已完成：`docs/GOVERNANCE.md` 是完成宣稱、狀態層級、驗證證據、委派與 UI/UX 治理入口；原暫存素材已複製到 `docs/development-history/governance-source-20260705/`。
- 2026-07-05 TODO 已補 Markdown / Knowledge Workflow candidates 與固定狀態值 `Todo` / `Doing` / `Blocked` / `Review` / `Done`。
- 2026-07-05 `MARKDOWN-SYNTAX-CANDIDATE-01` 已完成低風險 renderer/preview slice：GFM table/task list/code copy/heading anchor/ReadingView outline，以及 MarkForge prose extensions（GitHub alert、footnote、`==highlight==`、`:::markforge-box`、`:::markforge-details`）。沒有新增 dependency、schema/API、Go runtime 或 Mermaid/KaTeX/ABC renderer。
- 2026-07-05 Markdown heavy renderer 決策更新：Mermaid 只保留為 blocked decision gate；KaTeX 數學公式與 ABC 樂譜暫時凍結為備選，不列入下一個 Markdown renderer 入口，除非使用者明確重新開啟需求。
- 2026-07-05 KWF-01 Command Palette server-side search 已完成：Command Palette 輸入 `? xxx` 或至少 3 個字元會 debounce 呼叫既有 `/api/notes?q=...` adapter，顯示全庫結果；保留 navigation / recent / new note / theme actions，未改 Go API、DB schema、search engine 或 auth boundary。
- KWF-01 fresh verification：targeted pytest 11 passed；frontend build passed（僅既有 Browserslist / chunk-size warning）；`git diff --check` passed（僅 Windows CRLF warning）；full `pytest tests/ -v` 為 349 passed / 19 failed，失敗仍是 TODO 瘦身後舊測試期待歷史 `[x]` 條目的既有 docs regression。
- KWF-01 Pi live deploy：2026-07-05 已用 `scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` 推到 `PI5Mask24`。Artifact sha256 `b1216cc1aefcc893db9b867e97960de3bb3e4689a739ee8227b5fd4738dcb871`；pre-cutover snapshot `/home/mask070924/prism/backups/go-primary-t042-20260705_012430`；live checks passed（Go primary active、legacy `prism.service` inactive、Caddy active、migration v17 no pending、`/api/notes?q=prompt` success、served JS contains `command-palette-server-search-status`）。Evidence: `build/go-primary-live/pi/evidence.json`。
- 2026-07-08 KWF-02 Saved Search / Search Workspace 已完成：Home 可保存 / 套用 / 刪除目前 query、category、tag、archived、sort view；只使用 localStorage key `prism.savedSearchWorkspaces.v1`，未新增 DB schema、Go API、semantic search、auth 或 Pi deploy。
- 2026-07-08 NOTE-DELETE-MEDIA-UX-CANDIDATE-01 已完成：刪除 note / 批次刪除確認框與 Settings「清理未使用圖片」已補 reference-counted cleanup 語意 copy；未改 Go delete/media cleanup runtime。
- KWF-02 / NOTE-DELETE fresh verification：new regression 6 passed；related i18n/Home targeted tests 10 passed；`cd frontend && npm run build` passed（僅既有 Browserslist / chunk-size warning）；Browser smoke on `http://127.0.0.1:5173/` passed for page load + Search Workspace save/delete visible behavior。Go backend 5004 未啟動，browser console 只有資料 API fetch errors；未做 Pi deploy。
- 2026-07-08 KWF-03 Full data snapshot export 已完成：新增 `scripts/export_full_data_snapshot.ps1`，支援 dry-run 與 zip snapshot，包含 DB、WAL/SHM、`static/uploads/`、`docs/attachments/`、`docs/notes/`、config 與 `snapshot-manifest.json` sha256 manifest；未碰 live Pi。
- 2026-07-08 KWF-04 Agent-safe write guards 已完成：`POST /api/notes/batch/delete` 支援 `dry_run: true` preview；前端批次刪除 confirm 會先顯示 deletable / missing / image / attachment counts，再執行真正 batch delete。這不是 auth，也不改 public exposure boundary。
- 2026-07-08 KWF-05 Import dry-run / collision preview 已完成：Settings 批次 Markdown/TXT 匯入會先顯示本機 create / duplicate / unsupported preview；仍只用既有單檔 import / create-note 路徑，沒有 server-side batch import API、watcher 或 sync daemon。
- 2026-07-08 KWF-06 Source URL panel 已完成：ReadingView 使用既有 note `urls` 顯示 source URL panel、domain 與 duplicate URL 標記；未做 web clipper、外網 title fetch 或 link health 背景檢查。
- 2026-07-14 KWF-07 product decision 已關閉：Prism 是個人筆記庫，不加入 `status` / `review_state` / `last_verified_at` 審核 metadata；除非用途改變，不得重新 promote schema v18 workflow。`docs/SCHEMA.md` 維持 Migration v17。
- KWF-03..07 local release validation / Pi deploy gate（2026-07-08）已完成：`.loop/verify-gate.ps1` passed（含 `pytest tests/ -v` 379 passed、`cd go-shadow && go test ./...` passed、mirror check / `git diff --check` passed）；`cd frontend && npm run build` passed（僅既有 Browserslist / chunk-size warning）；Go package smoke、local artifact smoke、desktop portable smoke、browser e2e `python -m pytest e2e -q` 9 passed；tracked privacy sweep 與 portable zip forbidden-entry sweep passed。
- Pi live deploy（2026-07-08）已完成：`scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` passed，evidence `build/go-primary-live/pi/evidence.json`；`prism-go-primary.service` active、legacy `prism.service` inactive、`/api/system/migration-status` current/latest v17 且 pending empty、`/api/server/version` version `2.5`；live batch delete dry-run returned `status: success` without deletion，served JS `/assets/index-DqUfa497.js` contains `previewBatchDeleteNotes`、`bulk-import-dry-run-preview`、`reading-source-url-panel`。
- 2026-07-13 `GO-MAIN-SPLIT-CANDIDATE-01` / GMS-00..10 已完成：`go-shadow/main.go` 從 10,246 行降到 1,024 行；attachments、taxonomy、migrations、backup/system/options、import/export、uploads/media 與 notes 已依既有責任分到同一 `package main` 的 bounded-context files，沒有新增 package/dependency/API/schema/migration 或 deploy 行為。
- Go split fresh verification：425 個 top-level declarations AST 比對一致；`cd go-shadow && go test ./...` passed；targeted Go groups passed；`pytest tests/ -v` 379 passed；`scripts/build_go_runtime.ps1` passed；local artifact 與 Windows full-workflow package smoke passed。長版證據見 `docs/development-history/go-main-split-completion-20260713.md`；本輪未部署 Pi、未建立 release/tag。
- V2.6 release（2026-07-14）已完成：fresh verify gate 379 pytest + Go tests passed，frontend build passed with existing warnings，browser e2e 9 passed，Go artifact/package與 desktop clean-unzip smokes passed；GitHub Actions run `29266735767` passed。`PrismDesktopPortable-v2.6.zip` size 21,671,334 bytes，SHA256 `33A23644F664EEE74B9449A19EAA54AEBA758CDE199D2A8E6D22182240D24F74`；GitHub digest與重新下載 hash一致，privacy sweep passed。
- V2.6 Pi live deploy（2026-07-14）已完成：`scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` passed，artifact SHA256 `e650c5a0990d4ed36308d83a06c453b545cb50bb1da7a05b7c42986989685a36`，snapshot `/home/mask070924/prism/backups/go-primary-t042-20260714_010616`。Go active/enabled、legacy `prism.service` inactive/disabled、Caddy active；runtime version 2.6、migration v17 clean、T042 full workflow、5-sample soak、Playwright Home/Search Workspace/Command Palette server search與 browser console均通過。長版證據：`docs/development-history/v2.6-pi-live-deploy-20260714.md`。
- 2026-07-14 frontend label / research archive gate 已完成：`frontend/index.html` browser title 與 `Sidebar.tsx` brand 均改為 V2.6；2026-07-01 深入研究報告已依 current truth分成已完成／已吸收、候選與不採用事項，歸檔至 `docs/development-history/2026-07-01-深入研究-deep-research-report-Prism.md`。
- Label/archive fresh verification：36 個相關 pytest與完整 `pytest tests/ -v` 381 passed；`scripts/build_go_runtime.ps1` passed（含 frontend production build與 Go tests）；隔離 Go runtime Playwright smoke確認 Page Title `Prism V2.6`、sidebar `V2.6`、console 0 errors / 0 warnings。
- V2.6.1 About correction release / Pi live redeploy（2026-07-14）已完成：release commit`7f5469c`、Actions run`29276993209` success；GitHub digest與fresh download hash均為`8705C5F5CBCC24A3EEFBBC02E02695B0103CB04E879770A488D2A4429D229F17`。
- 修正後Pi evidence：artifact SHA256`1c1ff025f8653a48e97d87cbb29afa09d09e9ca8e020fef329d1e395e2fce01d`，latest snapshot`/home/mask070924/prism/backups/go-primary-t044-20260714_031146`，retention keep-5、full workflow與5-sample soak passed；Go active/enabled、legacy inactive/disabled、Caddy active、runtime 2.6.1、migration v17 clean。Live Playwright確認Page Title`Prism V2.6.1`、sidebar`V2.6.1`、About`Version: 2.6.1`、console 0 errors/0 warnings。
- Pi 上 `prism-go-readonly.service` 與 `prism-go-primary-staging.service` unit/file仍保留作歷史/隔離驗證，但兩者均 inactive+disabled；Caddy只 route 至 127.0.0.1:5004 Go primary。不得重新 enable readonly sidecar或讓它依賴 legacy Python。
- Product decision（2026-07-14）：Prism 維持個人筆記庫，不加入 `status` / `review_state` / `last_verified_at` 審核 metadata 或 schema v18 workflow；除非用途改變，不得重新 promote。
- 2026-08-12 深度產品／UX／技術審查已完成，報告為 `docs/PROJECT_OPTIMIZATION_REVIEW_2026-08-12.md`；P0 `PRISM-OPT-01` 到 `PRISM-OPT-06` 已完成本機實作與隔離 desktop/390px browser 驗收。內容包含 FK violation 真值、mobile drawer/accessibility、三種 note view action parity、selection scope/單次 delete preview、search partial diagnostics 與 latest-request-wins/Retry。完整 `pytest tests/ -v` 389 passed、Go tests passed、production build passed；未碰正式 DB、release 或 Pi deploy。
- 2026-08-12 P1 `PRISM-OPT-07` 到 `PRISM-OPT-14` 已完成本機實作：Data & Recovery/DB-only truth、full snapshot v1、Prompt save continuation、Home-only filters、安全 custom reorder、note relation batch queries、lazy routes與 test portfolio/current e2e。完整 snapshot 明確只支援 manual restore；未新增 schema/AI/cloud/auth。
- P1 fresh local evidence：targeted frontend/docs 41 passed；full pytest 396 passed；Go tests與production build passed；main JS由706.22 kB降至598.02 kB；isolated Chromium 5 passed（含fresh DB、26 notes、Prompt save-to-open、Settings desktop/390px）；mirror與diff check passed。未碰正式 DB、release或Pi deploy。
- 2026-08-23 `EDITOR-COPY-CONTENT-01` 已完成並部署 Pi：note 詳情編輯器工具列在「歷史」與 Preview/Edit 切換之間新增一鍵複製，複製目前表單正文（含未儲存編輯），沿用既有四語系 copy/toast。390px 以可換行 header 與 icon-only History/Save labels 避免溢位；full pytest 399 passed、Go runtime build passed、隔離 desktop/390px browser flow 與 console gate passed。Commit `70f04e7`；Pi artifact SHA256 `606056dcdbe53435957e2456ac09bc50db4d82236f9b0f20906011e012658ff1`，snapshot `/home/mask0709/prism/backups/go-primary-t042-20260823_153951/`；full workflow、post-smoke hashes、5-sample soak、live Copy button desktop/390px與console均通過。Go/Caddy active、legacy/readonly inactive、schema v17 pending empty、5004 only。未改 Preview 可編輯語意、Reading Workspace 或 API/schema；相關 commits 已於 2026-08-30 推送 `origin/main`，未建立新 release/tag。

## Next Entry

目前沒有未交付的 active construction item，也沒有 `Doing` item；`EDITOR-COPY-CONTENT-01` 已完成 commit + Pi live delivery。`PI-PATH-MIGRATION-01` 已完成 repo + Pi live 收斂；product optimization P0/P1 已 commit，並包含在本次 Pi artifact 中，但未逐條重跑其完整 live UX flow。2026-08-30 current changes 已推送 `origin/main`；未建立新 release/tag。

- P2/P3/Future 只留在 `docs/PROJECT_OPTIMIZATION_REVIEW_2026-08-12.md`，必須由使用者明確 promote；不要自動實作 Preview/Edit 語意、Reading Workspace lazy detail、flags命名、schema、automatic restore或大重構。
- 若要更改 note 刪除時的圖片刪除行為，只能另開 opt-in decision gate；不要順手改 Go delete/media cleanup runtime。
- 若要繼續 Markdown 重型支援，只能明確 promote `MARKDOWN-SYNTAX-CANDIDATE-01` 的 Mermaid decision gate 或 syntax-highlighting dependency review；KaTeX / ABC 目前凍結為備選，不要順手導入 schema/API 變更。
- 若要處理 governance、完成宣稱、委派或 UI/UX policy，先讀 `docs/GOVERNANCE.md`；需要追溯來源時讀 `docs/development-history/governance-source-20260705/`。
- 若要再次發佈或重包，仍須依 `docs/RELEASE_CHECKLIST.md` 重跑 fresh validation，再 commit / tag / package；push 後確認 GitHub Actions 綠燈。
- 若要處理維護項，只能 promote `DEEP-SCAN-RISK-CANDIDATE-01` 01H 的低優先小整理，不要擴成大重構。
- 不要自動開 AI、semantic search、installer、updater、public-internet auth 或 Pi deploy。

## Required Reads

接續施工前先讀：

- `AGENTS.md`
- `docs/GOVERNANCE.md`
- `docs/TODO.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEMA.md`
- `docs/API_REFERENCE.md`
- `DEPLOY-PI.md`（Pi delivery / live verification 時必讀）
- `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`（需要 V2.5 收尾脈絡時）
