# Prism API Reference

> 用途：提供外部 Agent / 自動化工具（例如 `murmur厭世貓`）直接對接 Prism 的實際 API 契約。
> 基準：以 Go primary live/default runtime 為準；Python Flask backend source 已於 T053 移除，Go primary 為唯一 runtime。
> 最後確認：2026-06-19

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
- `POST` / `PUT` / `DELETE` 預設會做 CSRF 檢查（Go runtime `csrfGate` middleware）：
  - 有 `Origin` / `Referer` 時必須同源；本機 dev server `localhost:5173/5174` 已在白名單，否則回 `403`
  - 無 `Origin` / `Referer` 的請求（curl / MCP / 外部 Agent，無法被瀏覽器 CSRF）放行，不受影響
  - 可在 **設定 > 資料 > CSRF 防護** 或 `/api/system/csrf-protection` 即時開關，預設開啟（關閉狀態以 data dir 的 `.csrf_disabled` marker 持久化）
- `/api/server/*`、`GET /api/export/full-snapshot` 與 `POST /api/system/inline-separated-notes` 有「直接連線 peer 的 loopback 檢查」：只看 TCP 連線的 `RemoteAddr` 是否為 `127.0.0.1` / `::1`，不讀 `X-Forwarded-For`。
  - 經同機 reverse proxy（例如 Pi 的 Caddy `reverse_proxy 127.0.0.1:5004`）轉進來的請求，在 Go 看來都來自 loopback，所以能連到 proxy 的 LAN 使用者也能呼叫這些端點；這不是 auth。
  - CSRF 檢查由 `csrfGate` 在路由之前執行：只有帶 `Origin` / `Referer` 而且兩者都不同源時才擋；沒有這兩個 header 的請求放行；CSRF 防護可整體關閉。
  - 2026-10-07 決定（PRISM-OPT-29）：不在程式內收緊這個檢查（例如不信任 `X-Forwarded-For`、不加 `--allow-lan-admin`）。Prism 的安全前提是信任的區網；需要時，在 reverse proxy 加認證（例如 Caddy `basic_auth`）。見 `DEPLOY-PI.md` 的安全邊界。

### 歷史相容層

- `Notes.type` 已從資料庫移除。
- 部分 API 仍保留 `type` 作為「分類名稱字串」的相容欄位或查詢參數，不代表資料庫仍有 `type` 欄位。
- `/api/system/go-read-routing` 是 Phase 19 舊讀取路由 proof 端點，已隨 T053 Python source 移除，不存在於 Go primary product runtime（not part of the Go primary product API）；本條僅作歷史說明。

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
| `parent_id` | int | 只列出指定 note 的直接 child variants；用於 variant tracking panel |
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
      "content": "markdown preview...",
      "content_preview": "markdown preview...",
      "content_truncated": true,
      "content_length": 12345,
      "content_first_image": "/static/uploads/first-image.webp",
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
      ],
      "parent_id": null,
      "parent_title": null,
      "variants_count": 0
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
- 搜尋比對語意（PRISM-OPT-56）：純 ASCII 查詢對標題 / 內文是 FTS 前綴比對；查詢含 CJK（漢字、平假名、片假名、韓文）時，標題 / 內文改用子字串比對。查詢中只要有一個 CJK token，其餘 ASCII token 也改用子字串比對（例如「rom 工程」會命中含 prompt 的卡片）。全形英數（U+FF01–U+FF5E、全形空白）只在查詢端折成半形；內容中的全形字不會因此被半形查詢搜到。
- Go primary current truth: `/api/notes?q=...` 已由 Go primary product runtime 負責，搜尋範圍包含 DB-backed 附件 metadata 與 bounded text attachment body scan。
- 文字附件內容搜尋是 request-time bounded scan：最多 200 個附件檔、5 MiB、250 ms。若超限，回應會加上 optional `search_diagnostics.attachment_body_scan.partial=true`，並標出 `reason`（`file_limit` / `byte_limit` / `time_limit` / `scan_error`）。
- 列表回應是 Home/card 輕量 payload：`content` 為相容用 preview（與 `content_preview` 相同），`content_truncated=true` 代表前端若要編輯、複製全文、匯出內容或閱讀完整內容，必須再呼叫 `GET /api/notes/<id>`；`content_length` 提供完整 `Notes.content` 字數供卡片 metadata 顯示；`content_first_image` 是從完整內容抽出的第一張圖片 URL，供卡片在不預載全文時維持「無手動封面時用第一張圖」的 fallback。
- list response shape 不變；Go primary 會先取得當頁 Notes，再各用一個 batch query hydrate tags 與 source URLs。relation query 數不隨 page note 數增加，避免 per-note N+1。
- 列表回應包含 `parent_id` / `parent_title`，供 Home 卡片直接顯示 variant 上一代來源；非 variant 為 `null`。
- `parent_id` query filter 只回直接 child variants，不回整棵樹；列表與詳情回應的 `variants_count` 是該 note 的直接 child variant 數量。
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
    "parent_title": null,
    "variants_count": 0
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
- 被刪筆記的 variant 子筆記不會被刪除，會改掛到被刪筆記自己的 `parent_id`（根筆記則為 `NULL`）；批次刪除時，子筆記會改掛到最近一個沒有被刪的祖先（PRISM-OPT-68）。

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

