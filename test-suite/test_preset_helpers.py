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
    FILTERS,
    PresetAspectRatioError,
    PresetTextError,
    apply_preset,
    apply_steps,
    load_preset,
    resolve_preset_path,
    resolve_user_text,
)


def test_resolve_preset_by_name() -> None:
    path = resolve_preset_path("bw_bg_glowing_subject", presets_dir=PRESETS)
    assert path.name == "bw_bg_glowing_subject.json"


def test_preset_files_have_steps() -> None:
    data = load_preset(PRESETS / "bw_bg_glowing_subject.json")
    assert data["steps"]
    assert data["steps"][0]["filter"] == "extract_subject"
    assert data.get("ar") == "non-square"
    assert data.get("text_input") == "no"
    assert data.get("default_text") == ""
    assert data.get("text_character_limit") == 0


def test_filter_registry_is_name_lookup() -> None:
    assert set(FILTERS) >= {
        "extract_subject",
        "composite",
        "grayscale",
        "glow_line_border",
        "draw_text",
        "place_on_canvas",
    }


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


def test_draw_text_paints_over_background() -> None:
    image = Image.new("RGB", (96, 96), (0, 0, 0))
    out = F.draw_text(image, text="HI", font_size=40, color=(255, 255, 255))
    assert out.convert("L").getextrema()[1] > 0


def test_apply_steps_binds_text_placeholder() -> None:
    image = Image.new("RGB", (96, 96), (0, 0, 0))
    steps = [
        {
            "filter": "draw_text",
            "on": "image",
            "text": "$text",
            "font_size": 36,
            "color": [255, 255, 255],
        }
    ]
    blank = apply_steps(image, steps, text="")
    painted = apply_steps(image, steps, text="HELLO")
    assert blank.convert("L").getextrema()[1] == 0
    assert painted.convert("L").getextrema()[1] > 0


def test_resolve_user_text_default_and_limit() -> None:
    preset = {
        "text_input": "yes",
        "default_text": "Hi",
        "text_character_limit": 4,
    }
    assert resolve_user_text(preset, None) == "Hi"
    assert resolve_user_text(preset, "Yo") == "Yo"
    with pytest.raises(PresetTextError, match="at most 4"):
        resolve_user_text(preset, "Hello")
    assert resolve_user_text({"text_input": "no"}, "ignored") == ""


def test_place_on_canvas_polaroid_has_larger_bottom() -> None:
    photo = Image.new("RGB", (100, 100), (10, 20, 30))
    framed = F.place_on_canvas(photo, scale=1.4, layout="polaroid", fill=(255, 255, 255))
    assert framed.size == (140, 140)
    # Top band matches side margin (~20); bottom leftover is larger.
    assert framed.getpixel((70, 10))[:3] == (255, 255, 255)
    assert framed.getpixel((70, 130))[:3] == (255, 255, 255)
    assert framed.getpixel((70, 50))[:3] == (10, 20, 30)


def test_bind_datetime_placeholder() -> None:
    from datetime import datetime

    from apply_preset import bind_placeholders

    fixed = datetime(2026, 9, 20, 18, 30)
    assert bind_placeholders("$datetime", text="", now=fixed) == "2026-09-20 18:30"
    assert bind_placeholders("$date", text="", now=fixed) == "2026-09-20"
    assert bind_placeholders("$time", text="", now=fixed) == "18:30"


def test_polaroid_memory_preset_file() -> None:
    data = load_preset(PRESETS / "polaroid_memory.json")
    assert data["ar"] == "square"
    assert data["text_input"] == "yes"
    assert data["default_text"] == "instant memory"
    assert data["text_character_limit"] == 24
    assert data["steps"][0]["filter"] == "contrast"
    assert any(s.get("filter") == "place_on_canvas" for s in data["steps"])
    assert any(s.get("text") == "$datetime" for s in data["steps"])
    assert any(s.get("text") == "$text" for s in data["steps"])


def test_apply_polaroid_memory_on_square(tmp_path: Path) -> None:
    from datetime import datetime

    from apply_preset import apply_steps

    data = load_preset(PRESETS / "polaroid_memory.json")
    square = Image.new("RGB", (80, 80), (120, 80, 40))
    out = apply_steps(
        square,
        data["steps"],
        text="instant memory",
        now=datetime(2026, 9, 20, 18, 30),
    )
    assert out.size == (112, 112)
