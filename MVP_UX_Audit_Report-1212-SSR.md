# MVP UX Audit Report (SSR Edition)

Date: 2025-12-12
Version: v1.0

## 1. [紅燈] 阻斷性問題 (Critical / Blocking)

_用戶無法完成任務，或會導致嚴重挫折的致命傷。_

### C-01. 文字可讀性嚴重不足 (Visibility)

- **位置**: 全域 (Global), 特別是 Sidebar 標籤計數、Footer 版本號、Prompt Builder 權重數值。
- **問題**: 使用了 `text-theme-muted` (對應 Tailwind `gray-500` #6b7280) 在深色背景 `gray-900` (#111827) 上。
- **對比度**: ~2.8:1 (WCAG AA 標準要求至少 4.5:1)。
- **影響**: 在非理想光源或螢幕亮度較低時，**用戶完全看不到這些資訊**，導致「標籤數量」、「權重數值」等關鍵資訊消失。
- **小白視角**: "為什麼這裡有一塊黑黑的？好像有字但看不清楚？"

### C-02. 標籤輸入邏輯陷阱 (Interaction Logic)

- **位置**: 快速新增 (Quick Add Modal) & 編輯器。
- **問題**: 用戶輸入標籤文字後，習慣直接點擊「儲存」或點選外部。目前的邏輯要求必須按下 `Enter` 才會將標籤加入陣列。
- **影響**: 用戶花時間打字，結果儲存後發現**標籤根本沒存進去**。這是極高頻的資料遺失風險。
- **小白視角**: "我明明打了 '設計' 這個標籤，為什麼存檔後找不到？系統壞了嗎？"

### C-03. Prompt Builder 權重模式的「隱形語法」 (Conceptual Model)

- **位置**: Prompt Builder 右側面板 "Weights" Toggle。
- **問題**: 開啟 "Weights" 後，雖然左側出現了 Slider，但用戶預覽區的 Prompt 會突然變成 `(keyword:1.2)` 格式。
- **影響**: 初學者不懂這是 Stable Diffusion/Midjourney 的特定語法，可能會以為是系統 Bug 或是亂碼，甚至直接把這個格式貼給不支援權重的模型 (如 ChatGPT)，導致產出不如預期。
- **小白視角**: "為什麼我的關鍵字被括號包起來還有一堆數字？能不能關掉？"

---

## 2. [黃燈] 摩擦與雜訊 (Friction / Noise)

_用戶需要思考才能操作的痛點，不直觀但勉強可用。_

### F-01. 專業術語過多 (Jargon)

- **位置**: Sidebar 篩選器。
- **問題**: `AND` / `OR` 切換按鈕。
- **影響**: 對工程師很直觀，但對一般用戶來說 `AND` (同時符合) 和 `OR` (符合任一) 需要腦力轉換。
- **建議**: 改為圖示或更直白的文字 "精確" vs "寬鬆"。 //改成 + 代替 or ， and 看有沒有什麼圖示

### F-02. 拖放功能的「隱藏條件」 (Hidden Affordance)

- **位置**: 筆記列表 (Grid View)。
- **問題**: 用戶直覺想拖曳卡片排序，但系統強制要求先切換到「自訂排序 (Custom)」模式才能拖曳，且 UI 上沒有明確提示。
- **影響**: 用戶嘗試拖曳失敗，會以為系統不支援拖曳，產生挫折感。
- **小白視角**: "這些卡片看起來像可以拖的，為什麼我拉不動？"

### F-03. Prompt Builder 進階選項藏得太深 (Discoverability)

- **位置**: Prompt Builder 左側面板。
- **問題**: "Randomize (骰子)" 和 "Edit (齒輪)" 按鈕只有圖示，缺乏文字標籤或 Tooltip (只有 title 屬性，手機上看不到)。
- **影響**: 用戶可能完全忽略這些強大的功能，導致只把工具當作簡單的填空題，無法體驗到「靈感激發」的價值。

---

## 3. [建議] 交互修正 (Low-Fidelity Wireframe / Logic)

### S-01. 標籤輸入優化 (針對 C-02)

**當前邏輯**:
`Input: "Design" -> Click Save -> Tag Lost`

**修正邏輯 (Auto-commit)**:
`Input: "Design" -> Blur Event (失焦) -> Auto Add Tag -> Content Saved`

**低保真交互描述**:

1.  **監聽 blur 事件**: 當游標離開標籤輸入框時，若框內有文字，自動觸發 `addTag` function。
2.  **Placeholder 提示**: 將 placeholder 改為 "輸入後按 Enter 或 逗號"。
3.  **視覺回饋**: 當標籤生成時，給予一個微小的閃爍或顏色變化 (如紫色光暈)，確認系統已接收。

### S-02. 權重模式 (Weights) 的漸進式揭露 (針對 C-03)

**當前設計**:
一個簡單的 Checkbox `[ ] Weights`。

**修正建議**:
將 Weights 功能隱藏在「進階模式」中，或在開啟時彈出 Toast 提示。

**互動建議**:

- **Default**: 隱藏 Slider，輸出純文字 Prompt。
- **Toggle ON**:
  1.  顯示 Slider。
  2.  右側預覽區上方顯示小提示: _"已啟用權重語法 (::)，適用於 MJ/SD"_。
  3.  若偵測到用戶複製到 ChatGPT (這比較難偵測，但可以做在「複製」按鈕上)，跳出詢問 _"是否要自動移除權重參數以符合 ChatGPT 格式？"_ //目前的權重模式還不完成，直接先隱藏權重開關、權重滑桿跟 Text
      JSON 開關關掉

### S-03. 篩選器語意化 (針對 F-01)

**當前 UI**:
`[ AND ]` (Button)

**修正 UI**:
使用 Dropdown 或 Segmented Control: //改成 + 代替 or ， and 看有沒有什麼圖示

- [✓] **包含所有** (Match All)
- [ ] **包含任一** (Match Any)

或者使用更直觀的圖示：

- 🔗 (AND) //用 + 符合
- ∪ (OR - 集合聯集符號，但這也偏數學，建議用文字) //可以 沒差啦 使用者點一點不知道 就不要知道好了

### S-04. 視覺對比度修復 (針對 C-01)

**全域 CSS 變數調整**:

```css
:root {
  /* 原本的 muted 太暗，提升亮度 */
  --color-text-muted: #94a3b8; /* gray-400 equivalent */

  /* 或者保留 muted 但增加 font-weight 彌補可讀性 */
  /* 但最直接是改顏色 */
}
```

**特定元件**:

- Sidebar 計數器: 使用 `bg-gray-800 text-gray-300` 膠囊樣式，增加背景對比。
- Prompt Builder Slider 數值: 放在 Slider 拇指上方或右側，使用亮色字體 (white/gray-200)。
