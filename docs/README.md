# Prism 文檔中心

> **版本**: v2.4.5
> **更新日期**: 2026-05-05
> **狀態**: 🟢 穩定運行 — Headless KMS，AI 功能已移除

主文檔索引請見 [INDEX.md](./INDEX.md)。

---

## 🚀 快速開始

### 目前推薦：Source / Dev mode

1. 安裝 Python 3.10+ 與 Node.js 18+
2. 後端：`pip install -r requirements.txt` 後執行 `python app.py`
3. 前端：`cd frontend && npm install && npm run dev`
4. 瀏覽器開啟 `http://localhost:5173`

### Portable / PyInstaller（後續發佈目標）

Portable / PyInstaller / 一鍵啟動目前不是 v2.4.9 的穩定推薦入口；repo 只保留內部打包流程。除非正式 GitHub Releases 已提供對應 artifacts，請以 Source / Dev mode 或既有 Pi 部署流程為準。

### 開發者

```bash
# 後端
pip install -r requirements.txt
python app.py

# 前端（另開終端機）
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

---

## 🧪 測試

```bash
pytest tests/ -v
# 預期: 61 passed, 1 xfailed, 1 xpassed
```

---

## 📁 文件結構

```
docs/
├── INDEX.md            # 文檔索引（主入口）
├── TODO.md             # 待辦清單 + 版本 Changelog  ← 持續更新
├── SCHEMA.md           # DB Schema + Migration 歷程  ← 持續更新
├── ARCHITECTURE.md     # C4 架構圖
├── Prism.md            # 專案總體戰略
├── API_REFERENCE.md    # REST API 完整參考
├── CONTRIBUTING.md     # 開發者指南
├── DEPLOYMENT.md       # 部署與環境設定
├── ER-DIAGRAM.md       # 資料表 ER 圖
├── SEQUENCE-UPLOAD.md  # 上傳流程 Sequence Diagram
├── docs-V1.41/         # V1.41 舊版文件（歷史備份）
└── 過期/               # 已封存的分析報告
```
