# Prism 深度審計報告 — 2026-05-13

> **檢視範圍**：v2.4.5（Headless KMS 穩定運行階段）
> **檢視者**：Claude Opus 4.7（read-only audit）
> **方法**：靜態分析 + 跨檔案 grep + 文件 / 程式 / 測試三向交叉比對 + 與既往 cco 體檢報告對齊
> **限制**：本輪僅讀取，未修改任何檔案；測試僅讀取 `test_run.log`，未重新執行 pytest

---

## 1. Project Mental Model

| 維度 | 觀察 |
|---|---|
| **產品目標** | 本機優先、離線可用的個人知識/Prompt 管理中樞，同時把後端當成可被外部 Agent（Claude Code、MCP、自製腳本）直接呼叫的 **Headless KMS REST API**。重點放在「穩定儲存 + 純關鍵字 FTS + 乾淨 REST」。 |
| **Active Scope** | `docs/TODO.md` Phase 13 已完成（v2.4.5，2026-05-05）。**目前處於穩定維護期**，沒有正在進行的 Phase；下一個 Phase 編號 14+ 尚未被宣告。 |
| **Canonical SoT** | 程式：`config.py` / `migrations/__init__.py` / `routes/`。文件：`AGENTS.md`、`CLAUDE.md`、`docs/SCHEMA.md`、`docs/ARCHITECTURE.md`、`docs/API_REFERENCE.md`、`docs/TODO.md`。**AGENTS.md 與 CLAUDE.md 內容完全一致，是雙頭真理**（見 §3.1）。 |
| **歷史 / 封存** | `docs/過期/` 放完成的審核與重構評估；`garbage-can/` 放 V1 時期構想筆記、舊報告、unnamed.jpg 等雜物；`demo/` 只有一份 16KB 的 index.html。**這三個目錄都不應該被當成 active scope**，但 `docs/TODO.md` 和 `docs/Prism.md` 仍多處引用 `garbage-can/1230-審核報告.md`。 |
| **開發方向** | **維護模式**（穩定運行）。沒有大重構、沒有新功能 epic。最近三版（v2.4.3 / v2.4.4 / v2.4.5）都是契約修補與搜尋擴充。 |
| **明確禁止** | (1) 不引入 AI/ML 依賴（numpy / sentence-transformers / torch / NIM / Ollama）。(2) 不使用 CDN，所有前端資源本地化。(3) 不破壞 API 契約（修改要建遷移）。(4) 不在 WSGI 請求生命週期內啟動背景執行緒。(5) 不直接操作 DB，統一使用 `db.py` 的 `get_db()`。 |
| **已完成但未充分驗證的點** | 主要由 `test_run.log`（2026-05-05）證明 70 個 pytest 全綠。**但前端 tsc/build 沒有 CI 記錄、UI 互動沒有自動化、Pi 部署只有手動驗證腳本**。 |
| **宣稱完成但文件 / 程式不一致** | docstring、INDEX.md 維護狀態欄位、Prism.md 規劃殘留、tests/README.md 計數，**全都落後於現況**（見 §3）。 |

**一句話結論**：地基已經乾淨（AI 拔除、Schema 收斂、SSRF / localhost / CSRF 都補了），但文件層出現「**程式跑在 v2.4.5、文件記錄停在 v2.4.1 / v2.4.2 / 甚至 v1.0**」的時差。沒有 P0 級別的程式錯誤，**最大風險是文件導航被破壞**（README/INDEX/TODO 各自指向不同路徑的同一份過期報告），會讓未來開發者（或外部 Agent）誤判專案狀態。

---

## 2. Executive Risk Summary

