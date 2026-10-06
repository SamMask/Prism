# Prism Work Orders（工單規格）

> 本檔只放工單**規格**。工單**狀態**只看 `docs/TODO.md` 的看板，本檔不重複記錄狀態。
> 證據與背景見 `docs/PROJECT_OPTIMIZATION_REVIEW_2026-10-06.md`；每張工單都標了對應的 Finding ID。
> 一個 roadmap 全部結案後，本檔對應的章節移到 `docs/development-history/`，看板只留一行歸檔指標。

## 工單欄位

每張工單都有以下欄位：

- **Finding**：審查報告中的證據 ID。
- **優先級**：P0／P1／P2／P3／Future。
- **目標**、**原因**。
- **修改範圍**、**不要修改**。
- **行為規格**、**驗收**、**驗證**。

`Blocked` 工單另有 **啟動條件**：條件成立且使用者明確 promote 後，才改為 `Todo`。

## 共同規則

- 遵守 `AGENTS.md`／`CLAUDE.md`、`docs/GOVERNANCE.md` 與反膨脹原則：
  - 不新增 dependency。
  - API 只做 additive 變更。
  - 不升 schema 版本；真的需要時先開 decision gate。
- 不碰正式 `knowledge.db`；runtime 驗證一律使用隔離 data-dir 與 fresh DB。
- 狀態流轉：
  1. 開工時把工單在 `docs/TODO.md` 標為 `Doing`。
  2. 完成時寫入驗證證據、改為 `Done`，並更新 `HANDOFF.md`。
- UI 工單：
  - 檢查 loading、empty、error、success、disabled、keyboard、focus。
  - 在 desktop 與 390px 實際用瀏覽器驗證。
- 測試要求：
  - 行為改變必須有可執行測試（Go test、HTTP 或 e2e）；source 或文件字串斷言不算行為證據。
  - 搜尋或文字處理相關的工單，測試資料必須包含 CJK 內容。
- 共同驗證指令（各工單另有補充）：

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

---

## 派工總表

依 `docs/AGENT_DISPATCH.md` 的類別（R/D/F/B/T/X/V/O）與難度（S/M/L/XL）指定代理。代理的模型與 effort 定義在 `.claude/agents/`。「主代理」表示不派工，由主代理自行完成或驗證。

| 工單 | 類別 | 難度 | 實作代理 | 驗收 |
|---|---|---|---|---|
| PRISM-OPT-15 | X | M | prism-engineer | prism-verifier |
| PRISM-OPT-16 | X | S | prism-engineer | prism-verifier |
| PRISM-OPT-17 | F | S | prism-builder | prism-verifier |
| PRISM-OPT-18 | B | L | prism-engineer | prism-verifier |
| PRISM-OPT-19 | X | L | prism-critical（兩段式） | prism-verifier |
| PRISM-OPT-20 | X | XL | prism-critical（兩段式，可覆寫為 fable） | prism-verifier |
| PRISM-OPT-21 | F | L | prism-engineer | prism-verifier |
| PRISM-OPT-22 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-23 | D | S | prism-docs | 主代理 |
| PRISM-OPT-24 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-25 | T | M | prism-builder | prism-verifier |
| PRISM-OPT-26 | T | L | prism-engineer | prism-verifier |
| PRISM-OPT-27 | D | L | 主代理（已完成） | 主代理 |
| PRISM-OPT-28 | X | M | prism-engineer（決策後） | prism-verifier |
| PRISM-OPT-29 | X | M | 第一階段 prism-docs；第二階段 prism-engineer | prism-verifier |
| PRISM-OPT-30 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-31 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-32 | F | L | prism-engineer | prism-verifier |
| PRISM-OPT-33 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-34 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-35 | D | M | prism-docs；還原演練由主代理執行 | prism-verifier |
| PRISM-OPT-36 | B | L | prism-engineer | prism-verifier |
| PRISM-OPT-37 | B | S | prism-builder | 主代理 |
| PRISM-OPT-38 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-39 | X | M | prism-engineer | prism-verifier |
| PRISM-OPT-40 | F | S | prism-builder | 主代理 |
| PRISM-OPT-41 | B | S | prism-builder | 主代理 |
| PRISM-OPT-42 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-43 | B | L | prism-engineer | prism-verifier |
| PRISM-OPT-44 | F | S | prism-builder | 主代理 |
| PRISM-OPT-45 | X | XL | prism-critical | prism-verifier |
| PRISM-OPT-46 | X | L | prism-critical | prism-verifier |
| PRISM-OPT-47 | X | XL | prism-critical | prism-verifier |
| PRISM-OPT-48 | X | XL | prism-critical | prism-verifier |
| PRISM-OPT-49 | X | XL | prism-critical | prism-verifier |
| PRISM-OPT-50 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-51 | B | L | prism-engineer | prism-verifier |
| PRISM-OPT-52 | D | M | 主代理（已完成） | 主代理 |
| PRISM-OPT-53 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-58 | X | M | prism-engineer | prism-verifier |
| PRISM-OPT-59 | X | M | prism-engineer | prism-verifier |
| PRISM-OPT-54 | F | S | prism-builder | 主代理 |
| PRISM-OPT-55 | F | M | prism-builder | prism-verifier |
| PRISM-OPT-56 | B | M | prism-builder | prism-verifier |
| PRISM-OPT-57 | V | S | 主代理 | prism-verifier |

開工前若發現工單的實際範圍與上表的難度不符，以 `docs/AGENT_DISPATCH.md` 的矩陣重新判定，並在 `docs/TODO.md` 的證據中記錄調整。

---

## Roadmap 2026-10-06 — P0

### PRISM-OPT-15 — DB 複本下載改為一致快照

- **Finding**：OPS-01 ｜ **優先級**：P0
- **目標**：`GET /api/export/db` 下載的檔案一定包含最近一次提交的所有寫入。
- **原因**：
  - `handleExportDB` 直接 `http.ServeFile` live 主檔（`go-shadow/export.go:122-142`），會漏掉還在 WAL 裡的資料。
  - 實測：fresh DB 下載到沒有 `Notes` 表的空殼；checkpoint 之後的新增與修改都不在下載檔內。
- **修改範圍**：
  - `handleExportDB` 比照 `handleBackupDownload`（`go-shadow/backups.go:21-48`）：先用 `writeConsistentDBBackup` 寫到暫存檔、送出，最後刪除暫存檔。
  - 在 `go-shadow/main_test.go` 補測試。
- **不要修改**：API 路徑、檔名格式、Content-Type、gate 條件；`backups.go` 的行為；UI 版面。
- **行為規格**：使用者看不到任何差異，只是下載內容一定是最新的。
- **驗收**：
  - 測試開啟 DB 後寫入一筆（不 checkpoint），下載的 .db 必須包含這筆。
  - fresh DB 下載後可以查到 `Notes` 表。
  - 暫存檔不殘留。
- **驗證**：`cd go-shadow && go test ./...`；`pytest tests/ -v`。

### PRISM-OPT-16 — 附件檢視的安全輸出

- **Finding**：TECH-07 ｜ **優先級**：P0
- **目標**：檢視一般文字附件時，內容一律以純文字呈現；附件項目可以用鍵盤操作。
- **原因**：
  - `frontend/src/hooks/editor/useNoteAttachments.ts:89-97` 用 template literal 把原始內容寫進同源 popup，形成 HTML injection，繞過 DOMPurify 的安全邊界。
  - 附件項目是只有 `onClick` 的 `<div>`（`AttachmentPanel.tsx:55-96`），鍵盤無法操作；刪除按鈕只在 hover 時出現。
