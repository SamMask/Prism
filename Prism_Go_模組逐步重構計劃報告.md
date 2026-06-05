# Prism Go 模組逐步重構盤點報告

> 掃描日期: 2026-05-17 | 策略: 漸進替換，Python 保持可用

---

## 2026-06-05 主線校準：本機封裝目標 + Pi 部署不變

> **白話說明**：
> 這一段是在把 Go 重構重新定為 Prism 的主線，而不是繼續從前端找零碎小修。
> 最後目標是：Prism 可以有明確的本機封裝執行方式，但使用者日常使用仍維持部署在樹莓派，透過 systemd + Caddy + 既有資料目錄運行。
> 使用者現在不會立刻看到功能差異，因為這是 roadmap / ownership 規劃；真正改 runtime、DB、file system、Caddy 或 Pi 前都還需要下一個明確 gate。
> 這段明確不會改：不直接實作 Go file-read/body scan、不擴 Go writes/files/migrations、不移除 Python、不改 frontend default、不改 Caddy、不部署 Pi、不擴 public exposure。

### Risk level

`P0 safety-critical` for Go ownership / runtime / DB / file system / migration / Caddy / Pi deploy.

### Final Target

- **Local packaged run**: Prism should eventually have a clear local packaging path for Windows/dev machines: bundled React `dist`, Go runtime artifact, explicit config, external data dir, and repeatable local startup.
- **Pi deployment unchanged**: Daily/real usage remains Raspberry Pi deployment with `prism.service`, Caddy, existing data dir, SQLite WAL mode, and the established backup/rollback discipline.
- **Gradual ownership transfer**: Go takes ownership one surface at a time. Python remains the owner for every route class not explicitly promoted and verified.
- **No implicit cutover**: A passing local build, single curl, or docs update never means Go owns a production surface.

### Current Runtime Truth

- Go currently owns only the hardened permanent read-only Caddy-routed GET surface already verified in Phase 19-20: `/api/test`, `/api/categories`, `/api/tags`, `/api/notes`, and numeric `/api/notes/{id}`.
- Python still owns writes, files/attachments, import/export, cleanup, system/server routes, migrations, frontend/static serving, and any unreviewed `/api/notes/...` path.
- Go `GET /api/notes?q=...` has DB-only attachment metadata parity for `Note_Attachments.title` / `file_path`.
- Text attachment body search is still Python-owned because it performs request-time file scanning.

### Roadmap Big Items

| Order | Workstream | Risk | Purpose | Completion Criteria |
|---|---|---|---|---|
| 1 | Runtime truth and roadmap consolidation | P0 | Keep future agents on the Go track and stop frontend-polish drift | `docs/TODO.md`, this report, and `docs/ARCHITECTURE.md` agree on active Go next step |
| 2 | Go read parity completion | P0 | Close the remaining read-only gap: text attachment body search | File-read contract, path safety, performance bounds, Python vs Go diff fixtures |
| 3 | Go write surface selection | P0 | Choose the first DB-write surface without file side effects | Side-effect map, transaction/rollback plan, CSRF/local-only boundary, fixture plan |
| 4 | First Go write route | P0 | Promote one smallest write route to Go | Parity tests, rollback proof, Python fallback/owner boundaries |
| 5 | File / attachment ownership | P0 | Move upload/attachment/cleanup/export/import only after DB writes are stable | Data-dir ownership, filesystem safety, backup/restore, Pi rollback |
| 6 | Migration / DB ownership decision | P0 | Decide whether migrations stay Python-owned or move partly to Go | Idempotent migration tests, schema lock, rollback and production safety plan |
| 7 | Local packaging track | P1/P0 mixed | Make local packaged execution repeatable | Local artifact, external data dir, config contract, smoke tests |
| 8 | Pi deployment track | P0 | Keep real usage on Pi while Go ownership expands | Pi preflight, service health, Caddy boundary, backups, rollback |
| 9 | Python reduction/removal | P0 | Only after every owned surface has a Go or explicit retained-Python decision | No orphan Python-owned runtime surfaces; rollback and release plan complete |

### Active Next Gate

`23.1 Go file-read parity plan gate is complete`.

