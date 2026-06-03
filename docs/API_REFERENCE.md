# Prism API Reference

> 用途：提供外部 Agent / 自動化工具（例如 `murmur厭世貓`）直接對接 Prism 的實際 API 契約。
> 基準：以目前 Flask 路由實作為準，不以舊前端型別或歷史文件為準。
> 最後確認：2026-05-27

---

## 1. 對接前先知道

### Base URL

- `http://<host>:<port>/api`

### 回應格式

除下載類型端點外，JSON 回應統一為：

```json
{
  "status": "success",
  "message": "optional",
  "data": {}
}
```

失敗時通常為：

```json
{
  "status": "error",
  "message": "error message"
}
```

### 安全限制

- Prism 沒有獨立 API Token / Bearer Token / 使用者認證機制，預設定位是本機 / 區網內受信環境。
- 不要把 Prism API 直接暴露到 public internet / 公網。
- 外部 Agent 對接建議在同機、trusted LAN、VPN、SSH tunnel，或受認證保護的 reverse proxy（例如 Caddy auth）下使用。
- `POST` / `PUT` / `DELETE` / `PATCH` 在生產模式會做簡易 CSRF 檢查：
  - 需要合法 `Origin` 或 `Referer`
  - 本機 dev server `localhost:5173/5174` 已在白名單
- `/api/server/*` 僅允許 `127.0.0.1` 或 `::1` 存取，遠端 Agent 不可直接呼叫。

### 歷史相容層

- `Notes.type` 已從資料庫移除。
- 部分 API 仍保留 `type` 作為「分類名稱字串」的相容欄位或查詢參數，不代表資料庫仍有 `type` 欄位。

### 建議對接範圍

如果你只是要讓外部 Agent 讀寫知識庫，優先使用這些端點：

1. `GET /notes`
2. `GET /notes/<id>`
3. `POST /notes`
4. `PUT /notes/<id>`
5. `DELETE /notes/<id>`
6. `GET /categories`
7. `GET /tags`
8. `POST /notes/<id>/attachments`
9. `GET /notes/<id>/attachments`
10. `GET /attachments/<id>`

---

## 2. Notes API

### GET `/api/notes`

取得筆記列表。

#### Query Params

| 參數 | 型別 | 說明 |
|---|---|---|
| `page` | int | 頁碼，預設 `1` |
| `per_page` | int | 每頁數量，預設 `20`，最大 `100` |
| `q` | string | 卡片搜尋關鍵字，後端會截斷到 200 字；搜尋範圍包含標題、內文、備註、附件標題 / 路徑 / 文字內容、標籤 |
| `type` | string | 分類名稱相容參數；不是 DB 欄位 |
| `category_id` | int | 分類 ID 過濾；前端應優先使用此欄位，避免分類改名造成 `type` 字串漂移 |
| `tags` | string | Tag ID 逗號分隔，例如 `1,2,3` |
| `tag_mode` | string | `AND` 或 `OR`，預設 `AND` |
| `include_archived` | bool | 是否包含封存筆記，預設 `false` |
| `archived` | bool | 只顯示封存筆記，預設 `false`；優先於 `include_archived` |
| `pinned_only` | bool | 只顯示置頂筆記，預設 `false` |
| `sort` | string | `updated` / `created` / `custom`，預設 `updated` |

#### Response