- **修改範圍**：
  - `handleLoadAttachment` 改用 DOM API 建立 `<pre>` 並設定 `textContent`，或先跳脫 HTML。
  - `AttachmentPanel.tsx` 的項目改用 `<button>`，或加上 `role`、`tabIndex` 並支援 Enter。
  - 刪除按鈕在 focus 時也要顯示。
- **不要修改**：auto-extracted 附件的載入流程（屬於 PRISM-OPT-19／20 的範圍）；上傳與刪除 API。
- **行為規格**：含 `<b>`、`<script>`、`</pre>` 的附件會原樣顯示為文字。
- **驗收**：
  - 回歸測試：e2e 驗證 popup 中不會出現注入的元素，或至少用 source test 鎖定不得以 `document.write` 寫入 `${attachmentContent}`。
  - 附件可以用 Tab + Enter 開啟。
- **驗證**：`cd frontend && npm run build`；`pytest tests/ -v`；browser 驗證。

### PRISM-OPT-17 — Header 全域動作改為 route-aware

- **Finding**：UX-01 ｜ **優先級**：P0
- **目標**：在任何 route 按 New 都能立刻開啟編輯器；在任何 route 送出搜尋都能看到結果。
- **原因**：
  - NoteEditor 只掛在 HomePage（`HomePage.tsx:617-623`）；Header 的 New（`Header.tsx:372`）與搜尋送出（`:63-66`）沒有導回 `/`。
  - 結果：在 Settings 或 Prompt Builder 會靜默失效，之後回到 Home 時編輯器自行彈出。
- **修改範圍**：`frontend/src/components/Header.tsx` 的 New 與 `handleSearchSubmit`，在 `!isHomeRoute` 時先 `navigate('/')`，寫法比照 `Header.tsx:116`。
- **不要修改**：`appStore`、HomePage 的 overlay 結構、API、i18n key。
- **行為規格**：
  - 從 `/settings` 或 `/prompt-builder` 按 New：導到 Library 並立即開啟「New note」。
  - 從同樣的頁面搜尋：導到 Library 並顯示結果。
- **驗收**：
  - browser smoke（desktop 與 390px）在兩個 route 各驗證 New 與搜尋。
  - 不再出現稍後才彈出的編輯器；console 沒有錯誤。
- **驗證**：`cd frontend && npm run build`；隔離 runtime 的 browser smoke；`pytest tests/ -v`。

### PRISM-OPT-18 — CJK 子字串搜尋

- **Finding**：FEAT-01 ｜ **優先級**：P0
- **目標**：
  - 中文與日文的詞出現在標題或內文的任何位置都能搜到。
  - Command Palette 對 CJK 輸入 2 個字就查詢 server。
- **原因**：
  - `Notes_FTS` 使用 `unicode61` tokenizer（`migrations.go:382-387`），查詢是逐 token 前綴（`notes_search.go:192-195,312-319`）。
  - 實測「工程」「角色設定」「夜景」「廣角」都回傳 0 筆。
  - palette 的門檻是 ≥3 字元（`CommandPalette.tsx:20,55`）。
- **修改範圍**：
  - `go-shadow/notes_search.go` `buildNotesSearchClause`：token 含 Han、Hiragana 或 Katakana 時，加上 `(LOWER(COALESCE(n.title,'')) LIKE ? OR LOWER(COALESCE(n.content,'')) LIKE ?)` 的 OR 分支；多個 token 之間 AND。token 已經過 `searchTokens` 淨化，不含 `%` 或 `_`。
  - `frontend/src/components/CommandPalette.tsx`：CJK 輸入的門檻改為 2。
  - Go test 使用中文 fixture。
- **不要修改**：FTS5 schema 與 tokenizer、migration、附件掃描上限、英文查詢的行為。
- **行為規格**：不需要額外 UI，查詢結果變得正確。
- **驗收**：
  - fixture「今天學習提示詞工程的方法，重點是角色設定與輸出格式。」對「工程」「角色設定」都能命中；「城市夜景」fixture 對「夜景」能命中。
  - 英文的既有測試全部不變。
  - 以 1,000 筆中文 fixture 量測查詢時間，記錄在 PR。參考值：10k × 1,800 字的 LIKE 約 227ms。
- **驗證**：`cd go-shadow && go test ./...`；`cd frontend && npm run build`；`pytest tests/ -v`。

### PRISM-OPT-19 — 停止新的長文拆分，修正已拆分筆記的存檔路徑

- **Finding**：FEAT-02 ｜ **優先級**：P0
- **目標**：新的長文留在 `Notes.content`；已拆分的筆記存檔後也回到 DB，不會再被舊附件覆蓋。
- **原因**：
  - 拆分讓匯出、歷史、DB 複本、API 只拿到 500 字預覽。
  - 實測：已拆分的長文改短並存檔後，編輯器重開時載入舊附件的全文（`useNoteAttachments.ts:21-26`）；再存一次就會覆寫新內容。
- **修改範圍**（`frontend/src/hooks/editor/useNoteForm.ts`）：
  - 移除儲存後呼叫 `separateContent` 的程式碼（`:123-129`）。
  - 筆記若有 auto-extracted 附件，且全文已經成功載入：
    1. 先呼叫既有的 `api.restoreContent(noteId)`（`POST /notes/:id/restore`，會把檔案收回 DB，並刪除附件列與檔案）。
    2. 再 PUT 表單內容。遇到 404（檔案已不存在）就直接 PUT。
  - 若全文**沒有**成功載入：禁止存檔並顯示錯誤。
  - `useNoteAttachments.ts` 需要提供「全文已載入」的狀態。
- **不要修改**：後端 `separate`、`check_separation`、`restore` endpoint（維持 API 相容）；schema；尚未被編輯的已拆分筆記；匯出程式。
- **行為規格**：使用者看不到新的 UI；編輯過的長文從此完整存在 DB 中。
- **驗收**：
  - 新建 6,000 字筆記後，`GET /api/notes/:id` 回傳全文，且沒有附件。
  - 已拆分筆記改成 34 字並存檔後，重開編輯器看到 34 字，附件與檔案都已移除。
  - 修改已拆分的長文後，版本歷史中有一筆完整的舊版。
  - 全文載入失敗時無法存檔。
- **驗證**：`cd frontend && npm run build`；`cd go-shadow && go test ./...`；隔離 runtime 的 browser 流程；`pytest tests/ -v`。

---

## Roadmap 2026-10-06 — P1

### PRISM-OPT-20 — 「合併長文回筆記」維護動作

- **Finding**：FEAT-02、PERF-01 ｜ **優先級**：P1 ｜ **依賴**：PRISM-OPT-19
- **目標**：一次把既有的 auto-extracted 長文合併回 `Notes.content`。
- **原因**：
  - 讓搜尋、匯出、版本歷史、DB 備份與 API 都完整。
  - 附件掃描量只剩真正的使用者附件。實測 230 篇長文時，每次搜尋只掃描 33–54 個檔案就觸頂，延遲約 260ms。
- **修改範圍**：
  - 後端新增一個 additive 端點，例如 `POST /api/system/inline-separated-notes`：
    - 支援 `dry_run`，由 server-system gate 保護。
    - 執行前用 `writeConsistentDBBackup` 建立還原點。
    - 逐筆重用 `restoreSeparatedContent` 的語意（`notes_actions.go:388-430`），但把檔案**移到** `backups/separated-notes-<ts>/`，而不是刪除。
    - 冪等。
  - 前端在 Maintenance 加一個按鈕：先顯示 dry-run 預覽，確認後執行；四語 i18n。
