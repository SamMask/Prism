# Prism 產品深度優化、功能整合、技術成本與改版方向審查

> 日期：2026-10-06
> 基線：`main` @ `5e8381f`（V2.6.1、Go primary 單一 runtime、schema v17）
> 性質：唯讀審查。本次只新增本文件；未修改 source、config、database、schema、asset、既有文件、deployment 或 production data。所有 runtime 實測都在 scratch 目錄中的隔離 data-dir 與 fresh DB 上進行，未讀寫 `knowledge.db`。
> 前次審查：`docs/PROJECT_OPTIMIZATION_REVIEW_2026-08-12.md`，其 P0/P1（`PRISM-OPT-01`～`14`）已於 `d6115e1` 完成。本報告不重複已完成項，只追蹤其殘項與本次新發現。
> ID 規則：本報告的 `UX / IA / FEAT / PERF / TECH / OPS / BIZ / REVAMP` 編號與 08-12 報告各自獨立；引用舊報告時寫作 `R0812:UX-04`。
> 優先級：**P0** 現在投入就值得（不等於線上事故）；**P1** 下一輪應做；**P2** 有價值、可稍後；**P3** 目前不建議；**Future** 證據不足。

### 證據與可信度標記

| 標記 | 意義 |
|---|---|
| 【RT】 | Runtime Observed：以 HEAD 建置的隔離 Go runtime（fresh DB、合成資料）＋內建 Chromium browser（desktop 1440×900、mobile 375×812）或 HTTP API 實測 |
| 【SRC】 | 原始碼證據（`file:line`） |
| 【CMD】 | 指令輸出（test / build / benchmark） |
| 【DOC】 | 文件證據 |
| 【AGT】 | 唯讀 subagent 盤點；本報告引用前已抽樣複核（見 §13.4） |

可信度分為 **Observed Fact**（有直接證據）、**High-confidence Inference**（多項證據合理推論）、**Product Hypothesis**（產品構想、尚未驗證）、**Unknown**（目前資料無法確認）。

---

## 1. Executive Summary

### 1.1 結論先行

Prism 是成熟、架構健康的單人本地知識庫：Go primary 單一 binary、SQLite WAL + FTS5、React SPA，Windows portable 與 Raspberry Pi 兩條交付路徑都穩定。08-12 審查的 14 項改善本次抽驗皆成立：FK 診斷、390px drawer、route-aware FilterStrip、Data & Recovery 整合、lazy routes 都在。Go 83 個測試、pytest 399 個全數通過。

但本次實測發現，**產品最核心的兩件事——「找得到」與「不會丟」——在常見條件下並不成立**，而現有測試完全沒有覆蓋這些條件：

1. **中文搜尋實際失效（FEAT-01）**。標題與內文搜尋只做 FTS5 預設 tokenizer 的前綴比對；中文沒有空白分詞，所以「工程」「角色設定」「夜景」「廣角」都搜不到明明存在的筆記。對以繁中為主要語言的產品，這是 core journey 缺陷。
2. **長文被自動拆出資料庫，而且會讓編輯被還原（FEAT-02）**。超過 5,000 字的筆記，本文會被移到 `docs/notes/note_<id>.md`，DB 只留 500 字預覽加一段寫死的中文橫幅。後果如下：
   - JSON/Markdown 匯出、DB 複本、還原點、版本歷史、REST API 拿到的都只是預覽。
   - 長文縮短到 5,000 字以下後，再開啟時編輯器會載入**舊的完整內容**覆蓋新內容。
3. **附件全文搜尋在約 50 個檔案就觸頂（PERF-01）**。有 230 篇長文時，每次搜尋都在 250ms 截止前只掃描 33–54 個檔案；「部分結果」變成常態，延遲約 260ms（一般列表 5ms）。
4. **「Download .db」會漏掉最近的寫入（OPS-01）**。它直接串流 live 主檔、不做 checkpoint：
   - 實測漏掉最近的新增與修改；fresh DB 甚至下載到沒有 `Notes` 表的空殼。
   - 同一頁另一顆「Download current database」用的是正確的 `VACUUM INTO`。
5. **寫作迴圈有摩擦（UX-01／UX-02／UX-03）**：
   - Header 的 **New** 與搜尋在 Settings、Prompt Builder 靜默失效，之後回到 Home 時編輯器還會「鬼開啟」。
   - `Ctrl+S` 存檔後立刻關閉編輯器。
   - 卡片的「預覽」其實是標題已自動 focus 的半編輯狀態。

技術成本方面，最大的拖累不在 runtime，而在**開發系統本身**：

- 399 個 pytest 中只有 27 個（6.8%）真的執行程式，其餘都在斷言 source 或文件字串（TECH-02）。
- 每次開工必讀約 186KB 文件，且有 16 個測試鎖住 HANDOFF/TODO 的字句（TECH-03）。
- `frontend/node_modules` 有 74MB（佔 HEAD tree 72%），被提交進 git 且不完整（TECH-04）。
- 版本字串散在 5 處，已造成兩次修正型發版（TECH-01）。

**判定：不需要大型改版，也不應繼續增加功能。** 下一輪做**小改版（B）**：以 REVAMP-01「Library Truth（搜尋與內容儲存可信度）」為主軸，加上 REVAMP-02 的寫作迴圈 MVP，並行小步的 REVAMP-03 engineering diet。

### 1.2 最大限制屬於哪一類

| 類別 | 判定 | 代表 ID |
|---|---|---|
| Feature correctness／資料架構 | **主要限制** | FEAT-01、FEAT-02、OPS-01、PERF-01 |
| UX workflow | 次要（高頻小摩擦） | UX-01、UX-02、UX-03 |
| 開發效率／可維護性 | 次要，但隨每輪開發放大 | TECH-01～TECH-04 |
| 安全 | 局部、修正成本極低 | TECH-07、OPS-04 |
| IA | 輕微 | IA-01、IA-02、UX-05 |
| Operations | 局部 | OPS-02、OPS-03、OPS-05 |

### 1.3 成熟度評估（對照 08-12）

| 維度 | 08-12 | 本次 | 說明 |
|---|---:|---:|---|
| Core workflow | 4 | 4 | CRUD、閱讀、附件、歷史都有；寫作迴圈仍有摩擦 |
| Search correctness | 未評 | 2 | 英文正確；中文子字串與長文後段失效 |
| Data reliability／portability | 3 | 2.5 | FK 診斷已修；但長文在匯出、DB 複本、歷史中失真，且 DB copy 不一致 |
| Product coherence／IA | 3 | 3.5 | filters 與 Data & Recovery 已收斂；剩重複導覽與 Settings 分組 |
| Responsive／a11y | 2.5 | 3.5 | drawer 與可存取名稱已補；mobile 缺排序、密度低 |
| Runtime／deployment | 4 | 4 | 穩定；Pi 代理後 localhost gate 失效，桌面版無自動備份 |
| Test／governance | 4 | 2.5 | 全綠，但 93% 不執行程式；文件鎖字；冷建置時 gate 時間大多花在 4 個打包 smoke |
| Scale readiness（個人資料 ×10） | 3 | 2.5 | 長文／文字附件約 50 個就觸頂 |

### 1.4 三個問題的直接答案

1. **現在最值得改善什麼？** 依序是：
   - OPS-01：讓 DB 複本一致。
   - TECH-07：附件檢視的 HTML injection（一行修正）。
   - UX-01：讓全域 New 與搜尋在任何頁面都有效。
   - FEAT-02a：停止產生新的長文拆分，並修正「縮短後被還原」。
   - FEAT-01：讓中文搜得到。

   五項都是小改動，而且都在處理「信任」問題。
2. **如果要改版，最合理的方向是什麼？** 不是 UI 重做，而是 REVAMP-01：讓筆記內容只有一個來源、讓中文搜尋正確、讓所有匯出與備份完整。再加上 REVAMP-02 的寫作迴圈 MVP。
3. **下一輪時間花在哪？不花在哪？**
   - **要花在**：§10 的 P0＋P1，共 15 個小型、可獨立 commit 的 task（§11）。
   - **不要花在**：新功能（回收桶、跨裝置同步、backlinks、AI）、視覺翻新、design system、換 framework 或 DB、trigram FTS、全面清除 flags、bundle 精簡、Settings 大改。

---

## 2. Project / Product Map

### 2.1 技術棧與規模（Observed Fact，【CMD】）

| 層 | Current | 規模 |
|---|---|---|
| Frontend | React 18.3、TypeScript 5.9、Vite 5.4、Zustand 4、Tailwind 3.4、Axios、marked 17 + DOMPurify、dnd-kit | TS/TSX 17,760 LOC；`i18n/index.ts` 一檔含 4 語、3,764 行（182,821 bytes） |
| Backend | Go 1.26（go.mod 1.26.1；本機 1.26.3）、`net/http`、modernc SQLite、go-webview2 | 11,706 LOC（不含 test）；test 4,556 LOC |
| Database | SQLite WAL、FTS5（`unicode61` 預設 tokenizer）、schema v17 | 9 張表 + `Notes_FTS` |
| Data-dir | DB、`static/uploads`、`docs/attachments`、`docs/notes`、`config`、`backups`、`logs` | 啟動時建立（`go-shadow/main.go:455-478`） |
| 交付 | Windows portable（WebView2、同一行程）；Pi（systemd + Caddy） | — |
| 測試 | pytest 399（冷建置 238.5s；cache 已熱時 72.4s）、Go 83 tests、Playwright e2e 5（不在 gate 內） | pytest 10,577 LOC |
| 文件 | Markdown ≥2.8MB、contract JSON 98 份 | 每次開工必讀約 186KB |
| Repo | 4,348 個 tracked files；HEAD tree 103.1MB，其中 `frontend/node_modules` 佔 74.1MB | — |

### 2.2 模組地圖

```text
frontend/src
├─ pages/        HomePage（eager）、PromptBuilder / SettingsPage（lazy，App.tsx:9-10）
├─ components/   Layout、Sidebar（mobile drawer）、Header、FilterStrip、NoteCard、NoteEditor、ReadingView、
│                CommandPalette、settings/*（Appearance / BackupImport / ServerDashboard / DangerZone…）
├─ hooks/        editor/*（form、history、attachments、paste、drag）、usePromptBuilder、useReadingWorkspace
├─ stores/       appStore（notes、filters、selection、modals）、toastStore
├─ services/     api.ts（axios，70 餘個 wrapper）
└─ i18n/         index.ts（zh-TW / en / ja / ko 同檔）

go-shadow（package main，單一 binary）
├─ main.go         啟動、flags、runtime config、49 條 route 註冊（:284-333）、SQLite owner
├─ notes_*.go      列表／搜尋／寫入／動作／歷史／變體／長文拆分
├─ taxonomy / attachments / uploads / media_cleanup / image_metadata
├─ import / export JSON、Markdown、DB、images、full snapshot
├─ backups / system 還原點、健康檢查、FTS/WAL、server dashboard、CSRF
├─ options.go      Prompt Builder 設定
├─ migrations.go   v1–v17 + fresh init
└─ desktop_shell_* WebView2、tray；hardware_*
```

### 2.3 Page / Route

| Route | Page | 主要能力 | Overlays |
|---|---|---|---|
| `/` | HomePage | 搜尋結果、分類/標籤/封存篩選、saved views、grid/list/compact、custom order、無限捲動、批次選取 | NoteEditor、ReadingView、CommandPalette |
| `/prompt-builder` | PromptBuilder | 模板、相機/風格/負面 prompt、wizard、三種輸出、複製、存入筆記庫 | WizardModal |
| `/settings?tab=` | SettingsPage | appearance / organization / backup（Data & Recovery）/ maintenance / access / about | confirm、toast |

共同外殼是 `Layout → Sidebar + Header + FilterStrip（只在 /）+ Outlet + Footer + CommandPalette`（`Layout.tsx:20-46`）。**NoteEditor 與 ReadingView 只掛在 HomePage 內**（`HomePage.tsx:617-623`），這是 UX-01 的根因。

### 2.4 API 地圖（Observed Fact，【SRC】【AGT】）

- 共 49 條 `HandleFunc` 加上 `Handle("/")`（`main.go:284-333`），middleware 為 `logRequests(csrfGate(mux))`。
- 主要分組：
  - Notes：列表、明細、CRUD、動作、歷史、變體、批次、排序、長文拆分
  - Taxonomy、Attachments、Uploads／圖片清理
  - Import／Export：JSON、MD、DB、images、full snapshot
  - System：health、stats、FTS、WAL、CSRF、consistency、migration
  - Server（localhost gate）：hardware、logs、restart、backups、version
  - Prompt／Wizard options
- React 從未呼叫的 route 有 15 條。多數只有已不再被提供的舊 Vue client（`static/js`）在用，例如 `/system/vacuum`、`/system/clear-history`、prompt-options CRUD、`/notes/batch/type|tags`、`/notes/export/batch`。`api.ts` 另有 5 個從未被呼叫的 wrapper。
- 13 個 `--enable-*` capability flags 在所有正式啟動路徑都全開：`start_go_primary.ps1:54-71`、桌面版強制開啟（`main.go:206-220`）、Pi 的 `setup.sh:112`。
- Response envelope 至少 6 種形狀：`{status,data}`、`{status}`、`{status,message}`、`{status:"ok"}`、plain-text 的 405/404、沒有 envelope 的檔案回應。

### 2.5 筆記內容實際存放在哪裡（本次關鍵地圖）

```text
一般筆記（≤ 5,000 字）             長文（> 5,000 字；儲存後前端自動呼叫 /separate）
Notes.content  = 全文               Notes.content  = 前 500 字 + 寫死的中文橫幅
Notes_FTS      = 全文               Notes_FTS      = 只有預覽
Note_History   = 全文               Note_History   = 只有預覽
                                    docs/notes/note_<id>.md = 全文（Note_Attachments.is_auto_extracted = 1）
App 內閱讀與編輯會另外讀取附件，所以使用者看起來一切正常。
```

證據：`useNoteForm.ts:8,123-129`、`notes_actions.go:285-386,439-445`、`main.go:38-39`，並已在【RT】重現。

### 2.6 Data flow

```text
User → Page / Overlay → Zustand（appStore）→ api.ts（axios；Prompt options 仍用 raw fetch）
     → Go handler（csrfGate）→ SQLite transaction / FTS5 trigger / data-dir 檔案
     → JSON → store 更新（多數 mutation 後呼叫 fetchNotes(true) 重置列表）→ toast

搜尋 q = FTS5 前綴比對（title/content）
       OR remarks LIKE
       OR tags LIKE
       OR 附件 metadata LIKE
       OR 逐檔讀取 md/txt 附件（每個請求都做；上限 200 檔 / 5MiB / 250ms）
```

### 2.7 Feature map（`*` 為本次新發現的問題點）

```text
Library
├─ Notes CRUD / 預覽（實為混合編輯態）* / Reading view / Reading list / History / Variants
├─ Search（header 需按 Enter；palette 需 ≥3 字）* / Filters / Saved views（localStorage）
├─ Grid / List / Compact / Custom order / 批次操作
├─ Categories / Tags / Starred tags / 圖片與 lightbox / 文字附件 / Source URLs
└─ 長文自動拆分（使用者看不到、無法關閉的自動行為）*
Prompt tools
└─ Prompt Builder / Quick templates（僅中文）* / Wizard / 存入筆記庫 / 「AI optimize」（實為複製提示詞）*
Data & Recovery
└─ JSON / .db* / Markdown 匯出、JSON 與 MD/TXT 匯入（含 dry-run）、Full snapshot（需手動還原）*、還原點
Maintenance
└─ 健康總覽 / 一致性檢查 / FTS / WAL / Stats（圖片數永遠 0）* / Server dashboard / Logs / Restart（假的）*
Preferences
└─ Appearance（混入行為設定）* / Organization / Access（CSRF + 圖片清理 Danger Zone）* / About（版本寫死）*
```

