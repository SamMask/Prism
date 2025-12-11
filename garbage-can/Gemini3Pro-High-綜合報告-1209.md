# Local Insight - UX/UI Design Audit Report

> Date: 2025-12-09
> Reviewer: Senior Product Designer & UX Researcher
> Version: 1.8.9

基於您提供的截圖與代碼文件（特別是 `index.html`、`styles.css` 與 `_quick-add-modal.html`），我進行了深度的 Design Audit。

核心目標是達到 **Leading SaaS (Linear/Vercel) 等級的實用美學**，但目前的實作代碼中存在幾個與此目標背道而馳的「隱形殺手」。

以下是我的審查報告：

## 🔴 [Critical] 體驗斷點：必須立即修復

### 1. 消失的 "Outfit" 字體 (Typography Broken)

- **問題**：您提到「標題導入 Outfit」，但在 `templates/index.html` 與 `static/css/styles.css` 中，我 **完全沒有看到 Outfit 的引入代碼**。目前的 `font-family` 只有 `Inter Tight`。標題與內文使用同一套字體，導致視覺層次感不足，缺乏 Premium 產品特有的「排版張力」。
- **後果**：標題缺乏個性，與內文混在一起，讓介面顯得平庸。
- **解法**：必須真正引入 Outfit 並在 Tailwind config 中定義。

### 2. Mobile CSS 的「暴力覆蓋」 (Dirty CSS Override)

- **問題**：在 `styles.css` (Line 622) 中，使用了 `!important` 的暴力寫法：
  ```css
  @media (max-width: 767px) {
    .p-6 {
      padding: 1rem !important;
    }
  }
  ```
- **後果**：這是 Tailwind 開發的 **大忌**。這會導致您未來在任何組件寫 `p-6`，在手機上都會被強制改成 `p-4` (1rem)，完全破壞了 Utility-First 的預期行為，讓佈局除錯變成地獄。
- **解法**：應直接在 HTML class 上使用響應式前綴（如 `p-4 md:p-6`），而非寫 Global CSS 覆蓋。

---

## 🟡 [Improvement] 質感提升：邁向 Premium 的關鍵

### 1. 按鈕的「廉價漸層」 vs 「頂級質感」

- **觀察**：`_quick-add-modal.html` 中的儲存按鈕使用了 `bg-gradient-to-r from-purple-600 to-blue-600`。
- **評論**：這種大跨度的雙色漸層在 2025 年的頂級 SaaS 設計中已顯得過時（看起來像 2018 年的 Crypto landing page）。Linear 與 Vercel 的風格傾向於 **單色、高微光 (Subtle Glow)、邊緣高亮 (Inner Border)**。
- **建議**：改用單色背景，搭配 `shadow-[...]` 製作有色陰影或內發光。

### 2. 輸入框的「泥濘感」 (Muddy Dark Mode)

- **觀察**：Quick Add 的 Textarea 使用了 `bg-gray-900/50` 疊在 Modal 的 `bg-gray-900` (Surface) 上。
- **評論**：深色模式下，「黑透黑」容易造成視覺上的髒感（Muddy）。Linear 的做法通常是讓輸入區域 **完全透明**，依靠 Placeholder 與文字本身的顏色，或者給予一個極淡的邊框來界定範圍，而不是用一塊半透明的黑色色塊。

### 3. 觸控目標與間距

- **觀察**：Mobile 端的按鈕雖然有設定 `min-height: 44px`，但 Quick Add Modal 在手機版會貼邊（如果沒有適當的 `mx`）。

---

## 🎨 [Tailwind Recipe]：具體修改建議

針對上述問題，請直接應用以下修改建議。

### Recipe 1: 修復字體與層次 (Tailwind Config)

首先在 HTML `head` 引入 Outfit (或下載字體檔)，然後修改配置：

```javascript
/* 建議修改 tailwind.config (位於 index.html 或配置檔) */
tailwind.config = {
  theme: {
    extend: {
      fontFamily: {
        // 標題專用：厚實、幾何感強
        display: ["Outfit", "sans-serif"],
        // 內文專用：高閱讀性
        body: ["Inter Tight", "sans-serif"],
      },
      // Linear 風格的陰影系統
      boxShadow: {
        glow: "0 0 20px -5px rgba(139, 92, 246, 0.3)", // 紫色微光
        "glow-sm": "0 0 10px -2px rgba(139, 92, 246, 0.2)",
      },
    },
  },
};
```