| # | 等級 | 一句話 | 涉及 | 為什麼重要 |
|---|---|---|---|---|
| R1 | **R1** | README.md 與 INDEX.md 引用 `docs/20260412-cco-綜合分析報告.md`，實際檔案在 `docs/過期/` 之下，3 條超連結全部 404 | [README.md:32](README.md:32), [README.md:108](README.md:108), [README.md:164](README.md:164), [docs/INDEX.md:36](docs/INDEX.md:36), [docs/CONTRIBUTING.md:154](docs/CONTRIBUTING.md:154) | 任何照文件操作的新成員或外部 Agent 進入專案時，第一件做的事就是讀「最新體檢報告」。連結壞掉等於閘門失守。 |
| R2 | **R1** | `AGENTS.md`（2026-05-05）與 `CLAUDE.md`（2026-04-12）內容幾乎逐字相同，但兩者都自稱「每次開發前必讀」，雙頭真理 | [AGENTS.md](AGENTS.md) vs [CLAUDE.md](CLAUDE.md) | 一旦兩者開始漂移，未來編輯者必定只改其中一份；Claude Code 預設自動載入 CLAUDE.md，AGENTS.md 則需手動讀。對外部 Agent 不可預測。 |
| R3 | **R1** | `docs/TODO.md` 頭部「核心目標 = Headless Architecture + Local AI」、「最後更新 2026-04-12」、Phase 10 仍標 🔴 Pending、引用 `1230-審核報告.md` 卻沒給 `garbage-can/` 路徑 | [docs/TODO.md:1-13](docs/TODO.md:1), [docs/TODO.md:80-82](docs/TODO.md:80) | TODO 是 active construction queue 的唯一入口。頭部標題誤導程度高（"Local AI" 已於 v2.3.0 拔除）；Phase 10 顯示為 🔴 但 changelog 已記錄 v2.4.2 完成。 |
| R4 | **R2** | `docs/INDEX.md` 的「維護狀態」欄位多處錯誤：cco 報告寫 🔴 待修補（其實已完成）、SEQUENCE-UPLOAD.md 標 ⚠️ 部分過時（其實已更新）、API_REFERENCE.md 標 ⚠️ 部分端點已變更（其實已重寫於 2026-05-05） | [docs/INDEX.md:26](docs/INDEX.md:26), [docs/INDEX.md:36](docs/INDEX.md:36), [docs/INDEX.md:45](docs/INDEX.md:45) | INDEX 是文件導覽圖，狀態欄位錯誤會讓人忽略「其實已是正確」的文件、或誤入「其實已過時」的內容。 |
| R5 | **R2** | `routes/system.py:284-296` `check_consistency()` docstring 仍寫「檢查 Notes.type 與 category_id 的不一致記錄」、Response 描述仍列 `type_category_mismatch`；實際 code 已清乾淨 | [routes/system.py:284](routes/system.py:284) | 程式正確但 docstring 在說謊。閱讀者可能誤以為這個 endpoint 還在回報「type 不一致」，並基於此寫出永遠 0 命中的監控規則。 |
| R6 | **R2** | `docs/Prism.md` 同時宣稱 v2.3.0 拔除 AI（line 5），又在「1.2 資料層升級」描述「引入 ChromaDB 或 SQLite-VSS」（line 22）；又在 line 166 說「Phase 0 現為最高優先級」 | [docs/Prism.md:22](docs/Prism.md:22), [docs/Prism.md:166](docs/Prism.md:166) | 同一份戰略文件互相矛盾。INDEX.md 把它列為「🗄️ 歷史參考，不再更新」、但 README.md 把它列為「戰略路線圖」。雙重信號。 |
| R7 | **R2** | `scripts/check_deps.py` 仍 `import numpy, sentence_transformers`，但這兩個依賴已在 v2.3.0 從 requirements 移除；沒人呼叫此腳本 | [scripts/check_deps.py](scripts/check_deps.py) | 殭屍腳本。一旦有人按字面執行會永遠寫出 `Failed: ...`，而且違反 CLAUDE.md 禁止 AI/ML 依賴的精神。屬於 Linus 報告口中「殭屍引用」的同型問題。 |
| R8 | **R2** | `tests/test_offline_mode.py` 是 V1 (Jinja2) 時期遺物，檢查 `templates/index.html` 是否含 Vue.js / Tailwind CDN，但 V2 已轉 React SPA；該檔不是 pytest 收集格式（用 `main()` + `sys.exit()`） | [tests/test_offline_mode.py](tests/test_offline_mode.py) | 看起來像測試但不會跑，且檢驗目標跟現行架構完全不符。會讓人誤以為「離線模式有自動驗證」。 |
| R9 | **R2** | `tests/README.md` 列出 10 個測試檔、宣稱 "15 passed in 3.16s"，但實際 pytest 已有 24+ 個 test_*.py、70+ 個測試案例 | [tests/README.md](tests/README.md) | 測試文件與實際差距 4-5 倍，已完全脫節。新成員按此判斷覆蓋率會嚴重失準。 |
| R10 | **R3** | `init_db()` 在 fresh DB 上會先 CREATE 出 `text_embedding`-free 的新 schema，接著 run_migrations 仍會把 v9（ADD text_embedding）→ v14（DROP text_embedding）跑完。功能正確但語意冗餘 | [app.py:227](app.py:227), [migrations/__init__.py:101-105](migrations/__init__.py:101) | 不會壞，但會讓 `_detect_existing_schema()` 的偵測點（停在 v7）顯得詭異。屬於品味債，不是 bug。 |
| R11 | **R3** | `auto_fix_consistency()` 仍在每次冷啟動跑 DELETE 孤兒 + UPDATE NULL category_id；cco 報告把它列為「刻意略過」但實際 v2.4.5 仍每次跑 | [app.py:412-452](app.py:412) | 小 DB 無感。但 Pi 上 systemd 每次 restart 都會掃全表。屬於 cco 決議「等規模到一萬筆再優化」的延後事項，不算 active issue。 |
| R12 | **R3** | `docs/SEQUENCE-UPLOAD.md` 標版本 v2.3.0；`docs/DEPLOYMENT.md` 標版本 v2.4.2；`docs/CONTRIBUTING.md` 預期 "61 passed, 1 xfailed, 1 xpassed"；多處最後更新日落後現實 | [docs/SEQUENCE-UPLOAD.md:3](docs/SEQUENCE-UPLOAD.md:3), [docs/DEPLOYMENT.md:206](docs/DEPLOYMENT.md:206), [docs/CONTRIBUTING.md:115](docs/CONTRIBUTING.md:115) | 不致命，但屬於「Release Checklist 漏項」的累積跡象。CONTRIBUTING.md §144 自己列出的 Release Checklist 沒有納入「同步 docs 日期」。 |

---

## 3. Confirmed Inconsistencies

每一項都附證據檔案行號 + 後果 + 最小修正方式。

### 3.1 雙頭真理：AGENTS.md vs CLAUDE.md

- **問題**：兩份檔案內容幾乎逐字相同（必讀清單、執行規則、技術堆疊、禁止事項），均自稱為「Prism 開發指引（Claude Code 自動載入）」。
- **證據**：
  - [AGENTS.md](AGENTS.md) line 1：`# Prism 開發指引（Claude Code 自動載入）`
  - [CLAUDE.md](CLAUDE.md) line 1：完全相同
  - AGENTS.md 必讀表第一列指向 `AGENTS.md` 自己；CLAUDE.md 同列指向 `CLAUDE.md` 自己（彼此都把自己當成 single source of truth）
  - AGENTS.md 修改時間 2026-05-05，CLAUDE.md 修改時間 2026-04-12 — 兩份內容已開始時差。
  - README.md:25 只指向 `CLAUDE.md`，沒提 AGENTS.md。
- **後果**：未來編輯者只會修一份；另一份慢慢與現實脫節。外部 Agent 不知道該讀哪一份。Claude Code 預設讀 CLAUDE.md，但其他 Agent 框架可能讀 AGENTS.md（OpenAI Codex 等）。
- **最小修正**：(a) 留一份做 source（建議 CLAUDE.md，因為 Claude Code 自動載入），(b) 將 AGENTS.md 改為 1 行 stub：`此文件已併入 CLAUDE.md。`，或 (c) AGENTS.md 與 CLAUDE.md 都改為 1 行 stub 並把實質內容搬到 `docs/DEV-GUIDE.md`，兩個 stub 都指向它。**禁止繼續維持雙份完整內容**。

