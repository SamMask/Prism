# Prism Active TODO

本檔只保留目前可施工的 active roadmap、候選 backlog 與下一步入口。完成紀錄、舊 phase 與長版 changelog 全部移到 `docs/development-history/`。

閱讀方式：

- `[x]` = 已完成，並且本檔保留必要驗證證據或歸檔入口。
- `[ ]` = 尚未施工、等待 promote、或 blocked/deferred；看括號內 `Todo` / `Blocked` 判斷能不能直接做。
- 狀態欄位固定使用：`Todo` / `Doing` / `Blocked` / `Review` / `Done`。未 promote 的候選項維持 `Todo`；缺少明確需求、決策 gate 或安全前提的項目標 `Blocked`；只有正在施工的單一 active item 才標 `Doing`。

---

## Current Truth（2026-07-05）

- Go primary 是唯一 current runtime owner；Python Flask backend source 已於 T053 移除。完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- Prism V2.5 已封版到 commit `42ce747bc273182b045455de49b8be06fd6c051a`；GitHub Release `V2.5` 與 portable zip asset 已對齊該 commit。
- Windows portable current path：`Prism.exe` GUI app + WebView2 + same-process Go runtime；預設資料在 exe 同層 `PrismData\`。`--data-dir` / `PRISM_GO_DATA_DIR` 只作進階/debug override。
- V2.5 release notes / README 已說明 unsigned portable、Windows SmartScreen、GitHub download Mark-of-the-Web (`Zone.Identifier`)、SHA256 驗證與 `Unblock-File` 流程。沒有購買或加入 code signing。
- Pi delivery 與 GitHub release package 是兩條流程。Pi live deploy 必須依 `DEPLOY-PI.md` 使用 Go primary live ops；GitHub Actions 只做 validation，不自動上傳 release asset。
- Prism 仍沒有內建 auth/token layer；safe boundary 是 localhost、trusted LAN、VPN、SSH tunnel，或外部 auth 保護的 reverse proxy。不得把 API 寫成可直接 public internet 暴露。
- V2.5 近期完成項已歸檔到 `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`，包含 Reading workspace、variant tracking、note-list preview、image lightbox/zoom、batch import、starred tags、category identity、deep scan 01A-01G、project review hygiene 01A-01E 與 release/package evidence。
- `build/` 只應保留最新 release 產物；不得把 DB、attachments、notes、uploads 等真資料當 build artifact 清理。
- `docs/GOVERNANCE.md` 是完成宣稱、狀態層級、驗證證據、委派與 UI/UX governance 的 current entry；新版治理素材已保留到 `docs/development-history/governance-source-20260705/`，正式文檔不依賴暫存素材目錄。

Current truth 仍以本檔、`HANDOFF.md`、`docs/ARCHITECTURE.md`, `docs/SCHEMA.md`, `docs/API_REFERENCE.md` 與實際 source/runtime 為準。不得因歷史報告曾討論過，就直接擴 scope 成 AI、semantic search、GraphRAG、auto-writing、schema/API/runtime 或 Pi deploy 變更。

---

## Progress At A Glance

- [x] `MARKDOWN-SYNTAX-CANDIDATE-01`（狀態：`Done`）：已完成低風險 Markdown renderer / preview slice，包含 GFM table/task list/code copy/heading anchor/ReadingView outline，以及 GitHub alert、footnote、`==highlight==`、MarkForge box/details prose extensions。
- [x] `KWF-01 Command Palette server-side search`（狀態：`Done`）：Command Palette 已能用既有 `/api/notes?q=...` 做全庫純關鍵字搜尋，且已完成 Pi live deploy evidence。
- [x] `KWF-02 Saved Search / Search Workspace`（狀態：`Done`）：Home 已能把目前 query/filter/sort view 保存成瀏覽器本機 Search Workspace，localStorage key `prism.savedSearchWorkspaces.v1`，不改 DB schema。
- [x] `NOTE-DELETE-MEDIA-UX-CANDIDATE-01`（狀態：`Done`）：已補刪卡片 / 批次刪除確認框與 Settings「清理未使用圖片」copy；runtime 已有 reference-counted cleanup，本輪未改 Go delete/media cleanup semantics。
- [ ] `KWF-03` 到 `KWF-07`（狀態：`Todo`）：full data snapshot、agent-safe write guards、import dry-run、source URL panel、knowledge quality metadata decision gate，依序等待 promote。
- [ ] Heavy renderer / installer / updater / AI 類項目（狀態：`Blocked`）：只有使用者明確重新開啟需求或 decision gate，才可施工。

目前沒有 `Doing` item。下一輪若要接續產品工作，優先做 `KWF-03 Full data snapshot export`；不要把 DB-only backup 說成完整資料快照。

---

## Remaining Work Summary

人類版：Prism 目前主線已經穩定在 Go primary、V2.5 portable、Pi live deploy 與基本 Markdown/Command Palette / Saved Search 工作流。常用搜尋視圖現在可以保存在本機瀏覽器，之後一鍵回到同一組 query/filter/sort view。刪除 note 時的提示文字也已補上：Go primary 會嘗試清理已偵測且未被其他 note 引用的 upload 圖片與縮圖，但 shared/未偵測/孤兒檔仍應透過圖片管理或 Settings「清理未使用圖片」確認。下一個最適合做的是 `KWF-03 Full data snapshot export`，把 DB、uploads、attachments、notes、config 與 manifest 打成明確的完整資料快照。

LLM 接續版：先讀 `AGENTS.md`、`HANDOFF.md`、`docs/GOVERNANCE.md`、本檔、`docs/ARCHITECTURE.md`、`docs/SCHEMA.md`、`docs/API_REFERENCE.md`；若接 `KWF-03`，先明確 full data snapshot 和 DB-only backup 的邊界，優先做 script 或受控 local/desktop action 的 dry-run / fixture data dir smoke，不要碰 live Pi、不新增 auth、不改 public exposure。任何 promoted item 完成後至少跑 `git diff --check`，有 frontend 行為則加 targeted tests/build，並把驗證證據寫回本檔或 `HANDOFF.md`。

---

## Completed Items Kept In This Active File

### [x] MARKDOWN-SYNTAX-CANDIDATE-01 Port MarkForge-MD supported Markdown syntax into Prism

狀態：`Done`

來源：2026-07-05 使用者要求把 `D:\AI\MarkForge-MD` 支援的 md 語法支援到 Prism，且 Markdown 語法支援列優先。

實際對照：MarkForge-MD current renderer 已支援 CommonMark / GFM-like table、task list、fenced code、syntax highlighting、相對/本機圖片 preview、GitHub alert、footnote、code block copy、outline、Mermaid、KaTeX、白名單 HTML、`==highlight==`、MarkForge box/details 與 ABC 樂譜 fence。Prism current renderer 使用 `marked` (`gfm=true`, `breaks=true`) + `DOMPurify`，共用入口是 `frontend/src/utils/markdown.ts`；本輪只接低風險 preview fidelity，不搬 renderer stack。

目標：把高頻、可維護、低風險的 MarkForge-compatible Markdown 顯示能力帶進 Prism 的 ReadingView / editor preview；先做前端 preview fidelity，不改 note schema、import/export contract、search contract、DB migration 或 Go runtime storage semantics。

完成範圍：

- [x] `MDS-01 Renderer contract audit`（狀態：`Done`）：`tests/test_markdown_sanitization.py` 已鎖住 ReadingView / EditablePreview 只能走共用 `renderSafeMarkdown()` + DOMPurify sanitizer path，並保留 unsafe tag / unsafe protocol boundary regression。
- [x] `MDS-02 Low-risk GFM preview UX`（狀態：`Done`）：`marked` 產出的 table、task list、code fence、heading 以 render 後 DOM helper 補 responsive table wrapper、task list 視覺、code-copy button、heading id/anchor；ReadingView 右側補 TOC/outline。沒有改 Markdown source，也沒有新增 WYSIWYG。
- [x] `MDS-03 MarkForge prose extensions`（狀態：`Done`）：本地 parser helper 支援 GitHub alert、footnote、`==highlight==`、`:::markforge-box info|success|warning`、`:::markforge-details title`，仍走 DOMPurify allowlist；未允許任意 CSS、`style`、script、iframe/object/embed、遠端 renderer 或 plugin host。
- [x] `MDS-04 Code syntax highlighting`（狀態：`Done`）：本次評估後不導入 `highlight.js` 或新 dependency；只補 code block copy 與可讀樣式。若未來需要語法高亮，另開 bundle/security review。

未施工 / blocked：

- [ ] `MDS-05 Mermaid decision gate`（狀態：`Blocked`）：本次未導入。若未來要支援圖表渲染，必須離線渲染、可設定開關、錯誤只影響該 block、render timeout、有 sanitizer / protocol boundary regression，並明確處理 export/preview fidelity 差異。
- [ ] `MDS-06 KaTeX math / ABC score optional renderer freeze`（狀態：`Blocked`）：2026-07-05 使用者決策：數學公式與樂譜顯示暫時凍結為備選，不列入下一個 Markdown renderer 入口。只有使用者明確需要把公式或樂譜當知識卡片顯示時，才另開離線 renderer / bundle / safety gate。

驗證證據：

- `pytest tests/test_markdown_sanitization.py tests/test_image_viewer_lightbox.py::test_reading_view_collects_cover_and_markdown_images -v`：5 passed。
- `cd frontend && npm run build`：passed；僅有既有 Browserslist outdated 與 Vite chunk-size warning。
- `pytest tests/ -v`：已跑完整套件一次，該次結果為 344 passed / 20 failed；其中 ReadingView handler name regression 已在本 slice 修正並以 targeted test 驗過，其餘失敗集中在 TODO/HANDOFF 瘦身後仍期待舊 `[x]` 歷史條目的既有 docs regression。
- 未新增 dependency，未引入 AI/ML、CDN、背景服務、遠端 renderer、schema/API change 或 editor rewrite。
- 未跑 Playwright screenshot smoke；本 slice 以 targeted regression + TypeScript/Vite build 作為驗收證據。

不做：

- 不追「所有 Markdown dialect」；只做 MarkForge 已證明且 Prism 高頻可用的子集。
- 不把 MarkForge 的 Tauri local-file asset scope、desktop file association、installer behavior 搬進 Prism。
- 不把 Markdown syntax gate 順手擴成 import/export 重做、搜尋重做、schema 欄位新增或 Pi deploy。

### [x] KWF-01 Command Palette server-side search

狀態：`Done`

- [x] `KWF-01 Command Palette server-side search`（狀態：`Done`）：Command Palette 輸入 `? xxx` 或至少 3 個字元時，debounced 呼叫既有 `api.getNotes({ search: xxx, per_page: N })` 顯示全庫結果；保留 navigation / recent / new note / theme actions。這是最小搜尋工作流改良，不改後端搜尋引擎。
  - 完成：新增 `results` 分組、loading / empty / error / count 狀態、四語 i18n、server result 點開前依 `content_truncated` 補抓完整 note detail。
  - 邊界：沒有改 Go API、FTS/search contract、DB schema、Pi deploy、auth 或 public internet exposure policy。
  - 驗證：`pytest tests/test_command_palette_server_search.py tests/test_phase22_command_palette_entrypoint_reliability.py tests/test_frontend_i18n_settings.py::test_active_ui_final_i18n_namespaces_are_translated_for_four_locales tests/test_frontend_i18n_settings.py::test_active_ui_final_components_use_i18n_for_extracted_strings -v`：11 passed；`cd frontend && npm run build`：passed，僅既有 Browserslist / chunk-size warning；`git diff --check`：passed，僅 Windows CRLF warning；`pytest tests/ -v`：349 passed / 19 failed，失敗仍集中在 TODO 瘦身後舊測試期待歷史 `[x]` 條目的既有 docs regression，KWF-01 tests 皆通過。
  - Pi live deploy：2026-07-05 已用 `powershell -ExecutionPolicy Bypass -File scripts/go_primary_pi_live_ops.ps1 -Mode Cutover -DeploySnapshotKeep 5` 推到 `PI5Mask24`。Artifact sha256 `b1216cc1aefcc893db9b867e97960de3bb3e4689a739ee8227b5fd4738dcb871`；pre-cutover snapshot `/home/mask070924/prism/backups/go-primary-t042-20260705_012430`；`prism-go-primary.service` active、legacy `prism.service` inactive、Caddy active；`/api/system/migration-status` current/latest v17 且 pending empty；`/api/notes?q=prompt&per_page=1&include_archived=true` success；served JS contains `command-palette-server-search-status`；local evidence at `build/go-primary-live/pi/evidence.json`。

---

## Open TODO Items

### [ ] KNOWLEDGE-WORKFLOW-CANDIDATE-01 Local-first knowledge workspace improvements after Markdown candidate

狀態：`Todo`

來源：2026-07-05 使用者貼上的 ChatGPT 優先序建議；依 Prism current docs/source 實際狀態評估後吸收到 TODO。Markdown syntax support 仍列優先，本 candidate 排在 Markdown 之後。

實際對照：

- `GET /api/notes?q=...` 已支援 title/content FTS5、remarks、tags、attachment metadata 與 bounded text attachment body scan，且仍是純關鍵字搜尋；API 也已有 category、tags、archived、pinned、sort 等條件。
- server backup/download 與 rotate 是 DB-only；`DEPLOY-PI.md` 與 API docs 已明確指出 DB backup 不包含 `static/uploads/` / `docs/attachments/`，不同於 deploy data snapshot。
- Prism 無內建 API token / Bearer token / 使用者認證；文件已要求 localhost、trusted LAN、VPN、SSH tunnel 或外部 auth reverse proxy。
- Settings 批次 Markdown/TXT 匯入仍是前端逐檔 wrapper，沒有 server-side batch import API，也沒有 dry-run / collision preview。

採納項目與施工順序：

- [x] `KWF-02 Saved Search / Search Workspace`（狀態：`Done`）：Home 已新增 Search Workspace bar，可保存 / 套用 / 刪除目前 query、category、tag、archived、sort view。保存資料只寫入瀏覽器 localStorage key `prism.savedSearchWorkspaces.v1`，沒有新增 DB migration、Go API、semantic search、auth 或 Pi deploy；若未來要跨裝置，再另開 schema gate。
- [ ] `KWF-03 Full data snapshot export`（狀態：`Todo`）：新增 script 或受控 local endpoint/desktop action，打包 DB、WAL/SHM safety handling、`static/uploads/`、`docs/attachments/`、`docs/notes/`、config 與必要 manifest。必須明確命名為 full data snapshot，避免和 DB-only backup 混淆；Pi/live 版本需保留 rollback 與 snapshot retention 邊界。
- [ ] `KWF-04 Agent-safe write guards`（狀態：`Todo`）：為 destructive/bulk/API write 增加小型防手殘機制候選，例如 `dry_run=true` preview、batch delete preview、`expected_updated_at` optimistic guard、`client_request_id` 或 `source=agent_name` 記錄。這不是 auth，不得宣稱能安全 public exposure。
- [ ] `KWF-05 Import dry-run / collision preview`（狀態：`Todo`）：先做 import preview，回報會建立、跳過、疑似重複與錯誤檔數；不做 watcher、不做 sync daemon、不把單檔 endpoint 偷升成未驗證大批次寫入。
- [ ] `KWF-06 Source URL panel`（狀態：`Todo`）：利用既有 `Source_Urls` / note `urls`，做來源連結面板：domain 顯示、duplicate URL detection、手動 title、失效檢查候選。避免直接做 full web clipper。
- [ ] `KWF-07 Knowledge quality metadata decision gate`（狀態：`Todo`）：`status` / `review_state` / `last_verified_at` 需要 schema v18+，排在搜尋工作流、snapshot 與 import preview 後面；啟動前必須先更新 `docs/SCHEMA.md` 與 migration/test contract。

不採納 / deferred：

- [ ] 內建登入、多使用者、OAuth、RBAC、cloud sync、semantic search、embeddings、GraphRAG、directory watcher、background sync daemon、大型備份平台、一次性 editor rewrite、一次性 Go runtime 大拆分（狀態：`Blocked`）。
- [ ] Source URL 自動抓 title / link health 若需要外網或批次請求，必須另開 privacy / timeout / user-triggered boundary，不得在讀取 note 時背景追蹤遠端 URL（狀態：`Blocked`）。

驗收候選：

- KWF-02 已以 `pytest tests/test_kwf02_saved_search_workspace.py tests/test_note_delete_media_ux_copy.py -v`、相關 i18n/Home targeted tests、`cd frontend && npm run build` 與 Browser smoke 驗證 saved view persistence / filter restore 基本路徑；本輪未新增 backend/API/DB contract。Browser smoke 在 `http://127.0.0.1:5173/` 驗證 Home 可載入、Search Workspace bar 可見、保存後 chip 出現、刪除後回到 empty state；Go backend 5004 未啟動，因此 console 有既有 API fetch errors。
- KWF-03 若只做 script，需有 dry-run / fixture data dir smoke；若做 API/desktop action，需 Go tests + artifact smoke，並清楚證明包含 DB、uploads、attachments、config，且不覆蓋 live data。
- KWF-04/KWF-05 涉及 API contract 時必須補 `docs/API_REFERENCE.md`、Go tests、frontend regression 與 failure/no-partial-write evidence。

