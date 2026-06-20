#!/usr/bin/env bash
# Run the LLM Free Gateway dev stack: FastAPI backend (background) + Streamlit
# dashboard (foreground). Stops with a clear message if the backend never
# becomes healthy. Ctrl-C tears down both.
set -euo pipefail

GATEWAY_HOST="127.0.0.1"
GATEWAY_PORT="8000"
HEALTH_URL="http://${GATEWAY_HOST}:${GATEWAY_PORT}/health"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_LOG="${PROJECT_ROOT}/server/data/backend.dev.log"

backend_pid=""

cleanup() {
    if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" 2>/dev/null; then
        echo "Stopping backend (pid ${backend_pid})..."
        kill "${backend_pid}" 2>/dev/null || true
        wait "${backend_pid}" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

mkdir -p "$(dirname "${BACKEND_LOG}")"

echo "Starting backend on ${GATEWAY_HOST}:${GATEWAY_PORT} ..."
(
    cd "${PROJECT_ROOT}"
    uv run uvicorn src.api.server:app --host "${GATEWAY_HOST}" --port "${GATEWAY_PORT}"
) >"${BACKEND_LOG}" 2>&1 &
backend_pid=$!

echo "Waiting for backend health at ${HEALTH_URL} ..."
for attempt in $(seq 1 30); do
    if ! kill -0 "${backend_pid}" 2>/dev/null; then
        echo "ERROR: backend exited before becoming healthy. Last log lines:" >&2
        tail -n 20 "${BACKEND_LOG}" >&2
        exit 1
    fi
    if curl -sf "${HEALTH_URL}" >/dev/null 2>&1; then
        echo "Backend healthy after ${attempt}s."
        break
    fi
    if [[ "${attempt}" -eq 30 ]]; then
        echo "ERROR: backend did not pass health check within 30s. Last log lines:" >&2
        tail -n 20 "${BACKEND_LOG}" >&2
        exit 1
    fi
    sleep 1
done

echo "Launching dashboard (foreground). Ctrl-C stops both."
cd "${PROJECT_ROOT}/dashboard"
uv run streamlit run app.py