### 3.2 cco 體檢報告連結全壞

- **問題**：cco 報告於 2026-04-12 完成後檔案已移至 `docs/過期/20260412-cco-綜合分析報告.md`；但 README、INDEX、CONTRIBUTING 仍指向 `docs/20260412-cco-綜合分析報告.md`（沒有 `過期/` prefix）。
- **證據**（grep `docs/20260412-cco`）：
  - [README.md:32](README.md:32) — 「最新體檢報告」表格列
  - [README.md:108](README.md:108) — 測試章節腳註
  - [README.md:164](README.md:164) — SSRF 警告腳註
  - [docs/INDEX.md:36](docs/INDEX.md:36) — 審核報告區塊
  - [docs/CONTRIBUTING.md:154](docs/CONTRIBUTING.md:154) — Release Checklist 中的「過往 desync 案例參照」
- **後果**：對外部 Agent / 新人，這 5 條連結是「最新體檢報告」的唯一入口，全 404。
- **最小修正**：把所有引用統一改為 `docs/過期/20260412-cco-綜合分析報告.md`，或乾脆把該報告搬回 `docs/`（因為 README 仍把它列為「最新」）。**兩者擇一**，現況是兩邊都不對。

### 3.3 TODO.md 頭部資訊與實際狀態不符

- **問題**：[docs/TODO.md:1-13](docs/TODO.md:1) 多處過期：
  - line 4：「核心目標: **Headless Architecture + Local AI**」← Local AI 已於 v2.3.0 拔除。
  - line 5：引用 `1230-審核報告.md` 但實際路徑是 `garbage-can/1230-審核報告.md`。
  - line 6：「最後更新: 2026-04-12」← Phase 13 完成於 2026-05-05。
  - line 80：「Phase 10: 體檢報告修補 — 🔴 Pending v2.4.2」← Phase 10 所有 14 條 `[x]` 已勾，changelog v2.4.2 / 2026-04-12 已記錄完成。
- **證據**：自查 [docs/TODO.md:1-13](docs/TODO.md:1) 與 [docs/TODO.md:80-110](docs/TODO.md:80) 與 [docs/TODO.md:223](docs/TODO.md:223) changelog。
- **後果**：TODO 是 active construction queue。頭部誤導 → 開發者可能誤以為「現在還在做 AI」「Phase 10 還沒完」「文件停在四月」。
- **最小修正**：
  - 改 line 4 為 `**核心目標**: Headless KMS API + 純關鍵字 FTS 搜尋`。
  - line 5：刪除 `1230-審核報告.md` 引用，或改為 `garbage-can/1230-審核報告.md`（明示已歸檔）。
  - line 6：`最後更新: 2026-05-05`。
  - line 80：把 🔴 Pending 改為 ✅ 已完成 v2.4.2（或整段移到「已完成項目」區塊）。

### 3.4 routes/system.py docstring 殭屍

- **問題**：[routes/system.py:284-296](routes/system.py:284) `check_consistency()` docstring 仍說「檢查 Notes.type 與 category_id 的不一致記錄」、Response 範例列 `type_category_mismatch` 欄位。實際 code（line 298-337）已完全清乾淨。
- **後果**：閱讀此 endpoint 的人會誤以為它在做 type 比對；若有人寫監控基於這個欄位，會永遠拿到 KeyError。
- **最小修正**：把 docstring 改成現況：
  ```
  資料一致性檢查（不檢查 type，因為 Notes.type 已於 v12 移除）
  Response: { orphan_note_tags, unused_tags, null_category_id, fk_status, fk_enabled, health }
  ```

### 3.5 docs/Prism.md 內部自相矛盾

- **問題**：[docs/Prism.md](docs/Prism.md) 同時宣稱兩個矛盾事實：
  - line 5：「AI 功能已拔除（NVIDIA NIM / Ollama / sentence-transformers）」
  - line 22：「1.2 資料層升級（Next-Gen Data）：引入 ChromaDB（嵌入式）或 SQLite-VSS」
  - line 25：「強化關聯（Edges table），支撐知識圖譜」
  - line 84：「✅ API 自動化 (pytest): 63 測試通過」← 實際 70+
  - line 166：「**Phase 0 現為最高優先級**」← Phase 0 完成於 2024-12-31
- **後果**：戰略文件互相打架。INDEX.md 標它為「🗄️ 歷史參考，不再更新」，但 README.md:31 仍把它列為「戰略路線圖」。
- **最小修正**：擇一：
  - (a) 認真標記它為歷史檔案：在文件頂部加 `> ⚠️ 此文件為 V2 規劃期歷史記錄（2024-2026 重構過程），現行戰略已合併進 README.md 與 docs/TODO.md。`，並從 README 戰略連結移除。
  - (b) 將 line 22-25（Vector Store / Graph Relations）與 line 166 整段刪除或畫上刪除線，並把 line 84 的 63 改為「70+」。

### 3.6 docs/INDEX.md 多處維護狀態錯誤

- **問題**：[docs/INDEX.md](docs/INDEX.md) 的「維護狀態」欄位多處不符實情：
  - line 26：API_REFERENCE.md 標「⚠️ 部分端點已變更，以實際程式碼為準」← 該檔已於 2026-05-05 重寫為「以實際路由為準」的對接文件。
  - line 36：cco 報告標「🔴 待修補（追蹤於 TODO.md Phase 10）」← Phase 10 完成於 v2.4.2 / 2026-04-12。
  - line 45：SEQUENCE-UPLOAD.md 標「⚠️ 部分過時 — AI Worker（Ollama/CLIP）段落已無效」← 實際檔案 line 5 已明示 v2.3.0 移除，內容已更新。
- **後果**：閱讀者會「跳過實際是正確的文件」，並把已修補的問題重新當未修。
- **最小修正**：把這三列維護狀態改為 ✅ 已更新。

