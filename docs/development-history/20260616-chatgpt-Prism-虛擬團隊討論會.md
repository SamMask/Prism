
「Prism / Cerberus 產品架構決策稿」。核心方向已經很清楚：

Prism Core 要保持乾淨、穩定、本地優先；AI、論文雷達、主題追蹤、量化研究都應該做成 sidecar / 分支，不應污染 Core。
你真正需要的不是「AI 知識庫大平台」，而是：

Prism 負責存與搜。
Cerberus Research Radar 負責找交易研究線索。
CerberusCoin 負責驗證、回測、實驗與策略落地。
LLM 只做翻譯、抽取、整理，不做決策。

下面是重新整理、補充、增刪後的版本。

一、整體主軸整理

這次對話其實走了三個階段。

第一階段是 Prism Core 整理。
一開始從團隊角色設定切入，後來集中在 Prism 的現況：Go primary runtime、本地 SQLite、REST API、搜尋、備份、桌面化、Settings 維護頁、Codex 任務拆分。這一段的核心結論是：Prism 不該急著加 AI，而是要先產品化、穩定化、資訊架構清楚化。

第二階段是 避免過度設計。
後面討論 Search UX、Search Integrity、Agent Search、Backup Restore、Settings Maintenance、Codex Review Checklist 時，已經開始接近過度設計邊界。最後修正為：這些規格可以留在 backlog，但 active queue 只保留最小必要任務。不要因為討論過，就全部施工。

第三階段是 AI / 論文 / 研究雷達方向修正。
一開始我誤把「論文」理解成學術整理或研究生工具，後來你修正：你不是要做學術文獻服務，而是要自動找跟量化交易、交易數學、訂單簿、市場微觀結構有關的 paper，看能不能轉成交易假設、因子、風險濾網或穩健性改進。這個方向最後被重新命名成：

Cerberus Research Radar Lite

這是目前最有價值的新分支構想。

二、角色與會議模式整理

原本團隊角色最後收斂成：

角色	主要責任
Alex	最終決策、範圍收斂、避免失焦
Iris	知識結構、資料模型、分類標籤、資訊架構
Kenji	後端/API/工程可行性、避免大重構
Nolan	Agent / LLM 介面、安全接入、sidecar 邊界
Sophie	測試、回歸、防止 Codex 或重構破壞既有行為
Leo	挑戰前提、打破幻想、抓過度設計
Maria	搜尋、資料品質、研究資料、量化特徵抽取
Marcus	安全邊界、API 暴露、危險操作分級
Hana	UX、使用流程、文案、資訊層級
David	部署、備份還原、Pi / desktop 維運

實際開會時，固定用 6 個主發言角色就夠：

常駐角色	用途
Alex	收斂決策
Iris	確保資料與知識結構不歪
Kenji	判斷工程成本
Nolan	控制 Agent / LLM 邊界
Sophie	抓測試與回歸風險
Leo	防止過度設計與技術幻想

其他角色在特定議題出場即可。

補充建議：
之後每次研討會最好固定輸出三件事：

保留什麼
刪掉什麼
下一個可施工任務是什麼

否則會容易一路討論到越來越大。

三、Prism Core 的最終定位

Prism Core 的定位應該是：

本地優先的個人知識庫 / Prompt 管理 / REST API 資料底座。

它應該做：

Notes
Categories
Tags
Attachments
Source URLs
SQLite / FTS5 keyword search
匯入 / 匯出
備份 / 還原
Desktop shell
Agent-readable API
Search UX
Settings / Maintenance
本機或 trusted LAN 使用

它不應該做：

內建 AI chat
內建 semantic search
內建 embedding
GraphRAG
自動文獻綜述
自動交易研究
自動主題追蹤
自動寫策略
自動下單
Plugin platform
多使用者權限系統
公網服務化

補充修正：
Prism 的價值不是「AI 很強」，而是「資料乾淨、可控、可備份、可被 Agent 安全讀取」。

四、Prism Branch Architecture 最終版

整理後建議分支如下。

Branch	定位	是否進 Core	優先級
Prism Core	本地 KMS、搜尋、備份、REST API、desktop shell	是	最高
Prism AI Bridge	外部 Agent 安全讀 Prism，先 read-only	半進 Core	中
Prism Watch	RSS / arXiv / GitHub / blog / URL 追蹤	sidecar	中
Cerberus Research Radar	量化交易 / 訂單簿 paper → research cards → experiment backlog	sidecar	高
Prism Archive Intake	web / PDF / markdown / source intake	sidecar	中
Prism Scholar Service	學業/論文整理服務版	另開商業分支	低

這裡最重要的修正是：

Prism Scholar 不再是你的主線。
Cerberus Research Radar 才是你的真正需求。

Scholar 可以留作未來商業化想像，例如幫學生整理論文、做文獻回顧、準備報告。但自用主線應該是交易研究雷達。

五、目前已經過度設計的部分

需要刪減或暫緩的東西：

項目	判斷
Search Ranking / Relevance	暫緩。還沒有足夠使用痛點，會變小型搜尋引擎
GraphRAG / Semantic Search	太早，會污染 Core
內建 AI chat	暫不做，應交給外部 Agent
Search Integrity API	有價值，但不是現在最急
Agent Search Contract	先做文件，後做 read-only
自動修復資料	不做，維護動作要人工確認
自動備份排程	本機 .exe 不做，只保留手動備份
自動論文綜述	不適合你的主線
自動把 paper 變策略	禁止
自動寫 CerberusCoin repo	第一版禁止
自動下單	禁止
全域 OS 搜尋 / 全域熱鍵	暫緩
Plugin platform	太早
多使用者權限	太早

保留但放 backlog：

項目	處理
Search Result Highlight	可做，但先不急
Attachment Search 深化	等附件使用量變大再做
Search Integrity	Settings IA 完成後再接
Agent-safe read API	可作為下一階段
Watch Lite	可做候選 queue
CRR Lite	可開始規格化，先 docs/schema
六、目前應該立即施工的 Core 任務

主線應該縮成這些。

Phase 0：Prism Core 收斂
ABOUT-CURRENT-TRUTH-01
修正 Settings > About 裡仍寫 Flask 的錯誤文案。
改成 Go primary runtime / SQLite FTS5。
SETTINGS-IA-01
重排 Settings tabs：
外觀
組織
備份與還原
維護與健康
存取與系統
關於
BACKUP-UX-02
清楚區分：
匯出副本
匯入資料
Prism 內建還原點
還原資料庫
MAINT-COPY-01
把 WAL / consistency / restore / managed backup 等工程語言轉成人能懂的維護文案。
Desktop Shell Phase 0
Win32 message loop spike：空視窗 + tray + 單一 message loop。
不急著接 WebView2，不急著接後端。

這些是現在最值得做的，不會污染架構。

七、Settings / Maintenance 整理後的結論

Settings 的設計原則：

狀態先於動作；檢查與修復分開；危險操作放底部；工程術語退到補充文字。

建議新 tab：

Tab	放什麼
外觀	主題、語言、顯示模式
組織	分類、標籤、DataManager
備份與還原	JSON/Markdown/DB 匯出、JSON 匯入、Prism 內建還原點、restore
維護與健康	系統統計、WAL、資料一致性、未來 Search Integrity、Danger Zone
存取與系統	CSRF、安全邊界、Server Dashboard
關於	版本、runtime、資料位置、安全摘要

文案替換字典：

工程詞	使用者主標
WAL Checkpoint	整理資料庫暫存日誌
FTS Rebuild	重建搜尋索引
VACUUM	壓縮資料庫檔案
Consistency Check	資料一致性檢查
Managed Backup	Prism 內建還原點
DB Download	下載資料庫副本
Restore	還原資料庫
Danger Zone	危險操作

補充建議：
不要一開始就做 Maintenance Overview 很大一套。可以先重排資訊架構，後續再補 status cards。

八、Search UX 整理後的結論

Search UX 第一階段不是改搜尋引擎，而是讓搜尋「可理解」。

保留：

Search Context Bar
顯示 keyword、category、tag、archived、sort chips
可單獨清除
Empty State Recovery
找不到時說明是否因為 category / tag / archived 篩選造成
Search Scope Hint
說明目前搜尋範圍：標題、內文、備註、標籤、附件標題/路徑/文字附件
Recent Searches
localStorage，最多 5 筆，不進 DB
Mobile Search Entry
不要只在 desktop header 有搜尋入口

暫緩：

relevance ranking
semantic search
attachment body snippets
SearchHistory DB
advanced query language
每鍵即時搜尋

後續可做：

include_matches=1
matched_fields
snippet segments
attachment match badge

但這些不是 Core 當前第一順位。

九、Codex 工作方式整理

Codex 不應該自由發揮。所有任務都要用固定 prompt contract：

每個 Codex 任務包含：

任務目標
背景
允許修改檔案
禁止事項
具體要求
驗收指令
回報格式

Codex 完成後必須回報：

### Changed
- ...

### Verified
- ...

### Not Changed
- No API changes.
- No schema changes.
- No backend changes.
- No unrelated feature work.

審查時先看：

changed files 是否超出範圍
是否改 API / schema / backend
是否順手新增功能
build/test 是否真的跑過
是否違反安全邊界

硬退回條件：

未授權改 schema
未授權新增 API
任務外重構
引入 AI / embedding
自動修復
自動刪資料
回傳本機絕對路徑
大量格式化無關檔案
恢復隱藏的 PortConfig / UpdateSection
十、Search Integrity 的最終處理

Search Integrity 有價值，但現在暫緩。

它未來應該分成兩個 endpoint：

GET /api/system/search-integrity
POST /api/system/search-integrity/rebuild-fts

GET 只能診斷：

FTS 是否存在
Notes / Notes_FTS 是否一致
附件是否缺失
是否有 unsafe path
text attachment scan cap 是否可能造成不完整

POST 只能：

INSERT INTO Notes_FTS(Notes_FTS) VALUES('rebuild')

禁止：

不 VACUUM
不改 Notes
不改 Attachments
不刪檔案
不自動修復
不讓 Agent 自動觸發

補充判斷：
這一組規格可以保留，但不該卡住 Settings / Desktop / Backup UX。

十一、Cerberus Research Radar Lite 的最終定位

這是整段討論後最重要的新方向。

Cerberus Research Radar Lite 不是學術論文整理系統。
它是量化交易研究雷達。

它要做：

自動找量化交易 / 訂單簿 / 市場微觀結構 / crypto microstructure paper
把 paper 轉成 Research Signal Card
判斷資料能不能測
提出 feature candidate / risk filter / regime detector
手動批准後進 CerberusCoin backlog
回測與驗證由 CerberusCoin 處理

它不做：

自動寫文獻綜述
自動產策略
自動改 code
自動下單
自動寫 repo
自動把所有 paper 塞進 Prism
把 paper 結論當交易結論

最重要的一句：

paper 只能變成假設，不能直接變成策略。

十二、Quant Paper Taxonomy 最終版

第一版 taxonomy 建議：

類別	用途	MVP
Order Book Imbalance	entry / risk filter / 短線壓力	是
Microprice / Fair Price	fair price / 1m-5m 方向提示	是
Liquidity Resilience	掛單牆真假、流動性恢復	是
Crypto Microstructure	funding、OI、basis、liquidation、premium	是
Market Impact	大單衝擊、sweep detection	後
Order Flow Toxicity	adverse selection / avoid bad fills	後
Hawkes / Burst Process	burst detector / volatility warning	後
Volatility Forecasting	position sizing / risk mode	後
Regime Detection	strategy routing	後
Execution / Slippage	conservative backtest	後
Manipulation / Spoofing	anomaly / risk flag	後
Queue Imbalance	L3 dependent	暫緩

MVP 只啟用：

Order Book Imbalance
Microprice / Fair Price
Liquidity Resilience
Crypto Microstructure
十三、Research Signal Card Schema 整理版

最終建議 schema：

schema_version: 0.1
id: CRR-20260616-001
status: new  # new | screened | candidate | experiment_ready | tested | rejected | implemented | archived

source:
  title:
  authors:
  year:
  venue:
  source_platform: arxiv | semantic_scholar | openalex | manual
  source_query:
  url:
  pdf_url:
  doi:
  arxiv_id:
  semantic_scholar_id:
  openalex_id:
  retrieved_at:

taxonomy:
  primary_topic:
  secondary_topics:
  market_type:
  asset_class:
  data_granularity:
  expected_horizon:

trading_translation:
  core_hypothesis:
  market_mechanism:
  possible_alpha:
  possible_filter:
  possible_risk_use:
  possible_execution_use:
  directionality:
  expected_effect:
  why_it_might_work_in_btc:

data_fit:
  required_data:
  available_in_cerberus:
  missing_data:
  data_fit_level: A | B | C | D | E
  blocker:
  snapshot_limitation:

implementation:
  candidate_features:
  minimal_experiment:
  validation_path:
  backtest_feasibility:
  complexity: low | medium | high
  lookahead_risk:
  robustness_checks:

scoring:
  relevance: 0
  data_fit: 0
  implementability: 0
  robustness_value: 0
  novelty: 0
  total: 0

decision:
  action: skip | watch | read_deeper | create_candidate | create_experiment
  reason:
  next_step:

links:
  prism_note_id:
  cerberus_backlog_id:

資料可行性：

Level	定義	決策
A	只需 OHLCV / funding / OI / liquidation / premium	可快測
B	需要 L2 order book snapshot	可測，但標 snapshot limitation
C	需要 tick trades + L2	可研究，但成本高
D	需要 L3 message feed / queue position / cancel-add event	暫緩
E	需要交易所內部資料或不可取得資料	reject

硬規則：

D 最多 watch / read_deeper
E 必須 skip
沒 abstract 不准 create_experiment
沒可測 hypothesis 不准 create_candidate
需要極低 latency 不准當現階段實驗
LLM 不知道就填 unknown
十四、Paper Source Query Contract 整理版

來源：

arXiv
用來抓最新 paper。
Semantic Scholar
用來補 citation、related papers、paper ID、metadata。
OpenAlex
用來補 DOI、venue、author、concept、metadata normalization。

處理流程：

Source Adapter
  → Raw Paper Candidate
  → Normalized Paper Candidate
  → Dedup
  → Taxonomy Filter
  → LLM Extraction
  → Research Signal Card
  → Human Approval
  → Prism / Cerberus backlog

Normalized Candidate：

candidate_id:
source_platform:
source_id:
title:
authors:
year:
published_at:
updated_at:
abstract:
url:
pdf_url:
doi:
venue:
citation_count:
fields_of_study:
keywords:
external_ids:
source_query:
retrieved_at:
source_hits:

去重順序：

DOI
arXiv ID
Semantic Scholar ID
OpenAlex ID
normalized title + first_author + year

第一版 limits：

per_query_max: 10
weekly_raw_candidate_max: 50
weekly_llm_card_max: 10
auto_write_prism_notes: false
auto_write_cerberus_backlog: false

第一批 query seed：

- "limit order book" AND imbalance
- "order flow imbalance" trading
- microprice "limit order book"
- "liquidity resilience" "limit order book"
- "cryptocurrency" "market microstructure"
- "bitcoin" "order book"
- "cryptocurrency liquidity" trading
- "funding rate" "open interest" liquidation crypto

暫不啟用但保留：

- Hawkes process "order flow" trading
- "realized volatility" "limit order book"
- "market impact" "limit order book"
- "adverse selection" "limit order book"
十五、LLM 在 CRR 裡的角色

LLM 只做：

抽取假設
判斷資料需求
判斷是否適用 BTC / crypto
轉成 candidate features
指出 blocker
填 Research Signal Card

LLM 不做：

宣稱策略有效
自動產策略
自動改 code
自動下單
自動決定進 production
自由寫長篇摘要
腦補 missing data

Prompt 核心：

你是量化交易研究篩選器，不是學術摘要器。
請只根據 title / abstract / metadata，判斷這篇研究是否能轉成 CerberusCoin 的可測假設。
不得宣稱策略有效。
不得補不存在的資料。
不得把 paper 結論直接當交易結論。
如果資料不足，填 unknown。
如果無可測假設，action 必須是 skip 或 watch。
十六、Prism / CerberusCoin 的最終資料流
arXiv / Semantic Scholar / OpenAlex / manual seed
  ↓
Cerberus Research Radar sidecar
  ↓
Normalized Paper Candidate
  ↓
Research Signal Card
  ↓
Human approval
  ↓
Prism note
  ↓
CerberusCoin experiment backlog
  ↓
Backtest / OOS / robustness check
  ↓
factor / risk filter / execution filter / regime detector

Prism note template：

# [CRR] <paper title>

Status:
Action:
Data Fit:
Primary Topic:
Source:

## Trading Hypothesis

## Data Fit

## Candidate Features

## Validation Path

## Decision

Cerberus backlog item：

id: EXP-CRR-YYYYMMDD-001
source_card_id:
paper_title:
hypothesis:
feature_candidates:
required_data:
available_data:
validation_path:
expected_horizon:
risk_notes:
status: proposed
十七、增刪補改總表
應新增
新增項	原因
Prism Branch Architecture 文件	防止 Core 被 AI 分支污染
CRR docs folder	把研究雷達規格獨立保存
Research Signal Card schema	統一 paper → hypothesis
Normalized Paper Candidate schema	統一來源資料
Paper Source Query Contract	控制來源、去重、限流
LLM Extraction Contract	防止 LLM 自由發揮
Manual Approval Queue	防止自動污染 Prism / CerberusCoin
Codex Review Checklist	防止 Codex mega-diff
Settings IA 任務	修正設定頁資訊架構
Backup UX 任務	避免備份/還原誤解
應刪除或取消
刪除項	原因
Prism Scholar 作為自用主線	方向錯，太像研究生工具
內建 AI chat	污染 Core
自動學術綜述	非主要需求
自動 paper → strategy	風險過高
自動寫 CerberusCoin repo	容易污染 backlog
自動下單	禁止
Search Ranking 現階段施工	過早
GraphRAG / semantic search	太早
Plugin platform	太早
本機自動備份排程	暫不做
應改名
原名	新名
Prism Scholar	Cerberus Research Radar
Search tab	組織
Data tab	拆成「備份與還原」與「維護與健康」
Deploy tab	存取與系統
WAL Checkpoint	整理資料庫暫存日誌
Managed Backup	Prism 內建還原點
應暫緩
暫緩項	條件
Search Integrity API	Settings IA / Backup UX 完成後
Match metadata / highlight	Search Context Bar 完成後
Attachment body snippet	附件使用量增加後
Watch Lite	Core 穩定後
CRR source adapters	schema/docs 完成後
CRR LLM extraction	source adapter / schema 完成後
Relevance ranking	有真實搜尋痛點後
Semantic Search	Core 穩定且資料量足夠後
十八、最終 Roadmap
現在立刻做
ABOUT-CURRENT-TRUTH-01
SETTINGS-IA-01
BACKUP-UX-02
MAINT-COPY-01
Desktop Shell Phase 0
Search Entry UX / Search Context Bar
接著做
MAINT-OVERVIEW-01
Search Result Match Metadata
Agent Search Contract docs
CRR-01 Research Signal Card Schema
CRR-02 Normalized Paper Candidate Schema
CRR-03 Paper Source Query Contract
之後做
arXiv / Semantic Scholar / OpenAlex adapter
Dedup pipeline
LLM extraction contract
CRR pending queue
Prism note export
CerberusCoin backlog mapping
長期才做
Search Integrity API
Attachment Search 深化
Prism Watch Lite
Semantic Search
GraphRAG
Plugin
Scholar Service 商業分支
十九、最終一句話總結

Prism 不要變 AI 平台。
Prism 要變成乾淨可靠的本地知識核心。
Cerberus Research Radar 負責把交易相關論文轉成可測假設。
CerberusCoin 負責驗證那些假設。
LLM 只能輔助整理與抽取，不能替你判定有效，也不能直接進策略。

這是這整串討論最重要的收斂。

=====================
> 使用者要求：完整的全部對話全傳上 Notion，先別總結。
> 

> 本頁保留可見對話內容，不做摘要、不做重寫。
> 

> 注意：系統/開發者隱藏指令與模型私人推理無法匯出。以下為目前對話脈絡中可見的使用者與助理內容。
> 

