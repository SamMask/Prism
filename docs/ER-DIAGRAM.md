# Entity Relationship Diagram (Prism v2.5 / Migration v17)

> **版本**: v2.5 (Migration v17)
> **更新日期**: 2026-06-19
> **注意**: 本圖以 `docs/SCHEMA.md` 的現行 Go primary schema 為準。AI 相關欄位與 `Embeddings` / `AI_Tasks` 已於 v14 移除；五個系統分類身份已於 v17 改由 `Categories.system_key` 表示，使用者改名只寫 `name_override`。

```mermaid
erDiagram
    Notes {
        INTEGER id PK
        TEXT title
        TEXT content
        TEXT remarks
        TEXT cover_image
        TEXT cover_position
        TEXT editor_layout
        BOOLEAN is_pinned
        BOOLEAN is_archived
        INTEGER sort_order
        INTEGER category_id FK
        INTEGER parent_id FK
        TEXT prompt_params
        DATETIME created_at
        DATETIME updated_at
    }

    Categories {
        INTEGER id PK
        TEXT name UK
        TEXT icon
        INTEGER sort_order
        BOOLEAN is_default
        TEXT system_key UK
        TEXT name_override
    }

    Tags {
        INTEGER id PK
        TEXT name UK
    }

    Note_Tags {
        INTEGER note_id PK,FK
        INTEGER tag_id PK,FK
    }

    Source_Urls {
        INTEGER id PK
        INTEGER note_id FK
        TEXT url
    }

    Note_History {
        INTEGER id PK
        INTEGER note_id FK
        TEXT content
        TEXT diff_summary
        DATETIME created_at
    }

    Note_Attachments {
        INTEGER id PK
        INTEGER note_id FK
        TEXT file_path
        TEXT file_type
        TEXT title
        INTEGER size_bytes
        INTEGER is_auto_extracted
        DATETIME created_at
    }

    Schema_Meta {
        TEXT key PK
        TEXT value
    }

    Notes_FTS {
        TEXT title
        TEXT content
    }

    Categories ||--o{ Notes : "category_id"
    Notes ||--o{ Notes : "parent_id (variant)"
    Notes ||--o{ Note_Tags : "has"
    Tags ||--o{ Note_Tags : "used in"
    Notes ||--o{ Source_Urls : "references"
    Notes ||--o{ Note_History : "versioned by"
    Notes ||--o{ Note_Attachments : "has"
    Notes ||--|| Notes_FTS : "indexed by triggers"
```

---

## 主要關聯說明

| 關聯 | 說明 |
|------|------|
| `Categories` → `Notes` | `Notes.category_id` FK；刪除分類時，有筆記的分類需指定搬移目標，預設分類不可刪 |
| `Notes` → `Notes` | `parent_id` 自參照，支援 variant / duplicate-as-variant lineage；目前只表示 direct parent / direct children，不是完整版本樹 |
| `Notes` ↔ `Tags` | N:M 透過 `Note_Tags` 中間表；`Tags.name` 使用 `COLLATE NOCASE` uniqueness |
| `Notes` → `Source_Urls` | 來源 URL 拆表保存，API 層仍以陣列接收 / 回傳 |
| `Notes` → `Note_History` | 每次內容更新可保留歷史版本，最多保留 50 版 |
| `Notes` → `Note_Attachments` | `.md` / `.txt` / `.markdown` 文字附件與長文自動分離檔案；實體檔位於 Go external data dir 下 |
| `Notes` → `Notes_FTS` | FTS5 virtual table 只索引 `title` / `content`，由 INSERT / UPDATE / DELETE triggers 同步 |

## 分類身份備註

`Categories.name` 仍保留 legacy canonical name 與舊資料相容用途。現行前端顯示五個系統分類時，不再用語系文字判斷身份，而是讀 `system_key`：

| system_key | 說明 |
|---|---|
| `prompt` | 提示詞 / Prompt |
| `note` | 筆記 / Note；`is_default=1`，刪除分類搬移目標 |
| `tutorial` | 教學 / Tutorial |
| `data` | 資料 / Data |
| `inspiration` | 靈感 / Inspiration |

使用者改名系統分類時只寫 `name_override`；清除 override 後回到目前語系的預設顯示名稱。
