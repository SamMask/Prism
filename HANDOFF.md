# HANDOFF — Prism active entry（2026-06-17）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`。

## Current State

- `main` 已包含 2026-06-14 local desktop / backup / dashboard 基礎工作；當時紀錄為 fast-forward 到 `24bf5f6`，未 push、未部署。
- Go primary 是唯一 current runtime owner；T001-T053 完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- i18n active UI 已完成到 zh-TW / en / ja / ko，可先視為收斂；不要再開大型 UI 抽字串批次。
- Core UX / Maintenance 三個 candidate 已完成：Home 搜尋可解釋性 UX（recent searches 只在 localStorage）、`/api/system/search-integrity` 診斷 + 手動 FTS rebuild、Settings 維護狀態總覽；未新增 semantic search、SearchHistory DB、自動修復、schema 或 deploy 變更。
- Server Dashboard Windows/no-temperature 平台不顯示 CPU 溫度 N/A 卡，改顯示系統運行卡；Pi/Linux 有溫度讀值時仍保留 CPU 溫度卡。
- `.exe` 桌面化已定方向：Windows 視窗程式、WebView2、tray、單一實例、同一行程內 Go server goroutine；關閉行為預設直接結束，close-to-tray 是進階選項。
- Desktop Shell Phase 0 完成：`desktop-spike/` 已建立 isolated Win32 message-loop spike，空視窗 + tray Show/Quit 共用單一 loop；未接 WebView2、後端、schema/API/runtime、deploy 或 production data。

## Next Entry

下一個可施工項是 `docs/TODO.md` 的 **Desktop Shell Phase 1 — WebView2 spike**：

- 沿用 Phase 0 的 Win32 message loop 與 tray 結構。
- 只接 WebView2 placeholder / URL target 驗證同一 loop 可行。
- 不接 Prism Go server goroutine、不改 schema/API/runtime、不碰 production data、不改 Pi deploy。
- 驗收：WebView2 內容可見、tray Show / Quit 仍有反應、關閉視窗正常退出。

## Required Reads

接續施工前先讀：

- `AGENTS.md`
- `docs/TODO.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEMA.md`
- `docs/API_REFERENCE.md`
- 需要歷史脈絡時再讀 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`
