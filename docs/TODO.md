# Prism - 開發待辦清單 (TODO)

**版本**: v1.3.0
**最後更新**: 2025-12-13
**修訂**: Phase 17 - 安全強化 (CSRF 防護與本機綁定)

---

## 📊 專案進度總覽

| Phase | 名稱                              | 狀態      | 完成日期   |
| ----- | --------------------------------- | --------- | ---------- |
| 1     | 環境建置與資料庫初始化            | ✅ 已完成 | 2025-11-27 |
| 2     | 後端 API 開發 + 安全性修復        | ✅ 已完成 | 2025-11-28 |
| 3     | 前端介面與瀑布流實作              | ✅ 已完成 | 2025-12-05 |
| 4     | 編輯器與進階功能                  | ✅ 已完成 | 2025-12-06 |
| 5     | 測試與優化                        | ✅ 已完成 | 2025-12-06 |
| 6     | 審計修復與架構補強                | ✅ 已完成 | 2025-12-07 |
| 7     | 進階功能與商務化 (Prompt Builder) | ✅ 已完成 | 2025-12-07 |
| 8     | UX 優化與維護功能                 | ✅ 已完成 | 2025-12-08 |
| 9     | 視覺優化與儲存效能                | ✅ 已完成 | 2025-12-09 |
| 10    | 架構重構 (Linus 式瘦身)           | ✅ 已完成 | 2025-12-09 |
| 11    | 文件與部署                        | ✅ 已完成 | 2025-12-10 |
| 12    | 無障礙與技術債清理                | ✅ 已完成 | 2025-12-09 |
| 13    | 功能擴展                          | 🚧 規劃中 | -          |

---

## ✅ 已完成功能摘要 (Phase 1-8)

### Phase 1-2: 基礎架構 (v0.1)

- Flask + SQLite + Vue.js 3 架構建立
- Notes/Tags/Source_Urls CRUD API
- 分頁機制、Magic Numbers 檢查、離線優先

### Phase 3-4: 前端 UI 與編輯器 (v0.1-0.4)

- 瀑布流卡片介面 (Grid/List 切換)
- Modal 編輯器 (Markdown + 預覽)
- Tags 管理 (重命名/刪除/合併)
- 複選模式 + 批量操作 (Ctrl+A)
- 圖片上傳 + 剪貼簿貼上
- 快速提示詞模式

### Phase 5-6: 安全性與架構優化 (v0.5)

- XSS 防護 (DOMPurify)
- SQL Injection 防護 (參數化查詢)
- 後端 API 分頁 + 伺服器端過濾
- 前端 JS 模組化拆分

### Phase 7: Prompt Builder (v0.6)

- 獨立組裝器頁面 `/prompt-builder`
- 結構化參數配置 (JSON 驅動)
- 靈感引導精靈 (4 維度隨機)
- 模板系統、權重滑桿
- 技術要求區塊 (長寬比/解析度)

### Phase 8: UX 優化 (v0.7-0.8.8)

- 分類管理 CRUD + 同步
- 歷史版本還原 (筆記時光機)
- 孤兒圖片清理
- 編輯器雙欄模式 (圖文並列)
- 封面圖片位置選項
- 無限滾動 + 自動載入設定
- 提示詞擴充包 (160+ 選項)
- 混沌係數隨機生成器
- 國際化 i18n (zh-TW / en)

---

## ✅ Phase 9: 視覺優化與儲存效能 (已完成)

### 9.1 UX 視覺優化 (基於 UX 報告 2025-12-07)

#### 🟢 P0 - Quick Wins (立竿見影)

- [x] **9.1.1** Web Fonts 導入 ✅ (2025-12-08)

  - 導入 Inter Tight 字體 (本地 woff2 檔案)
  - 建立 `static/css/styles.css` 定義 @font-face
  - 配置 Tailwind fontFamily 使用 Inter Tight
  - 支援 400/500/600/700/800 五種字重

