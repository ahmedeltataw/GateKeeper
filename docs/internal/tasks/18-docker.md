# Task 18 — Docker Packaging

> **Phase 4** · depends on: 07 · Reference: `IMPLEMENTATION_PLAN.md` §14.5, §14.6, §22

## Objective
Containerize the gateway for one-command run.

## Files to create/modify
- `Dockerfile` (§14.5)
- `docker-compose.yml` (§14.6)

## Detailed spec
- `Dockerfile`: `python:3.12-slim`, install `requirements.txt`, copy code, `mkdir -p /app/server/data`, `EXPOSE 8000`, `CMD uvicorn src.api.server:app --host 0.0.0.0 --port 8000`.
- `docker-compose.yml`: build, container `llm-free-gateway`, port `8000:8000`, mount `config.yaml` (ro), `server/data`, `.env` (ro); env `ENCRYPTION_KEY=${ENCRYPTION_KEY}`; `restart: unless-stopped`; healthcheck hitting `/health` every 30s.

## Acceptance criteria
- [ ] `docker compose build` succeeds.
- [ ] `docker compose up -d` starts; `/health` returns healthy.
- [ ] `server/data` persists across container restarts (volume).
- [ ] `.env`/`config.yaml` mounted read-only; `ENCRYPTION_KEY` passed through.
- [ ] Healthcheck reports healthy.

## Review checklist
- Matches §14.5/§14.6 exactly (paths, volumes, healthcheck command).
- No secrets baked into the image; provided via env/mount.
- Data dir writable in container.
