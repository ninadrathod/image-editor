#!/usr/bin/env bash
# Run the project — start the API and a static frontend server.
# Stops both processes when you press Ctrl+C.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/.venv"
PYTHON="${VENV_DIR}/bin/python"

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

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
  else
    return 1
  fi
}

if [[ ! -x "${PYTHON}" ]]; then
  echo "Error: backend/.venv not found or incomplete. Run ./scripts/setup.sh first." >&2
  exit 1
fi

# Fail fast when the venv was moved (broken console-script shebangs) or deps are missing
if ! "${PYTHON}" -c "import uvicorn, multipart, fastapi, PIL" >/dev/null 2>&1; then
  echo "Error: backend virtualenv is broken or missing dependencies." >&2
  echo "  Fix: ./scripts/setup.sh" >&2
  exit 1
fi

if port_in_use "${API_PORT}"; then
  echo "Error: port ${API_PORT} is already in use (API)." >&2
  echo "  Stop the other process, or run: API_PORT=8001 ./scripts/run.sh" >&2
  exit 1
fi

if port_in_use "${FRONTEND_PORT}"; then
  echo "Error: port ${FRONTEND_PORT} is already in use (frontend)." >&2
  echo "  Stop the other process, or run: FRONTEND_PORT=5501 ./scripts/run.sh" >&2
  exit 1
fi

echo "==> Starting API on http://localhost:${API_PORT}"
(
  cd "${BACKEND_DIR}"
  "${PYTHON}" -m uvicorn app.main:app --reload --host "${API_HOST}" --port "${API_PORT}"
) &
API_PID=$!

echo "==> Starting frontend on http://localhost:${FRONTEND_PORT}"
(
  cd "${ROOT_DIR}"
  "${PYTHON}" -m http.server "${FRONTEND_PORT}"
) &
FRONTEND_PID=$!

# Wait briefly for both listeners; fail if either died or health never comes up
ready=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if ! kill -0 "${API_PID}" 2>/dev/null; then
    echo "Error: API process exited early. Check the logs above." >&2
    exit 1
  fi
  if ! kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    echo "Error: frontend process exited early. Is port ${FRONTEND_PORT} free?" >&2
    exit 1
  fi
  if curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 0.5
done

if [[ "${ready}" -eq 1 ]]; then
  echo "==> API health: ok"
else
  echo "Error: API did not become healthy on port ${API_PORT}." >&2
  echo "  Tip: stop other listeners, or run ./scripts/setup.sh then try again." >&2
  exit 1
fi

echo ""
echo "Open http://localhost:${FRONTEND_PORT} in your browser."
echo "Press Ctrl+C to stop."
echo ""

wait