### 3.7 tests/README.md 已完全脫離現況

- **問題**：[tests/README.md](tests/README.md) 列出 10 個測試檔，但實際 `tests/` 有 24+ 個檔。範例輸出寫「15 passed in 3.16s」，實際 [test_run.log](test_run.log) 顯示 70+ 個案例。執行指令推薦 `.\python\python.exe -m pytest`，但 CLAUDE.md / README 的標準是 venv + `pytest tests/ -v`。
- **後果**：tests/README.md 給出的測試覆蓋面比現實窄一半以上；外部讀者會低估測試強度。
- **最小修正**：刪掉測試檔逐一列表（不要再維護表格），改為一段「執行方式」說明 + 連到 `pytest --collect-only` 自動列表的指令。把 `15 passed` 改為「以 `test_run.log` 為實際參考」。

### 3.8 scripts/check_deps.py 是殭屍

- **問題**：[scripts/check_deps.py](scripts/check_deps.py) 全內容只有 9 行：
  ```python
  try:
      import numpy
      import sentence_transformers
      with open("install_check.txt", "w") as f: f.write("Success")
  except ImportError as e:
      with open("install_check.txt", "w") as f: f.write(f"Failed: {e}")
  ```
  但 numpy / sentence_transformers 已於 v2.3.0 移除，現行 requirements.txt 沒這兩個套件。
- **證據**：grep 顯示沒有任何檔案 import 或呼叫 `check_deps`。
- **後果**：違反 CLAUDE.md「不引入 AI/ML 依賴」精神；任何人手動執行此腳本只會永遠寫出 `Failed: ...`，可能誤以為「AI 模組壞了」。
- **最小修正**：刪除整個檔案，或改寫成檢查 `flask, magic, PIL` 等實際依賴。

### 3.9 docs/CONTRIBUTING.md 數字過期

- **問題**：[docs/CONTRIBUTING.md:115](docs/CONTRIBUTING.md:115) 寫「預期: 61 passed, 1 xfailed, 1 xpassed」；line 49 寫「migrations/ ... v1–v14」（實際已至 v15）。
- **後果**：發版 checklist 的「測試通過」期望值停在 v2.4.2 時代。
- **最小修正**：把 61 改為「全綠（70+ cases）」或留「執行 `pytest tests/ -v`，全部需 PASS」；把 v14 改為 v15。

---

## 4. Suspected Bugs / Risk Hotspots

> 每項都是「未直接證實的高機率問題」，需要 grep 或寫測試驗證。

### 4.1 tests/test_offline_mode.py 已成 dead test，但若被誤觸會誤導

- **懷疑點**：此檔以 `main()` + `sys.exit()` 結構撰寫，pytest collection 不會把它當測試函式收集（因為沒有 `test_*` 命名的 function level test，只有 module 等級的 helpers）。但檔案前綴 `test_` 會誤導人以為是 pytest 用例。
- **推理依據**：[tests/test_offline_mode.py:21-132](tests/test_offline_mode.py:21) 全用 `def main(): ... if __name__ == '__main__': main()`；測試對象是 V1 `templates/index.html` 含 Vue.js / Tailwind CDN 字串，但 V2 React SPA 不走這個檔。
- **需要驗證的檔案**：`pytest tests/test_offline_mode.py -v --collect-only` 的輸出（推測為 0 collected）。
- **建議 grep**：`grep -n "def test_" tests/test_offline_mode.py`（推測無結果）。
- **建議測試**：N/A — 應該刪除或改寫，而非加測試。
- **優先級**：P2。不會壞當前功能，但會誤導離線模式被「自動驗證」的判斷。

### 4.2 init_db() 與 migrations 雙寫同樣資料表的時序漏洞

- **懷疑點**：[app.py:213-244](app.py:213) `init_db()` 先用 `CREATE TABLE IF NOT EXISTS Notes (... category_id INTEGER ... prompt_params TEXT ...)` 一次建出「最新版欄位」的 Notes 表；接著 [app.py:399](app.py:399) `run_migrations(db)` 才執行 v1→v15。對於**全新 DB**：
  1. CREATE 出含 `category_id` / `prompt_params` 的最新 Notes。
  2. `_detect_existing_schema()` 偵測到 `category_id` → 初始版本 v7。
  3. v8（attachments）、v9（add text_embedding）、v10（parent_id / ai_*）、v11（Embeddings 表）、v13（AI_Tasks）執行。
  4. v14 drop text_embedding / ai_*；v15 ADD prompt_params 命中 "duplicate column name"，被 except 接住跳過。
- **推理依據**：[migrations/__init__.py:101-105](migrations/__init__.py:101) v9 與 [migrations/__init__.py:177-191](migrations/__init__.py:177) v14、與 [migrations/__init__.py:306-313](migrations/__init__.py:306) 的「duplicate column name → skip」。
- **後果**：功能正確（最終 schema 一致）但對全新 DB 來說 v9-v14 全是「先加再砍」的空操作。對 Pi 上 systemd 第一次啟動會多 ~50ms。**真正風險**：未來如果有人改 v9 內容（誤以為它是新欄位 add migration），實際是會在「已存在」的 schema 上跑，行為可能不如預期。
- **需要驗證的檔案**：實際在乾淨環境跑一次 `python app.py` 看 stdout 是否有 `[SKIP] 欄位已存在` 訊息。
- **建議 grep**：`grep -n "duplicate column name" migrations/__init__.py`。
- **建議測試**：寫一個 `test_init_db_then_migrations_idempotent.py` 確認對乾淨 DB 連跑兩次 `init_db()` 結果一致。
- **優先級**：P3。不是 bug，是雙寫資料結構造成的維護債。Linus 哲學原文「Bad programmers worry about the code, good programmers worry about data structures」——這裡是兩份 schema 描述（init_db 的 CREATE 字串 vs migrations 的 ALTER 串），一份就夠。

### 4.3 frontend 仍存在 i18n 框架但 README 說 i18n 是凍結項

