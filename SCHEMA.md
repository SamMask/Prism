# Local Insight - 全域資料字典 (Database Schema)

**資料庫**: SQLite 3
**版本**: v1.0.0
**特性**: 啟用 Foreign Keys 約束 (`PRAGMA foreign_keys = ON;`)
**修訂**: Phase 10 - 架構重構 (Linus 風格瘦身)

---

## 1. 資料表總覽

| 表名           | 用途                | 關聯                             |
| -------------- | ------------------- | -------------------------------- |
| `Notes`        | 儲存筆記主體內容    | 主表 (1:N Source_Urls, N:M Tags) |
| `Source_Urls`  | 儲存筆記參考網址    | FK → Notes                       |
| `Tags`         | 儲存標籤名稱        | 主表 (N:M Notes)                 |
| `Note_Tags`    | 筆記與標籤關聯表    | FK → Notes, FK → Tags            |
| `Categories`   | 分類定義表 (v0.6)   | 獨立表，與 Notes.type 同步       |
| `Note_History` | 筆記版本歷史 (v0.6) | FK → Notes                       |
| `Notes_FTS`    | 全文檢索 (FTS5)     | 虛擬表，自動同步 Notes           |
| `Schema_Meta`  | 版本追蹤表 (v1.0)   | 儲存 Schema 版本號               |

---

## 2. 資料表詳細定義

### 2.1 Notes (筆記主體表)

| 欄位名           | 數據類型 | 約束                      | 預設值              | 說明                                                                                                                  |
| ---------------- | -------- | ------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `id`             | INTEGER  | PRIMARY KEY AUTOINCREMENT | -                   | 唯一識別碼                                                                                                            |
| `title`          | TEXT     | NOT NULL                  | -                   | 筆記標題 (最大建議 200 字元)                                                                                          |
| `content`        | TEXT     | NOT NULL                  | -                   | 筆記內容 (Markdown 格式)                                                                                              |
| `type`           | TEXT     | NOT NULL                  | `'筆記'`            | 分類屬性 (建議值: 提示詞/筆記/教學/資料/靈感)                                                                         |
| `remarks`        | TEXT     | -                         | NULL                | 備註 (簡短說明，顯示於卡片懸停)                                                                                       |
| `cover_image`    | TEXT     | -                         | NULL                | 封面圖片路徑 (例: `/static/uploads/abc.jpg`)<br>若為 NULL，前端自動抓取 content 第一張圖或顯示預設色塊                |
| `cover_position` | TEXT     | -                         | `'top'`             | 封面圖片顯示位置 (v0.8.4): 'top'=置頂, 'center'=置中, 'bottom'=置底<br>影響卡片封面的 CSS object-position 屬性        |
| `editor_layout`  | TEXT     | -                         | `'single'`          | 編輯器佈局模式 (v0.8.5): 'single'=單欄模式, 'dual'=雙欄模式（圖片在左，文字在右）<br>僅影響編輯器視圖，不影響卡片顯示 |
| `is_pinned`      | INTEGER  | -                         | `0`                 | 置頂標記 (v0.6.6): 0=未置頂, 1=置頂。置頂的筆記會優先顯示在列表最前方                                                 |
| `sort_order`     | INTEGER  | -                         | `0`                 | 排序權重 (v0.9.0): 用於自訂排序，數字越小越前面<br>僅在 sort=custom 時生效                                            |
| `category_id`    | INTEGER  | FK                        | NULL                | 分類 ID (v1.0): 關聯 Categories(id)，逐步取代 type 欄位                                                               |
| `prompt_params`  | TEXT     | -                         | NULL                | Prompt Builder 結構化參數 (JSON 格式, v0.6.5)<br>儲存原始表單狀態，用於再次編輯                                       |
| `created_at`     | DATETIME | NOT NULL                  | `CURRENT_TIMESTAMP` | 建立時間 (ISO 8601 格式)                                                                                              |
| `updated_at`     | DATETIME | NOT NULL                  | `CURRENT_TIMESTAMP` | 最後更新時間                                                                                                          |