It was **plan-only**: it defined explicit `--data-dir`, `docs/attachments` relative roots, `md` / `markdown` / `txt`, canonical path defense, rejection of `..` / symlink escape / absolute external path, 1 MiB per file, 200 files / 5 MiB / 250 ms per query, UTF-8 replacement decoding, Python vs Go copied-DB fixture cases, and rollback boundaries. It did not implement Go file scanning, change Caddy/systemd/frontend defaults, touch production DB, deploy Pi, remove Python, or expand public exposure.

`23.2 Go file-read parity implementation gate is complete`.

It implemented bounded local/copied-DB read-only text attachment body search inside the 23.1 contract. Go `GET /api/notes?q=...` can now scan text bodies for `md` / `markdown` / `txt` attachments under explicit `--data-dir` `docs/attachments`, then merge matching note ids into the existing search query. It still rejects traversal, absolute/volume/UNC/colon paths, symlink escape, unsupported extension, oversized files, missing files, and read errors as non-matches. It did not change Caddy/systemd/frontend defaults, touch production DB, deploy Pi, add Go writes/files/migrations, remove Python, or expand public exposure.

`23.3 Go write surface selection gate is complete`.

It was **plan-only**: it selected `PUT /api/tags/<tag_id>` (`tag_rename`) as the first Go write implementation candidate. The selected route only updates `Tags.name`, has no file/cascade/bulk/process side effects, and can be verified with Python-vs-Go response plus DB-state parity fixtures. It rejected or deferred broader notes writes, nested note actions, duplicate/reorder/batch, category delete, tag delete/merge, attachments/uploads/cleanup/import/export/system/server/config. It did not implement Go writes, change production DB, change Caddy/systemd/frontend defaults, deploy Pi, remove Python, or expand public exposure.

`23.4 First Go write route implementation gate is complete`.

It implemented the first Go write candidate as local/copied-DB parity only. Go now supports `PUT /api/tags/<tag_id>` behind an explicit `--enable-tag-write` / `PRISM_GO_ENABLE_TAG_WRITE=1` flag. Without that flag, the runtime remains `get-read-only` and keeps SQLite `query_only = ON`. The implementation updates only `Tags.name`, preserves `Tags.id` and `Note_Tags`, uses a transaction, and matches current Python response / DB-state behavior for success, validation errors, missing tag, and duplicate exact-name checks. It did not change Caddy/systemd/frontend defaults, touch production DB, deploy Pi, remove Python, or expand public exposure.

`23.5 Go DB-only write expansion gate` is the next recommended step, pending explicit approval. It should first decide whether tag rename needs a live/local routing gate before broader DB-only write expansion, then resolve or explicitly defer the `Tags.name` NOCASE schema/documentation discrepancy before tag CUD expansion.

---

## A. 模組分級總覽

### 🟢 Tier 1 — 可優先替換（唯讀、低耦合、無副作用）

| 模組 | Python 檔 | Endpoints | DB 表 | 寫DB | 改檔案 | Go難度 |
|------|----------|-----------|-------|------|--------|--------|
| Health | app.py | `GET /api/test` | 無 | ❌ | ❌ | ⭐ |
| Categories 讀取 | categories.py | `GET /api/categories` | Categories, Notes | ❌ | ❌ | ⭐ |
| Tags 讀取 | tags.py | `GET /api/tags` | Tags, Note_Tags | ❌ | ❌ | ⭐ |
| Notes 列表 | notes/crud.py | `GET /api/notes` | Notes, Tags, Categories, Note_Tags, Source_Urls | ❌ | ❌ | ⭐⭐ |
| Notes 詳情 | notes/crud.py | `GET /api/notes/{id}` | 同上 | ❌ | ❌ | ⭐⭐ |
| History 讀取 | notes/history.py | `GET /api/notes/{id}/history` | Note_History | ❌ | ❌ | ⭐ |
| Migration Status | system.py | `GET /api/system/migration-status` | Schema_Meta | ❌ | ❌ | ⭐ |
| Consistency Check | system.py | `GET /api/system/check-consistency` | 全表掃描 | ❌ | ❌ | ⭐⭐ |

