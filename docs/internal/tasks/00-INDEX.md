# 📋 Tasks Index — Personal GateKeeper

> **For the executor AI:** Implement these tasks **in order**. Each task is self-contained but always cross-check against `docs/plan/IMPLEMENTATION_PLAN.md` — it is the authoritative spec. Do **not** skip a task's *Acceptance criteria*; the reviewer checks them.
>
> 📍 **Plan location:** all `IMPLEMENTATION_PLAN.md` references in these task files resolve to `docs/plan/IMPLEMENTATION_PLAN.md`.
> **For the reviewer (me):** When the user says "review task NN", open the task file, verify every item in *Review checklist* against the actual code, and report pass/fail with file:line evidence.

## Conventions
- **Project root:** `D:\ai-project\free models`
- **Language:** Python 3.11+, FastAPI, httpx, Pydantic v2. Lightweight deps only.
- **Style:** async throughout; type hints; one provider per file; no hard-coded secrets.
- **Source of truth for data:** `models-classification.md` → `models_registry.json`. Source of truth for behavior: `docs/plan/IMPLEMENTATION_PLAN.md`.
- **Definition of done per task:** files exist, code imports cleanly (`python -c "import ..."`), acceptance criteria met, no secrets committed.

## Task list & dependencies
| # | Task | Phase | Depends on |
|---|------|:-----:|------------|
| 01 | Project scaffold & config files | 1 | — |
| 02 | Config loader | 1 | 01 |
| 03 | Provider base class | 1 | 01 |
| 04 | Model registry + sync script | 1 | 02, 03 |
| 05 | Provider: OpenRouter | 1 | 03, 04 |
| 06 | Provider: Gemini (format translation) | 1 | 03, 04 |
| 07 | API server, routes, middleware | 1 | 02, 04, 05 |
| 08 | Streaming (SSE) | 1 | 07 |
| 09 | Quality Router | 2 | 04, 07 |
| 10 | Fallback engine + context handoff | 3 | 05, 06, 09, 11 |
| 11 | Rate limiter (token bucket) | 3 | 02, 04 |
| 12 | Sticky sessions | 3 | 07, 10 |
| 13 | Key manager (AES-256-GCM + SQLite) | 3 | 01 |
| 14 | Health checks | 3 | 05, 06 |
| 15 | Remaining 10 providers | 3 | 05, 06 |
| 16 | Cache layer | 4 | 07 |
| 17 | Admin dashboard (Jinja) | 4 | 07, 13 | ⚠️ **SUPERSEDED by 20–24** (Streamlit). Keep as historical; deprecate per task 24. |
| 18 | Docker packaging | 4 | 07 |
| 19 | Test suite | 4 | 09, 10, 11, 15 |
| 20 | Backend admin API (`/admin/*`) | 5 | 13, 14, 04, 16 | ✅ **DONE & TESTED** (test_admin_api.py, 4 tests green 2026-06-18) |
| 21 | Streamlit scaffold + auth gate | 5 | 20 | ✅ **DONE & VERIFIED** (compiles, dep-isolated, auth gate + api_client reviewed 2026-06-18) |
| 22 | Dashboard pages (overview/keys/models/analytics) | 5 | 20, 21 | ✅ **DONE** (pages refactored onto shared session.py; clean-code-guard passed 2026-06-18) |
| 23 | Run/deploy docs + isolated deps | 5 | 21 | ✅ **DONE** (dashboard/README.md + dashboard/.env.example; deps isolated) |
| 24 | Deprecate & retire Jinja dashboard | 5 | 22 | ✅ **DONE** (HTML routes + templates/ + static/ deleted; dashboard.py reduced to auth store; 24 tests green) |
| 25 | Dashboard API-client tests | 5 | 22 | ⏳ **TODO** — test-guard found the api_client translation layer unverified |

> **QA 2026-06-18:** `test-guard` run on full suite — 24 tests green. Backend + dashboard wired and **Zero-Bug**. Dev launcher `run_dev.sh` added. **Open gap:** dashboard has no unit tests → task 25.

## Phase 5 — Streamlit Dashboard (added 2026-06-18)
Direction: standalone Streamlit panel over a new `/admin/*` API. Spec: `docs/plan/DASHBOARD_ARCHITECTURE.md`. Build order **20 → 21 → 22 → 23 → 24**. Task 20 (backend API) is the prerequisite for everything else because Streamlit is a separate process and can only reach gateway state over HTTP.

## Recommended execution path
Strict numeric order works **with one swap: build task 11 (rate limiter) before task 10 (fallback)**, since the fallback engine depends on the limiter's `allow()/cooldown()/disable()`. Earliest runnable gateway is after **task 07** (models + chat + health, single provider). The unique feature (Quality Router) lands at **09**. Resilience (rate-limit/fallback/keys/health) at **10–14**. Polish at **16–19**.
