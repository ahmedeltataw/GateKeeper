# Plan — Probe + Auto-Quarantine + Dashboard
> Date: 2026-06-21  
> Scope: Only these two workstreams.  
> Status: Draft for approval.

---

## 1. Probe + Auto-Quarantine (Day 1)

### New files
- `src/core/smoke.py` — `smoke_test_model(model_id, timeout=5.0) -> bool`
- `src/core/probe.py` — `probe_all_models(concurrency=3) -> dict[str, bool]`

### Files to patch
- `config.yaml` — add `probe:` block  
- `src/api/server.py` — call `probe_all_models()` in `_lifespan`
- `src/core/circuit.py` — verify `is_open()` blocks routing
- `src/api/routes.py` — `GET /v1/models` hides blacklisted models
- `src/api/admin.py` — add probe endpoints + breaker metadata
- `src/core/health.py` — `GET /health` adds `catalog_probe`

### Config
```yaml
probe:
  enabled: true
  concurrency: 3
  timeout_seconds: 5
  max_consecutive_failures: 3
  prompt: "Reply with the single word: OK"
  max_tokens: 4
```

### Behavior
- On boot: `probe_all_models()` runs smoke test for every model in registry
- After 3 consecutive failures → `STATE_BLACKLISTED` (already in `circuit.py`)
- `/v1/models` returns only `closed`/untested models
- `/admin/models` still shows all models + `breaker_state`
- `/health` adds:
  ```json
  "catalog_probe": {
    "probed": 46,
    "healthy": 44,
    "blacklisted": 2
  }
  ```

### New admin endpoints
- `POST /admin/probes/run` — manual re-probe all models
- `POST /admin/models/{model_id}/retry` — unblacklist + probe
- `POST /admin/models/{model_id}/disable` — manual disable
- `POST /admin/models/{model_id}/enable` — manual enable

---

## 2. Dashboard Completion (Days 2–3)

### Pages to update
| Page | Change |
|------|--------|
| `03_models.py` | Live status per model + action buttons |
| `06_probes.py` | **NEW** — probe results, stats, Run Probe Now |
| `01_overview.py` | Add `last_check` + `avg_latency_ms` |

### `03_models.py` requirements
- Columns: Model ID, Provider, Status (🟢/🔴/🟡), Last error, Actions
- Actions: Retry, Disable, Enable (call new admin endpoints)
- Detail panel: last 5 attempts from SQLite

### `06_probes.py` requirements (NEW)
- Header cards: Total | ✅ Healthy | ❌ Blacklisted
- Results table: model, status, latency, error
- Button: **Run Probe Now** with progress bar
- Auto-refresh every 30s during scan

### API support needed in `admin.py`
- `GET /admin/models` — include `breaker_state`, `last_code`, `last_detail`
- `GET /admin/analytics` — already returns per-provider latency/success
- New: `POST /admin/probes/run`
- New: `POST /admin/models/{id}/retry`
- New: `POST /admin/models/{id}/disable|enable`

---

## 3. Timeline

| Day | Tasks |
|-----|-------|
| 1 | `smoke.py` + `probe.py` + config + server wiring + circuit verify + routes filter + health field |
| 2 | `admin.py` new endpoints + `03_models.py` update |
| 3 | `06_probes.py` new page + `01_overview.py` update + manual test |

---

## 4. Verification Checklist
- [ ] Boot → `/health` shows `catalog_probe` with probed/healthy/blacklisted counts
- [ ] `/v1/models` excludes blacklisted models
- [ ] `/admin/models` shows breaker state per model
- [ ] 3 consecutive failures → auto-blacklist
- [ ] Dashboard Models page has live status + action buttons
- [ ] Dashboard Probes page shows scan results + Run Probe Now
- [ ] No restart needed for enable/disable/retry

---

*Plan authored by Hermes Agent, June 21, 2026.*
