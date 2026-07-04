# LLM UX/UI 設計指導原則

整理日期：2026-06-09
最後更新：2026-06-24

來源：

- 2026-06-09 使用者提供的 UI 設計原則參考對話
- Leonxlnx/taste-skill
- nexu-io/open-design
- VoltAgent/awesome-design-md
- bergside/awesome-design-skills
- OpenCoworkAI/open-codesign
- alchaincyf/huashu-design
- NN/g 10 Usability Heuristics
- WCAG 2.2
- W3C WAI Designing for Web Accessibility
- GOV.UK Service Standard / form structure / error summary
- GOV.UK Design System
- 18F UX Guide / Methods / Content Guide
- Microsoft Inclusive Design
- Radix Primitives
- Laws of UX
- Primer / Polaris / Atlassian / Carbon / Fluent / Material Web / USWDS design systems

這份文件用來約束 LLM / coding agent 設計 UX / UI 時的行為。它不是品牌手冊，也不是完整 design system。它的目標是讓 LLM 在做前端畫面前先判斷使用者任務、體驗流程、受眾、資料密度、既有元件與驗證方式，避免產出看似現代但流程不成立的 AI slop UI。

使用時機：新頁面、新 app、新 dashboard、新 landing page、既有 UI redesign、需要產出 `DESIGN.md` / design tokens / component guideline / UI skill 的任務。

不必完整使用：修錯字、單一按鈕文案、局部 spacing 小修、已有明確設計稿且只需照稿實作的任務。小修仍要遵守 accessibility、狀態完整與驗證規則。

## 1. 核心判斷

LLM 設計 UI 時，第一件事不是選 Tailwind class，也不是先畫 hero，而是回答：

> 這個介面要幫哪種使用者完成哪個主要任務？

如果主要任務不清楚，就不要直接開始做視覺風格。

UX / UI 的完成不等於畫面漂亮。至少要同時滿足：

- 使用者一眼知道現在在哪裡、能做什麼、下一步是什麼。
- 主要任務比裝飾元素更突出。
- 使用者能在合理步驟內完成任務。
- 錯誤能被預防、修正、撤銷或重試。
- 狀態完整：loading / empty / error / success / disabled / focus 等都處理。
- mobile / desktop 都可用。
- keyboard、focus、contrast、semantic HTML 不被犧牲。
- 有 preview、screenshot、互動測試或其他可檢查證據。

## 2. 來源權重

參考來源不是同一個層級。LLM 必須先分清楚底線、系統參考與視覺靈感。

來源權重由高到低：

1. UX / usability / accessibility 底線：NN/g、WCAG、W3C WAI。
2. 服務與任務流程底線：GOV.UK Service Standard、GOV.UK Design System、GOV.UK form / error patterns。
3. 專案既有 design system：本 repo / 產品內的 `DESIGN.md`、tokens、components。
4. UX 研究 / 方法 / content 參考：18F UX Guide、18F Methods、18F Content Guide。
5. 成熟產品級系統參考：Primer、Polaris、Atlassian、Fluent、Carbon、Material Web、USWDS。
6. LLM 工作流參考：Taste Skill、Huashu Design、Open Design、awesome-design-md、Open CoDesign。
7. 視覺靈感：品牌 `DESIGN.md`、公開網站分析、個別風格 skill。

若來源衝突，優先保留：

- 使用者任務。
- 可恢復性。
- Accessibility。
- Usability。
- 專案既有元件與 tokens。
- 正式資料 / 狀態 / 錯誤處理的可驗證性。

視覺靈感不能覆蓋 accessibility、任務流程或既有 design system。

## 3. UX 體驗原則

LLM 設計 UI 前，必須先判斷使用者體驗，而不是先判斷視覺風格。

UX 的第一目標是讓使用者更安全、更少思考、更少犯錯、更快完成任務。UI 美感只能服務這個目標，不得取代這個目標。

### 3.1 使用者任務優先

每個頁面都必須先定義：

- 使用者為什麼來？
- 使用者第一個要完成的任務是什麼？
- 這個任務完成後，使用者得到什麼？
- 如果使用者不能完成，損失是什麼？
- 此頁是否真的需要存在，或只是把其他流程切碎？

