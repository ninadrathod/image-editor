# ARCHITECTURE.md — The Local Studio

Detailed architecture for the current blur MVP.

## Goals

- Accept a user-uploaded image in the browser.
- Validate that the input is an image (client + server).
- Process blur on the **server** (not in the browser canvas).
- Return binary image data and display it on the frontend.
- Stay modular and easy to extend with more edit endpoints.

## System overview

```
┌──────────────────────────────────────────────────────────────┐
│  Browser                                                     │
│  index.html + script.js                                      │
│    ├─ js/image.js   → validate MIME / extension, object URLs │
│    └─ js/api.js     → FormData POST to /api/blur             │
└────────────────────────────┬─────────────────────────────────┘
                             │ multipart/form-data (field: file)
                             ▼
┌──────────────────────────────────────────────────────────────┐
│  Local FastAPI (uvicorn) on port 8000                        │
│    routes/blur.py  → validate upload, orchestrate            │
│    services/image_io.py → decode bytes ↔ Pillow / PNG encode │
│    services/blur.py     → GaussianBlur                       │
└──────────────────────────────────────────────────────────────┘
```

## Frontend

### Entry points

- `index.html` — UI shell (Tailwind via CDN, custom atmosphere in `css/styles.css`).
- `script.js` — wires DOM events (file pick, drag-drop, blur button) to helpers.
- `js/image.js` — `isImageFile`, object URL create/revoke.
- `js/api.js` — `blurImage(baseUrl, file)` → `Blob`.

### UX flow

1. User selects or drops a file.
2. Client rejects non-images and shows an inline error.
3. Original preview uses a local object URL.
4. On **Blur image**, the file is posted to the API; a loading state covers the result panel.
5. Response blob is shown via another object URL; download link reuses that URL.

### Config

- API base URL is currently hard-coded in `script.js` as `http://localhost:8000`.

### Marketing page

- `project.html` is a lightweight advertise-style page (flow, CTAs). It points users to **fork the GitHub repo** and run locally — there is no hosted live app.

## Backend

### Stack

- **Python 3.12**
- **FastAPI** — HTTP API
- **Pillow** — image decode / Gaussian blur / PNG encode
- **uvicorn** — ASGI server
- **python-multipart** — file uploads

### Package layout