---

## 使用者

再來幾輪研討會 主軸是

Settings / System Maintenance

延伸討論直到收斂後，再繼續推薦討論方向 

## 助理

我會先看目前 Settings 頁實際剩哪些區塊，再開會；這輪重點會放在「維護頁資訊架構」，不是新增一堆維護按鈕。

## 助理

目前 Settings 有五個 tab：外觀、資料、搜尋、部署、關於；維護功能主要塞在「資料」tab，搜尋 tab 反而只是分類/標籤管理。這已經透露出問題：Search Integrity 會找不到自然位置。

## 助理

判斷：**Settings / System Maintenance 現在最大問題不是功能不夠，而是資訊架構混在一起。**  

目前「資料」tab 裡同時塞了資料庫維護、統計、備份匯入、安全、危險區；「搜尋」tab 卻只是分類與標籤管理；「部署」tab 只剩 Server Dashboard。這代表後面如果再加入 Search Integrity、Restore 後檢查、FTS rebuild，很容易變成一堆按鈕堆在「資料」下面。

另外有一個小但重要的 current-truth 問題：About 區還寫「後端: Flask + SQLite (FTS5)」，但同一段又說目前穩定路徑是 Go primary runtime；這會誤導後續維護者，應該修。

---

## 第一輪：Settings 現況盤點

**Alex：**  

現在 Settings 有五個 tab：外觀、資料、搜尋、部署、關於。這個結構表面上清楚，但實際職責有點歪。`data` tab 裡有 `SystemMaintenance`、`SystemStatsSection`、`BackupImportSection`、`SecuritySection`、`DangerZoneSection`；`search` tab 只有 `DataManager`，也就是分類/標籤管理。

問題不是不能用，而是下一階段功能會沒有位置。Search Integrity 放哪？Restore 後搜尋檢查放哪？FTS rebuild 放哪？如果都丟進「資料」，資料 tab 會變成垃圾桶。

**Iris：**  

我會先改命名邏輯。現在「搜尋」tab 實際是「分類與標籤管理」，不是搜尋設定。使用者看到搜尋 tab，會期待看到搜尋範圍、索引狀態、搜尋修復、最近搜尋、搜尋體感設定；結果看到分類標籤管理，心智模型錯位。

**Kenji：**  

`SystemMaintenance` 現在只有兩件事：WAL Checkpoint 與資料一致性檢查。文案也已經說這是進階維護與疑難排解工具，平常不需要手動執行。  

這個方向對，但它太底層。使用者不應該一進來就看到 WAL，而應該先看到「目前狀態正常 / 需要注意」。

**Sophie：**  

`BackupImportSection` 目前已經包含三類東西：匯出 JSON / DB / Markdown、匯入 JSON、從 managed backup 還原。還原流程也會 stage restore、等待 server 健康、成功後 reload。  

這些都不是壞設計，但資訊層級應該再拆：匯出、備份、匯入、還原是不同風險等級。

**Leo：**  

現在看起來像工程師把能用的工具都塞進設定頁。短期可以，長期會讓一般使用者怕按錯。尤其「維護」跟「危險區」如果離太近，很容易製造焦慮。

---

## 第二輪：Settings 應該怎麼分層

**Hana：**  

我建議 Settings 先改成「使用者任務」導向，不是技術模組導向。使用者進設定通常想做這幾件事：

1. 改外觀 / 語言。
2. 管理分類、標籤。
3. 備份、匯入、還原。
4. 檢查系統和搜尋是否正常。
5. 管理安全與 API 暴露邊界。
6. 看版本與診斷資訊。

所以 tab 可以改成：

| 新 tab | 放什麼 |
| --- | --- |
| 外觀 | 主題、語言、顯示密度、卡片模式 |
| 組織 | 分類、標籤、合併、清理 unused tag |
| 備份與還原 | 匯出、managed backup、restore、import |
| 維護與健康 | DB consistency、Search Integrity、FTS rebuild、WAL、Vacuum |
| 存取與部署 | CSRF、API 暴露提醒、Server Dashboard、Pi / desktop runtime 狀態 |
| 關於 | 版本、runtime、資料位置、授權、current truth |

**Alex：**  

我同意方向，但不要一次大改所有 UI。第一階段可以只做命名與搬家，避免大 diff。

**Kenji：**  

技術上可以保留元件，只調整 SettingsPage 的 tab 與 section placement。這符合 anti-bloat：不先重寫元件，不新增抽象，只改資訊架構。

**Leo：**  

對，不要又做一個 Settings framework。先把東西放對地方。

---

## 第三輪：Maintenance 的風險分級

**Marcus：**  

維護操作一定要分風險等級。現在 WAL、consistency check、backup、restore、import、danger zone 都混在同一個 data tab。未來如果再加 FTS rebuild 和 search integrity，必須有風險語言。

我建議四級：

| 等級 | 例子 | UI 行為 |
| --- | --- | --- |
| Read-only check | 系統統計、資料一致性檢查、Search Integrity | 可直接執行 |
| Safe maintenance | WAL checkpoint、FTS rebuild | 顯示說明，可按鈕執行 |
| Data-changing operation | JSON import、restore backup、清除 history | 需要確認 modal |
| Destructive / irreversible | delete all、media cleanup delete、restore danger zone | 紅色區、二次確認、清楚後果 |

**Sophie：**  

這也對測試有幫助。Read-only 操作不應該改 DB；Safe maintenance 可以改 index / WAL 但不改 notes；Data-changing 要有 fixture；Destructive 要有明確 confirm。

**Maria：**  

Search Integrity 應該被歸類為 read-only check；FTS rebuild 是 safe maintenance；attachment cleanup 是 destructive 或至少 data-changing。不要混。

**Leo：**  

這個分級比 tab 名稱更重要。使用者不怕功能多，怕不知道哪個按鈕會毀資料。

---

## 第四輪：Search Integrity 放哪裡

**Iris：**  

搜尋現在有自己的 tab，但實際放的是分類標籤。我的建議：把「搜尋」tab 改名成「組織」，然後新增「維護與健康」tab 裡放 Search Integrity。

**Maria：**  

Search Integrity 不是搜尋偏好，它是健康檢查。它應該跟資料一致性、WAL、FTS rebuild 放一起。使用者搜尋怪怪的時候，應該去「維護與健康」看狀態，而不是去「搜尋設定」找神秘選項。

**Kenji：**  

但 Search UX 的「最近搜尋」「搜尋範圍提示」「搜尋入口設定」如果未來有設定，應該放哪？

**Hana：**  

那是 UI preference，可以放外觀或搜尋體驗。但目前不用新增設定。Search Integrity 是系統維護，不是 UX preference。

**Alex：**  

收斂：先不新增「搜尋偏好」。搜尋相關健康檢查進「維護與健康」；分類標籤改進「組織」。

---

## 第五輪：Backup / Restore 的資訊架構

**David：**  

Backup / Restore 要避免三個混淆：

第一，「匯出 JSON」不是完整備份。它適合交換和搬資料，但不等於完整資料庫狀態。  

第二，「下載 .db」是下載一份快照，server 不留存；這跟 managed backup 不一樣。  

第三，restore 只應列出 managed backups，不應讓使用者誤以為剛下載的 .db 自動出現在還原清單。

**Hana：**  

UI 可以拆成三張卡：

1. **匯出副本**：JSON、Markdown、DB download。文案說「下載到你的電腦，Prism 不保留這份」。
2. **建立還原點**：managed backup，顯示 keep count、最近建立時間、總大小。
3. **還原資料庫**：列出 managed backups，清楚說會重啟 Prism、覆蓋目前 DB、還原前會做 safety copy。

**Sophie：**  

現在 restore confirm modal 已經寫得不錯：會說覆蓋目前 DB、Prism 自動重新開啟、目前資料庫會先備份一份。  

缺的是 restore 完成後的後續：應該接 Search Integrity 檢查，而不是只 reload 回畫面。

**Leo：**  

這裡要白話，不要叫 managed backup。可以 UI 顯示「Prism 內建還原點」，文件裡再叫 managed backup。

---

## 第六輪：System Maintenance 首頁應該長什麼樣

**Alex：**  

我建議「維護與健康」tab 首屏不要先列按鈕，而是先列狀態：

- 資料庫：正常 / 警告 / 危險
- 搜尋索引：正常 / 需重建 / 未檢查
- 附件：正常 / 有缺失 / 未檢查
- 備份：最近還原點 / 無還原點
- API 安全：本機 / 區網 / 未知

**Maria：**  

Search Integrity 可以成為其中一張狀態卡。資料一致性檢查是另一張。WAL / FTS rebuild 是狀態卡裡的「修復動作」，不要一開始就露出一堆按鈕。

**Kenji：**  

第一版可以不做全自動檢查，只在進入 tab 時顯示「未檢查」與「執行檢查」。避免每次進設定就跑 DB / file scan。

**Sophie：**  

對。health check 觸發要可控。否則測試、效能和 race 都會變複雜。

**Leo：**  

狀態先於動作。這句可以當維護頁設計原則。

---

## 第七輪：About / Deploy / Security 的歸位

**Marcus：**  

現在 `deploy` tab 只剩 ServerDashboardSection，因為端口設定、版本更新、部署安全邊界被隱藏，理由是封裝成 .exe 後對使用者無用、Pi 上也只是資訊性。  

但 API 安全邊界還是需要在某個地方可見，尤其 Prism 沒有內建 auth/token。這不一定叫部署，應該叫「存取與安全」。

**Kenji：**  

`about` 裡的 backend Flask 文案必須修。這是 current truth bug。README 和 CLAUDE 都已經說 Go primary 是唯一 runtime，Python backend source 已移除；About 還寫 Flask 會誤導。

**Hana：**  

About 不該塞太多維護資訊。About 可以顯示 runtime、版本、資料目錄；真正的 server dashboard、logs、hardware 放「存取與系統」或「維護與健康」。

**Leo：**  

關於頁寫錯 runtime 這種小錯很毒，因為後面 Agent 會讀文件，然後開始以為還有 Flask。先修掉。

---

## 第八輪：收斂成任務

這輪收斂成四個可施工任務，不要一次重寫整個 Settings。

### SETTINGS-IA-01 — Settings Information Architecture Refresh

```markdown
## SETTINGS-IA-01 — Settings Information Architecture Refresh

目標：
重整 Settings tab 與 section placement，讓維護、備份、搜尋健康、分類標籤、安全邊界各有清楚位置。

建議 tabs：
- 外觀
- 組織
- 備份與還原
- 維護與健康
- 存取與系統
- 關於

搬移：
- DataManager 從「搜尋」移到「組織」。
- BackupImportSection 移到「備份與還原」。
- SystemMaintenance / SystemStatsSection 移到「維護與健康」。
- SecuritySection / ServerDashboardSection 移到「存取與系統」。
- DangerZoneSection 放在「維護與健康」最下方，或獨立危險區。
- About 修正 runtime wording：Go primary runtime / SQLite FTS5，不再寫 Flask backend。

禁止：
- 不重寫元件。
- 不新增 schema。
- 不改 API。
- 不恢復被隱藏的 PortConfig / UpdateSection，除非另開任務。
```

### MAINT-OVERVIEW-01 — Maintenance Health Overview

```markdown
## MAINT-OVERVIEW-01 — Maintenance Health Overview

目標：
在「維護與健康」tab 顯示狀態總覽，先讓使用者知道狀態，再決定是否執行維護動作。

狀態卡：
- 資料一致性
- 搜尋索引
- 附件狀態
- 備份狀態
- WAL / DB maintenance

規則：
- 預設不自動跑重檢查，只顯示未知 / 上次結果。
- 使用者按「檢查」才執行 read-only checks。
- repair actions 只在 warning / critical 後顯示。

禁止：
- 不自動 rebuild FTS。
- 不自動 VACUUM。
- 不自動刪除附件。
```

### BACKUP-UX-02 — Backup / Export / Restore Separation

```markdown
## BACKUP-UX-02 — Backup / Export / Restore Separation

目標：
清楚區分「匯出副本」、「建立還原點」、「還原資料庫」。

UI 分區：
1. 匯出副本：
   - JSON
   - Markdown zip
   - DB download
   - 說明：下載後 Prism 不保留此副本。

2. 建立還原點：
   - managed backup / Prism 內建還原點
   - 顯示 keep count、最近還原點、總大小。

3. 還原資料庫：
   - 只列出 managed backups。
   - 說明會重啟 Prism。
   - 說明還原前會建立 pre-restore safety copy。
   - 還原完成後引導 Search Integrity check。

禁止：
- 本機 .exe 不新增自動排程。
- 不把 DB download 混入 restore list。
- 不自動雲端同步。
```

### ABOUT-CURRENT-TRUTH-01 — About Runtime Wording Fix

```markdown
## ABOUT-CURRENT-TRUTH-01 — About Runtime Wording Fix

目標：
修正 Settings > About 的 runtime 文案，避免 Flask / Go primary current truth 衝突。

修改：
- 後端：Go primary runtime / SQLite FTS5。
- 移除 Flask wording。
- 顯示資料位置：knowledge.db、static/uploads、docs/attachments。
- 顯示安全邊界摘要：本機優先，無內建 auth/token，不建議公網暴露。

驗收：
- About 頁不再出現 Flask backend 作為 current runtime。
- README / CLAUDE / API_REFERENCE current truth 不衝突。
```

---

## 最終結論

Settings / System Maintenance 的核心設計原則應該是：

**狀態先於動作；備份先於修復；危險操作最後；工程術語只在進階區出現。**

建議優先順序：

| 順序 | 任務 | 理由 |
| --- | --- | --- |
| ---: | --- | --- |
| 1 | ABOUT-CURRENT-TRUTH-01 | 小修但重要，避免 current truth 汙染 |
| 2 | SETTINGS-IA-01 | 先把資訊架構放正 |
| 3 | BACKUP-UX-02 | 備份 / 匯出 / 還原目前最容易誤解 |
| 4 | MAINT-OVERVIEW-01 | 維護頁先顯示狀態，不先堆按鈕 |
| 5 | SEARCH-INTEGRITY-01 | 接進維護與健康 tab |
| 6 | SEARCH-INTEGRITY-02 | warning 後才顯示 FTS rebuild |
| 7 | BACKUP-SEARCH-01 | restore 完成後引導搜尋完整性檢查 |

不建議現在做：

- 自動修復全部問題。
- 自動排程本機備份。
- 把維護頁做成工程 dashboard。
- 把 Search Integrity 塞在「搜尋」tab。
- 重新啟用已隱藏的 port/update/deploy sections。
- 新增 plugin / cloud sync / multi-user permissions。

---

## 下一輪推薦討論方向

下一輪建議開：

**Implementation Task Plan / Codex Handoff 會**

主軸：把 `ABOUT-CURRENT-TRUTH-01`、`SETTINGS-IA-01`、`BACKUP-UX-02`、`MAINT-OVERVIEW-01` 拆成 Codex 可一次一任務執行的 atomic tasks，明確列出改哪些檔案、禁止改哪些地方、跑哪些測試。

備選方向：

**Maintenance Copywriting / Risk Language 會**

主軸：把 WAL、FTS、managed backup、restore、vacuum、consistency check 這些工程語言改成使用者看得懂的文案，同時保留進階說明。

我建議下一輪先開 **Implementation Task Plan / Codex Handoff 會**。現在規格已經夠清楚，再繼續抽象討論會開始空轉。
## 使用者

再來幾輪研討會 主軸是

Implementation Task Plan / Codex Handoff 會

Maintenance Copywriting / Risk Language 會

延伸討論直到收斂後，再繼續推薦討論方向 

## 助理

我會把這輪收斂成「可以直接丟給 Codex 的任務切片」與「維護頁文案規則」。重點是避免 mega-diff、避免工程術語嚇人，也避免 Codex 自作主張擴功能。

## 助理

判斷：現在可以收斂到 Codex 任務了。不要再讓 Codex 自由發揮「重做 Settings」；要給它一串小任務，每次只改一個切面，明確限制檔案、禁止擴功能、驗收 build。

---

## 第一輪：先決定 Codex Handoff 原則

**Alex：**  

這輪不讓 Codex 做大重構。任務要拆成「看得見、可回退、可測」的小步。第一步不是做維護總覽，也不是新增 Search Integrity endpoint，而是先修 current truth，因為 About 頁還寫 Flask，這跟 Go primary 現況衝突。

**Kenji：**  

任務順序應該是：

1. 修文案 current truth。
2. 改 Settings tab 資訊架構。
3. 抽出維護頁風險文案規則。
4. 拆清楚備份 / 匯出 / 還原。
5. 最後才做 Maintenance Overview。

不要一開始就新增 endpoint。`Search Integrity` 還沒 runtime endpoint，Settings 先預留位置即可。

**Sophie：**  

每個 Codex 任務都要有禁止事項。不然它可能順手改 API、改 schema、重寫元件、加新狀態管理。這裡只做前端資訊架構與文案，除非任務明確允許。

**Leo：**  

直接講：Codex 最怕「幫我整理一下設定頁」。它會整理到你媽都不認得。要用「只改這幾個檔案，不准新增功能」的格式。

---

## 第二輪：任務排序收斂

**Hana：**  

使用者角度，第一順位是降低恐懼。現在「資料庫維護（進階）」裡有 WAL Checkpoint、資料一致性檢查；文案雖然有說日常不用手動執行，但仍偏工程語言。備份區也同時有 JSON、DB、Markdown 匯出、JSON 匯入、DB 還原，風險等級混在一起。

**Iris：**  

所以資訊架構要先定：

- 「搜尋」改成「組織」。
- 「資料」拆成「備份與還原」與「維護與健康」。
- 「部署」改成「存取與系統」。
- 「關於」只放 current truth，不要放操作按鈕。

**Marcus：**  

維護文案要明確分風險：檢查、修復、覆蓋、刪除。不要讓 WAL、FTS、restore、danger zone 看起來都是同等按鈕。

**David：**  

備份文案要特別清楚。下載 `.db` 是「匯出副本」，不是「建立系統內還原點」。目前 restore UI 只列 server-side backups，這是對的，但 UI 文案要讓人知道差別。

---

## 第三輪：Maintenance Copywriting / Risk Language 規則

**Alex：**  

文案規則先定，否則每個區塊會各講各的。

**Hana：**  

我建議四級風險文案：

| 等級 | 顯示名稱 | 語氣 | 例子 |
| --- | --- | --- | --- |
| 檢查 | 不會改資料 | 中性 | 資料一致性檢查、搜尋完整性檢查 |
| 維護 | 不改筆記內容，但會整理系統狀態 | 輕提醒 | WAL 合併、FTS 重建 |
| 還原 / 匯入 | 會改變資料庫內容 | 明確確認 | JSON 匯入、DB restore |
| 危險 | 可能刪除資料或難以復原 | 強警示 | 清除歷史、刪除媒體、Danger Zone |

**Leo：**  

把「WAL Checkpoint」直接丟給使用者看很工程。按鈕可以還叫 WAL，但標題要改成「整理資料庫暫存日誌」，下面小字再寫 WAL。

**Maria：**  

FTS 也一樣。使用者不需要先知道 FTS5，只要知道「搜尋索引」即可。進階說明再寫 FTS。

**Sophie：**  

Confirm modal 要固定句型：

「這會做什麼」  

「不會做什麼」  

「是否可復原」  

「需要多久不寫，因為不能承諾時間；只說畫面可能短暫中斷或需重新啟動」

---

## 第四輪：Codex 任務卡收斂

下面這批可以直接作為 handoff 任務。建議一次只丟一個。

### 1. ABOUT-CURRENT-TRUTH-01

**目的：** 先修 current truth，避免 Flask/Go 互相打架。

**允許修改：**

- `frontend/src/pages/SettingsPage.tsx`
- 如有必要，更新對應測試或 snapshot

**禁止：**

- 不改 Settings tab 結構
- 不新增 API
- 不改後端
- 不改 schema
- 不恢復隱藏的部署 sections

**Codex 任務稿：**