- **不要修改**：schema 版本；不要在啟動時自動執行；不動使用者手動上傳的附件；export 格式。
- **行為規格**：
  - dry-run 先顯示「N 篇可合併、M 篇缺檔」，確認後執行並回報結果。
  - 缺檔的筆記保持原狀並列出。
  - dry-run 另外列出兩類（PRISM-OPT-19 規劃時發現，2026-10-06）：
    - 超過 1 MiB、因此無法載入也無法存檔的已拆分筆記。
    - `docs/notes/` 中沒有任何附件列引用的孤兒檔：在附件面板刪除 auto 附件時只會刪附件列（`attachments.go:286-306`），檔案會留下。
  - 多則筆記共用同一個 `docs/notes` 檔案時，搬移前要檢查，不得讓其他筆記失去檔案。
- **驗收**（Go test fixture：2 篇已拆分、1 篇缺檔、1 篇一般筆記）：
  - dry-run 計數正確。
  - 執行後 FTS 能找到尾段關鍵字、JSON 與 MD 匯出包含全文、檔案已移入隔離資料夾、還原點確實存在。
  - 第二次執行的變更數為 0。
- **驗證**：`cd go-shadow && go test ./...`；`pytest tests/ -v`；`cd frontend && npm run build`；隔離資料的 browser smoke。

### PRISM-OPT-21 — Ctrl+S 存檔後留在原處，加上未存內容保護

- **Finding**：UX-02 ｜ **優先級**：P1
- **目標**：
  - Ctrl+S 存檔但不關閉編輯器。
  - 新筆記第一次存檔後轉為「編輯既有筆記」。
  - 有未存變更時，離開頁面會先提示。
- **原因**：`useNoteForm.ts:130-131,177-189` 讓 Ctrl+S 存檔即關閉；app 外的關閉（分頁、WebView）沒有任何保護。
- **修改範圍**（`useNoteForm.ts`）：
  - 拆出 `save({ close })`；Ctrl+S 呼叫 `close: false`，成功後更新 `originalSnapshot`。
  - 新筆記用回傳的 `note_id` 取回筆記，再透過 store 換成 editing 狀態。
  - `hasUnsavedChanges` 為 true 時註冊 `beforeunload`。
  - Save 按鈕維持「存檔並關閉」。
- **不要修改**：驗證規則、toast 文案的 key、API。
- **行為規格**：
  - Ctrl+S 顯示「已儲存」的 toast 並留在編輯器。
  - 第二次 Ctrl+S 是更新，而不是新建。
  - 關閉分頁時出現瀏覽器原生提示。
- **驗收**：
  - e2e：新筆記連按兩次 Ctrl+S 只產生 1 筆。
  - 有未存變更時會觸發 `beforeunload`。
  - Save 按鈕行為不變。
- **驗證**：`cd frontend && npm run build`；e2e 或 browser smoke（desktop 與 390px）；`pytest tests/ -v`。

### PRISM-OPT-22 — 預覽狀態的最小語意修正

- **Finding**：UX-03（延續 R0812:UX-04）｜ **優先級**：P1 ｜ **依賴**：建議在 PRISM-OPT-21 之後（改同一批檔案）
- **目標**：以預覽模式開啟時，看起來與操作起來都是「預覽」。
- **原因**：目前 heading 是「Edit note」，標題輸入框 `autoFocus`（`NoteEditor.tsx:161-168`），任何按鍵都會改到標題。
- **修改範圍**：`NoteEditor.tsx`、`EditorToolbar.tsx`、i18n（四語）。
  - preview 時 heading 改為「預覽筆記」，標題以 heading 呈現且不 autoFocus。
  - 切換到 Edit 後才顯示標題 input 與 Save；有未存變更時 Save 一律顯示。
  - 保留 EditablePreview 的「Edit this block」。
- **不要修改**：`cardOpenMode` 設定、ReadingView、卡片的主要點擊目標。卡片點擊是否改導 ReadingView，等 usage 回饋再決定。
- **行為規格**：開啟預覽後按鍵不會改到標題；點「編輯」後的行為與現在相同。
- **驗收**（browser）：預覽態沒有被 focus 的 input；Edit 與 Preview 來回切換正常；鍵盤 focus 落在 dialog 內。
- **驗證**：`cd frontend && npm run build`；browser smoke（desktop 與 390px）；`pytest tests/ -v`。

### PRISM-OPT-23 — 匯出範圍文案誠實化

- **Finding**：FEAT-03 ｜ **優先級**：P1
- **目標**：JSON、Markdown、.db 各自說清楚包含與不包含什麼，並導向 Full snapshot。
- **原因**：Data & Recovery 寫「Download all notes… bring them back with Import data later」。實際上 JSON 缺置頂、封存、譜系、版面欄位與歷史，長文只有預覽。
- **修改範圍**：`BackupImportSection.tsx` 對應的 i18n key（四語），以及鎖定這些文案的 source test。
- **不要修改**：匯出格式與欄位（補欄位是 PRISM-OPT-39）。
- **行為規格**：
  - JSON 標明是「可攜的文字副本，不含置頂、封存、歷史、附件檔、圖片」。
  - Markdown 標明「不含文字附件」。
  - 三者都附上「完整備份請用 Full snapshot」。
  - PRISM-OPT-20 完成前，另註明長文可能只有預覽。
- **驗收**：四語都更新；390px 下沒有文字溢出。
- **驗證**：`cd frontend && npm run build`；`pytest tests/ -v`。

### PRISM-OPT-24 — 版本單一來源

- **Finding**：TECH-01 ｜ **優先級**：P1
- **目標**：發版時只需要改 `prismVersion()`（以及 README badge 與文件）。
- **原因**：
  - 版本寫死在 `Sidebar.tsx:162`、`SettingsPage.tsx:196`、`index.html:7`、`system.go:934`，`frontend/package.json` 還停在 `2.0.0`。
  - `/api/test` 不回傳 `version`，About 永遠顯示 fallback。
  - 這個 drift 已經造成 V2.6.1 label hotfix 與 About 同版重發兩次修正型發版。
- **修改範圍**：
  - `main.go` `handleTest` 的回應加入 `version`（additive）。
  - 前端在啟動時讀一次（可以擴充現有 store），供 Sidebar、About、`document.title` 使用；`index.html` 的 title 改為「Prism」。
  - `frontend/package.json` 的 version 同步，或註明不使用。
  - Go test，加上「不得寫死版本號」的 source test。
- **不要修改**：`/api/server/version` 的 gate；release 流程的其他步驟。
- **行為規格**：顯示的版本號與現在相同。
- **驗收**：
  - 把 `prismVersion()` 改成假的值後，三個 UI 位置都跟著變。
  - `Sidebar.tsx`、`SettingsPage.tsx`、`index.html` 中沒有版本字面值。
- **驗證**：`cd go-shadow && go test ./...`；`cd frontend && npm run build`；`pytest tests/ -v`；browser 確認 title、sidebar、About。

### PRISM-OPT-25 — node_modules 移出版控，清除死資產

- **Finding**：TECH-04 ｜ **優先級**：P1
- **目標**：全新 clone 後照文件可以 build；repo 不再追蹤沒有被引用的檔案。
- **原因**：
  - `frontend/node_modules` 有 74.1MB（佔 HEAD tree 72%）而且缺 `dompurify`，`scripts/start_v2_dev.bat:12-16` 在資料夾存在時又會跳過安裝。
  - `resources/`（23.7MB）沒有任何引用；`static/js|css|lib|locales|fonts` 是舊 Vue 前端。
  - `scripts/clean_test_data.py` 會清空 `./knowledge.db` 的筆記，且不經確認。
