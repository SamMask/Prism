# MVP 技術審查報告 - Local Insight v1.8.9

**審查日期**：2025-12-09
**審查範圍**：全專案（Flask 後端 + Vue.js 前端 + SQLite 資料庫）

---

## 執行摘要

| 指標 | 狀態 |
|------|------|
| **核心功能閉環** | ✅ 完整 |
| **致命邏輯** | ✅ 無阻斷性問題 |
| **SQL 注入風險** | ✅ 安全（全參數化查詢）|
| **架構完整性** | 🟡 可接受，有技術債 |
| **資料結構** | ✅ 支撐業務需求 |

**Linus 式品味評分**：🟡 湊合 - 實用主義做得好，但邊界情況處理有待加強

---

## [紅燈] 阻斷性問題

### 無阻斷性問題

經審查，系統核心功能閉環完整：
- 筆記 CRUD ✅
- 標籤管理 ✅
- 分類管理 ✅
- 圖片上傳 ✅
- 全文檢索 ✅
- 版本控制 ✅
- 匯出功能 ✅

**但以下問題需優先處理（非阻斷但高風險）：**

---

## [黃燈] 風險與技術債

### 1. 安全風險（需本週修復）

#### 1.1 路徑穿越驗證不完整
**位置**：[upload.py:170-179](routes/upload.py#L170-L179)

```python
# 現有代碼
if '/static/uploads/' in url:
    filename = url.split('/static/uploads/')[-1]  # 危險：未過濾 ../
```

**風險**：雖有 `os.path.abspath` 檢查，但 `split` 邏輯可被繞過
**修復**：
```python
filename = os.path.basename(url.split('/static/uploads/')[-1])
if '..' in filename or filename.startswith('.'):
    return error('Invalid filename')
```

#### 1.2 空異常捕捉掩蓋 Bug
**位置**：[notes.py:479](routes/notes.py#L479)

```python
except:  # 捕捉所有異常，包括 KeyboardInterrupt
```

**修復**：改為 `except sqlite3.OperationalError:`

#### 1.3 FTS5 搜尋輸入未完整清理
**位置**：[notes.py:60-66](routes/notes.py#L60-L66)

```python
safe_keyword = "".join([c for c in keyword if c.isalnum() or c.isspace()])
# 未處理 FTS5 特殊語法："", (), AND, OR, NOT
```

**修復**：
```python
def escape_fts(text):
    for char in '"()':
        text = text.replace(char, '')
    return text
```

---

### 2. 並發風險（可延後但需記錄）

#### 2.1 讀-改-寫競態條件
**位置**：[notes.py:358-402](routes/notes.py#L358-L402)

```
時間線：
T1: 用戶A SELECT content WHERE id=1  →  "Hello"
T2: 用戶B SELECT content WHERE id=1  →  "Hello"
T3: 用戶A UPDATE content = "Hello World"
T4: 用戶B UPDATE content = "Hello China"  →  用戶A的修改丟失
```

**MVP 狀態**：單用戶本地應用，風險低
**未來修復**：加入樂觀鎖（version 欄位）

#### 2.2 配置檔案並發寫入
**位置**：[prompt_options.py:39-48](routes/prompt_options.py#L39-L48)

**風險**：兩個請求同時修改 `prompt_options.json` 會互相覆蓋
**MVP 狀態**：單用戶低頻操作，風險低
**未來修復**：使用原子寫入（tempfile + os.replace）

#### 2.3 交易隔離不足
**位置**：[tags.py:166-187](routes/tags.py#L166-L187)

**風險**：標籤合併操作中若異常，已刪除的標籤不會回滾
**修復**：包裹在 `BEGIN TRANSACTION ... COMMIT` 中

---

### 3. 輸入驗證債務（低優先級）

| 位置 | 問題 | 風險 |
|------|------|------|
| [notes.py:40](routes/notes.py#L40) | 關鍵字長度無限制 | DoS |
| [notes.py:701](routes/notes.py#L701) | 批量 note_ids 未驗證類型 | 異常 |
| [export.py:159](routes/export.py#L159) | ZIP 匯出無大小限制 | OOM |

---

### 4. 架構技術債

#### 4.1 重複的 get_db() 定義
**現狀**：8 個 routes 檔案各自定義 `get_db()`
**問題**：違反 DRY，維護困難
**建議**：提取到 `db.py` 統一管理

#### 4.2 Jinja2 分隔符修改
**現狀**：為避免與 Vue `{{ }}` 衝突，改為 `[{ }]`
**問題**：非標準做法，增加認知負擔
**建議**：MVP 可保留，未來考慮純前後端分離

#### 4.3 i18n 函數逐層傳遞
**現狀**：`t()` 函數從 app.js 傳到各 composable
**問題**：耦合度高
**建議**：使用 Vue 的 provide/inject

---

## [建議] 架構修正

### 當前架構（簡化版）

```
┌─────────────────────────────────────────────┐
│              Flask Backend                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │ notes   │  │  tags   │  │ upload  │ ... │
│  └────┬────┘  └────┬────┘  └────┬────┘     │
│       │            │            │           │
│       └────────────┼────────────┘           │
│                    ▼                        │
│              ┌──────────┐                   │
│              │ SQLite   │                   │
│              │ (WAL)    │                   │
│              └──────────┘                   │
└─────────────────────────────────────────────┘
```

### 建議改進（Phase 2）

```
┌─────────────────────────────────────────────┐
│              Flask Backend                   │
│  ┌─────────────────────────────────────┐    │
│  │           routes/*.py               │    │
│  └──────────────────┬──────────────────┘    │
│                     ▼                       │
│  ┌─────────────────────────────────────┐    │
│  │        db.py (統一連線層)            │    │  ← 新增
│  │  - get_db()                         │    │
│  │  - transaction context manager      │    │
│  │  - query builder helpers            │    │
│  └──────────────────┬──────────────────┘    │
│                     ▼                       │
│              ┌──────────┐                   │
│              │ SQLite   │                   │
│              └──────────┘                   │
└─────────────────────────────────────────────┘
```

**統一資料庫層偽代碼**：
```python
# db.py
from contextlib import contextmanager

@contextmanager
def transaction():
    db = get_db()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise

# 使用方式
with transaction() as db:
    db.execute('INSERT ...')
    db.execute('UPDATE ...')
    # 自動 commit 或 rollback
```

---

## 資料結構評估

### 現有 Schema（通過審查）

```sql
Notes (id, title, content, type, remarks, cover_image,
       cover_position, editor_layout, is_pinned,
       prompt_params, created_at, updated_at)

Tags (id, name UNIQUE COLLATE NOCASE)

Note_Tags (note_id FK, tag_id FK) -- 多對多

Source_Urls (note_id FK, url)

Categories (id, name, icon, sort_order, is_default)

Note_History (id, note_id FK, content, diff_summary, created_at)

Notes_FTS (title, content) -- FTS5 虛擬表
```

**評估**：
- ✅ 正規化程度適當（3NF）
- ✅ 外鍵約束完整
- ✅ FTS5 全文檢索配置正確
- ✅ WAL 模式優化並發
- 🟡 缺少 `version` 欄位（樂觀鎖用）

---

## 修復優先級矩陣

```
緊急程度 ↑
    │
  高│  [1.1] 路徑穿越    [1.2] 空 except
    │
  中│  [1.3] FTS清理     [2.3] 交易隔離
    │                    [3.x] 輸入驗證
  低│  [2.1] 競態條件    [4.x] 架構債務
    │  [2.2] 配置並發
    └──────────────────────────────────→ 影響範圍
       小                              大
```

**建議順序**：
1. **今日**：1.1, 1.2（2小時）
2. **本週**：1.3, 2.3（3小時）
3. **下週**：3.x 系列（2小時）
4. **Phase 2**：2.1, 2.2, 4.x（重構週期）

---

## 結論

Local Insight v1.8.9 作為 MVP 已達到**可用狀態**：

| 維度 | 評估 |
|------|------|
| 致命邏輯 | ✅ 無 |
| 功能完整性 | ✅ 核心功能閉環 |
| 資料安全 | ✅ SQL 注入已防護 |
| 邊界安全 | 🟡 需加強（路徑、輸入）|
| 並發安全 | 🟡 單用戶可接受 |
| 可維護性 | 🟡 有技術債但可控 |

**Linus 總評**：
> "程式碼是實用的，沒有過度設計。但邊界情況處理太多 if/else，應該從資料結構層面消除特殊情況。路徑驗證那段尤其糟糕 — 不要用字符串操作，用 `os.path.basename()`。"

---

*報告生成時間：2025-12-09*
*審查工具：Claude Code + 人工覆核*
