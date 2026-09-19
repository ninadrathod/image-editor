"""Unit tests for `app.services.image_io` (service functions only)."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.services.image_io import load_image, save_png_bytes


def _png_bytes(size: tuple[int, int] = (10, 10), color=(1, 2, 3)) -> bytes:
    image = Image.new("RGB", size, color=color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_load_image_decodes_png_bytes() -> None:
    raw = _png_bytes((12, 8), color=(40, 50, 60))
    image = load_image(raw)
    assert image.size == (12, 8)
    assert image.getpixel((0, 0)) == (40, 50, 60)


def test_load_image_rejects_invalid_bytes() -> None:
    with pytest.raises(Exception):
        load_image(b"not-an-image")


def test_save_png_bytes_writes_png_signature() -> None:
    image = Image.new("RGB", (4, 4), color=(9, 8, 7))
    raw = save_png_bytes(image)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_save_png_bytes_round_trips_with_load_image() -> None:
    original = Image.new("RGB", (6, 5), color=(100, 110, 120))
    encoded = save_png_bytes(original)
    reloaded = load_image(encoded)
    assert reloaded.size == original.size
    assert reloaded.getpixel((0, 0)) == (100, 110, 120)
