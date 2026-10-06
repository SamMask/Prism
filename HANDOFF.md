# HANDOFF - Prism active entry（2026-10-06）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/`：

- 最新歸檔：`docs/development-history/todo-handoff-archive-20261006.md`
- 更早的歸檔：`docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`

## Current State

- Go primary 是唯一 runtime；Python backend source 已於 T053 移除。Schema 為 migration v17。
- 最新 release 為 V2.6.1（tag 對齊 `7f5469c`）。Pi 最後一次部署是 2026-08-23 的 `70f04e7`；之後的 commits 未發版、未部署。
- Windows desktop current path 是 `Prism.exe` GUI app + WebView2 + same-process Go runtime；預設資料在 exe 同層 `PrismData\`。Installer/updater/WebView2 bootstrap/shortcut automation 仍 deferred。
- Pi：
  - live root 是 `/home/mask0709/prism`；`prism-go-primary.service` 只監聽 5004，經 Caddy 對外。
  - legacy `prism.service` 與 readonly sidecar 都是 inactive/disabled。
  - Pi delivery 必須依 `DEPLOY-PI.md` 另開 gate。
- 安全邊界：沒有內建 auth/token，只能放在 localhost、trusted LAN、VPN、SSH tunnel 或外部 auth reverse proxy 後面。
- 仍有約束力的產品決策：
  - KWF-07 product decision 已關閉：Prism 是個人筆記庫，不加入 `status` / `review_state` / `last_verified_at`；除非用途改變，不得重新 promote schema v18 workflow。
  - 刪除 note 時的圖片清理語意維持不變；更強的連帶刪圖只能以 opt-in decision gate 另開。
  - Mermaid、KaTeX、ABC、AI、semantic search、installer/updater 仍 `Blocked`。
- 2026-10-06：
  - 完成全專案審查（`docs/PROJECT_OPTIMIZATION_REVIEW_2026-10-06.md`）。所有 findings 已轉為工單 PRISM-OPT-15～51：看板在 `docs/TODO.md`，規格在 `docs/WORK_ORDERS.md`。
  - 同日完成治理文件瘦身（PRISM-OPT-27）。`.loop/verify-gate.ps1` 通過：pytest 399 passed、`go test ./...` ok、mirror 與 diff check 通過。證據記錄於 `docs/TODO.md`。
  - 2026-10-06 的變更（`e77a631`、`2bb38a7`）已 fast-forward 合併到 `main` 並推送 `origin/main`；未建立 release/tag，未部署 Pi。

  - PRISM-OPT-15 已完成：`GET /api/export/db` 改為送出一致快照。驗證證據記錄於 `docs/TODO.md`。分支為 `prism-opt-15-consistent-db-export`。

## Next Entry

1. 施工剩下的 P0：PRISM-OPT-16、17、18、19。四張彼此獨立，各自 commit。開工時在 `docs/TODO.md` 把該工單標為 `Doing`。
   - 派工依 `docs/AGENT_DISPATCH.md`：每張工單的代理見 `docs/WORK_ORDERS.md` 的派工總表，代理定義在 `.claude/agents/`（新增後需重開 session）。
2. P1 從 PRISM-OPT-20（依賴 19）與 21 開始。以下兩項需要使用者先決策：
   - PRISM-OPT-28：桌面版自動還原點的預設值與保留份數。
   - PRISM-OPT-29 的第二階段：是否收緊 LAN 管理 API。
3. P3／Future 工單維持 `Blocked`；只有啟動條件成立、且使用者明確 promote，才能施工。
4. 不要自動做 release、Pi deploy、schema 升版、AI、semantic search、內建 auth。

## Required Reads

- 每次都讀：`AGENTS.md`（或 `CLAUDE.md`）、本檔、`docs/TODO.md`。
- 其他文件依任務讀，見 `AGENTS.md` 的分層必讀表。
- 施工中工單的規格在 `docs/WORK_ORDERS.md`；派子代理時讀 `docs/AGENT_DISPATCH.md`。
