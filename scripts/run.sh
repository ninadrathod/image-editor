#!/usr/bin/env bash
# Run the project — start the API and a static frontend server.
# Stops both processes when you press Ctrl+C.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/.venv"

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5500}"

cleanup() {
  echo ""
  echo "==> Shutting down..."
  if [[ -n "${API_PID:-}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo "Stopped."
}

trap cleanup EXIT INT TERM

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Error: backend/.venv not found. Run ./scripts/setup.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "==> Starting API on http://localhost:${API_PORT}"
(
  cd "${BACKEND_DIR}"
  uvicorn app.main:app --reload --host "${API_HOST}" --port "${API_PORT}"
) &
API_PID=$!

echo "==> Starting frontend on http://localhost:${FRONTEND_PORT}"
(
  cd "${ROOT_DIR}"
  python3 -m http.server "${FRONTEND_PORT}"
) &
FRONTEND_PID=$!

# Give the API a moment, then health-check
sleep 1
if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
  echo "==> API health: ok"
else
  echo "==> API is starting (health check not ready yet)"
fi

echo ""
echo "Open http://localhost:${FRONTEND_PORT} in your browser."
echo "Press Ctrl+C to stop."
echo ""

wait
