# Prism Active TODO

本檔只保留目前可施工的 active roadmap、候選 backlog 與下一步入口。完成紀錄、舊 phase 與長版 changelog 全部移到 `docs/development-history/`。

---

## Current Truth（2026-06-19）

- Go primary 是唯一 current runtime owner；Python Flask backend source 已於 T053 移除。
- Go 漸進重構 T001-T053 已完成，完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- 2026-06-16 Core UX intake 已吸收；已完成項與 2026-06-14/06-17 handoff 快照見 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`。
- 2026-06-17 Core UX / Maintenance 三個 candidate 已完成：搜尋可解釋性 UX、search integrity diagnostics + 手動 FTS rebuild、maintenance health overview。未新增 semantic search、SearchHistory DB、自動修復、schema/API exposure boundary 或 Pi deploy 變更。
- 2026-06-17 Server Dashboard Windows 硬體顯示已收斂：Windows 不顯示 CPU 溫度 N/A 卡，改以資料位置卡補位；Pi/Linux 有溫度讀值時仍顯示 CPU 溫度與 uptime 系統資訊。
- 2026-06-17/18 Desktop Shell Phase 0-6、post-package follow-up 與 manual acceptance 已完成；長版完成紀錄見 `docs/development-history/desktop-portable-release-handoff-20260618.md`。
- Windows portable current truth：`Prism.exe` 直接進 desktop shell，預設資料在 exe 同層 `PrismData\`；`--data-dir` / `PRISM_GO_DATA_DIR` 只作進階/debug override。runtime 不顯示 first-run data-dir selector、不寫 `PrismPortable.json`、不建立/修補桌面捷徑。Installer/updater/WebView2 bootstrap/Start Menu/uninstall/update 仍 deferred。
- 2026-06-18 Desktop Shell post-package manual acceptance 已由使用者確認：將最新 portable 複製到其他資料夾執行後，Windows Defender 未再阻擋，雙擊 `Prism.exe` 可正常開啟，簡化後的 `PrismData\` 同層資料路線成立。
- 新使用者前端預設值（無 localStorage 時）已收斂為淺色 / 暖灰 / 典雅金、卡片開啟預覽模式、自動載入更多開啟；語系不再自動偵測 OS/browser，預設 `en`，使用者可到「設定 > 外觀」手動切換繁中 / 英 / 日 / 韓並保存至 `localStorage`；閱讀模式仍保留元件但不再是卡片開啟模式選項。
- 2026-06-18 Variant tracking panel gate 已完成：`GET /api/notes?parent_id=<id>` 可查 direct child variants，note list/detail 回傳 `variants_count`；ReadingView 顯示 parent link + children variants 並可跳轉，NoteCard 顯示 variants count / quick link。未新增版本樹、diff/merge、協作語義、schema migration 或大型卡片樹狀 UI。
- 2026-06-18 Variant tracking panel 已完成 Pi delivery：依 `DEPLOY-PI.md` 透過 Go primary artifact cutover 推到 `PI5Mask24`，`prism-go-primary.service` active、legacy `prism.service` inactive、migration status v16 clean；live API 與 headless Chrome CDP smoke 已驗 `GET /api/notes?parent_id=<id>`、card variants count、ReadingView parent/child 跳轉與 console error=0。
- 2026-06-18 Variant duplicate attachment repair 已完成 local + Pi delivery：`POST /api/notes/<id>/duplicate` / as-variant 會複製既有文字附件與長內容自動分離附件，子 note 取得自己的 `Note_Attachments` row 與實體檔；ReadingView 會 lazy-load `is_auto_extracted` 附件全文。Live API smoke 與 Playwright UI smoke 已驗 child variant 可讀完整附件全文並清理 temp notes/files。這不是新版本樹、diff/merge 或 note-list partial-load API。
- 2026-06-18 Note list lightweight gate 已完成 local + Pi delivery，2026-06-19 first-image hint regression 也已完成 Pi delivery：`GET /api/notes` list payload 只回 `content_preview` / `content_truncated` / `content_length` / `content_first_image` 與相容 preview `content`；`content_first_image` 只保留卡片/閱讀在無手動封面時用第一張圖的 fallback，不回傳全文。`GET /api/notes/<id>` 保持完整 note detail，搜尋仍以 DB/attachment body contract 執行。Home card 使用 preview + full length metadata；Editor、card copy 與 image export 會先 lazy-load detail，ReadingView 維持 detail + auto-extracted attachment lazy-load。Pi live `https://prism.local` 已驗 list preview 不洩 tail、detail/search 命中 tail、Home card preview、Editor/ReadingView detail 載入、`content_first_image` late-image API regression 與真實 Home card cover fallback，temp validation note/image 已清理，console/page error=0。未新增 schema migration、cache layer、server-side UI state、全文預載、背景同步或附件 root 變更。
- 2026-06-18 Image viewer lightbox gate 已完成 local + Pi delivery：`ImageLightbox` 是純前端 shared component，ReadingView cover/markdown images、EditablePreview standalone images、NoteEditor 雙欄 gallery 與 NoteCard cover 明確 icon/button 都走同一 lightbox；Esc/左右鍵在 lightbox capture 階段攔截，不會連同底層 ReadingView/Editor modal 一起關閉。Pi live `https://prism.local` 已驗 card cover、ReadingView cover/markdown、Editor preview lightbox、console error=0，temp validation note/uploads 已清理。未改 upload/delete/cleanup API、DB schema、gallery DB 或 markdown renderer。
- 2026-06-19 Image viewer zoom follow-up 已完成 local gate：shared `ImageLightbox` 新增放大/縮小/重設縮放、背景點擊關閉與 ArrowUp/ArrowDown 快捷鍵；切換圖片或重開 lightbox 會回 100%/fit，ReadingView、EditablePreview、NoteEditor gallery 與 NoteCard cover 仍共用同一 viewer。未改 upload/delete/cleanup API、附件 contract、DB schema、gallery DB、per-image zoom persistence 或 Pi delivery。
- 2026-06-18 Header starred tag shortcuts gate 已完成 local + Pi delivery：`Settings > Organization > Tag management` 的星號只保存純前端 `localStorage` key `prism.starredTags.v1`，`FilterStrip` 分類右側只顯示 starred tags；沒有 starred tags 時只顯示低存在感提示文字。Pi live `https://prism.local` 已驗星號開關、reload persistence、header 顯示/隱藏、tag filter 點擊與 console error=0，temp validation notes/tags 已清理。未新增 DB 欄位、tags API、server-side preference、跨裝置同步、tag sort/group 或 sidebar redesign。
- 2026-06-18 Batch Markdown/txt import gate 已完成 local + Pi delivery：`Settings > Backup & Restore` 新增 `.md/.txt` 多檔匯入；前端待匯入清單可多次選擇不同資料夾檔案、同檔去重、單檔移除與清空，匯入後清空待匯入清單但保留結果摘要。`.md` 逐檔走既有單檔 `POST /api/notes/import/md`，`.txt` 由前端讀檔後走既有 `POST /api/notes`，結果逐檔回報 created / skipped / failed。Pi live `https://prism.local` 已驗 Markdown H1 title、frontmatter category/tags、TXT 檔名 title、跨批選檔累加、重複去重、混合 2 created / 1 failed summary、temp note/tag cleanup 與 Go journal evidence。未新增 server-side batch API、schema migration、目錄 watcher、AI 摘要、自動分類、overwrite/sync/background daemon 或批量 DB transaction。
- 2026-06-18 Reading list workspace 已完成 Pi delivery：新增純前端 `localStorage` key `prism.readingWorkspace.v1`，ReadingView 可加入目前 note、顯示暫存閱讀清單、切換、移除單張、清空全部與 scroll restore；NoteCard action menu、NoteEditor toolbar 與 Header 都可加入/開啟閱讀清單，卡片開啟模式維持既有習慣；Appearance sidebar width slider 為 150-320px。Pi live `https://prism.local` 已跑 Go primary cutover，`prism-go-primary.service` active、legacy `prism.service` inactive、migration status v16 clean；live Playwright smoke 已驗 Editor toolbar 加入、Header 開啟、workspace panel、sidebar `V2.5`、HTML title `Prism V2.5`、舊「提取圖片提示詞」入口不存在、console/page/request error=0。未新增 DB schema、note API、server-side persistence、跨裝置同步、native 多視窗、雙欄比對或 diff engine。
- 2026-06-18 Version 2.5 display gate 已完成：repo 內 current version 已全面改為 `2.5`；左上角 Prism 下方顯示 `V2.5`，HTML title 顯示 `Prism V2.5`。Go primary version fallback 改為 `2.5`，且不再讀 Pi 上 legacy `config.py` 的 stale `PRISM_VERSION`；`PRISM_VERSION` env override 仍保留。
- 2026-06-18 release checkpoint / repo hygiene gate 已完成：dirty tree 範圍只含 Reading list workspace 功能、測試與文件收尾；ignored `build/` 產物已清到只保留 `build/release` 與 `build/desktop-portable-smoke`，系統 temp 的 reading workspace smoke screenshots 也已清理；tracked runtime/private path sweep 未發現 `.omx`、production DB/WAL/SHM、uploads、attachments、notes、env/key/log 類檔案進入 git，既有 `resources/demo_db/knowledge_demo.db` 仍是 demo fixture。`main` 與 `origin/main` 在未提交工作前為 `0 0`；本 checkpoint 未 commit、未 tag、未重新 package。
- 2026-06-19 Pi deploy snapshot retention 已收斂：`scripts/go_primary_pi_live_ops.ps1` 的 pre-cutover `go-primary-*/data-files.tar.gz` snapshot 預設只保留最新 5 份，cutover smoke 通過後自動清理舊 snapshot；每週 `prism_backup_*.db` 仍是獨立 DB backup/rotate 流程，不能代替 uploads data snapshot。
- 2026-06-19 Default category identity split 已完成 local + Pi delivery：`Categories` schema 升到 migration v17，新增 `system_key` / `name_override` 與 `idx_categories_system_key`；五個系統分類以 `system_key` 作身份，使用者改名只寫 `name_override`，`is_default` 仍只作刪除分類搬移目標。Pi live `https://prism.local` 已完成 Go primary cutover，`prism-go-primary.service` active、legacy `prism.service` inactive、migration status v17 clean；live API 驗五個系統分類 `system_key` 正確且測試後 `name_override=null`，Playwright smoke 驗 zh-TW / en / ja / ko 分類顯示、暫時改名後跨語系固定顯示、清除 override 後回語系顯示、console/page/request error=0。
- 2026-06-19 Prism 深度掃描報告已產出：`20260619_Prism_深度掃描報告.md`。掃描當輪已修 request log query leak、CSRF origin prefix bypass、UTF-8 search query truncate、local artifact smoke migration hardcode，並同步 root/docs 最新進度。
- 2026-06-19 `DEEP-SCAN-RISK-CANDIDATE-01` 01A-01G 已完成 local gate：markdown render path 改為 DOMPurify sanitizer；文字附件 upload/read 同步 1 MiB hard limit；server DB backup/download/rotate 改 SQLite consistent DB snapshot；category invalid payload / delete target validation 回 400/404；bounded attachment body search 超限回 optional partial diagnostics；no-auth/local-only exposure boundary 有 runtime/docs regression；stability pack 補搜尋同步、中文/emoji、missing/Windows attachment path 與 bad pending-restore marker。未新增 auth、AI、schema、search index、備份平台、Pi deploy 或 Go runtime 大拆。
- 2026-06-19 `PROJECT_REVIEW.md` 與 image viewer follow-up 已完成 TODO 去重 intake：P1/P2 runtime/security findings 由 `DEEP-SCAN-RISK-CANDIDATE-01` 承接；未重複的新工作只新增 `IMAGE-VIEWER-ZOOM-CANDIDATE-01` 與 `PROJECT-REVIEW-HYGIENE-CANDIDATE-01`。
- `build/` 舊 generated smoke/build artifacts 已清理，只保留 `build/release` 與最新 desktop shell / portable smoke 輸出；真實資料目錄（DB、attachments、notes、uploads）未納入清理。
- i18n active UI 可先視為完成；不要再開大型 UI 抽字串批次。Hidden/deferred UI（`PortConfigSection`、`UpdateSection`、`TagInput`）若日後恢復 render，再於該 gate 同步補四語 key。

