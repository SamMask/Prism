# T053 — Test Disposition Plan（測試處置清單）

> 目的：定下 T053 刪除 Python backend source 時，每一個「依賴 Python」的測試該**轉 Go-golden / 刪除 / 保留並重接**。這是 boundary 文件第五節 Gate ② 的交付物。
> 性質：**決策清單，未刪除/修改任何測試**。實際動作在 T053 執行時依本清單進行。
> 基準：`tests/` 全量分類（`git ls-files tests/test_*.py`，2026-06-13）。
> 分類法：`needs_py` = import `app`/`create_app`/`migrations`/`routes`/`db`/`config` 或用 `client`/`app_with_db` fixture；`runs_go` = `build_go_shadow_exe` / `observe_http_fixture` / Popen Go / 打 `/healthz`。

## 處置代碼

- **KEEP**：T053 後仍有效，不動。
- **REWIRE**：保留測試意圖，但把資料來源從 Python（`app`/`migrations`）改接到 Go runtime 或固化 schema。
- **GOLDEN**：parity 測試去掉 Python 對照組，保留 Go 觀測值改成 Go-golden 斷言。
- **DELETE**：隨 Python source 一起移除（前提：等價 Go 覆蓋已存在）。
- **DELETE\***：DELETE，但**刪前必須先確認** `go-shadow/main_test.go` 或 GO-ONLY 測試或新 e2e 驗收網已覆蓋同一行為（標出待確認項，不可盲刪）。

---

## A. PARITY — Python oracle + Go（13 檔，Python 對照組會在 T053 死亡）

> 這些測試的價值來自「Python vs Go diff」。Python 一刪，對照組消失。預設處置：**GOLDEN 或 DELETE\***。判斷規則：若該 route 行為已被 `go-shadow/main_test.go` 覆蓋 → DELETE\*；若覆蓋了 main_test.go 沒有的組合（DB/file 副作用 invariant）→ GOLDEN（保留 Go 那半邊）。

| 測試檔 | 涵蓋面 | 處置 | 刪/轉前須確認 |
|---|---|---|---|
| `test_go_primary_t004_t006_foundation.py` | route manifest + config/data-dir parity | DELETE\* | foundation 屬遷移期 scaffolding；manifest 由 governance 測試另行守 |
| `test_go_primary_t011_t012_notes.py` | notes read/search/create/update parity | GOLDEN | notes CRUD/FTS 是核心；保留 Go 半邊斷言，新 e2e net 已涵蓋 happy path |
| `test_go_primary_t013_notes_delete.py` | delete + image cleanup parity | GOLDEN | 刪除 + thumbnail companion 清理 invariant，main_test.go 須確認覆蓋 |
| `test_go_primary_t014_t015_notes_actions_batch.py` | pin/archive/duplicate/reorder/batch | DELETE\* | 確認 main_test.go 有 actions/batch 覆蓋 |
| `test_go_primary_t016_t017_history_categories.py` | history restore + categories | DELETE\* | 確認 main_test.go 覆蓋 history/category CUD |
| `test_go_primary_t018_tags.py` | tags update/delete/merge + NOCASE | DELETE\* | 確認 main_test.go 覆蓋 merge/NOCASE |
| `test_go_primary_t019_attachments_metadata.py` | attachment metadata list/create/delete | DELETE\* | 確認 main_test.go 覆蓋附件 metadata |
| `test_go_primary_t036_t038_static_security_workflow.py` | static 邊界 + security + full workflow | GOLDEN | full workflow 已由新 e2e net 接手；security 邊界保留 Go 半邊 |
| `test_phase18_go_shadow_contract.py` | Phase 18 shadow 契約 | DELETE | Phase 18 shadow 已被 Go primary 取代，歷史 scaffolding |
| `test_phase23_b_next_notes_write_bundle.py` | notes write bundle parity | DELETE\* | 與 t011-t015 重疊，確認無獨有覆蓋 |
| `test_phase23_go_attachment_text_read_implementation.py` | attachment text read parity | DELETE\* | 確認 main_test.go 覆蓋 text read |
| `test_phase23_go_category_update_write_implementation.py` | category update parity | DELETE\* | 與 t016/t017 重疊 |
| `test_phase23_go_first_write_route_implementation.py` | 首個 write route parity | DELETE | 遷移期里程碑 scaffolding |

> 註：分類器把新檔 `test_go_primary_e2e_pure_go_acceptance.py` 誤列入此組；它**無 Python import**（自帶 guard test 證明），實際屬 GO-ONLY → **KEEP**。

---

## B. PURE-PYTHON functional — 只測 Python backend（26 檔）

> 直接測 `app`/`routes`/`utils` 的功能。Python source 一刪即失效。預設 **DELETE\***（須確認 Go 側等價覆蓋），少數需 **REWIRE** 或本就是 **KEEP**。

