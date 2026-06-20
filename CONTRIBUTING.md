# Contributing to GateKeeper

Thanks for your interest in improving GateKeeper! Contributions of every size —
bug reports, docs, new provider adapters, features — are welcome.

## Getting started

1. **Fork** the repository and clone your fork.
2. Create the environment and install dev dependencies:
   ```bash
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```
3. Run the test suite to confirm a clean baseline:
   ```bash
   pytest -q
   ```

## Development workflow

1. Create a branch: `git checkout -b feat/short-description`.
2. Make your change. Keep it focused — one logical change per pull request.
3. **Add or update tests.** Every behavior change should be covered.
4. Make sure the full suite passes: `pytest -q`.
5. Commit with a clear message and open a pull request describing **what** and **why**.

## Project layout

| Path | Purpose |
|------|---------|
| `src/api/` | FastAPI server, routes, middleware, admin endpoints |
| `src/core/` | registry, router, fallback, circuit breaker, health, usage, tenants |
| `src/providers/` | one adapter per upstream provider |
| `dashboard/` | Streamlit control panel |
| `tests/` | pytest suite |
| `docs/` | public docs (`docs/internal/` holds development notes) |

## Adding a new provider

1. Add an adapter under `src/providers/` (use an existing one as a template).
2. Register it so the router can construct it.
3. Add the models to `models_schema.json` / `models_registry.json`.
4. Add tests under `tests/`.

## Coding standards

- Target **Python 3.12+** with type hints.
- Match the surrounding style: small, well-named functions and clear docstrings.
- Never commit secrets. `.env`, `*.key`, and `*.db` are git-ignored — keep it that way.
- Keep the request hot path fast; prefer the existing in-memory + write-behind patterns.

## Reporting bugs

Open an issue with: what you expected, what happened, steps to reproduce, and your
OS / Python version. Logs (with secrets removed) help a lot.

## Code of conduct

Be respectful and constructive. We want this to be a welcoming project for
everyone.
