> ⚠️ **`CLAUDE.md` / `AGENTS.md` 互為鏡像**：兩份內容必須完全一致（Claude Code 自動讀 `CLAUDE.md`，Codex / 其他外部 Agent 讀 `AGENTS.md`）。修改任一份必須同步另一份；發版前 Release Checklist 會比對 diff。

# Prism 開發指引

## 每次開發前必讀

| 文件 | 內容 |
|---|---|
| `CLAUDE.md` / `AGENTS.md` | 開發規範（哲學 / 禁止事項 / 專案快查） — 雙份鏡像 |
| `DEPLOY-PI.md` | 樹莓派 Go primary 更新流程（artifact deploy、systemd、Caddy、rollback/soak） |
| `docs/ARCHITECTURE.md` | 架構圖（C4 Container Diagram） |
| `docs/SCHEMA.md` | 現行 DB 綱要（所有資料表欄位定義，改 DB 前必讀） |
| `docs/TODO.md` | 原子化 active 待辦與近期更新摘要；完整完成項目 / Changelog 見 `docs/development-history/` |
| `docs/Prism.md` | V2 規劃期歷史記錄（已凍結，不再更新；僅供重構決策脈絡參考） |

### 重大重構 / Go 收尾 / 前端改版額外必讀

| 文件 | 內容 |
|---|---|
| `docs/development-history/Prism_Go_模組逐步重構計劃報告.md` | 已封存的 Python → Go 漸進替換盤點；只供早期 shadow backend / response diff 決策追溯，current truth 以 `docs/TODO.md` 為準 |
| `docs/development-history/Go重構審查報告-20260613-codex.md` | 2026-06-13 Go primary 收尾審查原文；T046-T052 findings 已掃過並收斂，T053 前只作 source 封存/刪除 guardrail，current truth 以 `docs/TODO.md` / contracts / API docs 為準 |
| `docs/FRONTEND-REDESIGN-PLAN.md` | 新 UI 參考檔與 Go 重構路線的整合規劃；採納 UX 工作流，明確暫緩 collections schema、AI、協作與大規模 scope creep |
| `docs/contracts/phase19-go-runtime-packaging.md` | Go runtime / packaging proof；single binary、external data dir、SQLite driver spike、Windows/Pi build plan |
| `docs/New_UI/Prism Redesign - standalone.html` | UI 原型參考；只採工作流與視覺方向，不直接搬 prototype-only code / sample data / tweak panel |

## 執行規則

1. **有未規劃事項** → 先在 `docs/TODO.md` 拆解原子任務，更新後再繼續實作
2. **完成一個階段** → 回頭更新相關文件：
   - `docs/TODO.md`（打 `[x]`、更新近期摘要；長版歷程歸檔到 `docs/development-history/`）
   - `docs/ARCHITECTURE.md`（新模組 / 架構變動時）
   - `docs/SCHEMA.md`（有新 DB 欄位或遷移時）
   - `CLAUDE.md` + `AGENTS.md`（開發規範本身要改時，**兩份都要改**）
3. **測試** → 每次實作後跑 `pytest tests/ -v`；Go runtime / contracts 有變更時加跑 `cd go-shadow && go test ./...`；docs-only 變更至少跑 `git diff --check`、鏡像比對與相關文件 regression

## 專案快查

```
工作目錄：  D:/AI/Prism
Runtime：   scripts/start_go_primary.ps1（Go primary；Python 只保留 legacy/dev/test 到 T053）
前端：      cd frontend && npm run dev
建置：      scripts/build_go_runtime.ps1
測試：      pytest tests/ -v
資料庫：    knowledge.db (SQLite, WAL mode)
設定：      Go external data-dir + config.py legacy source context
```

## 技術堆疊

| 層 | 技術 |
|---|---|
| Backend | Go primary runtime / SQLite (FTS5)；Python Flask source 僅 legacy/dev/test until T053 |
| Frontend | React 18 / TypeScript / Vite / Zustand / Tailwind CSS |
| Search | SQLite FTS5 + 關聯欄位 / 文字附件搜尋（純關鍵字，無 AI） |
| Deploy | Go primary artifact / Raspberry Pi (`prism-go-primary.service` + Caddy) |

## 核心架構

```
[Browser] → [React SPA (Vite)] → [Go Primary REST API] → [SQLite]
                                                      → [File System (uploads/)]
```

- **前後端分離**: Go primary 為 JSON API Server，React SPA 由 Vite 建置並嵌入 artifact
- **Legacy Python**: Python Flask source 保留到 T053 作 source/deletion gate；不得再作產品啟動主路徑
- **資料庫遷移**: Go runtime 已具備 v16 fresh/existing migration runner；Python migrations 僅保留 source parity context 到 T053

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

> **白話說明**：
> 目前 Go primary 已是 live/default runtime，T046-T052 也已把 2026-06-13 收尾審查中的前端漏接 API、文件 current truth 與 stale artifact 清完。
> 下一個大邊界是 T053：封存或刪除剩餘 Python backend source，並把 docs/API/deploy/release wording 收斂成 Go primary runtime truth。
> T053 不是重開 Python 路線，也不是順手做新功能；它只處理 legacy source/dev/test context 的最終歸宿。開始前先確認哪些 Python 檔案仍被 pytest、parity fixture、migration history 或 rollback evidence 需要，不能因為「看起來舊」就刪。
> 若審查報告、舊 roadmap 與 current docs 衝突，以 `docs/TODO.md`、contracts、`docs/API_REFERENCE.md`、runtime source 與新測試為準。

## 禁止事項

- 不引入 AI/ML 依賴（numpy, sentence-transformers, torch 等）— 已拔除
- 不使用 CDN — 所有前端資源必須本地化（離線優先）
- 不破壞現有 API 契約 — 新增可以，修改簽名要建遷移
- 不在 WSGI 請求生命週期內啟動背景執行緒
- 不繞過既有 DB owner/helper 直接散落操作 DB；Go 走現有 SQLite owner / transaction helper，legacy Python source 若仍保留則使用 `db.py` 的 `get_db()`
