# Codex Task / Review Checklist

本文件把 `20260616-chatgpt-Prism-虛擬團隊討論會.md` 中可採用的 Codex 任務契約與審查條件收斂成可重複使用的 checklist。

Current truth 仍以 `AGENTS.md` / `CLAUDE.md`、`docs/TODO.md`、`docs/ARCHITECTURE.md`、`docs/SCHEMA.md`、`docs/API_REFERENCE.md` 與實際 source/runtime 為準。本文件只輔助交辦與 review；不修改 agent runtime、不取代 repo canonical docs、不授權任務外 scope。

## 使用時機

- 交辦 Codex 做小到中型 task、review、docs sync、UI wording、frontend-only 修補。
- 任務需要明確禁止 schema/API/runtime/AI/semantic search/無關重構時。
- reviewer 需要快速判斷回報是否真的完成驗證、是否超出 allowed files。

不適用：重大架構改版、DB migration、Pi production cutover、public exposure policy、跨產品線分支。這些需先回 `docs/TODO.md` 拆原子任務並補對應 contract。

## 任務 prompt 契約

每次交辦 Codex 時，盡量包含下列欄位：

```markdown
## 任務目標
- <要完成的單一結果>

## 背景
- <current truth、相關 TODO/contract/doc、已知限制>

## 允許修改檔案
- <精準列出可改路徑；若是 docs-only 就只列 docs/tests>

## 禁止事項
- 不改 schema / migration。
- 不新增或修改 API contract。
- 不引入 AI / embedding / semantic search / GraphRAG。
- 不改 runtime / deploy / Pi service / Caddy。
- 不做任務外重構或大量格式化。

## 具體要求
- <行為、文案、UI、文件、測試等具體條件>

## 驗收指令
- <targeted tests>
- <lint/typecheck/build/smoke，依任務風險選最小充分集合>

## 回報格式
### Changed
- ...

### Verified
- ...

### Not Changed
- No API changes.
- No schema changes.
- No backend changes.
- No unrelated feature work.
```

## Allowed Files

交辦時要把可改範圍寫窄。若需要擴 scope，Codex 應先指出原因並把擴 scope 寫入 TODO/contract，而不是順手施工。

| 任務類型 | 常見允許檔案 | 典型驗收 |
|---|---|---|
| docs-only checklist / current-truth sync | `docs/*.md`、必要的 docs regression test | `pytest <targeted test>`、`git diff --check` |
| frontend wording / IA | 指定 React component、指定 frontend tests | targeted pytest、`cd frontend && npm run build`、browser/headless smoke |
| API contract docs | `docs/API_REFERENCE.md`、`docs/contracts/*`、contract regression | targeted pytest、必要時 `go test ./...` |
| Go runtime change | 指定 `go-shadow/*`、contract/test files | `cd go-shadow && go test ./...`、targeted pytest、runtime smoke |

## Forbidden Scope

以下情況一律不得在未授權任務中順手做：

- schema / migration / DB table 或欄位變更。
- 新增、移除或改變 API endpoint、request、response、status code。
- 引入 AI、embedding、semantic search、GraphRAG、LLM extraction、agent runner。
- 改 runtime owner、deploy script、Pi service、Caddy、packaging、public exposure policy。
- 自動修復、自動刪資料、自動 VACUUM、背景排程或未要求的 data mutation。
- 任務外重構、跨檔大量格式化、抽象層新增、dependency 新增。
- 回傳本機絕對路徑到使用者資料或把私有 runtime data 納入 docs。
- 恢復已隱藏的 `PortConfigSection`、`UpdateSection` 或「部署安全邊界」區塊，除非 task 明確授權。

## Verification Checklist

驗證前先寫清楚要證明的 claim，再選最小充分指令。

- Docs-only：`pytest <docs regression>`、`git diff --check`、必要時 mirror check。
- Frontend-only：targeted pytest、`cd frontend && npm run build`、browser/headless smoke 截到 DOM 或畫面證據。
- Go runtime/API：`cd go-shadow && go test ./...`、targeted pytest、必要時本機 smoke。
- Pi deploy：依 `DEPLOY-PI.md` 執行 cutover，確認 service active、Caddy/API header、version/status endpoint、journal 無新錯誤。

若驗證不能跑，回報必須列在 `Not-tested` 或 `Verified` 中說明缺口；不得宣稱完成。

## Reviewer Checklist

Review 時先看這些問題：

- Changed files 是否都在「允許修改檔案」內？
- 是否改到 schema/API/backend/runtime/deploy/Pi？
- 是否新增 AI/semantic/embedding/GraphRAG 或自動修復行為？
- 是否恢復 hidden `PortConfigSection` / `UpdateSection` / 部署安全邊界？
- 是否有任務外重構、大量格式化、dependency 新增？
- 驗收指令是否真的跑過，且輸出能支持完成 claim？
- `### Not Changed` 是否明確列出 API/schema/backend/unrelated feature work 沒動？

## Hard Return Conditions

出現以下任一項，reviewer 應退回，不把任務視為完成：

- 未授權改 schema、migration、API contract、backend runtime 或 deploy path。
- 未授權新增 AI / embedding / semantic search / GraphRAG。
- 未授權加入自動修復、自動刪資料、背景排程、Pi service/Caddy 變更。
- 任務外大重構、跨檔大量格式化、引入新 dependency。
- 回報宣稱完成但沒有 fresh verification evidence。
- 回報把未測試、推測、舊文件內容說成 current runtime truth。
- 回傳或固化本機絕對路徑、private runtime data、credential-like 內容。

## 回報格式

```markdown
### Changed
- <檔案與使用者可見結果>

### Verified
- `<command>` -> <關鍵結果>

### Not Changed
- No API changes.
- No schema changes.
- No backend changes.
- No unrelated feature work.
```

若有部署，另加：

```markdown
### Deployed
- Pi target: <alias/service/url>
- Evidence: <service/API/header/journal summary>
```
