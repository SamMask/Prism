# HANDOFF - Prism active entry（2026-07-05）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/`；最新 TODO/HANDOFF 瘦身歸檔見 `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`。

## Current State

- Go primary 是唯一 current runtime owner；Python Flask backend source 已移除，T001-T053 完整紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Prism V2.5 release / tag / portable asset 已對齊 commit `42ce747bc273182b045455de49b8be06fd6c051a`。Windows portable 是 unsigned build；README 與 release notes 已說明 SmartScreen、`Zone.Identifier`、SHA256 驗證與 `Unblock-File`。
- Windows desktop current path 是 `Prism.exe` GUI app + WebView2 + same-process Go runtime，預設資料在 exe 同層 `PrismData\`。Installer/updater/WebView2 bootstrap/shortcut automation 仍 deferred。
- Recent V2.5 UX/runtime gates 已完成並歸檔：Reading workspace、variant tracking、note-list preview、image lightbox/zoom、batch import、starred tags、category identity、deep scan 01A-01G、project review hygiene 01A-01E。
- Pi delivery 與 GitHub release packaging 分開處理；Pi 上線必須讀 `DEPLOY-PI.md` 並驗 service/migration/API/UI live evidence。
- Prism 沒有內建 auth/token layer；safe boundary 是 localhost、trusted LAN、VPN、SSH tunnel 或外部 auth 保護的 reverse proxy。
- Note deletion media behavior 已記入 TODO：刪卡片不保證刪除實體 upload 圖片檔；圖片管理面板與 Settings「清理未使用圖片」才是明確刪檔入口。未來可補 copy 或 opt-in checkbox，預設不做 cascade 刪檔。
- 2026-07-05 governance intake 已完成：`docs/GOVERNANCE.md` 是完成宣稱、狀態層級、驗證證據、委派與 UI/UX 治理入口；原暫存素材已複製到 `docs/development-history/governance-source-20260705/`。
- 2026-07-05 TODO 已補 Markdown / Knowledge Workflow candidates 與固定狀態值 `Todo` / `Doing` / `Blocked` / `Review` / `Done`。
- 2026-07-05 `MARKDOWN-SYNTAX-CANDIDATE-01` 已完成低風險 renderer/preview slice：GFM table/task list/code copy/heading anchor/ReadingView outline，以及 MarkForge prose extensions（GitHub alert、footnote、`==highlight==`、`:::markforge-box`、`:::markforge-details`）。沒有新增 dependency、schema/API、Go runtime 或 Mermaid/KaTeX/ABC renderer。
- 2026-07-05 KWF-01 Command Palette server-side search 已完成：Command Palette 輸入 `? xxx` 或至少 3 個字元會 debounce 呼叫既有 `/api/notes?q=...` adapter，顯示全庫結果；保留 navigation / recent / new note / theme actions，未改 Go API、DB schema、search engine 或 auth boundary。
- KWF-01 fresh verification：targeted pytest 11 passed；frontend build passed（僅既有 Browserslist / chunk-size warning）；`git diff --check` passed（僅 Windows CRLF warning）；full `pytest tests/ -v` 為 349 passed / 19 failed，失敗仍是 TODO 瘦身後舊測試期待歷史 `[x]` 條目的既有 docs regression。
- KWF-01 Pi live deploy：2026-07-05 已用 `scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` 推到 `PI5Mask24`。Artifact sha256 `b1216cc1aefcc893db9b867e97960de3bb3e4689a739ee8227b5fd4738dcb871`；pre-cutover snapshot `/home/mask070924/prism/backups/go-primary-t042-20260705_012430`；live checks passed（Go primary active、legacy `prism.service` inactive、Caddy active、migration v17 no pending、`/api/notes?q=prompt` success、served JS contains `command-palette-server-search-status`）。Evidence: `build/go-primary-live/pi/evidence.json`。

## Next Entry

目前沒有未交付的 active construction item。

- 若要處理使用者剛提的刪卡/圖片語意，從 `NOTE-DELETE-MEDIA-UX-CANDIDATE-01` 做 UX copy 或 opt-in decision gate；先不要改 runtime deletion semantics。
- 下一個建議入口是 `KNOWLEDGE-WORKFLOW-CANDIDATE-01` 的 `KWF-02` Saved Search / Search Workspace；先用 localStorage 儲存常用 query/filter/sort view，不改 DB schema。
- 若要繼續 Markdown 重型支援，只能明確 promote `MARKDOWN-SYNTAX-CANDIDATE-01` 的 blocked decision gates（Mermaid / KaTeX / ABC / syntax highlighting dependency review）；不要順手導入 schema/API 變更。
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