#### 規則

- 複製會保留原 note 的 tags、source URLs 與文字附件。
- 附件會複製成新 note 自己的 `Note_Attachments` row 與實體檔，不共用父 note 的 `file_path`。
- 若原 note 已做長內容自動分離，variant 會得到自己的 `docs/notes/note_<child_id>.md` 自動分離附件；閱讀模式會在打開該 note 時 lazy-load 這份完整內容。

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

可先用 destructive preview guard 取得 dry-run 結果，不刪 DB row、不刪 upload / attachment 檔：

```json
{
  "note_ids": [1, 2, 3],
  "dry_run": true
}
```

`dry_run: true` 回傳 `requested_count`、`deletable_count`、`missing_count`、`image_count`、`attachment_count` 與即將刪除的 note title preview。這不是 auth，也不代表 API 可以公開到 public internet；它只是在本機 / trusted boundary 內給 UI 或外部 Agent 執行 destructive write 前做 preview。

單筆詳情不套用 list preview 截斷；`content` 回傳目前 `Notes.content` 完整欄位。若該 note 已經由長內容自動分離機制轉成附件 preview，前端仍需使用 `/api/notes/<id>/attachments` 與 `/api/attachments/<attachment_id>` lazy-load `is_auto_extracted` 附件全文。

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
  "system_key": "note",
  "name_override": null,
  "count": 42
}
```

`system_key` 只會出現在五個系統分類（`prompt` / `note` / `tutorial` / `data` / `inspiration`）。`name_override` 為使用者改名後的固定顯示文字；`null` 代表前端依目前語系顯示系統分類預設名。

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
  "sort_order": 10,
  "name_override": "My Notes"
}
```

注意：

- `system_key` 是 server-owned identity，client 不可修改。
- 一般自訂分類仍更新 `name`。
- 系統分類（有 `system_key`）不直接改 canonical `name`；使用者改名寫入 `name_override`。傳 `null` 或空字串可清除 override，回到依語系顯示預設名。

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

限制：

- 單一文字附件最大 1 MiB；超限會回 `400`，不建立 `Note_Attachments` row，也不保留 partial file。

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

自 PRISM-OPT-19 起，前端存檔不再呼叫 `separate`；編輯已拆分的筆記時，會先呼叫 `restore` 再 PUT。這三個端點保留以維持 API 相容。若同一個 `docs/notes` 檔仍被其他筆記的附件引用，`restore` 不會刪除該檔。

`restore` 交易的第一個語句就會認領（刪除）這則筆記的一個 auto 附件列；檔案不存在或之後任何一步失敗都會整筆 rollback，回應與狀態碼不變。既有已拆分筆記的一次性合併見 `POST /api/system/inline-separated-notes`。

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

