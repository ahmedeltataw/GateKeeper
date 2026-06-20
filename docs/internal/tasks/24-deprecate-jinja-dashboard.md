# Task 24 — Deprecate & Retire Jinja Dashboard — ✅ DONE (2026-06-18)

> **DONE (full delete, no git).** Removed `templates/` + `static/` + all `/dashboard/*` HTML routes;
> `src/api/dashboard.py` reduced to the scrypt auth store (`init` + hash/verify helpers for a future
> `/admin/login`); dead `/static` mount + unused imports removed from `server.py`. 24 tests green.

> **Phase 5** · depends on: 22 (Streamlit pages reach parity)
> Reference: `docs/plan/DASHBOARD_ARCHITECTURE.md` §6

## Objective
Once the Streamlit panel covers every page, retire the old in-app Jinja dashboard cleanly. **Do
not** start this task until task 22's acceptance criteria all pass.

## Decision on the old artifacts
| Artifact | Action | Reason |
|----------|--------|--------|
| `src/api/dashboard.py` | **Reduce**, don't delete: keep `init()` + scrypt helpers (`_hash_password`/`_verify_password`/`_set_password`) if reused by a future `/admin/login`; **remove** all HTML page routes (`dashboard_index`, `keys_page`, `models_page`, `analytics_page`, `login_*`). | scrypt auth may back the admin login later; HTML routes are dead. |
| `templates/dashboard/*.html` | **Delete** (6 files). | No longer served. |
| `static/css/style.css` | **Delete** or move to `dashboard/` if styles reused. | Jinja-only asset. |
| `static/js/` | Already empty — remove if unused. | — |
| `server.py` include of `dashboard.router` | Remove the HTML-route include; keep `dashboard.init()` only if scrypt helpers retained. | Routes gone. |
| `config.dashboard.enabled` | Repurpose to gate `/admin/*` (done in task 20). | Single flag, new meaning. |
| `tasks/17-dashboard.md` | Mark **SUPERSEDED** at top, link to tasks 20–24. Keep for history. | Audit trail. |

## Acceptance criteria
- [ ] No route under `/dashboard/*` remains (verify `server.py` + `dashboard.py`).
- [ ] `templates/dashboard/` removed; no template-not-found errors on boot.
- [ ] App boots clean (`uv run uvicorn src.api.server:app`) and existing tests still pass.
- [ ] `tasks/17-dashboard.md` header marked SUPERSEDED.
- [ ] The dead `key_manager.get_key_metadata` caller is gone (fixed via task 20).

## Review checklist
- Removal is gated on Streamlit parity — no page lost.
- No broken imports after route removal; test suite green.

## Out of scope
Any new features (those are separate future modules under `dashboard/pages/`).