**風險**: 極低。全部唯讀，前端零修改即可驗證 response 一致性。

### 🟡 Tier 2 — 中期替換（寫入 DB，但不碰檔案系統）

| 模組 | Endpoints | 寫DB | 改檔案 | Go難度 |
|------|-----------|------|--------|--------|
| Notes 建立 | `POST /api/notes` | ✅ | ❌ | ⭐⭐ |
| Notes 更新 | `PUT /api/notes/{id}` | ✅ | ❌ | ⭐⭐ |
| Notes 刪除 | `DELETE /api/notes/{id}` | ✅ | ✅ 刪圖片 | ⭐⭐⭐ |
| Pin/Archive | `POST .../pin\|archive` | ✅ | ❌ | ⭐ |
| Duplicate | `POST .../duplicate` | ✅ | ❌ | ⭐⭐ |
| Reorder | `PUT /api/notes/reorder` | ✅ | ❌ | ⭐ |
| Batch Ops | `POST /api/notes/batch/*` | ✅ | ✅ 批刪圖 | ⭐⭐⭐ |
| Categories CUD | `POST\|PUT\|DELETE /api/categories/*` | ✅ | ❌ | ⭐⭐ |
| Tags CUD+Merge | `PUT\|DELETE /api/tags/*`, merge | ✅ | ❌ | ⭐⭐ |

### 🔴 Tier 3 — 最後替換（檔案系統操作、高風險）

| 模組 | Python 檔 | 行數 | 改檔案 | Go難度 |
|------|----------|------|--------|--------|
| Upload | upload.py | 597 | ✅ 寫圖片/縮圖 | ⭐⭐⭐⭐ |
| Attachments | attachments.py | 490 | ✅ 讀寫附件 | ⭐⭐⭐⭐ |
| Export | export.py | 444 | ✅ 建ZIP | ⭐⭐⭐ |
| Import | notes/import_.py | 242 | ✅ 可能下載圖 | ⭐⭐⭐ |
| Cleanup | cleanup.py | 638 | ✅ 刪/修圖片 | ⭐⭐⭐⭐ |
| Server | server.py | 567 | ✅ 日誌/備份 | ⭐⭐⭐⭐ |

### ⚪ Tier 4 — 暫緩

| 模組 | 理由 |
|------|------|
| prompt_options.py | 純 JSON CRUD，非核心，需求可能變動 |
| wizard_options.py | 同上 |
| Port Config | Go 版可能用不同端口策略 |
| Update Check | Go release 策略可能不同 |
| Desktop Mode (pywebview) | Go 用 Wails，完全不同架構 |

---

## B. 關鍵模組詳細盤點

### B1. `GET /api/categories`
- **Python**: categories.py L14-44
- **SQL**: `SELECT c.*, (SELECT COUNT(*) FROM Notes WHERE category_id=c.id) FROM Categories ORDER BY sort_order`
- **DB 表**: Categories (讀), Notes (COUNT)
- **檔案系統**: 無依賴
- **前端**: appStore.ts `fetchCategories()`, usePromptBuilder.ts L530
- **驗收**: JSON `{status, data: [{id, name, icon, sort_order, is_default, count}]}`

### B2. `GET /api/tags`
- **Python**: tags.py L14-46
- **SQL**: `SELECT t.id, t.name, COUNT(nt.note_id) FROM Tags LEFT JOIN Note_Tags GROUP BY t.id`
- **DB 表**: Tags, Note_Tags
- **檔案系統**: 無依賴
- **前端**: appStore.ts `fetchTags()`
- **驗收**: JSON `{status, data: [{id, name, count}]}`

### B3. `GET /api/notes` (列表+分頁)
- **Python**: notes/crud.py + query_builder.py (296行)
- **DB 表**: Notes, Categories, Tags, Note_Tags, Source_Urls, Notes_FTS, Attachments
- **依賴**: QueryBuilder Fluent API、FTS5 搜尋、附件內容搜尋 (search.py)
- **查詢參數**: page, per_page, q, type, category_id, tags, tag_mode, sort, pinned_only, archived
- **前端**: appStore.ts `fetchNotes()` — 應用最核心資料來源
- **Go 難度**: ⭐⭐ (Phase 0 先做基本分頁，Phase 1 加搜尋)
- **驗收**: `{status, data: [...], pagination: {total, page, per_page, total_pages}}`

