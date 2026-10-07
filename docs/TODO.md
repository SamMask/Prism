# Prism Active TODO

本檔只保留 active roadmap 的工單看板、deferred 候選與下一步入口。

- 工單完整規格：`docs/WORK_ORDERS.md`（本檔只記狀態，規格不在這裡重複）。
- 完成紀錄、舊 phase 與長版 changelog：`docs/development-history/`。2026-10-06 瘦身移出的內容見 `docs/development-history/todo-handoff-archive-20261006.md`。

閱讀方式：

- 狀態欄位固定使用：`Todo` / `Doing` / `Blocked` / `Review` / `Done`。只有正在施工的單一工單標 `Doing`。
- `Todo` = 已規劃、可以直接施工；`Blocked` = 需要決策、證據或觸發條件，啟動條件寫在 `docs/WORK_ORDERS.md`。
- 優先級：**P0** 現在做；**P1** 下一輪；**P2** 稍後；**P3** 目前不建議；**Future** 證據不足。

---

## Current Truth（2026-10-06）

- Go primary 是唯一 runtime owner；Python Flask backend source 已於 T053 移除（完整紀錄：`docs/development-history/go-primary-runtime-completion-20260617.md`）。Schema 為 migration v17。
- 最新 release 為 V2.7.0（2026-10-07，tag 對齊 `a478a8b`），同一版已部署到 Pi。
- Windows portable：`Prism.exe` GUI app + WebView2 + same-process Go runtime，資料在 exe 同層 `PrismData\`；installer/updater 仍 deferred。
- Pi：live root `/home/mask0709/prism`，`prism-go-primary.service` 只監聽 5004，經 Caddy 對外。Pi delivery 與 GitHub release 是兩條流程，Pi 上線依 `DEPLOY-PI.md` 另開 gate。
- Prism 沒有內建 auth/token layer；安全邊界是 localhost、trusted LAN、VPN、SSH tunnel，或外部 auth 保護的 reverse proxy。
- 2026-10-06 全專案審查：`docs/PROJECT_OPTIMIZATION_REVIEW_2026-10-06.md`。所有 findings 已轉為下方工單 PRISM-OPT-15～51；08-12 審查遺留的 P2/P3 已併入本看板。
- 不得因審查建議自動擴大 scope 到 AI、semantic search、內建 auth、cloud sync、schema 版本升級、release 或 Pi deploy；需要時另開決策關卡。

---

## Active Roadmap — PROJECT-OPTIMIZATION-ROADMAP-2026-10-06

證據在審查報告，規格在 `docs/WORK_ORDERS.md`。一次只 promote 一張工單為 `Doing`；每張工單都可以單獨 branch、commit、review、rollback。

固定邊界：

- 不升 schema 版本、不新增 dependency；API 只做 additive 變更。
- 不碰正式 `knowledge.db`；runtime 驗證一律使用隔離 data-dir 與 fresh DB。
- UI 工單需要 desktop + 390px 的實際瀏覽器驗證；行為宣稱需要可執行測試（Go test、HTTP 或 e2e），不能只靠 source 或文件字串斷言。
- 任何工單若擴散到 schema、資料修復、release 或 Pi delivery，立即停止並另開 decision gate。

### P0 — 信任修正

| 工單 | 摘要 | 狀態 | 依賴 | Finding |
|---|---|---|---|---|
| PRISM-OPT-15 | `Download .db` 改為一致快照（重用 `writeConsistentDBBackup`） | Done | — | OPS-01 |
| PRISM-OPT-16 | 附件檢視改為純文字輸出；附件項目可用鍵盤操作 | Done | — | TECH-07 |
| PRISM-OPT-17 | Header 的 New 與搜尋在任何 route 都導向 Library 並生效 | Done | — | UX-01 |
| PRISM-OPT-18 | CJK 子字串搜尋 fallback；palette 對 CJK 輸入 2 字即觸發 | Done | — | FEAT-01 |
| PRISM-OPT-19 | 停止新的長文拆分；已拆分筆記存檔前先把全文收回 DB | Done | — | FEAT-02 |
| PRISM-OPT-60 | 修正 OPT-19 回歸：restore 前先保存分歧內容；共用檔判斷改用 `os.SameFile` | Done | 19 | OPT-20 規劃追蹤 |

完成證據（2026-10-06）：

- `PRISM-OPT-15`（本機驗證；未發版、未部署 Pi）：
  - `handleExportDB`（`go-shadow/export.go`）改為先用 `writeConsistentDBBackup` 寫到暫存檔再送出，結束後刪除暫存檔，寫法比照 `handleBackupDownload`。API 路徑、檔名格式、Content-Type、gate 都不變。
  - 新增 Go 測試 `TestExportDBIncludesUncheckpointedWALWrite`（CJK 資料）、`TestExportDBFreshInitDBIncludesSchema`、`TestExportDBGates`；下載 helper 會斷言暫存目錄沒有殘留。前兩個測試在舊的 `http.ServeFile` 實作上失敗，修正後通過。
  - 獨立驗收（prism-verifier）在隔離 data-dir 的 fresh runtime 實測 HTTP：
    - fresh DB 下載檔有 `Notes` 表，integrity ok；同一時間 live 主檔本身沒有 `Notes`。
    - 新增 CJK 筆記後（尚未 checkpoint）立刻下載，下載檔含這筆。
    - 暫存目錄沒有殘留檔。
  - 驗證：`go vet` 通過、`go test ./...` ok、pytest 402 passed、`git diff --check` 通過。
- `PRISM-OPT-16`（本機驗證；未發版、未部署 Pi）：
  - `handleLoadAttachment`（`useNoteAttachments.ts`）改用 DOM API 建立 popup：`<pre>` 加上 `textContent`，不再以 `document.write` 插入附件內容。auto-extracted 載入流程沒有改。
  - `AttachmentPanel.tsx` 的每個附件列改為兩個原生按鈕：開啟按鈕，以及帶 `aria-label` 的刪除按鈕。刪除按鈕在 hover、鍵盤 focus 時顯示，在不支援 hover 的觸控裝置上一直顯示。
  - 回歸測試在 `tests/test_project_optimization_p0_frontend.py`，共兩個 source-lock 測試：
    - 用 regex 禁止 HTML sink：`.write(`、`.writeln(`、`innerHTML`、`srcdoc`、`createContextualFragment` 等，並要求以 `textContent` 寫入內容。
    - 檢查附件項目是原生按鈕，刪除按鈕有 `aria-label` 和 focus 顯示。
    - 兩個測試在 HEAD 原始碼上都失敗，`doc.write` 等突變也都會被抓到。
  - 瀏覽器實測：使用隔離的 fresh runtime，附件內容含 `<script>`、`</pre><img onerror>` 與 CJK。
    - Tab 鍵可以把 focus 移到開啟按鈕，focus ring 可見，刪除按鈕同時出現。按 Enter 會讀取附件。
    - popup 內只有一個 `<pre>`，原樣顯示 payload 文字，不會產生 script、img 元素。
    - 390px 寬度下刪除按鈕一直可見，沒有橫向捲動。刪除時會跳出確認，按取消後附件保留。
  - 獨立驗收（prism-verifier）在 headless Chromium 開真的 popup 對照：HEAD 版本被注入（title 變成 `PWNED`、script 被執行），新版本沒有。
  - 驗證：`npm run build` 通過、pytest 404 passed、`git diff --check` 通過。
  - 尚未驗證：Firefox／Safari，以及 WebView2 desktop shell 中真正開出的 popup。
- `PRISM-OPT-17`（本機驗證；未發版、未部署 Pi）：
  - `Header.tsx` 的 New（新增的 `handleAddNote`）與 `handleSearchSubmit`：不在首頁時先 `navigate('/')`，寫法比照 `handleOpenReadingWorkspace`。appStore、HomePage、API、i18n 都沒有改。
  - 回歸測試 `test_header_new_note_and_search_submit_navigate_home_from_other_routes`（source-lock）：在 HEAD 版本上失敗；拿掉任何一個 handler 的 navigate 也會失敗。
  - 瀏覽器 smoke，隔離 fresh runtime，主代理與 prism-verifier 各跑一次：
    - desktop：從 `/settings`、`/prompt-builder` 按 New，都會導到 Library 並立即開啟 New note。從這兩頁搜尋，會導到 Library 並只顯示符合的筆記。
    - 不再出現稍後才彈出的編輯器；console 沒有錯誤。
    - verifier 用 HEAD 版前端重現了原始 bug：URL 停在原頁、編輯器沒開，回到 Home 後編輯器自己彈出。
  - 390px：
    - 從兩個 route 按 New 都正常，沒有橫向捲動。
    - 「從這兩頁搜尋」不適用：md 以下 Header 搜尋框隱藏（`hidden md:block`），command palette 按鈕只在 `lg` 以上顯示。手機只能在 Library 頁內的 `mobile-search-form` 搜尋。非首頁在手機上沒有搜尋入口，這是既有的 UX 缺口，不在本工單範圍。
  - 已知小瑕疵：從非首頁搜尋會送出兩次相同的 `/api/notes?q=` 請求（`setSearchQuery` 一次、HomePage 掛載一次）。store 的 request sequence 會丟掉舊的回應，結果正確；要消除就得改 appStore，不在範圍內。
  - 驗證：`npm run build` 通過、pytest 405 passed、`git diff --check` 通過。
- `PRISM-OPT-18`（本機驗證；未發版、未部署 Pi）：
  - `buildNotesSearchClause`（`go-shadow/notes_search.go`）：查詢 token 含 Han、Hiragana 或 Katakana 時，多一個 OR 分支，對每個 token 做 title／content 的 `LIKE`，token 之間 AND。純英文查詢產生的 SQL 與參數和修正前逐字相同：verifier 比對了 10 種非 CJK 查詢，包含韓文與全形字。FTS schema、tokenizer、migration、附件掃描上限都沒有改。
  - Command Palette：CJK 輸入 2 字就查詢 server；英文門檻維持 3。
  - 測試：
    - `TestNotesSearchFindsCJKSubstringsInTitleAndContent` 經 HTTP handler 執行，有 9 個案例：工程、角色設定、夜景、廣角、ポートレート、多 token AND、混合的「prompt 工程」，以及兩個應該 0 筆的負面案例。7 個正面案例在 HEAD 上失敗。
    - `TestNotesSearchClauseAddsCJKBranchOnlyForCJKQueries`。
    - pytest 鎖定 palette 的門檻。
  - 隔離 runtime 實測（prism-verifier）：
    - HTTP：工程、角色設定、夜景、カメラ、ポートレート都命中；英文 `prom` 的前綴比對照舊；「城市 工程」為 0 筆，AND 語意正確。
    - Chromium 中的 palette：輸入「夜」不送出請求，「夜景」會送出並出現結果；"ab" 不送出、"abc" 會送出；console 沒有錯誤。
  - 效能（`go test -run '^$' -bench BenchmarkNotesSearchCJK -benchtime 20x .`，fresh schema，每筆約 1,800 個 CJK 字）：
    - 1,000 筆約 30–34 ms/op。修正前只走 FTS，約 4.5 ms，但命中 0 筆。
    - 10,000 筆約 1.0–1.14 s/op。handler 的 COUNT 與列表各掃一次全文，單一 LIKE COUNT 約 378 ms。這組數字是 PRISM-OPT-45（trigram 索引）的判斷依據。
  - 已知語意與範圍：
    - 查詢只要含 CJK token，裡面的 ASCII token 也改用子字串比對，例如「rom 工程」會命中 prompt。
    - 韓文（Hangul）與全形英數字的行為和修正前相同。
  - 驗證：`go vet` 通過、`go test ./...` ok、`npm run build` 通過、pytest 406 passed、`git diff --check` 通過。
- `PRISM-OPT-19`（本機驗證；未發版、未部署 Pi）：
  - 流程：prism-critical 兩段式施工（先出計畫，主代理確認後才實作），prism-verifier 獨立驗收。
  - 前端：
    - `useNoteForm.ts`：
      - 移除存檔後的 `separateContent`。
      - 已拆分筆記先 `restore`、再 PUT；restore 回 404 時直接 PUT。
      - 全文載入中或載入失敗時封鎖存檔（重用既有的 `loadFullFailed` 與 `common.loading`，沒有新增 i18n key）。
      - 加入 `savingRef` 防止重複送出。
    - `useNoteAttachments.ts` 提供 `FullContentState`：附件清單 405 視為 `none`，其他失敗視為 `failed`。
    - 刪除四語中已無人使用的 `editor.form.separationFailed`。
  - 後端：刻意偏離規格的「不要修改 restore」，只為了安全，API 形狀、狀態碼與回應都不變。
    - `restoreSeparatedContent` 在其他筆記的附件列仍引用同一個 `docs/notes` 檔時，保留該檔案不刪。
    - 理由：OPT-19 讓 restore 成為每次存檔都會走的路徑；舊資料若有共用檔，另一則筆記會失去全文（規劃時已用 probe 重現）。
  - 測試：
    - Go：`TestRestoreSeparatedContentKeepsFileSharedWithAnotherNote` 在 HEAD 上失敗。另有兩個契約鎖定測試，鎖住 restore 不寫歷史、PUT 會快照全文、缺檔時 restore 回 404 且不改資料。
    - pytest：三個 source-lock 測試，加上改寫的 T046 測試，在 HEAD 上都失敗。
  - 隔離 runtime 的 headless Chromium 流程，實作代理與 verifier 各自撰寫腳本：
    - 新建 6,000 字筆記：沒有 `/separate` 請求，GET 回傳全文，沒有附件。
    - 已拆分筆記改成 34 字：請求順序是 `restore` → PUT，重開顯示 34 字，附件列與檔案已移除。
    - 版本歷史只有 1 筆，內容等於完整原文。
    - 全文載入失敗時，Save 按鈕與 Ctrl+S 都不會送出請求，DB 不變。
    - restore 成功但 PUT 失敗時，重試只送 PUT。一般筆記不受影響。
    - 結果：實作代理 26/26（HEAD 9/26）；verifier 20/20，HEAD 重現原 bug。
  - 回滾演練 6/6：
    - 用 HEAD 版程式開修正後的資料夾，相容。
    - 流程前用 full-snapshot 建立的快照可以當還原點。
  - 已知邊角，已寫入 PRISM-OPT-20 的規格：
    - 超過 1 MiB 的已拆分筆記無法編輯。
    - 載入全文之後、存檔之前檔案消失，會留下懸空的 auto 列，之後無法存檔。
    - 共用檔防護有大小寫之分。
    - 若某個環境開了 notes-write 卻沒開 attachment-write，已拆分筆記不會被保護；所有正式設定都兩者同開。
  - 驗證：`npm run build` 通過、`go vet` 通過、`go test ./...` ok、pytest 409 passed、`git diff --check` 通過。
- `PRISM-OPT-60`（本機驗證；未發版、未部署 Pi）：修正 PRISM-OPT-19 的回歸，在 PRISM-OPT-20 規劃時被 probe 發現。
  - 問題：
    - 在 OPT-19 之前被使用者改短的已拆分筆記，透過編輯器存檔時，`restore` 會用舊檔蓋掉 DB 中的短版，而且不留歷史。
    - 共用檔判斷有大小寫之分，Windows 上大小寫不同的路徑會誤刪另一則筆記的檔案。
  - 修正（`restoreSeparatedContent`，API 形狀、狀態碼與訊息都不變）：
    - 附件列查詢、讀檔、刪列、寫歷史、更新內容都在同一個交易內。刪列加上 `note_id` 與 `is_auto_extracted` 條件，必須剛好刪到 1 列，否則 rollback 並回既有的 404，防止並發的 restore 寫入過期內容。
    - DB 內容既不是全文、也不是自動預覽時，先寫入 `Note_History`（`還原前自動備份`）。
      - 自動預覽的定義：拆分橫幅前的內容是檔案的非空**嚴格**前綴，判斷寫成 `isAutoSeparatedPreview`，供 OPT-20 重用。
    - 共用檔判斷改成「排除這一列附件、檢查其餘所有列」，含同一筆記的一般附件列（`noteFileSharedByOtherRow`）：
      - 路徑字串相同就視為共用。
      - 只差大小寫時用 `os.SameFile` 比對；無法確認時保守地視為共用。
      - 只對大小寫變體做檔案系統呼叫，避免持有寫鎖時逐列 stat。verifier 量測舊寫法每列約 1.3–4.4 ms。
  - 測試（Go，經 HTTP handler 或直接呼叫 helper）：
    - 在 HEAD 或前一版上失敗的有：分歧內容寫入歷史、大小寫共用檔保留、同一筆記一般附件列保住檔案、刪列 0 筆時中止且沒有任何副作用（用 `RAISE(IGNORE)` trigger 模擬）、無法確認的大小寫變體視為共用、嚴格前綴的邊界案例。
    - CRLF 預覽不寫歷史。OPT-19 的三個契約測試沒有修改，仍然通過。
  - 獨立驗收（prism-verifier）：
    - 隔離 runtime 的 HTTP 實測：分歧筆記 restore 後，歷史留下短版；一般拆分筆記的歷史為 0 筆；大小寫變體的檔案會保留到最後一個引用被收回。
    - 另以 probe 確認：被判為預覽時，內容一定能從全文重建，不會丟失獨有的使用者文字。
  - 驗收後依 Codex astra 對 OPT-20 計畫的審查意見，再補上四項：嚴格前綴、只排除單一附件列、無法確認視為共用、交易內再驗證。四項都有 fail-before 證據，由主代理讀回並確認。
  - 驗證：`go vet` 通過、`go test ./...` ok、pytest 409 passed、`git diff --check` 通過。
- `PRISM-OPT-20`（本機驗證；未發版、未部署 Pi；**尚未在正式資料上執行**）：
  - 流程：
    - prism-critical 兩段式施工，計畫改了三版。
    - Codex astra（`gpt-6-astra`，唯讀）審過三輪計畫和一輪實際改動：
      - v1、v2 的結論都是「需修改」，v3 剩兩項，以實作條件 A1、A2 的形式納入。
      - 實際改動的審查發現兩項，已修正：隔離區改成原子、不覆蓋的搬移；full snapshot 在 panic 時也會解鎖。
      - astra 有一項意見被主代理以程式證據駁回：維護後已開啟的編輯器可以照常存檔，因為 restore 回 404 後仍會 PUT。astra 第 3 輪已撤回。
    - prism-verifier 獨立驗收。
  - 功能：
    - 新端點 `POST /api/system/inline-separated-notes`（additive），前端在 Maintenance 新增「合併長文回筆記」卡片，四語 i18n。
    - 預設只做 dry-run，只有明確送 `"dry_run": false` 才執行；重複 key、超過大小上限、型別不符都回 400。只接受直接連線的 loopback peer，並受 server-system gate 保護。
    - 執行時：
      - 在 `backups/separated-notes-<ts>/` 建立還原點（`writeConsistentDBBackup`，含 WAL 中的資料）、不可變的 `plan.json`／`moves.tsv`，以及 `result.json`。
      - 逐筆交易處理，先 commit DB 再搬檔。檔案移入隔離區，不刪除，也不覆蓋既有檔案。
      - `updated_at` 不變。
    - 處理方式：
      - **merge**（一般已拆分筆記）：全文寫回 `Notes.content`。
      - **D2**（內容分歧的筆記）：以 DB 為準，附件全文寫入 `Note_History`。舊全文若引用了沒有其他保護的本機媒體，就只列出、不處理；這項判斷在交易內以當下的 DB 重新驗證。
      - 以下情況只列出、不處理：缺檔、懸空列、超過 1 MiB、預覽不符、路徑無效或非標準、symlink／junction、共用檔（含大小寫變體、硬連結）、同一筆記有多個 auto 列、找不到筆記、孤兒檔、媒體未受保護、檔案身分無法確認。
    - 並發：`server.noteFilesMu`，與 restore、separate、複製、刪除、附件上傳與刪除、匯入、媒體清理、full snapshot 的暫存複製共用。讀 request body 與寫大小沒有上限的回應時，不持有這把鎖。
      - restore 的第一個語句改成只刪一列的 `DELETE … RETURNING`，避免 `SQLITE_BUSY_SNAPSHOT`。
      - restore 的共用檔判斷改以開啟的 handle 取得檔案身分。保留 EqualFold 預篩，所以不同檔名的別名（硬連結、8.3 短檔名）在每次存檔的路徑上偵測不到；Prism 沒有任何路徑會產生這種列。維護動作在搬檔前會比對所有列的檔案身分，不做預篩。
  - 測試：
    - Go：新增 `notes_inline_test.go`，共 G1–G25 加 G12b，以及兩條補測。
    - fail-before：14 條 HTTP 測試在 HEAD 上回 404；鎖與 restore 的測試在 HEAD 上失敗。
    - mutation：16 項，拿掉任一項防護，對應的測試都會轉紅。verifier 另外自己抽查 3 項。
    - pytest：3 條治理檢查，readonly-promotion-gate 的 discard 清單加入新路由。
  - 隔離 runtime：
    - 實作代理：browser smoke 21/21，涵蓋 1280 與 390 寬度、預覽、確認、成功、部分失敗、「結果未知」，以及「編輯器開著時執行維護」的 merge 與 D2。
    - 實作代理：回滾演練 22/22，涵蓋完整回滾、執行到一半被 kill、回滾被中斷後重跑、殘留 WAL、名稱衝突、缺少來源、managed restore 驗證失敗。回滾不需要 Python。
    - verifier：HTTP 檢查與 headless 瀏覽器（1280、390）都通過。
  - 效能（隔離資料：1,000 篇筆記、230 篇已拆分、300 個文字附件）：
    - 合併 230 篇約 1.2 s。dry-run 第一次 9.4 s（剛寫入的檔案，持鎖期間存已拆分的筆記要等），之後約 1 s。
    - 尾段詞從 0/29 變成 29/29 找得到。但搜尋仍然 partial，因為 300 個文字附件本身就超過掃描上限；已記到 PRISM-OPT-47 作為啟動依據。
  - 已知、不阻擋：只支援單一行程；搬檔被鎖住時筆記仍會合併，原檔變成孤兒檔並列出；D2 的歷史 `diff_summary` 是固定中文；在正式資料上執行前建議先下載 full snapshot。
  - 驗證：`go vet` 通過、`go test ./...` ok、`npm run build` 通過、pytest 412 passed、`git diff --check` 通過、鏡像一致。
- `PRISM-OPT-21`（本機驗證；未發版、未部署 Pi）：
  - `useNoteForm.ts`：
    - 拆出 `save({ close })`。`Ctrl+S` 使用 `close: false`；Save 按鈕使用 `close: true`，行為不變。
    - 存檔成功後更新 snapshot，`hasUnsavedChanges` 改成每次 render 重算。
    - 有未存變更時才註冊 `beforeunload`。
  - 新筆記第一次 `Ctrl+S`：
    - 用回傳的 `note_id` 取回筆記，再以 `openEditor(created)` 原地轉成編輯狀態，所以第二次是 PUT。`NoteEditor` 不重新 mount，表單內容與游標都保留。
    - `getNote` 失敗時退回「存檔並關閉」。
    - 對剛建立的筆記，忽略附件重載造成的 `pending`，避免第二次存檔被擋下。對其他筆記照常保護。
  - 已拆分筆記：OPT-19/60/20 的保護不變（`restore` → PUT → 之後只 PUT；全文載入失敗時擋下存檔）。`restore` 真的成功後，附件面板會在本地移除被伺服器刪掉的 auto 列，規則比照伺服器只刪一列，不重新載入。
  - 驗證：
    - pytest：4 個 source-lock 測試在 HEAD 上都失敗。
    - 實作代理：隔離 runtime 的 headless Chromium，1280 與 390 共 38/38，含拿掉 pending 保護的負對照。
    - prism-verifier 自寫腳本，主腳本 48 項、補充 10 項、反向對照 1 項，全部通過：
      - 新筆記連按兩次 `Ctrl+S` 只產生 1 筆，快速連按也一樣。
      - 有未存變更才跳 `beforeunload`，存檔後就不跳。
      - Save 按鈕仍是存檔並關閉。
      - 已拆分筆記：`restore` → PUT，附件面板同步移除該列；檔案損壞時擋下存檔。
      - `getNote` 回 500 時會退回關閉；tag 與 URL 存檔後不算未存變更。
    - 指令：`npm run build` 通過、pytest 416 passed、`go test ./...` ok、`git diff --check` 通過。
  - 已知：
    - 桌面版（WebView2）關閉視窗時沒有保護，另開 PRISM-OPT-61。
    - PRISM-OPT-59 若要為 `NoteEditor` 加 `key`，必須在「建立後轉為編輯」時保持不變，已寫進 OPT-59 的規格。
- `PRISM-OPT-22`（本機驗證；未發版、未部署 Pi）：
  - 預覽態：
    - heading 顯示「預覽筆記」，新增 i18n key `editor.toolbar.previewNote`，四語：預覽筆記／Preview note／ノートをプレビュー／노트 미리보기。
    - 標題以 `<h3>` 呈現，不渲染 input，也沒有 autofocus。
    - 開啟時 focus 落在 dialog 容器（`tabIndex={-1}`）。
    - Save 只在 Edit 模式或有未存變更時顯示。
  - 「Edit this block」、`cardOpenMode`、ReadingView、卡片的點擊目標都沒有改；`useNoteForm` 沒有 diff，OPT-21 與 OPT-19/60/20 的存檔行為不變。
  - 驗證：
    - pytest 的 source-lock 測試在 HEAD 上失敗。
    - 實作代理：隔離 runtime 在 1280 與 390 跑 17 項，全部通過。
    - prism-verifier：自寫 Playwright，涵蓋 1280／390 × zh-TW／en，124 項 0 失敗。
      - 預覽態沒有 focus 的 input，focus 在 dialog 內；按鍵不會改到標題，DOM 與 GET 都確認過。
      - Edit 與 Preview 來回切換正常；「Edit this block」後 Save 出現並能存檔。
      - 預覽態按 `Ctrl+S` 存檔並留在編輯器。
      - edit 模式開啟與新增筆記的行為不變；Escape 與未存確認正常。
      - 反向對照：HEAD 版前端同一支腳本失敗，打字會改到標題。
    - 指令：`npm run build` 通過、pytest 417 passed、`git diff --check` 通過。
  - 已知：`Modal` 沒有 `role="dialog"` 與 focus trap，Tab 可以離開對話框。另開 PRISM-OPT-62。
- `PRISM-OPT-59`（本機驗證；未發版、未部署 Pi）：
  - **重現結果（HEAD，隔離 runtime 的 headless Chromium，1280 與 390 一致）**：
    - 前提：筆記 A 在編輯器中、有未存修改時，`Ctrl+K` 開出的 palette 在編輯器 modal 的**下方**（兩者都是 z-50，modal 用 portal 蓋在上面）。畫面上看不到，但在預覽模式（預設的 cardOpenMode）下 palette 會拿到 focus。
    - 預覽模式：`Ctrl+K` → 輸入 B 的標題 → Enter → 切到 Edit → `Ctrl+S`，結果 **B 被寫成 A 的標題加上剛編輯的內容**，B 的歷史多一筆舊內容，A 不變。
    - 編輯模式：要按 Tab 數十次才進得了 palette，選 B 後結果相同。
    - palette 的「New note」，以及用 Tab 移到背景 Header 的「New note」再按 Enter：用 A 的表單**新建一筆**，A 的編輯沒有存回 A。
    - B 是已拆分筆記時：A 的表單內容被 B 的全文蓋掉，A 的編輯無聲消失。
  - 修正：
    - `appStore.openEditor` 在編輯器已開啟時是 no-op，除非帶了新增的 `inPlace` 選項。只有 OPT-21 的「建立後轉為編輯」使用 `inPlace`。
    - 編輯器開著時 `Ctrl+K` 不開 palette；在編輯器內 `Ctrl+K` 仍是插入連結。
    - `Layout` 在路由離開 `/` 時清掉編輯器的開啟狀態，否則按瀏覽器上一頁之後，guard 會一直擋住後續開啟。
      - 不放在 HomePage 的 unmount cleanup：React StrictMode 會在開發模式下假 unmount，把 OPT-17「從 Settings 按 New」剛開的編輯器關掉，已在 vite dev 實測。
  - 驗證：
    - pytest 的 source-lock 測試在 HEAD 上失敗。
    - 實作代理比較三個 build（HEAD、第一版修正、最終版），1280 與 390：
      - 修正後 A、B 的內容與歷史都正確，B 不變；拆分的 B 不會蓋掉 A 的表單；筆記總數不變。
      - 上一頁之後 palette、開 B、Header New 都正常，回到 `/` 也不再出現舊的 A。
      - OPT-17、21、22 沒有退化。
    - prism-verifier 獨立驗收 (i)(ii)(iii)，並以 HEAD build 重現原 bug：
      - (i) 表單不會存進別則筆記。
      - (ii) 這些路徑不會無聲丟掉 A 的編輯。
      - (iii) OPT-21 原地轉換不會 remount。
      - 上一頁殘留狀態的退化是它發現的，已由上述 `Layout` 修正處理。
    - 指令：`npm run build` 通過、pytest 418 passed、`git diff --check` 通過。
  - 已知、另開工單：
    - 沒有 focus trap 時，Tab 可以移到背景的導覽連結或 palette 按鈕，導覽後編輯內容會消失。PRISM-OPT-62 已提升為 P1。
    - app 內導覽（上一頁、連結）時，未存的編輯仍會消失。另開 PRISM-OPT-63（P1）。
- `PRISM-OPT-61`（本機驗證；未發版、未部署 Pi）：
  - 先做唯讀評估，在 scratch 用原型實測：WebView2 關窗時不會執行頁面的 `beforeunload`（`WM_CLOSE` 到 `WM_DESTROY` 只隔數毫秒）；F5／reload 時 WebView2 會跳出自己的離開提示，OPT-21 的保護在這條路徑有效。go-webview2 沒有關閉攔截點。
  - 實作：
    - `desktop_shell_windows.go` subclass 主視窗，只攔 `WM_SYSCOMMAND`/`SC_CLOSE`。
    - 頁面在有未存變更時，透過 bound `prismDesktopSetUnsaved` 推送在地化提示，shell 直接跳原生 `MessageBoxW`（OK／Cancel，預設 Cancel）。關窗時不必回頭問頁面，所以頁面卡住時仍能關閉。
    - 確認框開著時防止重入；`MessageBoxW` return 後補一個 `Dispatch(func(){})`，讓被 modal loop 吃掉的 tray Quit 能執行。
    - tray Quit（`WM_CLOSE`）不攔。
    - 前端只改 OPT-21 的 beforeunload effect，瀏覽器裡這個函式不存在，所以是 no-op。
    - 沒有新增 dependency，沒有改 tray／單一實例邏輯，也沒有改 API。
  - 驗證：
    - fail-before：Go 判斷函式的表格測試在 HEAD 上無法編譯，pytest source-lock 在 HEAD 上失敗。
    - 實作代理（隔離 data-dir、自訂 mutex、CDP 驅動真實 UI 輸入）：desktop harness 14/14，包含真實 OS 層 Alt+F4；HEAD build 的負對照在關窗時遺失編輯內容。
    - prism-verifier 用真的 desktop exe 加自寫 GUI harness 驗收：
      - 有未存變更時 `SC_CLOSE` 出現 owner 為主視窗的確認框，預設是 Cancel。Cancel 保留內容；OK 關閉，不寫入 DB。
      - 存檔後、改回原樣、reload 之後都直接關閉；reload 證明 Init 會重設殘留的旗標。
      - 有未存變更時 tray Quit 直接結束，`--desktop-self-test` 自行退出。
      - 確認框開著時的重入，以及確認框開著時的 tray Quit 都正確；popup 視窗不會誤清旗標。
      - 瀏覽器的 `beforeunload` 不變，`prismDesktopSetUnsaved` 在瀏覽器中是 undefined。
    - 指令：`go vet`、`go test ./...`、linux/arm64 cross-build（Pi）、`npm run build` 都通過，pytest 419 passed、`git diff --check` 通過。
  - 已知：
    - Windows 登出／關機（`WM_QUERYENDSESSION`）與不加 `/F` 的 `taskkill` 不受保護，與修改前相同。
    - 工作列的「關閉視窗」與實體滑鼠點 X 沒有以實體輸入驗證，但它們都會送同一個 `SC_CLOSE`。
    - `SetWindowLongPtrW` 只存在於 64 位元的 user32；目前只建置 amd64。
    - 實作代理一開始用了固定 debug 埠 9333，該埠屬於使用者本機另一個瀏覽器；它只讀過頁面清單、沒有任何操作，之後改用隨機埠。
- `PRISM-OPT-63`（本機驗證；未發版、未部署 Pi）：
  - 做法：
    - `main.tsx` 從 `BrowserRouter` 改成 data router：`createBrowserRouter([{ path: '*', element: <App /> }])` 加上 `RouterProvider`。這是官方的最小遷移寫法，`App.tsx` 沒有修改。
    - `useNoteForm` 用 `useBlocker` 攔截：只在有未存變更、而且 pathname 會改變時才攔。確認文案與 `handleClose` 共用 `confirmDiscard()`，沒有新增 i18n key。
    - `ConfirmDialog`：新的 confirm 會讓被取代的 pending confirm 以 `false`（取消）resolve。否則導覽確認框開著時按 Escape，會疊出第二個確認框，blocker 會永遠卡在 blocked。
  - 驗證：
    - pytest 的 source-lock 測試在 HEAD 上失敗。
    - 實作代理：隔離 runtime 在 1280 與 390 共 43 項，含 Escape 的邊界案例。
    - prism-verifier 自寫腳本：CUR 1280 與 390 各 32/32，edge 7/7。
      - 有未存變更時按上一頁／下一頁、點側欄連結（鍵盤 Enter 與點擊）都會詢問。取消會留在 `/`，內容保留；確認後才離開，DB 不變。
      - 沒有未存變更、或 `Ctrl+S` 存檔後，照常導覽不詢問。
      - 導覽確認框開著時按 Escape 不會卡住。
      - OPT-17、21、22、59、其他 `confirm()`、`beforeunload` 都沒有退化。verifier 逐一檢查了 13 個 `confirm()` 呼叫端，被取代時回傳 `false` 都不會觸發動作。
      - HEAD 負對照：同樣的操作不詢問，編輯內容遺失。
    - 指令：`npm run build` 通過、pytest 420 passed、`git diff --check` 通過。
  - 已知：
    - data router 讓 main chunk 增加約 14.5 kB（gzip）。
    - 確認框上按 Escape 會變成「放棄並關閉？」確認框，這是既有行為，屬於 PRISM-OPT-62 的範圍。
    - 新 router 沒有在 desktop WebView2 上實測。
- `PRISM-OPT-62`（本機驗證；未發版、未部署 Pi；2026-10-07 由 P2 提升為 P1）：
  - `Modal.tsx` 新增共用 hook `useDialogLayer`：
    - module 層級的 dialog 堆疊；在 window capture 階段快照按鍵當下的最上層。
    - Tab trap 只作用於最上層，Escape 也只交給最上層。
    - 開啟時 focus 移入；關閉時歸還給 opener。opener 是 body、已卸載或 disabled 時，退回下一層 dialog 的面板。
    - opener 只在每次開啟時擷取一次，StrictMode 不會清掉它。
  - 套用範圍：
    - `Modal`：`role="dialog"`、`aria-modal`、`aria-labelledby`。
    - `ConfirmDialog`：`role="alertdialog"`、`aria-labelledby`／`describedby`，並移除它自己的 document Escape listener。OPT-63 的「被取代的 confirm 回 false」保留。
    - `ImageLightbox` 也登記為一層，這是規格範圍外、但修正退回項所必要的改動；只在有圖片時登記。
  - 效果：
    - Tab 無法再到達背景的導覽連結，補上 OPT-59／63 發現的資料遺失路徑。
    - 確認框上按 Escape 只取消該確認框，不會再疊出第二個。
  - 驗證：
    - prism-verifier 第一輪**退回**：lightbox 疊在 ReadingView 或編輯器上時，Tab 被底層 trap 拉回，lightbox 的控制項用鍵盤到不了，這是相對 HEAD 的退化。另有歷史視窗關閉後 focus 掉到 body。
    - 修正後複驗通過，1280 與 390、HEAD 對照：
      - 編輯器（編輯與預覽模式）Tab／Shift+Tab 各 30 次都不離開、碰不到背景連結；HEAD 會到達背景連結。
      - 確認框上 Escape 只關確認框；HEAD 會疊出第二個。
      - OPT-63 上一頁加 Escape 不會卡住；focus 會回到 Header 的 New 按鈕。
      - lightbox（ReadingView 上、編輯器雙欄 gallery、預覽）的 8 個控制項都能用 Tab 到達，Escape 只關 lightbox，方向鍵行為與 HEAD 相同、不外洩到底層。
      - 歷史視窗關閉後 focus 留在編輯器；OPT-21、22、59 沒有退化。
    - e2e：新增 `e2e/test_dialog_a11y.py` 5 項，沿用既有的 Playwright fixture，沒有新增 dependency；既有的 `e2e/test_note_flow.py` 5 項仍然通過。修改前 5 項全部失敗。
    - 指令：`npm run build` 通過、pytest 422 passed、`git diff --check` 通過。
  - 已知：
    - 用滑鼠點卡片或卡片選單開啟的對話框，opener 已不存在，關閉後 focus 會落在 body。卡片是 div，要讓它可聚焦需另開工單。
    - 背景沒有 `inert`／`aria-hidden`，螢幕閱讀器的虛擬游標仍能讀到背景。
    - Settings、Wizard、BackupImport 自己的 fixed div 不在本單範圍。
    - StrictMode 在 dev 下的行為是推論，沒有實跑。
- `PRISM-OPT-29`（docs-only；第二階段依使用者決策不收緊）：
  - `DEPLOY-PI.md` 的安全邊界新增「管理端點對 LAN 的實際範圍」：
    - 經 Caddy 轉發的 LAN 請求在 Go 看來是 loopback，所以能連到 `prism.local` 的裝置可以使用 `/api/server/*`、full snapshot 與合併長文。
    - 筆記 API 本來就沒有限制。
    - 若 LAN 內有不信任的裝置，改用 Caddy `basic_auth`。
  - `docs/API_REFERENCE.md`：既有的「直接連線 peer 的 loopback 檢查」說明（PRISM-OPT-20 已改寫）後面，補上 2026-10-07 的不收緊決策。
  - 驗證：相關文件測試 22 passed；`git diff --check` 通過；鏡像一致。
- `PRISM-OPT-28`（本機驗證；未發版、未部署 Pi）：使用者決策為預設開啟、保留 7 份、只限桌面版。
  - 實作：
    - 桌面殼在 runtime 通過 `/healthz` 後，以 goroutine 檢查一次：最新的 managed backup（`prism_backup_*.db`，依 mtime）超過 24 小時才建立一致快照，並保留 7 份。
    - 關閉時等檢查結束才關 DB。
    - plain runtime（Pi／瀏覽器）與 `--desktop-shell-smoke` 不會觸發。
    - `defaultBackupKeepCount` 由 3 改為 7；手動「建立還原點」改送 `{}`，由後端預設決定，手動與自動共用同一組備份。
    - 新增 `managedBackupMu`，讓手動 rotate 與每日檢查序列化。並發測試在加鎖前實際失敗（同名檔案、VACUUM INTO 衝突），拿掉鎖的對照組也會失敗。
    - 備份清單 additive 欄位 `auto_restore_point`（只在桌面版出現）；檢查失敗時顯示一行警告。
  - **與規格的偏離（主代理決定）**：失敗警告放在 Settings「資料與還原」分頁的還原點區塊，不在「維護與健康」的總覽。理由：警告和使用者會處理它的還原點清單放在一起。若之後要在總覽也顯示，另開工單。
  - 驗證：
    - Go：7 個新測試；`TestBackupRotateDefaultKeepsSeven` 在 HEAD 上失敗。
    - prism-verifier 的隔離 desktop smoke：
      - 啟動兩次只建立 1 份；mtime 往前調 25 小時後會建立第 2 份。
      - 預先放 8 份舊備份後剩 7 份，pre_restore、pre_migrate、`.tmp` 等檔案都保留。
      - plain runtime 不建立；強制失敗時 log 有記錄，警告也會顯示（headless Edge，1280／英文）。
    - 指令：linux/arm64 cross-build（Pi）、`go test ./...`、`npm run build`、pytest 422 passed、`git diff --check`、portable smoke（pwsh 7）都通過。
  - 已知（低）：
    - 結果欄位在寫入失敗時仍帶著不存在的檔名；retention 失敗時 status 也標成 failed；UI 直接顯示原始錯誤字串。
    - `handleBackupDelete`／`Restore` 沒有拿 `managedBackupMu`，與 retention 有很窄的 race（rotate 與 delete 之間原本就有）。
    - 第二個桌面實例在單一實例檢查之前也可能跑一次檢查（24 小時內只會略過）。
    - 390px 與 zh-TW 的畫面沒有實測。
    - Pi timer 仍傳 `keep_count=3`，已記入「Pi 自動備份改每天」的延後項目。
- `PRISM-OPT-58`（本機驗證；未發版、未部署 Pi）：
  - 調查結果（唯讀）：
    - JSON 匯出對已拆分筆記只帶 500 字預覽加橫幅，**沒有全文**；任何附件都只有 metadata，沒有檔案內容。
    - 匯入是全有全無：只要有一列 `docs/notes/...`，`skip` 與 `duplicate` 兩種 mode 都回 400 `unsafe attachment path`，一篇都沒匯入。
  - 修正（`go-shadow/import.go`）：
    - 路徑經 `path.Clean` 後以 `docs/notes/` 開頭、不是絕對路徑、也不含 `:` 的附件列，一律略過並計數，不寫檔、不建立附件列。只看路徑，不看 auto 旗標，這是主代理的決定。
    - 回應新增 additive 欄位 `skipped_attachments`；其他路徑照舊經過 `resolveAttachmentMutationPath`。
  - 驗證：
    - Go `import_test.go` 3 項測試：兩個行為測試在 HEAD 上回 400；防護測試在 HEAD 與新版都通過（7 種不安全路徑 × auto 旗標，rollback）。
    - prism-verifier 的 runtime 端到端驗證：
      - 匯入 fresh target，兩種 mode 都回 200，`skipped_attachments=1`。
      - 拆分筆記的內容等於匯出的預覽；匯回來源端時 auto 列仍只有 1 列，全文完好。
      - 17 種惡意路徑（反斜線、UNC、磁碟代號、`../` 等）都被拒絕，或安全地略過，沒有任何寫入。
    - 指令：`go test ./...` ok、pytest 422 passed、`git diff --check` 通過。
  - 已知：
    - 匯入後的拆分筆記只有預覽，橫幅仍寫「點擊附件可查看」，但其實沒有附件。前端提示見 PRISM-OPT-65，`API_REFERENCE.md` 已說明。
    - 用 skip mode 匯回原 DB 時，一般附件列會重複新增，屬於 PRISM-OPT-64。
    - `scratchpad/opt58-plan` 的刪除被權限擋下，裡面沒有正式資料，保留未刪。
- `PRISM-OPT-25`（本機驗證；CI 結果見 push 後的 GitHub Actions）：
  - 移出版控與刪除的範圍：
    - `git rm -r --cached frontend/node_modules`（3,890 檔）：只動 index，本機資料夾保留，`.gitignore` 本來就已忽略。
    - 刪除 `resources/`、`static/{js,css,lib,locales,fonts}`（舊 Vue 前端）、`tools/`，以及 5 個死 script。其中 `clean_test_data.py` 會不經確認清空 `./knowledge.db` 的筆記。
    - 移除 `.vscode/launch.json` 的 Flask 設定、`vite.config.ts` 中 Go 已不提供的 `/prompt-builder.html` 與 `/templates` proxy，以及 `index.html` 指向不存在檔案的 favicon。
    - 總共 3,944 筆刪除，約 100 MB。
  - `static/config`、`static/uploads`、`knowledge.db`、`desktop-spike/`、`install.*`、`requirements-pi.txt` 都沒有碰。不需要修改任何測試。
  - 驗證：
    - prism-verifier 用刪除後的追蹤清單做乾淨複本：`npm ci && npm run build` 成功，裝得到 `dompurify`；用複本的 dist 執行 `go build ./...` 也成功。
    - 對全部 tracked script／程式／CI／tests 做引用掃描，沒有 live 引用；只剩歷史文件中的提及。
    - 指令：pytest 422 passed、`go test ./...` ok、`npm run build` 通過；`e2e/test_note_flow.py` 5 passed，會跑 `scripts/build_go_runtime.ps1`，證明 build script 不依賴已刪的路徑；`git diff --check` 通過。
  - 已知（低）：
    - `.vscode/launch.json` 還有無作用的 Flask 時代環境變數。
    - `.gitignore` 裡 `resources/` 的兩條忽略規則還在。
    - `scripts/start_v2_dev.bat` 與 `install.sh` 用 `npm install`，可以考慮改成 `npm ci`。
- `PRISM-OPT-26`（本機驗證；CI 結果見 push 後的 GitHub Actions）：
  - gate 分流：
    - `pytest.ini` 新增 `slow`、`historical` 兩個 marker：4 個打包／桌面 smoke 標 slow；26 個只讀文件的 Phase 19–23 模組標 historical，共 165 個測試。
    - `.loop/verify-gate.ps1` 預設是 fast gate：diff check、鏡像比對、`pytest -m "not slow and not historical"`（253 個）、`go test`。
    - 加 `-Release` 跑全部 422 個 pytest 再加 `pytest e2e`（17 個）。CI 改跑 `-Release`，並先安裝 Chromium。`.loop/manifest.md` 的完成 gate 改為 `-Release`。
  - 計時（記錄於 `docs/TEST_PORTFOLIO.md`）：pytest 冷建置從 129.6–143.3s 降到 71.5–75.0s；熱快取從約 96s 降到約 45–52s。
  - 行為測試：新增 `e2e/test_review_regressions.py` 7 個，涵蓋：
    - 附件 popup 不會被注入、從 Settings 按 New、從 Prompt Builder 做中文搜尋、palette 輸入 2 個 CJK 字即查詢 server。
    - `Ctrl+S` 存檔並留在編輯器、長文存檔後留在 inline、拆分長文改短後重開。
    - 其中 6 個有 fail-before：倒回修正後確實失敗。verifier 另外在 scratch 同時還原 OPT-16／17／18 三個修正，對應的 4 個 e2e 失敗、其他 13 個通過。
  - Header 的 source-lock 改為 regex，接受 `!isHomeRoute` 等等價寫法；verifier 用 12 種寫法驗證過。`requirements.txt` 補上原本就在用的 `pytest-playwright`／`playwright`。
  - Go 測試盤點：CJK、WAL、長文、縮短後被還原，前面的工單都已補齊；`handleSystemVacuum`／`handleWALCheckpoint` 仍沒有測試。
  - 主代理額外修正：
    - `scripts/build_go_runtime.ps1` 原本在 `npm run build` 失敗時不會中止，release gate 的 e2e 可能跑在舊的 dist 上而誤判通過（實作時真的發生過）。現在 npm build、go test、go build 失敗都會 throw；已實測前端編譯錯誤會讓腳本 exit 1，而且不產出 artifact。
    - `CLAUDE.md`／`AGENTS.md` 的測試規則與快查表改為 fast／`-Release` 兩段，兩份一致。
  - 驗證：
    - prism-verifier 檢查 marker 分類：historical 全部只讀文件，沒有分錯。
    - fast 與 `-Release` 都通過；pytest 的 test ID 集合與 HEAD 逐行相同，沒有刪除任何測試。
    - 第一輪因為計時沒有寫進文件、`TEST_PORTFOLIO.md` 還留著過時的段落而退回，主代理已補上。
  - 已知（低）：放寬後的 Header 鎖仍綁 `data-testid` 與 `onClick` 的屬性順序（行為已由 e2e 守住）；CI 首次加上 e2e，可能偶爾不穩。
- `PRISM-OPT-23`（本機驗證；未發版、未部署 Pi）：
  - Settings「資料與還原」的匯出文案改為照實描述，四語都更新：
    - JSON：可攜的文字副本（筆記、分類、標籤），不含置頂、封存、版本歷史、附件檔與圖片。
    - Markdown：每則筆記一個 .md，含置頂／封存標記與本機圖片，不含文字附件。這點已讀 `buildMarkdownExportZip` 確認。
    - .db：只有資料庫，不含上傳圖片、附件檔、docs/notes 檔與 config。
    - 三者都指向「完整資料快照」。
  - 新增 `exportSplitNotesNote`：已拆分的長文在三種匯出中只有 500 字預覽，請先到「維護與健康」執行「合併長文回筆記」。主代理核對過四語的分頁名稱與按鈕名稱，都和實際 UI 一致。
  - 修改鎖定舊文案的 source test，斷言方式不變。
  - 驗證：`npm run build` 通過；`git diff --check` 通過；隔離 runtime 的 headless 瀏覽器在 4 種語言 × 390／1280 都沒有水平捲動，文字正常換行。
  - 已知：OPT-20 在正式資料上執行後，可以拿掉預覽提示；PRISM-OPT-39 補上欄位後，JSON 文案要同步修改。
- `PRISM-OPT-24`（本機驗證；未發版、未部署 Pi）：
  - `/api/test` 加上 `version`（`prismVersion()`，additive）。前端的 `appStore.fetchAppVersion()` 由 `Layout` 在啟動時呼叫一次，供 Sidebar、Settings → About 與 `document.title`（`Prism V<ver>`）使用。
  - `index.html` 的 title 改為 `Prism`。讀取中或失敗時不顯示假版本。
  - `Sidebar.tsx`、`SettingsPage.tsx`、`index.html` 不再有版本字面值，由 regex source test 鎖住。`frontend/package.json`（private、沒有用到）不列入版本更新，已寫進 `RELEASE_CHECKLIST.md` 新增的 Version Bump 段。
  - 驗證：
    - Go `TestAPITestReturnsRuntimeVersion`、pytest source test 都有 fail-before。
    - prism-verifier 的假版本證明：`prismVersion()` 改成 7.7.7-verify 後，title、Sidebar、About 在 1280 與 390 都跟著變；真實 build 仍顯示 2.6.1；擋掉 `/api/test` 時不顯示任何版本。
    - 整個 SPA 只讀一次版本；`-Release` gate 通過（pytest 422 passed、e2e 17 passed）。
- `PRISM-OPT-64`（本機驗證；未發版、未部署 Pi）：
  - `go-shadow/import.go`：
    - 寫檔改用 `O_CREATE|O_EXCL`（`createImportFile`），`createdFiles` 只記錄這次匯入真正新建的檔案；後段失敗的清理不會再刪到目標端原有的檔案。
    - 附件帶 `content_b64`、而且撞到既有檔案時，改寫成 `<名>_import_<n><副檔名>`，每個候選路徑都重新做安全檢查，並存入新路徑。
    - upload 撞名時略過，計入 additive `skipped_uploads`，因為筆記以檔名引用圖片。
    - 同一筆記已有相同（正規化或原始）路徑的附件列時不重複新增，所有 mode 都適用；DB 一律存正規化路徑。
  - 驗證：
    - Go 5 項新測試，4 項行為測試在 HEAD 上失敗。
    - prism-verifier：`-Release` gate 通過（pytest 422、e2e 17）。
    - 隔離 runtime 實測：失敗匯入時原檔 sha256 不變；成功匯入時原檔不變，新附件讀得到；skip 重新匯入時列數不變。
    - 邊界 probe：目標是目錄時安全失敗；大小寫衝突會改名或略過；duplicate mode 下同一則筆記的重複列只會建立 1 列。
  - 已知：
    - M1：改名後再用 skip mode 匯入帶內容的 JSON，會累積 `_import_N`，已記入 PRISM-OPT-66 的已知限制。
    - M2：不帶內容的附件列會共用目標端的檔案，之後刪除會刪到別人的檔案。這是 HEAD 原本就有的問題，另開 **PRISM-OPT-66（P1）**。
- `PRISM-OPT-66`（本機驗證；未發版、未部署 Pi）：
  - `deleteAttachment` 改成單一交易：第一句 `DELETE … RETURNING file_path` → `noteFileSharedByOtherRow` 檢查 → 沒有被共用才刪檔 → commit。
    - 刪檔放在 commit 之前，以維持原本「刪檔失敗回 500、附件列保留」的語意，主代理同意。
  - 從 `noteFileSharedByOtherRow` 抽出 `noteFileAliases`，行為不變。筆記刪除與批次刪除（含 dry-run 預覽）改用 `noteFileReferencedElsewhere`：先比字串，再用 handle 比對大小寫變體的檔案身分。這修正了 Windows 上大小寫不同的路徑被誤刪。
  - 驗證：
    - 新增 `attachment_delete_test.go`，5 個 case 在 HEAD 上都失敗。
    - prism-verifier：`-Release` gate 通過（pytest 422、e2e 17）；OPT-60 的 restore 與 shared 測試全部通過。
    - 額外驗證：同一筆記兩列指向同一檔時不會留下孤兒檔；dry-run 計數正確；刪檔失敗回 500 並保留附件列；併發刪除與讀取各 20 次都正常。
    - 兩個隔離 runtime 的真實重現：A、B 同秒上傳造成真正撞名，B 匯出後匯入 A。刪匯入的列、或刪除筆記 A 時，A 的檔案都保留；刪掉最後一個引用才刪檔。
  - 已知：每次刪除都會掃一遍附件表；刪檔成功但 commit 失敗時，會留下指向不存在檔案的附件列，與 HEAD 原本的失敗型態相同。
- `PRISM-OPT-30`（本機驗證；未發版、未部署 Pi）：
  - `Header.tsx`：
    - 排序按鈕在 <640px 也顯示（只有圖示），mobile 選單改為 `fixed`，靠右且不溢出。
    - a11y：`aria-haspopup`／`aria-expanded`、`role=menu`、`menuitemradio` 加 `aria-checked`；Escape 可關閉。
    - 關閉後 focus 回到排序按鈕，但只在 focus 原本就在選單內時才搶回，避免把 focus 拉出上層對話框（OPT-62）。
  - `HomePage.tsx` 在 mobile 壓縮間距，≥640px 不變。`appStore`：沒有存過 `prism.viewMode` 時，<640px 預設 list；已存的偏好照舊。
  - 實測（375／390）：
    - 第一張卡片 top 從 287 降到 238px；預設 list 完整可見 5～6 張（原本 2～3 張）。
    - 三種排序的 DOM 順序都和 API 一致。
    - 640、700、768、1024、1280 的全頁截圖與 HEAD 逐像素相同。
  - prism-verifier 退回兩次：
    - 第一次：既有 e2e 的 locator 因 role 改變而失效。另外發現 `test_dialog_a11y` 在 HEAD 上就不穩定，已改成用搜尋開啟 anchor，只動測試、斷言不變；`pytest e2e` 連續 3 次全綠。
    - 第二次：focus 歸還會在 Escape 時把 focus 拉出上層的確認框。主代理加上 `sortMenuRef.contains` 判斷，並新增 e2e `test_escape_with_sort_menu_open_keeps_focus_in_the_top_dialog`；拿掉判斷時這個 e2e 會失敗。
  - e2e：新增 `e2e/test_mobile_sort_density.py` 3 項，在 HEAD 上失敗；`-Release` gate 通過（pytest 422、e2e 20）。
  - 同時期另一個修正（獨立 commit `f342139`）：`test_desktop_shell_go_build_and_runtime_smoke` 不再重跑 `go test ./...`。它原本設 120s timeout，隨著 Go 測試變多，在 CI 上逾時，造成 OPT-66 那次 push 的 CI 失敗；修正後 CI 恢復綠燈。
  - 已知（低）：排序選單沒有方向鍵導覽；mobile 預設 list 只在第一次載入時判斷。
- `PRISM-OPT-31`（本機驗證；未發版、未部署 Pi）：
  - API（additive）：`/api/test` 的 stats 加上 `library_count`（未封存筆記數，含未分類）；`/api/system/stats` 的 uploads 加上 `files`（不含 `*_thumb.*` 縮圖）。
  - 前端：
    - store 的 `libraryTotal` 跟著啟動時那次 `/api/test` 一起讀，之後在 `fetchNotes(reset)` 與刪除後刷新。Sidebar 的 All、Header 首頁 meta、Footer 都用它；篩選後的數字只出現在 HomePage 副標，那裡原本就有標示。
    - Maintenance 改讀 `/api/system/stats`：notes＝總數減封存，images＝`uploads.files`，並顯示大小。
    - 讀取前或失敗時顯示「–」，不顯示 0。
    - 主代理另外讓 SettingsPage 重用自己那次 `/api/test` 的 `library_count`，不再多打一次。
  - 驗證：
    - Go `TestLibraryCountExcludesArchivedAndUploadStatsCountFiles`、pytest source-lock 都在 HEAD 上失敗。
    - prism-verifier 的隔離 runtime（7 筆、含 1 筆封存與 1 筆未分類、3 張圖加縮圖）17/17：
      - 三處都是 6（舊算法會是 7）；直接載入 `/settings` 不是 0；搜尋或篩選後總數不變。
      - 封存、取消封存、刪除、建立、JSON 匯入後都同步更新；Maintenance 與 API 一致；390px 沒有溢位。
    - `-Release` gate 通過（pytest 423、e2e 20）。
  - 已知（低）：
    - 每次列表 reset 都會多打一次 `/api/test`（4 個 COUNT），可以在 PRISM-OPT-32 收斂。
    - server-system 停用時，Maintenance 四張卡都顯示「–」。
    - 分類計數仍包含封存筆記，規格要求不改這個語意。
- `PRISM-OPT-32`（本機驗證；未發版、未部署 Pi）：
  - 前端：store 新增 `refreshLoadedNotes()`。mutation 後並行重抓已載入的第 1～k 頁（沿用 `notesRequestSequence`，依 id 去重），不再 `fetchNotes(true)` 回到第 1 頁。
    - 套用處：編輯器存檔與 `Ctrl+S`、卡片選單的 pin／archive／variant、history restore、ReadingView 的 pin／archive。
    - 分頁大小仍是 20（`NOTES_PAGE_SIZE`），API 與 Go 都沒改。
    - `fetchNotes(reset)` 不再順帶打 `/api/test`，Library total 只在會改變總數的操作後刷新（收斂 OPT-31 的已知低風險）。新增 `libraryTotalRequestSequence`；Prompt Builder 存成筆記後也會刷新總數。
    - 列表 grid 加上 `[overflow-anchor:none]`，避免重抓時瀏覽器拿卡片當捲動錨點而跳動。
  - 驗證：
    - 新增 `tests/test_list_in_place_updates_opt32.py` 與 `e2e/test_list_in_place_updates.py`（72 筆、載入 3 頁後改第 45 筆）。用 HEAD（`22dc2a1`）的 tree 跑：source lock 4 failed，e2e 失敗並顯示 `list was reset: 20 cards left`。
    - prism-verifier 在隔離 runtime（70 筆中文筆記）實測 1280 grid、390 list、390 grid：
      - 七種操作後卡片都還是 60 張，scrollTop 不變；只有 variant 位移 40–48px（容忍 60px 內）。
      - pin 後該筆在置頂區第一位；每次操作剛好打 page 1～3 三個請求。
      - Sidebar、Footer 與 `/api/test` 在 archive、variant、delete、批次刪除、取消封存後都一致；純搜尋、篩選、排序不打 `/api/test`。
    - `-Release` gate 通過（pytest 426、go test ok、e2e 21）；另跑一次 `pytest e2e` 也是 21 passed。
  - 已知：
    - 刪除有 variant 子筆記的父筆記會回 500（HEAD 既有的後端 bug）→ 已開 `PRISM-OPT-68`。
    - 刪除與批次刪除只在本地濾掉筆記，之後 load-more 用舊的位移，可能漏掉跨頁的那一筆（HEAD 既有）→ 已開 `PRISM-OPT-69`。
    - 低：刷新失敗後按 Retry 會回到第 1 頁；SettingsPage 寫回 `libraryTotal` 時沒經過序號，理論上可能被較舊的回應蓋掉。
- `PRISM-OPT-68`（本機驗證；未發版、未部署 Pi）：
  - Go：單筆與批次刪除原本就共用 `deleteNotesByID`（同一個 transaction、持有 `noteFilesMu`）。在刪除前逐筆執行 `UPDATE Notes SET parent_id = (被刪筆記的 parent_id) WHERE parent_id = 被刪 id`，子筆記因此改掛到最近一個沒被刪的祖先，與刪除順序無關。schema、API 形狀、檔案與附件處理都沒改。
  - 驗證：
    - 新增 `go-shadow/note_variant_delete_test.go` 的 3 個測試，每個都分 single、batch 兩條路徑（共 8 個子測試）：刪除根筆記、刪除中間一代、批次同時刪除父與子（正序與反序）。每個都檢查 `PRAGMA foreign_key_check` 為空。
    - 修正前 8 個子測試都失敗（`FOREIGN KEY constraint failed (787)`）。主代理另外把修正 stash 掉重跑，3 個測試都失敗；還原後通過。
    - fast gate 通過（pytest 257、go test ok）。
  - 已知（低）：刪除後，variant 卡片上的 parent_title 與 variants_count 要等列表重新載入才會更新，由 PRISM-OPT-69 一併處理。批次刪除的 dry-run 預覽不會列出哪些 variant 會被改掛。
- `PRISM-OPT-33`（本機驗證；未發版、未部署 Pi）：
  - 前端：
    - FilterStrip 在 ≥md 且 Sidebar 展開時，隱藏 All 與分類 chips，只留 Archive、starred tags，以及「目前分類」與「目前非 starred 標籤」兩個可清除的 chip（aria-label 為四語 i18n）。
    - Sidebar 收合時，Sidebar 會把分類藏起來，所以 FilterStrip 在 ≥md 也恢復完整 chips。為此把 Sidebar 的 `isCollapsed` 移到 appStore 的 `sidebarCollapsed`（不持久化），Sidebar 結構沒變。mobile 維持完整 chips。
    - Home 的 Header 不再顯示標題與「N items」，因為它和 H1 重複；篩選後數量仍在 H1 副標，總數在 Sidebar All 與 Footer。順手刪掉不再使用的 i18n `header.all／archive／homeMeta`（四語）。
  - 驗證：
    - 新增 `e2e/test_library_nav_dedup.py` 5 條，涵蓋：desktop 只剩 Sidebar 一組分類、mobile 保留 chips、標題與計數不重複、收合後恢復 chips、搜尋加非 starred tag 時有 active chip。
    - 用 HEAD 跑會失敗；prism-verifier 另外只還原 `mdHide`，確認收合那條真的在測收合邏輯。
    - prism-verifier 第一次退回：desktop 收合 Sidebar 後完全沒有分類導覽。修正後複驗通過：
      - 1280 展開與收合兩種狀態都正常，Tab 與 Enter 可以操作 chips。
      - 390 沒有水平溢位，drawer 行為不變。
      - 「收合→縮到 390→放回 1280」沒有怪狀態。
    - `-Release` gate 通過（pytest 426、go test ok、e2e 26）。
  - 已知（低）：390 在「搜尋＋非 starred tag」時看不出是哪個 tag，只有泛用的篩選提示。
- `PRISM-OPT-34`（本機驗證；未發版、未部署 Pi）：
  - 前端：
    - Appearance 不新增 tab，改成分兩段：「Display」與「Library & editor」（卡片開啟模式、快速新增預設分類、自動載入）。
    - 圖片儲存模式（抽成 `ImageSaveModeSetting.tsx`）與整個 DangerZoneSection（三種圖片清理）移到 Maintenance 新增的「Images & storage」；Access 只剩 Security。
    - `?tab=` 的別名：`data` → `backup`；六個舊 tab id 照舊有效。
    - 圖片儲存模式的 select 加上 state，選完立刻顯示新值，localStorage key 與寫入時機不變。
    - 四語 i18n。
    - 主代理收尾時處理了兩項 Low：DangerZone 每列的圖示加 `shrink-0`（390 時原本被壓到幾乎看不見）；韓文標題改為「이미지 및 저장 공간」。
  - 驗證：
    - 新增 `e2e/test_settings_regroup.py` 5 條。HEAD 上 4 條失敗；390 溢位那條是防回歸用，所以在 HEAD 上也會通過。
    - prism-verifier 在隔離 runtime 實測：
      - 舊的 localStorage 值 reload 後都還在；六個 tab id 與 `data` 都導到正確的 panel。
      - 390 下七個 tab 都沒有溢位。
      - 三種圖片清理都實際執行到確認對話並完成，結果正確，文案與流程和 HEAD 相同（修復壞路徑原本就不跳確認）。
    - `-Release` gate：verifier 那次 e2e 失敗 1 條，是不相關的 `test_ctrl_s_saves_new_note_keeps_editor_open_and_updates_same_note`；單獨重跑 3/3 通過，完整重跑 31 passed → 已開 `PRISM-OPT-70`。
  - 已知（低）：Danger Zone 卡片嵌在 SectionPanel 裡，390 時兩層 padding 疊加，內容變窄但可讀；heading 是 `h2` 包 `h2`。
- `PRISM-OPT-35`（本機演練；未在真實 Pi 上演練，未發版）：
  - 文件：`docs/desktop/README-PORTABLE.md`（PowerShell）與 `DEPLOY-PI.md`（bash）各新增「從 Full snapshot 還原」，兩份都是同樣的六步：
    1. 關閉程式。
    2. 備份目前的 data-dir，並印出備份路徑。
    3. 解壓 snapshot。
    4. 放回檔案並改 DB 檔名。刪除之前必須先驗證解壓出來的資料夾；移除舊的 `-wal`／`-shm` 後要明確檢查已經刪掉。
    5. 用 manifest 的 SHA-256 函式驗證，還原前後各跑一次。
    6. 啟動後檢查 `migration-status`。

    另外附上回復指令，並說明 `backups`／`.csrf_disabled` 不在 snapshot 裡。
  - `docs/contracts/full-data-snapshot-v1.md:69` 改為指向這兩份文件。Settings 的 Full snapshot 卡片加上一行四語說明，是純文字，不是連結。
  - 驗證（prism-verifier 照文件逐字演練，路徑全部在 scratch）：
    - 來源資料：中文筆記、11622 字的長文（拆分到 `docs/notes`）、附件、CJK 檔名的圖片與附件、config。
    - 桌面版：目標 data-dir 先放舊資料與過期的 WAL，照步驟還原。還原後的基準資料與來源完全相同，`migration-status` 是 17/17，`pending` 為空。
    - 故意改壞或移走檔案，驗證會報 `MISMATCH`／`MISSING`。
    - 反向對照：沒刪舊的 `-wal` 時，讀到的是舊資料，證實這一步必要。
    - PowerShell 5.1／7 的 `Expand-Archive`、Windows tar、python zipfile 解出的 CJK 檔名都正確；Git Bash 的 `unzip` 會亂碼，但驗證能攔下。
    - Pi 步驟在 Git Bash 實際跑過（`systemctl`、`chown` 只審閱沒執行），結果與來源相同。
    - 演練回報 8 個 Low：驗證改成刪除前的強制步驟、STOP 檢查、port 變數、亂碼原因寫錯、回復指令、還原點提醒、UI 名稱。全部由 prism-docs 修正，修正後的片段在 scratch 假目錄中實際跑過。
    - fast gate 通過；`pytest tests/` 426 passed。
  - 演練順帶發現：純 CJK 檔名的圖片會被拒絕、附件標題變成 `_`。已併入 `PRISM-OPT-67`。
- `PRISM-OPT-36`（本機驗證；**Pi 實機 smoke 待下次 deploy 補做**；未發版）：
  - 選 A。`handleServerRestart` 保留 POST、localhost、server-system 三道 gate，CSRF 仍包在外層；先寫出回應再呼叫 `s.restart()`（nil 時退回 `triggerRestart`）。
    - supervised 模式以 exit 42 結束，由 systemd `Restart=on-failure` 重新拉起。
    - standalone 與桌面版則 re-exec 自己。
  - `GET /api/server/hardware` 的 `service_management.available` 改成 `true`。原本固定是 `false`，前端因此一直把 Restart 按鈕藏起來；現在按鈕看得到了。
  - 前端：保留原本的確認對話。送出後顯示「重新啟動中」，用 `waitForHealthy` 等到恢復才 reload；逾時就顯示錯誤，不再假成功。文案有四語 i18n。
  - 文件：`docs/API_REFERENCE.md`、`go-shadow/README.md`、兩份 contract 的舊說法（「safe acknowledgement」）都已更新。
  - 驗證：
    - Go `TestHandleServerRestart` 有 6 個 case：method、localhost、server-system、CSRF，以及恰好重啟一次。修正前 restart 次數是 0，測試失敗。
    - pytest `test_server_restart_really_exits_for_supervisor` 確認程序真的以 42 結束。
    - prism-engineer 實測重啟：standalone 2 輪、desktop shell 3 輪（每輪只有 1 個程序、1 個視窗，資料都在）、UI 的成功與逾時兩條路徑。
    - prism-verifier 另外跑了一輪 standalone：回應在 2ms 內送達，舊程序 287ms 後退出，0.8s 恢復 healthy，資料還在。cross-origin 的 POST 被擋（403），程序沒有重啟。
    - `-Release` gate 通過（pytest 427、go test ok、e2e 31）。
  - 已知：
    - Pi 經 Caddy 進來時，localhost gate 擋不住區網使用者，只剩 CSRF 防護；還原點端點也一樣。
    - 桌面版重啟後會殘留一個幽靈 tray icon；剛啟動時按 Restart，可能撞上正在寫入的每日還原點 → 已開 `PRISM-OPT-71`。
    - 桌面 GUI 版的 log 檔一直是 0 bytes → 已開 `PRISM-OPT-72`。
- `PRISM-OPT-37`（本機驗證；未發版、未部署 Pi）：
  - Go 只改字串：
    - 13 條 `--enable-*` flag 的說明拿掉「local/copied-DB … parity candidate」。
    - 啟動 log 改成 `Prism runtime listening on …`。
    - 附件 raw 被停用時的錯誤，從「remain Python-owned」改成 `Attachment raw read route is disabled`。
    - `/healthz` 的 `runtime.mode` 值從 `go-runtime-proof` 改成 `go-runtime`（key 不變）。主代理 grep 過 repo 的 scripts、tests、frontend、deploy，沒有其他地方依賴這個值或舊的 log 字串。
  - 不改：flag 名稱與行為、DB 檔名、API 結構、內部識別字、module 與目錄名、歷史文件。
  - 驗證：
    - 新增 `go-shadow/neutral_strings_test.go` 的 `TestRuntimeOutputHasNoMigrationEraWording`。它實際 build 並啟動 runtime，收集 `-h`、`/healthz`、附件 405 回應與啟動 log，斷言其中都沒有 candidate、proof、parity、python。
    - 在 HEAD 上，這個測試會因 4 處字樣而失敗。
    - fast gate 通過（pytest 258、go test ok）。
- `PRISM-OPT-38`（本機驗證；未發版、未部署 Pi）：
  - 前端 `ReadingView.tsx`：
    - 預取範圍：不再預取整個閱讀清單，只抓目前項目的前後各一個。
    - 側欄 metadata：優先用已載入的 detail，其次用 store 的 list notes；兩者都沒有時，標題顯示 `#id`，第二行留空。原本的「讀取中」會一直卡著，已移除，`reading.workspacePending` 四語一併刪除。
    - 錯誤處理：只有 404 會透過 `useReadingWorkspace.removeNote` 移出清單；500、斷線維持 unavailable 標記。
    - 不變：localStorage 的 key 與格式、版面。
  - 驗證：
    - 新增 `e2e/test_reading_lazy_detail.py`，用 50 筆 CJK 筆記測試。開啟時 HEAD 發出 50 個 detail 請求，修改後是 3 個；切換項目最多再多 2 個；刪除的筆記輪到時會被移出清單與 localStorage。
    - prism-verifier 實測：
      - 500、abort 不會移除，404 會移除。
      - 延遲回應的過期請求不會寫進 state；連續快速切換時，active 與 localStorage 一致。
      - 1280／390 的 `#id` 不會破版，點擊後會換成 CJK 標題。
    - verifier 第一次退回兩項：e2e 單跑 5 次失敗 3 次（背景 load-more 讓遠端項目拿到標題）、未載入項目永遠顯示「讀取中」。修正後，e2e 改為攔截第 2 頁以後的 list 回應，單跑連續 5 次通過。
    - `-Release` gate 通過（pytest 427、e2e 32）。
  - 已知：
    - 低：圖書館很大，或首頁處於篩選狀態時，側欄多數項目會長期顯示 `#id`。
    - 預取還沒回來就點了該項目時，可能重複抓一次。
    - 目前閱讀的筆記被刪除後，Header 的閱讀清單一直打不開（HEAD 既有）→ 已開 `PRISM-OPT-73`。
- `PRISM-OPT-39`（本機驗證；未發版、未部署 Pi）：
  - 匯出（`export.go`）：每筆新增 `is_pinned`、`is_archived`、`parent_id`、`cover_position`、`editor_layout`、`sort_order`（additive），`export_info.version` 由 `1.6-go` 升為 `1.7-go`。
  - 匯入（`import.go`）：
    - 五個值欄位在 INSERT 時寫入。
    - `parent_id` 在同一個 transaction 的第二輪處理，只透過 `idMap` 重新對應，不直接使用檔中的數字：
      - parent 被 skip 時，指向既有的那一筆；
      - parent 不在檔中時設為 NULL；
      - 會形成環時設為 NULL。
    - 被 skip 的既有筆記完全不修改。
    - 不合法的值退回預設值，整批匯入照常成功。
    - 使用者決定（2026-10-07）：`cover_position`／`editor_layout` 和寫入 API 一致，只檢查型別、不做 enum 檢查。
  - 文案：四語 `jsonCopyDescription` 與 `docs/API_REFERENCE.md` 都照實寫出包含與不包含的內容。不包含：版本歷史、`prompt_params`、附件與圖片檔案內容；拆分長文只有預覽。
  - 驗證：
    - 新增 `go-shadow/import_fields_test.go`，共 6 個測試：round-trip（含 fresh 與 occupied-ids，檔案順序為 C、B、A）、parent 不在檔中、舊版 JSON、不合法值、skip mode、環。修正前有 3 個 FAIL，另外 3 個是相容性守門測試。
    - prism-verifier 讀 code 並在 scratch 測了以下邊界：id 重疊、skip 不修改既有筆記、duplicate mode、三節點環、第二輪 UPDATE 失敗時整批 rollback 且不留檔。
    - runtime 端到端：source 的 id 從 5 開始、與 target 錯開，6 個欄位逐筆一致，譜系指向新 id，UI 的置頂區、封存檢視、variant 面板都正確。HEAD 匯出的 1.6-go 檔可以匯入，欄位為預設值。
    - `-Release` gate 通過（pytest 427、go test ok、e2e 32）。
  - 已知（低）：
    - duplicate mode 的譜系與 rollback 路徑只在 scratch 驗證過，沒有 repo 測試鎖住。
    - 匯入到非空的 DB 時，custom sort 會和既有筆記交錯，這是既有語意。
- `PRISM-OPT-53`（本機驗證；未發版、未部署 Pi）：
  - 前端：
    - Header 在非首頁加一顆 `md:hidden` 的搜尋圖示（aria-label 用 `common.search`），點擊後 `navigate('/', { state: { focusSearch: true } })`。
    - HomePage 掛載時，讀到這個 state 就把 focus 放到 `mobile-search-input`。
    - 桌面版 Header、`mobile-search-form`、appStore 都沒動。
  - 驗證：
    - 新增 `e2e/test_mobile_search_entry.py`：390px 下，從 `/settings`、`/prompt-builder` 點圖示，回到 `/` 後輸入框取得 focus，輸入中文關鍵字送出可看到結果，沒有水平溢位，console error 為 0；1280px 下按鈕不可見。
    - 在 HEAD 上，390 的兩條測試會失敗。
    - `-Release` gate 通過（e2e 35）。
    - 改動很小，而且 e2e 已涵蓋驗收條件，所以由主代理讀 diff 驗收，沒有另外派 prism-verifier。
  - 已知（低）：
    - `history.state` 沒有清除，在 `/` 重新整理時會再聚焦一次。
    - iOS 由程式設定的 focus 不一定會叫出鍵盤。
    - 390 下閱讀工作區按鈕也出現時的版面沒有另外量測，標題可以截斷。
- `PRISM-OPT-55`（本機驗證；未發版、未部署 Pi）：
  - 前端：
    - appStore 用 module 變數 `libraryViewMounted` 記錄 Library 畫面是否掛載：HomePage 掛載時設為 true，unmount 時設回 false。
    - `setSearchQuery`、`setSelectedCategory`、`setSelectedTag`、`setSortBy`、`setShowArchived`、`applySearchWorkspace` 只在 Library 已掛載時才 fetch。不在首頁時只更新 state，等 HomePage 掛載時一次 fetch。
    - 不論呼叫順序是 Sidebar 那種「先 setter 再 navigate」，或 Header 那種「先 navigate 再 setter」，都能正確處理。
  - 請求數（修改前 → 修改後）：
    - `/settings`、`/prompt-builder` 的 Header 搜尋：2 → 1
    - `/settings` 的 Sidebar 分類、Archive：2 → 1
    - `/` 上的各種操作：1 → 1
  - 驗證：
    - 新增 `e2e/test_single_list_request.py`，共 6 條。HEAD 上有 4 條失敗（`2 == 1`）。
    - prism-verifier 讀 code 推理了 StrictMode、Reading view／編輯器是 HomePage 的子元件、兩種呼叫順序、OPT-32 的序號，並 grep 所有呼叫點，沒有「Library 未掛載時呼叫 setter 又需要立即拿到結果」的用法。
    - verifier 也實測補上 e2e 沒涵蓋的入口：Sidebar 標籤、Command Palette 的 Archive／All、Reading view 開關、從 Prompt Builder 返回、在 `/` 快速連點、清空搜尋，全部都是每個動作 1 次，結果正確。
    - `-Release` gate 通過（pytest 427、e2e 41）。
  - 已知（低，既有）：在 `/` 已有篩選時，點 Sidebar 的 Prompt Builder 或 Settings，`clearLibraryFilters` 仍會送出 2 個沒有人使用的請求。
- `PRISM-OPT-54`（本機驗證；未發版、未部署 Pi）：
  - 前端（主代理實作）：`AttachmentPanel` 的刪除按鈕加上 `inline-flex shrink-0`，並在 `max-md` 與 `[@media(hover:none)]` 下設 `min-h-11 min-w-11`（44px）。桌面仍是 `p-1`，約 20px；OPT-16 的按鈕語意與 API 都沒動。
  - 驗證：
    - 新增 `e2e/test_attachment_touch_target.py`。附件是 CJK 檔案。1280 時刪除按鈕 ≤24px；390 時 ≥32px，附件列與頁面都沒有水平溢位。
    - 在 HEAD 上，390 那條斷言失敗（按鈕尺寸不足）。
    - `-Release` gate 通過。
- `PRISM-OPT-56`（本機驗證；未發版、未部署 Pi）：
  - Go `notes_search.go`：
    - `hasCJKToken` 加入 `unicode.Hangul`。
    - 新增 `foldFullwidth`：U+FF01–U+FF5E 減 0xFEE0，U+3000 轉成空白。`searchTokens` 先折疊再 `ToLower`，FTS、LIKE、附件掃描都會經過這一步。
    - 只作用在查詢端；FTS schema、tokenizer、migration、已存內容都沒動。
  - 前端：CommandPalette 的 `CJK_CHAR_PATTERN` 加入 `\p{Script=Hangul}`，韓文同樣是 2 字就開始搜。
  - 文件：`docs/API_REFERENCE.md` 新增「搜尋比對語意」：ASCII 用前綴比對；CJK（含韓文）用子字串比對；查詢混合時，只要有 CJK，ASCII token 也改用子字串比對；全形英數只在查詢端折疊。
  - 驗證：
    - 新增 `go-shadow/notes_search_norm_test.go`，三個測試都經過 HTTP handler：
      - 韓文詞中段「의록」：修正前 0 筆。
      - 「ＰＲＯＭＰＴ」與「prompt」得到相同 id；「ｒｏｍ　工程」也能命中。
      - `TestNotesSearchASCIIQuerySQLUnchanged`：`prompt`、`a b`、`foo-bar` 產生的 SQL hash 與 args，和修改前擷取的完全相同。
    - 主代理把 `notes_search.go` stash 掉重跑，前兩個測試失敗，ASCII 那個通過，符合預期。
    - fast gate 通過（pytest 258）。source-lock `tests/test_command_palette_server_search.py` 的 regex 字串已同步更新。
    - 改動很小，而且測試直接涵蓋，由主代理驗收。
  - 已知（低）：
    - 內容中的全形字，用半形查詢仍搜不到；要雙向一致，需要在索引端正規化，屬於 schema decision gate。
    - 簡繁轉換、半形片假名不在本單範圍。
- `PRISM-OPT-57`（純驗證，沒有改程式；main `166a2ed`）：
  - 測試內容：
    - payload 為 `</pre><img onerror>`、`<b id="injected">`、`<script>document.title='PWNED2'</script>`，加上繁體、簡體、日文、韓文。
    - 先用 API 讀回，確認存進去的內容與原文一致。
  - 結果，三個環境都 PASS：
    - 每個 popup 只有一個 `<pre>`，`textContent` 與 payload 完全一致；`img`、`script`、`#injected`、`b` 都是 0 個；popup 與 opener 的 title 都沒被改。
    - Firefox 140（build 1489）、WebKit 26（build 2191，代替 Safari 實機）：用 Playwright 1.58 經 `executable_path` 指向本機已安裝的舊版 build。1.58 預設要找 1509／2248，本機沒有，也沒有另外下載。這是非標準的 driver 與 browser 搭配，但驗證內容是 DOM 行為，與 driver 版本無關。
    - Windows desktop shell（GUI build，WebView2 154）：經 CDP（`--remote-debugging-port`）連線，在隔離的 mutex、title、data-dir 與 `WEBVIEW2_USER_DATA_FOLDER` 下執行。
      - `window.open` 沒有被 shell 攔截。shell 沒有註冊 `NewWindowRequested`，所以由 WebView2 預設開一個獨立的頂層視窗（有網址列 `about:blank`，會出現在工作列）。
  - 截圖與腳本放在 scratchpad（`popup-*.png`、`popup_check.py`、`desktop_check.py`）。
  - 順帶確認 `PRISM-OPT-72`：GUI build 跑過之後，`desktop-shell.log` 仍是 0 bytes。
- `PRISM-OPT-65`（本機驗證；未發版、未部署 Pi）：
  - 前端 `BackupImportSection.tsx`：
    - JSON 匯入成功後讀取 `skipped_attachments`、`skipped_uploads`，缺值時視為 0。任一個大於 0，就在 JSON 匯入列下方顯示 inline 的 `role="status"` 提示。
    - 用 inline 而不用 toast，因為 toast 很快就消失，這類資料有損的訊息需要讓使用者讀得到。
    - 原本的成功 toast 保留。
    - 型別：`api.ts` 的 `importJSON` 回傳型別新增這兩個 optional 欄位，屬 additive，API 本身沒改。
    - 文案：四語 i18n 新增 `importSkippedSeparated`（N 個已拆分的長文只匯入了預覽，要完整還原請用 Full snapshot）與 `importSkippedUploads`（N 張同名圖片已存在，沿用原有的那張）。
  - 驗證：
    - 新增 `e2e/test_import_skip_warning.py`，共 5 條，透過 UI 選檔匯入，含 CJK 資料：
      - 拆分筆記：1280 與 390 都會出現提示，數字正確。
      - 普通 JSON：1280 與 390 都不會出現提示。
      - 同名圖片第二次匯入：會出現圖片那一行提示。
    - HEAD 上會失敗的有 3 條（拆分 ×2、圖片 ×1）。
    - `-Release` gate 通過（e2e 47）。
    - 用 sonnet 實作；改動小、e2e 直接涵蓋驗收，由主代理驗收。
- `PRISM-OPT-67`（本機驗證；未發版、未部署 Pi；由 opus 實作）：
  - 檔名：
    - `uploads.go` 新增共用 helper：`filenameWordRune`（`IsLetter`／`IsNumber`／`IsMark`）、`finishSafeFilename`（180 byte 截斷，保留副檔名，不切斷 UTF-8；去掉結尾的點與空白；Windows 保留名稱加 `_` 前綴）、`windowsReservedFilename`。
    - 附件的 `sanitizeAttachmentFilename` 與圖片的 `safeUploadFilename` 都改用這組 helper。
    - 結果：`說明.md` 存成 `說明_<時間戳>.md`，標題是「說明」；`圖片測試.png` 可以上傳，縮圖照常產生。
    - 原本被拒的原因：sanitize 之後只剩下 `png`，沒有副檔名。
  - 配套（允許 CJK 檔名後，需要同步修的資料安全問題）：所有「是否仍被引用」的判斷，都同時認原字串、`url.PathUnescape` 後的字串，以及重新編碼後的字串。
    - 範圍：孤兒掃描與刪除、`POST /api/upload/delete`、刪除筆記（單筆與批次）、OPT-20 的 `mediaProtected`、壞路徑判斷。
    - 解碼失敗時只用原字串比對。
    - 主代理另外把 `otherNoteImageReferenceCount` 的封面比對從 `=` 改成 `LIKE`，讓小寫 hex 的封面也受到保護。
  - 驗證：
    - `go-shadow/upload_filenames_test.go`：
      - sanitize 對照表（中、日、韓、NFD、`../`、`a\b`、`CON`／`nul`、`<>:"|?*`、控制字元、300 個漢字）。
      - 附件與圖片各一個 HTTP 測試。
      - percent-encoded 引用的保護：修正前，`/api/upload/delete` 實際刪掉了仍在使用的原圖與縮圖。
      - `mediaProtected`、ASCII 結果不變，以及小寫 hex 封面（修正前失敗）。
    - prism-verifier 獨立驗收：
      - 逐條檢查所有會刪檔的路徑，都只有變得更保守。
      - 20 萬筆隨機輸入的 property test，加上全形斜線、UNC、`C:` 等路徑逃逸案例，都安全。
      - 60 個 ASCII 名稱與 HEAD 比對，只有刻意的差異：保留名稱、結尾的點、截斷。
      - 隔離 runtime 實測：原始寫法與編碼寫法（含大小寫混用）的引用，刪除筆記後檔案都還在，三種清理預覽都沒有列出使用中的圖片。
    - `-Release` gate 通過（pytest 427、e2e 47）；主代理修完封面比對後，`go test ./...` 也通過。
  - 已知（低）：
    - 刪除原圖時，不會改寫編碼寫法的引用（HEAD 原本就是這樣；現在可以用「修復壞路徑」修好）。
    - export JSON 會多列出解碼後的檔名。極端情況是手寫的 `%3A` 會讓 Windows 上的匯入失敗。
    - 同一秒內上傳同名附件會互相覆寫（HEAD 原本就是這樣）→ 已開 `PRISM-OPT-74`。
- `PRISM-OPT-69`（本機驗證；未發版、未部署 Pi）：
  - 前端：`deleteNote` 與 `deleteSelectedNotes` 成功後，多呼叫一次 OPT-32 的 `refreshLoadedNotes()`。本地先濾掉被刪筆記的即時回饋保留；Library total 一樣只刷新 1 次。
  - 刪除後的請求：列表請求數等於已載入的頁數，`/api/test` 打 1 次。
  - 驗證：
    - 新增 `e2e/test_delete_refreshes_list.py`，共 3 條：
      - 載入 2 頁後刪掉第 5 筆，再 load-more：原本的第 41 筆有出現，沒有重複，順序正確。
      - 批次刪除 2 筆後再 load-more：不漏、不重複，捲動位移小於 60px。
      - 根→子→孫 刪掉子之後，孫卡片的 parent 顯示根、根卡片顯示「1 variants」；再刪掉根，孫卡片上就沒有根的標題。
    - 在 HEAD 上 3 條都失敗，原因是沒有刪除後的列表重抓。
    - `-Release` gate 通過（e2e 50）。
    - 改動只有兩行，由主代理讀 diff 驗收。
  - 已知（低）：
    - 刪除視窗上方的卡片後，捲動位置沒有測。grid 有 `overflow-anchor:none`，可能會有位移。
    - refresh 回來之前，列表會短暫少一筆。
- `PRISM-OPT-70`（本機驗證；未發版、未部署 Pi）：
  - **判定：產品競態，而且會遺失內容**（測試的等待方式讓它更容易發生）。
    - 新筆記第一次存檔時依序執行 `POST`、`GET /api/notes/{id}`、`openEditor(inPlace)`，`savingRef` 要到最後的 `finally` 才放掉。整段期間再按 Ctrl+S，會碰到 `if (savingRef.current) return`，被靜默吞掉。
    - 結果：畫面上是第二版，伺服器上仍是第一版。
    - 完整 e2e 負載高時，GET 變慢，第二次 Ctrl+S 就更容易落在這段期間。
  - 前端 `useNoteForm.ts`：存檔進行中按 Ctrl+S（`close:false`）時，先記下「待存」。`isSaving` 變回 false 之後的第一次 render 由 effect 補存一次；這時已經有最新內容和剛建立的筆記，所以送出的是 PUT，不會重複建立。Ctrl+S 的語意與 API 不變。
  - 測試：
    - 原測試改成等明確的 POST／PUT 回應，並用 `GET /api/notes/{id}` 讀完整內容。
    - 新增 `test_ctrl_s_during_first_save_of_new_note_saves_latest_text_once[create|fetch]`，用 `page.route` 卡住第一次 POST 或建立後的 GET。
    - source-lock `tests/test_project_optimization_p0_frontend.py` 同步更新。
  - 驗證：
    - 修正前兩個新測試都失敗（等不到 PUT，伺服器上是第一版）。
    - 原測試連跑 20/20 通過；完整 `pytest e2e` 連跑 3 次都是 52 passed。
    - `-Release` gate 通過。
    - 由 prism-engineer 診斷與實作，主代理讀 diff 驗收。
  - 已知（低）：第一次存檔失敗時，排隊的 Ctrl+S 會再試一次，可能出現兩次錯誤 toast。
- `PRISM-OPT-71`（本機驗證；桌面版）：
  - 讀 code 確認：
    - 每日還原點原本就是原子寫入（`VACUUM INTO .db.tmp` → 驗證 → rename），而 `db.Close()` 會等 VACUUM 跑完，所以不會出現壞掉的 `.db` 還原點。
    - 唯一的缺口：在 VACUUM 與 rename 之間結束程序，會留下 `.db.tmp`，而且之後一直沒人清。
  - Go：
    - `server` 新增可選欄位 `beforeExit`，`triggerRestart` 在 DB 關閉之後、結束程序之前呼叫一次。
    - `os.Exit` 抽成 `exitProcess`，方便測試替換。
    - desktop shell 把 `beforeExit` 設成「移除 tray icon」：`deleteTrayIcon` 改用 `atomic.Bool` CAS，最多只移除一次。
    - `ensureDailyRestorePoint` 在 `managedBackupMu` 鎖內，先清掉殘留的 `prism_backup_*.db.tmp`。
  - 驗證：
    - `restore_test.go` 新增 4 個測試：
      - 殘留 tmp 會被清除（修正前失敗）。
      - `beforeExit` 只呼叫一次，且在 DB 關閉之後、exit 之前。
      - 沒有 `beforeExit` 時，照常 exit。
      - 守門測試：約 40MB DB、4 種時序，重啟與還原點交錯，不會留下壞掉的備份。
    - desktop smoke：隔離的 mutex、title、data-dir、WebView2 profile，3 組各重啟 3 次。每輪都是 1 個程序、1 個視窗；log 每次都有 `tray icon removed before restart: ok=true`；正常關閉後沒有殘留。
    - `-Release` gate 通過（pytest 427、e2e 52）。
  - 未能觀察：這台 Windows 11 連 HEAD 對照組都看不到幽靈 icon，所以 tray 的證據只有 `NIM_DELETE` 的回傳值與 code。
  - 已知（低）：
    - smoke 的頭兩組第 1 輪，WebView2 新視窗分別延遲了 46s 與 14.8s 才出現（Go 在 0.8s 內就 healthy）。其中一次有 WebView2 子程序殘留，已手動清除。之後 7 次都正常，原因沒有查明。
    - Pi 上 rotate 若被中斷，留下的 tmp 不會被清。
- `PRISM-OPT-72`（本機驗證；桌面版）：
  - 原因（已重現確認）：`configureDesktopLog` 原本是 `io.MultiWriter(previous=stderr, file)`。GUI build 沒有有效的 stderr，寫入第一個 writer 就失敗，而 MultiWriter 遇到錯誤即停止，所以檔案永遠寫不到內容。
  - 修正：`desktop_shell_windows.go` 改成 `io.MultiWriter(file, previous)`。`log.Printf` 不理會 `Output` 回傳的錯誤，因此 stderr 失敗也無妨。log 的位置、輪替，以及非 desktop 的 runtime 都沒動。
  - 驗證：
    - `TestConfigureDesktopLogWritesFileWhenStderrFails`：用一定會失敗的 writer 模擬 stderr，log 檔內容含 CJK。修正前 log 檔是空的，測試失敗。
    - GUI smoke：不導向 std handle 的情況下，修正前 log 為 0 bytes，修正後 1053 bytes（含 `log opened`、`listening on`、每日還原點）。debug 版的 stderr 與 log 檔兩邊都有內容。
    - fast gate 通過。
    - 改動只有一行，由主代理驗收。
- `PRISM-OPT-73`（本機驗證；未發版、未部署 Pi）：
  - 前端：
    - `Header.handleOpenReadingWorkspace` 先試 activeId，再依清單順序往下試。遇到 404 就用 `removeNote` 移除並繼續，第一個成功的就開啟；全部都 404 時，toast 一次 `reading.workspaceAllDeleted`（四語）。
    - `ReadingView` 目前項目回 404 時，從清單移除，依序改試後面、再試前面的項目；全部都沒了就提示並關閉。
    - 非 404 錯誤維持原行為：保留項目，顯示錯誤。
    - 一律沿用 `useReadingWorkspace` 既有函式，不改 localStorage。
  - 驗證：
    - 新增 `e2e/test_reading_deleted_active.py`，共 4 條：
      - Header 跳過被刪的 active，開啟下一筆。
      - 全部刪除時只提示一次，每個 id 只打一次 GET，沒有 console error。
      - ReadingView 的目前項目被刪除後，會移出清單並切換。
      - active 回 500 時保留項目並顯示錯誤。
    - HEAD 上前 3 條失敗；第 4 條是守門測試，所以會通過。
    - source-lock `tests/test_reading_workspace.py` 已同步更新。
    - `-Release` gate 通過（pytest 427、e2e 56）。
    - 由主代理讀報告與 gate 驗收。
  - 已知（低）：閱讀途中才被刪除的筆記，要等下次切換或重新讀取時才會處理，和 OPT-38 一樣採懶處理。
- `PRISM-OPT-74`（本機驗證；未發版、未部署 Pi）：
  - Go：
    - 新增 `createAttachmentFile`：用 `O_EXCL` 依序嘗試 `<base><ext>`、`<base>_2<ext>`，最多到 `_1000`。名稱已被占用就換下一個；其他錯誤直接回傳；永遠不覆寫既有檔案。
    - 附件上傳改用這個函式，時間戳改用既有的可替換時鐘 `uploadNow`。
    - 複製筆記時的一般附件（`_copy_`）改用 `copyAttachmentFile`，原本的 `copyFileAtomic` 會先刪掉目的檔。`docs/notes/note_<id>.md` 是固定命名，維持原樣。
    - 失敗時只刪除這次新建的檔案；沒有新增鎖，沿用 `noteFilesMu`。
  - 驗證：
    - 新增 `go-shadow/attachment_no_overwrite_test.go` 的 4 個測試，都經 HTTP handler、資料為 CJK、固定時鐘。修正前 4 個都失敗，修正後都通過：
      - 同秒上傳三個同名附件，三個檔案都在，各自讀回各自的內容。
      - 預先放好的同名無關檔案，內容不變。
      - insert 失敗時，只清掉新檔，既有檔案不動。
      - 複製筆記時，不會覆寫既有的同名 `_copy_` 檔。
    - `-Release` gate 通過（pytest 427、e2e 56）。
    - 主代理讀 diff 驗收。
  - 已知：
    - 圖片上傳（`uploads.go`，`<時間戳>_<檔名>` 加 `os.WriteFile`）也有同秒同名覆寫的問題，原圖與縮圖都會被蓋掉 → 已開 `PRISM-OPT-75`。
    - `note_<id>.md` 在還原舊 DB、序號回捲後，可能蓋掉孤兒檔；屬筆記檔範圍，不在本單。
- `PRISM-OPT-75`（本機驗證；未發版、未部署 Pi）：
  - Go `uploads.go`：新增 `createUploadFiles`／`claimUploadName`，原圖與縮圖成對建檔。
    - 命名：原圖 `<主體><ext>`，縮圖 `<主體>_thumb.webp`。只要任一名稱已被佔用，主體就改成 `_2`、`_3`… 再試。
    - 建檔方式：兩個檔都用 `O_EXCL`（共用既有的 `createImportFile`）。縮圖建檔失敗時，只刪掉剛建立的原圖。
    - 只寫其中一邊時（thumbnail_only，或沒有縮圖），用 `Lstat` 確認另一個名稱是空的。
    - `/api/upload`、`/api/upload/url`、Markdown 匯入都走這條路徑。JSON 匯入維持 OPT-64 的 skip 規則，`import.go` 沒有改動。
  - 驗證：
    - 新增 `go-shadow/upload_no_overwrite_test.go`，使用固定時鐘與 CJK 檔名。修正前 4 個 HTTP 測試都失敗，修正後都通過：
      - 同秒上傳兩張同名圖片：兩組原圖加縮圖都在，URL 不同，GET 讀回各自的 bytes，縮圖寬度分別是 64 與 80。
      - thumbnail_only 同秒上傳兩次。
      - 預先放好與原圖名或縮圖名相同的無關檔案：該檔不變，新上傳的那對變成 `_2` 且成對，不會留下孤立的原圖。
      - `/api/upload/url` 同秒同名，用 fake transport 模擬。
    - 既有的 OPT-67 測試 `TestImageUploadAcceptsUnicodeFilename` 原本隱含「第二張覆寫第一張」的行為。現在改成每一輪檢查完就刪掉該檔，檔名斷言保持不變。
    - `-Release` gate 跑了 3 次：2 次全綠；1 次是無關的 `test_reading_lazy_detail` 失敗 → 已開 `PRISM-OPT-76`。
    - 主代理讀 diff 驗收。
  - 已知（低）：只寫其中一邊時，另一邊的名稱只用 `Lstat` 檢查，沒有實際預留，極少數情況下配對可能錯開，但不會覆寫任何檔案。
- `PRISM-OPT-76`（測試修正，未改產品程式）：
  - 原因：`e2e/test_reading_lazy_detail.py` 用 `next(i for i in range(10, 40) if created[i] in shown)` 挑第 1 頁的筆記，前提是第 1 頁一定會出現第 10～39 筆。
    - 但列表依 `is_pinned DESC, updated_at DESC` 排序，`updated_at` 只精確到秒，同一秒建立的筆記順序不固定。
    - 完整 e2e 執行時，其他測試留下的資料也會占掉第 1 頁的位置。
    - 這個範圍可能整個落空，於是拋出 `StopIteration`。CI 在 `fc1b9aa` 那次就是因此變紅。
  - 修正：測試建立的 50 筆改成置頂，讓其他測試留下的非置頂筆記擠不掉它們；`pos` 改成在 1～47 之間，從 DOM 實際顯示的項目中挑。其他斷言都沒動。
  - 驗證：
    - 以 20 筆置頂筆記佔滿第 1 頁，重現了原本的 `StopIteration`。
    - 修正後，單檔連跑 20/20 通過；完整 `pytest e2e` 連跑 3 次都是 56 passed。
    - `-Release` gate 通過。

### Pi 部署紀錄（2026-10-07，使用者逐步授權）

- **1. 部署前備份**：`/home/mask0709/prism-predeploy-20261007-190419/`（299M），內含：
  - `sqlite3 .backup` 產生的一致 DB，`integrity_check` = ok；
  - `knowledge.db.bak`；
  - `static/uploads`、`docs/attachments`、`docs/notes`、`config`，共 2575 個檔案，`SOURCE.sha256` 逐檔比對通過；
  - 筆記 299 篇、附件列 102 筆，與線上相同。

  這個資料夾不在 `prism/backups/` 之下，部署腳本不會清除它。
- **2. 部署**：`scripts/go_primary_pi_live_ops.ps1 -Mode Cutover`（main `f7c2be5`）exit 0，線上 full workflow smoke 通過。
  - 證據在 `build/go-primary-live/pi/`。
  - 部署後狀態：
    - `/healthz` 的 `mode` = `go-runtime`，schema 17/17，pending 為空，journal 沒有錯誤；
    - 筆記 299、附件列 102、uploads 2478，與部署前相同；
    - 線上 smoke 留下 3 個沒有被使用的標籤 `t042-live-go-primary-*`（id 667–669），待使用者決定是否刪除。
  - **OPT-36 Pi 重啟 smoke**：`POST /api/server/restart` 之後，systemd 收到 exit 42 並重新拉起，5.8s 後 `/healthz` 恢復 200；PID 從 1256566 變成 1256847，筆記仍是 299。
    - 低：systemd 會把 exit 42 記成「Failed with result 'exit-code'」再重啟，只是日誌外觀問題。
- **3. OPT-20 在 Pi 上執行**：
  - dry-run：merge 77、history 1、skipped 24（missing_file 23、preview_mismatch 1）、orphan_files 5。
  - 執行結果：merged 77、historied 1，failed 0、move_failed 0。
  - 還原點：`backups/separated-notes-20261007_190834_141235567/restore_point.db`，78 個檔案移到同一個資料夾隔離。
  - 驗證：
    - 再跑一次 dry-run，actionable = 0；
    - `quick_check` ok；
    - 77 篇合併後的 `Notes.content` 與隔離檔案的全文逐字一致（換行正規化後）；
    - note 88 新增一筆 history「合併長文：保留附件全文」；
    - 搜尋 note 100 尾段的詞「與黑市地緣」會命中 100（合併前尾段詞搜不到）；
    - uploads 仍是 2478。
  - 仍待處理：23 篇筆記的全文檔案早已不存在，1 篇（海酒食堂）預覽不一致，另有 5 個孤兒檔 → 已開 `PRISM-OPT-77`。
- `PRISM-OPT-77`（唯讀調查完成；使用者決定維持現狀）：
  - 結論：遺失全文的有 24 篇。除了 23 筆 `missing_file`，note 67 也算在內，因為它現存的 `note_67.md` 其實是另一篇筆記。這些全文**從來沒有到過 Pi**，Pi 上一篇都找不回來。
  - 遺失原因：2026-03-15 搬遷時，DB 與 uploads 是從日常使用版複製的，`docs/` 卻是從開發 repo `d:\AI\Prism\docs` 整包 `scp` 過去的。證據：
    - `created_at < 2026-03-16` 的附件列（id 1–25）全部是壞的，之後建立的全部完好。
    - 孤兒檔 `note_65/67/68.md` 的 git blob 與 repo commit `24607f4`／`abbafb4` 的測試資料一致。
    - `docs/` 有 20 個檔案的 mtime 都是 2026-03-15 20:47:14，與 Pi 上的 `deploy_to_pi.bat` 一致。
    - 搬遷前的 `knowledge.db.bak` 只有 1 篇筆記。
  - 查過的來源，都沒有全文：
    - Pi 上 28 個 Prism DB（最早是 2026-06-01）；
    - `Note_History`：只存了預覽，34 與 45 另有比全文短的早期版本；
    - 所有 `data-files.tar.gz`：不含 `docs/notes`；
    - `~/backups`、releases、staging：都是其他專案。
  - 孤兒檔：
    - `note_65`、`note_68` 是 repo 的測試資料，不需要保留；
    - `note_256`／`note_257` 與現存的 note 214 逐字相同；
    - `note_190` 是已刪除筆記「路邊烤肉 WildBBQ」的較長版本（5,295 字），只存在這個檔案裡，要不要保留由使用者決定。
  - 待使用者確認的來源，可能性由高到低：
    1. 日常使用版 `D:\Program Files\Prism_V2\docs\notes\`；
    2. 如果日常使用版搬過位置，新位置下的 `docs\notes\`；
    3. 桌面版 PrismData；
    4. 手邊的 Full snapshot 或 03-15 前後的備份；
    5. 資源回收筒、檔案歷程記錄、雲端版本紀錄。

    `D:\AI\Prism\docs\notes\` 是 repo 的測試資料，不是來源。
  - 找不到時的替代做法：從原始網址重新擷取並另建新筆記；34、45 可以改用 history 裡的早期版本。
  - 完整的逐筆表格在調查報告（scratchpad 的 `opt77_report.md`）；結論已整理在本段。
  - 範圍外的發現：Pi 的 `docs/attachments` 裡有 11 個 `20251230` 的檔案，同樣是 03-15 從 repo 複製過去的測試資料 → 已開 `PRISM-OPT-79`。
  - **使用者決定（2026-10-07）**：使用者說明，Pi 才是日常使用的環境，3 月以前的資料應該是複製來的備份。先查標題是否重複，沒有重複就維持現狀。
    - 唯讀查詢 Pi DB 的結果：
      - #5 山堺The Woods 與 #333 同名，#333 是完整版（6,129 字）；
      - #8 與 #57「尚牛二館」彼此同名，兩篇都只有預覽；
      - #70 與 #38 同名（兩篇都很短）；
      - #45 有後續版本 #46「claude.md-自更新2-最佳化版」；
      - #50 與 #196 是同一家店（#196 是 1,093 字）；
      - 其餘 19 篇沒有重複。
    - 結論：**24 篇都維持現狀，不還原**，本單結案。
    - 重複的預覽副本：使用者表示 #5／#333 這類標題大概是測試用的，不用處理（2026-10-07）。
- `PRISM-OPT-79`（使用者 2026-10-07 選 A 並同意執行指令）：
  - 唯讀確認：
    - Pi 的 `docs/attachments` 有 11 個 `*_20251230_*.md`，mtime 都是 2026-03-15 20:47:14。
    - 沒有任何 `Note_Attachments` 列引用這 11 個檔案；資料庫裡指向 `docs/attachments` 的列為 0。
    - 11 個檔案都已在 repo git 歷史中，最早出現在 `abbafb4`（2025-12-30），內容一致。
    - 同名的 note #277「人類五指的神經限制」本身就是完整版（OPT-20 已合併）。
  - 處理：搬移，不刪除。搬到 `/home/mask0709/prism/backups/repo-leftover-attachments-20261007/`，用的是 `mv -n`，`MANIFEST.sha256` 記下每個檔案的雜湊。
    - 搬移前再查一次引用數，仍為 0。
    - 搬移後：雜湊逐檔比對通過、隔離資料夾內有 11 個檔、原資料夾已清空、`/healthz` 回 200。
    - 要還原：`mv "$Q"/*_20251230_*.md /home/mask0709/prism/docs/attachments/`。
- `PRISM-OPT-78`（本機驗證；下次 Pi cutover 生效，因為部署時會上傳本機的 smoke 腳本）：
  - `scripts/go_primary_full_workflow_smoke.py` 新增 `remove_smoke_tags`。刪掉自己的筆記之後，只刪名稱完全等於本次 label 的 3 個 smoke 標籤（`-go-primary`、`-go-primary-updated`、`-imported`），而且必須沒有掛在任何筆記上；刪完重新列出確認，有殘留就讓 smoke 失敗。
  - runtime 沒有 `local-tag-write`（例如 package smoke）時不刪，在證據檔記錄 `skipped`。這是明確記錄，不算成功。
  - 驗證：
    - 修正前，package smoke 的 DB 留下 `t039-windows-package-*` 三個標籤。
    - 修正後，package smoke 通過，`smoke_tag_cleanup.status = skipped`。
    - 用與 Pi 相同的完整 flag 開一個隔離 runtime 跑 smoke：`removed` 三個標籤，DB 只剩 `Welcome`。
    - fast gate 通過。
- **4. 發版 V2.7.0**：tag `V2.7.0` → `a478a8b`，GitHub Actions `37613790399` success。GitHub Release 附 `PrismDesktopPortable-v2.7.0.zip`，SHA256 `3a743a9f…d66d60f`，重新下載後比對一致。之後再 cutover Pi 一次，`/api/test` version 為 2.7.0，schema 17/17，筆記 299。每次 cutover，線上 smoke 都會留下 3 個空標籤，兩次都已刪除 → 已開 `PRISM-OPT-78`。

### P1 — 下一輪

| 工單 | 摘要 | 狀態 | 依賴 | Finding |
|---|---|---|---|---|
| PRISM-OPT-20 | 「合併長文回筆記」維護動作（dry-run、先建還原點、檔案移入隔離資料夾） | Done | 19、60 | FEAT-02、PERF-01 |
| PRISM-OPT-21 | `Ctrl+S` 存檔後留在編輯器；未存變更時以 `beforeunload` 保護 | Done | — | UX-02 |
| PRISM-OPT-22 | 預覽狀態的最小語意修正（標題不 autofocus） | Done | 建議在 21 之後 | UX-03 |
| PRISM-OPT-23 | 匯出範圍文案誠實化（JSON、Markdown、.db） | Done | — | FEAT-03 |
| PRISM-OPT-24 | 版本單一來源（由 runtime 提供，移除寫死的版本號） | Done | — | TECH-01 |
| PRISM-OPT-25 | `frontend/node_modules` 移出版控；清除死資產與死 script | Done | — | TECH-04 |
| PRISM-OPT-26 | 補強 behavior test；fast／release gate 分流；historical marker | Done | 建議在 15、18、19 之後 | TECH-02 |
| PRISM-OPT-27 | 治理文件瘦身、修正斷鏈、解除 docs-lock 測試耦合 | Done | — | TECH-03 |
| PRISM-OPT-28 | 桌面版每日自動還原點 | Done | — | OPS-02 |
| PRISM-OPT-29 | LAN 管理邊界：先修正文件，再決定是否收緊 | Done | 第二階段已決定不收緊 | OPS-04 |
| PRISM-OPT-52 | 子代理派工：依類別與難度指定模型與 effort（`.claude/agents/` + `docs/AGENT_DISPATCH.md`） | Done | — | 使用者需求 |
| PRISM-OPT-58 | JSON 匯入遇到已拆分筆記（`docs/notes` 附件）時不再整批失敗 | Done | — | OPT-19 追蹤 |
| PRISM-OPT-64 | JSON 匯入不得刪除或覆寫目標端既有的檔案（rollback 會刪掉原有檔案） | Done | — | OPT-58 追蹤 |
| PRISM-OPT-66 | 刪除附件時不得刪掉其他附件列仍在用的檔案（匯入後共用檔案會被誤刪） | Done | — | OPT-64 追蹤 |
| PRISM-OPT-59 | 編輯器開著時從 palette 開另一則筆記，確認不會存錯筆記（先重現） | Done | — | OPT-19 追蹤 |
| PRISM-OPT-61 | 桌面版（WebView2）關閉視窗時保護未存變更 | Done | 21 | OPT-21 追蹤 |
| PRISM-OPT-62 | 對話框無障礙：`Modal`／`ConfirmDialog` 加上 `role="dialog"`、focus trap、關閉後歸還 focus | Done | — | OPT-22 追蹤 |
| PRISM-OPT-63 | 編輯器有未存變更時，app 內導覽（上一頁、連結、palette 導覽）先詢問 | Done | — | OPT-59 追蹤 |

完成證據（2026-10-06）：

- `PRISM-OPT-27`：
  - `docs/ARCHITECTURE.md` 62.5KB → 約 12KB。
  - TODO、HANDOFF、ARCHITECTURE 的歷史原文移到 `docs/development-history/`（`todo-handoff-archive-20261006.md`、`architecture-go-migration-history-20261006.md`）。
  - 必讀改為分層、修正斷鏈、刪除重複的 `docs2/`。
  - 28 個測試改讀歸檔，斷言內容不變。
  - 驗證：`.loop/verify-gate.ps1` 通過（pytest 399 passed、`go test` ok）。commit `e77a631`。
- `PRISM-OPT-52`：
  - 新增 `.claude/agents/` 六個代理：scout＝haiku；docs、builder＝sonnet／medium；engineer＝opus／high；critical＝opus／xhigh；verifier＝opus／high、唯讀。
  - 派工矩陣在 `docs/AGENT_DISPATCH.md`，每張工單的派工在 `docs/WORK_ORDERS.md` 的派工總表。
  - `tests/test_agent_dispatch.py` 檢查三者一致，且能偵測故意製造的設定漂移。
  - 驗證：`.loop/verify-gate.ps1` 通過。新代理需重開 session 才會載入。

### P2 — 稍後

| 工單 | 摘要 | 狀態 | 依賴 | Finding |
|---|---|---|---|---|
| PRISM-OPT-30 | Mobile 排序控制與首屏密度 | Done | — | UX-04 |
| PRISM-OPT-31 | 筆記計數改用單一來源；Maintenance 改讀 `/api/system/stats` | Done | — | UX-05 |
| PRISM-OPT-32 | mutation 後就地更新，不再重置列表 | Done | 21 | PERF-02 |
| PRISM-OPT-68 | 刪除有 variant 子筆記的父筆記回 500（FOREIGN KEY constraint failed） | Done | — | OPT-32 追蹤 |
| PRISM-OPT-33 | Library 導覽去重（desktop 的 FilterStrip、重複三次的標題與計數） | Done | — | IA-01 |
| PRISM-OPT-34 | Settings 重新分組（Library & Editor、Images & storage、tab 深連結） | Done | — | IA-02 |
| PRISM-OPT-35 | Full snapshot 手動還原說明 | Done | — | OPS-03 |
| PRISM-OPT-36 | Server dashboard 的 Restart：接上真正的重啟，或移除 | Done | — | OPS-05 |
| PRISM-OPT-37 | 使用者看得到的遷移期字串改為中性文案 | Done | — | TECH-05 |
| PRISM-OPT-38 | Reading list 預取加上限或改為 lazy detail | Done | — | R0812:PERF-03 |
| PRISM-OPT-39 | JSON 匯出與匯入補齊欄位（置頂、封存、譜系、版面） | Done | 23 | FEAT-03 |
| PRISM-OPT-53 | Mobile 在非 Library 頁面也有搜尋入口 | Done | — | OPT-17 追蹤 |
| PRISM-OPT-54 | 附件刪除按鈕在觸控裝置上的點擊範圍 | Done | — | OPT-16 追蹤 |
| PRISM-OPT-55 | 從非 Library 頁面搜尋只送出一次請求 | Done | — | OPT-17 追蹤 |
| PRISM-OPT-56 | 搜尋正規化：韓文子字串、全形英數、混合查詢語意 | Done | — | OPT-18 追蹤 |
| PRISM-OPT-57 | 附件 popup 跨瀏覽器與 desktop shell 驗證 | Done | — | OPT-16 追蹤 |
| PRISM-OPT-65 | JSON 匯入後提示「拆分筆記只匯入了預覽」 | Done | 58 | OPT-58 追蹤 |
| PRISM-OPT-67 | 上傳附件與圖片的 CJK 檔名被濾掉或拒絕（`說明.md` 變成 `_<時間戳>.md`；`圖片測試.png` 回 Invalid file type） | Done | — | OPT-66 追蹤 |
| PRISM-OPT-69 | 刪除後 load-more 用舊的頁面位移，可能漏掉一筆 | Done | 32 | OPT-32 追蹤 |
| PRISM-OPT-70 | e2e `test_ctrl_s_saves_new_note_keeps_editor_open_and_updates_same_note` 在完整 gate 下偶爾失敗 | Done | — | OPT-34 驗收 |
| PRISM-OPT-71 | 桌面版重啟：殘留幽靈 tray icon；重啟可能撞上每日還原點寫入 | Done | 36 | OPT-36 追蹤 |
| PRISM-OPT-72 | 桌面 GUI 版 `logs/desktop-shell.log` 一直是 0 bytes | Done | — | OPT-36 追蹤 |
| PRISM-OPT-73 | 目前閱讀的筆記被刪除後，Header 的閱讀清單一直打不開 | Done | 38 | OPT-38 追蹤 |
| PRISM-OPT-74 | 同一秒上傳同名附件會覆寫前一個檔案（`O_TRUNC`） | Done | — | OPT-67 追蹤 |
| PRISM-OPT-75 | 同一秒上傳同名圖片會覆寫前一張（原圖與縮圖） | Done | — | OPT-74 追蹤 |
| PRISM-OPT-76 | e2e `test_reading_lazy_detail` 在完整 gate 下偶爾失敗 | Done | — | OPT-75 驗收 |
| PRISM-OPT-77 | Pi 上 23 篇拆分筆記的全文檔案遺失：調查能否從舊備份找回；1 篇預覽不符、5 個孤兒檔 | Done | — | Pi 部署 OPT-20 |
| PRISM-OPT-78 | Pi 部署的線上 smoke 每次都留下 3 個空的 `t042-live-go-primary-*` 標籤 | Done | — | V2.7.0 部署 |
| PRISM-OPT-79 | Pi `docs/attachments` 內 11 個 2026-03-15 從 repo 複製來的測試檔（疑似孤兒） | Done | — | OPT-77 調查 |

### P3 / Future — 需要證據或明確 promote

| 工單 | 摘要 | 狀態 | 啟動條件 | Finding |
|---|---|---|---|---|
| PRISM-OPT-40 | Prompt Builder：「AI optimize」改名、模板語系、seed 缺失時的死路 | Blocked | 使用者明確 promote | UX-06 |
| PRISM-OPT-41 | Prompt Builder seed config 內嵌到 binary；`pack.bat` 補帶 config | Blocked | 使用者明確 promote | OPS-06 |
| PRISM-OPT-42 | API 表面衛生：死 route、死 wrapper、未引用元件、API 文件標 deprecated | Blocked | 先確認外部 agent 的實際用途 | TECH-06 |
| PRISM-OPT-43 | 移除 capability flags；`go-shadow` 改名 | Blocked | 出現新增 runtime mode 的需求，或 flags 誤配的證據 | TECH-05 |
| PRISM-OPT-44 | 非中文使用者的首次體驗（雙語 welcome note 與模板） | Blocked | 有非中文使用者的證據 | BIZ-01 |
| PRISM-OPT-45 | FTS5 trigram 索引 | Blocked | 資料超過 1 萬筆，且 3 字以上的查詢占多數 | FEAT-01 |
| PRISM-OPT-46 | `Note_History` 保留策略 | Blocked | PRISM-OPT-20 之後出現 DB 成長的證據 | PERF-03 |
| PRISM-OPT-47 | 文字附件內容索引 | Blocked | PRISM-OPT-20 之後仍有約 50 個以上文字附件，且搜尋常態 partial | PERF-01 |
| PRISM-OPT-48 | 回收桶（軟刪除與復原） | Blocked | 出現誤刪事件的證據 | FEAT-05 |
| PRISM-OPT-49 | 桌面版與 Pi 之間跨裝置同步 | Blocked | 有多裝置寫入的證據；先完成 PRISM-OPT-35 | FEAT-06 |
| PRISM-OPT-50 | Prompt options 自訂 UI | Blocked | 有使用者需求的證據 | FEAT-07 |
| PRISM-OPT-51 | Wiki 連結與 backlinks | Blocked | 有使用者需求的證據 | FEAT-08 |

---

## Deferred Candidates

- [ ] `DEEP-SCAN-RISK-CANDIDATE-01` 01H 仍是低優先維護 triage（狀態：`Blocked`）：剩餘 frontend bundle/Browserslist warning、歷史 frozen docs/test wording仍需另行 promote；其中 `go-shadow/main.go` route-local 小整理已明確化為 `GO-MAIN-SPLIT-CANDIDATE-01`，但一次性 runtime 大拆分仍 `Blocked`。
- [x] ~~Pi 自動備份從每週改為每天~~（2026-10-07 使用者改變決定：**維持每週、最多 3 份輪替**，不改 timer，也不改 `keep_count=3`）。以下為原始紀錄：Pi 是使用者的主要使用方式，目前 systemd timer 每週一次，最壞會損失近 7 天的資料。另外，Pi timer 目前明確傳 `keep_count=3`（`DEPLOY-PI.md:134`），每週會把共用的 managed backup 修剪回 3 份；PRISM-OPT-28 已把預設改為 7，改 timer 時要一併改成 7。
- [ ] Desktop installer/updater/WebView2 bootstrap/shortcut automation（狀態：`Blocked`；需使用者明確需要 installer/updater 類能力）。
- [ ] Hidden/deferred i18n UI（`PortConfigSection`、`UpdateSection`、`TagInput`）（狀態：`Blocked`；只有日後恢復 render，才於該 gate 同步補四語 key）。2026-10-06 審查確認 `UpdateSection`、`TagInput` 沒有被引用，是否刪除由 PRISM-OPT-42 決定。
- [ ] Mermaid 圖表渲染（狀態：`Blocked`；只有 `MARKDOWN-SYNTAX-CANDIDATE-01` 的 `MDS-05` 被明確 promote 後才可施工；不得順手導入 heavy renderer）。
- [ ] KaTeX 數學公式 / ABC 樂譜渲染（狀態：`Blocked`；目前凍結為備選，只有使用者明確重新開啟需求時才可施工）。
- [ ] AI / semantic search / embeddings / GraphRAG / auto-writing（狀態：`Blocked`；仍不在 active roadmap）。
- [ ] 內建登入、多使用者、OAuth、RBAC、cloud sync、directory watcher、background sync daemon、大型備份平台、一次性 editor rewrite（狀態：`Blocked`；來源為 `KNOWLEDGE-WORKFLOW-CANDIDATE-01` 的不採納清單）。
- [ ] Source URL 自動抓 title / link health（狀態：`Blocked`；需要外網或批次請求時，必須另開 privacy / timeout / user-triggered boundary，不得在讀取 note 時背景追蹤遠端 URL）。
- [ ] 刪除 note 時一併刪除「只被這些卡片使用的圖片」（狀態：`Blocked`；只能以 opt-in、預設不勾的方式另開 decision gate；不得改 current Go delete/media cleanup runtime semantics）。

---

## Release / Pi 規則

- 任何 release、tag 或 portable package 都必須依 `docs/RELEASE_CHECKLIST.md` 重跑 fresh validation；push 後確認 GitHub Actions 綠燈。
- Pi delivery 不是 release 的自動副作用；每次上線都要依 `DEPLOY-PI.md` 重驗 service、migration、changed endpoint 與 UI evidence。

---

## Archive Index

- `docs/development-history/todo-handoff-archive-20261006.md`：2026-10-06 治理瘦身時移出的 TODO 完成項（EDITOR-COPY、MARKDOWN-SYNTAX、KWF-01～07、08-12 optimization roadmap、V2.6／V2.6.1 release 與 Pi gates、GO-MAIN-SPLIT、NOTE-DELETE-MEDIA、PI-PATH-MIGRATION）與 HANDOFF 長版 current state。
- `docs/development-history/architecture-go-migration-history-20261006.md`：從 `docs/ARCHITECTURE.md` 移出的 Phase 18–23 與 T004–T053 歷史敘事、Frontend Redesign Intake。
- `docs/development-history/todo-handoff-archive-20260619-v2.5-stabilization.md`：2026-06-19 TODO/HANDOFF 瘦身時移出的 V2.5 收尾、完成 gate、release/package evidence 與 deferred notes。
- `docs/development-history/go-primary-runtime-completion-20260617.md`：T001-T053 Go primary migration 完成敘事、artifact 與完整任務表。
- `docs/development-history/desktop-backup-i18n-handoff-20260617.md`：2026-06-14 local desktop / backup / dashboard handoff、2026-06-17 Core UX 與 i18n 詳細完成記錄。
- `docs/development-history/desktop-portable-release-handoff-20260618.md`：Desktop Shell Phase 0-6、portable baseline、manual acceptance、README split 與 release packaging 邊界。
- `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`：Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。
- `docs/development-history/todo-changelog.md`：長版版本歷程。
- `docs/development-history/todo-completed-phases.md`：更早期完成 phase 與歷史工作清單。