- **懷疑點**：`frontend/src/i18n/` 目錄存在；TODO.md 與 Prism.md 都把 i18n 列入 🧊 凍結項。可能是已被 scaffolded 但未啟用的死碼，或反過來——已啟用但文件沒同步。
- **推理依據**：頂層目錄 listing 顯示 `frontend/src/i18n` 存在；TODO.md:207 寫「i18n 多語系 — 待用戶群擴大再啟動」。
- **需要驗證的檔案**：`frontend/src/i18n/` 目錄內容、`frontend/src/main.tsx` 是否 import i18n。
- **建議 grep**：`grep -rn "import.*i18n" frontend/src/`。
- **優先級**：P3。不影響後端，但若 i18n 已部分接線，README 該更新。

### 4.4 `services/` 目錄幾乎是空殼

- **懷疑點**：`services/__init__.py` 只有 59 bytes（推測是 `# placeholder` 之類）；整個 services/ 沒有實質模組。Architecture 圖也未提到 services 層。
- **推理依據**：`ls -la D:/AI/Prism/services/` 只看到 `__init__.py` (59 bytes)。
- **後果**：如果是 AI 拔除時清空的殘餘空目錄，留著屬於 dead folder noise；如果未來有計畫要放東西，應該記載。
- **建議 grep**：`grep -rn "from services" D:/AI/Prism/`（推測無 import）。
- **優先級**：P3。

### 4.5 `tools/`、`build/`、`資料庫備份/` 等資料夾未被任何文件涵蓋

- **懷疑點**：頂層有 `tools/`、`build/`、`資料庫備份/` 三個資料夾，但 README.md 的「專案結構」與 docs/CONTRIBUTING.md 的「專案結構」都沒列。
- **後果**：新成員不知道這些資料夾的角色（build 產出物？工具腳本？備份？）。`資料庫備份/` 還用中文資料夾名，會有 path encoding 問題在某些 Linux distro。
- **建議 grep**：`grep -n "tools/\|build/\|資料庫備份" docs/*.md`。
- **優先級**：P3。

---

## 5. Contract / Schema / Runtime Gaps

> 「文件規則已寫，但 runtime 或 tests 未跟上」的地方。

| # | 規則 | runtime 現況 | tests 是否覆蓋 | 證據 |
|---|---|---|---|---|
| 5.1 | CLAUDE.md / AGENTS.md：「不引入 AI/ML 依賴」 | `routes/` / `app.py` / `utils/` 已乾淨；但 `scripts/check_deps.py` 仍 import numpy / sentence_transformers | ✅ test_schema_regression.py 確認 DB 欄位已拔除；❌ 沒有測試掃描 `scripts/` 與 source code 中的禁用 import | §3.8 |
| 5.2 | CLAUDE.md：「不使用 CDN」 | V2 React SPA 由 Vite 打包，預期是本地化的；但**沒有自動化驗證**。tests/test_offline_mode.py 是 V1 遺物，根本不在 pytest collection | ❌ V2 路徑無對應測試 | §4.1 |
| 5.3 | CLAUDE.md：「不直接操作 DB — 統一使用 db.py 的 get_db()」 | `tests/test_batch_type_sync.py:11-15` 自行定義 `get_db(app)` 並 `sqlite3.connect(app.config['DATABASE'])`，繞過 db.py 的 FK 驗證 | ❌ 沒有 lint / grep 把關 | [tests/test_batch_type_sync.py:11](tests/test_batch_type_sync.py:11) |
| 5.4 | AGENTS.md：「不在 WSGI 請求生命週期內啟動背景執行緒」 | 已遵守。`app.py` 的 PyWebView 是 main thread 啟動，FlaskThread daemon=True 是桌面模式專用 | ❌ 沒有測試強制 | [app.py:586-588](app.py:586) |
| 5.5 | API_REFERENCE.md §17：HTTP 403 = CSRF 或 localhost 限制 | runtime 確實會回 403（app.py csrf_protect + server.py before_request）。**但生產模式 V2_MODE 與 debug 的判斷耦合 `current_app.config.get('V2_MODE') and not current_app.debug`**，沒有測試覆蓋此 branch | ❌ 沒看到 `test_csrf_production_mode_blocks_anonymous` 之類測試 | [app.py:97-103](app.py:97) |
| 5.6 | DEPLOY-PI.md：`.port_config` 必須是 JSON 格式 | runtime 在 [app.py:475-483](app.py:475) try/except 包住 json.load，失敗會 print warning 並 fall back，但仍可能用錯 port。實際 Pi 上有發生過此事故（DEPLOY-PI 文件本身記錄） | ❌ 沒有測試強制 `.port_config` 格式錯誤時行為 | [DEPLOY-PI.md:112-114](DEPLOY-PI.md:112) |
| 5.7 | SCHEMA.md：「v15 補上 prompt_params 遷移」 | migration v15 真的會 ADD COLUMN，但**對全新 DB 來說 init_db 已建好，v15 會撞 duplicate column name 被 silently skip**。語意正確但寫法迂迴 | ✅ test_schema_regression.py:101 確認 prompt_params 存在 | §4.2 |
| 5.8 | API_REFERENCE.md §11：`/api/system/check-consistency` Response 含 `null_category_id` | runtime 確實回；但 docstring 已脫節（§3.4） | ✅ test_system.py::test_consistency_check 有跑（雖然不知有沒有檢查具體欄位） | §3.4 |

---

## 6. Verification Gaps

> 目前不能宣稱完成的項目。

