# Prism Test Portfolio

> Baseline: 2026-08-12（分類）；2026-10-07 依實際執行性重新分類（PRISM-OPT-26）
> Current runtime: Go primary
> Inventory: 78 Python test modules / 422 collected pytest, 137 Go test functions, 17 isolated browser e2e

本文件說明測試「在證明什麼」，避免把 source wording、歷史計畫或部署紀錄誤當成 current product behavior。分類依據是測試**實際做了什麼**（執行程式、讀 source、讀文件），不是測試名稱。

## Gates

| Gate | 指令 | 內容 |
|---|---|---|
| Fast（日常） | `pwsh -NoProfile -File .loop/verify-gate.ps1` | `git diff --check`、mirror、`pytest tests/ -m "not slow and not historical"`（253）、`go test ./...` |
| Release（發版、CI） | `pwsh -NoProfile -File .loop/verify-gate.ps1 -Release` | Fast 的全部 + `slow`（4）+ `historical`（165）= 全部 422 pytest，再加 `pytest e2e`（17） |

- Marker 定義在 `pytest.ini`。`slow`：4 個打包／桌面 smoke（build binary、重跑 `go test ./...`、portable smoke）。`historical`：26 個只讀文件的 Phase 19–23 證據模組。
- CI（`.github/workflows/ci.yml`）安裝 Playwright Chromium 並跑 `-Release`。
- Release gate 的覆蓋 = 分流前的全部 pytest + Go tests，再加 e2e；分流沒有刪除或跳過任何測試。

計時（2026-10-07，同一台 Windows 開發機；數字會因機器而異，只作量級參考）：

| 量測 | 分流前（全部 pytest） | Fast gate | Release gate |
|---|---|---|---|
| pytest 冷建置（全新 GOCACHE，交替跑） | 129.6–143.3s | 71.5–75.0s | — |
| pytest 熱快取 | 約 96s | 約 45–52s | 72–133s（422 個，依快取） |
| 整個 gate 熱快取 | — | 47–55s | 114–176s（含 `pytest e2e` 17 個，約 24–46s） |

## 依執行性分類

| 層 | 數量 | Gate | 證明什麼 |
|---|---:|---|---|
| Go unit／handler（`go-shadow/*_test.go`） | 137 | fast + release | SQL、handler、檔案、migration、restore 的實際行為；Go correctness 的第一層 owner |
| pytest 執行型（build／啟動 Go runtime、HTTP、subprocess） | 27（fast 23、`slow` 4） | fast 23；release 27 | artifact、fresh DB、migration、uploads、import/export、server/system 的跨層驗收 |
| Browser e2e（`e2e/`，隔離 runtime） | 17 | release | 使用者流程與本次審查找到的 bug（見下表） |
| pytest source／contract lock | 230 | fast | 斷言 frontend／Go／scripts 原始碼或 contract 含某段；快速防止入口被移除，**不能**單獨證明行為 |
| Historical 文件鎖（`historical`） | 165 | release | 舊 phase 的 contract JSON 與歸檔敘事仍可讀；不能作 current acceptance |

Behavior 類模組（下節）大多屬於 source lock。行為宣稱需要 Go test、pytest 執行型或 e2e 證據（`docs/GOVERNANCE.md` §3）。

## 2026-10-06 審查 bug 的執行型守門

| Bug（工單） | Go | e2e（`e2e/test_review_regressions.py` 除非另註） |
|---|---|---|
| 中文搜尋失效（FEAT-01／OPT-18） | `TestNotesSearchFindsCJKSubstringsInTitleAndContent`、`TestNotesSearchClauseAddsCJKBranchOnlyForCJKQueries` | `test_header_cjk_search_from_prompt_builder_finds_mid_sentence_word`、`test_command_palette_queries_server_after_two_cjk_chars` |
| DB 複本漏 WAL（OPS-01／OPT-15） | `TestExportDBIncludesUncheckpointedWALWrite`、`TestBackupDownloadAndRotateIncludeLatestWALState`、`TestFullDataSnapshotExportIsLocalAtomicAndManifestVerified` | — |
| 長文拆分與縮短後被還原（FEAT-02／OPT-19、20、60） | `main_test.go` 的 `TestRestoreSeparated*`（8 個）、`go-shadow/notes_inline_test.go`（27 個） | `test_saving_a_long_note_keeps_the_full_text_in_the_note`、`test_shortened_split_note_keeps_the_new_text_after_reopen` |
| 非 Home 的 New 與搜尋（UX-01／OPT-17） | — | `test_header_new_from_settings_opens_editor_in_library`、`test_header_cjk_search_from_prompt_builder_finds_mid_sentence_word` |
| Ctrl+S 存檔後關閉（UX-02／OPT-21） | — | `test_ctrl_s_saves_new_note_keeps_editor_open_and_updates_same_note` |
| 附件 popup 可被注入（TECH-07／OPT-16） | — | `test_text_attachment_popup_shows_markup_as_text` |
| Dialog 非 modal（OPT-62） | — | `e2e/test_dialog_a11y.py` |

對應的 source lock（`test_project_optimization_p0_frontend.py`、`test_project_optimization_p1.py`、`test_command_palette_server_search.py`）保留作 fast 防線；Header 的鎖接受等價寫法（例如 `!isHomeRoute`）。

