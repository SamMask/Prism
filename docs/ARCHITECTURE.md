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

## Planned Modernization Boundary

> 本節是 2026-05-27 的規劃邊界，不代表目前 runtime 已改成 Go 或新 UI。

### Go Shadow Backend

`Prism_Go_模組逐步重構計劃報告.md` 定義的方向是平行 read-only shadow backend，而不是替換現有 Flask 主線：

```mermaid
flowchart LR
    FE[React SPA] --> PY[Flask API :5000]
    FE -. contract-compatible read checks .-> GO[Go Shadow API :5001]
    PY --> DB[(knowledge_test.db copy)]
    GO --> DB
```

- Phase 0-1 只允許 read-only endpoints: `/api/test`、categories、tags、notes list、note detail、system read checks。
- Go 開發期只連 `*_test.db` / `*_dev.db`；不得碰正式 `knowledge.db`。
- 驗收標準是 Python vs Go response diff，不是單次 curl success。
- 前端不得為 Go Phase 0 改 API contract。

Phase 18.4 的 repo-local scaffold 位於 `go-shadow/`：

- `go-shadow/main.go` 只註冊核心 GET read surface，沒有 Go write route、file route、maintenance route 或 `/api/server/*`。
- 啟動時必須明確傳入 copied DB，預設拒絕名為 `knowledge.db` 的正式 DB，並對 SQLite connection 設定 `PRAGMA query_only = ON`。
- `tests/test_phase18_go_shadow_contract.py` 是 Python vs Go response diff harness；Go CLI 可用時會用同一 pytest `temp_db` 啟動 Go server 比對 Flask client JSON。沒有 Go CLI 時 runtime diff 會 skip，但 static read-only gate 仍會跑。
- 目前 Go shadow 是 contract verification target，不是前端流量來源。

### Frontend Redesign Intake

`docs/New_UI/Prism Redesign - standalone.html` 是 UI 原型參考，整合規劃在 `docs/FRONTEND-REDESIGN-PLAN.md`：

- 可採納: shell / sidebar / topbar / command palette / filter strip / card density / reading view / editor modal / settings tabs。
- 必須保留: 現有 React + Vite + Zustand + Tailwind stack、route-aware filters、`EditablePreview`、NoteEditor hooks、純關鍵字搜尋契約。
- 暫緩: `collections` / smart folders schema、server-side UI preference persistence、Wails、AI、collaboration、realtime。
- UI 改版驗收除了 typecheck / build，也需要 Browser flow 驗證實際工作流。
