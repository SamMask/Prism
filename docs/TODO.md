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
- 最新 release 為 V2.6.1（tag 對齊 `7f5469c`）。2026-08-23 的 commit `70f04e7` 已部署到 Pi；之後的 commits 未發版、未部署。
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

### P1 — 下一輪

| 工單 | 摘要 | 狀態 | 依賴 | Finding |
|---|---|---|---|---|
| PRISM-OPT-20 | 「合併長文回筆記」維護動作（dry-run、先建還原點、檔案移入隔離資料夾） | Done | 19、60 | FEAT-02、PERF-01 |
| PRISM-OPT-21 | `Ctrl+S` 存檔後留在編輯器；未存變更時以 `beforeunload` 保護 | Done | — | UX-02 |
| PRISM-OPT-22 | 預覽狀態的最小語意修正（標題不 autofocus） | Done | 建議在 21 之後 | UX-03 |
| PRISM-OPT-23 | 匯出範圍文案誠實化（JSON、Markdown、.db） | Todo | — | FEAT-03 |
| PRISM-OPT-24 | 版本單一來源（由 runtime 提供，移除寫死的版本號） | Todo | — | TECH-01 |
| PRISM-OPT-25 | `frontend/node_modules` 移出版控；清除死資產與死 script | Todo | — | TECH-04 |
| PRISM-OPT-26 | 補強 behavior test；fast／release gate 分流；historical marker | Todo | 建議在 15、18、19 之後 | TECH-02 |
| PRISM-OPT-27 | 治理文件瘦身、修正斷鏈、解除 docs-lock 測試耦合 | Done | — | TECH-03 |
| PRISM-OPT-28 | 桌面版每日自動還原點 | Doing | — | OPS-02 |
| PRISM-OPT-29 | LAN 管理邊界：先修正文件，再決定是否收緊 | Done | 第二階段已決定不收緊 | OPS-04 |
| PRISM-OPT-52 | 子代理派工：依類別與難度指定模型與 effort（`.claude/agents/` + `docs/AGENT_DISPATCH.md`） | Done | — | 使用者需求 |
| PRISM-OPT-58 | JSON 匯入遇到已拆分筆記（`docs/notes` 附件）時不再整批失敗 | Todo | — | OPT-19 追蹤 |
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
| PRISM-OPT-30 | Mobile 排序控制與首屏密度 | Todo | — | UX-04 |
| PRISM-OPT-31 | 筆記計數改用單一來源；Maintenance 改讀 `/api/system/stats` | Todo | — | UX-05 |
| PRISM-OPT-32 | mutation 後就地更新，不再重置列表 | Todo | 21 | PERF-02 |
| PRISM-OPT-33 | Library 導覽去重（desktop 的 FilterStrip、重複三次的標題與計數） | Todo | — | IA-01 |
| PRISM-OPT-34 | Settings 重新分組（Library & Editor、Images & storage、tab 深連結） | Todo | — | IA-02 |
| PRISM-OPT-35 | Full snapshot 手動還原說明 | Todo | — | OPS-03 |
| PRISM-OPT-36 | Server dashboard 的 Restart：接上真正的重啟，或移除 | Todo | — | OPS-05 |
| PRISM-OPT-37 | 使用者看得到的遷移期字串改為中性文案 | Todo | — | TECH-05 |
| PRISM-OPT-38 | Reading list 預取加上限或改為 lazy detail | Todo | — | R0812:PERF-03 |
| PRISM-OPT-39 | JSON 匯出與匯入補齊欄位（置頂、封存、譜系、版面） | Todo | 23 | FEAT-03 |
| PRISM-OPT-53 | Mobile 在非 Library 頁面也有搜尋入口 | Todo | — | OPT-17 追蹤 |
| PRISM-OPT-54 | 附件刪除按鈕在觸控裝置上的點擊範圍 | Todo | — | OPT-16 追蹤 |
| PRISM-OPT-55 | 從非 Library 頁面搜尋只送出一次請求 | Todo | — | OPT-17 追蹤 |
| PRISM-OPT-56 | 搜尋正規化：韓文子字串、全形英數、混合查詢語意 | Todo | — | OPT-18 追蹤 |
| PRISM-OPT-57 | 附件 popup 跨瀏覽器與 desktop shell 驗證 | Todo | — | OPT-16 追蹤 |

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
- [ ] Pi 自動備份從每週改為每天（狀態：`Blocked`；2026-10-07 使用者同意方向，等下次 Pi 部署時依 `DEPLOY-PI.md` 另開 gate 處理）。Pi 是使用者的主要使用方式，目前 systemd timer 每週一次，最壞會損失近 7 天的資料。
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