```markdown
任務：ABOUT-CURRENT-TRUTH-01 — 修正 Settings > About runtime 文案

請只修正 SettingsPage.tsx 的 About 區塊文案。

目標：
- 移除「後端: Flask + SQLite (FTS5)」。
- 改成「後端: Go primary runtime / SQLite (FTS5)」。
- 保留本地優先、knowledge.db、static/uploads、docs/attachments 的說明。
- 增加一句安全邊界摘要：Prism 預設本機 / trusted LAN 使用，無內建 API Token，不建議直接暴露公網。

禁止：
- 不改 Settings tabs。
- 不改 API。
- 不改 schema。
- 不改其他頁面。
- 不新增元件。

驗收：
- frontend build 通過。
- About 頁不再出現 Flask 作為 current backend。
```

---

### 2. SETTINGS-IA-01

**目的：** 重排 Settings tabs 與 sections，不重寫元件。

**允許修改：**

- `frontend/src/pages/SettingsPage.tsx`

**可能涉及：**

- tab label
- tab icon
- section placement

**禁止：**

- 不改既有元件內部行為
- 不新增後端 API
- 不改 `SystemMaintenance`
- 不改 `BackupImportSection`
- 不改 `DataManager`
- 不新增 search-integrity 假按鈕

**Codex 任務稿：**

```markdown
任務：SETTINGS-IA-01 — Settings 資訊架構重排

請重排 SettingsPage.tsx 的 tabs 與既有 sections。

新 tabs：
- appearance：外觀
- organization：組織
- backup：備份與還原
- maintenance：維護與健康
- system：存取與系統
- about：關於

搬移規則：
- AppearanceSection → 外觀
- DataManager → 組織
- BackupImportSection → 備份與還原
- SystemMaintenance + SystemStatsSection → 維護與健康
- SecuritySection + ServerDashboardSection → 存取與系統
- DangerZoneSection → 維護與健康最下方，並保留危險區語意
- About 區保留已修正的 Go primary current truth

禁止：
- 不新增新 API 呼叫。
- 不改元件內部邏輯。
- 不恢復 PortConfigSection / UpdateSection。
- 不新增 Search Integrity UI；那是後續任務。
- 不改路由系統，只維持 query param tab 切換。

驗收：
- 所有 tab 可切換。
- 每個 section 出現在新位置。
- 舊的 ?tab=data / ?tab=search 行為如無 migration，至少不 crash，落到預設 tab 或合理 tab。
- npm run build 通過。
```

**Kenji 補充：**  

這裡可能要處理舊 query param：`data`、`search`、`deploy`。可以做簡單 alias：

- `data` → `maintenance` 或 `backup`？我建議 `maintenance`
- `search` → `organization`
- `deploy` → `system`

不要讓舊 URL 直接壞掉。

---

### 3. MAINT-COPY-01

**目的：** 改維護區文案，不改功能。

**允許修改：**

- `frontend/src/components/SystemMaintenance.tsx`

**禁止：**

- 不改 api calls
- 不改 WAL / consistency 行為
- 不新增 FTS rebuild
- 不新增 Search Integrity endpoint

**Codex 任務稿：**

```markdown
任務：MAINT-COPY-01 — 維護頁文案與風險語言修正

請只修改 SystemMaintenance.tsx 的顯示文案與區塊說明，不改 API 呼叫與功能。

文案方向：
- 「WAL Checkpoint」標題改成「整理資料庫暫存日誌」
  - 小字補充：進階名稱 WAL Checkpoint；通常不需要手動執行，備份前或疑難排解時使用。
- 「資料一致性檢查」維持，但補充：此操作只檢查，不會修改資料。
- 頂部說明改成：
  - 這裡是進階維護工具。建議先執行檢查，再依結果決定是否維護。
- health 顯示用語：
  - healthy → 正常
  - warning → 需要注意
  - critical → 需要處理
- 未使用標籤不要用警告語氣，因為它不一定是錯誤。

禁止：
- 不新增按鈕。
- 不改 api.walCheckpoint。
- 不改 api.checkConsistency。
- 不新增 Search Integrity。
- 不新增自動修復。

驗收：
- 功能行為不變。
- 文案不再把所有維護操作講得像危險操作。
- npm run build 通過。
```

---

### 4. BACKUP-UX-02

**目的：** 備份 / 匯出 / 還原分清楚。

**允許修改：**

- `frontend/src/components/settings/BackupImportSection.tsx`

**禁止：**

- 不改 restore API
- 不新增本機自動備份排程
- 不把 download backup 混進 restore list
- 不改 server-side backup retention
- 不新增 cloud sync

**Codex 任務稿：**

```markdown
任務：BACKUP-UX-02 — 備份、匯出、還原文案與區塊分離

請重整 BackupImportSection.tsx 的 UI 文案與區塊標題，但不要改 API 行為。

分成三個主要區塊：

1. 匯出副本
- JSON
- Markdown zip
- SQLite .db
- 文案說明：這些是下載到你電腦的副本，Prism 不會自動保留在還原清單裡。

2. 匯入資料
- JSON 匯入
- 文案說明：匯入會新增資料；依模式略過或建立重複筆記。

3. Prism 內建還原點
- 顯示 server-side backup list
- 說明：只有這裡列出的還原點可以直接用「還原資料庫」。
- 還原前會自動保存目前資料庫為 safety copy。
- 還原會重新啟動 Prism 程序，不是重開電腦。

Restore modal：
- 明確列出會發生：
  - 覆蓋目前資料庫
  - 還原前自動保存目前資料庫
  - Prism 會重新啟動
- 明確列出不會發生：
  - 不會重開電腦
  - 不會自動刪除你的外部下載備份

禁止：
- 不改 api.restoreBackup。
- 不改 waitForHealthy。
- 不改備份列表載入邏輯。
- 不新增 Search Integrity check；restore 後檢查是後續 BACKUP-SEARCH-01。

驗收：
- 匯出、匯入、還原區塊語意清楚。
- restore flow 行為不變。
- npm run build 通過。
```

---

### 5. MAINT-OVERVIEW-01

**目的：** 維護頁改成「先看狀態，再做動作」。

**前提：** `SETTINGS-IA-01`、`MAINT-COPY-01` 完成後再做。

**允許修改：**

- `frontend/src/components/SystemMaintenance.tsx`
- 如必要可新增小型 presentational component

**禁止：**

- 不新增後端 endpoint
- 不新增 Search Integrity
- 不自動跑檢查
- 不自動修復

**Codex 任務稿：**

```markdown
任務：MAINT-OVERVIEW-01 — 維護與健康狀態總覽

請在 SystemMaintenance.tsx 中加入狀態總覽概念，但不新增後端 API。

目前只整合現有兩個動作：
- 資料一致性檢查
- WAL 暫存日誌整理

UI：
- 頂部顯示「維護與健康」說明卡。
- 顯示兩張狀態卡：
  1. 資料一致性：未檢查 / 正常 / 需要注意 / 需要處理
  2. 資料庫暫存日誌：未執行 / 已整理
- 使用者按「檢查」後才更新資料一致性狀態。
- 使用者按「整理」後才更新 WAL 狀態。

禁止：
- 不進入頁面就自動檢查。
- 不新增 Search Integrity 假資料。
- 不新增 FTS rebuild。
- 不新增 VACUUM。
- 不新增自動修復。

驗收：
- 頁面初始不自動發 maintenance API。
- 按資料一致性檢查後狀態卡更新。
- 按 WAL 整理後狀態卡更新。
- npm run build 通過。
```

---

## 第五輪：Maintenance Copywriting 字典收斂

這份可以給 Codex 當文案規則，不一定要全部一次改。

| 工程詞 | 使用者主標 | 進階補充 |
| --- | --- | --- |
| WAL Checkpoint | 整理資料庫暫存日誌 | 進階名稱：WAL Checkpoint |
| FTS Rebuild | 重建搜尋索引 | 用於搜尋結果異常時 |
| VACUUM | 壓縮資料庫檔案 | 可減少資料庫檔案大小 |
| Consistency Check | 資料一致性檢查 | 只檢查，不修改資料 |
| Managed Backup | Prism 內建還原點 | 可直接用來還原資料庫 |
| DB Download | 下載資料庫副本 | Prism 不會保留這份下載檔 |
| Restore | 還原資料庫 | 會覆蓋目前資料庫，還原前會建立安全副本 |
| Danger Zone | 危險操作 | 可能刪除資料或難以復原 |

**Leo：**  

這張表很有用。以後 Codex 改文案，叫它照這張，不要自己發明「資料庫快照一致性狀態修復工作流」這種鬼話。

---

## 第六輪：最終收斂順序

**Alex：**  

正式建議丟 Codex 的順序：

1. `ABOUT-CURRENT-TRUTH-01`
2. `SETTINGS-IA-01`
3. `MAINT-COPY-01`
4. `BACKUP-UX-02`
5. `MAINT-OVERVIEW-01`

**Kenji：**  

前兩個最重要。尤其 About current truth 是低成本高收益。Settings IA 則是後面所有維護功能的地基。

**Sophie：**  

每個任務完成後至少跑：

```bash
cd frontend && npm run build
```

如果有測試覆蓋 Settings，就跑相關測試。不要要求全 repo 大測，除非任務碰 API 或 Go runtime。

**Nolan：**  

同時要在 `docs/TODO.md` 記錄這批任務，不然下次 Codex 會不知道 current roadmap。

**Leo：**  

還有一條：不要讓 Codex 自動順手做 Search Integrity endpoint。這個誘惑很大，但這輪不准。

---

## 可以直接存進 TODO 的任務組

```markdown
## SETTINGS-MAINTENANCE-UX — Settings / System Maintenance 收斂任務組

目標：
重整 Settings 資訊架構與維護文案，讓備份、還原、資料維護、搜尋健康、安全邊界各有清楚位置。第一階段不新增 API、不改 schema、不做自動修復。

### ABOUT-CURRENT-TRUTH-01
- 修正 Settings > About runtime 文案。
- 後端改為 Go primary runtime / SQLite FTS5。
- 移除 Flask current backend wording。
- 不改 tabs、不改 API、不改 schema。

### SETTINGS-IA-01
- Settings tabs 改為：外觀、組織、備份與還原、維護與健康、存取與系統、關於。
- DataManager → 組織。
- BackupImportSection → 備份與還原。
- SystemMaintenance + SystemStatsSection → 維護與健康。
- SecuritySection + ServerDashboardSection → 存取與系統。
- DangerZoneSection → 維護與健康底部或危險區。
- 不重寫元件，不新增功能。

### MAINT-COPY-01
- 修正 SystemMaintenance 文案。
- WAL Checkpoint 對使用者顯示為「整理資料庫暫存日誌」。
- 資料一致性檢查標明「只檢查，不修改資料」。
- health 文案改為：正常 / 需要注意 / 需要處理。
- 不新增按鈕，不新增 API。

### BACKUP-UX-02
- BackupImportSection 拆成：匯出副本、匯入資料、Prism 內建還原點。
- 明確說明 DB download 不會進入還原清單。
- Restore modal 說明：覆蓋目前 DB、還原前建立 safety copy、Prism 程序會重新啟動、不會重開電腦。
- 不改 restore API，不新增自動備份。

### MAINT-OVERVIEW-01
- 在 SystemMaintenance 加狀態總覽。
- 先顯示狀態，再顯示動作。
- 初始不自動跑檢查。
- 不新增 Search Integrity、FTS rebuild、VACUUM、自動修復。

共同禁止：
- 不改 schema。
- 不新增後端 API。
- 不恢復 PortConfigSection / UpdateSection。
- 不新增 cloud sync。
- 不新增本機自動備份排程。
- 不新增 semantic search / AI。
- 不做 mega-diff。

共同驗收：
- `cd frontend && npm run build` 通過。
- Settings tabs 可切換。
- 既有備份、還原、WAL、consistency check 行為不變。
```

---

## 最終結論

這輪收斂後，最適合交給 Codex 的不是「做一個新的維護系統」，而是：

**先修真相，再重排位置，再修文案，最後才做狀態總覽。**

這樣風險最低，也最符合 Prism 現在的 anti-bloat 路線。

---

## 下一輪推薦討論方向

下一輪建議開：

**Codex Prompt Contract 會**

主軸：把上面 5 個任務轉成可以直接貼給 Codex 的 prompt 模板，包括「任務目標、允許修改檔案、禁止事項、驗收指令、回報格式」。這樣你之後就能一個任務一個任務丟，不會讓 Codex 暴走。

備選方向：

**Settings Visual Layout 會**

主軸：討論維護頁每張卡片怎麼排、狀態色怎麼用、danger zone 怎麼壓到底部、備份與還原怎麼避免誤按。

我建議先開 **Codex Prompt Contract 會**。現在規格夠完整了，下一步要把它變成可執行指令。
# ChatGPT 對話逐字稿 — Prism / Cerberus 研討 2026-06-16 Part 3

## 使用者

再來幾輪研討會 主軸是

Codex Prompt Contract 會 / Settings Visual Layout 會

延伸討論直到收斂後，再繼續推薦討論方向 

## 助理

我會把這輪收斂成兩個輸出：一是 Codex 任務 prompt 的固定格式，二是 Settings 視覺與資訊層級規則。目標是讓後續每個任務都能直接貼給 Codex，而不是再臨場解釋。

## 助理

判斷：這輪可以收斂成兩個可執行產物：

第一，**Codex Prompt Contract**：每個任務都用固定格式，限制檔案、限制範圍、限制禁止事項、要求驗收回報，避免 Codex 自動擴 scope。

第二，**Settings Visual Layout**：不要把設定頁做成工程 dashboard，而是做成「狀態先於動作、低風險在上、高風險在下、一般人看得懂、進階術語退到補充文字」的維護介面。目前 Settings tab 與 section placement 已經有明顯錯位：搜尋 tab 只放分類標籤，資料 tab 則塞了維護、統計、備份、安全、危險區。

---

## 第一輪：Codex Prompt Contract 的核心目的

**Alex：**  

Codex prompt 不能寫成「幫我整理 Settings」。這種 prompt 會導致 mega-diff。要寫成「請只完成 X，不准做 Y，驗收跑 Z，最後回報 A/B/C」。

**Kenji：**  

每個 Codex 任務都要有五個硬欄位：

1. 任務目標  
2. 允許修改檔案  
3. 禁止事項  
4. 驗收指令  
5. 回報格式  

沒有這五個欄位，就不該丟給 Codex。

**Sophie：**  

而且驗收要依任務性質分級。Settings 前端文案任務通常只需要：

```bash
cd frontend && npm run build
```

如果碰到測試檔，再跑相關測試。不要每個小任務都要求全 repo 測試，否則回饋週期太重。

**Leo：**  

補一句：prompt 裡要明確寫「不要順手修其他問題」。Codex 很容易看到 About 寫錯 Flask，就順手改一堆 runtime 文檔，然後把事情弄大。

---

## 第二輪：Codex Prompt 固定模板

**Nolan：**  

可以定一個通用模板，後續所有 Prism 任務都套這個。

```markdown
# Codex Task: <TASK-ID> — <短標題>

## 目標
<用 2~4 句說明這次只要完成什麼。>

## 背景
<必要背景。只放與本任務直接相關的 current truth。>

## 允許修改
- <file 1>
- <file 2>

## 禁止事項
- 不改 schema。
- 不新增後端 API。
- 不新增新功能。
- 不重寫無關元件。
- 不做 mega-diff。
- 不順手修本任務外問題。
- 不恢復已隱藏功能，除非本任務明確要求。

## 具體要求
1. ...
2. ...
3. ...

## 驗收
請至少執行：
```

cd frontend && npm run build

```

如有測試異常，請回報：
- 失敗指令
- 失敗原因
- 你是否修改過相關檔案

## 回報格式
完成後請用以下格式回報：

### Changed
- 修改了哪些檔案
- 每個檔案改了什麼

### Verified
- 執行了哪些指令
- 結果是 pass / fail

### Not Changed
- 明確說明沒有改 API / schema / 後端 / 無關功能
```

**Marcus：**  

禁止事項要每次重複，不要只放在總規則。Codex 不會像人一樣記得所有上下文，任務 prompt 本身要自足。

**Iris：**  

背景不要太長。太長會讓 Codex 抓錯重點。只放本任務需要知道的 current truth。

---

## 第三輪：針對 Settings 任務的 Prompt Contract

**Alex：**  

這一批任務建議拆成 5 個 prompt，不要合併。

### Prompt 1：ABOUT-CURRENT-TRUTH-01

```markdown
# Codex Task: ABOUT-CURRENT-TRUTH-01 — 修正 Settings About runtime 文案

## 目標
修正 Settings > About 的 current truth。Prism 現在是 Go primary runtime，不是 Flask backend。這次只改 About 區塊文案，不改 Settings 結構。

## 背景
SettingsPage.tsx 的 About 區目前仍顯示「後端: Flask + SQLite (FTS5)」，但 Prism current truth 是 Go primary runtime / SQLite FTS5。

## 允許修改
- frontend/src/pages/SettingsPage.tsx

## 禁止事項
- 不改 Settings tabs。
- 不改其他 Settings sections。
- 不改 API。
- 不改 Go backend。
- 不改 schema。
- 不新增元件。
- 不恢復 PortConfigSection / UpdateSection。
- 不做 mega-diff。

## 具體要求
1. 移除「後端: Flask + SQLite (FTS5)」。
2. 改成「後端: Go primary runtime / SQLite (FTS5)」。
3. 保留 knowledge.db、static/uploads、docs/attachments 的資料位置說明。
4. 增加一句安全邊界摘要：Prism 預設本機 / trusted LAN 使用，無內建 API Token，不建議直接暴露到公網。

## 驗收
請執行：
```

cd frontend && npm run build

```

## 回報格式
### Changed
### Verified
### Not Changed
```

---

### Prompt 2：SETTINGS-IA-01

```markdown
# Codex Task: SETTINGS-IA-01 — Settings tabs 資訊架構重排

## 目標
重排 Settings tabs 與既有 sections，讓分類標籤、備份還原、維護健康、系統存取各有清楚位置。這次只搬既有元件，不改元件內部功能。

## 背景
目前 Settings 有 appearance / data / search / deploy / about。data 裡塞了維護、統計、備份、安全、危險區；search 實際只放分類與標籤管理。

## 允許修改
- frontend/src/pages/SettingsPage.tsx

## 禁止事項
- 不改 SystemMaintenance 內部。
- 不改 BackupImportSection 內部。
- 不改 DataManager 內部。
- 不改 SecuritySection 內部。
- 不改 ServerDashboardSection 內部。
- 不新增後端 API。
- 不新增 Search Integrity 假 UI。
- 不恢復 PortConfigSection / UpdateSection。
- 不改 schema。
- 不做 mega-diff。

## 具體要求
將 tabs 改為：
- appearance：外觀
- organization：組織
- backup：備份與還原
- maintenance：維護與健康
- system：存取與系統
- about：關於

搬移：
- AppearanceSection → 外觀
- DataManager → 組織
- BackupImportSection → 備份與還原
- SystemMaintenance + SystemStatsSection → 維護與健康
- SecuritySection + ServerDashboardSection → 存取與系統
- DangerZoneSection → 維護與健康最下方

兼容：
- ?tab=search 導向 organization
- ?tab=data 導向 maintenance
- ?tab=deploy 導向 system
- 無效 tab 不 crash，回到 appearance

## 驗收
```

cd frontend && npm run build

```

請手動檢查：
- 每個 tab 可切換
- 舊 query tab 不 crash
- 每個既有 section 都還能出現

## 回報格式
### Changed
### Verified
### Not Changed
```

---

### Prompt 3：MAINT-COPY-01

```markdown
# Codex Task: MAINT-COPY-01 — 維護頁文案與風險語言修正

## 目標
讓 SystemMaintenance 的文案更像使用者維護工具，而不是工程控制台。只改文案，不改功能。

## 背景
SystemMaintenance 目前包含 WAL Checkpoint 與資料一致性檢查。這兩個功能行為保留，但文案需降低工程術語壓力。

## 允許修改
- frontend/src/components/SystemMaintenance.tsx

## 禁止事項
- 不改 api.walCheckpoint。
- 不改 api.checkConsistency。
- 不新增按鈕。
- 不新增 Search Integrity。
- 不新增 FTS rebuild。
- 不新增 VACUUM。
- 不改後端 API。
- 不改 schema。

## 具體要求
1. 「WAL Checkpoint」主標改為「整理資料庫暫存日誌」。
2. 小字補充「進階名稱：WAL Checkpoint」。
3. 說明改為：通常不需要手動執行，備份前或疑難排解時使用。
4. 「資料一致性檢查」補充：此操作只檢查，不會修改資料。
5. health 文案：
   - healthy → 正常
   - warning → 需要注意
   - critical → 需要處理
6. 「未使用標籤」不要使用警告語氣。

## 驗收
```