不得先從 hero、卡片、gradient、動畫、icon 開始設計。

### 3.2 完整流程，不只單頁

LLM 必須描述完整使用者流程：

- 入口：使用者從哪裡進來？
- 主流程：最短完成路徑是什麼？
- 分支：有哪些必要選擇？
- 錯誤：輸入錯、資料錯、權限錯、系統錯時怎麼辦？
- 回復：是否能取消、返回、撤銷、重試？
- 完成：成功後使用者看到什麼？
- 續接：是否需要保存草稿、恢復狀態、下次接續？

只設計單一漂亮畫面，不算完成 UX 設計。

### 3.3 使用者假設與驗證

UX 不得只靠模型推測。LLM 必須標明：

- 已知使用者。
- 推測使用者。
- 核心任務。
- 尚未驗證的假設。
- 可能造成錯誤設計的未知資訊。
- 最小驗證方式：訪談、可用性測試、log、既有客服 / issue、競品流程觀察。

若缺少使用者證據，最多只能宣稱「UX 假設」或「設計草案」，不能宣稱體驗已驗證。

### 3.4 UX 方法選擇

LLM 必須依不確定性選方法，不要所有問題都只用 heuristic checklist。

- 不知道使用者是誰：先做 user group / stakeholder map。
- 不知道流程哪裡卡：做 journey map / service blueprint。
- 不知道資訊怎麼分類：做 card sorting / IA review。
- 不知道畫面是否可用：做 usability test / heuristic evaluation。
- 不知道文案是否懂：做 content review / first-click test。
- 只是小修：用 lightweight checklist，不開完整 UX 流程。

方法不是儀式。選方法是為了降低不確定性，不是為了把小任務拖成研究專案。

### 3.5 認知負荷

UI 應讓使用者辨識，而不是記憶。

必須避免：

- 要求使用者記住上一頁資訊。
- 同一概念使用不同名詞。
- 同一操作在不同頁面有不同位置或樣式。
- 一次展示太多同級選項。
- 把少用功能放在主要任務路徑上。
- 用內部技術詞取代使用者語言。

若功能複雜，應用分組、漸進揭露、預設值、範例、contextual help 降低負荷。

### 3.6 可控制與可回復

使用者必須能掌控流程。

高風險操作必須支援至少一種：

- cancel
- back
- undo
- retry
- draft save
- soft delete
- confirmation
- recovery path

不得讓使用者進入無法退出、無法理解、無法修正的狀態。

### 3.7 新手與熟手

工具型 UI 要同時照顧新手與熟手。

新手需要：

- 清楚入口。
- 空狀態說明。
- 範例。
- helper text。
- 安全預設值。

熟手需要：

- 快捷操作。
- 批次操作。
- 搜尋 / 篩選。
- keyboard shortcuts。
- 可掃描資訊密度。
- 少打斷的流程。

不得為了新手提示犧牲高頻使用效率，也不得為了熟手密度讓新手無法開始。

### 3.8 Content UX

文案就是介面的一部分。UX 不只靠 layout，也靠 label、button、error、empty state 與 success message。

Content UX 原則：

- 使用使用者語言，不使用內部術語。
- Button / label / error / empty state 必須說明下一步。
- 不用「已優化」「管理」「設定」這種模糊詞遮蔽實際動作。
- 錯誤訊息要說明問題、位置、修正方式。
- 空狀態要告訴使用者現在能做什麼。
- 專業詞第一次出現要有脈絡或說明。

### 3.9 成功標準

UI 設計完成前，必須定義成功標準：

- 使用者能否在不讀文件下理解主要任務？
- 是否能在合理步驟內完成？
- 錯誤是否能被預防或恢復？
- 重要狀態是否可見？
- 是否能支援鍵盤、手機、小螢幕與不同文字長度？
- 是否有可觀察的完成證據：preview、interaction steps、screenshot、測試或實際操作紀錄？

沒有成功標準，不得宣稱 UX 已完成。

## 4. 設計前讀稿規則