**索引建議**:

```sql
CREATE INDEX idx_notes_type ON Notes(type);
CREATE INDEX idx_notes_updated_at ON Notes(updated_at DESC);
```

**⚡ 效能備註 (v0.1)**:

- `idx_notes_updated_at DESC` 索引優化排序查詢，配合分頁使用
- 建議定期使用 `ANALYZE` 指令更新查詢優化統計

> [!WARNING] > **已知問題 (2025-12-11 Audit)**:
>
> - `Notes.type` 與 `Notes.category_id` 存在「雙重事實」分裂。
> - 應用層 (`crud.py`) 目前僅寫入 `type`，`category_id` 為 NULL。
> - **修復方向**: 短期在 CRUD 時同步寫入 `category_id`；長期廢棄 `type`。

---

### 2.2 Source_Urls (來源網址表)

| 欄位名    | 數據類型 | 約束                                         | 預設值 | 說明                                 |
| --------- | -------- | -------------------------------------------- | ------ | ------------------------------------ |
| `id`      | INTEGER  | PRIMARY KEY AUTOINCREMENT                    | -      | 唯一識別碼                           |
| `note_id` | INTEGER  | FOREIGN KEY → Notes(id)<br>ON DELETE CASCADE | -      | 所屬筆記 ID (刪除筆記時自動刪除網址) |
| `url`     | TEXT     | NOT NULL                                     | -      | 完整 URL (建議驗證格式：http/https)  |

**索引建議**:

```sql
CREATE INDEX idx_source_urls_note_id ON Source_Urls(note_id);
```

---

### 2.3 Tags (標籤表)

| 欄位名 | 數據類型 | 約束                      | 預設值 | 說明                                           |
| ------ | -------- | ------------------------- | ------ | ---------------------------------------------- |
| `id`   | INTEGER  | PRIMARY KEY AUTOINCREMENT | -      | 唯一識別碼                                     |
| `name` | TEXT     | NOT NULL UNIQUE           | -      | 標籤名稱 (不區分大小寫建議使用 COLLATE NOCASE) |

**索引建議**:

```sql
CREATE UNIQUE INDEX idx_tags_name ON Tags(name COLLATE NOCASE);
```

**標籤管理操作 (v0.2 新增)**:

- **重命名**: 直接 `UPDATE Tags SET name = ? WHERE id = ?`，自動影響所有關聯筆記
- **刪除**: 利用 `ON DELETE CASCADE` 自動清理 Note_Tags 關聯
- **合併**: 將來源標籤的 Note_Tags 關聯轉移到目標標籤後刪除來源標籤
  ```sql
  -- 合併範例: 將 tag_ids [1,2,3] 合併到 tag_id 4
  INSERT OR IGNORE INTO Note_Tags (note_id, tag_id)
  SELECT note_id, 4 FROM Note_Tags WHERE tag_id IN (1,2,3);
  DELETE FROM Tags WHERE id IN (1,2,3);
  ```
- **防重複機制**: 使用 `PRIMARY KEY (note_id, tag_id)` 防止重複關聯

---

### 2.4 Note_Tags (筆記標籤關聯表)

| 欄位名    | 數據類型 | 約束                                         | 預設值 | 說明    |
| --------- | -------- | -------------------------------------------- | ------ | ------- |
| `note_id` | INTEGER  | FOREIGN KEY → Notes(id)<br>ON DELETE CASCADE | -      | 筆記 ID |
| `tag_id`  | INTEGER  | FOREIGN KEY → Tags(id)<br>ON DELETE CASCADE  | -      | 標籤 ID |

**主鍵約束**:

```sql
PRIMARY KEY (note_id, tag_id)
```

**說明**: 複合主鍵防止重複關聯；CASCADE 刪除確保資料一致性。

