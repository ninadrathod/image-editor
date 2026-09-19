# ARCHITECTURE.md — Image Editor (Blur Studio)

Detailed architecture for the current blur MVP.

## Goals

- Accept a user-uploaded image in the browser.
- Validate that the input is an image (client + server).
- Process blur on the **server** (not in the browser canvas).
- Return binary image data and display it on the frontend.
- Stay modular, containerized, and easy to extend with more edit endpoints.

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
│  Docker Compose service: api (port 8000)                     │
│  FastAPI (uvicorn)                                           │
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
  Dockerfile
  requirements.txt
  app/
    main.py              # FastAPI app, CORS, /health, router mount
    routes/
      blur.py            # POST /api/blur
    services/
      blur.py            # is_allowed_image, apply_blur
      image_io.py        # load_image, save_png_bytes

test-suite/              # pytest unit tests for services only (not routes/HTTP)
  conftest.py            # adds backend/ to sys.path
  requirements.txt       # pytest
  test_blur.py
  test_image_io.py
```
### API contracts

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/health` | — | `{ "status": "ok" }` |
| POST | `/api/blur` | `multipart/form-data` field `file` | `image/png` bytes |

Error responses use FastAPI `HTTPException` with JSON `detail` (e.g. non-image, empty file, decode failure).

### Blur algorithm

- Pillow `ImageFilter.GaussianBlur` with default radius **12** (`DEFAULT_BLUR_RADIUS` in `services/blur.py`).
- Non-RGB(A) modes are converted to RGBA before filtering for stable PNG output.

### CORS

- Development CORS allows all origins so any local static host can call the API. Tighten this before production deployment.

## Containerization

- `backend/Dockerfile` — slim Python image, installs deps, runs uvicorn on `0.0.0.0:8000`.
- Root `docker-compose.yml` — builds `./backend`, maps `8000:8000`, mounts `./backend/app` for reload during development.

## Documentation responsibilities

| File | Contents |
|------|----------|
| `README.md` | Setup & run only |
| `CONTEXT.md` | Short agent/contributor briefing |
| `ARCHITECTURE.md` | This file — design & data flow |
| `project.html` | Advertise-style overview; CTAs link to GitHub fork |
| `scripts/setup.sh` | One-command local bootstrap |
| `scripts/run.sh` | One-command API + frontend start |
| `test-suite/` | Service-function unit tests (pytest); CI via `.github/workflows/test-suite.yml` |

When features change, update these in the same change set (enforced by `.cursor/rules/docs-and-branch-safety.mdc`). When `backend/app/services/` change, update matching `test-suite/` tests **only where necessary**.

## Helper scripts

- `scripts/setup.sh` — creates `backend/.venv`, installs `requirements.txt`, ensures scripts are executable.
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
