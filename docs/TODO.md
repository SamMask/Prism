# Prism Active TODO

本檔只保留目前可施工的 active roadmap。舊 TODO 與歷史 phase 已完整歸檔到 `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`。

目前結論：Python 仍是正式 runtime。Go 要能取代 Python，必須完成下表全部 runtime surface、部署切換與刪除驗證；任何單一路線完成都不等於可以刪 Python。

| ID | 任務 | 依賴 | 契約 | 結構依據 | 驗收標準 | 狀態 |
|---|---|---|---|---|---|---|
| T001 | 將舊 `docs/TODO.md` 完整歸檔到 development-history，active TODO 只保留目前 roadmap | - | CONTRACT-GO-PRIMARY-TODO-GOVERNANCE | ARCH-GO-PRIMARY-00 / development-history README | 歸檔檔存在且包含原 phase 歷史；active TODO 不再混入舊 phase 長文 | Done |
| T002 | 建立 Go primary runtime 契約索引 `docs/CONTRACTS.md` | T001 | CONTRACT-GO-PRIMARY-TODO-GOVERNANCE | ARCH-GO-PRIMARY-00 | TODO 中每個契約名稱都能在 `docs/CONTRACTS.md` 找到 | Done |
| T003 | 在 `docs/ARCHITECTURE.md` 補 Go primary runtime 目標拓樸與切換邊界 | T002 | CONTRACT-GO-PRIMARY-ARCHITECTURE | ARCH-GO-PRIMARY-00 / ARCH-GO-PRIMARY-09 | 架構文件明確區分 current retained-Python 與 target Go-primary runtime | Done |
| T004 | 建立 Flask route ownership manifest，列出所有正式 API route、HTTP method、Python handler、資料庫與檔案副作用 | T003 | CONTRACT-GO-PRIMARY-ROUTE-OWNERSHIP | ARCH-GO-PRIMARY-01 | manifest 覆蓋 Flask `url_map` 全部 route；缺 Go owner 的 route 標示 Python-owned | Todo |
| T005 | 建立 Python-vs-Go route parity fixture harness，固定 status code、JSON shape、DB mutation 與檔案 mutation 比對格式 | T004 | CONTRACT-GO-PRIMARY-PARITY | ARCH-GO-PRIMARY-01 / ARCH-GO-PRIMARY-02 | 可對任一 route 宣告 fixture，測試能同時跑 Python 與 Go 並輸出差異 | Todo |
| T006 | 實作 Go runtime config 與 external data dir parity，統一 DB、uploads、attachments、logs、backups 路徑解析 | T005 | CONTRACT-GO-PRIMARY-CONFIG | ARCH-GO-PRIMARY-02 | Go 在 copied data dir 可讀寫所有必要路徑；拒絕未指定或逃逸路徑 | Todo |
| T007 | 實作 Go SQLite connection owner，支援 WAL、busy timeout、transaction helper 與 write-mode 開關 | T006 | CONTRACT-GO-PRIMARY-DB | ARCH-GO-PRIMARY-02 / SCHEMA: SQLite WAL | Go write-mode 測試證明 transaction commit/rollback 與 Python 行為一致 | Todo |
| T008 | 實作 Go fresh DB init，建立全新 Prism DB schema 與必要初始資料 | T007 | CONTRACT-GO-PRIMARY-MIGRATIONS | SCHEMA: 全資料表 / ARCH-GO-PRIMARY-03 | 空 data dir 啟動後可建立 DB；Schema_Meta current version 正確 | Todo |
| T009 | 實作 Go existing DB migration runner，對齊 Python migration order、idempotent skip 與 Schema_Meta 更新 | T008 | CONTRACT-GO-PRIMARY-MIGRATIONS | SCHEMA: Schema_Meta / ARCH-GO-PRIMARY-03 | 從舊版 fixture 升級到 latest；pending migrations 為空；重跑不重複套用 | Todo |
| T010 | 實作 Go failed migration rollback 與 backup-before-migrate | T009 | CONTRACT-GO-PRIMARY-MIGRATIONS | ARCH-GO-PRIMARY-03 / DEPLOY-PI backup flow | 故意失敗 migration 會保留 pre-migrate backup，DB 不留下半套 schema | Todo |
| T011 | 實作 Go `GET /api/notes` 完整 read/search parity，包含 FTS、關聯欄位、文字附件搜尋與 pagination | T007 | CONTRACT-GO-PRIMARY-NOTES | SCHEMA: Notes / Notes_FTS / Note_Tags / Source_Urls | Python-vs-Go fixture 覆蓋空查詢、關鍵字、tag/category/filter、pagination，結果一致 | Todo |
| T012 | 實作 Go notes create/update，包含 category、tags、source_urls、content、timestamps 與 validation | T011 | CONTRACT-GO-PRIMARY-NOTES | SCHEMA: Notes / Note_Tags / Source_Urls | 建立與更新後 DB state、response JSON、FTS 更新與 rollback 測試一致 | Todo |
| T013 | 實作 Go notes delete，包含單筆刪除、batch delete 與 referenced image cleanup decision | T012 | CONTRACT-GO-PRIMARY-NOTES | ARCH-GO-PRIMARY-04 / SCHEMA: Notes | 刪除 note 後 DB 關聯、FTS、history、圖片引用計數與 companion `_thumb.webp` 處理一致 | Todo |
| T014 | 實作 Go notes actions：pin、archive、duplicate、reorder | T012 | CONTRACT-GO-PRIMARY-NOTES | SCHEMA: Notes | 每個 action 的 response、排序欄位、時間欄位與 DB mutation parity 通過 | Todo |
| T015 | 實作 Go notes batch actions：type、tags、archive、delete | T013 | CONTRACT-GO-PRIMARY-NOTES | SCHEMA: Notes / Note_Tags | 批次成功、部分失敗、空 id、rollback/no partial write fixtures 通過 | Todo |
| T016 | 實作 Go notes history list、restore、delete-history | T012 | CONTRACT-GO-PRIMARY-NOTES | SCHEMA: Notes history tables | history 讀取、還原、刪除與原 Python response/DB state 一致 | Todo |
| T017 | 實作 Go categories create/update/delete/default/sort ownership | T007 | CONTRACT-GO-PRIMARY-TAXONOMY | SCHEMA: Categories / Notes.category_id | category CUD、default fallback、duplicate、in-use delete、sort fixtures 通過 | Todo |
| T018 | 實作 Go tags create/update/delete/merge ownership，包含 NOCASE 與 Note_Tags 關聯維護 | T017 | CONTRACT-GO-PRIMARY-TAXONOMY | SCHEMA: Tags / Note_Tags | tag CUD/merge fixtures 覆蓋大小寫重複、in-use delete、merge rollback，結果一致 | Todo |
| T019 | 實作 Go attachments metadata list/create/update/delete ownership | T007 | CONTRACT-GO-PRIMARY-FILES | SCHEMA: Attachments / ARCH-GO-PRIMARY-04 | attachment metadata DB mutation 與檔案存在性 validation parity 通過 | Todo |
| T020 | 實作 Go attachment raw/text/binary serving，包含 MIME、range 或 download 行為邊界 | T019 | CONTRACT-GO-PRIMARY-FILES | ARCH-GO-PRIMARY-04 | text、binary、missing、unsafe path、unsupported type fixtures 與 Python 行為一致 | Todo |
| T021 | 實作 Go multipart `POST /api/upload` live-owner candidate，包含原圖寫入、檔名安全、size limit、MIME/magic validation | T020 | CONTRACT-GO-PRIMARY-UPLOADS | ARCH-GO-PRIMARY-04 | jpg/png/webp/gif、bad MIME、oversize、path traversal、rollback/no orphan file fixtures 通過 | Todo |
| T022 | 實作 Go thumbnail generation live-owner candidate，取代 helper-only 模式並覆蓋 `_thumb.webp`、max width、quality、thumbnail_only | T021 | CONTRACT-GO-PRIMARY-UPLOADS | ARCH-GO-PRIMARY-04 | upload/upload-url/import 產生 thumbnail 的 output 與現行契約一致，不依賴 Pillow | Todo |
| T023 | 實作 Go `POST /api/upload/url`，包含 SSRF、redirect、timeout、Content-Type、magic、stream cap 與 filename hash fallback | T022 | CONTRACT-GO-PRIMARY-UPLOADS | ARCH-GO-PRIMARY-04 / ARCH-GO-PRIMARY-08 | local/remote fixture 覆蓋 private IP、redirect、oversize、bad MIME、thumbnail_only，無未清檔案 | Todo |
| T024 | 實作 Go upload delete，包含 original、thumbnail companion 與 DB/reference 檢查 | T023 | CONTRACT-GO-PRIMARY-UPLOADS | ARCH-GO-PRIMARY-04 | referenced file 不誤刪；unreferenced original 與 `_thumb.webp` 清理一致 | Todo |
| T025 | 實作 Go orphan images scan/delete cleanup | T024 | CONTRACT-GO-PRIMARY-MEDIA-CLEANUP | ARCH-GO-PRIMARY-04 | 掃描 uploads 後只刪真正 orphan；dry-run 與 delete mode fixture 通過 | Todo |
| T026 | 實作 Go originals cleanup，處理 thumbnail-only 與原圖保留/刪除規則 | T025 | CONTRACT-GO-PRIMARY-MEDIA-CLEANUP | ARCH-GO-PRIMARY-04 | originals cleanup 對 referenced、unreferenced、thumbnail_only 檔案結果一致 | Todo |
| T027 | 實作 Go broken images scan/fix cleanup | T026 | CONTRACT-GO-PRIMARY-MEDIA-CLEANUP | ARCH-GO-PRIMARY-04 / SCHEMA: Notes.content | broken image 報告、修復後 Markdown/DB state 與 Python 行為一致 | Todo |
| T028 | 實作 Go Markdown import，包含 local image bundling、remote image download、source URLs、tags/categories mapping | T023 | CONTRACT-GO-PRIMARY-IMPORT-EXPORT | ARCH-GO-PRIMARY-05 / SCHEMA: Notes | Markdown import fixture 覆蓋文字、metadata、本機圖、遠端圖、rollback，結果一致 | Todo |
| T029 | 實作 Go JSON import，包含 existing id、duplicate、attachments/uploads restore 與 rollback | T028 | CONTRACT-GO-PRIMARY-IMPORT-EXPORT | ARCH-GO-PRIMARY-05 / SCHEMA: 全資料表 | JSON import fixture 覆蓋完整備份還原、衝突、失敗 no partial write | Todo |
| T030 | 實作 Go JSON/Markdown export，包含 notes、tags、categories、attachments、uploads references | T029 | CONTRACT-GO-PRIMARY-IMPORT-EXPORT | ARCH-GO-PRIMARY-05 | export 內容、檔名、metadata、排序與 Python output fixture 一致 | Todo |
| T031 | 實作 Go DB/images export，產出可還原的 DB backup 與 images bundle | T030 | CONTRACT-GO-PRIMARY-IMPORT-EXPORT | ARCH-GO-PRIMARY-05 / DEPLOY-PI backup flow | 匯出的 DB/images 可在 fresh data dir restore 並通過 smoke | Todo |
| T032 | 實作 Go server version/status/hardware/logs API | T007 | CONTRACT-GO-PRIMARY-SERVER-SYSTEM | ARCH-GO-PRIMARY-06 | `/api/server/version`、status、hardware、logs response shape 與 Pi/local fixture 通過 | Todo |
| T033 | 實作 Go backup list/create/download/delete/rotate API | T031 | CONTRACT-GO-PRIMARY-SERVER-SYSTEM | ARCH-GO-PRIMARY-06 / DEPLOY-PI backup flow | backup 建立、下載、刪除、保留數、路徑安全 fixtures 通過 | Todo |
| T034 | 實作 Go port/config/service availability API，取代 Python server ops surface | T032 | CONTRACT-GO-PRIMARY-SERVER-SYSTEM | ARCH-GO-PRIMARY-06 | local 與 Pi fixture 證明 port/config/status 行為一致且不需 Python service | Todo |
| T035 | 實作 Go prompt/wizard/options runtime surface，若仍有 Python-owned 設定 route 則全部補齊 | T034 | CONTRACT-GO-PRIMARY-SERVER-SYSTEM | ARCH-GO-PRIMARY-06 / SCHEMA: App settings | route ownership manifest 中 prompt/wizard/options 類 route 無 Python-owned | Todo |
| T036 | 實作 Go embedded SPA 與 static/uploads serving 邊界，Caddy 可只代理 Go 或由 Caddy serve static/uploads | T006 | CONTRACT-GO-PRIMARY-STATIC-SERVING | ARCH-GO-PRIMARY-07 | fresh artifact 可載入 SPA、API fallback 不混淆、uploads static 路徑安全 | Todo |
| T037 | 補 Go security parity：localhost/public exposure policy、path traversal、SSRF、MIME、size、auth absence warning | T023 | CONTRACT-GO-PRIMARY-SECURITY | ARCH-GO-PRIMARY-08 | security fixtures 與 docs 明確鎖住 public exposure 邊界；危險輸入不突變 DB/files | Todo |
| T038 | 建立 full workflow E2E：create、upload、search、export、import、delete、cleanup、backup、migration | T035 | CONTRACT-GO-PRIMARY-PARITY | ARCH-GO-PRIMARY-09 | Python 與 Go 對同一 fixture 跑完整工作流，response、DB、files 結果一致 | Todo |
| T039 | 建立 Go primary Windows package smoke，不含 Python/venv/Flask/PyInstaller runtime 依賴 | T038 | CONTRACT-GO-PRIMARY-PACKAGING | ARCH-GO-PRIMARY-09 | fresh checkout/build artifact 在沒有 Python venv 的環境通過 local smoke | Todo |
| T040 | 建立 Go primary linux/arm64 package smoke，不含 Python/venv runtime 依賴 | T039 | CONTRACT-GO-PRIMARY-PACKAGING | ARCH-GO-PRIMARY-09 | linux/arm64 artifact 可在 copied data dir 啟動並通過 full workflow smoke | Todo |
| T041 | 建立 Pi staging Go primary unit，使用 copied production DB/data，不改 live Caddy default | T040 | CONTRACT-GO-PRIMARY-DEPLOY-CUTOVER | ARCH-GO-PRIMARY-09 / DEPLOY-PI | Pi staging service active；copied DB/data full smoke 通過；live DB SHA256 不變 | Todo |
| T042 | 執行 Pi live Go primary cutover：backup、systemd primary switch、Caddy route switch、frontend default API 驗證 | T041 | CONTRACT-GO-PRIMARY-DEPLOY-CUTOVER | ARCH-GO-PRIMARY-09 / DEPLOY-PI | live smoke 覆蓋 read/write/upload/import/export/server/migration；Python service 不接流量 | Todo |
| T043 | 執行 rollback drill：從 Go primary 還原 Python runtime、Caddy、systemd、DB/files backup | T042 | CONTRACT-GO-PRIMARY-ROLLBACK | ARCH-GO-PRIMARY-09 / DEPLOY-PI | rollback 後 live smoke 通過；DB/files hash 或 restore evidence 完整 | Todo |
| T044 | 完成 Go primary soak window，監看 logs、memory、DB WAL、uploads、backup、cleanup 無回歸 | T042 | CONTRACT-GO-PRIMARY-DEPLOY-CUTOVER | ARCH-GO-PRIMARY-09 | soak 期間無新 error；核心 workflow 重跑通過；memory 不高於 retained-Python baseline | Todo |
| T045 | 刪除 Python packaged runtime 依賴與啟動路徑，保留 Python source 僅作 legacy 或完全移除 | T044, T043 | CONTRACT-GO-PRIMARY-PYTHON-DELETION | ARCH-GO-PRIMARY-10 | requirements/venv/PyInstaller/start scripts 不再是產品啟動必要條件；full tests/package smoke 通過 | Todo |
| T046 | 最終刪除或封存 Python backend source，更新 docs/API、deploy、release wording 為 Go primary runtime | T045 | CONTRACT-GO-PRIMARY-PYTHON-DELETION | ARCH-GO-PRIMARY-10 | repo 搜尋不再有 production startup 依賴 Python backend；文件沒有 retained-Python 主路徑描述 | Todo |
