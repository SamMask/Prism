# Entity Relationship Diagram (Prism v2.3+)

> **版本**: v2.3.0 (Migration v14)
> **更新日期**: 2026-04-04
> **注意**: AI 相關欄位（`ai_summary`、`ai_tags`、`embedding_status`）及 `Embeddings`、`AI_Tasks` 表已於 v14 移除。詳見 `SCHEMA.md` Section 8。

```mermaid
erDiagram
    Notes {
        INTEGER id PK
        TEXT title
        TEXT content
        INTEGER category_id FK
        TEXT created_at
        TEXT updated_at
        INTEGER is_pinned
        INTEGER is_archived
        TEXT remarks
        TEXT cover_image
        TEXT cover_position
        TEXT source_urls
        TEXT prompt_params
        INTEGER sort_order
        INTEGER parent_id FK
        TEXT parent_title
    }

    Categories {
        INTEGER id PK
        TEXT name
        TEXT icon
        INTEGER is_default
        INTEGER sort_order
        TEXT created_at
    }

    Tags {
        INTEGER id PK
        TEXT name
        TEXT created_at
    }

    Note_Tags {
        INTEGER note_id FK
        INTEGER tag_id FK
    }

    Note_History {
        INTEGER id PK
        INTEGER note_id FK
        TEXT title
        TEXT content
        TEXT changed_at
    }

    Note_Attachments {
        INTEGER id PK
        INTEGER note_id FK
        TEXT filename
        TEXT file_path
        INTEGER file_size
        TEXT created_at
    }

    Schema_Meta {
        INTEGER version PK
        TEXT applied_at
    }

    Notes_FTS {
        TEXT content "虛擬表 FTS5，自動同步 Notes"
    }

    Notes ||--o{ Note_Tags : "has"
    Tags ||--o{ Note_Tags : "used in"
    Notes ||--o{ Note_History : "versioned by"
    Notes ||--o{ Note_Attachments : "has"
    Categories ||--o{ Notes : "contains"
    Notes ||--o| Notes : "parent_id (variant)"
```

---

## 主要關聯說明

| 關聯 | 說明 |
|------|------|
| `Notes` → `Categories` | `category_id` FK，刪除分類時筆記移至預設分類 |
| `Notes` → `Notes` | `parent_id` 自參照，支援 Prompt 卡片變體 (Phase 3.7) |
| `Notes` ↔ `Tags` | N:M 透過 `Note_Tags` 中間表 |
| `Notes` → `Note_History` | 每次 PUT /api/notes/:id 自動記錄，最多保留 50 版 |
| `Notes` → `Note_Attachments` | 長文分離後的 `.md` 附件，或手動上傳的文字附件 |