```json
{
  "status": "success",
  "data": [
    {
      "id": 12,
      "title": "Prompt A",
      "content": "markdown...",
      "type": "筆記 | Note",
      "category_name": "筆記 | Note",
      "remarks": "",
      "cover_image": "/static/uploads/xxx.webp",
      "cover_position": "top",
      "editor_layout": "single",
      "is_pinned": true,
      "created_at": "2026-04-24 10:00:00",
      "updated_at": "2026-04-24 10:30:00",
      "tags": [
        { "id": 1, "name": "demo" }
      ],
      "urls": [
        "https://example.com"
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

#### 備註

- `q` 保持純關鍵字搜尋，無 AI / embedding；標題與內文走 FTS5，備註 / 標籤 / 附件走關聯欄位與文字附件檔案比對。
- 列表回應目前不包含 `parent_id`。
- 排序永遠先把 `is_pinned=1` 的筆記排前面，再套用 `sort`。

### GET `/api/notes/<note_id>`

取得單筆筆記詳情。

#### Response

```json
{
  "status": "success",
  "data": {
    "id": 12,
    "title": "Prompt A",
    "content": "markdown...",
    "type": "筆記 | Note",
    "remarks": "",
    "cover_image": "/static/uploads/xxx.webp",
    "cover_position": "top",
    "editor_layout": "single",
    "prompt_params": {},
    "created_at": "2026-04-24 10:00:00",
    "updated_at": "2026-04-24 10:30:00",
    "tags": [
      { "id": 1, "name": "demo" }
    ],
    "urls": [
      "https://example.com"
    ],
    "parent_id": null,
    "parent_title": null
  }
}
```

### POST `/api/notes`

建立筆記。

#### Request Body

```json
{
  "title": "Optional title",
  "content": "Markdown content",
  "category_id": 1,
  "remarks": "",
  "tags": ["tag-a", "tag-b"],
  "urls": ["https://example.com"],
  "cover_image": "/static/uploads/xxx.webp",
  "cover_position": "top",
  "editor_layout": "single",
  "prompt_params": {
    "subject": "cat"
  }
}
```

#### 規則

- `content` 必填。
- `title` 可省略，後端會用內容第一行自動生成。
- `category_id` 可省略，後端會落到預設分類。
- `tags` 是字串陣列，後端會自動建立不存在的 tag。

#### Response

```json
{
  "status": "success",
  "data": {
    "note_id": 12
  }
}
```

### PUT `/api/notes/<note_id>`

更新筆記。

#### Request Body

`title` 與 `content` 都必填，其餘欄位與 `POST /notes` 相同。

#### 規則

- 若內容有變動，後端會自動寫一筆 `Note_History`。
- 若未帶 `category_id`，會保留原本分類。
- `tags` / `urls` 會採整批覆寫，不是 merge。

### DELETE `/api/notes/<note_id>`

刪除筆記。

#### 規則

- 會同步刪除不再被其他筆記引用的上傳圖片。
- `Note_History` / `Note_Tags` / `Source_Urls` 由 `ON DELETE CASCADE` 清理。

---

## 3. Notes Actions

### POST `/api/notes/<note_id>/pin`

切換或指定釘選狀態。

#### Body

可不帶 body 做 toggle，也可傳：

```json
{ "pinned": true }
```

#### Response

```json
{
  "status": "success",
  "data": {
    "id": 12,
    "is_pinned": true
  }
}
```

### POST `/api/notes/<note_id>/archive`

切換或指定封存狀態。

```json
{ "archived": true }
```

### POST `/api/notes/<note_id>/duplicate`

複製筆記，或建立 variant。

#### Body

```json
{
  "as_variant": true,
  "title_suffix": " (Variant)"
}
```

#### Response

```json
{
  "status": "success",
  "data": {
    "note_id": 13,
    "parent_id": 12,
    "is_variant": true
  }
}
```

### PUT `/api/notes/reorder`

拖曳排序。

```json
{
  "note_ids": [5, 2, 9]
}
```

限制：

- `note_ids` 必須為非空整數陣列
- 最多 `500` 筆

---

## 4. Notes Batch

### POST `/api/notes/batch/type`

批次更新分類。

```json
{
  "note_ids": [1, 2, 3],
  "category_id": 4
}
```

### POST `/api/notes/batch/tags`

批次更新標籤。

```json
{
  "note_ids": [1, 2, 3],
  "tags": ["stable-diffusion", "prompt"],
  "mode": "append"
}
```

`mode` 只接受：

- `append`
- `replace`

### POST `/api/notes/batch/delete`

批次刪除筆記。

```json
{
  "note_ids": [1, 2, 3]
}
```

---

## 5. Note History

### GET `/api/notes/<note_id>/history`

回傳最多 50 筆歷史版本。

### POST `/api/notes/<note_id>/restore/<history_id>`

還原指定版本；還原前會再自動備份一次目前內容。

### DELETE `/api/notes/<note_id>/history`

清空該筆記所有歷史。

---

## 6. Categories API

### GET `/api/categories`

Response 每筆欄位：

```json
{
  "id": 1,
  "name": "筆記 | Note",
  "icon": "📝",
  "sort_order": 0,
  "is_default": true,
  "count": 42
}
```

### POST `/api/categories`

```json
{
  "name": "Research",
  "icon": "🔬",
  "sort_order": 10
}
```

### PUT `/api/categories/<category_id>`

可更新欄位：

```json
{
  "name": "Research",
  "icon": "🔬",
  "sort_order": 10
}
```

### DELETE `/api/categories/<category_id>`

若該分類下仍有筆記，必須帶 `target_category_id`：

```json
{
  "target_category_id": 1
}
```

注意：

- 不能刪除預設分類
- 舊文件裡的 `target_name` 已失效，請不要再用

---

## 7. Tags API

### GET `/api/tags`

```json
[
  {
    "id": 1,
    "name": "prompt",
    "count": 8
  }
]
```

實際 envelope 仍為 `{ status, data }`。

### PUT `/api/tags/<tag_id>`

```json
{
  "name": "new-tag-name"
}
```

### DELETE `/api/tags/<tag_id>`

刪除 tag。

### POST `/api/tags/merge`

```json
{
  "source_tag_ids": [3, 4],
  "target_tag_id": 1
}
```

注意：

- 舊文件中的 `source_ids` / `target_id` 不是實際欄位名

---

## 8. Upload API

### POST `/api/upload`

上傳圖片，`multipart/form-data`。

#### Form Fields

- `file`: 必填
- `thumbnail_only`: 可選，`true` 時若成功生成縮圖，只保留縮圖路徑

#### 成功回應

```json
{
  "status": "success",
  "data": {
    "url": "/static/uploads/20260424_xxx.webp",
    "filename": "20260424_xxx.webp",
    "size": 123456,
    "thumbnail_only": true
  }
}
```

#### 限制

- 僅允許 `jpg` / `jpeg` / `png` / `gif` / `webp`
- 後端會做副檔名、magic number、檔案大小驗證

### POST `/api/upload/delete`

刪除圖片與對應縮圖。

```json
{
  "url": "/static/uploads/xxx.png"
}
```

### POST `/api/upload/url`

下載遠端圖片並存到本地。

```json
{
  "url": "https://example.com/image.png",
  "thumbnail_only": true
}
```

#### 備註

- 後端有 SSRF 防護，private / loopback / reserved IP 會被拒絕

### POST `/api/upload/extract-prompt`

從既有圖片檔提取 prompt metadata。

```json
{
  "image_path": "/static/uploads/xxx.png"
}
```

注意：

- 這不是上傳檔案接口
- 舊文件寫成 multipart/form-data 是錯的

---

## 9. Attachments API

### GET `/api/notes/<note_id>/attachments`

列出附件。

### POST `/api/notes/<note_id>/attachments`

上傳附件，`multipart/form-data`。

#### Form Fields

- `file`: 必填，僅允許 `.md` / `.txt` / `.markdown`
- `title`: 可選

### GET `/api/attachments/<attachment_id>`

預設回 JSON：

```json
{
  "status": "success",
  "data": {
    "id": 5,
    "title": "Reference",
    "file_type": "md",
    "content": "..."
  }
}
```

若加 `?raw=true`，直接回傳原始檔內容。

### DELETE `/api/attachments/<attachment_id>`

刪除附件檔與 DB 記錄。

### GET `/api/notes/<note_id>/check_separation`

檢查內容是否超過自動分離閾值。

### POST `/api/notes/<note_id>/separate`

把長文主體抽成附件。

```json
{
  "preview_length": 500
}
```

### POST `/api/notes/<note_id>/restore`

把自動分離的完整內容還原回 note body。

---

## 10. Cleanup API

### GET `/api/cleanup/orphan-images`

取得未被任何筆記 / 附件引用的圖片列表。

### DELETE `/api/cleanup/orphan-images`

```json
{
  "filenames": ["a.png", "b.webp"]
}
```

注意：

- 舊文件寫成 `paths` 不正確，實際要傳 `filenames`

### GET `/api/cleanup/originals`

取得原圖統計（非縮圖）。

### DELETE `/api/cleanup/originals`

刪除原圖並把內容引用切到縮圖。

### GET `/api/cleanup/broken-images`

掃描斷圖。

### POST `/api/cleanup/broken-images`

自動把失效原圖路徑改成存在的縮圖路徑。

---

## 11. System API

### POST `/api/system/vacuum`

執行：

1. WAL checkpoint
2. FTS rebuild
3. VACUUM

### POST `/api/system/clear-history`

清空所有 note history。

### GET `/api/system/stats`

取得 DB / uploads 統計。

### GET `/api/system/startup-preference`

### POST `/api/system/startup-preference`

```json
{
  "auto_open_browser": true
}
```

### POST `/api/system/wal-checkpoint`

手動合併 WAL。

### GET `/api/system/check-consistency`

目前回傳：

```json
{
  "orphan_note_tags": 0,
  "unused_tags": 0,
  "null_category_id": 0,
  "fk_status": 1,
  "fk_enabled": true,
  "health": "healthy"
}
```

注意：

- 舊文件中的 `type_category_mismatch` 已移除

### GET `/api/system/port-config`

### POST `/api/system/port-config`

```json
{
  "preferred_port": 5000,
  "fallback_enabled": true,
  "fallback_range": 20
}
```

### GET `/api/system/check-update`

檢查更新來源是否有新版本。

Response：

```json
{
  "current_version": "2.4.5",
  "latest_version": "v2.4.6",
  "has_update": true,
  "release_url": "https://github.com/.../releases/tag/v2.4.6",
  "release_notes": "...",
  "message": "發現新版本"
}
```

備註：

- 若未設定更新來源，會回 `has_update: false` 與 `message: "未設定更新來源"`。
- 更新來源優先讀 `PRISM_RELEASE_API_URL`，其次讀 `GITHUB_REPOSITORY`，最後嘗試從本機 `git remote origin` 推導 GitHub Releases API。

### GET `/api/system/go-read-routing`

Phase 19.3 controlled read routing proof 狀態。這是 Python-owned status endpoint，用來確認目前是否啟用 opt-in Go read routing switch；它不是 Go runtime endpoint，也不代表 production cutover。

Response：

```json
{
  "status": "success",
  "data": {
    "phase": "19.3",
    "enabled": false,
    "base_url": null,
    "valid_base_url": null,
    "mode": "controlled-read-routing-proof",
    "default_owner": "python",
    "fallback_owner": "python",
    "allowed_api_surface": [
      "/api/categories",
      "/api/notes",
      "/api/tags",
      "/api/test",
      "/api/notes/<id>"
    ],
    "blocked_methods": ["POST", "PUT", "DELETE", "PATCH"],
    "error": null
  }
}
```

啟用條件：

- `PRISM_GO_READ_ROUTING=1`
- `PRISM_GO_READ_BASE_URL=http://127.0.0.1:<port>` 或 localhost / `[::1]`
- 只代理已驗證 GET read surface；其他 API 仍由 Python 處理。