- [x] **9.1.2** 微互動增強 ✅ (2025-12-08)
  - 所有按鈕添加 `active:scale(0.95)` 動畫
  - 卡片 hover 添加 lift 效果
  - 輸入框 focus 添加平滑過渡
  - 定義 CSS 變數：`--transition-fast/normal/slow`

#### 🟡 P1 - 體驗優化

- [x] **9.1.3** 品牌色彩系統定義 ✅ (2025-12-08)

  - CSS Root 定義 6 組主題色 (default/cyberpunk/eye-care/elegant/ocean/sunset)
  - `data-theme` 屬性切換主題
  - 設定存入 localStorage (`colorTheme`)
  - 設定視窗新增主題色選擇器 UI
  - 統一首頁與 Prompt Builder 色系

- [x] **9.1.4** 移動端優化 ✅ (2025-12-08)
  - 新增漢堡菜單按鈕 (md 以下顯示)
  - 側邊欄滑入動畫 + 背景遮罩
  - 響應式卡片間距 (gap-4 / md:gap-6)
- [x] **9.1.4** 移動端優化 ✅ (2025-12-08)

  - 新增漢堡菜單按鈕 (md 以下顯示)
  - 側邊欄滑入動畫 + 背景遮罩
  - 響應式卡片間距 (gap-4 / md:gap-6)
  - 移動端 CSS 優化 (觸控目標、內距)

- [x] **9.1.5** 優化複選操作 UI (Sub-header) ✅ _(2025-12-09)_

  - ✅ 實作獨立的第二排工具列 (`_selection-bar.html`)
  - ✅ 將複選狀態與操作按鈕移出 Header，解決擁擠問題
  - ✅ 實作滑入/滑出動畫 (Transition)
  - ✅ 修復 Dropdown 閃退與標籤計數同步問題

- [x] **9.1.6** 導覽列與預設分類優化 ✅ _(2025-12-09)_
  - ✅ 導覽列按鈕重構：「新增卡片」(藍) 與「快速新增」(紫/閃電) 樣式區分
  - ✅ 預設分類設定拆分邏輯：
    - 下拉選單控制「快速新增」預設值
    - 分類管理「星號」控制「新增卡片」預設值
  - ✅ UI 優化：系統預設分類改為鎖頭圖示，使用者預設標籤跟隨星號移動
  - ✅ 修正複選模式多語系失效問題

---

### 9.8 完整主題色彩系統 (v0.9.0)

**問題背景**: 目前主題色彩只定義了 CSS 變數，但模板中仍大量使用 Tailwind 硬編碼顏色  
（如 `bg-gray-900`, `bg-blue-600`），導致切換主題時只有部分顏色變化。

#### 🔴 P0 - CSS 設計系統

- [x] **9.8.1** 擴展 CSS 變數定義 ✅ _(2024-12-09)_

  - ✅ 新增背景色系統：`--color-bg-base`, `--color-bg-surface`, `--color-bg-elevated`, `--color-bg-hover`
  - ✅ 新增邊框色系統：`--color-border-default`, `--color-border-subtle`, `--color-border-hover`
  - ✅ 為 6 套主題定義完整色盤 (含主題特有的背景色調)

- [x] **9.8.2** 新增主題感知 Utility Classes ✅ _(2024-12-09)_
  - ✅ 背景類別：`.bg-theme-base`, `.bg-theme-surface`, `.bg-theme-elevated`, `.bg-theme-hover`
  - ✅ 邊框類別：`.border-theme-default`, `.border-theme-subtle`, `.border-theme-hover`
  - ✅ 文字類別：`.text-theme-primary`, `.text-theme-secondary`, `.text-theme-muted`
  - ✅ 漸層類別：`.brand-gradient`, `.brand-gradient-text`
  - ✅ 狀態類別：`.bg-theme-success/warning/danger`

#### 🟡 P1 - 模板替換

