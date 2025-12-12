# Prism

> 🔒 **本地優先** | 📴 **離線可用** | 🚀 **零依賴部署**

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

一句話：**給 AI 創作者的本地知識庫，專注於 Prompt 管理與靈感捕捉。**

---

## 為什麼選 Prism？

| vs 其他工具     | Prism 的優勢                                                 |
| --------------- | ------------------------------------------------------------ |
| **Notion**      | 資料在本機 `SQLite` 單檔儲存，不怕服務關閉，隱私絕佳         |
| **Obsidian**    | 內建視覺化 Prompt Builder 參數組裝器，不需要折騰插件         |
| **純 Markdown** | 擁有類似 Pinterest 的瀑布流卡片介面，結合 Type+Tags 雙重過濾 |

---

## 📸 截圖展示

> _[待補充：主介面截圖 - 瀑布流卡片]_ > _[待補充：Prompt Builder 截圖 - 結構化組裝]_ >

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

---

## ⚡ 馬上體驗（10 秒）

1. 下載釋出版本
2. 把 `demo_db/knowledge_demo.db` 複製到專案根目錄，改名成 `knowledge.db`
3. 執行 `start.bat` (或 `python app.py`) → 直接看到 50+ 則完整範例！

---

## 🚀 正式安裝

### 系統需求

| 軟體                                              | 必要性   | 說明                                               |
| ------------------------------------------------- | -------- | -------------------------------------------------- |
| [Python 3.10+](https://www.python.org/downloads/) | **必要** | 安裝時請勾選 "Add Python to PATH"                  |
| Flask                                             | 必要     | `start.bat` 會自動安裝                             |
| Pillow                                            | 選用     | 用於生成縮圖。未安裝時圖片仍可上傳，但不會產生縮圖 |

> 💡 **免安裝版**：下載 `Prism_*_Portable_*.zip` 完整版，解壓即用，無需安裝任何軟體！

### Windows 使用者

**方法一：懶人包 (推薦)**

1. 雙擊 `start.bat` 啟動（首次會自動安裝依賴）
2. 瀏覽器自動開啟 `http://127.0.0.1:5000`

**方法二：命令列**

```bash
pip install -r requirements.txt
pip install Pillow  # 選用：啟用縮圖功能
python app.py
```

### Linux / macOS 使用者

```bash
chmod +x install.sh
./install.sh
pip install Pillow  # 選用：啟用縮圖功能
```

---

## 💡 小撇步

> **Ctrl + V 貼圖**：在編輯器的 Markdown 文字區按 `Ctrl + V`，即可直接貼上螢幕截圖或剪貼簿中的圖片！

> **備份資料庫前**：請先在設定頁執行「整理資料庫」(VACUUM)，確保 WAL 日誌合併，備份才會完整。或直接使用設定頁的「匯出資料庫」功能。

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

- **刻意不支援遞迴匯入資料夾**：
  - 「知識整理」本身就是一種心智活動
  - 請先在檔案總管把你真的想留下的東西整理好，再匯入
  - 這不是 bug，是 feature

---

## 📁 專案結構

```
Prism/
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
