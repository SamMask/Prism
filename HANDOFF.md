# HANDOFF - Prism active entry（2026-10-06）

本檔只放新對話接手需要的最短狀態。長版交接與完成紀錄已移到 `docs/development-history/`：

- 最新歸檔：`docs/development-history/todo-handoff-archive-20261006.md`
- 更早的歸檔：`docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`

## Current State

- Go primary 是唯一 runtime；Python backend source 已於 T053 移除。Schema 為 migration v17。
- 最新 release 為 **V2.7.0**（2026-10-07，tag 對齊 `a478a8b`）。Pi 已部署同一版，`/api/test` 回報 version 2.7.0。
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
  - PRISM-OPT-15～26、28、29、58～64、66 已完成；P1 全部完成，都合併到 `main` 並推送；P0 全部完成。逐張的證據見 `docs/TODO.md`。
  - PRISM-OPT-20 的「合併長文回筆記」尚未在正式資料上執行；執行前建議先下載 full snapshot。
  - 未建立 release／tag，未部署 Pi。

## Next Entry

1. 2026-10-06 roadmap 的 P0、P1、P2 已全部完成，並已發版為 V2.7.0。剩下的工單：
   - 77 已結案：24 篇遺失全文的舊筆記依使用者決定維持現狀；是否刪除重複的預覽副本（#5、#8／#57）待使用者決定。
   - 79：Pi `docs/attachments` 裡殘留的測試檔。
   - 78 已完成。
   - 新發現的問題照「已知的後面要處理」登記成 P2 或 P3。
   - 開工時在 `docs/TODO.md` 標 `Doing`。
   - 最高風險（X／XL）的工單，計畫與實際改動另外交給 Codex astra 復審：用 `codex exec -m gpt-6-astra -s read-only`，範圍收窄並限時，因為它容易走偏、過度驗證。Codex sol 只在需要幫手時才用。
   - runtime smoke 用的隔離 data-dir 若缺少 `prompt_options.json`、`wizard_options.json`，Prompt Builder 會出現 404／405 console error。這是環境問題，不是回歸；屬於 PRISM-OPT-41 的範圍。
   - 使用者 2026-10-06 授權：工單審查與測試都通過後，直接 commit、fast-forward 合併回 `main` 並 push，不需再問。這項授權不包含 release、tag 或 Pi deploy。
   - 派工依 `docs/AGENT_DISPATCH.md`：每張工單的代理見 `docs/WORK_ORDERS.md` 的派工總表，代理定義在 `.claude/agents/`（新增後需重開 session）。
2. Pi 部署與發版（使用者 2026-10-07 決定的順序；每一步執行前仍要使用者說開始）：
   1. ✅ 2026-10-07 已把 Pi 現有的 DB、圖片、附件、notes、config 備份到 `/home/mask0709/prism-predeploy-20261007-190419/`，SHA-256 已驗證。
   2. ✅ 2026-10-07 已部署 `f7c2be5`。OPT-36 的 Pi 重啟 smoke 在 5.8s 內恢復。
   3. ✅ 2026-10-07 已在 Pi 上執行 OPT-20：合併 77 篇，1 篇寫入 history。還原點在 `backups/separated-notes-20261007_190834_141235567/`。
   4. ✅ 2026-10-07 發版 V2.7.0（GitHub Release，附 portable zip），並再 cutover Pi 一次，Pi 現在顯示 2.7.0。
   - Pi 自動備份維持每週、最多 3 份輪替，不改。
3. P3／Future 工單維持 `Blocked`；只有啟動條件成立、且使用者明確 promote，才能施工。
4. 不要自動做 release、Pi deploy、schema 升版、AI、semantic search、內建 auth。

## Required Reads

- 每次都讀：`AGENTS.md`（或 `CLAUDE.md`）、本檔、`docs/TODO.md`。
- 其他文件依任務讀，見 `AGENTS.md` 的分層必讀表。
- 施工中工單的規格在 `docs/WORK_ORDERS.md`；派子代理時讀 `docs/AGENT_DISPATCH.md`。
