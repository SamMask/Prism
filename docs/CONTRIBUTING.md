# Contributing to Prism

## 快速開始 (Getting Started)

### 環境需求

| 軟體 | 版本 | 說明 |
|------|------|------|
| Python | 3.10+ | 後端運行環境 |
| Node.js | 18+ | 前端建置工具 (Vite) |
| SQLite | 內建 | 無需額外安裝 |

### 安裝依賴

```bash
# 後端
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 啟動開發伺服器

```bash
# 後端 (Flask API Server)
python app.py
# → http://127.0.0.1:5000

# 前端 (Vite HMR，另開終端機)
cd frontend
npm run dev
# → http://127.0.0.1:5173
```

> **V2 模式說明**: 環境變數 `PRISM_V2=true` 讓 Flask 以 React SPA 模式服務。
> 開發時前後端分別啟動；生產部署先 `npm run build`，再 `python app.py`。

---

## 專案結構 (Project Structure)

```
D:/AI/Prism/
├── app.py                  # Flask 應用程式入口 (create_app)
├── config.py               # 設定常數 (PRISM_VERSION, port)
├── db.py                   # 資料庫連線 (get_db / close_db)
├── migrations/             # 版本化 DB 遷移 (v1–v15，啟動時自動執行)
├── routes/                 # Flask Blueprints
│   ├── notes/              # 筆記子模組
│   │   ├── crud.py         # GET/POST/PUT/DELETE /api/notes
│   │   ├── actions.py      # pin / archive / duplicate / reorder
│   │   ├── batch.py        # 批次 category / tags / delete
│   │   ├── history.py      # 版本歷史 / 還原
│   │   ├── import_.py      # 匯入 Markdown
│   │   └── export.py       # 匯出 ZIP
│   ├── tags.py             # 標籤 CRUD + 合併
│   ├── categories.py       # 分類 CRUD
│   ├── upload.py           # 圖片上傳 / 刪除 / URL 下載 / prompt 擷取
│   ├── attachments.py      # 附件管理 + 長文分離
│   ├── cleanup.py          # 孤兒圖片 / 原圖清理 / 斷圖修復
│   ├── system.py           # VACUUM / 統計 / 端口設定 / WAL
│   ├── server.py           # 硬體監控 / 日誌 / 備份 / 版本 (Headless)
│   ├── prompt_options.py   # Prompt Builder 選項配置
│   └── export.py           # JSON / DB / 圖片 匯出入
├── frontend/               # React SPA (Vite)
│   ├── src/
│   │   ├── components/     # UI 組件 (含 ui/ 設計系統)
│   │   ├── hooks/editor/   # NoteEditor 拆分 hooks (6 個)
│   │   ├── pages/          # 路由頁面
│   │   ├── services/api.ts # axios API 客戶端
│   │   └── stores/         # Zustand 狀態 (appStore / toastStore)
│   ├── dist/               # 建置產出 (Flask 靜態服務)
│   └── package.json
├── tests/                  # pytest 測試套件
├── knowledge.db            # SQLite 資料庫 (WAL mode)
└── docs/                   # 技術文件
```

---

## 開發規範 (Development Guidelines)

### 程式碼風格

| 層 | 規範 |
|----|------|
| **Python** | PEP 8，`snake_case`，縮排 ≤ 3 層 |
| **TypeScript / React** | `camelCase` 變數，`PascalCase` 組件，Composition 優先 |
| **CSS** | Tailwind Utility Class 為主；CSS 變數 `--color-*` 定義於 `index.css` |

### 核心原則

- **函式單一職責** — 只做一件事，長度 < 50 行為佳
- **不破壞現有 API 契約** — 新增端點可以，修改現有簽名需建 Migration
- **不直接操作 DB** — 統一使用 `db.py` 的 `get_db()`
- **不引入 AI/ML 依賴** — numpy、torch、sentence-transformers 等已全面移除
- **不使用 CDN** — 所有前端資源必須本地化（離線優先）

### 資料庫遷移

- 遷移腳本位於 `migrations/__init__.py`，依版本號順序執行
- 每個 Migration 必須**冪等**（重複執行結果相同）
- 修改 Schema 前必讀 `docs/SCHEMA.md`

---

## 測試 (Testing)

### 後端 (pytest)

```bash
pytest tests/ -v
# 預期: 全綠（以 test_run.log 為準）
```

測試檔案位於 `tests/`，涵蓋：CRUD、批次操作、標籤合併、上傳安全性、SQL 注入防護。

### 前端 (TypeScript)

```bash
cd frontend
npx tsc --noEmit
# 零錯誤才算通過
```

### E2E (Playwright)

位於 `tests/e2e/`，測試核心流程（新增 / 編輯 / 刪除 / 搜尋）。

---

## 授權規範 (License Compliance)

| 燈號 | 協議 | 策略 |
|------|------|------|
| 🟢 | MIT, Apache 2.0 | 可複製，需保留版權聲明 |
| 🟡 | GPL-3.0 | 僅參考架構，禁止直接複製 |
| 🛑 | AGPL-3.0 | 完全禁止，僅限學習思路 |

---

## 打包發布 (Packaging)

> **狀態說明**: v2.4.9 的穩定主線是 Source / Dev mode 與既有 Raspberry Pi 部署。PyInstaller / Portable 目前僅保留為實驗性或內部打包流程；正式「零依賴、解壓即用、一鍵啟動」發佈要等 UI 改版與 Go 模組基底重構後再重新定義。

### 版本號 (Single Source of Truth)

```python
# config.py
PRISM_VERSION = "2.4.5"
```

> ⚠️ **發版前必檢**：`config.py` 的 `PRISM_VERSION` 必須與 `docs/TODO.md` Changelog 最新一列、`README.md` 開頭 badge 三處同步。
> 過去曾發生 `config.py` 卡在 `2.0.0-alpha.1` 而 Changelog 已到 `v2.4.1` 的長期 desync，詳見 [`docs/過期/20260412-cco-綜合分析報告.md`](./過期/20260412-cco-綜合分析報告.md) §3 P2-10.7。

### 建置流程

```bash
# 1. 建置前端
cd frontend
npm run build

