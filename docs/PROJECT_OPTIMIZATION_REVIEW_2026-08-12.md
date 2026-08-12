# Prism 深度優化與產品改進審查

> 日期：2026-08-12
> 審查範圍：`D:/AI/Prism` 全專案
> 性質：唯讀產品／UX／技術架構審查；不包含修正實作
> 版本基線：Prism V2.6.1、Go primary 單一 runtime、React SPA
> 優先級語意：本報告的 P0 表示「現在投入就值得」，不等同線上事故或必須緊急停機。

---

## 1. Executive Summary

### 1.1 結論先行

Prism 已不是原型，而是一個可離線、可攜、具備完整筆記生命週期的成熟個人知識／提示詞工具。現在已能完成筆記 CRUD、全文與附件文字搜尋、分類標籤、圖片與文字附件、版本歷史、變體、閱讀工作區、Prompt Builder、匯入匯出、資料庫還原點、維護診斷、Windows portable 與 Raspberry Pi 部署。Go primary、SQLite、React 與外部 data-dir 的基本架構適合目前「單一使用者、本地優先」定位，不需要換框架、微服務、Redis、訊息佇列或資料庫遷移。

目前最大改善空間不在「再加更多功能」，而在把已完成能力整理成更可信、更少步驟、更符合觸控／鍵盤與資料成長的產品：

1. **資料健康判斷不完整（DATA-01）**：實際 repo DB 有 23 筆外鍵孤兒關聯，但維護頁仍顯示 Healthy。這是本次最明確的可靠性／營運缺口。
2. **390px shell 與主要動作可用性（UX-01、UX-02）**：固定圖示側欄壓縮內容，部分 icon-only 入口沒有可存取名稱；list／compact 檢視又沒有與 grid 等價的筆記動作。
3. **搜尋與批次選取的可信度（SEARCH-01、UX-03）**：後端已知道附件搜尋可能 partial，前端卻丟棄診斷；快速切換搜尋／篩選時請求可被直接略過；批次選取則可能跨篩選殘留，且「全選」其實只選已載入頁。
4. **資料恢復能力的產品表達不完整（OPS-01）**：UI 的 `.db` 備份／restore point 不包含 data-dir 內的上傳與附件；完整 snapshot 只有 script，且備份與還原點管理散落於兩個設定分頁。
5. **資料量增加後的明確痛點（PERF-01、SORT-01）**：筆記列表每筆再查 tags 與 URLs；custom reorder 只提交已載入項目，和 infinite pagination 的全域排序語意衝突。

建議採取 **「先整理既有功能 + 小型可靠性技術債並行」**：先完成 DATA-01、UX-01～03、SEARCH-01，再做 OPS-01、FLOW-01、IA-01、PERF-01、SORT-01。暫不新增 AI、協作、公開分享、通知、遊戲化或新的資料模型。

### 1.2 產品背景判定

| 類別 | 判定 | 證據／說明 |
|---|---|---|
| 已確認 | 本地優先的個人知識庫與 AI 提示詞管理工具 | `README.md`、`README.zh-TW.md`、首頁 welcome note、`HANDOFF.md` |
| 已確認 | Go primary 是唯一產品 runtime | `AGENTS.md`、`HANDOFF.md`、`docs/ARCHITECTURE.md`、`go-shadow/main.go` |
| 已確認 | 無內建認證；預設阻擋 public bind | `/healthz` runtime payload、`go-shadow/system.go`、`DEPLOY-PI.md` |
| 已確認 | Windows portable 與 Pi 是正式交付面 | README、`DEPLOY-PI.md`、desktop shell source、release docs |
| 高信心推斷 | 主要使用者是管理私人資料、prompt 與長文素材的單一知識工作者 | 單一資料庫、無角色模型、主要 journeys、localStorage workspace |
| 未知 | 使用頻率、最常用 view mode、Prompt Builder 使用率、restore 使用率 | Repo 無匿名 analytics 或 usage research |
| 未知 | 商業模式、付費意願、團隊／多人需求 | 文件未定義；不得推定 SaaS、B2B 或消費訂閱 |

### 1.3 成熟度評估

| 維度 | 評估 | 判斷 |
|---|---:|---|
| Core workflow | 4/5 | CRUD、搜尋、閱讀、附件、歷史、匯出均已存在 |
| Product coherence | 3/5 | 能力完整，但跨頁 filter、設定分組、view action parity 尚未收斂 |
| Runtime / deployment | 4/5 | Go 單一 runtime、portable、Pi、backup-before-migrate 已建立 |
| Data reliability | 3/5 | SQLite 本體正常，但 health check 漏掉實際 FK orphan |
| Responsive / accessibility | 2.5/5 | 有 390px layout，但 compact rail 與 icon-only accessible name 有缺口 |
| Test / governance | 4/5 | 382 pytest + Go tests 通過；但 current behavior 與歷史 source-contract 測試比例需重整 |
| Scale readiness（個人資料量 ×10） | 3/5 | SQLite 足夠；list N+1、partial search、reorder scope、workspace prefetch 會先變痛 |

---

## 2. Project / Product Map

### 2.1 技術與交付地圖

| 層 | Current truth |
|---|---|
| Frontend | React 18、TypeScript、Vite、Zustand、React Router、Tailwind、Axios、Marked + DOMPurify |
| Backend | Go 1.26、`net/http` route mux、模組化 handler、embedded SPA |
| Database | SQLite WAL + FTS5，Go migration owner，latest schema v17 |
| State | `frontend/src/stores/appStore.ts` 管理 notes/filter/modal/selection；部分閱讀工作區與 UI 偏好在 localStorage |
| Storage | external data-dir：DB、`static/uploads/`、`docs/attachments/`、config、backups、logs |
| Authentication | 無；localhost 預設，public bind 需明確 opt-in，文件要求 trusted LAN/VPN/proxy auth |
| Deployment | Windows WebView2 portable；Pi `prism-go-primary.service` + Caddy；Go artifact 可嵌入 SPA |
| Logging / analytics | 本地 log 與系統 dashboard；沒有產品使用 analytics／telemetry |
| Tests | 382 pytest cases、Go `main_test.go` + package tests、9 個舊 Playwright e2e cases（未納入主 gate） |
| Build / CI | Windows CI：frontend build、embed dist、pytest、Go test、文件與治理 gate |

### 2.2 Repo 模組地圖

```text
Prism
├─ frontend/src
│  ├─ pages                 Home / Prompt Builder / Settings
│  ├─ components            Layout、Header、Sidebar、FilterStrip、NoteCard
│  │                         NoteEditor、ReadingView、CommandPalette、Settings sections
│  ├─ stores                notes、filter、selection、modal state
│  ├─ hooks                 note form、reading workspace、prompt builder
│  ├─ services              typed API client
│  └─ i18n                  4 語字典
├─ go-shadow
│  ├─ main.go               boot、runtime config、route registration、SQLite owner
│  ├─ notes_*               list/search/write/actions
│  ├─ taxonomy.go           category/tag
│  ├─ attachments/uploads   file lifecycle
│  ├─ import/export         data portability
│  ├─ backups/system        restore、health、logs、runtime info
│  ├─ options.go            Prompt Builder config
│  ├─ migrations.go         v1–v17 + fresh schema
│  └─ desktop_shell_*       Windows WebView2 shell
├─ static/config            prompt / wizard option data
├─ scripts                  build、start、release、Pi、full-data snapshot
├─ tests                    Go runtime、contract、docs/source、release regression
├─ e2e                      legacy Playwright happy-path suite
└─ docs                     current authority、contracts、history、deployment
```

掃描規模：442 個 repo files；`docs/` 154、`tests/` 83、`frontend/` 70、`go-shadow/` 28。Frontend source 有 41 個 TSX 與 20 個 TS；Go 有 25 個 `.go` 檔。`go-shadow/main.go` 註冊 48 個 handler path。

### 2.3 Page / Route 地圖

| Route | Page | 主要能力 | 主要 overlays |
|---|---|---|---|
| `/` | `HomePage` | 搜尋、篩選、saved views、grid/list/compact、無限載入、custom reorder | `NoteEditor`、`ReadingView`、variant modal、command palette |
| `/prompt-builder` | `PromptBuilder` | template、camera/style/negative prompt、wizard、preview、copy、save to library | wizard / option interactions |
| `/settings?tab=...` | `SettingsPage` | 外觀、組織、備份匯入、維護健康、access/system、about | confirm、toast、file picker |