---

### 2.5 Schema_Meta (版本追蹤表 - v1.0)

| 欄位名  | 數據類型 | 約束        | 說明                       |
| ------- | -------- | ----------- | -------------------------- |
| `key`   | TEXT     | PRIMARY KEY | 設定鍵 (如 schema_version) |
| `value` | TEXT     | NOT NULL    | 設定值 (如 7)              |

**用途**:
用於版本化遷移系統 (`migrations/`) 判斷當前資料庫版本，決定需要執行哪些遷移腳本。取代了過往 `app.py` 中散亂的 `if 'column' not in columns` 檢查。

---

## 3. 完整建表 SQL

```sql
-- 啟用外鍵約束
PRAGMA foreign_keys = ON;

-- 1. Notes 表
CREATE TABLE IF NOT EXISTS Notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT '筆記',
    remarks TEXT,
    cover_image TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notes_type ON Notes(type);
CREATE INDEX idx_notes_updated_at ON Notes(updated_at DESC);

-- 2. Source_Urls 表
CREATE TABLE IF NOT EXISTS Source_Urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE
);

CREATE INDEX idx_source_urls_note_id ON Source_Urls(note_id);

-- 3. Tags 表
CREATE TABLE IF NOT EXISTS Tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE UNIQUE INDEX idx_tags_name ON Tags(name COLLATE NOCASE);

-- 4. Note_Tags 表
CREATE TABLE IF NOT EXISTS Note_Tags (
    note_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES Notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES Tags(id) ON DELETE CASCADE
);

-- 5. Schema_Meta 表 (v1.0)
CREATE TABLE IF NOT EXISTS Schema_Meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## 4. 資料關係圖 (ERD)

```
┌─────────────┐        ┌─────────────┐
│   Notes     │◄──────┤Source_Urls  │
│             │1      N│             │
│ PK: id      │        │ FK: note_id │
└─────┬───────┘        └─────────────┘
      │
      │M
      │
      ▼
┌─────────────┐        ┌─────────────┐
│ Note_Tags   │◄──────►│    Tags     │
│ (中介表)     │N      1│             │
│ FK: note_id │        │ PK: id      │
│ FK: tag_id  │        │             │
└─────────────┘        └─────────────┘
```

---

## 5. 範例資料

### 5.1 插入範例筆記

```sql
INSERT INTO Notes (title, content, type, remarks, cover_image)
VALUES (
    'Flask RESTful API 教學',
    '# Flask API 快速入門\n\n建立基本路由...',
    '教學',
    '適合初學者的 Flask 教學',
    '/static/uploads/flask_logo.png'
);
```

### 5.2 插入範例標籤與關聯

```sql
-- 插入標籤 (若不存在)
INSERT OR IGNORE INTO Tags (name) VALUES ('Python'), ('Flask'), ('教學');

-- 建立關聯 (假設 note_id=1)
INSERT INTO Note_Tags (note_id, tag_id)
VALUES
    (1, (SELECT id FROM Tags WHERE name='Python')),
    (1, (SELECT id FROM Tags WHERE name='Flask'));
```

### 5.3 插入範例網址

```sql
INSERT INTO Source_Urls (note_id, url)
VALUES
    (1, 'https://flask.palletsprojects.com'),
    (1, 'https://realpython.com/flask-tutorial');
```

---

## 6. 查詢範例

### 6.1 取得單一筆記完整資訊 (含標籤與網址)

```sql
SELECT
    n.*,
    (SELECT GROUP_CONCAT(t.name, '||')
     FROM Note_Tags nt
     JOIN Tags t ON nt.tag_id = t.id
     WHERE nt.note_id = n.id) AS tags,
    (SELECT GROUP_CONCAT(url, '||')
     FROM Source_Urls
     WHERE note_id = n.id) AS urls