# 2. 實驗性 / 內部打包 EXE (PyInstaller)
python build_release.py
```

| 產出 | 說明 |
|------|------|
| `Prism_v*_*.zip` | 內部打包目標，需安裝 Python；不是目前推薦使用方式 |
| `Prism_v*_Portable_*.zip` | 實驗性 Portable 目標；只有正式 release artifacts 存在時才可視為可交付版本 |

### Release Checklist（每次發版前必確認）

- [ ] `config.py` 的 `PRISM_VERSION` 與 `docs/TODO.md` Changelog 最新版本一致
- [ ] `docs/TODO.md` Changelog 已新增本版條目（版本號、日期、摘要）
- [ ] `README.md` 開頭的版本 badge 已同步
- [ ] `pytest tests/ -v` 全部通過（含 `test_schema_regression.py`）
- [ ] `cd frontend && npx tsc --noEmit` 零錯誤
- [ ] `cd frontend && npm run build` 成功，`frontend/dist/` 已更新
- [ ] 若有新 Migration：確認版本號遞增，且遷移為冪等操作
- [ ] `docs/INDEX.md`、`docs/Prism.md`、`docs/SEQUENCE-UPLOAD.md`、`docs/CONTRIBUTING.md`、`docs/DEPLOYMENT.md` 的版本 / 日期 / 「最後更新」標記已同步本版
- [ ] `AGENTS.md` 與 `CLAUDE.md` 內容已同步（兩份互為鏡像，diff 應僅有檔名相關差異）：`diff AGENTS.md CLAUDE.md`
