# HANDOFF - Prism active entry（2026-07-13）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/`；最新 TODO/HANDOFF 瘦身歸檔見 `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`。

## Current State

- Go primary 是唯一 current runtime owner；Python Flask backend source 已移除，T001-T053 完整紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Prism V2.5 release / tag / portable asset 已對齊 commit `42ce747bc273182b045455de49b8be06fd6c051a`。Windows portable 是 unsigned build；README 與 release notes 已說明 SmartScreen、`Zone.Identifier`、SHA256 驗證與 `Unblock-File`。
- Windows desktop current path 是 `Prism.exe` GUI app + WebView2 + same-process Go runtime，預設資料在 exe 同層 `PrismData\`。Installer/updater/WebView2 bootstrap/shortcut automation 仍 deferred。
- Recent V2.5 UX/runtime gates 已完成並歸檔：Reading workspace、variant tracking、note-list preview、image lightbox/zoom、batch import、starred tags、category identity、deep scan 01A-01G、project review hygiene 01A-01E。
- Pi delivery 與 GitHub release packaging 分開處理；Pi 上線必須讀 `DEPLOY-PI.md` 並驗 service/migration/API/UI live evidence。
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
- 2026-07-08 KWF-07 Knowledge quality metadata decision gate 已完成：`status / review_state / last_verified_at` 保留為 schema v18 decision gate；本輪未改 `docs/SCHEMA.md` current Migration v17，未新增 DB 欄位或 migration。
- KWF-03..07 local release validation / Pi deploy gate（2026-07-08）已完成：`.loop/verify-gate.ps1` passed（含 `pytest tests/ -v` 379 passed、`cd go-shadow && go test ./...` passed、mirror check / `git diff --check` passed）；`cd frontend && npm run build` passed（僅既有 Browserslist / chunk-size warning）；Go package smoke、local artifact smoke、desktop portable smoke、browser e2e `python -m pytest e2e -q` 9 passed；tracked privacy sweep 與 portable zip forbidden-entry sweep passed。
- Pi live deploy（2026-07-08）已完成：`scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` passed，evidence `build/go-primary-live/pi/evidence.json`；`prism-go-primary.service` active、legacy `prism.service` inactive、`/api/system/migration-status` current/latest v17 且 pending empty、`/api/server/version` version `2.5`；live batch delete dry-run returned `status: success` without deletion，served JS `/assets/index-DqUfa497.js` contains `previewBatchDeleteNotes`、`bulk-import-dry-run-preview`、`reading-source-url-panel`。
- 2026-07-13 `GO-MAIN-SPLIT-CANDIDATE-01` / GMS-00..10 已完成：`go-shadow/main.go` 從 10,246 行降到 1,024 行；attachments、taxonomy、migrations、backup/system/options、import/export、uploads/media 與 notes 已依既有責任分到同一 `package main` 的 bounded-context files，沒有新增 package/dependency/API/schema/migration 或 deploy 行為。
- Go split fresh verification：425 個 top-level declarations AST 比對一致；`cd go-shadow && go test ./...` passed；targeted Go groups passed；`pytest tests/ -v` 379 passed；`scripts/build_go_runtime.ps1` passed；local artifact 與 Windows full-workflow package smoke passed。長版證據見 `docs/development-history/go-main-split-completion-20260713.md`；本輪未部署 Pi、未建立 release/tag。

## Next Entry

目前沒有未交付的 active construction item。

- 下一個建議入口是 release/tag/package decision：若要把 2026-07-08 KWF 與 2026-07-13 Go source split 對外發版，先依 `docs/RELEASE_CHECKLIST.md` 決定版本號、commit/tag/package/push，並確認 GitHub Actions 綠燈；不要把本機 package smoke 或 Pi live deploy 視為 GitHub release asset 自動完成。
- 若要更改 note 刪除時的圖片刪除行為，只能另開 opt-in decision gate；不要順手改 Go delete/media cleanup runtime。
- 若要繼續 Markdown 重型支援，只能明確 promote `MARKDOWN-SYNTAX-CANDIDATE-01` 的 Mermaid decision gate 或 syntax-highlighting dependency review；KaTeX / ABC 目前凍結為備選，不要順手導入 schema/API 變更。
- 若要處理 governance、完成宣稱、委派或 UI/UX policy，先讀 `docs/GOVERNANCE.md`；需要追溯來源時讀 `docs/development-history/governance-source-20260705/`。
- 若要發佈新版或重包，先依 `docs/RELEASE_CHECKLIST.md` 重跑 fresh validation，再 commit / tag / package；push 後確認 GitHub Actions 綠燈。
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
