# Contributing to Prism

## 快速開始 (Getting Started)

### 環境需求

| 軟體 | 版本 | 說明 |
|------|------|------|
| Go | current stable | Go primary runtime |
| Node.js | 18+ | 前端建置工具 (Vite) |
| Python | 3.10+ | Dev/test only (pytest)；無 backend source |
| SQLite | 內建 | 無需額外安裝 |

### 安裝依賴

```bash
cd frontend
npm install
```

### 啟動開發伺服器

```bash
# Go primary API Server
.\scripts\build_go_runtime.ps1
.\scripts\start_go_primary.ps1
# → http://127.0.0.1:5004

# 前端 (Vite HMR，另開終端機)
cd frontend
npm run dev
# → http://127.0.0.1:5173
```

> **Runtime 說明**: React SPA 由 Go primary artifact 嵌入與服務。Python backend source 已於 T053 移除；Go primary 為唯一產品 runtime。

---

## 專案結構 (Project Structure)

```
D:/AI/Prism/
├── go-shadow/              # Go primary runtime source（唯一 backend；notes/tags/categories/upload/cleanup/import-export/server/system 全 Go-owned）
│   ├── main.go             # 所有 API handler + SQLite owner + migration runner + 嵌入式 SPA
│   └── main_test.go        # Go 單元/整合測試
├── scripts/start_go_primary.ps1 # Product startup entrypoint
# Python Flask backend source（app.py / routes/ / utils/ / db.py / config.py / migrations/）已於 T053 移除
├── frontend/               # React SPA (Vite)
│   ├── src/
│   │   ├── components/     # UI 組件 (含 ui/ 設計系統)
│   │   ├── hooks/editor/   # NoteEditor 拆分 hooks (6 個)
│   │   ├── pages/          # 路由頁面
│   │   ├── services/api.ts # axios API 客戶端
│   │   └── stores/         # Zustand 狀態 (appStore / toastStore)
│   ├── dist/               # 建置產出（嵌入 Go artifact）
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
| **Go** | 小函式、明確錯誤處理、維持 data-dir / path safety |
| **Python** | Legacy source/test 修改仍用 PEP 8，`snake_case`，縮排 ≤ 3 層 |
| **TypeScript / React** | `camelCase` 變數，`PascalCase` 組件，Composition 優先 |
| **CSS** | Tailwind Utility Class 為主；CSS 變數 `--color-*` 定義於 `index.css` |

### 核心原則

- **函式單一職責** — 只做一件事，長度 < 50 行為佳
- **不破壞現有 API 契約** — 新增端點可以，修改現有簽名需建 Migration
- **不直接操作 DB** — 統一使用 `db.py` 的 `get_db()`
- **不引入 AI/ML 依賴** — numpy、torch、sentence-transformers 等已全面移除
- **不使用 CDN** — 所有前端資源必須本地化（離線優先）

### 資料庫遷移

- Go runtime 為唯一 migration path（v16 fresh/existing）；Python migration source 已於 T053 移除
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

> **狀態說明**: v2.4.9+ 的穩定主線是 Go primary runtime artifact 與 Raspberry Pi `prism-go-primary.service` 部署。PyInstaller / embedded Python portable path 已由 T045 移除。
> T052 後，repo 不再追蹤 embedded Python zip、Pillow wheel 或 root empty `package-lock.json`；前端 lockfile 只在 `frontend/package-lock.json`。

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

# 2. 建置 Go primary package
scripts\pack.bat
```

| 產出 | 說明 |
|------|------|
| `Prism_v2.4.9-go-primary_*.zip` | Go primary artifact package；不包含 embedded Python runtime |

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