共同 shell 是 `Layout → Sidebar + Header + FilterStrip + Outlet + Footer`。這代表 Home 專屬的分類 filter 也出現在 Prompt Builder 與 Settings；這是 IA-01 的直接來源。

### 2.4 API 地圖

主要 API group：

- Notes：list/detail/create/update/delete、pin/archive、duplicate、variant、reorder、batch delete/tag、history。
- Search：FTS5、remarks、tag、附件 metadata、request-time attachment body scan。
- Taxonomy：categories、tags、merge、reorder、starred tags。
- Media：uploads、URL upload、thumbnails、attachments、image cleanup。
- Portability：JSON/Markdown/DB export、JSON/MD/TXT import。
- Operations：backup/restore point、logs、stats、consistency、FTS integrity、WAL checkpoint、migration status。
- Prompt configuration：prompt options、wizard options、quick templates。

API client 主要集中於 `frontend/src/services/api.ts`，但 Prompt Builder 仍使用 raw `fetch`，形成 FLOW-01 的 contract 重複。

### 2.5 Data flow 與資料生命週期

```text
Local user
  → React page / overlay
  → Zustand or component-local state
  → Axios API client（Prompt Builder 部分 raw fetch）
  → Go route handler
  → SQLite transaction / FTS5 / external data-dir files
  → JSON / file response
  → store refresh、toast、modal、download
```

筆記生命週期：建立筆記 → 寫入分類／tags／URLs → 編輯時產生 history → 可附加文字檔與圖片 → 可產生 variant／加入閱讀工作區 → archive 或 delete → export／backup／restore。資料並非全部在 DB：uploads、文字 attachments、config 與 logs 位於外部 data-dir，因此「DB copy」不等於完整 recovery package。

### 2.6 Feature map

```text
Library
├─ Notes CRUD / preview / reading
├─ Search / filters / saved search views
├─ Categories / tags / starred shortcuts
├─ Attachments / images / source URLs
├─ History / variants / reading workspace
└─ Grid / list / compact / custom order

Prompt tools
├─ Prompt Builder
├─ Quick templates / wizard
└─ Save to note library

Data & system
├─ JSON / Markdown / DB export
├─ JSON / MD / TXT import
├─ Restore points
├─ Consistency / FTS / WAL maintenance
├─ Server info / logs
└─ Full data snapshot script（未在 UI）

Preferences
├─ Theme / color / density / radius / sidebar width
├─ Locale / quick-add category / image save mode
├─ Taxonomy management
└─ Access / about
```

### 2.7 文件描述 vs 目前實作

| 主題 | 文件描述 | 實作觀察 | 判定 |
|---|---|---|---|
| Runtime | Go primary 唯一 runtime | source、tests、啟動結果一致 | 一致 |
| Schema | latest v17、category identity | repo DB 尚為 v16；隔離啟動自動 backup 並升至 v17 | runtime 機制正確；repo DB 是待啟動資料狀態 |
| Migration owner | `docs/SCHEMA.md` 部分段落仍指 `go-shadow/main.go` | definitions 已在 `go-shadow/migrations.go` | 文件 drift（DOC-01） |
| Python | 已移除產品路徑 | current source 無 Flask backend | 一致；歷史文件仍大量提舊路線 |
| Full data backup | deploy docs／script 有 data snapshot | Settings 主要只呈現 DB/JSON/Markdown 與 DB restore point | 產品入口與 recovery mental model 不完整（OPS-01） |
| UI workflows | KWF 已完成 | 功能確實存在 | 完成狀態成立；action parity、mobile shell、流程收尾仍可優化 |

---

## 3. User Journey + UI / UX Review

### 3.1 審查邊界

- **已實際查看**：headed Playwright local preview；desktop viewport 與 390×844；Home grid/list、NoteEditor preview、Settings Appearance/Backup/Maintenance、Prompt Builder。
- **source + runtime 共同確認**：route hierarchy、可存取名稱、view action parity、filter strip、save flow、selection state、loading/error behavior。
- **未做視覺定論**：未以真實手機、Safari、Firefox、Pi browser 或 Windows portable WebView2 判斷字體渲染／GPU／觸控手感。

### 3.2 Journey A：進入產品 → 找到筆記 → 閱讀／編輯

目前流程：進入 `/` → Home 顯示 notes → 搜尋／分類／tag → 點卡片 → `NoteEditor` 的 preview state → 個別 block 可進 edit → Save／Close。

優點：首頁能直接理解「筆記庫」、有 sample welcome note、empty/loading/end-of-list 狀態、桌機搜尋與 390px 搜尋入口都存在；modal 保留 Home context。

改善點：

#### UX-01 — 390px 固定 icon rail 同時損失寬度與語意

- **已實際查看**：390px 左側固定約 64px rail，分類與大量 tag icons 形成獨立長捲動欄；主內容、設定 tabs、表單說明與 control 被壓縮，Settings 的 Language 說明文字出現極窄換行。
- **可存取性證據**：Playwright accessibility snapshot 中 mobile Home、Prompt Builder、Settings、Archive、New 與多個 tag icon button 顯示為無名稱的 `link`／`button`；分類只剩 emoji 名稱。
- **source 證據**：`frontend/src/components/Sidebar.tsx` 在窄寬隱藏文字但保留 rail；`Header.tsx` mobile New 只顯示 icon；`Layout.tsx` 永遠掛 Sidebar。
- **建議**：mobile 改為現有 sidebar content 的 off-canvas drawer，header 提供有 `aria-label` 的 menu；保留 Home、Prompt Builder、Settings 三個高階入口，category/tag 在 drawer 內展開。若暫不做 drawer，至少先為所有 icon-only controls 加 accessible name 與 tooltip。
- **收益**：增加 64px 有效內容寬、減少認知負荷、讓鍵盤／讀屏操作可辨識。
- Impact 5 / Effort 3 / Risk 2 / Confidence 高 / **P0**。

#### UX-02 — 三種 view mode 的動作與選取能力不等價

- **已實際查看**：desktop 與 390px 的 list note row 只呈現內容與日期，沒有 action menu 或 selection starter。
- **source 證據**：`NoteCard.tsx` 的 compact/list branches 沒有 grid branch 的 More actions；grid menu／checkbox 多以 `opacity-0 group-hover:opacity-100` 顯示。right-click 是 list/compact 唯一進入 selection 的隱性途徑。
- **影響**：touch 使用者不能 right-click；keyboard/touch 難以發現 Reading、pin、archive、delete、variant、export、add-to-workspace。view mode 現在改變的不只是密度，也改變功能集合。
- **建議**：抽出共用 `NoteActions` 與 selection affordance；三種 view 都提供可聚焦的 overflow menu。grid 可保留 hover 動效，但 `focus-visible`、touch 與 selection mode 必須可見。
- Impact 4 / Effort 2 / Risk 2 / Confidence 高 / **P0**。

#### UX-04 — Preview 的產品語意仍像 Edit modal

- **已實際查看**：卡片設定為 Preview 開啟時，modal heading 是「Edit note」，標題本身是 textbox，header 同時出現 Save；正文雖是 preview，但仍有「Edit this block」。
- **建議**：先做最小語意修正：preview state 顯示「Preview note」，標題以 read-only heading 呈現，主動按 Edit 後才切入 inputs／Save。結構性方案才是將 primary click 導向 ReadingView。
- **目前建議**：先做最小方案；是否改成 ReadingView 要用 usage feedback 決定。
- Impact 3 / Effort 2 / Risk 2 / Confidence 高 / **P2**。

### 3.3 Journey B：搜尋／篩選 → 判斷結果 → 保存檢視

目前流程：桌機 header 或 mobile Home search → Enter → store fetch → Home list；category/tag 可從 sidebar 或 filter strip 選；可保存 search workspace。

#### SEARCH-01 — 搜尋結果可能過期或不完整，但 UI 沒有可信度訊號

這包含兩個已確認、但同屬「使用者能否相信目前結果」的機制：