LLM 不得一開始就套預設模板。先讀現有文件與程式，最小必要地確認：

- 產品類型：工具、SaaS、dashboard、CRM、內容網站、品牌頁、遊戲、資料分析介面。
- 主要使用者：新手、專家、營運人員、管理者、開發者、消費者。
- 核心任務：使用者進來第一件真正要完成的事。
- 資料密度：少量行銷資訊、中等表單、多資料表、多圖表、高頻操作。
- 現有規範：是否已有 `DESIGN.md`、design tokens、component library、brand guide。
- 技術限制：框架、元件庫、響應式需求、無障礙要求、資料狀態。
- 不做事項：本輪不得新增的風格、頁面、元件、動畫或設計系統。

若是既有專案，優先讀：

1. 現有 UI / components / design tokens。
2. 相關頁面與路由。
3. `AGENTS.md` / `CLAUDE.md`。
4. `DESIGN.md` 或本文件。
5. 任務指定的設計稿、截圖或 reference。

沒有看過既有 components，就不要新增重複元件。

### 4.1 Design Context 抽取

高保真 UX / UI 必須從既有 context 長出來。LLM 不得看一眼就憑印象重畫。

開工前優先找：

- 專案內的 `DESIGN.md`、tokens、theme、global stylesheet。
- 既有 component：Button、Card、Dialog、Table、Form、Layout scaffold。
- 已上線產品、現有頁面截圖、Figma 截圖、品牌指南、logo、行銷素材。
- 使用者指定的 reference URL、競品、同產品舊版流程。

若可讀 codebase，必須抽出具體值，而不是只說「大概風格」：

- hex / oklch / CSS variables。
- spacing scale。
- font stack / font loading。
- border radius。
- shadow / elevation pattern。
- component vocabulary：button variant、card pattern、table density、form error style。

沒有 design context 時，只能標成 fallback 設計假設；不得宣稱符合品牌或既有產品。

### 4.2 具名品牌 / 產品資產協議

只要設計中出現可識別的品牌、公司、產品、SDK、AI 工具、硬體或 app，LLM 不得只靠記憶、色值或通用 icon 製作。

必須先確認：

- 產品 / 技術 / 版本 / 發布狀態是否為最新事實。
- 官方 logo 或可辨識 mark。
- 實體產品是否有官方產品圖、渲染圖或可授權圖片。
- 數位產品是否有 UI 截圖、App Store / Google Play 圖、官網截圖或使用者提供截圖。
- 品牌色、字體、禁用事項與視覺語氣是否有來源。

落地方式：

- 在目標專案的 `DESIGN.md` 或 `brand-spec.md` 固化來源、檔案路徑、色值與使用邊界。
- CSS 使用 token / variable，不在不同頁面臨時發明相近色。
- 缺 logo / 產品圖 / UI 截圖時，先問使用者或標誠實 placeholder，不用通用 SVG、CSS 剪影、假資料或 AI 風格圖硬補。
- 資產是否可用要驗證：能開啟、解析度足夠、版本正確、沒有未遮罩個資或敏感資訊。

## 5. 使用者流程輸出格式

若任務涉及新頁面、redesign、dashboard、form、table 或工具型 UI，LLM 必須把 3.2 的流程整理成可施工格式。

輸出格式：

- 入口：
- 主任務：
- 主要 CTA：
- 次要 action：
- 成功路徑：
- 失敗 / 無權限 / 資料缺失：
- 退出 / 取消 / 撤銷：
- 草稿 / 恢復 / 未儲存變更：

工具型 UI、SaaS、dashboard、CRM、後台管理介面，優先服務工作流程，不優先服務視覺展示。若頁面主要任務是操作、審查、分析或管理，不得把第一屏做成 marketing hero。

### 5.1 Navigation / Wayfinding

使用者必須知道自己在哪裡、從哪裡來、下一步能去哪裡。

LLM 必須檢查：

