# TODO Completed Phase Archive

> 從 `docs/TODO.md` 瘦身移出。此檔保存已完成階段與已決議事項，避免 active TODO 入口被歷史內容淹沒。

## ✅ 已完成項目 (Completed Projects)

### 🚨 Phase 0: 架構淨化 (Architecture Purification) ✅ 2024-12-31
> **來源**: Linus-style 審核報告 (`1230-審核報告.md`)

- [x] **0.1 淨化資料結構** — Migration v12: 移除 `Notes.type` 雙重事實，統一用 `category_id`
- [x] **0.2 任務隊列** — Migration v13: `AI_Tasks` 表 + `workers/task_processor.py` 取代 ThreadPoolExecutor
- [x] **0.3 重構查詢** — 提取 `NoteQueryBuilder`，分離 `sanitize_fts_query()` 與 Filter
- [x] **0.4 V1 功能移植** — 主題色彩、卡片開啟模式、圖片保存模式、快速新增預設分類、自動載入更多
- [x] **0.5 殘留清理** — Schema 淨化、FTS5 安全性、拆分 NoteEditor/SettingsPage、VectorStore 執行緒安全

### 🟢 Phase 1: 現代化地基 (The Big Rewrite) ✅
> **目標**: 建立 Vite + React + Flask 的混合開發環境，打通 API 通訊。

- [x] **1.1 前端專案初始化** — Vite + React + TS + Tailwind + Zustand
- [x] **1.2 後端 API 改造** — `PRISM_V2` 模式切換，保留 V1 向後相容
- [x] **1.3 核心組件移植** — `Button`, `Input`, `Modal`, `Toast` 設計系統
- [x] **1.4 開發規範更新** — Versioning、Testing Philosophy、License Policy

### 🟡 Phase 2: 功能復刻 (Feature Parity) ✅
> **目標**: 讓 React 版本擁有 v1.x 的核心功能 (CRUD)。

- [x] **2.1 筆記管理** — MasonryGrid + NoteCard (懸停預覽、快速操作)
- [x] **2.2 編輯器 V2** — 貼上圖片、拖曳上傳
- [x] **2.3 標籤與分類** — TagInput 自動完成、DataManager 管理介面
- [x] **2.4 Prompt Builder** — React Hook 移植、結構化參數表單、權重滑桿

### 🔴 Phase 3: 本地智慧 (Local Intelligence) — ⚠️ AI 已拔除 (2026-04-04)
> **原目標**: 引入 PyTorch / Ollama / Sentence-Transformers。
> **現況**: AI 功能已全部拔除，Prism 轉型為純筆記 + Headless KMS。參見 `docs/20260404-重構評估報告.md`。

- [x] ~~**3.1 智慧標籤**~~ — 已拔除 (Ollama / NVIDIA NIM)
- [x] ~~**3.2 語意搜尋**~~ — 已拔除 (Embeddings / Vector Store / Hybrid Search)
- [x] **3.4 附件系統** — Note_Attachments 表 + 拖曳上傳 + 長文自動分離 (保留)
- [x] ~~**3.5 RAG Knowledge API**~~ — 已拔除
- [x] **3.7 卡片譜系** — 父子繼承 (`as_variant`) + 單表關聯 (保留)

### 🧪 Phase 6: 自動化測試 ✅
- [x] **6.0 安全性修復** — P0/P1/P2 問題
- [x] **6.1 後端 API 測試** — CRUD, Search, AI 服務
- [x] **6.2 前端 E2E** — Playwright 核心流程

### 📦 Phase 7: 打包與更新 ✅ (部分凍結)
- [x] **7.0 建置腳本** — `build_release.py` (Frontend Build + PyInstaller)
- [x] **7.1 下載更新 (Plan A)** ✅ 2026-03-15 — `check-update` API + `UpdateSection.tsx`
- [x] **7.3 啟動遷移** ✅ 2026-03-15 — `init_db()` 移入 `create_app()`，冪等遷移

### 🍓 Phase 8: 樹莓派與無頭部署 ✅ 2026-03-15
> **目標**: 無頭伺服器環境的連線、維運與遠端管理。

- [x] **8.1 反向代理與 mDNS** — avahi-daemon + Caddy (80→5000) + systemd + 一鍵安裝腳本
- [x] **8.2 伺服器管理面板** — 硬體監控 / 日誌檢視 / 服務重啟 / 備份管理 / 版本資訊