| 項目 | 缺什麼證據 | 為什麼重要 |
|---|---|---|
| 「V2 React SPA 完全離線、無 CDN」 | 沒有自動化測試掃描 `frontend/dist/index.html` 是否還有 `http://cdn.*` / `https://unpkg.com` / `https://cdn.jsdelivr.net` 等 URL。`tests/test_offline_mode.py` 是 V1 遺物（§4.1） | CLAUDE.md 明文禁止 CDN；但沒驗證等於沒承諾 |
| 「Phase 13 部署到 Raspberry Pi 並驗證 live API」 | TODO.md:145 標 `[x] 13.4`，但沒有 fixture / dump / health-check 結果存檔 | 一個 SSH 失敗或 Caddy 版本變化就可能讓 live API 跟 local 不一致 |
| 「pytest 全綠（v2.4.5 後）」 | [test_run.log](test_run.log) 是 2026-05-05 留下的；之後若有檔案修改（例如 README、docs），雖然不會影響測試，但**沒有近期重新執行的紀錄** | CONTRIBUTING Release Checklist 寫 `pytest tests/ -v` 必須全綠，但無檔案佐證最近一次 |
| 「前端 tsc 零錯誤」 | 同上，沒有 `tsc.log` 之類產物 | CONTRIBUTING Release Checklist 列為必過項 |
| 「Migration v15 對 legacy DB（v9 或更早）能正確升級」 | 沒有測試從 v9 schema 起跑完整 migration chain | v15 補丁的初衷就是修「legacy DB 沒 prompt_params」的問題，但驗證只走 fresh DB 的路徑（schema regression 是從空 DB 開始） |
| 「`/api/upload/url` 的 SSRF 防護真的拒絕內網」 | `_is_ssrf_target()` 邏輯正確但**沒有測試**；test_upload_security.py 只測 magic number | SSRF 是 v2.4.2 的新防護，沒回歸測試 = 隨時可能被誤砍 |
| 「`routes/server.py` localhost-only guard 真的擋住非 127.0.0.1」 | 同上沒有測試 | 服務管理 API 一旦失守，整個 knowledge.db 可下載、可被重啟 |
| 「production 模式 CSRF 對無 Origin 請求回 403」 | 同上沒有測試覆蓋 V2_MODE=true + debug=False 的 branch | 唯一在 production 才會觸發的安全 branch，沒測試 |

---

## 7. Minimal Action Plan

> 10 步以內。每步標明動作類型 + 範圍 + 驗證 + 不該順手做什麼。

### Step 1 — 文件導航閘門修補（不碰程式）

- **類型**：先改文件
- **允許修改範圍**：README.md / docs/INDEX.md / docs/CONTRIBUTING.md 中所有指向 `docs/20260412-cco-綜合分析報告.md` 的連結改為 `docs/過期/20260412-cco-綜合分析報告.md`；同步修正 docs/INDEX.md 中 cco / SEQUENCE-UPLOAD / API_REFERENCE 的「維護狀態」欄位
- **驗證**：`grep -rn "docs/20260412-cco" --include="*.md" .` 結果應全部含 `過期/`
- **不該順手做**：不要改 cco 報告本身內容；不要把它搬回 `docs/`（除非團隊決議「最新體檢報告」永遠放 `docs/` 而不是 `docs/過期/`，這是另一個討論）。

### Step 2 — TODO.md 頭部修補（不碰程式）

- **類型**：先改文件
- **允許修改範圍**：[docs/TODO.md:1-13](docs/TODO.md:1) 與 [docs/TODO.md:80-82](docs/TODO.md:80)
- **動作**：
  - line 4：移除「Local AI」
  - line 5：`1230-審核報告.md` → `garbage-can/1230-審核報告.md`（或乾脆刪除這條引用）
  - line 6：日期改為 `2026-05-05`
  - line 80：Phase 10 從 🔴 Pending 改為 ✅ 已完成 v2.4.2
- **驗證**：人眼 review；`grep -n "Local AI\|🔴 Pending v2.4.2\|2026-04-12" docs/TODO.md` 確認上述字串已不出現在頭部
- **不該順手做**：不要動 changelog 的歷史條目（那是時間軸事實）。

### Step 3 — AGENTS.md / CLAUDE.md 收斂為單頭真理（不碰程式）

- **類型**：先改文件 — 需要團隊決議哪一份是主檔
- **允許修改範圍**：[AGENTS.md](AGENTS.md) 與 [CLAUDE.md](CLAUDE.md)
- **建議**：保留 CLAUDE.md 為主（Claude Code 預設讀），把 AGENTS.md 改為 stub `# Prism Dev Guide — 內容已併入 CLAUDE.md，請讀該檔。`
- **驗證**：`wc -l AGENTS.md` 應 < 5
- **不該順手做**：不要刪除 AGENTS.md 整個檔案（保留 stub 讓外部 Agent 走 AGENTS 慣例時仍能找到指引）。

### Step 4 — 加 SSRF / localhost / production-CSRF 三條 regression test（先加測試）

- **類型**：先加測試
- **允許修改範圍**：在 `tests/` 新增 `test_security_guards.py`
- **建議內容**：
  - `test_ssrf_blocks_loopback()` — POST `/api/upload/url` with `http://127.0.0.1/x.png` 應 400 / 403
  - `test_ssrf_blocks_private_range()` — POST with `http://192.168.1.1/x.png` 應 400 / 403
  - `test_server_api_localhost_only()` — 用 test client 模擬 `REMOTE_ADDR=10.0.0.5` 呼叫 `/api/server/hardware`，應 403
  - `test_csrf_production_blocks_anonymous()` — V2_MODE=true + debug=False 環境呼叫 POST /api/notes 不帶 Origin/Referer，應 403
- **驗證**：`pytest tests/test_security_guards.py -v`
- **不該順手做**：不要在現有 `test_upload_security.py` 裡加，這是不同層的測試；不要動 SSRF/CSRF 程式本身。

### Step 5 — routes/system.py docstring 修補（在測試保護下小修）

- **類型**：在測試保護下修 code（docstring 等同 code）
- **允許修改範圍**：[routes/system.py:284-296](routes/system.py:284) 只改 docstring
- **驗證**：`pytest tests/test_system.py -v` 仍綠
- **不該順手做**：不要重構 check_consistency 邏輯。docstring fix 是純文字改動。

### Step 6 — 刪除 scripts/check_deps.py 與 tests/test_offline_mode.py 兩個殭屍

