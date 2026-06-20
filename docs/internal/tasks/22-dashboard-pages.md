# Task 22 — Dashboard Pages — ✅ DONE (2026-06-18)

> **DONE.** Four pages (`01_overview`–`04_analytics`) + components built and refactored onto
> `session.py` (shared auth/client/error — removed 4× duplication). clean-code-guard passed.

> **Phase 5** · depends on: 20 (admin API), 21 (scaffold)
> Reference: `docs/plan/DASHBOARD_ARCHITECTURE.md` §2, `IMPLEMENTATION_PLAN.md` §16.1

## Objective
Implement the four control-panel pages, one file per module, consuming the `/admin/*` API via
`api_client.py`. Adding a future page = adding one file here; no other file must change
(beyond an optional new `api_client` method).

## Files to create
```
dashboard/pages/
├── 01_overview.py    # metric cards: requests_total, requests_last_hour, cache_hits, fallback_count + provider status grid
├── 02_keys.py        # list provider keys (masked ●●●●●); add key form; delete button
├── 03_models.py      # registry table: id, provider, strength, use_cases, context_window
└── 04_analytics.py   # per-provider latency/tokens charts (plotly), provider status timeline
```
Plus reusable widgets in `dashboard/components/` (`metric_cards.py`, `tables.py`).

## Detailed spec — per page
- **Overview** ← `GET /admin/stats` + `GET /admin/providers`. Cards + colored status grid.
- **Keys** ← `GET /admin/keys`; add via `POST /admin/keys` (form: provider dropdown + key input);
  delete via `DELETE /admin/keys/{provider}`. Keys shown masked only; input never echoed back.
- **Models** ← `GET /admin/models`. Sortable/filterable table (pandas DataFrame + `st.dataframe`).
- **Analytics** ← `GET /admin/analytics`. Plotly charts: avg latency per provider, tokens per
  provider; degrade gracefully when data is empty.

## Acceptance criteria
- [ ] All four pages render with live data from a running gateway.
- [ ] Adding a key in the UI results in an encrypted key in SQLite, usable by the gateway.
- [ ] Keys are never shown in plaintext (masked) and the add-input is not echoed after submit.
- [ ] Models page lists the full registry; Analytics shows per-provider breakdown.
- [ ] Each page is a single self-contained file in `pages/`; a new page needs no edits elsewhere except an optional `api_client` method.

## Review checklist
- No business logic in `components/` (pure widgets); data fetching only via `api_client`.
- Empty/error states handled (no tracebacks on missing data or 4xx).
- No plaintext secrets in UI or logs.

## Out of scope
Run/deploy docs (task 23), retiring the Jinja dashboard (task 24).