### Recipe 2: 重構 Quick Add Modal 的輸入區 (去除泥濘感)

將原本的 `_quick-add-modal.html` 中 Textarea 的 class 替換為以下「無邊框、專注內容」的風格：

```html
<!-- 原本: bg-gray-900/50 ... border-theme-default/20 -->
<!-- 建議: 去除背景色塊，改用純粹的文字排版，或者以 focus-within 來強調整個區塊 -->

<div
  class="group relative rounded-xl border border-gray-800 bg-gray-900/40 focus-within:border-purple-500/50 focus-within:bg-gray-900/80 focus-within:shadow-glow-sm transition-all duration-300"
>
  <textarea
    v-model="currentNote.content"
    class="w-full bg-transparent p-5 text-gray-100 placeholder-gray-600 border-none focus:ring-0 resize-none font-mono text-[15px] leading-relaxed"
    placeholder="在此輸入內容..."
  ></textarea>

  <!-- 右下角的上傳提示可以做得更精緻 -->
  <div class="absolute bottom-3 right-3">
    <!-- Indicator content -->
  </div>
</div>
```

### Recipe 3: 頂級質感的「保存按鈕」 (取代漸層)

將既有的漸層按鈕替換為常見於 Linear 的「高亮邊框」風格：

```html
<!-- 原本: bg-gradient-to-r from-purple-600 to-blue-600 -->
<!-- 建議: 單色背景 + 頂部高亮邊框 (Inner Highlight) + 底部陰影 -->

<button
  class="relative overflow-hidden rounded-lg bg-purple-600 px-5 py-2 text-sm font-medium text-white shadow-lg shadow-purple-900/40 hover:bg-purple-500 active:scale-95 transition-all
  before:absolute before:inset-0 before:rounded-lg before:border before:border-white/20 before:content-['']"
>
  <span class="relative flex items-center gap-2">
    {{ isSaving ? 'Saving...' : 'Save Note' }}
    <kbd
      class="hidden sm:inline-block rounded bg-purple-700/50 px-1.5 py-0.5 text-[10px] font-sans text-purple-200"
      >⌘S</kbd
    >
  </span>
</button>
```

### Recipe 4: 移除 CSS 中的許多 `!important`

**請務必** 刪除 `styles.css` 中關於 `.p-6 { padding: 1rem !important; }` 的區塊。
相對的，去 HTML 結構中找到那些容器，改成：

```html
<div class="p-4 md:p-6 lg:p-8 ...">
  <!-- Content -->
</div>
```

這才是響應式設計的正道。

---

# Keyboard-First Audit: QuickAdd & PromptBuilder

> Date: 2025-12-09
> Reviewer: Keyboard-First Advocate (Senior Frontend Dev)
> Target: "Mouse-Free" Operation

作為一名「鍵盤優先」的倡導者，我對您的 `Quick Add` 與 `Prompt Builder` 進行了嚴格的無滑鼠操作審查。以下是我的發現與具體修正建議。

## 1. Quick Add Modal (快速新增)

**總評：勉強及格 (Grade C)**
雖然支援 `Ctrl+Enter` 快速儲存，但核心的導航體驗存在「隱形陷阱」，導致盲打使用者會迷失方向。

### 🔴 Critical Issues (必須修復)

1.  **隱形焦點 (Invisible Focus State)**

    - **問題**：`QuickAddModal` 中的 "Title" (Ghost Input) 與 "Source URL" 輸入框在 CSS 中被設定為 `focus:ring-0` 且無背景變化。
    - **後果**：當我按下 `Shift+Tab` 回到標題時，**我完全不知道我對焦在哪裡**。游標可能在閃爍，但缺乏明顯的邊框或背景色變化，這違反了 WCAG 2.1 Focus Visible 準則。
    - **Fix**：增加 `focus:bg-white/5` 或 `focus:placeholder-white` 讓使用者知道「我在這裡」。

2.  **Tab 順序與 DOM 邏輯衝突**

    - **問題**：HTML 結構是 `Title -> Content`，但您給了 `Content` `autofocus`。
    - **後果**：開啟時焦點在 Content (正確)，但如果我按 `Tab`，焦點會跳去 `URL Input`。如果我想打標題，我必須按 `Shift+Tab`。這雖然是可以接受的妥協，但因為問題 #1 (隱形焦點)，這個 `Shift+Tab` 的動作會讓使用者覺得「焦點消失了」。