### [x] NOTE-DELETE-MEDIA-UX-CANDIDATE-01 Deleting notes and unused images copy

狀態：`Done`

來源：2026-06-19 使用者回報，下載版新增有圖片的卡片後，單張刪除或批次刪除 note 時，體感上關聯 upload 圖片檔不一定會一起刪；使用者也指出「不要無條件一起刪」有安全上的好處，目前可用「清理未使用的圖片」事後處理。

目標：先把這個行為當成 UX / documentation candidate，不直接改 runtime deletion semantics。

已決定 / current truth：

- Go primary / API current behavior：刪除 note 時會嘗試清理從 note content / cover_image 偵測到、且未被其他 note 引用的 `/static/uploads/` 圖片；同時處理 original / `_thumb.webp` companion。
- 這不是「無條件 cascade 刪圖」。shared references 會保留；未被 delete handler 偵測到的 leftover/orphan 檔案仍由 Settings「清理未使用圖片」或圖片管理入口處理。
- 此 candidate 的決定是補 UX copy，避免使用者把「刪卡片」誤解成「所有相關圖片檔一定被刪乾淨」，同時不改現有 Go delete/media cleanup runtime。

完成範圍：

- [x] 可施工方向 A（狀態：`Done`）：在刪除 note/批次刪除確認框加一句短 copy，說明已偵測且無其他引用的圖片會被清理，但 shared/未偵測/orphan 圖片可到 Settings 清理未使用圖片檢查。
- [x] 可施工方向 B（狀態：`Done`）：在 Settings 清理未使用圖片區塊補說明，標明刪除 notes 後留下的未引用圖片會在這裡掃出。
- [ ] 可施工方向 C（狀態：`Blocked`）：若未來真的要新增更強的「跟著刪圖」行為，只能另開 opt-in decision gate，例如「同時刪除只被這些卡片使用的圖片」，且預設不勾。

