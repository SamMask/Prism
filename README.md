# Prism

> 🔒 **本地優先** | 📴 **離線可用** | 🧠 **Headless KMS**
> 📦 **目前推薦**：Go primary runtime artifact（Node.js / Go 用於建置）
> 🧪 **Python source/dev/test only**：Python backend source 保留到 T046 作 legacy/deletion gate

![Version](https://img.shields.io/badge/version-2.4.9-blue)
![Go](https://img.shields.io/badge/runtime-Go%20primary-green)
![Frontend](https://img.shields.io/badge/react-18-61dafb)
![License](https://img.shields.io/badge/license-MIT-yellow)

**個人知識中樞與 Prompt 管理工具。一個 SQLite 檔案就是你的全部資料。**

> v2.3.0 (2026-04-04) 起，Prism 拔除所有本機 AI / Embedding 功能，正式轉型為 **Headless KMS**：
> 一個專注、極速、可被外部 Agent (Claude / MCP / 自訂腳本) 呼叫的純筆記 API。
> AI 智慧由外部代理負責，Prism 只做最擅長的事——**穩定的儲存、極速的全文檢索、乾淨的 REST API**。

---

## 📚 文件導覽

| 想做的事 | 看這份 |
|---|---|
| 第一次使用 | 本檔 §快速開始 |
| 開發 / 改 code | [`CLAUDE.md`](CLAUDE.md) — 開發規範與哲學 |
| 了解架構 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — C4 容器圖 |
| 改 DB | [`docs/SCHEMA.md`](docs/SCHEMA.md) — 資料表完整定義 |
| API 串接 | [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) |
| 看待辦 | [`docs/TODO.md`](docs/TODO.md) — 原子任務 + Changelog |
| 部署 | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — 樹莓派 / Caddy / systemd |
| 歷史背景參考 | [`docs/Prism.md`](docs/Prism.md) — V2 規劃期歷史記錄（不再更新） |
| **最新體檢報告** | [`docs/過期/20260412-cco-綜合分析報告.md`](docs/過期/20260412-cco-綜合分析報告.md) |

---

## ✨ 核心特色

- **🧠 Headless KMS** — 純 REST API 設計，可被 Claude Code / MCP / 任何 LLM Agent 直接呼叫
- **🔍 卡片全文檢索** — 標題、內文、備註、附件、標籤皆可查，純關鍵字、零 AI 依賴
- **🎨 React SPA** — Vite + Zustand + Tailwind，完全離線、無 CDN
- **🛠️ Prompt Builder** — 結構化參數表單、權重滑桿、亂數靈感
- **📎 附件系統** — 拖曳上傳、長文自動分離、Markdown 雙向同步
- **🌳 卡片譜系** — Parent / Variant 關聯，追蹤 Prompt 演化
- **🔄 時光機** — 每次儲存自動快照，可隨時回滾
- **🍓 樹莓派友善** — Phase 8 提供 avahi mDNS + Caddy 反向代理 + systemd 一鍵部署；定位為 trusted LAN / VPN 使用，不建議直接對公網開放
- **🔒 隱私優先** — 所有資料在本機 `knowledge.db` 單檔 (WAL Mode)，無雲端、無遙測

---

## 🚀 快速開始

### Go primary runtime（目前推薦）

```powershell
cd D:/AI/Prism
.\scripts\build_go_runtime.ps1
.\scripts\start_go_primary.ps1    # -> http://127.0.0.1:5004
```

熟悉的批次入口也會啟動 Go primary：

```cmd
start_v2.bat
scripts\start.bat
```

### 開發前端

```bash
cd frontend
npm install
npm run dev                      # -> http://localhost:5173
```

### Package

```cmd
scripts\pack.bat
```

PyInstaller / embedded Python portable path 已在 T045 移除；Python source 只保留 legacy/dev/test 到 T046。Python runtime 不依賴 Pillow；thumbnail generation 已由 Go helper / Go primary 路徑承接。

---

## 🧪 開發與測試

```bash
# 跑全部測試
pytest tests/ -v

# 跑單一檔
pytest tests/test_notes_crud.py -v

# 前端 type-check + build
cd frontend && npm run build

# 資料庫一致性檢查（API）
curl http://127.0.0.1:5004/api/system/check-consistency
```

> ⚠️ **注意**：目前 (v2.4.1) 測試 fixture 仍走手寫 schema 而非真實 migration，
> 部分 schema regression 不會被測試捕捉到。詳見
> [`docs/過期/20260412-cco-綜合分析報告.md`](docs/過期/20260412-cco-綜合分析報告.md) §2.1。

---

## 🏗️ 技術堆疊

| 層 | 技術 |
|---|---|
| Backend | Go primary runtime / SQLite (FTS5, WAL) |
| Frontend | React 18 / TypeScript / Vite 5 / Zustand / Tailwind CSS |
| Search | SQLite FTS5（純關鍵字，無向量） |
| Image | Go WebP thumbnail generation |
| Deploy | Go primary artifact / Raspberry Pi (`prism-go-primary.service` + Caddy + avahi) |
| Test | pytest（legacy Python/source regression + Go migration/static gates）/ Playwright（前端 E2E） |

---

## 📂 專案結構

```
Prism/
├── go-shadow/                # Go primary runtime source
├── scripts/start_go_primary.ps1 # 本機 Go primary 啟動入口
├── app.py                    # Legacy Python source until T046
├── config.py                 # Legacy Python source context
├── db.py                     # Legacy Python DB source context
├── routes/                   # Legacy Flask route source until T046
│   ├── notes/                # CRUD / actions / history / batch / import / export
│   ├── attachments.py        # Phase 3.4 附件系統
│   ├── upload.py             # 圖片上傳 + URL 下載 + AI metadata 提取
│   ├── system.py             # VACUUM / WAL / 一致性檢查 / port-config
│   ├── server.py             # Phase 8.2 樹莓派 Server Dashboard
│   ├── categories.py / tags.py / cleanup.py / export.py
│   └── prompt_options.py / wizard_options.py
├── migrations/               # Legacy Python migration source; Go owns runtime migration path
├── utils/
│   └── query_builder.py      # NoteQueryBuilder + sanitize_fts_query
├── tests/                    # pytest 測試套件（執行 pytest --collect-only 列出，全綠以 test_run.log 為準）
├── frontend/                 # React SPA
│   └── src/
│       ├── components/       # NoteCard / NoteEditor / DataManager / ...
│       ├── pages/            # HomePage / SettingsPage / PromptBuilder
│       ├── stores/           # Zustand state
│       └── services/api.ts   # 統一 API client + axios interceptor
├── deploy/                   # 樹莓派 Go primary setup templates
├── docs/                     # 完整文件（含 docs/過期/：歷史審計報告 + 舊 demo UI）
├── garbage-can/              # 個人歸檔（V1 設計筆記、雜物） — 非開發必讀
└── knowledge.db              # 你的所有資料 (SQLite, WAL)
```

---

## 🔐 安全與隱私

> ⚠️ **API 暴露邊界**：Prism API / Go runtime 目前沒有內建 API Token / Bearer Token / 使用者認證機制。預設使用場景是 `localhost`、trusted LAN、VPN，或 SSH tunnel / 受認證保護的 reverse proxy（例如 Caddy auth）。不要把 Go runtime 或 Caddy 入口直接暴露到 public internet / 公網。

- ✅ **CSRF 防護**：驗證 Origin / Referer
- ✅ **路徑穿越防護**：圖片 API 三層防禦 (basename + `..` 過濾 + abspath prefix)
- ✅ **Magic Number 驗證**：上傳圖片必須通過 MIME 真實型別檢查
- ✅ **FK 強制啟用**：資料庫連線啟動時驗證 `PRAGMA foreign_keys`
- ✅ **FTS Token 限制**：搜尋 token 上限 20，防 DoS
- ✅ **SSRF 防護**：`/api/upload/url` 已過濾 loopback / private / link-local 位址（v2.4.2）；詳見 [體檢報告 §2.2](docs/過期/20260412-cco-綜合分析報告.md)

---

## 💡 使用小撇步

- **Ctrl + V 貼圖**：在編輯器內直接貼上剪貼簿圖片
- **拖曳排序**：自訂排序模式可拖曳卡片
- **時光機**：點筆記右上角 → 「歷史版本」
- **長文自動分離**：超過閾值的內容會自動轉成 .md 附件
- **資料庫維護**：設定 → 系統維護 → VACUUM
- **未儲存防護**：關閉編輯器時若有未儲存變更會攔截

---

## 📦 版本歷程（最近）

| 版本 | 日期 | 重點 |
|---|---|---|
| v2.4.9 | 2026-05-26 | 非首頁點分類/標籤會回首頁並套用篩選 |
| v2.4.8 | 2026-05-26 | Preview 模式可就地編輯段落並移除圖片引用 |
| v2.4.5 | 2026-05-05 | 搜尋覆蓋標題、內文、備註、附件、標籤 |
| v2.4.4 | 2026-04-24 | 前後端 API 契約修補 |
| v2.4.3 | 2026-04-24 | 外部 Agent API 對接整理 |
| v2.4.2 | 2026-04-12 | cco 體檢報告修補 |
| v2.4.1 | 2026-04-04 | IconButton 統一、tsc 零錯誤 |
| v2.4.0 | 2026-04-04 | NoteEditor 拆 hooks、Toast → Zustand、api.ts 完整型別 |
| **v2.3.0** | **2026-04-04** | **AI 全面拔除，轉型 Headless KMS** |
| v2.2.0 | 2026-03-15 | 全域錯誤攔截 + ConfirmDialog + 標籤自動補全 |
| v2.1.2 | 2026-03-15 | Pi Server Dashboard |
| v2.1.1 | 2026-03-15 | Pi 反向代理 + systemd |
| v2.1.0 | 2026-03-15 | 更新檢查 + 啟動 migration |
| v1.5.1 | 2026-02-27 | 未儲存變更防護 |
| v1.5.0 | 2026-02-27 | 圖片管理增強 + 端口自選 |

完整歷程見 [`docs/TODO.md`](docs/TODO.md) Changelog。

---

## 🤝 開發哲學

- **實用主義優先** — 解決實際問題，不做過度設計
- **簡潔至上** — 函式短小、縮排不超過 3 層、消除特殊情況優於增加條件
- **不破壞使用者空間** — 向後相容是鐵律，DB migration 必須冪等
- **語言** — 以英文思考，以繁體中文表達

完整開發規範見 [`CLAUDE.md`](CLAUDE.md)。

---

## 📜 授權

MIT License — 見 [`LICENSE`](LICENSE)（若不存在請補上）。

---

**Built for personal knowledge management. Designed to outlive its creator's enthusiasm.**
