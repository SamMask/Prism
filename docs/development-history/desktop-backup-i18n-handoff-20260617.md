# Desktop, Backup, Core UX, and i18n Handoff Archive (2026-06-17)

> Moved out of `HANDOFF.md` and slimmed from `docs/TODO.md`. Current entry point stays in `HANDOFF.md` and active tasks stay in `docs/TODO.md`.

---

## Original HANDOFF.md Snapshot

# HANDOFF — 本機桌面化 / 備份 / 儀表板（2026-06-14）

> 上一段對話（誤在 SymArranger 視窗下、但全程以絕對路徑操作 `D:\AI\Prism`）的推理快照。
> 開新對話接續時先讀本檔，再看 `docs/TODO.md`「桌面化（.exe）決策與待辦」與「i18n 還原」兩節。

## 狀態

- 已 **merge 進 `main`**（fast-forward 到 `24bf5f6`），未 push、未部署。
- 合併後驗證綠：`go test ./...` ok、`tsc --noEmit` ok、前端 build ok、linux/arm64 交叉編譯 ok。
- 分支 `feat/local-desktop-and-backup` 與 main 同點，可刪可留。

## 這段做完了什麼（main 上的 6 個 commit）

| commit | 內容 |
|--------|------|
| `b4f650b` | `fix(deploy)` — `go_primary_pi_live_ops.ps1` 所有 ssh/scp 走 `Invoke-Ssh/Invoke-Scp`（BatchMode + `-n` + ConnectTimeout），修背景無 TTY 永久卡死。 |
| `f654750` | `feat(backup)` — **重啟式 DB 還原**：`POST /api/server/backup/restore` 驗證備份→寫 `pending-restore` 標記→重啟；開機 `openDB` 前 `applyPendingRestore` 換檔（覆蓋前存 `prism_pre_restore_*.db` 後悔藥）。重啟協定：supervised（systemd，靠 `INVOCATION_ID`）`os.Exit(42)`；獨立 .exe 自我 re-exec。`main()` 用 `select{}` 把程序終結權讓給 restart goroutine。**download 解耦**：`/backup/download` 改吐暫存快照、不再留 server-side 備份（留存交給 rotate）。前端 `設定 > 資料` 加「從備份還原資料庫」卡片。測試：`restore_test.go`。 |
| `3724875` | `feat(dashboard)` — `hardware_windows.go`（kernel32 讀真實磁碟/記憶體/uptime）。CPU 溫度 Windows 維持 N/A（無可靠 API）。`hardware_other.go` 改 `!linux && !windows`。測試：`hardware_windows_test.go`。 |
| `e6c4d52` | `chore(settings)` — 隱藏 `設定 > 部署` 的「部署安全邊界 / 端口設定 / 版本更新」（元件檔留著、僅不 render，復原方式見 TODO）；`docs/TODO.md` 記錄桌面化路線。 |
| `9ebf47c` | `docs` — 修掉誤導的 Pi 備份份數（changelog `8` → 實際 `3`）。 |
| `24bf5f6` | `docs(todo)` — i18n 還原拆成 5 階段待辦。 |

## 已定的產品決策（細節在 docs/TODO.md）

- **.exe = 視窗程式**，要有「關閉視窗：連背景關 / 縮 tray 常駐」設定。
- **備份**：Pi 每週自動（keep 3）；**.exe 本機不做自動排程**，使用者手動按。
- **AND/OR 搜尋不做**（英文有空格、中文邊角不值得動搜尋核心）。
- 已答的確認：搜尋會查筆記內容 + `.md/.txt` 附件內文；CSRF 只擋「跨來源瀏覽器寫入」，純 API/curl 不受影響、Pi 與本機同一套碼。

## 待續討論：.exe 視窗外殼設計（卡在這裡，沒動工）

地基事實：前端已 `//go:embed web/dist/*` 進 Go binary → 單一 .exe 已是「server + 前端」，外殼只要開 webview 指向 `127.0.0.1:<port>`。

推薦架構：單一 .exe = 啟動現有 Go server + 開 WebView2 視窗 + tray icon + 單一實例（named mutex）。後端不動。

**選型傾向**：WebView2 用 `jchv/go-webview2`（純 syscall，**可保 `CGO_ENABLED=0`**，不要 `webview/webview_go` 因為要 cgo）。

**唯一真風險**：WebView2 視窗與 tray 都要主執行緒 message pump，會搶。解法＝自寫薄層 `Shell_NotifyIcon` 共用單一 Win32 loop。**建議下一步先做「空視窗 + tray + 單一 loop」spike 驗證可行，再接後端。**

