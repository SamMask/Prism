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
- Desktop Shell Phase 1-3 完成：正式桌面入口接到 `go-shadow --desktop-*`，支援 WebView2 placeholder / URL target、tray Show/Quit、同一行程 Go primary runtime goroutine、`/healthz` gate、desktop log、named mutex single-instance、debug console build 與 `-H=windowsgui` GUI build script。
- Desktop Shell Phase 4-6 完成：`scripts/build_desktop_portable.ps1` 產出 portable zip/folder，`Prism.exe` 以 `-H=windowsgui` + `main.desktopShellDefault=1` 直接進 desktop shell；第一次啟動 data-dir 選擇順序是 `--data-dir` / env、exe 同層 `PrismPortable.json`、既有 `PrismData\`、最後顯示選擇器（AppData / portable `PrismData\` / custom path）。`scripts/smoke_desktop_portable.ps1` 驗證 clean unzip、external data-dir、fresh DB、desktop log 與基本 note create/search workflow。Installer/updater 仍 deferred，Pi deploy 仍是 linux/arm64 Go artifact + systemd + Caddy。

## Next Entry

下一個建議入口是 `docs/TODO.md` 的 **Desktop Shell post-package manual acceptance**：

- 把 portable zip 放到乾淨 Windows 使用者環境，雙擊 `Prism.exe`。
- 確認 WebView2 可開、沒有終端機、資料落到 external data-dir、重開資料仍存在。
- 只有 manual acceptance 顯示 portable zip 不夠用時，才另開 installer / updater decision gate；目前不要直接引入 NSIS/WiX/MSIX 或 auto updater。

## Required Reads

接續施工前先讀：

- `AGENTS.md`
- `docs/TODO.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEMA.md`
- `docs/API_REFERENCE.md`
- 需要歷史脈絡時再讀 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`
