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

---

## E. Go 覆蓋驗證（`go-shadow/main_test.go` 實查，2026-06-13）

> 對每個行為查 `main_test.go` 是否真有打該 HTTP 路徑的斷言（path-literal 實查，非關鍵字計數）。`main_test.go` 共 49 個測試。

| 行為 | Go unit 覆蓋（main_test.go path-literal） | 結論 |
|---|---|---|
| notes create/update/FTS/search/delete | ✅ `TestNotesCreateAndUpdate...` / `TestNotesSearch...` / `TestNotesDeleteCleansImagesFTS...` | DELETE\*/GOLDEN 可行 |
| separation `check_separation` / `separate` / `restore` | ✅ `/restore`×2、`check_separation`×2、`TestLongContentSeparationAndRestoreHandlers` | 已覆蓋 |
| pagination `per_page` | ✅ ×6 | `test_pagination.py` DELETE\* 可行 |
| categories write | ✅ `TestCategoryWriteMode...` | 可行 |
| tags write | ✅ `TestTagWriteMode...` | 可行（但 **merge 除外**，見下） |
| attachments text/raw/write | ✅ `TestAttachmentTextRead...` / `TestAttachmentWrite...` | 可行 |
| upload / upload-url / thumbnail / SSRF | ✅ 多個 `TestUpload*` / `TestThumbnail*`（含 private host/redirect/invalid 拒絕） | 可行 |
| migrations / fresh init / rollback | ✅ `TestOpenRuntimeSQLite*` / `TestRunExistingDBMigrations...` | 可行 |
| **notes actions：`/pin` `/archive` `/duplicate` `reorder`** | ❌ **path-literal = 0** | **⚠️ 缺口** |
| **batch：`batch/type` `batch/tags`** | ❌ **path-literal = 0** | **⚠️ 缺口** |
| **`tags/merge`** | ❌ **path-literal = 0** | **⚠️ 缺口** |
| **notes history list/delete：`/history`** | ❌ **path-literal = 0**（`restore` 有、list/delete 無） | **⚠️ 缺口** |
| **CSRF（Origin/Referer）** | ❌ main_test.go = 0 | **⚠️ 缺口**（SSRF 有覆蓋，CSRF 無） |

### 修正後處置（覆蓋本檔 A/B 組的暫定值）

這些行為目前**只活在用 Python oracle 的 parity 測試裡**；盲刪 = 靜默漏測。改判為 **GOLDEN（保留 Go 半邊斷言）或先補 `main_test.go` Go unit test 再 DELETE**：

| 測試檔 | 原暫定 | **修正** | 原因 |
|---|---|---|---|
| `test_go_primary_t014_t015_notes_actions_batch.py` | DELETE\* | **GOLDEN / 先補 Go test** | pin/archive/duplicate/reorder/batch Go unit 零覆蓋 |
| `test_go_primary_t016_t017_history_categories.py` | DELETE\* | **GOLDEN（history 半邊）** | history list/delete Go unit 零覆蓋（categories 已覆蓋） |
| `test_go_primary_t018_tags.py` | DELETE\* | **GOLDEN（merge 半邊）** | tags merge Go unit 零覆蓋 |
| `test_security_guards.py` | DELETE\* | **DELETE\*-blocked** | CSRF Go 覆蓋未證實，補 Go CSRF test 或確認 Go 行為前不刪 |

> **本驗證的價值**：證明「一口氣刪掉所有 parity + 純 Python 測試」會靜默掉 notes actions / batch / tags-merge / history / CSRF 的覆蓋。這正是紅線存在的理由——T053 執行時，上述四檔**不可**走 plain DELETE。

### 更新（2026-06-13，缺口處理結果）

**4/5 缺口已用真 Go unit test 補上**（commit `22d608d`，`go-shadow/main_test.go`，`go test ./...` ok，53 tests）：