### 🖼️ v1.5.0 圖片管理增強 + 端口自選 ✅ 2026-02-27
- [x] **圖片管理** — 批次選取/刪除、設為封面、個別操作 (複製語法/移除引用/刪除檔案)
- [x] **端口自選** — Settings 端口設定 + `.port_config` + WinError 10013 處理 + 智能 fallback

### 🛡️ v1.5.1 未儲存變更防護 ✅ 2026-02-27
- [x] **Unsaved Changes Guard** — 原始快照 + 變更偵測 + 關閉攔截 (背景/ESC/X)

### 🎨 Phase 9: 前端 UX 強化 ✅ 2026-03-15
> **來源**: Claude 4.6 UI/UX 綜合檢閱報告
- [x] **9.1 全域錯誤攔截器** — axios interceptor 統一處理網路錯誤 / 5xx / 404
- [x] **9.2 ConfirmDialog** — 取代全部 11 處 `window.confirm()`，支援暗色主題 + danger/warning 變體
- [x] **9.3 標題 autoFocus** — NoteEditor 開啟時自動聚焦標題欄位
- [x] **9.4 標籤自動補全** — EditorSidebar 模糊匹配現有標籤 + 鍵盤導覽 + 使用次數顯示
- [x] **9.5 色彩對比度修正** — `--color-text-muted` 暗色 #6b7280→#848b98 (≈5.0:1)、亮色 #666→#525252 (≈4.7:1)，達 WCAG AA

---

## 🩹 Phase 10: 體檢報告修補 (cco audit) — ✅ 已完成 v2.4.2

> **來源**: [`docs/過期/20260412-cco-綜合分析報告.md`](../過期/20260412-cco-綜合分析報告.md) (Linus-mode 深度體檢, 2026-04-12)
> **目標**: 清理 v2.3.0 AI 拔除 + v12 `Notes.type` 移除後遺留的殭屍程式碼，補上 SSRF 防護，修正測試地基。
> **執行順序**: P0 → P1 → P2，禁止跳級。

### 🔴 P0 — Critical (上線即炸 / 殭屍欄位)

- [x] **10.1** `routes/system.py` — 移除 `type_category_mismatch` 殭屍 query，`issues` 計算與 response 同步清除
- [x] **10.2** `routes/export.py` — `export_json()` SELECT 改用 `LEFT JOIN Categories c` 取 `c.name as category`，移除 `n.type`

### 🟠 P1 — High (系統性風險)

- [x] **10.3** `tests/conftest.py` — `temp_db()` 改為建立最小 pre-migration base schema，再呼叫 `migrations.run_migrations(conn)` 走真實遷移路徑；移除 `sample_note_data` 中的死欄位 `type`
- [x] **10.4** `routes/upload.py` — 新增 `_is_ssrf_target()` helper，`download_from_url()` 在 scheme 驗證後解析 hostname IP，拒絕 loopback/private/link-local/reserved 目標
- [x] **10.5** `routes/notes/crud.py` — 刪除 `_HAS_PARENT_ID` 模組全域快取，`get_note()` 直接設 `parent_cols`/`parent_join`（schema 已穩定）
- [x] **10.6** `routes/notes/crud.py` — 移除 `delete_note()` 手動 cascade DELETEs，依賴 `ON DELETE CASCADE`；更新過時註解

### 🟡 P2 — Medium (品質 / 一致性)

- [x] **10.7** `config.py` — `PRISM_VERSION` 同步為 `2.4.1`（將在本版完成後升 `2.4.2`）
- [x] **10.8** `frontend/src/services/api.ts` — `ConsistencyCheckResponse` 移除 `type_category_mismatch: number` 死碼
- [x] **10.9** `routes/notes/crud.py` — `update_note()` 內 `existing` 改名 `existing_note`
- [x] **10.10** `routes/upload.py` — `extract_prompt()` 改用 `with Image.open(...) as img` context manager，消除 file handle 洩漏
- [x] **10.11** `routes/server.py` — 新增 `@server_bp.before_request` localhost-only guard，非 `127.0.0.1/::1` 回傳 403
- [x] **10.12** `app.py` — `csrf_protect()` 在生產模式（`V2_MODE=true` + `not debug`）拒絕無 Origin 的 unsafe method

### 📋 補充