3.  **缺少 ESC 關閉**
    - **問題**：代碼中只有 `@keydown.ctrl.enter`，沒有 `ESC` 監聽。
    - **後果**：如果不小心按錯打開了 Modal，鍵盤使用者必須 Tab 很多次去按「取消」按鈕，非常低效。

### ⌨️ Code Recipe: Quick Add 鍵盤優化

修改 `templates/components/_quick-add-modal.html`:

```html
<!-- 1. 在最外層 div 加上 @keydown.esc -->
<div
  v-if="isQuickAddOpen"
  @keydown.esc.prevent="closeEditor"
  @keydown.ctrl.enter.prevent="saveNote"
  tabindex="-1"
  class="..."
>
  <!-- ... -->

  <!-- 2. 修復 Title 的隱形焦點 -->
  <input
    type="text"
    v-model="currentNote.title"
    class="... focus:bg-white/5 focus:ring-1 focus:ring-purple-500/30 rounded px-2 transition-all"
    :placeholder="t('editor.titlePlaceholder', '標題 (可留空)')"
  />

  <!-- ... -->
</div>
```

---

## 2. Prompt Builder (提示詞產生器)

**總評：有很多視覺才看得到的元素 (Grade C-)**
許多進階控制項 (Toggle, Hover Actions) 對鍵盤使用者是「隱形」或「無法觸及」的。

### 🔴 Critical Issues

1.  **隱形的 Toggle Switch**

    - **問題**：右側面板的「權重模式 (Weights)」使用了 `class="sr-only peer"` 的 Checkbox。
    - **後果**：當鍵盤 Tab 到這個選項時，因為它是 `sr-only` (Screen Reader Only)，瀏覽器預設的 Focus Ring 被隱藏了，而其兄弟元素 `div` 沒有設定 `peer-focus:ring`。結果就是：焦點走到了這裡，但畫面上**沒有任何變化**，使用者會以為當機了。

2.  **薛丁格的刪除按鈕 (Hover-only Actions)**

    - **問題**：左側面板的自定義模板刪除按鈕使用了 `opacity-0 group-hover:opacity-100`。
    - **後果**：鍵盤使用者 Tab 到按鈕時，按鈕依然是透明的 (opacity-0)。**這是嚴重的無障礙缺失**。使用者會聚焦在一個「看不見的東西」上。
    - **Fix**：改為 `opacity-0 group-hover:opacity-100 focus:opacity-100`。

3.  **缺乏全局快捷鍵**
    - **問題**：Prompt Builder 是生產力工具，但居然不支援 `Ctrl+Enter` 快速「複製結果」或「儲存」。使用者調整完參數後，還要 Tab 幾十次才能按到右下角的按鈕。

### ⌨️ Code Recipe: Prompt Builder 優化

**A. 修復 Toggle Switch 可見性 (`_right-panel.html`):**

```html
<label
  class="flex items-center gap-2 text-xs text-theme-secondary cursor-pointer"
>
  <!-- 加上 focus:ring-2 讓 sr-only 的 checkbox 在被 focus 時能體現在 peer 上 -->
  <input type="checkbox" v-model="useWeights" class="sr-only peer" />
  <div
    class="... peer-focus:ring-2 peer-focus:ring-purple-500 peer-focus:ring-offset-2 peer-focus:ring-offset-gray-900 ..."
  ></div>
  {{ t('promptBuilder.weights', '權重') }}
</label>
```

**B. 修復隱形刪除按鈕 (`_left-panel.html`):**

```html
<button
  v-if="template.isCustom"
  class="... opacity-0 group-hover:opacity-100 focus:opacity-100 ..."
  :title="t('common.delete', '刪除')"
></button>
```

**C. 增加全域快捷鍵 (`usePromptBuilder.js` + `prompt-builder.html`):**

在 `prompt-builder.html` 的最外層 `div` (或是 `window` listener) 加上：

```html
<div
  id="app"
  @keydown.ctrl.enter.prevent="copyOutput"
  @keydown.ctrl.s.prevent="saveToLibrary"
></div>
```

_(需在 `usePromptBuilder` 中實作對應的處理，或直接綁定到現有函式)_

---

## 總結改進清單

1.  **所有 Modal**：必須綁定 `ESC` 關閉。
2.  **所有 Input**：移除 `focus:ring-0` 除非你有自定義的 Focus 樣式 (Border/Background change)。
3.  **所有 Hover 顯示的元素**：必須補上 `focus:opacity-100`。
4.  **Prompt Builder**：補上 `Ctrl+Enter` (複製) 與 `Ctrl+S` (儲存)。