- [x] **9.8.3** 主頁模板替換 (`index.html` 及 components) ✅ _(2024-12-09)_

  - ✅ `index.html` - 滾動條、背景色使用 CSS 變數
  - ✅ `_header.html` - 導航欄、按鈕、搜尋框
  - ✅ `_sidebar.html` - 側邊欄、標籤過濾
  - ✅ `_note-grid.html` - 卡片、狀態提示、漸層
  - ✅ `_editor-modal.html` - 編輯器模態框
  - ✅ `_settings-modal.html` - 設定模態框
  - ✅ `_context-menus.html` - 右鍵選單

- [x] **9.8.4** Prompt Builder 模板替換 ✅ _(2024-12-09)_
  - ✅ `_header.html` - 導航欄、語言切換
  - ✅ `_left-panel.html` - 配置表單、所有選項區塊
  - ✅ `_right-panel.html` - 輸出預覽、按鈕樣式
  - ✅ `_modals.html` - 所有彈出視窗

#### 🟢 P2 - 驗證與文件

- [x] **9.8.5** 驗證所有主題 ✅ _(2024-12-09)_

  - ✅ 已驗證 6 套主題切換效果 (default, cyberpunk, eye-care, elegant, ocean, sunset)
  - ✅ 所有 UI 元素正確響應主題變化
  - ✅ 截圖記錄各主題效果 (6 張截圖已保存)

- [x] **9.8.6** 更新文件 ✅ _(2024-12-09)_
  - ✅ SCHEMA.md 新增 CSS 設計系統規範
  - ✅ 更新 Local Insight.md 功能說明 (v0.9.0)
  - ✅ 版本號統一更新為 v0.9.0

### 9.2 圖片儲存優化

- [x] **9.2.1** 新增設定：貼上圖片時只保存縮圖 ✅ (2025-12-08)

  - 後端 `/api/upload` 支援 `thumbnail_only` 參數
  - 前端 `imageSaveMode` 設定保存到 localStorage
  - 設定視窗新增選項：原圖+縮圖 / 僅縮圖
  - `useEditor` 和 `api.js` 整合完成

- [x] **9.2.2** 一鍵刪除所有原圖功能 ✅ (2025-12-08)

  - 後端 API: `GET/DELETE /api/cleanup/originals`
  - 掃描 `static/uploads/`，找出有縮圖備份的原圖
  - 刪除前自動更新筆記中的圖片路徑為縮圖
  - 設定視窗新增掃描與刪除按鈕
  - 顯示釋放空間大小

- [x] **9.2.3** 圖片路徑自動修正與縮圖降級 ✅ (2025-12-08)

  - 後端 API: `GET/POST /api/cleanup/broken-images`
  - 掃描筆記中原圖不存在但有縮圖可用的路徑
  - 一鍵修正：自動將失效路徑替換為縮圖路徑
  - 設定視窗新增掃描與修正按鈕

---

### 9.3 編輯器進階功能

#### 🟡 P1 - 拖放排序

- [x] **9.3.2** 拖放排序功能 ✅ _(2024-12-09)_

  - ✅ 新增 `sort_order` 欄位到 Notes 表 (自動遷移)
  - ✅ 後端 API: `PUT /api/notes/reorder` (Mock 測試驗證通過)
  - ✅ `get_notes` API 支援 `sort` 參數 (updated/custom/created)
  - ✅ 前端 `useNotes.js` 新增拖放狀態與函數
  - ✅ Header 排序模式切換按鈕 (時鐘/箭頭/日曆圖示)
  - ✅ 卡片支援拖曳 (僅在自訂排序模式下啟用)
  - ✅ 修復縮圖路徑重複疊加 BUG (`utils.js`)

- [x] **9.3.3** 快速新增編輯器簡化 ✅ _(2025-12-09)_
  - 重構為單欄垂直佈局，移除 Tabs
  - 內容優先設計，支援自動聚焦與 Ctrl+V 貼圖
  - 標題可留空（自動生成日期標題）
  - 標籤輸入優化與智能推薦 (Frequency-based)

### 9.5 前端架構重構 (index.html 模組化)

#### 🟢 P0 - 高優先

