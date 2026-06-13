# T053 — Python Source / Dependency Inventory 與 Deletion Boundary Proof

> 目的：在執行 T053（最終封存/刪除 Python backend source）**之前**，用證據盤點所有 Python source、建立依賴閉包，並劃出可刪 / 必留 / 待確認的刪除邊界。
> 性質：**純分析，未刪除/搬移/修改任何檔案**。本檔是 T053 的施工前 guardrail，不是 T053 的執行本身。
> 日期：2026-06-13　基準：`git ls-files '*.py'`（排除 `venv/`、`__pycache__/`）
> 對應 guardrail（CLAUDE.md 白話）：「開始前先確認哪些 Python 檔案仍被 pytest、parity fixture、migration history 或 rollback evidence 需要，不能因為『看起來舊』就刪。」

---

## 一、方法（刪除邊界如何被證明）

刪除邊界不靠檔名臆測，靠 **import 消費邊 + pytest 收集範圍**：

1. **pytest 收集範圍**：`pytest.ini` → `testpaths = tests`。只有 `tests/` 被收集；`e2e/`、`tools/`、`scripts/` 不在綠燈閉包內。
2. **驗收入口**：`tests/conftest.py:28` → `from app import create_app`；`tests/conftest.py:146` → `from migrations import run_migrations`。任何使用 `client` / `app_with_db` / `temp_db` fixture 的測試，**transitively** 需要整條 Python stack。
3. **消費邊**：對每個 production 模組（app / config / db / routes / utils / migrations / services）grep 出「誰 import 它」。零消費者 = 死碼，可刪；有消費者且在 pytest 閉包內 = 必留到驗收網建立。

---

## 二、Source Inventory 總表

### 2.1 Production backend source（retained-Python 主體）

| 模組 | 檔案 | 消費者（證據） | 分級 |
|---|---|---|---|
| App 工廠 | `app.py` | `tests/conftest.py` + 34 個功能/parity 測試 `from app import create_app` | **B（必留）** |
| 設定 | `config.py` | `app.py:12 from config import config` | **B（必留）** |
| DB owner | `db.py` | `app.py` + 13 個 `routes/*`（`get_db`） | **B（必留）** |
| Flask routes | `routes/`（17 檔：`__init__`、`attachments`、`categories`、`cleanup`、`export`、`helpers`、`prompt_options`、`server`、`system`、`tags`、`upload`、`wizard_options`、`notes/{__init__,actions,batch,crud,export,history,import_}`） | `app.py` 註冊 blueprint；全部用 `db.py` | **B（必留）** |
| Migration chain | `migrations/__init__.py`（內聯 `MIGRATIONS` v1→16、`run_migrations`、`get_migration_status`） | `tests/conftest.py:146`、`scripts/apply_migrations.py`、多個 schema/parity 測試 | **B（必留）** |
| Utils（live） | `utils/query_builder.py`、`utils/search.py`、`utils/image_tools.py`、`utils/go_read_routing.py`、`utils/__init__.py` | `routes/notes/crud.py`、`routes/notes/import_.py`、`routes/upload.py`、`routes/system.py`、`app.py`、`tests/test_query_builder.py`、`tests/test_phase19_go_read_routing.py` | **B（必留）** |

### 2.2 測試 harness（驗收基礎設施）

| 檔案 | 角色 | 分級 |
|---|---|---|
| `conftest.py`（root） | （root-level，pytest rootdir） | **B（必留）** |
| `tests/conftest.py` | Flask test client + temp_db（真實 migration chain） fixtures | **B（必留）** |
| `tests/go_primary_parity_harness.py` | parity 比對引擎：`observe_flask_fixture`（Python 對照）+ `observe_http_fixture`（Go）+ `build_go_shadow_exe` | **B（必留，且為 Go parity 的 Python oracle）** |
| `tests/test_*.py`（功能 + parity，約 70 檔） | 見第三節閉包 | **B（必留）** |

### 2.3 死碼 / 零消費者（可刪，已證明無 importer）

