# Task 04 — Model Registry + Sync Script

> **Phase 1** · depends on: 02, 03 · Reference: `IMPLEMENTATION_PLAN.md` §2.1, §2.6, §13, §17

## Objective
Build the in-memory model registry and the script that generates `models_registry.json` from `models-classification.md`.

## Files to create/modify
- `scripts/sync_models.py`
- `src/core/registry.py`
- `models_registry.json` (generated output, committed)

## Detailed spec
### sync_models.py
- Parse `models-classification.md` provider tables → list of `ModelInfo` objects (§2.1).
- Output `models_registry.json` = array validated against §2.1 (required keys: id, display_name, provider_id, provider_model_id, strength, use_cases, context_window, max_output_tokens, enabled, status, added_at, last_verified).
- Derive `strength_order` (S=0,A=1,B=2,C=3). Default `modalities=["text"]`, `pricing={"input":0,"output":0}`, `status="active"`, `enabled=true`.
- Use the full data in §13 as the authoritative model set (~55 models across 12 providers) — IDs, provider_model_id, strength, use_cases, context, output, rate_limits must match §13.
- `id` must satisfy `^[a-z0-9.-]+$` (dots allowed for ids like `gemini-3.5-flash`, `claude-3.5-sonnet`) and be unique gateway-wide (note §13 disambiguates duplicates, e.g. `nemotron-3-ultra` vs `nemotron-3-ultra-nv`, `gpt-oss-120b` vs `gpt-oss-120b-cb`).

### registry.py
- Load `models_registry.json` into memory on `await registry.load()`.
- Query API (§2.6): `get_by_strength(s)`, `get_by_use_case(uc)`, `get_best_for_task(uc)`, `get_by_provider(pid)`, `get_active()`, `search(term)`, plus `get(id)` and `get_providers_for_model(id)`.
- `get_best_for_task` returns active models for the use_case sorted by `strength_order`.

## Acceptance criteria
- [ ] `python scripts/sync_models.py` regenerates `models_registry.json` without errors.
- [ ] Registry loads and `get_by_use_case("coding")` returns the coding models from §13.
- [ ] All `id`s are unique and match the `^[a-z0-9.-]+$` pattern.
- [ ] Required schema keys present on every entry.
- [ ] `get_best_for_task("coding")[0]` is an **S-tier** coding model (this method is a **pure strength sort**). The curated coding chain (Codestral first) is applied by the **Quality Router in task 09**, not here.

## Review checklist
- Model count and IDs match §13; no provider table omitted.
- `strength_order` correct; duplicate base names disambiguated.
- rate_limits per model align with the provider limits in §8/§13.