1. `appStore.fetchNotes()` 在 `isLoading` 時直接 return；`setSearchQuery`、category、tag、sort 隨即呼叫它。快速連續切換時，最新條件可能沒有對應 request，也沒有 request generation／abort guard。
2. Go `handleNotes` 在 attachment body scan 達到 200 files、5 MiB 或 250ms 時回傳 `search_diagnostics.partial`；`api.getNotes()` 只回 notes/pagination，直接捨棄 diagnostics。

錯誤時 store 只 `console.error` 並清除 loading，Home 沒有明確 retry／error state。這不是單純技術細節，而是「沒有結果」到底代表沒有資料、最新查詢未執行，或附件只掃了一部分，使用者無法分辨。

建議分兩個小提交：

- API types 保留 diagnostics，Home／Command Palette 顯示 non-blocking partial notice。
- 以 request sequence 或 AbortController 確保 latest request wins，並加入 inline retry state。

Impact 5 / Effort 2 / Risk 2 / Confidence 高 / **P0**。

### 3.4 Journey C：選取多筆 → 批次處理／刪除

目前流程：grid hover checkbox 或 context menu → selection header → 可全選、加 tag、archive、delete → dry-run preview → confirm → delete。

#### UX-03 — selection scope 與「全選」語意不安全

- `selectedNoteIds` 是 global store state；search/category/tag/archive/sort 切換都不會清除或重算 selection。
- Header 的「Select all」呼叫 `notes.map(id)`，只涵蓋已載入的 20 筆／目前 infinite-scroll buffer，label 卻沒有說「已載入」。
- 已選筆記切到另一 filter 後可全部不可見，selection header 仍可對隱藏 IDs 執行 destructive action。
- batch delete 已在 `Header` 做 dry-run，`deleteSelectedNotes()` 又做一次相同 preview API round trip（API-01）。

建議：filter/search/archive 變更時明確清除 selection，或把 selection scope 綁定 query signature；文字改成「選取目前已載入的 N 筆」。若要真正全選結果，需由後端接受 filter snapshot，不應假裝 client 已載入全部。刪除 preview 只執行一次並將 token／payload傳入執行層。

Impact 5 / Effort 2 / Risk 2 / Confidence 高 / **P0**。

### 3.5 Journey D：組合 Prompt → 儲存到筆記庫 → 繼續使用

Prompt Builder 本身已具備 template、wizard、camera/style、negative prompt、三種 output 與 copy；390px 實際畫面可用，主要 CTA 清楚。

#### FLOW-01 — Save to library 是死端點，且繞過既有 domain contract

- `usePromptBuilder.saveToLibrary()` raw-fetch categories，再 raw POST notes；validation、copy、success/failure 使用 native `alert()`，與其他頁的 Toast/Confirm 不一致。
- category lookup 依硬編碼 `提示詞 | Prompt` 或名稱包含「提示」；schema v17 已有 `system_key='prompt'`，但此流程沒有使用。
- save success 後不 refresh Zustand notes/categories/tags，也沒有「開啟剛儲存筆記」或「回到 Prompt 分類」CTA。

建議：改用共用 API client 與 typed payload，優先以 `system_key` 找 prompt category；成功 toast 提供「Open note」與「View in library」，並更新／invalidates relevant store。不要新增 service layer，只重用現有 API/store。

Impact 4 / Effort 2 / Risk 2 / Confidence 高 / **P1**。

### 3.6 Journey E：備份／維護 → 判斷健康 → 還原

使用者目前需在 Settings → Backup & Restore 做 exports／restore，在 Settings → Maintenance & Health → Server dashboard 建立／管理 restore points。實際 Maintenance 畫面對一般使用者同時呈現 WAL、FTS、hardware、data-dir、logs、restore points，資訊完整但目的混合。詳細建議見 OPS-01、IA-01、DATA-01。

---

## 4. Information Architecture

### 4.1 目前 IA

```text
Prism
├─ Global shell
│  ├─ Sidebar：All / Prompt Builder / Categories / Archive / Settings / Tags
│  ├─ Header：Search / Sort / View / New
│  └─ FilterStrip：All / Archive / Categories / Starred tags
├─ Home
│  ├─ Search workspace
│  └─ Notes + overlays
├─ Prompt Builder
│  └─ 仍顯示 global FilterStrip
└─ Settings
   ├─ Appearance
   ├─ Organization
   ├─ Backup & Restore：exports / imports / DB restore
   ├─ Maintenance & Health：checks / stats / restore point create / logs
   ├─ Access & System
   └─ About
```

### 4.2 建議 IA

```text
Prism
├─ Library
│  ├─ Search / filters / saved views
│  ├─ Notes（action parity）
│  ├─ Reading / editing / history / variants
│  └─ Categories / tags（desktop sidebar；mobile drawer）
├─ Prompt Studio
│  ├─ Composer / templates / wizard
│  └─ Save → Open in Library
├─ Data & Recovery
│  ├─ Export / import
│  ├─ Full data snapshot
│  ├─ Restore points / restore
│  ├─ Health diagnostics
│  └─ Advanced：WAL / FTS rebuild / logs / restart / raw paths
└─ Preferences
   ├─ Appearance
   ├─ Organization
   ├─ Access
   └─ About
```

#### IA-01 — 讓 navigation 與 filter 依 route 有明確責任

| 動作 | 目前 | 建議 | 收益 | 技術影響 |
|---|---|---|---|---|
| Move / Hide | FilterStrip 在所有 routes | 只在 `/` 顯示；Prompt/Settings 保留最小 header | 少一層無關分類、減少誤跳 Home | `Layout` route-aware conditional |
| Merge | Sidebar 與 FilterStrip 重複 All/Archive/Categories | Sidebar 管 navigation；FilterStrip 管 active library filter shortcuts | 清楚區分「去哪裡」與「怎麼篩」 | 不改 API/schema |
| Merge | DB restore 在 Backup；restore point create/list 在 Maintenance | 全部移到 Data & Recovery | 同一生命週期不跨 tabs | 移動既有 components |
| Hide | WAL、FTS rebuild、logs、restart 與 raw paths 在一般維護頁 | 放入 Advanced，health summary 保留上層 | 新手不必理解 runtime module boundary | conditional disclosure |
| Rename | Prompt Builder | Prompt Studio（可選） | 若未來同頁含 templates/manage，名稱更貼近完整工作流 | 僅文案；目前可暫不改 |
| Promote | Full data snapshot 只有 script | Data & Recovery 清楚提供／指引 | backup mental model 完整 | 見 OPS-01 |

Impact 4 / Effort 2 / Risk 1 / Confidence 高 / **P1**。

不建議拆 Settings 成更多 top-level routes；對單人本地工具，tabs 足夠。重點是合併 recovery workflow 與隱藏低頻 server details，不是建立新的管理後台。

---

## 5. Feature Matrix & Consolidation

### 5.1 主要功能盤點

| 功能 | 類型 | 價值／頻率推定 | 重疊或缺口 | 建議 | Priority |
|---|---|---|---|---|---|
| Notes CRUD | Core | 高／高 | Preview 語意偏 edit | 保留；引用 UX-04 | P2 |
| Search + filters | Core | 高／高 | partial/race feedback 缺口 | 引用 SEARCH-01 | P0 |
| Grid/list/compact | Supporting | 中高／高 | action 不等價 | 引用 UX-02 | P0 |
| Multi-select/batch | Power User | 高／中 | selection scope 不明 | 引用 UX-03、API-01 | P0 |
| Categories/tags/starred | Supporting | 高／高 | sidebar/filter strip 重複 | 引用 IA-01 | P1 |
| Saved search workspace | Power User | 中高／中 | 空狀態永久佔區塊 | 空狀態縮成 secondary CTA；使用後展開 | P2 |
| ReadingView | Supporting | 高／中高 | card primary click 仍進 editor | 保留；先修 preview 語意 | P2 |
| Reading workspace | Power User | 中／未知 | 無上限 prefetch | 引用 PERF-03 | P2 |
| History / variants | Power User | 中高／中 | 入口依 view 不一致 | 經共用 NoteActions promote | P1 |
| Images / text attachments | Supporting | 高／中 | backup recovery 未完整涵蓋 | 引用 OPS-01 | P1 |
| Prompt Builder | Power User / differentiator | 高／未知 | save flow 不收尾 | 引用 FLOW-01 | P1 |
| JSON / Markdown / DB export | Supporting | 高／低中 | DB copy 被誤解為完整資料 | 合併 Data & Recovery | P1 |
| Restore points | Supporting | 高／低 | create/list/restore 分散 | Merge candidate，引用 IA-01/OPS-01 | P1 |
| WAL/FTS/log/server dashboard | Power User / Operations | 中／低 | 一般 UI 暴露過深 | Hide under Advanced | P1 |
| Custom order | Questionable / Power User | 未知／未知 | pagination scope 不成立 | 引用 SORT-01；先限制再決定 | P1 |
| Extensive appearance settings | Nice-to-have | 中／低 | mobile setting layout 擁擠 | 保留；不再增加設定項 | P2 |
| Command palette | Power User | 中高／中 | 搜尋信任問題共享 | 保留；共用 SEARCH-01 contract | P1 |

