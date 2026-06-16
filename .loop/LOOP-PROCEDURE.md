# Prism Loop Engineering Procedure for Codex

本檔是 Codex 版 Loop Engineering 流程。它只規範開發工作怎麼跑，不是 Prism 產品 runtime 的一部分。

## 鐵則

1. 先讀 `.loop/manifest.md`，再開始任務。
2. 規則只從 Prism 既有治理文件讀取；不要把外部模板規則貼進任務判斷。
3. `verify` 階段必須實際執行 manifest 的 `gate` 指令；gate 未通過不得宣稱完成。
4. 若 gate 失敗，帶著真實輸出回到 `iterate` 修正；預設最多 5 輪，除非 manifest 指定不同上限。
5. 使用者可隨時說「停」、「中斷迴圈」、「先回報目前狀態」；收到後停止新動作並回報目前讀取、修改、驗證狀態。

## 程序

### 0. Load Manifest

- 讀 `.loop/manifest.md`。
- 確認 manifest 指到的治理文件存在。
- 若文件缺失，回報缺哪個檔案並停止，不自行編規則。

### 1. Explore

- 讀 manifest `explore` 列出的文件。
- 確認任務本質、受影響範圍、現有 runtime/source truth。
- 產出一句話任務本質與受影響範圍。

### 2. Plan

- 讀 manifest `plan` 列出的文件。
- 把任務切成一次一個、可驗收的最小步驟。
- 明確列出驗收依據與禁止越界範圍。

### 3. Execute

- 讀 manifest `execute` 列出的文件。
- 只改任務範圍內必要檔案。
- 不順手重構、不中途新增未被需求證明的抽象、依賴、runtime path 或 schema/API scope。

### 4. Verify

- 讀 manifest `verify` 列出的文件。
- 執行 manifest 的 `gate` 指令，使用真實輸出判定。
- 若任務只改文件，仍至少跑 manifest gate；若 manifest gate 不適合，需明確說明並執行 Prism 文件治理的最小替代檢查。

### 5. Iterate

- 讀 manifest `iterate` 列出的文件。
- gate 失敗就修正並重跑，直到通過或到達 `max_iterations`。
- 到達上限仍未通過時，停止並回報卡點、已試修正、下一步建議。

## 交付回報格式

```text
目前完成層級：文件完成 / 候選或本機通過 / 正式流程接入 / 部署可用 / 舊依賴可刪

做了什麼：
- ...

gate 結果：
- 指令：<manifest.gate>
- 結果：通過 / 失敗（摘要真實輸出）
- 迭代輪數：N

未動的範圍：
- ...

風險 / 未解：
- ...
```

不要只寫「完成」；必須附完成層級與 gate 證據。