- **修改範圍**：
  - `git rm -r --cached frontend/node_modules`（`.gitignore` 已經忽略）。
  - 刪除 `resources/`、`static/{js,css,lib,locales,fonts}`、`tools/`。
  - 刪除 5 個死 script：`python_live_workflow_smoke.py`、`check_schema.py`、`clean_test_data.py`、`download_fonts.py`、`migrate_theme_colors.py`。
  - 刪除 `.vscode/launch.json` 的 Flask 設定、`vite.config.ts` 中過時的 proxy、`index.html` 指向不存在檔案的 favicon。
  - 必要時更新只鎖這些路徑的測試。
- **不要修改**：
  - `static/config`、`static/uploads`、`knowledge.db`。
  - 被測試鎖住的 shim（`desktop-spike/`、`install.*`、`requirements-pi.txt`）另外處理。
  - 不改寫 git history。
  - `docs2/` 與根目錄 `PROJECT_REVIEW.md` 已由 PRISM-OPT-27 處理。
- **行為規格**：無使用者可見的變化。
- **驗收**：
  - 在暫存目錄全新 clone 後，`cd frontend && npm ci && npm run build` 成功。
  - `git ls-files frontend/node_modules` 為空。
  - runtime、scripts、CI 都沒有引用已刪除的路徑；CI 綠燈。
- **驗證**：`pytest tests/ -v`；`cd go-shadow && go test ./...`；fresh-clone build；`git diff --check`。

### PRISM-OPT-26 — 補強 behavior test，gate 分流

- **Finding**：TECH-02 ｜ **優先級**：P1 ｜ **依賴**：建議在 PRISM-OPT-15、18、19 之後（以它們的 bug 作為回歸案例）
- **目標**：本次審查找到的每一類 bug 都由執行型測試看守；日常 gate 縮短；歷史測試不再干擾日常開發。
- **原因**：
  - 399 個 pytest 只有 27 個會執行程式；`docs/TEST_PORTFOLIO.md` 的 Behavior 類 100 個測試中，執行型為 0。
  - 冷建置時 4 個打包／桌面 smoke 佔 238.5s 中的 189.3s；pytest 裡又重跑一次完整的 `go test ./...`。
- **修改範圍**：
  - a. Go tests：CJK 搜尋、WAL 一致性、長文 inline 與「縮短後被還原」（若前面的工單尚未補）。
  - b. 把 3 條 e2e（非 Home 的 New、Ctrl+S、中文搜尋）放進 release gate，並把 `pytest-playwright` 列入相依。
  - c. `pytest.ini` 加上 marker：`slow`（4 個打包／桌面 smoke）、`historical`（只讀文件的 phase19–23 模組）。`.loop/verify-gate.ps1` 預設跑 fast（`-m "not slow and not historical"`），`-Release` 跑全部；CI 跑 release。
  - d. `test_desktop_shell_phase1_3.py:83-90` 重複的 `go test ./...` 改標為 slow，或移除。
  - e. PRISM-OPT-16／17／18 留下的 source-lock 測試要補上對應的執行型測試，可以併入 b 的 e2e：
    - 附件 popup 不會被注入。
    - 非 Home 頁面的 New 與搜尋。
    - palette 的 CJK 門檻。
    - 保留 source-lock 作為快速防線。Header 測試要放寬，不鎖定等價寫法（例如 `!isHomeRoute`）。
- **不要修改**：不刪除任何測試；不降低 migration、release、package 的 safety 覆蓋；不改 runtime。
- **驗收**：
  - fast gate 的冷建置與熱快取時間都量測並記錄。
  - release gate 覆蓋與現在相同，再加上 e2e。
  - `docs/TEST_PORTFOLIO.md` 依實際執行性重新分類。
- **驗證**：`pwsh -NoProfile -File .loop/verify-gate.ps1` 與 `-Release` 兩種都跑；CI 綠燈。

### PRISM-OPT-27 — 治理文件瘦身、斷鏈修正、docs-lock 測試解耦（已完成）

- **Finding**：TECH-03 ｜ **優先級**：P1
- **已完成內容**（2026-10-06）：
  - `docs/ARCHITECTURE.md` 只保留 current truth，歷史原文移到 `docs/development-history/architecture-go-migration-history-20261006.md`。
  - `docs/TODO.md` 改為工單看板；`HANDOFF.md` 只留最短狀態。完成紀錄原文移到 `docs/development-history/todo-handoff-archive-20261006.md`。
  - `CLAUDE.md`／`AGENTS.md` 改為分層必讀，並修正 `docs/New_UI`、`docs/過期` 斷鏈。
  - 刪除重複的 `docs2/`；根目錄 `PROJECT_REVIEW.md` 移入歷史資料夾。
  - `docs/GOVERNANCE.md` 新增工單、文件預算與 docs-lock 測試規則。
  - 歷史斷言改讀歸檔檔案，斷言內容本身不變。
- **驗證證據**：見 `docs/TODO.md` 看板下方。

### PRISM-OPT-28 — 桌面版每日自動還原點

- **Finding**：OPS-02 ｜ **優先級**：P1
- **啟動條件**：使用者決定以下三件事：預設是否開啟、保留份數 N、是否只限桌面版。
- **目標**：桌面版使用者在什麼都不做的情況下，最多只會失去 24 小時的 DB 變更。
- **原因**：Go runtime 沒有任何排程；只有 Pi 有每週 systemd timer（`DEPLOY-PI.md:136-161`）。
- **修改範圍**：
  - 在 desktop shell 啟動、且 runtime 健康之後，執行一次檢查。
  - 若最新的還原點已超過 24 小時，就用 `writeConsistentDBBackup` 建一份，並以 `enforceBackupRetention` 保留 N 份。
  - 結果寫進 log。
- **不要修改**：不做常駐排程；不備份上傳檔；不動 Pi 的 timer 與還原流程。
- **行為規格**：在背景完成，不阻擋 UI；失敗只記 log，並在 Maintenance 總覽可以看到。
- **驗收**：
  - Go 單元測試涵蓋「應不應該建立」的判斷與 retention。
  - 隔離 data-dir smoke：啟動兩次只建立 1 份。
- **驗證**：`cd go-shadow && go test ./...`；`scripts/smoke_desktop_portable.ps1`。

### PRISM-OPT-29 — LAN 管理邊界：文件誠實化，加上決策關卡

- **Finding**：OPS-04 ｜ **優先級**：P1
- **目標**：文件與實際行為一致；是否收緊由使用者決定。
- **原因**：
  - `requireLocalhostRequest` 只檢查 `RemoteAddr`（`system.go:168-178`）。
  - Pi 的 Caddy 以 `reverse_proxy 127.0.0.1:5004` 代理，所以 LAN 請求在 Go 看來都來自 loopback。
  - `docs/API_REFERENCE.md:45` 卻寫「遠端 Agent 不可直接呼叫」。
- **修改範圍**：
  - 第一階段（docs-only）：在 `API_REFERENCE.md:45` 與 `DEPLOY-PI.md` 的安全邊界段落說明，Pi 經反向代理時 `/api/server/*` 與 full snapshot 對 LAN 開放。
  - 第二階段（決策之後）：`requireLocalhostRequest` 把帶有非 loopback `X-Forwarded-For`／`Forwarded` 的請求視為遠端，並新增 `--allow-lan-admin`；Pi deploy scripts 明確傳入，以保留現有的 dashboard 用法。
- **不要修改**：不加 auth；不改 CSRF gate；不改變 Caddy 的對外暴露範圍。
- **驗收**：
  - 第一階段：文件不再聲稱遠端無法呼叫。
  - 第二階段：測試涵蓋三種情況——direct loopback 允許；forwarded 的 LAN 請求在未開 flag 時回 403；開 flag 後允許。
