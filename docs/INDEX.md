# Prism 文檔索引 (INDEX)

> **專案版本**: v2.4.9
> **更新日期**: 2026-05-28
> **專案狀態**: 🟢 穩定運行 — Headless KMS (AI 功能已於 v2.3.0 拔除)

---

## 核心開發文件 ⭐ (每次開發前必讀)

| 文件 | 說明 | 維護狀態 |
|------|------|----------|
| [TODO.md](./TODO.md) | 原子化待辦清單、已完成項目、版本 Changelog | ✅ 持續更新 |
| [SCHEMA.md](./SCHEMA.md) | **現行 DB 綱要** — 所有資料表欄位定義（唯一真實來源），附 Migration 歷程 | ✅ 持續更新 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | C4 Container Diagram、模組邊界、資料流向 | ✅ 持續更新 |
| [Prism.md](./Prism.md) | V2 架構決策記錄與歷史路線圖（V1→V2 重構背景、AI 拔除決策脈絡） | 🗄️ 歷史參考，不再更新 |

> **注意**: `CLAUDE.md`（開發規範）位於專案根目錄，不在此資料夾。

---

## 技術規格文件

| 文件 | 說明 | 維護狀態 |
|------|------|----------|
| [API_REFERENCE.md](./API_REFERENCE.md) | REST API 端點完整參考 (`/api/*`)、請求參數、回應格式 | ✅ 已確認 (2026-05-27) |
| [FRONTEND-REDESIGN-PLAN.md](./FRONTEND-REDESIGN-PLAN.md) | 新 UI 參考檔 + Go shadow backend 路線整合規劃；前端改版與重構前必讀 | 📋 規劃中 |
| [contracts/phase18-readiness.md](./contracts/phase18-readiness.md) | Phase 18 contract pack：golden fixture、endpoint side-effect map、UI workflow map、Go read shadow acceptance | ✅ 已建立 |
| [contracts/api-readonly-manifest.json](./contracts/api-readonly-manifest.json) | Phase 18 read-only API manifest；Go shadow backend 與工具 surface 的機器可讀草稿 | ✅ 已建立 |
| [../go-shadow/README.md](../go-shadow/README.md) | Phase 18.4 Go read-only shadow backend scaffold；啟動方式、scope、runtime safety 與 diff harness | ✅ 已建立 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | 環境變數設定、Source / Dev mode、Raspberry Pi 部署流程；PyInstaller 僅作內部打包參考 | ✅ 仍適用 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 本地開發環境建置、依賴安裝、PR 規範 | ✅ 仍適用 |

---

## 審核 / 體檢報告 (Audit Reports)

| 文件 | 說明 | 狀態 |
|------|------|------|
| [20260412-cco-綜合分析報告.md](./過期/20260412-cco-綜合分析報告.md) | **體檢報告** — Linus-mode 深度審核，列出 P0/P1/P2 問題與「好品味」段落 | ✅ 已完成 v2.4.2 |

---

## 圖表文件

| 文件 | 說明 | 維護狀態 |
|------|------|----------|
| [ER-DIAGRAM.md](./ER-DIAGRAM.md) | Entity Relationship Diagram (Mermaid) — 已依 v14 更新，與 SCHEMA.md 同步 | ✅ 已更新 |
| [SEQUENCE-UPLOAD.md](./SEQUENCE-UPLOAD.md) | 圖片上傳流程 Sequence Diagram | ✅ 已更新 |

---

## 歷史 / 參考文件 (已封存)

| 文件 | 說明 | 狀態 |
|------|------|------|
| [README.md](./README.md) | 舊版文檔索引 (v1.4.1, 2025-12-15) | 🗄️ 已由本文件取代 |
| [hypothetical_modern_prism.md](./hypothetical_modern_prism.md) | 現代化架構評估報告（前後端分離 Vite/React 方案探討）| 🗄️ 已完成實作，僅供歷史參考 |
| [future_possibilities_heavy_local.md](./future_possibilities_heavy_local.md) | 本地 AI 重度依賴方案探索（PyTorch / Ollama / HuggingFace）| 🗄️ 已廢棄 — AI 功能於 v2.3.0 全面移除 |

---

## 原型 / 重構參考

| 文件 | 說明 | 狀態 |
|------|------|------|
| [Prism Redesign - standalone.html](./New_UI/Prism%20Redesign%20-%20standalone.html) | 新 UI 前端原型參考；只採工作流與視覺方向，不直接搬 prototype code / sample data | 📎 參考 |
| [Prism_Go_模組逐步重構計劃報告.md](../Prism_Go_模組逐步重構計劃報告.md) | Python → Go 漸進替換盤點；Phase 0-1 read-only shadow backend 與 response diff 依據 | 📎 參考 |

---

## 快查：改什麼讀什麼

| 情境 | 必讀文件 |
|------|----------|
| 新增 / 修改 API 端點 | `SCHEMA.md` + `API_REFERENCE.md` |
| 修改資料庫欄位或新增 Migration | `SCHEMA.md` |
| 架構調整 / 新模組 | `ARCHITECTURE.md` |
| 規劃新功能 / 查進度 | `TODO.md` |
| 前端改版 / UI rewrite | `FRONTEND-REDESIGN-PLAN.md` + `docs/New_UI/Prism Redesign - standalone.html` |
| Go shadow backend / API contract lock | `contracts/phase18-readiness.md` + `contracts/api-readonly-manifest.json` + `Prism_Go_模組逐步重構計劃報告.md` + `API_REFERENCE.md` + `SCHEMA.md` |
| 首次部署 / 環境設定 | `DEPLOYMENT.md` + `CONTRIBUTING.md` |
| 理解整體方向 | `Prism.md` |