Current truth 仍以本檔、`docs/ARCHITECTURE.md`、`docs/SCHEMA.md`、`docs/API_REFERENCE.md` 與實際 source/runtime 為準。不得因歷史報告曾討論過，就直接擴 scope 成 AI、semantic search、GraphRAG、auto-writing、schema/API/runtime 或 Pi deploy 變更。

---

## 下一個可施工入口

### Desktop Shell / Release Packaging

Desktop Shell 目前沒有 active construction item。Phase 0-6、post-package follow-up、manual acceptance 與 release baseline 已歸檔到 `docs/development-history/desktop-portable-release-handoff-20260618.md`。

下一個 desktop/packaging 入口只在使用者明確需要 installer/updater 類功能時成立，包括 Start Menu、桌面捷徑、指定資料夾 UI、WebView2 bootstrap、uninstall 或 update flow。啟動前必須另開 decision gate；不得直接引入 NSIS/WiX/MSIX、auto updater、shortcut automation 或 hidden PowerShell。

### Pi Delivery Follow-up

Variant tracking panel、variant duplicate attachment repair、Note list lightweight、Image viewer lightbox、Header starred tag shortcuts、Batch Markdown/txt import、Reading list workspace 與 Version 2.5 display gate 的 Pi delivery 已於 2026-06-18 完成。後續若要把其他 UX/API gate 上 Pi，需另開 Pi delivery gate：先讀 `DEPLOY-PI.md`，使用 Go primary live ops 流程部署到 `PI5Mask24`，並驗證 `https://prism.local` 的 service status、migration status、changed API endpoint 與對應前端行為。