**待你拍板**：①WebView2 方向 OK？②close-to-tray 預設值（建議預設「關閉=直接結束」，常駐當進階選項）③先 spike 還是先寫完整 design doc。

## 其他待辦（docs/TODO.md）

- i18n 還原（中/英/日/韓，設定>外觀切換）— 2026-06-17 active UI 階段 1-5 已完成：locale 接入 Zustand reactive state、新增穩定 `useTranslation()`、`設定 > 外觀` 四語下拉、Settings / Appearance、Home shell、ReadingView / NoteEditor / editor hooks、Prompt Builder、Settings 維護/備份/Server Dashboard、DataManager、global API/toast error adapter、remaining hardcoded UI string audit / hidden legacy settings triage、CommandPalette / Security / DangerZone / shared UI fallback 都已抽到 zh-TW/en/ja/ko key。階段 5 收尾已把 missing-key 行為改為缺漏 key 先回 zh-TW fallback，四語都沒有該 key 才回 key 字串並 `console.warn`；`{count} 參數替換` 保留；新增 namespace-level `TranslationKey` / `TranslationParams` 型別與 typed `useTranslation()` function surface，作為後續固定 key 逐步收斂的 typed guard。預設分類顯示 i18n 只對 DB 名稱完全符合原始 seed 的 5 個分類（`提示詞 | Prompt`、`筆記 | Note`、`教學 | Tutorial`、`資料 | Data`、`靈感 | Inspiration`）生效；英文顯示純英文；使用者改名或自訂分類（例如 `美食 | Gourmet`）保留 DB 原文。全量 deep key union 曾評估但目前字典規模會讓 TypeScript 報 `Type instantiation is excessively deep`，故不採用。Deferred/hidden：PortConfigSection、UpdateSection 未由 SettingsPage render；TagInput 目前未掛載，日後恢復 render 時再補四語。Allowed non-UI/data literals：Settings tab fallback label、Appearance option name metadata、Prompt Builder 分類匹配字串、註解與 API/server 動態內容。後端回傳的 API `message` / `error` 保留原文不翻譯。不要再開大型 UI 抽字串批次；下一步建議回到 Desktop Shell Phase 0 / message loop spike。
- 自啟動（registry Run key）— 併入桌面化。

---

## Detailed Active TODO Records Before Slimming

### 2026-06-16 Core UX Adoption

### 採納：Core UX / 文件治理候選

- [x] **CORE-UX-01 About current-truth wording**（2026-06-17 完成）：`Settings > About` 已改為 Go primary runtime / SQLite FTS5 / local-first current truth；未改 API、schema、runtime、deploy。驗收：前端 About 不再宣稱 Flask backend，`cd frontend && npm run build` 通過。
- [x] **SETTINGS-IA-01 Settings information architecture refresh**（2026-06-17 完成）：Settings tabs 已重排為「外觀 / 組織 / 備份與還原 / 維護與健康 / 存取與系統 / 關於」。只搬移既有 section 與文案，未新增 endpoint、未恢復已隱藏的 PortConfig / Update / 部署安全邊界、未改 schema。驗收：Chrome headless rendered DOM / screenshot 覆蓋 tab navigation；in-app Browser runtime 本輪不可用，已以 Chrome headless 替代。
- [x] **MAINT-COPY-01 Maintenance copywriting pass**（2026-06-17 完成）：WAL / checkpoint / consistency 等工程詞已退到補充文字，主標改為「整理資料庫暫存日誌」「資料一致性檢查」等使用者語言；未改維護 API 行為，未新增自動修復。驗收：`cd frontend && npm run build` 通過，危險操作仍需明確確認。
- [x] **BACKUP-UX-02 Backup / export / restore separation**（2026-06-17 完成）：UI 文案已區分「匯出副本」「匯入資料」「Prism 內建還原點」「還原資料庫」。保留既有 restore restart 協定；未新增本機自動備份排程，未改 Pi 每週備份策略。驗收：備份下載、JSON 匯入、DB restore 入口語義清楚且現有 API 呼叫不變。
- [x] **CODEX-REVIEW-01 Codex task/review checklist extraction**（2026-06-17 完成）：已新增 `docs/CODEX-TASK-REVIEW-CHECKLIST.md`，把報告中的任務 prompt 契約、allowed files、forbidden scope、verification、Not Changed 回報格式、review checklist 與硬退回條件收斂成 docs-only checklist。驗收：`tests/test_codex_task_review_checklist.py` 鎖定 checklist 內容與 TODO closure；不改 agent runtime、不改 `AGENTS.md` / `CLAUDE.md`，未新增 schema/API/AI/semantic/runtime/deploy scope。
- [ ] **Desktop Shell Phase 0**：已在下方「產品方向：桌面化」追蹤；本次 intake 確認其優先級仍成立，不另開重複項。