- **驗證**：
  - 第一階段：`git diff --check`、`pytest tests/ -v`。
  - 第二階段：再加 `cd go-shadow && go test ./...`。

### PRISM-OPT-58 — JSON 匯入遇到已拆分筆記時整批失敗

- **Finding**：PRISM-OPT-19 規劃時實測（2026-10-06）｜ **優先級**：P1
- **目標**：含已拆分筆記的 JSON 匯出檔可以匯入，不會整批失敗。
- **原因**：匯入用 `resolveAttachmentMutationPath` 驗證附件路徑（`import.go:318`），只允許 `docs/attachments/`。只要匯出檔中有 `docs/notes/note_<id>.md` 這類 auto-extracted 附件，就整批回 400 `unsafe attachment path`。PRISM-OPT-20 完成前匯出的 JSON 備份都受影響。
- **修改範圍**：`go-shadow/import.go`。
  - 先確認 JSON 匯出對已拆分筆記帶了什麼：只有預覽與路徑，還是也有全文。
  - 匯入時不再整批失敗：
    - auto-extracted 的 `docs/notes` 附件列要嘛略過並保留預覽，要嘛在 JSON 含全文時直接寫入 content。採用哪一種，施工前在計畫中說明。
    - 回應中回報略過的筆數。
  - 路徑安全檢查不得放寬到任意路徑。
- **不要修改**：一般附件的路徑安全檢查；schema；export 格式（欄位的擴充屬於 PRISM-OPT-39）。
- **驗收**（Go test）：一份含一篇已拆分筆記的匯出 JSON 可以匯入 fresh DB；其他筆記完整；略過或寫回的結果與回報一致；含 `../` 等不安全路徑的附件仍然被拒絕。
- **驗證**：`cd go-shadow && go test ./...`；`pytest tests/ -v`。

### PRISM-OPT-59 — 編輯器開著時從 Command Palette 開另一則筆記（先重現）

- **Finding**：PRISM-OPT-19 規劃時的觀察，**未驗證**（2026-10-06）｜ **優先級**：P1
- **目標**：確認編輯器開著時切換到另一則筆記，不會把前一則的內容存進新的筆記；若會，修正它。
- **原因**（推測）：
  - `HomePage.tsx:617-618` 的 `NoteEditor` 沒有用 note id 當 `key`。
  - 編輯器開著時 `Ctrl+K` 仍會開啟 palette（`CommandPalette.tsx:317-321`）。
  - 如果在 palette 中選了另一則筆記，表單可能沿用前一則的內容，存檔時卻寫到新的 note id。
- **修改範圍**：
  - 第一步：在隔離 runtime 重現。開 A 並修改內容 → `Ctrl+K` 選 B → 存檔 → 檢查 A、B 的 DB 內容與歷史。
  - 若重現成功：最小修正，例如 `NoteEditor` 加上 `key={editingNote?.id ?? 'new'}`，或在編輯器開著時讓 palette 開筆記前先關閉編輯器，並保留 PRISM-OPT-21 的未存提醒語意。
  - 若無法重現：記錄重現步驟與結果，並關閉工單。
- **不要修改**：API；schema；PRISM-OPT-19 的存檔流程。
- **驗收**：重現步驟的結果記錄在 `docs/TODO.md`；若有修正，A、B 的內容與歷史都正確，並有回歸測試或 browser smoke 證據。
- **驗證**：`cd frontend && npm run build`；`pytest tests/ -v`；隔離 runtime 的 browser 流程。

### PRISM-OPT-52 — 子代理派工：依類別與難度指定模型與 effort（已完成）

- **來源**：使用者需求（2026-10-06）｜ **優先級**：P1
- **目標**：派工時，依工單類別與難度選擇合適的子代理、模型與推理程度，而不是全部用同一個設定。
- **已完成內容**：
  - `.claude/agents/` 新增六個代理定義：prism-scout（haiku）、prism-docs（sonnet／medium）、prism-builder（sonnet／medium）、prism-engineer（opus／high）、prism-critical（opus／xhigh，可覆寫為 fable）、prism-verifier（opus／high，唯讀）。
  - `docs/AGENT_DISPATCH.md`：類別、難度、派工矩陣、升級規則、兩段式派工、Codex 對應。
  - 本檔「派工總表」為每張工單指定實作與驗收代理。
  - `.gitignore` 改為只追蹤 `.claude/agents/`，`settings.local.json` 與 `worktrees/` 仍然忽略。
  - `tests/test_agent_dispatch.py` 檢查代理定義、派工指南與派工總表三者一致。
- **驗證證據**：見 `docs/TODO.md` 看板下方。

---

## Roadmap 2026-10-06 — P2

### PRISM-OPT-30 — Mobile 排序控制與首屏密度

- **Finding**：UX-04 ｜ **優先級**：P2
- **目標**：375–390px 寬時可以切換排序；首屏至少看到 2–3 筆筆記。
- **原因**：
  - `Header.tsx:273-274` 在 <640px 隱藏排序，drawer 裡也沒有。
  - 實測第一張卡片從 295px 開始，grid 模式一屏只完整看到 1 張。
- **修改範圍**：
  - 在 drawer 或 mobile header 加排序選單，重用 `sortOptions` 與 `setSortBy`。
  - `HomePage.tsx` 在 mobile 壓縮標題列與「Save current view」列。
  - 可選：使用者沒有設定過 `prism.viewMode` 時，mobile 預設用 list 或 compact。
- **不要修改**：desktop 版面、排序 API、使用者已存的 viewMode 偏好。
- **行為規格**：mobile 在 2 次點擊內可以換排序；首屏在 list/compact 下可見 ≥2 張卡片。
- **驗收**（390px browser）：排序可操作、`aria-label` 正確；沒有水平溢位；desktop 沒有差異。
- **驗證**：`cd frontend && npm run build`；browser smoke（desktop 與 390px）；`pytest tests/ -v`。

### PRISM-OPT-31 — 筆記計數單一來源，Maintenance 顯示真實 stats

- **Finding**：UX-05 ｜ **優先級**：P2
- **目標**：
  - Sidebar「All」、Header、Footer 顯示同一個 Library 總數（不含封存）。
  - Maintenance 顯示真實的圖片數量或大小。
- **原因**：
  - Sidebar 用分類計數加總（含封存、不含未分類；`Sidebar.tsx:194`）。
  - Footer 讀 store 的 `totalNotes`：直接進 `/settings` 時顯示 0，搜尋後顯示搜尋結果數。
  - `SettingsPage.tsx:90-98` 寫死 `images_count`、`total_size_mb` 為 0，而 `/api/system/stats` 已經回傳真值。
- **修改範圍**：
  - Footer 與 Sidebar 使用同一個 Library 總數，來源是 `/api/system/stats` 的 `notes_count - archived_count`，或新增 additive 欄位。
  - Maintenance stats 改讀 `/api/system/stats`；需要張數時，在 uploads 加 additive 欄位 `files`。
- **不要修改**：notes list API；分類計數 API 的語意。
- **驗收**：
  - 有 1 筆封存筆記時，三處計數一致。
  - 直接載入 `/settings` 時 Footer 不顯示 0。
  - Maintenance 的圖片欄位不再是寫死的值。
- **驗證**：`cd frontend && npm run build`；有改 API 時加 `cd go-shadow && go test ./...`；browser smoke。

### PRISM-OPT-32 — mutation 後就地更新，不再重置列表