## Module 分類

### Behavior（source lock 為主）

- Library/search: `test_command_palette_server_search.py`, `test_kwf02_saved_search_workspace.py`, `test_phase22_command_palette_entrypoint_reliability.py`, `test_phase22_home_search_empty_state_context_copy.py`, `test_starred_tag_filters.py`.
- Notes/content: `test_markdown_sanitization.py`, `test_note_delete_media_ux_copy.py`, `test_note_list_lightweight_payload.py`, `test_note_variant_lineage.py`, `test_reading_workspace.py`, `test_editor_copy_content.py`, `test_dialog_a11y_opt62.py`.
- Import/UI/i18n: `test_bulk_markdown_txt_import.py`, `test_default_category_i18n.py`, `test_frontend_i18n_settings.py`, `test_image_viewer_lightbox.py`, `test_kwf03_to_kwf07_workflow.py`.
- Product surfaces: `test_phase22_prompt_builder_mobile_action_bar.py`, `test_phase22_settings_tab_deep_linking.py`, `test_phase24_settings_home_maintenance_followups.py`, `test_project_optimization_p0_frontend.py`, `test_project_optimization_p1.py`, `test_desktop_portable_followups.py`.

### Contract（執行型 + source lock）

- 執行型（HTTP／subprocess）: `test_go_primary_e2e_pure_go_acceptance.py`, `test_go_primary_t008_fresh_db_init.py`, `test_go_primary_t009_t010_migrations.py`, `test_go_primary_t020_t023_files_uploads.py`, `test_go_primary_t024_t027_media_cleanup.py`, `test_go_primary_t028_t031_import_export.py`, `test_go_primary_t032_t035_server_system.py`, `test_schema_regression.py`.
- Packaging／desktop（各含 1 個 `slow` smoke）: `test_desktop_shell_phase0_spike.py`, `test_desktop_shell_phase1_3.py`, `test_desktop_shell_phase4_6.py`, `test_phase19_go_runtime_packaging.py`.
- Source lock: `test_go_primary_t007_sqlite_owner.py`, `test_go_primary_t039_t041_package_staging.py`, `test_go_primary_t042_t044_live_cutover.py`, `test_go_primary_t045_python_packaged_runtime_deletion.py`, `test_go_primary_t046_t050_frontend_route_coverage.py`, `test_go_primary_t051_t052_current_truth_cleanup.py`, `test_phase19_go_readonly_promotion_gate.py`, `test_phase23_go_local_smoke_artifact_release_boundary.py`, `test_phase23_go_packaged_runtime_release_candidate.py`, `test_phase23_python_package_deletion_closure.py`.

### Governance（fast）

- `test_agent_dispatch.py`, `test_codex_task_review_checklist.py`, `test_go_primary_t046_t053_audit_queue_planning.py`, `test_phase22_product_frontend_backlog_intake.py`, `test_phase22_product_frontend_next_selection.py`, `test_project_review_hygiene.py`, `test_todo_go_primary_runtime_plan.py`.

Governance assertions只鎖定範圍、狀態層級與下一入口。它們通過時，不代表 build、runtime、browser、deploy 或 Pi 已驗證。

### Historical（`historical` marker，release only）

只讀 `docs/contracts/*.json` 與歸檔文件的 26 個模組：

- Phase 19（12）: caddy cutover candidate decision、caddy extended readonly soak、caddy matcher runbook hardening、caddy readonly routing drill、cutover readiness audit、permanent caddy readonly cutover、post matcher hardening stabilization、post permanent caddy stabilization、readonly long soak decision、readonly service cutover plan、readonly soak execution、reverse proxy service cutover plan。
- Phase 20（4）: candidate fixture planning、post polish stabilization、post readonly scope assessment、write surface contract inventory。
- Phase 21（2）: local commit push readiness、post push product frontend selection。
- Phase 23（8）: db-only write expansion selection、file read parity plan、live cutover rollback proof、ownership closure audit、pi deployment rollout、write surface selection、python removal and final stabilization、python runtime ownership closure。

Phase 19–23 中仍讀 current source／scripts 的模組（上面 Contract 的 4 個）不標 `historical`，留在 fast gate。

## Required gates

| Change | Required checks |
|---|---|
| Frontend behavior | targeted pytest, `npm run build`, 相關 e2e（`pytest e2e -k ...`） |
| Go/API/SQL/files | targeted Go tests, fast gate |
| Docs/governance only | targeted pytest, mirror check, `git diff --check` |
| Release/deploy | `.loop/verify-gate.ps1 -Release`，再加 release／Pi runbook 證據；不由本文件代表 |

Browser e2e builds the current `prism-go-runtime.exe` (`scripts/build_go_runtime.ps1`), starts it on a free localhost port with a temporary data directory and fresh test DB, copies only Prompt/Wizard config fixtures, seeds its own notes, and terminates the process after the session. It never reads or writes the repository `knowledge.db`. `build_go_runtime.ps1` 在 `npm run build`、`go test` 或 `go build` 失敗時會中止並回傳非 0（2026-10-07 起），所以 e2e 不會跑在舊的 `frontend/dist` 上。
