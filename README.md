# Image Editor (Blur Studio)

Upload an image, send it to the API, and get a blurred copy back.

## Requirements

- Python 3.12+ (3.14 works with the pinned dependencies)
- A modern browser (Chrome, Firefox, Safari, or Edge)
- Optional: [Docker](https://docs.docker.com/get-docker/) and Docker Compose

## Quick start (scripts)

1. Clone the repository:

```bash
git clone https://github.com/ninadrathod/image-editor.git
cd image-editor
```

2. Set up the project (creates `backend/.venv` and installs dependencies):

```bash
./scripts/setup.sh
```

3. Run the API and frontend:

```bash
./scripts/run.sh
```

4. Open [http://localhost:5500](http://localhost:5500), upload an image, and click **Blur image**.

Press **Ctrl+C** in the terminal to stop both servers.

## Alternative: Docker for the API

```bash
docker compose up --build
```

Then serve the frontend separately:

```bash
python3 -m http.server 5500
```

## Stop (Docker)

```bash
docker compose down
```