頻率是根據入口與 workflow 的高信心推定，不是 usage analytics；Prompt Builder、custom order、restore points 的實際使用率未知。

### 5.2 Consolidation actions

| 類型 | 目前流程 → 建議流程 | 使用者收益 | 技術影響 | 對應 ID |
|---|---|---|---|---|
| Merge | Backup tab + Maintenance restore points → Data & Recovery | recovery 不跨頁找控制 | 搬現有 components | OPS-01 / IA-01 |
| Simplify | 三種 view 各自 action → 共用 NoteActions | 換密度不丟能力 | 小型 shared component | UX-02 |
| Simplify | Prompt save → alert → 自行找筆記 → toast + Open/View | 完成後一步到位 | 共用 API/store | FLOW-01 |
| Remove | 不建議現在刪除正式功能 | 缺 usage data，不宜誤刪 | 先觀察 | — |
| Hide | WAL、raw logs、restart、raw data paths → Advanced | 降低一般設定認知成本 | display grouping | IA-01 |
| Hide | Empty saved-search 大區塊 → 小 CTA | 首頁 focus 回到 notes | 純 frontend | IA-01 |
| Promote | Full data snapshot / recovery scope | 降低資料遺失風險 | script/API/UI 整合 | OPS-01 |
| Promote | Reading/history/variant actions 到所有 views | 高價值功能可發現 | 共用 actions | UX-02 |
| Automate | health check 自動跑完整 FK check | 真實反映資料健康 | read-only SQL | DATA-01 |
| Automate | latest request wins / cancel stale | 不需使用者重試猜測 | request lifecycle | SEARCH-01 |

### 5.3 明確不建議

- 不新增全面 Design System；現有 shared Button/IconButton/Confirm/Toast 足以局部收斂。
- 不因 `go-shadow` 名稱不漂亮而搬 repo 或 rewrite runtime。
- 不把 SQLite 換成 server DB；個人本地資料量不是瓶頸。
- 不新增新的 global state framework；Zustand 足夠，應修正 request/selection semantics。
- 不在沒有 usage evidence 前刪除 custom order、Reading Workspace 或 Prompt Builder；先限制錯誤語意並量化使用。

---

## 6. New Feature Opportunities

新功能只列能解決已出現問題的最小能力；其餘構想不進 roadmap。

### 6.1 Evidence-backed opportunity

| 機會 | 實際問題 | 最小 MVP | 是否可只改現有功能 | Impact | Effort | Risk | Confidence | 現在值得？ |
|---|---|---|---|---:|---:|---:|---|---|
| 完整 recovery package | DB restore 不包含 uploads/attachments/config；完整 script 無 UI | 在 Data & Recovery 產生有 manifest 的完整 snapshot，或先提供明確 guided action | 是；優先整合現有 `export_full_data_snapshot.ps1` 與文案 | 5 | 3 | 3 | 高 | 下一輪，OPS-01 |
| FK orphan repair assistant | 已觀察 23 筆 orphan，health 卻 Healthy | read-only detail + backup + dry-run + 明確逐類清理；預設不自動修 | 先補現有 health check 就能取得大部分價值 | 4 | 3 | 3 | 高 | diagnostics 現在做；repair 下一階段 |
| Save-success continuation | Prompt save 後沒有開啟／定位新 note | toast action：Open note / View Prompt category | 完全是既有功能改善 | 4 | 2 | 2 | 高 | 現在做，FLOW-01 |

### 6.2 Product Hypothesis（不列入 P0/P1）

| 構想 | 為何目前證據不足 | MVP／觸發條件 | 判定 |
|---|---|---|---|
| 多人協作／分享 | 無 user/role/auth 模型，定位是個人工具 | 只有確認多人 workflow 與部署邊界後再研究 | Future，現在不做 |
| 內建 AI 生成／摘要 | current authority 明確 no AI/ML dependency；無 API 成本模型 | 使用者研究證明 Prompt Builder 需要 provider 後另案 | Future，現在不做 |
| 通知／streak／gamification | 與知識庫自然 workflow 無證據關聯 | 不設 MVP | 不建議 |
| 雲端同步 | 無衝突解決、帳號、隱私與營運需求證據 | 先確認跨裝置是高頻痛點 | Future |
| 使用 analytics | local-first／privacy positioning；沒有 consent policy | 優先人工 usage study；必要時才設計 opt-in local metrics | Future |

---

## 7. Performance & Technical Improvements

### 7.1 Frontend

#### PERF-02 — 單一 initial JS chunk 已達 Vite warning 門檻

- 隔離 production build：JS 698.58 kB minified / 215.54 kB gzip，CSS 54.44 kB / 10.67 kB gzip；Vite 明確警告 chunk >500 kB。
- `App.tsx` eager import Home、Prompt Builder、Settings；`i18n/index.ts` 約 168 kB source，Settings/Prompt/markdown/editor 能力都進 initial graph。
- 建議最小改善：route-level `React.lazy` 分割 Prompt Builder 與 Settings；不要先做複雜 manualChunks。量測 Home initial chunk 與 route transition，再決定是否拆 locale dictionaries。
- Impact 3 / Effort 2 / Risk 1 / Confidence 高 / **P1**。

#### PERF-03 — Reading Workspace 對所有累積 ID 平行抓 detail

- `useReadingWorkspace` 的 `noteIds` 無上限；`ReadingView` 對 missing IDs 呼叫 `api.getNote()`，並另抓當前附件／variants。
- 現在 repo DB 只有 1 note，無 runtime 痛感；當使用者累積數十至數百 workspace items，開啟 ReadingView 會形成 request burst。
- 建議：只載 active 與鄰近 item；workspace list 用已有 list metadata，切換時才 fetch detail；可加合理上限或清理 unavailable IDs。
- Impact 3 / Effort 2 / Risk 2 / Confidence 高 / **P2**。

不建議現在做 virtualization：Home 每頁 20、infinite load，沒有實際 DOM scale 證據。先修 query 與 request semantics。

### 7.2 Backend

#### PERF-01 — Notes list 的 tags / URLs 是每筆 N+1

- `handleNotes` 先 count、再 page query；每個 row 經 `scanNoteRow()` 分別呼叫 `noteTags(id)` 與 `noteURLs(id)`。
- Home 一頁 20 筆約為 page/count + 40 次關聯查詢；API 上限 100 筆時約 202 次 SQL query，主 SELECT 還包含 variants correlated count。
- 這條路徑被 Home、filters、search、Command Palette 反覆使用。資料量 ×10 後，先變痛的是 page latency 與 DB round trips，而不是 SQLite 本身。
- 建議：先取得 page IDs，再以 1 次 tag join 與 1 次 URL query batch hydrate map；保持 response contract 不變。不要為此 denormalize 或加 cache。
- Impact 4 / Effort 2 / Risk 2 / Confidence 高 / **P1**。

### 7.3 Database

#### DATA-01 — Health check 沒有檢查真正的 FK violations