FROM Notes n
WHERE n.id = 1;
```

**🔧 v1.0 重構 (json_group_array)**:

從 v1.0 開始，改用 SQLite `json_group_array` 函數取代 `GROUP_CONCAT`，解決了標籤名稱包含分隔符號導致解析錯誤的問題。

```sql
SELECT
    n.*,
    (SELECT json_group_array(json_object('id', t.id, 'name', t.name))
     FROM Note_Tags nt
     JOIN Tags t ON nt.tag_id = t.id
     WHERE nt.note_id = n.id) AS tags_json,
    (SELECT json_group_array(url)
     FROM Source_Urls
     WHERE note_id = n.id) AS urls_json
FROM Notes n
WHERE n.id = 1;
```

後端 Python 直接使用 `json.loads()` 解析，無需手動 `split()`。

### 6.2 依 Type 與 Tags 過濾

```sql
-- 查詢 type='教學' 且包含標籤 'Python' 的筆記
SELECT DISTINCT n.*
FROM Notes n
JOIN Note_Tags nt ON n.id = nt.note_id
JOIN Tags t ON nt.tag_id = t.id
WHERE n.type = '教學' AND t.name IN ('Python')
ORDER BY n.updated_at DESC;
```

### 6.3 分頁查詢 (v0.1 新增)

```sql
-- 取得第 2 頁筆記 (每頁 20 筆)
SELECT
    n.*,
    (SELECT GROUP_CONCAT(t.name, '||')
     FROM Note_Tags nt
     JOIN Tags t ON nt.tag_id = t.id
     WHERE nt.note_id = n.id) AS tags,
    (SELECT GROUP_CONCAT(url, '||')
     FROM Source_Urls
     WHERE note_id = n.id) AS urls
FROM Notes n
ORDER BY n.updated_at DESC
LIMIT 20 OFFSET 20;  -- OFFSET = (page - 1) * per_page

