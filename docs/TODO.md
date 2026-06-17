# Prism Active TODO

本檔只保留目前可施工的 active roadmap、候選 backlog 與下一步入口。完成紀錄、舊 phase 與長版 changelog 全部移到 `docs/development-history/`。

---

## Current Truth（2026-06-18）

- Go primary 是唯一 current runtime owner；Python Flask backend source 已於 T053 移除。
- Go 漸進重構 T001-T053 已完成，完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- 2026-06-16 Core UX intake 已吸收；已完成項與 2026-06-14/06-17 handoff 快照見 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`。
- 2026-06-17 Core UX / Maintenance 三個 candidate 已完成：搜尋可解釋性 UX、search integrity diagnostics + 手動 FTS rebuild、maintenance health overview。未新增 semantic search、SearchHistory DB、自動修復、schema/API exposure boundary 或 Pi deploy 變更。
- 2026-06-17 Server Dashboard Windows 硬體顯示已收斂：Windows 不顯示 CPU 溫度 N/A 卡，改以資料位置卡補位；Pi/Linux 有溫度讀值時仍顯示 CPU 溫度與 uptime 系統資訊。
- 2026-06-17/18 Desktop Shell Phase 0-6、post-package follow-up 與 manual acceptance 已完成；長版完成紀錄見 `docs/development-history/desktop-portable-release-handoff-20260618.md`。
- Windows portable current truth：`Prism.exe` 直接進 desktop shell，預設資料在 exe 同層 `PrismData\`；`--data-dir` / `PRISM_GO_DATA_DIR` 只作進階/debug override。runtime 不顯示 first-run data-dir selector、不寫 `PrismPortable.json`、不建立/修補桌面捷徑。Installer/updater/WebView2 bootstrap/Start Menu/uninstall/update 仍 deferred。
- 2026-06-18 Desktop Shell post-package manual acceptance 已由使用者確認：將最新 portable 複製到其他資料夾執行後，Windows Defender 未再阻擋，雙擊 `Prism.exe` 可正常開啟，簡化後的 `PrismData\` 同層資料路線成立。
- 新使用者前端預設值（無 localStorage 時）已收斂為淺色 / 暖灰 / 典雅金、卡片開啟預覽模式、自動載入更多開啟；語系會先依 OS/browser 在中/英/日/韓內偵測，簡中/繁中都落到 `zh-TW`，其他語系預設 `en`；閱讀模式仍保留元件但不再是卡片開啟模式選項。
- `build/` 舊 generated smoke/build artifacts 已清理，只保留最新 desktop shell / portable smoke 輸出；真實資料目錄（DB、attachments、notes、uploads）未納入清理。
- i18n active UI 可先視為完成；不要再開大型 UI 抽字串批次。Hidden/deferred UI（`PortConfigSection`、`UpdateSection`、`TagInput`）若日後恢復 render，再於該 gate 同步補四語 key。

Current truth 仍以本檔、`docs/ARCHITECTURE.md`、`docs/SCHEMA.md`、`docs/API_REFERENCE.md` 與實際 source/runtime 為準。不得因歷史報告曾討論過，就直接擴 scope 成 AI、semantic search、GraphRAG、auto-writing、schema/API/runtime 或 Pi deploy 變更。

---

## 下一個可施工入口

### Desktop Shell / Release Packaging

Desktop Shell 目前沒有 active construction item。Phase 0-6、post-package follow-up、manual acceptance 與 release baseline 已歸檔到 `docs/development-history/desktop-portable-release-handoff-20260618.md`。

下一個 desktop/packaging 入口只在使用者明確需要 installer/updater 類功能時成立，包括 Start Menu、桌面捷徑、指定資料夾 UI、WebView2 bootstrap、uninstall 或 update flow。啟動前必須另開 decision gate；不得直接引入 NSIS/WiX/MSIX、auto updater、shortcut automation 或 hidden PowerShell。

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

### Core UX / Maintenance

- [x] **SEARCH-UX-CANDIDATE-01 Search explainability UX**（2026-06-17 完成）：Home 已加入 Search Context Bar、Empty State Recovery、Search Scope Hint、Recent Searches（`localStorage` 最多 5 筆、不進 DB）、Mobile Search Entry。未新增 relevance ranking、semantic search、attachment body snippets、SearchHistory DB、advanced query language 或每鍵即時搜尋。
- [x] **SEARCH-INTEGRITY-CANDIDATE-01 Search integrity diagnostics contract**（2026-06-17 完成）：已新增 `GET /api/system/search-integrity` 與 `POST /api/system/search-integrity/rebuild-fts`。第一版只做診斷與手動 FTS rebuild；禁止 VACUUM、改 Notes、改 Attachments、刪檔、自動修復、讓 Agent 自動觸發。
- [x] **MAINT-OVERVIEW-CANDIDATE-01 Maintenance health overview**（2026-06-17 完成）：Settings 維護頁已新增狀態總覽，只呈現資料一致性、搜尋索引與 WAL 手動狀態；不新增修復行為。

### Future Branch Candidates

以下是不同產品線或 sidecar 方向，先記錄不施工。Promote 前必須先補 contract / docs，不得直接改 Prism Core runtime。

- [ ] **BRANCH-CANDIDATE-CRR-LITE**：Cerberus Research Radar Lite。第一版只可先做 docs/schema：Research Signal Card、Normalized Paper Candidate、Paper Source Query Contract、Dedup Contract、LLM Extraction Contract、Prism/Cerberus mapping。不接 API、不接 LLM、不寫 Prism、不寫 CerberusCoin repo；paper 只能變成可測假設，不能變成策略結論。
- [ ] **BRANCH-CANDIDATE-AI-BRIDGE**：外部 Agent 安全讀取 Prism 的 read-only bridge。不得內建 AI chat、embedding、semantic search、GraphRAG 或 agent runner；若未來啟動，先做 read-only contract 與安全邊界文件。
- [ ] **BRANCH-CANDIDATE-WATCH-LITE**：RSS / arXiv / GitHub / blog / URL tracking sidecar。只收集候選到 pending queue，不自動寫 permanent Prism note；等 Core UX 與備份/還原語義穩定後再評估。
- [ ] **BRANCH-CANDIDATE-ARCHIVE-INTAKE**：web / PDF / markdown / source intake sidecar。先記錄為匯入輔助方向，不得把 crawler、summarizer 或大量自動寫入帶進 Core。

---

## Archive Index

- `docs/development-history/go-primary-runtime-completion-20260617.md`：T001-T053 Go primary migration 完成敘事、artifact 與完整任務表。
- `docs/development-history/desktop-backup-i18n-handoff-20260617.md`：2026-06-14 local desktop / backup / dashboard handoff、2026-06-17 Core UX 與 i18n 詳細完成記錄。
- `docs/development-history/desktop-portable-release-handoff-20260618.md`：Desktop Shell Phase 0-6、portable baseline、manual acceptance、README split 與 release packaging 邊界。
- `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`：Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。
- `docs/development-history/todo-changelog.md`：長版版本歷程。
- `docs/development-history/todo-completed-phases.md`：更早期完成 phase 與歷史工作清單。
