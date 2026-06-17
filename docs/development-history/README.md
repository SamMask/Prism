# Development History

此資料夾保存從 AGENTS.md 指定的開發入口文件中拆出的長篇歷史內容。目標是讓 `docs/TODO.md` 保持可掃描，同時不丟失決策、完成紀錄與驗證脈絡。

| 檔案 | 內容 |
|---|---|
| `todo-completed-phases.md` | 已完成 phase、已決議事項與歷史工作清單。 |
| `todo-changelog.md` | 原 `docs/TODO.md` 的完整 Changelog 長表。 |
| `todo-archive-pre-go-primary-runtime-migration-20260606.md` | Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。 |
| `go-primary-runtime-completion-20260617.md` | 從 `docs/TODO.md` 瘦身移出的 T001-T053 Go primary migration 完成敘事、artifact 與任務表。 |
| `desktop-backup-i18n-handoff-20260617.md` | 從 `HANDOFF.md` / `docs/TODO.md` 瘦身移出的 2026-06-14 local desktop / backup / dashboard handoff、2026-06-17 Core UX 與 i18n 完成細節。 |
| `desktop-portable-release-handoff-20260618.md` | 從 `HANDOFF.md` / `docs/TODO.md` 瘦身移出的 Desktop Shell Phase 0-6、Windows portable baseline、manual acceptance、README split 與 release packaging 邊界。 |
| `Prism_Go_模組逐步重構計劃報告.md` | 早期 Python → Go 漸進替換盤點與 Phase 19/23 決策脈絡；已由 active `docs/TODO.md` 取代 current roadmap 角色。 |
| `Go重構審查報告-20260613-codex.md` | 2026-06-13 Go primary 收尾唯讀審查原文；T046-T052 已吸收其 findings，保留作 T053 Python source 封存/刪除 guardrail。 |
| `20260616-chatgpt-Prism-虛擬團隊討論會.md` | Prism / Cerberus 討論逐字稿與整理稿；已將 Core UX、備選項與未來分支候選吸收到 `docs/TODO.md` 的 2026-06-16 intake。 |

維護規則：
- `docs/TODO.md` 只保留 active roadmap、候選 backlog、下一步入口與歸檔索引。
- `HANDOFF.md` 只保留新對話接手所需的最短 current state / next entry；長版交接快照移入本資料夾。
- 完成階段後，先在 `docs/TODO.md` 標記狀態；若該段不再指導下一步工作，再移入本資料夾。
- 長版版本歷程寫入 `todo-changelog.md`；`docs/TODO.md` 只保留最近幾筆高信號摘要。