- repo DB `PRAGMA integrity_check` 回 `ok`，不是檔案損毀。
- `PRAGMA foreign_key_check` 回 23 筆：`Note_Attachments` 7、`Note_History` 14、`Source_Urls` 2；Notes 只有 1 筆。
- current delete path `deleteNotesByID()` 會明確清關聯，SQLite DSN 也啟用 `foreign_keys(1)`；因此這較可能是歷史資料殘留，不能推論 current delete 仍會製造 orphan。
- `handleCheckConsistency()` 只算 orphan `Note_Tags`、unused tags、null category，再讀 `PRAGMA foreign_keys` 是否啟用。它把「FK enforcement 開啟」誤當「現有資料無 FK violation」。
- 實際 Maintenance UI 顯示 Data consistency = Healthy、Foreign keys = Enabled，和同一隔離 DB 的 23 violations 矛盾。
- 建議第一步只修 diagnostics：執行 `PRAGMA foreign_key_check` 或逐關聯 aggregate，health 依實際 violation 分級並顯示 table/count。第二步另案做 backup + dry-run repair；不得在 check 時自動刪除。
- Impact 5 / Effort 2 / Risk 2 / Confidence 高 / **P0**。

#### SORT-01 — Custom reorder 與 infinite pagination 的 scope 衝突

- Home DnD 將目前 `notes` buffer 的 IDs 傳給 `/notes/reorder`；backend 依 array index 寫 `sort_order=0..N-1`，未載入 notes 保留舊值。
- 在超過 20 筆、尚未載完或已套 filter 時，這會產生 sort_order collision／全域語意不明；使用者看到的是 filter subset，API 實作的卻像全域排序。
- Option B 最小改善：只有 `sort=custom`、無 filter/search 且全部載入時允許 reorder；否則 disabled 並解釋原因。
- Option C 結構性改善：API 改成 move semantics（moved ID + before/after ID）並使用穩定 rank；只有確認 custom order 是高頻核心後才值得。
- Impact 4 / Effort 2（B）或 4（C）/ Risk 2 或 3 / Confidence 高 / **P1（先 B）**。

SQLite、FTS5、WAL 與 schema normalization 對目前產品足夠；不要換 DB。attachment body scan 的 bounded design 合理，真正缺口是 UI 沒顯示 partial diagnostics（SEARCH-01）。

### 7.4 API

#### API-01 — 小型 contract 重複與不必要 round trip

- batch delete preview 在 Header 與 store 各呼叫一次。
- `NotePayload` 同時服務 create/update，但 update runtime 要求 title/content；型別沒有表達差異。
- Prompt Builder 繞過共用 client，以 raw fetch + `any` 重複 notes/categories contract。

建議隨 UX-03/FLOW-01 局部修：preview result 單一路徑、拆 `CreateNoteInput`/`UpdateNoteInput`、Prompt Builder 使用現有 API client。不要引入 codegen 或全專案 schema framework。

Impact 3 / Effort 2 / Risk 1 / Confidence 高 / **P2**。

### 7.5 Deployment / build

- Go artifact、external data-dir、backup-before-migrate、public-bind guard、Windows/Pi 流程都有明確 contract，沒有證據支持重做 deployment。
- `scripts/build_go_runtime.ps1` 會 build frontend、同步 embed dist、跑 tests；CI 與 release docs 已對齊。
- `scripts/start_go_primary.ps1` 仍需傳多個歷史 candidate enable flags；desktop mode 則強制全開。這增加啟動參數與測試矩陣，但目前沒有 runtime failure 證據，列 TECH-02/P3，不應先於使用者問題處理。
- 完整資料 snapshot script 存在，但不是 app recovery workflow；這是 OPS-01，不是 deployment rewrite 理由。

---

## 8. Maintainability / Scalability / Operations

### 8.1 現在就值得處理

#### OPS-01 — 將「DB 備份」與「完整可恢復資料」分清楚

- Settings 的 Download database copy 文案稱「full SQLite .db」，restore points 也只管理 DB；`DEPLOY-PI.md` 明確說 DB backup 不含 uploads/attachments。
- 實際 data flow 顯示 attachments/uploads/config 在 DB 外；`scripts/export_full_data_snapshot.ps1` 才會打包 DB/WAL/SHM、uploads、attachments、notes、config 與 manifest。
- Backup & Restore 只做 restore；create/list/download restore point 又在 Maintenance Server dashboard，mental model 被 module boundary 拆開。

建議兩階段：

1. **最小改善**：所有 DB copy／restore point 文案明確寫「只包含資料庫，不包含上傳圖片、文字附件與 config」；在同一 Data & Recovery 區顯示完整備份指引與 data-folder action。
2. **結構性改善**：把現有 full snapshot 能力做成可驗證、含 manifest 的本地操作；restore 先維持手動 runbook，避免一開始就自動覆寫全 data-dir。

Impact 5 / Effort 2（階段 1）～4（階段 2）/ Risk 2～4 / Confidence 高 / **P1**。

#### TECH-01 — 讓 test portfolio 回到 current behavior，而非無限保留歷史施工 contract

- 本次主 suite 382 passed，但耗時 482.92 秒；73 個 pytest modules 都被 broad source/file-contract grep 命中。這不代表它們全是 static tests：不少也會 build/啟動 Go runtime；但 phase19～24、Txxx、docs wording/source substring assertions 佔明顯維護面。
- `e2e/` 另有 9 個 Playwright cases，仍寫 Flask/localhost:5000 前置，部分 action 以 `if count > 0` 跳過 assertion；它不在 `.loop/verify-gate.ps1` 主 gate。
- `go-shadow/main_test.go` 約 4,049 行；current TODO 已把 test-only split 列低優先 candidate。

建議先建立 test inventory：Behavior / Contract / Governance / Historical。保留真正的 HTTP/DB/release safety；將已完成 phase 的固定文字 assertions 歸檔或合併為少數 current-truth tests；把 3～5 條 current browser smoke 納入可選 gate。不要一次 rewrite 382 tests。

Impact 4 / Effort 3 / Risk 3 / Confidence 高 / **P1**。

### 8.2 到一定規模再處理

- **PERF-03**：Reading Workspace 到數十 items 才會明顯 burst；現在先 lazy detail 已足夠。
- 大型 tag 清單可考慮搜尋／虛擬化，但目前只有 44 tags，沒有 runtime bottleneck 證據。
- Attachment search 若經常 partial，再考慮預先建立附件文字 index；現在先 surface diagnostics，不要先新增索引表／migration。
- Full-data automatic restore 需先有 snapshot format compatibility、rollback 與 manual acceptance；先提供 export，不急著自動覆寫。

### 8.3 Future Consideration

#### DOC-01 — current docs 與 history 邊界仍可再縮

`docs/ARCHITECTURE.md` 前段 current truth 清楚，但保留大量早期 phase 流程；`docs/SCHEMA.md` 有 stale `main.go` migration owner；`DEPLOY-PI.md` 仍有 T053 future wording。這會增加新維護者辨識成本，但不影響 runtime。建議下一次 docs-only maintenance 修正 current pointer，將長歷史移至 `docs/development-history/`。

Impact 3 / Effort 2 / Risk 1 / Confidence 高 / **P2**。

#### TECH-02 — 移除歷史 candidate flags / `go-shadow` 命名

Go primary 已正式化，但 13 個 capability flags、`api_surface` 長字串與 `go-shadow` module/folder 命名仍保留迁移痕跡。現在改名會擴散 scripts、CI、docs、contracts，收益小於風險。只有當下一輪需要新增 runtime mode 或 flags 已造成實際誤配時，再以 separate contract 做收斂。

Impact 2 / Effort 4 / Risk 4 / Confidence 高 / **P3：暫不處理**。

### 8.4 不需要處理

- **Authentication**：本地／trusted-network 工具目前無需內建帳號系統；若公開上網，應先由 reverse proxy auth 保護，而不是臨時加 app login。
- **Database engine**：SQLite + WAL + FTS5 足夠；先修 query pattern 與 health semantics。
- **Microservices / queue / Redis / Kubernetes**：沒有 current cost 或 reliability evidence。
- **Global state rewrite**：Zustand 問題是局部 request/selection lifecycle，不是 framework 限制。
- **AI provider abstraction**：目前產品刻意無 AI runtime，不需為未知未來建立 adapter。

### 8.5 使用者 ×10、資料量 ×10、功能 ×2

