# CONTEXT.md — The Local Studio

Short briefing for AI agents and new contributors. Prefer this file for orientation; see `ARCHITECTURE.md` for deeper design.

## What this project is

A local **image editor** for applying JSON presets to photos:

1. User picks a preset from the gallery (post-edit preview thumbnails from `previews/`).
2. User uploads an image in the browser (validated as an image).
3. Frontend `POST`s preset name + file to `POST /api/apply-preset`.
4. Backend resolves the preset from SQLite, runs the JSON filter pipeline, returns a PNG.
5. Frontend shows (and can download) the result. Refresh clears in-memory session state.

Repo: https://github.com/ninadrathod/local-studio

## Layout (high level)

| Path | Role |
|------|------|
| `index.html`, `script.js`, `js/`, `css/`, `icons/` | Frontend UI |
| `previews/` | Preset gallery assets: `pre-edit/` + `post-edit/` (before/after per DB preset) + `presets.json` |
| `project.html` | Advertise-style project pitch (fork on GitHub to use) |
| `backend/` | FastAPI app |
| `backend/helpers/` | CLI helpers: subject extraction + JSON preset runner |
| `backend/presets/` | JSON image presets (ordered filter steps); see `PRESETS.md` |
| `backend/database/` | SQLite preset metadata (`presets.db` + `db_ops.py`) |
| `.cursor/skills/create-preset/` | Skill: gated workflow to design and ship a new preset |
| `test-suite/` | Unit tests for backend **service functions** (not HTTP/API) |
| `.github/workflows/` | CI (runs `test-suite/` on PRs) |
| `scripts/setup.sh` | Full local setup (venv + deps) |
| `scripts/run.sh` | Start API + frontend together |
| `README.md` | Setup & run only |
| `ARCHITECTURE.md` | How the system works |
| `.cursor/rules/` | Agent rules (docs sync, branch safety, post-change review) |
| `.cursor/skills/cleanup-after-push/` | After push: checkout main, pull, delete local feature branch |
| `.cursor/skills/commit-draft-pr/` | Commit locally (no push) and draft PR title + description |
| `.cursor/skills/prune-unused-code/` | Audit + remove unused code without changing UI/workflows |

## Key conventions

- Keep code **modular and easy to read** (small modules, clear names).
- Frontend styling: **Tailwind** (CDN) + light custom CSS in `css/styles.css`.
- Backend image work lives in `backend/app/services/`; routes stay thin.
- Service-function tests live in `test-suite/` (pytest); keep them in sync when service behavior changes.
- Do **not** put architecture detail in `README.md`.
- After meaningful product/code changes, update `project.html`, `README.md`, `ARCHITECTURE.md`, `CONTEXT.md`, `scripts/setup.sh` / `scripts/run.sh`, and `test-suite/` as needed.
- **Never commit directly on `main`** — create a feature branch first (see Cursor rule).
- After finishing product/code changes on a branch, the agent must run a thorough **bug + security** review of branch changes (and **UI responsiveness** across phone/tablet/desktop when frontend layout changed) and list **all** findings at once (see `.cursor/rules/docs-and-branch-safety.mdc`).

## Local defaults

- API: `http://localhost:8000`
- Frontend static server: typically `http://localhost:5500` (any static host of the repo root)
- Health check: `GET /health`
- Blur endpoint: `POST /api/blur` (multipart field name: `file`)
- Apply-preset endpoint: `POST /api/apply-preset` (multipart fields: `preset_name`, `file`) → PNG
- Preset search: `GET /api/presets/search?q=…` → JSON list of `{ preset_name, keywords }` (matches name or keywords)
- Upload caps (blur + apply-preset): 20 MiB body, max side 8000 px / 25M pixels; preset JSON paths must stay under `backend/presets/`
- Apply-preset concurrency: 1 in-flight job (extra requests get **503**)

## Current scope

- Preset gallery (left, ~65% width on desktop): search + post-edit thumbnails from `previews/presets.json`; click to select
- Search filters the gallery in place via realtime `GET /api/presets/search?q=…` (DB `preset_name` + `keywords`)
- Image upload (right, ~35% width on desktop): client-side type check + preview
- Studio UI uses the full browser width (no max-content cap on `index.html`)
- Generate edit when both preset + file are set → `POST /api/apply-preset` → result + download
- Session state is in-memory only (refresh clears upload + edited result)
- Gallery only accepts `preset_name` + relative `previews/pre-edit|post-edit/…` paths from `presets.json`
- Server-side Gaussian blur still available via `POST /api/blur` (not the primary UI flow)

Optional helpers:
- `backend/helpers/extract_subject.py` — background removal (rembg / `u2net`)
- `backend/helpers/apply_preset.py` — run a JSON preset from `backend/presets/` (also used by the apply-preset API)
- Example presets: `bw_bg_glowing_subject`
- `backend/database/` — lightweight SQLite file (`presets.db`) for preset metadata (name, path, keywords). Ops in `db_ops.py`; created/seeded by `./scripts/setup.sh`.
- `previews/` — static preset gallery assets (`pre-edit/` + `post-edit/` + `presets.json`); wired into the index UI gallery
- Preset catalog + how-to: `backend/presets/PRESETS.md`
- To design/ship a new preset from plain language, use skill `.cursor/skills/create-preset/`
- To commit locally without pushing and get PR title/description copy, use skill `.cursor/skills/commit-draft-pr/`
- To remove unused/redundant code without changing UI or workflows, use skill `.cursor/skills/prune-unused-code/`

`./scripts/setup.sh` installs helper deps and downloads the `u2net` model into `~/.rembg/` (outside the repo; gitignored). It also recreates `backend/.venv` if the project was renamed/moved and console-script shebangs are stale. `./scripts/run.sh` uses the venv Python directly and exits with a clear error if deps are missing or ports `8000`/`5500` are already taken.
