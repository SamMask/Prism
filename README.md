# Prism

> 🔒 **本地優先** | 📴 **離線可用**  
> 🚀 **Portable 版**: 零依賴，解壓即用  
> 📦 **Light 版**: 需 Python 3.10+

![Version](https://img.shields.io/badge/version-1.4.1-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

一句話：**給 AI 創作者的本地知識庫，專注於 Prompt 管理與靈感捕捉。**

---

## ✨ 核心特色

- **可視化 Prompt Builder**：積木式組裝 AI 提示詞，內建風格模板、參數權重與亂數靈感，告別手打指令。
- **極致 UX 體驗**：採用 **Waterfall Grid** (瀑布流) 佈局，專注於內容呈現，提供流暢的閱覽體驗與微互動回饋。
- **絕對隱私**：所有資料儲存於本機 `SQLite` 單檔 (WAL Mode 優化)，無需連網，無訂閱制，隨時可打包帶走。
- **輕量架構**：純 Python + Flask 開發，無需 Node.js 與複雜構建工具。

---

## 📸 介面預覽

![alt text](/resources/index.png)
![alt text](/resources/prompt-builder.png)


---

## 🚀 快速開始 (10 秒)

1. **下載** `Prism_Portable_x.x.zip` (推薦)。
2. **解壓** 後點擊 `start.bat`。
3. **完成**！系統將自動開啟瀏覽器進入 `http://127.0.0.1:5000`。

## 📦 安裝說明

| 版本 | 適用對象 | 大小 | 說明 |
| :--- | :--- | :--- | :--- |
| **Portable** | 一般使用者 | ~80MB | **推薦**。內建 Python 環境，解壓即用。 |
| **Light** | 開發者 | ~8MB | 需自備 Python 3.10+。執行 `pip install -r requirements.txt`。 |

---

## 💡 使用小撇步

- **Ctrl + V 貼圖**：在編輯器內直接貼上剪貼簿圖片，系統自動儲存。
- **拖曳排序**：在 Grid View 切換至「自訂排序」模式，即可拖曳卡片整理順序。
- **資料庫維護**：內建 `VACUUM` 整理功能，保持 SQLite 高效運作。

---

## 🛠️ 技術棧

- **Backend**: Flask, SQLite (Full Text Search 5)
- **Frontend**: Vanilla JS, Tailwind CSS (No Build Step)
- **UI Design**: Waterfall Grid Layout, Inter Tight Typography, 3D Tilt Effects

---

**Made with  for personal knowledge management**