| 測試檔 | 性質 | 處置 |
|---|---|---|
| `test_schema_regression.py` | fixture schema == 真實 migration 鏈（schema 真相） | **REWIRE** → 改以 Go fresh-init schema 為真相（Gate ③）；或保留 `migrations/__init__.py` 僅作 schema 來源 |
| `test_notes_crud.py` | Python notes CRUD | DELETE\*（Go 覆蓋：t011/main_test.go/e2e net） |
| `test_categories.py` | Python categories | DELETE\*（確認 Go category 覆蓋） |
| `test_tags.py` / `test_tags_filter.py` / `test_tags_merge.py` | Python tags | DELETE\*（確認 Go tags/merge 覆蓋） |
| `test_pagination.py` | Python 分頁 | DELETE\*（確認 Go `/api/notes` 分頁覆蓋） |
| `test_reorder.py` / `test_sql.py` | Python reorder/SQL | DELETE\* |
| `test_batch_delete_bug.py` / `test_batch_delete_images.py` / `test_batch_type_sync.py` | Python batch | DELETE\* |
| `test_cleanup.py` | Python media cleanup | DELETE\*（Go 覆蓋：t024-t027 GO-ONLY） |
| `test_export_markdown.py` | Python markdown export | DELETE\*（Go 覆蓋：t028-t031 GO-ONLY） |
| `test_separator.py` / `test_separator_auto.py` / `test_separator_simple.py` / `test_comma_tags.py` | Python 分離/逗號 tag | DELETE\*（確認 Go separation 覆蓋） |
| `test_system.py` | Python system（vacuum/wal/consistency） | DELETE\*（確認 Go system 覆蓋） |
| `test_server_backup_management.py` | Python backup 管理 | DELETE\*（Go 覆蓋：t032-t035 GO-ONLY） |
| `test_security_guards.py` / `test_upload_security.py` | Python 安全（CSRF/SSRF/magic） | DELETE\*（**高關注**：確認 Go T037 security parity 已覆蓋同等案例再刪） |
| `test_query_builder.py` | `utils/query_builder.py`（Python-only util） | DELETE（query_builder 隨 routes 一起死；Go 有自己的 query builder） |
| `test_phase18_api_golden.py` | Phase 18 Python API golden | DELETE（歷史 golden） |
| `test_phase19_go_read_routing.py` | legacy `go_read_routing` shadow proxy | DELETE（Phase 19 legacy，連同 `utils/go_read_routing.py`） |
| `test_phase23_go_thumbnail_parity_and_pillow_removal_gate.py` | import `routes`；pillow 移除 gate | DELETE\*（Go 已自有 thumbnail；確認無獨有 gate 斷言） |
| `test_go_primary_t046_t050_frontend_route_coverage.py` | frontend route coverage（讀 api.ts + 契約） | **KEEP**（實質是 governance/route-coverage，非 Python runtime；確認其不 import `app`） |

---

## C. GO-ONLY — 無 Python 依賴（9 檔）→ 全部 **KEEP**

> T053 後原封不動仍有效，是 Go 端的回歸主力。

```
test_go_primary_t008_fresh_db_init.py
test_go_primary_t009_t010_migrations.py
test_go_primary_t020_t023_files_uploads.py
test_go_primary_t024_t027_media_cleanup.py
test_go_primary_t028_t031_import_export.py
test_go_primary_t032_t035_server_system.py
test_go_primary_t039_t041_package_staging.py
test_phase19_go_readonly_soak_execution.py
test_phase19_go_runtime_packaging.py
```
＋新增 `test_go_primary_e2e_pure_go_acceptance.py`（純 Go 驗收網）。

---

## D. GOVERNANCE — 無 runtime，斷言 docs/contracts（56 檔）→ 預設 **KEEP**

> 測文件/契約一致性，與 Python runtime 無關，T053 後仍有效。但其中一部分斷言「retained-Python」字樣或 Python source 路徑，**Gate ④ 改文案時必須同步更新這些斷言**，否則文案一改它們就紅。

需在 ④ 一併處理（wording-coupled）的代表：
- `test_go_primary_t045_python_packaged_runtime_deletion.py`、`test_go_primary_t046_t053_audit_queue_planning.py`、`test_go_primary_t051_t052_current_truth_cleanup.py`
- `test_phase23_python_package_deletion_closure.py`、`test_phase23_python_removal_and_final_stabilization.py`、`test_phase23_python_runtime_ownership_closure.py`、`test_phase23_go_ownership_closure_audit.py`
- `test_todo_go_primary_runtime_plan.py`、`test_phase24_settings_home_maintenance_followups.py`

其餘 phase19/20/21/22/23 的 planning/decision/inventory 測試屬歷史治理，**KEEP**（可選：未來連同 contract 一起精簡，但非 T053 阻擋項，且不在本輪 scope）。

---

## 數量總結與 T053 執行順序

| 組別 | 檔數 | 主要處置 |
|---|---|---|
| A 之 PARITY | 13 | GOLDEN ×3、DELETE/DELETE\* ×10 |
| B 純 Python 功能 | 26 | DELETE\* ×23、REWIRE ×1（schema_regression）、KEEP ×1、DELETE ×1（query_builder） |
| C GO-ONLY | 9（+1 新） | 全 KEEP |
| D 治理 | 56 | KEEP（其中 ~9 隨 ④ 改斷言） |

**T053 內建議順序**：
1. 先 **REWIRE** `test_schema_regression.py` 把 schema 真相轉到 Go（Gate ③）——這是唯一「刪 Python 會掉 schema 守門」的點，須先補。
2. 確認每個 **DELETE\*** 的 Go 等價覆蓋（逐項勾 main_test.go / GO-ONLY / e2e net）。**未勾到的不刪**。
3. 對 3 個 **GOLDEN** 改寫成純 Go 斷言。
4. 才刪 Python source（`app.py`/`routes/`/`utils`{query_builder,search,image_tools,go_read_routing}/`db.py`/`config.py` 與 DELETE 組測試）。`migrations/__init__.py` 視步驟 1 決定保留與否。
5. **④** 更新 docs/API/release 文案，同步調整 D 組 wording-coupled 斷言。

> **紅線**：DELETE\* 在「Go 等價覆蓋未勾到」前一律不執行；schema_regression 在 REWIRE 完成前不刪。違反就是把驗收守門一起刪掉。