### GET `/api/system/migration-status`

取得資料庫 migration 狀態。

Response：

```json
{
  "current_version": 15,
  "latest_version": 15,
  "completed": [
    { "version": 1, "name": "add_is_pinned" }
  ],
  "pending": []
}
```

---

## 12. Export / Import API

### GET `/api/export/json`

下載整包 JSON。

### GET `/api/export/db`

下載 SQLite DB 檔。

### GET `/api/export/markdown`

下載所有筆記的 Markdown zip。每筆記一個 `{id:04d}-{slug(title)}.md` 檔，含 YAML frontmatter（`id` / `title` / `category` / `tags` / `is_pinned` / `is_archived` / `created_at` / `updated_at` / 可選 `remarks`）+ markdown body。zip 內附 `_manifest.json` 記錄匯出資訊（version / format / exported_at / notes_count）。

可直接導入 Obsidian / VSCode 等支援 frontmatter 的工具。**本端點為 read-only，無對應的 Markdown import**——回寫請走 `/api/import/json`。

### POST `/api/export/images`

```json
{
  "images": [
    "/static/uploads/a.webp",
    "/static/uploads/b.png"
  ],
  "note_title": "My Note"
}
```

注意：

- 舊文件寫成 `paths` / `filename` 不正確

### POST `/api/import/json`

