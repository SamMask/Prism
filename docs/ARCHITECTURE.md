# System Architecture (C4 Model)

```mermaid
C4Context
      title C4 Container Diagram - Prism (Headless KMS)

      Person(user, "User", "Content Creator / Knowledge Worker")
      Person(agent, "External Agent", "Claude Code / MCP / Custom Script")

      System_Boundary(prism, "Prism - Headless KMS") {

            Container(frontend, "Frontend SPA", "React, Vite, Zustand, Tailwind", "Modern UI for browsing and editing notes.")
            Container(backend, "API Server", "Python, Flask", "REST API, Business Logic, Card Search.")

            ContainerDb(sqlite, "Database", "SQLite (WAL Mode)", "Stores Notes, Tags, Categories, Attachments, Lineage.")
            ContainerDb(fs, "File System", "OS File System", "Stores Images, Thumbnails, .md Attachments.")
      }

      System_Boundary(integrations, "External Tools") {
            System_Ext(comfyui, "ComfyUI / Stable Diffusion", "Image Generation Source")
            System_Ext(clipper, "Web Clipper", "Browser Extension (Future)")
      }

      Rel(user, frontend, "Uses", "HTTPS/Browser")
      Rel(agent, backend, "API Calls", "JSON/REST")

      Rel(frontend, backend, "API Requests", "JSON/REST")
      Rel(backend, sqlite, "Reads/Writes", "sqlite3")
      Rel(backend, fs, "Reads/Writes", "File I/O")

      Rel(comfyui, fs, "Saves Images", "Watched Folder")
      Rel(clipper, backend, "Clips Content", "API")

      UpdateRelStyle(frontend, backend, $textColor="blue", $lineColor="blue")
      UpdateRelStyle(agent, backend, $textColor="green", $lineColor="green")
```

## Search Read Path

`GET /api/notes?q=...` 維持單一查詢入口：

- `Notes.title` / `Notes.content` 使用 SQLite FTS5 (`Notes_FTS`)。
- `Notes.remarks`、`Tags.name`、`Note_Attachments.title` / `file_path` 使用 SQL 關聯條件。
- 文字附件內容（`.md` / `.markdown` / `.txt`）由後端在 request 期間 read-only 掃描檔案內容，再把命中的 `note_id` 併回 SQL 條件。

此搜尋仍是純關鍵字比對，沒有 AI / embedding / 外部服務依賴。
