# Prism Active TODO

本檔只保留 active roadmap 的工單看板、deferred 候選與下一步入口。

- 工單完整規格：`docs/WORK_ORDERS.md`（本檔只記狀態，規格不在這裡重複）。
- 完成紀錄、舊 phase 與長版 changelog：`docs/development-history/`。2026-10-06 瘦身移出的內容見 `docs/development-history/todo-handoff-archive-20261006.md`。

閱讀方式：

- 狀態欄位固定使用：`Todo` / `Doing` / `Blocked` / `Review` / `Done`。只有正在施工的單一工單標 `Doing`。
- `Todo` = 已規劃、可以直接施工；`Blocked` = 需要決策、證據或觸發條件，啟動條件寫在 `docs/WORK_ORDERS.md`。
- 優先級：**P0** 現在做；**P1** 下一輪；**P2** 稍後；**P3** 目前不建議；**Future** 證據不足。

---

## Current Truth（2026-10-06）

- Go primary 是唯一 runtime owner；Python Flask backend source 已於 T053 移除（完整紀錄：`docs/development-history/go-primary-runtime-completion-20260617.md`）。Schema 為 migration v17。
- 最新 release 為 V2.6.1（tag 對齊 `7f5469c`）。2026-08-23 的 commit `70f04e7` 已部署到 Pi；之後的 commits 未發版、未部署。
- Windows portable：`Prism.exe` GUI app + WebView2 + same-process Go runtime，資料在 exe 同層 `PrismData\`；installer/updater 仍 deferred。
- Pi：live root `/home/mask0709/prism`，`prism-go-primary.service` 只監聽 5004，經 Caddy 對外。Pi delivery 與 GitHub release 是兩條流程，Pi 上線依 `DEPLOY-PI.md` 另開 gate。
- Prism 沒有內建 auth/token layer；安全邊界是 localhost、trusted LAN、VPN、SSH tunnel，或外部 auth 保護的 reverse proxy。
- 2026-10-06 全專案審查：`docs/PROJECT_OPTIMIZATION_REVIEW_2026-10-06.md`。所有 findings 已轉為下方工單 PRISM-OPT-15～51；08-12 審查遺留的 P2/P3 已併入本看板。
- 不得因審查建議自動擴大 scope 到 AI、semantic search、內建 auth、cloud sync、schema 版本升級、release 或 Pi deploy；需要時另開決策關卡。

---

## Active Roadmap — PROJECT-OPTIMIZATION-ROADMAP-2026-10-06

證據在審查報告，規格在 `docs/WORK_ORDERS.md`。一次只 promote 一張工單為 `Doing`；每張工單都可以單獨 branch、commit、review、rollback。

固定邊界：

- 不升 schema 版本、不新增 dependency；API 只做 additive 變更。
- 不碰正式 `knowledge.db`；runtime 驗證一律使用隔離 data-dir 與 fresh DB。
- UI 工單需要 desktop + 390px 的實際瀏覽器驗證；行為宣稱需要可執行測試（Go test、HTTP 或 e2e），不能只靠 source 或文件字串斷言。
- 任何工單若擴散到 schema、資料修復、release 或 Pi delivery，立即停止並另開 decision gate。

### P0 — 信任修正

| 工單 | 摘要 | 狀態 | 依賴 | Finding |
|---|---|---|---|---|
| PRISM-OPT-15 | `Download .db` 改為一致快照（重用 `writeConsistentDBBackup`） | Done | — | OPS-01 |
| PRISM-OPT-16 | 附件檢視改為純文字輸出；附件項目可用鍵盤操作 | Done | — | TECH-07 |
| PRISM-OPT-17 | Header 的 New 與搜尋在任何 route 都導向 Library 並生效 | Todo | — | UX-01 |
| PRISM-OPT-18 | CJK 子字串搜尋 fallback；palette 對 CJK 輸入 2 字即觸發 | Todo | — | FEAT-01 |
| PRISM-OPT-19 | 停止新的長文拆分；已拆分筆記存檔前先把全文收回 DB | Todo | — | FEAT-02 |

完成證據（2026-10-06）：

- `PRISM-OPT-15`（本機驗證；未發版、未部署 Pi）：
  - `handleExportDB`（`go-shadow/export.go`）改為先用 `writeConsistentDBBackup` 寫到暫存檔再送出，結束後刪除暫存檔，寫法比照 `handleBackupDownload`。API 路徑、檔名格式、Content-Type、gate 都不變。
  - 新增 Go 測試 `TestExportDBIncludesUncheckpointedWALWrite`（CJK 資料）、`TestExportDBFreshInitDBIncludesSchema`、`TestExportDBGates`；下載 helper 會斷言暫存目錄沒有殘留。前兩個測試在舊的 `http.ServeFile` 實作上失敗，修正後通過。
  - 獨立驗收（prism-verifier）在隔離 data-dir 的 fresh runtime 實測 HTTP：
    - fresh DB 下載檔有 `Notes` 表，integrity ok；同一時間 live 主檔本身沒有 `Notes`。
    - 新增 CJK 筆記後（尚未 checkpoint）立刻下載，下載檔含這筆。
    - 暫存目錄沒有殘留檔。
  - 驗證：`go vet` 通過、`go test ./...` ok、pytest 402 passed、`git diff --check` 通過。
- `PRISM-OPT-16`（本機驗證；未發版、未部署 Pi）：
  - `handleLoadAttachment`（`useNoteAttachments.ts`）改用 DOM API 建立 popup：`<pre>` 加上 `textContent`，不再以 `document.write` 插入附件內容。auto-extracted 載入流程沒有改。
  - `AttachmentPanel.tsx` 的每個附件列改為兩個原生按鈕：開啟按鈕，以及帶 `aria-label` 的刪除按鈕。刪除按鈕在 hover、鍵盤 focus 時顯示，在不支援 hover 的觸控裝置上一直顯示。
  - 回歸測試在 `tests/test_project_optimization_p0_frontend.py`，共兩個 source-lock 測試：
    - 用 regex 禁止 HTML sink：`.write(`、`.writeln(`、`innerHTML`、`srcdoc`、`createContextualFragment` 等，並要求以 `textContent` 寫入內容。
    - 檢查附件項目是原生按鈕，刪除按鈕有 `aria-label` 和 focus 顯示。
    - 兩個測試在 HEAD 原始碼上都失敗，`doc.write` 等突變也都會被抓到。
  - 瀏覽器實測：使用隔離的 fresh runtime，附件內容含 `<script>`、`</pre><img onerror>` 與 CJK。
    - Tab 鍵可以把 focus 移到開啟按鈕，focus ring 可見，刪除按鈕同時出現。按 Enter 會讀取附件。
    - popup 內只有一個 `<pre>`，原樣顯示 payload 文字，不會產生 script、img 元素。
    - 390px 寬度下刪除按鈕一直可見，沒有橫向捲動。刪除時會跳出確認，按取消後附件保留。
  - 獨立驗收（prism-verifier）在 headless Chromium 開真的 popup 對照：HEAD 版本被注入（title 變成 `PWNED`、script 被執行），新版本沒有。
  - 驗證：`npm run build` 通過、pytest 404 passed、`git diff --check` 通過。
  - 尚未驗證：Firefox／Safari，以及 WebView2 desktop shell 中真正開出的 popup。

### P1 — 下一輪

| 工單 | 摘要 | 狀態 | 依賴 | Finding |
|---|---|---|---|---|
| PRISM-OPT-20 | 「合併長文回筆記」維護動作（dry-run、先建還原點、檔案移入隔離資料夾） | Todo | 19 | FEAT-02、PERF-01 |
| PRISM-OPT-21 | `Ctrl+S` 存檔後留在編輯器；未存變更時以 `beforeunload` 保護 | Todo | — | UX-02 |
| PRISM-OPT-22 | 預覽狀態的最小語意修正（標題不 autofocus） | Todo | 建議在 21 之後 | UX-03 |
| PRISM-OPT-23 | 匯出範圍文案誠實化（JSON、Markdown、.db） | Todo | — | FEAT-03 |
| PRISM-OPT-24 | 版本單一來源（由 runtime 提供，移除寫死的版本號） | Todo | — | TECH-01 |
| PRISM-OPT-25 | `frontend/node_modules` 移出版控；清除死資產與死 script | Todo | — | TECH-04 |
| PRISM-OPT-26 | 補強 behavior test；fast／release gate 分流；historical marker | Todo | 建議在 15、18、19 之後 | TECH-02 |
| PRISM-OPT-27 | 治理文件瘦身、修正斷鏈、解除 docs-lock 測試耦合 | Done | — | TECH-03 |
| PRISM-OPT-28 | 桌面版每日自動還原點 | Blocked | 使用者決定預設值與保留份數 | OPS-02 |
| PRISM-OPT-29 | LAN 管理邊界：先修正文件，再決定是否收緊 | Todo | 第二階段需要決策 | OPS-04 |
| PRISM-OPT-52 | 子代理派工：依類別與難度指定模型與 effort（`.claude/agents/` + `docs/AGENT_DISPATCH.md`） | Done | — | 使用者需求 |

完成證據（2026-10-06）：

- `PRISM-OPT-27`：
  - `docs/ARCHITECTURE.md` 62.5KB → 約 12KB。
  - TODO、HANDOFF、ARCHITECTURE 的歷史原文移到 `docs/development-history/`（`todo-handoff-archive-20261006.md`、`architecture-go-migration-history-20261006.md`）。
  - 必讀改為分層、修正斷鏈、刪除重複的 `docs2/`。
  - 28 個測試改讀歸檔，斷言內容不變。
  - 驗證：`.loop/verify-gate.ps1` 通過（pytest 399 passed、`go test` ok）。commit `e77a631`。
- `PRISM-OPT-52`：
  - 新增 `.claude/agents/` 六個代理：scout＝haiku；docs、builder＝sonnet／medium；engineer＝opus／high；critical＝opus／xhigh；verifier＝opus／high、唯讀。
  - 派工矩陣在 `docs/AGENT_DISPATCH.md`，每張工單的派工在 `docs/WORK_ORDERS.md` 的派工總表。
  - `tests/test_agent_dispatch.py` 檢查三者一致，且能偵測故意製造的設定漂移。
  - 驗證：`.loop/verify-gate.ps1` 通過。新代理需重開 session 才會載入。

### P2 — 稍後

| 工單 | 摘要 | 狀態 | 依賴 | Finding |
|---|---|---|---|---|
| PRISM-OPT-30 | Mobile 排序控制與首屏密度 | Todo | — | UX-04 |
| PRISM-OPT-31 | 筆記計數改用單一來源；Maintenance 改讀 `/api/system/stats` | Todo | — | UX-05 |
| PRISM-OPT-32 | mutation 後就地更新，不再重置列表 | Todo | 21 | PERF-02 |
| PRISM-OPT-33 | Library 導覽去重（desktop 的 FilterStrip、重複三次的標題與計數） | Todo | — | IA-01 |
| PRISM-OPT-34 | Settings 重新分組（Library & Editor、Images & storage、tab 深連結） | Todo | — | IA-02 |
| PRISM-OPT-35 | Full snapshot 手動還原說明 | Todo | — | OPS-03 |
| PRISM-OPT-36 | Server dashboard 的 Restart：接上真正的重啟，或移除 | Todo | — | OPS-05 |
| PRISM-OPT-37 | 使用者看得到的遷移期字串改為中性文案 | Todo | — | TECH-05 |
| PRISM-OPT-38 | Reading list 預取加上限或改為 lazy detail | Todo | — | R0812:PERF-03 |
| PRISM-OPT-39 | JSON 匯出與匯入補齊欄位（置頂、封存、譜系、版面） | Todo | 23 | FEAT-03 |

### P3 / Future — 需要證據或明確 promote

| 工單 | 摘要 | 狀態 | 啟動條件 | Finding |
|---|---|---|---|---|
| PRISM-OPT-40 | Prompt Builder：「AI optimize」改名、模板語系、seed 缺失時的死路 | Blocked | 使用者明確 promote | UX-06 |
| PRISM-OPT-41 | Prompt Builder seed config 內嵌到 binary；`pack.bat` 補帶 config | Blocked | 使用者明確 promote | OPS-06 |
| PRISM-OPT-42 | API 表面衛生：死 route、死 wrapper、未引用元件、API 文件標 deprecated | Blocked | 先確認外部 agent 的實際用途 | TECH-06 |
| PRISM-OPT-43 | 移除 capability flags；`go-shadow` 改名 | Blocked | 出現新增 runtime mode 的需求，或 flags 誤配的證據 | TECH-05 |
| PRISM-OPT-44 | 非中文使用者的首次體驗（雙語 welcome note 與模板） | Blocked | 有非中文使用者的證據 | BIZ-01 |
| PRISM-OPT-45 | FTS5 trigram 索引 | Blocked | 資料超過 1 萬筆，且 3 字以上的查詢占多數 | FEAT-01 |
| PRISM-OPT-46 | `Note_History` 保留策略 | Blocked | PRISM-OPT-20 之後出現 DB 成長的證據 | PERF-03 |
| PRISM-OPT-47 | 文字附件內容索引 | Blocked | PRISM-OPT-20 之後仍有約 50 個以上文字附件，且搜尋常態 partial | PERF-01 |
| PRISM-OPT-48 | 回收桶（軟刪除與復原） | Blocked | 出現誤刪事件的證據 | FEAT-05 |
| PRISM-OPT-49 | 桌面版與 Pi 之間跨裝置同步 | Blocked | 有多裝置寫入的證據；先完成 PRISM-OPT-35 | FEAT-06 |
| PRISM-OPT-50 | Prompt options 自訂 UI | Blocked | 有使用者需求的證據 | FEAT-07 |
| PRISM-OPT-51 | Wiki 連結與 backlinks | Blocked | 有使用者需求的證據 | FEAT-08 |

---

## Deferred Candidates

- [ ] `DEEP-SCAN-RISK-CANDIDATE-01` 01H 仍是低優先維護 triage（狀態：`Blocked`）：剩餘 frontend bundle/Browserslist warning、歷史 frozen docs/test wording仍需另行 promote；其中 `go-shadow/main.go` route-local 小整理已明確化為 `GO-MAIN-SPLIT-CANDIDATE-01`，但一次性 runtime 大拆分仍 `Blocked`。
- [ ] Desktop installer/updater/WebView2 bootstrap/shortcut automation（狀態：`Blocked`；需使用者明確需要 installer/updater 類能力）。
- [ ] Hidden/deferred i18n UI（`PortConfigSection`、`UpdateSection`、`TagInput`）（狀態：`Blocked`；只有日後恢復 render，才於該 gate 同步補四語 key）。2026-10-06 審查確認 `UpdateSection`、`TagInput` 沒有被引用，是否刪除由 PRISM-OPT-42 決定。
- [ ] Mermaid 圖表渲染（狀態：`Blocked`；只有 `MARKDOWN-SYNTAX-CANDIDATE-01` 的 `MDS-05` 被明確 promote 後才可施工；不得順手導入 heavy renderer）。
- [ ] KaTeX 數學公式 / ABC 樂譜渲染（狀態：`Blocked`；目前凍結為備選，只有使用者明確重新開啟需求時才可施工）。
- [ ] AI / semantic search / embeddings / GraphRAG / auto-writing（狀態：`Blocked`；仍不在 active roadmap）。
- [ ] 內建登入、多使用者、OAuth、RBAC、cloud sync、directory watcher、background sync daemon、大型備份平台、一次性 editor rewrite（狀態：`Blocked`；來源為 `KNOWLEDGE-WORKFLOW-CANDIDATE-01` 的不採納清單）。
- [ ] Source URL 自動抓 title / link health（狀態：`Blocked`；需要外網或批次請求時，必須另開 privacy / timeout / user-triggered boundary，不得在讀取 note 時背景追蹤遠端 URL）。
- [ ] 刪除 note 時一併刪除「只被這些卡片使用的圖片」（狀態：`Blocked`；只能以 opt-in、預設不勾的方式另開 decision gate；不得改 current Go delete/media cleanup runtime semantics）。

---

## Release / Pi 規則

- 任何 release、tag 或 portable package 都必須依 `docs/RELEASE_CHECKLIST.md` 重跑 fresh validation；push 後確認 GitHub Actions 綠燈。
- Pi delivery 不是 release 的自動副作用；每次上線都要依 `DEPLOY-PI.md` 重驗 service、migration、changed endpoint 與 UI evidence。

---

## Archive Index

- `docs/development-history/todo-handoff-archive-20261006.md`：2026-10-06 治理瘦身時移出的 TODO 完成項（EDITOR-COPY、MARKDOWN-SYNTAX、KWF-01～07、08-12 optimization roadmap、V2.6／V2.6.1 release 與 Pi gates、GO-MAIN-SPLIT、NOTE-DELETE-MEDIA、PI-PATH-MIGRATION）與 HANDOFF 長版 current state。
- `docs/development-history/architecture-go-migration-history-20261006.md`：從 `docs/ARCHITECTURE.md` 移出的 Phase 18–23 與 T004–T053 歷史敘事、Frontend Redesign Intake。
- `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`：2026-06-19 TODO/HANDOFF 瘦身時移出的 V2.5 收尾、完成 gate、release/package evidence 與 deferred notes。
- `docs/development-history/go-primary-runtime-completion-20260617.md`：T001-T053 Go primary migration 完成敘事、artifact 與完整任務表。
- `docs/development-history/desktop-backup-i18n-handoff-20260617.md`：2026-06-14 local desktop / backup / dashboard handoff、2026-06-17 Core UX 與 i18n 詳細完成記錄。
- `docs/development-history/desktop-portable-release-handoff-20260618.md`：Desktop Shell Phase 0-6、portable baseline、manual acceptance、README split 與 release packaging 邊界。
- `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`：Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。
- `docs/development-history/todo-changelog.md`：長版版本歷程。
- `docs/development-history/todo-completed-phases.md`：更早期完成 phase 與歷史工作清單。