- **Finding**：PERF-02 ｜ **優先級**：P2 ｜ **依賴**：PRISM-OPT-21
- **目標**：存檔、置頂、封存、建立變體、還原歷史之後，列表維持原本的捲動位置與已載入頁數。
- **原因**：上述動作都呼叫 `fetchNotes(true)`，列表被重置為第一頁（`appStore.ts:154-158`）。來源位置包括 `useNoteForm.ts:130`、`NoteCard.tsx:150,164,216`、`useNoteHistory.ts:52`。
- **修改範圍**：
  - `appStore` 新增 `upsertNote`／`removeNote`，或改為「重新抓取已載入的頁數」。
  - 上述呼叫點改用新函式。
  - 若改動影響排序（例如置頂、依更新時間排序），把該筆移到正確位置，或局部重抓。
- **不要修改**：分頁大小、API、latest-request-wins 的請求序號機制。
- **驗收**：
  - 載入 3 頁後編輯第 45 筆並存檔：列表仍有 ≥60 筆，捲動位置不跳回頂端。
  - 置頂後該筆出現在置頂區。
- **驗證**：`cd frontend && npm run build`；browser smoke（26 筆以上的 fixture）；`pytest tests/ -v`。

### PRISM-OPT-33 — Library 導覽去重

- **Finding**：IA-01 ｜ **優先級**：P2
- **目標**：desktop 上分類只出現在一處；標題與計數只出現一次。
- **原因**：desktop 同時顯示 Sidebar 的分類與 FilterStrip 的分類 chips；Header meta、H1、Footer 重複顯示標題與計數。
- **修改範圍**：
  - `FilterStrip.tsx`：在 ≥md（Sidebar 可見）時，只顯示目前篩選狀態、Archive 切換與 Starred tags；mobile 維持完整 chips。
  - `Header.tsx`：在 Home 移除與 H1 重複的 meta（或 H1 移除重複說明，二擇一）。
- **不要修改**：篩選的 state 與 API；Sidebar 結構；starred tags 功能；mobile drawer。
- **驗收**：desktop 只剩一組分類導覽；mobile 不退化；鍵盤可達。
- **驗證**：`cd frontend && npm run build`；browser（desktop 與 390px）；`pytest tests/ -v`。

### PRISM-OPT-34 — Settings 重新分組

- **Finding**：IA-02 ｜ **優先級**：P2
- **目標**：設定的位置符合使用者心智模型；圖片相關設定集中一處；tab 深連結的行為可預期。
- **原因**：
  - Appearance 混入卡片開啟模式、圖片儲存模式、快速新增預設分類、自動載入。
  - 圖片清理放在 Access & System 的 Danger Zone。
  - `?tab=data` 無效，實際的 tab id 是 `backup`。
- **修改範圍**：
  - Settings 新增「Library & Editor」分組，或在 Appearance 內分段（取最小改動）。
  - 圖片儲存模式與三種圖片清理移到 Maintenance 的「Images & storage」。
  - tab id 接受別名（例如 `data` → `backup`）。
  - 四語 i18n。
- **不要修改**：各設定的 localStorage key、清理 API、確認對話流程。
- **驗收**：所有既有設定都還找得到、值也保留；舊的深連結仍有效；390px 沒有溢位。
- **驗證**：`cd frontend && npm run build`；browser；`pytest tests/ -v`（含 settings deep link 測試）。

### PRISM-OPT-35 — Full snapshot 手動還原說明

- **Finding**：OPS-03 ｜ **優先級**：P2
- **目標**：使用者拿到 Full snapshot 後，可以照文件在桌面版與 Pi 還原。
- **原因**：
  - UI 與 contract（`docs/contracts/full-data-snapshot-v1.md:69`）只寫「需要手動程序」，沒有步驟。
  - snapshot 內的 DB 叫 `database/knowledge.db`，桌面版實際檔名是 `prism_desktop_dev.db`（`main.go:203-205`）。
- **修改範圍**：
  - 在 `docs/desktop/README-PORTABLE.md` 與 `DEPLOY-PI.md` 各加一段「從 Full snapshot 還原」，步驟依序為：
    1. 關閉程式。
    2. 備份目前的 data-dir。
    3. 解壓 snapshot。
    4. 依路徑對應放回檔案，並改 DB 檔名。
    5. 驗證 manifest 的 SHA-256。
    6. 啟動並檢查 `migration-status`。
  - Data & Recovery 的 snapshot 卡片加上文件連結（四語）。
- **不要修改**：snapshot 格式；不做自動還原；API。
- **驗收**：在隔離 data-dir 實際照步驟還原一次，筆記、附件、圖片、長文都在；文件與 UI 連結一致。
- **驗證**：手動演練紀錄；`cd frontend && npm run build`；`pytest tests/ -v`。

### PRISM-OPT-36 — Server dashboard 的 Restart 不再假成功

- **Finding**：OPS-05 ｜ **優先級**：P2
- **目標**：Restart 按鈕要嘛真的重啟，要嘛不存在。
- **原因**：`handleServerRestart` 只回傳 candidate 訊息，不會重啟（`system.go:696-710`）；UI 卻顯示成功並在 5 秒後重新整理。
- **修改範圍**：二擇一，施工前在工單記錄選擇：
  - A：handler 改走既有的 `s.restart`／`triggerRestart`（還原點流程已在用，`backups.go:160-164`），維持 localhost 與 server-system gate。
  - B：移除 UI 按鈕與對應 i18n，API 回明確的「not supported」。
- **不要修改**：還原點流程、systemd 設定、CSRF gate。
- **驗收**：
  - A：桌面版與 Pi 都會實際重啟並回到健康狀態。
  - B：UI 不再出現按鈕，`docs/API_REFERENCE.md` 同步更新。
- **驗證**：`cd go-shadow && go test ./...`；`cd frontend && npm run build`；選 A 時加上桌面或 Pi smoke。

### PRISM-OPT-37 — 使用者看得到的遷移期字串改為中性文案

- **Finding**：TECH-05 ｜ **優先級**：P2
- **目標**：使用者與日誌看得到的訊息，不再出現 candidate、proof、Python-owned 等遷移期字樣。
- **原因**：
  - flag 說明寫「parity candidate」（`main.go:148-160`）。
  - restart 回應「Go local server-system candidate…」（`system.go:700-709`）。
  - 啟動 log 寫「Prism Go runtime proof listening」。
  - 附件錯誤訊息寫「remain Python-owned」（`attachments.go:42`）。
- **修改範圍**：只改字串（flag usage、log、錯誤訊息），並同步更新鎖這些字串的測試。
- **不要修改**：
  - flag 的名稱與行為（屬於 PRISM-OPT-43）。
  - DB 檔名 `prism_desktop_dev.db`：這是使用者資料，改名需要 migration，不在本工單。
  - API 結構。
- **驗收**：runtime 的輸出與錯誤回應中 grep 不到上述字樣。
- **驗證**：`cd go-shadow && go test ./...`；`pytest tests/ -v`。

### PRISM-OPT-38 — Reading list 預取加上限，或改為 lazy detail

- **Finding**：R0812:PERF-03 ｜ **優先級**：P2
- **目標**：開啟 Reading view 時，不再一次抓取整個閱讀清單每一篇的全文。
- **原因**：`ReadingView.tsx:137-142` 對 workspace 中所有缺少的 ID 平行呼叫 `api.getNote()`，而清單沒有上限。
- **修改範圍**：
  - 只抓目前與相鄰項目的 detail；清單列表使用已有的 list metadata。
  - 設定合理的上限，或清除已不存在的 ID。
