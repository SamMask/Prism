# Prism Frontend Redesign Plan

> **用途**: 把 `docs/New_UI/Prism Redesign - standalone.html` 的 UI 原型與 `Prism_Go_模組逐步重構計劃報告.md` 的 Go shadow backend 路線整合成可執行的前端改版規劃。
> **最後更新**: 2026-05-27
> **狀態**: 規劃中；本文件不是已完成清單。

---

## 1. 來源與採納邊界

### 1.1 來源

- `docs/New_UI/Prism Redesign - standalone.html`
  - 可採納: shell / sidebar / topbar / command palette / filter strip / card density / reading view / editor modal / settings tabs 的互動方向。
  - 不直接採納: 原型內 sample data、`collections` 資料模型、tweak panel 作為正式產品功能、prototype-only inline code。
- `Prism_Go_模組逐步重構計劃報告.md`
  - 可採納: 先固定 API contract、做 Python vs Go response diff、Go read-only shadow backend、React dist embed、前端替換不阻塞 Go Phase 0。
  - 不直接採納: 任何會提前碰正式 `knowledge.db`、POST/PUT/DELETE、檔案系統操作或新產品型態的擴 scope。

### 1.2 不變的產品定位

Prism 仍是本地優先、SQLite、純關鍵字搜尋、React SPA + REST API 的個人 Headless KMS。新 UI 只能改善日常瀏覽、搜尋、分類/標籤篩選、閱讀、編輯、Prompt Builder 與設定體驗；不得引入 AI/ML、協作 wiki、realtime、workspace permission、timeline/social feed 或 plugin platform。

### 1.3 Schema 邊界

原型裡的「清單 / collections / 智慧資料夾」目前不是 Prism DB contract。除非後續先完成 schema proposal、migration、API contract 與 tests，否則前端不得新增 `collections` 表或假裝它已存在。Phase 18 先用現有 `Categories`、`Tags`、`Notes.is_archived`、`Notes.is_pinned`、`sort_order` 與 `GET /api/notes` query contract。

---

## 2. 推薦分期

### Phase 18.0 — Readiness / Contract Lock

目標: 在任何大 UI rewrite 或 Go shadow backend 前，先把現有行為固定成可比對的 contract。

- Golden response fixtures: `GET /api/test`、`GET /api/categories`、`GET /api/tags`、`GET /api/notes`、`GET /api/notes/<id>`。
- Endpoint side-effect map: readonly / DB-write / file-write / server-local-only。
- UI route map: Home、Prompt Builder、Settings、NoteEditor、Preview、Sidebar filters 的現況流程與驗收點。
- API manifest draft: 先文件化 read-only tool surface，不改 runtime。

驗收:

- Python endpoint fixtures 可重跑並 diff。
- `docs/API_REFERENCE.md` 與 fixtures 不互相矛盾。
- `docs/TODO.md` 有拆好的 atomic tasks。

### Phase 18.1 — Shell And Navigation Refresh

目標: 先改可逆的前端 shell，不碰 backend/schema。

- `Layout` / `Sidebar` / `Header` 對齊原型的密度、資訊層級與 view switcher。
- 保留既有 route-aware category/tag filter: 非 Home 點擊要回 Home 並套用篩選。
- 加入 grid / list / compact list 的顯示模式時，先用 local UI state，不新增 server persistence。
- command palette 先做 navigation + recent notes + create actions，不包裝危險寫入。

驗收:

- `cd frontend && npx tsc --noEmit`
- `cd frontend && npm run build`
- Browser flow: category/tag filter、view mode、command palette、settings navigation。

### Phase 18.2 — Reading And Editor Workflow

目標: 改善閱讀與編輯入口，但保留已成立的 Preview Editing UX。

- Reading view 可以採納原型的專注閱讀面板與快速動作。
- `NoteEditor` 繼續重用既有 hooks: `useNoteForm`、`usePasteHandler`、`useDragDrop`、`useNoteAttachments`、`useNoteHistory`、`usePromptExtraction`。
- `EditablePreview` 保持「預覽中就地切小型 Markdown 區塊」策略，不引入大型 WYSIWYG editor。
- 附件與圖片操作沿用現有 `AttachmentPanel` / `ImageManagementPanel` / `imageReferences` 邏輯。

驗收:

- Preview 內可改文字、移除圖片引用。
- 貼圖 / 拖曳上傳 / 附件 / history 行為不退化。
- Browser console 無新增 warn/error。

### Phase 18.3 — Prompt Builder And Settings Re-layout

目標: 重新整理低頻但重要的工具頁，而不是新增功能。

- Prompt Builder 可以採納原型的 preview / form density / action hierarchy。
- Settings 可採納外觀、資料、搜尋、部署、關於分頁，但各 tab 只搬現有功能。
- Server dashboard、backup、update、port config 保持既有 API 邊界。

驗收:

- Prompt Builder 產出與儲存流程維持現有 contract。
- Settings 每個現有 section 可開、可操作、錯誤訊息正常。

### Phase 18.4 — Go Read Shadow Backend

目標: 等 fixtures 與 UI read flow 明確後，照 Go 報告啟動 read-only shadow backend。

- Go server 只連 `*_test.db` / `*_dev.db`，開發期禁止連正式 `knowledge.db`。
- 實作 `GET /api/test`、categories、tags、notes list、note detail。
- 保留 React dist embed 作為 single binary 發布方向，但不改目前 Flask 穩定主線。
- 前端不為 Go Phase 0 改 API contract。

驗收:

- Python (5000) vs Go (5001) response diff 通過。
- Go 端未實作任何 POST/PUT/DELETE。
- `pytest tests/ -v` 對 Python 主線保持綠燈。

---

## 3. 明確暫緩

- `collections` / smart folder DB schema。
- server-side UI preference persistence。
- Wails / desktop mode rewrite。
- collaboration / comments / permissions / realtime。
- AI chat、embedding、semantic search、reranker、agent runner。
- upload / attachment / cleanup / export 的 Go 版，直到 read-only 與 DB-write phases 穩定。

---

## 4. 後續實作規則

1. 每次只 promote 一個最小 task，先以 `docs/TODO.md` 的 atomic task 為準。
2. UI 改版每輪必須有 browser flow 驗證；不能只靠 build。
3. Go backend 每輪必須有 Python vs Go response diff；不能只靠手動 curl success。
4. 有 DB/schema/API contract 變動時，同步 `docs/SCHEMA.md`、`docs/API_REFERENCE.md`、`docs/ARCHITECTURE.md`。
5. `AGENTS.md` 與 `CLAUDE.md` 若再調整開發規則，必須保持鏡像。