-- 取得總筆記數
SELECT COUNT(*) AS total FROM Notes;
```

**效能建議**:

- 使用 `idx_notes_updated_at` 索引加速 ORDER BY
- 前端應實作「載入更多」而非傳統頁碼（減少 OFFSET 大值的效能問題）

---

## 7. 資料完整性與效能

### 7.1 完整性約束

1. **Foreign Key Cascade**: 刪除筆記時，自動清理 `Source_Urls` 與 `Note_Tags`
2. **UNIQUE 約束**: 標籤名稱不可重複（不區分大小寫）
3. **NOT NULL 約束**: 核心欄位 `title`, `content`, `type` 必填

### 7.2 效能優化

1. **索引策略**:

   - 所有 JOIN 的欄位都已建立索引 (`note_id`, `tag_id`)
   - 排序欄位 `updated_at` 建立降序索引

2. **查詢優化**:

   - 避免使用 `SELECT *`（明確指定欄位可減少 I/O）
   - 分頁查詢使用 `LIMIT` + `OFFSET`

3. **維護建議**:

   ```sql
   -- 定期執行以更新查詢優化統計
   ANALYZE;

   -- 檢查查詢計劃（確保使用索引）
   EXPLAIN QUERY PLAN
   SELECT * FROM Notes WHERE type = '教學' ORDER BY updated_at DESC LIMIT 20;
   ```

---

---

## 8. v0.3 新增資料表 (分類與歷史紀錄)

### 8.1 Categories (分類表)

用於集中管理筆記分類，支援拖曳排序與自訂圖示。

| 欄位名       | 數據類型 | 約束                      | 預設值 | 說明                           |
| ------------ | -------- | ------------------------- | ------ | ------------------------------ |
| `id`         | INTEGER  | PRIMARY KEY AUTOINCREMENT | -      | 唯一識別碼                     |
| `name`       | TEXT     | NOT NULL UNIQUE           | -      | 分類名稱 (如: 提示詞, 筆記)    |
| `icon`       | TEXT     | -                         | NULL   | 分類圖示 (Emoji 或 Icon Class) |
| `sort_order` | INTEGER  | NOT NULL                  | 0      | 排序權重 (數字越小越前面)      |
| `is_default` | BOOLEAN  | NOT NULL                  | 0      | 是否為預設分類                 |

**備註**:

- 現有的 `Notes.type` 欄位將保留，但在程式邏輯上需與 `Categories` 表保持同步。
- 修改分類名稱時，需執行 `UPDATE Notes SET type = ? WHERE type = ?` 批次更新。

### 8.2 Note_History (筆記歷史記錄表)

用於實作「筆記時光機」，記錄每次修改前的內容快照。

| 欄位名         | 數據類型 | 約束                                         | 預設值              | 說明                |
| -------------- | -------- | -------------------------------------------- | ------------------- | ------------------- |
| `id`           | INTEGER  | PRIMARY KEY AUTOINCREMENT                    | -                   | 唯一識別碼          |
| `note_id`      | INTEGER  | FOREIGN KEY → Notes(id)<br>ON DELETE CASCADE | -                   | 所屬筆記 ID         |
| `content`      | TEXT     | NOT NULL                                     | -                   | 內容快照            |
| `diff_summary` | TEXT     | -                                            | NULL                | 變更摘要 (Optional) |
| `created_at`   | DATETIME | NOT NULL                                     | `CURRENT_TIMESTAMP` | 備份時間            |

**索引建議**:

```sql
CREATE INDEX idx_note_history_note_id ON Note_History(note_id);
```

**歷史紀錄管理 (v1.0)**:

| 操作     | 端點                             | 說明                               |
| -------- | -------------------------------- | ---------------------------------- |
| 取得歷史 | `GET /api/notes/<id>/history`    | 取得指定筆記的所有歷史版本         |
| 還原版本 | `POST /api/notes/<id>/restore`   | 還原到指定歷史版本                 |
| 清空歷史 | `DELETE /api/notes/<id>/history` | 刪除指定筆記的所有歷史 (v1.0 新增) |

> **應用層 Cascade Delete (v1.0)**:
> 刪除筆記時，後端會先執行 `DELETE FROM Note_History WHERE note_id = ?`，
> 確保歷史紀錄一併清除，避免孤兒資料 (Orphan Data)。

**匯出功能 (v1.0)**:

| 操作     | 端點                           | 說明                                 |
| -------- | ------------------------------ | ------------------------------------ |
| 批量匯出 | `POST /api/notes/export/batch` | 將多筆筆記打包為 ZIP (含 .md + 圖片) |

Request Body: `{ "note_ids": [1, 2, 3] }`
Response: ZIP file (notes/_.md + assets/_.jpg)

**匯入功能 (v1.1 已實作)**:

| 操作     | 端點                        | 說明              |
| -------- | --------------------------- | ----------------- |
| 匯入單檔 | `POST /api/notes/import/md` | 上傳 .md 建立筆記 |

- 支援批量選擇（前端 `multiple` 屬性）
- 自動解析 YAML front matter (type, tags)
- 自動下載外部圖片並儲存至 `static/uploads/`

**系統維護 API (v1.1 已實作)**:

| 操作         | 端點                                  | 說明                   |
| ------------ | ------------------------------------- | ---------------------- |
| VACUUM       | `POST /api/system/vacuum`             | 緊縮資料庫釋放碎片空間 |
| 清空歷史     | `POST /api/system/clear-history`      | 刪除所有 Note_History  |
| 啟動偏好(讀) | `GET /api/system/startup-preference`  | 取得自動開啟瀏覽器設定 |
| 啟動偏好(寫) | `POST /api/system/startup-preference` | 設定自動開啟瀏覽器偏好 |

---

## 9. 前端設定儲存 (localStorage)

### 9.1 已實作的設定項

| 鍵名                  | 類型    | 預設值      | 說明                                                                              |
| --------------------- | ------- | ----------- | --------------------------------------------------------------------------------- |
| `autoLoadMore`        | boolean | `true`      | 自動載入更多筆記                                                                  |
| `locale`              | string  | `'zh-TW'`   | 語言偏好 (zh-TW / en)                                                             |
| `quickAddDefaultType` | string  | `'提示詞'`  | 快速新增的預設分類 (控制閃電按鈕預設值)                                           |
| `newNoteDefaultType`  | string  | `'筆記'`    | 新增卡片的預設分類 (控制藍色按鈕預設值，v0.9.0 新增)                              |
| `imageSaveMode`       | string  | `'both'`    | 貼上圖片時保存模式：'both' / 'thumbnail_only'                                     |
| `colorTheme`          | string  | `'default'` | 品牌主題色：'default' / 'cyberpunk' / 'eye-care' / 'elegant' / 'ocean' / 'sunset' |
| `autoOpenBrowser`     | boolean | `null`      | 啟動時自動開啟瀏覽器 (v1.1 規劃，首次詢問使用者)                                  |

---

## 10. 資料庫效能考量 (Phase 9 規劃)

### 10.1 現狀分析

- 所有筆記主體內容 (`content` TEXT) 存於單一 `knowledge.db`
- 當筆記數量超過數千則，或單則筆記內容過大時，可能產生效能問題

### 10.2 未來分拆方案評估

| 方案                  | 優點                           | 缺點                       |
| --------------------- | ------------------------------ | -------------------------- |
| 按時間分表            | 查詢效能優化，舊資料歸檔       | 跨表查詢複雜               |
| 內容外部化 (.md 檔案) | 資料庫輕量化，易於備份單則筆記 | 搜尋需額外索引，原子性降低 |
| 附件 Metadata 分離    | 圖片管理更靈活                 | 需要額外的關聯查詢         |

### 10.3 圖片儲存優化

- **縮圖命名規則**: `thumb_{timestamp}_{filename}` (與原圖對應)
- **原圖路徑回退**: 若原圖不存在，前端/後端自動嘗試載入對應縮圖
- **批量清理**: 提供 API 刪除所有原圖並修正筆記內容中的路徑

### 10.4 資料庫維護 API (Phase 9.4)

| 端點                 | 方法 | 說明                                 |
| -------------------- | ---- | ------------------------------------ |
| `/api/system/vacuum` | POST | 執行 VACUUM 緊縮資料庫，釋放碎片空間 |

---

## 11. CSS 設計系統 (v0.9.0)

### 11.1 設計令牌 (Design Tokens)

所有顏色定義於 `static/css/styles.css` 的 `:root` 及 `[data-theme="..."]` 選擇器中。

#### 背景色系統

| 變數名                | 用途                   | Default 值 (dark) |
| --------------------- | ---------------------- | ----------------- |
| `--color-bg-base`     | 頁面最底層背景         | `#030712`         |
| `--color-bg-surface`  | 卡片、面板、側邊欄背景 | `#111827`         |
| `--color-bg-elevated` | 懸浮元素、Modal 背景   | `#1f2937`         |
| `--color-bg-hover`    | 懸停狀態背景           | `#374151`         |