取得 DB / uploads 統計。`uploads.files`（additive，PRISM-OPT-31）是 uploads 目錄中不含 `*_thumb.*` 縮圖的檔案數；`size_bytes`／`size_mb` 仍包含所有檔案。Maintenance 的圖片統計讀這裡。

### GET `/api/system/startup-preference`

### POST `/api/system/startup-preference`

```json
{
  "auto_open_browser": true
}
```

### GET `/api/system/csrf-protection`

回傳目前 CSRF 防護開關狀態（預設開啟）：

```json
{ "status": "success", "data": { "csrf_protection": true } }
```

### POST `/api/system/csrf-protection`

切換 CSRF 防護，立即生效、免重啟；關閉時於 data dir 寫入 `.csrf_disabled` marker，開啟時移除。

```json
{
  "csrf_protection": false
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
  "foreign_key_violations_total": 0,
  "foreign_key_violations_by_table": {},
  "health": "healthy"
}
```

注意：

- 舊文件中的 `type_category_mismatch` 已移除
- `fk_enabled` 只表示目前連線有啟用外鍵 enforcement；資料是否一致以唯讀 `PRAGMA foreign_key_check` 的 `foreign_key_violations_total` / `foreign_key_violations_by_table` 為準。
- 任一實際外鍵違規會把 `health` 標為 `critical`；端點只回報，不會刪除、修復或遷移資料。

### GET `/api/system/search-integrity`

檢查 `Notes` 與 `Notes_FTS` 是否對齊。此端點只回報狀態，不修改資料。

Response：

```json
{
  "status": "success",
  "data": {
    "status": "ok",
    "notes_count": 42,
    "fts_rows": 42,
    "missing_fts_rows": 0,
    "orphan_fts_rows": 0,
    "integrity_error": "",
    "rebuild_route": "/api/system/search-integrity/rebuild-fts",
    "auto_repair": false
  }
}
```

`status` 可能為：

- `ok`
- `needs_rebuild`

### POST `/api/system/search-integrity/rebuild-fts`

手動重建 `Notes_FTS`。此端點只執行 SQLite FTS rebuild；不執行 `VACUUM`、不修改 `Notes` / `Note_Attachments`、不刪檔，也不會由診斷端點自動觸發。

Response：

```json
{
  "status": "success",
  "data": {
    "notes_count": 42,
    "fts_rows": 42,
    "message": "FTS index rebuilt"
  }
}
```

### POST `/api/system/inline-separated-notes`

把舊版「長文自動拆分」留下的筆記合併回 `Notes.content`（PRISM-OPT-20）。手動維護動作，不會自動執行。

Gate：`POST`；直接連線 peer 的 loopback 檢查（見「安全限制」）；server-system 必須啟用（停用時 `405`）。

Request：

```json
{ "dry_run": true }
```

- body 為空、`{}`、沒有 `dry_run` 或 `"dry_run": null` → dry-run，不寫入任何東西。
- 只有明確的布林 `"dry_run": false` 才執行。
- body 必須是單一 JSON object（上限 1 MiB）；非 object、尾隨資料、重複的 `dry_run`、非布林值都回 `400`。

分類（每個 `is_auto_extracted = 1` 的附件列一筆）：

- `merge`：DB 內容等於檔案全文，或是它自動產生的預覽（橫幅結尾、橫幅前是全文的非空嚴格前綴）。這是啟發式判斷：保證 DB 文字可由檔案推導，不證明檔案歸屬；「保留橫幅並從預覽尾端刪字」的編輯意圖可能遺失，還原點保有原樣。合併寫入 `normalizeTextContent(檔案)`，**不改 `updated_at`**，不寫版本歷史。
- `history`：DB 內容沒有橫幅且不等於檔案全文（例如 OPT-19 前改短後存檔）。保留 DB 內容，把檔案全文寫成一筆 `Note_History`（`diff_summary`：「合併長文：保留附件全文」）。檔案全文引用的 `/static/uploads/...` 若在執行後不再受孤兒清理保護，改列為 `media_unprotected`。
- 其餘只列出、不修改：`missing_file`、`dangling_row`（檔案不存在；懸空列永不刪除）、`too_large`（超過 1 MiB）、`preview_mismatch`、`invalid_path`、`unsafe_path`（路徑經 symlink／junction 或不是一般檔案）、`nonstandard_path`（不是 `docs/notes/note_<自己的 id>.md|markdown|txt`，保守的自動處理邊界，請手動處理）、`shared_file`（另一個附件列以相同路徑或相同檔案身分引用）、`identity_unverified`（任何其他附件列的檔案身分無法讀取，或自己的檔案身分無法讀取）、`unreadable`、`multiple_auto_rows`、`note_missing`；執行期間才出現的 `changed_during_run`。
- 另列 `orphan_files`（`docs/notes` 中沒有任何附件列引用的檔案）、`shared_files`、`unverified_rows`。

