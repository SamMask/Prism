# Prism Governance Guide

更新日期：2026-07-05

本文件是 Prism 的開發治理規則，整理自 `docs/development-history/governance-source-20260705/` 的新版治理素材後，收斂成適合本 repo 的版本。它約束的是「怎麼規劃、宣稱、驗證、委派、維護文件」，不是 Prism 產品 runtime 功能。

## 1. 權威來源與適用範圍

Prism 的 current truth 以目前 repo source、contracts、tests、runtime 文件為準；舊審查報告、研究報告、外部建議與 `docs/development-history/governance-source-20260705/` 都只能作為素材，不能覆蓋 current truth。

權威讀取順序：

| 情境 | 主要來源 |
|---|---|
| 開發規範與入口 | `AGENTS.md` / `CLAUDE.md`（必須完全鏡像） |
| 最新接手狀態 | `HANDOFF.md` |
| Active roadmap / 候選 backlog | `docs/TODO.md` |
| API / runtime contract | `docs/API_REFERENCE.md`、`docs/contracts/`、`docs/CONTRACTS.md` |
| 架構 / DB | `docs/ARCHITECTURE.md`、`docs/SCHEMA.md` |
| Pi deploy / rollback | `DEPLOY-PI.md` |
| 歷史脈絡 | `docs/development-history/` |

治理文件只允許描述 process、證據標準與協作邊界。不得因治理更新新增 runtime feature、schema、API、deploy path 或背景同步流程。

## 2. 狀態與完成層級

`docs/TODO.md` 的每個可執行項目都應有狀態。允許值固定為：

| 狀態 | 意義 |
|---|---|
| `Todo` | 已規劃，可排入後續施工。 |
| `Doing` | 當前正在處理，應只有少量 active 項目。 |
| `Blocked` | 有明確外部依賴、決策或非目標邊界，暫不施工。 |
| `Review` | 已完成主要修改，等待驗證、審查或交付檢查。 |
| `Done` | 已完成並有驗證證據；長版紀錄可移到 `docs/development-history/`。 |

完成宣稱必須對齊證據，不可把不同層級混用：

| 層級 | 可以宣稱 | 不可宣稱 |
|---|---|---|
| 文件 / 設計 | 已規劃、已記錄、已建立 contract | 已實作、已可用 |
| 本機候選 | 本機變更存在、候選方案可評估 | 已成為 active roadmap 或正式 contract |
| 本機驗證 | 目標測試 / build / smoke 已通過 | 已部署、所有環境可用 |
| 發佈 / 部署 | 指定 artifact 或 Pi 路徑已驗證 | 未驗證平台也可用 |
| 依賴移除 | 舊路徑無 runtime owner、tests/docs 已收斂 | 只因新路徑存在就可刪除舊路徑 |

如果 source、docs、tests 互相衝突，先找 current source 與最小驗證，不要用舊 roadmap 或記憶宣稱完成。

## 3. 驗證證據標準

完成回報必須說明實際跑過什麼。不能執行時，要明講缺口。

| 變更類型 | 最小驗證 |
|---|---|
| Docs-only | `git diff --check`；若碰 `AGENTS.md` / `CLAUDE.md`，加做鏡像比對。 |
| Roadmap / TODO | 檢查狀態值、active/candidate/deferred 邊界、下一步入口是否一致。 |
| Frontend UI | Targeted build/typecheck；必要時 browser smoke 或 screenshot 驗證。 |
| Go API / runtime | Targeted Go tests；API contract 有變更時跑相關 contract/smoke。 |
| DB / migration | Fresh + existing DB 路徑、冪等、backup/rollback 邊界。 |
| Pi deploy | 依 `DEPLOY-PI.md` 做 artifact、systemd、Caddy、rollback/soak 檢查。 |
| Release / packaging | Artifact build、external data-dir、local data exclusion、release wording。 |

高風險修改不能只靠「我檢查過」自我背書。至少要有 diff、test output、read-back、runtime smoke 或可重跑命令之一。

Windows/PowerShell 注意事項：

- 路徑含空白、中文或特殊字元時使用 `-LiteralPath` 或引號。
- 需要可讀 git 路徑時可用 `git -c core.quotepath=off ...`。
- 不要把 Git 的 LF/CRLF warning 當成失敗；以 `git diff --check` 是否有 whitespace error 為準。
- 不混用 Bash 與 PowerShell 語法；避免跨 shell 組合 destructive file operations。