#### 主色系統

| 變數名                  | 用途              | Default 值 (Blue) |
| ----------------------- | ----------------- | ----------------- |
| `--color-primary`       | 主要按鈕、連結    | `#3b82f6`         |
| `--color-primary-hover` | 主色懸停          | `#2563eb`         |
| `--color-primary-light` | 主色淺版 (badge)  | `#60a5fa`         |
| `--color-primary-rgb`   | RGB 值 (透明度用) | `59, 130, 246`    |

#### 強調色系統

| 變數名                 | 用途           | Default 值 (Purple) |
| ---------------------- | -------------- | ------------------- |
| `--color-accent`       | 次要強調、漸層 | `#8b5cf6`           |
| `--color-accent-hover` | 強調色懸停     | `#7c3aed`           |
| `--color-accent-light` | 強調色淺版     | `#a78bfa`           |

#### 文字色系統

| 變數名                   | 用途         | Default 值 |
| ------------------------ | ------------ | ---------- |
| `--color-text-primary`   | 主要文字     | `#f3f4f6`  |
| `--color-text-secondary` | 次要文字     | `#9ca3af`  |
| `--color-text-muted`     | 輔助說明文字 | `#6b7280`  |

#### 邊框色系統

| 變數名                   | 用途       | Default 值 |
| ------------------------ | ---------- | ---------- |
| `--color-border-default` | 預設邊框   | `#374151`  |
| `--color-border-subtle`  | 輕微分隔線 | `#1f2937`  |

