# HANDOFF — Prism active entry（2026-06-18）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/desktop-backup-i18n-handoff-20260617.md` 與 `docs/development-history/desktop-portable-release-handoff-20260618.md`。

## Current State

- Go primary 是唯一 current runtime owner；T001-T053 完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Desktop Shell / Windows portable baseline 已完成並歸檔；current Windows release path 是 `Prism.exe` GUI app + WebView2 + same-process Go runtime，預設資料在 exe 同層 `PrismData\`。Installer/updater/WebView2 bootstrap/shortcut automation 仍 deferred。
- i18n active UI 已完成到 zh-TW / en / ja / ko；fresh browser 會先依 OS/browser 在中/英/日/韓內偵測，簡中/繁中都落到 `zh-TW`，其他語系預設 `en`；自行切換後存在 localStorage。
- Core UX / Maintenance 三個 candidate 已完成：Home 搜尋可解釋性 UX、`/api/system/search-integrity` 診斷 + 手動 FTS rebuild、Settings 維護狀態總覽；未新增 semantic search、SearchHistory DB、自動修復、schema 或 deploy 變更。
- Frontend 新使用者預設已改為淺色 / 暖灰 / 典雅金、卡片預覽模式、自動載入更多開啟。Windows Server Dashboard 固定不顯示 CPU 溫度卡，四格為記憶體 / 儲存空間 / 資料位置 / 資料庫狀態。
- `build/` 舊 generated smoke/build artifacts 已清理，只保留最新 desktop shell / portable smoke 輸出；不要把 DB、attachments、notes、uploads 這類真資料當 build artifact 清理。

## Next Entry

Desktop Shell 目前沒有 active construction item。下一個建議入口是使用者選定的新產品/維護候選；installer / updater 只有在明確需要 Start Menu、桌面捷徑、指定資料夾 UI、WebView2 bootstrap、uninstall 或 update flow 時才另開 decision gate。

## Required Reads

接續施工前先讀：

- `AGENTS.md`
- `docs/TODO.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEMA.md`
- `docs/API_REFERENCE.md`
- 需要歷史脈絡時再讀 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`
- 桌面封裝 / release 脈絡讀 `docs/development-history/desktop-portable-release-handoff-20260618.md`