- [x] **9.5.1** index.html 拆分為 Jinja2 組件 ✅ _(2024-12-08)_

  - ✅ 建立 `templates/components/` 目錄
  - ✅ 拆分 7 個組件檔案：
    - ✅ `_header.html` (400 行) - Header 含搜尋、按鈕、選擇工具列
    - ✅ `_sidebar.html` (170 行) - 側邊欄含類型/標籤篩選
    - ✅ `_note-grid.html` (521 行) - 筆記卡片網格/列表
    - ✅ `_editor-modal.html` (1,294 行) - 編輯器彈窗
    - ✅ `_settings-modal.html` (852 行) - 設定彈窗
    - ✅ `_context-menus.html` (102 行) - 右鍵選單
    - ✅ `_scripts.html` (113 行) - ES Modules 載入
  - ✅ index.html 從 3,544 行減至 115 行
  - 📄 備用：`tools/extract_components.py` 提取腳本

- [x] **9.5.2** 組件整合驗證 ✅ _(2024-12-08)_
  - ✅ 所有路由正常運作
  - ✅ Vue.js 綁定正常 (標籤右鍵選單、重命名/合併彈窗)
  - ✅ 主題切換/移動端功能正常

### 9.4 資料庫效能優化 (SQLite Tuning)

> 📄 參考: `9.4 資料庫效能規劃-建議.md`

#### 🟡 P1 - 中優先

- [x] **9.4.1** 啟用 WAL 模式 ⚡ ✅ _(2024-12-08)_

  - ✅ 在 `app.py` `get_db()` 加入 `PRAGMA journal_mode=WAL`
  - 支援高併發讀寫，效能大幅提升

- [x] **9.4.2** 確認索引覆蓋率 ✅ _(2024-12-08)_

  - ✅ 所有建議索引已在 `init_db()` 實作：
    - `idx_notes_type` - 分類過濾
    - `idx_notes_updated_at DESC` - 排序分頁
    - `idx_source_urls_note_id` - 來源網址查詢
    - `idx_tags_name` - 標籤搜尋
    - `idx_note_history_note_id` - 歷史記錄
  - ✅ FTS5 全文檢索已啟用 (含 INSERT/UPDATE/DELETE Triggers)

- [x] **9.4.3** 封存機制 (Archiving) ✅ _(2024-12-08)_

  - ✅ 新增 `is_archived` 欄位 + 自動遷移 (`app.py`)
  - ✅ `get_notes()` 預設 `WHERE is_archived = 0`
  - ✅ 支援 `?include_archived=true` 參數查看封存筆記
  - ✅ 新增 API: `POST /api/notes/<id>/archive` 封存/取消封存

- [x] **9.4.4** 資料庫緊縮 (VACUUM) 功能 ✅ _(2024-12-08)_
  - ✅ 後端 API: `POST /api/system/vacuum` (`routes/system.py`)
  - ✅ 設定視窗新增「整理資料庫」按鈕 (`_settings-modal.html`)
  - ✅ 確認對話框防止誤觸
  - ✅ 顯示操作前後空間變化 (MB)

> **決策說明**:
>
> - ❌ 方案 A (時間分表): 不適合筆記應用
> - ❌ 方案 B (.md 檔案): 增加 I/O 複雜度，除非需要 Obsidian 同步
> - ✅ 方案 C (附件分離): 現行架構，維持不變
> - ✅ WAL Mode + FTS5: 效能優化首選

### 9.5 MVP 審查修復 ✅ _(2024-12-09)_

- [x] **9.5.1** 路徑穿越漏洞修復 (`upload.py`)
- [x] **9.5.2** 空異常捕捉修復 (`notes.py`, `system.py`)
- [x] **9.5.3** FTS5 搜尋輸入清理 (`notes.py`)
- [x] **9.5.4** 交易隔離修復 (`tags.py`)
- [x] **9.5.5** 輸入驗證強化 (批量操作限 500 筆, 圖片匯出限 100 張)

### 9.6 架構重構 ✅ _(2024-12-09)_

- [x] **9.6.1** 統一資料庫層 (`db.py`)

  - ✅ `get_db()` - 共用連線
  - ✅ `transaction()` - Context Manager
  - ✅ `close_db()` - 連線關閉
  - ✅ 所有 routes 模組已更新