### 2.8 使用者角色與主要 journeys

- 角色：單一使用者，沒有帳號或角色模型（High-confidence Inference，與 08-12 相同）。主要語言推定為繁中：預設分類、welcome note、文件與 Prompt 模板都是中文（High-confidence Inference）。
- 本次追蹤的 7 條 journey：J1 捕捉（新增）、J2 找到（搜尋與篩選）、J3 閱讀與編輯、J4 整理、J5 Prompt、J6 保護資料（備份、匯出、還原）、J7 匯入與攜出。

### 2.9 文件描述 vs 目前實作（本次新發現的落差）

| 主題 | 文件怎麼說 | 實作／實測 | 判定 |
|---|---|---|---|
| 搜尋 | `API_REFERENCE.md:138`、`SCHEMA.md:225`、`ARCHITECTURE.md:61`：標題與內文走 FTS5 | 中文只做前綴比對，子字串搜不到【RT】 | 文件沒揭露限制（FEAT-01） |
| JSON 匯出 | UI：「Download all notes… bring them back with Import data later」 | 長文只有預覽；缺置頂、封存、譜系、版面欄位【RT】 | 文案過度承諾（FEAT-03） |
| Markdown 匯出 | UI：「One .md file per note… readable by Obsidian」 | 長文只有預覽；不含文字附件【RT】 | 同上 |
| DB copy | UI：「Download the SQLite .db file」 | 會缺最近的寫入【RT】 | 實作缺陷（OPS-01） |
| Server API | `API_REFERENCE.md:45`：`/api/server/*` 只允許 127.0.0.1/::1，遠端 Agent 不可呼叫 | Pi 經 Caddy 代理後，所有 LAN 請求都來自 127.0.0.1【SRC】 | 對 Pi 不成立（OPS-04） |
| Full snapshot | UI：「Recovery requires an explicit manual procedure」 | 找不到任何手動還原步驟；桌面 DB 檔名與 snapshot 內檔名不同 | 流程缺口（OPS-03） |
| 必讀文件 | `CLAUDE.md:28` / `AGENTS.md` 列出 `docs/New_UI/...html` | 檔案不存在；`docs/過期/` 也不存在 | 斷鏈（TECH-03） |
| About 版本 | — | `/api/test` 從不回傳 `version`，About 永遠顯示寫死的 fallback | TECH-01 |
| Restart 按鈕 | Server dashboard 有 Restart | handler 回 success 但不會重啟（`system.go:696-710`） | OPS-05 |

### 2.10 08-12 審查項目的現況

| 08-12 項目 | 現況 | 本次證據 |
|---|---|---|
| P0/P1 共 14 項 | 已完成，抽驗成立 | Maintenance 有「Foreign key violations」列【RT】；375px drawer 可用、無水平溢位【RT】；`/settings` 不顯示 FilterStrip【RT】；Data & Recovery 為單頁且有 DB-only 說明【RT】；PromptBuilder/SettingsPage 是獨立 chunk【CMD】 |
| R0812:UX-04 預覽語意 | **未處理** | 本報告 UX-03【RT】 |
| R0812:PERF-03 Reading list 無上限預取 | 未處理 | `ReadingView.tsx:137-142`【SRC】；維持 P2 |
| R0812:API-01 | 部分完成 | Prompt 存檔已改用 typed API；options 仍是 raw fetch（`usePromptBuilder.ts:192,232`） |
| R0812:DOC-01 | 未處理，範圍擴大 | 本報告 TECH-03 |
| R0812:TECH-02 flags 與命名 | 未處理，且已滲入使用者看得到的地方 | 本報告 TECH-05 |
| R0812:PERF-02 bundle | 已處理；現值 642.4kB（gzip 200.4kB） | TODO 記錄為 598.0kB，但之後前端只改了 41 行 → 差異原因 **Unknown** |

---

## 3. User Journey + UX Review

### 3.1 審查邊界

- **已實際操作**【RT】：
  - 環境：隔離 runtime（HEAD 建置、fresh DB），合成約 270 筆中英混合筆記，含 1 張圖、置頂、封存、230 篇長文。
  - 瀏覽器：內建 Chromium，desktop 1440×900 與 mobile 375×812。
  - 涵蓋畫面：Home grid、NoteEditor（新增與預覽）、ReadingView、Prompt Builder、Settings 四個分頁、mobile drawer。
- **只看原始碼**：WebView2 桌面行為、Pi、真實手機、Safari/Firefox、螢幕閱讀器。
- 不對字型、配色或美感下結論。

### 3.2 J1 — 捕捉：在任何頁面新增筆記並存檔

目前流程：Header「+ New」→ NoteEditor（只在 Home 掛載）→ 輸入 → Save（存檔並關閉）。

#### UX-01 — Header 的「New」與搜尋在 Library 以外靜默失效，之後還會「鬼開啟」

- **可信度**：Observed Fact【RT】【SRC】
- **原因**：
  - `Header.tsx:372` 直接呼叫 `openEditor(null)`；`Header.tsx:63-66` 直接呼叫 `setSearchQuery()`。兩者都沒有先導回 `/`。
  - 但 NoteEditor 與 ReadingView 只在 `HomePage.tsx:617-623` render。
- **對照**：其他入口都先 `navigate('/')`，包括 CommandPalette（`CommandPalette.tsx:97-98`）、Sidebar（`Sidebar.tsx:116,123,129`）、FilterStrip（`FilterStrip.tsx:29`）、閱讀清單（`Header.tsx:116`）、Prompt 存檔（`usePromptBuilder.ts:593,600`）。
- **【RT】實測**：
  - 在 `/settings` 按 New：DOM 中沒有 dialog 也沒有 editor。之後點 Sidebar「All」回到 Home，「New note」編輯器自己彈出來。
  - 在 `/prompt-builder` 搜尋「React」並按 Enter：停在原頁、沒有結果，但 footer 默默變成「3 notes」。
- **影響**：Prompt Builder 與 Settings 正是使用者最常「順手想記一筆」的地方。兩個最主要的全域動作沒有回饋，之後又在錯誤時機出現。
- **建議**：沿用既有 pattern——不在 Home 時先 `navigate('/')`，再開啟編輯器或搜尋；或者在非 Home route 隱藏搜尋框。不需改 store 或 API。
- Impact 4 / Effort 1 / Risk 1 / Confidence 高 / **P0**

#### UX-02 — `Ctrl+S` 等於「存檔並關閉」；寫到一半無法存了繼續寫，也沒有離開保護

- **可信度**：
  - Ctrl+S 會關閉編輯器：Observed Fact【RT】
  - 沒有草稿或離開保護：Observed Fact【SRC】（grep 找不到 `beforeunload` 或 draft）
- **證據**：`useNoteForm.ts:177-189` 把 Ctrl+S 綁到 `handleSave`；`handleSave` 成功後會呼叫 `fetchNotes(true)` 與 `onClose()`（`:130-131`）。
- **【RT】實測**：輸入半句話後按 Ctrl+S，出現「Note created」並關閉編輯器。重新打開又會先進入 UX-03 的預覽態，需要再切換一次。
- **影響**：
  - 習慣按 Ctrl+S 的長文寫作者會被踢出編輯器；新筆記存檔後還要回列表找。
  - 關閉 Pi 的瀏覽器分頁或結束桌面版時，未存內容不會有任何提示；只有 app 內的關閉按鈕會詢問。
  - 存檔後列表也會被重置（見 PERF-02）。
- **建議**：
  - `Ctrl+S` 改為存檔後留在原處，並更新 baseline snapshot；新筆記存檔後轉為「編輯既有筆記」狀態。
  - Save 按鈕維持「存檔並關閉」。
  - 有未存變更時註冊 `beforeunload`。
  - 不做常駐 autosave。
- Impact 4 / Effort 2 / Risk 2 / Confidence 高 / **P1**

### 3.3 J2 — 找到：搜尋與篩選，判斷結果

#### FEAT-01 — 中文（CJK）子字串搜尋實際失效

- **可信度**：Observed Fact【RT】【SRC】【CMD】
- **根因**：
  - `Notes_FTS` 使用 FTS5 預設的 `unicode61` tokenizer（`migrations.go:382-387`）。中文沒有空白，一整段文字（直到標點）會變成單一 token。
  - 查詢則被轉成逐 token 的前綴比對 `"詞"*`（`notes_search.go:192-195,312-319`）。
  - 結果是只有剛好位於句首或標點之後的詞會命中。
- **【RT】實測**：標題為「提示詞工程筆記」，內文含「今天學習提示詞工程的方法，重點是角色設定與輸出格式。」與「使用廣角鏡頭拍攝城市夜景…」

| 查詢 | 結果 | 原因 |
|---|---|---|
| 工程、角色設定、夜景、城市夜景、廣角 | **0 筆** | 詞位於 token 中段 |
| 提示詞、今天、相機 | 命中 | 詞恰好在 token 開頭 |
| engineering、prompt | 命中 | 英文有空白分詞 |

- **【CMD】benchmark**（合成 10,000 筆、每筆 1,800 個中文字）：
  - 現行前綴查詢：命中 0/11。
  - `LIKE '%夜景%'`：命中 11/11，耗時 227ms。
  - trigram FTS：3 字以上的查詢 <1ms；但建立索引要 36.7 秒，DB 膨脹到 329MB，而 2 字詞仍會退回全表掃描（228ms）。
- **讓問題更嚴重的因素**：
  - Command Palette 要輸入 ≥3 個字元才會查詢 server（`CommandPalette.tsx:20,55`），而多數中文詞只有 2 個字。
  - 所有 Go 搜尋測試只用 ASCII token（`main_test.go:1746-2017`），沒有任何 CJK 測試。
- **影響**：J2 對主要語言失效。使用者看到「沒有結果」會以為筆記不存在；搜尋診斷提示只涵蓋附件掃描，不涵蓋這種情況。日文同樣受影響；韓文以空白分詞，影響較小（Inference）。
- **建議**（Option B，不改 schema）：
  - 查詢含 Han／Hiragana／Katakana 時，對 title/content 加上 `LIKE '%token%'`（多個 token 之間 AND）作為 OR 分支。
  - Command Palette 對 CJK 輸入 2 個字就觸發查詢。
  - 個人資料量下，LIKE 成本約每百萬字 13ms（由 benchmark 推估）。
  - trigram FTS 列為 Future：只有在資料達數萬筆、且查詢以 3 字以上為主時才值得。
- Impact 5 / Effort 2 / Risk 2 / Confidence 高 / **P0**

#### PERF-01 — 每次關鍵字搜尋都在請求內逐檔讀取附件，約 50 個檔就觸頂，「部分結果」成為常態

- **可信度**：Observed Fact【RT】【SRC】
- **證據**：
  - 每個帶 `q` 的請求都會查出所有 md/txt 附件，逐檔執行 `resolveAttachmentFile`（Abs、EvalSymlinks、Lstat）與 `ReadFile`；上限為 200 檔、5MiB、250ms（`notes_search.go:321-384`）。
  - 查詢沒有 `ORDER BY`；觸頂時被略過的推定是較新的檔案（Inference：依 rowid 順序）。
- **【RT】實測**（建立 230 篇被拆分的長文，連續 3 輪）：
  - 每次搜尋都以 `time_limit` 結束，只掃描 33–54 個檔案。
  - 尾段關鍵字只有最舊的那一篇找得到（`uniqtail000`）；第 100 篇之後全部 0 筆。
  - 任何關鍵字（包括「research」「夜景」）延遲都在 256–267ms，而沒有查詢的列表只要 5ms。
  - 無限捲動的第 2 頁會再掃描一次（259ms）。
  - Home 與 Command Palette 每次都顯示 partial 提示。
- **根因**：FEAT-02 讓每一篇長文都落入附件掃描路徑，而附件內容沒有進任何索引。
- **影響**：「資料 ×10」的痛點在 Windows 上約 50 個長文或文字附件就出現。Pi SD 卡上每檔的成本 **Unknown**。
- **建議**：先完成 FEAT-02（長文回到 `Notes.content`，進入 FTS 與 LIKE 範圍；掃描量只剩真正的使用者附件）。若之後文字附件仍多，再評估附件文字索引（需改 schema，列為 Future）。不建議只把上限調大。
- Impact 4 / Effort 由 FEAT-02 解決 / Risk 2 / Confidence 高 / **P1（隨 FEAT-02b）**

#### UX-04 — Mobile 沒有排序控制，首屏 chrome 佔約 36%

- **可信度**：Observed Fact【RT】
- **證據**：
  - 375px 寬時，排序按鈕存在於 DOM 但被隱藏（`Header.tsx:273-274` 的 `hidden sm:block`）；drawer 裡也沒有排序。
  - 第一張卡片從 295px 才開始，grid 模式下 viewport 內只完整顯示 1 張卡片。
- **建議**：在 drawer 或 mobile header 補上排序選單；mobile 預設改用 list/compact，或壓縮標題與「Save current view」這一列。
- Impact 3 / Effort 2 / Risk 1 / Confidence 高 / **P2**

### 3.4 跨旅程根因：長文自動拆分

#### FEAT-02 — 長文自動拆分讓筆記本體分散在 DB 與檔案，連帶使搜尋、匯出、歷史、DB 備份、API 失真，並會還原使用者的編輯

- **可信度**：
  - 拆分的後果：Observed Fact【RT】【SRC】
  - 拆分的原始目的已過時：High-confidence Inference
- **機制**：
  1. 儲存時若 `content.length > 5000`，前端呼叫 `POST /notes/:id/separate`（`useNoteForm.ts:8,123-129`）。
  2. 後端把全文寫到 `docs/notes/note_<id>.md`，並建立 `is_auto_extracted = 1` 的附件。
  3. `Notes.content` 被改成 500 字預覽，加上寫死的中文「此筆記內容過長，已自動分離為附件…」（`notes_actions.go:285-386,439-445`；常數在 `main.go:38-39`）。

  這是使用者不知道、也無法關閉的自動行為。
- **【RT】實測**：一篇 6,075 字的筆記拆分後，各管道拿到的內容如下。

| 管道 | 拿到的內容 |
|---|---|
| App 內閱讀與編輯 | 全文。UI 會另外讀附件（`ReadingView.tsx:180-182`、`useNoteAttachments.ts:21-26`），所以使用者覺得正常 |
| `GET /api/notes/:id`（README 主打給外部 agent 使用的 REST API） | 557 字的預覽 |
| JSON 匯出 | 557 字，尾段關鍵字不存在；附件只有路徑 metadata（`export.go:516-555,597-622`） |
| Markdown 匯出（給 Obsidian 用） | 737 字（含 frontmatter），尾段不存在（`export.go:664-751`） |
| DB 複本／還原點 | 只有預覽，全文在 DB 之外 |
| 版本歷史 | 編輯兩次後，兩筆歷史都只有 557 字預覽加橫幅，任何舊版長文都無法還原（`notes_write.go:117` 存的是 DB 裡的舊值） |
| 全文索引 | 只索引預覽；後段要靠 PERF-01 的有限掃描 |
| **縮短後的編輯** | 把已拆分的長文改成 34 字並存檔後：列表卡片顯示新內容，**但開啟編輯器時載入的是舊的 6,088 字 v3 全文**（`useNoteAttachments.ts:21-26` 會無條件用附件覆蓋表單內容）。只要再按一次 Save，舊內容就會覆寫新內容 |
| 非中文使用者 | 筆記內容被寫入一段中文橫幅（i18n 缺陷直接寫進使用者資料） |

