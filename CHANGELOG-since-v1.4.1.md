# Prism — V1.4.1 → v2.5 重大演進

> **時間範圍**：2026-01-27（V1.4.1 公開版）→ 2026-06-19（v2.5 本地 / Pi）
> **目的**：給「只記得 GitHub 上 V1.4.1」的人一份可讀的重點追溯。
> **公開版**：[github.com/SamMask/Prism](https://github.com/SamMask/Prism)（仍停在 V1.4.1）

---

## 🎯 一句話總結

V1.4.1 是「**個人 Prompt 管理工具**」，v2.5 是「**Go primary 單一 runtime 的個人 Headless 知識中樞 + Windows portable + 樹莓派常駐服務**」。中間繞了一圈 AI（v2.3.0 全部拔除），最後回歸「純關鍵字 FTS + 乾淨 REST API」路線；v2.4.8–v2.4.9 收斂 Preview / Sidebar 工作流，v2.5 則完成 Go primary、desktop portable、schema v17 category identity 與近期 UX 穩定化。

---

## 📊 兩個版本快速對照

| 維度 | V1.4.1 | v2.5 |
|---|---|---|
| 前端 | Vanilla JS + Tailwind（無 build） | React 18 + TS + Vite + Zustand + Tailwind |
| 後端 | Flask 單體 + SQLite FTS5 | Go primary REST API + SQLite WAL / FTS5；Python Flask backend source 已移除 |
| AI | 無 | 中途引入 NIM / Ollama / sentence-transformers，**v2.3.0 全部拔除** |
| 部署 | Windows Portable `.zip` | Windows desktop portable `Prism.exe` + Raspberry Pi Go primary service（systemd + Caddy mDNS + 每週 DB backup / deploy data snapshot） |
| 對外 API | 內部用 | **Headless KMS REST API**（外部 Agent 可直連，含對接文件） |
| 搜尋範圍 | title + content | title + content + remarks + tags + attachment metadata + bounded text attachment body scan |
| 匯出 | JSON 備份 | JSON / SQLite DB / **Markdown zip (frontmatter)** / 圖片 zip |
| 安全 | 基本 | SSRF 防護 / localhost-only guard / 生產 CSRF / 檔案 magic 驗證 |
| 測試 | 無自動化 | 350+ pytest acceptance / docs contract tests + Go unit tests + frontend build + smoke/gate scripts |
| 文件 | 1 份 README | README / docs center / ARCHITECTURE / SCHEMA / API_REFERENCE / DEPLOY-PI / TODO / HANDOFF + 審計報告 |

---

## 🛠 重大架構轉折

### 1. 前端全面重寫（V1 Jinja2 → V2 React SPA → Go primary embedded SPA）

V1 是 Flask 直接 render Jinja2 + Vanilla JS。早期 V2 曾拆成「Flask 純 JSON API + React SPA」雙層，由 Vite 打包；v2.5 current truth 則是 Go primary REST API 服務同一套 React SPA，Python Flask backend source 已移除。

### 2. AI 引入 → 全面拔除（v2.3.0, 2026-04-04）

中間嘗試過 NVIDIA NIM 智慧標籤、Ollama 語意搜尋、sentence-transformers embeddings、Hybrid Search、RAG Knowledge API。最後一次性砍掉所有 AI 依賴（numpy / torch / sentence-transformers），定位回**純筆記 + Headless KMS**，AI 部分交給外部 Agent 處理。Migration v14 砍掉 `text_embedding` / `ai_*` 欄位。

### 3. 樹莓派常駐部署（v2.1.1, 2026-03-15）

V1 只能在 Windows 上跑。V2 加入 Pi 部署：avahi mDNS（`prism.local`） + Caddy 反向代理（80→5000） + systemd 自啟 + 一鍵安裝腳本 + 服務管理 Dashboard（硬體監控 / 日誌檢視 / 服務重啟 / 備份管理）。**等於有了一台隨時可訪問的家用知識伺服器**。

### 4. Headless KMS API 路線（v2.4.3, 2026-04-24）

整理出可直接給外部 Agent（Claude Code / Codex / 自製腳本）使用的 REST API 對接文件，REST 契約穩定後，Prism 從「網頁筆記應用」變成「**任何 client 都能呼叫的個人知識後端**」。

### 5. 安全強化（v2.4.2, 2026-04-12）

cco 審計後一次性補完：SSRF 防護（拒絕內網 / loopback IP）、`/api/server/*` localhost-only guard、生產 CSRF（V2_MODE + non-debug 拒絕無 Origin 的 unsafe method）、檔案 magic number 驗證。

### 6. 全自動備份（v2.4.7, 2026-05-13）

Pi systemd timer 每週日 03:00 自動 `curl /api/server/backup/download` + `/rotate`（`keep_count=3`），保留最近 3 份。**踩過的坑**：Caddy → Werkzeug HTTP/2 stream 收尾不乾淨會讓 curl exit 92，必須強制 `--http1.1`。

### 7. Preview 編輯體驗修補（v2.4.8, 2026-05-26）

Preview 模式從純閱讀面板變成可互動編輯面：文字區塊可在 Preview 中就地切入小型 Markdown textarea 修改；獨立 Markdown / HTML 圖片可直接移除內容引用；圖片引用移除邏輯與側欄圖片管理共用 helper，避免重複維護。

### 8. Sidebar 篩選導覽修補（v2.4.9, 2026-05-26）

分類 / 標籤點擊被明確收斂成首頁卡片篩選器：在非首頁點擊會回到首頁並套用篩選；首頁仍保留再次點同一篩選可取消的互動。前端 notes 查詢改送 `category_id`，降低對已移除 `Notes.type` 名稱相容層的依賴風險。

### 9. Go primary / Desktop portable / category identity 收斂（v2.5, 2026-06-19）

Go primary 已是唯一 product runtime；Python Flask backend source 已於 T053 移除。Windows desktop portable 走 `Prism.exe` + exe 同層 `PrismData\`，Pi live 走 `prism-go-primary.service` + Caddy。近期完成 Reading workspace、Image lightbox、Header starred tags、Batch Markdown/txt import、Note list lightweight payload、Variant attachment preservation、Version 2.5 display，以及 migration v17 的 default category identity split（`system_key` / `name_override`）。本線仍不新增 AI、semantic search、多使用者 auth 或雲端同步。

---

## 📅 版本歷程（精簡）

| 版本 | 日期 | 主軸 |
|---|---|---|
| **v2.5** | 2026-06-19 | Go primary sole runtime、Windows desktop portable baseline、recent UX gates、schema v17 default category identity split |
| **v2.4.9** | 2026-05-26 | Sidebar filter navigation：非首頁點分類 / 標籤會回首頁並套用篩選；notes 查詢改送 `category_id` |
| **v2.4.8** | 2026-05-26 | Preview Editing UX：Preview 可就地編輯文字區塊、移除 Markdown / HTML 圖片引用，並共用圖片引用移除 helper |
| **v2.4.7** | 2026-05-13 | Markdown 匯出 + 自動備份 timer |
| **v2.4.6** | 2026-05-13 | 深度審計修補（文件對齊 / 安全回歸測試 / 殭屍清理） |
| **v2.4.5** | 2026-05-05 | 搜尋範圍擴充（覆蓋備註 / 附件 / 標籤） |
| **v2.4.4** | 2026-04-24 | 前後端 API 契約修補 |
| **v2.4.3** | 2026-04-24 | 外部 Agent API 對接整理 |
| **v2.4.2** | 2026-04-12 | cco 審計後安全強化（SSRF / localhost / CSRF） |
| **v2.4.0–2.4.1** | 2026-04-04 | 前端技術債清償 + IconButton 統一 |
| **v2.3.0** | 2026-04-04 | **AI 全面拔除**（轉型 Headless KMS） |
| **v2.2.0** | 2026-03-15 | UX 強化（全域錯誤攔截、ConfirmDialog、autoFocus、tag 補全） |
| **v2.1.2** | 2026-03-15 | Pi Server Dashboard |
| **v2.1.1** | 2026-03-15 | **Pi 部署**（avahi + Caddy + systemd） |
| **v2.1.0** | 2026-03-15 | check-update API + 啟動遷移 |
| **(中間)** | 2026-02–03 | React 重寫（Phase 1-2 現代化地基 + 功能復刻） |
| **v1.5.1** | 2026-02-27 | Unsaved Changes Guard |
| **v1.5.0** | 2026-02-27 | 圖片管理增強 + 端口自選 |
| **V1.4.1** | 2026-01-27 | **GitHub 公開版基準** |

---

## ⚠️ 不相容變更（從 V1.4.1 升級）

如果有 V1.4.1 的 `knowledge.db` 想升上來：

1. **可以直接升級** — Go primary runtime 啟動時會跑 v1→v17 migration，向後相容（這是專案鐵律）
2. `Notes.type` 欄位已移除（v12），但 migration 自動轉成 `category_id`
3. AI 相關欄位（`text_embedding` / `ai_*`）若 V1 沒寫過，無感
4. 目前只有 Go primary + React SPA 產品路徑；舊 Flask/Jinja runtime 與 Python backend source 已移除，不再有 `PRISM_V2=false` 的 V1 模板路線

**API 契約**：Go primary 保留目前 REST contract；舊 Flask/Jinja runtime 已不是產品路徑。外部 Agent 應以 `docs/API_REFERENCE.md` 的 current Go primary API 為準。

---

## 🚫 已廢棄方向（v2.4.6 清算）

走過但最終放棄的路線（避免你之後想到「咦這個怎麼沒做」時又被誘惑）：

- **AI 整合**（NIM / Ollama / Embeddings）— v2.3.0 拔除
- **知識畫布 / Graph View** — 個人 KMS 視覺化價值近零
- **參數 Diff View** — Parent/Child 連結已覆蓋實際需求
- **內建更新器 Plan B** — Plan A（download + UpdateSection）已夠用
- **進階多媒體 (Whisper / SD)** — 與「拔除 AI」戰略矛盾
- **外掛生態** — 個人工具不需要外掛市場

---

## 🔗 進一步閱讀

- [docs/TODO.md](docs/TODO.md) — 原子化版本歷程與 Changelog
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — C4 架構圖
- [docs/SCHEMA.md](docs/SCHEMA.md) — 現行 DB 綱要
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md) — REST API 對接文件
- [DEPLOY-PI.md](DEPLOY-PI.md) — 樹莓派部署 + 自動備份排程
- [docs/過期/20260412-cco-綜合分析報告.md](docs/過期/20260412-cco-綜合分析報告.md) — Linus-mode 深度體檢
- [docs/20260513-deep-audit-report.md](docs/20260513-deep-audit-report.md) — 最近一次審計報告