```json
{
  "data": {
    "notes": [...]
  },
  "mode": "skip"
}
```

`mode`：

- `skip`
- `duplicate`

### POST `/api/notes/export/batch`

把多筆 note 匯出成 ZIP（markdown + assets）。

```json
{
  "note_ids": [1, 2, 3]
}
```

### POST `/api/notes/import/md`

上傳單一 markdown 檔並建立 note。

支援：

- 第一個 `# ` 標題作為 note title
- YAML front matter 中的 `type` 或 `category`
- `tags: [a, b]`

---

## 13. Prompt / Wizard Config API

這組主要是 Prism 內建 Prompt Builder 用的設定檔 CRUD；如果 `murmur厭世貓` 不需要管理 UI 選項，可以跳過。

### GET `/api/prompt-options`
### POST `/api/prompt-options/category/<category_key>`
### PUT `/api/prompt-options/category/<category_key>/<index>`
### DELETE `/api/prompt-options/category/<category_key>/<index>`
### POST `/api/prompt-options/template`
### DELETE `/api/prompt-options/template/<template_id>`

### GET `/api/wizard-options`
### POST `/api/wizard-options/dimension/<dimension_key>`
### DELETE `/api/wizard-options/dimension/<dimension_key>/<index>`

---

## 14. Server API