- [x] **10.13** 新增 `tests/test_schema_regression.py` — 4 個測試：`type` 欄位已移除、必要欄位存在、AI 欄位已清除、fixture schema 與 migration 輸出一致
- [x] **10.14** `docs/CONTRIBUTING.md` — 加上 Release Checklist（版本同步 / 測試 / build / migration 確認）

---

## 📘 Phase 11: 外部 Agent API 對接文件整理 ✅ 2026-04-24

> **目標**: 以目前實際後端契約為準，整理可直接提供外部 Agent（如 murmur厭世貓）使用的 API 對接文件，並順手清掉阻礙對接的 schema 漂移問題。

- [x] **11.1** 修正 `routes/notes/crud.py` 單筆讀取 `has_parent_id` 未定義造成的 500
- [x] **11.2** 修正 `routes/notes/actions.py` duplicate 仍引用已移除 `Notes.type` 欄位
- [x] **11.3** 修正 `routes/notes/import_.py` / `routes/notes/export.py` / `routes/export.py` 殘留 `Notes.type` 寫法，改回 `category_id` / `category` 相容層
- [x] **11.4** 更新 `docs/API_REFERENCE.md`，重寫為可直接交付外部 Agent 的對接文件，標明限制、回應格式、已知不建議端點

---

## 🔧 Phase 12: 前後端 API 契約修補 ✅ 2026-04-24

> **目標**: 修正前端 API wrapper 與 Flask 路由之間的實際落差，讓設定頁、分類管理、封存/置頂篩選與 migration 診斷都能對上後端契約。

- [x] **12.1** 補回 `GET /api/system/check-update`，支援環境設定、GitHub repository 推導與網路失敗降級回應
- [x] **12.2** 補回 `GET /api/system/migration-status`，直接回傳 `migrations.get_migration_status()`
- [x] **12.3** 修正前端 `deleteCategory()` 改送 `target_category_id`，DataManager 改用預設分類 ID 遷移筆記
- [x] **12.4** 修正 `GET /api/notes` 查詢契約，支援 `archived` / `include_archived` / `pinned_only` / `category_id`
- [x] **12.5** 擴充 note create/update 對 `is_pinned`、`is_archived` 的支援，並保持未傳欄位時不覆寫既有狀態
- [x] **12.6** 補測試覆蓋 system 缺路由、分類刪除遷移、封存/置頂篩選

---

## 🔎 Phase 13: 搜尋範圍擴充 ✅ 2026-05-05

> **目標**: 搜尋欄維持同一個 `GET /api/notes?q=...` 契約，但命中範圍從卡片標題 / 內文擴充到備註、附件、標籤。

- [x] **13.1** 擴充 `GET /api/notes` 搜尋條件，覆蓋 `Notes.title`、`Notes.content`、`Notes.remarks`、`Note_Attachments`、`Tags.name`
- [x] **13.2** 補 pytest 覆蓋標題、內文、備註、附件內容、標籤搜尋
- [x] **13.3** 同步更新 `AGENTS.md`、`docs/API_REFERENCE.md`、`docs/SCHEMA.md`、`docs/ARCHITECTURE.md`、`docs/Prism.md`
- [x] **13.4** 部署到 Raspberry Pi 並驗證 live API

---

## 🧭 Phase 17: Sidebar Filter Navigation — ✅ 已完成 v2.4.9 (2026-05-26)

> **觸發**: 分類/標籤本質是首頁卡片篩選器；在設定頁或其他非首頁頁面點擊時，篩選狀態會變但頁面不跳回首頁，看起來像按鈕失效。
> **目標**: 非首頁點分類/標籤時自動回到首頁並套用篩選；首頁上保留再次點擊同一分類/標籤可取消篩選的原互動。

- [x] **17.1** Sidebar filter routing — `Sidebar` 對分類/標籤 click 加上 route-aware handler；非首頁一律導回 `/` 並套用該篩選。
- [x] **17.2** Category query contract — notes 查詢改送 `category_id`，不再依賴分類名稱 `type` 相容層，避免分類改名後的篩選風險。
- [x] **17.3** 收尾驗證 — `cd frontend && npx tsc --noEmit` / `cd frontend && npm run build` / `pytest tests/ -v` / Browser flow 驗證。

---

## ✏️ Phase 16: Preview Editing UX — ✅ 已完成 v2.4.8 (2026-05-26)

