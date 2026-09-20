---
name: create-preset
description: >-
  Create a new JSON preset for The Local Studio from a plain-language request (and
  optional reference images). Runs a gated POC → name → keywords → ar → text_input →
  ship → gallery preview workflow into backend/presets/, helpers/, the SQLite presets
  database, and previews/. Use when the user asks to create a preset, add a new
  look/filter recipe, design an image effect pipeline, or follow the
  create-preset skill.
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
- [ ] 5. Confirm `ar`: `square` (square-only) or `non-square` (any aspect ratio)
- [ ] 6. Confirm text input: `text_input` yes/no (+ default_text + text_character_limit if yes)
- [ ] 7. Ship: helpers (if needed) + presets/*.json + database row + docs/tests
- [ ] 8. Gallery previews: search → square 720 → apply → user picks → ship assets
```

## How the user will ask

I will tell what I want in plain language (may also provide some reference images as input)

- understand what I want
- once you understand it, create some temporary preset (as proof of concepts) along with how the output images would look like after applying preset.
- I'll finalize one of the presets.
- then give me potential preset names for the database. I'll finalize one name
- then generate a list of potential keywords that would associate well with the preset, I'll finalize this list
- then confirm whether the preset is square-only (`ar=square`) or works on any image (`ar=non-square`)
- then confirm whether the preset needs user text (`text_input=yes`) — if yes, finalize `default_text` and `text_character_limit` (1–200)
- after all of this is finalized, create any helper scripts in helper/ if necessary, add the preset json to presets/, create an entry for this new preset in the database.
- then find open-licensed candidate photos that suit the new preset, prepare square 720×720 previews, show me the applied results, and only after I pick one write `previews/pre-edit/`, `previews/post-edit/`, and `previews/presets.json`.

## Step details

### 1. Understand

- Restate the effect in 2–4 bullets (layers, order, look).
- If reference images were attached, note what to match (tone, border, B&W bg, etc.).
- Note whether the look is **square-only** (`ar=square`) or works on any frame (`ar=non-square`). Ask if that is unclear.
- Note whether the look needs **user text** (caption, title, initials, etc.). If yes, plan a step that uses `"$text"` (usually `draw_text`). Ask if that is unclear.
- Confirm understanding briefly; only ask clarifying questions if the request is ambiguous.
- Prefer existing filters in `backend/helpers/filters.py` before inventing new ones.
- Each JSON step’s `"filter"` is the helper function name; remaining keys are that helper’s parameters. Do **not** invent API if/else for a new look — register the helper in `FILTERS` instead.

### 2. Temporary POC presets + preview images

- Branch safety: if on `main`/`master`, create a feature branch before any repo edits. POC files may live only under `/tmp`.
- Write **2–3** draft preset JSON files under `/tmp/local-studio-preset-poc/<slug>/` (not under `backend/presets/` yet).
- Include `text_input` / `default_text` / `text_character_limit` in drafts when the look needs text; use `"text": "$text"` (or another `$text` param) in the step that consumes it.
- Apply each draft with:

```bash
source backend/.venv/bin/activate
python backend/helpers/apply_preset.py INPUT.jpg -p /tmp/.../draft_a.json -o /tmp/.../out_a.png
# If text_input=yes:
python backend/helpers/apply_preset.py INPUT.jpg -p /tmp/.../draft_a.json --text "Sample" -o /tmp/.../out_a.png
```

- If the user did not provide an input image, use a clear sample (or a prior `/tmp` POC photo) and say which file you used.
- If a draft is square-only (`"ar": "square"`), apply it to a **square** sample. A non-square input will error.
- Show the user: draft JSON summary (steps + text fields if any) **and** the output images (Read the PNGs so they render in chat).
- Wait until the user **finalizes one** draft. Do not propose DB names yet.

### 3. Preset names

- Offer **4–6** `snake_case` name candidates suitable for `preset_name` / filename.
- Wait until the user **finalizes one name**.

### 4. Keywords

- Offer a keyword list tied to the look (style, colors, subject treatment, use cases).
- Wait until the user **finalizes the list** (they may edit/remove items).

### 5. Aspect ratio (`ar`)

- Offer `square` (preset only works on square images) or `non-square` (works on any aspect ratio; default).
- Wait until the user **finalizes `ar`**. JSON, DB, and gallery `previews/presets.json` must all use that same value.

### 6. Text input

- Offer `text_input: no` (default — no caption field in the UI) or `text_input: yes`.
- If **yes**, also finalize:
  - `default_text` (prefill / fallback when apply omits `text`; may be `""`)
  - `text_character_limit` (integer **1–200**)
- If **no**, set `default_text: ""` and `text_character_limit: 0`.
- When `text_input` is `yes`, at least one step must use `"$text"` in a string parameter (typically `"text": "$text"` on `draw_text`).
- Wait until the user **finalizes** these fields. JSON, DB (`add_preset`), and `previews/presets.json` must all match.

### 7. Ship (only after 2–6 are finalized)

1. Add any new filter ops under `backend/helpers/filters.py` and register them in `backend/helpers/apply_preset.py` `FILTERS` (use `_run_simple` for single-layer ops). Keep helpers modular. Do not add per-filter if/else in the API or the step runner.
2. Write `backend/presets/<final_name>.json` with `name`, `label`, `description`, `ar` (`square` or `non-square`), `text_input` (`yes` or `no`), `default_text`, `text_character_limit`, and `steps`. Each step’s `"filter"` is the helper function name; remaining keys are that helper’s parameters. Use `"$text"` in a param when the step should receive the user string.
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
    ar='<square|non-square>',
    text_input='<yes|no>',
    default_text='<default or empty>',
    text_character_limit=<n>,
))
"
```

4. Update `backend/presets/PRESETS.md`, `CONTEXT.md`, and `ARCHITECTURE.md` for the new preset/filter.
5. Add/adjust `test-suite/` coverage when new filter behavior needs it.
6. Run a final apply on a sample image (pass `--text` when `text_input=yes`) and show the shipped output once.

Do **not** write gallery assets under `previews/` in this step — that is step 8.

### 8. Gallery previews (only after step 7)

Understand what the shipped preset does, then pick photos where that effect actually looks good (subject cutout, color vs B&W, silhouette + glow, caption placement, etc.). Subject matter can be anything that fits the look — scenic, street, portrait, poster/music-cover vibe — not limited to landscapes.

1. **Search** for several **open-licensed** photographs on the internet that would show this preset well. Prefer CC0 / CC BY / CC BY-SA (e.g. Wikimedia Commons) or other clearly free licenses. Never use unlicensed stock. Verify license + photographer/source for each candidate.
2. **Prepare** each candidate: crop to a square (crop excess from one side so composition stays strong), then downsample to **720×720**. Keep work under `/tmp` or `previews/_candidates/` until the user picks — do not overwrite shipped `pre-edit/` / `post-edit/` yet.
3. **Apply** the shipped preset to each prepared square (use `--text` with the finalized `default_text` or a short sample when `text_input=yes`), show the user the results (and optionally originals), and **ask which image is best** for the gallery preview. Wait for the user to finalize one letter/candidate.
4. **Once finalized**, write:
   - `previews/pre-edit/<final_name>.*` — the chosen square 720×720 source
   - `previews/post-edit/<final_name>.png` — same crop after the preset
   - append `{ "preset_name", "ar", "text_input", "default_text", "text_character_limit", "pre_edit_image", "post_edit_image" }` to `previews/presets.json`
   - record source + photographer + license in `previews/CREDITS.md`
   - remove any temporary `previews/_candidates/` (or `/tmp` POC) files used for comparison

## Rules

- Never commit rembg/ONNX weights; models stay in `~/.rembg/`.
- Do not invent extra HTTP routes unless asked — apply by DB name via existing `POST /api/apply-preset` (optional multipart `text` when needed).
- Do not finalize name/keywords/`ar`/text fields/DB/files/gallery assets before the user confirms each gate.
- Keep `ar` and text-input fields in sync across preset JSON, `add_preset(...)`, and `previews/presets.json`.
- Gallery previews must be open-licensed, square **720×720**, with matching pre-edit and post-edit crops.
- If a needed look cannot be done with current filters, say so in step 1–2 and propose a small new helper filter before POC.
- Studio UX assumes **select preset first**, then upload; presets with `text_input=yes` show a constrained text field before generate.