| 檔案 | 證明 | 分級 |
|---|---|---|
| `services/`（`__init__.py`，4 行 docstring，無實體程式） | `grep "from services|import services"` 於 `app.py routes/ utils/ migrations/` → **NONE** | **A（可刪，空 namespace）** |
| `scripts/read_007.py`、`read_garbage.py`、`read_new_garbage.py`、`dump_files.py`、`read_files_tool.py`、`deep_clean.py`、`debug_pytest.py` | 對全部 tracked `.py` grep import → 每個皆 **零引用**（一次性 dev 雜物） | **A（可刪）** |

### 2.4 死碼但具歷史價值（封存優先，非載入相依）

| 檔案 | 狀態 | 分級 |
|---|---|---|
| `migrations/add_notes_pinned.py`、`migrations/add_prompt_params.py` | v1.x 時代 standalone 腳本（檔頭寫「執行方式：python migrations/add_xxx.py」）；**不在** `run_migrations` 鏈（該鏈已內聯於 `migrations/__init__.py` 的 `MIGRATIONS`）。grep 確認無 importer。 | **C（封存到 development-history；非載入相依，但屬 migration 歷史）** |

### 2.5 證據腳本（依 guardrail 必須保留）

| 檔案 | 角色 | 分級 |
|---|---|---|
| `scripts/python_live_workflow_smoke.py` | T043 rollback drill 證據（Python runtime stats/create/upload/search/export/backup/migration/delete workflow） | **C（保留為 rollback evidence）** |
| `scripts/go_primary_full_workflow_smoke.py` | Go-side HTTP full workflow smoke（非 Python source） | **保留（Go 側，與 T053 無關）** |

### 2.6 待人工確認（D）

| 檔案 / 目錄 | 為何不確定 | 分級 |
|---|---|---|
| `e2e/`（`conftest.py`、`test_note_flow.py`、`__init__.py`） | **不在** `pytest.ini testpaths`，pytest 不收集；可能由 Playwright/獨立 CI 跑。刪前需確認 CI 流程。 | **D** |
| `tools/create_demo_db.py`、`tools/extract_components.py` | 一次性產生器，零測試引用，但可能仍供手動使用。 | **D** |
| `scripts/apply_migrations.py`、`init_db_manual.py`、`check_schema.py`、`migrate_theme_colors.py`、`clean_test_data.py`、`download_fonts.py`、`run_tests.py` | dev 工具；部分 import `app`/`config`/`db`/`migrations`（會隨 2.1 一起壞）。屬「與 source 同生共死」的維運腳本。 | **D（隨 2.1 一併決策）** |

---

## 三、Retained-Python 依賴閉包證明（為什麼 2.1/2.2 必須留到 T053 後）

```
tests/conftest.py
  ├─ from app import create_app ────────► app.py
  │                                         ├─ from config import config ──► config.py
  │                                         ├─ register blueprints ────────► routes/* (17)
  │                                         │                                  └─ get_db ──► db.py
  │                                         │                                  └─ utils.{query_builder,search,image_tools,go_read_routing}
  │                                         └─ utils.go_read_routing
  └─ from migrations import run_migrations ► migrations/__init__.py (MIGRATIONS v1→16)

tests/go_primary_parity_harness.py
  └─ observe_flask_fixture(client, ...) ──► 同一條 app.py 閉包（作為 Go 的 Python 對照 oracle）
```

- **34** 個測試檔直接使用 `client` / `app` fixture（功能性 Python 測試）。
- **23** 個測試檔透過 harness 實際 build + run Go，並以 **Flask client 作為 Python 對照組**。
- 因此 2.1 + 2.2 是 `test_run.log`（525 passed）與全部 Go parity 的共同地基。

> **關鍵結論**：直接刪除 2.1 的閉包，會同時 (a) 讓 34 個功能測試無法 import、(b) 抽掉 23 個 parity 測試的 Python oracle。**驗收鏈會瞬間歸零**，這正是審查報告 P1 風險的具體展開。

---

## 四、Deletion Boundary（刪除邊界，分級總結）

