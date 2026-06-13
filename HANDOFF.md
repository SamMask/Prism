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

- i18n 還原（中/英/日/韓，設定>外觀切換）— 純前端大工，5 階段，先修「`currentLocale` 非反應式、切了不重繪」這個根。
- 自啟動（registry Run key）— 併入桌面化。
