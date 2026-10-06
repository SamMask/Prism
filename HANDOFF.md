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
- 2026-10-06～07：
  - PRISM-OPT-15～22、59～61 已完成，都合併到 `main` 並推送；P0 全部完成。逐張的證據見 `docs/TODO.md`。
  - PRISM-OPT-20 的「合併長文回筆記」尚未在正式資料上執行；執行前建議先下載 full snapshot。
  - 未建立 release／tag，未部署 Pi。

## Next Entry

1. 下一張 P1 由使用者指定。建議先做 62（對話框 focus trap）與 63（app 內導覽保護）：兩者都會在 Pi 的瀏覽器上遺失未存編輯。其他 P1：58、23～26、29 第一階段。
   - 開工時在 `docs/TODO.md` 標 `Doing`。
   - 最高風險（X／XL）的工單，計畫與實際改動另外交給 Codex astra 復審：用 `codex exec -m gpt-6-astra -s read-only`，範圍收窄並限時，因為它容易走偏、過度驗證。Codex sol 只在需要幫手時才用。
   - runtime smoke 用的隔離 data-dir 若缺少 `prompt_options.json`、`wizard_options.json`，Prompt Builder 會出現 404／405 console error。這是環境問題，不是回歸；屬於 PRISM-OPT-41 的範圍。
   - 使用者 2026-10-06 授權：工單審查與測試都通過後，直接 commit、fast-forward 合併回 `main` 並 push，不需再問。這項授權不包含 release、tag 或 Pi deploy。
   - 派工依 `docs/AGENT_DISPATCH.md`：每張工單的代理見 `docs/WORK_ORDERS.md` 的派工總表，代理定義在 `.claude/agents/`（新增後需重開 session）。
2. PRISM-OPT-28（自動還原點的預設值）與 29 的第二階段（LAN 管理 API）需要使用者先決策。P2 的 53～57、62 是驗收時發現的已知問題，之後處理。
3. P3／Future 工單維持 `Blocked`；只有啟動條件成立、且使用者明確 promote，才能施工。
4. 不要自動做 release、Pi deploy、schema 升版、AI、semantic search、內建 auth。

## Required Reads

- 每次都讀：`AGENTS.md`（或 `CLAUDE.md`）、本檔、`docs/TODO.md`。
- 其他文件依任務讀，見 `AGENTS.md` 的分層必讀表。
- 施工中工單的規格在 `docs/WORK_ORDERS.md`；派子代理時讀 `docs/AGENT_DISPATCH.md`。
