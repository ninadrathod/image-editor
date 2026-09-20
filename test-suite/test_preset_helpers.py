"""Unit tests for preset filter helpers (no rembg / no HTTP)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / "backend" / "helpers"
PRESETS = ROOT / "backend" / "presets"
if str(HELPERS) not in sys.path:
    sys.path.insert(0, str(HELPERS))

import filters as F  # noqa: E402
from apply_preset import (  # noqa: E402
    PresetAspectRatioError,
    apply_preset,
    apply_steps,
    load_preset,
    resolve_preset_path,
)


def test_resolve_preset_by_name() -> None:
    path = resolve_preset_path("bw_bg_glowing_subject", presets_dir=PRESETS)
    assert path.name == "bw_bg_glowing_subject.json"


def test_preset_files_have_steps() -> None:
    data = load_preset(PRESETS / "bw_bg_glowing_subject.json")
    assert data["steps"]
    assert data["steps"][0]["filter"] == "extract_subject"
    assert data.get("ar") == "non-square"


def test_grayscale_and_composite() -> None:
    bg = Image.new("RGB", (32, 32), (200, 40, 40))
    subject = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    # opaque white square in center
    for y in range(8, 24):
        for x in range(8, 24):
            subject.putpixel((x, y), (255, 255, 255, 255))

    gray = F.grayscale(bg)
    assert gray.getpixel((0, 0))[0] == gray.getpixel((0, 0))[1]
    out = F.composite(gray, subject)
    assert out.getpixel((16, 16))[:3] == (255, 255, 255)


def test_glow_line_border_keeps_interior_and_accepts_color() -> None:
    subject = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    for y in range(12, 36):
        for x in range(12, 36):
            subject.putpixel((x, y), (10, 20, 30, 255))

    outlined = F.glow_line_border(subject, color=(255, 0, 0), width=4, blur=0)
    assert outlined.mode == "RGBA"
    # Interior subject pixels stay original (not filled with red glow)
    assert outlined.getpixel((24, 24))[:3] == (10, 20, 30)
    # Some ring pixel outside the solid square should pick up red
    edge = outlined.getpixel((10, 24))
    assert edge[0] > edge[1] and edge[0] > edge[2]


def test_apply_steps_without_extract() -> None:
    image = Image.new("RGB", (24, 24), (100, 120, 140))
    steps = [
        {"filter": "grayscale", "on": "image"},
        {"filter": "brightness", "on": "image", "amount": 1.1},
    ]
    out = apply_steps(image, steps)
    assert out.size == (24, 24)


def test_apply_preset_square_ar_requires_square_image(tmp_path: Path) -> None:
    preset = tmp_path / "square_only.json"
    preset.write_text(
        json.dumps(
            {
                "name": "square_only",
                "ar": "square",
                "steps": [{"filter": "grayscale", "on": "image"}],
            }
        ),
        encoding="utf-8",
    )

    wide = Image.new("RGB", (10, 6), (1, 2, 3))
    with pytest.raises(PresetAspectRatioError, match="square"):
        apply_preset(wide, preset)

    square = Image.new("RGB", (6, 6), (1, 2, 3))
    out = apply_preset(square, preset)
    assert out.size == (6, 6)
