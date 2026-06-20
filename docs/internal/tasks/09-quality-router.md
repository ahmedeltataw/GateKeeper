# Task 09 — Quality Router (UNIQUE FEATURE)

> **Phase 2** · depends on: 04, 07 · Reference: `IMPLEMENTATION_PLAN.md` §5, §13 (Top picks)

## Objective
Select the strongest task-appropriate model that still has budget. This is the project's differentiator.

## Files to create/modify
- `src/core/quality_router.py`
- `src/core/router.py` (Model→Provider resolution if not already present)

## Detailed spec
- `async select_best_model(task_type, available_models)` per §5: filter by `task_type in use_cases and enabled and status=="active"`, then return the first candidate whose provider passes `rate_limiter.allow()` (rate limiter may be a permissive stub until task 11), else `fallback_any()`.
- **Ordering (authoritative tiebreak — resolves the strength-vs-curation conflict):** the curated `PREFERRED[task_type]` chain is the **PRIMARY** sort key; any task-appropriate model **not** in the chain follows, ordered by `strength_order` (S<A<B<C). The curated chain **overrides raw strength** — e.g. for `coding`, `codestral` (A) ranks above `gpt-4o` (S) because the chain lists it first. Do **not** use a pure strength sort.
- task_type → preferred chains exactly per §5 table (coding/search/reasoning/creative/data/vision/default).
- `model:"auto"` → pick by `task_type` (default `default` task if absent, per `quality_router.default_task_type`).
- Explicit `model` provided → use it; `task_type` is only a hint (used for fallback ordering).
- `router.py`: `get_provider(provider_id)`, `get_providers_for_model(model_id)`.

## Acceptance criteria
- [ ] `select_best_model("coding", ...)` returns the top available model in the **curated coding chain** (`codestral` first when available), not the raw S-tier model.
- [ ] `model:"auto"` with `task_type:"reasoning"` selects a reasoning-appropriate model.
- [ ] When the top model's provider is over budget, the next candidate is chosen.
- [ ] Explicit model is respected; task_type does not override it.

## Review checklist
- Sort uses `strength_order` (S<A<B<C), ties broken stably.
- Preferred chains match §5 table.
- Graceful behavior when rate limiter / fallback not yet wired (no crash).
