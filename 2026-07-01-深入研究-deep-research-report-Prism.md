# Prism 深入研究與產品架構審查

## 一頁式總結

先講判斷：**Prism 現在最像的，不是 Obsidian/Logseq 那種 file-first PKM，也不是 AnythingLLM/Khoj 那種 AI-first knowledge chat；它更像一個本機優先、SQLite 為核心、可被其他工具呼叫的「個人知識層」與 card-oriented local API server，外加一個可攜 Windows shell。**這個定位其實有價值，而且已經比很多「想做很多事」的知識工具更清楚。README、架構文件與目前路由面都把它描述成 Go primary runtime + React SPA + SQLite/FTS5 + local file storage；外部工具透過 REST API 使用 Prism，而不是把 Prism 做成雲端協作平台。citeturn37view1turn39view0turn17view2

**目前最有價值的核心**不是 UI 花俏功能，而是四件事的組合：本機 SQLite 穩定儲存、FTS5 關鍵字檢索、乾淨的 REST API、以及 Windows portable / headless Pi 兩條部署路徑都已經串起來。這讓 Prism 有資格被當成「Agent 可用的本地知識底層」，而不是單純的個人筆記玩具。README 明確寫了不內建 AI、cloud sync、telemetry，核心是 durable storage、fast keyword search、predictable local operations；架構文件也把 external agent 視為正式使用者之一。citeturn37view1turn39view0

**最大風險**不是功能不夠，而是「邊界開始鬆掉」：目前 Go runtime 已同時承擔 API、DB migration、搜尋、附件、匯入匯出、server/system 維運、備份、Windows desktop shell，而且核心檔 `go-shadow/main.go` 已超過一萬行。這不是立即壞掉，但它會讓後續每加一個功能，都同時放大維護成本、測試成本、平台分支成本與安全邊界判斷成本。再加上 desktop 模式會一次打開大量 write/system 能力，代表「功能開關」雖然靈活，但也形成 mode explosion。citeturn16view0turn21view0turn17view2turn20view9

**Prism 現在最值得立刻改善的五件事**，我會排成這樣：

| 優先 | 建議 | 判斷 | 主要依據 |
|---|---|---|---|
| 高 | 把 `go-shadow/main.go` 依 bounded context 拆成小包，但**不要**做大重構 | 現在最危險的技術債 | `main.go` 10128 lines；同檔處理路由、runtime、migrations、desktop、backup、security。citeturn16view0turn17view2turn18view7 |
| 高 | 收斂 runtime surface，把「知識 API」和「系統/維運 API」邊界切乾淨 | 產品定位會更穩，安全邊界也更清楚 | `/api/server/*`、`/api/system/*`、backup/restart/logs/hardware 與 notes/search 同居。citeturn17view2turn40view3 |
| 高 | 強化 search contract：讓使用者知道搜到的是 title/content、remarks/tag、還是附件內容 | 現在 search 有能力，但可解釋性還不夠 | `Notes_FTS` 只索引 `title/content`，其餘靠 join 與 request-time 掃描文字附件。citeturn39view0turn41view3 |
| 高 | 把 import/export 做成更對稱、更可回放、更可驗證 | 這是 local-first 工具能否長期信任的關鍵 | 有 JSON import / JSON+DB+Markdown export，但 Markdown 回寫仍缺，batch markdown import 目前只是前端 wrapper。citeturn40view6turn40view7turn31view6 |
| 高 | 文件與實作同步治理 | 文件可信度會直接影響維護效率 | README/釋出說明/Schema 歷史資訊很多，且 v1.4.1 釋出仍強調瀑布流；現行 HomePage 已是一般 grid/list/compact。citeturn36view0turn25view3turn25view9turn41view6 |

**哪些方向我不建議現在做**，而且理由很明確：

| 不建議方向 | 原因 |
|---|---|
| 把 AI / embedding / semantic search 放進核心 runtime | repo 自己的 active TODO 已明確把這類需求列為不要自動擴 scope；Prism 的核心優勢是 local durable layer，不是 AI feature buffet。citeturn42view3 |
| 多使用者登入、RBAC、OAuth、API token 體系 | 這會把 Prism 從本機工具拉成服務平台，維護成本和風險暴增，而且 TODO 也明列不建議現在做。citeturn42view3 |
| 雲端同步、背景 daemon、企業協作 | 這不是目前 repo 的主軸，且會破壞 local-first 簡潔邊界。citeturn37view1turn42view3 |
| Installer / updater / shortcut automation 先做完整產品化 | 文件已明確把 installer/updater 視為後續 decision gate，不應直接引入 NSIS/WiX/MSIX/auto updater。citeturn39view0turn42view3 |
| 炫目的 graph / knowledge map / social-like UX 先衝 | Prism 的差異不是 graph，而是「整理過、可 API 化、可重用」的 card layer；太早做圖譜，多半只會把專案變重。這點是我的架構判斷，不是 repo 現行承諾。citeturn37view1turn39view0 |

反方意見我先講清楚：**Prism 不一定需要一個「大升級版」**。如果你的真正目標只是「單人、本機、穩定、可搜尋、可被工具呼叫的知識卡片層」，那其實目前方向已經夠合理；真正需要的是穩定化、邊界收斂、匯入匯出可靠化，而不是另起一個更大的產品幻想。這也是我下面所有建議的基準線。citeturn37view1turn42view0turn42view3

## 現有 repo 架構地圖

先給結論：**目前 repo 已經不像「單純一個 app」，而是四個子系統疊在一起**：Go runtime、React SPA、Windows desktop shell/portable packaging、以及 Pi headless deployment。這很能做事，但也正是為什麼要主動整理邊界。repo 根目錄也直接露出 `frontend`、`go-shadow`、`desktop-spike`、`deploy/raspberry_pi`、`scripts`、`e2e`、`tests` 等多條路徑。citeturn37view3turn38view0turn38view1