- [x] **9.6.2** i18n Provide/Inject 模式 (`useI18n.js`)

  - ✅ `provideI18n()` - 根組件使用
  - ✅ `injectT()` - composables 自動注入
  - ✅ 不再需要逐層傳遞 `t()` 函數

- [x] **9.6.3** Jinja2 分隔符 (維持現狀)

  - 現狀: 使用 `[{ }]` 避免與 Vue `{{ }}` 衝突
  - 維持至 Phase 3 前後端分離

- [x] **9.6.4** 測試腳本標準化整理 ✅ _(2025-12-09)_
  - ✅ 建立 `tests/` 目錄，優化根目錄結構
  - ✅ 將根目錄散落的 `test_*.py` 腳本全數移入
  - ✅ 建立 `tests/README.md` 說明腳本用途與執行方式

---

### 9.7 Prompt Builder 改進 ✅ _(2025-12-09)_

#### 🔴 P1 - 新功能 (優先)

- [x] **9.7.1** 自動造句 (`narrativeOutput`) ✅ _(2024-12-09)_

  - ✅ 新增 computed 屬性，將參數組成通順句子
  - ✅ Style 前綴 + Lighting + Camera + Quality

- [x] **9.7.2** LLM 潤飾指令 (`copyMetaPrompt`) ✅ _(2024-12-09)_
  - ✅ 新增「複製 Gemini/ChatGPT 優化指令」按鈕
  - ✅ 支援針織、黏土、微縮模型等特殊風格 (Material-Specific)

#### 🟡 P2 - 模板拆分 (Phase 2)

- [x] **9.7.3** 拆分 `prompt-builder.html` ✅ _(2024-12-09)_
  - ✅ `templates/prompt-builder/_header.html` - Header 區塊
  - ✅ `templates/prompt-builder/_left-panel.html` - 左側配置面板
  - ✅ `templates/prompt-builder/_right-panel.html` - 右側輸出預覽
  - ✅ `templates/prompt-builder/_modals.html` - 所有 Modal 對話框
  - ✅ 主模板使用 Jinja2 `{% include %}` 引入組件

#### 🟢 P3 - JS 模組化 (Phase 3)

- [x] **9.7.4** 拆分 inline script 為 ES Module ✅ _(2024-12-09)_
  - ✅ `static/js/composables/usePromptBuilder.js` - 完整 composable (~1000 行)
  - ✅ 主模板從 ~1100 行內聯 JS 減少到 ~20 行 ES Module import
  - ✅ 包含 i18n、表單狀態、輸出生成、Wizard、Modal 等所有功能

---

## ✅ Phase 10: 架構重構 (Linus 式瘦身) - 已完成 2025-12-09

### 10.1 版本化遷移系統 (Phase A) ✅

- [x] **10.1.1** 建立 `migrations/__init__.py` 遷移執行器
  - 聲明式遷移定義 (7 個版本)
  - 自動偵測現有欄位
  - 冪等執行 + 交易回滾
- [x] **10.1.2** 移除 `app.py` 的 5 個 if 分支遷移邏輯
- [x] **10.1.3** 新增 `Schema_Meta` 表追蹤版本
- [x] **10.1.4** 新增 `Notes.category_id` FK 欄位
- [x] **10.1.5** 填充所有筆記的 `category_id` 值

### 10.2 查詢重構 (Phase B) ✅

- [x] **10.2.1** 建立 `routes/helpers.py` JSON 解析模組
- [x] **10.2.2** `get_notes()` 改用 `json_group_array()`
- [x] **10.2.3** `get_note()` 改用 `json_group_array()`
- [x] **10.2.4** 消除 `GROUP_CONCAT(id:name, '||')` 特殊字元風險

### 10.3 模組拆分 (Phase C) ✅

