# GateKeeper — Streamlit Dashboard

Standalone admin control panel for GateKeeper. It runs as a
separate process and talks to the gateway over its `/admin/*` HTTP API — it
shares no code or memory with the gateway.

## Pages
- **Overview** — request/cache/fallback counters + provider status grid
- **Keys** — add / delete provider API keys (always shown masked)
- **Models** — full model registry table
- **Analytics** — per-provider requests, tokens, average latency

## Prerequisites
- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- A running gateway (`uvicorn src.api.server:app …`) with `ADMIN_TOKEN` set

## Environment
Copy the template and set the values:

```bash
cp .env.example .env
```

| Variable | Required | Meaning |
|----------|:--------:|---------|
| `GATEWAY_URL` | no | Gateway base URL. Default `http://127.0.0.1:8000`. |
| `ADMIN_TOKEN` | yes | Bearer token for `/admin/*`. **Must match the gateway's `ADMIN_TOKEN`.** |

OS environment variables take precedence over `.env`. If `ADMIN_TOKEN` is left
blank you can still paste it into the sign-in screen at runtime.

## Run
Two processes:

```bash
# 1) gateway (from the project root)
uv run uvicorn src.api.server:app --host 127.0.0.1 --port 8000

# 2) dashboard (from this folder, isolated env)
uv venv
uv pip install -r requirements.txt
uv run streamlit run app.py        # http://localhost:8501
```

Dependencies here (`streamlit`, `httpx`, `pandas`, `plotly`) are isolated to
this folder and are **not** part of the gateway's `requirements.txt`.

## Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| "admin token is not configured" | gateway has no `ADMIN_TOKEN` | set it in the gateway `.env`, restart the gateway |
| "admin token was rejected" | token mismatch | make dashboard `ADMIN_TOKEN` equal the gateway's |
| "gateway is unavailable" | gateway not running / wrong `GATEWAY_URL` | start the gateway or fix `GATEWAY_URL` |
| `Port 8501 is already in use` | another Streamlit instance | `streamlit run app.py --server.port 8502` |