| 分級 | 內容 | 何時可動 | 風險 |
|---|---|---|---|
| **A 立即可刪（零相依）** | `services/`、`scripts/{read_007,read_garbage,read_new_garbage,dump_files,read_files_tool,deep_clean,debug_pytest}.py` | **現在即可**（與 T053 解耦，不影響任何測試） | 低；已證明零 importer |
| **B 必留到「純 Go 驗收網」建立後** | `app.py`、`config.py`、`db.py`、`routes/`、`migrations/__init__.py`、`utils/{query_builder,search,image_tools,go_read_routing}.py`、`conftest.py`、`tests/conftest.py`、`tests/go_primary_parity_harness.py` 與 2.2 測試 | **不得在前置 gate 滿足前刪**（見第五節） | **高**：誤刪＝驗收鏈斷 |
| **C 封存 / 保留為證據** | `migrations/add_notes_pinned.py`、`add_prompt_params.py`（→ development-history）；`scripts/python_live_workflow_smoke.py`（rollback evidence，原地保留或隨封存說明） | T053 封存階段 | 低；非載入相依 |
| **D 人工確認後再決策** | `e2e/`、`tools/`、`scripts/{apply_migrations,init_db_manual,check_schema,migrate_theme_colors,clean_test_data,download_fonts,run_tests}.py` | T053；逐一確認 CI / 手動用途 | 中；憑名字刪有誤刪維運腳本之虞 |

---

## 五、T053 安全執行前置 Gate（依賴本檔的結論）

T053 對 **B 級閉包**的刪除，必須先滿足以下前置條件（與審查報告 P1 一致）：

1. **建立純 Go 端對端驗收網**：一組不依賴 Flask 對照組、直接打 Go HTTP 的 pytest（或固化 parity 的 Go golden），覆蓋 create/upload/search/separate/export/import/delete/backup/migration。
2. **重接驗收入口**：`tests/conftest.py` 的 `client` / `temp_db` fixture 不再 `from app import` / `from migrations import`，改以 Go runtime 或固化 schema 為基準。
3. **migration 來源轉移**：確認 schema regression 測試的真實 migration 來源從 `migrations/__init__.py` 轉到 Go migration runner（或保留 `migrations/__init__.py` 為唯一 schema 真相而僅刪 routes/app）。
4. **docs/API/release 文案收斂**：README 測試警語（已過期，`conftest.py` 早已走真實 migration）、`routes/system.py` 的 `go_read_routing` 殘留、專案結構 Python 主體敘述一併處理。

> **可立即進行（無需等 gate）**：A 級刪除（`services/` 與 7 個 read_*/dump/debug 腳本）。這是 T053 範圍內唯一現在就零風險的動作。

---

## 六、證據錨點（可重現）

```
pytest 收集範圍：              pytest.ini → testpaths = tests
app 閉包入口：                 tests/conftest.py:28 (from app import create_app)
migration 入口：               tests/conftest.py:146 (from migrations import run_migrations)
migration 鏈位置：             migrations/__init__.py:25 (MIGRATIONS), :272 (run_migrations)
db.py 消費者：                 app.py + routes/{attachments,categories,cleanup,export,server,system,tags,notes/*}
utils 存活證明：               query_builder→crud/test；search→crud；image_tools→import_/upload；go_read_routing→app/system/test
services 死碼證明：            grep "from services|import services" app.py routes/ utils/ migrations/ → NONE
死腳本證明：                   read_007/read_garbage/read_new_garbage/dump_files/read_files_tool/deep_clean/debug_pytest → 零 import
standalone migration 死碼證明： add_notes_pinned/add_prompt_params 不在 run_migrations 鏈、無 importer
驗收現況：                     test_run.log = 525 PASSED / 0 FAILED / 0 SKIPPED (2026-06-13 13:08)；go test ./... = ok
```

---

## 七、一句話總結

> **現在唯一能安全動的是 A 級死碼（`services/` + 7 個一次性腳本）。B 級 Python 閉包是 525 個 pytest 與 23 個 Go parity 的共同地基，刪它之前必須先有一張不依賴 Python 的純 Go 驗收網——否則 T053 不是收尾，是把驗收鏈一起刪掉。**
