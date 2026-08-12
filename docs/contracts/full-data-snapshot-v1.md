# Full Data Snapshot v1 Contract

> Contract: `CONTRACT-FULL-DATA-SNAPSHOT-V1`
> Endpoint: `GET /api/export/full-snapshot`
> Owner: Go primary runtime

## Purpose

Prism 的 `.db` 下載與內建還原點是 DB-only。Full Data Snapshot 提供明確的完整檔案留存入口，但不新增自動整機還原、排程備份、雲端同步或 schema migration。

## Runtime boundary

- 只接受 `GET` 且沿用 localhost-only request gate。
- 只有在 import/export surface 啟用時可用。
- 全部 staging 必須位於 external data dir 的暫存目錄；成功或失敗後都要清除。
- 資料庫必須透過既有 consistent SQLite backup helper 產生，不能直接複製可能尚有 WAL 內容的 live DB。
- uploads、attachments、notes、config 只從 runtime config 指向的 data-dir roots 收集；symlink 不得跟隨或打包。
- ZIP 先寫入 `.tmp`，關閉並完成後才 atomic rename；失敗不得留下可被誤認為完成的 snapshot。
- endpoint 不修改 DB/schema、內容檔案、設定或還原狀態。

## Archive layout

```text
database/knowledge.db
static/uploads/**
docs/attachments/**
docs/notes/**
config/**
snapshot-manifest.json
```

不存在的選配資料夾可為空；manifest 的 `contents` 仍描述五個資料類別。

## Manifest

`snapshot-manifest.json` 必須包含：

```json
{
  "format": "prism.full_data_snapshot.v1",
  "version": 1,
  "created_at": "UTC RFC3339 timestamp",
  "contents": ["database", "uploads", "attachments", "notes", "config"],
  "total_size_bytes": 0,
  "manual_restore_required": true,
  "files": [
    {
      "path": "database/knowledge.db",
      "size_bytes": 0,
      "sha256": "lowercase hex digest"
    }
  ]
}
```

`files` 依 archive path 排序，列出 manifest 以外的 payload files。每一筆 size 與 SHA-256 必須可由 ZIP 內容重算驗證。

## Response metadata

- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename=prism_full_data_snapshot_YYYYMMDD_HHMMSS.zip`
- `Content-Length`
- `X-Prism-Snapshot-Manifest-Version: 1`
- `X-Prism-Snapshot-Created-At`
- `X-Prism-Snapshot-Contents`

## Restore boundary

v1 **不提供自動 restore API**。產品 UI 必須明示 `manual_restore_required` 的意思；下載完成不代表已驗證異機復原。任何未來自動還原都必須另開任務、威脅/資料安全審查、rollback contract 與 isolated destructive test。

## Verification

- Go test 要用 temporary data dir 建立 DB 與四種 file roots，解開 ZIP 後驗證 layout、manifest、size/hash、localhost gate 與無暫存目錄殘留。
- Frontend source regression 鎖住 typed API、可見入口、內容範圍與 manual restore 文案。
- Browser smoke只驗證 Data & Recovery 入口可見；不在每次 smoke 建立大型 snapshot。