- [x] **10.3.1** 將 `routes/notes.py` (1,028 行) 拆分為 4 個子模組:
  - `routes/notes/__init__.py` - Blueprint 註冊
  - `routes/notes/crud.py` (~420 行) - CRUD 操作
  - `routes/notes/actions.py` (~230 行) - pin/archive/duplicate/reorder
  - `routes/notes/history.py` (~110 行) - 版本歷史
  - `routes/notes/batch.py` (~220 行) - 批量操作
- [x] **10.3.2** 更新 `routes/__init__.py` 導入結構
- [x] **10.3.3** 驗證所有 14 個 API 端點正常運作

---

## ✅ Phase 11: 文件與部署 - 已完成 2025-12-10

- [x] **11.1** 撰寫 README.md (專案介紹/安裝/使用) ✅
- [x] **11.2** 撰寫開發者文件 (API/資料庫) ✅ → `docs/API_REFERENCE.md`
- [x] **11.3** 建立初始化腳本 (一鍵安裝) ✅ → `install.bat` / `install.sh`
- [x] **11.4** 批量匯出 (Markdown + Assets ZIP) ✅
  - 複選模式下打包匯出為 ZIP (含 .md + 圖片)

---

## ✅ Phase 12: 無障礙與技術債清理 (源自審核報告) - 已完成 2025-12-09

> 📄 來源: `Gemini3Pro-High-綜合報告-1209.md`, `Performance_Audit_1209.md`
> 篩選原則: Linus 風格 - 只修真正的 bug，拒絕純審美變更

### 12.1 🔴 P0 - 必修 Bug ✅

- [x] **12.1.1** 移除 CSS `!important` 暴力覆蓋

  - 位置: `static/css/styles.css` Line ~622
  - 問題: `.p-6 { padding: 1rem !important; }` 破壞 Tailwind 響應式設計
  - 修復: 已移除，改用 HTML class `p-4 md:p-6 lg:p-8`

- [x] **12.1.2** 修復隱形 Focus State (無障礙)

  - 問題: `focus:ring-0` 移除可見焦點環，違反 WCAG 2.1
  - 修復: 已加入 `focus:bg-white/5 focus:ring-1 focus:ring-purple-500/30`
  - 影響範圍: Quick Add Modal 的 Title/URL/Tag 輸入框

- [x] **12.1.3** ESC 關閉所有 Modal (鍵盤可及性)

  - 問題: Modal 缺少 `@keydown.esc` 監聽
  - 修復: 已在 Quick Add, Editor, Settings Modal 加上 `@keydown.esc.prevent`

- [x] **12.1.4** 修復 Prompt Builder 黑屏崩潰

  - 問題: Vue Template 中字串表達式換行導致編譯錯誤
  - 修復: 修正 `_right-panel.html` 中的 `t()` 函數調用

- [x] **12.1.5** 歷史紀錄資料一致性
  - 問題: 刪除筆記未連帶刪除歷史紀錄 (Orphan Data)
  - 修復: 後端實作 Cascade Delete，並新增「清空單一筆記歷史」功能 (Frontend + Backend)

### 12.2 🟡 P1 - 改進 ✅

- [x] **12.2.1** Hover 按鈕補 focus 可見性

  - 問題: `opacity-0 group-hover:opacity-100` 缺少 `focus:opacity-100`
  - 修復: 已加入 `focus:opacity-100`
  - 影響範圍: Prompt Builder 自定義模板刪除按鈕

- [x] **12.2.2** Toggle Switch 焦點指示器
  - 問題: `sr-only` checkbox 被 focus 時無視覺回饋
  - 修復: 已加入 `peer-focus:ring-2 peer-focus:ring-purple-500`
  - 影響範圍: Prompt Builder 權重模式開關

### 12.3 🟢 P2 - 長期規劃

- [x] **12.3.1** Prompt Builder 快捷鍵

  - 功能: `Ctrl+Enter` 複製結果, `Ctrl+S` 儲存至筆記庫
  - 狀態: 已實作 (v1.0)

- [x] **12.3.2** DOM 虛擬化 (Virtualization) - 延後至 v1.X
  - 目前資料量不足，無需行動，改列入未來規劃