- 目前頁面 / section 是否清楚標示。
- 側邊欄、tab、breadcrumb、stepper 的 active state 是否明確。
- 搜尋、篩選、排序後，使用者是否知道目前結果範圍。
- detail page 是否有返回列表或上一層路徑。
- 多步驟流程是否顯示目前步驟、剩餘步驟與可返回範圍。
- 空狀態或錯誤狀態是否仍保留可離開路徑。

## 6. 三個設計旋鈕

每次設計前先明確選擇，不要讓模型用預設審美。

| 旋鈕 | 意義 | 低 | 高 |
| --- | --- | --- | --- |
| `DESIGN_VARIANCE` | 設計變異度 | 穩定、常規、低風險 | 非對稱、強品牌、實驗性 |
| `MOTION_INTENSITY` | 動效強度 | hover / focus / basic transition | scroll animation / gesture / rich motion |
| `VISUAL_DENSITY` | 資訊密度 | 留白多、低資訊量 | dashboard、資料表、高頻操作 |

建議預設：

- SaaS / CRM / dashboard / 內部工具：`DESIGN_VARIANCE` 低到中、`MOTION_INTENSITY` 低、`VISUAL_DENSITY` 中到高。
- 品牌頁 / portfolio / landing page：`DESIGN_VARIANCE` 中到高、`MOTION_INTENSITY` 中、`VISUAL_DENSITY` 低到中。
- 遊戲 / 創意互動：可提高變異度與動效，但仍要可操作、可讀、可驗證。

## 7. Design System 與文件分工

有既有 design system 時，優先沿用，不另創一套。

沒有 design system 時，只定義本輪必要 tokens：

- color
- typography
- spacing
- layout
- radius
- elevation / shadow
- motion
- component states
- voice / microcopy
- anti-patterns

文件分工：

- `AGENTS.md` / `CLAUDE.md`：LLM 施工入口與不可越界事項。
- `DESIGN.md`：這個專案的 UX / UI 要解決什麼任務、流程如何成立、畫面應該長什麼樣。
- `LLM-UX-UI-DESIGN-PRINCIPLES.md`：通用 UX / UI 設計約束與 anti-slop 原則。
- `SKILL.md`：若要做成 agent skill，才放任務步驟、使用時機、禁止事項、quality gates。

不要把 `DESIGN.md`、`SKILL.md`、`AGENTS.md` 寫成三份互相重複的長文。入口文件只放路由與硬邊界；具體視覺語言放 `DESIGN.md`。

## 8. Layout 與資訊層級

Layout 要服務任務，不是服務模板。

原則：

- 第一屏必須呈現主要任務。
- 工具型 UI 不要做成 marketing hero。
- SaaS、CRM、dashboard、營運工具應該安靜、密集、可掃描。
- 主要 CTA 必須清楚且有限，不要每個區塊都搶主行動。
- 表格、圖表、表單要有清楚群組、排序、篩選、空狀態與錯誤狀態。
- 不要卡片套卡片；頁面區塊應用 layout band 或自然分區。
- 固定格式元素要有穩定尺寸，避免 hover、loading、數值更新造成 layout shift。

常見錯誤：

- 大 hero + 三張 feature card 套到所有產品。
- dashboard 只做漂亮卡片，沒有資料新鮮度、缺資料、錯誤與 drill-down。
- 工具型產品把主要操作藏在第二屏。
- mobile 只縮小 desktop，沒有重新安排資訊優先序。

### 8.1 Performance / Perceived Performance

效能也是 UX。LLM 不得用大量動畫、圖片、blur、shadow 或 client-only heavy component 讓介面變慢。

必須檢查：

- 首屏是否能快速顯示主要任務。
- loading 是否有明確範圍，不要整頁無限 spinner。
- 長表格、圖表、圖片列表是否需要 pagination、virtual scroll 或 progressive loading。
- 資料更新時是否避免 layout shift。
- skeleton / placeholder 是否符合實際內容尺寸。
- 動畫與視覺效果不得拖慢高頻操作。

## 9. Typography

字體層級要對應資訊層級。

原則：

- hero-scale type 只用在真正 hero。
- panel、card、sidebar、table 使用緊湊標題。
- 不用 viewport width 直接縮放字體。
- 不使用負 letter-spacing。
- 長字、按鈕文字、表格欄位必須在 mobile / desktop 都不溢出。
- 文案要可掃描；不要讓裝飾性標語壓過任務資訊。

