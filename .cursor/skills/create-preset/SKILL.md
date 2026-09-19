---
name: create-preset
description: >-
  Create a new image-editor JSON preset from a plain-language request (and
  optional reference images). Runs a gated POC → name → keywords → ship
  workflow into backend/presets/, helpers/, and the SQLite presets database.
  Use when the user asks to create a preset, add a new look/filter recipe,
  design an image effect pipeline, or follow the create-preset skill.
disable-model-invocation: true
---

# Create preset

Follow this workflow **in order**. Do **not** skip ahead or write final files
until the user finalizes each gated step.

Read [backend/presets/PRESETS.md](../../../backend/presets/PRESETS.md) for the
current helpers, filters, shipped presets, and JSON step format.

## Progress checklist

```
Create-preset progress:
- [ ] 1. Understand the request (and any reference images)
- [ ] 2. Temporary POC presets + sample output images (user picks one)
- [ ] 3. Propose preset names (user picks one)
- [ ] 4. Propose keywords (user finalizes the list)
- [ ] 5. Ship: helpers (if needed) + presets/*.json + database row
```

## How the user will ask

I will tell what I want in plain language (may also provide some reference images as input)

- understand what I want
- once you understand it, create some temporary preset (as proof of concepts) along with how the output images would look like after applying preset.
- I'll finalize one of the presets.
- then give me potential preset names for the database. I'll finalize one name
- then generate a list of potential keywords that would associate well with the preset, I'll finalize this list
- after all of this is finalized, create any helper scripts in helper/ if necessary, add the preset json to presets/, create an entry for this new preset in the database.

## Step details

### 1. Understand

- Restate the effect in 2–4 bullets (layers, order, look).
- If reference images were attached, note what to match (tone, border, B&W bg, etc.).
- Confirm understanding briefly; only ask clarifying questions if the request is ambiguous.
- Prefer existing filters in `backend/helpers/filters.py` before inventing new ones.

### 2. Temporary POC presets + preview images

- Branch safety: if on `main`/`master`, create a feature branch before any repo edits. POC files may live only under `/tmp`.
- Write **2–3** draft preset JSON files under `/tmp/image-editor-preset-poc/<slug>/` (not under `backend/presets/` yet).
- Apply each draft with:

```bash
source backend/.venv/bin/activate
python backend/helpers/apply_preset.py INPUT.jpg -p /tmp/.../draft_a.json -o /tmp/.../out_a.png
```

- If the user did not provide an input image, use a clear sample (or a prior `/tmp` POC photo) and say which file you used.
- Show the user: draft JSON summary (steps) **and** the output images (Read the PNGs so they render in chat).
- Wait until the user **finalizes one** draft. Do not propose DB names yet.

### 3. Preset names

- Offer **4–6** `snake_case` name candidates suitable for `preset_name` / filename.
- Wait until the user **finalizes one name**.

### 4. Keywords

- Offer a keyword list tied to the look (style, colors, subject treatment, use cases).
- Wait until the user **finalizes the list** (they may edit/remove items).

### 5. Ship (only after 2–4 are finalized)

1. Add any new filter ops under `backend/helpers/filters.py` and register them in `backend/helpers/apply_preset.py` `_SIMPLE_FILTERS` (and color alias handling if needed). Keep helpers modular.
2. Write `backend/presets/<final_name>.json` with `name`, `label`, `description`, and `steps`.
3. Insert a DB row:

```bash
source backend/.venv/bin/activate
python -c "
import sys
sys.path.insert(0, 'backend')
from database.db_ops import add_preset
print(add_preset(
    '<final_name>',
    'backend/presets/<final_name>.json',
    <final_keywords_list>,
))
"
```

4. Update `backend/presets/PRESETS.md`, `CONTEXT.md`, and `ARCHITECTURE.md` for the new preset/filter.
5. Add/adjust `test-suite/` coverage when new filter behavior needs it.
6. Run a final apply on a sample image and show the shipped output once.

## Rules

- Never commit rembg/ONNX weights; models stay in `~/.rembg/`.
- Do not invent HTTP routes unless asked — presets are CLI/helper scoped today.
- Do not finalize name/keywords/DB/files before the user confirms each gate.
- If a needed look cannot be done with current filters, say so in step 1–2 and propose a small new helper filter before POC.