驗證證據：`tests/test_note_delete_media_ux_copy.py` 鎖定 confirmation / Settings copy 與 docs closure；`cd frontend && npm run build` passed（僅既有 Browserslist / chunk-size warning）。本輪只補 confirmation / Settings copy，未改 Go delete/media cleanup runtime。

不做：

- 預設無條件 cascade 刪 upload 檔。
- 繞過引用掃描。
- 刪仍被其他 note / attachment / cover 引用的圖片。
- 在 V2.5 封版後只為此重包 release。

驗收候選：copy 或 opt-in 行為需有 frontend regression；若涉及刪檔 runtime，必須補 Go/API tests 證明 shared references、cover image、Markdown/HTML image、thumbnail companion 與 batch delete order 都不誤刪。

---

## Deferred Candidates

- [ ] `DEEP-SCAN-RISK-CANDIDATE-01` 01H 仍是低優先維護 triage（狀態：`Blocked`；需明確 promote 才可施工）。
- [ ] Desktop installer/updater/WebView2 bootstrap/shortcut automation（狀態：`Blocked`；需使用者明確需要 installer/updater 類能力）。
- [ ] Hidden/deferred i18n UI（`PortConfigSection`、`UpdateSection`、`TagInput`）（狀態：`Blocked`；只有日後恢復 render，才於該 gate 同步補四語 key）。
- [ ] Mermaid 圖表渲染（狀態：`Blocked`；只有 `MARKDOWN-SYNTAX-CANDIDATE-01` 的 `MDS-05` 被明確 promote 後才可施工；不得順手導入 heavy renderer）。
- [ ] KaTeX 數學公式 / ABC 樂譜渲染（狀態：`Blocked`；目前凍結為備選，只有使用者明確重新開啟需求時才可施工）。
- [ ] AI / semantic search / embeddings / GraphRAG / auto-writing（狀態：`Blocked`；仍不在 active roadmap）。