## 10. Color / Contrast / Tokens

色彩必須有角色，不是只求好看。

至少定義：

- primary
- surface
- border
- muted
- danger
- warning
- success
- info
- focus

規則：

- 狀態不可只靠顏色傳達。
- 對比度要可讀。
- focus ring 必須可見。
- disabled state 必須可辨識但仍可讀。
- 不要把整個產品做成單一色系變體。
- 避免無理由的 AI purple / blue gradient、深色 mesh、裝飾 orb。

## 11. 元件狀態完整性

任何互動元件至少考慮：

- default
- hover
- focus
- active
- disabled
- loading
- empty
- error
- success
- permission denied
- stale / out-of-date

表單必須有：

- label
- helper text
- validation
- error message
- submit loading
- submit success / failure
- keyboard 操作

資料表必須有：

- loading
- empty
- error
- stale data 標記
- sorting / filtering / pagination 或 scrolling 策略
- mobile 檢視策略

Dashboard 必須有：

- 資料來源或時間戳。
- 缺資料狀態。
- stale 狀態。
- 圖表 fallback。
- 指標定義或 tooltip，避免使用者猜測。

## 12. 表單、錯誤與危險操作

表單中的每個欄位都必須有存在理由。不得收集本輪任務不需要的資料。

每個欄位必須能回答：

- 為什麼需要這個資料？
- 哪些使用者需要填？
- 如何驗證？
- 錯誤時如何修正？
- 這份資料如何更新、保護或刪除？

表單結構：

- 複雜表單優先拆成步驟或 one thing per page。
- 高頻內部工具可合併欄位，但必須證明掃描與操作效率更好。
- 表單送出後要有明確 feedback，不可讓使用者猜是否成功。
- 有未儲存變更時，離開前必須提示或自動保存。

錯誤處理必須同時照顧總覽與欄位本身：

- 表單錯誤要有清楚總覽。
- 每個錯誤要能定位到對應欄位。
- 欄位旁要有具體錯誤訊息。
- 錯誤文案要說明問題與修正方式。
- 不得只顯示 `Something went wrong`。
- 不得只用紅色表示錯誤。

危險操作必須有防呆：

- destructive action 必須明確標示後果。
- 高風險操作需要 confirm、undo、soft delete 或 recovery path。
- 批次操作要顯示影響數量與範圍。
- 有未儲存變更時，離開頁面前必須提示或自動保存。

## 13. 資料型 UI 規則

資料型 UI 的核心不是漂亮，而是可信、可讀、可操作。

Dashboard、table、chart、analytics、monitoring、trading、admin 類 UI 必須檢查：

- 數字是否有單位？
- 是否有時間範圍？
- 是否顯示資料來源？
- 是否顯示 last updated？
- 是否區分 loading、empty、error、partial、stale、permission denied？
- 表格是否有排序、篩選、搜尋、分頁或 virtual scroll 策略？
- 圖表是否有 legend、tooltip、axis label、空值與異常值處理？
- 是否只靠顏色傳達漲跌、警告、類別或狀態？
- 匯出、複製、批次操作是否有明確範圍？

空值必須分型，不得全部顯示為空白：

- 尚未載入。
- 查無結果。
- 使用者無權限。
- 資料源失敗。
- 尚未建立資料。
- 資料被篩選條件排除。
- 資料過期或不完整。

高風險資料不可用漂亮卡片掩蓋不確定性。

### 13.1 Privacy / Trust UX

涉及帳號、金鑰、交易、個資、內部資料、正式資料或不可逆操作時，UI 必須讓使用者理解風險。

必須檢查：

- 是否遮罩 token、secret、email、phone、account id 等敏感資料。
- screenshot / preview 是否避免暴露真實敏感資料。
- 權限不足時是否說明原因與下一步，而不是只顯示空白。
- destructive / irreversible action 是否顯示影響範圍。
- AI 產生、推測、未驗證、stale、partial data 是否有明確標記。
- 使用者是否知道資料會被儲存、送出、覆蓋或刪除。

