# Prism 子代理派工指南（Agent Dispatch）

> 建立：2026-10-06，依使用者決策，按工單的**類別**與**難度**指定子代理的模型與推理程度（effort）。
> 這取代 2026-07-05 治理素材中「委派只寫 role-neutral 原則、不指定模型」的做法。
> 代理定義在 `.claude/agents/prism-*.md`（Claude Code 自動載入，新增後需重開 session）。模型與 effort 以那些檔案的 frontmatter 為準；`tests/test_agent_dispatch.py` 檢查它們與本檔一致。

## 1. 分工

- **主代理**（與使用者對話的 session）負責：
  - 選工單、在 `docs/TODO.md` 標 `Doing`。
  - 撰寫派工訊息、整合結果、最終驗證。
  - 更新 `docs/TODO.md` 與 `HANDOFF.md`，並 commit。
- **不派給子代理的事**：commit、push、release、Pi deploy。這些由主代理執行，且需要使用者明確授權。
- **子代理**只做派工訊息指定的那張工單（或其中一段），回報後結束。依 `docs/GOVERNANCE.md` §5，子代理的結論不是完成證據，主代理必須讀回並驗證。

## 2. 代理一覽

| 代理 | 模型 | effort | 工具 | 用途 |
|---|---|---|---|---|
| prism-scout | haiku | （不設定；Haiku 4.5 不支援 effort） | 唯讀（不可 Edit/Write） | 探勘、盤點、確認工單引用的 `file:line` |
| prism-docs | sonnet | medium | 全部 | 文件、四語 i18n 文案、治理文件 |
| prism-builder | sonnet | medium | 全部 | 規格清楚的一般實作（前端、Go、測試） |
| prism-engineer | opus | high | 全部 | 跨層或需判斷的實作；一般資料或安全修正 |
| prism-critical | opus | xhigh | 全部 | 資料搬移、不可逆、安全邊界；兩段式派工 |
| prism-verifier | opus | high | 唯讀加上執行測試 | 獨立驗收，決定能否標 `Done` |

成本參考（Anthropic API 公開價，每百萬 token 輸入／輸出，2026-09）：

| 模型 | 價格 | 定位 |
|---|---|---|
| Haiku 4.5 | $1／$5 | 快速、便宜，適合讀取型工作 |
| Sonnet 5.5 | $2／$10 | 日常 coding 主力；agentic coding 建議從 `medium` 起 |
| Opus 5.5 | $4／$20 | 需要判斷的工作；正確性敏感時至少用 `high` |
| Fable 5.1 | $10／$50 | 目前最強，回合較長；只作為升級選項 |

## 3. 類別與難度

類別：

| 代碼 | 類別 | 範例 |
|---|---|---|
| R | 探勘／盤點（唯讀） | 找引用、量測大小、確認行號 |
| D | 文件／文案／i18n | 文案改寫、治理文件、還原說明 |
| F | 前端（React／TypeScript／CSS） | Header 動作、預覽語意、mobile 排序 |
| B | 後端 Go（handler／SQL／搜尋） | 搜尋條件、版本來源、restart |
| T | 測試與 gate（Go test、e2e、pytest、CI） | behavior test、gate 分流 |
| X | 資料與安全 | DB 一致性、資料搬移、匯出完整性、備份還原、XSS、存取邊界 |
| V | 驗收／審查 | 工單完成後的獨立驗證 |
| O | 發版／部署／Pi | 不派工 |

難度：

| 等級 | 定義 |
|---|---|
| S | 1 個檔或機械式修改；規格完整、可逆 |
| M | 2–5 個檔；單一層；規格清楚 |
| L | 跨層，或需要設計判斷、狀態管理、效能取捨 |
| XL | 資料搬移、可能遺失資料或不可逆的變更、安全邊界 |

## 4. 派工矩陣

| 類別 \ 難度 | S | M | L | XL |
|---|---|---|---|---|
| R | prism-scout | prism-scout | prism-scout（model 覆寫為 sonnet） | — |
| D | prism-docs | prism-docs | prism-engineer | — |
| F / B / T | prism-builder | prism-builder | prism-engineer | prism-critical |
| X | prism-engineer | prism-engineer | prism-critical | prism-critical（可覆寫為 fable） |
| V | prism-verifier | prism-verifier | prism-verifier | prism-verifier |
| O | 不派工 | 不派工 | 不派工 | 不派工 |

- 一張工單跨多個類別時，取風險最高的類別。例如同時動到 F 與 X，就依 X 派工。
- 每張工單的實際派工見 `docs/WORK_ORDERS.md` 的「派工總表」。

## 5. 升級、降級與停止

- **升級**：同一張工單子代理失敗兩次，或回報「不確定」，就升一級：scout → builder → engineer → critical。
- **最高級**：critical 仍失敗時，主代理在派工時把 `model` 覆寫為 `fable`（effort 沿用 frontmatter 的 `xhigh`），並在 `docs/TODO.md` 的證據中記錄理由。
  - 依官方文件，`model` 可以在每次派工時覆寫，`effort` 只能由 frontmatter 決定。
- **停止**：子代理回報範圍擴散到 schema、資料修復、release 或 Pi 時，停止派工，回到主代理開 decision gate。
- **不降級**：X 類工單不為了省成本降級。R、D 類的小工作，主代理可以直接做，不一定要派工。

## 6. 派工流程

1. 主代理把工單在 `docs/TODO.md` 標為 `Doing`。
2. （選用）先派 `prism-scout`，確認工單引用的 `file:line` 仍然正確。審查報告是快照，程式可能已經改變。
3. 依矩陣派實作代理。派工訊息必須包含：
   - 工單 ID，以及 `docs/WORK_ORDERS.md` 中的規格（全文或明確指標）。
   - 邊界：「不要修改」清單、不得接觸的資料。
   - 回報格式：依 `docs/GOVERNANCE.md` §5。
4. **X 類 L／XL 採兩段式**：
   - 第一次派工不寫「計畫已確認」，代理只回報計畫。
   - 主代理審過計畫後，第二次派工寫明「計畫已確認」，代理才實作。
5. 實作完成後派 `prism-verifier`。docs-only 的 S 級工單，主代理可以自行跑 `git diff --check`、鏡像比對與 pytest 代替。
6. 主代理讀回 diff、確認驗收結果，更新 `docs/TODO.md` 的證據與 `HANDOFF.md`，然後 commit：一張工單一個 commit。

並行派工：

- 互不相干、檔案不重疊的工單可以同時派工。
- 注意：`isolation: worktree` 會從 **default branch** 開新的 worktree，看不到目前分支尚未合併的變更。在 feature branch 上工作時，不要用 worktree 隔離。

## 7. Codex 對應

Codex 讀 `AGENTS.md`，不使用 `.claude/agents/`。沿用同一套類別與難度：

| 難度 | Codex reasoning effort |
|---|---|
| S | low |
| M | medium |
| L、XL | 最高可用等級 |

- 模型使用 Codex 當前預設的 coding 模型。
- X 類工單與驗收，仍需要另一個 session 或人工做獨立驗證。
