# API Reference

**Base URL**: `/api`

---

## Notes

### GET /notes

取得筆記列表 (分頁)

| 參數     | 類型   | 說明                         |
| -------- | ------ | ---------------------------- |
| page     | int    | 頁碼 (預設 1)                |
| per_page | int    | 每頁數量 (預設 20)           |
| q        | string | 搜尋關鍵字                   |
| type     | string | 分類過濾                     |
| tags     | string | 標籤過濾 (逗號分隔)          |
| sort     | string | 排序: updated/created/custom |

**Response**: `{ status, data: [...], pagination: {...} }`

---

### POST /notes

新增筆記

**Body**: `{ title, content, type, remarks?, tags?, urls? }`

---

### PUT /notes/:id

更新筆記

---

### DELETE /notes/:id

刪除筆記

---

## History

### GET /notes/:id/history

取得歷史版本

### POST /notes/:id/restore/:historyId

還原版本

### DELETE /notes/:id/history

清空歷史

---

## Export

### POST /notes/export/batch

批量匯出 ZIP

**Body**: `{ note_ids: [1, 2, 3] }`
**Response**: ZIP 檔案

---

## Tags

### GET /tags

取得所有標籤

### PUT /tags/:id

重新命名標籤

### DELETE /tags/:id

刪除標籤

### POST /tags/merge

合併標籤

---

## Categories

### GET /categories

取得所有分類

### POST /categories

新增分類

### PUT /categories/:id

更新分類

### DELETE /categories/:id

刪除分類

---

## System

### POST /system/vacuum

整理資料庫 (VACUUM)

### GET /system/orphan-images

取得孤兒圖片

### DELETE /system/orphan-images

清除孤兒圖片

---

## Upload

### POST /upload/image

上傳圖片

**Content-Type**: multipart/form-data
**Response**: `{ status, url, thumb_url }`

---

## 錯誤碼說明

所有 API 回傳格式：`{ status: 'success' | 'error', message?, data? }`

| HTTP 狀態碼 | 說明           |
| ----------- | -------------- |
| 200         | 成功           |
| 400         | 請求參數錯誤   |
| 404         | 資源不存在     |
| 500         | 伺服器內部錯誤 |

**常見錯誤訊息**:

- `Note not found` - 筆記不存在
- `Invalid note_ids` - 無效的筆記 ID
- `Title is required` - 標題為必填
- `Tag not found` - 標籤不存在