### Desktop and i18n Details

## 產品方向：桌面化（.exe 視窗程式）— 決策與待辦（2026-06-14）

Go 重構的目標之一是把本機產品封裝成**獨立 .exe 視窗程式**（非 .bat 啟動、非純 console）。本節記錄相關決策與待辦，供後續開發接續。

**已定決策**
- **桌面模型 = 視窗程式**，需有「關閉視窗時：連背景一起關 / 只關視窗、背景常駐（close-to-tray）」設定。tray 常駐主要服務「仍想用 API」的使用者。**關閉行為預設 = 直接結束行程**（2026-06-14 拍板）；close-to-tray 常駐為進階選項，使用者主動開啟。
- **Windowing 技術 = 內嵌 WebView2，純 Go syscall（2026-06-14 拍板）**：
  - 單一 .exe = 在同一行程內啟動現有 Go server（goroutine，沿用 `go-shadow/main.go`）+ 主執行緒開 WebView2 視窗指向 `127.0.0.1:<port>` + tray icon + named mutex 單一實例。後端零改動。
  - 套件走 **`jchv/go-webview2`（純 syscall，可保 `CGO_ENABLED=0`）**，**不用** `webview/webview_go`（要 cgo，會毀掉純 Go build 與 linux/arm64 交叉編譯）。
  - **無 console 視窗**：正式 build 用 `-ldflags="-H=windowsgui"`（GUI subsystem，從不配給 console，非事後隱藏）。代價：stdout/stderr 無處顯示，log 必須寫檔。
  - **無孤兒行程**：server 是同行程 goroutine，非 spawn 子行程；關視窗 → 行程結束 → server 隨之消失，不會殘留背景。
  - **唯一真風險**：WebView2 與 tray 都要主執行緒 Win32 message pump，會互搶。解法 = 自寫薄層 `Shell_NotifyIcon` 共用單一 message loop。**故先 spike 驗證事件迴圈，再接後端。**
- **資料庫還原 = 重啟式（已實作，2026-06-14）**：`POST /api/server/backup/restore` 寫 pending-restore 標記 → 程序重啟 → 開機時於 `openDB` 前 swap（覆蓋前自動存 `prism_pre_restore_*.db`）。重啟協定：supervised（systemd，靠 `INVOCATION_ID` 偵測）走 `os.Exit(42)`；獨立 .exe 走自我 re-exec。**「重啟」僅 Prism 程序重開，非 PC/Pi 重開機。**
- **備份策略**：**Pi 維持每週自動備份（keep 3）**；**.exe 本機不做自動排程**，使用者自行手動按備份即可。→ 不新增本機 scheduler。
- **下載備份不留 server-side 記錄（已實作）**：`/backup/download` 改吐暫存快照、傳完即刪；server-side 留存交給 `/backup/rotate`。
- **設定精簡（hidden sections，已實作）**：`設定 > 部署` 移除「部署安全邊界」「端口設定（PortConfigSection）」「版本更新（UpdateSection）」三區，封裝 .exe 後對使用者無用、在 Pi 上也僅資訊性。**元件檔仍保留**於 `frontend/src/components/settings/`，僅未 render。**復原方式**：在 `SettingsPage.tsx` deploy tab 重新 import 並加回 `<PortConfigSection />` / `<UpdateSection />` 與「部署安全邊界」SectionPanel 即可。部署 tab 現只剩 `ServerDashboardSection`。

**待辦（未施工，待後續設計）**
- [ ] **.exe 桌面外殼（windowing 技術已拍板，見上方「已定決策」）** — 分階段施工：
  - [ ] **階段 0：message loop spike**（下一步，進行中）。獨立 `desktop-spike/`（自己的 go.mod，僅 `golang.org/x/sys/windows` syscall，零第三方）：空 Win32 視窗 + tray icon（右鍵 Show / Quit）+ **單一 message loop** 同餵視窗與 tray。驗收：tray 選單有反應、關視窗正常退出、loop 不卡。spike 階段先用普通 console build（看得到 log 好除錯），不引 WebView2。
  - [ ] **階段 1：接 WebView2**。spike 綠後引 `jchv/go-webview2`，視窗指向 `127.0.0.1:<port>`，沿用同一 message loop。
  - [ ] **階段 2：接後端 + 單一實例**。同行程 goroutine 起 Go server、named mutex 單一實例（第二次啟動喚醒既有視窗）。
  - [ ] **階段 3：正式封裝**。切 `-ldflags="-H=windowsgui"`、log 寫檔、關閉=直接結束、close-to-tray 進階選項、開機自啟（registry Run key）。重啟協定（exit 42 / re-exec）在此串接驗證。
