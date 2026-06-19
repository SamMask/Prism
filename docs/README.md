# Prism 文檔中心

> **版本**: v2.5 / Go primary runtime
> **更新日期**: 2026-06-19
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

- `docs/TODO.md` 只保留 active roadmap、候選 backlog 與下一步入口。
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
├── TODO.md            # Active roadmap / next entry only
├── CONTRACTS.md       # Active task contract index
├── RELEASE_CHECKLIST.md # Public release/tag/package validation evidence template
├── SCHEMA.md          # DB Schema + Migration 歷程
├── ARCHITECTURE.md    # C4 架構圖與 Go primary boundary
├── API_REFERENCE.md   # REST API 完整參考
├── CONTRIBUTING.md    # 開發者指南
├── DEPLOYMENT.md      # Go primary deployment
├── ER-DIAGRAM.md      # 資料表 ER 圖
├── SEQUENCE-UPLOAD.md # 上傳流程 Sequence Diagram
├── contracts/         # Contract artifacts
├── development-history/# 舊 TODO / handoff / changelog archive
└── 過期/              # 已封存的分析報告
```

近期歸檔：

- `development-history/go-primary-runtime-completion-20260617.md`
- `development-history/desktop-backup-i18n-handoff-20260617.md`
- `development-history/desktop-portable-release-handoff-20260618.md`

近期 current-truth 更新：

- 2026-06-19：Default category identity split 已完成，schema 為 migration v17；`Categories.system_key` / `name_override` 是系統分類身份與改名的 current contract。
- 2026-06-19：深度掃描報告見 repo root `20260619_Prism_深度掃描報告.md`；`DEEP-SCAN-RISK-CANDIDATE-01` 01A-01G 已關閉主要 local security/runtime risk gates，01H 保留為低優先維護 triage。
- 2026-06-19：`PROJECT-REVIEW-HYGIENE-CANDIDATE-01` 01A-01E 已收斂 GitHub / reuse readiness：root `LICENSE`、CI baseline、verification environment、release evidence checklist 與 CONTRIBUTING E2E path 已對齊。
