# Local Insight - SCHEMA v1.0 架構重構計劃

**版本**: v1.0.0  
**日期**: 2025-12-09  
**狀態**: ✅ 已完成  
**審查**: Linus 風格架構審查

---

## 📋 目錄

1. [重構目標與原則](#1-重構目標與原則)
2. [版本化遷移系統](#2-版本化遷移系統)
3. [資料表結構變更](#3-資料表結構變更)
4. [API 查詢重構](#4-api-查詢重構)
5. [後端模組拆分](#5-後端模組拆分)
6. [遷移執行計劃](#6-遷移執行計劃)
7. [風險評估與回滾方案](#7-風險評估與回滾方案)

---

## 1. 重構目標與原則

### 1.1 核心問題 (從 v0.x 識別)

| 問題編號 | 問題描述                                            | 嚴重度 | 現狀                  |
| -------- | --------------------------------------------------- | ------ | --------------------- |
| P-01     | 遷移邏輯為 if 分支堆疊，每版本加一個                | 🔴 高  | `app.py` 134-163 行   |
| P-02     | 標籤查詢使用 `GROUP_CONCAT(id:name, '\|\|')` 序列化 | 🔴 高  | `notes.py` 128-134 行 |
| P-03     | `Notes.type` 與 `Categories.name` 是兩個真相來源    | 🟡 中  | 需同步更新            |
| P-04     | `notes.py` 1,040 行，職責過重                       | 🟡 中  | 13 個 API 端點        |
| P-05     | 防禦性 try/except 處理欄位不存在                    | 🟢 低  | 遷移不可靠的症狀      |

### 1.2 重構原則

> "消除邊界情況永遠優於增加條件判斷" - Linus Torvalds

1. **聲明式優於命令式** - 遷移腳本應該是資料，不是邏輯
2. **單一真相來源** - 消除 `Notes.type` 與 `Categories` 的重複
3. **SQL 負責取資料，應用層負責格式化** - 移除 SQL 中的序列化
4. **小檔案、單一職責** - 每個模組 < 300 行

### 1.3 向後相容承諾 ⚠️

> "Never break userspace"

- 現有 API 介面保持不變
- 現有資料零損失
- 遷移失敗可回滾
- 前端無感知升級

---

## 2. 版本化遷移系統

### 2.1 新增 Schema_Meta 表

```sql
CREATE TABLE IF NOT EXISTS Schema_Meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 初始化版本
INSERT OR IGNORE INTO Schema_Meta (key, value) VALUES ('schema_version', '0');
```

### 2.2 遷移腳本結構

```
migrations/
├── __init__.py          # 遷移執行器
├── v001_add_is_pinned.py
├── v002_add_cover_position.py
├── v003_add_editor_layout.py
├── v004_add_is_archived.py
├── v005_add_sort_order.py
├── v006_add_category_id.py    # 新增：FK 關聯
└── v007_remove_type_column.py # 新增：移除冗餘欄位
```

### 2.3 遷移執行器 (`migrations/__init__.py`)

```python
"""
版本化遷移系統
消除 if 分支堆疊，改用聲明式遷移
"""

MIGRATIONS = [
    # (版本號, 遷移描述, SQL 語句列表)
    (1, "add_is_pinned", [
        "ALTER TABLE Notes ADD COLUMN is_pinned INTEGER DEFAULT 0",
    ]),
    (2, "add_cover_position", [
        "ALTER TABLE Notes ADD COLUMN cover_position TEXT DEFAULT 'top'",
    ]),
    (3, "add_editor_layout", [
        "ALTER TABLE Notes ADD COLUMN editor_layout TEXT DEFAULT 'single'",
    ]),
    (4, "add_is_archived", [
        "ALTER TABLE Notes ADD COLUMN is_archived INTEGER DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_notes_is_archived ON Notes(is_archived)",
    ]),
    (5, "add_sort_order", [
        "ALTER TABLE Notes ADD COLUMN sort_order INTEGER DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_notes_sort_order ON Notes(sort_order)",
        "UPDATE Notes SET sort_order = id WHERE sort_order = 0",
    ]),
    (6, "add_category_id", [
        # 新增 FK，但保留 type 欄位作為過渡
        "ALTER TABLE Notes ADD COLUMN category_id INTEGER REFERENCES Categories(id)",
        "CREATE INDEX IF NOT EXISTS idx_notes_category_id ON Notes(category_id)",
        # 根據現有 type 值填充 category_id
        """
        UPDATE Notes SET category_id = (
            SELECT id FROM Categories WHERE name = Notes.type
        ) WHERE category_id IS NULL
        """,
    ]),
    # v007 暫不實作，等 v1.0 穩定後再移除 type 欄位
]


def get_current_version(db):
    """取得當前 schema 版本"""
    try:
        row = db.execute(
            "SELECT value FROM Schema_Meta WHERE key = 'schema_version'"
        ).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        # Schema_Meta 表不存在
        return 0


def run_migrations(db):
    """執行所有待處理的遷移"""
    # 確保 Schema_Meta 表存在
    db.execute("""
        CREATE TABLE IF NOT EXISTS Schema_Meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    db.execute(
        "INSERT OR IGNORE INTO Schema_Meta (key, value) VALUES ('schema_version', '0')"
    )

    current = get_current_version(db)

    for version, name, statements in MIGRATIONS:
        if version > current:
            print(f"[Migration] v{version:03d}: {name}")
            try:
                for sql in statements:
                    db.execute(sql)
                db.execute(
                    "UPDATE Schema_Meta SET value = ? WHERE key = 'schema_version'",
                    (str(version),)
                )
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[Migration] v{version:03d} FAILED: {e}")
                raise

    final = get_current_version(db)
    if final > current:
        print(f"[Migration] 完成！版本 {current} → {final}")
```

### 2.4 app.py 變更

**移除** (舊版 134-163 行):

```python
# 自動遷移：確保 is_pinned 欄位存在 (v0.6.6)
if 'is_pinned' not in columns:
    ...
# 自動遷移：確保 cover_position 欄位存在 (v0.8.4)
if 'cover_position' not in columns:
    ...
# ... 更多 if 分支
```

**新增**:

```python
from migrations import run_migrations

def init_db():
    db = get_db()
    # ... 建表邏輯保持不變 ...

    # 執行版本化遷移 (取代所有 if 分支)
    run_migrations(db)
```

---

## 3. 資料表結構變更

### 3.1 Notes 表 v1.0

| 欄位名           | v0.x 狀態 | v1.0 變更 | 說明                        |
| ---------------- | --------- | --------- | --------------------------- |
| `id`             | ✓         | 保留      | -                           |
| `title`          | ✓         | 保留      | -                           |
| `content`        | ✓         | 保留      | -                           |
| `type`           | ✓         | **棄用**  | 遷移後由 `category_id` 取代 |
| `category_id`    | ✗         | **新增**  | FK → Categories(id)         |
| `remarks`        | ✓         | 保留      | -                           |
| `cover_image`    | ✓         | 保留      | -                           |
| `cover_position` | ✓         | 保留      | -                           |
| `editor_layout`  | ✓         | 保留      | -                           |
| `is_pinned`      | ✓         | 保留      | -                           |
| `is_archived`    | ✓         | 保留      | -                           |
| `sort_order`     | ✓         | 保留      | -                           |
| `prompt_params`  | ✓         | 保留      | -                           |
| `created_at`     | ✓         | 保留      | -                           |
| `updated_at`     | ✓         | 保留      | -                           |

### 3.2 遷移策略：type → category_id

**三階段遷移**:

```
Phase A: 新增 category_id，保留 type (向後相容)
         ↓
Phase B: 程式碼改用 category_id，type 唯讀
         ↓
Phase C: 移除 type 欄位 (v1.1 或更晚)
```

**Phase A SQL**:

```sql
-- v006 遷移
ALTER TABLE Notes ADD COLUMN category_id INTEGER REFERENCES Categories(id);
CREATE INDEX IF NOT EXISTS idx_notes_category_id ON Notes(category_id);

-- 填充 category_id (根據現有 type 值)
UPDATE Notes SET category_id = (
    SELECT id FROM Categories WHERE name = Notes.type
) WHERE category_id IS NULL;

-- 為沒有匹配分類的筆記設定預設分類
UPDATE Notes SET category_id = (
    SELECT id FROM Categories WHERE is_default = 1 LIMIT 1
) WHERE category_id IS NULL;
```

### 3.3 新增 Schema_Meta 表

```sql
CREATE TABLE IF NOT EXISTS Schema_Meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

| key                 | 說明                |
| ------------------- | ------------------- |
| `schema_version`    | 當前 schema 版本號  |
| `last_migration_at` | 最後遷移時間 (可選) |

---

## 4. API 查詢重構

### 4.1 標籤查詢問題

**v0.x 現狀** (`notes.py` 128-134):

```sql
(SELECT GROUP_CONCAT(t2.id || ':' || t2.name, '||')
 FROM Note_Tags nt2
 JOIN Tags t2 ON nt2.tag_id = t2.id
 WHERE nt2.note_id = n.id) as tags
```

**問題**:

- 標籤名稱含 `||` 或 `:` 會破壞解析
- SQL 負責序列化違反職責分離
- 無法使用 SQLite JSON 函數的優勢

### 4.2 方案評估

| 方案                      | 優點           | 缺點            | 推薦 |
| ------------------------- | -------------- | --------------- | ---- |
| **A: 應用層 JOIN**        | 完全控制格式   | 多一次查詢      | 🟡   |
| **B: json_group_array()** | 標準 JSON 輸出 | 需 SQLite 3.38+ | ✅   |
| **C: 保持現狀 + 跳脫**    | 改動最小       | 治標不治本      | ❌   |

### 4.3 v1.0 實作：json_group_array()

**新查詢**:

```sql
SELECT
    n.id,
    n.title,
    n.content,
    c.name as type,  -- 從 Categories JOIN 取得
    c.icon as type_icon,
    n.remarks,
    n.cover_image,
    COALESCE(n.cover_position, 'top') as cover_position,
    COALESCE(n.editor_layout, 'single') as editor_layout,
    COALESCE(n.is_pinned, 0) as is_pinned,
    n.created_at,
    n.updated_at,
    -- v1.0: 使用 JSON 函數
    (SELECT json_group_array(json_object('id', t.id, 'name', t.name))
     FROM Note_Tags nt
     JOIN Tags t ON nt.tag_id = t.id
     WHERE nt.note_id = n.id) as tags_json,
    (SELECT json_group_array(s.url)
     FROM Source_Urls s
     WHERE s.note_id = n.id) as urls_json
FROM Notes n
LEFT JOIN Categories c ON n.category_id = c.id
WHERE ...
```

**後端處理**:

```python
import json

# v1.0: 直接解析 JSON，無需手動 split
tags = json.loads(row['tags_json']) if row['tags_json'] else []
urls = json.loads(row['urls_json']) if row['urls_json'] else []
```

### 4.4 SQLite 版本檢查

```python
def check_sqlite_version():
    """確認 SQLite 版本支援 json_group_array"""
    import sqlite3
    version = sqlite3.sqlite_version_info
    # json_group_array 從 SQLite 3.38.0 開始穩定
    if version < (3, 38, 0):
        print(f"[WARNING] SQLite {sqlite3.sqlite_version} 可能不支援 json_group_array")
        return False
    return True
```

---

## 5. 後端模組拆分

### 5.1 現狀分析

**`routes/notes.py`** (1,040 行, 13 端點):

| 端點                             | 行數(約) | 職責     |
| -------------------------------- | -------- | -------- |
| `GET /notes`                     | 175      | 列表查詢 |
| `GET /notes/<id>`                | 80       | 單筆詳情 |
| `POST /notes`                    | 70       | 新增     |
| `PUT /notes/<id>`                | 90       | 更新     |
| `DELETE /notes/<id>`             | 25       | 刪除     |
| `POST /notes/<id>/pin`           | 50       | 釘選     |
| `POST /notes/<id>/archive`       | 50       | 封存     |
| `GET /notes/<id>/history`        | 45       | 歷史列表 |
| `POST /notes/<id>/restore/<hid>` | 55       | 還原版本 |
| `POST /notes/<id>/duplicate`     | 55       | 複製     |
| `POST /notes/batch/type`         | 60       | 批量分類 |
| `POST /notes/batch/tags`         | 95       | 批量標籤 |
| `DELETE /notes/batch`            | 60       | 批量刪除 |
| `PUT /notes/reorder`             | 70       | 排序     |

### 5.2 v1.0 模組結構

```
routes/
├── __init__.py           # Blueprint 註冊
├── notes/
│   ├── __init__.py       # notes_bp Blueprint
│   ├── crud.py           # GET/POST/PUT/DELETE (~250 行)
│   ├── actions.py        # pin/archive/duplicate/reorder (~180 行)
│   ├── history.py        # 版本歷史相關 (~100 行)
│   └── batch.py          # 批量操作 (~200 行)
├── categories.py         # 保持不變
├── tags.py               # 保持不變
├── upload.py             # 保持不變
├── cleanup.py            # 保持不變
├── export.py             # 保持不變
├── system.py             # 保持不變
├── prompt_options.py     # 保持不變
└── wizard_options.py     # 保持不變
```

### 5.3 拆分實作

**`routes/notes/__init__.py`**:

```python
from flask import Blueprint

notes_bp = Blueprint('notes', __name__, url_prefix='/api')

# 導入所有子模組的路由
from . import crud
from . import actions
from . import history
from . import batch
```

**`routes/notes/crud.py`**:

```python
from flask import request, jsonify
from . import notes_bp
from db import get_db, transaction

@notes_bp.route('/notes', methods=['GET'])
def get_notes():
    # ... 列表查詢邏輯 ...

@notes_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    # ... 單筆詳情邏輯 ...

@notes_bp.route('/notes', methods=['POST'])
def create_note():
    # ... 新增邏輯 ...

@notes_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    # ... 更新邏輯 ...

@notes_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    # ... 刪除邏輯 ...
```

### 5.4 共用函數抽取

**`routes/notes/helpers.py`** (可選):

```python
"""
Notes 模組共用函數
"""
import json
from db import get_db


def parse_tags_json(tags_json: str) -> list:
    """解析 JSON 格式的標籤列表"""
    if not tags_json:
        return []
    try:
        return json.loads(tags_json)
    except json.JSONDecodeError:
        return []


def parse_urls_json(urls_json: str) -> list:
    """解析 JSON 格式的網址列表"""
    if not urls_json:
        return []
    try:
        return json.loads(urls_json)
    except json.JSONDecodeError:
        return []


def note_exists(note_id: int) -> bool:
    """檢查筆記是否存在"""
    db = get_db()
    row = db.execute('SELECT 1 FROM Notes WHERE id = ?', (note_id,)).fetchone()
    return row is not None


def get_note_row(note_id: int):
    """取得筆記原始資料 (用於檢查/更新)"""
    db = get_db()
    return db.execute('SELECT * FROM Notes WHERE id = ?', (note_id,)).fetchone()
```

---

## 6. 遷移執行計劃

### 6.1 Phase A: Schema 遷移 (破壞性: 低)

| 步驟 | 工作項目                      | 風險 | 可回滾 |
| ---- | ----------------------------- | ---- | ------ |
| A1   | 建立 `migrations/` 目錄結構   | 無   | ✓      |
| A2   | 實作遷移執行器                | 無   | ✓      |
| A3   | 將現有 if 遷移轉為聲明式      | 低   | ✓      |
| A4   | 新增 `Schema_Meta` 表         | 低   | ✓      |
| A5   | 新增 `Notes.category_id` 欄位 | 低   | ✓      |
| A6   | 填充 `category_id` 值         | 低   | ✓      |

### 6.2 Phase B: 查詢重構 (破壞性: 中)

| 步驟 | 工作項目                                | 風險 | 可回滾 |
| ---- | --------------------------------------- | ---- | ------ |
| B1   | 檢查 SQLite 版本支援                    | 無   | N/A    |
| B2   | 重寫 `get_notes()` 使用 JSON 函數       | 中   | ✓      |
| B3   | 重寫 `get_note()` 使用 JSON 函數        | 中   | ✓      |
| B4   | 更新 `create_note()` 使用 `category_id` | 中   | ✓      |
| B5   | 更新 `update_note()` 使用 `category_id` | 中   | ✓      |
| B6   | 移除 type 同步邏輯 (categories.py)      | 中   | ✓      |

### 6.3 Phase C: 模組拆分 (破壞性: 低)

| 步驟 | 工作項目                  | 風險 | 可回滾 |
| ---- | ------------------------- | ---- | ------ |
| C1   | 建立 `routes/notes/` 目錄 | 無   | ✓      |
| C2   | 拆分 crud.py              | 低   | ✓      |
| C3   | 拆分 actions.py           | 低   | ✓      |
| C4   | 拆分 history.py           | 低   | ✓      |
| C5   | 拆分 batch.py             | 低   | ✓      |
| C6   | 更新 Blueprint 註冊       | 低   | ✓      |
| C7   | 刪除舊 `notes.py`         | 低   | ✓      |

### 6.4 Phase D: 清理 (破壞性: 無)

| 步驟 | 工作項目              | 風險 | 可回滾 |
| ---- | --------------------- | ---- | ------ |
| D1   | 移除防禦性 try/except | 無   | ✓      |
| D2   | 更新 SCHEMA.md 文件   | 無   | ✓      |
| D3   | 更新 TODO.md          | 無   | ✓      |

---

## 7. 風險評估與回滾方案

### 7.1 高風險操作

| 操作             | 風險描述                  | 緩解措施                      |
| ---------------- | ------------------------- | ----------------------------- |
| category_id 填充 | 未匹配的 type 會得到 NULL | 提供預設分類 fallback         |
| JSON 函數        | 舊版 SQLite 不支援        | 版本檢查 + fallback 查詢      |
| type 欄位移除    | 破壞向後相容              | 延後到 v1.1，先保持 type 唯讀 |

### 7.2 回滾方案

**資料庫備份**:

```bash
# 執行任何遷移前
cp knowledge.db knowledge.db.backup.$(date +%Y%m%d_%H%M%S)
```

**遷移失敗回滾**:

```python
# 遷移執行器已內建 rollback
try:
    db.execute(sql)
    db.commit()
except Exception:
    db.rollback()
    raise
```

**程式碼回滾**:

```bash
# Git 恢復到遷移前的 commit
git checkout <commit-before-migration>
```

### 7.3 驗證清單

- [x] 現有筆記可正常顯示
- [x] 新增筆記功能正常
- [x] 編輯筆記功能正常
- [x] 標籤過濾正常
- [x] 分類過濾正常
- [x] 批量操作正常
- [x] 歷史版本正常
- [x] Prompt Builder 正常

---

## 8. 時程估計

| Phase | 工作項目        | 預估時間 | 優先序 |
| ----- | --------------- | -------- | ------ |
| A     | Schema 遷移系統 | 2-3 小時 | 🔴 P0  |
| B     | 查詢重構        | 3-4 小時 | 🔴 P0  |
| C     | 模組拆分        | 2-3 小時 | 🟡 P1  |
| D     | 清理與文件      | 1-2 小時 | 🟢 P2  |

**總計**: 8-12 小時

---

## 9. v0.x → v1.0 對照表

### 9.1 資料表

| v0.x         | v1.0                       | 說明                |
| ------------ | -------------------------- | ------------------- |
| `Notes.type` | `Notes.category_id` + JOIN | FK 關聯取代字串同步 |
| 無           | `Schema_Meta`              | 版本追蹤表          |

### 9.2 後端檔案

| v0.x 路徑         | v1.0 路徑                 | 說明       |
| ----------------- | ------------------------- | ---------- |
| `routes/notes.py` | `routes/notes/crud.py`    | CRUD 操作  |
| `routes/notes.py` | `routes/notes/actions.py` | 動作類操作 |
| `routes/notes.py` | `routes/notes/history.py` | 歷史版本   |
| `routes/notes.py` | `routes/notes/batch.py`   | 批量操作   |
| 無                | `migrations/__init__.py`  | 遷移執行器 |

### 9.3 API 介面 (無變更)

所有現有 API 端點保持不變:

- `GET /api/notes`
- `GET /api/notes/<id>`
- `POST /api/notes`
- `PUT /api/notes/<id>`
- `DELETE /api/notes/<id>`
- `POST /api/notes/<id>/pin`
- `POST /api/notes/<id>/archive`
- `GET /api/notes/<id>/history`
- `POST /api/notes/<id>/restore/<hid>`
- `POST /api/notes/<id>/duplicate`
- `POST /api/notes/batch/type`
- `POST /api/notes/batch/tags`
- `DELETE /api/notes/batch`
- `PUT /api/notes/reorder`

---

## 10. 決策記錄

### 10.1 為何選擇 json_group_array 而非多次查詢？

**考量**:

- 單次查詢 vs N+1 查詢的效能差異
- SQLite 3.38+ 已廣泛支援
- JSON 解析在 Python 中非常快

**結論**: 效能優先，採用 JSON 函數方案。

### 10.2 為何不立即移除 Notes.type？

**考量**:

- 現有前端可能依賴 `note.type` 字串
- 遷移風險需分階段降低
- 給使用者緩衝期

**結論**: Phase A 新增 category_id，Phase B 改用 FK，v1.1 再移除 type。

### 10.3 為何拆分 notes.py 而非使用 Class-based View？

**考量**:

- Flask 原生支援 Blueprint
- 函數式路由更直觀
- 避免引入新的抽象層

**結論**: 保持函數式風格，僅按職責拆分檔案。

---

**END OF SCHEMA_V2.md**

---

## ✅ 執行紀錄

| Phase | 工作項目                     | 完成時間         |
| ----- | ---------------------------- | ---------------- |
| A     | Schema 遷移系統              | 2025-12-09 18:30 |
| B     | 查詢重構 (json_group_array)  | 2025-12-09 19:10 |
| C     | 模組拆分 (notes.py → notes/) | 2025-12-09 19:35 |
| D     | 清理與文件更新               | 2025-12-09 19:45 |

**總執行時間**: ~1.5 小時
