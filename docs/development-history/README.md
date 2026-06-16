# Development History

此資料夾保存從 AGENTS.md 指定的開發入口文件中拆出的長篇歷史內容。目標是讓 `docs/TODO.md` 保持可掃描，同時不丟失決策、完成紀錄與驗證脈絡。

| 檔案 | 內容 |
|---|---|
| `todo-completed-phases.md` | 已完成 phase、已決議事項與歷史工作清單。 |
| `todo-changelog.md` | 原 `docs/TODO.md` 的完整 Changelog 長表。 |
| `todo-archive-pre-go-primary-runtime-migration-20260606.md` | Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。 |
| `Prism_Go_模組逐步重構計劃報告.md` | 早期 Python → Go 漸進替換盤點與 Phase 19/23 決策脈絡；已由 active `docs/TODO.md` 取代 current roadmap 角色。 |
| `Go重構審查報告-20260613-codex.md` | 2026-06-13 Go primary 收尾唯讀審查原文；T046-T052 已吸收其 findings，保留作 T053 Python source 封存/刪除 guardrail。 |
| `20260616-chatgpt-Prism-虛擬團隊討論會.md` | Prism / Cerberus 討論逐字稿與整理稿；已將 Core UX、備選項與未來分支候選吸收到 `docs/TODO.md` 的 2026-06-16 intake。 |

維護規則：
- `docs/TODO.md` 只保留 active roadmap、backlog/icebox、近期更新摘要與歸檔索引。
- 完成階段後，先在 `docs/TODO.md` 標記狀態；若該段不再指導下一步工作，再移入本資料夾。
- 長版版本歷程寫入 `todo-changelog.md`；`docs/TODO.md` 只保留最近幾筆高信號摘要。