- **為何拆分已不必要**：列表 API 已經回傳截斷過的 `content_preview` 與 `content_truncated`（`notes_search.go:672-690`），payload 不會因長文而膨脹；SQLite 單列存放 MB 級文字也沒有問題（Inference）。目前只有 Full snapshot 會把 `docs/notes` 一起帶走（`export.go:200-204`）。
- **選項**：
  - A：維持現狀。問題隨長文數量線性擴大，還原 bug 持續存在。
  - B：停止產生**新的**拆分，並修正已拆分筆記的存檔路徑。
  - C：B 再加上一個有備份與 dry-run 的「合併長文回筆記」維護動作，重用既有且有測試的 `restoreSeparatedContent`（`notes_actions.go:388-430`；測試在 `main_test.go:2516-2568`）。後端 endpoint 保留，維持 API 相容。
- **建議**：**P0 做 B（FEAT-02a），P1 做 C（FEAT-02b）**。B 必須同時處理已拆分的筆記：存檔前先用既有的 `POST /notes/:id/restore` 把檔案收回 DB，再 PUT 新內容。否則舊附件仍會覆蓋新內容。細節見 Task PRISM-OPT-19。
- Impact 5 / Effort 1～2（a）、3（b）/ Risk 2（a）、3（b，資料搬移）/ Confidence 高 / **P0 + P1**

### 3.5 J3 — 閱讀與編輯既有筆記

#### UX-03 — 卡片預設的「預覽」，實際是標題已 focus 的半編輯態（延續 R0812:UX-04）

- **可信度**：Observed Fact【RT】
- **證據**：預設 `cardOpenMode = preview`，開啟後：
  - heading 顯示「Edit note」。
  - 標題是已經 `autoFocus` 的 `<input>`（`NoteEditor.tsx:161-168`）。
  - header 同時有 Save 與 Edit mode，每個區塊還有「Edit this block」。
  - 另一個純閱讀介面 ReadingView 只能從選單的「Read」進入。
- **影響**：
  - 最頻繁的動作（點卡片看內容）落在一個模糊的狀態，任何按鍵都會直接改到標題。
  - 和 UX-02 疊加後，寫作流程變成「開啟 → 切換 → 寫 → 按 Ctrl+S 被關掉 → 重開」。
- **建議（最小版本）**：
  - preview 狀態的 heading 改為「預覽」，標題以 heading 呈現、不 autoFocus。
  - Save 只在有變更或進入 Edit 模式時出現。
  - 卡片的主要點擊是否改導到 ReadingView，等 usage 回饋再決定（REVAMP-02 完整版）。
- Impact 3 / Effort 2 / Risk 2 / Confidence 高 / **P1**

#### PERF-02 — 任何 mutation 之後都把列表重置回第 1 頁

- **可信度**：High-confidence Inference【SRC】
- **證據**：以下動作都會呼叫 `fetchNotes(true)`，store 再以第一頁取代整份 notes（`appStore.ts:154-158`）：
  - 存檔：`useNoteForm.ts:130`
  - 置頂、封存、建立變體：`NoteCard.tsx:150,164,216`
  - 歷史還原：`useNoteHistory.ts:52`
- **影響**：捲到很深之後編輯一篇，列表會縮回 20 筆，捲動位置與上下文都會遺失。
- **建議**：mutation 後就地更新該筆；或保留已載入的頁數重新抓取。不需要每次都重置。
- Impact 3 / Effort 2 / Risk 2 / Confidence 中 / **P2**

### 3.6 J4 — 整理：分類、標籤、計數

#### UX-05 — 同一個畫面上有四種互相矛盾的筆記數，維護頁的圖片數永遠是 0

- **可信度**：Observed Fact【RT】【SRC】
- **證據**：
  - Sidebar「All 37」是各分類計數的加總：包含封存、不含未分類（`Sidebar.tsx:194`）。Home 顯示「36 items」，不含封存。
  - Footer 讀的是 store 的 `totalNotes`：直接進 `/settings` 時顯示「0 notes」；在 Prompt Builder 搜尋後變成「3 notes」。
  - Maintenance 的「Database stats」來自 `/api/test`，而 `images_count: 0`、`total_size_mb: 0` 是寫死的（`SettingsPage.tsx:90-98`）。
  - 已經存在但沒被使用的 `/api/system/stats` 會回傳封存數、歷史數、DB 大小、上傳大小等真實數值【RT】。
- **建議**：定義單一的「Library 總數（不含封存）」來源，給 Sidebar 與 Footer 共用；Maintenance 改用 `/api/system/stats`。
- Impact 2 / Effort 1 / Risk 1 / Confidence 高 / **P2**

分類與 FilterStrip 的重複，見 IA-01。

### 3.7 J5 — Prompt Builder

#### UX-06 — Prompt Builder 的命名、語系，以及 fresh data-dir 的死路

- **可信度**：Observed Fact【RT】
- **問題**：
  - **命名誤導**：「AI optimize」其實是複製一段要貼到 ChatGPT/Claude 的優化指令（見 i18n 的 `optimizeTitle`）。在明確不含 AI 的產品裡容易被誤解，應改名。
  - **模板只有中文**：Quick templates 是只有中文的 seed data，英文 UI 下仍顯示「電影海報」「人像攝影」等。
  - **fresh data-dir 的死路**：沒有 seed 時顯示「Failed to load configuration / Retry」，但 Retry 永遠不會成功。seed 是從五個候選路徑尋找（`options.go:238-263`）；打包版有附帶，`pack.bat` 沒有【AGT】。
  - Header 的 New 與搜尋失效，見 UX-01。
- Impact 2 / Effort 1 / Risk 1 / Confidence 中 / **P3**（改名可以在任何與 Prompt 相關的 task 中順手完成）

### 3.8 J6 — 保護資料：備份、匯出、還原

#### OPS-01 — 「Download .db」串流 live 主檔，會遺漏最近的寫入

- **可信度**：Observed Fact【RT】【SRC】
- **證據**：
  - `handleExportDB` 直接 `http.ServeFile(dbPath)`，沒有 checkpoint，也沒用 backup API（`export.go:122-142`）。
  - 同一頁的「Download current database」走 `handleBackupDownload`，使用 `VACUUM INTO` 產生一致的快照（`backups.go:21-48,82-101`）。
  - 兩顆按鈕都在 Data & Recovery（`BackupImportSection.tsx:420` 與 `:131`）。
  - DSN 沒有調整 `wal_autocheckpoint`（`main.go:701-704`），預設要累積約 1,000 頁才會自動 checkpoint。
- **【RT】實測**：
  - fresh instance 下載到的 .db 只有 4,096 bytes，沒有 `Notes` 表。
  - 手動 checkpoint 後，新增 1 筆並修改 1 筆的標題。live API 顯示 6 筆與新標題；下載的 .db 仍是 5 筆與舊標題。
- **影響**：使用者以為拿到了備份，實際上缺少最近（可能好幾天）的工作。若用它手動覆蓋 DB，這些工作就會遺失。
- **建議**：
  - `/api/export/db` 改用既有的 `writeConsistentDBBackup` 寫到暫存檔再送出，寫法與 `handleBackupDownload` 相同，API 路徑不變。
  - 補一個 Go test：寫入後即使還沒 checkpoint，下載內容也必須包含它。
- Impact 5 / Effort 1 / Risk 1 / Confidence 高 / **P0**

#### FEAT-03 — JSON 與 Markdown 匯出的文案過度承諾

- **可信度**：Observed Fact【RT】
- **證據**：
  - JSON 中每筆 note 只有 `id/title/content/category/remarks/cover_image/created_at/updated_at/tags/urls`。
  - 缺少 `is_pinned`、`is_archived`、`parent_id`（變體譜系）、`cover_position`、`editor_layout`、`sort_order`，也沒有歷史與附件檔案內容；長文只有預覽（FEAT-02）。
  - UI 卻寫著「Download all notes… You can bring them back with Import data later」。
- **建議**：
  - P1：先改文案為「可攜的文字副本，不含置頂、封存、歷史、附件檔與圖片；完整備份請用 Full snapshot」。
  - 長文的完整性由 FEAT-02b 解決。
  - 是否補上缺少的欄位（需同步修改 import）列為 P2。
- Impact 3 / Effort 1 / Risk 1 / Confidence 高 / **P1**

#### OPS-02 — Windows 桌面版沒有任何自動備份

- **可信度**：Observed Fact【SRC】
- **證據**：
  - Go runtime 內沒有任何排程（找不到 ticker 或 AfterFunc）。
  - Pi 靠 systemd 的每週 timer 備份（`DEPLOY-PI.md:136-161`）。
  - portable 版的資料預設放在 exe 旁的 `PrismData\`，很可能就在下載資料夾裡。
- **建議**：
  - 桌面殼啟動成功後，若最新的還原點已超過 24 小時，就建立一個新的（重用 `writeConsistentDBBackup` 與 `enforceBackupRetention`，保留 N 份）。
  - 預設是否開啟、N 要多少、是否顯示通知，需要使用者決策。
  - 不做常駐的背景排程。
- Impact 4 / Effort 2 / Risk 2 / Confidence 中 / **P1（需先決策）**

#### OPS-03 — 唯一完整的備份（Full snapshot）沒有還原路徑

- **可信度**：Observed Fact【DOC】【SRC】
- **證據**：
  - UI 與 contract 只寫「需要明確的手動程序」（`full-data-snapshot-v1.md:69`），但沒有任何文件寫出步驟。
  - snapshot 內的 DB 檔名固定為 `database/knowledge.db`（`export.go:191`）；桌面版實際的 DB 檔名是 `prism_desktop_dev.db`（`main.go:203-205`）。手動還原時必須改名，但沒有任何說明。
- **建議**：先補一頁「手動還原」說明（桌面與 Pi 各一段，含改名與 data-dir 的對應關係），並在 UI 加上連結。自動還原仍然不做。
- Impact 3 / Effort 1 / Risk 1 / Confidence 高 / **P2**

### 3.9 J7 — 匯入與攜出

- JSON、MD、TXT 匯入已經有 dry-run 預覽（KWF-05）。主要缺口在匯出端（FEAT-03、FEAT-02）。
- JSON 匯出再匯入後會遺失置頂、封存與譜系。這是依匯出欄位清單推定（High-confidence Inference），沒有在 runtime 實際匯回驗證。

---

## 4. Information Architecture

### 4.1 目前 IA（Runtime observed）

```text
Prism
├─ 外殼
│  ├─ Sidebar：All（計數含封存）/ Prompt Builder / Categories（5）/ System：Archive、Settings / Tags（21）/ 收合
│  ├─ Header：頁名 + meta / 搜尋（按 Enter；所有 route 可見，但只對 Home 有效）/ 排序（≥640px）/ 檢視 / Ctrl K / 閱讀清單 / New（只對 Home 有效）
│  ├─ FilterStrip（只在 /）：All / Archive / Categories（與 Sidebar 重複）/ Starred tags
│  └─ Footer：連線 / SQLite WAL / notes 數（依 store）/ tags 數
├─ Home：H1 標題與說明 / Save current view / 搜尋 context / 卡片 / Editor 與 Reading overlay
├─ Prompt Builder
└─ Settings
   ├─ Appearance：主題、語言、背景、密度、強調色、圓角、側欄寬、卡片開啟模式*、圖片儲存模式*、快速新增預設分類*、自動載入*
   ├─ Organization：分類、標籤
   ├─ Data & Recovery：範圍說明 / JSON、.db*、Markdown / JSON 匯入 / MD、TXT 批次匯入 / Full snapshot / 還原點（另有 Download current database*）
   ├─ Maintenance & Health：總覽 / 一致性 / Stats（圖片數 0）/ Advanced：WAL、FTS、Server dashboard、Logs、Restart*
   ├─ Access & System：CSRF / Danger Zone = 圖片清理*
   └─ About：版本（寫死）
```

`*` 為本次指出的問題。

### 4.2 建議 IA（只做局部、可逆的調整）

```text
Prism
├─ 外殼
│  ├─ Sidebar（desktop）／ Drawer（mobile）：Library 導覽、分類、標籤（不變）
│  ├─ Header：New 與搜尋在任何 route 都導向 Library 並生效（UX-01）；mobile 補上排序（UX-04）
│  ├─ FilterStrip（只在 /）：desktop 只放「目前篩選狀態 + Starred tags + Archive」；mobile 才顯示分類 chips（IA-01）
│  └─ Footer：Library 總數改用單一來源（UX-05）
├─ Library（Home）：H1 與 header meta 只保留其一
├─ Prompt Builder：「AI optimize」改名為「複製優化提示詞」
└─ Settings
   ├─ Appearance（只放外觀設定）
   ├─ Library & Editor：卡片開啟模式、快速新增預設分類、自動載入
   ├─ Organization（不變）
   ├─ Data & Recovery：只留一顆 DB 下載（一致快照）、JSON 與 MD 文案寫清楚範圍、Full snapshot + 如何還原
   ├─ Maintenance & Health：健康檢查 / Images & storage（圖片儲存模式 + 三種圖片清理）/ Advanced
   ├─ Access（CSRF）
   └─ About（版本由 runtime 提供）
