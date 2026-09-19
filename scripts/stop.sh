#!/usr/bin/env bash
# Stop processes listening on the API and frontend ports (defaults: 8000, 5500).
set -euo pipefail

API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5500}"

kill $(lsof -tiTCP:"${API_PORT}" -sTCP:LISTEN) $(lsof -tiTCP:"${FRONTEND_PORT}" -sTCP:LISTEN) 2>/dev/null || true
