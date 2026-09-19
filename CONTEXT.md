# CONTEXT.md — Image Editor (Blur Studio)

Short briefing for AI agents and new contributors. Prefer this file for orientation; see `ARCHITECTURE.md` for deeper design.

## What this project is

A local **image editor** whose first feature is **server-side blur**:

1. User uploads an image in the browser (validated as an image).
2. Frontend `POST`s the file to `POST /api/blur`.
3. Backend (FastAPI + Pillow) applies a Gaussian blur and returns a PNG.
4. Frontend shows (and can download) the result.

Repo: https://github.com/ninadrathod/image-editor

## Layout (high level)

| Path | Role |
|------|------|
| `index.html`, `script.js`, `js/`, `css/`, `icons/` | Frontend UI |
| `project.html` | Advertise-style project pitch (fork on GitHub to use) |
| `backend/` | FastAPI app, Dockerfile |
| `backend/helpers/` | CLI helpers: subject extraction + JSON preset runner |
| `backend/presets/` | JSON image presets (ordered filter steps); see `PRESETS.md` |
| `backend/database/` | SQLite preset metadata (`presets.db` + `db_ops.py`) |
| `.cursor/skills/create-preset/` | Skill: gated workflow to design and ship a new preset |
| `test-suite/` | Unit tests for backend **service functions** (not HTTP/API) |
| `.github/workflows/` | CI (runs `test-suite/` on PRs) |
| `scripts/setup.sh` | Full local setup (venv + deps) |
| `scripts/run.sh` | Start API + frontend together |
| `docker-compose.yml` | Runs the API on port 8000 |
| `README.md` | Setup & run only |
| `ARCHITECTURE.md` | How the system works |
| `.cursor/rules/` | Agent rules (docs sync, branch safety, post-change review) |
| `.cursor/skills/cleanup-after-push/` | After push: checkout main, pull, delete local feature branch |

## Key conventions

- Keep code **modular and easy to read** (small modules, clear names).
- Frontend styling: **Tailwind** (CDN) + light custom CSS in `css/styles.css`.
- Backend image work lives in `backend/app/services/`; routes stay thin.
- Service-function tests live in `test-suite/` (pytest); keep them in sync when service behavior changes.
- Do **not** put architecture detail in `README.md`.
- After meaningful product/code changes, update `project.html`, `README.md`, `ARCHITECTURE.md`, `CONTEXT.md`, `scripts/setup.sh` / `scripts/run.sh`, and `test-suite/` as needed.
- **Never commit directly on `main`** — create a feature branch first (see Cursor rule).
- After finishing product/code changes on a branch, the agent must run a thorough **bug + security** review of branch changes and list **all** findings at once (see `.cursor/rules/docs-and-branch-safety.mdc`).

## Local defaults

- API: `http://localhost:8000`
- Frontend static server: typically `http://localhost:5500` (any static host of the repo root)
- Health check: `GET /health`
- Blur endpoint: `POST /api/blur` (multipart field name: `file`)

## Current scope

- Image upload + client-side type check
- Server-side Gaussian blur
- Side-by-side preview + download

Optional helpers (not part of the blur API):
- `backend/helpers/extract_subject.py` — background removal (rembg / `u2net`)
- `backend/helpers/apply_preset.py` — run a JSON preset from `backend/presets/`
- Example presets: `bw_bg_glowing_subject`
- `backend/database/` — lightweight SQLite file (`presets.db`) for preset metadata (name, path, keywords). Ops in `db_ops.py`; created/seeded by `./scripts/setup.sh`.
- Preset catalog + how-to: `backend/presets/PRESETS.md`
- To design/ship a new preset from plain language, use skill `.cursor/skills/create-preset/`

`./scripts/setup.sh` installs helper deps and downloads the `u2net` model into `~/.rembg/` (outside the repo; gitignored).
