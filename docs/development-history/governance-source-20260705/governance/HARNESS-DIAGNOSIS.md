# Harness 診斷：前三名問題與修法

診斷日期：2026-07-03（Claude Fable 5 session）
診斷對象：這個使用者的 Claude Code 環境（Windows 11、PowerShell 主 shell、本資料夾為母模板庫）
用途：本檔是「治理/」其他檔案的依據。之後的 session 修 harness 問題時，先讀這份，不要重新診斷一遍。

## 診斷依據（當時實測到的環境事實）

- CLAUDE.md（8.6KB，全 CJK 約等於 4-5K token）每個 session 自動全文載入，且 AGENTS.md 全文重複一份需人工同步。
- 舊版 CLAUDE.md 的必讀順序要求「處理任何文件前」先讀 LLM-DEV-COLLAB-LESSONS.md（36.8KB，約 743 行、35 條規則清單 + 9 個章節 + 2 個附錄）。
- 三份母模板（LESSONS / SDD-WORKFLOW / UX-UI）刻意跨檔重複四塊共用內容（完成層級階梯、主張→最低證據表、第一性原理三問/四問、反膨脹決策階梯），規定「改一份必須同步其他份」，但沒有任何機械手段能檢查有沒有同步。
- git status 顯示中文檔名被 octal escape（`\345\267\245\345\205\267/...`）、六份文件有 CRLF/LF 警告——CJK 路徑 + 雙 shell（PowerShell 與 Git Bash）+ 換行混雜是這個環境的常態。
- 環境有大量 MCP 工具（Notion、Chrome、computer-use、mempalace、scheduled-tasks 等），但 harness 已用 deferred loading 壓住 schema 成本，這部分不是主要漏洞。

## 第一名（最漏 token）：主對話自己下場做 token-heavy 工作

**症狀**：主對話直接整檔讀大文件、掃 repo、貼整段 log、自己跑冗長指令再吃完整輸出。LESSONS §7.6 已有「不要用生資料餵爆上下文」規則，但那是給單一模型的自律要求，沒有制度性的分工——自律規則對弱模型約束力最低。

**代價**：主對話 context 被生資料吃掉 → 更早壓縮/失憶 → 後半段品質下降 → 重問重讀 → 二次浪費。這是複利型漏洞。

**修法**（已落地）：
1. `治理/MODEL-DISPATCH.md`：指揮官不下場——大量讀取、掃 repo、查網頁、跑冗長驗證一律派 subagent，主對話只進結論與 `檔案:行號`。
2. `治理/DELEGATION-TEMPLATES.md`：五種任務型態的委派模板，降低「派工比自己做麻煩」的心理門檻。
3. CLAUDE.md 必讀順序改為「按任務類型讀最小必要段落」，不再要求先吞整份 LESSONS。

## 第二名（最容易失焦）：規則量大、重複、缺乏「當下該做什麼」的入口

**症狀**：LESSONS 有 35 條規則清單，且多數規則在正文章節又重述一次；三份模板還互相重複共用塊。弱模型讀完的典型反應是「都很有道理」然後憑慣性行動——規則越多，單條規則的邊際約束力越低。失焦的具體表現：報告寫得很像有讀過規則，行為卻照舊（自驗完成、順手擴張、讀整包生資料）。

**代價**：規則檔的 token 花了，行為沒變。這比沒有規則更糟，因為它製造「已受治理」的假象。

**修法**（已落地）：
1. `治理/JUDGMENT-RUBRICS.md`：把「事前判斷」做成帶正反例的 rubric——弱模型不需要記住 35 條，只需要在五個關口（升級、完成、停下、換路、品質）各查一張表。
2. CLAUDE.md 重寫成路由頁：只回答「你現在是什麼任務 → 去讀哪一段」，規則本體留在各檔。
3. `治理/MAINTENANCE-PROTOCOL.md` 的 SYNC-BLOCK 機制：跨檔重複塊加上可 grep 的標記與版本號，同步檢查從「憑記憶」變成「跑一條 grep」。

## 第三名（最容易出錯）：完成宣稱靠自驗 + Windows/CJK/雙 shell 環境陷阱

**症狀 A（自驗）**：寫程式的同一個 context 自己驗收自己，會繼承同一套盲點與同一份想被說服的動機。LESSONS §7.4 只管「接手時再驗證」，沒管「同 session 內的驗收由誰做」。

**症狀 B（環境）**：這台機器的實際錯誤來源——(1) CJK 路徑在 git 輸出被 escape，弱模型會把 escape 後字串當真實路徑用；(2) PowerShell 與 Git Bash 語法互串（`%VAR%`、`NUL`、backtick 續行貼進錯的 shell）；(3) CRLF/LF 混雜讓 diff 出現假變更；(4) 路徑含空格/CJK 沒加引號。

**修法**（已落地）：
1. `治理/MODEL-DISPATCH.md` §驗證不自驗：驗收一律派 fresh-context agent；檔案用 read-back、程式碼用測試或實跑、高風險判斷加第二意見。
2. CLAUDE.md 新增「本機環境備忘」小節：CJK 路徑一律加引號用絕對路徑、需要可讀輸出時用 `git -c core.quotepath=off <子指令>`、兩個 shell 語法不可互串、CRLF 警告屬正常不要「修」它。

## 落選但值得知道的

- **MCP 工具海**：已被 deferred loading 緩解，不用處理。
- **memory 機制閒置**：harness 有檔案式 memory（`~/.claude/projects/<本專案>/memory/`）+ MEMORY.md 索引，跨 session 傳承靠它比靠重讀大文件便宜。已寫進 `治理/LETTER-TO-FUTURE-SESSIONS.md`。

## Harness 的極限（誠實條款）

制度補得了的：執行品質、驗收紀律、token 紀律、狀態回報。
制度補不了的：模糊題與品味判斷（架構取捨、UX 品味、「這樣寫好不好」）。弱模型遇到這類問題時，正確動作不是硬答，而是走 `治理/JUDGMENT-RUBRICS.md` §1 的升級判準：升級模型、要求外部第二意見、或明說「這題我的判斷不可靠」。明說做不到是合規行為，不是失敗。
