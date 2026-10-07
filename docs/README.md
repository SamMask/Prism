# Prism 文檔中心

> **版本**: v2.7.0 / Go primary runtime
> **更新日期**: 2026-10-07
> **狀態**: Go primary 為唯一 runtime owner；Python Flask backend source 已於 T053 移除

主文檔索引請見 [INDEX.md](./INDEX.md)。

---

## 快速開始

### Go primary runtime

```powershell
cd D:/AI/Prism
.\scripts\build_go_runtime.ps1
.\scripts\start_go_primary.ps1
```

本機入口：

- `scripts/start_go_primary.ps1`
- `scripts/start.bat`
- `start_v2.bat`

Pi live 入口：

- `scripts/go_primary_pi_live_ops.ps1`
- `prism-go-primary.service`
- `https://prism.local` through Caddy

### 開發者

```bash
# 前端（另開終端機）
cd frontend
npm install
npm run dev

# 測試
pytest tests/ -v
```

Go runtime / contracts 有變更時另跑：

```bash
cd go-shadow
go test ./...
```

---

## 文件治理

- `docs/GOVERNANCE.md` 是完成宣稱、狀態層級、驗證證據、委派、工單、文件預算與 UI/UX 治理入口。
- `docs/TODO.md` 是工單看板（狀態）、deferred 候選與下一步入口；工單規格在 `docs/WORK_ORDERS.md`。
- 必讀分層：每次開工只讀 `AGENTS.md`／`CLAUDE.md`、`HANDOFF.md`、`docs/TODO.md`；其他文件依任務讀（見 `AGENTS.md`）。
- `HANDOFF.md` 只保留新對話接手需要的最短 current state / next entry。
- 長版完成紀錄、handoff 快照、舊 phase 與 changelog 放在 `docs/development-history/`。
- `AGENTS.md` 與 `CLAUDE.md` 是鏡像；修改任一份必須同步另一份。
- GitHub 預設首頁是英文 `README.md`；繁中首頁是 `README.zh-TW.md`，兩者頂端互相連結。

---

## 文件結構

```
docs/
├── README.md          # 本文件中心入口
├── INDEX.md           # 完整文檔索引
├── GOVERNANCE.md      # 開發治理、完成宣稱、驗證證據與 UI/UX 準則
├── TODO.md            # 工單看板 / next entry
├── WORK_ORDERS.md     # 工單規格（目標、範圍、驗收、Blocked 啟動條件）與派工總表
├── AGENT_DISPATCH.md  # 子代理派工指南（類別×難度 → 代理、模型、effort）
├── CONTRACTS.md       # Active task contract index
├── TEST_PORTFOLIO.md  # Behavior / Contract / Governance / Historical 測試資產分類
├── RELEASE_CHECKLIST.md # Public release/tag/package validation evidence template
├── SCHEMA.md          # DB Schema + Migration 歷程
├── ARCHITECTURE.md    # C4 架構圖、Go primary boundary、已知限制（只放 current truth）
├── API_REFERENCE.md   # REST API 完整參考
├── CONTRIBUTING.md    # 開發者指南
├── DEPLOYMENT.md      # Go primary deployment
├── ER-DIAGRAM.md      # 資料表 ER 圖
├── SEQUENCE-UPLOAD.md # 上傳流程 Sequence Diagram
├── contracts/         # Contract artifacts
└── development-history/# 舊 TODO / handoff / changelog / 架構歷史 archive
```

近期歸檔：

- `development-history/todo-handoff-archive-20261006.md`
- `development-history/architecture-go-migration-history-20261006.md`
- `development-history/governance-source-20260705/`
- `development-history/go-primary-runtime-completion-20260617.md`
- `development-history/desktop-backup-i18n-handoff-20260617.md`
- `development-history/desktop-portable-release-handoff-20260618.md`

近期 current-truth 更新：

- 2026-10-06：全專案審查 `PROJECT_OPTIMIZATION_REVIEW_2026-10-06.md` 完成，findings 轉為工單 PRISM-OPT-15～51（`TODO.md` 看板、`WORK_ORDERS.md` 規格）；治理文件瘦身：`ARCHITECTURE.md` 只留 current truth、`TODO.md`／`HANDOFF.md` 完成紀錄歸檔、必讀改為分層、刪除重複的 `docs2/`。
- 2026-07-05：新版治理素材已歸檔到 `development-history/governance-source-20260705/` 並收斂為 `docs/GOVERNANCE.md`；正式治理入口是該檔、`docs/TODO.md`、`docs/CONTRACTS.md` 與鏡像的 `AGENTS.md` / `CLAUDE.md`。
- 2026-06-19：Default category identity split 已完成，schema 為 migration v17；`Categories.system_key` / `name_override` 是系統分類身份與改名的 current contract。
- 2026-06-19：深度掃描報告已歸檔到 `development-history/20260619_Prism_深度掃描報告.md`；`DEEP-SCAN-RISK-CANDIDATE-01` 01A-01G 已關閉主要 local security/runtime risk gates，01H 保留為低優先維護 triage。
- 2026-06-19：`PROJECT-REVIEW-HYGIENE-CANDIDATE-01` 01A-01E 已收斂 GitHub / reuse readiness：root `LICENSE`、CI baseline、verification environment、release evidence checklist 與 CONTRIBUTING E2E path 已對齊。