以下端點僅供本機 headless 維運，外部 Agent 通常不要接：

- `GET /api/server/hardware`
- `GET /api/server/logs`
- `POST /api/server/restart`
- `GET /api/server/backup/list`
- `GET /api/server/backup/download`
- `POST /api/server/backup/rotate`
- `GET /api/server/version`

限制：

- 只接受 localhost 來源

---

## 15. 前端契約同步狀態

目前 `frontend/src/services/api.ts` 內的 API wrapper 均有對應後端路由。

已同步的歷史差異：

- `GET /api/system/check-update` 已補回後端路由。
- `GET /api/system/go-read-routing` 是 Phase 19.3 Python-owned Go read routing proof status endpoint。
- `GET /api/system/migration-status` 已補回後端路由。
- `DELETE /api/categories/<id>` 使用 `target_category_id`，不再使用舊的 `target_category` / `target_name`。
- `GET /api/notes` 支援 `archived`、`include_archived`、`pinned_only`、`category_id`。

---

## 16. 建議給 murmur厭世貓的最小對接流程

1. `GET /api/test` 檢查服務是否活著。
2. `GET /api/categories` 先建立分類名稱對照表。
3. `GET /api/tags` 取得現有 tags。
4. `GET /api/notes?q=...&page=1&per_page=20` 做查詢。
5. `GET /api/notes/<id>` 讀全文。
6. `POST /api/notes` 或 `PUT /api/notes/<id>` 做寫入。
7. 若有長文本或補充資料，用 `attachments` 系列端點，不要硬塞進主 body。

---

## 17. 常見錯誤碼

| HTTP | 說明 |
|---|---|
| `200` | 成功 |
| `201` | 建立成功 |
| `400` | 參數錯誤 / 驗證失敗 |
| `403` | CSRF 或 localhost 限制 |
| `404` | 資源不存在 |
| `409` | 命名衝突（如重複 tag / category） |
| `500` | 伺服器內部錯誤 |

常見訊息：

- `Note not found`
- `Tag not found`
- `Category not found`
- `Content is required`
- `Title and content are required`
- `Target category required`
