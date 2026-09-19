# Presets & helpers

Guide for image-editor JSON presets: what exists today, and how to add a new one.

For the agent workflow (POC → name → keywords → ship), use the project skill
`.cursor/skills/create-preset/SKILL.md`.

## Layout

| Path | Role |
|------|------|
| `backend/presets/*.json` | Named recipes (ordered filter steps) |
| `backend/helpers/filters.py` | Filter implementations (Pillow + rembg) |
| `backend/helpers/apply_preset.py` | Step runner + CLI |
| `backend/helpers/extract_subject.py` | Subject cutout CLI (rembg / `u2net`) |
| `backend/helpers/download_model.py` | Warm-cache `u2net` during setup |
| `backend/database/` | SQLite metadata (`presets.db`, `db_ops.py`) |

## Run a preset

```bash
source backend/.venv/bin/activate
python backend/helpers/apply_preset.py path/to/photo.jpg -p PRESET_NAME -o out.png
```

`PRESET_NAME` is a file under `backend/presets/` (with or without `.json`), or a full path to a JSON file.

## Shipped presets

### `bw_bg_glowing_subject`

- **Idea:** Extract subject → grayscale background → glowing **line** border on subject → composite.
- **File:** `backend/presets/bw_bg_glowing_subject.json`
- **DB:** seeded via `seed_default_presets()` / setup

## Built-in filters

| Filter | What it does | Common params |
|--------|----------------|---------------|
| `extract_subject` | rembg cutout + blurred fill background | `on`, `as` (subject), `bg_as` (background) |
| `brightness` | Brightness enhance | `on`, `amount` |
| `color` | Saturation enhance | `on`, `amount` |
| `contrast` | Contrast enhance | `on`, `amount` |
| `overlay` | Blend a solid tint | `on`, `rgb`/`color`, `alpha` |
| `grayscale` | Desaturate | `on` |
| `glow_border` | Soft halo under subject (fills expanded mask) | `on`, `rgb`/`color`, `width`, `blur` |
| `glow_line_border` | Outline **ring** only (subject body unchanged) | `on`, `color`/`rgb`, `width`, `blur` |
| `composite` | Paste overlay on base | `base`, `overlay`, `as` |

Layers are named images in memory. Typical keys: `image`, `subject`, `background`.

## Preset JSON shape

```json
{
  "name": "example_name",
  "label": "Human label",
  "description": "What this look does.",
  "steps": [
    {
      "filter": "extract_subject",
      "on": "image",
      "as": "subject",
      "bg_as": "background"
    },
    { "filter": "grayscale", "on": "background" },
    {
      "filter": "glow_line_border",
      "on": "subject",
      "color": [0, 255, 200],
      "width": 5,
      "blur": 2
    },
    {
      "filter": "composite",
      "base": "background",
      "overlay": "subject",
      "as": "image"
    }
  ]
}
```

Rules of thumb:

1. Always end with a `composite` (or other step) that writes `as: "image"`.
2. Apply background edits with `"on": "background"`; subject edits with `"on": "subject"`.
3. Prefer `glow_line_border` when you want an outline, not a filled glow.

## Database metadata

Table `presets` in `backend/database/presets.db`:

| Column | Meaning |
|--------|---------|
| `preset_id` | Auto primary key |
| `preset_name` | Unique name (usually matches JSON `name` / filename stem) |
| `preset_path` | Repo-relative path, e.g. `backend/presets/foo.json` |
| `keywords` | JSON list of search tags |
| `created_date` | Auto timestamp |

```bash
source backend/.venv/bin/activate
python -c "
import sys
sys.path.insert(0, 'backend')
from database.db_ops import add_preset, list_presets
print(list_presets())
"
```

## How to create a new preset (human checklist)

1. Describe the look in plain language (optional reference images).
2. Ask the agent to use **create-preset** (or follow that skill).
3. Review temporary POC outputs under `/tmp` and pick one recipe.
4. Pick a final `snake_case` preset name.
5. Finalize the keywords list.
6. Agent then:
   - adds helpers/filters only if needed
   - writes `backend/presets/<name>.json`
   - inserts a row with `add_preset(...)`
   - updates this file + CONTEXT/ARCHITECTURE

## Adding a new filter (when needed)

1. Implement a function in `backend/helpers/filters.py`.
2. Register it in `backend/helpers/apply_preset.py` → `_SIMPLE_FILTERS`.
3. If it takes a tint, accept `color` and/or `rgb`, and extend the color-alias block in `apply_steps`.
4. Add a focused unit test under `test-suite/` when behavior is non-trivial.
5. Document it in the filters table above.