- **類型**：先改 code（刪除死碼）
- **允許修改範圍**：直接 `git rm scripts/check_deps.py tests/test_offline_mode.py`
- **驗證**：
  - `grep -rn "check_deps" .` 應無命中（python/ 內套件不算）
  - `pytest tests/ -v` 仍綠（test_offline_mode 本來就沒被 pytest 收集）
- **不該順手做**：不要連帶刪 `scripts/build_release.py` 的 `--exclude-module numpy/sentence_transformers`，那是給 PyInstaller 的防禦性 flag，留著無害。

### Step 7 — docs/Prism.md 標記為歷史

- **類型**：先改文件
- **允許修改範圍**：[docs/Prism.md](docs/Prism.md) 頂部 + line 22-25 + line 84 + line 166
- **動作**：
  - 頂部加標題 `> ⚠️ 此文件為 V2 規劃期歷史記錄（2024–2026 重構過程）。現行戰略以 README.md 與 docs/TODO.md 為準。`
  - line 22 起的 Vector Store / Graph 段落整段加上 `~~刪除線~~` 或刪除
  - line 84 的 `63 測試` 改為「以 `test_run.log` 為準（70+）」或刪除
  - line 166 的「Phase 0 現為最高優先級」整句刪除
  - README.md 戰略路線圖連結改指到 `docs/TODO.md`（或保留 Prism.md 但備註「歷史參考」）
- **驗證**：人眼 review
- **不該順手做**：不要刪整個 Prism.md（V1→V2 重構決策脈絡有歷史價值）。

### Step 8 — tests/README.md 改為自動化導覽

- **類型**：先改文件
- **允許修改範圍**：[tests/README.md](tests/README.md)
- **動作**：刪除手寫的測試檔表格；改為 `## 列出所有測試\n\`\`\`bash\npytest tests/ --collect-only\n\`\`\``，並把預期結果改成「全綠 PASS（以 `test_run.log` 為準）」
- **驗證**：人眼 review
- **不該順手做**：不要保留舊表格再加新內容（雙頭真理會再次發生）。

### Step 9 — CONTRIBUTING.md Release Checklist 補「文件同步」項

- **類型**：先改文件
- **允許修改範圍**：[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) §Release Checklist
- **動作**：把 [line 115](docs/CONTRIBUTING.md:115) 的 `61 passed` 改為「全綠（以 test_run.log 為準）」；line 49 的 `v1–v14` 改為 `v1–v15`；Release Checklist 末尾加一行：
  - `[ ] docs/INDEX.md、docs/Prism.md、docs/SEQUENCE-UPLOAD.md、docs/CONTRIBUTING.md、docs/DEPLOYMENT.md 的版本 / 日期 / 「最後更新」標記已同步本版`
- **驗證**：人眼 review
- **不該順手做**：不要在這次 PR 把所有文件版號一次升到 v2.4.6，那是發版動作不是 audit fix。

### Step 10 — Closure：重新跑 pytest + 前端 build，留下證據

- **類型**：跑驗證
- **允許修改範圍**：產生 `test_run.log`（覆寫）、確認 `frontend/dist/` 重建
- **驗證命令**：
  - `pytest tests/ -v 2>&1 | tee test_run.log`
  - `cd frontend && npx tsc --noEmit && npm run build`
- **不該順手做**：不要因為某個現有測試被你前面步驟順手改動了就 skip 它；不要 commit `frontend/dist/` 除非團隊規範要 commit build 產物（看現況 dist 應該是 build 產物不入 git，DEPLOY-PI 走 tar+SSH）。

---

## 8. Suggested Follow-up Prompts

### Prompt A — Documentation Alignment（只改文件）

```
你是 Prism 文件對齊執行者。本輪只改文件，不碰程式、不加測試、不執行任何 build / pytest。

必讀:
1. docs/20260513-deep-audit-report.md（本份審計，§3 與 §7 Step 1-3、7-9）
2. README.md / docs/INDEX.md / docs/TODO.md / docs/Prism.md / docs/CONTRIBUTING.md
3. AGENTS.md / CLAUDE.md

允許修改範圍:
- README.md / docs/INDEX.md / docs/CONTRIBUTING.md 中所有指向 docs/20260412-cco-綜合分析報告.md 的連結 → docs/過期/20260412-cco-綜合分析報告.md
- docs/INDEX.md 中 cco / SEQUENCE-UPLOAD / API_REFERENCE 的「維護狀態」欄位
- docs/TODO.md line 1-13 與 line 80-82 的頭部資訊
- docs/Prism.md 加歷史標題、line 22-25 / 84 / 166 修補
- AGENTS.md 改為 1 行 stub
- docs/CONTRIBUTING.md Release Checklist 補一行
- tests/README.md 改為自動化導覽

禁止事項:
- 不修改 routes/、app.py、migrations/、tests/*.py、frontend/src/
- 不刪除 docs/過期/ 與 garbage-can/ 任何檔案
- 不重新組織目錄結構
- 不寫新的審計報告

驗證命令（不執行，只列出來給 reviewer 跑）:
- grep -rn "docs/20260412-cco" --include="*.md" . （應全部含「過期/」）
- grep -n "Local AI" docs/TODO.md （應無命中）
- wc -l AGENTS.md （應 < 5）

完成後要更新:
- docs/TODO.md Changelog 新增一條 v2.4.6 (Docs Alignment)
```

### Prompt B — Regression Tests（只寫測試）