| 變化 | 最先變痛 | 現有跡象 | 延後成本 | 分類 |
|---|---|---|---|---|
| Notes ×10 | PERF-01 list N+1 | 每頁已固定 2 queries/note | 越多 consumer 越難改 | 現在修 |
| Attachments ×10 | SEARCH-01 partial scan | backend 已設 limits/diagnostics | 使用者先失去搜尋信任 | 現在修 UI；索引晚點 |
| Loaded pages ×10 | SORT-01 | reorder 只送 buffer | 排序 collision 更難清 | 現在限制 scope |
| Workspace items ×10 | PERF-03 | 無 cap、平行 detail fetch | request burst | 到規模再完整優化 |
| Features ×2 | IA-01 / TECH-01 | global shell、歷史 contract 已密 | navigation/test 成本擴大 | 現在先收斂 |
| Users ×10（仍各自本地） | 無共享 backend bottleneck | 每人獨立 runtime | 幾乎線性分散 | 不需處理 |

### 8.6 Business / Operations

目前不需要商業化／營運設計。Repo 無商業模式、付費或多人服務證據；產品也沒有外部 AI/API 成本。

- **Activation**：welcome note、清楚 New CTA、Prompt templates 已足夠；應先修 mobile navigation 與 preview semantics，不需增加 onboarding wizard。
- **Retention**：history、saved search、favorites/pin、reading workspace、reusable prompt config 已提供自然回訪理由；不需通知、streak 或 points。
- **現在需要的 operations**：真實 consistency health、完整 recovery mental model、restore/export 驗證、local logs。
- **未來才可能需要**：error telemetry、admin、moderation、billing、rate limit；只有成為 hosted/multi-user 產品才成立。

### 8.7 大型改善方案比較

| 候選 | Option A 保持現狀 | Option B 最小改善 | Option C 結構性改善 | 建議 |
|---|---|---|---|---|
| Mobile shell | 零成本；持續壓縮與無名稱 icons | 補 aria/tooltip、縮短 tag rail | off-canvas drawer、route-focused header | 直接做 C，但重用 Sidebar content，不重寫 navigation |
| Recovery | 現有 DB restore 穩定；完整性易誤解 | 明確 DB-only + 整合同頁 + full snapshot 指引 | app 內產生／驗證完整 snapshot + restore workflow | 現在 B，下一階段 C export；automatic restore 暫緩 |
| List N+1 | 實作簡單；隨 page size 成本線性 | page IDs 後 batch tags/URLs | JSON aggregate / denormalize / cache | B；C 沒必要 |
| Custom order | 目前小資料看不痛 | 只允許 unfiltered + fully-loaded reorder | stable rank + move API | B；用量證明後才 C |
| Tests | 高覆蓋敘事但 gate 慢／歷史耦合 | 分類、合併歷史 assertions、補 current smoke | 全面重寫 suite | B；禁止 C big-bang |
| Global filter strip | controls 隨處可見；跨頁干擾 | 只在 Home render | 重做整個 shell/IA framework | B；不需大改 |

---

## 9. Highest ROI + Product Evolution Roadmap

詳細問題只在前述首次出現處完整說明；此處只引用 Evidence ID。

### 9.1 Top 10 Highest ROI Improvements

| Rank | ID | 改善名稱 | Impact | Effort | Risk | Confidence | Priority |
|---:|---|---|---:|---:|---:|---|---|
| 1 | DATA-01 | 以實際 FK violations 重做資料健康判定 | 5 | 2 | 2 | 高 | P0 |
| 2 | UX-01 | 390px drawer + icon accessible names | 5 | 3 | 2 | 高 | P0 |
| 3 | UX-03 | selection scope 與 loaded-only 全選語意 | 5 | 2 | 2 | 高 | P0 |
| 4 | SEARCH-01 | latest-request-wins + partial search feedback | 5 | 2 | 2 | 高 | P0 |
| 5 | UX-02 | 三種 view 的 action / selection parity | 4 | 2 | 2 | 高 | P0 |
| 6 | OPS-01 | DB-only 文案與完整 recovery workflow | 5 | 2～4 | 2～4 | 高 | P1 |
| 7 | PERF-01 | batch hydrate note tags / URLs | 4 | 2 | 2 | 高 | P1 |
| 8 | FLOW-01 | Prompt save 後可直接開啟／定位筆記 | 4 | 2 | 2 | 高 | P1 |
| 9 | IA-01 | route-aware filter + Data & Recovery 合併 | 4 | 2 | 1 | 高 | P1 |
| 10 | SORT-01 | 限制 partial custom reorder scope | 4 | 2 | 2 | 高 | P1 |

### 9.2 Roadmap

#### 現在（P0）

1. DATA-01：讓 Maintenance 不再誤報 Healthy。
2. UX-01：修 mobile shell 與 accessible names。
3. UX-02：補 list/compact actions。
4. UX-03：清楚定義 selection scope。
5. SEARCH-01：保證 latest search 並顯示 partial/error。

#### 下一階段（P1）

1. OPS-01：先文案／IA，後完整 snapshot export。
2. IA-01：Home-only FilterStrip、合併 recovery controls、advanced disclosure。
3. FLOW-01：Prompt save continuation。
4. PERF-01：batch tags/URLs。
5. SORT-01：限制 reorder，先不重做 rank。
6. PERF-02：route-level lazy loading。
7. TECH-01：test inventory 與 current browser smoke。

#### 有價值但可晚點（P2）

- UX-04、PERF-03、API-01、DOC-01。

#### 暫不建議（P3）

- TECH-02；全面 design system；換 framework／DB；新增 hosted infrastructure。

#### Future

- Collaboration、cloud sync、AI provider、analytics、monetization；需先有 persona／usage／business evidence。

---

## 10. 可直接交給 LLM 的後續任務

以下都只是任務規格，不在本次執行。

### Task PRISM-OPT-01

- **對應改善**：DATA-01
- **目標**：讓 `/api/system/check-consistency` 回報所有 FK violations，UI 不得把「foreign_keys enabled」等同「資料一致」。
- **原因**：同一份 DB 實際有 23 violations，但 UI 顯示 Healthy。
- **修改範圍**：`go-shadow/system.go`、API response type、`SystemMaintenance.tsx`、i18n、targeted tests。
- **不要修改**：schema、migration、正式 DB、任何自動刪除／修復行為。
- **UX / behavior specification**：顯示 violation total 與 table-level counts；0 才能 Healthy；check 永遠 read-only。
- **驗收條件**：fixture 含 orphan attachment/history/URL 時為 warning/critical；健康 fixture 維持 Healthy。
- **檢查指令**：`go test ./...`、`pytest tests/ -v`、`cd frontend && npm run build`。

### Task PRISM-OPT-02

- **對應改善**：UX-01
- **目標**：390px 使用 drawer 取代永久 icon rail，補齊所有 icon-only accessible names。
- **原因**：實際 390px 畫面被 rail 壓縮，accessibility snapshot 有多個 unnamed controls。
- **修改範圍**：`Layout.tsx`、`Sidebar.tsx`、`Header.tsx`、shared icon button、i18n、responsive tests。
- **不要修改**：desktop sidebar behavior、routes、taxonomy API、theme system。
- **UX / behavior specification**：mobile header 有具名 menu；drawer 開啟後可選 Home/Prompt/Settings/category/tag，選擇後關閉；focus trap/ESC/return focus 正常。
- **驗收條件**：390px 無永久 rail；主要 controls accessible name 非空；desktop regression 無差異。
- **檢查指令**：`npm run build`、targeted tests、Playwright 390px + desktop smoke、`pytest tests/ -v`。

### Task PRISM-OPT-03

- **對應改善**：UX-02
- **目標**：grid/list/compact 共用 NoteActions 與 selection affordance。
- **原因**：切換密度會遺失 actions，touch/keyboard 不可發現。
- **修改範圍**：`NoteCard.tsx` 與最小 shared component、i18n/tests。
- **不要修改**：各 view 的 visual density、backend API、delete semantics。
- **UX / behavior specification**：三種 view 都有可聚焦 overflow menu；selection starter 在 touch/focus/selection mode 可見。
- **驗收條件**：Reading/pin/archive/delete/variant/export/workspace action parity；Tab 可達；mobile 可操作。
- **檢查指令**：`npm run build`、component/source regression、Playwright desktop + 390px。

