# MVP UX/UI 體驗審查報告 (Audit Report)

**日期**: 2025-12-11
**審查對象**: Local Insight (v1.0 MVP)
**審查員**: Antigravity (Agentic AI)

本報告針對 MVP 版本的「核心任務流暢度」與「認知負荷」進行審查，忽略非阻斷性的視覺細節。

---

## 1. 🚦 [紅燈] 阻斷性體驗 (Showstoppers)

> **定義**: 用戶無法完成任務、陷入死胡同、或產生嚴重誤解的設計。

### 1-1. 提示詞產生器 (Prompt Builder) 的錯誤死胡同

- **位置**: `templates/prompt-builder.html`
- **問題**: 當配置檔 (`prompt_options.json`) 載入失敗時，畫面顯示紅色錯誤框與 "Retry" 按鈕。
- **致命傷**: 如果重試無效（例如伺服器端檔案遺失），用戶將**被困在該頁面**。該頁面是獨立的 HTML，沒有全域導航列 (Global Nav)，也沒有「返回首頁」的連結。用戶只能透過瀏覽器上一頁離開，這違背了 "User Control and Freedom" 原則。
- **建議**: 在錯誤訊息框中增加 `<a href="/" class="...">返回首頁</a>` 連結。

### 1-2. 搜尋空的誤導性狀態 (Dead End Trap)

- **位置**: `templates/components/_note-grid.html`
- **問題**: 當搜尋關鍵字導致結果為 0 時，系統顯示 "No Notes... Create First" (尚無筆記... 建立第一則)。
- **致命傷**: 這誤導用戶認為**資料庫是空的**，鼓勵他們重複建立資料，而不是「清除搜尋條件」。這在尋找特定筆記時會造成極大的認知困惑。
- **建議**: 區分 `filteredNotes.length === 0` 的原因。如果是因為搜尋/過濾導致，應顯示 "No matches found" 並提供「Clear Search」按鈕。

### 1-3. 手機版側邊欄的互動摩擦 (Mobile Friction)

- **位置**: `templates/components/_sidebar.html`
- **問題**: 在手機版 (Mobile) 模式下，側邊欄是覆蓋層 (Overlay)。當用戶點擊「筆記類型」或「標籤」進行過濾時，**側邊欄不會自動收合**。
- **致命傷**: 用戶點擊後看不到任何反饋（因為列表被側邊欄擋住了），必須手動點擊背景關閉側邊欄才能確認過濾結果。這打破了 "Visibility of System Status" 與操作預期。
- **建議**: 在 `_sidebar.html` 的過濾按鈕 `click` 事件中，加入 `mobileSidebarOpen = false` 的邏輯。

---

## 2. ⚠️ [黃燈] 摩擦與雜訊 (Friction & Noise)

> **定義**: 認知負荷過高、操作不直覺，但尚可勉強使用的問題。

### 2-1. "Quick Add" 與 "New Note" 的競食 (Button Confusion)

- **位置**: `templates/components/_header.html`
- **問題**: 標頭同時存在 "Quick Add (閃電)" 與 "New Note (加號)" 按鈕，且視覺權重相近 (Accent vs Primary Color)。
- **摩擦**: 新手用戶需思考「我該按哪一個？有什麼差別？」。這增加了決策時間 (Hick's Law)。
- **建議**:
  1.  降低其一的視覺權重 (例如 Quick Add 改為 Icon-only 或 Ghost button)。
  2.  或明確區分文案：例如 "Quick Draft (速記)" vs "Full Article (完整編輯)"。

### 2-2. 標籤過濾的邏輯負擔 // 這個不改

- **位置**: `templates/components/_sidebar.html`
- **問題**: 提供 "AND / OR" 切換按鈕。
- **摩擦**: 對於普通用戶，"Boolean Logic" 是沉重的認知負擔。大多數筆記軟體的預設行為是 OR (包含任一) 或 AND (精確匹配)，讓用戶手動切換增加了介面複雜度。
- **建議**: MVP 階段建議固定為一種邏輯 (通常是 OR，擴大搜尋範圍)，或將此開關移至「進階搜尋」。

### 2-3. 原始 Markdown 編輯的門檻 //太麻煩的話不加，但會用到 Markdown 語法 我想到的是復制備份 ai 給的 帶復制鈕那框文用(提示詞或 code)，這時就行方便 也不用自已打

- **位置**: `templates/components/_editor-modal.html`
- **問題**: 編輯器是純文字框 (Textarea)，依賴用戶手打 Markdown 語法 (如 `**bold**`)。雖然有「預覽」模式，但缺乏 WYSIWYG 工具列。
- **摩擦**: 對於非技術背景的 "Visual Insight" 用戶，這是一個高門檻。
- **建議**: 短期內增加一個簡易工具列 (Bold, Image, Link)；長期建議整合 Tiptap 或 EasyMDE。

---

## 3. 🛠️ [建議] 交互修正 (Interaction Fixes)

### 針對 1-1 (Prompt Builder Dead End):

```html
<!-- 在 Error State div 中加入 -->
<div class="mt-4 flex gap-3">
  <button @click="initialize">Retry</button>
  <a href="/" class="text-white underline">返回首頁</a>
  <!-- 新增 -->
</div>
```

### 針對 1-2 (Search Feedback):

```html
<div v-else-if="filteredNotes.length === 0">
  <div v-if="searchKeyword || selectedTags.length > 0">
    <p>No matches found for "{{ searchKeyword }}"</p>
    <button @click="clearSearch">Clear Search</button>
  </div>
  <div v-else>
    <p>No Notes yet. Create your first one!</p>
  </div>
</div>
```

### 針對 1-3 (Mobile Sidebar):

```javascript
// 在 Sidebar Vue Component 中
methods: {
    selectType(type) {
        this.selectedType = type;
        if (window.innerWidth < 768) { // 簡單的 mobile 偵測
            this.$emit('close-mobile-sidebar'); // 或修改 prop
        }
    }
}
```

---

**總結**:
MVP 的核心功能（CRUD、Prompt Builder）已具備，但在**錯誤處理**與**手機版互動**上有明顯的體驗斷層。修復上述 [紅燈] 問題僅需極少的程式碼改動，但能大幅提升產品的穩定感與專業度。
