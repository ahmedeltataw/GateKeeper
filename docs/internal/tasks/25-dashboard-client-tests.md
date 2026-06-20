# Task 25 — Dashboard API-Client Tests

> **Phase 5** · depends on: 22 · Reference: `dashboard/api_client.py`
> **Why:** test-guard flagged the dashboard's data-translation layer as unverified. A gateway
> response field rename would silently break the dashboard today. This task closes that gap.

## Objective
Unit-test the **pure** functions in `dashboard/api_client.py` — the JSON→typed-object translators
and the status-to-exception mapper. No network, no Streamlit, no running gateway.

## Scope (test-guard aligned)
**Test these (each catches a real bug — a wrong/renamed field or status):**
- `_as_admin_stats`, `_as_provider_status`, `_as_key_summary`, `_as_analytics_entry`, `_as_model_info`
  — feed a representative dict (mirror the real shapes in `tests/test_admin_api.py` / `src/api/admin.py`),
  assert the returned dataclass fields. Use one `@pytest.mark.parametrize` where shapes are similar
  (Rule 3). Construct **real** payloads, not mocks (Rule 8).
- `_raise_for_status` — parametrize over `401 → AdminUnauthorizedError`, `403 →
  AdminTokenNotConfiguredError`, `500 → AdminApiError`, `200 → no raise`. Build a real
  `httpx.Response` (no mock).

**Do NOT test (test-guard Rule 7 — framework/UI):**
- Streamlit page `main()` functions or any `st.*` rendering.
- `AdminApiClient._request` network path (that's an integration concern; the admin API already has
  integration tests in `tests/test_admin_api.py`).

## Where the tests live
`dashboard/tests/test_api_client.py`. Add `pytest` to `dashboard/pyproject.toml` under a dev
dependency group (so it stays out of the runtime deps). Run with `cd dashboard && uv run pytest -q`.

## Acceptance criteria
- [ ] Every `_as_*` translator has a test asserting all returned fields from a real dict.
- [ ] `_raise_for_status` covered for 401/403/500/200 via parametrize, real `httpx.Response`.
- [ ] No mocks of dataclasses or `httpx.Response`; no Streamlit imports in tests.
- [ ] `cd dashboard && uv run pytest -q` green.
- [ ] test-guard run on the new tests: no Rule 3/4/7/8 violations.

## Review checklist
- Each test answers "what bug does this catch that no other does?" (a renamed/missing gateway field).
- Payloads mirror the live shapes in `src/api/admin.py`; if they drift, the test should fail.