### B4. `GET /api/notes/{id}` (詳情)
- **Python**: notes/crud.py L200-280
- **SQL**: 複雜 JOIN + `json_group_array(json_object(...))` 聚合 tags/urls/attachments
- **前端**: api.ts `getNote(id)` — 編輯器資料來源
- **Go 注意**: `json_group_array` 可保留 (SQLite 原生支持) 或改為多查詢組裝
- **驗收**: 完整 Note 含 tags[], urls[], parent_title

---

## C. 建議遷移順序

```
Phase 0 (骨架)         Phase 1 (唯讀完整)      Phase 2 (寫入)          Phase 3 (檔案)
──────────────         ──────────────────      ──────────────          ──────────────
• Go server 啟動        • QueryBuilder 移植     • CRUD notes            • Upload
• embed React dist     • FTS5 搜尋             • Categories CUD        • Attachments
• 連接複製 DB           • 附件內容搜尋           • Tags CUD+merge        • Export/Import
• GET /api/test        • GET notes 完整版       • Pin/Archive/Dup       • Cleanup
• GET categories       • History 讀取           • Batch operations      • Server dashboard
• GET tags             • System 唯讀            • WAL checkpoint
• GET notes (基本)     
• GET notes/{id}       
```

### 核心原則
1. **先唯讀後寫入** — Phase 0-1 全部只讀
2. **先無副作用後有副作用** — 不碰檔案系統直到 Phase 3
3. **Shadow backend** — Go 平行運行，用複製 DB 驗證
4. **永不碰正式 DB** — 開發期只用 `knowledge_test.db`
5. **前端不改** — API contract 100% 一致

---

## D. Phase 0 最小可行目標

### 目標
Go server 啟動、serve React SPA、5 個唯讀 endpoint 回傳與 Python 完全一致的 JSON。

### Endpoints
1. `GET /api/test` → `{"status":"success","message":"API is working"}`
2. `GET /api/categories` → 分類列表 (含筆記計數)
3. `GET /api/tags` → 標籤列表 (含使用計數)
4. `GET /api/notes?page=1&per_page=20` → 筆記列表 (基本分頁)
5. `GET /api/notes/{id}` → 單筆詳情

### 不做
- ❌ 任何 POST/PUT/DELETE
- ❌ 檔案上傳/下載/清理
- ❌ 搜尋功能 (Phase 1)
- ❌ 修改前端
- ❌ 觸碰正式 knowledge.db

---

## E. 測試策略

### E1. Python/Go Response 對照
```bash
# 同一 DB 副本，Python (5000) vs Go (5001)
curl localhost:5000/api/categories | jq . > py.json
curl localhost:5001/api/categories | jq . > go.json
diff py.json go.json  # 必須完全一致
```

### E2. Fixture DB
- 複製 `knowledge.db` → `knowledge_test.db`
- Go 只連接測試 DB
- 測試前重新複製，確保冪等

### E3. 正式 DB 保護
- Config 層硬編碼禁止連接 `knowledge.db`
- 只允許 `*_test.db` 或 `*_dev.db`
- 生產模式需明確 flag: `--production=true`

### E4. 前端手動驗收
- [ ] 首頁載入顯示筆記卡片
- [ ] 側邊欄分類正確 (含計數)
- [ ] 側邊欄標籤正確 (含計數)
- [ ] 點擊卡片載入詳情
- [ ] 分頁滾動載入
- [ ] 分類/標籤過濾

---

## F. 結論

### ✅ 第一批替換 (Phase 0, 5 endpoints)
1. `GET /api/test`
2. `GET /api/categories`
3. `GET /api/tags`
4. `GET /api/notes` (基本分頁)
5. `GET /api/notes/{id}`

### ❌ 不碰的模組
- upload.py, attachments.py, cleanup.py, export.py, import_.py, server.py, prompt/wizard_options.py