```
你是 Prism 測試補完執行者。本輪只新增測試，不改程式、不改文件、不執行 build。

必讀:
1. docs/20260513-deep-audit-report.md §6 Verification Gaps、§7 Step 4
2. routes/upload.py（看 _is_ssrf_target 與 download_from_url）
3. routes/server.py（看 _require_localhost）
4. app.py（看 csrf_protect 的 production branch）
5. tests/conftest.py 與 tests/test_upload_security.py（瞭解既有 fixture 與測試風格）

允許修改範圍:
- 新增 tests/test_security_guards.py，包含至少 4 個測試:
  - test_ssrf_blocks_loopback
  - test_ssrf_blocks_private_range
  - test_server_api_localhost_only
  - test_csrf_production_blocks_anonymous（需要 patch app config V2_MODE=true + debug=False）

禁止事項:
- 不修改 routes/、app.py、migrations/
- 不修改現有測試
- 不引入 mock 框架以外的新依賴（用 pytest monkeypatch / unittest.mock 即可）

驗證命令:
- pytest tests/test_security_guards.py -v
- pytest tests/ -v（確認沒打到其他測試）

完成後要更新:
- docs/TODO.md Changelog 新增一條 v2.4.6 (Security Regression Tests)
- 不需動 docs/SCHEMA.md / docs/ARCHITECTURE.md（沒新 schema / 新模組）
```

### Prompt C — Runtime / Code Fixes（在測試保護下修 P2 級殘留）

```
你是 Prism P2 殘留清理執行者。Prompt B 必須已 land 並全綠，否則不要動 code。

必讀:
1. docs/20260513-deep-audit-report.md §3.4 / §3.8 / §4.1
2. routes/system.py:284-296（要改的 docstring 位置）
3. scripts/check_deps.py 全文
4. tests/test_offline_mode.py 全文（驗證它確實不被 pytest 收集）

允許修改範圍:
- routes/system.py:284-296 docstring（只改文字，不改邏輯）
- 刪除 scripts/check_deps.py 整個檔案
- 刪除 tests/test_offline_mode.py 整個檔案

禁止事項:
- 不重構 check_consistency 邏輯
- 不動 scripts/build_release.py 的 PyInstaller --exclude-module 設定
- 不順手清 services/ 空目錄（那需要單獨評估）
- 不改 tests/test_batch_type_sync.py（雖然名字怪但測試是有效的）

驗證命令:
- pytest tests/ -v（必須跟 Prompt B 之後一致數量 PASS）
- pytest tests/test_security_guards.py -v
- grep -rn "check_deps\|test_offline_mode" --include="*.py" .（應只剩 .git/ 殘留）

完成後要更新:
- docs/TODO.md Changelog 新增一條 v2.4.6 (P2 Residue Cleanup)
```

### Prompt D — Closure Verification（只跑驗證 + 更新 handoff）

```
你是 Prism v2.4.6 發版收尾執行者。Prompt A/B/C 必須都已 land。

必讀:
1. docs/20260513-deep-audit-report.md §7 Step 10
2. docs/CONTRIBUTING.md Release Checklist

允許執行（read + write，但只寫產出檔）:
- 跑 pytest tests/ -v，把輸出存到 test_run.log（覆寫）
- 跑 cd frontend && npx tsc --noEmit（不需存產物）
- 跑 cd frontend && npm run build（產出 frontend/dist/，不 commit）

允許修改範圍:
- test_run.log（覆寫為最新一次執行結果）
- config.py 把 PRISM_VERSION 升為 "2.4.6"
- README.md 開頭的版本 badge 升為 2.4.6
- docs/TODO.md Changelog 整合 Prompt A/B/C 三條為一條 v2.4.6 總結

禁止事項:
- 不修改 routes/、app.py、migrations/、tests/*.py
- 不 commit frontend/dist/（除非 git status 顯示原本就有追蹤）
- 不執行 git push / gh pr create
- 不重新生成審計報告

驗證命令:
- cat test_run.log | grep -E "PASSED|FAILED|ERROR" | wc -l
- python -c "from config import Config; print(Config.PRISM_VERSION)"（應印 2.4.6）
- grep -n "version-2.4.6" README.md（應命中 badge 行）

完成後要更新:
- docs/TODO.md Changelog: v2.4.6 條目（合併 Prompt A/B/C 三項摘要）
- 不需要其他文件改動
```

---

## 9. Questions For Human

> 不問能從 repo 自己判斷的問題。

1. **「最新體檢報告」要放在 `docs/` 還是 `docs/過期/`？**
   現況是檔案在 `過期/` 但所有引用指向 `docs/`。需要決議：(a) 把檔案搬回 `docs/`（保留「最新一份」的快速存取），未來下次體檢做完才搬 `過期/`；或 (b) 把所有引用改為 `docs/過期/`，明白宣告「最新體檢報告 = 已完成體檢報告中最新的那份」。

2. **AGENTS.md 是否要保留？**
   它是 OpenAI / Cursor / 部分外部 Agent 框架的慣例檔名。Claude Code 預設讀 CLAUDE.md。建議的「stub 路線」是否可接受？或你要保留兩份完整內容並接受未來會漂移？

3. **`garbage-can/` 與 `demo/` 是否計劃保留？**
   `garbage-can/` 含 V1 設計筆記、unnamed.jpg、舊報告，是「個人歸檔」性質；`demo/` 只有一份 16KB index.html。如果要保留，建議在 README 「專案結構」明示這兩個資料夾的角色（archive / showcase），避免外部 Agent 誤入。

4. **`docs/Prism.md` 的角色定位？**
   INDEX.md 標它「🗄️ 歷史參考」、README.md 標它「戰略路線圖」。如果要繼續更新（戰略性質），就應該修掉 line 22-25 的 ChromaDB / Graph 殘留；如果不更新（歷史性質），就把 README 的連結改成「歷史背景參考」。

5. **下一步真的不做新 feature 嗎？**
   v2.4.5 後 TODO.md 沒有 Phase 14；Prism.md 提的 ChromaDB / Graph View 都凍結了；README 自稱 Headless KMS 已完成。本輪審計沒有發現「需要新 feature 才能解決的問題」，但想確認你的方向是「文件 / 測試 / 死碼清理為主，不開新 epic」。

---

**報告完。**

> Linus 哲學收尾：「程式碼是事實，文件是承諾。承諾跟事實對不上，先修承諾——除非承諾才是對的，那就修事實。」
> v2.4.5 的事實已經乾淨（程式、schema、測試），文件這份承諾沒跟上。先補承諾。
