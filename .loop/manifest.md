---
# Prism 專用 Loop Engineering 對照表。
# 本檔只描述 Codex 開發迴圈要讀哪些治理文件，以及收尾 gate 怎麼跑。
# 不要把外部模板規則貼進這裡；規則以 Prism 既有文件與 runtime source 為準。

explore:
  - AGENTS.md
  - docs/ARCHITECTURE.md
  - docs/SCHEMA.md
  - docs/TODO.md

plan:
  - docs/TODO.md
  - docs/CONTRACTS.md
  - docs/API_REFERENCE.md

execute:
  - AGENTS.md
  - docs/ARCHITECTURE.md
  - docs/SCHEMA.md

verify:
  - AGENTS.md
  - docs/CONTRACTS.md

iterate:
  - HANDOFF.md
  - docs/TODO.md

# Codex 版沒有 Claude Stop hook；每次 verify 階段由 agent 主動執行此 gate。
gate: "pwsh -NoProfile -ExecutionPolicy Bypass -File .loop/verify-gate.ps1"

max_iterations: 5
---

# 使用方式

需要跑迴圈時，對 Codex 說「照 Loop Engineering 跑這個任務」或「做到 gate 通過再收尾」。
Codex 必須先讀 `.loop/LOOP-PROCEDURE.md` 與本 manifest，再依階段讀取上方治理文件。

本 manifest 是 Prism 專用；`迴圈工程/` 原始模板資料夾可在本地化完成並驗證後刪除。