---

## ✅ Phase 13: 功能擴展 (v1.1) - 已完成

- [x] **13.1** 匯入功能 ✅

  - 設定頁新增匯入 `.md` 按鈕
  - 支援單檔或批量匯入（不含子資料夾）
  - YAML front matter 解析 (type, tags)
  - 自動下載外部圖片並儲存至本地

- [x] **13.2** 首次啟動引導 ✅

  - 首次執行詢問：自動開啟瀏覽器 / 手動開啟
  - 偏好儲存至 `.auto_open_yes` / `.auto_open_no`
  - 設定頁「啟動設定」可切換偏好

- [x] **13.3** 資料庫維護增強 ✅
  - 整理資料庫（VACUUM）+ 結果顯示
  - 清空歷史版本（新功能）

---

## ✅ Phase 14: 審計修復 (v1.1.0 - 2025-12-11)

### 14.1 🔴 P0 - 技術阻斷

- [x] **14.1.1** 分類資料一致性修復 (Category Split Brain) ✅ _(2025-12-11)_

  - 新增 `get_category_id_by_name()` Helper，同步寫入 `category_id`

- [x] **14.1.2** Schema 雙重事實修復 (Single Source of Truth) ✅ _(2025-12-12)_
  - `get_notes`/`get_note` 改用 `LEFT JOIN Categories` 取得分類名稱

---

### 14.2 🔴 P0 - UX 阻斷

- [x] **14.2.1** Prompt Builder 錯誤死胡同修復 ✅ _(2025-12-11)_
- [x] **14.2.2** 搜尋空狀態誤導修復 ✅ _(2025-12-11)_
- [x] **14.2.3** 手機版側邊欄自動收合 ✅ _(2025-12-11)_

---

### 14.3 🟢 新功能 (2025-12-12)

- [x] **14.3.1** 專案更名 (Local Insight -> Prism) ✅

  - README, app.py, 所有模板標題已更新

- [x] **14.3.2** Demo DB 生成腳本 ✅

  - `tools/create_demo_db.py` - 生成 51 則範例筆記

- [x] **14.3.3** README 文檔優化 ✅

  - 新增「馬上體驗 10 秒」快速開始
  - 新增「Ctrl+V 貼圖」小撇步

- [x] **14.3.4** 編輯器 Ctrl+V 提示 (i18n) ✅

  - 在 Markdown 編輯標題右方新增提示文字

- [x] **14.3.5** 文件版本對齊 ✅
  - TODO.md, SCHEMA.md, Prism.md 統一為 v1.1.0

---

## 📅 開發里程碑

| 日期       | 版本   | 里程碑                         |
| ---------- | ------ | ------------------------------ |
| 2025-11-27 | v0.1   | Phase 1 環境建置完成           |
| 2025-11-28 | v0.2   | Phase 2 API + 安全性修復       |
| 2025-12-05 | v0.3   | Phase 3-4 前端 UI + 編輯器     |
| 2025-12-06 | v0.5   | Phase 5-7 進階功能 + XSS 修復  |
| 2025-12-07 | v0.6   | Prompt Builder 完整功能        |
| 2025-12-08 | v0.8.8 | Phase 8 UX 優化 + i18n         |
| 2025-12-09 | v0.9.1 | Phase 9 視覺優化 + 儲存效能    |
| 2025-12-09 | v1.0.0 | Phase 10-12 架構重構 + 無障礙  |
| 2025-12-11 | v1.1.0 | Phase 13 匯入功能 + DB 維護    |
| 2025-12-12 | v1.1.0 | Phase 14 審計修復 + 更名 Prism |

---

## ✅ Phase 17: 安全強化 (v1.3 - 2025-12-13)

> 📄 來源: `MVP_Audit_Report-1213.md`

### 17.1 🔴 P0 - 阻斷性問題

- [x] **17.1.1** 未經驗證遠端存取風險修復 ✅ _(2025-12-13)_

  - 預設綁定 `127.0.0.1` (僅本機訪問)
  - 透過 `HOST` 環境變數可覆蓋 (警告提示)
  - 位置: `app.py` 最後數行

