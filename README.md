# Local Insight

**本地優先的個人知識庫與 AI 提示詞管理工具**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

---

## ✨ 特色功能

- **📝 筆記管理** - 瀑布流卡片介面，支援 Markdown
- **🎨 Prompt Builder** - 結構化組裝 AI 提示詞
- **🏷️ 標籤系統** - 雙重過濾：分類 + 標籤
- **🕐 版本歷史** - 筆記時光機，隨時還原
- **📦 批量匯出** - 打包下載 Markdown + 圖片
- **🌐 多語系** - 繁體中文 / English
- **🎨 主題切換** - 6 種品牌主題色
- **💾 本地優先** - 資料儲存在本機，隱私安全

---

## 🚀 快速開始

### Windows 使用者

**方法一：雙擊啟動**

1. 首次使用：雙擊 `install.bat` 安裝依賴
2. 日常使用：雙擊 `start.bat` 啟動服務器
3. 開啟瀏覽器：http://127.0.0.1:5000

**方法二：命令列**

```bash
pip install -r requirements.txt
python app.py
```

### Linux / macOS 使用者

```bash
chmod +x install.sh
./install.sh
```

---

## 📁 專案結構

```
Local Insight/
├── app.py              # 主程式入口
├── config.py           # 配置檔案
├── db.py               # 資料庫連線
├── knowledge.db        # SQLite 資料庫
├── requirements.txt    # Python 依賴
├── routes/             # API 路由模組
├── static/             # 前端資源 (CSS/JS/圖片)
├── templates/          # HTML 模板
└── docs/               # 技術文件
```

---

## 🛠️ 技術棧

| 層級     | 技術                    |
| -------- | ----------------------- |
| 後端     | Python 3 + Flask        |
| 資料庫   | SQLite 3                |
| 前端     | Vue.js 3 + Tailwind CSS |
| Markdown | Marked.js               |

---

## 📄 授權

MIT License

---

**Made with ❤️ for personal knowledge management**
