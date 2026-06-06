# Prism Contracts

本檔是 active TODO 的契約索引。每個 active TODO 任務都必須指向本檔中的一個契約名稱；契約名稱只描述必須守住的 runtime 邊界，不代表該功能已完成。

| Contract | Boundary |
|---|---|
| CONTRACT-GO-PRIMARY-TODO-GOVERNANCE | `docs/TODO.md` 只保留 active roadmap；歷史 phase 移入 `docs/development-history/`，active task 必須有依賴、結構依據、驗收標準與狀態。 |
| CONTRACT-GO-PRIMARY-ARCHITECTURE | 文件必須明確區分 current retained-Python runtime 與 target Go-primary runtime，不得把 candidate、sidecar、rollback proof 寫成 live owner。 |
| CONTRACT-GO-PRIMARY-ROUTE-OWNERSHIP | 所有正式 API route 必須有唯一 production owner；Go 替代 Python 前，manifest 中不得留有 Python-owned request-time surface。 |
| CONTRACT-GO-PRIMARY-PARITY | Go route promoted 前，必須有 Python-vs-Go parity fixture 證明 status、JSON shape、DB state、file state 與 rollback 行為一致。 |
| CONTRACT-GO-PRIMARY-CONFIG | Go runtime 必須使用明確 external data dir，所有 DB/uploads/attachments/logs/backups path 都不能逃逸資料根目錄。 |
| CONTRACT-GO-PRIMARY-DB | Go 必須正確擁有 SQLite connection、WAL、transaction、busy timeout、write mode 與 rollback semantics。 |
| CONTRACT-GO-PRIMARY-MIGRATIONS | Go 必須能 fresh init、existing DB upgrade、idempotent skip、failed migration rollback、backup-before-migrate，才可取代 Python migration runner。 |
| CONTRACT-GO-PRIMARY-NOTES | Notes read/write/actions/batch/history 必須完整 Go-owned，包含 FTS、關聯欄位、history、delete side effects 與 image cleanup 邊界。 |
| CONTRACT-GO-PRIMARY-TAXONOMY | Categories/tags CUD/merge/default/sort 必須完整 Go-owned，且與 schema uniqueness、NOCASE、Note_Tags 關聯行為一致。 |
| CONTRACT-GO-PRIMARY-FILES | Attachments metadata、raw/text/binary serving 與 path/MIME 安全必須由 Go 完整負責。 |
| CONTRACT-GO-PRIMARY-UPLOADS | upload、upload-url、upload delete、thumbnail generation 必須 Go-owned，並覆蓋 SSRF、MIME/magic、size、filename、rollback/no orphan file。 |
| CONTRACT-GO-PRIMARY-MEDIA-CLEANUP | orphan images、originals、broken images、note delete companion cleanup 必須 Go-owned，且不得誤刪仍被引用檔案。 |
| CONTRACT-GO-PRIMARY-IMPORT-EXPORT | Markdown/JSON/DB/images import/export 必須 Go-owned，且輸出可還原、失敗不留下 partial DB/files。 |
| CONTRACT-GO-PRIMARY-SERVER-SYSTEM | server version/status/hardware/logs/backup/port/config/service availability 必須 Go-owned，正式 runtime 不依賴 Python service。 |
| CONTRACT-GO-PRIMARY-STATIC-SERVING | SPA、static assets、uploads serving 與 API fallback 必須有 Go/Caddy 明確分工，不能因 fallback 讓 API 404/405 變成 SPA。 |
| CONTRACT-GO-PRIMARY-SECURITY | Go primary 必須保留現有 exposure boundary，並鎖住 path traversal、SSRF、MIME、size、public internet warning 與 no-auth 風險。 |
| CONTRACT-GO-PRIMARY-PACKAGING | Windows 與 linux/arm64 package smoke 必須證明產品啟動不需要 Python/venv/Flask/PyInstaller runtime。 |
| CONTRACT-GO-PRIMARY-DEPLOY-CUTOVER | live cutover 必須包含 backup、systemd primary switch、Caddy route switch、frontend default API 驗證與 full workflow smoke。 |
| CONTRACT-GO-PRIMARY-ROLLBACK | rollback 必須能從 Go primary 還原 Python runtime、Caddy、systemd、DB/files，並有 live smoke 證據。 |
| CONTRACT-GO-PRIMARY-PYTHON-DELETION | 只有 Go primary cutover、rollback、soak、package smoke 全部通過後，才允許刪除 Python packaged runtime 或封存 Python backend。 |