- [x] **17.1.2** CSRF 防護機制 ✅ _(2025-12-13)_
  - 新增 `before_request` 中介軟體
  - 驗證 `Origin`/`Referer` 標頭是否為同源
  - 允許無標頭的本機請求 (curl/Postman)
  - 位置: `app.py` `create_app()` 內

---

## 🔮 未來規劃 (Future Roadmap)

> 以下項目尚未實作，列入長期規劃。

### Phase 15: 系統可靠性與維運 (v1.2)

#### ✅ 高風險技術債 (P1) - 已完成

- [x] **15.1** 圖片刪除引用計數檢查 (🟡-1) ✅ _(2025-12-12)_

  - `_cleanup_note_images()` 刪除前檢查其他筆記是否引用

- [x] **15.2** WAL Checkpoint 機制 (🟡-2) ✅ _(2025-12-12)_

  - 整合到 VACUUM 函數 (API 保留: `POST /api/system/wal-checkpoint`)
  - UI 按鈕已移除，「整理資料庫」一併執行 WAL + FTS + VACUUM

- [x] **15.3** 資料一致性檢查 (🟡-3) ✅ _(2025-12-12)_
  - 啟動時自動修復 `auto_fix_consistency()` in `app.py`
  - API 保留: `GET /api/system/check-consistency`

#### ✅ 設定頁簡化 _(2025-12-12)_

- [x] 移除「匯出資料庫」按鈕 (README 有說明 knowledge.db 位置)
- [x] 移除「合併 WAL 日誌」按鈕 (整合到 VACUUM)
- [x] 新增 cardOpenMode 英文翻譯

#### 備份與日誌

- [ ] **15.4** 資料庫自動備份與回滾

  - 定期備份機制 (排程任務)
  - 備份檔案管理 UI (下載/刪除)
  - 一鍵回滾 (Restore) 功能

- [ ] **15.5** 應用層日誌管理
  - 設定頁面整合 `app.log` 檢視器
  - 日誌輪替 (Rotation) 設定 UI

### 功能擴充 (Enhancements)

- [ ] DOM 虛擬化 (Virtual Scrolling)

  - 觸發條件: 筆記數 > 500
  - 方案: Virtual Scroller 或傳統分頁

- [ ] Quick Add vs New Note 視覺區分

  - 調整按鈕視覺權重或文案

- [ ] 長期考慮，不新增第三方依賴

### Phase 16: UX 細緻化與 UX 審計修復 (v1.3) ✅ _(2025-12-12)_

#### ✅ 阻斷性問題 (Critical) - 已完成

- [x] **16.1** 全域視覺對比度優化 (C-01) ✅

  - 修正 `--color-text-muted` 顏色 (#6b7280 -> #94a3b8)
  - 改善 WCAG AA 對比度合規性

- [x] **16.2** 標籤輸入邏輯優化 (C-02/S-01) ✅

  - 實作失焦自動加入 (Auto-add on blur)
  - 更新 Placeholder 提示文字

- [x] **16.3** Prompt Builder 權重模式隱藏 (C-03/S-02) ✅
  - 暫時隱藏 Weights Toggle 與相關 UI
  - 避免出現 `(keyword:1.2)` 格式困擾新手

#### ✅ 體驗優化 (Friction) - 已完成

- [x] **16.4** 拖曳排序提示 (F-02) ✅

  - Grid View 卡片 tooltip 顯示「切換至自訂排序以拖曳」

- [x] **16.5** Prompt Builder 工具提示 (F-03) ✅ (已有 title 屬性)

### 長期優化 (v2.0+)

- [ ] 廢棄 `Notes.type` 欄位，完全依賴 `category_id`
- [ ] 批量操作查詢優化 (N+1 → 批量 INSERT)

---

## 📚 相關文件

- **SCHEMA.md** - 資料庫結構與 API 規格
- **Prism.md** - 技術規格書

---

**END OF TODO.md (v1.1.0 - 2025-12-12)**