執行（`dry_run: false`，且有可處理項目）：

1. 建立 `backups/separated-notes-<時間戳>/`，以 `writeConsistentDBBackup` 寫入 `restore_point.db`（含 WAL 中已提交的資料）。
2. 寫入不可變的 `plan.json` 與 `moves.tsv`（回滾預檢用的 tab 分隔檔）。
3. 每筆一個交易：先刪附件列（第一句即寫入），再於交易內重驗 DB 內容、共用狀態與（history）媒體保護，然後寫入；commit 後才把檔案 rename 進隔離資料夾。搬移失敗時檔案留在原處，下次 dry-run 列為孤兒檔。
4. 寫入 `result.json`。這個資料夾永不自動刪除，也不在 full snapshot 內。

Response（dry-run 與執行同形狀，節錄）：

```json
{
  "status": "success",
  "data": {
    "dry_run": false,
    "counts": { "actionable": 3, "merge": 2, "history": 1, "merged": 2, "historied": 1, "move_failed": 0, "failed": 0, "skipped": 1, "skipped_by_reason": { "missing_file": 1 }, "orphan_files": 0, "shared_files": 0, "unverified_rows": 0 },
    "merge": [{ "note_id": 2, "title": "長文 A", "attachment_id": 1, "file_path": "docs/notes/note_2.md", "size_bytes": 18234 }],
    "history": [],
    "results": [{ "note_id": 2, "action": "merge", "status": "merged", "reason": "", "moved_to": "backups/separated-notes-20261007_120000_000000000/docs/notes/note_2.md", "move_error": "", "error": "" }],
    "skipped": [{ "note_id": 4, "attachment_id": 3, "file_path": "docs/notes/note_4.md", "size_bytes": null, "reason": "missing_file", "detail": "" }],
    "orphan_files": [], "shared_files": [], "unverified_rows": [],
    "aborted": false, "audit_error": "",
    "restore_point": "backups/separated-notes-20261007_120000_000000000/restore_point.db",
    "quarantine_dir": "backups/separated-notes-20261007_120000_000000000"
  }
}
```

- 沒有可處理項目時不建立資料夾，`restore_point` / `quarantine_dir` 為 `null`；第二次執行因此是 no-op。
- 第一個 DB 錯誤會中止（`aborted: true`），已提交的筆記保持合併；`result.json` 寫入失敗時仍回 `200`，`audit_error` 帶原因。
- `500` 只在保證沒有修改任何筆記時回傳，body 帶 `"notes_changed": 0`。其他錯誤或連線中斷時結果未知，請重新 dry-run 並查看 `result.json`。
- 單一行程假設：維護動作與 restore、separate、複製筆記、刪除筆記／附件、上傳附件、JSON 匯入、媒體清理、full snapshot 共用一把行程內的鎖；同一 data-dir 不要同時跑兩個 Prism 行程。

回滾（回到執行前；執行後的 DB 編輯會一併還原）：