| 面向 | 已由 repo 證實 | 從程式碼合理推測 | 目前看不到，需要作者確認 | 主要證據 |
|---|---|---|---|---|
| 技術棧 | Go primary runtime、React 18、Vite 5、TypeScript 5、Zustand、Tailwind、Axios、SQLite、WebView2、PowerShell build scripts。citeturn37view1turn15view0turn39view0turn20view9 | 前端偏單頁應用，後端偏單體 local service，不是 microservice。 | 是否會長期維持 Go+React+WebView2，而不是改 Wails/Tauri。 | `README.md`、`frontend/package.json`、`docs/ARCHITECTURE.md`、desktop flags。citeturn37view1turn15view0turn39view0turn20view9 |
| 主要目錄 | `frontend`、`go-shadow`、`tests`、`e2e`、`scripts`、`deploy/raspberry_pi`、`desktop-spike`、`docs`。citeturn37view3turn38view0turn38view1 | repo 還留有一些歷史/交接/掃描文件，代表單作者手動治理比重很高。 | 哪些資料夾會被視為長期 product surface，哪些只是 staging artifact。 | repo root tree。citeturn37view3 |
| 後端架構 | 單一 Go runtime；`/api/*`、`/api/system/*`、`/api/server/*`、`/api/export/*`、`/api/import/*`、`/api/upload*` 等路由都在同一 runtime。citeturn17view2 | 目前是「單體後端 + feature flags + mode switching」，不是模組化 service。 | 是否有計畫把 admin/runtime-management surface 抽離。 | `go-shadow/main.go` 路由註冊。citeturn17view2 |
| 前端架構 | App 只有三個主頁：`HomePage`、`PromptBuilder`、`SettingsPage`；狀態以單一 Zustand store 為核心。citeturn15view1turn24view2 | UI 狀態與 domain state 混在同一 store，適合早期，但會限制中後期維護。 | 是否故意維持「單 store，不追求大型前端架構」。 | `App.tsx`、`appStore.ts`。citeturn15view1turn24view2 |
| 資料庫與搜尋 | SQLite WAL；`Schema_Meta` 管 migration version；schema 現行文件是 Migration v17；`Categories` 有 `system_key` 與 `name_override`；`Notes_FTS` 用 FTS5 只索引 `title/content`。citeturn39view0turn41view5turn41view0turn41view3turn18view7 | 搜尋實際上是「FTS + SQL join/filter + request-time attachment text scan」的混合系統。 | 大資料量時 attachment scan 的實際延遲表現、是否已有 benchmark。 | `docs/ARCHITECTURE.md`、`docs/SCHEMA.md`。citeturn39view0turn41view3 |
| API 邊界 | Notes / taxonomy / attachments / uploads / cleanup / import-export / system-server 全都在本機 REST API。citeturn17view2turn40view3 | 這是 headless KMS 的優點，也是 boundary 風險。 | 哪些 endpoint 會被視為穩定公開 contract。 | `main.go`、`API_REFERENCE.md`。citeturn17view2turn40view3 |
| 啟動與部署 | Windows portable 由 `Prism.exe` 啟動 in-process Go runtime + WebView2；Pi 部署走 headless Go artifact + service path；desktop 模式預設資料在 `PrismData\`。citeturn37view1turn39view0turn20view9 | 本地 GUI 與 headless server 共用同一 runtime，是 Prism 的真正工程特色。 | 未來是否會維持單 executable，或拆出獨立 desktop shell。 | README、architecture、desktop flags。citeturn37view1turn39view0turn20view9 |
| 測試與工具鏈 | CI 用 Windows runner，安裝 Go/Node/Python；建 frontend；最後跑 `.loop/verify-gate.ps1`。Loop gate 會跑 `git diff --check`、AGENTS/CLAUDE mirror check、`pytest tests/ -v`、`go test ./...`。citeturn33view1turn35view0 | 測試面其實不算薄，但 CI workflow 直接可見的邏輯過度委託給自訂 PowerShell gate。 | e2e coverage 的深度與 flaky 狀況。 | `.github/workflows/ci.yml`、`.loop/verify-gate.ps1`。citeturn33view1turn35view0 |
| 文件與實作落差 | API/Schema/Architecture 文件相對完整；但歷史敘事量很大，且舊 release 說明仍殘留與現況不同的 UI 說法，例如 v1.4.1 的「瀑布流」，而現行 `HomePage` 是標準 grid/list/compact。citeturn36view0turn25view3turn25view9 | 文件可信度若不持續整理，會從優勢變成負擔。 | 哪些文檔作者預期對外公開維持，哪些只是內部 handoff。 | releases、`SCHEMA.md`、`TODO.md`。citeturn36view0turn41view6turn42view0 |

我自己的架構判斷是：**Prism 真正該守住的，不是「它現在有哪些功能」，而是「它是一個本機知識層，而不是全功能知識產品」**。一旦這個邊界守不住，你會開始在同一個 runtime 裡面同時做筆記 app、維運面板、agent memory、匯入中心、桌面安裝器與半個 document system。那時候不是功能更多，而是產品意圖會變混。這是從 repo 現況合理推測，不是 repo 已明文承認。citeturn17view2turn39view0turn42view3

## 現有版本改善建議

下面這一段，我會用**嚴格架構審查**角度寫。排序偏向「小改但高收益」優先，再往後才是較大的整理。表格中的狀態標記如下：

- **證實**：repo / docs / code 直接看得到
- **推測**：從 code 組織或行為推得出來
- **待確認**：目前 repo 無法單靠靜態閱讀確認

| 優先 | 問題名稱 | 類型 | 嚴重度 | 證據 | 為什麼是問題 | 長期影響 | 建議修法 | 成本 | 風險 | 現版或升級版 |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | `main.go` 單檔過大 | Maintainability / Architecture | High | `go-shadow/main.go` 10128 lines，且同檔含 runtime、desktop、migrations、routes、security。**證實**。citeturn16view0turn17view2turn18view7 | 任何修改都容易波及不相干領域。 | 測試成本、回歸風險、接手難度都上升。 | 先按 bounded context 抽出 `runtime/config`、`api/notes`、`api/system`、`storage/migrate`、`desktop`，不要大翻修。 | M | 容易過度重構 | 現版 |
| P2 | API surface 過寬 | API / Security / Product boundary | High | notes/search 與 hardware/logs/restart/backup 同在同一 API 面。**證實**。citeturn17view2turn40view3 | 使用者與 agent 很難知道哪些是「知識層」，哪些是「主機管理」。 | 讓 Prism 從 KMS 漸變成 admin console。 | 把 `/api/server/*`、危險 `/api/system/*` 做 capability profile、明確標記 admin-only，最好另組文件與 UI 區塊。 | M | 可能牽動前端設定頁 | 現版 |
| P3 | 搜尋 contract 不夠可解釋 | Search / UX | High | FTS5 只索引 `Notes.title/content`；remarks、tag、附件內容靠 API 擴充與 request-time 掃描。**證實**。citeturn39view0turn41view3 | 使用者不知道命中來源，結果可預期性弱。 | 之後很難做搜尋品質優化與除錯。 | 回傳 `match_source`、snippet、是否來自 attachment scan；Settings 可加 search scope 說明。 | M | 需改 API response 與 UI | 現版 |
| P4 | 匯入匯出不夠對稱 | Import / Export / Product integrity | High | 有 JSON/DB/Markdown export，但 Markdown 回寫缺；batch Markdown import 是前端逐檔 wrapper。**證實**。citeturn40view6turn40view7turn31view6 | local-first 最怕資料可帶出但帶不回。 | 使用者資料主權弱，Prism 會更像封閉容器。 | 補 deterministic Markdown import pipeline，至少先支援 Prism 自家 frontmatter manifest round-trip。 | M | 需想清楚 canonical mapping | 現版 |
| P5 | 備份語義容易誤會 | DB / Docs / UX | High | `backup/download` 是 DB snapshot，不含 uploads/attachments；server-side 保留則是 rotate 的責任。**證實**。citeturn40view3 | 使用者很容易把 DB download 誤認為完整備份。 | 還原失敗或資料遺失誤解。 | UI 與文件明示「DB-only backup」與「full profile backup」差異；最好新增 one-click profile export。 | M | 需整理打包內容 | 現版 |
| P6 | desktop 模式會自動打開大量 write/system 權限 | Security / Maintainability | High | `--desktop-shell` 會打開 tag/category/notes/attachments/upload/import-export/server-system 等能力。**證實**。citeturn21view0 | 功能方便，但 capability 邊界鬆。 | 之後更難判斷哪些路由在哪些模式能安全暴露。 | 定義明確 profile：`reader`、`editor`、`admin`、`desktop-full`，並寫入 docs。 | M | 可能碰到現有便利性 | 現版 |
| P7 | API contract 靠手寫同步 | API / Docs / Maintainability | High | `api.ts` 明寫 “Types matching backend schema”；docs 也靠手寫維護。**證實**。citeturn15view2turn39view1 | TS 型別、後端 JSON、 docs 很容易漂移。 | 每次改 response shape 都可能造成靜默錯誤。 | 最少加 contract tests；更好是導出 OpenAPI / JSON schema。 | M | 初期額外工具成本 | 現版 |
| P8 | HomePage 的搜尋設定會立即觸發 fetch | UX / Performance | Medium | `setSearchQuery` 直接 `fetchNotes(true)`。**證實**。citeturn23view3 | 若桌面端是即時輸入，容易造成多次 request。 | 搜尋體感和後端負載都變差。 | 加 debounce 或 explicit submit 模式選項。 | S | 很低 | 現版 |
| P9 | 分頁判定過於脆弱 | UX / API | Medium | `hasMore: response.notes.length === 20`，`per_page` 固定 20。**證實**。citeturn23view6turn24view2 | 這依賴隱性契約，不夠穩。 | 未來改 per_page 或排序後容易出錯。 | 以 `total/page/per_page` 正式計算 `hasMore`。 | S | 很低 | 現版 |
| P10 | appStore 混了 UI 與 domain state | Frontend / Maintainability | Medium | 同一 store 同管 notes、locale、viewMode、editor、reading、command palette、selection、filters。**證實**。citeturn24view2 | 初期方便，後期會很難局部測試與重用。 | Settings / Home / Editor 耦合加深。 | 至少拆成 `noteStore`、`uiStore`、`settingsStore` 三塊。 | M | 中等 | 現版 |
| P11 | Server restart UX 用固定 5 秒 reload | UX / Reliability | Medium | `setTimeout(() => window.location.reload(), 5000)`。**證實**。citeturn32view2 | 真實重啟時間不可預測。 | 偽失敗 / 偽成功都可能發生。 | 改成 `/healthz` polling + exponential backoff。 | S | 很低 | 現版 |
| P12 | CSRF 開關是 marker file，邊界說明仍可更強 | Security / Docs | Medium | `.csrf_disabled` marker 控制保護開關；前端可即時 toggle。**證實**。citeturn17view4turn31view0 | 對本機工具合理，但一旦走 Pi/LAN，就需要更明確風險提示。 | 使用者可能低估暴露於內網/反向代理時的風險。 | 在 Access/Security 頁加「localhost only / reverse proxy / LAN exposed」模式說明與警示。 | S | 很低 | 現版 |
| P13 | `SCHEMA.md` 歷史敘事過重 | Docs / Maintainability | Medium | 現行 schema 文件同時夾帶大量 T009-T053 歷史 gate 敘事。**證實**。citeturn41view6turn41view5 | current truth 與歷史證據混讀，降低可用性。 | 新人更難快速理解現行資料模型。 | 把歷史驗證敘事全面移到 `development-history`；schema 主文只保留 current truth。 | S | 很低 | 現版 |
| P14 | 舊文件與現況 UI 有落差 | Docs / UX | Medium | v1.4.1 release 強調玻璃擬態與瀑布流；現行 `HomePage` 是 grid/list/compact。**證實**。citeturn36view0turn25view9 | 文件一旦有時代差，讀者會懷疑其他描述。 | 專案可信度下降。 | 做一版「what is current truth」頁，舊 releases 不改內容，但在 README 連到 current UI screenshots。 | S | 很低 | 現版 |
| P15 | Search explainability 還停在 hint 層級，沒有結果層級 | Search / UX | Medium | TODO 已提過 Search Context Bar / Scope Hint / Recent Searches，但沒有 per-result explain。**證實 + 推測**。citeturn42view3turn25view8 | 對重複使用知識卡片來說，知道「為什麼被搜到」很重要。 | 搜尋會像黑箱。 | 顯示命中欄位、snippet、附件來源、tag hits。 | M | 需小改 API | 現版 |
| P16 | category identity 雖然進化了，但 invariant 仍需再鎖緊 | DB / Model integrity | Medium | v17 新增 `system_key` / `name_override`，系統分類身份與顯示名分離。**證實**。citeturn41view0turn41view1 | 這是好設計，但一旦 import/update 邏輯沒守住，就會污染分類模型。 | 系統分類被誤刪、誤合併、誤重建時會變難修。 | 補 invariant tests：唯一 system_key、rename/merge/delete/restore round-trip。 | S | 低 | 現版 |
| P17 | Data backup / import UI 逐漸變成「資料中心」，有變重風險 | UX / Product focus | Medium | Settings 已含 DataManager、BackupImport、Maintenance、Security、ServerDashboard。**證實**。citeturn28view4turn28view6turn28view7 | 這些都合理，但過多會讓主產品焦點從 knowledge workflow 漂移。 | Settings 變半個 admin panel。 | 保留必要能力，但把「作者工具」與「一般使用者工具」分層。 | M | 中等 | 現版 |
| P18 | release / package friction 仍高 | Packaging / UX | Medium | v2.5 release 明寫 portable exe 未簽章，SmartScreen 可能阻擋；需人工驗 hash / unblock。**證實**。citeturn36view0 | 這會降低非技術使用者完成率。 | 影響 adoption。 | 先補更好的 portable first-run 檢查與說明，再評估 installer gate；不要直接做 auto-updater。 | M | 中等 | 現版 |
| P19 | repo 對單一作者依賴高 | Maintainability | Medium | Issues 0、PRs 0、repository 為 public template；大量 handoff/history docs。**證實**。citeturn16view0turn37view3turn42view0 | 代表實際知識多半在作者腦中。 | 維護 bus factor 高。 | 建立 `ARCHITECTURE_DECISIONS.md`、`CONTRACTS.md`、feature profiles。 | S | 很低 | 現版 |
| P20 | `desktop-spike` 已完成歷史任務，但 repo 仍要避免讀者誤認為正式 runtime | Docs / Maintainability | Low | `desktop-spike` README 自己寫明是 isolated Phase 0 proof，真正 desktop 已移到 `go-shadow --desktop-*`。**證實**。citeturn38view0turn39view0 | 歷史 spike 還留 repo 是可以的，但一定要明確標示。 | 讀者誤判 code ownership。 | 在 repo root 開發說明中更明確標註「historical spike / not runtime owner」。 | S | 很低 | 現版 |

這 20 項裡，**最值得先做的不是大重寫，而是把邊界、契約、搜尋可解釋性和 backup/import 可信度補齊。**因為只要這四項站穩，Prism 就已經能作為「本地知識層」成立；反過來說，如果這四項不穩，任何升級版都只是堆功能。citeturn37view1turn39view0turn40view3turn40view7

## 升級版自由發揮方向

這一段是**自由發想，不代表現在版本都該做**。我的原則只有一個：**凡是會把 Prism 從 local-first 知識層拉成重量級產品的東西，都應該優先考慮做成 plugin、sidecar、browser extension、desktop extension 或獨立專案，而不是塞進核心。**

| 方向 | 核心概念 | 適合解什麼問題 | 為什麼適合 Prism | 與現在差異 | MVP | 進階版 | 技術挑戰 | 把專案做壞的風險 | 最適合形態 |
|---|---|---|---|---|---|---|---|---|---|
| Semantic Search Sidecar | 向量索引不進核心 DB，而是吃 Prism API/exports 建 secondary index | 關鍵字搜不到同義概念、語意召回不足 | Prism 已有乾淨 API 與可匯出資料；很適合外掛索引器 | 現在是純 keyword/FTS5 | 讀 JSON export 建 embedding index，回傳 note ids | 增量同步、hybrid search、re-ranking | 同步一致性、資安、模型選型 | 一旦進核心，就會綁死模型與索引生命週期 | **Sidecar** |
| Prism as Local MCP Server | 把 Prism 的 note/search/read/write 包成 MCP 工具 | 讓 Claude/Codex/本地 agent 有穩定知識層 | 比把 agent 邏輯塞進 Prism 更乾淨 | 現在是一般 REST API | 包裝 read/search/create/update MCP tools | 加 relation, lifecycle, provenance, batch refine | permission model、tool schema 演化 | 若直接把 agent workflow 寫進 Prism，定位會歪 | **獨立專案或 sidecar** |
| Browser Capture Extension | 一鍵擷取網頁、GitHub repo、LLM 對話，先進 inbox 再整理 | 減少手動搬運與遺漏 | 很符合「不是垃圾桶，而是整理前 inbox」 | 現在缺正式 clipper | title/url/selection/screenshot/summary 存成 inbox card | 支援 GitHub repo 摘要、Chat export、YouTube transcript | 清洗內容、重複偵測、來源追蹤 | 若直接全量存原文，Prism 會變垃圾倉庫 | **Browser extension + API** |
| Knowledge Lifecycle | `inbox → review → refined card → archived` | 防止未整理資料污染主知識層 | 非常符合 Prism 的卡片式定位 | 目前只有 archive/pin/variant 等局部能力 | 增加 status/state + review queue | 加 review checklist、approval、staleness reminders | 狀態機與搜尋/列表整合 | 做太重會變 task manager | **核心少量 + 其餘 plugin** |
| Diff-aware Updates | 同一主題更新時，先建候選 diff，不要一直新增 card | 防止知識碎片化與重複卡片 | 對可重用知識卡很重要 | 現在比較偏新增/複製/variant | 以 title/url/source hash 找相似候選 | 支援 merge proposal、field-level diff、provenance | 相似度判斷、UX 決策 | 做太激進會造成誤合併與資料污染 | **核心輕量 + sidecar 輔助** |
| Versioned Knowledge Cards | 卡片有版本、摘要 diff、回看與 restore | 適合 prompt、流程、研究結論演化 | 比全文 note history 更符合 card reuse | 現有有 history/restore，但偏內容層 | 每次儲存保留 compact version metadata | 比較版本、版本 pin、發布版卡片 | data model 與 UI 複雜化 | 如果 version 太細，操作會變煩 | **核心，但先做輕版** |
| Typed Card Templates | prompt card、concept card、checklist card、research card、task card 等 typed schema | 提高重用率與檢索品質 | Prism 是 card layer，比自由筆記更適合 typed card | 現在比較接近 generic notes + prompt tooling | 先做少數內建 card types + optional fields | Plugin-defined card schemas + custom views | schema 演化與 backward compatibility | 做成 Notion clone 會很重 | **核心最小 + plugin 擴充** |
| Local Sync / Backup Profile | 不是即時雲同步，而是 profile export/import + snapshot + portable profile | 解決跨機器搬移與備份 | 不破壞 local-first | 現在有 DB download / rotate backups，但 full profile 還不夠清楚 | 一鍵 full profile zip | profile compare、incremental backup、conflict assistant | 檔案一致性與大型附件 | 若做成即時 sync daemon，立刻變複雜 | **核心輕量** |
| Research Radar Sidecar | 定期抓 repo/release/RSS/頁面變動，產生候選更新卡 | 讓知識不是死資料 | 這是「整理過知識層」很有價值的外圍能力 | 現在沒有雷達層 | watch list + diff digest → inbox | source scoring、dedupe、review workflow | 抓取成本、來源穩定性 | 容易把 Prism 變成 feed reader | **Sidecar** |
| CLI-first Workflow | 讓 terminal / scripts 直接批次建立、更新、查詢 cards | 照顧進階用戶與 agent workflow | Prism 天生就像 local API + DB layer | 現在以 REST 與 UI 為主 | `prism add/search/export/import` CLI | pipeline/templating/script hooks | packaging、cross-platform UX | 若 CLI 與 API contract 分裂，維護加倍 | **CLI 獨立層** |

我的直球判斷是：**如果真要做升級版，我最看好的是「Prism Core + 可選 sidecar 生態」**，而不是做一個更大、更會聊天、更像 SaaS 的 Prism 3。因為你現在真正有競爭力的是 local durable layer，不是 AI orchestration；AI 那一層變動太快，做 sidecar 反而能保住核心穩定。這個判斷同時也呼應 repo 自己的 TODO：不要自動把 scope 擴成 AI、semantic search、installer、updater、多使用者。citeturn42view3

## 參考專案地圖

先給選題結論：**Prism 不該只看「長得像筆記 app」的專案。它應該同時看四類東西**：

- file-first PKM：學資料組織、backlink、capture flow
- headless / API / search 工具：學邊界與檢索契約
- AI/RAG 工具：只借它們的 sidecar 與 ingestion 做法，不抄產品定位
- desktop / local infra：學分發、可攜 profile、runtime 包裝

下面是我認為**值得掃描的 20 個專案**。為了可讀性，我把每列寫得很密，但仍保留你要的判斷欄位。stars 與活躍度以 GitHub 2026-07-01 當下頁面或 latest release 頁面為準；部分專案的 release flow 不完全一致，我會直接註記。citeturn43view0turn45view0turn46view1turn45view2turn46view3turn45view5turn46view6turn46view7turn45view8turn44view0turn45view11turn45view12turn45view13turn45view14turn45view15turn45view17

| 專案 | 類別 | GitHub 現況 | 解決什麼問題 | Prism 可借鑑什麼 | Prism 不該照抄什麼 | 參考價值 |
|---|---|---|---|---|---|---|
| Logseq | Local-first PKM / graph | 約 43.6k stars；大型多平台 PKM；latest release 顯示 2025-12-01。citeturn43view0turn46view0 | block-based PKM、graph、backlinks | 關聯與 block/card 連結感；capture→linking UX | 不要把 Prism 變 file/block graph 大系統 | High |
| Joplin | PKM / sync note | 高星、成熟 cross-platform；latest release 2026-06-20。citeturn43view1turn46view1 | 筆記、附件、同步、跨平台 | 匯入匯出、資料主權、附件治理、plugin discipline | 不要直接走 sync-first 產品路線 | High |
| SilverBullet | Markdown knowledge tool | 中型但很有辨識度；latest release 2026-06-11。citeturn43view2turn46view2 | Markdown + scriptable personal space | 輕量 plugin/scripting、空間化 UX | 不要把 DSL/scripting 變核心門檻 | High |
| TriliumNext Notes | 個人知識庫 / card tree | 持續活躍；latest release 2026-06-15。citeturn43view3turn46view3 | 結構化知識樹、template、屬性 | typed card / metadata / template 設計 | 不要把 Prism 做成全能 hierarchical universe | High |
| Dendron | Markdown PKM / dev workflow | repo 仍大且有歷史價值；latest release 頁未直接導向 tag。citeturn43view4turn45view4turn46view4 | developer-oriented knowledge workflow | 命名規則、workspace discipline、知識分解方法 | 不要背整套 file naming 宗教 | Medium |
| AppFlowy | local-first workspace | 大型協作 workspace；latest release 2026-06-23。citeturn43view5turn46view5 | Notion-like 文件/資料庫/團隊 | block editor、data control、local-first messaging | 不要變「另一個 Notion」 | Medium |
| Outline | team knowledge base | 成熟團隊知識庫；latest release 2026-06-06。citeturn43view6turn46view6 | 團隊 wiki / docs / publishing | 資訊架構、乾淨編輯與搜尋 UX | 不要引入大量協作/權限模型 | Medium |
| Meilisearch | Search / indexing | 搜尋引擎；latest release 2026-06-29。citeturn43view7turn46view7 | 即時搜尋、ranking、typo tolerance | snippet/highlight、query UX、relevance tuning ideas | 不要把 Prism 拉成獨立搜尋服務 | High |
| Typesense | Search engine | 搜尋引擎；release page可見 v30.2。citeturn43view8turn45view8turn46view8 | schema-based search API | search result explainability、sorting/facet 思路 | 不要引入外部 search infra 複雜度 | Medium |
| Tantivy | Full-text library | Rust library；release flow持續前進。citeturn43view9turn45view9turn46view9 | Lucene-like library 級全文索引 | 借鑑 index abstraction 與 search architecture 思考 | 不要為了搜尋重寫 storage stack | Medium |
| Khoj | AI knowledge / local docs | 約 35.4k stars；latest release 可見 2.0 beta。citeturn44view0turn45view10turn46view10 | AI second brain / retrieval / agents | sidecar 式 AI 層、資料接入面 | 不要把 AI 變產品中心 | High |
| AnythingLLM | RAG / local-first AI workspace | 高活躍；latest release 可見 v1.15.0。citeturn44view1turn45view11turn46view11 | 文件接入、workspace、模型串接 | provider abstraction、ingestion pipeline | 不要變聊天容器與模型管理器 | Medium |
| Open WebUI | AI interface / knowledge features | 高活躍；latest release 可見 v0.10.1。citeturn44view2turn45view12turn46view12 | 模型 UI、文件/knowledge 功能 | plugin ecosystem、integration shell | 不要把 Prism 變 AI front-end | Medium |
| Paperless-ngx | 文檔歸檔 / capture | 持續活躍；latest release 可見 2026-06。citeturn44view3turn45view13turn46view13 | OCR、文件 ingestion、歸檔流程 | ingestion queue、source tracking、dedupe / status UX | 不要變 raw document warehouse | High |
| Wails | Desktop local app architecture | Go-based desktop framework；latest release 2026-06。citeturn44view4turn45view14turn46view14 | Go + web frontend desktop app | 桌面分發、shell/runtime boundary | Prism 已有自家 shell 路線，不要為框架重做 | Medium |
| Tauri | Desktop shell framework | 高星 desktop framework；latest release 2026-06。citeturn44view5turn45view15turn46view15 | web frontend + native shell | package/update/install lessons | 不要為了框架改寫整條桌面線 | Medium |
| mem0 | agent memory layer | AI memory infra；latest release 可見 2026。citeturn44view6turn45view16turn46view16 | agent memory abstraction | sidecar memory schema / retrieval patterns | 不要把它內建成核心資料模型 | Medium |
| MCP Servers | MCP / tool integration | 官方 MCP server collection；latest release 2026-01-26。citeturn44view7turn45view17turn46view17 | tool surface 標準化 | Prism-MCP 設計參考 | 不要把所有工具整合硬塞本體 | High |
| Yjs | local-first / collaboration infra | collaboration CRDT library；latest release 2026。citeturn44view8turn45view18turn46view18 | shared data types / CRDT | 只有在未來真做 sync/collab 時才值得看 | 現階段絕對不要引入 | Low |
| DB Browser for SQLite | SQLite-first desktop app | 長期維護中；latest release 存在。citeturn44view9turn45view19turn46view19 | SQLite 桌面工具與 profile handling | SQLite-first UX、資料透明感 | 不要把 Prism 變 DB admin tool | Medium |

如果只挑 **最值得深入看的 10 個**，我會選：

- Joplin
- SilverBullet
- TriliumNext Notes
- Meilisearch
- Paperless-ngx
- Logseq
- Khoj
- MCP Servers
- Wails
- Typesense

原因很直接：這 10 個剛好拼成 Prism 需要的五種視角——資料主權、輕量擴充、typed knowledge、搜尋 UX、ingestion pipeline、tool integration、desktop packaging。citeturn43view0turn43view1turn43view2turn43view3turn43view7turn44view3turn44view0turn44view7turn44view4turn43view8

## 參考專案對 Prism 的啟發

這裡不再列清單，而是直接轉成**可落地的開發任務方向**。

**Prism 應該直接學的功能**，我選這幾類：

| 任務方向 | 可借鑑對象 | 為什麼值得直接學 | 轉成 Prism 任務 |
|---|---|---|---|
| 搜尋結果解釋與 snippet | Meilisearch、Typesense | Prism 已經有搜尋能力，但缺 explainability。citeturn43view7turn43view8turn39view0 | 在 `/api/notes` 搜尋回傳中加入 `match_source`、`snippet`、`attachment_hit`、`tag_hit`。 |
| 匯入匯出做成明確 contract | Joplin、Paperless-ngx | local-first 工具的信用來自於資料可以帶走、帶回、可驗證。citeturn43view1turn44view3turn40view6turn40view7 | 加 `profile export`、Markdown round-trip import、匯入結果 manifest、dedupe report。 |
| Typed card / template | TriliumNext、SilverBullet | Prism 天生比自由筆記更適合 typed knowledge。citeturn43view3turn43view2 | 先做 3–5 種 card template：prompt、concept、research、checklist、task。 |
| 輕量 plugin / extension 邊界 | SilverBullet、MCP Servers | 不把變動快的東西塞核心。citeturn43view2turn44view7turn42view3 | 設計 `plugin/sidecar contract`，先從 importer 和 semantic sidecar 開始。 |
| Inbox / ingestion queue | Paperless-ngx、Khoj | Prism 缺「收進來但尚未整理」的正式層。citeturn44view3turn44view0 | 新增 inbox status、source metadata、review queue、dedupe candidates。 |

**只適合升級版，不適合現在塞核心的功能**：

| 功能 | 理由 |
|---|---|
| semantic search / embeddings / rerank | 與核心 storage/search contract 無關，變動快，應做 sidecar。citeturn42view3turn44view0turn44view1 |
| browser clipper / GitHub repo 摘要 / chat export capture | 很有價值，但屬於 acquisition layer，不是核心 storage layer。 |
| MCP server / agent memory wiring | 值得做，但更適合獨立 adapter 層。citeturn44view7turn44view6 |
| graph/backlink 視覺化 | 有幫助，但不是先決條件。Logseq/Trilium 的價值不等於 Prism 也要走那條路。citeturn43view0turn43view3 |

**看起來很好用，但會讓 Prism 變重的功能**：

- 多使用者 auth / 權限 / 協作編輯
- 即時同步 / daemon / CRDT
- full document warehouse + OCR + scanning
- 內建模型管理、聊天介面、多 provider 設定
- installer / updater / background service orchestration 做到產品級

這些在其他產品裡成立，不代表在 Prism 成立。Outline、AppFlowy、AnythingLLM、Open WebUI、Yjs 都有自己的產品邏輯；Prism 若照抄，只會失去自己最稀缺的特性：**小而穩的本地知識層**。citeturn43view6turn43view5turn44view1turn44view2turn44view8

**最值得借鑑的架構模式**，我會抓三個：

- **Core + optional sidecars**：學 MCP Servers、Khoj、AnythingLLM 的邊界概念，但不要學它們把 AI 變核心產品敘事。citeturn44view7turn44view0turn44view1
- **SQLite-first transparency**：學 DB Browser for SQLite 的資料透明感，以及 Joplin 那種使用者可以理解資料如何出入的感覺。citeturn44view9turn43view1
- **Desktop shell as packaging layer, not product brain**：學 Wails/Tauri 的桌面分發思維，但 Prism 目前自家 WebView2 + Go runtime 路線已成立，沒必要為框架而框架。citeturn44view4turn44view5turn39view0 |

## 建議路線圖

### 現有 Prism 穩定化

這一層用 **1–2 週**就該能做出明顯收益，而且**不要**碰 AI / sync / graph 這些大題。

| 面向 | 內容 |
|---|---|
| 目標 | 讓 Prism 的核心與邊界更可信：search 可解釋、backup 可理解、API 更清楚、文件更同步。 |
| 不做什麼 | 不做 semantic search、不做 installer/updater、不做多使用者 auth、不做大重構。citeturn42view3 |
| 具體任務 | ① `/api/notes` 搜尋加 `match_source/snippet`。② Settings/Docs 明確區分 DB backup 與 full profile backup。③ `hasMore` 改用 `total/page/per_page`。④ restart UX 改 health polling。⑤ 把 `SCHEMA.md` 的歷史敘事搬出主文。⑥ 補 category identity invariant tests。 |
| 驗收標準 | 搜尋結果能顯示命中來源；使用者不再把 DB download 誤認完整備份；前端不靠 `length===20` 判停；docs current truth 變短且更準。 |
| 風險 | 容易被誘惑順手重構太多。 |
| 依賴項 | 現有 API、前端 settings、測試框架。citeturn35view0 |
| 預估收益 | 這是最低成本、最高信任提升的一層。 |

### Prism vNext

這一層是 **1–2 個月**可做，而且仍然要守住「不是大產品」。

| 面向 | 內容 |
|---|---|
| 目標 | 把 Prism 從「能用」拉到「可以長期依賴」。 |
| 不做什麼 | 不把 AI 放進核心，不做協作，不做 sync daemon。 |
| 具體任務 | ① 按 bounded context 拆 `main.go`。② 知識 API 與系統/維運 API 做 capability profile。③ Markdown import round-trip。④ inbox/review lifecycle 最小版。⑤ typed templates 最小版。⑥ contract tests 或簡版 OpenAPI 導出。 |
| 驗收標準 | `main.go` 明顯縮小；API 文件與 TS 型別可自動驗證；匯入匯出 round-trip 可測；新增卡片型別不污染 generic note 流程。 |
| 風險 | 如果你同時做 typed cards + lifecycle + search schema，會開始碰資料模型設計。 |
| 依賴項 | 現有 schema v17、匯入匯出流程、UI/store 整理。citeturn41view5turn40view7 |
| 預估收益 | 真正把 Prism 固化成「可當個人知識層」的版本。 |

### Prism 升級版

這一層是 **3–6 個月以上**，而且前提是前兩層已經穩。

| 面向 | 內容 |
|---|---|
| 目標 | 擴成「Prism Core + sidecar 生態」，而不是變成全功能怪物。 |
| 不做什麼 | 不把聊天 UI、模型管理、向量索引、CRDT sync 一次塞進 Prism 本體。 |
| 具體任務 | ① Semantic search sidecar。② Prism MCP server。③ Browser capture extension。④ Research Radar sidecar。⑤ Full profile backup/sync assistant。⑥ Diff-aware update / versioned knowledge cards 進階版。 |
| 驗收標準 | sidecar 壞掉不影響 Prism Core；Prism Core 仍可單獨穩定工作；資料可帶出、可回復、可 API 使用。 |
| 風險 | 很容易因為「都是很酷的功能」而失去主軸。 |
| 依賴項 | 穩定 API contract、清楚的 plugin/sidecar interface。 |
| 預估收益 | 讓 Prism 變成真正可被 agent、生產流程、研究工具串接的本地知識平台。 |

## 防止過度設計與最終建議

先給最重要的一句：**Prism 現階段最該守住的，不是 editor、不是 graph、不是 AI，而是「本機可依賴的知識卡片層」這個核心。**README、架構文件、TODO 都已經反覆在替你踩煞車：不要自動擴成 semantic search、installer/updater、多使用者、雲端同步。這些不是保守，而是對定位的自覺。citeturn37view1turn39view0turn42view3

我建議直接把下面這套守則，當作 Prism 的架構憲法：

| 守則 | 原則 |
|---|---|
| 核心只做 durable local knowledge layer | 核心責任是存、搜、整理、匯出、API，不是聊天、推理、協作。 |
| 能做 sidecar 的，不進核心 | semantic search、MCP、agent memory、research radar、browser capture 優先外掛化。 |
| 能靠 import/export/API 解決的，不先做完整內建產品 | 很多需求其實不需要做成 full feature。 |
| 任何新增功能都要回答「它會不會污染知識層」 | 會造成 raw dump、重複卡片、模糊來源、無法回放的功能，一律先擋。 |
| 任何系統/維運能力都要明示 capability | 不要讓 notes API 與 host admin 功能界線含糊。 |
| 資料模型優先於炫目功能 | 若 schema 與 import/export 還不穩，先不要做 graph、AI、sync。 |
| 桌面 shell 是 distribution layer，不是第二個產品核心 | 打包與啟動很重要，但不應支配資料模型。 |
| 有歷史價值的模組可保留，但要清楚標示 ownership | 例如 `desktop-spike`。citeturn38view0turn39view0 |

最後給你最務實、最不空泛的結論。

**Prism 現階段最該守住的核心**：  
就是 **SQLite + FTS5 + local file storage + clean local REST API + card-oriented knowledge model**。換句話說，Prism 的核心不是「寫東西」，而是「把整理過、可重用、可行動的知識卡片穩定保存並讓別的工具可用」。citeturn37view1turn39view0turn41view3

**最該立刻改善的東西**：  
不是新增功能，而是四件事：
- 收斂 runtime/API 邊界
- 強化 search explainability
- 做好 backup/import/export 的資料主權
- 拆解 `main.go` 的維護風險  
這四件事做完，Prism 的完成度會比加十個新功能還高。citeturn17view2turn40view3turn40view7turn16view0

**最值得升級版探索的方向**：  
我只選三個：
- Semantic search sidecar
- Prism as local MCP server
- Browser capture + inbox/review pipeline  
因為這三個會放大 Prism 的核心價值，而不是替代它。citeturn44view0turn44view7turn42view3

**最不值得碰的東西**：  
多使用者 auth、雲端協作、即時同步 daemon、把 AI/embedding 硬塞進核心、把 Prism 做成 model hub/chat UI、以及因為桌面分發麻煩就先全面產品化 installer/updater。這些每一個都可能讓專案維護成本跳級。citeturn42view3turn39view0

**最值得參考的 5 個 GitHub 專案**：  
我會是這五個：
- **Joplin**：資料主權、匯入匯出、附件治理。citeturn43view1turn46view1
- **SilverBullet**：輕量擴充與 scriptable knowledge space。citeturn43view2turn46view2
- **TriliumNext Notes**：typed knowledge / metadata / template。citeturn43view3turn46view3
- **Meilisearch**：搜尋 UX 與可解釋性思路。citeturn43view7turn46view7
- **Paperless-ngx**：ingestion pipeline 與來源/狀態管理。citeturn44view3turn46view13

**如果現在只能做 3 個任務，我建議就是這 3 個**：

| 任務 | 原因 |
|---|---|
| 搜尋結果 explainability + snippet | 立刻提升 Prism 的核心體驗，而且不改產品定位。 |
| full profile backup/export 與 round-trip import 改善 | 這直接決定使用者敢不敢把知識交給 Prism。 |
| `main.go` 按 bounded context 輕拆 | 這是在為未來所有功能買保險。 |

最後的總判斷很明確：  
**Prism 現在不是不夠大，而是不夠「收斂」。**  
它最有價值的未來，不是變成下一個大型 PKM，也不是變成下一個 AI 工作台；而是把自己做成一個**小而硬、可攜、可搜尋、可匯出、可被工具使用的本地知識層**。如果你守住這個核心，升級版才有意義；如果守不住，升級版只會把現在的優點稀釋掉。citeturn37view1turn39view0turn42view3