| 缺口 | 新增 Go 測試 | 狀態 |
|---|---|---|
| notes actions（pin/archive/duplicate/reorder） | `TestNotesPinArchiveDuplicateReorderHandlers` | ✅ 已補 |
| batch（type/tags） | `TestNotesBatchTypeAndTagsHandlers` | ✅ 已補 |
| tags/merge | `TestTagsMergeHandlerTransfersNotesAndDeletesSourceTags` | ✅ 已補 |
| history list/delete | `TestNotesHistoryListAndDeleteHandlers` | ✅ 已補 |

→ 因此 `test_go_primary_t014_t015`、`t016_t017`、`t018` 的處置**從 GOLDEN 改回可 DELETE**：行為已由上述 Go 測試獨立守門，T053 刪 Python oracle 不再掉覆蓋。

**第 5 項 CSRF 升級為已確認的產品級缺口（非測試缺口）：**

`go-shadow/main.go` 實查確認 **Go primary 完全沒有 CSRF / Origin / Referer 入站驗證**：唯一 middleware 是 `logRequests`（純記錄，main.go:228），唯一 `Referer` 是 SSRF 抓圖的**出站**標頭（main.go:4868）。但 `README.md` §安全與隱私仍宣稱「✅ CSRF 防護：驗證 Origin / Referer」。

- 這是 **Python → Go 的安全 parity 退化**，不是 `test_security_guards.py` 寫不寫的問題——對應功能在 live runtime 不存在。
- `test_security_guards.py` 的 SSRF（`TestUploadURLRejects*`）與 server-localhost-only（main.go:1588 403 guard）兩部分 **Go 已覆蓋**；唯獨 CSRF 部分 Go 無對應。
- **需要決策（使用者層級，不該我擅自決定）**：
  - (a) 在 Go 補入站 Origin/Referer 驗證 middleware（恢復 parity，但屬 live runtime 行為變更，須評估是否誤擋合法 client）；或
  - (b) 接受無 CSRF 的現況（定位為 trusted LAN/VPN + reverse-proxy auth），並把 README 的 CSRF 宣稱改為實話。
- 在 (a)/(b) 拍板前，`test_security_guards.py` 維持 **DELETE\*-blocked**，不刪。

> 修正後紅線剩一條：**CSRF 決策（implement 或 honest-doc）未定前，`test_security_guards.py` 不刪、README CSRF 宣稱不視為已驗證。** 其餘四缺口已關閉。

### 更新（2026-06-13，CSRF 決策＝(a) implement，已完成）

使用者選 (a)：**在 Go 補入站 Origin/Referer CSRF 驗證**。已完成（commit `885a6f9`）：

- `go-shadow/main.go` 新增 `csrfProtect` middleware（`logRequests(csrfProtect(mux))`），對 POST/PUT/DELETE 比照 Flask `csrf_protect`：有 Origin/Referer 必須同源（host http/https、localhost↔127 互換、Vite 5173/5174），否則 403；無 Origin/Referer（curl/MCP/agent，無法被瀏覽器 CSRF）放行——保住 headless-KMS API 與所有 HTTP harness。
- 新增 `TestCSRFProtectMiddleware`（same-origin / swap / cross-origin / anonymous / safe-method / referer / vite 八案）。
- 驗收：`go test ./...` ok（54 tests）、完整 `pytest` 527 passed。
- **5/5 缺口全關閉。** `test_security_guards.py` 解除 DELETE\*-blocked：Go 現已覆蓋 SSRF（`TestUploadURLRejects*`）＋ localhost-only（main.go 403 guard）＋ CSRF（`TestCSRFProtectMiddleware`）三部分，T053 可走 DELETE。README §安全的「✅ CSRF 防護：驗證 Origin/Referer」宣稱重新成立。

> **紅線已全部解除。** T053 剩餘前置：③ `schema_regression` REWIRE 到 Go schema 真相；之後即可進行物理刪除 + ④ 文案。