1. 停掉其他 writer（關閉編輯畫面、停止呼叫 API 的 agent；Pi 先 `systemctl stop prism-backup.timer`），用 `POST /api/server/backup/rotate`（或 `GET /api/server/backup/download`）取得目前 DB 的一致備份。
2. 停止 Prism。
3. 依 `moves.tsv` 逐列預檢：`restore_point` 的 SHA-256 必須相符；原位置已有相同 hash 的檔案就接受（可重入），hash 不同或兩處都沒有正確的檔就停止，不換 DB。
4. 從隔離資料夾**複製**（不是搬移）檔案回原位，複製後再核對 hash。
5. 把 `restore_point.db` 複製成 `backups/prism_backup_<YYYYMMDD_HHMMSS>_000000000.db`，寫入 `config/pending-restore.json`（`{"backup": "<檔名>", "requested_at": "<RFC3339>"}`），啟動 Prism；開機時在任何連線之前驗證並換上 DB（log：`restored database from backup`）。
6. 再跑一次 dry-run，結果應與執行前相同。

只核對進度而不回滾時，`result.json` 不完整也沒關係：用同一個 binary 以另一個 port 開啟停機後的 DB 與 data-dir **副本**，查 plan 中附件列 id 是否還在、D2 筆記是否有對應的歷史，不要只看內容 hash。

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
  "current_version": "2.6.1",
  "latest_version": "v2.7.0",
  "has_update": true,
  "release_url": "https://github.com/.../releases/tag/V2.7",
  "release_notes": "...",
  "message": "發現新版本"
}
```

備註：

- 若未設定更新來源，會回 `has_update: false` 與 `message: "未設定更新來源"`。
- 更新來源優先讀 `PRISM_RELEASE_API_URL`，其次讀 `GITHUB_REPOSITORY`，最後嘗試從本機 `git remote origin` 推導 GitHub Releases API。

### GET `/api/system/go-read-routing`

Legacy-only Phase 19.3 controlled read routing proof 狀態。這個 endpoint 已隨 T053 Python source 移除，不存在於任何 runtime；外部 Agent 與前端不應依賴此 endpoint。保留本節僅作 Phase 19 歷史說明。

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

目前產品 runtime 已是 Go primary；上述啟用條件只供讀歷史 evidence 或手動跑 legacy Flask source 時理解，不是現行部署步驟。

### GET `/api/system/migration-status`

取得資料庫 migration 狀態。

Response：

```json
{
  "current_version": 17,
  "latest_version": 17,
  "completed": [
    { "version": 1, "name": "add_is_pinned" },
    { "version": 17, "name": "add_category_identity" }
  ],
  "pending": []
}
```

---

## 12. Export / Import API

Current owner: Go primary runtime。T028-T031 原本是 local/copied candidate；T042-T050 後產品啟動與 Pi live route 已由 Go primary 提供 import/export surface。

### GET `/api/export/json`

下載整包 JSON。

`categories[]` 會包含 `system_key` 與 `name_override`，供還原五個系統分類 identity；note 的 `category` 仍使用 canonical category name。

`export_info.version` 為 `1.7-go`（PRISM-OPT-39）。`notes[]` 每筆有 `id`、`title`、`content`、`category`、`remarks`、`cover_image`、`created_at`、`updated_at`、`tags`、`urls`，以及 additive 欄位：

- `is_pinned`、`is_archived`（boolean）
- `parent_id`（匯出端的 note id 或 `null`，匯入時會重新對應）
- `cover_position`（缺值時為 `top`）、`editor_layout`（缺值時為 `single`）
- `sort_order`（整數或 `null`）

不包含：版本歷史、`prompt_params`（Prompt Builder 的結構化參數）、附件與圖片的檔案內容（`attachments[]`、`uploads[]` 只有路徑 metadata）；已拆分長文的 `content` 只有預覽。完整備份請用 full snapshot。

### GET `/api/export/db`

下載 SQLite DB 檔。這是 **DB-only** 副本，不包含 `static/uploads`、`docs/attachments`、`docs/notes` 或 `config`。

### GET `/api/export/full-snapshot`

建立並下載完整資料 ZIP。此端點只接受 localhost request，且 import/export surface 必須啟用。

包含：

- consistent SQLite backup：`database/knowledge.db`
- `static/uploads/**`
- `docs/attachments/**`
- `docs/notes/**`
- `config/**`
- `snapshot-manifest.json`

manifest format 是 `prism.full_data_snapshot.v1`，每個 payload file 都有 `size_bytes` 與 SHA-256；response 同時提供 manifest version、建立時間與內容類別 headers。ZIP 只在 staging、manifest 與壓縮全部完成後回傳，暫存檔會清除。

這是下載／留存入口，**不提供自動還原**。完整契約見 [`contracts/full-data-snapshot-v1.md`](./contracts/full-data-snapshot-v1.md)。

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
    "categories": [
      {
        "name": "筆記 | Note",
        "icon": "📝",
        "sort_order": 2,
        "is_default": true,
        "system_key": "note",
        "name_override": null
      }
    ],
    "notes": [...]
  },
  "mode": "skip"
}
```

若 `categories[]` 存在，匯入會先套用分類 identity，再匯入 notes。舊備份沒有 `system_key` / `name_override` 時仍以 `name` 相容匹配；note `category` 可匹配 `Categories.name` 或 `Categories.name_override`。

`mode`：

- `skip`
- `duplicate`

note 欄位 `is_pinned`、`is_archived`、`cover_position`、`editor_layout`、`sort_order`、`parent_id`（PRISM-OPT-39）：

- 有值就套用；缺欄位或型別不對時用預設值（未置頂、未封存、`top`、`single`、`sort_order` 為 `null`、無 parent），不會讓整批失敗。舊版 JSON 照常可匯入。
- `cover_position`、`editor_layout` 與 `PUT /api/notes/{id}` 相同：字串照存，非字串用預設值。
- `parent_id` 依檔案內的舊 id 重新對應，所有筆記建立後才在同一個 transaction 內補上，所以子筆記可以排在 parent 前面：
  - parent 在檔中且本次建立 → 指向新 id。
  - parent 在檔中、但被 `skip` 判為重複 → 指向目標端既有的那筆。
  - parent 不在檔中 → `null`，不會指向目標端碰巧同 id 的筆記。
  - 會形成環的連結 → `null`。
- 被 `skip` 的既有筆記本身不會被修改。

回應的 `data` 有 `imported`、`skipped`、`duplicates`，以及 additive 欄位 `skipped_attachments`（PRISM-OPT-58）：
- 路徑在 `docs/notes/`（已拆分長文）的附件列會被略過並計入這個數字，不寫檔也不建立附件列。原因是 JSON 匯出只有這類筆記的 500 字預覽，沒有全文；而路徑指的是匯出端的 `note_<舊 id>.md`，在目標端可能是另一則筆記的檔案。
- 這類筆記在目標端只會有預覽加拆分橫幅。要完整保留已拆分長文，請用 full snapshot，或先執行「合併長文回筆記」（PRISM-OPT-20）再匯出 JSON。
- 其他附件路徑仍須通過路徑安全檢查，否則整批回 `400`。
- 匯入不會刪除或覆寫目標端既有的檔案（PRISM-OPT-64）：
  - 附件列帶 `content_b64`、而目標路徑已有檔案時，改寫成 `<原名>_import_<n><副檔名>` 並存入新路徑。
  - upload（圖片）同名時略過，計入 additive 欄位 `skipped_uploads`。筆記以檔名引用圖片，所以匯入的筆記會顯示目標端原有的那張。
  - 同一筆記已有相同（正規化）路徑的附件列時不重複新增；存入 DB 的路徑一律正規化。
  - 需要用備份內容覆蓋現有檔案時，請用 full snapshot 還原。

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

Frontend usage note:

- Settings 的批次 Markdown/TXT 匯入是前端逐檔 wrapper，沒有 server-side batch import API。
- 前端維護本機待匯入清單；使用者可多次從不同資料夾選檔後一次匯入，同一檔案以 name / size / lastModified 去重，匯入後清空待匯入清單但保留結果摘要。
- `.md` 檔逐一呼叫這個單檔 endpoint；單一檔案失敗只回報該檔，不回滾其他已成功建立的 note。
- `.txt` 檔不走 `/api/notes/import/md`，而是由前端讀取文字後呼叫既有 `POST /api/notes`，title 使用檔名 stem，content 使用純文字內容。

---

## 13. Prompt / Wizard Config API

Current owner: Go primary runtime。Prompt / Wizard options 讀寫 `PRISM_GO_DATA_DIR/config/*.json`；PromptBuilder 目前使用 `/api/wizard-options`，不再讀 legacy `/static/config/wizard_options.json`。

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

Current owner: Go primary runtime。`scripts/start_go_primary.ps1` 與 Pi `prism-go-primary.service` 會啟用 server/system surface。`POST /api/server/restart` 會真的重啟 Prism 程序（PRISM-OPT-36），與 backup restore 共用同一條重啟路徑：被 supervisor 管理時（systemd 會設 `INVOCATION_ID`，或 `PRISM_GO_SUPERVISED=1`）以 exit code 42 結束，由 Pi 的 `Restart=on-failure` 拉起；獨立執行（桌面版、本機 runtime）則自我 re-exec。它不呼叫 `systemctl`，也不重開機。

以下端點僅供本機 headless 維運，外部 Agent 通常不要接：

- `GET /api/server/hardware`
- `GET /api/server/logs`
- `POST /api/server/restart`（先回 `{status: "success", message: "restarting", data: {restarting: true, supervised, service_management: {available: true, reason}}}`，約 250ms 後關閉 HTTP server、checkpoint 並關閉 DB，再重啟程序；呼叫端應輪詢 `/healthz` 直到恢復。`GET /api/server/hardware` 的 `service_management.available` 也改為 `true`）
- `GET /api/server/backup/list`（桌面版：本次啟動跑過每日還原點檢查時，回應多一個 additive 欄位 `auto_restore_point`，內容是 `{status: created|skipped|failed, backup, error, checked_at}`；瀏覽器／Pi 的 runtime 不會出現這個欄位。PRISM-OPT-28）
- `GET /api/server/backup/download`（以 SQLite `VACUUM INTO` 產生目前 DB 的一致快照，包含 request 當下 active WAL 最新交易，供使用者自行保存；**不在 server-side 留存或輪換備份**——server-side 保留是 `rotate` 的職責；此 DB backup 不包含 `static/uploads/` / `docs/attachments/` 檔案）
- `POST /api/server/backup/rotate`（以同樣一致 DB snapshot 建立 server-side 備份並輪換；body 可用 `{ "keep_count": N }`，預設保留最近 7 份（2026-10-07 起由 3 改為 7，與桌面版每日自動還原點共用同一組 managed backup 與保留份數）；相容舊鍵 `{ "keep": N }`；仍是 DB-only backup，不等於 deploy data snapshot）
- `POST /api/server/backup/restore`（body `{ "backup": "<managed backup filename>" }`；驗證該備份後寫入 pending-restore 標記並重啟程序，開機時以該備份覆蓋 live DB，覆蓋前自動另存目前 DB 一份）
- `DELETE /api/server/backup/<filename>`
- `GET /api/server/version`

限制：

- 只接受 localhost 來源

---

## 15. 前端契約同步狀態

目前 `frontend/src/services/api.ts` 內的 API wrapper 均有對應後端路由。

已同步的歷史差異：

- `GET /api/system/check-update` 已補回後端路由。
- `GET /api/system/go-read-routing` 是 legacy Phase 19 proof endpoint，已於 T053 隨 Python source 移除，不存在於任何 runtime。
- `GET /api/system/migration-status` 已補回後端路由。
- `DELETE /api/categories/<id>` 使用 `target_category_id`，不再使用舊的 `target_category` / `target_name`。
- `GET /api/notes` 支援 `archived`、`include_archived`、`pinned_only`、`category_id`、`parent_id`。
- Settings 批次 Markdown/TXT 匯入只是在前端逐檔使用 `POST /api/notes/import/md` 與 `POST /api/notes`；沒有新增 server-side batch import endpoint。

---

## 16. 建議給 murmur厭世貓的最小對接流程

1. `GET /api/test` 檢查服務是否活著；回應帶 `version`（`prismVersion()`，additive，PRISM-OPT-24），前端以它顯示版本。`stats.library_count`（additive，PRISM-OPT-31）是未封存筆記數（含未分類），也就是側欄 All、Header、Footer 顯示的 Library 總數。
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
