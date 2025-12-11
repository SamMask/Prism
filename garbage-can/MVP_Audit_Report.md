# Local Insight MVP 技術審查報告

**審查日期**: 2025-12-06
**審查對象**: Local Insight v1.3 (Source Code)
**審查者**: 全端架構審查員 (Antigravity)

---

## 🚦 審查總結 (Executive Summary)

本次審查針對 MVP 核心功能閉環進行檢測。專案在資料庫設計與基礎 CRUD 實作上相當穩健，且對於 XSS 與檔案上傳等安全性有極佳的防護意識。

然而，發現一個 **致命的邏輯缺陷 (Fatal Logic)** 存在於「檢索系統」中：目前的架構採用「後端分頁」搭配「前端搜尋/過濾」。這意味著使用者無法搜尋到尚未載入（位於後續頁數）的筆記，導致「知識檢索」這項核心價值完全失效。

此外，**CORS 設定過於寬鬆** 導致了本機應用程式常見的隱私外洩風險。

---

## 🛑 [紅燈] 阻斷性問題 (Blockers)

必須在 MVP 發布前修復，否則核心功能無法正常運作。

### 1. 檢索功能邏輯斷裂 (Search Logic Broken)

- **問題描述**:
  - 後端 API (`GET /api/notes`) 僅實作了 `page` 與 `per_page` 分頁參數，並未接受搜尋關鍵字或過濾條件。
  - 前端 (`index.html`) 的搜尋與過濾邏輯 (`filteredNotes`) 僅針對 **已載入瀏覽器的筆記 (`notes.value`)** 進行運算。
- **影響場景**:
  - 使用者共有 100 則筆記（共 5 頁）。
  - 使用者在第 1 頁（載入前 20 則）輸入關鍵字 "Flask"，但目標筆記位於第 3 頁。
  - 結果：**搜尋結果為空**。使用者必須手動點擊「載入更多」直到該筆記出現，搜尋才會生效。
- **違反原則**: 核心價值「高維度檢索」無法實現。
- **修復建議**:
  - **後端**: 修改 `get_notes` API，新增 `keyword`, `type`, `tag_id` 等 Query Parameters，並在 SQL 中動態組裝 `WHERE` 子句。
  - **前端**: 當使用者輸入搜尋或切換過濾條件時，重置 `page=1` 並呼叫後端 API 取得篩選後的結果，而非僅在前端過濾。

### 2. 高風險 CORS 設定 (Insecure CORS)

- **問題描述**: `app.py` line 37 設定了 `Access-Control-Allow-Origin: *`。
- **風險**:
  - 雖然這是本機應用 (`localhost:5000`)，但若使用者在使用此應用的同時瀏覽了惡意網站，該惡意網站可以透過 JavaScript (`fetch('http://localhost:5000/api/notes')`) 讀取使用者的所有私密筆記。
  - 一般網頁受限於 Same-Origin Policy，但 `*` 標頭明確允許了跨域讀取。
- **修復建議**:
  - 移除 `Access-Control-Allow-Origin: *`。
  - 由於前後端同源 (都在 `localhost:5000` 下運行，前端由 Flask `render_template` 服務)，**根本不需要啟用 CORS**。直接刪除 `after_request` 中的 header 設定即可。

---

## 🟡 [黃燈] 風險與債務 (Risks & Debt)

不影響 MVP 啟動，但需列入已知問題或短期優化清單。

### 1. 缺乏 CSRF 防護 (Missing CSRF Protection)

- **風險**: 類似 CORS 問題，惡意網站可偽造請求（如 `POST /api/notes/delete`）刪除使用者資料。
- **緩解**: 由於目前主要依賴 JSON API 且無身分驗證 (Cookie/Session)，CSRF 攻擊難度較高（瀏覽器會對非 Simple Request 發送 Preflight，若移除了 CORS 即可大幅防護）。
- **建議**: MVP 階段可暫緩，但建議移除 CORS 設定以斷絕大部分風險。

### 2. 前端單檔過大 (Monolithic Frontend)

- **狀況**: `index.html` 已達 2471 行，包含 HTML, CSS (Tailwind classes), JavaScript (Vue 邏輯)。
- **風險**: 維護性極低，閱讀與除錯困難。若需多人協作將產生嚴重衝突。
- **建議**: MVP 後應立即引入構建工具 (Vite) 或使用 Flask `{% include %}` 將組件 (Modal, Card, Sidebar) 拆分為獨立的 HTML 片段。

### 3. API 更新邏輯隱憂 (Update Logic Efficiency)

- **狀況**: `update_note` (Line 560+) 採取「全刪全建」策略 (Delete all tags/urls then Insert)。
- **風險**: 雖然有 Transaction 保護資料一致性，但若關聯資料量大，會造成 `id` 跳號過快與不必要的 I/O 寫入。
- **建議**: MVP 可接受。未來可優化為 Diff 更新 (僅刪除移除的，僅新增不存在的)。

---

## 🛠 [建議] 架構修正方案 (Architectural Fixes)

針對 **紅燈 1 (檢索功能)** 的修正偽代碼：

### Backend (`app.py`)

```python
@app.route('/api/notes', methods=['GET'])
def get_notes():
    # 接收參數
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('q', '')      # 新增
    msg_type = request.args.get('type', '')  # 新增
    tag_id = request.args.get('tag', type=int) # 新增

    # 動態組裝 SQL
    base_sql = "SELECT DISTINCT n.* FROM Notes n"
    joins = []
    wheres = []
    params = []

    if tag_id:
        joins.append("JOIN Note_Tags nt ON n.id = nt.note_id")
        wheres.append("nt.tag_id = ?")
        params.append(tag_id)

    if msg_type and msg_type != 'all':
        wheres.append("n.type = ?")
        params.append(msg_type)

    if keyword:
        # 簡單實作：搜尋標題或內容
        wheres.append("(n.title LIKE ? OR n.content LIKE ?)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")

    # ... 組合 SQL, LIMIT, OFFSET ...
    # 注意：需處理 COUNT(*) 的對應查詢以計算分頁
```

### Frontend (`index.html`)

```javascript
// 修改 fetchNotes 支援參數
const fetchNotes = async (page = 1, reset = false) => {
  // 收集當前過濾狀態
  const params = new URLSearchParams({
    page: page,
    per_page: perPage.value,
    q: searchKeyword.value,
    type: selectedType.value === "all" ? "" : selectedType.value,
    tag: selectedTags.value.join(","), // 若後端支援多標籤
  });

  const response = await fetch(`/api/notes?${params.toString()}`);
  // ... 處理資料 ...

  if (reset) {
    notes.value = result.data;
  } else {
    notes.value = [...notes.value, ...result.data];
  }
};

// 監聽器
watch([selectedType, selectedTags], () => {
  fetchNotes(1, true); // 條件變更時，重置回第一頁並覆蓋資料
});

// 搜尋防抖後
const handleSearchInput = () => {
  // ... debounce ...
  fetchNotes(1, true);
};
```