> **觸發**: Preview 模式只能看渲染結果，實際修字或移除圖片仍要切回 Markdown 原始編輯 / 側欄圖片管理；日常編輯流程不夠順手。
> **目標**: 保持 Preview 的閱讀感，同時允許就地修改文字區塊與移除圖片引用；不新增後端 API、不改 DB schema。

- [x] **16.1** `EditablePreview` — Preview 模式改為可互動：文字區塊 hover 後可切入小型 Markdown textarea 直接修改內容，離焦回到預覽。
- [x] **16.2** Preview 圖片移除 — 對獨立 Markdown / HTML 圖片渲染刪除按鈕，直接從內容移除引用；若該圖是封面，同步清空 `cover_image`。
- [x] **16.3** 圖片移除 helper 共用 — 側欄 `ImageManagementPanel` 與 Preview 圖片刪除共用同一套 Markdown / HTML image reference 移除邏輯。
- [x] **16.4** 收尾驗證 — `cd frontend && npx tsc --noEmit` / `cd frontend && npm run build` / `pytest tests/ -v` 全通過；Browser flow 實測 Preview 內可改文字、刪圖片引用且 console 無 warn/error；`PRISM_VERSION` / README badge / TODO Changelog 同步至 v2.4.8。

### ⏸️ 本輪不處理

- 完整 WYSIWYG Markdown round-trip（例如直接在渲染後的 bold / table / list DOM 上保留所有 Markdown 語法細節）— 目前採用「預覽中就地切入小型 Markdown 區塊」以避免引入大型 editor 依賴。
- 實體圖片檔案刪除 — Preview 只移除內容引用；永久刪檔仍由既有側欄「圖片管理」與確認對話處理。

---

## 💾 Phase 15: 維護模式雜項 (Maintenance Sundries) — ✅ 已完成 v2.4.7 (2026-05-13)

> **觸發**: Phase 14 收尾後用戶確認啟動兩項：(a) 自動備份排程確認、(b) Markdown 匯出。
> **背景發現** (2026-05-13 重新驗證)：
> - 真正的備份位置是 `backups/`（不是中文 `資料庫備份/`）；Pi `backups/` 目前有 3 份：4/4、4/24、5/13，**用戶手動點 UI 觸發、間隔約 3 週**
> - 後端 `routes/server.py` 已有 `/api/server/backup/download` + `/rotate (keep=3)`，但**完全靠手動觸發**——crontab 空、systemd timer 空
> - 頂層中文資料夾 `資料庫備份/` 是 V1 殘留 dead folder（4/4 後就沒動），實際使用的是英文 `backups/`
> - **Pi 儲存媒介是 SSD 不是 SD 卡**（用戶 2026-05-13 確認）——失效機率比 SD 卡低一個量級，無寫入次數疲勞集中、無 SD 卡控制器悲劇
> **真實風險**（最終版）：SSD 仍是單點故障（控制器、檔案系統損毀、電源異常 / 雷擊）。手動備份 ~3 週習慣已覆蓋大部分情境；自動化純粹是「假期 / 出差 / 忘記時的便宜保險」。**整個 Phase 15 沒有 P0/P1**。

### 🟢 自動備份排程（便宜的保險）

- [x] **15.1** Pi 加 `prism-backup.timer` (每週日 03:00) + `prism-backup.service` 觸發 `/home/mask070924/prism/scripts/auto-backup.sh`
- [x] **15.2** 腳本內 `--http1.1 --fail` 下載 + `Origin: https://prism.local` POST rotate keep=8（**踩過的坑**：Caddy → Werkzeug HTTP/2 stream 收尾不乾淨會讓 curl exit 92，必須強制 HTTP/1.1）
- [x] **15.3** 手動 `systemctl start prism-backup.service` 驗證通過（產出完整 4MB 備份 + rotate 成功）
- [x] **15.4** `DEPLOY-PI.md` 補「自動備份排程」章節（含 service / timer / script 完整安裝指令 + 還原備份範例）

### 🟢 Dead folder 清理

- [x] **15.5** Windows + Pi 雙端 `git rm -r 資料庫備份/` / `rm -rf 資料庫備份/`，audit §4.5 path encoding 隱患同步清除

### 🟢 Markdown 匯出（可離線、跨工具可讀）