```
backend/
  requirements.txt
  helpers/
    requirements.txt     # rembg[cpu] — installed by setup.sh
    download_model.py    # warm-cache u2net during setup (~/.rembg)
    extract_subject.py   # CLI: image in → subject PNG (transparent bg)
    filters.py           # Pillow + rembg filter ops for presets
    apply_preset.py      # CLI: apply JSON preset steps to an image
  presets/
    bw_bg_glowing_subject.json
  database/
    schema.sql           # presets table
    init_db.py           # create presets.db
    db_ops.py            # CRUD for preset metadata
    presets.db           # SQLite file (created by setup/init)
  app/
    main.py              # FastAPI app, CORS, /health, router mount
    routes/
      blur.py            # POST /api/blur
      preset.py          # POST /api/apply-preset
    services/
      blur.py            # is_allowed_image, apply_blur
      image_io.py        # load_image, save_png_bytes, upload/dimension caps
      preset.py          # resolve DB preset name → JSON (sandboxed); apply_named_preset

test-suite/              # pytest unit tests for services only (not routes/HTTP)
  conftest.py            # adds backend/ to sys.path
  requirements.txt       # pytest
  test_blur.py
  test_image_io.py
  test_preset.py
```
### API contracts

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/health` | — | `{ "status": "ok" }` |
| POST | `/api/blur` | `multipart/form-data` field `file` | `image/png` bytes |
| POST | `/api/apply-preset` | `multipart/form-data` fields `preset_name`, `file` | `image/png` bytes |

Error responses use FastAPI `HTTPException` with JSON `detail` (e.g. non-image, empty file, unknown preset, decode failure). Oversized uploads/images return **413**. Apply-preset returns **503** when the concurrency gate is full.

Upload guards (`services/image_io.py`): max **20 MiB** body (`MAX_UPLOAD_BYTES`), max side **8000** px, max **25M** pixels. Preset JSON paths from the DB must resolve under `backend/presets/` (`PresetPathUnsafeError` otherwise). Apply-preset runs off the event loop via `asyncio.to_thread` and allows only **1** concurrent job (`MAX_CONCURRENT_PRESET_JOBS`) so rembg cannot pile up.

### Blur algorithm

- Pillow `ImageFilter.GaussianBlur` with default radius **12** (`DEFAULT_BLUR_RADIUS` in `services/blur.py`).
- Non-RGB(A) modes are converted to RGBA before filtering for stable PNG output.

### Subject extraction helper (CLI only)

- `backend/helpers/extract_subject.py` — local background removal via **rembg** (`u2net` session / onnxruntime).
- Input: any Pillow-readable image path. Output: PNG with alpha (subject kept, background transparent).
- Not mounted as an HTTP route.
- `./scripts/setup.sh` installs `backend/helpers/requirements.txt` and runs `download_model.py` so `u2net` (~176MB) is cached under `~/.rembg/` (outside the repo).
- Gitignore blocks `.rembg/`, `*.onnx`, and `backend/helpers/models/` so weights are never committed.
- Example: `python backend/helpers/extract_subject.py photo.jpg -o subject.png`

### JSON preset pipeline

- Presets live in `backend/presets/*.json` as ordered `steps` with named layers (`image`, `subject`, `background`, …).
- Runner: `backend/helpers/apply_preset.py` (uses `filters.py`).
- HTTP: `POST /api/apply-preset` looks up `preset_name` in `presets.db`, loads that JSON path, runs the same runner, returns PNG (`app/services/preset.py` + `app/routes/preset.py`).
- Built-in filters: `extract_subject`, `brightness`, `color`, `contrast`, `overlay`, `grayscale`, `glow_border`, `glow_line_border`, `composite`.
- `glow_line_border` draws a colored outline ring only (does not fill/glow the subject body). Pass `"color": [R,G,B]` (or `"rgb"`).
- Shipped presets:
  - `bw_bg_glowing_subject` — extract → grayscale background → `glow_line_border` on subject → composite
- Example CLI: `python backend/helpers/apply_preset.py photo.jpg -p bw_bg_glowing_subject -o out.png`
- Human/agent guide: `backend/presets/PRESETS.md`
- New-preset workflow skill: `.cursor/skills/create-preset/SKILL.md`

### Preset metadata database

- Location: `backend/database/` (SQLite file `presets.db`, same pattern as a lightweight local store).
- Table `presets`: `preset_id` (PK auto), `preset_name`, `preset_path`, `keywords` (JSON list), `created_date` (auto `datetime('now')`).
- Service functions: `backend/database/db_ops.py` (`add_preset`, `list_presets`, `get_preset_by_id`, `update_preset`, `delete_preset`, `seed_default_presets`).
- `./scripts/setup.sh` runs `init_db()` and seeds `bw_bg_glowing_subject`.

### CORS

- Development CORS allows all origins so any local static host can call the API. Tighten this before production deployment.

## Local run

- `./scripts/setup.sh` creates `backend/.venv`, installs deps, and initializes the preset DB.
- `./scripts/run.sh` starts uvicorn on `0.0.0.0:8000` and a static frontend on port `5500`.

## Documentation responsibilities

| File | Contents |
|------|----------|
| `README.md` | Setup & run only |
| `CONTEXT.md` | Short agent/contributor briefing |
| `ARCHITECTURE.md` | This file — design & data flow |
| `backend/presets/PRESETS.md` | Helpers, filters, shipped presets, create-preset how-to |
| `.cursor/skills/create-preset/SKILL.md` | Gated agent workflow to design/ship a new preset |
| `project.html` | Advertise-style overview; CTAs link to GitHub fork |
| `scripts/setup.sh` | One-command local bootstrap |
| `scripts/run.sh` | One-command API + frontend start |
| `test-suite/` | Service-function unit tests (pytest); CI via `.github/workflows/test-suite.yml` |

When features change, update these in the same change set (enforced by `.cursor/rules/docs-and-branch-safety.mdc`). When `backend/app/services/` change, update matching `test-suite/` tests **only where necessary**. When helpers/filters/presets/DB metadata change, update `PRESETS.md` as needed.

## Helper scripts

- `scripts/setup.sh` — creates `backend/.venv`, installs API + helper requirements, downloads rembg `u2net` into `~/.rembg/`, initializes `backend/database/presets.db`, ensures scripts are executable.
- `scripts/run.sh` — starts uvicorn (port 8000) and a static file server on the repo root (port 5500); Ctrl+C stops both.

## Extension points

New edits should follow the same pattern:

1. Add a service function under `backend/app/services/`.
2. Add or update unit tests under `test-suite/` for that service (not the HTTP route).
3. Add a thin route under `backend/app/routes/` and mount it from `main.py`.
4. Add a small client helper under `js/` and wire it from `script.js`.
5. Refresh docs + `project.html` if user-visible behavior changed.

### Testing

- Scope: **service functions only** (`app.services.*`). Do not exercise FastAPI routes here.
- Local: after `./scripts/setup.sh`, install `test-suite/requirements.txt` into the same venv, then `pytest test-suite/ -v`.
- CI: `.github/workflows/test-suite.yml` runs the same suite on pull requests (and pushes to `main`).
