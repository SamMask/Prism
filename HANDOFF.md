# HANDOFF — Prism active entry（2026-06-18）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`。

## Current State

- `main` 已包含 2026-06-14 local desktop / backup / dashboard 基礎工作；當時紀錄為 fast-forward 到 `24bf5f6`，未 push、未部署。
- Go primary 是唯一 current runtime owner；T001-T053 完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- i18n active UI 已完成到 zh-TW / en / ja / ko，可先視為收斂；不要再開大型 UI 抽字串批次。
- Core UX / Maintenance 三個 candidate 已完成：Home 搜尋可解釋性 UX（recent searches 只在 localStorage）、`/api/system/search-integrity` 診斷 + 手動 FTS rebuild、Settings 維護狀態總覽；未新增 semantic search、SearchHistory DB、自動修復、schema 或 deploy 變更。
- Server Dashboard Windows/no-temperature 平台不顯示 CPU 溫度 N/A 卡，改顯示資料位置卡；Pi/Linux 有溫度讀值時仍保留 CPU 溫度卡與 uptime 系統資訊。
- `.exe` 桌面化已定方向：Windows 視窗程式、WebView2、tray、單一實例、同一行程內 Go server goroutine；關閉行為預設直接結束，close-to-tray 是進階選項。
- Desktop Shell Phase 0 完成：`desktop-spike/` 已建立 isolated Win32 message-loop spike，空視窗 + tray Show/Quit 共用單一 loop；未接 WebView2、後端、schema/API/runtime、deploy 或 production data。
- Desktop Shell Phase 1-3 完成：正式桌面入口接到 `go-shadow --desktop-*`，支援 WebView2 placeholder / URL target、tray Show/Quit、同一行程 Go primary runtime goroutine、`/healthz` gate、desktop log、named mutex single-instance、debug console build 與 `-H=windowsgui` GUI build script。
- Desktop Shell Phase 4-6 完成：`scripts/build_desktop_portable.ps1` 產出 portable zip/folder，`Prism.exe` 以 `-H=windowsgui` + `main.desktopShellDefault=1` 直接進 desktop shell；雙擊預設資料放在 exe 同層 `PrismData\`，`--data-dir` / env 只作進階/debug override。runtime 不再顯示 first-run data-dir selector、不寫 `PrismPortable.json`、不建立或修補桌面捷徑；指定資料夾、Windows account data folder、桌面捷徑、WebView2 bootstrap、Start Menu、uninstall/update 都 deferred 到 installer gate。`scripts/smoke_desktop_portable.ps1` 驗證 clean unzip、external data-dir、fresh DB、desktop log 與基本 note create/search workflow。Installer/updater 仍 deferred，Pi deploy 仍是 linux/arm64 Go artifact + systemd + Caddy。
- Desktop Shell post-package follow-up 完成：主 Prism 視窗導向 runtime 前會顯示啟動畫面，避免無說明白屏；package 會帶 `static/config/prompt_options.json` / `wizard_options.json` 供 Prompt Builder fresh data-dir seed；`Prism.ico` 由程式生成方塊 + P，build scripts 會用 `rsrc` 產生暫時 `.syso` 並把 icon 內嵌進 exe resource，desktop shell 也會從 exe 同層載入視窗/tray icon。
- Desktop Shell post-package manual acceptance 完成：使用者已把最新 portable 複製到其他資料夾執行並確認 OK，Windows Defender 沒有再阻擋；簡化後的 exe 同層 `PrismData` portable baseline 可接受。
- Frontend 新使用者預設已改為淺色 / 暖灰 / 典雅金、卡片預覽模式、自動載入更多開啟；閱讀模式不再出現在卡片開啟模式選項。Windows Server Dashboard 固定不顯示 CPU 溫度卡，四格為記憶體 / 儲存空間 / 資料位置 / 資料庫狀態。
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