- [x] **15.6** `routes/export.py` 新增 `GET /api/export/markdown` — 回傳 zip：`{id:04d}-{slug(title)}.md` + YAML frontmatter (`id` / `title` / `category` / `tags` / `is_pinned` / `is_archived` / `created_at` / `updated_at` / 可選 `remarks`) + body + `_manifest.json`
- [x] **15.7** `tests/test_export_markdown.py` — 4 測試（zip 結構 / frontmatter 欄位 / manifest 計數 / 空標題 edge case），全綠
- [x] **15.8** `BackupImportSection.tsx` 加「下載 .zip」按鈕，呼叫 `api.exportMarkdown()`
- [x] **15.9** `docs/API_REFERENCE.md` §12 加 `/api/export/markdown` 端點說明（含 frontmatter 規格）

### 📋 收尾驗證

- [x] **15.10** `pytest tests/ -v` → **80 passed** (+4)，test_run.log 已覆寫
- [x] **15.11** `npx tsc --noEmit` 零錯誤；`npm run build` 1509 modules / 2.26s
- [x] **15.12** `PRISM_VERSION` → `2.4.7`；README badge 同步；Changelog v2.4.7 已加
- [x] **15.13** 部署到 Pi 驗證：timer next run = Sun 2026-05-17 03:00；markdown export 透過 Caddy 取得 178 檔 zip（177 筆 + manifest），中文檔名保留正確

### ⏸️ 本輪不處理

- 雙向 markdown 匯入（write-back）— 寫端是 1-way 比較安全，避免外部編輯造成 schema 漂移；若有需求再開 Phase 15.5
- markdown frontmatter 包含附件二進位 — 附件用獨立 `attachments/` 資料夾在 zip 內，若太複雜本輪先跳過、frontmatter 只記附件路徑

---

## 🧹 Phase 14: 深度審計修補 (Deep Audit Fixes) — ✅ 已完成 v2.4.6 (2026-05-13)

> **來源**: [`docs/20260513-deep-audit-report.md`](../20260513-deep-audit-report.md) (Claude Opus 4.7 read-only audit, 2026-05-13)
> **目標**: 修補 v2.4.5 後文件層的時差（README/INDEX/TODO/Prism 引用 404、雙頭真理、殭屍 docstring/腳本、測試文件脫節），補上 SSRF / localhost / production-CSRF 的回歸測試。**程式地基已乾淨，本輪以「修承諾對齊事實」為主。**
> **執行順序**: P1 文件閘門 → P1 回歸測試 → P2 殘留清理 → 收尾驗證。禁止跳級。

### 🔴 P1 — 文件導航閘門修補（純文件，不碰程式）

- [x] **14.1** `README.md` / `docs/INDEX.md` / `docs/CONTRIBUTING.md` — 把所有 `docs/20260412-cco-綜合分析報告.md` 引用統一為 `docs/過期/20260412-cco-綜合分析報告.md`（5 條死連結，見審計 §3.2）
- [x] **14.2** `docs/INDEX.md` — 修正維護狀態欄位：cco 報告改 ✅ 已完成 v2.4.2、`SEQUENCE-UPLOAD.md` 改 ✅ 已更新、`API_REFERENCE.md` 改 ✅ 已重寫 (2026-05-05)（見審計 §3.6）
- [x] **14.3** `docs/TODO.md` 頭部 — line 4 移除「Local AI」改為「Headless KMS API + 純關鍵字 FTS 搜尋」；line 5 `1230-審核報告.md` 補 `garbage-can/` prefix；line 6 日期改 `2026-05-13`；line 80 Phase 10 從 🔴 Pending 改 ✅ 已完成 v2.4.2（見審計 §3.3）
- [x] **14.4** `AGENTS.md` ↔ `CLAUDE.md` 雙份完整同步（2026-05-13 補做）：兩份內容對齊（合併 AGENTS 的 Search 欄位描述 + CLAUDE 的 DEPLOY-PI.md 列、Prism.md 標為已凍結、執行規則改為「兩份都要改」）；兩份頂部加 sync banner；`docs/CONTRIBUTING.md` Release Checklist 補 `diff AGENTS.md CLAUDE.md` 比對行；`diff` 驗證僅有 banner 互指對方檔名的差異
- [x] **14.5** `docs/Prism.md` — **明確標記為歷史檔案**（決議：用戶現處純使用模式，戰略路線圖維護不下去；保留 V1→V2 重構決策脈絡的歷史價值）
- [x] **14.6** `tests/README.md` — 刪除過期的 10 檔表格（實際 24+ 檔），改為 `pytest --collect-only` 自動導覽 + 「以 test_run.log 為實際參考」（見審計 §3.7）
- [x] **14.7** `docs/CONTRIBUTING.md` — line 49 `v1–v14` 改 `v1–v15`；line 115 `61 passed` 改「全綠（以 test_run.log 為準）」；Release Checklist 末尾加一行「文件版本 / 日期同步檢查」（見審計 §3.9）