- **不要修改**：localStorage key 與格式；ReadingView 版面。
- **驗收**：
  - 清單有 50 筆時，開啟 Reading view 的 detail 請求 ≤3 個，切換項目時才抓。
  - 已刪除的筆記會從清單中清除。
- **驗證**：`cd frontend && npm run build`；觀察 browser network；`pytest tests/ -v`。

### PRISM-OPT-39 — JSON 匯出與匯入補齊欄位

- **Finding**：FEAT-03 ｜ **優先級**：P2 ｜ **依賴**：PRISM-OPT-23
- **目標**：JSON 匯出再匯入後，置頂、封存、變體譜系、封面位置、版面設定都保留。
- **原因**：`exportJSONNotes`（`export.go:516-555`）只輸出 10 個欄位。
- **修改範圍**：
  - 匯出加入 additive 欄位：`is_pinned`、`is_archived`、`parent_id`、`cover_position`、`editor_layout`、`sort_order`。
  - 匯入讀到這些欄位時套用；缺欄位時維持現行預設，舊檔案仍相容。
  - `export_info.version` 遞增。
- **不要修改**：既有欄位的名稱與型別；匯入的重複判斷邏輯。
- **驗收**（Go test）：匯出 → 匯入到 fresh DB → 欄位一致；舊版 JSON 仍可匯入。
- **驗證**：`cd go-shadow && go test ./...`；`pytest tests/ -v`。

### PRISM-OPT-53 — Mobile 在非 Library 頁面也有搜尋入口

- **Finding**：PRISM-OPT-17 驗收時發現（2026-10-06）｜ **優先級**：P2
- **目標**：手機寬度（md 以下）在 Settings、Prompt Builder 等頁面也能開始搜尋。
- **原因**：
  - Header 搜尋框是 `hidden md:block`，Command Palette 按鈕是 `lg:flex`。
  - 手機只能在 Library 頁內的 `mobile-search-form` 搜尋；在其他頁面完全沒有搜尋入口。
- **修改範圍**：`frontend/src/components/Header.tsx`。在 md 以下、非首頁時顯示一個搜尋圖示按鈕：導到 `/`，並把 focus 移到 `mobile-search-input`。aria-label 優先重用既有的 `common.search` key。
- **不要修改**：桌面版 Header 版面、HomePage 的 `mobile-search-form`、appStore、API。
- **行為規格**：390px 在 `/settings` 點搜尋圖示 → 回到 Library，搜尋框取得 focus，輸入後送出可看到結果。
- **驗收**：390px 的 browser smoke，在 `/settings`、`/prompt-builder` 都要驗證；桌面版沒有變化；console 沒有錯誤。
- **驗證**：`cd frontend && npm run build`；`pytest tests/ -v`；隔離 runtime 的 browser smoke（desktop 與 390px）。

### PRISM-OPT-54 — 附件刪除按鈕在觸控裝置上的點擊範圍

- **Finding**：PRISM-OPT-16 驗收時發現（2026-10-06）｜ **優先級**：P2
- **目標**：觸控裝置上，附件刪除按鈕的點擊範圍至少 32×32px（建議 44×44px）。
- **原因**：目前刪除按鈕約 20×20px（12px 圖示加 `p-1`），在 390px 不易點中，也容易誤點旁邊的開啟按鈕。
- **修改範圍**：`frontend/src/components/editor/AttachmentPanel.tsx` 的刪除按鈕。只在 `[@media(hover:none)]` 或小螢幕放大 padding 或最小尺寸，桌面外觀不變。
- **不要修改**：PRISM-OPT-16 的純文字輸出與按鈕語意；上傳與刪除 API。
- **驗收**：390px 量測刪除按鈕尺寸 ≥ 32×32px；附件列沒有橫向溢出；桌面截圖與修改前相同。
- **驗證**：`cd frontend && npm run build`；`pytest tests/ -v`；browser 驗證。

### PRISM-OPT-55 — 從非 Library 頁面搜尋只送出一次請求

- **Finding**：PRISM-OPT-17 驗收時發現（2026-10-06）｜ **優先級**：P2
- **目標**：從 Settings 或 Prompt Builder 搜尋時，`/api/notes?q=` 只送出一次。
- **原因**：
  - Header 先 `navigate('/')`、再 `setSearchQuery`；`setSearchQuery` 會自己 fetch，HomePage 掛載時又 `fetchNotes(true)` 一次。
  - 結果正確（store 的 request sequence 會丟掉舊回應），但每次多一個重複請求。在 `/` 上搜尋只送一次。
- **修改範圍**：`frontend/src/stores/appStore.ts`，以及必要時的 `Header.tsx`、`HomePage.tsx`。最小做法：讓非首頁的搜尋只更新 query 不 fetch，交給 HomePage 掛載時 fetch；不得在 Header 重複 `setSearchQuery` 的內部邏輯。
- **不要修改**：在 `/` 上搜尋的行為；API；PRISM-OPT-17 的導頁行為。
- **驗收**：用 XHR 或 network 計數：在 `/` 搜尋送出 1 次，從 `/settings` 搜尋也只送出 1 次，結果正確；其他會觸發 fetch 的入口（分類、標籤、排序、封存）行為不變。
- **驗證**：`cd frontend && npm run build`；`pytest tests/ -v`；隔離 runtime 的 browser smoke。

### PRISM-OPT-56 — 搜尋正規化：韓文子字串、全形英數、混合查詢語意

- **Finding**：PRISM-OPT-18 驗收時發現（2026-10-06）｜ **優先級**：P2
- **目標**：韓文詞在句中也能搜到；全形英數字查詢與半形一致；混合查詢的語意寫進文件。
- **原因**：
  - PRISM-OPT-18 只把 Han、Hiragana、Katakana 列為 CJK。韓文（Hangul）在詞中段仍搜不到。
  - SQLite `LOWER` 只轉 ASCII；查詢「ＡＢＣ」不會命中內容中的「abc」，反之亦然。
  - 查詢只要含 CJK token，ASCII token 也改用子字串比對（例如「rom 工程」會命中 prompt），而純 ASCII 查詢仍是前綴比對。這個語意目前沒有文件說明。
- **修改範圍**：
  - `go-shadow/notes_search.go`：`hasCJKToken` 加入 `unicode.Hangul`；查詢 token 先把全形 ASCII（U+FF01–U+FF5E）折成半形。不新增 dependency。
  - `frontend/src/components/CommandPalette.tsx`：CJK 門檻的 regex 加入 Hangul。
  - `docs/API_REFERENCE.md` 的搜尋說明：寫明前綴比對、CJK 子字串比對與混合查詢的語意。
- **不要修改**：FTS schema 與 tokenizer、migration；純英文查詢產生的 SQL 與參數；已存內容（不改寫資料）。
- **施工前確認**：
  - 全形折疊只作用在查詢端，內容中的全形字不會被搜到。若要雙向一致，需要索引端正規化，屬於 schema 變更，另開 decision gate。
  - 混合查詢的語意預設維持現狀，只補文件。
- **驗收**（Go test，經 HTTP handler）：韓文句中的詞可命中；「ＰＲＯＭＰＴ」與「prompt」的結果相同；PRISM-OPT-18 的既有案例全部不變；純英文查詢的 SQL 與參數不變。
- **驗證**：`cd go-shadow && go test ./...`；`cd frontend && npm run build`；`pytest tests/ -v`。

### PRISM-OPT-57 — 附件 popup 跨瀏覽器與 desktop shell 驗證