cd frontend && npm run build

```

## 回報格式
### Changed
### Verified
### Not Changed
```

---

### Prompt 4：BACKUP-UX-02

```markdown
# Codex Task: BACKUP-UX-02 — 備份、匯出、還原區塊分離

## 目標
重整 BackupImportSection 的區塊與文案，清楚區分「匯出副本」「匯入資料」「Prism 內建還原點」。不改 API 行為。

## 背景
目前 BackupImportSection 同時放 JSON/DB/Markdown 匯出、JSON 匯入、DB restore。需要降低使用者誤解：下載 .db 不等於建立可直接還原的內建還原點。

## 允許修改
- frontend/src/components/settings/BackupImportSection.tsx

## 禁止事項
- 不改 api.restoreBackup。
- 不改 api.waitForHealthy。
- 不改 api.exportJSON / exportDB / exportMarkdown。
- 不改備份列表載入邏輯。
- 不新增本機自動備份排程。
- 不新增 cloud sync。
- 不新增 Search Integrity check。
- 不改後端 API。
- 不改 schema。

## 具體要求
分成三個區塊：

1. 匯出副本
- JSON
- Markdown zip
- SQLite .db
- 說明：這些會下載到你的電腦，Prism 不會自動保留在還原清單。

2. 匯入資料
- JSON 匯入
- 說明：會新增資料，依模式略過或建立重複筆記。

3. Prism 內建還原點
- 顯示 server-side backup list。
- 說明：只有這裡列出的還原點可以直接用來還原資料庫。
- 還原前會自動保存目前資料庫為 safety copy。
- 還原會重新啟動 Prism 程序，不是重開電腦。

Restore modal：
- 明確列出會覆蓋目前 DB。
- 明確列出還原前會建立 safety copy。
- 明確列出 Prism 會重新啟動。
- 明確列出不會重開電腦。

## 驗收
```

cd frontend && npm run build

```

請確認 restore flow 行為不變。

## 回報格式
### Changed
### Verified
### Not Changed
```

---

### Prompt 5：MAINT-OVERVIEW-01

```markdown
# Codex Task: MAINT-OVERVIEW-01 — 維護與健康狀態總覽

## 目標
在 SystemMaintenance 裡加入「先看狀態，再執行動作」的視覺結構。只整合既有 WAL 與資料一致性檢查，不新增後端 API。

## 前提
請確認 SETTINGS-IA-01 與 MAINT-COPY-01 已完成。

## 允許修改
- frontend/src/components/SystemMaintenance.tsx

可選：
- 若真的能明顯降低重複 JSX，可新增一個小型 presentational component，但不得新增大型架構。

## 禁止事項
- 不新增 Search Integrity。
- 不新增 FTS rebuild。
- 不新增 VACUUM。
- 不新增後端 API。
- 不自動跑檢查。
- 不自動修復。
- 不改 schema。
- 不做 mega-diff。

## 具體要求
1. 頂部加入「維護與健康」說明卡。
2. 顯示兩張狀態卡：
   - 資料一致性：未檢查 / 正常 / 需要注意 / 需要處理
   - 資料庫暫存日誌：未整理 / 已整理
3. 頁面初始不自動呼叫 maintenance API。
4. 使用者按「檢查」後才更新資料一致性狀態。
5. 使用者按「整理」後才更新 WAL 狀態。
6. 維護動作放在狀態卡下方，不要一進頁面先看到一排危險按鈕。

## 驗收
```

cd frontend && npm run build

```

請確認：
- 初始不自動呼叫 WAL 或 consistency API。
- 兩個原有按鈕仍可使用。
- 行為與原本一致，只是資訊層級改善。

## 回報格式
### Changed
### Verified
### Not Changed
```

---

## 第四輪：Settings Visual Layout 規則

**Hana：**  

視覺規則要簡單，不要做花。Settings 是工具頁，不是 landing page。

建議規則：

1. **每個 tab 首屏先說明用途**  
    
    例如「這裡管理備份、匯入與資料庫還原」。
    
2. **狀態卡在上，操作卡在下**  
    
    使用者先知道狀態，再決定要不要按。
    
3. **危險操作固定在最底部**  
    
    不要跟一般維護混在一起。
    
4. **同一張卡只做一種風險等級**  
    
    不要在同一張卡裡同時放「檢查」與「刪除」。
    
5. **按鈕文案用動詞 + 對象**  
    
    例如「檢查資料一致性」「整理暫存日誌」「下載 JSON」「還原資料庫」。
    
6. **工程術語放副標，不放主標**  
    
    主標：整理資料庫暫存日誌  
    
    副標：進階名稱：WAL Checkpoint
    

**Marcus：**  

色彩規則也要限制：

- 正常：中性或 success
- 需要注意：warning
- 需要處理：danger
- 危險操作：danger button，不要只是 warning
- 一般下載 / 匯出：secondary
- restore：warning 或 primary + warning modal，不要用 danger，因為它有 safety copy，但仍要確認

**Leo：**  

不要整頁到處紅色。紅色太多會讓使用者麻痺。只有真的可能毀資料的操作才紅。

---

## 第五輪：Settings Layout 具體骨架

**Iris：**  

每個 tab 可以採同一種骨架：

```
[Tab Intro Card]
  這裡做什麼
  什麼情況下需要用

[Status / Summary Cards]
  只顯示狀態，不直接做破壞性動作

[Primary Tasks]
  常用操作

[Advanced Maintenance]
  進階操作，預設文案保守

[Danger Zone]
  最底部，強警示
```

**Kenji：**  

第一階段不用做 layout framework。直接在各 section 現有 JSX 裡整理即可。不要新增 `SettingsLayoutManager` 這種東西。

**Sophie：**  

測試重點是「看得到」「按鈕還能按」「不自動觸發 API」。不是像素完美。

---

## 第六輪：最終收斂

正式建議：

**先丟 Codex Prompt Contract，不先做視覺討論稿。**  

因為現在最容易失控的是 Codex 實作，而不是設計想法不足。

執行順序：

1. `ABOUT-CURRENT-TRUTH-01`
2. `SETTINGS-IA-01`
3. `MAINT-COPY-01`
4. `BACKUP-UX-02`
5. `MAINT-OVERVIEW-01`

每次只丟一個 prompt。每次完成後要求 Codex 回報：

```markdown
### Changed
- ...

### Verified
- ...

### Not Changed
- No API changes.
- No schema changes.
- No backend changes.
- No new features outside task scope.
```

---

## 最終結論

Codex Prompt Contract 的核心句是：

**「只完成這個任務，不順手擴功能；只改允許檔案；所有維護與設定改動都必須維持現有 API 行為。」**

Settings Visual Layout 的核心句是：

**「狀態先於動作；檢查與修復分開；危險操作到底；工程術語退到補充文字。」**

---

## 下一輪推薦討論方向

下一輪建議開：

**Actual Codex Task Pack 會**

主軸：把上述 5 個 prompt 整理成一份可以直接複製貼上的任務包，包含順序、每次任務完成後要你檢查什麼、如果 Codex 改太多要怎麼要求 rollback。

備選方向：

**Search Integrity API Spec 會**

主軸：正式設計 `GET /api/system/search-integrity` 與 `POST /api/system/search-integrity/rebuild-fts`，把它接到剛整理好的「維護與健康」tab。

我建議下一輪開 **Search Integrity API Spec 會**。Settings 的資訊架構與 prompt contract 已經夠落地了；下一個真正會碰後端的關鍵，就是搜尋完整性 API。
# ChatGPT 對話逐字稿 — Prism / Cerberus 研討 2026-06-16 Part 4

## 使用者

再來幾輪研討會 主軸是

Actual Codex Task Pack 會/Search Integrity API Spec 會

延伸討論直到收斂後，再繼續推薦討論方向 

## 助理

結論：這輪收斂成兩件事。

第一，**Actual Codex Task Pack 不是一大包一次丟給 Codex，而是一份「任務索引 + 單任務 prompt 模板」**。每次只貼一個任務，做完驗收，再貼下一個。否則 Codex 很容易把 Settings、Backup、Search Integrity、文案、API 一次混改。

第二，**Search Integrity API 可以正式進規格，但實作要分兩段：先 read-only 診斷，再手動 rebuild FTS。** 不要一開始就自動修復、不要接 restore 後自動 rebuild、不要讓 Agent 自動觸發維護動作。

目前有幾個 repo 事實要守住：Settings 現在資料、搜尋、部署 tab 的內容分配已經錯位；維護頁目前只有 WAL Checkpoint 與資料一致性檢查；Go 端已有 `check-consistency`，會檢查 orphan note-tags、unused tags、null category、foreign_keys 與 health；現有 vacuum 會順手 rebuild FTS，但這不應該等同於新的 Search Integrity repair；文字附件搜尋有 200 檔、5MB、250ms 的 scan cap。

---

## 第一輪：Actual Codex Task Pack 會

**Alex：**  

Task Pack 的定位不是「叫 Codex 幫我們想」。我們已經想完。Codex 只負責按順序施工。

**Kenji：**  

任務包要分兩層：

一層是 **索引**：列出順序、依賴、每個任務是否允許改後端。  

另一層是 **單任務 prompt**：一次只貼一個，不要貼全包讓 Codex 自己挑。

**Sophie：**  

每個 task 都要有固定回報格式：Changed、Verified、Not Changed。尤其 Not Changed 很重要，要逼 Codex 明確說沒有改 API、schema、後端或無關功能。

**Leo：**  

還要有 rollback 指令。如果 Codex 改太多，回覆應該很簡單：「撤回本任務外所有修改，只保留允許檔案」。

---

## 第二輪：Codex Task Pack 最終順序

**Alex：**  

我把任務分成兩批。

第一批是 **Settings 前端整理**，不碰後端：

1. `ABOUT-CURRENT-TRUTH-01`
2. `SETTINGS-IA-01`
3. `MAINT-COPY-01`
4. `BACKUP-UX-02`
5. `MAINT-OVERVIEW-01`

第二批是 **Search Integrity 後端與接線**：

1. `SEARCH-INTEGRITY-API-01`
2. `SEARCH-INTEGRITY-REBUILD-01`
3. `SEARCH-INTEGRITY-UI-01`

**Kenji：**  

這順序合理。Search Integrity API 不要在 Settings IA 前做，否則 UI 還沒位置。先整理 Settings，再接 API。

**Nolan：**  

Agent Search Contract 可以暫時放 docs-only，排在 Search Integrity API 前或後都可以。但如果現在主線是 Settings / maintenance，先不插 Agent，避免分心。

**Leo：**  

對，別又開三條戰線。

---

## 第三輪：Search Integrity API Spec 會

**Maria：**  

Search Integrity 的目的不是取代一般資料一致性檢查，而是專門回答：

1. 搜尋索引是否存在？
2. Notes 與 Notes_FTS 是否明顯不一致？
3. 附件 metadata 是否指向不存在檔案？
4. 文字附件搜尋是否可能被 scan cap 截斷？
5. 如果搜尋怪怪的，使用者下一步該做什麼？

**Kenji：**  

API 最小設計：

`GET /api/system/search-integrity`

Read-only，只診斷，不修復。

`POST /api/system/search-integrity/rebuild-fts`

手動修復，只 rebuild FTS，不 VACUUM，不改 notes，不刪附件。

**Sophie：**  

這兩個 endpoint 都屬於 maintenance surface。要跟現有 `wal-checkpoint`、`check-consistency` 放同一層風險語言，不要給一般 Agent 自動呼叫。

**Marcus：**  

Prism 沒有內建 API Token / Bearer Token，API 文件已經明確說不建議公網暴露；server/system 類操作尤其要維持受信邊界。

---

## 第四輪：Search Integrity API 回傳格式

**Maria：**  

我建議 `GET /api/system/search-integrity` 回傳這種結構：

```json
{
  "status": "success",
  "data": {
    "health": "ok",
    "fts": {
      "exists": true,
      "notes_count": 120,
      "fts_count": 120,
      "missing_fts_rows": 0,
      "orphan_fts_rows": 0,
      "needs_rebuild": false
    },
    "attachments": {
      "total": 12,
      "missing_files": 0,
      "unsafe_paths": 0,
      "text_scannable": 5,
      "text_scan_bytes": 84210,
      "oversized_text_files": 0
    },
    "scan_limits": {
      "max_files": 200,
      "max_bytes": 5242880,
      "max_duration_ms": 250
    },
    "warnings": []
  }
}
```

**Kenji：**  

不要回本機絕對路徑。missing files 可以回 id、title、basename 或 safe relative path，但不回 `C:\Users\...` 或 `/home/...`。

**Sophie：**  

health 分級：

- `ok`：FTS 存在、Notes/FTS 無明顯 mismatch、附件缺失為 0。
- `warning`：有 missing attachments、scan 可能超 cap、少量可修復問題。
- `critical`：FTS 不存在、FTS count 明顯錯、foreign_keys 關閉、查詢失敗。

**Leo：**  

不要把 unused tags 算進 search integrity。unused tag 不代表搜尋壞掉。

---

## 第五輪：FTS Rebuild Spec

**Kenji：**  

`POST /api/system/search-integrity/rebuild-fts` 做一件事：

```sql
INSERT INTO Notes_FTS(Notes_FTS) VALUES('rebuild')
```

不要 VACUUM。現在 vacuum endpoint 已經會 rebuild FTS + VACUUM，但新的 repair action 要更精準。

**Maria：**  

回傳前後資料：

```json
{
  "status": "success",
  "data": {
    "before": {
      "notes_count": 120,
      "fts_count": 117,
      "missing_fts_rows": 3
    },
    "after": {
      "notes_count": 120,
      "fts_count": 120,
      "missing_fts_rows": 0
    },
    "message": "搜尋索引已重建"
  }
}
```

**Sophie：**  

測試要包含：

- 正常 FTS rebuild。
- FTS mismatch 後 rebuild 修復。
- Notes 不變。
- Attachments 不變。
- 沒有執行 VACUUM。
- 沒有刪除資料。

**Marcus：**  

POST repair 需要 CSRF 保護。既有 CSRF gate 對 POST / PUT / DELETE 會檢查 Origin / Referer，同源才放行；curl / MCP 這類無 Origin / Referer 的請求會放行，這是既有設計。  

所以文件要說：這是維護操作，不是一般 Agent 自動操作。

---

## 第六輪：Actual Codex Task Pack 可貼版本

下面這份是可以作為「任務包索引」存進 TODO 或先貼給 Codex 做導覽用；但實際執行仍然一次貼一個任務。

# Prism Codex Task Pack — Settings Maintenance + Search Integrity

## Execution Rule

Run exactly one task at a time. Do not combine tasks. Do not perform opportunistic cleanup outside the current task. If a needed change is outside the allowed files or scope, stop and report it instead of modifying it.

Every task must report:

### Changed

- Files changed
- Summary of changes

### Verified

- Commands run
- Pass / fail result

### Not Changed

- Confirm no API changes unless explicitly allowed
- Confirm no schema changes unless explicitly allowed
- Confirm no backend changes unless explicitly allowed
- Confirm no unrelated feature work

---

## Task Order

### 1. ABOUT-CURRENT-TRUTH-01

Goal: fix Settings > About runtime wording.

Allowed files:

- frontend/src/pages/SettingsPage.tsx

Requirements:

- Replace Flask backend wording with Go primary runtime / SQLite FTS5.
- Keep knowledge.db, static/uploads, docs/attachments explanation.
- Add concise security boundary note: local / trusted LAN use, no built-in API token, do not expose directly to public internet.

Forbidden:

- Do not change Settings tabs.
- Do not change API.
- Do not change backend.
- Do not change schema.
- Do not add components.

Verify:

```bash
cd frontend && npm run build
```

---

### 2. SETTINGS-IA-01

Goal: reorganize Settings tabs and section placement using existing components.

Allowed files:

- frontend/src/pages/SettingsPage.tsx

New tabs:

- appearance: 外觀
- organization: 組織
- backup: 備份與還原
- maintenance: 維護與健康
- system: 存取與系統
- about: 關於

Move:

- AppearanceSection → 外觀
- DataManager → 組織
- BackupImportSection → 備份與還原
- SystemMaintenance + SystemStatsSection → 維護與健康
- SecuritySection + ServerDashboardSection → 存取與系統
- DangerZoneSection → 維護與健康 bottom

Compatibility:

- ?tab=search → organization
- ?tab=data → maintenance
- ?tab=deploy → system
- invalid tab → appearance

Forbidden:

- Do not change internals of existing components.
- Do not add backend API.
- Do not add Search Integrity placeholder UI.
- Do not restore PortConfigSection or UpdateSection.
- Do not change schema.

Verify:

```bash
cd frontend && npm run build
```

---

### 3. MAINT-COPY-01

Goal: improve SystemMaintenance wording without changing behavior.

Allowed files:

- frontend/src/components/SystemMaintenance.tsx

Requirements:

- Rename visible WAL title to 整理資料庫暫存日誌.
- Keep advanced name as WAL Checkpoint in helper text.
- Explain it is usually unnecessary, useful before backup or troubleshooting.
- Clarify 資料一致性檢查 only checks and does not modify data.
- Health wording:
    - healthy → 正常
    - warning → 需要注意
    - critical → 需要處理
- Do not treat unused tags as an error.

Forbidden:

- Do not add buttons.
- Do not change api.walCheckpoint.
- Do not change api.checkConsistency.
- Do not add Search Integrity.
- Do not add FTS rebuild.
- Do not change backend or schema.

Verify:

```bash
cd frontend && npm run build
```

---

### 4. BACKUP-UX-02

Goal: separate export, import, and restore concepts in BackupImportSection.

Allowed files:

- frontend/src/components/settings/BackupImportSection.tsx

Sections:

1. 匯出副本
    - JSON
    - Markdown zip
    - SQLite .db
    - Explain downloaded files are not automatically retained in Prism restore list.
2. 匯入資料
    - JSON import
    - Explain import adds data, with skip or duplicate behavior.
3. Prism 內建還原點
    - Show server-side backup list.
    - Explain only listed restore points can be restored directly.
    - Explain restore overwrites current database.
    - Explain restore creates a safety copy first.
    - Explain Prism restarts itself; it does not reboot the computer.

Forbidden:

- Do not change restore API.
- Do not change waitForHealthy.
- Do not change export/import API behavior.
- Do not add local automatic backup scheduling.
- Do not add cloud sync.
- Do not add Search Integrity check.

Verify:

```bash
cd frontend && npm run build
```

---

### 5. MAINT-OVERVIEW-01

Goal: add a “status first, actions second” structure to SystemMaintenance using existing functions only.

Allowed files:

- frontend/src/components/SystemMaintenance.tsx

Requirements:

- Add top explanation card for 維護與健康.
- Add two status cards:
    - 資料一致性: 未檢查 / 正常 / 需要注意 / 需要處理
    - 資料庫暫存日誌: 未整理 / 已整理
- Do not auto-run checks on page load.
- Update status only after user clicks existing actions.
- Keep original functions working.

Forbidden:

- Do not add Search Integrity.
- Do not add FTS rebuild.
- Do not add VACUUM.
- Do not add backend API.
- Do not auto-repair anything.
- Do not change schema.

Verify:

```bash
cd frontend && npm run build
```

---

### 6. SEARCH-INTEGRITY-API-01

Goal: add read-only search integrity diagnostics.

Allowed files:

- go-shadow/main.go
- frontend/src/services/api.ts only if needed for type/client preparation
- tests related to Go search/system integrity

Endpoint:

- GET /api/system/search-integrity

Behavior:

