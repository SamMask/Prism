# Development History

此資料夾保存從 AGENTS.md 指定的開發入口文件中拆出的長篇歷史內容。目標是讓 `docs/TODO.md` 保持可掃描，同時不丟失決策、完成紀錄與驗證脈絡。

| 檔案 | 內容 |
|---|---|
| `todo-completed-phases.md` | 已完成 phase、已決議事項與歷史工作清單。 |
| `todo-changelog.md` | 原 `docs/TODO.md` 的完整 Changelog 長表。 |
| `todo-archive-pre-go-primary-runtime-migration-20260606.md` | Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。 |

維護規則：
- `docs/TODO.md` 只保留 active roadmap、backlog/icebox、近期更新摘要與歸檔索引。
- 完成階段後，先在 `docs/TODO.md` 標記狀態；若該段不再指導下一步工作，再移入本資料夾。
- 長版版本歷程寫入 `todo-changelog.md`；`docs/TODO.md` 只保留最近幾筆高信號摘要。