## 14. 複雜元件規則

複雜互動元件不得用普通 `div` 假裝完成。

以下元件必須優先使用既有元件庫或成熟 primitive：

- Dialog
- Dropdown
- Popover
- Tooltip
- Tabs
- Accordion
- Combobox
- Select
- Date picker
- Command palette
- Toast / notification
- Drag and drop

若自行實作，必須列出並驗證：

- keyboard navigation
- focus visible
- focus trap / focus return
- Escape 行為
- outside click 行為
- ARIA role / name / value
- screen reader label
- disabled / loading / error state
- mobile touch behavior

沒有上述驗證，不得宣稱該元件完成。

## 15. Interaction / Motion

動效只用於狀態轉換、空間關係、操作回饋。

規則：

- 不用動效掩蓋資訊架構不清。
- 操作流程要能取消、返回、撤銷或重試。
- 高頻工作介面不要用過多 scroll animation、magnetic cursor、視差效果。
- 動效不得阻礙閱讀、鍵盤操作或 reduced motion。
- 有破壞性操作時，要有確認、undo 或 rollback 思考。

## 16. Responsive / Density

Responsive 不是把 desktop 壓扁。

LLM 必須考慮：

- mobile / tablet / desktop 的資訊優先序。
- touch target 是否足夠。
- sidebar、toolbar、table、modal 在小螢幕如何重排。
- 長文字、長數值、長檔名是否溢出。
- 圖表與表格在窄螢幕是否仍可讀。

資料密度要對產品類型調整：

- 工作型 UI：優先掃描、比較、批次操作、穩定布局。
- 行銷 / 內容型 UI：優先敘事、節奏、可讀性。
- 遊戲 / 創意型 UI：優先沉浸、回饋、可操作性。

## 17. Accessibility 底線

完成前至少檢查：

- keyboard 可操作。
- focus visible。
- semantic HTML。
- form label 與 error message 正確。
- name / role / value 正確。
- 不只用顏色表達狀態。
- mobile touch target 足夠。
- 內容可重排，不因小螢幕重疊或被遮住。
- 對 reduced motion 有處理。

WCAG 2.2 是 accessibility 的技術標準參考；本文件只保存 LLM 施工時最小必查項，不取代完整 WCAG 檢查。

## 18. Content Tone / Microcopy

UI 文案要協助使用者完成任務。

原則：

- 用使用者懂的詞，不用內部術語。
- 錯誤訊息要說明發生什麼、影響什麼、下一步怎麼做。
- CTA 寫具體動作，不寫空泛詞。
- 空狀態要說明為什麼沒有資料，以及如何開始。
- 權限不足、資料過期、外部服務失敗要明確標記。

不要在 UI 裡放大段說明「這個功能怎麼用」。如果介面需要長篇教學才可用，優先修正資訊架構。

## 19. Anti-Slop 黑名單

黑名單不是禁止美感，而是禁止無理由套模板。好的設計可以有 gradient、motion、cards、hero，但必須有產品類型、品牌語氣、資訊層級或互動目的支撐。

LLM 預設禁止：

- 無理由 AI purple / blue gradient。
- 深色 mesh hero + centered headline + 三張 feature cards。
- 所有專案都 Inter / slate / rounded-2xl / shadow-xl。
- 裝飾用 orb、bokeh blob、無意義 glassmorphism。
- 沒有資料狀態的 dashboard。
- 沒有 empty / error / loading 的 form、table、chart。
- 未讀現有 components 就新增重複元件。
- 小頁面硬生完整 design system。
- 用漂亮截圖宣稱流程完成，但沒有互動驗證。
- 把 landing page 審美套到 CRM / 後台 / 資料工具。
- 只做靜態 mock，不處理 hover / focus / disabled / validation。

## 20. LLM 輸出格式

設計或實作 UI 時，回報不要只說「完成」。

建議格式：