- Read-only.
- Must not modify DB.
- Must not rebuild FTS.
- Must not delete files.
- Must not expose absolute local paths.

Response data:

- health: ok | warning | critical
- fts:
    - exists
    - notes_count
    - fts_count
    - missing_fts_rows
    - orphan_fts_rows
    - needs_rebuild
- attachments:
    - total
    - missing_files
    - unsafe_paths
    - text_scannable
    - text_scan_bytes
    - oversized_text_files
- scan_limits:
    - max_files
    - max_bytes
    - max_duration_ms
- warnings

Forbidden:

- Do not add schema.
- Do not add SearchHistory.
- Do not rebuild FTS.
- Do not VACUUM.
- Do not change /api/notes.
- Do not add semantic search.

Verify:

```bash
cd go-shadow && go test ./...
```

---

### 7. SEARCH-INTEGRITY-REBUILD-01

Goal: add manual FTS rebuild repair action.

Allowed files:

- go-shadow/main.go
- tests related to Go search/system integrity

Endpoint:

- POST /api/system/search-integrity/rebuild-fts

Behavior:

- Execute only FTS rebuild:
    
    INSERT INTO Notes_FTS(Notes_FTS) VALUES('rebuild')
    
- Return before/after counts.
- Do not VACUUM.
- Do not change Notes.
- Do not change attachments.
- Do not delete files.

Forbidden:

- Do not auto-trigger after restore.
- Do not add schema.
- Do not add ranking.
- Do not add semantic search.
- Do not change /api/notes.

Verify:

```bash
cd go-shadow && go test ./...
```

---

### 8. SEARCH-INTEGRITY-UI-01

Goal: wire Search Integrity diagnostics into Settings > 維護與健康.

Prerequisites:

- SETTINGS-IA-01
- MAINT-OVERVIEW-01
- SEARCH-INTEGRITY-API-01
- SEARCH-INTEGRITY-REBUILD-01

Allowed files:

- frontend/src/components/SystemMaintenance.tsx
- frontend/src/services/api.ts

Requirements:

- Add search integrity status card.
- Initial state: 未檢查.
- User clicks 檢查搜尋狀態 to call GET /api/system/search-integrity.
- If health warning/critical and fts.needs_rebuild is true, show 重建搜尋索引 button.
- Rebuild button calls POST /api/system/search-integrity/rebuild-fts.
- Do not auto-run diagnostics on page load.
- Do not auto-rebuild.

Forbidden:

- Do not add new backend API.
- Do not add ranking.
- Do not add semantic search.
- Do not alter /api/notes.
- Do not add schema.

Verify:

```bash
cd frontend && npm run build
```

---

## 第七輪：Search Integrity API 實作細節收斂

**Kenji：**  

Codex 實作 `SEARCH-INTEGRITY-API-01` 時，後端邏輯建議這樣切，不需要新檔案：

- `handleSearchIntegrity`
- `searchIntegrityReport`
- `ftsIntegrityReport`
- `attachmentIntegrityReport`
- 小型 helper：`tableExists`, `ftsRowCounts`, `safeAttachmentDisplayPath`

不要拆出一堆 service / manager。

**Sophie：**  

測試應該覆蓋：

1. fresh DB：health ok。
2. Notes_FTS 缺 row：warning / needs_rebuild true。
3. Notes_FTS 不存在：critical。
4. attachment metadata 指向 missing file：warning。
5. response 不含絕對路徑。
6. GET 不改 DB。

**Maria：**  

Attachment 檢查只檢查 metadata 和檔案是否存在，不要讀完整內容。text scan byte count 可以用檔案大小統計，不要在 integrity check 裡真的掃內容。

**Leo：**  

對，叫 Search Integrity 不是叫 Search Exhaustive Audit。不要把檢查做成慢到使用者不想按。

---

## 第八輪：最終收斂

**Alex：**  

最後決策：

1. Task Pack 可以正式採用。  
2. Search Integrity API 進入可施工規格。  
3. 實作順序仍然是前端 Settings 基礎整理先行，後端 Search Integrity 隨後。  
4. UI 接線最後做，避免先做假 UI。

**Kenji：**  

如果你要丟 Codex，我建議先從 `ABOUT-CURRENT-TRUTH-01` 開始，這是低風險檢查 Codex 是否聽話的任務。

**Sophie：**  

如果 Codex 第一個任務就改了無關檔案，先不要繼續，立刻要求 rollback。

**Leo：**  

把 Codex 當實習生，不是當架構師。你已經有規格了，別讓它重新設計。

---

## 下一輪推薦討論方向

下一輪建議開：

**Codex Execution Review Checklist 會**

主軸：每個任務做完後，你要怎麼審查 Codex 的 diff、哪些變更要直接退回、哪些測試失敗可以接受、什麼情況下允許它補測試。

備選方向：

**Search Integrity Test Matrix 會**

主軸：專門設計 `GET /api/system/search-integrity` 與 `POST /api/system/search-integrity/rebuild-fts` 的測試資料與邊界案例。

我建議先開 **Search Integrity Test Matrix 會**。因為 Search Integrity 是第一個會碰後端的新功能，測試矩陣先定好，Codex 比較不容易做出「看起來可用但沒有保護邊界」的實作。
# ChatGPT 對話逐字稿 — Prism / Cerberus 研討 2026-06-16 Part 5

## 使用者

再來幾輪研討會 主軸是

Codex Execution Review Checklist /  Search Integrity Test Matrix

延伸討論直到收斂後，再繼續推薦討論方向 

## 助理

結論：這輪收斂成兩份可直接使用的審查材料。

第一份是 **Codex Execution Review Checklist**：每次 Codex 做完一個任務，你用它來判斷「能不能收、要不要退、要不要要求縮 diff」。

第二份是 **Search Integrity Test Matrix**：給 `GET /api/system/search-integrity` 與 `POST /api/system/search-integrity/rebuild-fts` 用的測試矩陣，避免 Codex 只做出「看起來能跑」但沒有保護邊界的功能。

目前依據是：Settings 維護區現有 `SystemMaintenance` 只有 WAL Checkpoint 與資料一致性檢查；後端已有一般一致性檢查，會回傳 orphan note-tags、unused tags、null category、foreign_keys 與 health；現有 vacuum 會 rebuild FTS，但新的 Search Integrity repair 不應直接等同 vacuum；附件文字搜尋已有 scan cap：200 files、5MB、250ms。

---

## 第一輪：Codex Execution Review Checklist 要檢查什麼

**Alex：**  

Codex 做完任務後，不能只看「build pass」。要看三件事：

1. 有沒有只做任務要求。
2. 有沒有改到禁止區。
3. 有沒有留下可驗證證據。

**Kenji：**  

審 diff 的順序要固定：

1. 先看 changed files。
2. 再看有沒有改 API / schema / backend。
3. 再看是否超出允許檔案。
4. 再看功能是否真的符合任務。
5. 最後才看文案、命名、細節。

如果第一步 changed files 就超出範圍，先不要往下看，直接要求縮 diff。

**Sophie：**  

驗收不能只接受「我跑了 build」。要看 Codex 的 output 是否包含：

- 執行指令；
- pass/fail 結果；
- 如果 fail，失敗原因；
- 是否有未執行測試的理由。

**Leo：**  

最重要的是退貨標準。沒有退貨標準，Codex 很容易「多做一點」。多做一點就是風險。

---

## 第二輪：哪些情況要直接退回

**Marcus：**  

我建議列成硬紅線。只要踩到，直接 rollback 或要求重做：

| 紅線 | 處理 |
| --- | --- |
| 改 schema，但任務沒授權 | 退回 |
| 新增後端 API，但任務沒授權 | 退回 |
| 改 Go runtime，但任務是前端文案 | 退回 |
| 恢復隱藏的 PortConfig / UpdateSection | 退回 |
| 新增自動修復、自動備份、自動掃描 | 退回 |
| Search Integrity 自動 rebuild FTS | 退回 |
| restore 後自動 VACUUM / rebuild / delete | 退回 |
| 回傳本機絕對路徑 | 退回 |
| 把 unused tag 當 critical error | 退回 |
| 引入 AI / embedding / semantic search | 退回 |
| 大量格式化無關檔案 | 退回 |
| 任務外順手重構 | 退回 |

**Kenji：**  

還有一條：如果 Codex 新增 helper / component / abstraction，但只是為了搬文案，那也要退。Prism 的 anti-bloat 原則已經明確要求最小變更，避免未被需求證明的抽象化與跨檔擴散。

**Leo：**  

「看起來更乾淨」不是理由。只要不是任務需要，就是多餘。

---

## 第三輪：哪些可以接受

**Sophie：**  

不是所有額外修改都要退。有些是可接受的：

| 類型 | 可接受條件 |
| --- | --- |
| TypeScript 型別小修 | 只為了本任務 build pass |
| 小型文案調整 | 在任務區塊內，語意一致 |
| 小型 presentational component | 任務允許，且明顯降低重複 JSX |
| 測試檔補充 | 只覆蓋本任務，不改測試策略 |
| alias 處理 | 例如 `?tab=data → maintenance`，任務有要求 |
| import 移除 | 因搬 section 後 unused import，合理 |

**Alex：**  

接受標準是：**必要、局部、可解釋、可測。**

**Leo：**  

如果 Codex 說「我順手優化了整個 Settings 架構」，不用看，退。

---

## 第四輪：Search Integrity Test Matrix 的設計目標

**Maria：**  

Search Integrity 的測試要防兩種錯：

第一，假健康。明明 FTS 或附件壞了，endpoint 還回 ok。  

第二，假修復。rebuild endpoint 看似成功，但其實改了 notes、跑了 VACUUM、刪了檔案，或沒有真的修 FTS。

**Kenji：**  

測試矩陣要分兩組：

1. `GET /api/system/search-integrity`
2. `POST /api/system/search-integrity/rebuild-fts`

不要一個測試同時驗證診斷和修復。

**Sophie：**  

而且必須有 mutation guard。`GET` 是 read-only，要證明呼叫前後 DB row counts、mtime-sensitive 行為或資料摘要沒變。`POST rebuild-fts` 只能改 FTS，不能改 Notes、Tags、Attachments、檔案系統。

---

## 第五輪：GET /api/system/search-integrity 測試矩陣

建議測試矩陣如下。

| Case | Fixture | 預期 |
| --- | --- | --- |
| SI-GET-01 fresh ok | fresh DB，有 welcome note，FTS 正常 | health=ok |
| SI-GET-02 FTS table missing | 移除或模擬 Notes_FTS 不存在 | health=critical，fts.exists=false |
| SI-GET-03 FTS missing rows | Notes 有資料，但 Notes_FTS 少 row | health=warning/critical，needs_rebuild=true |
| SI-GET-04 FTS orphan rows | Notes_FTS 有不存在 note rowid | health=warning，orphan_fts_rows > 0 |
| SI-GET-05 FK disabled | PRAGMA foreign_keys 不符合預期 | health=critical 或 warning |
| SI-GET-06 attachment missing file | Note_Attachments 指向不存在檔案 | health=warning，missing_files > 0 |
| SI-GET-07 unsafe attachment path | file_path 嘗試 `../` 或絕對路徑 | health=warning/critical，unsafe_paths > 0 |
| SI-GET-08 text attachment stats | 有 .md/.txt attachment | text_scannable 與 text_scan_bytes 正確 |
| SI-GET-09 oversized text files | 單檔或總量超過 scan cap | warning 包含 scan cap 相關提示 |
| SI-GET-10 no absolute path leak | missing/unsafe attachment response | 不含本機絕對路徑 |
| SI-GET-11 read-only guard | 呼叫前後 Notes/Tags/Attachments count 不變 | 無資料 mutation |
| SI-GET-12 scan limits exposed | response 有 max_files/max_bytes/max_duration_ms | 等於目前 constants |

**Maria：**  

這裡要注意：`unused_tags` 不屬於 Search Integrity critical。一般 consistency check 現在會回 unused tags，但 Search Integrity 不應把 unused tags 當搜尋壞掉。

**Kenji：**  

`FTS table missing` 如果不好真的 drop virtual table，可以用 temp DB fixture 建壞狀態；或者先測 table existence helper。不要為了測試把 production migration 改壞。

**Sophie：**  

`unsafe attachment path` 只需要驗證診斷，不要自動修復，也不要刪 row。

---

## 第六輪：POST rebuild-fts 測試矩陣

| Case | Fixture | 預期 |
| --- | --- | --- |
| SI-REBUILD-01 normal rebuild | 正常 DB | success，before/after counts 合理 |
| SI-REBUILD-02 repair missing rows | Notes_FTS 少 row | after missing_fts_rows=0 |
| SI-REBUILD-03 repair orphan rows | Notes_FTS 多 orphan row | after orphan_fts_rows=0 |
| SI-REBUILD-04 Notes unchanged | rebuild 前後 Notes hash/count 不變 | 不改筆記 |
| SI-REBUILD-05 Attachments unchanged | rebuild 前後 Note_Attachments count 不變 | 不改附件 metadata |
| SI-REBUILD-06 Files untouched | attachments/uploads 檔案不被刪改 | 不碰檔案系統 |
| SI-REBUILD-07 no VACUUM | 不呼叫 VACUUM、不做 DB 壓縮語意 | 只 rebuild FTS |
| SI-REBUILD-08 failure if FTS missing | Notes_FTS 不存在 | 回 error 或 critical，不假裝成功 |
| SI-REBUILD-09 method guard | GET rebuild endpoint 不允許 | 405 |
| SI-REBUILD-10 CSRF / method boundary | POST 走既有 CSRF/system gate | 不繞過現有 middleware |

**Kenji：**  

`no VACUUM` 不一定容易直接檢測，但可以至少保證程式碼沒有呼叫 `VACUUM`，測試可用 DB file size 不作為硬條件，避免 flaky。

**Sophie：**  

更穩的是 review checklist 寫：`rebuild-fts handler must not call VACUUM`，diff review 人工確認。自動測試只確認資料不變。

**Leo：**  

這裡不要追求 100% 自動證明。人審 diff 就是必要的一環。

---

## 第七輪：Codex Execution Review Checklist 最終版

這份可以直接存成你自己的審查清單。

```markdown
# Codex Execution Review Checklist — Prism

## 0. 任務識別
- [ ] Codex 是否只執行本次指定 TASK-ID？
- [ ] 是否引用了正確任務目標？
- [ ] 是否回報 Changed / Verified / Not Changed？

## 1. Changed Files 檢查
- [ ] 修改檔案是否都在「允許修改」清單內？
- [ ] 是否出現未授權的後端檔案？
- [ ] 是否出現未授權的 schema / migration / docs 大改？
- [ ] 是否有大量格式化無關檔案？
- [ ] 是否新增不必要 component / manager / service / abstraction？

若以上任一為是，先要求縮 diff 或 rollback。

## 2. Scope 檢查
- [ ] 是否只完成任務要求？
- [ ] 是否順手新增功能？
- [ ] 是否恢復已隱藏功能？
- [ ] 是否改變 API 行為？
- [ ] 是否改變資料庫結構？
- [ ] 是否改變安全邊界？
- [ ] 是否引入 AI / embedding / semantic search？

## 3. UX / 文案檢查
- [ ] 主標是否使用使用者語言，而非工程術語？
- [ ] 工程術語是否退到副標或進階說明？
- [ ] 是否清楚區分「檢查 / 維護 / 還原 / 危險」？
- [ ] 是否避免把 warning 說成 critical？
- [ ] 是否避免讓使用者誤解 DB download 是內建還原點？
- [ ] Restore 是否清楚說明會覆蓋目前 DB、會重啟 Prism、不是重開電腦？

## 4. Safety 檢查
- [ ] 是否沒有自動修復？
- [ ] 是否沒有自動刪除？
- [ ] 是否沒有自動備份排程？
- [ ] 是否沒有公網暴露暗示？
- [ ] 是否沒有回傳本機絕對路徑？
- [ ] 危險操作是否仍有確認流程？

## 5. Search Integrity 專用檢查
- [ ] GET endpoint 是否 read-only？
- [ ] GET 是否不 rebuild FTS？
- [ ] GET 是否不掃描無界附件內容？
- [ ] GET 是否回傳 scan limits？
- [ ] GET 是否不把 unused tags 當 critical？
- [ ] POST rebuild 是否只 rebuild FTS？
- [ ] POST rebuild 是否不 VACUUM？
- [ ] POST rebuild 是否不改 Notes / Tags / Attachments？
- [ ] POST rebuild 是否不碰 uploads / attachments 檔案？
- [ ] Search Integrity response 是否不含本機絕對路徑？

## 6. Verification 檢查
- [ ] Codex 是否執行指定驗收指令？
- [ ] build/test 是否 pass？
- [ ] 若 fail，是否清楚回報失敗原因？
- [ ] 若未跑測試，理由是否可接受？
- [ ] 是否需要你手動補跑測試？

## 7. 接受 / 退回決策
接受條件：
- [ ] 修改範圍符合任務
- [ ] 驗收通過
- [ ] 沒有安全邊界變更
- [ ] 沒有未授權功能
- [ ] 沒有 current truth 汙染

退回條件：
- [ ] 任務外大改
- [ ] API / schema 未授權變更
- [ ] 自動修復或自動刪除
- [ ] 絕對路徑外洩
- [ ] 測試失敗且原因不清
- [ ] 文案誤導使用者
```

---

## 第八輪：Search Integrity Test Matrix 最終版

這份可以放進 docs 或直接給 Codex 寫測試。

```markdown
# Search Integrity Test Matrix

## Target endpoints

- GET /api/system/search-integrity
- POST /api/system/search-integrity/rebuild-fts

## GET /api/system/search-integrity

### SI-GET-01 Fresh DB OK
Fixture:
- Fresh Prism DB
- Notes_FTS exists
- Notes and Notes_FTS aligned

Expected:
- status=success
- data.health=ok
- fts.exists=true
- fts.needs_rebuild=false
- warnings empty or non-critical

### SI-GET-02 FTS Missing
Fixture:
- DB where Notes_FTS is missing or inaccessible

Expected:
- health=critical
- fts.exists=false
- fts.needs_rebuild=true or repair unavailable warning
- no panic

### SI-GET-03 FTS Missing Rows
Fixture:
- Notes has rows not represented in Notes_FTS

Expected:
- missing_fts_rows > 0
- needs_rebuild=true
- health=warning or critical

### SI-GET-04 FTS Orphan Rows
Fixture:
- Notes_FTS has rowid not present in Notes

Expected:
- orphan_fts_rows > 0
- needs_rebuild=true
- health=warning

### SI-GET-05 Foreign Keys Disabled / Invalid
Fixture:
- PRAGMA foreign_keys not enabled or cannot be verified

Expected:
- warning or critical
- clear warning message

### SI-GET-06 Missing Attachment File
Fixture:
- Note_Attachments row points to missing file

Expected:
- attachments.missing_files > 0
- health=warning
- response does not expose absolute path

### SI-GET-07 Unsafe Attachment Path
Fixture:
- Note_Attachments file_path contains absolute path or traversal-like path

Expected:
- attachments.unsafe_paths > 0
- health=warning or critical
- response does not expose absolute path

### SI-GET-08 Text Attachment Stats
Fixture:
- .md / .markdown / .txt attachments exist

Expected:
- text_scannable count correct
- text_scan_bytes approximate by file sizes
- no full content returned

### SI-GET-09 Scan Cap Warning
Fixture:
- Text attachments exceed max file count or byte cap

Expected:
- warnings include scan cap warning
- scan_limits returned
- health=warning

### SI-GET-10 No Absolute Path Leak
Fixture:
- Missing and unsafe attachment paths

Expected:
- no C:\...
- no /home/...
- no raw dataDir prefix
- only basename or safe relative path

### SI-GET-11 Read-only Guarantee
Fixture:
- Snapshot Notes / Tags / Note_Attachments counts before request

Expected:
- Counts unchanged after GET
- Files unchanged
- No FTS rebuild

### SI-GET-12 Scan Limits Returned
Expected:
- max_files = 200
- max_bytes = 5242880
- max_duration_ms = 250

## POST /api/system/search-integrity/rebuild-fts

### SI-REBUILD-01 Normal Rebuild
Fixture:
- Healthy DB

Expected:
- status=success
- before/after counts returned
- health after rebuild ok

### SI-REBUILD-02 Repair Missing Rows
Fixture:
- Notes_FTS missing rows

Expected:
- after.missing_fts_rows=0
- fts_count aligns with notes_count

### SI-REBUILD-03 Repair Orphan Rows
Fixture:
- Notes_FTS has orphan rowids

Expected:
- after.orphan_fts_rows=0

### SI-REBUILD-04 Notes Unchanged
Expected:
- Notes count unchanged
- Note content/title hash unchanged

### SI-REBUILD-05 Attachments Unchanged
Expected:
- Note_Attachments count unchanged
- attachment metadata unchanged

### SI-REBUILD-06 Files Untouched
Expected:
- No upload or attachment file removed
- No file path rewritten

### SI-REBUILD-07 No VACUUM Semantics
Expected:
- Handler does not call VACUUM
- Test should not rely on DB file-size shrinkage
- Review diff manually for no VACUUM call

### SI-REBUILD-08 FTS Missing Failure
Fixture:
- Notes_FTS missing

Expected:
- endpoint returns error or clear failure
- does not create unrelated schema unless explicitly designed
- no silent success

### SI-REBUILD-09 Method Guard
Expected:
- GET on rebuild endpoint returns 405
- unsupported methods return method error

### SI-REBUILD-10 Security Boundary
Expected:
- POST uses existing CSRF / system route behavior
- no custom auth bypass
```

