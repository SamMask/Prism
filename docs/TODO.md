# Prism Active TODO

本檔只保留目前可施工的 active roadmap、候選 backlog 與下一步入口。完成紀錄、舊 phase 與長版 changelog 全部移到 `docs/development-history/`。

---

## Current Truth（2026-06-17）

- Go primary 是唯一 current runtime owner；Python Flask backend source 已於 T053 移除。
- Go 漸進重構 T001-T053 已完成，完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- 2026-06-16 Core UX intake 已吸收；已完成項與 2026-06-14/06-17 handoff 快照見 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`。
- 2026-06-17 Core UX / Maintenance 三個 candidate 已完成：搜尋可解釋性 UX、search integrity diagnostics + 手動 FTS rebuild、maintenance health overview。未新增 semantic search、SearchHistory DB、自動修復、schema/API exposure boundary 或 Pi deploy 變更。
- 2026-06-17 Server Dashboard Windows 硬體顯示已收斂：Windows 不顯示 CPU 溫度 N/A 卡，改以系統運行卡補位；Pi/Linux 有溫度讀值時仍顯示 CPU 溫度。
- i18n active UI 可先視為完成；不要再開大型 UI 抽字串批次。Hidden/deferred UI（`PortConfigSection`、`UpdateSection`、`TagInput`）若日後恢復 render，再於該 gate 同步補四語 key。

Current truth 仍以本檔、`docs/ARCHITECTURE.md`、`docs/SCHEMA.md`、`docs/API_REFERENCE.md` 與實際 source/runtime 為準。不得因歷史報告曾討論過，就直接擴 scope 成 AI、semantic search、GraphRAG、auto-writing、schema/API/runtime 或 Pi deploy 變更。

---

## 下一個可施工入口

### Desktop Shell Phase 0 — message loop spike

目標：先驗證 Windows desktop shell 的單一 Win32 message loop，可同時服務空視窗與 tray icon，再決定是否接 WebView2 / 後端。

Contract：`CONTRACT-DESKTOP-SHELL-SPIKE`（見 `docs/CONTRACTS.md`）。

- [ ] 建立獨立 `desktop-spike/`（自己的 `go.mod`）。
- [ ] 僅使用 `golang.org/x/sys/windows` syscall；Phase 0 不引 WebView2、不接後端、不改 schema/API/runtime。
- [ ] 空 Win32 視窗 + tray icon，右鍵選單至少有 Show / Quit。
- [ ] 關閉視窗預設直接結束行程；close-to-tray 仍是後續正式封裝的進階選項。
- [ ] 驗收：tray 選單有反應、關視窗正常退出、message loop 不卡住；普通 console build 保留除錯 log。

已定桌面化產品決策：

- `.exe` 是視窗程式，不是 `.bat` 或純 console。
- 技術方向是內嵌 WebView2，傾向 `jchv/go-webview2`（純 syscall、可保 `CGO_ENABLED=0`），不採 `webview/webview_go`（需要 cgo）。
- 單一 `.exe` 後續目標：同一行程內啟動 Go server goroutine、WebView2 視窗指向 `127.0.0.1:<port>`、tray icon、named mutex 單一實例。
- 正式封裝才切 `-ldflags="-H=windowsgui"` 並改為檔案 log。

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
- `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`：Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。
- `docs/development-history/todo-changelog.md`：長版版本歷程。
- `docs/development-history/todo-completed-phases.md`：更早期完成 phase 與歷史工作清單。