### Release Checkpoint / Repo Hygiene

2026-06-18 checkpoint 已完成，沒有未交付的 active construction item。若要發佈，下一步是明確執行 commit / tag / package checklist；若要繼續產品功能，先從 Future Branch Candidates 或新的使用者需求 promote 一個最小 gate，不自動開 AI、semantic search、installer 或 updater 實作。

### Deep Scan Risk Follow-up（2026-06-20）

`DEEP-SCAN-RISK-CANDIDATE-01` 的 01A-01G 已完成 local gate。01H 仍是低優先維護 triage，只有在要主動整理 frontend bundle/browserslist warning、歷史 frozen docs/test wording 或 route-local Go 小整理時才 promote；不得把 01H 擴成 code-splitting 大重構、批量歷史改寫或整檔 Go runtime 拆分。

若要接下一個可施工項，建議優先處理 `PROJECT-REVIEW-HYGIENE-CANDIDATE-01` 的 **01A LICENSE consistency gate**，因為這是 GitHub/release/reuse readiness 的最小明確缺口，且不牽涉 runtime schema/API。

### Windows Desktop vs Pi Deployment 差異表

| 面向 | Windows desktop | Raspberry Pi |
|---|---|---|
| 入口 | `Prism.exe` GUI app；正式 build 不出現終端機 | systemd service 啟動 Go primary binary |
| UI | WebView2 內嵌本機 Web UI + tray | 使用瀏覽器連 `https://prism.local` / Caddy |
| Runtime | 同一行程內 desktop shell + Go server goroutine | headless Go primary service |
| 網路 | 綁 `127.0.0.1:<port>`，只給本機 WebView2 | Caddy reverse proxy 到 local service port |
| 資料 | 預設 exe 同層 `PrismData\`；`--data-dir` / env 僅作進階 override | Pi 上既有 production data dir |
| Log | 檔案 log + debug console build | journald / service log / Go runtime log |
| 打包 | 先 portable zip / folder；installer deferred | artifact deploy + systemd + rollback / soak |
| 相依 | WebView2 Runtime、Win32 shell APIs | Linux/arm64、systemd、Caddy |
| 不共用項 | tray、window、mutex、`-H=windowsgui` | Caddy live routing、systemd enable/restart |

---

## Active Candidates

### Deep Scan Risk Follow-up Queue

#### DEEP-SCAN-RISK-CANDIDATE-01 2026-06-19 scan risk closure

來源：`20260619_Prism_深度掃描報告.md`。

目標：用小步、可驗證、低風險修補關閉深度掃描找到的實際風險與測試缺口。這不是大重構，也不是新增平台能力；不得因安全/維護性名義引入 enterprise-style 架構。

共同邊界：

- 一次只 promote 一個子項；每個子項完成後再決定下一項。
- 不新增 AI / semantic search / embeddings / 多使用者 auth / cloud sync。
- 不做 `go-shadow/main.go` 一次性大拆；只有在修該子項時順手抽出明顯重複或必要 helper。
- 不改公開 API contract，除非該子項明確要求並同步 `docs/API_REFERENCE.md`、tests 與前端呼叫。
- 不改 DB schema；若實作證明必須改 schema，先另開 schema contract，不在本 candidate 內偷做。
- 涉及 Pi live delivery 時，先讀 `DEPLOY-PI.md`，使用 Go primary live ops 流程，並驗 service/header/migration/API/UI smoke；純 local/docs/test 子項不自動部署 Pi。

- [x] **01A Markdown rendering sanitization（P1，2026-06-19 完成）**
  - 風險：`ReadingView` / `EditablePreview` 直接把 `marked()` 結果送進 `dangerouslySetInnerHTML`，未見 sanitizer；惡意 note/import/attachment markdown 可能形成 stored XSS，並同源呼叫本機 `/api/*`。
  - 施工範圍：只處理 markdown render path；優先用本地已安裝或小型明確 dependency / existing sanitizer；不得改 note schema、不得重寫 editor、不得新增 markdown WYSIWYG、不得新增 auth 系統。
  - 驗收：`<script>`、`onerror`、`javascript:` link、iframe/svg、HTML comment、中文 markdown 混排都不能執行 unsafe HTML；正常 markdown、圖片 lightbox、code block、link rendering 不退化。
  - 驗收：`frontend/src/utils/markdown.ts` 使用 DOMPurify 統一 sanitizer；ReadingView / EditablePreview 不再直接 import/use `marked()` output，`<script>`、event handler、`javascript:` URL、iframe/svg/raw HTML comments 由 sanitizer gate 處理；正常 markdown/code/link/image lightbox 保留。
  - 驗證：`pytest tests/test_markdown_sanitization.py -q`、`cd frontend && npm run build`、local Playwright smoke、Loop gate。

- [x] **01B Attachment upload hard size gate（P2，2026-06-19 完成）**
  - 風險：`POST /api/notes/<id>/attachments` 用 `ParseMultipartForm(maxUploadFileBytes)` 後直接 `io.Copy`，沒有像 image upload 一樣用 `LimitReader` 明確拒絕超限內容；read path 又受 `maxAttachmentFileBytes` 限制。
  - 施工範圍：讓文字附件 upload limit 與 read limit / documented contract 對齊；若採 1 MiB，API error 要明確；若採 5 MiB，read path 與 docs/test 必須一起調整。
  - 驗收：超限 `.md/.txt/.markdown` 不留下 DB row 或 partial file；missing note / unsupported extension / valid small upload 行為不退化。
  - 驗收：文字附件 upload 以 1 MiB 為 hard limit；超限回明確 400，不留下 `Note_Attachments` row 或 partial file；missing note / unsupported extension / valid small upload 行為已鎖。
  - 驗證：`TestAttachmentUploadRejectsOversizedTextWithoutRowOrPartialFile`、`cd go-shadow && go test ./...`、Loop gate。

- [x] **01C Backup WAL snapshot proof（P2，2026-06-19 完成）**
  - 風險：`/api/server/backup/download` 目前是 transient `.db` copy；報告未確認 WAL active write 下是否包含最新交易。DB backup 也不包含 `static/uploads/` / `docs/attachments/`，容易和 deploy data snapshot 混淆。
  - 施工範圍：先用 test/proof 確認現況；若 DB-only copy 不足，改 SQLite online backup 或明確 WAL checkpoint strategy。不得做大型備份平台，不改 data snapshot retention policy。
  - 驗收：active WAL write 後下載/rotate backup 可通過 integrity check，且包含預期最新 DB state；docs 清楚區分 DB backup 與 data snapshot。
  - 驗收：`/api/server/backup/download` 與 `/api/server/backup/rotate` 改用 SQLite `VACUUM INTO` consistent DB snapshot；active WAL 最新 DB state 可在 download/rotate backup 中查到；API/DEPLOY docs 明確標記 DB-only，不包含 uploads/attachments data snapshot。
  - 驗證：`TestBackupDownloadAndRotateIncludeLatestWALState`、`cd go-shadow && go test ./...`、Loop gate。

- [x] **01D Category API invalid input hardening（P2，2026-06-19 完成）**
  - 風險：category update 的 `name` / `name_override` 型別錯誤目前可能回 500；delete category 有 notes 時未先驗 `target_category_id` 是否存在或等於自己，錯誤可讀性不足。
  - 施工範圍：只修 validation 與 error code/message；不改 category identity schema，不改 frontend category workflow。
  - 驗收：wrong JSON type 回 400；missing target / invalid target / self target 有明確 400/404；合法 update/delete/migrate notes 不退化。
  - 驗收：`name` / `name_override` wrong type 回 400；delete category 的 missing/wrong/self/missing target 回明確 400/404；合法 delete + migrate notes 不退化。
  - 驗證：`TestCategoryInvalidPayloadsReturnClientErrorsAndValidMigrationStillWorks`、`cd go-shadow && go test ./...`、Loop gate。

- [x] **01E Attachment search bounded-scan transparency（P2，2026-06-19 完成）**
  - 風險：文字附件 body search 有 200 files / 5 MiB / 250 ms 上限；超過上限時可能漏結果，且目前對使用者/Agent 不透明。
  - 施工範圍：先鎖 current bounded behavior 測試；再決定是否只補 docs/API note，或在不破壞 response contract 的前提下回傳 partial scan hint。不得取消上限、不得把附件全文塞進 FTS、不得引入新索引/schema。
  - 驗收：大量附件時不吃爆 memory/time；超限行為可診斷；一般中文/英文/符號搜尋不退化。
  - 驗收：bounded attachment body scan 保留 200 files / 5 MiB / 250 ms 上限；超限時 list response 可回 `search_diagnostics.attachment_body_scan.partial=true` 與 reason/limits/scanned counts；一般附件 body search 不退化。
  - 驗證：`TestAttachmentBodySearchReportsPartialWhenScanLimitIsHit`、`TestStabilityPackSearchSyncUnicodeAndUnsafeAttachmentPaths`、`cd go-shadow && go test ./...`、Loop gate。

- [x] **01F Local exposure / no-auth boundary audit（P2，2026-06-19 完成）**
  - 風險：Prism 無內建 auth 是明確設計；若 raw Go/Caddy 被 public internet 暴露，`/api/*` 風險不可接受。`/api/server/*` 依 localhost/proxy boundary 與 CSRF 控制，需要保持文件與 runtime 一致。
  - 施工範圍：只補啟動/health/docs/test guard；不得直接新增 login、OAuth、JWT、RBAC、API key 或多使用者系統。
  - 驗收：non-local bind guard、public bind warning、Origin/Referer same-origin、server/system localhost assumptions 有 regression；README / DEPLOY-PI / API docs warning 一致。
  - 驗收：non-local bind 預設拒絕且錯誤訊息保留 no-auth warning；`PRISM_GO_ALLOW_PUBLIC_BIND=1` 只作明確 override；healthz 回報 `auth:none` / public exposure policy；`/api/server/*` remote address 403；README / DEPLOY-PI / API warning 一致。
  - 驗證：`TestExposureBoundaryRegressionGuards`、既有 `TestCSRFProtectMiddleware` / `TestCSRFProtectionToggleHandlerAndGate`、Loop gate。

- [x] **01G Stability test-gap pack（P2/P3，2026-06-19 完成）**
  - 風險來源：掃描報告列出的空資料庫、中文/emoji/特殊字元、大量文件、update/delete 後搜尋同步、檔案不存在、Windows 路徑、port occupied、DB lock/concurrent request、壞 DB / restore pending marker 等測試缺口。
  - 施工範圍：這不是單一大任務；明天若要做，先選一組最小相關 tests，例如「搜尋同步 + 中文/emoji」或「Windows path + missing attachment」。不得一次補完整壓測框架。
  - 驗收：每個 promoted test pack 要有明確 fixture、失敗前提與 runtime owner；只補測試時不得改 runtime。
  - Promoted pack：搜尋同步 + 中文/emoji + missing/Windows attachment path + bad pending-restore marker。未做 port occupied/DB lock 壓測框架，保留到未來有明確 runtime failure 時再 promote。
  - 驗收：note update/delete 後 FTS/search sync；中文/emoji title/content 與 unicode attachment body 不破壞搜尋；missing file / Windows absolute attachment path 不 crash、不逃逸 data dir；bad/missing pending restore marker 不阻塞啟動且會移除 marker、保留 current DB。
  - 驗證：`TestStabilityPackSearchSyncUnicodeAndUnsafeAttachmentPaths`、`TestPendingRestoreBadMarkerIsDroppedAndKeepsCurrentDB`、Loop gate。

- [ ] **01H Low-priority maintenance triage（P3，前三項完成後再看）**
  - 風險：frontend bundle size / browserslist warning、`go-shadow/main.go` 單檔過大、歷史 frozen docs/tests 仍含 migration 16 字樣。
  - 施工範圍：只做真正降低風險的小整理；不做 code-splitting 大重構、不批量改歷史 evidence、不為了美觀拆 Go runtime。
  - 驗收：若只修 docs/tooling，`git diff --check` + relevant regression；若動 frontend build config，跑 `npm run build`；若動 Go 檔案，跑 `go test ./...`。

不建議現在做：

- 內建登入 / 多使用者 / API token / OAuth / RBAC。
- semantic search / AI / embedding / GraphRAG。
- 大型備份平台、目錄 watcher、背景同步 daemon。
- 一次性重寫 markdown editor 或拆分整個 Go runtime。

### Project Review Hygiene Backlog

#### PROJECT-REVIEW-HYGIENE-CANDIDATE-01 GitHub / reuse readiness

來源：`PROJECT_REVIEW.md`。

目標：把外部 fork / GitHub release / reuse 會踩到、且尚未被 `DEEP-SCAN-RISK-CANDIDATE-01` 覆蓋的專案衛生缺口拆成小 gate。這不是 runtime 功能開發，也不是 public service 化。

共同邊界：

- 不重複 markdown sanitization、attachment size gate、backup WAL proof、category invalid input、no-auth boundary 這些已在 deep-scan queue 的 P1/P2 項目。
- 不新增登入、OAuth、JWT、RBAC、cloud sync、telemetry 或 SaaS 多使用者假設。
- 不為了 CI / release hygiene 大拆 `go-shadow/main.go`；單檔過大只在相關 route 維修時小步整理。
- 不自動部署 Pi；Pi/live 驗證只在 release 或 deploy gate 明確需要時依 `DEPLOY-PI.md` 執行。

- [ ] **01A LICENSE consistency gate**
  - 問題：README 宣稱 MIT / See `LICENSE`，但 repo root 未見 `LICENSE` / `LICENSE.md` / `COPYING`。
  - 施工範圍：若 owner 確認維持 MIT，新增 root `LICENSE` 並確認 README / release package wording 一致；若不是 MIT，先更新 README 與 release metadata，不偷改授權語意。
  - 驗收：clean checkout 可直接看到明確授權檔；README 不再指向不存在的 license file。

- [ ] **01B GitHub CI baseline**
  - 問題：repo root 未見 `.github/workflows`，外部導入者無法從 GitHub 狀態判斷基本驗證是否通過。
  - 施工範圍：新增無祕密、無 Pi 依賴的 baseline workflow；至少跑 Go tests、frontend type/build check、pytest contract gate 的可負擔 subset 或 full gate。
  - 驗收：PR / push 能在 clean runner 上重現主要本機驗證；不需要 SSH、Pi、production DB、uploads 或 private path。

- [ ] **01C Verification environment alignment**
  - 問題：`PROJECT_REVIEW.md` 記錄本機 pytest 版本與 `requirements.txt` pin 不一致；導入者可能不知道應採 pinned env 或 local toolchain。
  - 施工範圍：決定並記錄測試環境真實 contract；必要時同步 requirements / docs / CI install step。
  - 驗收：README / docs / CI 對 pytest、Go、Node/npm 版本要求一致；不把未驗證版本宣稱為 supported。

- [ ] **01D Release validation checklist**
  - 問題：外部 release claim 需要 full gate、frontend build、browser/desktop smoke 證據；單次 source review 不足以宣稱 release asset 可用。
  - 施工範圍：補 release 前 checklist 或 script entry；至少列 `pytest tests/ -v`、`cd go-shadow && go test ./...`、`cd frontend && npm run build`、local browser smoke、desktop portable smoke 的證據欄位。
  - 驗收：每次 public release / tag / package claim 都能對應新鮮驗證日期與結果；未跑項目必須明確列為 Not-tested。

- [ ] **01E Small docs consistency cleanup**
  - 問題：`PROJECT_REVIEW.md` 記錄 CONTRIBUTING 的 e2e 路徑與 repo 實際 `e2e/` 目錄有小落差，README release/license wording 也依賴 01A/01D。
  - 施工範圍：只修明確不一致的 docs；不批量改歷史 archived evidence，不改 runtime。
  - 驗收：`git diff --check`、相關 docs path check、AGENTS/CLAUDE mirror check（若有 touching agent guidance）。

### Core UX / Maintenance

- [x] **SEARCH-UX-CANDIDATE-01 Search explainability UX**（2026-06-17 完成）：Home 已加入 Search Context Bar、Empty State Recovery、Search Scope Hint、Recent Searches（`localStorage` 最多 5 筆、不進 DB）、Mobile Search Entry。未新增 relevance ranking、semantic search、attachment body snippets、SearchHistory DB、advanced query language 或每鍵即時搜尋。
- [x] **SEARCH-INTEGRITY-CANDIDATE-01 Search integrity diagnostics contract**（2026-06-17 完成）：已新增 `GET /api/system/search-integrity` 與 `POST /api/system/search-integrity/rebuild-fts`。第一版只做診斷與手動 FTS rebuild；禁止 VACUUM、改 Notes、改 Attachments、刪檔、自動修復、讓 Agent 自動觸發。
- [x] **MAINT-OVERVIEW-CANDIDATE-01 Maintenance health overview**（2026-06-17 完成）：Settings 維護頁已新增狀態總覽，只呈現資料一致性、搜尋索引與 WAL 手動狀態；不新增修復行為。

### Supplemental UX Backlog

以下補充功能目前只是 low-priority 候選；先記錄方便日後想做時 promote。不得因列在此處就自動施工、擴 schema、改 API contract 或引入大型 UI 重構。Promote 時一次只拉一個最小 gate；若該 gate 需要 API/schema contract，先補 `docs/API_REFERENCE.md` / targeted tests，再做 UI。

#### VARIANT-PANEL-CANDIDATE-01 Variant tracking panel

目標：在卡片或閱讀頁補一個輕量變體追蹤面板，顯示 parent link 與 children variants，並可直接跳轉到相關 note。

- [x] **01A Children lookup contract**（2026-06-18 完成）：沿用既有 `Notes.parent_id`、`parent_title`、`POST /api/notes/<id>/duplicate` as-variant 行為；新增最小 read-only `GET /api/notes?parent_id=<id>` direct children lookup，note list/detail 回傳 `variants_count`。已同步 `docs/API_REFERENCE.md`、`docs/CONTRACTS.md` 與 targeted Go/API regression；未新增版本樹、diff engine、merge、collaboration semantics。
- [x] **01B Reading view panel**（2026-06-18 完成）：`ReadingView` 顯示 parent link + children variants list；點擊 parent/child 會載入相關 note 並保留現有 modal workflow。children lookup 失敗時顯示明確 unavailable 狀態，不假造 children。
- [x] **01C Card affordance polish**（2026-06-18 完成）：`NoteCard` 保留既有 lineage badge，新增 variants count 與 action menu quick link；未把卡片改成樹狀列表，也未改卡片預設 preview 開啟習慣。
- [x] **01D Attachment preservation repair**（2026-06-18 完成）：variant duplicate 複製 `Note_Attachments` rows 與實體 `.md/.txt/.markdown` 檔，長內容自動分離檔改寫到 child note 自己的 `docs/notes/note_<child_id>.md`；ReadingView 打開 note 時 lazy-load `is_auto_extracted` 附件全文。未改 DB schema，未新增 note-list partial-load API。
- 驗收：Loop gate 已跑 `.loop/verify-gate.ps1`；targeted Go/API、frontend build、API smoke 與 headless Chrome CDP / Playwright rendered smoke 已覆蓋 parent note、variant child lookup、無 child count、卡片 variants count、ReadingView parent/child 跳轉、variant duplicate attachment preservation、ReadingView auto-extracted attachment lazy-load 與 console error=0。Pi delivery 已跑 `scripts/go_primary_pi_live_ops.ps1 -Mode Cutover`，live `https://prism.local` 驗證同一 variant contract、child auto attachment full-content read、ReadingView child variant full-content render，temp validation notes/files 已清理。

#### NOTE-LIST-LIGHTWEIGHT-CANDIDATE-01 Partial note payloads for Home/list

目標：降低 Home / 卡片列表載入大量長文時的記憶體與 network 壓力；列表只拿可渲染卡片需要的 preview/detail metadata，打開 ReadingView 或 Editor 才讀完整內容或 lazy-load 自動分離附件。

- [x] **01A Read contract inventory**（2026-06-18 完成；2026-06-19 補 first-image fallback regression）：已盤點 list `content` 依賴：卡片 preview / cover fallback / word count、card copy、card image export、ReadingView initial note、Editor open 與搜尋結果。採相容策略：list `content` 保留為 preview 字串，同步新增 `content_preview` / `content_truncated` / `content_length` / `content_first_image`；需要全文的 flow 改為 lazy-load detail。
- [x] **01B Backend list payload gate**（2026-06-18 完成）：`GET /api/notes` list 只投影 preview payload；`GET /api/notes/<id>` 維持完整 note detail；Go regression 鎖住 list 不洩漏長文尾段、detail 保留全文、搜尋仍可命中 preview 之外的 tail token。
- [x] **01C Frontend lazy detail gate**（2026-06-18 完成）：Home card 使用 preview 與 `content_length` metadata；NoteCard 開 Editor、複製內容、匯出圖片前會先抓 detail；ReadingView 已維持 detail + `is_auto_extracted` attachment lazy-load。未改卡片預設預覽模式，也未新增快取或全文預載。
- 不做：新的快取層、server-side UI state、全文預載、背景同步、schema migration、改附件儲存根目錄。
- 驗收：大量長文 fixture 下 list preview 不含全文 tail、detail 仍回全文、tail token 搜尋命中不退化；targeted Go / static regression、frontend build 與 Loop gate 已通過。Pi delivery 已跑 `scripts/go_primary_pi_live_ops.ps1 -Mode Cutover`；live API smoke 驗 preview/detail/search contract，Playwright live UI smoke 驗 Home card tail hidden、Editor/ReadingView tail visible、console error=0，temp validation notes 已清理。

#### STARRED-TAG-FILTERS-CANDIDATE-01 Header starred tag shortcuts

目標：讓「設定 > 組織 > 標籤管理」控制 Home 上方分類列右側顯示哪些 tag shortcuts；使用者以星號釘選常用標籤，未釘選任何標籤時 header 不顯示 tag chips，只顯示提示文字。

- [x] **01A Frontend state contract**（2026-06-18 完成）：新增純前端 `localStorage` 狀態 key `prism.starredTags.v1`，只保存 starred tag IDs。刪除 / merge tag 後若 ID 不存在，讀取時自動忽略；未新增 DB 欄位、未改 tags API、未做跨裝置同步。
- [x] **01B Settings tag star control**（2026-06-18 完成）：`Settings > Organization > Tag management` 的每個 tag chip 已加星號按鈕；點星號只切換 starred 狀態並 stop propagation，不影響既有 tag merge selection、rename、delete。星號亮表示會出現在 header tag shortcuts；已補四語 aria-label / tooltip。
- [x] **01C Header tag strip integration**（2026-06-18 完成）：`FilterStrip` 分類按鈕右側只顯示 starred tags，維持現有 tag click filter 行為與 active state；若 starred tags 為空，不渲染 tag chips，只顯示低存在感提示文字。分類 / 封存 / 全部按鈕與現有水平捲動行為不改。
- [x] **01D Regression and smoke**（2026-06-18 完成）：static regression 鎖住 localStorage key、DataManager 星號 stop propagation、FilterStrip 只讀 starred tags 與 empty hint；frontend build、browser smoke 與 Loop gate 已通過。Pi live smoke 已驗星號開關、header 顯示/隱藏、tag filter 點擊、reload persistence、無 starred tags 時只顯示提示文字且 console error=0。
- 不做：server-side preference、DB schema/API、tag 排序拖曳、tag 群組、全域 pin sync、側邊欄 tag 列表改版。
- 驗收：Settings 星號狀態 reload 後保留；header 只顯示 starred tags；全部取消 starred 後 header 不再顯示 tag chips、只顯示提示文字；既有 tag merge / rename / delete 操作不被星號按鈕誤觸。

#### BULK-MARKDOWN-TXT-IMPORT-CANDIDATE-01 Batch Markdown/txt import

目標：允許使用者一次選多個 `.md` / `.txt` 檔建立 notes，回報逐檔結果摘要。

- [x] **01A Import path lock**（2026-06-18 完成）：current runtime 仍是 `POST /api/notes/import/md` 單檔 `.md` import；frontend 新增 `api.importMarkdown(file)` wrapper，但不新增 batch endpoint。`.md` 逐檔呼叫既有 Markdown import；`.txt` 由 frontend `file.text()` 後走既有 `POST /api/notes`，title 使用檔名 stem、content 使用純文字內容。
- [x] **01B Settings import UI**（2026-06-18 完成）：`Settings > Backup & Restore` 匯入區已新增 `.md/.txt` 多檔 selector、檔案清單、清空、單檔移除、匯入按鈕與 created / skipped / failed 結果摘要。待匯入清單可多次選不同資料夾檔案並以 name / size / lastModified 去重；匯入逐檔執行，匯入後清空待匯入清單但保留結果摘要。單檔失敗不回滾已成功 note，並在該檔結果列顯示 backend error。
- [x] **01C Contract/docs cleanup**（2026-06-18 完成）：已同步 `docs/CONTRACTS.md` / `docs/API_REFERENCE.md`，明確標記這只是 Settings 前端逐檔 wrapper；沒有 server-side batch import API，`.txt` 不走 `/api/notes/import/md`。
- [x] **01D Regression and smoke**（2026-06-18 完成）：static regression 鎖住 `api.importMarkdown` 單檔 endpoint、Settings `.md/.txt` 多檔 UI、跨批選檔累加、同檔去重、單檔移除、清空、匯入後清空待匯入清單、`.txt` create-note path、逐檔 try/catch 與 summary data attributes；frontend build、本機 embedded Go runtime + Playwright smoke 已驗 Markdown H1 title、frontmatter category/tags、`.txt` filename title、跨批選檔累加、重複去重、混合 2 created / 1 failed summary、API detail content 與 temp note cleanup。Pi delivery 已跑 `scripts/go_primary_pi_live_ops.ps1 -Mode Cutover`；live Playwright smoke 驗同一 flow，temp notes/tags 已清理，service/header/migration/journal final check clean。
- 不做：目錄遞迴 watcher、自動分類/AI 摘要、覆蓋既有 notes、同步機制、background daemon、批量 DB transaction。
- 驗收：跨批選檔累加、重複去重、匯入後清空待匯入清單、Markdown H1 title、frontmatter category/tags、`.txt` filename title、混合成功/失敗摘要；frontend build；若只改 frontend，不需要 Go schema/migration 測試。Pi delivery 已依 `DEPLOY-PI.md` 完成 live verification。

#### IMAGE-VIEWER-CANDIDATE-01 Unified image lightbox

目標：閱讀頁、編輯預覽與可行的卡片封面使用同一個 app 內圖片 lightbox。

- [x] **01A Shared lightbox component**（2026-06-18 完成）：新增純前端 `ImageLightbox`，支援 close、prev/next、copy path、open original；圖片清單由呼叫端傳入，不碰 upload/storage/cleanup API。
- [x] **01B Reading view integration**（2026-06-18 完成）：`ReadingView` 從 cover image + rendered markdown images 收集圖片；點擊圖片開 lightbox，鍵盤 Esc/左右鍵可操作。
- [x] **01C Editor preview/card integration**（2026-06-18 完成）：`EditablePreview` standalone image、`NoteEditor` 雙欄 gallery 與 `NoteCard` cover image 已接同一 `ImageLightbox`。卡片 cover 只用明確 icon/button 開啟，並 stop propagation；不改整張卡片開啟 note 的習慣。
- 不做：改圖片儲存模式、改 upload/delete/cleanup API、重寫 markdown renderer、建立 gallery DB、OCR/AI 圖片描述。
- 驗收：01A/01B local gate 已覆蓋 ReadingView markdown 多圖 prev/next、cover-only note、無圖 note、Esc close、左右鍵、copy path/open original contract；01C static regression 已鎖住 Editor preview / editor gallery / NoteCard cover 都走 shared lightbox，且卡片 cover 入口不 hijack card click。Local Playwright smoke 已驗 Home card cover `1/1`、ReadingView cover/markdown `1/3 -> 2/3`、Editor preview `1/2 -> 2/2`、Esc 後底層 panel/editor 仍開啟、console error=0；Loop gate 已通過。Pi delivery 已跑 `scripts/go_primary_pi_live_ops.ps1 -Mode Cutover`，live Playwright smoke 驗同一 flow，temp validation note/uploads 已清理，service/header/migration/journal final check clean。

#### IMAGE-VIEWER-ZOOM-CANDIDATE-01 Lightbox pure-view zoom controls

來源：使用者 2026-06-19 follow-up。

目標：在既有 shared `ImageLightbox` 內補純觀看縮放與更直覺的關閉操作；只改善 lightbox viewing，不改圖片儲存、上傳、刪除或附件 contract。

- [x] **01A Zoom controls**（2026-06-19 完成）
  - 施工範圍：在 lightbox toolbar 加入放大 / 縮小控制，限制合理 min/max scale，切換圖片或重新打開時回到可預期的 fit/100% 狀態。
  - 驗收：ReadingView cover/markdown image、EditablePreview standalone image、NoteEditor gallery、NoteCard cover lightbox 都能使用同一組 zoom controls。

- [x] **01B Backdrop click close**（2026-06-19 完成）
  - 施工範圍：點擊圖片外的 dimmed background 關閉 lightbox；點擊圖片本身、toolbar、prev/next、copy/open original 不關閉。
  - 驗收：背景 click 只關 lightbox，不連帶關閉底層 ReadingView / Editor modal；Esc close 既有行為不退化。

- [x] **01C Keyboard zoom shortcuts**（2026-06-19 完成）
  - 施工範圍：lightbox 開啟時，`ArrowUp` 放大、`ArrowDown` 縮小；既有 `ArrowLeft` / `ArrowRight` 圖片切換仍保留。
  - 驗收：快捷鍵只在 lightbox active 時攔截，不影響底層閱讀/編輯頁；到 min/max scale 時不產生 layout jump 或 console error。

- [x] **01D Regression and smoke**（2026-06-19 完成）
  - 最小驗證：static/frontend regression、`cd frontend && npm run build`、local Playwright smoke 覆蓋 background close、zoom buttons、上下鍵縮放、左右鍵切圖與底層 modal 不被誤關。
  - Pi delivery：只有在使用者要求上 Pi 或 release gate 需要時，才依 `DEPLOY-PI.md` 另跑 live delivery。

- 不做：crop / rotate / image edit、persisted per-image zoom、gallery DB、upload/delete/cleanup API、server-side preference、AI/OCR 圖片分析。
- 驗收：local static regression 鎖住 min/max zoom、reset-on-image-change、ArrowUp/ArrowDown、backdrop close 與 prev/next/image/toolbar stop propagation；frontend build 與 local rendered smoke 覆蓋 zoom buttons、keyboard zoom、left/right image switch、background close、Esc close，以及 ReadingView / Editor 底層 modal 不被連帶關閉。Loop gate 已通過。本輪未做 Pi delivery，需 release/deploy gate 另行執行。

#### READING-WORKSPACE-CANDIDATE-01 Reading list workspace

目標：讓使用者把多張卡片加入暫存閱讀清單，閱讀時快速切換，不必關閉上一張 note。

- [x] **01A State contract**（2026-06-18 完成）：新增純前端 `useReadingWorkspace` hook，key 為 `prism.readingWorkspace.v1`；保存 note ids、active id、layout preference（tabs/sidebar）與每張 note 的 scroll position。狀態限 `localStorage`，不新增 DB schema、不改 note API。
- [x] **01B Reading panel switcher**（2026-06-18 完成）：`ReadingView` 右側清單顯示暫存閱讀清單，支援加入目前 note、切換、移除單張、清空全部；reload 後會按 note id 重新抓 detail/title，載入失敗時保留清單並顯示可移除狀態。
- [x] **01C Home/card entry points**（2026-06-18 完成）：`NoteCard` action menu 新增「加入閱讀清單」，只寫入 frontend workspace state；使用者直接開單張閱讀時仍維持既有 card open mode，不強迫建立 workspace。
- [x] **01D Scroll restore**（2026-06-18 完成）：閱讀容器 scrollTop 會保存到 workspace state；切換 note 前保存目前位置，切回同 note 後 restore。若 note 內容重新載入失敗，清單保留並可單張移除。
- [x] **01E Affordance polish + Pi delivery**（2026-06-18 完成）：`NoteEditor` toolbar 將既有「提取圖片提示詞」可見按鈕封存並改為「加入閱讀清單」；Header 顯示閱讀清單入口並可開啟 active/first note workspace；Appearance sidebar width slider 可調 150-320px；左上角 Prism 下方顯示 `V2.5`，HTML title 顯示 `Prism V2.5`。未刪除 dormant prompt-extraction API/hook、未改 DB/API、未新增 server persistence。
- 不做：native 多視窗、雙欄比對、diff engine、server persistence、跨裝置同步、改 `GET /api/notes` contract。
- 驗收：`pytest tests/test_reading_workspace.py tests/test_frontend_i18n_settings.py tests/test_note_variant_lineage.py -q` 27 passed；`pytest tests/test_go_primary_t032_t035_server_system.py tests/test_reading_workspace.py tests/test_frontend_i18n_settings.py -q` 30 passed；`pytest tests/test_go_primary_t032_t035_server_system.py -q` 4 passed；`cd go-shadow && go test ./...` passed；`npm run build` passed（僅既有 browserslist/chunk-size warning）；`.loop/verify-gate.ps1` 第 2 輪通過（`git diff --check`、AGENTS/CLAUDE mirror、`pytest tests/ -v` 349 passed、`go test ./...` passed）。Pi delivery 已跑 `scripts/go_primary_pi_live_ops.ps1 -Mode Cutover`；live `https://prism.local` 驗 `prism-go-primary.service` active、legacy `prism.service` inactive、`X-Prism-Go-Primary: hit`、version `2.5`、migration v16 clean。Browser plugin `iab` 不可用，rendered 驗證改用 Playwright fallback；live smoke 驗 title `Prism V2.5`、sidebar `V2.5`、Editor toolbar 加入閱讀清單、Header 開啟 `READING LIST (1)`、舊「提取圖片提示詞」入口不存在、console/page/request error=0。

### Future Branch Candidates

#### CATEGORY-IDENTITY-CANDIDATE-01 Default category identity split

目標：把「五個系統預設分類的身份」與「使用者可見/可改的分類名稱」拆開，停止依賴 legacy seed name（例如 `提示詞 | Prompt`）來判斷是否要跟語系切換。

目前 live 行為邊界：

- `is_default` 只代表刪除分類時的搬移目標，不代表五個系統預設分類身份。
- 目前前端以 `Categories.name` 是否等於 `提示詞 | Prompt` / `筆記 | Note` / `教學 | Tutorial` / `資料 | Data` / `靈感 | Inspiration` 來判斷是否顯示語系化名稱。
- 使用者若把分類實際改成 `提示詞` / `Prompt` 等單一語系文字，前端會把它視為自訂名稱，切換語系不再翻譯；這是 legacy name-based 判斷造成的混淆。

- [x] **01A Schema contract / migration plan**（2026-06-19 完成）：新增 nullable `Categories.system_key`（允許值 `prompt` / `note` / `tutorial` / `data` / `inspiration` / `NULL`）與 `Categories.name_override`；fresh schema 與 v17 migration 建立 `idx_categories_system_key` partial unique index。migration 只回填仍保留完整 legacy seed name 的五個系統分類，避免把已自訂名稱的分類誤判回系統分類。
- [x] **01B Go API and import/export contract**（2026-06-19 完成）：`GET /api/categories` 回傳 `system_key` / `name_override`；`PUT /api/categories/<id>` 拒絕 client 改 `system_key`，系統分類改名寫入 `name_override`，傳 `null` 可清除 override；一般自訂分類仍更新 `name`。JSON export/import 會保留 categories identity，note category 匯入可匹配 `name` 或 `name_override`。
- [x] **01C Frontend display/edit semantics**（2026-06-19 完成）：分類顯示改用 `system_key`；`system_key` 有值且未自訂改名時依語系顯示，`name_override` 有值時固定顯示使用者文字且不跟語系切換。Settings 編輯框顯示目前可見名稱；儲存未變更的預設顯示名不會意外寫成自訂名稱，輸入該語系預設名可清除既有 override。
- [x] **01D Regression and Pi delivery gate**（2026-06-19 完成）：補 Go migration/fresh DB/API regression、frontend category display/edit regression、import/export roundtrip regression；本機驗 `pytest tests/ -q` 352 passed、targeted pytest 24 passed、`cd go-shadow && go test ./...` passed、`npm run build` passed（僅既有 browserslist/chunk-size warning）。Pi delivery 依 `DEPLOY-PI.md` cutover 到 `PI5Mask24`；live 驗 `https://prism.local` service active、migration v17 clean、四語分類切換、改名後固定顯示與 console/page/request error=0。

不做：把 `is_default` 重新定義成系統分類身份、用前端多認 `提示詞` / `Prompt` 等別名當短期 workaround、重排分類 UI、增加多語自訂名稱表、server-side user profile / cross-device preference。

驗收：legacy seed-name mapping 已不是唯一身份來源；五個預設分類在未改名時可依 zh-TW / en / ja / ko 顯示，改名後固定為使用者輸入文字；DB migration 已在 Pi live data 升到 v17 並保留使用者自訂分類語義。



---

## Archive Index

- `docs/development-history/go-primary-runtime-completion-20260617.md`：T001-T053 Go primary migration 完成敘事、artifact 與完整任務表。
- `docs/development-history/desktop-backup-i18n-handoff-20260617.md`：2026-06-14 local desktop / backup / dashboard handoff、2026-06-17 Core UX 與 i18n 詳細完成記錄。
- `docs/development-history/desktop-portable-release-handoff-20260618.md`：Desktop Shell Phase 0-6、portable baseline、manual acceptance、README split 與 release packaging 邊界。
- `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`：Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。
- `docs/development-history/todo-changelog.md`：長版版本歷程。
- `docs/development-history/todo-completed-phases.md`：更早期完成 phase 與歷史工作清單。