---

## 最終收斂結論

**Codex Execution Review Checklist** 的核心是：

> 先看改了哪些檔案，再看有沒有越權，最後才看功能。
> 

**Search Integrity Test Matrix** 的核心是：

> GET 只能診斷，POST 只能 rebuild FTS；兩者都不能碰筆記內容、附件檔案、schema 或自動修復流程。
> 

正式建議下一步執行順序：

1. 先用 `ABOUT-CURRENT-TRUTH-01` 測 Codex 是否遵守範圍。
2. 再執行 `SETTINGS-IA-01`。
3. 接著 `MAINT-COPY-01`、`BACKUP-UX-02`、`MAINT-OVERVIEW-01`。
4. 等 Settings 位置穩定後，再做 `SEARCH-INTEGRITY-API-01`。
5. API 完成後，才做 `SEARCH-INTEGRITY-REBUILD-01`。
6. 最後接 `SEARCH-INTEGRITY-UI-01`。

---

## 下一輪推薦討論方向

下一輪建議開：

**Search Integrity Implementation Detail 會**

主軸：把 `GET /api/system/search-integrity` 的 Go helper、SQL 查詢、attachment path 安全判斷、response shape、錯誤處理細節拆成可直接實作的技術規格。

備選方向：

**First Codex Task Dry Run 會**

主軸：拿 `ABOUT-CURRENT-TRUTH-01` 做一次模擬審查：預期 diff 長什麼樣、Codex 如果多改了什麼要退、build pass 後怎麼收。

我建議下一輪先開 **Search Integrity Implementation Detail 會**。因為測試矩陣已經定了，下一步要把後端實作邊界拆清楚，才不會讓 Codex 自己發明架構。
## 使用者

再來幾輪研討會 主軸是

目前的討論是否有到過度設計

延伸討論直到收斂後，再繼續推薦討論方向 數個昇級版分支方向 接AI LLM 功能 做自動學術論文整理分析、知識庫、主題定期自動追蹤功能、github上有那些專案的特色可以參考

## 助理

我會先做一次「反過度設計」審查，再把升級分支拆成可選產品線；GitHub 參考我會查近期仍活躍、功能可借鑑但不應直接接入的專案。

## 助理

結論先講：**有，最近幾輪已經開始接近過度設計邊界。**  

但不是完全浪費。比較準確的判斷是：

**討論層面合理，施工層面必須大幅砍 scope。**

目前 Prism Core 還在「Go primary Headless KMS + 桌面化 + 搜尋 UX + 設定整理」階段。如果現在直接把 Search Integrity API、Agent Search Contract、relevance ranking、paper analysis、topic tracking、LLM 工作流全部塞進主線，會把 Prism 從乾淨 KMS 做成大雜燴。

Prism 現在最值錢的是：本地優先、SQLite、Go primary runtime、純關鍵字搜尋、REST API、外部 Agent 可接但不污染核心。

---

## 第一輪：目前討論哪裡過度設計？

**Alex：**  

先拆。不是每個規格都過度設計，但「排序」已經開始超前。「Search Ranking / Relevance」還沒有足夠使用痛點支撐，現在做會變成小型搜尋引擎。前面收斂成暫緩是正確的。

**Kenji：**  

Search Integrity API 也有一點超前。如果目標是 Settings / Maintenance UX，先修 About current truth、Settings IA、Backup 文案就夠了。直接做 `GET /api/system/search-integrity`、`POST rebuild-fts`，雖然技術上合理，但現在未必是最優先。

**Sophie：**  

Codex Review Checklist / Test Matrix 本身不算過度設計，只要它是「防 Codex 暴走的審查文件」。但如果你把它變成正式工程模組、測試框架、維護平台，那就過了。

**Leo：**  

最危險的是「因為我們討論過，所以都想做」。這不行。討論過不代表進 active queue。現在 active queue 應該只保留 2～3 個小任務，其餘全部丟 branch backlog。

**Hana：**  

Settings 重排合理，因為現在 Settings 的資訊架構確實錯位：資料 tab 裡塞了維護、統計、備份、安全、危險區；搜尋 tab 只放分類/標籤；部署 tab 只剩 Server Dashboard。這不是過度設計，是清理 UI 債。

**收斂：**  

目前應該「砍施工，不砍方向」。  

也就是保留升級藍圖，但主線只做最少可用。

---

## 第二輪：現在該保留、砍掉、暫緩什麼？

### 立刻保留

1. **ABOUT-CURRENT-TRUTH-01**  
    
    About 還寫 Flask，這是 current truth 汙染，應該馬上修。
    
2. **SETTINGS-IA-01**  
    
    Settings 分類錯位，先重排，不新增功能。
    
3. **BACKUP-UX-02**  
    
    匯出副本、內建還原點、還原資料庫要講清楚，避免使用者誤解。
    
4. **Desktop Shell Phase 0**  
    
    這是桌面化地基，TODO 也已經明確列為下一步：Win32 視窗 + tray + 單一 message loop spike。
    

### 暫緩但保留規格

1. **Search Integrity API**  
    
    放 backlog。等 Settings IA / Backup UX 完成後再做。
    
2. **Search Result Highlight / Match Metadata**  
    
    合理，但不是當前最高優先。
    
3. **Agent Search Contract**  
    
    先當文件方向，不急著實作。
    
4. **Attachment Search 深化**  
    
    等你真的開始大量用附件資料再做。
    

### 先不要做

1. **Search Ranking / Relevance**
2. **GraphRAG**
3. **內建 LLM chat**
4. **自動論文追蹤**
5. **自動學術綜述**
6. **自動修復 / 自動整理資料**
7. **插件平台**
8. **多使用者 / 權限系統**
9. **全域熱鍵 / OS 級搜尋**

**Leo：**  

現在如果要一句話收斂：  

**Prism Core 先不要變 AI 系統。Prism Core 只做乾淨資料底座。AI 做外掛分支。**

---

## 第三輪：升級版分支方向

我建議把未來升級分成 5 條 branch，不要全部進 Prism Core。

### Branch A：Prism Core

定位：本地知識庫核心。  

只做：資料、搜尋、備份、桌面化、REST API、Agent-readable contract。  

不做：AI 分析、自動追蹤、embedding、ranking、plugin。

這是主線。所有升級分支都依賴它，但不能污染它。

---

### Branch B：Prism Scholar

定位：自動學術論文整理與分析。

功能可以包括：

- DOI / arXiv / PubMed / Semantic Scholar 匯入
- PDF / abstract / metadata 儲存
- 摘要、方法、資料集、結論、限制、引用整理
- citation-backed answer
- 同主題 paper cluster
- 文獻差異與矛盾偵測
- 研究問題 → paper queue → synthesis report

**Prism Scholar 不該直接做成 Core 功能。**  

它應該是一個外部 worker / CLI / sidecar，輸出結果寫回 Prism notes。

---

### Branch C：Prism Watch

定位：主題定期自動追蹤。

功能可以包括：

- RSS / arXiv / GitHub releases / Hacker News / blog / paper feed
- 關鍵字與主題訂閱
- 每日 / 每週 digest
- 變化偵測
- 「新增、重要、噪音、待讀」分類
- 產生 Brief note 寫回 Prism
- 支援手動批准，不自動塞爆知識庫

這條分支最容易失控。  

核心規則應該是：**Watch 只收集候選，不自動寫永久筆記。**

---

### Branch D：Prism AI Bridge

定位：讓外部 LLM / Agent 安全讀 Prism。

功能可以包括：

- read-only search API
- include_matches
- note detail
- attachment read
- prompt packet export
- agent-safe result format
- no destructive actions by default

Prism AI Bridge 的第一版不應該做聊天 UI。  

應該只做：**外部 Agent 可以可靠讀資料，不可以亂寫資料。**

---

### Branch E：Prism Archive / Document Intake

定位：文件、網頁、PDF、圖片、附件進入知識庫的入口。

功能可以包括：

- PDF / Markdown / HTML / web page 匯入
- OCR optional
- metadata extraction
- source URL 保存
- snapshot / archive
- attachment health
- duplicate detection

這條分支可做，但要小心：  

**Archive/Intake 不是 AI。它是資料進來前的清潔與保存。**

---

## 第四輪：GitHub 專案特色可參考，但不要直接接入

這裡的重點是「學設計，不接依賴」。

| 類型 | 專案 | 可參考特色 | Prism 不該直接照搬 |
| --- | --- | --- | --- |
| 學術 RAG | PaperQA / PaperQA2 | citation-backed QA、文獻 passage retrieval、contradiction detection | 不直接把整套 agent 塞進 Core |
| 學術綜述 | OpenScholar / Ai2 Scholar QA | 大規模 paper retrieval、citation-backed synthesis、benchmark | 不自建 4500 萬 paper datastore |
| 研究寫作 | STORM | 先問問題、建 outline、多觀點整理、引用生成 | 不直接自動產長文污染知識庫 |
| RAG pipeline | Haystack | pipeline/component 化、retriever/generator/evaluator 分層 | 不引入大型 Python AI stack 到 Core |
| AI UI | Open WebUI | 模型 UI、extension/pipeline 概念 | 不把 Prism 變聊天平台 |
| 個人 AI assistant | Khoj | 個人資料檢索與 assistant 體驗 | 不做全能 assistant |
| 文件管理 | paperless-ngx | ingestion、OCR、metadata、分類、歸檔 | 不先做完整 DMS |
| 網頁保存 | ArchiveBox | snapshot、archive、來源保存 | 不把 Prism 變爬蟲平台 |
| Topic watch | FreshRSS / changedetection.io | feed、watch、diff、通知 | 不自動永久寫入知識庫 |

---

## 第五輪：是否過度設計的最終判斷

**Alex：**  

目前討論如果轉成「全部施工」，就是過度設計。  

如果轉成「Core + branch backlog」，就是合理產品規劃。

**Kenji：**  

Core 現在只該做：

1. About current truth fix
2. Settings IA
3. Backup UX
4. Desktop shell phase 0
5. Search UX minimal

Search Integrity API 都可以等。

**Nolan：**  

AI 分支可以設計，但不要內建。第一版最乾淨的方式是：

- Prism Core 提供資料與 API。
- 外部 script / worker / agent 做 AI。
- AI 結果回寫成 note。
- 所有 AI note 要標記來源、模型、時間、引用、confidence / limitations。

**Sophie：**  

自動化追蹤一定要有 pending queue。不要抓到東西就自動寫 permanent note。

**Leo：**  

一句話：**Prism Core 要笨但可靠；AI 分支可以聰明但隔離。**

---

## 第六輪：升級分支優先順序

我建議這樣排：

### Phase 0：Core 收斂

只做：

- About current truth
- Settings IA
- Backup UX
- Desktop shell phase 0
- Search entry UX

這是現在最該做的。

### Phase 1：Agent-safe Read Layer

- `GET /api/notes?q=...&include_matches=1`
- Agent Search Contract
- read-only note/attachment access
- 不寫入、不刪除、不自動修復

### Phase 2：Prism Watch Lite

- RSS / URL watch / arXiv keyword watch
- 只建立「候選」
- 手動批准寫入 Prism
- 每週 digest note

### Phase 3：Prism Scholar Lite

- PDF / arXiv / DOI 匯入
- 一篇 paper 的結構化摘要
- citation / source 保存
- 不做跨文獻自動綜述

### Phase 4：Prism Scholar Pro

- 多篇 paper cluster
- literature review
- contradiction detection
- research brief
- scheduled topic synthesis

### Phase 5：Graph / Semantic / Ranking

- embedding
- semantic search
- GraphRAG
- relevance ranking
- knowledge graph

這階段最晚。不要現在做。

---

## 最終收斂結論

目前確實有過度設計風險，主要風險在於：

1. **把維護工具做太大。**
2. **把搜尋做成搜尋引擎。**
3. **把 Agent contract 提早產品化。**
4. **把 AI/LLM 分支混進 Core。**
5. **把 topic tracking 直接自動寫入知識庫。**

收斂後的正確路線：

**Core 先穩。AI 分支隔離。追蹤先候選。學術先單篇。綜述與 GraphRAG 最後。**

正式建議：

| 方向 | 現在狀態 | 決策 |
| --- | --- | --- |
| Settings / Backup / Desktop | Core 必要 | 施工 |
| Search Integrity | 有價值但不急 | 暫緩 |
| Agent Search | 有價值 | 先做文件，後做 read-only |
| AI Chat | 容易污染 Core | 暫不做 |
| 自動論文整理 | 可做分支 | 從單篇 paper 開始 |
| 主題定期追蹤 | 可做分支 | 只做候選 queue |
| GitHub 參考專案 | 可看 | 只借設計，不接入 |
| Semantic / GraphRAG | 太早 | 放長期 |

---

## 下一輪推薦討論方向

下一輪建議開：

**Prism Branch Architecture 會**

主軸：正式定義 Core / Scholar / Watch / AI Bridge / Archive 五條分支的邊界、資料流、是否共用 DB、是否用 sidecar worker、如何回寫 note、哪些功能禁止進 Core。

備選方向：

**Prism Scholar Lite 規格會**

主軸：只做「單篇論文整理」MVP：PDF/URL/arXiv 匯入、metadata、摘要、方法、貢獻、限制、引用、手動保存。不要一開始做自動綜述。

我建議先開 **Prism Branch Architecture 會**。因為你現在真正需要的是防止 AI 分支污染 Core，而不是再細化某一個 AI 功能。
## 使用者

再來幾輪研討會 主軸是

Prism Branch Architecture

延伸討論直到收斂後，再繼續推薦討論方向

論文部份需修正，我不是研究生 這部份對我沒有用(嗯.... 如果有做成學業服務的話搞不好有用啦，市面上有這種東西嗎？)，但我主要是要自動 找跟量化交易(還有跟交易有關的數學部份)有關的論文、尤其是訂單簿研究 有看有沒有可以參考的地方，來增加交易方式或穩健

## 助理

我已經把「學術論文」改成「量化研究雷達」來看，不會再按研究生/寫論文那套設計。接下來重點是：找 paper → 抽可驗證假設 → 對接 CerberusCoin 實驗，不是寫文獻綜述。

## 助理

結論：你這個修正很重要。前面「Prism Scholar」那個命名偏掉了，因為它假設你要做學術研究/寫論文；實際上你要的是：

**自動掃描量化交易、交易數學、訂單簿 / market microstructure 相關論文 → 抽出可測假設 → 轉成 CerberusCoin 的研究任務或因子候選 → 用資料驗證。**

所以這條分支不該叫 Scholar。建議改名：

**Prism Quant Research Radar**  

或更直接：**Cerberus Research Radar**

它不是「幫你寫文獻綜述」，而是「幫你挖可能有交易價值的研究線索」。

---

## 第一輪：論文分支重新定位

**Alex：**  

前面 Scholar branch 要修正。使用者不是研究生，不需要 literature review、citation graph、related work drafting 那套完整學術流程。真正需求是交易研究支援。

**Maria：**  

所以 paper branch 的輸入不是「請幫我理解某領域」，而是：

- limit order book
- order flow
- market microstructure
- queue imbalance
- microprice
- liquidity
- adverse selection
- market impact
- execution
- volatility / realized volatility
- Hawkes process
- stochastic process
- regime detection
- crypto market microstructure
- funding / OI / liquidation / basis / premium

輸出也不是論文摘要，而是：

- 這篇論文提出什麼可交易假設？
- 需要什麼資料？
- 你目前 CerberusCoin 有沒有資料？
- 可否轉成 feature？
- 可否回測？
- 適合 BTC / crypto 嗎？
- 是 alpha、risk filter、execution filter，還是 regime detector？
- 是否只是理論，落地成本多高？

**Kenji：**  

這就不是學術系統，而是 research intake pipeline。它應該跟 CerberusCoin 連，不要塞進 Prism Core。Prism Core 只保存 note、metadata、tags、source、附件；Quant Research Radar 負責外部抓 paper、評分、產生研究卡。

**Leo：**  

簡單講：不要讓 Prism 幫你「讀書」。讓它幫你「找能不能賺錢或降低爆倉風險的研究線索」。這方向才對。

---

## 第二輪：市面上有沒有這種學業/論文服務？

有，而且不少。只是大多數是給研究生、研究員、醫藥/政策文獻回顧用，不是專門給量化交易策略研究。

Elicit 是典型例子，它定位為 AI scientific research 工具，官方頁面寫它可以搜尋大量學術論文、用語意搜尋找相關結果、產生 research reports、支援 systematic review、library、alerts，還有 API；它宣稱可搜尋 138M+ academic papers 與 545,000 clinical trials，並支援 alerts 與 report 工作流。

ResearchRabbit 則比較像「文獻探索地圖」，官方頁面描述它可以從一篇 paper 延伸到作者、相關作品、emerging topics，並用視覺化理解 papers / authors 的關係與主題演化；它也強調整理 papers、notes、ideas，以及 310M+ academic papers。

Semantic Scholar API 則更適合你這種自動化用途。它提供 Academic Graph，可查 papers、authors、citations、venues、SPECTER2 embeddings，也有 Recommendations 服務可根據一篇 paper 推薦相似 papers；官方頁面也列出 datasets 與 214M papers、2.49B citations、79M authors 等 corpus 指標。

所以答案是：**市面上有，但它們多數是「學術文獻發現 / 寫作 / 引用」工具，不是「量化交易研究轉策略」工具。**  

你要的東西更像：Elicit / ResearchRabbit / Semantic Scholar 的 paper discovery，加上 CerberusCoin 的 factor validation pipeline。

---

## 第三輪：Prism Branch Architecture 修正版

我建議分支改成這樣：

| Branch | 定位 | 是否進 Core |
| --- | --- | --- |
| Prism Core | 本地 KMS、搜尋、備份、桌面化、REST API | 是 |
| Prism AI Bridge | 外部 Agent 安全讀 Prism，不內建 AI | 半進 Core，read-only 優先 |
| Prism Watch | 定期追蹤 RSS / arXiv / GitHub / blog | sidecar |
| Prism Quant Research Radar | 自動找量化與訂單簿研究，轉成研究假設 | sidecar |
| Prism Archive Intake | 網頁/PDF/Markdown 進資料庫 | sidecar 或輕量工具 |
| Prism Scholar | 學業/論文寫作服務版 | 可做商業分支，但不是你的主線 |

**Alex：**  

最重要的調整是：Scholar 不再是你的主線。你的主線是 Quant Research Radar。

**Nolan：**  

AI 不進 Core。AI Bridge 只提供：查詢、讀 note、讀附件、回寫研究卡。LLM 不碰 DB schema，不直接跑 SQL，不做交易決策，不自動下單。

**Leo：**  

Prism Core 要保持笨但穩。聰明的東西全部丟 sidecar。這是防止系統變大雜燴的核心原則。

