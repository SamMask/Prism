# HANDOFF — Prism active entry（2026-06-19）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/desktop-backup-i18n-handoff-20260617.md` 與 `docs/development-history/desktop-portable-release-handoff-20260618.md`。

## Current State

- Go primary 是唯一 current runtime owner；T001-T053 完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Desktop Shell / Windows portable baseline 已完成並歸檔；current Windows release path 是 `Prism.exe` GUI app + WebView2 + same-process Go runtime，預設資料在 exe 同層 `PrismData\`。Installer/updater/WebView2 bootstrap/shortcut automation 仍 deferred。
- i18n active UI 已完成到 zh-TW / en / ja / ko；fresh browser 預設 `en`，使用者可到「設定 > 外觀」手動切換繁中 / 英 / 日 / 韓並保存至 `localStorage`。
- Core UX / Maintenance 三個 candidate 已完成：Home 搜尋可解釋性 UX、`/api/system/search-integrity` 診斷 + 手動 FTS rebuild、Settings 維護狀態總覽；未新增 semantic search、SearchHistory DB、自動修復、schema 或 deploy 變更。
- Frontend 新使用者預設已改為淺色 / 暖灰 / 典雅金、卡片預覽模式、自動載入更多開啟。Windows Server Dashboard 固定不顯示 CPU 溫度卡，四格為記憶體 / 儲存空間 / 資料位置 / 資料庫狀態。
- Variant tracking panel gate 已完成 local + Pi live verification：Go API 支援 `GET /api/notes?parent_id=<id>` direct children lookup，note list/detail 回傳 `variants_count`；ReadingView 顯示 parent link + children variants，NoteCard 顯示 variants count / quick link。2026-06-18 追加修補 duplicate-as-variant 附件保存：文字附件與長內容自動分離附件會複製成 child note 自己的 row/file，ReadingView 會 lazy-load `is_auto_extracted` 完整內容。沒有新增 schema、version tree、diff/merge 或 collaboration semantics；Pi 上 `prism-go-primary.service` active，live API/UI smoke 已通過。
- Note list lightweight gate 已完成 local + Pi delivery：`GET /api/notes` list payload 回 preview-compatible `content`、`content_preview`、`content_truncated`、`content_length`；`GET /api/notes/<id>` 保持完整 note detail，搜尋仍可命中 preview 外的 tail content。Home card 使用 preview + full length metadata，Editor / card copy / image export 會先 lazy-load detail，ReadingView 維持 detail + auto-extracted attachment lazy-load。Pi live `https://prism.local` 已跑 Go primary cutover、API smoke 與 Playwright UI smoke；temp validation notes 已清理。未新增 schema、cache、server-side UI state、全文預載、背景同步或附件 root 變更。
- Image viewer lightbox gate 已完成 local + Pi delivery：新增純前端 shared `ImageLightbox`，ReadingView cover/markdown images、EditablePreview standalone images、NoteEditor 雙欄 gallery 與 NoteCard cover 明確 icon/button 都接同一 lightbox；Esc/左右鍵由 lightbox capture 攔截，不會連同底層 ReadingView/Editor modal 一起關閉。Pi live `https://prism.local` 已跑 Go primary cutover 與 Playwright UI smoke，temp validation note/uploads 已清理。未改 upload/delete/cleanup API、DB schema、gallery DB 或 markdown renderer。
- Header starred tag shortcuts gate 已完成 local + Pi delivery：`Settings > Organization > Tag management` 的星號使用純前端 `localStorage` key `prism.starredTags.v1`，`FilterStrip` 分類右側只顯示 starred tags；沒有 starred tags 時只顯示低存在感提示文字。Pi live `https://prism.local` 已跑 Go primary cutover 與 Playwright UI smoke，temp validation notes/tags 已清理。未新增 DB 欄位、tags API、server-side preference、跨裝置同步、tag sort/group 或 sidebar redesign。
- Batch Markdown/txt import gate 已完成 local + Pi delivery：`Settings > Backup & Restore` 新增 `.md/.txt` 多檔匯入；前端待匯入清單可多次選擇不同資料夾檔案、同檔去重、單檔移除與清空，匯入後清空待匯入清單但保留結果摘要。`.md` 逐檔走既有單檔 `POST /api/notes/import/md`，`.txt` 由前端讀檔後走既有 `POST /api/notes`，逐檔回報 created / skipped / failed。Pi live `https://prism.local` 已驗 Markdown H1、frontmatter category/tags、TXT filename title、跨批選檔累加、重複去重、混合 2 created / 1 failed summary，temp notes/tags 已清理。未新增 server-side batch API、schema、目錄 watcher、AI 摘要、自動分類、overwrite/sync/background daemon 或批量 DB transaction。
- Reading list workspace 已完成 Pi delivery：新增純前端 `localStorage` key `prism.readingWorkspace.v1`，ReadingView 可加入目前 note、顯示暫存閱讀清單、切換、移除單張、清空全部與 scroll restore；NoteCard action menu、NoteEditor toolbar 與 Header 都可加入/開啟閱讀清單，卡片開啟模式維持既有習慣；Appearance sidebar width slider 為 150-320px。Pi live `https://prism.local` 已跑 Go primary cutover，`prism-go-primary.service` active、legacy `prism.service` inactive、migration status v16 clean；live Playwright smoke 已驗 Editor toolbar 加入、Header 開啟、workspace panel、sidebar `V2.5`、HTML title `Prism V2.5`、舊「提取圖片提示詞」入口不存在、console/page/request error=0。未新增 DB schema、note API、server-side persistence、跨裝置同步、native 多視窗、雙欄比對或 diff engine。
- Version 2.5 display gate 已完成：repo 內 current version 已全面改為 `2.5`；左上角 Prism 下方顯示 `V2.5`，HTML title 顯示 `Prism V2.5`。Go primary version fallback 改為 `2.5`，且不再讀 Pi 上 legacy `config.py` 的 stale `PRISM_VERSION`；`PRISM_VERSION` env override 仍保留。
- Release checkpoint / repo hygiene gate 已完成：dirty tree 只含 Reading list workspace 功能、測試與文件收尾；ignored `build/` 已清到只保留 `build/release` 與 `build/desktop-portable-smoke`，reading workspace temp screenshots 已清理；tracked runtime/private path sweep 未發現 `.omx`、production DB/WAL/SHM、uploads、attachments、notes、env/key/log 類檔案進入 git。`main` 與 `origin/main` 在未提交工作前為 `0 0`；本 checkpoint 未 commit、未 tag、未重新 package。
- Pi deploy snapshot retention 已收斂：`go-primary-*/data-files.tar.gz` 是 deploy/cutover 前資料快照，現在預設只保留最新 5 份；每週 `prism_backup_*.db` 是獨立 DB backup，不包含已刪 uploads 圖片檔。
- Default category identity split 已完成 local + Pi delivery：migration v17 新增 `Categories.system_key` / `name_override` 與 `idx_categories_system_key`；五個系統分類以 `system_key` 作身份，使用者改名只寫 `name_override`，`is_default` 仍只作刪除分類搬移目標。`GET /api/categories` 與 JSON export/import 保留 identity 欄位，frontend 依 `system_key` 做 zh-TW / en / ja / ko 顯示，override 有值時固定顯示使用者文字。Pi live `https://prism.local` 已 cutover：`prism-go-primary.service` active、legacy `prism.service` inactive、migration v17 clean；Playwright smoke 驗四語分類切換、暫時改名跨語系固定顯示、清回 `name_override=null`、console/page/request error=0。
- `build/` 舊 generated smoke/build artifacts 已清理，只保留 `build/release` 與最新 desktop shell / portable smoke 輸出；不要把 DB、attachments、notes、uploads 這類真資料當 build artifact 清理。

## Next Entry

目前沒有未交付的 active construction item。若要發佈，入口是 commit / tag / package checklist：先確認 commit scope 只含已完成的 Reading list workspace、version 2.5、Pi snapshot retention、Default category identity split 與文件/測試收尾，再依 Lore Commit Protocol commit，視需要重建/確認 release package 與 tag。若要繼續產品功能，需先從 `docs/TODO.md` 的 Future Branch Candidates 明確 promote 一個最小 gate；installer / updater 只有在明確需要 Start Menu、桌面捷徑、指定資料夾 UI、WebView2 bootstrap、uninstall 或 update flow 時才另開 decision gate。不要自動開 AI、semantic search、installer 或 updater 實作。

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