#### 狀態色系統

| 變數名            | 用途 | Default 值 |
| ----------------- | ---- | ---------- |
| `--color-success` | 成功 | `#10b981`  |
| `--color-warning` | 警告 | `#f59e0b`  |
| `--color-danger`  | 錯誤 | `#ef4444`  |

---

### 11.2 主題色盤 (6 套)

| 主題 ID     | 名稱     | Primary   | Accent    | 說明               |
| ----------- | -------- | --------- | --------- | ------------------ |
| `default`   | 專業藍   | `#3b82f6` | `#8b5cf6` | 預設主題，穩重專業 |
| `cyberpunk` | 賽博龐克 | `#e879f9` | `#22d3ee` | 霓虹粉紫，科技感   |
| `eye-care`  | 護眼綠   | `#34d399` | `#a3e635` | 柔和綠色，減輕疲勞 |
| `elegant`   | 優雅金   | `#d4a574` | `#a1887f` | 暖色調，典雅質感   |
| `ocean`     | 海洋藍綠 | `#14b8a6` | `#0ea5e9` | 清新透亮，自然感   |
| `sunset`    | 日落橙   | `#f97316` | `#f472b6` | 活力橙色，溫暖感   |

---

### 11.3 主題感知 Utility Classes

#### Tailwind → Theme 映射表

| Tailwind 硬編碼   | Theme Class            | CSS 變數                 |
| ----------------- | ---------------------- | ------------------------ |
| `bg-gray-950`     | `bg-theme-base`        | `--color-bg-base`        |
| `bg-gray-900`     | `bg-theme-surface`     | `--color-bg-surface`     |
| `bg-gray-800`     | `bg-theme-elevated`    | `--color-bg-elevated`    |
| `bg-gray-700`     | `bg-theme-hover`       | `--color-bg-hover`       |
| `bg-blue-600`     | `bg-theme-primary`     | `--color-primary`        |
| `bg-purple-600`   | `bg-theme-accent`      | `--color-accent`         |
| `border-gray-700` | `border-theme-default` | `--color-border-default` |
| `border-gray-800` | `border-theme-subtle`  | `--color-border-subtle`  |
| `text-gray-100`   | `text-theme-primary`   | `--color-text-primary`   |
| `text-gray-400`   | `text-theme-secondary` | `--color-text-secondary` |
| `text-gray-500`   | `text-theme-muted`     | `--color-text-muted`     |

#### 使用範例

```html
<!-- 舊寫法 (硬編碼) -->
<div class="bg-gray-900 border border-gray-700 text-gray-100">
  <!-- 新寫法 (主題感知) -->
  <div
    class="bg-theme-surface border border-theme-default text-theme-primary"
  ></div>
</div>
```

---

## 12. 前端模板結構 (Phase 9.5 規劃)

### 12.1 Jinja2 組件化架構

將 `templates/index.html` (3,500+ 行) 拆分為可維護的組件：

