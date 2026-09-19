#!/usr/bin/env python3
"""
Apply a JSON preset (ordered filter steps) to an image.

Usage:
  python apply_preset.py INPUT.jpg --preset bw_bg_glowing_subject -o out.png
  python apply_preset.py INPUT.jpg --preset path/to/custom.json -o out.png

Presets live in backend/presets/ by default.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image

import filters as F

HELPERS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = HELPERS_DIR.parent
DEFAULT_PRESETS_DIR = BACKEND_DIR / "presets"

# Filters that only transform a single layer in-place / to `as`
_SIMPLE_FILTERS = {
    "brightness": F.brightness,
    "color": F.color,
    "contrast": F.contrast,
    "overlay": F.overlay,
    "grayscale": F.grayscale,
    "glow_border": F.glow_border,
    "glow_line_border": F.glow_line_border,
}


def resolve_preset_path(preset: str | Path, presets_dir: Path = DEFAULT_PRESETS_DIR) -> Path:
    path = Path(preset)
    if path.is_file():
        return path
    candidate = presets_dir / path
    if candidate.is_file():
        return candidate
    if not path.suffix:
        candidate = presets_dir / f"{path.name}.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Preset not found: {preset} (looked in {presets_dir})")


def load_preset(preset_path: Path) -> dict[str, Any]:
    data = json.loads(preset_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "steps" not in data:
        raise ValueError(f"Preset must be an object with a 'steps' array: {preset_path}")
    if not isinstance(data["steps"], list) or not data["steps"]:
        raise ValueError(f"Preset 'steps' must be a non-empty list: {preset_path}")
    return data


def _params(step: dict[str, Any]) -> dict[str, Any]:
    skip = {"filter", "on", "as", "bg_as", "base", "overlay"}
    return {k: v for k, v in step.items() if k not in skip}


def apply_steps(image: Image.Image, steps: list[dict[str, Any]]) -> Image.Image:
    """Run ordered preset steps over named layers. Returns the final `image` layer."""
    layers: dict[str, Image.Image] = {"image": image.convert("RGBA")}

    for index, step in enumerate(steps):
        if not isinstance(step, dict) or "filter" not in step:
            raise ValueError(f"Step {index} must be an object with a 'filter' key")

        name = step["filter"]
        params = _params(step)

        if name == "extract_subject":
            source_key = step.get("on", "image")
            if source_key not in layers:
                raise KeyError(f"Step {index}: unknown layer '{source_key}'")
            subject, background = F.extract_subject_layers(layers[source_key])
            layers[step.get("as", "subject")] = subject
            layers[step.get("bg_as", "background")] = background
            continue

        if name == "composite":
            base_key = step.get("base", "background")
            overlay_key = step.get("overlay", "subject")
            if base_key not in layers:
                raise KeyError(f"Step {index}: unknown base layer '{base_key}'")
            if overlay_key not in layers:
                raise KeyError(f"Step {index}: unknown overlay layer '{overlay_key}'")
            result = F.composite(layers[base_key], layers[overlay_key])
            layers[step.get("as", "image")] = result
            continue

        if name not in _SIMPLE_FILTERS:
            allowed = ", ".join(sorted([*_SIMPLE_FILTERS, "extract_subject", "composite"]))
            raise ValueError(f"Step {index}: unknown filter '{name}'. Allowed: {allowed}")

        on_key = step.get("on", "image")
        if on_key not in layers:
            raise KeyError(f"Step {index}: unknown layer '{on_key}'")

        # Normalize color aliases for filters that take an RGB tint
        call_params = dict(params)
        if name in {"overlay", "glow_border", "glow_line_border"}:
            if "color" in call_params and "rgb" not in call_params:
                call_params["rgb"] = call_params.pop("color")

        result = _SIMPLE_FILTERS[name](layers[on_key], **call_params)
        layers[step.get("as", on_key)] = result

    if "image" not in layers:
        raise RuntimeError("Preset finished without an 'image' layer — add composite with as=image")
    return layers["image"]


def apply_preset(
    image: Image.Image,
    preset: str | Path,
    *,
    presets_dir: Path = DEFAULT_PRESETS_DIR,
) -> Image.Image:
    path = resolve_preset_path(preset, presets_dir=presets_dir)
    data = load_preset(path)
    return apply_steps(image, data["steps"])


def apply_preset_file(
    input_path: str | Path,
    preset: str | Path,
    output_path: str | Path,
    *,
    presets_dir: Path = DEFAULT_PRESETS_DIR,
) -> Path:
    src = Path(input_path)
    dst = Path(output_path)
    if not src.is_file():
        raise FileNotFoundError(f"Input image not found: {src}")

    with Image.open(src) as image:
        image.load()
        result = apply_preset(image, preset, presets_dir=presets_dir)

    dst.parent.mkdir(parents=True, exist_ok=True)
    # Preserve alpha if present
    if result.mode == "RGBA" and result.getchannel("A").getextrema() != (255, 255):
        result.save(dst, format="PNG")
    else:
        result.convert("RGB").save(dst, format="PNG")
    return dst


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a JSON image preset (step pipeline).")
    parser.add_argument("input", type=Path, help="Input image path")
    parser.add_argument(
        "--preset",
        "-p",
        required=True,
        help="Preset name (in backend/presets/) or path to a .json file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PNG path (default: <input>_<preset>.png)",
    )
    parser.add_argument(
        "--presets-dir",
        type=Path,
        default=DEFAULT_PRESETS_DIR,
        help="Directory of preset JSON files",
    )
    args = parser.parse_args(argv)

    preset_label = Path(args.preset).stem
    output = args.output or args.input.with_name(f"{args.input.stem}_{preset_label}.png")

    try:
        path = apply_preset_file(
            args.input,
            args.preset,
            output,
            presets_dir=args.presets_dir,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote preset result: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
