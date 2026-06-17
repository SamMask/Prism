# Prism Active TODO

本檔只保留目前可施工的 active roadmap、候選 backlog 與下一步入口。完成紀錄、舊 phase 與長版 changelog 全部移到 `docs/development-history/`。

---

## Current Truth（2026-06-18）

- Go primary 是唯一 current runtime owner；Python Flask backend source 已於 T053 移除。
- Go 漸進重構 T001-T053 已完成，完整完成紀錄見 `docs/development-history/go-primary-runtime-completion-20260617.md`。
- 2026-06-16 Core UX intake 已吸收；已完成項與 2026-06-14/06-17 handoff 快照見 `docs/development-history/desktop-backup-i18n-handoff-20260617.md`。
- 2026-06-17 Core UX / Maintenance 三個 candidate 已完成：搜尋可解釋性 UX、search integrity diagnostics + 手動 FTS rebuild、maintenance health overview。未新增 semantic search、SearchHistory DB、自動修復、schema/API exposure boundary 或 Pi deploy 變更。
- 2026-06-17 Server Dashboard Windows 硬體顯示已收斂：Windows 不顯示 CPU 溫度 N/A 卡，改以資料位置卡補位；Pi/Linux 有溫度讀值時仍顯示 CPU 溫度與 uptime 系統資訊。
- 2026-06-17 Desktop Shell Phase 0-6 已完成：Windows desktop shell、direct `Prism.exe` GUI artifact、portable zip/folder、clean-unzip smoke、installer/updater deferred、Pi deployment boundary unchanged。
- 2026-06-18 Desktop Shell post-package follow-up 已收斂為簡化 portable 路線：雙擊 `Prism.exe` 時預設資料固定放在 exe 同層 `PrismData\`；`--data-dir` / `PRISM_GO_DATA_DIR` 只作進階/debug override。runtime 不再顯示第一次啟動資料夾選擇器、不寫 `PrismPortable.json`、不建立或修補桌面捷徑，避免 hidden PowerShell / shortcut automation 造成防毒或二次啟動疑慮。指定資料夾、Windows account data folder、桌面捷徑、WebView2 bootstrap、Start Menu、uninstall/update 流程全部延後到真正要做 installer gate 時再一起處理。portable package 會帶 `static/config/prompt_options.json` / `wizard_options.json` 供 Prompt Builder fresh data-dir seed；`Prism.ico` 由 `scripts/generate_prism_icon.ps1` 程式生成（方塊 + P），並由 `scripts/generate_windows_resource.ps1` 內嵌到 Windows exe resource。Windows Server Dashboard 固定不顯示 CPU 溫度卡，改成四格：記憶體、儲存空間、資料位置、資料庫狀態。
- 2026-06-18 Desktop Shell post-package manual acceptance 已由使用者確認：將最新 portable 複製到其他資料夾執行後，Windows Defender 未再阻擋，雙擊 `Prism.exe` 可正常開啟，簡化後的 `PrismData\` 同層資料路線成立。
- 新使用者前端預設值（無 localStorage 時）已收斂為淺色 / 暖灰 / 典雅金、卡片開啟預覽模式、自動載入更多開啟；閱讀模式仍保留元件但不再是卡片開啟模式選項。
- `build/` 舊 generated smoke/build artifacts 已清理，只保留最新 desktop shell / portable smoke 輸出；真實資料目錄（DB、attachments、notes、uploads）未納入清理。
- i18n active UI 可先視為完成；不要再開大型 UI 抽字串批次。Hidden/deferred UI（`PortConfigSection`、`UpdateSection`、`TagInput`）若日後恢復 render，再於該 gate 同步補四語 key。

Current truth 仍以本檔、`docs/ARCHITECTURE.md`、`docs/SCHEMA.md`、`docs/API_REFERENCE.md` 與實際 source/runtime 為準。不得因歷史報告曾討論過，就直接擴 scope 成 AI、semantic search、GraphRAG、auto-writing、schema/API/runtime 或 Pi deploy 變更。

---

## 下一個可施工入口

### Desktop Shell Roadmap（Windows desktop only）

本路線只處理 Windows 桌面殼與封裝體驗；Pi 部署仍維持 Go primary artifact + systemd + Caddy，不引入 WebView2、tray、installer 或 Windows GUI 假設。

Desktop Shell post-package manual acceptance 已完成。Phase 0-6 與 portable baseline 是已完成證據；後續若要做 installer / updater，必須另開決策 gate，不得直接引入 installer stack。

已定桌面化產品決策：

- `.exe` 是視窗程式，不是 `.bat` 或純 console。
- 技術方向是內嵌 WebView2，傾向 `jchv/go-webview2`（純 syscall、可保 `CGO_ENABLED=0`），不採 `webview/webview_go`（需要 cgo）。
- 單一 `.exe` 後續目標：同一行程內啟動 Go server goroutine、WebView2 視窗指向 `127.0.0.1:<port>`、tray icon、named mutex 單一實例。
- 正式封裝才切 `-ldflags="-H=windowsgui"` 並改為檔案 log。

#### Phase 0 — message loop spike（2026-06-17 完成）

目標：先驗證 Windows desktop shell 的單一 Win32 message loop，可同時服務空視窗與 tray icon，再決定是否接 WebView2 / 後端。

Contract：`CONTRACT-DESKTOP-SHELL-SPIKE`（見 `docs/CONTRACTS.md`）。

- [x] 建立獨立 `desktop-spike/`（自己的 `go.mod`）。
- [x] 僅使用 `golang.org/x/sys/windows` syscall；Phase 0 不引 WebView2、不接後端、不改 schema/API/runtime。
- [x] 空 Win32 視窗 + tray icon，右鍵選單至少有 Show / Quit。
- [x] 關閉視窗預設直接結束行程；close-to-tray 仍是後續正式封裝的進階選項。
- [x] 驗收：tray 選單有反應、關視窗正常退出、message loop 不卡住；普通 console build 保留除錯 log。

#### Phase 1 — WebView2 spike（2026-06-17 完成）

目標：在 Phase 0 已驗證的單一 Win32 message loop 上接入 WebView2 視窗，先載入受控本機 placeholder / URL target，確認 WebView2 與 tray 共用同一 loop 不互搶。

Contract：`CONTRACT-DESKTOP-SHELL-WEBVIEW2-SPIKE`（見 `docs/CONTRACTS.md`）。

- [x] `desktop-spike/` 保留為 Phase 0 isolated proof；Phase 1-3 正式桌面入口接到 `go-shadow --desktop-*`，以便 Phase 2 能使用同一行程 Go primary runtime internals。
- [x] 引入 `jchv/go-webview2` 驗證 WebView2 可顯示 placeholder / URL target。
- [x] Phase 1 standalone 模式不接 Prism Go server goroutine、不新增 API/schema/migration、不碰 production data、不改 Pi deploy。
- [x] 驗收：`go run . --desktop-webview-only --desktop-self-test ...` 通過；WebView2 message loop、tray Show / Quit、關閉退出可跑完 bounded self-test，debug console build 保留 log。

#### Phase 2 — Local runtime host integration（2026-06-17 完成）

目標：把桌面殼與 Go primary runtime 合成同一行程的本機桌面模式，WebView2 指向 `127.0.0.1:<port>`。

Contract：`CONTRACT-DESKTOP-SHELL-RUNTIME-HOST`（見 `docs/CONTRACTS.md`）。

- [x] 桌面入口 `go-shadow --desktop-shell` 啟動 Go server goroutine，port 明確，啟動後先等 `/healthz`。
- [x] 使用 Go primary 既有 external data-dir contract；desktop default fresh DB 是 `prism_desktop_dev.db`，避免誤碰 production-like `knowledge.db` guard。
- [x] WebView2 只在 health 通過後導向本機 URL；啟動失敗會回傳錯誤並寫入 desktop shell log。
- [x] Quit / close 會先觸發 WebView message loop exit，再執行 HTTP server shutdown。
- [x] 不新增 API/schema/migration，不碰 production Pi data，不改 Pi deploy。
- [x] 驗收：`go run . --desktop-shell-smoke --data-dir <temp> --addr 127.0.0.1:<free-port>` 通過，fresh DB 建立、`/healthz` 200、shutdown 正常。

#### Phase 3 — Windows desktop UX hardening（2026-06-17 完成）

目標：把 spike 變成使用者可接受的 Windows 桌面 `.exe` 行為，但仍不做安裝包。

Contract：`CONTRACT-DESKTOP-SHELL-UX-HARDENING`（見 `docs/CONTRACTS.md`）。

- [x] GUI build script 使用 `-ldflags="-H=windowsgui"`，正式桌面 build 不出現終端機；`PrismDesktop-debug.exe` 保留 console。
- [x] 加入檔案 log，預設寫到 `data-dir/logs/desktop-shell.log`，涵蓋 shell init、runtime health 與 shutdown path。
- [x] 加入 named mutex 單一實例；第二次啟動會嘗試 bring-to-front 既有 `webview` 視窗，不再開第二個 server。
- [x] 明確定義 close 行為：第一版維持 close exits process；close-to-tray 仍是後續 UX gate。
- [x] Windows CPU 溫度維持隱藏策略；Dashboard 空位由目前 Prism 資料位置補位，不新增 Windows-only sensor dependency，也不顯示對本機版價值低的主機 uptime。
- [x] 驗收：`scripts/build_desktop_shell.ps1 -Mode Both` 通過，bounded WebView2/tray self-test 通過，runtime smoke 會建立 desktop log。

#### Phase 4 — Portable Windows package（2026-06-17 完成）

目標：產出不需安裝的 portable Windows release artifact，先滿足「直接執行檔」需求。

- [x] `scripts/build_desktop_portable.ps1` 產出 portable zip / folder：`Prism.exe`、`PrismDesktop-debug.exe`、`README-PORTABLE.md`。
- [x] Desktop build 以 `main.desktopShellDefault=1` link-time flag 讓 `Prism.exe` 直接進 Windows desktop shell；一般 `go run` / Pi artifact 不受影響。
- [x] 第一次啟動使用 external data-dir；`--data-dir` / `PRISM_GO_DATA_DIR` 最高優先，否則預設 exe 同層 `PrismData\`，讓綠色版資料跟著資料夾移動。
- [x] 2026-06-18 follow-up：移除第一次啟動資料夾選擇器、`PrismPortable.json` persisted choice、桌面捷徑建立/修補與 hidden PowerShell shortcut automation；指定資料夾、Windows account data folder、桌面捷徑與 WebView2 bootstrap 改列 installer gate deferred。
- [x] 2026-06-18 follow-up：主視窗在導向本機 runtime 前先顯示啟動畫面，避免使用者看到無說明白屏。
- [x] 2026-06-18 follow-up：portable folder/zip 會帶 `static/config/prompt_options.json` 與 `static/config/wizard_options.json`，讓 Prompt Builder 在乾淨 data-dir 可由 Go runtime seed config，不依賴 repo cwd。
- [x] 2026-06-18 follow-up：`Prism.ico` 由程式生成方塊 + P icon，portable package 帶同層 `Prism.ico`；build scripts 會用 `rsrc` 產生暫時 `.syso`，把 icon 內嵌進 `Prism.exe` / debug exe resource，desktop shell 視窗/tray 也會載入同層 icon。
- [x] `scripts/smoke_desktop_portable.ps1` 從乾淨 unzip 目錄啟動 debug artifact，使用獨立 external data-dir，建立 fresh DB，跑 desktop runtime health + basic note create/search workflow，確認 DB/log 仍在 data-dir。
- [x] `docs/desktop/README-PORTABLE.md` 記錄 WebView2 Runtime 前置條件；本 phase 不做 bootstrap installer。
- [x] 不做 MSI/NSIS/WiX installer、不做 auto updater、不改 Pi deploy。
- [x] 驗收：portable smoke、GUI `-H=windowsgui` build flag、artifact 無 bundled DB、desktop log 可定位。

#### Phase 5 — Installer / updater decision gate（2026-06-17 完成）

目標：只在 portable artifact 已穩定後，再決定是否值得做安裝包。預設不做，除非後續需求明確。

- [x] Installer 必要性只在需要 Start Menu、檔案關聯、自動安裝 WebView2 Runtime、移除程式或更新流程時成立。
- [x] 目前決策：不引入 NSIS / WiX / MSIX；portable zip 是 Windows release 主路徑。
- [x] Auto updater 另開 security / rollback gate；不得與 installer 第一版混做。
- [x] 驗收：`CONTRACT-DESKTOP-SHELL-INSTALLER-DECISION` 鎖定 installer deferred，build/smoke scripts 不含 installer stack。

#### Phase 6 — Pi deployment boundary check（2026-06-17 完成）

目標：確認 Windows desktop 化沒有污染 Pi / headless deployment。

- [x] Pi 仍使用 linux/arm64 Go primary artifact、`prism-go-primary.service`、Caddy reverse proxy、`DEPLOY-PI.md` 流程。
- [x] Pi 不包含 WebView2、Win32 tray、Windows mutex、Windows GUI build flag、installer/updater。
- [x] Desktop shell code 透過 `desktop_shell_windows.go` / `desktop_shell_other.go` build tags 與 Pi runtime 分離；portable scripts 只建 Windows artifact。
- [x] 驗收：Windows desktop package smoke 通過；Pi artifact build / deploy docs 不引用 desktop-only path。

#### Desktop Shell post-package manual acceptance（2026-06-18 完成）

結果：使用者已把最新 portable 複製到其他資料夾執行並確認 OK，Windows Defender 沒有再阻擋。這代表移除 first-run picker / shortcut automation / hidden PowerShell 後，portable baseline 可接受。

目前 desktop shell 不再有 active construction item。只有未來明確需要 Start Menu、桌面捷徑、指定資料夾 UI、WebView2 bootstrap、uninstall 或 update flow 時，才重新評估 installer / updater。

### Windows Desktop vs Pi Deployment 差異表

| 面向 | Windows desktop | Raspberry Pi |
|---|---|---|
| 入口 | `Prism.exe` GUI app；正式 build 不出現終端機 | systemd service 啟動 Go primary binary |
| UI | WebView2 內嵌本機 Web UI + tray | 使用瀏覽器連 `https://prism.local` / Caddy |
| Runtime | 同一行程內 desktop shell + Go server goroutine | headless Go primary service |
| 網路 | 綁 `127.0.0.1:<port>`，只給本機 WebView2 | Caddy reverse proxy 到 local service port |
| 資料 | 預設 exe 同層 `PrismData\`；`--data-dir` / env 僅作進階 override | Pi 上既有 production data dir |
| Log | 檔案 log + debug console build | journald / service log / Go runtime log |
| 打包 | 先 portable zip / folder；installer deferred | artifact deploy + systemd + rollback / soak |
| 相依 | WebView2 Runtime、Win32 shell APIs | Linux/arm64、systemd、Caddy |
| 不共用項 | tray、window、mutex、`-H=windowsgui` | Caddy live routing、systemd enable/restart |

---

## Active Candidates

### Core UX / Maintenance

- [x] **SEARCH-UX-CANDIDATE-01 Search explainability UX**（2026-06-17 完成）：Home 已加入 Search Context Bar、Empty State Recovery、Search Scope Hint、Recent Searches（`localStorage` 最多 5 筆、不進 DB）、Mobile Search Entry。未新增 relevance ranking、semantic search、attachment body snippets、SearchHistory DB、advanced query language 或每鍵即時搜尋。
- [x] **SEARCH-INTEGRITY-CANDIDATE-01 Search integrity diagnostics contract**（2026-06-17 完成）：已新增 `GET /api/system/search-integrity` 與 `POST /api/system/search-integrity/rebuild-fts`。第一版只做診斷與手動 FTS rebuild；禁止 VACUUM、改 Notes、改 Attachments、刪檔、自動修復、讓 Agent 自動觸發。
- [x] **MAINT-OVERVIEW-CANDIDATE-01 Maintenance health overview**（2026-06-17 完成）：Settings 維護頁已新增狀態總覽，只呈現資料一致性、搜尋索引與 WAL 手動狀態；不新增修復行為。

### Future Branch Candidates

以下是不同產品線或 sidecar 方向，先記錄不施工。Promote 前必須先補 contract / docs，不得直接改 Prism Core runtime。

- [ ] **BRANCH-CANDIDATE-CRR-LITE**：Cerberus Research Radar Lite。第一版只可先做 docs/schema：Research Signal Card、Normalized Paper Candidate、Paper Source Query Contract、Dedup Contract、LLM Extraction Contract、Prism/Cerberus mapping。不接 API、不接 LLM、不寫 Prism、不寫 CerberusCoin repo；paper 只能變成可測假設，不能變成策略結論。
- [ ] **BRANCH-CANDIDATE-AI-BRIDGE**：外部 Agent 安全讀取 Prism 的 read-only bridge。不得內建 AI chat、embedding、semantic search、GraphRAG 或 agent runner；若未來啟動，先做 read-only contract 與安全邊界文件。
- [ ] **BRANCH-CANDIDATE-WATCH-LITE**：RSS / arXiv / GitHub / blog / URL tracking sidecar。只收集候選到 pending queue，不自動寫 permanent Prism note；等 Core UX 與備份/還原語義穩定後再評估。
- [ ] **BRANCH-CANDIDATE-ARCHIVE-INTAKE**：web / PDF / markdown / source intake sidecar。先記錄為匯入輔助方向，不得把 crawler、summarizer 或大量自動寫入帶進 Core。

---

## Archive Index

- `docs/development-history/go-primary-runtime-completion-20260617.md`：T001-T053 Go primary migration 完成敘事、artifact 與完整任務表。
- `docs/development-history/desktop-backup-i18n-handoff-20260617.md`：2026-06-14 local desktop / backup / dashboard handoff、2026-06-17 Core UX 與 i18n 詳細完成記錄。
- `docs/development-history/todo-archive-pre-go-primary-runtime-migration-20260606.md`：Go primary runtime migration active roadmap 前的完整 `docs/TODO.md` 原文歸檔。
- `docs/development-history/todo-changelog.md`：長版版本歷程。
- `docs/development-history/todo-completed-phases.md`：更早期完成 phase 與歷史工作清單。
