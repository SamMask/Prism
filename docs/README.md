# Prism 文檔中心

> **版本**: v2.4.9 / Go primary runtime
> **更新日期**: 2026-06-13
> **狀態**: Go primary live owner；Python source/dev/test only until T053

主文檔索引請見 [INDEX.md](./INDEX.md)。

---

## 快速開始

### 目前推薦：Go primary runtime

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

Python backend source 與 `requirements*.txt` 只保留為 legacy source / dev / test context；T045 後不再是產品啟動必要條件。T053 會決定 source 最終刪除或封存。

---

## 測試

```bash
pytest tests/ -v
```

---

## 文件結構

```
docs/
├── INDEX.md            # 文檔索引（主入口）
├── TODO.md             # Active Go primary roadmap
├── CONTRACTS.md        # Active task contract index
├── SCHEMA.md           # DB Schema + Migration 歷程
├── ARCHITECTURE.md     # C4 架構圖與 Go primary boundary
├── API_REFERENCE.md    # REST API 完整參考
├── CONTRIBUTING.md     # 開發者指南
├── DEPLOYMENT.md       # Go primary deployment
├── ER-DIAGRAM.md       # 資料表 ER 圖
├── SEQUENCE-UPLOAD.md  # 上傳流程 Sequence Diagram
├── development-history/# 舊 TODO / changelog archive
└── 過期/               # 已封存的分析報告
```
