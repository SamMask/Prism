# Gemini3 綜合評估報告 - 深度 (Deep Technical Audit)

**版本**: v1.0
**日期**: 2025-12-11
**審核對象**: Local Insight v1.0.0 (Architecture to Code)
**審核員**: Antigravity (Google DeepMind Agentic Coding Assistant)

---

## 1. 架構邏輯 (Architecture Logic)

整體採用 **Flask Blueprint + SQLite + Vue.js (ES Modules)** 的輕量化架構，符合「單機執行、零依賴」的專案目標。

- **優點**:

  - **Blueprint 拆分**: `routes/` 目錄下的模組化 (notes, tags, upload, etc.) 邊界清晰，避免了單一 `app.py` 過於肥大的問題。
  - **統一資料庫層**: `db.py` 提供了各模組共用的 `get_db()` 與 `transaction()` Context Manager，確保了連線管理的一致性與 WAL 模式的正確啟用。
  - **前端無編譯**: 使用原生 ES Modules (`.js` files) 直接運行，去除了 Node.js/Webpack 建置流程，極大降低了部署與修改門檻。

- **潛在衝突**:
  - **雙重事實 (Source of Truth) 分裂**: `Notes` 表同時保留了 `type` (TEXT) 與 `category_id` (INTEGER)。雖然 `crud.py` 中有 `get_category_id_by_name` 試圖同步，但這違反了資料庫正規化原則。若直接從 SQL 修改 `type`，`category_id` 及其關聯的 Icon/排序將不會自動更新，反之亦然。

## 2. 功能正確性 (Functional Correctness)

- **CRUD 完整性**: `routes/notes/crud.py` 完整實作了增刪改查，並正確處理了關聯表 (`Note_Tags`, `Source_Urls`) 的寫入。
- **搜尋邏輯**: 結合 SQL `LIKE` 與 FTS5 全文檢索，且在 `get_notes` 中正確處理了 `params` 參數化查詢，避免了簡單的注入風險。
- **標籤過濾**: 正確實作了 `AND` (預設) 與 `OR` 邏輯，利用 `EXISTS` 子查詢效能較佳。
- **分頁計算**: `offset` 與 `total_pages` 計算邏輯正確。

- **待改進點**:
  - **圖片清理的正則表達式**: `_cleanup_note_images` 使用 `re.findall` 抓取內容中的圖片路徑。若 Markdown 語法包含特殊屬性或變體 (e.g., `<img src="...">`)，可能無法匹配導致孤兒檔案殘留。

## 3. 變數與函式 (Variables & Functions)

- **命名一致性**: Python 端採用 `snake_case`，JS 端採用 `camelCase`，整體風格統一。
- **函式粒度**:
  - `crud.py/get_notes`: 函式過長 (約 150 行)，混合了「參數解析」、「SQL 組裝」、「資料庫查詢」、「資料轉換」四種職責。建議可將 SQL 組裝邏輯抽取為 `_build_search_query` 輔助函式。
- **未使用代碼**:
  - `routes/helpers.py` (推測): 雖然未完整讀取，但在 `crud.py` 中僅使用了 `parse_tags_json`, `parse_urls_json`。需確認是否有冗餘的 helper 函式。

## 4. 漏洞與脆弱點 (Vulnerabilities & Weaknesses)

- **Path Traversal (已修復)**: `upload.py` 中的 `delete_image` 現已包含 `os.path.abspath` 的雙重檢查，防護到位。
- **Magic Number 檢測**: 上傳功能使用了 `python-magic` 檢測真實 MIME type，防止了偽裝副檔名的惡意腳本上傳。
- **XSS 防護**: 雖然是用 Vue.js 渲染，但 Markdown 渲染後的 HTML 需依賴 `DOMPurify`。需確認前端 `v-html` 處是否原本就嚴格執行了 sanitize (根據 `TODO.md` 應已修復，但代碼層面需持續關注)。
- **CSRF**: 作為純本地應用，目前未見 CSRF Token 機制。雖然是 Localhost 環境風險較低，但若使用者訪問惡意網站且 Local Insight 正在運行，仍有被跨站構建請求的理論風險。