## 4. 停損、詢問與路線切換

預設自動完成安全、可逆、local 的修改與驗證。只有以下情況需要停下詢問：

- 會刪除資料、改寫歷史、覆蓋使用者未授權變更，或不可逆。
- 需要憑證、外部 production、公開部署或金鑰。
- 權威文件互相衝突，且不同選擇會導致不同 product contract。
- 使用者明確要求先不要改、只分析、或限制任務窗口。

需要切換路線的訊號：

- 同一修法連續失敗，且錯誤訊息沒有變小。
- 為了通過驗證開始堆 workaround、fallback、compat layer。
- 單一小任務擴散到跨層重構、schema/API 改動或新服務。
- 發現實際 owner 與原假設不同。

遇到上述訊號時，先回到 source、contract、最小 reproduction，不要擴張 scope。

## 5. 委派與子任務契約

Codex native subagents 或 OMX workflow 只在能提高速度、正確性或覆蓋面時使用。一般小型 docs/code 變更由主 agent 直接完成。

委派任務必須包含三件事：

1. **目標**：要回答或完成的具體結果。
2. **邊界**：可讀/可改檔案、不可做事項、current truth 來源。
3. **回報格式**： findings、evidence、changed files、tests、risks。

委派者仍負責整合與最終驗證。子 agent 的結論不是完成證據；必須由主 agent 讀回、比對 source，並執行必要驗證。

## 6. TODO、Handoff 與文件維護

`docs/TODO.md` 只保留 active roadmap、候選 backlog 與下一步入口。長版完成記錄、舊審查、研究與歷史脈絡放到 `docs/development-history/`。

新增或更新 TODO 時：

- 任務要能獨立施工與驗收。
- 每項都要有狀態與驗收標準。
- Candidate 不等於 active scope；deferred/non-goal 應標成 `Blocked` 或清楚寫明不施工條件。
- 不把外部建議原文直接升格成 roadmap；先轉成 Prism 現有 architecture / contract 下可驗證的工作項。

`HANDOFF.md` 只保留下一輪需要知道的最短 current state、驗證缺口與下一步入口。避免把完整歷史、研究摘要或大段 reasoning 放進 handoff。

## 7. UI / UX 治理

Prism 是 local-first knowledge workspace，不是行銷網站。UI 工作以高頻工作流為核心，優先保留既有操作習慣與資料安全。

UI 變更準則：

- 第一屏應是可工作的介面，不是 landing hero。
- SaaS/knowledge 工具風格應安靜、密集、可掃描，避免裝飾性卡片堆疊與單色調氾濫。
- 使用既有元件、state store、tokens 與互動模式；只有需求證明時才新增抽象。
- 每個 user flow 要有 loading、empty、error、success、disabled、keyboard/focus 狀態。
- 文字不得在 mobile/desktop 溢出或互相遮擋；固定格式元件要有穩定尺寸。
- 表格、長內容、附件、Markdown preview 應優先處理 overflow、copy、anchor、TOC 等日常可用性。
- 視覺變更需要 browser 或 screenshot 驗證；不能只靠靜態閱讀宣稱完成。

Markdown 顯示能力應服務知識工作流。優先順序是低風險、高頻：task list、table overflow、code copy、heading anchor、TOC、callout。Mermaid / KaTeX / embedding / semantic search 屬高複雜度或非當前方向，必須另立 contract 才能施工。

## 8. Governance Maintenance Protocol

`AGENTS.md` / `CLAUDE.md` 是短入口與硬規則鏡像；本文件承載細節。不要把長篇治理內容複製進兩份入口檔，避免鏡像成本膨脹。

修改治理文件時：

1. 先確認修改屬於 process / evidence / collaboration，而非 runtime feature。
2. 若新增官方治理文件，同步 `docs/README.md`、`docs/INDEX.md`，必要時更新 `docs/CONTRACTS.md`。
3. 若碰 `AGENTS.md` 或 `CLAUDE.md`，兩份必須完全一致。
4. 跑 docs-only 驗證：`git diff --check`、鏡像比對、必要的 link/read-back 檢查。
5. Final 回報只宣稱已驗證的範圍，未跑 runtime tests 就明講。

`docs/development-history/governance-source-20260705/` 是原新版治理素材的保留副本，不屬於 Prism 權威治理入口。正式規則應收斂到本文件、`docs/TODO.md`、`docs/CONTRACTS.md` 或其他已索引的官方文檔。
