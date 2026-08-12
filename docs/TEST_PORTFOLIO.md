# Prism Test Portfolio

> Baseline: 2026-08-12
> Current runtime: Go primary
> Inventory: 75 Python test modules / 396 collected tests, 83 Go test functions, 5 isolated browser smoke tests

本文件說明測試「在證明什麼」，避免把 source wording、歷史計畫或部署紀錄誤當成 current product behavior。模組以主要責任分類；同一模組可能同時覆蓋次要契約。

## Portfolio summary

| Category | Python modules | Main proof | Completion authority |
|---|---:|---|---|
| Behavior | 20 | 使用者流程、前端互動、i18n、搜尋、匯入、閱讀與產品優化 | targeted pytest + frontend build；關鍵流程再加 isolated browser smoke |
| Contract | 14 | Go API/DB/files/import-export/system、schema 與 pure-Go acceptance | functional pytest + `go test ./...` |
| Governance | 10 | TODO/HANDOFF/contract/review 邊界與任務選擇 | wording/source regression；不能單獨證明 runtime 完成 |
| Historical | 31 | Phase 19-23、desktop shell、舊 cutover/soak/release 證據仍可讀 | archive/read-back only；不能作 current product acceptance |

## Behavior

- Library/search: `test_command_palette_server_search.py`, `test_kwf02_saved_search_workspace.py`, `test_phase22_command_palette_entrypoint_reliability.py`, `test_phase22_home_search_empty_state_context_copy.py`, `test_starred_tag_filters.py`.
- Notes/content: `test_markdown_sanitization.py`, `test_note_delete_media_ux_copy.py`, `test_note_list_lightweight_payload.py`, `test_note_variant_lineage.py`, `test_reading_workspace.py`.
- Import/UI/i18n: `test_bulk_markdown_txt_import.py`, `test_default_category_i18n.py`, `test_frontend_i18n_settings.py`, `test_image_viewer_lightbox.py`, `test_kwf03_to_kwf07_workflow.py`.
- Product surfaces: `test_phase22_prompt_builder_mobile_action_bar.py`, `test_phase22_settings_tab_deep_linking.py`, `test_phase24_settings_home_maintenance_followups.py`, `test_project_optimization_p0_frontend.py`, `test_project_optimization_p1.py`.

這組仍包含不少 source-string assertions；它們適合防止入口或契約被移除，但不能取代瀏覽器行為。`e2e/test_note_flow.py` 因此固定驗收 Home 搜尋開啟、Prompt 直接載入、Prompt save-to-open 與 Data & Recovery 深連結。

## Contract

- Pure Go / DB: `test_go_primary_e2e_pure_go_acceptance.py`, `test_go_primary_t007_sqlite_owner.py`, `test_go_primary_t008_fresh_db_init.py`, `test_go_primary_t009_t010_migrations.py`.
- Files and data: `test_go_primary_t020_t023_files_uploads.py`, `test_go_primary_t024_t027_media_cleanup.py`, `test_go_primary_t028_t031_import_export.py`, `test_go_primary_t032_t035_server_system.py`.
- Packaging and ownership: `test_go_primary_t039_t041_package_staging.py`, `test_go_primary_t042_t044_live_cutover.py`, `test_go_primary_t045_python_packaged_runtime_deletion.py`, `test_go_primary_t046_t050_frontend_route_coverage.py`, `test_go_primary_t051_t052_current_truth_cleanup.py`.
- Schema: `test_schema_regression.py`.

Go handler/SQL correctness的第一層 owner 是 `go-shadow/*_test.go`；Python contract tests負責 artifact、跨層、文件與 isolated subprocess acceptance。兩層不可互相取代。

## Governance

- `test_codex_task_review_checklist.py`
- `test_go_primary_t046_t053_audit_queue_planning.py`
- `test_phase20_go_write_surface_contract_inventory.py`
- `test_phase21_post_push_product_frontend_selection.py`
- `test_phase22_product_frontend_backlog_intake.py`
- `test_phase22_product_frontend_next_selection.py`
- `test_phase23_go_db_only_write_expansion_selection.py`
- `test_phase23_go_write_surface_selection.py`
- `test_project_review_hygiene.py`
- `test_todo_go_primary_runtime_plan.py`

Governance assertions只鎖定範圍、狀態層級與下一入口。它們通過時，不代表 build、runtime、browser、deploy 或 Pi 已驗證。

## Historical

- Desktop/archive: `test_desktop_portable_followups.py`, `test_desktop_shell_phase0_spike.py`, `test_desktop_shell_phase1_3.py`, `test_desktop_shell_phase4_6.py`.
- Phase 19: all 14 `test_phase19_*.py` modules.
- Phase 20: `test_phase20_go_candidate_fixture_planning.py`, `test_phase20_go_post_polish_stabilization.py`, `test_phase20_go_post_readonly_scope_assessment.py`.
- Phase 21: `test_phase21_local_commit_push_readiness.py`.
- Phase 23: file-read plan, rollback proof, local smoke boundary, ownership audit, packaged candidate, Pi rollout, and the three Python deletion/ownership closure modules (9 total).

本輪移除兩個 feature tests 對 HANDOFF 句子「目前沒有未交付的 active construction item」的重複鎖定；該句與 feature behavior 無關，active queue 改變時不應讓 Search／Saved View 測試失敗。相關測試仍保留自己的 TODO、contract 與 Next Entry assertions。

## Required gates

| Change | Required checks |
|---|---|
| Frontend behavior | targeted pytest, `npm run build`, relevant isolated browser smoke |
| Go/API/SQL/files | targeted Go tests, `go test ./...`, `pytest tests/ -v` |
| Docs/governance only | targeted pytest, mirror check, `git diff --check` |
| Release/deploy | above gates plus explicit release/Pi runbook evidence; not implied by this portfolio |

Browser smoke builds the current `prism-go-runtime.exe`, starts it on a free localhost port with a temporary data directory and fresh test DB, copies only Prompt/Wizard config fixtures, seeds its own note, and terminates the process after the session. It never reads or writes the repository `knowledge.db`.