### 🔴 P1 — 安全回歸測試（先加測試，不改程式）

- [x] **14.8** 新增 `tests/test_security_guards.py` — 4 個測試（`test_ssrf_blocks_loopback` / `test_ssrf_blocks_private_range` / `test_server_api_localhost_only` / `test_csrf_production_blocks_anonymous`）

### 🟡 P2 — 殭屍 / docstring 殘留清理（在 14.8 測試保護下動 code）

- [x] **14.9** `routes/system.py:284-296` — `check_consistency()` docstring 與 Response 範例移除 `type_category_mismatch` 殭屍描述，改寫為現況（v12 已移除 `Notes.type`）（見審計 §3.4）
- [x] **14.10** 刪除 `scripts/check_deps.py`（殭屍：仍 import 已拔除的 `numpy` / `sentence_transformers`）
- [x] **14.11** 刪除 `tests/test_offline_mode.py`（V1 Jinja2 遺物，不被 pytest 收集）

### 📋 收尾驗證 (Closure)

- [x] **14.12** 執行 `pytest tests/ -v 2>&1 | tee test_run.log` 重新留下證據（76 passed，2026-05-13 22:24）
- [x] **14.13** 執行 `cd frontend && npx tsc --noEmit && npm run build`，確認 tsc 零錯誤、build 成功
- [x] **14.14** `config.py` `PRISM_VERSION` 升 `2.4.6`；`README.md` 開頭 badge 同步
- [x] **14.15** TODO.md Changelog 新增 v2.4.6 條目（合併 14.1–14.16 摘要）

### 📁 目錄歸檔（依用戶決議）

- [x] **14.16** （2026-05-13 補做）`git mv demo docs/過期/demo`；`README.md` 「專案結構」章節新增 `garbage-can/`（個人歸檔）+ `docs/過期/` 註記，順手把 `migrations/ (v1 → v14)` 修為 `v15`、`tests/ (61+)` 改為「執行 pytest --collect-only 列出，全綠以 test_run.log 為準」

### 💡 未來功能候選（未承諾）

> 已決議啟動的見 Phase 15。其餘想法暫不列入。

- ~~**Prism MCP Server wrapper**~~ — 已評估排除（2026-05-13）：用戶日常工作流為「Web UI 查筆記 + Claude Code 寫程式」兩條線不交集；MCP 不省 token（response 內容照計），單次查詢僅省 ~50 token，需月呼叫 100+ 次才有感，使用模式不符。

---

### ⏸️ 本輪不處理（已評估，列入未來追蹤）

- **R10 / §4.2** `init_db()` 與 migrations 雙寫 schema（v9 ADD → v14 DROP `text_embedding` 對 fresh DB 是空操作）— 屬品味債，不是 bug，未來重寫 init_db 時一併處理
- **R11** `auto_fix_consistency()` 每次冷啟動掃全表 — cco 已決議「等規模到一萬筆再優化」
- **§5.3** `tests/test_batch_type_sync.py` 自定 `get_db()` 繞過 db.py — 雖違反 CLAUDE.md 精神但測試本身有效，列入未來重構
- **§4.3 / §4.4 / §4.5** `frontend/src/i18n/`、`services/` 空殼、`tools/` `build/` `資料庫備份/` 文件未涵蓋 — 待 Phase 15 目錄盤點

### ✅ 已決議（2026-05-13 用戶確認）

1. ✅ **體檢報告位置**：保留在 `docs/過期/`，所有引用統一指向該路徑（見 14.1）
2. ✅ **AGENTS.md / CLAUDE.md**：保留雙份完整內容並要求同步（理由：Codex 可作另一視角 debug）（見 14.4）
3. ✅ **garbage-can / demo**：garbage-can 保留為個人歸檔；demo 搬至 `docs/過期/`（見 14.16）
4. ✅ **Prism.md**：明確標記為歷史檔案，不再更新（見 14.5）
5. ✅ **新 epic**：v2.4.6 後仍維護模式；新功能候選暫列 backlog（見下方「未來功能候選」）

---

