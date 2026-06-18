# HANDOFF — Prism active entry（2026-06-18）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/desktop-backup-i18n-handoff-20260617.md` 與 `docs/development-history/desktop-portable-release-handoff-20260618.md`。

## Current State

- Go primary 是唯一 current runtime owner；T001-T053 完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Desktop Shell / Windows portable baseline 已完成並歸檔；current Windows release path 是 `Prism.exe` GUI app + WebView2 + same-process Go runtime，預設資料在 exe 同層 `PrismData\`。Installer/updater/WebView2 bootstrap/shortcut automation 仍 deferred。
- i18n active UI 已完成到 zh-TW / en / ja / ko；fresh browser 預設 `en`，使用者可到「設定 > 外觀」手動切換繁中 / 英 / 日 / 韓並保存至 `localStorage`。
- Core UX / Maintenance 三個 candidate 已完成：Home 搜尋可解釋性 UX、`/api/system/search-integrity` 診斷 + 手動 FTS rebuild、Settings 維護狀態總覽；未新增 semantic search、SearchHistory DB、自動修復、schema 或 deploy 變更。
- Frontend 新使用者預設已改為淺色 / 暖灰 / 典雅金、卡片預覽模式、自動載入更多開啟。Windows Server Dashboard 固定不顯示 CPU 溫度卡，四格為記憶體 / 儲存空間 / 資料位置 / 資料庫狀態。
- Variant tracking panel gate 已完成 local + Pi live verification：Go API 支援 `GET /api/notes?parent_id=<id>` direct children lookup，note list/detail 回傳 `variants_count`；ReadingView 顯示 parent link + children variants，NoteCard 顯示 variants count / quick link。2026-06-18 追加修補 duplicate-as-variant 附件保存：文字附件與長內容自動分離附件會複製成 child note 自己的 row/file，ReadingView 會 lazy-load `is_auto_extracted` 完整內容。沒有新增 schema、version tree、diff/merge 或 collaboration semantics；Pi 上 `prism-go-primary.service` active，live API/UI smoke 已通過。
- Note list lightweight gate 已完成 local verification：`GET /api/notes` list payload 回 preview-compatible `content`、`content_preview`、`content_truncated`、`content_length`；`GET /api/notes/<id>` 保持完整 note detail，搜尋仍可命中 preview 外的 tail content。Home card 使用 preview + full length metadata，Editor / card copy / image export 會先 lazy-load detail，ReadingView 維持 detail + auto-extracted attachment lazy-load。未新增 schema、cache、server-side UI state、全文預載、背景同步或附件 root 變更；尚未做 Pi delivery。
- `build/` 舊 generated smoke/build artifacts 已清理，只保留最新 desktop shell / portable smoke 輸出；不要把 DB、attachments、notes、uploads 這類真資料當 build artifact 清理。

## Next Entry

下一個建議入口是 `NOTE-LIST-LIGHTWEIGHT` 的 Pi delivery gate：先讀 `DEPLOY-PI.md`，用 Go primary artifact cutover 推到 `PI5Mask24`，再 live 驗 `GET /api/notes` preview payload、`GET /api/notes/<id>` detail 全文、tail token 搜尋、Home card preview metadata、Editor/ReadingView detail 載入與 console error=0。若先繼續本地 UX polish，下一個 candidate 建議推 `IMAGE-VIEWER-CANDIDATE-01 Unified image lightbox`。installer / updater 只有在明確需要 Start Menu、桌面捷徑、指定資料夾 UI、WebView2 bootstrap、uninstall 或 update flow 時才另開 decision gate。

## Required Reads

接續施工前先讀：

- `AGENTS.md`
- `docs/TODO.md`
- `docs/ARCHITECTURE.md`
- `docs/SCHEMA.md`
- `docs/API_REFERENCE.md`
- `DEPLOY-PI.md`（Pi delivery / live verification 時必讀）
- 需要歷史脈絡時再讀 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`
- 桌面封裝 / release 脈絡讀 `docs/development-history/desktop-portable-release-handoff-20260618.md`
