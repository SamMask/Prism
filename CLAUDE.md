> ⚠️ **本檔與 `AGENTS.md` 互為鏡像**：兩份內容必須完全一致（Claude Code 自動讀 `CLAUDE.md`，Codex / 其他外部 Agent 讀 `AGENTS.md`）。修改任一份必須同步另一份；發版前 Release Checklist 會比對 diff。

# Prism 開發指引

## 每次開發前必讀

| 文件 | 內容 |
|---|---|
| `CLAUDE.md` / `AGENTS.md` | 開發規範（哲學 / 禁止事項 / 專案快查） — 雙份鏡像 |
| `DEPLOY-PI.md` | 樹莓派更新流程（日常 tar+SSH sync、首次 venv 設定、常見問題） |
| `docs/ARCHITECTURE.md` | 架構圖（C4 Container Diagram） |
| `docs/SCHEMA.md` | 現行 DB 綱要（所有資料表欄位定義，改 DB 前必讀） |
| `docs/TODO.md` | 原子化待辦清單與版本歷程 |
| `docs/Prism.md` | V2 規劃期歷史記錄（已凍結，不再更新；僅供重構決策脈絡參考） |

## 執行規則

1. **有未規劃事項** → 先在 `docs/TODO.md` 拆解原子任務，更新後再繼續實作
2. **完成一個階段** → 回頭更新相關文件：
   - `docs/TODO.md`（打 `[x]`、更新 Changelog）
   - `docs/ARCHITECTURE.md`（新模組 / 架構變動時）
   - `docs/SCHEMA.md`（有新 DB 欄位或遷移時）
   - `CLAUDE.md` + `AGENTS.md`（開發規範本身要改時，**兩份都要改**）
3. **測試** → 每次實作後跑 `pytest tests/ -v`

## 專案快查

```
工作目錄：  D:/AI/Prism
Python：    python (venv)
前端：      cd frontend && npm run dev
後端：      python app.py
測試：      pytest tests/ -v
建置前端：  cd frontend && npm run build
資料庫：    knowledge.db (SQLite, WAL mode)
設定：      config.py + .port_config
```

## 技術堆疊

| 層 | 技術 |
|---|---|
| Backend | Python 3.10+ / Flask / SQLite (FTS5) |
| Frontend | React 18 / TypeScript / Vite / Zustand / Tailwind CSS |
| Search | SQLite FTS5 + 關聯欄位 / 文字附件搜尋（純關鍵字，無 AI） |
| Deploy | PyInstaller (exe) / Raspberry Pi (systemd + Caddy) |

## 核心架構

```
[Browser] → [React SPA (Vite)] → [Flask REST API] → [SQLite]
                                                   → [File System (uploads/)]
```

- **前後端分離**: Flask 為純 JSON API Server，React SPA 由 Vite 建置
- **V2 模式**: 環境變數 `PRISM_V2=true` 啟用 React SPA，否則 fallback 到 V1 Jinja2 模板
- **資料庫遷移**: `migrations/__init__.py` 版本化遷移，啟動時自動執行

## 開發哲學

- **實用主義優先**：解決實際問題，不做過度設計
- **簡潔至上**：函式短小、縮排不超過 3 層、消除特殊情況優於增加條件判斷
- **不破壞使用者空間**：向後相容是鐵律，DB 遷移必須冪等
- **語言**：以英文思考，以繁體中文表達

## Anti-Bloat Principle（反膨脹原則）

每次開發都以「符合 contract 的最小變更」為準，主動避免未被需求證明的抽象化、重構與跨檔案擴散。

- **Planning**：先找能滿足 `docs/TODO.md`、`docs/SCHEMA.md`、現有 API/schema contract 與架構邊界的最小改動。優先改既有模組，不新增不必要的 file、service、manager、adapter、factory、registry 或 compatibility layer。
- **Implementation**：不得加入未被任務、runtime safety、schema compatibility 或 contract 要求的 future-proofing、泛化抽象、fallback、retry、logging、cache、config layer、migration code。不得跨層重複 validation、schema/config/API/domain assumptions。保持 backend、frontend、DB、search、deploy 邊界清楚；若簡單需求開始變大，先停下重估。
- **Final review**：檢查 diff 時優先刪掉不必要的 code、file、class、function、abstraction 或 compatibility path。若保留額外複雜度，需說明必要性、考慮過的更簡方案、以及由什麼測試或 contract 驗證。

Anti-bloat 不等於最短程式碼；不得犧牲 correctness、tests、runtime safety、schema integrity 或 contract boundaries。必要的 validation、error handling 與 tests 不是 bloat。目標是減少沒有理由的 moving parts。

## 禁止事項

- 不引入 AI/ML 依賴（numpy, sentence-transformers, torch 等）— 已拔除
- 不使用 CDN — 所有前端資源必須本地化（離線優先）
- 不破壞現有 API 契約 — 新增可以，修改簽名要建遷移
- 不在 WSGI 請求生命週期內啟動背景執行緒
- 不直接操作 DB — 統一使用 `db.py` 的 `get_db()`