---

## Release / GitHub / Pi Maintenance

- [ ] Release / GitHub maintenance（狀態：`Blocked`）：目前沒有未交付的 release construction item。若要重新發佈或更新 V2.5 以後的版本，先依 `docs/RELEASE_CHECKLIST.md` 重跑 fresh evidence，再 commit / tag / package；push 後必須確認 GitHub Actions workflow 綠燈。
- [ ] Pi delivery（狀態：`Blocked`）：Pi delivery 不是 release notes / GitHub asset 的自動副作用。任何 Pi 上線都需另開 gate：先讀 `DEPLOY-PI.md`，使用 Go primary live ops 流程部署到 `PI5Mask24`，並驗證 service status、migration status、changed API endpoint 與對應前端行為。

---

## Windows Desktop vs Pi Deployment 差異表

| 面向 | Windows desktop | Raspberry Pi |
|---|---|---|
| 入口 | `Prism.exe` GUI app；正式 build 不出現終端機 | systemd service 啟動 Go primary binary |
| UI | WebView2 內嵌本機 Web UI + tray | 使用瀏覽器連 `https://prism.local` / Caddy |
| Runtime | 同一行程內 desktop shell + Go server goroutine | headless Go primary service |
| 網路 | 綁 `127.0.0.1:<port>`，只給本機 WebView2 | Caddy reverse proxy 到 local service port |
| 資料 | 預設 exe 同層 `PrismData\`；`--data-dir` / env 僅作進階 override | Pi 上既有 production data dir |
| Log | 檔案 log + debug console build | journald / service log / Go runtime log |
| 打包 | portable zip / folder；installer deferred | artifact deploy + systemd + rollback / soak |
| 相依 | WebView2 Runtime、Win32 shell APIs | Linux/arm64、systemd、Caddy |
| 不共用項 | tray、window、mutex、`-H=windowsgui` | Caddy live routing、systemd enable/restart |

---

## Archive Index

- `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`：2026-06-19 TODO/HANDOFF 瘦身時移出的 V2.5 收尾、完成 gate、release/package evidence 與 deferred notes。
- `docs/development-history/go-primary-runtime-completion-20260617.md`：T001-T053 Go primary migration 完成敘事、artifact 與完整任務表。
- `docs/development-history/desktop-backup-i18n-handoff-20260617.md`：2026-06-14 local desktop / backup / dashboard handoff、2026-06-17 Core UX 與 i18n 詳細完成記錄。
- `docs/development-history/desktop-portable-release-handoff-20260618.md`：Desktop Shell Phase 0-6、portable baseline、manual acceptance、README split 與 release packaging 邊界。
- `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`：Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。
- `docs/development-history/todo-changelog.md`：長版版本歷程。
- `docs/development-history/todo-completed-phases.md`：更早期完成 phase 與歷史工作清單。