```
templates/
├── index.html              # 主框架 (~150 行)
├── components/
│   ├── _header.html        # 頂部導航欄 (~400 行)
│   ├── _sidebar.html       # 側邊欄 (~160 行)
│   ├── _note-grid.html     # 卡片網格 (~520 行)
│   ├── _editor-modal.html  # 編輯器 Modal (~1,300 行)
│   ├── _settings-modal.html# 設定 Modal (~870 行)
│   ├── _selection-bar.html # 複選操作列 (New)
│   ├── _context-menus.html # 右鍵選單 (~100 行)
│   └── _scripts.html       # JS 初始化 (~94 行)
```

### 12.2 組件說明

| 組件                   | 內容                                       |
| ---------------------- | ------------------------------------------ |
| `_header.html`         | Logo、搜尋框、新增按鈕、語言切換、設定按鈕 |
| `_sidebar.html`        | 分類過濾、標籤過濾、移動端遮罩             |
| `_note-grid.html`      | Grid/List 切換、卡片渲染、載入狀態         |
| `_editor-modal.html`   | 編輯器所有 UI (標籤、預覽、圖片上傳)       |
| `_settings-modal.html` | 分類管理、用戶偏好、圖片清理工具           |
| `_selection-bar.html`  | 複選模式下的批次操作工具列                 |
| `_context-menus.html`  | 標籤右鍵選單、重命名/合併 Modal            |
| `_scripts.html`        | Vue.js 初始化、ES Module imports           |

### 12.3 Include 語法

```jinja2
{% include 'components/_header.html' %}
```

---

---

## 13. 後端架構重構 (v1.0)

### 13.1 模組拆分

為解決 `routes/notes.py` 過於龐大 (1,000+ 行) 的問題，v1.0 將其拆分為子模組：

```
routes/
├── __init__.py           # Blueprint 註冊
├── notes/                # Notes 子模組目錄
│   ├── __init__.py       # notes_bp Blueprint 定義
│   ├── crud.py           # 基本 CRUD (GET/POST/PUT/DELETE)
│   ├── actions.py        # 動作 (Pin/Archive/Duplicate/Reorder)
│   ├── history.py        # 歷史版本 (History/Restore)
│   └── batch.py          # 批量操作 (Type/Tags/Delete)
├── helpers.py            # 共用工具 (JSON 解析)
└── ... (其他模組)
```

### 13.2 版本化遷移系統

引入 `migrations/` 目錄與聲明式遷移腳本，取代 `app.py` 中的命令式 `if` 檢查。

```python
# migrations/__init__.py
MIGRATIONS = [
    (1, "add_is_pinned", [...]),
    (2, "add_cover_position", [...]),
    ...
    (6, "add_category_id", [...]),
]
```

系統啟動時自動檢查 `Schema_Meta` 版本號並執行必要的遷移。

---

## 14. 無障礙設計規範 (Accessibility)

> 📄 來源: Phase 12 審核報告 (Linus 式篩選)

### 14.1 鍵盤可及性

| 規範               | 說明                                                           |
| ------------------ | -------------------------------------------------------------- |
| **ESC 關閉 Modal** | 所有 Modal 必須監聽 `@keydown.esc`                             |
| **Focus 可見**     | 禁止使用 `focus:ring-0` 除非有替代樣式                         |
| **Hover = Focus**  | `opacity-0 group-hover:opacity-100` 必須補 `focus:opacity-100` |

### 14.2 CSS 禁令

```css
/* ❌ 禁止：暴力覆蓋破壞 Tailwind 設計 */
.p-6 {
  padding: 1rem !important;
}

/* ✅ 正確：使用響應式前綴 */
/* HTML: class="p-4 md:p-6 lg:p-8" */
```

### 14.3 效能警戒線

| 指標              | 警戒值 | 行動                 |
| ----------------- | ------ | -------------------- |
| 無限滾動 DOM 數量 | > 500  | 考慮虛擬化           |
| 筆記總數          | > 1000 | 評估分頁 vs 虛擬滾動 |

---

**END OF SCHEMA.md (v1.0.0)**