- [x] **本機儀表板硬體讀值修正（Windows）（2026-06-14 完成）**：新增 `go-shadow/hardware_windows.go`，以 kernel32（GetDiskFreeSpaceExW / GlobalMemoryStatusEx / GetTickCount64）讀真實磁碟/記憶體/uptime；`hardware_other.go` build tag 改為 `!linux && !windows`。CPU 溫度在 Windows 維持 N/A（無第三方驅動無可靠 API，誠實回 nil）。regression：`hardware_windows_test.go`。native build/test + linux/arm64 cross-build 皆綠。
- [ ] **語系（i18n）還原** → 獨立大工，細項見下方專節。與桌面化無關，可獨立排程。

---

## i18n（多語系）還原 — 進行中（2026-06-17 更新）

**目標**：中(zh-TW)/英(en)/日(ja)/韓(ko) 四語，於 `設定 > 外觀` 即時切換、localStorage 持久化。

**現況盤點**（`frontend/src/i18n/index.ts`）
- 2026-06-17 已把 locale 接入 `useAppStore` reactive state；`useTranslation()` 會訂閱 locale 變更並觸發 React 重繪。
- 2026-06-17 已擴成 zh-TW、en、ja、ko 四語，並在 `設定 > 外觀` 加入語言下拉；語系沿用 `localStorage` key `locale` 持久化。
- 2026-06-17 已完成 Settings shell / tabs / About 與 AppearanceSection 的第一批 key 化，並移除舊 i18n 字典中的過期 `ai` 區塊。
- 2026-06-17 已完成第二批 Home shell / Header / Sidebar / FilterStrip / HomePage / NoteCard 字串抽取，並同步補 zh-TW/en/ja/ko 字典；使用者資料（分類、標籤、筆記內容）不翻譯。
- 2026-06-17 已完成第三批 ReadingView / NoteEditor / editor 子元件與 hooks 字串抽取，包含閱讀面板、編輯器 toolbar/sidebar、附件、圖片管理、history、drag/drop/paste/prompt extraction toast/confirm；使用者內容、分類、標籤、附件標題與筆記標題不翻譯。
- 2026-06-17 已完成第四批 Prompt Builder 字串抽取，包含頁面 chrome、參數群組、輸出預覽、Wizard、alert/error 與 LLM optimization copy；Prompt Builder 產出的 prompt 內容、API options/templates、分類匹配資料仍保留原文不翻譯。
- 2026-06-17 已完成第五批 Settings 維護深層 section / server dashboard / backup-restore 字串抽取，包含匯出/匯入/還原資料庫、還原點管理、硬體/日誌/服務管理、維護檢查與資料庫統計；備份檔名、API log line、version/changelog 資料與使用者內容不翻譯。
- 2026-06-17 已完成第六批 Settings 組織管理（DataManager）字串抽取，包含分類新增/編輯/刪除、標籤 rename/delete/merge、confirm/toast/placeholder/aria-label；使用者自訂分類名稱與標籤名稱不翻譯，刪除分類遷移目標顯示實際 default category 名稱。
- 2026-06-17 已完成第七批 global API/toast error adapter 字串抽取；axios interceptor 的 network / 5xx fallback toast 走 `apiErrors` 四語 key，後端回傳的 `message` / `error` 仍保留原文優先顯示。
- 2026-06-17 已完成第八批 remaining hardcoded UI string audit / hidden legacy settings triage。Active UI 待抽：`CommandPalette.tsx`（命令面板群組、命令標題/副標/placeholder/toast/empty）、`SecuritySection.tsx`（CSRF 說明與 toast）、`DangerZoneSection.tsx`（危險區域三組清理 workflow）、shared UI fallback（`ConfirmDialog.tsx` 預設按鈕、`Toast.tsx` / `Modal.tsx` aria label）。Deferred/hidden：`PortConfigSection.tsx`、`UpdateSection.tsx` 仍保留但未由 `SettingsPage` render；`TagInput.tsx` 目前未掛載，先列 legacy/deferred，不阻塞 active i18n 收尾。Allowed non-UI/data literals：Settings tab fallback `label`、Appearance option `name` metadata、Prompt Builder 分類匹配字串、註解與 API/server 動態內容。
- 2026-06-17 已完成第九批 active UI final 字串抽取，包含 `CommandPalette.tsx`、`SecuritySection.tsx`、`DangerZoneSection.tsx`、shared UI fallback（`ConfirmDialog.tsx` / `Toast.tsx` / `Modal.tsx`）；以上 active UI surface 均已補 zh-TW/en/ja/ko key。Deferred/hidden 與 allowed non-UI/data literals 仍照第八批分類，不阻塞階段 3 active UI 收尾。驗證：`npm run build`、`pytest tests/test_frontend_i18n_settings.py -q`（19 passed）、`pytest tests/ -v`（303 passed）、active UI hardcoded scan 無命中、Chrome rendered smoke（CommandPalette + Settings access，zh-TW/en/ja/ko，0 app console/page errors）、`git diff --check`（僅既有 LF→CRLF warning）。
- 2026-06-17 已完成階段 5 收尾：缺漏 key 先回 zh-TW fallback，四語都沒有該 key 才回 key 字串並 `console.warn`；`{count} 參數替換` 保留並改成 nullish fallback；新增 namespace-level `TranslationKey` / `TranslationParams` 型別與 `useTranslation()` typed function surface，作為後續固定 key 逐步收斂的 typed guard。全量 deep key union 曾評估但目前字典規模會讓 TypeScript 報 `Type instantiation is excessively deep`，故本輪不採用；動態 key 仍可明確傳入 string。未新增大型 UI 抽字串批次，未改後端/schema/runtime。
- 2026-06-17 已補預設分類顯示 i18n：只對 DB 名稱完全符合原始 seed 的 5 個分類（`提示詞 | Prompt`、`筆記 | Note`、`教學 | Tutorial`、`資料 | Data`、`靈感 | Inspiration`）做顯示層翻譯；英文顯示純英文。若預設分類名稱已被使用者改過，或是後續新增的自訂分類（例如 `美食 | Gourmet`），語系切換時保留 DB 原文，不自動改字。此規則只改前端 display helper，不改 DB/schema/API。
- 後續建議：i18n active UI 可以先視為完成；若要繼續產品主線，優先進「Desktop Shell Phase 0 / message loop spike」，而不是再追 hidden legacy i18n。