```text
目前判斷：設計草案 / 本機可跑 / 已接正式流程 / 仍有缺口

Design intent：
- 本次設計目標：
- 不做事項：

UX assumptions：
- 已知使用者：
- 推測使用者：
- 未驗證假設：
- 風險與最小驗證方式：

Design context：
- 沿用來源：
- 抽取 tokens / component vocabulary：
- 具名品牌 / 產品資產：
- 缺失與 fallback：

User flow：
- 入口：
- 主任務：
- 成功路徑：
- 失敗 / 無權限 / 資料缺失：
- 退出 / 取消 / 撤銷：

UI structure：
- 頁面區塊：
- 資訊層級：
- 主要 CTA：

Component plan：
- 沿用元件：
- 新增元件：
- 狀態覆蓋：

設計取捨：
- DESIGN_VARIANCE:
- MOTION_INTENSITY:
- VISUAL_DENSITY:

Tokens used：
- color:
- typography:
- spacing:
- radius:
- shadow:

Accessibility notes：
- keyboard:
- focus:
- label:
- contrast:
- reduced motion:

Evidence：
- preview / screenshot:
- interaction steps:
- viewport:
- browser smoke:

Completion level：
- 設計草案 / 靜態實作 / 本機互動可跑 / 接正式資料 / 已部署：
```

不得只用「完成」、「已優化」、「更現代」、「更漂亮」作為回報。

Completion level 的 UX 用語對應通用完成階梯：設計草案 / 靜態實作 ≈ 文件 / 設計完成，本機互動可跑 ≈ 候選 / 本機通過，接正式資料 ≈ 正式流程接入，已部署 ≈ 部署可用；UX 設計本身通常不涉及「舊依賴可刪」。

## 21. 完成前 Quality Gate

LLM 回報 UX / UI 完成前必須回答：

UX Quality Gate：

- 使用者主任務是什麼？
- 這個頁面是否真的需要存在？
- 最短完成路徑有幾步？
- 使用者在哪些地方可能犯錯？
- 錯誤能否預防、撤銷、重試或修正？
- 新手是否知道第一步要做什麼？
- 熟手是否能快速完成高頻任務？
- 是否使用使用者語言，而非內部技術詞？
- 是否讓使用者知道目前狀態、下一步與結果？
- 是否避免要求使用者記憶上一頁資訊？
- 使用者是否知道目前頁面、結果範圍、返回路徑與下一步？

UI / implementation Quality Gate：

- 主要使用者任務是否一眼可辨識？
- 是否沿用既有 tokens / components？
- 是否已抽取並說明具體 design context，而不是憑印象設計？
- 具名品牌 / 產品是否使用官方或可驗證資產，缺失處是否誠實標記？
- 是否先整理入口、主任務、成功、失敗、退出流程？
- loading / empty / error / success 是否存在？
- 表單錯誤是否有總覽、欄位錯誤、可定位連結與可理解文案？
- 資料型 UI 是否顯示單位、時間範圍、資料來源與 last updated？
- 複雜元件是否處理 keyboard、focus、ARIA 與 mobile touch？
- mobile / desktop 是否都可用？
- keyboard / focus 是否可用？
- 文字是否溢出、重疊或遮擋？
- 表格 / 表單 / dashboard 是否有資料密度策略？
- loading、skeleton、資料更新是否避免整頁等待與 layout shift？
- screenshot / preview 是否避免暴露真實敏感資料？
- 是否有 preview、screenshot 或實際互動證據？
- 本輪完成層級是設計草案、本機可跑、已接正式流程，還是已部署？

若無法完成 visual verification，要明確回報「未跑視覺驗證」與原因，不能把未驗證 UI 說成完成。

## 22. 參考來源吸收定位

