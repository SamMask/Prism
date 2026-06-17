# HANDOFF — Prism active entry（2026-06-17）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`。

## Current State

- `main` 已包含 2026-06-14 local desktop / backup / dashboard 基礎工作；當時紀錄為 fast-forward 到 `24bf5f6`，未 push、未部署。
- Go primary 是唯一 current runtime owner；T001-T053 完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- i18n active UI 已完成到 zh-TW / en / ja / ko，可先視為收斂；不要再開大型 UI 抽字串批次。
- Core UX / Maintenance 三個 candidate 已完成：Home 搜尋可解釋性 UX（recent searches 只在 localStorage）、`/api/system/search-integrity` 診斷 + 手動 FTS rebuild、Settings 維護狀態總覽；未新增 semantic search、SearchHistory DB、自動修復、schema 或 deploy 變更。
- `.exe` 桌面化已定方向：Windows 視窗程式、WebView2、tray、單一實例、同一行程內 Go server goroutine；關閉行為預設直接結束，close-to-tray 是進階選項。

## Next Entry

下一個可施工項是 `docs/TODO.md` 的 **Desktop Shell Phase 0 — message loop spike**：

- 獨立 `desktop-spike/`。
- Phase 0 只做空 Win32 視窗 + tray icon + 單一 message loop。
- 不引 WebView2、不接後端、不改 schema/API/runtime。
- 驗收：tray Show / Quit 有反應、關視窗正常退出、loop 不卡。

## Required Reads

接續施工前先讀：

- `AGENTS.md`
- `docs/TODO.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEMA.md`
- `docs/API_REFERENCE.md`
- 需要歷史脈絡時再讀 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`