- **Finding**：PRISM-OPT-16 驗收時發現（2026-10-06）｜ **優先級**：P2
- **目標**：確認 PRISM-OPT-16 的純文字 popup 在 Chromium 以外的環境也正確。
- **原因**：PRISM-OPT-16 只在 Chromium（headless 與 browser pane）驗證過；Firefox、Safari（WebKit），以及 Windows desktop shell（WebView2 的預設 popup）沒有實測。
- **修改範圍**：驗證工作，不改程式。在隔離 runtime 上，用含 `<script>`、`</pre><img onerror>` 與 CJK 的附件，在 Firefox、WebKit（或 Safari）與 `Prism.exe` desktop shell 各開一次 popup。
- **驗收**：
  - 每個環境的 popup 都只有一個 `<pre>`，原樣顯示 payload，沒有產生 script 或 img 元素。
  - 結果記錄在 `docs/TODO.md`。
  - 任何環境失敗時，另開修正工單。
- **驗證**：截圖或 DOM 檢查的紀錄；desktop shell 使用隔離的 `PrismData`。

---

## Roadmap 2026-10-06 — P3 / Future（Blocked）

### PRISM-OPT-40 — Prompt Builder 命名、模板語系、seed 缺失的死路

- **Finding**：UX-06 ｜ **優先級**：P3
- **啟動條件**：使用者明確 promote。
- **目標與範圍**：
  - 「AI optimize」改為「複製優化提示詞」（四語）。
  - Quick templates 依 UI 語系顯示：在 seed 加多語欄位，且向後相容。
  - seed 缺失時，錯誤訊息說明缺了什麼，並提供「使用預設設定」。
- **不要修改**：prompt 組合規則；options JSON 結構（只能做向後相容的新增）。
- **驗收**：英文 UI 顯示英文模板；刪除 seed 後畫面不再是死路。

### PRISM-OPT-41 — Prompt Builder seed config 內嵌

- **Finding**：OPS-06 ｜ **優先級**：P3
- **啟動條件**：使用者明確 promote，或出現 seed 缺失的回報。
- **範圍**：
  - 用 `go:embed` 內嵌一份預設的 `prompt_options.json`／`wizard_options.json`，作為最後的唯讀 fallback；寫入仍寫到 data-dir。
  - `scripts/pack.bat` 補帶 `static/config`。
- **驗收**：空的 data-dir 首次開 Prompt Builder 可以使用；既有的使用者設定不被覆蓋。
- **觀察**（2026-10-06，PRISM-OPT-17／18 驗收時）：隔離 data-dir 的 runtime smoke 若缺少這兩個檔案，Prompt Builder 會出現 404／405 console error，干擾「console 沒有錯誤」的驗收。目前的 workaround 是把 seed 複製到 exe 旁。這也算 seed 缺失的實例，可以作為 promote 的依據。

### PRISM-OPT-42 — API 表面衛生

- **Finding**：TECH-06 ｜ **優先級**：P3
- **啟動條件**：先確認外部 agent 是否使用以下只剩舊 Vue client 呼叫的 route：vacuum、clear-history、startup-preference、prompt-options CRUD、batch type/tags、export batch。
- **範圍**：
  - 刪除 `api.ts` 的 5 個死 wrapper、`UpdateSection.tsx`、`TagInput.tsx`。
  - 處理 `.port_config` 的寫入（連同 `PortConfigSection` 的去留）。
  - `docs/API_REFERENCE.md`：保留給 agent 的 route 註明用途，淘汰的標為 deprecated（不直接刪 route）。
- **不要修改**：任何仍被 React 或已知 agent 使用的 route；不做全面統一 response envelope。

### PRISM-OPT-43 — 移除 capability flags；`go-shadow` 改名

- **Finding**：TECH-05 ｜ **優先級**：P3
- **啟動條件**：出現新增 runtime mode 的需求，或 flags 誤配造成的事故。
- **範圍**：
  - 以單一 profile（或預設全開）取代 13 個 `--enable-*`，舊 flag 保留相容一個版本。
  - `go-shadow` 目錄改名時，同步 scripts、CI、docs、contracts。
- **風險**：波及面大，需要完整的 release gate。

### PRISM-OPT-44 — 非中文使用者的首次體驗

- **Finding**：BIZ-01 ｜ **優先級**：P3
- **啟動條件**：出現非中文使用者的回報或需求。
- **範圍**：
  - welcome note 依首次使用的語系呈現，或改為雙語（`migrations.go:444-446`）。
  - Prompt 模板語系，與 PRISM-OPT-40 合併評估。

### PRISM-OPT-45 — FTS5 trigram 索引

- **Finding**：FEAT-01 ｜ **優先級**：Future
- **啟動條件**：三者同時成立——筆記超過約 1 萬筆；PRISM-OPT-18 的 LIKE fallback 實測延遲不可接受；3 字以上的查詢占多數。
- **範圍**：新增 trigram FTS 表（schema 升版，需要 decision gate）；2 字查詢仍走 LIKE。
- **已知成本**：本機 benchmark（10k 筆 × 1,800 字）建索引 36.7s，DB 膨脹到 329MB。
- **PRISM-OPT-18 實測**（`BenchmarkNotesSearchCJK1000Notes`，每筆約 1,800 個 CJK 字）：
  - 1,000 筆約 30–34 ms／查詢；10,000 筆約 1.0–1.14 s／查詢。
  - handler 的 COUNT 與列表各掃一次全文；單一 LIKE COUNT 約 378 ms。
  - 改 trigram 之前，可以先評估把 COUNT 與列表合併成只掃一次全文的較小改善。

### PRISM-OPT-46 — Note_History 保留策略

- **Finding**：PERF-03 ｜ **優先級**：Future
- **啟動條件**：PRISM-OPT-20 完成後，`Note_History` 出現成長證據，例如佔 DB 一半以上，或超過 100MB。
- **範圍**：每筆只保留最近 N 版，或依時間保留；UI 提供手動清理（`/system/clear-history` 已存在）。

### PRISM-OPT-47 — 文字附件內容索引

- **Finding**：PERF-01 ｜ **優先級**：Future
- **啟動條件**：PRISM-OPT-20 完成後，文字附件仍有約 50 個以上，且搜尋常態回傳 partial。
- **範圍**：上傳時把 md/txt 內容寫入獨立的 FTS（需要 schema 升版與 decision gate）；刪除附件時同步；搜尋不再逐檔掃描。

### PRISM-OPT-48 — 回收桶（軟刪除與復原）

- **Finding**：FEAT-05 ｜ **優先級**：Future
- **啟動條件**：出現誤刪事件的回報。
- **範圍**：以 `deleted_at` 軟刪除，30 天後清除；需要 schema 升版、所有查詢加上過濾，並重新審查媒體清理的語意。

### PRISM-OPT-49 — 桌面版與 Pi 跨裝置同步

- **Finding**：FEAT-06（REVAMP-05）｜ **優先級**：Future
- **啟動條件**：有同一使用者同時在桌面版與 Pi 寫入、需要合併的證據；先完成 PRISM-OPT-35。
- **範圍**：先研究以 note 識別碼加 `updated_at` 的增量匯出與匯入；不做即時同步。

### PRISM-OPT-50 — Prompt options 自訂 UI

- **Finding**：FEAT-07 ｜ **優先級**：Future
- **啟動條件**：使用者需要自訂相機與風格選項。
- **範圍**：接回既有 prompt-options／wizard-options CRUD API 的簡單管理面板（API 已有測試）。

### PRISM-OPT-51 — Wiki 連結與 backlinks

- **Finding**：FEAT-08 ｜ **優先級**：Future
- **啟動條件**：有使用者需求的證據。
- **範圍**：解析 `[[標題]]` 連結並提供反向連結面板；需要關聯表（schema 升版）。