| 來源 | 可吸收內容 | 採用邊界 |
| --- | --- | --- |
| Leonxlnx/taste-skill | brief-first、反 AI slop、設計旋鈕、anti-pattern blacklist | 部分採用；偏 landing / polished frontend，不直接取代產品型 UI 規範。 |
| alchaincyf/huashu-design | design context 優先、具名品牌 / 產品資產協議、早展示假設、Playwright 驗證與 5 維評審 | 部分採用；只吸收 context、資產、驗證與 anti-slop 原則，不導入 skill、subagent、PPT/MP4 pipeline 或風格庫。 |
| nexu-io/open-design | `DESIGN.md`、`SKILL.md`、design system / skill 化結構 | 部分採用；只吸收文件分工與 agent 可讀格式。 |
| VoltAgent/awesome-design-md | `DESIGN.md` 章節格式與 AI 可讀設計語言 | 部分採用；不照抄品牌風格。 |
| bergside/awesome-design-skills | `SKILL.md` + `DESIGN.md` 成對管理 | 部分採用；作為工具模板參考。 |
| OpenCoworkAI/open-codesign | preview、局部修改、UI kit、boolean rubric 驗證 | 部分採用；不導入工具本身。 |
| 18F UX Guide | UX research / design work 的 norms、practices 與一致品質起點 | 採用為「LLM 不得假裝知道使用者」依據；該 repo 已 archived / moved，只摘要原則。 |
| 18F Methods | human-centered design 方法卡與方法選擇 | 採用為 UX 方法選擇參考；不把所有任務升級成完整研究流程。 |
| 18F Content Guide | plain language、information accessibility 與 content design | 採用為 Content UX 參考；該 repo 已 archived / moved，只保留文案原則。 |
| NN/g 10 Usability Heuristics | usability 底線：狀態可見、使用者控制、一致性、錯誤預防、辨識優於記憶等 | 採用為 UX 基線。 |
| WCAG 2.2 | accessibility 技術標準與檢查方向 | 採用為 accessibility 底線；本文件不取代完整 WCAG 審查。 |
| W3C WAI Designing for Web Accessibility | 對比、不可只靠顏色、互動元素辨識、清楚 navigation、label、feedback、heading / spacing、不同 viewport | 採用為 accessibility 施工檢查。 |
| GOV.UK Service Standard | 理解使用者需求、解完整問題、簡單可用、所有人可用、定義成功 | 採用為任務流程與服務設計底線。 |
| GOV.UK Design System | styles、components、patterns 與服務型任務流程 | 採用為服務流程 UX 參考；不採 GOV.UK 視覺。 |
| GOV.UK form structure / error summary | question protocol、one thing per page、validation error summary、錯誤連到欄位 | 採用為表單與錯誤處理底線；不要求所有產品使用 GOV.UK 視覺。 |
| USWDS | fast、accessible、mobile-friendly 公共服務 / 工具型網站底線 | 部分採用；補 mobile-first、accessibility-first 與速度優先。 |
| Microsoft Inclusive Design | recognize exclusion、learn from diversity、solve for one extend to many | 採用為 inclusive design 方向。 |
| Radix Primitives | 複雜元件的 ARIA、focus management、keyboard navigation 實作風險 | 採用為「不要用普通 div 假裝完成」依據。 |
| Laws of UX | cognitive load、Hick's Law、Jakob's Law、proximity 等直覺檢查 | 候選輔助；不是正式標準。 |
| Primer Design System | Product UI、Brand UI、Shared Foundations、Accessibility 的分層 | 部分採用；參考 pattern / component / foundation 分工。 |
| Carbon Design System | working code、design tools / resources、human interface guidelines | 部分採用；要求 UX 決策能落到 token、component 與 guideline。 |
| Fluent UI | utilities、React components、Web Components、版本與 migration 文件 | 部分採用；補長期產品 redesign / migration / 既有習慣保護。 |
| Material Web | Material 3 web components 與 accessible web app 基礎 | 部分採用；補語義正確元件與平台一致性。 |
| Primer / Polaris / Atlassian / Carbon / Fluent / Material Web / USWDS | foundations、tokens、components、patterns、accessibility 文件組織 | 部分採用；只參考結構，不照搬品牌風格。 |

## 23. 最後提醒

LLM 設計 UI 的責任不是讓畫面「看起來像 AI 會做的現代網站」，而是讓使用者能在正確狀態下完成正確任務。

如果介面越做越炫，但主要任務更不清楚，停下來。

如果只有靜態畫面，沒有狀態與互動驗證，只能宣稱設計草案，不能宣稱 UI 完成。