### Task PRISM-OPT-04

- **對應改善**：UX-03、API-01
- **目標**：定義 selection query scope，消除 hidden selection 與重複 delete preview。
- **原因**：filter 變更不清 selection；全選只選已載入；preview API 呼叫兩次。
- **修改範圍**：`appStore.ts`、`Header.tsx`、API client、tests/i18n。
- **不要修改**：batch delete backend semantics、media cleanup contract。
- **UX / behavior specification**：filter/search/archive/sort 變更後 selection 清除；label 顯示「已載入 N 筆」；confirm 使用唯一 preview。
- **驗收條件**：不可刪除當前畫面不可見的舊 selection；network trace 只有一次 dry-run。
- **檢查指令**：`npm run build`、targeted pytest/frontend tests、browser smoke。

### Task PRISM-OPT-05

- **對應改善**：SEARCH-01（diagnostics）
- **目標**：保留 backend `search_diagnostics` 並在 Home/Command Palette 顯示 partial notice。
- **原因**：附件 body scan 有明確上限，client 現在捨棄 diagnostics。
- **修改範圍**：`api.ts` types、Home/CommandPalette、i18n、tests。
- **不要修改**：search algorithm、limits、schema、FTS。
- **UX / behavior specification**：結果仍可用；partial 時顯示已掃描數量與「部分附件內容未掃描」，可重新縮小關鍵字。
- **驗收條件**：partial payload 可見；非 partial 不增加 UI 噪音。
- **檢查指令**：`go test ./...`、`npm run build`、targeted search tests、`pytest tests/ -v`。

### Task PRISM-OPT-06

- **對應改善**：SEARCH-01（request lifecycle）
- **目標**：latest search/filter request wins，加入 inline error/retry。
- **原因**：`isLoading` early return 會略過最新條件。
- **修改範圍**：`appStore.ts`、Home loading/error state、API request cancellation 或 sequence guard、tests。
- **不要修改**：Zustand framework、API routes、pagination size。
- **UX / behavior specification**：快速連續輸入／切 filter 時只呈現最新條件；error 不覆蓋舊結果但清楚可 retry。
- **驗收條件**：out-of-order response test；最新 query 必定有 request 或結果；沒有永久 loading。
- **檢查指令**：`npm run build`、store tests、browser throttling smoke、`pytest tests/ -v`。

### Task PRISM-OPT-07

- **對應改善**：OPS-01、IA-01（最小階段）
- **目標**：合併 restore point workflow，明確標示 DB-only recovery scope。
- **原因**：現有文案可能讓使用者誤以為 uploads/attachments 已包含，controls 又跨兩 tabs。
- **修改範圍**：Settings Backup/Maintenance grouping、i18n、相關 docs/tests。
- **不要修改**：backup file format、restore backend、data-dir、deployment。
- **UX / behavior specification**：Data & Recovery 同頁含 export/import/create/list/restore；DB copy 每個入口都列出不包含項目；server logs/WAL 進 Advanced。
- **驗收條件**：不跨 tab 可完成 restore point lifecycle；沒有把 DB-only 稱為完整資料備份。
- **檢查指令**：`npm run build`、targeted settings tests、desktop/390px smoke、`git diff --check`。

### Task PRISM-OPT-08

- **對應改善**：OPS-01（完整 snapshot）
- **目標**：把現有 full-data snapshot 做成可從 app 安全觸發或清楚導引的 export。
- **原因**：真正完整資料跨 DB、uploads、attachments、config。
- **修改範圍**：先寫 contract；選擇重用 script 或新增 localhost-only streaming endpoint；manifest/verifier/tests。
- **不要修改**：自動 full restore、schema、remote/cloud upload、production data。
- **UX / behavior specification**：顯示內容、大小、產生時間、manifest；失敗不留下看似成功的 package。
- **驗收條件**：隔離 data-dir snapshot 可驗證且含所有宣稱項；DB snapshot 使用安全 checkpoint/copy 流程。
- **檢查指令**：contract-specific tests、`go test ./...`、`pytest tests/ -v`、manual isolated restore-read verification。

### Task PRISM-OPT-09

- **對應改善**：FLOW-01、API-01
- **目標**：Prompt Builder save 使用共用 API/types，以 `system_key='prompt'` 定位分類並提供 continuation CTA。
- **原因**：raw fetch、hardcoded display name、native alert 與 save dead end。
- **修改範圍**：`usePromptBuilder.ts`、`api.ts`、store refresh、Toast、i18n/tests。
- **不要修改**：prompt generation rules、option JSON、schema、AI provider。
- **UX / behavior specification**：success toast 有 Open note / View in Library；找不到 system category 時提供明確 recoverable error。
- **驗收條件**：改語系／改 category display name 仍能儲存；Home 不需 reload 就看得到新 note。
- **檢查指令**：`npm run build`、Prompt Builder tests、isolated browser save flow、`pytest tests/ -v`。

### Task PRISM-OPT-10

- **對應改善**：IA-01
- **目標**：FilterStrip 只在 Library route 顯示，縮小 empty saved-view surface。
- **原因**：Settings/Prompt Builder 目前仍顯示 Home filters，增加認知與垂直空間成本。
- **修改範圍**：`Layout.tsx`、`FilterStrip.tsx`、Home saved view empty state、tests。
- **不要修改**：filter state/API、desktop sidebar、saved search data format。
- **UX / behavior specification**：非 Home route 不顯示 category filters；empty saved view 是 secondary CTA，已有 views 才展開管理區。
- **驗收條件**：route navigation 不殘留多餘 strip；Home filters 不退化。
- **檢查指令**：`npm run build`、route tests、desktop/390px screenshots。

### Task PRISM-OPT-11

- **對應改善**：PERF-01
- **目標**：筆記 page list 以 batch queries hydrate tags/URLs。
- **原因**：目前每 note 兩次 SQL query。
- **修改範圍**：`go-shadow/notes_search.go` 與 targeted tests/benchmark query counter。
- **不要修改**：response JSON、schema、pagination、cache layer。
- **UX / behavior specification**：無 UI change；排序、tags、URLs 完全相容。
- **驗收條件**：100-note page 的關聯查詢固定為 O(1) batches，不是 200；contract tests 通過。
- **檢查指令**：`go test ./...`、`pytest tests/ -v`、isolated 100-note timing/query test。

### Task PRISM-OPT-12

- **對應改善**：SORT-01
- **目標**：在 partial/filtered list 禁用 custom reorder，清楚說明 scope。
- **原因**：目前 client buffer reorder 會和未載入 notes 產生全域排序衝突。
- **修改範圍**：Home DnD enable condition、empty/help copy、tests。
- **不要修改**：schema、rank algorithm、reorder API。
- **UX / behavior specification**：只有 custom sort + unfiltered + all loaded 才能 drag；其他情況顯示簡短原因。
- **驗收條件**：20+ notes 未載完時不送 reorder request；fully loaded 時保持現況。
- **檢查指令**：`npm run build`、Home reorder tests、isolated browser smoke。

### Task PRISM-OPT-13

- **對應改善**：PERF-02
- **目標**：route-level lazy load Prompt Builder 與 Settings。
- **原因**：initial JS 698.58 kB，Vite chunk warning。
- **修改範圍**：`App.tsx`、route fallback、bundle measurement test/note。
- **不要修改**：router framework、manual vendor chunk、locale architecture（本 task）。
- **UX / behavior specification**：route transition 有現有風格的輕量 fallback；錯誤可恢復。
- **驗收條件**：Home initial JS 明顯下降；三 routes direct-load 正常。
- **檢查指令**：`npx tsc --noEmit`、`npm run build`、比較 bundle sizes、route browser smoke。

### Task PRISM-OPT-14

- **對應改善**：TECH-01
- **目標**：產生 test inventory，合併低價值歷史 wording assertions，更新 current browser smoke。
- **原因**：382-case gate 8 分鐘，歷史 phase/source contracts 維護面大，e2e 前置已 stale。
- **修改範圍**：tests/e2e 與 test governance docs；先 inventory，再小批移動。
- **不要修改**：runtime、產品功能、一次刪大量 safety tests、降低 migration/release coverage。
- **UX / behavior specification**：至少 Home load/search/open、Prompt render、Settings backup 三條 current smoke；全部使用隔離 temp DB/data-dir。
- **驗收條件**：每個移除／合併 test 有 replacement 或明確 historical rationale；主 gate 不依賴正式資料。
- **檢查指令**：`pytest tests/ -v`、`go test ./...`、更新後 browser smoke、`git diff --check`。

