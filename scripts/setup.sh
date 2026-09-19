#!/usr/bin/env bash
# Full project setup — create backend venv and install Python dependencies.
# Prefer Docker for the API if you have it; this script prepares the local (non-Docker) path.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/.venv"

echo "==> Project root: ${ROOT_DIR}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but was not found." >&2
  exit 1
fi

echo "==> Creating virtualenv at backend/.venv (if missing)"
python3 -m venv "${VENV_DIR}"

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "==> Upgrading pip"
pip install --upgrade pip

echo "==> Installing backend requirements"
pip install -r "${BACKEND_DIR}/requirements.txt"

echo "==> Making scripts executable"
chmod +x "${ROOT_DIR}/scripts/setup.sh" "${ROOT_DIR}/scripts/run.sh"

HELPERS_DIR="${BACKEND_DIR}/helpers"
if [[ -f "${HELPERS_DIR}/requirements.txt" ]]; then
  echo "==> Installing optional helper deps (subject extraction)"
  pip install -r "${HELPERS_DIR}/requirements.txt"

  echo "==> Downloading rembg u2net model (~176MB, cached in ~/.rembg — not in the repo)"
  (
    cd "${HELPERS_DIR}"
    python download_model.py
  )
fi

echo "==> Initializing preset metadata database"
python -c "
import sys
sys.path.insert(0, '${BACKEND_DIR}')
from database.init_db import init_db
from database.db_ops import seed_default_presets
path = init_db()
seeded = seed_default_presets()
print(f'Database ready: {path}')
print(f'Seeded {len(seeded)} preset(s)')
"

echo ""
echo "Setup complete."
echo "  Next: ./scripts/run.sh"
echo "  Or with Docker: docker compose up --build"
echo "  Then open http://localhost:5500"
echo "  Subject helper: python backend/helpers/extract_subject.py photo.jpg -o subject.png"
