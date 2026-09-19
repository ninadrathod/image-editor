# Image Editor (Blur Studio)

Upload an image, send it to the API, and get a blurred copy back.

## Requirements

- Python 3.12+ (3.14 works with the pinned dependencies)
- A modern browser (Chrome, Firefox, Safari, or Edge)

## Quick start (scripts)

1. Clone the repository:

```bash
git clone https://github.com/ninadrathod/image-editor.git
cd image-editor
```

2. Set up the project (creates `backend/.venv`, installs API + helper deps, downloads the rembg `u2net` model into `~/.rembg/`, and initializes `backend/database/presets.db`):

```bash
./scripts/setup.sh
```

3. Run the API and frontend:

```bash
./scripts/run.sh
```

4. Open [http://localhost:5500](http://localhost:5500), upload an image, and click **Blur image**.

Press **Ctrl+C** in the terminal to stop both servers.

## Run tests

Service-function unit tests (not HTTP/API) live in `test-suite/` and run on PRs via GitHub Actions.

```bash
source backend/.venv/bin/activate
pip install -r test-suite/requirements.txt
pytest test-suite/ -v
```

## Optional: subject extraction helper

Setup already installs helper deps and pulls the `u2net` model. To run:

```bash
source backend/.venv/bin/activate
python backend/helpers/extract_subject.py path/to/photo.jpg -o subject.png
```

Model weights live in `~/.rembg/` and are gitignored (also `*.onnx`).

## Optional: JSON presets

Presets are JSON step lists in `backend/presets/`.

```bash
source backend/.venv/bin/activate
python backend/helpers/apply_preset.py path/to/photo.jpg -p bw_bg_glowing_subject -o out.png
```
