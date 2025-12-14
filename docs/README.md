# Prism 文檔中心

> **版本**: v1.4.1  
> **更新日期**: 2025-12-15

歡迎來到 Prism 專案文檔。本資料夾包含所有技術文檔與開發指南。

---

## 📚 文檔索引

### 入門指南

| 文檔 | 說明 | 適合對象 |
|------|------|----------|
| [DEPLOYMENT.md](./DEPLOYMENT.md) | 部署與環境設定 | 使用者、運維 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 開發者貢獻指南 | 開發者 |

### 技術文檔

| 文檔 | 說明 | 適合對象 |
|------|------|----------|
| [API_REFERENCE.md](./API_REFERENCE.md) | REST API 完整參考 | 開發者 |
| [SCHEMA.md](./SCHEMA.md) | 資料庫結構與遷移歷程 | 開發者、DBA |

### 專案管理

| 文檔 | 說明 | 適合對象 |
|------|------|----------|
| [TODO.md](./TODO.md) | 開發進度與版本歷程 | 專案管理、開發者 |
| [Prism.md](./Prism.md) | 專案完整說明書 | 所有人 |

---

## 🚀 快速開始

### 使用者 (User)

1. 下載發布的 ZIP 檔案
2. 解壓縮後執行 `start.bat`
3. 瀏覽器開啟 `http://127.0.0.1:5000`

### 開發者 (Developer)

```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動開發伺服器
python app.py
```

詳細說明請參考 [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 🧪 測試

```bash
# 建立虛擬環境並執行測試
python -m venv venv
venv\Scripts\activate
pip install flask pytest requests python-magic-bin Pillow
pytest tests/ -v
```

測試覆蓋 Notes, Tags, Categories, Upload, System API 等核心功能。

---

## 📁 目錄結構

```
docs/
├── README.md          # 本文件 (文檔索引)
├── API_REFERENCE.md   # REST API 參考
├── CONTRIBUTING.md    # 開發者指南
├── DEPLOYMENT.md      # 部署說明
├── SCHEMA.md          # 資料庫結構
├── TODO.md            # 開發進度
└── Prism.md           # 專案說明書
```

---

## 📝 文檔維護

- 新增功能時請更新 `TODO.md`
- 修改資料庫結構請更新 `SCHEMA.md`
- API 變更請更新 `API_REFERENCE.md`
