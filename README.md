# Local Insight

> 🔒 **本地優先** | 📴 **離線可用** | 🚀 **零依賴部署**

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

一句話：**給 AI 創作者的本地知識庫，專注於 Prompt 管理與靈感捕捉。**

---

## 為什麼選 Local Insight？

| vs 其他工具     | Local Insight 的優勢                                         |
| --------------- | ------------------------------------------------------------ |
| **Notion**      | 資料在本機 `SQLite` 單檔儲存，不怕服務關閉，隱私絕佳         |
| **Obsidian**    | 內建視覺化 Prompt Builder 參數組裝器，不需要折騰插件         |
| **純 Markdown** | 擁有類似 Pinterest 的瀑布流卡片介面，結合 Type+Tags 雙重過濾 |

---

## 📸 截圖展示

> _[待補充：主介面截圖 - 瀑布流卡片]_ > _[待補充：Prompt Builder 截圖 - 結構化組裝]_ > _[待補充：主題切換 GIF - 6 種色系]_

---

## 🎯 核心功能

### 1. Prompt Builder（差異化賣點）

結構化組裝 AI 圖像提示詞，解決 "不知道該下什麼指令" 的困擾：

- **風格模板一鍵套用**：內建電影感、賽博龐克、自然光等多種預設
- **參數化調整**：鏡頭角度、光線、材質下拉選單
- **混沌係數**：隨機生成靈感，打破創意僵局
- **直接儲存**：一鍵將組裝好的 Prompt 存入筆記庫

### 2. 本地知識管理

- **� 筆記管理** - 瀑布流卡片介面，支援 Markdown 實時預覽
- **🏷️ 標籤系統** - 靈活的分類 (Category) 與標籤 (Tags) 雙重篩選
- **📦 匯入匯出** - 支援標準 Markdown 批量匯入，隨時可打包搬家
- **� 版本歷史** - 內建筆記時光機，保留每一次修訂，隨時還原

### 3. 極致體驗

- **�🔧 系統維護** - 資料庫緊縮 (Vacuum) 與圖片清理工具
- **🚀 啟動引導** - 自定義瀏覽器開啟偏好
- **🌐 多語系** - 完整支援 繁體中文 / English
- **🎨 主題切換** - 內建 6 種品牌主題色 (Cyberpunk, Elegant Gold, Eye-care...)

---

## 🚀 30 秒快速開始

### Windows 使用者

**方法一：懶人包 (推薦)**

1. 雙擊 `install.bat` 自動安裝依賴 (僅首次)
2. 雙擊 `start.bat` 啟動
3. 瀏覽器自動開啟 `http://127.0.0.1:5000`

**方法二：命令列高手**

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

## � 設計原則

- **離線優先 (Offline First)**：

  - 所有前端資源 (Vue3, Tailwind, Fonts) 全部本地化
  - 拔掉網路線也能完整運作，適合飛機上或無網環境

- **零 Node.js (Zero Dependency)**：

  - 拒絕 `npm install` 黑洞
  - 只需 Python 環境，刻意避免複雜的前端建構工具鏈

- **SQLite 單檔 (Portable)**：
  - 一個 `.db` 檔案就是你的全部資料
  - 備份只需複製該檔案，遷移/還原超簡單

---

## 📁 專案結構

```
Local Insight/
├── app.py              # 主程式入口
├── knowledge.db        # 你的核心資料
├── static/             # 圖片、JS、CSS (全本地資源)
├── templates/          # HTML 模板
└── docs/               # 進階技術文件
```

---

## 📄 授權

MIT License

**Made with ❤️ for personal knowledge management**
