# MVP Technical Audit Report

**日期**: 2025-12-11
**版本**: v1.0-Audit
**對象**: 專案管理員 / 架構師 / 全端開發者

---

## 1. [紅燈] 阻斷性問題 (Fatal Logic)

> **定義**: 必須立即修復，否則核心功能閉環破裂或資料將發生不可逆錯誤。

### 1-1. 分類系統的「雙重事實」分裂 (Data Split Brain)

- **現象**: 資料庫 (`Notes` table) 同時擁有 `type` (TEXT) 與 `category_id` (INTEGER) 欄位，但應用層與資料層脫節。
  - **資料庫層 (v1.0 Schema)**: 定義了 `category_id` FK 關聯 `Categories(id)`，並期望逐步取代 `type`。
  - **與遷移層 (Migrations)**: Migration v7 嘗試根據 `type` 回填 `category_id`。
  - **應用層 (CRUD)**: `routes/notes/crud.py` 的 `create_note` 與 `update_note` 函式 **完全忽略** `category_id`。
- **後果**:
  - 任何在 Migration v7 之後透過 API 新增的筆記，其 `category_id` 均為 `NULL`。
  - 前端若未來改用 `category_id` 進行關聯查詢，將找不到這些新筆記。
  - `routes/categories.py` 在更新分類名稱時，僅同步更新 `Notes.type`，導致 `category_id` 成為「死欄位 (Dead Column)」，完全失去 Foreign Key 的約束與參照意義。
- **修復建議**:
  1.  **短期 (MVP Hotfix)**: 在 `routes/notes/crud.py` 中，寫入 `type` 時同步查詢並寫入 `category_id`。
  2.  **長期**: 廢棄 `Notes.type`，全面改用 `category_id` 作為唯一關聯依據。

### 1-2. 遷移系統的潛在競態 (Migration Race Condition)

- **現象**: `app.py` 的 `init_db()` 函式中包含了完整的 `CREATE TABLE` 邏輯 (含 v1.0 最新欄位)，同時又會在啟動時呼叫 `migrations.run_migrations()`。
- **風險**:
  - 對於全新安裝，`init_db` 建立了包含 `category_id` 的表。`run_migrations` 隨後執行，偵測到欄位已存在 (透過 `_detect_existing_schema` 或 `duplicate column` 錯誤)，這部分邏輯尚屬健壯。
  - 但在 `init_db` 與 `SCHEMA.md` 的同步維護上存在巨大的人為失誤風險。如果開發者修改了 `SCHEMA.md` 或 Migrations 但忘記同步更新 `app.py` 中的巨大 SQL 字串，會導致新裝用戶與舊用戶資料庫結構不一致。
- **建議**: `app.py` 應只負責建立最基礎的空表或 Schema Version 0，其餘所有結構變更（包括初始建表）應全權交由 `migrations` 系統負責，確保「單一真實來源 (Single Source of Truth)」。

---

## 2. [黃燈] 風險與債務 (Structural Risks)

> **定義**: MVP 可暫時上線，但屬於技術債，需排程改善。

### 2-1. API 安全性配置缺失

- **Secret Key**: `config.py` 與 `app.py` 中均未顯式設定 `SECRET_KEY`。雖然目前未大量使用 Flask Session，但一旦引入 Flash 訊息或擴充 Extension，將引發運行時錯誤或安全風險。
- **Debug Mode**: 生產環境切換依賴 `FLASK_DEBUG` 環境變數。建議在程式啟動時明確輸出當前運行的 Config Class 名稱，避免在不知情下以 Debug 模式運行生產服務。

### 2-2. 模組邊界的一致性

- **Export 邏輯分散**: 存在 `routes/export.py` 與 `routes/notes/export.py` (雖然 `routes/notes/__init__.py` 引入了它，但 `routes/__init__.py` 又註冊了全域的 `export_bp`)。
  - 需確認這兩者是否功能重疊或命名混淆。如果是不同層級的匯出（全站 vs 筆記），應在命名上區隔（如 `GlobalExport` vs `NoteExport`）。

### 2-3. 資料流過度依賴字串匹配

- **分類關聯**: 目前分類刪除 (`routes/categories.py`) 依賴前端傳入 `target_category` 名稱字串。若前端傳入錯字，將導致筆記分類遷移失敗或資料錯亂。應全面改用 API 傳遞 ID。

---

## 3. 架構修正建議 (Architectural Proposals)

### 3-1. 統一資料庫關聯 (針對 1-1 問題)

**現狀 (Pseudo Code)**:

```python
# routes/notes/crud.py
def create_note():
    type_name = request.json.get('type')
    # 只存了 type，category_id 變為 NULL
    db.execute("INSERT INTO Notes (type) VALUES (?)", type_name)
```

**修正方案 (MVP Compatible)**:

```python
# routes/notes/crud.py - Helper Function
def get_category_id_by_name(db, name):
    row = db.execute("SELECT id FROM Categories WHERE name = ?", (name,)).fetchone()
    if row: return row['id']
    # Fallback to default if not found
    return db.execute("SELECT id FROM Categories WHERE is_default = 1").fetchone()['id']

# create_note
def create_note():
    type_name = request.json.get('type')
    category_id = get_category_id_by_name(db, type_name)

    db.execute(
        "INSERT INTO Notes (type, category_id) VALUES (?, ?)",
        (type_name, category_id)
    )
```

### 3-2. 瘦身 `app.py` 初始化邏輯

將 `init_db` 中的 SQL 字串全部移出，僅保留：

1. `Schema_Meta` 表的建立。
2. 呼叫 `migrations.run_migrations(db)`。
   這樣可以保證所有 Schema 定義都在 `migrations/` 目錄中管理。

---

## 4. 數據結構與 MVP 檢核

| 項目              | 狀態      | 說明                                                               |
| :---------------- | :-------- | :----------------------------------------------------------------- |
| **Schema 完整性** | ⚠️ 黃燈   | Notes 表欄位冗餘 (`type` vs `category_id`)，需在應用層手動同步。   |
| **核心功能閉環**  | ✅ 綠燈   | CRUD、搜尋、分類、標籤、匯出、Wizard 功能代碼均已就位。            |
| **SQL Injection** | ✅ 綠燈   | 全面使用參數化查詢 (`?`)，FTS5 搜尋有做字元過濾。                  |
| **XSS 防護**      | ✅ 綠燈   | 前端使用 Vue.js 自動跳脫，且引入了 DOMPurify (見 `index.html`)。   |
| **MVP 準備度**    | 🟡 待修正 | 必須先修復 **1-1 分類資料一致性** 問題才能發布，否則會產生髒資料。 |