```

### 4.3 變更表

| 動作 | 目前 → 建議 | 使用者收益 | 認知／操作成本 | 技術影響 | ID |
|---|---|---|---|---|---|
| Fix／Promote | Header New 與搜尋只在 Home 有效 → 任何頁都可用 | 隨手記錄、隨處搜尋 | 少一次猜測 | `Header.tsx` 兩處 | UX-01 |
| Merge | desktop 上 Sidebar 分類與 FilterStrip 分類 chips 同時可見 → desktop strip 只留篩選狀態與星標 | 少一列重複控制 | 降低 | `FilterStrip.tsx` 依 breakpoint 切換 | IA-01 |
| Remove | 標題與計數重複三次（header meta、H1、footer） | 視覺噪音變少 | 降低 | 純 UI | IA-01 |
| Move | 行為設定放在 Appearance → 移到 Library & Editor | 找設定更直覺 | 降低 | 搬 component | IA-02 |
| Move／Merge | 圖片儲存模式（Appearance）與圖片清理（Access → Danger Zone）→ 合併到 Maintenance 的 Images & storage | 圖片生命週期在同一處管理 | 降低 | 搬 component | IA-02 |
| Merge／Fix | 兩顆 DB 下載 → 一顆一致快照 | 不會拿到壞掉的備份 | 降低 | 見 OPS-01 | OPS-01 |
| Remove／Fix | 假的 Restart → 接上既有的 restart，或直接移除 | 不再顯示假成功 | — | `system.go:696` | OPS-05 |
| Rename | AI optimize → 複製優化提示詞 | 不會誤以為有內建 AI | — | i18n | UX-06 |
| Fix | `?tab=data` 無效（實際的 tab id 是 `backup`） | 深連結行為可預期 | — | 小 | IA-02 |
| Keep | Settings 6 個 tab，不拆成多個 route | — | — | — | — |

- **IA-01 — Library 導覽重複**：Impact 2 / Effort 2 / Risk 1 / Confidence 中 / **P2**
- **IA-02 — Settings 分組不當，圖片設定散在三處**：Impact 2 / Effort 2 / Risk 1 / Confidence 中 / **P2**

不建議：新增 top-level route、大改 Sidebar、重做 navigation framework。

---

## 5. Feature Matrix & Consolidation

### 5.1 主要功能

| 功能 | 類型 | 價值／頻率（推定） | 核心 journey | 重疊或缺口 | 建議 | ID |
|---|---|---|---|---|---|---|
| Notes CRUD 與編輯器 | Core | 高／高 | J1、J3 | Ctrl+S 會關閉；預覽是混合態 | Simplify | UX-02、UX-03 |
| 關鍵字搜尋（header、palette） | Core | 高／高 | J2 | 中文失效；長文後段失效；palette 需 ≥3 字 | Fix | FEAT-01、PERF-01 |
| 分類、標籤、星標 | Supporting | 高／高 | J4 | Sidebar 與 FilterStrip 重複 | 局部 Merge | IA-01 |
| Grid／List／Compact | Supporting | 中高／高 | J2 | mobile 密度低 | Keep；mobile 預設可調 | UX-04 |
| 批次選取與刪除（含 dry-run） | Power User | 中／中 | J4 | — | Keep | — |
| Saved views（localStorage） | Power User | 中／未知 | J2 | 不跨裝置 | Keep | — |
| Reading view | Supporting | 高／中 | J3 | 與編輯器預覽重疊 | Merge candidate（等 usage） | UX-03 |
| Reading list（workspace） | Power User／Questionable | 未知 | J3 | 無上限預取 | Keep；P2 | R0812:PERF-03 |
| 版本歷史 | Supporting | 高／低中 | J3、J6 | 對長文無效 | Fix（隨 FEAT-02b） | FEAT-02 |
| 變體與譜系 | Power User | 中／低 | J3 | JSON 匯出會遺失 parent | Keep | FEAT-03 |
| **長文自動拆分** | **Remove candidate** | 負值（隱性成本） | — | 破壞匯出、歷史、搜尋、API，並會還原編輯 | Remove（停用後合併回 DB） | FEAT-02 |
| 圖片、封面、lightbox | Supporting | 高／中 | J1 | 相關設定分散三處 | Move | IA-02 |
| 文字附件 | Supporting | 中／低中 | J1 | 搜尋只能靠逐檔掃描 | Keep；索引列 Future | PERF-01 |
| Source URLs | Supporting | 中／中 | J3 | — | Keep | — |
| Prompt Builder | Power User／差異化功能 | 未知 | J5 | 模板只有中文；options CRUD 沒有 UI | Keep；改一處名稱 | UX-06、FEAT-07 |
| Custom order（拖曳排序） | Questionable | 未知 | J4 | scope 已在上一輪限縮 | Keep（觀察） | — |
| JSON、MD、.db 匯出 | Supporting | 高／低 | J6、J7 | .db 不一致；文案過度承諾 | Fix + Merge | OPS-01、FEAT-03 |
| Full snapshot | Supporting | 高／低 | J6 | 沒有還原說明 | Promote（補說明） | OPS-03 |
| 還原點 | Supporting | 高／低 | J6 | 桌面版沒有自動建立 | Automate | OPS-02 |
| 健康檢查、FTS、WAL | Power User | 中／低 | J6 | 已收進 Advanced | Keep | — |
| Server dashboard、Logs | Power User | 中／低（Pi） | — | Restart 是假成功 | 修正或移除那顆按鈕 | OPS-05 |
| 圖片清理（Danger Zone） | Power User | 中／低 | — | 位置不符合心智模型 | Move | IA-02 |
| 外觀客製（5 種背景、6 種強調色、圓角、側欄寬） | Nice-to-have | 中／低 | — | — | Keep；不再增加 | — |
| Command palette | Power User | 中高／中 | J2 | CJK 觸發門檻太高 | Fix（隨 FEAT-01） | FEAT-01 |
| CSRF 開關 | Power User | 低 | — | — | Keep | — |
| Port config、Update section、TagInput（隱藏或未被 import） | Remove candidate | 0 | — | `.port_config` 寫入後沒人讀；2 個元件沒被引用 | Remove | TECH-06 |
| 只剩舊 Vue client 使用的 API（vacuum、clear-history、startup-preference、prompt-options CRUD、batch type/tags、export batch） | Questionable | 未知（也許有外部 agent 使用） | — | React 沒有呼叫 | 決定保留給 agent 使用，或標為 deprecated | TECH-06 |

表中頻率皆為推定，沒有 usage analytics。

### 5.2 整併動作

| 類型 | 項目 | ID |
|---|---|---|
| Merge | 兩顆 DB 下載；Sidebar 與 strip 的分類；重複三次的標題與計數；圖片設定 | OPS-01、IA-01、IA-02 |
| Simplify | Ctrl+S 語意、預覽狀態、mutation 後不重置列表 | UX-02、UX-03、PERF-02 |
| Remove | 長文自動拆分；假的 Restart；未被引用的元件與 `.port_config`；死資產 | FEAT-02、OPS-05、TECH-06、TECH-04 |
| Hide | 08-12 已把 WAL、FTS、server 資訊收進 Advanced；本次不再新增 | — |
| Promote | Full snapshot 的還原說明；mobile 排序 | OPS-03、UX-04 |
| Rename | AI optimize；長期再處理 `prism_desktop_dev.db` 等遷移期名稱 | UX-06、TECH-05 |
| Automate | 桌面版每日還原點；CJK 查詢自動 fallback（使用者不必改變搜尋方式） | OPS-02、FEAT-01 |

### 5.3 明確保持現狀

SQLite／FTS5／WAL、Go 單一 binary、Zustand、React Router、Tailwind、外觀設定、Saved views 存在 localStorage、Custom order 的現行限制、Reading list、Settings 的 tab 結構、不內建 auth（本地／可信網段的產品定位）。

---

## 6. Revamp Direction

### 6.1 這個產品現在值得改版嗎？

判定為 **B：小改版**，不是 C 或 D。

- IA 與視覺在 08-12 之後已大致收斂。目前最大的問題不在畫面，而在「內容存放模型＋搜尋 tokenizer＋匯出與備份的實作」這一層，以及寫作迴圈裡幾個高頻摩擦。
- 這些問題都能在不動頁面結構、不換技術棧的前提下修正。唯一的結構性變更是把長文合併回 DB；這是資料搬移，但邏輯已經存在且有測試。
- 不選 D：沒有證據顯示產品模型、IA 或技術結構正在限制下一階段。

### 6.2 候選方向

#### REVAMP-01 — Library Truth（屬 G 類：資料與搜尋的架構強化）

| 項目 | 內容 |
|---|---|
| 目標 | 任何筆記的完整內容只有一個來源（`Notes.content`）；中文搜得到；所有匯出、備份、歷史、API 都完整且一致 |
| 現有證據 | FEAT-01、FEAT-02、PERF-01、OPS-01、FEAT-03、OPS-03 |
| 主要變更 | 搜尋條件加上 CJK LIKE fallback；停止拆分並合併回 DB；`/export/db` 改為一致快照；修正匯出文案；補上 snapshot 還原說明；加上對應的 behavior test |
| 保留 | FTS5、schema v17（不加表）、所有 API 路徑與 response 形狀、附件功能、Full snapshot 格式 |
| Merge／Remove／Hide／Promote | Remove 長文拆分；Merge 兩顆 DB 下載；Promote 還原說明 |
| User Benefit | 找得到、匯出可用、歷史可還原、備份可信 |
| Technical Impact | Go：`notes_search`、`notes_actions`、`export`；frontend：`useNoteForm`、`CommandPalette`、Data & Recovery 文案；tests |
| Migration Risk | 中。合併回 DB 是資料搬移：需先建立還原點、提供 dry-run、逐筆冪等，檔案移入隔離資料夾而不是刪除 |
| MVP（20–30%） | OPS-01、FEAT-01、FEAT-02a，約 3 個小 PR |
| Full | 再加 FEAT-02b、FEAT-03、OPS-03，以及 CJK、WAL、長文的 behavior test；之後才評估附件文字索引 |
| 評分 | Impact 5 / Effort 3 / Risk 2 / Confidence 高 |
| Recommendation | **現在做** |

#### REVAMP-02 — Write Loop（屬 A 類，輕量的 Workflow-first）

| 項目 | 內容 |
|---|---|
| 目標 | 在任何地方一步開始記錄；寫作中存檔不中斷；關閉時不遺失內容；開啟筆記時語意清楚 |
| 現有證據 | UX-01、UX-02、UX-03、PERF-02 |
| 主要變更 | Header 先導向 Library；Ctrl+S 存檔後留在原處；`beforeunload`；預覽狀態語意；mutation 後就地更新 |
| 保留 | NoteEditor 版面、EditablePreview、ReadingView、其他快捷鍵 |
| Merge／Remove／Hide／Promote | Simplify；完整版才考慮 Promote ReadingView |
| User Benefit | 最高頻的 J1、J3 少 1–3 次操作與誤觸 |
| Technical Impact | 只動 frontend：Header、useNoteForm、NoteEditor、EditorToolbar、appStore |
| Migration Risk | 低。行為改變需要一句說明；Save 按鈕語意不變 |
| MVP | UX-01，以及 Ctrl+S 存檔後留在原處 |
| Full | 再加 UX-03、PERF-02；卡片主要點擊是否改導 ReadingView，等 usage 再定 |
| 評分 | Impact 4 / Effort 2 / Risk 2 / Confidence 高 |
| Recommendation | **MVP 現在做；完整版下一階段** |

#### REVAMP-03 — Engineering Diet（不是產品改版，是開發效率）

| 項目 | 內容 |
|---|---|
| 目標 | 讓測試保護「行為」；讓文件只承載 current truth；讓 repo 能乾淨地 clone 與 build；版本只有一個來源 |
| 現有證據 | TECH-01～TECH-04：399 個測試只有 27 個會執行程式；必讀約 186KB；16 個測試鎖 HANDOFF/TODO 字句；node_modules 74MB 且缺 dompurify；兩次版本修正型發版 |
| 主要變更 | Go 與 3–5 條 e2e 的 behavior test；fast／release gate 分流；歷史 docs-text 測試改為 opt-in；文件瘦身；將 node_modules 與死資產移出版控；版本單一來源 |
| 保留 | release、migration、package 的 safety test；contract JSON（不改寫歷史紀錄）；治理原則 |
| Merge／Remove／Hide／Promote | Remove 死資產；Hide 歷史測試（改為 opt-in） |
| User Benefit | 開發者與 agent 每輪少讀、少改；真正的 bug 會被測試擋下 |
| Technical Impact | `tests/`、`.loop`、docs、repo 檔案；不碰 runtime |
| Migration Risk | 低。需同步 CI；避免一次刪光 |
| MVP | TECH-01、TECH-04，以及為本報告的 P0 bug 補 behavior test |
| Full | gate 分流、歷史測試 opt-in、文件瘦身、e2e 進入 release gate |
| 評分 | Impact 4 / Effort 3 / Risk 2 / Confidence 高 |
| Recommendation | **下一階段**（可與 01、02 並行） |

#### REVAMP-04 — IA 整理與 mobile 密度（屬 B／E 類）

| 項目 | 內容 |
|---|---|
| 目標 | 去除重複；Settings 分組符合使用者心智模型；mobile 可排序且一屏看得更多 |
| 現有證據 | IA-01、IA-02、UX-04、UX-05、OPS-05、UX-06 |
| 主要變更 | 見 §4.2 |
| 保留 | route 與 tab 結構、drawer、主題系統 |
| User Benefit | 理解成本略降；mobile 上找筆記更快 |
| Technical Impact | 只動 frontend |
| Migration Risk | 低。設定位置移動時需要提示 |
| MVP | UX-04 的排序、UX-05 的計數 |
| Full | §4.3 全部 |
| 評分 | Impact 3 / Effort 2 / Risk 1 / Confidence 中 |
| Recommendation | **下一階段後段，或等 usage data 再決定** |

#### REVAMP-05 — 桌面版與 Pi 之間跨裝置（屬 H 類：產品擴張）

| 項目 | 內容 |
|---|---|
| 目標 | 在兩個部署之間同步或合併資料 |
| 現有證據 | 只有「兩條交付路徑同時存在」；沒有證據顯示同一使用者同時在兩邊寫入，或有衝突的痛點 → **Product Hypothesis** |
| 主要變更 | 需要 identity、衝突解決、增量匯出入，可能還要改 schema |
| Migration Risk | 高 |
| MVP | 寫出「Full snapshot → 在另一端還原」的手動說明（就是 OPS-03） |
| 評分 | Impact ？ / Effort 5 / Risk 4 / Confidence 低 |
| Recommendation | **不建議**（先做 OPS-03） |

### 6.3 比較

| 方向 | 解決的問題 | 範圍 | Migration risk | Impact | Effort | Risk | Confidence | 建議 |
|---|---|---|---|---:|---:|---:|---|---|
| REVAMP-01 Library Truth | 找不到、匯出不完整、備份過期、編輯被還原 | Go＋小量 frontend | 中（資料搬移） | 5 | 3 | 2 | 高 | 現在做 |
| REVAMP-02 Write Loop | 全域新增失效、Ctrl+S 被踢出、預覽態模糊 | frontend | 低 | 4 | 2 | 2 | 高 | MVP 現在做 |
| REVAMP-03 Engineering Diet | 測試不擋真 bug；文件與版控成本 | tests／docs／repo | 低 | 4 | 3 | 2 | 高 | 下一階段（並行） |
| REVAMP-04 IA 整理 | 重複導覽、設定分散、mobile 密度 | frontend | 低 | 3 | 2 | 1 | 中 | 稍後 |
| REVAMP-05 跨裝置 | 假設中的多裝置需求 | 全層 | 高 | ？ | 5 | 4 | 低 | 不建議 |

### 6.4 建議方向

**以 REVAMP-01 為主，搭配 REVAMP-02 的 MVP；REVAMP-03 以小步並行。** 理由如下：

1. **解決的是「信任」**：找不到、匯出不完整、備份過期、編輯被還原，對知識庫的傷害比缺少任何新功能都大。
2. **成本低**：MVP 都是重用既有的 helper，包括 `writeConsistentDBBackup`、`restoreSeparatedContent`，以及既有的 navigate pattern。
3. **不擴大技術面**：沒有新 dependency、不改 schema 版本、沒有新服務。
4. **讓之後每一輪都更便宜**：REVAMP-03 會降低後續開發成本，而且不會阻擋 01 與 02。

---

## 7. New Feature Opportunities

### 7.1 有證據支持的機會

| # | 機會 | 實際問題 | 使用者／頻率 | 能否靠改善既有功能解決？ | Minimum MVP | Tech cost | UI 複雜度 | 維護成本 | Data model | 現在值得做嗎？ |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 桌面版每日自動還原點（OPS-02） | 桌面版沒有任何自動備份；Pi 有 | 所有桌面使用者／每日、自動 | 是：重用 rotate 與一致快照的 helper | 啟動時若 >24h 就建一份，保留 N 份 | 低 | 無（只有記錄） | 低 | 無 | **是**（先決定預設值） |
| 2 | 未存內容保護（UX-02 的一部分） | 關閉分頁或 WebView 時內容直接消失 | 寫作者／偶發但代價高 | 是 | 有未存變更時的 `beforeunload` | 極低 | 無 | 極低 | 無 | **是** |
| 3 | 「把長文合併回筆記」維護動作（FEAT-02b） | 長文分裂造成的全部問題 | 所有長文使用者／一次性 | 是：重用 `restoreSeparatedContent` | dry-run 計數 → 建立還原點 → 逐筆合併 → 檔案移入隔離資料夾 | 中 | 低（Maintenance 一個按鈕） | 低 | 無（只搬資料） | **是（P1）** |

### 7.2 Product Hypothesis（不進 P0/P1）

| ID | 構想 | 為什麼證據不足 | MVP 或觸發條件 | 判定 |
|---|---|---|---|---|
| FEAT-05 | 回收桶（軟刪除與復原） | 刪除是永久的（歷史也會 cascade 刪除），但已有「封存」可替代，也沒有誤刪事件的證據 | 出現誤刪回報後，再做 30 天回收桶（需要 `deleted_at` 欄位） | Future |
| FEAT-06 | 桌面版與 Pi 同步 | 見 REVAMP-05 | 先做 OPS-03 | 不建議 |
| FEAT-07 | Prompt options 自訂 UI | API 已有 CRUD，舊 Vue client 曾有 UI；但沒有使用者需求證據 | 接回既有 API 的簡單管理面板 | Future |
| FEAT-08 | Wiki 連結與 backlinks | 是 PKM 常見功能，但沒有本專案的需求證據 | 需要解析器與關聯表 | Future |
| FEAT-09 | 內建 AI | 治理規則明確禁止，也沒有成本模型 | — | 不建議 |
| BIZ-01 | 非中文使用者的首次體驗 | 英文 UI 下，welcome note、Prompt 模板與長文橫幅仍是中文（`migrations.go:444-446`）；但沒有英文使用者的證據 | 雙語的 welcome note 與模板 | P3 |

---

## 8. Performance & Technical Improvements

### 8.1 實測數據摘要（【RT】【CMD】）

| 情境 | 結果 |
|---|---|
| 一般列表 `GET /api/notes?per_page=20`（約 270 筆） | 5ms |
| 任何關鍵字搜尋（230 篇已拆分的長文） | 256–267ms，每次都是 `partial: time_limit`，只掃描 33–54 個檔案 |
| 搜尋結果第 2 頁 | 259ms（再掃描一次） |
| `LIKE '%詞%'`，10,000 筆 × 1,800 中文字 | 227ms，結果正確 |
| FTS5 trigram（同一份資料） | 3 字以上 <1ms；建索引 36.7s；DB 329MB；2 字仍是 228ms |
| Production bundle | main JS 642,364 B（gzip 200,443）；Settings chunk 88.7kB；PromptBuilder chunk 32.1kB；CSS 56.3kB |
| pytest 全套 | 399 passed：首次（冷建置）238.5s，其中 4 個打包／桌面 smoke 合計 189.3s；新增本報告後再跑一次（Go／npm cache 已熱）72.4s |
| Go tests | ok（package 本身 14.1s；含 build 約 65s）；`go vet` 無警告 |

### 8.2 Frontend

- **PERF-02**（見 §3.5）：mutation 後就地更新，P2。
- **FEAT-01**：Command Palette 對 CJK 的觸發門檻。
- **Bundle：保持現狀。** 本地或 LAN 載入 200kB gzip 的成本很低，route 也已經 lazy 化；把語系拆成 lazy 的收益不足（P3）。
- **R0812:PERF-03** Reading list 預取：P2，維持不變。
- **Prompt options 仍用 raw fetch**（`usePromptBuilder.ts:192,232`），會繞過 axios 的錯誤處理：P3，下次改到 Prompt Builder 時順手處理。

### 8.3 Backend

- **PERF-01**：§3.3。
- **TECH-07**（新，安全）：見下方。
- **OPS-05**：假的 Restart，見下方。
- **TECH-05**：遷移期的字串滲入使用者看得到的地方，見 §9.1。

#### TECH-07 — 附件檢視用 `document.write` 寫入未跳脫的內容（HTML injection，繞過 DOMPurify 的安全邊界）

- **可信度**：High-confidence Inference【SRC】。沒有在 runtime 實際觸發：popup 需要可信的使用者點擊，而本次 browser pane 處於隱藏狀態。
- **證據**：
  - 一般附件的「檢視」會呼叫 `window.open('', '_blank')`，再用 template literal 把原始內容直接寫進 `<pre>${attachmentContent}</pre>`（`useNoteAttachments.ts:80-100`）。
  - `about:blank` 會繼承 opener 的 origin。
  - CSRF gate 只要求同源（`API_REFERENCE.md:42`）。
- **推論**：一個含 `</pre><script>…` 的 .md 或 .txt 附件，在被點開時可以用 app 的 origin 呼叫所有 API。專案其他地方的 Markdown 都有經過 sanitizer（`tests/test_markdown_sanitization.py`），只有這條路徑例外。
- **建議**：改用 `textContent` 建立 `<pre>`，或先跳脫 HTML。一行等級的修改，並補一個 source 或 e2e 回歸測試。
- Impact 3 / Effort 1 / Risk 1 / Confidence 高 / **P0**

附帶的小型 a11y 問題：附件項目是只有 `onClick` 的 `<div>`，沒有 role 或 tabIndex，鍵盤無法操作；刪除按鈕只在 hover 時出現（`AttachmentPanel.tsx:55-96`）。列為 P2，可隨 TECH-07 一起處理。

#### OPS-05 — Server dashboard 的 Restart 回報成功，但實際上沒有重啟

- **可信度**：Observed Fact【SRC】
- **證據**：
  - `handleServerRestart` 只回傳一段 candidate 時期的訊息，不會重啟（`system.go:696-710`）。
  - UI 照樣顯示成功，5 秒後重新整理頁面。
  - 還原點流程有自己真正會重啟的路徑（`backups.go:160-164`）。
- **建議**：改用同一條真正的 restart 路徑，或移除這顆按鈕。
- Impact 2 / Effort 1 / Risk 1 / Confidence 高 / **P2**

### 8.4 Database

- **FEAT-01**（tokenizer）與 **FEAT-02**（內容分裂）：見 §3。
- **PERF-03 — `Note_History` 沒有保留上限**：每次更新都存一份完整的舊內容（`notes_write.go:117`），沒有任何保留策略；`/system/clear-history` 也只剩舊 Vue client 在呼叫。FEAT-02b 之後，長文的歷史會開始存全文，DB 成長會變快（Inference）。屬於「到一定規模再處理」，例如每筆只保留最後 N 版：Future。
- **Index**：現有 index 足以應付個人資料量。沒有 N+1 問題，08-12 的 PERF-01 已改為批次 hydrate。
- **trigram FTS**：Future。條件是資料超過約 1 萬筆、且 3 字以上的查詢占多數。

### 8.5 API

#### TECH-06 — API 表面的衛生問題

- **可信度**：Observed Fact【AGT】＋抽驗
- **現況**：
  - response envelope 有 6 種形狀；功能被關閉時回 405 而不是 403 或 404。
  - 15 條 route 只有舊 Vue client 在用；`api.ts` 有 5 個從未被呼叫的 wrapper。
  - `/api/test` 被當成 stats 來源，同時又有 `/api/system/stats`（見 UX-05）。
  - `.port_config` 寫入後沒人讀取。
  - `UpdateSection.tsx`、`TagInput.tsx` 沒有被引用。
- **建議**：只做「刪除死碼」與「在 API 文件中標註 deprecated」。不做全面統一 envelope，避免破壞外部 agent 的相容性。
- Impact 2 / Effort 2 / Risk 2 / Confidence 中 / **P3**；其中 stats 的部分併入 UX-05（P2）

### 8.6 Deployment

#### OPS-04 — 「localhost-only」的 server API 在 Pi 的反向代理後面會失效，而文件聲稱遠端無法呼叫

- **可信度**：High-confidence Inference【SRC】【DOC】。沒有連到 Pi 實測。
- **證據**：
  - `requireLocalhostRequest` 只檢查 `RemoteAddr`（`system.go:168-178`）。
  - Caddy 設定為 `reverse_proxy 127.0.0.1:5004`（`deploy/raspberry_pi/Caddyfile`），所以所有 LAN 請求在 Go 看來都來自 127.0.0.1。
  - `API_REFERENCE.md:45` 卻寫「遠端 Agent 不可直接呼叫」。
  - 沒有 `Origin` 的 LAN 腳本可以呼叫 restore、logs、備份下載與 full snapshot。
- **背景**：Prism 宣告的安全邊界本來就是可信 LAN（`DEPLOY-PI.md:8`），所以這不是對外網的曝險；但文件的承諾不成立。而且使用者本來就從 LAN 使用 Pi 的 dashboard，修正行為可能直接破壞現有的工作方式。
- **選項**：
  - A：讓文件誠實反映現況。
  - B：把帶有非 loopback `X-Forwarded-For` 的請求視為遠端，並提供 `--allow-lan-admin` 讓 Pi 明確開啟。
  - C：加入 auth（不建議）。
- **建議**：P1 先做 A，B 則開決策關卡。
- Impact 3 / Effort 1（A）、2（B）/ Risk 3（B）/ Confidence 中 / **P1**

#### OPS-06 — Prompt Builder 的 seed config 沒有內嵌在 binary

- **可信度**：Observed Fact【RT】【SRC】
- **現況**：seed 是從五個候選路徑尋找（`options.go:238-263`），`pack.bat` 也沒有附帶。打包版不受影響。
- Impact 1 / Effort 1 / Risk 1 / Confidence 中 / **P3**

其他部署流程（artifact、systemd、Caddy、rollback、soak、portable）沒有證據支持需要重做。

---

## 9. Maintainability / Scalability / Operations

### 9.1 現在值得處理

#### TECH-01 — 版本字串散在 5 處，已造成兩次修正型發版

- **可信度**：Observed Fact【SRC】【DOC】
- **證據**：
  - 版本出現在：`Sidebar.tsx:162`（`V2.6.1`）、`SettingsPage.tsx:196`（fallback `2.6.1`）、`index.html:7`、`system.go:934`（`prismVersion()`），以及仍停在 `2.0.0` 的 `frontend/package.json`。
  - `/api/test` 從不回傳 `version`（`main.go:1005-1027`；`SettingsPage.tsx:90-94` 卻去讀它），所以 About 永遠顯示寫死的 fallback。
  - `docs/TODO.md:42-45,171-197` 記錄了後果：V2.6 上線後 title 與 sidebar 仍顯示 V2.5，於是發了 V2.6.1 並重新部署 Pi；接著 About 仍顯示 2.5，又做了同版重發並再部署一次 Pi。
- **建議**：
  - 以 runtime 為單一來源：`/api/test`（或 `/healthz`）回傳 `prismVersion()`，這是 additive 變更。
  - Sidebar、About、`document.title` 都改讀這個值；`index.html` 只留不含版本的「Prism」。
  - 補一個 Go test 與一個「不得寫死版本號」的 source test。
- Impact 3 / Effort 1 / Risk 1 / Confidence 高 / **P1**

#### TECH-02 — 測試組合：399 個 pytest 只有 27 個真的執行程式，真正的 bug 沒人看守

- **可信度**：Observed Fact【AGT】＋抽驗＋【CMD】
- **證據**：
  - **分類**：R（執行程式）27 個（6.8%）、只讀 source 109 個、只讀文件 235 個（其中 186 個是在斷言 contract JSON 這類證據紀錄）、混合 28 個。
  - **「Behavior」名不符實**：`docs/TEST_PORTFOLIO.md` 所稱的 Behavior 類 100 個測試中，執行型為 0。抽查 5 個檔案共 44 個測試，全部只有 `read_text` 斷言。
  - **與文件綁定**：
    - 51 個測試會讀可變動的文件；其中 16 個綁住 HANDOFF/TODO 的字句。
    - 文件修改曾讓 19–20 個測試失敗（`docs/TODO.md:100`、`HANDOFF.md:20`）。
    - commit `f632cee` 只改了 TODO 的 1 行（+1／−1），卻連帶修改 20 個測試檔（整個 commit 共 21 檔，+78／−53）。
  - **Gate 成本**：
    - 冷建置時（CI 的全新 runner、或剛改過 frontend／Go 之後），4 個打包／桌面 smoke 佔 238.5s 中的 189.3s；cache 已熱時全套只要 72.4s。所以 gate 時間是次要問題，主要問題是測試擋不住真 bug。
    - 測試程式中有 9 個 `go build` 呼叫點（部分位於每個測試都會呼叫的 helper 中），subagent 估計每次 pytest 約執行 22 次 build。
    - `test_desktop_shell_phase1_3.py:83-90` 會在 pytest 裡再跑一次完整的 `go test ./...`。
    - 5 個 Playwright e2e 不在 gate 內。
  - **覆蓋盲點**：
    - 49 個 handler 中有 27 個在 Go tests 裡沒有名稱或 route 引用；`handleSystemVacuum` 與 `handleWALCheckpoint` 完全沒有測試。
    - 沒有 CJK 搜尋測試。
    - `/export/db` 的測試在 WAL 這個 bug 存在的情況下依然通過。
- **影響**：本次找到的 FEAT-01、FEAT-02、OPS-01、UX-01、UX-02 全部屬於「字串斷言抓不到」的行為缺陷。
- **建議**：
  1. 為本次發現的 bug 補 behavior test：Go 的 CJK、WAL 一致性、長文、縮短後被還原；e2e 的 Header New、Ctrl+S、中文搜尋。
  2. gate 分流：預設的 fast gate 跳過 `slow` 與 `historical`；release gate 跑全部測試加 e2e。
  3. 歷史的 docs-text 測試改為 opt-in marker，不刪除。
  4. 不再鎖 HANDOFF/TODO 的字句，改做結構檢查。
- Impact 4 / Effort 3 / Risk 2 / Confidence 高 / **P1**

#### TECH-03 — 文件與治理的負擔：每次開工必讀約 186KB，且有斷鏈

- **可信度**：Observed Fact【CMD】【DOC】
- **證據**：
  - `CLAUDE.md` 的必讀清單合計 186,237 bytes，其中 `ARCHITECTURE.md` 62KB，大半是遷移期的 phase 敘事（例如 `:144-214`）；`TODO.md` 52KB 雖然寫著「只放 active」，卻以完成項為主；`HANDOFF.md` 16KB 含 SHA256 證據。
  - 斷鏈：`CLAUDE.md:28` 與 `AGENTS.md` 指向不存在的 `docs/New_UI/`；`docs/INDEX.md`、`docs/README.md`、`CONTRIBUTING.md` 指向不存在的 `docs/過期/`。
  - `docs2/` 與 `development-history/governance-source-20260705/` 逐檔相同；根目錄的 `PROJECT_REVIEW.md` 已被取代。
  - 為了讓歷史測試通過，`ARCHITECTURE.md:193` 必須保留「retained-Python normal path」這句已經過時的話【AGT】。
- **影響**：每個 agent session 開工前都要先讀數萬 token；改文件會連帶要改測試。
- **建議**：
  - 給必讀文件設預算（約 60KB 以內）。
  - 歷史敘事移到 `development-history/`。
  - 修正斷鏈；刪除重複的 `docs2/`。
  - HANDOFF 控制在約 4KB 以內。
  - 與 TECH-02 第 4 點一起解除文件鎖字。
- Impact 3 / Effort 2 / Risk 1 / Confidence 高 / **P1**

#### TECH-04 — Repo 的死重量：node_modules 74MB 入庫而且不完整

- **可信度**：Observed Fact【CMD】【AGT】＋抽驗
- **證據**：
  - **node_modules**：
    - `frontend/node_modules` 有 3,890 個檔案、74.1MB，佔 HEAD tree 的 72%，在 `75c4711`（2026-01-28）被誤加入版控，雖然 `frontend/.gitignore:2` 早就忽略它。
    - 它**缺少 `dompurify`**（`markdown.ts:1` 依賴這個套件）。
    - `scripts/start_v2_dev.bat:12-16` 在資料夾已存在時會跳過 `npm install`，所以全新 clone 之後用 dev script 會 build 失敗。
    - 被追蹤的 `.vite/deps` 會在 `npm run dev` 時被改寫（08-12 審查曾遇到這個副作用）。
  - **其他死資產**：
    - `resources/`（23.7MB，沒有任何引用）。
    - `static/js|css|lib|locales|fonts`（舊 Vue 前端，Go 不會提供這些檔案；`main.go:760-799`）。
    - 與歷史資料夾完全相同的 `docs2/`。
    - `tools/`。
    - 5 個死 script，其中 `scripts/clean_test_data.py` 會先複製一份備份，然後**不經確認就清空 `./knowledge.db` 的 Notes、Note_Tags、Source_Urls、Note_History**（`:43-46`）。
    - 指向已刪除 `app.py` 的 `.vscode/launch.json`。
    - `vite.config.ts` 中過時的 proxy（`/prompt-builder.html`、`/templates`）。
    - 不存在的 favicon `/vite.svg`。
- **建議**：
  - `git rm -r --cached frontend/node_modules`。
  - 刪除上述死資產，但**不可**動到 `static/config` 與 `static/uploads`（本地開發時的 data-dir 是 repo root）。
  - 被測試鎖住的 shim（`desktop-spike/`、`install.*`、`requirements-pi.txt`）另外處理。
  - 不改寫 git history。
- Impact 3 / Effort 1 / Risk 1 / Confidence 高 / **P1**

#### TECH-05 — 遷移期的命名與旗標滲入使用者看得到的地方

- **可信度**：Observed Fact【RT】【SRC】
- **證據**：
  - flag 說明寫著「parity candidate」（`main.go:148-160`）。
  - Restart 回應「Go local server-system candidate…」（`system.go:700-709`）。
  - 啟動 log 寫「Prism Go runtime proof listening」【RT】。
  - 附件錯誤訊息寫「remain Python-owned」【AGT】。
  - 桌面版正式 DB 的檔名是 `prism_desktop_dev.db`（`main.go:203-205`）。
- **建議**：
  - 使用者看得到的字串改為中性文案：P2，Effort 1。
  - flags 本身保留：全面移除的波及面太大，P3。
  - DB 檔名牽涉使用者資料，不在沒有 migration 的情況下改名，只在 OPS-03 的文件中說明。
- Impact 2 / Effort 1 / Risk 1 / Confidence 高 / **P2**（flags 部分 P3）

OPS-02 已在 §3.8 說明。

### 9.2 到一定規模再處理

- 附件文字索引：FEAT-02b 之後，若文字附件仍超過約 50 個，再評估（需改 schema）。
- PERF-03 `Note_History` 保留策略。
- R0812:PERF-03 Reading list 預取。
- trigram FTS：超過約 1 萬筆，且 3 字以上的查詢為主時。
- 標籤數量破百之後，清單的搜尋與虛擬化。

### 9.3 不需要處理

- 換資料庫、微服務、queue、Redis。
- 全域 state 重寫、design system。
- 本地工具內建帳號系統。
- 依語系拆 bundle、`go-shadow` 改名、全面清除 flags（P3）。

### 9.4 Future Consideration（不進 P0/P1）

跨裝置同步（REVAMP-05）、多人協作、AI、telemetry、回收桶（FEAT-05）、backlinks（FEAT-08）。

### 9.5 使用者 ×10、資料 ×10、功能 ×2：哪裡最先變痛

| 變化 | 最先變痛 | 現有跡象 | 分類 |
|---|---|---|---|
| 長文或文字附件 ×10（≥50 個） | PERF-01：搜尋觸頂、延遲 260ms、長文後段搜不到 | 已實測 | **現在修**（FEAT-02b） |
| 筆記 ×10（約 3,000 筆） | CJK LIKE 掃描約 70ms（由 benchmark 推估） | benchmark | 可接受；超過 1 萬筆再評估 trigram |
| 編輯次數 ×10 | `Note_History` 沒有上限 | source | 到一定規模再處理 |
| Reading list ×10 | R0812:PERF-03 | source | P2 |
| 功能 ×2 | 測試與文件鎖字、Settings 擁擠 | TECH-02、TECH-03、IA-02 | TECH 現在處理；IA 稍後 |
| 使用者 ×10（各自本地） | 沒有共用瓶頸；但備份責任分散到每一台桌面 | OPS-02 | 自動還原點 |

### 9.6 Business／Operations

**目前不需要商業化或營運設計。** Repo 中沒有商業模式、付費或多人服務的證據，產品也沒有外部 AI 或 API 成本。

- **Activation**：welcome note 與 New CTA 已足夠。唯一的問題是非中文使用者的首次體驗（BIZ-01，P3）。不需要 onboarding wizard。
- **Retention**：歷史、置頂、saved views、reading list、Prompt 模板已提供自然的回訪理由。不需要通知、streak 或點數。
- **Cost**：沒有 AI、API 或頻寬成本。
- **Operations**：
  - 現在需要：可信的 DB 複本（OPS-01）、桌面版自動還原點（OPS-02）、snapshot 還原說明（OPS-03）、誠實的 LAN 邊界文件（OPS-04）。
  - 未來才可能需要：error telemetry、admin、moderation、billing、rate limit——只有變成 hosted 或多人產品時才成立。

### 9.7 大型改善方案比較

| 候選 | Option A：保持現狀 | Option B：最小改善 | Option C：結構性改善 | 建議 |
|---|---|---|---|---|
| 中文搜尋 | 零成本；繁中搜尋持續失效 | CJK 時加上 LIKE fallback（無 schema；成本 O(內容量)） | trigram FTS（schema v18；索引是全文的數倍；2 字詞仍需掃描） | **B** |
| 長文存放 | 匯出、歷史、搜尋失真；編輯會被還原 | 停止新拆分，並修正已拆分筆記的存檔 | B＋合併回 DB（重用 restore 邏輯、備份、dry-run） | **先 B（P0）再 C（P1）** |
| DB 複本 | 漏掉最近的寫入 | 改用一致快照 | 移除重複的按鈕與 API | **B**（API 保留相容） |
| 測試 | 全綠但不擋真 bug；4 分鐘 | 補 behavior test、gate 分流、歷史測試 opt-in | 全面重寫測試套件 | **B**（禁止 big-bang） |
| 文件 | 每次讀 186KB；鎖字 | 瘦身、修斷鏈、解除鎖字 | 重建文件系統 | **B** |
| 桌面版備份 | 沒有 | 啟動時每日一份還原點 | 常駐排程，並備份上傳檔 | **B**（需決策） |
| LAN 管理 API | 文件不實 | 修正文件 | 依 forwarded header 判斷，加上 opt-in flag | **先 B，C 進決策關卡** |
| Header 全域動作 | 靜默失效 | 先導向 `/` | 把 editor 掛到 Layout 層 | **B**（沿用既有 pattern） |

---

## 10. Highest ROI + Product Evolution Roadmap

詳細說明只在首次出現處；此處只引用 ID。

### 10.1 Top 10 Highest ROI Improvements

| 排名 | ID | 改善 | Impact | Effort | Risk | Confidence | Priority |
|---:|---|---|---:|---:|---:|---|---|
| 1 | OPS-01 | DB 複本改用一致快照 | 5 | 1 | 1 | 高 | P0 |
| 2 | UX-01 | Header New 與搜尋在任何頁面都有效 | 4 | 1 | 1 | 高 | P0 |
| 3 | TECH-07 | 附件檢視不再寫入未跳脫的 HTML | 3 | 1 | 1 | 高 | P0 |
| 4 | FEAT-02a | 停止新的長文拆分，修正「縮短後被還原」 | 5 | 2 | 2 | 高 | P0 |
| 5 | FEAT-01 | CJK 子字串搜尋與 palette 門檻 | 5 | 2 | 2 | 高 | P0 |
| 6 | TECH-01 | 版本單一來源 | 3 | 1 | 1 | 高 | P1 |
| 7 | TECH-04 | node_modules 移出版控、清除死資產 | 3 | 1 | 1 | 高 | P1 |
| 8 | FEAT-02b（含 PERF-01） | 合併長文回筆記 | 5 | 3 | 3 | 高 | P1 |
| 9 | UX-02 | Ctrl+S 存檔後留在原處、未存內容保護 | 4 | 2 | 2 | 高 | P1 |
| 10 | TECH-02 | behavior test 補強、gate 分流 | 4 | 3 | 2 | 高 | P1 |

### 10.2 Roadmap

#### P0（現在）

OPS-01 → TECH-07 → UX-01 → FEAT-01 → FEAT-02a。

每項都附帶自己的回歸測試，彼此之間沒有依賴，可以平行進行。

#### P1（下一輪）

1. FEAT-02b（依賴 FEAT-02a，且執行前必須先建立還原點）。順帶解決 PERF-01。
2. UX-02、UX-03。
3. FEAT-03（文案）。
4. TECH-01、TECH-04（越早做，越早讓全新 clone 可以 build）。
5. TECH-02（behavior test 與 gate 分流）→ TECH-03（文件瘦身，需配合 TECH-02 解除鎖字）。
6. OPS-02、OPS-04：兩者都先做決策關卡。

#### P2（有價值，可稍後）

UX-04、UX-05、PERF-02、IA-01、IA-02、OPS-03、OPS-05、TECH-05（字串部分）、R0812:PERF-03、附件項目的鍵盤可及性。

#### P3（目前不建議）

UX-06、OPS-06、TECH-06、TECH-05 的 flags 移除、BIZ-01、trigram FTS、bundle 與語系拆分、`go-shadow` 改名。

#### Future

FEAT-05、FEAT-06／REVAMP-05、FEAT-07、FEAT-08、FEAT-09、PERF-03 保留策略、附件文字索引。

### 10.3 下一輪「不要做」的事

- 不加新功能：回收桶、同步、backlinks、Prompt options UI、AI。
- 不做視覺翻新、不做 design system、不重做 Settings 或導覽。
- 不換 DB 或 framework，不導入 trigram 或任何新索引表，不升 schema 版本。
- 不做全面的 flags 移除、`go-shadow` 改名，也不改寫 git history。
- 不在合併長文之前「先修匯出」：直接解決根因，避免寫出很快就變成死碼的相容邏輯。

---

## 11. 可直接交給 LLM 的後續 Tasks（只列 P0／P1）

> 本節是審查當下的快照。所有 findings（含 P2／P3／Future）已轉為工單：最新規格以 `docs/WORK_ORDERS.md` 為準，狀態看 `docs/TODO.md` 看板。

共同規則：

- 每個 task 都可以單獨開 branch、單獨 commit、單獨 review、單獨 rollback。
- 遵守 `AGENTS.md`／`CLAUDE.md`、`docs/GOVERNANCE.md` 與反膨脹原則；不新增 dependency；API 只能做 additive 變更。
- 不碰正式的 `knowledge.db`；完成後依規範回寫 `docs/TODO.md` 與 `HANDOFF.md`。
- UI task 必須檢查 loading、empty、error、success、disabled、keyboard、focus 這些狀態，並在 desktop 與 390px 實際用瀏覽器驗證。
- 共同驗證指令（各 task 另有補充）：

```bash
cd go-shadow && go test ./...
```

```bash
pytest tests/ -v
```

```bash
cd frontend && npm run build
```

```bash
git diff --check
```

### PRISM-OPT-15 — DB 複本下載改為一致快照

| 項目 | 內容 |
|---|---|
| 對應 Improvement | OPS-01 |
| 目標 | `GET /api/export/db` 一定要包含最近一次提交的所有寫入 |
| 原因 | 目前直接串流 live 主檔，會漏掉還在 WAL 裡的資料；fresh DB 甚至會下載到空殼 |
| 修改範圍 | `go-shadow/export.go` `handleExportDB`：比照 `handleBackupDownload`（`backups.go:21-48`），先用 `writeConsistentDBBackup` 寫到暫存檔、送出，最後刪除暫存檔；`go-shadow/main_test.go` 補測試 |
| 不要修改 | API 路徑、檔名格式、Content-Type、gate 條件；`backups.go` 的行為；UI 版面 |
| UX／Behavior 規格 | 使用者看不到任何差異，只是下載內容一定是最新的 |
| Acceptance Criteria | 測試在開啟 DB 後寫入一筆（不 checkpoint），下載的 .db 必須含這筆；fresh DB 下載後可以查到 `Notes` 表；暫存檔不殘留 |
| Verification | `cd go-shadow && go test ./...`；`pytest tests/ -v` |

### PRISM-OPT-16 — 附件檢視的安全輸出

| 項目 | 內容 |
|---|---|
| 對應 Improvement | TECH-07 |
| 目標 | 檢視一般文字附件時，內容一律以純文字呈現 |
| 原因 | `useNoteAttachments.ts:89-97` 用 template literal 把原始內容寫進同源 popup，形成 HTML injection |
| 修改範圍 | `useNoteAttachments.ts` `handleLoadAttachment`：用 DOM API 建立 `<pre>` 並設定 `textContent`，或先跳脫 HTML；可以順便讓 `AttachmentPanel.tsx` 的項目改用 `<button>` 或加上 `role` 與 `tabIndex`，以支援鍵盤操作 |
| 不要修改 | auto-extracted 附件的載入流程（屬於 FEAT-02 的範圍）、上傳與刪除 |
| UX／Behavior 規格 | 含 `<b>`、`<script>`、`</pre>` 的附件會原樣顯示為文字 |
| Acceptance Criteria | 新增回歸測試：source test 確認沒有用 `document.write` 寫入 `${attachmentContent}`，或用 e2e 驗證 popup 中不會出現被注入的元素；附件項目可以用 Tab 與 Enter 開啟 |
| Verification | `cd frontend && npm run build`；`pytest tests/ -v` |

### PRISM-OPT-17 — Header 全域動作改為 route-aware

| 項目 | 內容 |
|---|---|
| 對應 Improvement | UX-01 |
| 目標 | 在任何 route 按 New 都能立刻開啟編輯器；在任何 route 送出搜尋都能看到結果 |
| 原因 | NoteEditor 只掛在 HomePage；Header 沒有導回 `/`，造成靜默失效，之後還會「鬼開啟」 |
| 修改範圍 | `frontend/src/components/Header.tsx`：New 與 `handleSearchSubmit` 在 `!isHomeRoute` 時先 `navigate('/')`，寫法比照 `Header.tsx:116`；i18n 不變 |
| 不要修改 | `appStore`、HomePage 的 overlay 結構、API |
| UX／Behavior 規格 | 從 `/settings` 或 `/prompt-builder` 按 New：導到 Library 並立即開啟「New note」。搜尋：導到 Library 並顯示結果 |
| Acceptance Criteria | browser smoke（desktop 與 390px）：兩個 route 各驗證 New 與搜尋；不再出現稍後才彈出的編輯器；console 沒有錯誤 |
| Verification | `cd frontend && npm run build`；隔離 runtime 的 browser smoke；`pytest tests/ -v` |

### PRISM-OPT-18 — CJK 子字串搜尋

| 項目 | 內容 |
|---|---|
| 對應 Improvement | FEAT-01 |
| 目標 | 中文與日文的詞出現在標題或內文的任何位置都能搜到；palette 輸入 2 個 CJK 字就會查詢 server |
| 原因 | `unicode61` 的前綴查詢對沒有空白的語言無效 |
| 修改範圍 | `go-shadow/notes_search.go` `buildNotesSearchClause`：當 token 含 Han、Hiragana 或 Katakana 時，額外加上 `(LOWER(COALESCE(n.title,'')) LIKE ? OR LOWER(COALESCE(n.content,'')) LIKE ?)` 的 OR 分支（多個 token 之間 AND；token 已經過 `searchTokens` 淨化，不含 `%` 或 `_`）。`frontend/src/components/CommandPalette.tsx`：CJK 輸入的門檻改為 2。Go test 使用中文 fixture |
| 不要修改 | FTS5 schema 與 tokenizer、migration、附件掃描上限、英文查詢的行為 |
| UX／Behavior 規格 | 不需要額外 UI；查詢結果變得正確 |
| Acceptance Criteria | fixture「今天學習提示詞工程的方法…」對「工程」「角色設定」「夜景」都能命中；英文的既有測試全部不變；以 1,000 筆中文 fixture 量測查詢時間並記錄在 PR |
| Verification | `cd go-shadow && go test ./...`；`cd frontend && npm run build`；`pytest tests/ -v` |

### PRISM-OPT-19 — 停止新的長文拆分，修正已拆分筆記的存檔路徑

| 項目 | 內容 |
|---|---|
| 對應 Improvement | FEAT-02a |
| 目標 | 新的長文保留在 `Notes.content`；已拆分的筆記存檔後也回到 DB，不會再被舊附件覆蓋 |
| 原因 | 拆分讓匯出、歷史、API 失真，而且縮短後的編輯會被舊附件還原【RT】 |
| 修改範圍 | `frontend/src/hooks/editor/useNoteForm.ts`：移除儲存後呼叫 `separateContent` 的程式碼（`:123-129`）。若筆記有 auto-extracted 附件，且全文已經成功載入：先呼叫既有的 `api.restoreContent(noteId)`（`POST /notes/:id/restore`，會把檔案收回 DB，並刪除附件列與檔案），**再** PUT 表單內容；遇到 404（檔案已不存在）就直接 PUT。若全文**沒有**成功載入（`useNoteAttachments` 的 `loadFullFailed`），就禁止存檔並顯示錯誤。`useNoteAttachments.ts` 需要提供「全文已載入」的狀態 |
| 不要修改 | 後端 `separate`、`check_separation`、`restore` endpoint（維持 API 相容）；schema；尚未被編輯的已拆分筆記；匯出程式 |
| UX／Behavior 規格 | 使用者看不到任何新的 UI；編輯過的長文從此完整存在 DB 中 |
| Acceptance Criteria | e2e 或整合測試：新建 6,000 字筆記後，`GET /api/notes/:id` 回傳全文，且沒有附件；已拆分的筆記改成 34 字並存檔後，重開編輯器看到 34 字，附件與檔案都已移除；修改已拆分的長文後，歷史中有一筆完整的舊版；全文載入失敗時無法存檔 |
| Verification | `cd frontend && npm run build`；`cd go-shadow && go test ./...`；隔離 runtime 的 browser 流程；`pytest tests/ -v` |

### PRISM-OPT-20 — 「合併長文回筆記」維護動作

| 項目 | 內容 |
|---|---|
| 對應 Improvement | FEAT-02b（含 PERF-01） |
| 目標 | 一次把既有的 auto-extracted 長文合併回 `Notes.content` |
| 原因 | 讓搜尋、匯出、歷史、DB 備份、API 都完整；附件掃描量只剩真正的使用者附件 |
| 修改範圍 | 後端新增一個 additive 端點（例如 `POST /api/system/inline-separated-notes`，支援 `dry_run`），由 server-system gate 保護。執行前用 `writeConsistentDBBackup` 建立還原點；逐筆重用 `restoreSeparatedContent` 的語意，但把檔案**移到** `backups/separated-notes-<ts>/` 而不是刪除；冪等。前端在 Maintenance 加一個帶有 dry-run 預覽與確認的按鈕，四語 i18n |
| 不要修改 | schema 版本、自動在啟動時執行、使用者手動上傳的附件、export 格式 |
| UX／Behavior 規格 | dry-run 先顯示「N 篇可合併、M 篇缺檔」，確認後執行並回報結果；缺檔的筆記保持原狀並列出 |
| Acceptance Criteria | Go test：2 篇已拆分、1 篇缺檔、1 篇一般筆記 → dry-run 計數正確；執行後 FTS 能找到尾段關鍵字、JSON 與 MD 匯出包含全文、檔案已移入隔離資料夾；第二次執行的變更數為 0；還原點確實存在 |
| Verification | `cd go-shadow && go test ./...`；`pytest tests/ -v`；`cd frontend && npm run build`；隔離資料的 browser smoke |

### PRISM-OPT-21 — Ctrl+S 存檔後留在原處，加上未存內容保護

| 項目 | 內容 |
|---|---|
| 對應 Improvement | UX-02 |
| 目標 | Ctrl+S 存檔但不關閉編輯器；新筆記第一次存檔後轉為編輯既有筆記；有未存變更時離開頁面會先提示 |
| 原因 | 目前存檔就會被踢出編輯器，而且關閉時沒有任何保護 |
| 修改範圍 | `useNoteForm.ts`：拆出 `save({ close })`；Ctrl+S 呼叫 `close: false`，成功後更新 `originalSnapshot`；新筆記用回傳的 `note_id` 取回筆記，再透過 store 換成 editing 狀態。`hasUnsavedChanges` 為 true 時註冊 `beforeunload`。Save 按鈕維持存檔並關閉 |
| 不要修改 | 驗證規則、toast 文案的 key、API |
| UX／Behavior 規格 | Ctrl+S 顯示「已儲存」的 toast 並留在編輯器；第二次 Ctrl+S 是更新而不是新建；關閉分頁時出現瀏覽器原生提示 |
| Acceptance Criteria | e2e：新筆記連按兩次 Ctrl+S 只會產生 1 筆；有未存變更時觸發 `beforeunload`；Save 按鈕行為不變 |
| Verification | `cd frontend && npm run build`；e2e 或 browser smoke（desktop 與 390px）；`pytest tests/ -v` |

### PRISM-OPT-22 — 預覽狀態的最小語意修正

| 項目 | 內容 |
|---|---|
| 對應 Improvement | UX-03 |
| 目標 | 以預覽模式開啟時，看起來與操作起來都是「預覽」 |
| 原因 | 目前 heading 是「Edit note」，標題輸入框會 autoFocus，任何按鍵都會改到標題 |
| 修改範圍 | `NoteEditor.tsx`、`EditorToolbar.tsx`、i18n（四語）：preview 時 heading 改為「預覽筆記」，標題以 heading 呈現且不 autoFocus；切換到 Edit 後才顯示標題 input 與 Save（有未存變更時 Save 一律顯示）；保留 EditablePreview 的「Edit this block」 |
| 不要修改 | `cardOpenMode` 設定、ReadingView、卡片的主要點擊目標 |
| UX／Behavior 規格 | 開啟預覽後按鍵不會改到標題；點「編輯」後的行為與現在相同 |
| Acceptance Criteria | browser 驗證：預覽態沒有被 focus 的 input；Edit 與 Preview 來回切換正常；鍵盤 focus 落在 dialog 內 |
| Verification | `cd frontend && npm run build`；browser smoke（desktop 與 390px）；`pytest tests/ -v` |

### PRISM-OPT-23 — 匯出範圍文案誠實化

| 項目 | 內容 |
|---|---|
| 對應 Improvement | FEAT-03 |
| 目標 | JSON、Markdown、.db 各自說清楚包含與不包含什麼，並導向 Full snapshot |
| 原因 | 「Download all notes… bring them back」過度承諾 |
| 修改範圍 | `BackupImportSection.tsx` 對應的 i18n key（四語），以及鎖定這些文案的 source test |
| 不要修改 | 匯出格式與欄位（補欄位列為 P2） |
| UX／Behavior 規格 | JSON 標明是「可攜的文字副本（不含置頂、封存、歷史、附件檔、圖片）」；Markdown 標明「不含文字附件」；三者都附上「完整備份請用 Full snapshot」 |
| Acceptance Criteria | 四語都更新；390px 下沒有文字溢出 |
| Verification | `cd frontend && npm run build`；`pytest tests/ -v` |

### PRISM-OPT-24 — 版本單一來源

| 項目 | 內容 |
|---|---|
| 對應 Improvement | TECH-01 |
| 目標 | 發版時只需要改 `prismVersion()`（以及 README 的 badge 與文件） |
| 原因 | 5 處寫死的版本已造成兩次修正型發版 |
| 修改範圍 | `main.go` `handleTest` 回傳中加入 `version`（additive）；前端在啟動時讀一次（可以擴充現有 store），供 Sidebar、About、`document.title` 使用；`index.html` 的 title 改為「Prism」；`frontend/package.json` 的 version 同步，或註明不使用；Go test 加上禁止寫死版本號的 source test |
| 不要修改 | `/api/server/version` 的 gate；release 流程的其他步驟 |
| UX／Behavior 規格 | 與現在顯示相同的版本號 |
| Acceptance Criteria | 把 `prismVersion()` 改成假的值後，三個 UI 位置都跟著變；source test 確認 `Sidebar.tsx`、`SettingsPage.tsx`、`index.html` 中沒有 `\d+\.\d+\.\d+` 這類版本字面值 |
| Verification | `cd go-shadow && go test ./...`；`cd frontend && npm run build`；`pytest tests/ -v`；browser 確認 title、sidebar、About |

### PRISM-OPT-25 — node_modules 移出版控，清除死資產

| 項目 | 內容 |
|---|---|
| 對應 Improvement | TECH-04 |
| 目標 | 全新 clone 後可以照文件 build；repo 不再追蹤沒有被引用的檔案 |
| 原因 | 74MB 的 node_modules 不完整而且會誤導；還有一個死 script 會清空本地的 DB |
| 修改範圍 | `git rm -r --cached frontend/node_modules`；刪除 `resources/`、`static/{js,css,lib,locales,fonts}`、`docs2/`、`tools/`、5 個死 script、`.vscode/launch.json` 的 Flask 設定、`vite.config.ts` 過時的 proxy、`index.html` 不存在的 favicon；必要時更新只鎖這些路徑的測試 |
| 不要修改 | `static/config`、`static/uploads`、`knowledge.db`、`desktop-spike/`、`install.*`、`requirements-pi.txt`（這些被測試鎖住的 shim 另外處理）；不改寫 git history |
| UX／Behavior 規格 | 無使用者可見的變化 |
| Acceptance Criteria | 在暫存目錄全新 clone 後，`cd frontend && npm ci && npm run build` 成功；`git ls-files frontend/node_modules` 為空；runtime、scripts、CI 都沒有引用已刪除的路徑；CI 綠燈 |
| Verification | `pytest tests/ -v`；`cd go-shadow && go test ./...`；fresh-clone build；`git diff --check` |

### PRISM-OPT-26 — 補強 behavior test，gate 分流

| 項目 | 內容 |
|---|---|
| 對應 Improvement | TECH-02 |
| 目標 | 本報告找到的每一類 bug 都由執行型測試看守；日常的 gate 縮短；歷史測試不再干擾日常開發 |
| 原因 | 399 個測試只有 27 個會執行程式，P0 那幾個 bug 都在全綠的狀態下存在 |
| 修改範圍 | （a）Go tests：CJK、WAL 一致性、長文 inline 與縮短後被還原（若前面的 task 尚未補）。（b）把 3 條 e2e（非 Home 的 New、Ctrl+S、中文搜尋）放進 release gate，並把 `pytest-playwright` 列入相依。（c）`pytest.ini` 加上 `slow`（4 個打包／桌面 smoke）與 `historical`（只讀文件的 phase19–23 模組）marker；`.loop/verify-gate.ps1` 預設跑 fast（`-m "not slow and not historical"`），`-Release` 跑全部；CI 跑 release。（d）移除 pytest 中重複執行的 `go test ./...`，或改標為 slow |
| 不要修改 | 不刪除任何測試；不降低 migration、release、package 的 safety 覆蓋；不改 runtime |
| UX／Behavior 規格 | — |
| Acceptance Criteria | fast gate 的冷建置與熱快取時間都量測並記錄在 PR，冷建置時間應明顯低於目前的 238s；release gate 與現在的覆蓋相同，再加上 e2e；`docs/TEST_PORTFOLIO.md` 依實際執行性重新分類 |
| Verification | `pwsh -NoProfile -File .loop/verify-gate.ps1` 與 `-Release` 兩種都跑；CI 綠燈 |

### PRISM-OPT-27 — 文件瘦身，修正斷鏈

| 項目 | 內容 |
|---|---|
| 對應 Improvement | TECH-03 |
| 目標 | 必讀文件合計不超過約 60KB；沒有斷鏈；文件修改不會讓測試失敗 |
| 原因 | 每次開工要讀 186KB；斷鏈；文件鎖字 |
| 修改範圍 | `ARCHITECTURE.md` 只保留 current truth，phase 敘事移到 `development-history/`；`HANDOFF.md` 控制在約 4KB 以內；`TODO.md` 只留 active；修正 `CLAUDE.md`／`AGENTS.md` 中的 `docs/New_UI` 與各處 `docs/過期` 斷鏈；刪除重複的 `docs2/`；根目錄的 `PROJECT_REVIEW.md` 移到歷史資料夾；把鎖 HANDOFF/TODO 字句的測試改為結構檢查（例如標題存在） |
| 不要修改 | contract JSON 與歷史紀錄的內容；治理規則的實質內容 |
| UX／Behavior 規格 | — |
| Acceptance Criteria | `CLAUDE.md` 與 `AGENTS.md` 保持鏡像；必讀文件合計 ≤60KB；link 檢查沒有斷鏈；`pytest` 綠燈 |
| Verification | `git diff --no-index --exit-code CLAUDE.md AGENTS.md`；`pytest tests/ -v`；`git diff --check` |

### PRISM-OPT-28 — 桌面版每日自動還原點（先過決策關卡）

| 項目 | 內容 |
|---|---|
| 對應 Improvement | OPS-02 |
| 目標 | 桌面版使用者在什麼都不做的情況下，最多只會失去 24 小時的 DB 變更 |
| 原因 | Go runtime 沒有排程；只有 Pi 有每週 timer |
| 修改範圍 | 先在 TODO 開決策關卡：預設是否開啟、N 的值、是否只限桌面版。決定後才在 desktop shell 啟動且 runtime 健康之後執行一次檢查：最新的還原點若超過 24 小時，就用 `writeConsistentDBBackup` 建一份，並以 `enforceBackupRetention` 保留 N 份；結果寫進 log |
| 不要修改 | 常駐排程、上傳檔的備份、Pi 的 timer、還原流程 |
| UX／Behavior 規格 | 背景完成，不阻擋 UI；失敗只記 log，並在 Maintenance 的總覽可以看到 |
| Acceptance Criteria | Go 單元測試涵蓋「應不應該建立」的判斷與 retention；隔離 data-dir 的 smoke：啟動兩次只建立 1 份 |
| Verification | `cd go-shadow && go test ./...`；desktop shell smoke（`scripts/smoke_desktop_portable.ps1`） |

### PRISM-OPT-29 — LAN 管理邊界：文件誠實化，加上決策關卡

| 項目 | 內容 |
|---|---|
| 對應 Improvement | OPS-04 |
| 目標 | 文件與實際行為一致；是否收緊交由使用者決定 |
| 原因 | Pi 經 Caddy 代理後，「localhost-only」的 API 可以從 LAN 呼叫 |
| 修改範圍 | 第一階段（docs-only）：在 `API_REFERENCE.md:45` 與 `DEPLOY-PI.md` 的安全邊界段落說明，Pi 經反向代理時 `/api/server/*` 與 full snapshot 對 LAN 開放。第二階段（決策之後）：`requireLocalhostRequest` 把帶有非 loopback `X-Forwarded-For`／`Forwarded` 的請求視為遠端，並新增 `--allow-lan-admin`（Pi deploy scripts 明確傳入，以保留現有的 dashboard 用法） |
| 不要修改 | 加入 auth；改動 CSRF gate；改變 Caddy 對外的暴露範圍 |
| UX／Behavior 規格 | 第一階段無行為變化 |
| Acceptance Criteria | 第一階段：文件不再聲稱遠端無法呼叫。第二階段：測試涵蓋 direct loopback 允許、forwarded 的 LAN 請求在未開 flag 時回 403、開 flag 後允許 |
| Verification | 第一階段：`git diff --check`、`pytest tests/ -v`。第二階段：再加 `cd go-shadow && go test ./...` |

---

## 12. Review Limitations

### 12.1 Observed Fact

- 實測環境：以 HEAD 建置的隔離 Go binary（嵌入的 dist 是本次 pytest 的打包 smoke 剛 build 出來的）；scratch 目錄中的 fresh DB；合成資料；內建 Chromium 的 desktop 1440×900 與 mobile 375×812。
- **沒有**實測：Windows portable WebView2、Pi live、真實手機、Safari/Firefox、螢幕閱讀器。
- 沒有讀取使用者的 `knowledge.db`，也沒有讀取 Pi 的資料。合成資料只能代表「結構」，不能代表真實的資料分布。
- 程式碼、指令、文件都以 `5e8381f` 為準；開始與結束時 `git status` 都是乾淨的。

### 12.2 High-confidence Inference

- 主要語言是繁中；使用者是單人。
- PERF-02 的列表重置會讓捲動位置遺失（依 source 推論，沒有實際捲動驗證）。
- TECH-07 的 HTML injection：source 很明確，但 popup 需要可信的使用者點擊，本次 pane 處於隱藏狀態，所以沒有在 runtime 觸發。
- OPS-04 的 LAN 可達性：依 source 與 Caddyfile 推論，沒有連到 Pi 驗證。
- JSON 匯出再匯入會遺失置頂、封存與譜系：依欄位清單推論，沒有實際匯回驗證。
- PERF-01 觸頂時被略過的是較新的檔案：依 SQLite 不指定 ORDER BY 時的常見行為推論。

### 12.3 Product Hypothesis

回收桶、跨裝置同步、Prompt options UI、backlinks、非中文使用者族群，以及 reading list 與 custom order 的實際價值。

### 12.4 Unknown

- 真實使用者有多少長文與文字附件（決定 PERF-01 的實際嚴重度）。
- Pi SD 卡上每個檔案的掃描成本。
- 實際的使用頻率與 persona（沒有 analytics）。
- main bundle 從 598.0kB 增加到 642.4kB 的原因：source 只改了 41 行，可能是量測方式或相依套件漂移。

### 12.5 未執行或無法完整驗證

| 檢查 | 狀態 | 原因與影響 |
|---|---|---|
| `python -m pytest e2e` | 未執行 | 不在 gate 內；需要 `pytest-playwright`；其 fixture 會 build 到 repo 內的 `build/`。改以內建 browser 手動驗證 |
| `npm run lint` | 無法執行 | 沒有 lint script |
| Windows portable 打包與 WebView2 | 未執行 | 避免動到使用者的桌面資料；桌面行為依 source 判斷 |
| Pi live | 未執行 | 沒有連線；OPS-04 屬於推論 |
| Full snapshot 下載與手動還原 | 未執行 | 依 source 與 contract；完整性在 08-12 已有證據 |
| 還原點的 restore 流程 | 未執行 | 會讓 process 重啟；依 `restore_test.go` 與 source 判斷 |
| 附件 HTML injection 的 runtime 觸發 | 未完成 | 合成點擊沒有 user activation，popup 被擋；pane 隱藏時無法做可信點擊 |
| Prompt Builder 首次載入 | 失敗後補救 | fresh data-dir 沒有 seed（屬於 OPS-06）；把 repo 的 `static/config` 複製到隔離 data-dir 後成功 |
| browser 截圖 | 數次逾時後重試成功 | pane 重繪逾時；改以 DOM／JS 讀值作為主要證據 |

---

## 13. Appendix

### 13.1 掃描的主要目錄

`frontend/`（src、設定、dist、tracked node_modules）、`go-shadow/`、`docs/`（含 contracts、development-history 的索引）、`tests/`、`e2e/`、`scripts/`、`static/`、`resources/`、`deploy/`、`desktop-spike/`、`docs2/`、`tools/`、`.github/workflows/`、`.loop/`、根目錄的 manifest 與 docs。

### 13.2 深度閱讀的檔案

- **治理**：`CLAUDE.md`、`HANDOFF.md`、`docs/README.md`、`docs/GOVERNANCE.md`、`docs/TODO.md`、`docs/PROJECT_OPTIMIZATION_REVIEW_2026-08-12.md`、`README.md`、`docs/contracts/full-data-snapshot-v1.md`、`.loop/manifest.md`、`.loop/verify-gate.ps1`、`.github/workflows/ci.yml`、`pytest.ini`。
- **Frontend**：`App.tsx`、`main.tsx`、`Layout.tsx`、`Header.tsx`、`HomePage.tsx`、`NoteCard.tsx`、`NoteEditor.tsx`、`EditorToolbar.tsx`、`AttachmentPanel.tsx`、`stores/appStore.ts`、`hooks/editor/useNoteForm.ts`、`useNoteHistory.ts`、`useNoteAttachments.ts`；以及 `CommandPalette.tsx`、`Sidebar.tsx`、`SettingsPage.tsx`、`ReadingView.tsx` 的相關段落。
- **Backend**：`notes_search.go`（`handleNotes`、搜尋、附件掃描）、`notes_actions.go`（separate／restore）、`export.go`（JSON、MD、DB、snapshot）、`backups.go`（一致快照、download、restore）、`migrations.go`（FTS、seed）、`options.go`（seed 尋找）、`system.go`（restart、localhost gate）、`main.go`（flags、desktop 預設、DSN、`/api/test`）。
- **測試**：`tests/` 抽樣、`go-shadow/main_test.go` 的搜尋段落、`test_desktop_shell_phase1_3.py`、`test_desktop_shell_phase4_6.py`。

### 13.3 執行的指令與結果

| 指令／檢查 | 結果 |
|---|---|
| `git status --short`（開始與結束） | 乾淨 |
| `git ls-files`、`git ls-tree -r -l HEAD` | 4,348 個檔案；tree 103,137,489 B；node_modules 74,145,637 B；resources 23,730,028 B |
| `python -m pytest tests/ -q --durations=40` | **399 passed in 238.54s**（冷建置）；最慢的 4 個：65.07s、49.60s、42.20s、32.39s |
| 新增本報告後 `python -m pytest tests/ -q` | **399 passed in 72.37s**（cache 已熱）；新文件沒有觸發任何 docs 掃描測試 |
| `cd go-shadow && go test ./... -count=1` | ok（14.073s）；整體約 65s |
| `go vet ./...` | 無警告 |
| `go build -o <scratch>/prism-review.exe .` | 成功（19.5MB） |
| 隔離 runtime（13 個 enable flags、`--db <scratch>/review.db`） | `/healthz` 回 200 |
| CJK 搜尋矩陣（API） | 見 FEAT-01 表格 |
| 長文 separate、匯出、歷史、縮短（API＋browser） | 見 FEAT-02 表格 |
| `/export/db` 在 checkpoint 前後（API＋Python sqlite） | 見 OPS-01 |
| 230 篇長文搜尋 × 3 輪 | 見 PERF-01 |
| SQLite 3.45.1 benchmark（10k × 1,800 字） | 見 §8.1 |
| `frontend/dist` 的大小與 gzip | 見 §8.1 |
| 內建 browser：desktop／mobile 的 DOM 與截圖 | 見 §3 |
| 3 個唯讀 subagent（API 地圖、測試組合、死資產） | 抽驗一致，見 §13.4 |

### 13.4 Subagent 結論的抽驗

| 主張 | 抽驗方式 | 結果 |
|---|---|---|
| node_modules 74.1MB 且缺 `dompurify` | `git ls-tree` 加總；`git ls-files …/dompurify` | 一致（0 個檔案） |
| `docs2/` 與 governance-source 完全相同 | 逐檔 `cmp` | 8/8 相同 |
| `docs/New_UI`、`docs/過期` 不存在 | `ls` | 一致 |
| Behavior 類測試不執行程式 | 抽 5 個檔案共 44 個測試 grep subprocess／HTTP | 0 個執行呼叫 |
| 9 個測試檔讀 `HANDOFF.md` | grep | 一致 |
| pytest 中重複執行 `go test ./...` | 讀 `test_desktop_shell_phase1_3.py:83-90` | 一致 |
| Restart 是 stub、`.port_config` 沒人讀、localhost gate 只看 RemoteAddr | 讀 `system.go` 與 Caddyfile | 一致 |
| `clean_test_data.py` 會清空 DB | 讀 `:6,43-46` | 一致（會先複製備份，不經確認） |
| `f632cee` 為文件修改動了大量測試 | `git show --stat` | TODO 只改 1 行（+1／−1）；整個 commit 共 21 個檔案，+78／−53 |
| `go build` 呼叫點數量 | grep（排除函式定義） | 9 個呼叫點 |
| vacuum 與 WAL checkpoint 沒有執行型測試 | grep `go-shadow/*_test.go`、`tests/*.py` | 只出現在 route 清單字串（`test_go_primary_t032_t035_server_system.py:427,430`） |

### 13.5 Evidence Ledger 與 Improvement ID 索引

| ID | 名稱 | 首次完整說明 | 關鍵證據 | Priority |
|---|---|---|---|---|
| UX-01 | Header 全域動作失效 | §3.2 | `Header.tsx:63-66,372`；`HomePage.tsx:617-623`【RT】 | P0 |
| UX-02 | Ctrl+S 關閉、沒有離開保護 | §3.2 | `useNoteForm.ts:130-131,177-189`【RT】 | P1 |
| UX-03 | 預覽是混合編輯態 | §3.5 | `NoteEditor.tsx:161-168`【RT】 | P1 |
| UX-04 | Mobile 排序與密度 | §3.3 | `Header.tsx:273-274`【RT】 | P2 |
| UX-05 | 計數矛盾、stats 寫死 | §3.6 | `Sidebar.tsx:194`；`SettingsPage.tsx:90-98`【RT】 | P2 |
| UX-06 | Prompt Builder 命名、語系、seed | §3.7 | i18n `optimizeTitle`；`options.go:238-263`【RT】 | P3 |
| IA-01 | Library 導覽重複 | §4.3 | desktop 截圖【RT】 | P2 |
| IA-02 | Settings 分組、圖片設定分散 | §4.3 | Settings 文字讀取【RT】 | P2 |
| FEAT-01 | CJK 搜尋失效 | §3.3 | `migrations.go:382-387`；`notes_search.go:192-195,312-319`；`CommandPalette.tsx:20,55`【RT】【CMD】 | P0 |
| FEAT-02 | 長文拆分讓內容分裂並還原編輯 | §3.4 | `useNoteForm.ts:123-129`；`notes_actions.go:285-445`；`useNoteAttachments.ts:21-26`【RT】 | P0（a）／P1（b） |
| FEAT-03 | 匯出文案過度承諾 | §3.8 | `export.go:516-555`【RT】 | P1 |
| FEAT-05～09 | 產品假設 | §7.2 | — | Future／不建議 |
| PERF-01 | 請求內逐檔掃描附件觸頂 | §3.3 | `notes_search.go:321-384`【RT】 | P1（隨 FEAT-02b） |
| PERF-02 | mutation 後列表重置 | §3.5 | `appStore.ts:154-158`等【SRC】 | P2 |
| PERF-03 | 歷史沒有保留上限 | §8.4 | `notes_write.go:117` | Future |
| TECH-01 | 版本多處寫死 | §9.1 | 4 個 source 位置；`TODO.md:42-45,171-197` | P1 |
| TECH-02 | 測試組合 | §9.1 | 【AGT】＋抽驗；durations | P1 |
| TECH-03 | 文件負擔與斷鏈 | §9.1 | 必讀 186,237 B；`CLAUDE.md:28` | P1 |
| TECH-04 | Repo 死重量 | §9.1 | `git ls-tree`；`clean_test_data.py:43-46` | P1 |
| TECH-05 | 遷移期命名外露 | §9.1 | `main.go:148-160,203-205`；`system.go:700-709` | P2／P3 |
| TECH-06 | API 表面衛生 | §8.5 | 【AGT】 | P3 |
| TECH-07 | 附件檢視 HTML injection | §8.3 | `useNoteAttachments.ts:80-100` | P0 |
| OPS-01 | DB 複本不一致 | §3.8 | `export.go:122-142`；`backups.go:21-48`【RT】 | P0 |
| OPS-02 | 桌面版無自動備份 | §3.8 | 沒有排程；`DEPLOY-PI.md:136-161` | P1（需決策） |
| OPS-03 | Snapshot 沒有還原說明 | §3.8 | `full-data-snapshot-v1.md:69`；`export.go:191`；`main.go:203-205` | P2 |
| OPS-04 | LAN 可達的 localhost-only API | §8.6 | `system.go:168-178`；Caddyfile；`API_REFERENCE.md:45` | P1 |
| OPS-05 | Restart 是 stub | §8.3 | `system.go:696-710` | P2 |
| OPS-06 | seed config 沒有內嵌 | §8.6 | `options.go:238-263` | P3 |
| BIZ-01 | 非中文使用者的首次體驗 | §7.2 | `migrations.go:444-446` | P3 |
| REVAMP-01～05 | 改版方向 | §6.2 | — | 01、02 現在做；03 下一階段；04 稍後；05 不建議 |

### 13.6 與 08-12 ID 的對照

| 08-12 | 本報告 |
|---|---|
| UX-04 預覽語意 | UX-03（升為 P1，因為與 UX-02 疊加） |
| PERF-03 Reading list | 沿用 R0812:PERF-03（P2） |
| DOC-01 | 併入 TECH-03 |
| TECH-02 flags 與命名 | TECH-05 |
| API-01 殘項 | §8.2（P3） |
| SEARCH-01（partial 診斷） | 已完成；本次發現 partial 在約 50 檔就成為常態 → PERF-01 |

### 13.7 本次審查的完成邊界

本次只新增本文件。沒有修改 source、config、database、schema、asset、既有文件、deployment 或 production data；沒有 commit、push 或 deploy。依照指示，沒有回寫 `docs/TODO.md` 與 `HANDOFF.md`。

隔離 runtime、合成資料與 benchmark DB 都放在 session 的 scratch 目錄，結束時已停止 runtime。browser 的 viewport 模擬已重設。
