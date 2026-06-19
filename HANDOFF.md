# HANDOFF - Prism active entry（2026-06-19）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/`；最新 TODO/HANDOFF 瘦身歸檔見 `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`。

## Current State

- Go primary 是唯一 current runtime owner；Python Flask backend source 已移除，T001-T053 完整紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Prism V2.5 release / tag / portable asset 已對齊 commit `42ce747bc273182b045455de49b8be06fd6c051a`。Windows portable 是 unsigned build；README 與 release notes 已說明 SmartScreen、`Zone.Identifier`、SHA256 驗證與 `Unblock-File`。
- Windows desktop current path 是 `Prism.exe` GUI app + WebView2 + same-process Go runtime，預設資料在 exe 同層 `PrismData\`。Installer/updater/WebView2 bootstrap/shortcut automation 仍 deferred。
- Recent V2.5 UX/runtime gates 已完成並歸檔：Reading workspace、variant tracking、note-list preview、image lightbox/zoom、batch import、starred tags、category identity、deep scan 01A-01G、project review hygiene 01A-01E。
- Pi delivery 與 GitHub release packaging 分開處理；Pi 上線必須讀 `DEPLOY-PI.md` 並驗 service/migration/API/UI live evidence。
- Prism 沒有內建 auth/token layer；safe boundary 是 localhost、trusted LAN、VPN、SSH tunnel 或外部 auth 保護的 reverse proxy。
- Note deletion media behavior 已記入 TODO：刪卡片不保證刪除實體 upload 圖片檔；圖片管理面板與 Settings「清理未使用圖片」才是明確刪檔入口。未來可補 copy 或 opt-in checkbox，預設不做 cascade 刪檔。

## Next Entry

目前沒有未交付的 active construction item。

- 若要處理使用者剛提的刪卡/圖片語意，從 `NOTE-DELETE-MEDIA-UX-CANDIDATE-01` 做 UX copy 或 opt-in decision gate；先不要改 runtime deletion semantics。
- 若要發佈新版或重包，先依 `docs/RELEASE_CHECKLIST.md` 重跑 fresh validation，再 commit / tag / package；push 後確認 GitHub Actions 綠燈。
- 若要處理維護項，只能 promote `DEEP-SCAN-RISK-CANDIDATE-01` 01H 的低優先小整理，不要擴成大重構。
- 不要自動開 AI、semantic search、installer、updater、public-internet auth 或 Pi deploy。

## Required Reads

接續施工前先讀：

- `AGENTS.md`
- `docs/TODO.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEMA.md`
- `docs/API_REFERENCE.md`
- `DEPLOY-PI.md`（Pi delivery / live verification 時必讀）
- `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`（需要 V2.5 收尾脈絡時）
