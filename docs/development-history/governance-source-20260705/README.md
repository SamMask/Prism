# Governance Source Archive - 2026-07-05

本目錄保留原 `docs2/` 新版治理素材的副本，供日後追溯。本 repo 的正式治理入口是：

- `docs/GOVERNANCE.md`
- `docs/TODO.md`
- `docs/CONTRACTS.md`
- 根目錄鏡像檔 `AGENTS.md` / `CLAUDE.md`

原 `docs2/` 可由使用者手動刪除；後續不要再把 `docs2/` 當作權威路徑引用。

## Source Files

| Archived file | Original source | Use in Prism |
|---|---|---|
| `LLM-DEV-COLLAB-LESSONS.md` | `docs2/LLM-DEV-COLLAB-LESSONS.md` | Current truth、completion levels、TODO discipline、anti-bloat。 |
| `LLM-UX-UI-DESIGN-PRINCIPLES.md` | `docs2/LLM-UX-UI-DESIGN-PRINCIPLES.md` | Prism UI/UX governance guardrails。 |
| `governance/DELEGATION-TEMPLATES.md` | `docs2/治理/DELEGATION-TEMPLATES.md` | Subtask prompt boundary and report contract。 |
| `governance/HARNESS-DIAGNOSIS.md` | `docs2/治理/HARNESS-DIAGNOSIS.md` | Environment pitfalls、self-verification limits、Windows/CJK notes。 |
| `governance/JUDGMENT-RUBRICS.md` | `docs2/治理/JUDGMENT-RUBRICS.md` | Ask/stop/switch-route/completion rubrics。 |
| `governance/LETTER-TO-FUTURE-SESSIONS.md` | `docs2/治理/LETTER-TO-FUTURE-SESSIONS.md` | Future-session honesty and evidence discipline。 |
| `governance/MAINTENANCE-PROTOCOL.md` | `docs2/治理/MAINTENANCE-PROTOCOL.md` | Governance maintenance, mirror sync, read-back, doc hygiene。 |
| `governance/MODEL-DISPATCH.md` | `docs2/治理/MODEL-DISPATCH.md` | Role-neutral delegation principles only; Claude-specific model names are not Prism policy。 |

## Adoption Boundary

These files are historical source material. They do not override current Prism source, contracts, tests, architecture, or runtime docs.

When updating governance later:

1. Prefer editing `docs/GOVERNANCE.md` and official indexes.
2. Do not cite deleted `docs2/` paths.
3. Do not import template-repo-only rules, Claude-only model routing, or unrelated runtime workflows into Prism.