## 5. 效能與可維護性 (Performance & Maintainability)

- **資料庫效能**:
  - **WAL 模式**: `db.py` 中正確啟用 `PRAGMA journal_mode = WAL`，大幅提升併發讀寫效能。
  - **JSON Group Array**: `get_notes` 使用 SQLite 原生 JSON 函數聚合 Tags 與 URLs，避免了 Python 端 N+1 查詢問題，這是極佳的優化。
- **可維護性問題**:
  - **Schema 定義位置**: `app.py` 中的 `init_db` 函式包含了極長的 `CREATE TABLE` 字串。這導致每次修改 Schema 需同時維護 `migrations/` 與 `init_db` 的初始 SQL。這容易導致新安裝環境與遷移後的環境 Schema 不一致。

## 6. 模組之間的耦合 (Coupling)

- **Routes 與 Logic 耦合**: 目前業務邏輯 (Business Logic) 直接寫在 `routes/` 函式中。例如 `update_note` 中包含了「比對內容差異寫入 History」的邏輯。若未來要開發 CLI 工具或批次處理腳本，這些邏輯難以復用。
  - **建議**: 將 CRUD 核心邏輯下沉至 `services/note_service.py`。

## 7. 缺少的功能 (Missing Features)

- **資料庫備份回滾**: 雖然有 `export_bp`，但缺乏自動化的定期備份機制。
- **日誌輪替清理**: `app.log` 雖然有 `RotatingFileHandler`，但應用層缺乏查看或清理日誌的 UI。

## 8. 改進建議 (Actionable Recommendations)

### 8.1 架構重構：Schema 定義外部化

- **問題**: `app.py/init_db` 硬編碼 SQL 難以維護且易與 Migration 脫節。
- **如何改**: 建立 `schema.sql` 檔案，`init_db` 改為讀取該檔案執行。
- **預期效果**: 單一真理來源 (Single Source of Truth)，新環境初始化更可靠。

### 8.2 資料模型：移除 `type` 欄位

- **問題**: `Notes.type` 與 `Notes.category_id` 資料冗餘。
- **如何改**:
  1.  確認所有程式碼 (前端篩選、後端查詢) 改用 `category_id` JOIN `Categories` 表。
  2.  將 `type` 欄位標記為 Deprecated，最終移除。
- **預期效果**: 消除資料不一致風險，分類改名時無需全表更新 `Notes`。

### 8.3 程式碼品質：SQL Builder 抽象化

- **問題**: `crud.py/get_notes` 充滿了字串拼接 (`if keyword: ... where_clauses.append(...)`)。
- **如何改**: 引進輕量級的 Query Builder (如 `pypika` 或自行封裝簡單的 `QueryBuilder` class)。
- **預期效果**: 查詢邏輯更易讀、易測，減少拼接錯誤。

### 8.4 安全性：CSRF 保護

- **問題**: 缺少 CSRF Token。
- **如何改**: 引入 `Flask-WTF` 的 CSRFProtect，或在 API 請求頭強制要求自訂 Header (e.g., `X-Requested-With: LocalInsight`)。
- **預期效果**: 防止瀏覽器端的跨站請求偽造攻擊。

### 8.5 圖片清理：更強健的解析

- **問題**: Regex 清理圖片可能漏網。
- **如何改**: 使用 `BeautifulSoup` 或 `markdown-it-py` 解析 Markdown AST 來提取圖片連結。
- **預期效果**: 精確識別所有圖片引用，確保「孤兒圖片清理」100% 準確。

---

**總結**:
Local Insight 的程式碼品質在「單人開發、輕量級」的前提下表現優異。使用了許多進階 SQLite 技巧 (JSON, FTS5, WAL) 確保效能。主要的改進空間在於「資料庫正規化 (Type vs Category)」與「業務邏輯層的抽離」。