---

## 11. 本次 Review 限制

### 11.1 Observed Fact

- 實際啟動的是隔離 DB copy + temp data-dir + Go runtime + Vite，非 Windows portable WebView2，也非 Pi deployed instance。
- 實際看過 desktop 與 390×844；未看真實 iOS/Android、Safari、Firefox、觸控手勢與螢幕閱讀器實機。
- repo DB 只有 1 note、5 categories、44 tags；無法用它代表大量真實使用資料。
- build/test 都在本機 Windows 2026-08-12 執行；沒有 production load test。
- Prompt Builder 第一次在 temp data-dir 啟動時因未複製兩個 config JSON 而 404；複製 repo 的 `static/config/prompt_options.json` 與 `wizard_options.json` 到 temp 後 Retry 成功並完成 UI 審查。這是審查 setup artifact，不列為產品缺陷。

### 11.2 Inference

- 使用頻率與 persona 是由 route、UI、資料模型與文件推定，沒有 usage analytics 支持。
- DATA-01 的 23 orphan 很可能是歷史路徑殘留，因 current delete code 會清相關表且 FK 已開啟；未以 git history 精確重建產生時間，不能斷言成因。
- PERF-01、PERF-03、SORT-01 的未來痛感根據確定的 query/request/order semantics 推估；未做大資料 benchmark，因此沒有宣稱特定毫秒門檻。

### 11.3 Product Hypothesis

- 多人、雲同步、AI provider、商業化需求皆未知；相關構想不進 P0/P1。

### 11.4 未執行／無法完整驗證

| 檢查 | 狀態 | 原因／影響 |
|---|---|---|
| `npm run lint` | 未執行 | `frontend/package.json` 沒有 lint script；無 lint 結果可宣稱 |
| `pytest e2e/` | 未執行 | suite hardcode `localhost:5000`、註解仍要求 Flask，且含 create write flow；本次改用隔離手動 Playwright inspection，不把舊 e2e 當 current evidence |
| Windows portable package smoke | 未執行 | 避免啟動正式 user data / desktop shell；本次只查 source、tests、docs |
| Pi deployed UI / service | 未執行 | 未連線外部 Pi；deployment 評估來自 current runbook/contracts/source |
| Production DB repair / restore | 禁止且未執行 | 本次唯讀；只查 copy 與 read-only PRAGMA |
| Load / stress benchmark | 未執行 | repo sample 太小；效能結論限於 query/request structure 與 bundle measurement |

---

## 12. Appendix

### 12.1 掃描過的主要目錄

`frontend/`、`go-shadow/`、`docs/`、`tests/`、`e2e/`、`scripts/`、`static/`、`.github/workflows/`、`.loop/`、root release/deploy/config manifests。

### 12.2 深度閱讀的主要文件／source

- 治理／current truth：`AGENTS.md`、`HANDOFF.md`、`docs/README.md`、`docs/GOVERNANCE.md`、`docs/TODO.md`、`docs/ARCHITECTURE.md`、`docs/SCHEMA.md`、`docs/API_REFERENCE.md`、`DEPLOY-PI.md`、README 雙語、`docs/FRONTEND-REDESIGN-PLAN.md`。
- Frontend：`App.tsx`、`Layout.tsx`、`Sidebar.tsx`、`Header.tsx`、`FilterStrip.tsx`、`HomePage.tsx`、`NoteCard.tsx`、`NoteEditor.tsx`、`ReadingView.tsx`、`PromptBuilder` page/hook、`SettingsPage.tsx` 與主要 settings sections、`appStore.ts`、`api.ts`、i18n/build config。
- Backend：`main.go`、`migrations.go`、`notes_search.go`、`notes_write.go`、`notes_actions.go`、`attachments.go`、`options.go`、`system.go`、backup/import/export/deploy scripts。
- Tests：`tests/conftest.py`、Go acceptance/runtime/source-contract tests、reading/search/delete/project hygiene tests、`e2e/`、`.loop/verify-gate.ps1`。

### 12.3 執行指令與結果摘要

| 指令／檢查 | 結果 |
|---|---|
| `git status --short --branch`（開始） | clean，`main...origin/main` |
| `rg --files` + extension/module inventory | 442 files；完成目錄／route／component／test mapping |
| `go test ./...`（`go-shadow`） | PASS；package output 11.645s |
| `npx tsc --noEmit`（frontend） | PASS |
| `npx vite build --outDir <temp>` | PASS；JS 698.58 kB / gzip 215.54 kB；chunk warning |
| `python -m pytest tests/ -q` | 382 passed in 482.92s |
| `sqlite3 -readonly knowledge.db` integrity | `integrity_check=ok`；schema v16；23 FK violations |
| 隔離 Go startup | copy 自動 backup + v16→v17；`/healthz` 200；migration applied 1 |
| `/api/system/check-consistency` | 回 `health=healthy`、`orphan_note_tags=0`、`fk_enabled=true`；未呈現 23 FK violations |
| Original DB SHA-256 before/after | 均為 `CC8BFD2D3AED5E977708F431A8226A634F9F6C97360F79E9FA67E0AEC0DFF536` |
| Playwright headed inspection | Home、list、editor preview、Settings、Backup、Maintenance、Prompt Builder；desktop + 390px |
| Source TODO/FIXME/HACK scan | product source 僅 1 個 Settings hidden-section 註解，未見大量未收斂 markers |

隔離 runtime、Vite 與 browser 已停止。Vite dev 曾自動更新 tracked `.vite/deps` cache，本次已精確還原；未保留該副作用。

### 12.4 Evidence ID 對照

| ID | 名稱 | 首次完整說明 | 關鍵證據位置 |
|---|---|---|---|
| UX-01 | Mobile shell / accessible names | §3.2 | `Sidebar.tsx`、`Header.tsx`、390px Playwright snapshot |
| UX-02 | View action parity | §3.2 | `NoteCard.tsx` compact/list/grid branches、desktop/390px list |
| UX-03 | Selection scope | §3.4 | `appStore.ts`、`Header.tsx` |
| UX-04 | Preview vs Edit semantics | §3.2 | NoteEditor runtime snapshot、Appearance card-open setting |
| SEARCH-01 | Search request + partial diagnostics | §3.3 | `appStore.ts`、`api.ts`、`notes_search.go` |
| FLOW-01 | Prompt save continuation | §3.5 | `usePromptBuilder.ts`、Prompt runtime |
| IA-01 | Route-aware IA / recovery grouping | §4.2 | `Layout.tsx`、Settings tabs/runtime |
| DATA-01 | FK health truth | §7.3 | readonly PRAGMA、`system.go`、Maintenance runtime |
| SORT-01 | Partial custom reorder | §7.3 | `HomePage.tsx`、`notes_actions.go` |
| PERF-01 | Notes list N+1 | §7.2 | `notes_search.go: handleNotes/scanNoteRow/noteTags/noteURLs` |
| PERF-02 | Initial JS chunk | §7.1 | temp Vite production build、`App.tsx` |
| PERF-03 | Reading workspace prefetch | §7.1 | `ReadingView.tsx`、`useReadingWorkspace.ts` |
| API-01 | Duplicate contracts/round trip | §7.4 | `Header.tsx`、`appStore.ts`、`api.ts`、Prompt hook |
| OPS-01 | Complete recovery model | §8.1 | Backup/Maintenance runtime、`DEPLOY-PI.md`、snapshot script |
| TECH-01 | Test portfolio | §8.1 | pytest result、tests inventory、e2e、loop gate |
| DOC-01 | Current docs drift | §8.3 | SCHEMA/ARCHITECTURE/DEPLOY docs vs source |
| TECH-02 | Historical flags/naming | §8.3 | `main.go` flags、start scripts、module name |

### 12.5 Review 完成邊界

本報告只新增此文件；沒有修改 source、config、database、既有 docs 或 assets，也沒有執行任何 repair、migration on production data、deploy、commit 或 push。