### Phase 0 任務清單 (可交給 Codex/Claude)

```
1. 初始化: go mod init, 安裝 chi/sqlx/modernc-sqlite
2. Config: 讀 PORT/DB_PATH 環境變數, 禁止連 knowledge.db
3. Database: Open(), FK+WAL, MaxOpenConns(1)
4. Model: Note/Category/Tag/APIResponse 結構體 (JSON tag 對齊 Python)
5. CSRF middleware: 檢查 Origin/Referer
6. 5 個唯讀 handler (見上方 SQL)
7. SPA: go:embed frontend/dist, fallback index.html
8. main.go: config → db → router → http.ListenAndServe
9. 驗收: 啟動 → 瀏覽器看到 SPA → 5 個 API diff 通過
```

### 禁止事項
- 不要實作 POST/PUT/DELETE
- 不要修改前端
- 不要連接 knowledge.db
- 不要重新設計產品功能

---

## G. GitHub 參考專案與採納邊界（2026-05-26 補充）

> 目的：這些專案只作為 Go 重構與功能取捨的參考，不代表 Prism 要改成它們的產品型態。Prism 仍維持本地優先、SQLite、純關鍵字搜尋、React SPA + REST API、無 AI/ML 依賴。

### G1. 參考專案清單

| 專案 | 為什麼值得看 | 可借鏡 | 不採納 / 暫緩 |
|------|-------------|--------|--------------|
| [usememos/memos](https://github.com/usememos/memos) | Go + React 的自架筆記工具，Markdown-native、單一 Go binary、REST/gRPC API、支援 SQLite/MySQL/PostgreSQL | Go API server 切分、單 binary 發布、Markdown 資料可攜性、API-first 思維 | 不採納 timeline / microblog / social network 產品型態；不引入多 DB 支援作為 Phase 0 目標 |
| [silverbulletmd/silverbullet](https://github.com/silverbulletmd/silverbullet) | Browser-based Markdown PKM，TypeScript frontend + Go backend，重視 Live Preview / local space | 編輯器與 Preview 的互動邊界、Go backend + 前端 bundle 的開發流程、Markdown page model 的可攜性 | 不採納 Lua plugin / programmable platform；Prism 不做可程式化筆記系統 |
| [pocketbase/pocketbase](https://github.com/pocketbase/pocketbase) | Go + SQLite 的 portable backend 範例，內建 REST-ish API、檔案與 user 管理 | SQLite lifecycle、single executable、migration/test 組織、admin/debug tooling 的思路 | 不直接改用 PocketBase；Prism 既有 schema/API contract 必須保留，且 PocketBase 未到 v1.0 前不把它當穩定框架依賴 |
| [miniflux/v2](https://github.com/miniflux/v2) | 非筆記產品，但 Go server 風格極簡、意見明確、API/背景作業/部署紀律清楚 | 小核心、少抽象、config/migration/test discipline、server package 組織 | 不採納 PostgreSQL-only 路線；Prism 仍以 SQLite + WAL 為核心 |
| [siyuan-note/siyuan](https://github.com/siyuan-note/siyuan) | TypeScript + Golang 的 local-first PKM，重視 self-hosted、資產、同步與知識庫操作 | 檔案/圖片資產管理、local-first、跨裝置同步的長期設計參考 | 不採納 OCR/AI/chat/local model 功能；AGPL 專案只作設計參考，不搬 code |
| [TriliumNext/Trilium](https://github.com/TriliumNext/Trilium) | 大型個人知識庫，階層筆記、clone、rich editor、圖片與歷史能力完整 | 大型 KB 的 note detail、history、rich editor、圖片 UX 參考 | 不採納深層樹狀/clone 資料模型作為 Prism 主模型；避免把簡單筆記庫變成完整 PKM |
| [docmost/docmost](https://github.com/docmost/docmost) / [outline/outline](https://github.com/outline/outline) | 協作型 wiki / knowledge base，權限、歷史、附件、搜尋與頁面 UX 成熟 | 可作 frontend rewrite 時的頁面資訊密度、歷史/附件 UI、搜尋 UX 參考 | Prism 不是多人協作 wiki；不引入 realtime collaboration、workspace permission、comment system |

### G2. 重構時機判斷

**結論：方向要在重構時就帶進去，但不要為了參考專案提前擴 scope。**

| 時機 | 要做 | 不做 |
|------|------|------|
| 重構前 | 補 contract / golden response 測試、整理 API response fixture、確認每個 endpoint 的 DB/檔案副作用邊界 | 不先重寫前端、不抽象化 service layer、不導入新 framework |
| Phase 0-1（唯讀 Go shadow backend） | 參考 Memos / Miniflux / PocketBase 的 Go server discipline：小 router、小 handler、明確 repository、SQLite lifecycle、React dist embed、Python vs Go response diff | 不做 POST/PUT/DELETE、不碰正式 DB、不做多 DB、不換 schema |
| Phase 2（寫入 DB） | 引入交易邊界、idempotent mutation、回滾測試、與 Python 行為對照 | 不把寫入 API 順手改成新 contract |
| Phase 3（檔案系統） | 參考 SiYuan / Trilium 的 asset safety：引用移除與實體刪檔分離、孤兒檔檢查、批次刪除保守化 | 不把 upload/cleanup/export 提前塞進 Phase 0 |
| Frontend replacement | 等 Go read API contract 穩定後再啟動；可借鏡 SilverBullet / Trilium / Docmost 的 editor 與 attachment UX | 不讓 frontend rewrite 阻塞 Go Phase 0；不為協作 wiki 功能改產品定位 |

### G3. 對 Prism 的具體採納原則

1. **Memos 路線只採 architecture，不採產品型態**：Go binary + API-first + Markdown 可攜性值得學；timeline/social 功能不進 Prism 主線。
2. **SilverBullet / Trilium 只採 editor UX 的局部靈感**：例如 Preview 內就地編輯、圖片引用刪除、history/attachment 視覺整理；不採 plugin/scriptable platform。
3. **PocketBase 只當 Go + SQLite 參考，不當依賴**：Prism 已有 SQLite schema、migrations、REST contract，直接套 PocketBase 會增加 migration 成本。
4. **Miniflux 當 anti-bloat 樣板**：少抽象、清楚 config、清楚 migration、測試夠用；這比大型框架更符合 Prism。
5. **Docmost / Outline 只看高階 UX**：搜尋、頁面歷史、附件呈現、資訊密度可參考；協作、權限、realtime 不納入。

### G4. API 給 LLM 調用的邊界

Prism 不需要加 AI 功能，但可以把既有 REST API 整理成更適合 LLM tool 調用的形式：

- **可以做**：補一份 machine-readable API manifest / OpenAPI-like JSON，列出可讀 endpoint、參數、response schema、錯誤碼、side effect 等級。
- **可以做**：把 search / notes detail / tags / categories / export metadata 做成穩定 read-only tool surface，讓外部 LLM client 呼叫。
- **可以做**：每個 tool endpoint 標記 `readonly: true/false`、`requires_confirmation: true/false`、`local_only: true`。
- **暫緩**：Prism 內建 chat UI、embedding、semantic search、reranker、agent runner、背景任務代理。
- **禁止**：引入 numpy / torch / sentence-transformers / local model runtime，或讓 LLM API 改動既有資料時繞過 Prism 的確認與權限邊界。

### G5. 更新後的建議 Roadmap 插入點

```
Phase -1 (重構準備)
• Golden response fixtures: Python API 目前輸出固定下來
• Endpoint side-effect map: readonly / DB-write / file-write
• API manifest draft: 給人與 LLM tool client 看，不改 runtime

Phase 0-1 (Go read shadow backend)
• Go server + SQLite + embed SPA
• categories/tags/notes/detail/system readonly endpoints
• Python vs Go response diff harness

Phase 2 (DB writes)
• notes/categories/tags mutation
• transaction tests
• write response diff / DB diff

Phase 3 (files)
• upload / attachments / cleanup / export
• reference removal != physical deletion
• orphan scan + batch delete confirmation

Phase 4 (frontend replacement, optional)
• editor / preview / image UX refinement
• search results and attachment browsing
• no collaboration/wiki scope creep
```
