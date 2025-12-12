# Contributing to Prism (Local Insight)

感謝您有興趣參與 Prism 的開發！這份文件將引導您了解專案結構與開發流程。

## 🚀 快速開始 (Getting Started)

### 1. 環境需求

| 軟體         | 必要性   | 說明                               |
| ------------ | -------- | ---------------------------------- |
| Python 3.10+ | **必要** | 核心運行環境                       |
| Flask        | 必要     | 由 `requirements.txt` 安裝         |
| Pillow       | 選用     | 圖片縮圖功能，未安裝時只能上傳原圖 |
| SQLite       | 內建     | 無需額外安裝                       |

### 2. 安裝依賴

```bash
pip install -r requirements.txt
pip install Pillow  # 選用：啟用縮圖功能
```

### 3. 啟動開發伺服器

```bash
python app.py
```

伺服器預設於 `http://127.0.0.1:5000` 啟動。詳細環境變數設定請參考 [部署指南](./DEPLOYMENT.md)。

## 📂 專案結構 (Project Structure)

```
/
├── app.py                 # Flask 應用程式入口與主要路由
├── routes/                # 路由模組 (Blueprints)
│   ├── notes/             # 筆記相關 (CRUD, History)
│   ├── tags.py            # 標籤管理
│   └── ...
├── templates/             # Jinja2 模板 (HTML)
│   ├── components/        # 可重用元件 (Modals, Grids)
│   └── prompt-builder/    # 提示詞產生器元件
├── static/                # 靜態資源
│   ├── css/               # Tailwind (CDN) + Custom CSS
│   ├── js/                # Vue.js 邏輯
│   └── locales/           # i18n 翻譯檔
└── knowledge.db           # SQLite 資料庫 (自動建立)
```

## 🛠 開發規範 (Development Guidelines)

### 1. 程式碼風格 (Code Style)

- **Python**: 遵循 PEP 8。變數命名使用 `snake_case`。
- **JavaScript (Vue)**: 使用 Composition API。變數命名使用 `camelCase`。
- **CSS**: 使用 Tailwind CSS Utility classes 為主，特殊樣式寫在 `styles.css`。

### 2. 資料庫遷移 (Database Migrations)

- 本專案使用輕量級遷移系統。
- 若修改了 `schema.sql`，請確保在 `migrations/` 目錄下建立相應的遷移腳本。
- 使用 `python migrations/manage.py migrate` 執行遷移。

### 3. 國際化 (i18n)

- 所有使用者介面文字**必須**支援多語系。
- 新增文字時，請同步更新 `static/locales/zh-TW.json` 與 `en.json`。

## 🧪 測試 (Testing)

提交修復或新功能前，請確保：

1. **Server 啟動正常**: 執行 `python -c "from app import create_app; print(create_app())"` 無錯誤。
2. **基本功能運作**: 新增/編輯/刪除筆記功能正常。
3. **無主控台錯誤**: 瀏覽器 Console 無紅色錯誤訊息。

## 📝 提交變更 (Submitting Changes)

- 請保持 Commit 訊息簡潔明確 (例如: `fix: text contrast issue` 或 `feat: auto-title generation`)。
- 重大變更請先更新 `docs/TODO.md` 或 `implementation_plan.md`。

## 📦 打包發布 (Packaging)

發布新版本時，執行以下腳本：

| 腳本                        | 產出                              | 說明                          |
| --------------------------- | --------------------------------- | ----------------------------- |
| `scripts\pack.bat`          | `Prism_v*_*.zip` (~8MB)           | 輕量版，用戶需先安裝 Python   |
| `scripts\pack_portable.bat` | `Prism_v*_Portable_*.zip` (~80MB) | 完整版，內嵌 Python，解壓即用 |

### 版本號更新

發布前請更新以下檔案中的版本號：

- `scripts/pack.bat` 和 `scripts/pack_portable.bat` 中的 `VERSION`
- `start.bat` 標題
- `README.md` 徽章

## 🤝 行為準則 (Code of Conduct)

保持友善、尊重。我們致力於打造一個開放、包容的開發環境。