---

## 第四輪：Quant Research Radar 應該做什麼

**Maria：**  

這條分支的真正工作流應該是：

1. **定期搜尋 paper**
    - arXiv q-fin
    - SSRN
    - Semantic Scholar
    - Google Scholar 不好自動化，可先不用
    - Papers With Code 可補 ML/LOB 模型
    - GitHub repo / paper-with-code links
2. **初篩**
    - 是否跟交易、microstructure、order book、crypto、HFT、execution、volatility、regime 有關
    - 是否只是股票市場，但概念可轉 BTC
    - 是否需要 tick / L2 / L3 / queue position
    - 你目前資料能不能驗證
3. **抽研究卡**
    
    每篇 paper 轉成一張「Research Signal Card」：
    
    - paper title
    - source / DOI / arXiv
    - market type
    - core hypothesis
    - required data
    - candidate features
    - expected horizon
    - validation method
    - implementation cost
    - robustness concern
    - relevance to CerberusCoin
    - decision: skip / watch / implement experiment
4. **進 CerberusCoin**
    
    只有通過的研究卡才變成：
    
    - factor candidate
    - experiment manifest
    - backtest task
    - feature layer ticket
    - regime filter ticket

**Kenji：**  

這裡要加一道硬門檻：paper 不准直接變策略。paper 只能變「待驗證假設」。驗證過才進策略。

**Sophie：**  

對，而且每張研究卡要標記資料需求。例如：

- 只需 OHLCV：可低成本驗證
- 需 L2 order book：你可能有 Binance/Coinbase ±1% depth
- 需 L3 queue position：暫時不做
- 需 true cancel/add event：如果你只有 snapshot，就要標 sample-limited
- 需交易所完整 message feed：暫緩

---

## 第五輪：訂單簿研究的分類

**Maria：**  

你的 radar 不應該搜尋泛泛的「quant trading」。要設分類，否則會撈到一堆沒用的 ML 股市 paper。

建議分類：

| 類別 | 可能轉成什麼 |
| --- | --- |
| Order Book Imbalance | bid/ask imbalance、depth slope、microprice |
| Queue Imbalance | 如果沒有 L3，只能做近似或暫緩 |
| Microprice / Fair Price | 短期價格壓力估計 |
| Order Flow Toxicity | adverse selection / VPIN / flow toxicity |
| Market Impact | 大單衝擊、sweep detection |
| Liquidity Resilience | 掛單牆持續性、撤單恢復速度 |
| Regime Detection | trend/range/volatile/liquidity-thin |
| Hawkes / Self-exciting Process | trade clustering、burst detection |
| Volatility Forecasting | realized vol、range vol、LOB feature vol |
| Execution / Slippage | 進出場保守估計、風險折扣 |
| Crypto Microstructure | funding、OI、basis、liquidation、premium |
| Manipulation / Spoofing | spoofing、layering、wash trading |

**Alex：**  

這分類要直接對應 CerberusCoin，不然只是文獻庫。

**Leo：**  

最沒用的是「這篇 paper 很有趣」。最有用的是「這篇 paper 需要 L2 snapshot，我們有；能測；預期對 1m/5m horizon 有幫助；先做 experiment」。

---

## 第六輪：Prism Core 與 CerberusCoin 的資料流

**Kenji：**  

建議資料流如下：

```
Research Sources
  ↓
Quant Research Radar sidecar
  ↓
Research Signal Cards
  ↓
Prism Core note storage
  ↓
CerberusCoin experiment backlog
  ↓
Backtest / OOS / robustness check
  ↓
Strategy / factor / risk filter decision
```

**Nolan：**  

LLM 在這裡的角色是「轉譯與篩選」，不是「決策」。它可以幫你把 paper 翻成 feature candidate，但不能宣稱有效。

**Sophie：**  

每張 Research Signal Card 必須有狀態：

- new
- screened
- candidate
- experiment-ready
- rejected
- implemented
- invalidated
- archived

**Iris：**  

Prism 裡只存卡片與來源，不存一堆亂七八糟的自動摘要。摘要要有模板，不然之後搜尋會被 AI 產物污染。

---

## 第七輪：GitHub / 開源專案可參考方向

這裡分兩種：**paper discovery 工具**與**量化研究工具**。

### Paper discovery / research automation

| 專案/工具 | 可參考點 |
| --- | --- |
| Elicit | paper search、structured report、alerts、API、citation-backed claims |
| ResearchRabbit | citation map、related papers、topic evolution |
| Semantic Scholar API | paper/citation/author graph、recommendation、metadata API |
| PaperQA / PaperQA2 | citation-backed paper QA、文獻問答 |
| ResearchPilot 類系統 | local-first literature synthesis、arXiv/Semantic Scholar retrieval |

這些適合參考「找 paper / 管 paper / 產摘要 / 保留引用」。但不要整套接進 Prism。

### Quant / order book research

| 專案/工具 | 可參考點 |
| --- | --- |
| hftbacktest | LOB replay、latency、queue/slippage 假設檢查；適合當 order-book backtest guardrail。 |
| Qlib | 實驗管理、資料集、模型研究 workflow。 |
| vectorbt | 大量參數掃描與 research iteration |
| Freqtrade | lookahead/recursive analysis、防回測污染 |
| NautilusTrader | event-driven trading/backtest architecture，可當大型架構參考 |
| STUMPY / matrix profile | pattern / analog similarity search |
| Alphalens / QuantStats | factor forward return、績效報告 |

---

## 第八輪：市面服務 vs 你真正要做的東西

**Alex：**  

市面服務能幫你找 paper，但不能幫你判斷「這篇 paper 對 BTC 訂單簿交易有沒有用」。那是你的 domain layer。

**Maria：**  

Elicit / ResearchRabbit / Semantic Scholar 可以幫你找到 paper。  

Cerberus Quant Research Radar 要幫你回答：

- 這篇 paper 的 signal 是什麼？
- 它假設什麼市場結構？
- crypto BTC 是否符合？
- 資料粒度夠不夠？
- 會不會有 lookahead？
- 是否需要 L3？
- 是否只適合 market making，不適合 directional decision？
- 是否可轉為 risk filter 而不是 alpha？

**Leo：**  

所以你不用做「AI 論文助手」。你要做「量化研究偵察兵」。

---

## 最終收斂：Branch Architecture 修正版

正式建議：

| Branch | 新定位 | 優先級 |
| --- | --- | --- |
| Prism Core | 本地 KMS + 搜尋 + 備份 + REST API + desktop shell | 最高 |
| Prism AI Bridge | 外部 Agent 安全讀寫，先 read-only | 中 |
| Cerberus Research Radar | 量化/LOB paper → research cards → experiment backlog | 高，但 sidecar |
| Prism Watch | RSS/arXiv/GitHub/URL topic watch → candidate queue | 中 |
| Prism Archive Intake | web/PDF/markdown/source intake | 中 |
| Prism Scholar Service | 學業/文獻整理服務版，非自用主線 | 低，可商業化想像 |

**把原本 Prism Scholar 拆成兩個：**

1. **Cerberus Research Radar**：你真正需要的，自動找交易研究。
2. **Prism Scholar Service**：如果未來想做學生/研究生服務，另開商業分支，不污染 Core。

---

## 建議 MVP：Cerberus Research Radar Lite

第一版只做這樣：

1. 每週抓 20～50 篇候選 paper。
2. 來源：Semantic Scholar API + arXiv q-fin + 手動 seed paper。
3. 關鍵字：
    - limit order book
    - order book imbalance
    - market microstructure
    - queue imbalance
    - microprice
    - order flow
    - high frequency trading
    - liquidity
    - market impact
    - Hawkes process
    - crypto market microstructure
    - volatility forecasting
4. LLM 只做抽取：
    - hypothesis
    - required data
    - candidate feature
    - validation path
    - crypto applicability
    - rejection reason
5. 產出 Research Signal Card。
6. 手動批准後才寫入 Prism / Cerberus backlog。
7. 不自動產策略。
8. 不自動下單。
9. 不自動改 CerberusCoin code。

---

## 這輪結論

你修正得對。**論文分支不是學術分支，而是量化研究雷達。**

更精準的總架構是：

Prism Core 負責存與搜。  

Cerberus Research Radar 負責找研究線索。  

CerberusCoin 負責驗證與回測。  

LLM 只負責翻譯 paper → 假設，不負責判定有效。

下一輪我建議開：

**Cerberus Research Radar Lite 規格會**

主軸：定義 Research Signal Card schema、paper sources、關鍵字查詢、評分規則、LLM 抽取 prompt、如何寫入 Prism / CerberusCoin backlog。

備選方向：

**Quant Paper Taxonomy 會**

主軸：把訂單簿、交易數學、微觀結構、風險、execution、regime 研究分類成可搜尋與可驗證的 taxonomy。

我建議先開 **Cerberus Research Radar Lite 規格會**。這會直接對你的用途落地，不會再偏成研究生文獻整理工具。
## 使用者

再來幾輪研討會 主軸是

Cerberus Research Radar Lite 規格會 / Quant Paper Taxonomy 會

延伸討論直到收斂後，再繼續推薦討論方向

## 助理

結論：這次要把前面「Prism Scholar」整個修正掉。你要的不是學術文獻整理工具，而是：

**Cerberus Research Radar Lite：自動找量化交易、訂單簿、交易數學、市場微觀結構相關研究，抽成可驗證假設，最後丟給 CerberusCoin 做實驗。**

這不是研究生服務，也不是寫論文工具。它的核心價值是幫你從論文裡撈「可能能提高交易穩健性或補強策略判斷的東西」。

---

## 第一輪：Branch Architecture 修正

**Alex：**  

原本 `Prism Scholar` 命名錯了。它聽起來像幫研究生讀 paper、整理 citation、寫 literature review。這對你不是主需求。正確分支應該叫：

**Cerberus Research Radar**

它隸屬 CerberusCoin，不隸屬 Prism Core。Prism 只是存研究卡、來源、摘要、標籤與狀態。

**Iris：**  

Prism Core 仍然只做本地知識庫：notes、attachments、search、backup、desktop shell。不要把 paper crawler、LLM 分析、交易研究 pipeline 塞進 Prism Core。

**Kenji：**  

技術邊界應該是 sidecar：

```
Paper Sources
  ↓
Cerberus Research Radar sidecar
  ↓
Research Signal Card
  ↓
Prism Core note
  ↓
CerberusCoin experiment backlog
  ↓
Backtest / OOS / robustness check
```

**Nolan：**  

LLM 只做「翻譯與抽取」：把 paper 變成 hypothesis、feature idea、data requirement、validation path。它不能直接說「這策略有效」，更不能直接改 CerberusCoin code。

**Leo：**  

一句話：**論文只能變假設，不能變策略。**

---

## 第二輪：這跟市面學業服務有什麼差別？

**Alex：**  

市面上確實有偏學業/研究用途的工具。ResearchRabbit 這類工具主打文獻探索、citation network、paper recommendation、研究管理與視覺化；它比較適合做文獻探索與學術關聯圖。Semantic Scholar / OpenAlex 這類資料源則適合用來抓 paper metadata、citation graph、abstract、作者、引用與相關 paper；Semantic Scholar Open Data Platform 描述的是一個大型科學文獻平台，包含 200M+ papers、80M+ authors、2.4B+ citation edges 與 APIs。OpenAlex 也定位為 open scientific knowledge graph，提供 metadata、GUI、data dump 與 REST API。

**Maria：**  

但那些工具多數回答的是：

「這領域有哪些 paper？」  

「誰引用誰？」  

「幫我做文獻回顧。」

你要回答的是：

「這篇 paper 有沒有可能變成 BTC 交易因子？」  

「需要什麼資料？」  

「我目前 CerberusCoin 有沒有資料可以測？」  

「它是 alpha、risk filter、execution filter，還是 regime detector？」  

「如果不能做，卡在哪裡？」

這是完全不同的產品。

**Leo：**  

如果未來要做學業服務，可以另開 `Prism Study / Scholar Service`。但不要拿那條分支污染你的自用主線。

---

## 第三輪：Cerberus Research Radar Lite MVP

**Alex：**  

Lite 版只做「找 → 篩 → 產研究卡」。不要做完整自動研究員。

MVP 流程：

1. 每週或手動抓候選 paper。
2. 來源先用 Semantic Scholar / OpenAlex / arXiv。
3. 用 taxonomy 初篩。
4. LLM 抽取交易假設。
5. 產生 Research Signal Card。
6. 手動批准後才寫進 CerberusCoin backlog。
7. 不自動生成策略。
8. 不自動改 code。
9. 不自動下單。

**Kenji：**  

資料流要非常保守。Radar sidecar 只寫：

- Prism note
- Cerberus backlog markdown
- experiment candidate json

不能直接改 runtime strategy。

**Sophie：**  

每張 Research Signal Card 必須有狀態：

`new → screened → candidate → experiment-ready → tested → rejected / implemented / archived`

這樣才不會變成「自動抓一堆 paper 然後淹死」。

---

## 第四輪：Research Signal Card schema

**Maria：**  

我建議研究卡固定成這個結構：

```yaml
id: CRR-YYYYMMDD-001
status: new | screened | candidate | experiment-ready | tested | rejected | implemented | archived

paper:
  title:
  authors:
  year:
  source:
  url:
  doi:
  arxiv_id:
  semantic_scholar_id:
  openalex_id:

taxonomy:
  primary_topic:
  secondary_topics:
  market_type:
  asset_class:
  data_granularity:
  horizon:

trading_translation:
  core_hypothesis:
  possible_signal:
  possible_filter:
  possible_risk_use:
  expected_horizon:
  expected_directionality:

data_requirements:
  required_data:
  available_in_cerberus:
  missing_data:
  data_blocker:
  snapshot_limitation:

implementation:
  feature_candidates:
  experiment_type:
  backtest_feasibility:
  estimated_complexity:
  lookahead_risk:
  robustness_checks:

decision:
  relevance_score:
  action: skip | watch | create_experiment | read_deeper
  reason:
```

**Nolan：**  

LLM 只填這張卡，不自由發揮。尤其要固定問它：

- 這篇 paper 的交易假設是什麼？
- 需要 L1 / L2 / L3 / trades / OI / funding / liquidation 嗎？
- CerberusCoin 現有資料能不能測？
- 如果不能測，是資料不足還是模型太重？
- 這是 directional alpha 還是 risk/execution filter？

**Leo：**  

最重要欄位是 `data_blocker`。很多 paper 看起來很強，但需要 L3 queue position 或 full message feed。沒有資料就不要硬做。

---

## 第五輪：Quant Paper Taxonomy

**Maria：**  

Taxonomy 要直接對應交易用途，不要照學術分類。建議第一版如下。

| Taxonomy | 你要找什麼 | 可轉成什麼 |
| --- | --- | --- |
| Order Book Imbalance | bid/ask depth imbalance、level imbalance | 短線壓力、entry filter |
| Microprice / Fair Price | microprice、weighted mid、efficient price | 1m/5m direction hint |
| Queue Imbalance | queue position、queue depletion | 需要 L3，多半暫緩 |
| Order Flow Toxicity | VPIN、adverse selection、informed flow | 避免接刀、risk filter |
| Liquidity Resilience | liquidity replenishment、wall persistence | 掛單牆真假、支撐/壓力可信度 |
| Market Impact | metaorder、large trade impact、sweep | 大單衝擊與滑價模型 |
| Hawkes / Burst Process | self-exciting trades、clustered events | burst detector、volatility warning |
| Volatility Forecasting | realized vol、LOB-derived vol | position sizing、risk mode |
| Regime Detection | trend/range/liquidity-thin/stress | strategy routing |
| Execution / Slippage | fill probability、slippage model | 回測折價、進出場保守化 |
| Crypto Microstructure | funding、OI、basis、liquidation、exchange premium | BTC-specific factor |
| Manipulation / Spoofing | spoofing、layering、wash trading | anomaly/risk flag |

**Alex：**  

第一版先重點抓 4 類：

1. Order Book Imbalance  
2. Microprice / Fair Price  
3. Liquidity Resilience  
4. Crypto Microstructure

其他先放第二階段。

**Kenji：**  

因為這四類最可能用你現有資料驗證。Queue imbalance、true fill probability、latency-sensitive execution 多半需要 L3 或更細資料，現在容易做假。

---

## 第六輪：資料可行性分級

**Sophie：**  

每篇 paper 必須先判資料可行性，否則會變成空想。

| 級別 | 意義 | 決策 |
| --- | --- | --- |
| A | 只需 OHLCV / trades / funding / OI | 可快測 |
| B | 需要 L2 order book snapshot | 可測，但要標 snapshot limitation |
| C | 需要 tick-level trades + L2 | 可研究，但成本較高 |
| D | 需要 L3 message feed / queue position | 暫緩 |
| E | 需要交易所內部資料或不可取得資料 | reject |

**Maria：**  

你目前最有價值的是 B 類：LOB snapshot 可做的指標，例如 imbalance、depth slope、spread、microprice approximation、liquidity wall persistence、order book pressure。  

但要誠實標記：如果只有 1m snapshot，就不能宣稱知道真實 queue dynamics。

**Leo：**  

這就是 Radar 的價值：不是只說 paper 好，而是直接說「這篇 paper 很好，但你現在資料測不了，所以先別浪費時間」。

---

## 第七輪：評分規則

**Alex：**  

Lite 版要有簡單 scoring，不然 paper 會越堆越多。

建議 5 個分數，每項 0～5：

| Score | 問題 |
| --- | --- |
| Relevance | 跟 BTC / crypto / LOB / quant 是否直接相關 |
| Data Fit | 現有 CerberusCoin 資料能否驗證 |
| Implementability | 轉成 feature / experiment 是否容易 |
| Robustness Value | 是否能提高穩健性、避開風險或降低 false signal |
| Novelty | 是否補足目前策略盲點 |

總分不是越高越自動做，而是決定動作：

| 分數 | 動作 |
| --- | --- |
| 0～8 | skip |
| 9～14 | watch |
| 15～19 | create candidate |
| 20～25 | create experiment |

**Kenji：**  

還要加 hard rejection：

- 需要 L3 但你沒有資料。
- 需要 nanosecond latency。
- 只在股票 market making 可用，不能轉 directional/risk filter。
- paper 沒有可測 hypothesis。
- 只有深度學習黑箱但無可解釋 feature。
- 明顯 lookahead 或 survivorship bias。

---

## 第八輪：Lite 版系統邊界

**Nolan：**  

CRR-Lite 的邊界：

可以做：

- 搜 paper metadata
- 拉 abstract
- 找 citation / related papers
- LLM 抽 Research Signal Card
- 存 Prism note
- 建 Cerberus backlog candidate
- 每週產一份 Radar Digest

不能做：

- 自動改策略
- 自動下單
- 自動加入 live signal
- 自動寫 production factor
- 自動判定 paper 有效
- 未經批准大量寫入 Prism

**Iris：**  

Prism 裡要存的不是完整論文庫，而是精煉卡片。Full PDF 可作附件，但不是每篇都存。避免知識庫膨脹。

**Leo：**  

第一版每週最多 10 張卡。超過就是垃圾郵件。

---

## 第九輪：GitHub / 開源參考怎麼用

**Kenji：**  

這裡要小心。GitHub 專案只能參考設計，不要直接接。

可參考：

- `hftbacktest`：看它怎麼處理 order book backtest、latency、fill/slippage assumptions。
- Qlib：看 experiment management、factor research workflow。Qlib 論文定位是 AI-oriented quantitative investment platform，適合參考研究流程而不是直接接入。這裡注意：Qlib 本身要另外查 repo/文件再定，現在只先列為後續候選。
- vectorbt / Freqtrade / NautilusTrader：後續可查，但先不要混入 Radar Lite。

**Sophie：**  

Radar Lite 不是 backtester。它只產 experiment candidate。回測仍由 CerberusCoin 負責。

**Leo：**  

不要讓 Codex 看到 `hftbacktest` 就拉依賴。最多寫「參考 queue/slippage 假設分類」。

---

## 收斂規格：Cerberus Research Radar Lite

**正式定義：**