**施工順序（建議分階段，避免一次全改）**
- [x] **階段 1 — 修反應式根**（2026-06-17 完成）：locale 已移入 `useAppStore`，新增 `useTranslation()` hook；`t()` / `translate(locale, key)` 保留給非元件與測試場景。
- [x] **階段 2 — 切換器 + 持久化**（2026-06-17 完成）：`AppearanceSection`（設定 > 外觀）已有四語下拉，沿用 localStorage，切換後 Settings / Appearance 已 key 化區塊即時重繪。
- [x] **階段 3 — 字串抽取**（2026-06-17 active UI 完成）：已完成第一批 Settings shell / tabs / About / AppearanceSection、第二批 Home shell / Header / Sidebar / FilterStrip / HomePage / NoteCard、第三批 ReadingView / NoteEditor / editor 子元件與 hooks、第四批 Prompt Builder、第五批 Settings 維護深層 section / server dashboard / backup-restore、第六批 Settings 組織管理（DataManager）、第七批 global API/toast error adapter、第八批 remaining hardcoded UI string audit / hidden legacy settings triage、第九批 CommandPalette / Security / DangerZone / shared UI fallback。Hidden/deferred 檔案（PortConfigSection / UpdateSection / TagInput）不阻塞 active UI completion。
- [x] **階段 4 — 補 ja/ko 字典**（2026-06-17 active UI 完成）：已補第一批 Settings / Appearance key、第二批 Home shell / NoteCard key、第三批 editor / reading key、第四批 promptBuilder key、第五批 Settings 維護/備份/Server Dashboard key、第六批 DataManager key、第七批 API error fallback key、第九批 active UI final key 的 ja/ko；後續若恢復 hidden/deferred UI，再於該 gate 同步補四語。
- [x] **階段 5 — 收尾**（2026-06-17 完成）：缺漏 key 先回 zh-TW fallback，四語都沒有該 key 才回 key 字串 + `console.warn`；`{count} 參數替換` 已保留；新增 namespace-level `TranslationKey` / `TranslationParams` 型別與 typed `useTranslation()` surface，作為後續固定 key 逐步收斂的 typed guard；全量 deep key union 因 TypeScript 深度限制暫不採用。Hidden/deferred UI 若日後恢復 render，需在該 gate 同步補四語 key。

**注意**：純前端、不動後端/schema。字串抽取會碰大量元件檔，務必分批小 PR，不要一次 mega-diff。