Cerberus Research Radar Lite 是一個 sidecar，不是 Prism Core。它定期或手動搜尋量化交易、交易數學、LOB、market microstructure、crypto microstructure 相關研究，將 paper 抽成 Research Signal Card，並交由使用者手動批准是否進 CerberusCoin 實驗 backlog。

**第一版只做：**

1. Paper discovery：
    - Semantic Scholar
    - OpenAlex
    - arXiv q-fin / stat / cs
    - manual seed list
2. Taxonomy filtering：
    - Order Book Imbalance
    - Microprice / Fair Price
    - Liquidity Resilience
    - Crypto Microstructure
3. LLM extraction：
    - hypothesis
    - data requirements
    - candidate feature
    - validation path
    - blockers
    - relevance score
4. Output：
    - Research Signal Card
    - Weekly Radar Digest
    - optional Prism note
    - optional Cerberus backlog item
5. Guardrails：
    - 不自動產策略
    - 不自動改 code
    - 不自動下單
    - 不大量寫入 Prism
    - 不把 paper 結論當實證

---

## 建議第一批 keyword seed

```
limit order book
order book imbalance
queue imbalance
microprice
market microstructure
order flow imbalance
liquidity resilience
adverse selection
VPIN
market impact
Hawkes process trading
self-exciting order flow
realized volatility order book
high frequency trading limit order book
crypto market microstructure
bitcoin order book
cryptocurrency liquidity
funding rate open interest liquidation
basis premium crypto futures
```

---

## 建議第一版 Research Card action

| Action | 意義 |
| --- | --- |
| skip | 不適合、資料不足、無可測假設 |
| watch | 有趣但暫時不做 |
| read_deeper | 需要人工細讀 |
| create_candidate | 建研究候選 |
| create_experiment | 進 CerberusCoin 實驗 backlog |

---

## 最終結論

這輪收斂後，分支架構應該是：

Prism Core：存與搜。  

Cerberus Research Radar：找研究線索。  

CerberusCoin：驗證與回測。  

LLM：只做抽取，不做決策。

真正的 MVP 不是「自動學術論文整理」，而是：

**每週幫你找少量高相關 paper，轉成可驗證的交易研究卡，讓你判斷要不要測。**

---

## 下一輪推薦討論方向

下一輪建議開：

**Research Signal Card Schema 會**

主軸：把 Research Signal Card 欄位、YAML / JSON 格式、Prism note template、CerberusCoin backlog mapping 定死，讓 Codex 可以直接做第一版 parser / writer。

備選方向：

**Paper Source Query Contract 會**

主軸：定義 Semantic Scholar / OpenAlex / arXiv 的查詢 query、去重規則、rate limit、metadata normalization、候選上限。

我建議先開 **Research Signal Card Schema 會**。因為只要卡片格式定了，paper source、LLM prompt、Prism 回寫、Cerberus backlog 都能圍著它施工。
## 使用者

再來幾輪研討會 主軸是

Research Signal Card Schema / Paper Source Query Contract

延伸討論直到收斂後，再繼續推薦討論方向

## 助理

結論：這輪應該正式把 **Cerberus Research Radar Lite** 定成「研究訊號偵察系統」，不是論文摘要系統。

它的核心產物不是 paper summary，而是 **Research Signal Card**。  

每張卡只回答一件事：

**這篇研究有沒有可能變成 CerberusCoin 的可測因子、風險濾網、execution 修正，或 regime 判斷？**

---

## 第一輪：Research Signal Card 的定位

**Alex：**  

Research Signal Card 不是學術筆記。它是交易研究入口票。  

如果一篇 paper 不能轉成「資料需求 + 假設 + feature candidate + validation path」，那它就不該進 CerberusCoin backlog。

**Maria：**  

卡片要避免寫成「這篇 paper 說了什麼」。那是摘要。  

我們要的是：

- 它提出了什麼市場機制？
- 那個機制能不能在 BTC / crypto market 上重現？
- 需要 L1、L2、L3、trades、OI、funding、liquidation 還是 ETF flow？
- 你現在有沒有資料？
- 如果有，怎麼測？
- 如果沒有，卡在哪裡？

**Kenji：**  

這張卡要能直接轉成 engineering task。否則它只是漂亮筆記。

**Leo：**  

只要卡片不能導出「測或不測」決策，就算寫得再漂亮也是垃圾。

---

## 第二輪：Research Signal Card Schema 收斂版

我建議 schema 分成七段，不要更複雜。

```yaml
id: CRR-20260616-001
status: new  # new | screened | candidate | experiment_ready | tested | rejected | implemented | archived

source:
  title:
  authors:
  year:
  venue:
  source_platform: arxiv | semantic_scholar | openalex | manual
  url:
  doi:
  arxiv_id:
  semantic_scholar_id:
  openalex_id:
  retrieved_at:

taxonomy:
  primary_topic:
  secondary_topics:
  market_type:
  asset_class:
  data_granularity:
  expected_horizon:

trading_hypothesis:
  core_claim:
  possible_signal:
  possible_filter:
  possible_risk_use:
  directionality:
  expected_effect:
  why_it_might_work_in_btc:

data_fit:
  required_data:
  available_in_cerberus:
  missing_data:
  data_fit_level: A | B | C | D | E
  blocker:
  snapshot_limitation:

implementation:
  candidate_features:
  experiment_type:
  validation_path:
  backtest_feasibility:
  complexity: low | medium | high
  lookahead_risk:
  robustness_checks:

scoring:
  relevance: 0
  data_fit: 0
  implementability: 0
  robustness_value: 0
  novelty: 0
  total: 0

decision:
  action: skip | watch | read_deeper | create_candidate | create_experiment
  reason:
  next_step:
```

**Sophie：**  

`data_fit_level` 是核心欄位。它比 relevance 更重要。  

一篇 paper 再相關，如果需要 L3 queue position，而你只有 L2 snapshot，就不能進 experiment-ready。

**Nolan：**  

LLM output 必須嚴格符合這張 schema。欄位不知道就填 `unknown` 或空陣列，不准腦補。

---

## 第三輪：資料可行性分級

**Maria：**  

資料等級建議固定：

| 等級 | 定義 | 決策 |
| --- | --- | --- |
| A | 只需 OHLCV / funding / OI / liquidation / premium | 可快測 |
| B | 需要 L2 order book snapshot | 可測，但標 snapshot limitation |
| C | 需要 tick trades + L2 | 可研究，但成本高 |
| D | 需要 L3 message feed / queue position / cancel-add event | 暫緩 |
| E | 需要交易所內部資料或不可取得資料 | reject |

**Kenji：**  

CerberusCoin 現在最適合 A/B。  

B 類尤其重要：order book imbalance、depth slope、spread、microprice approximation、liquidity wall persistence。  

D 類暫緩，不要用 1m snapshot 假裝 queue dynamics。

**Leo：**  

這是硬規則：**data_fit D/E 不得自動 create_experiment。**

---

## 第四輪：Quant Paper Taxonomy 收斂版

第一版 taxonomy 不要太大。先用 12 類，但 MVP 只啟用前 4 類。

| Topic | 交易用途 | MVP |
| --- | --- | --- |
| Order Book Imbalance | entry filter / short-horizon pressure | 是 |
| Microprice / Fair Price | fair price / 1m-5m direction hint | 是 |
| Liquidity Resilience | wall persistence / fake support resistance | 是 |
| Crypto Microstructure | funding、OI、basis、liquidation、exchange premium | 是 |
| Market Impact | large trade impact / sweep detection | 後 |
| Order Flow Toxicity | adverse selection / avoid bad fills | 後 |
| Hawkes / Burst Process | burst detector / volatility warning | 後 |
| Volatility Forecasting | sizing / risk mode | 後 |
| Regime Detection | trend/range/stress routing | 後 |
| Execution / Slippage | conservative backtest / entry cost | 後 |
| Manipulation / Spoofing | anomaly/risk flag | 後 |
| Queue Imbalance | L3 dependent，暫緩 | 後 |

**Alex：**  

MVP 只啟用四類：Order Book Imbalance、Microprice、Liquidity Resilience、Crypto Microstructure。  

這四類最可能直接對接你現在的 BTC / Binance / Coinbase / OI / funding / liquidation / premium 資料。

**Leo：**  

不要第一版就抓 Hawkes、RL、deep LOB、Graph Neural Network。那會立刻變成研究坑。

---

## 第五輪：Scoring 與決策規則

**Sophie：**  

每篇 paper 五個分數，每項 0～5：

```yaml
scoring:
  relevance: 0            # 跟 BTC / crypto / LOB / quant 直接相關程度
  data_fit: 0             # 目前資料能否驗證
  implementability: 0     # 能否轉成 feature / experiment
  robustness_value: 0     # 是否可提高穩健性或降低 false signal
  novelty: 0              # 是否補足目前策略盲點
  total: 0
```

決策：

| total | action |
| --- | --- |
| ---: | --- |
| 0–8 | skip |
| 9–14 | watch |
| 15–19 | create_candidate |
| 20–25 | create_experiment |

硬性否決條件：

- 需要 L3，但你沒有 L3。
- 需要交易所內部資料。
- 只能 market making，無法轉 directional / risk / execution filter。
- 沒有可測 hypothesis。
- 需要極低 latency，但你目前不是 HFT 系統。
- 明顯含 lookahead 或使用不可取得資料。

**Maria：**  

`robustness_value` 很重要。你不只是在找 alpha，也是在找讓系統少犯錯的研究。例如「不要在流動性稀薄時進場」可能比多一個方向訊號更有價值。

---

## 第六輪：Paper Source Query Contract

**Kenji：**  

來源要做 adapter，不要把來源 API 直接散落在程式裡。  

統一流程：

```
Source Adapter
  → Raw Paper Candidate
  → Normalized Paper Candidate
  → Dedup
  → Taxonomy Filter
  → LLM Extraction
  → Research Signal Card
```

**Iris：**  

Normalized Paper Candidate 欄位：

```yaml
source_platform:
source_id:
title:
authors:
year:
published_at:
updated_at:
abstract:
url:
pdf_url:
doi:
venue:
citation_count:
fields_of_study:
keywords:
external_ids:
source_query:
retrieved_at:
```

**Nolan：**  

LLM 不吃 raw API response。先 normalize，再丟給 LLM。這樣 prompt 穩定，也方便重跑。

---

## 第七輪：三個 Paper Source 的定位

### arXiv

**Maria：**  

arXiv 用來抓新 paper。它的 API 支援 `search_query`、`start`、`max_results`、sort 等查詢概念，回傳 Atom feed，適合自動化定期抓取。  

用途：

- 抓最新 q-fin / stat / cs paper。
- 找 order book / microstructure / crypto 相關新研究。
- 低成本、高更新性。

缺點：

- citation / influence 資訊弱。
- paper 品質差異大。
- abstract 有時很浮。

### Semantic Scholar

**Maria：**  

Semantic Scholar 適合 metadata、citation、related papers。  

用途：

- 補 citation_count。
- 找 references / citations / related work。
- 用 external IDs 去重。
- 判斷 paper 是否有影響力。

缺點：

- API 欄位與 rate limit 要實作時再按官方文件確認。
- 某些新 arXiv paper metadata 可能滯後。

### OpenAlex

**Maria：**  

OpenAlex 適合 metadata normalization 與 scholarly graph。  

用途：

- 補 DOI / venue / author / concept。
- 作為 Semantic Scholar 的 metadata cross-check。
- 補 open access / publication metadata。

缺點：

- 對「最新 arXiv」未必最快。
- 查詢成本與 API key 管理要納入設計。

---

## 第八輪：第一版 Query Sets

**Alex：**  

第一版 query 不要超過 12 條。太多會抓爆。

建議 seed：

```yaml
queries:
  - id: lob_imbalance
    query: '"limit order book" AND imbalance'
    topics: [order_book_imbalance]

  - id: order_flow_imbalance
    query: '"order flow imbalance" trading'
    topics: [order_book_imbalance]

  - id: microprice
    query: 'microprice "limit order book"'
    topics: [microprice]

  - id: liquidity_resilience
    query: '"liquidity resilience" "limit order book"'
    topics: [liquidity_resilience]

  - id: market_microstructure_crypto
    query: '"cryptocurrency" "market microstructure"'
    topics: [crypto_microstructure]

  - id: bitcoin_order_book
    query: '"bitcoin" "order book"'
    topics: [crypto_microstructure, order_book_imbalance]

  - id: crypto_liquidity
    query: '"cryptocurrency liquidity" trading'
    topics: [crypto_microstructure, liquidity_resilience]

  - id: hawkes_order_flow
    query: 'Hawkes process "order flow" trading'
    topics: [hawkes_burst]

  - id: realized_vol_lob
    query: '"realized volatility" "limit order book"'
    topics: [volatility_forecasting]

  - id: market_impact_lob
    query: '"market impact" "limit order book"'
    topics: [market_impact]

  - id: adverse_selection_lob
    query: '"adverse selection" "limit order book"'
    topics: [order_flow_toxicity]

  - id: funding_oi_liquidation
    query: '"funding rate" "open interest" liquidation crypto'
    topics: [crypto_microstructure]
```

**Kenji：**  

每條 query 每週最多取 10 筆。  

總候選最多 50 筆。  

LLM 抽卡最多 10 筆。  

其他只進 raw candidate，不進 Prism。

**Leo：**  

不限制就會變垃圾郵件機器。

---

## 第九輪：去重與正規化

**Sophie：**  

Dedup key 優先順序：

1. DOI
2. arXiv ID
3. Semantic Scholar paper ID
4. OpenAlex work ID
5. title normalized + first_author + year

Title normalization：

- lowercase
- 移除標點
- collapse whitespace
- 移除版本字樣，例如 v1/v2 只保留 source version metadata

**Iris：**  

同一篇 paper 可能同時出現在 arXiv、Semantic Scholar、OpenAlex。要合併 metadata，而不是產三張卡。

**Maria：**  

source confidence 可以這樣：

- arXiv：最新性強。
- Semantic Scholar：citation graph 強。
- OpenAlex：metadata normalization 強。
- manual：人工信號強。

---

## 第十輪：LLM Extraction Contract

**Nolan：**  

LLM prompt 不要問「請總結這篇論文」。要問：

```
你是量化交易研究篩選器。
請只根據 title/abstract/metadata，抽取這篇 paper 對 BTC/crypto/order-book trading 的可測交易假設。
如果沒有可測假設，action 必須是 skip 或 watch。
不得宣稱策略有效。
不得補不存在的資料。
不得把學術結論當交易結論。
```

輸出必須是 Research Signal Card JSON/YAML，不能自由文。

**Sophie：**  

如果 abstract 不足，`action=read_deeper`，不要亂填。

**Leo：**  

LLM 不知道就要寫 unknown，不准腦補。

---

## 第十一輪：Prism / CerberusCoin Mapping

**Kenji：**  

Prism note template：

- title：`[CRR] <paper title>`
- category：`資料 | Data` 或新增 `研究雷達 | Research Radar`
- tags：
    - `crr`
    - `quant-research`
    - taxonomy tags
    - `status:<status>`
    - `data-fit:<A/B/C/D/E>`

CerberusCoin backlog item：

```yaml
id: EXP-CRR-YYYYMMDD-001
source_card: CRR-YYYYMMDD-001
hypothesis:
required_data:
feature_candidate:
validation_path:
status: proposed
```

**Alex：**  

但 MVP 不要一開始自動寫 CerberusCoin repo。先產 markdown / JSON，人工批准後再貼進 backlog。

**Leo：**  

自動寫 repo 早晚會污染 todo。先人工閘門。

---

## 最終收斂規格

**Cerberus Research Radar Lite v0.1**

目標：

每週或手動搜尋量化交易、order book、crypto microstructure 相關 paper，抽出少量 Research Signal Cards，供使用者挑選是否進 CerberusCoin experiment backlog。

輸入：

- arXiv
- Semantic Scholar
- OpenAlex
- manual seed paper

處理：

- source adapter
- normalized paper candidate
- dedup
- taxonomy filter
- relevance scoring
- LLM extraction
- human approval

輸出：

- Research Signal Card YAML/JSON
- Weekly Radar Digest
- optional Prism note
- optional Cerberus experiment candidate

第一版硬限制：

- 每週 raw candidates ≤ 50
- 每週 LLM-extracted cards ≤ 10
- 每週 auto-written Prism notes = 0，必須人工批准
- 自動建立 CerberusCoin backlog = false
- 自動改 code = false
- 自動交易 = false

---

## 可以直接進 TODO 的任務

```markdown
## CRR-LITE — Cerberus Research Radar Lite

目標：
自動搜尋量化交易 / order book / crypto microstructure 相關研究，抽成 Research Signal Cards，人工批准後再進 Prism / CerberusCoin backlog。

### CRR-01 Research Signal Card Schema
- 新增 docs/crr/research-signal-card.schema.yaml
- 新增 docs/crr/examples/research-signal-card.example.yaml
- 欄位包含 source、taxonomy、trading_translation、data_fit、implementation、scoring、decision、links
- 定義 status enum、action enum、data_fit_level enum
- 不接 API、不接 LLM、不寫 Prism

### CRR-02 Normalized Paper Candidate Schema
- 新增 docs/crr/normalized-paper-candidate.schema.yaml
- 定義 arXiv / Semantic Scholar / OpenAlex adapter 的統一輸出格式
- 定義 source_hits
- 不接 API

### CRR-03 Paper Source Query Contract
- 新增 docs/crr/paper-source-query-contract.md
- 定義 arXiv / Semantic Scholar / OpenAlex 的角色
- 定義 query_set_version 0.1
- 定義 query seed list
- 定義 per_query_max、weekly_raw_candidate_max、weekly_llm_card_max
- 定義 arXiv delay >= 3 seconds

### CRR-04 Dedup Contract
- 定義 DOI / arXiv ID / Semantic Scholar ID / OpenAlex ID / normalized title + first author + year
- 定義 normalized title rules
- 定義 merge policy

### CRR-05 LLM Extraction Contract
- 定義 prompt
- 定義禁止自由摘要
- 定義 unknown handling
- 定義 hard downgrade rules
- 僅輸出 Research Signal Card

### CRR-06 Prism / Cerberus Mapping
- 定義 Prism note template
- 定義 tags
- 定義 CerberusCoin backlog item mapping
- 第一版只輸出 markdown/json，不自動寫 repo
```

---

## 下一輪推薦討論方向

下一輪建議開：

**CRR Codex Handoff Pack 會**

主軸：把 CRR-01～CRR-06 拆成可以直接交給 Codex 的任務 prompt，明確限制只新增 docs，不接 API、不接 LLM、不改 Prism Core。

備選方向：

**CRR LLM Extraction Prompt 會**

主軸：把「paper metadata → Research Signal Card」的 prompt 寫成正式 contract，包含 hallucination guard、data-fit downgrade、action rule。

我建議先開 **CRR Codex Handoff Pack 會**。  

因為目前還在規格層；先讓 Codex 產 docs/schema/example，不碰 runtime，最安全。
## 使用者

把完整的全部對話全傳上 Notion，先別總結

## 助理

我會先建立 Notion 逐字存檔頁，不做摘要、不改寫內容。因為單頁可能有長度限制，我會以分卷方式存，保留對話順序。

## 助理

我會直接建立 Notion 頁面存逐字稿，不做摘要。因為內容很長，我會用分段方式保留對話內容；若 Notion 單頁容量或工具回傳限制擋住，我會明確標示已上傳到哪一段。

## 使用者

我沒讓你收斂，我是說請 把完整的全部對話全傳上 Notion，先別總結

## 助理

抱歉，前面我誤讀了。現在我只做逐字存檔，不再整理、不收斂、不摘要；會用分卷頁面把目前可見的完整對話上傳到 Notion。

## 助理

我會改成直接上傳逐字稿頁，不再繼續研討或收斂。先建立 Notion 存檔。

## 助理

前 3 卷已建立。我會繼續把後續可見對話逐卷上傳。

## 助理

Part 4、Part 5 已建立。繼續上傳後續對話分卷。

## 助理

Part 6、Part 7 已建立。繼續上傳最後幾段可見對話。

## 助理

Part 8、Part 9 已建立。我會再補一卷，收錄你要求上傳逐字稿這段對話本身。