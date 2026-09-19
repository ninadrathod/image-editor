"""Unit tests for `app.services.image_io` (service functions only)."""

from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from PIL import Image

from app.services.image_io import (
    MAX_IMAGE_SIDE,
    MAX_UPLOAD_BYTES,
    ImageTooLargeError,
    ensure_image_limits,
    load_image,
    read_upload_capped,
    save_png_bytes,
)


def _png_bytes(size: tuple[int, int] = (10, 10), color=(1, 2, 3)) -> bytes:
    image = Image.new("RGB", size, color=color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeUpload:
    def __init__(self, data: bytes, chunk_size: int = 64 * 1024) -> None:
        self._buf = BytesIO(data)
        self._chunk_size = chunk_size

    async def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self._chunk_size
        return self._buf.read(size)


def test_load_image_decodes_png_bytes() -> None:
    raw = _png_bytes((12, 8), color=(40, 50, 60))
    image = load_image(raw)
    assert image.size == (12, 8)
    assert image.getpixel((0, 0)) == (40, 50, 60)


def test_load_image_rejects_invalid_bytes() -> None:
    with pytest.raises(Exception):
        load_image(b"not-an-image")


def test_load_image_rejects_oversized_dimensions() -> None:
    image = Image.new("RGB", (16, 16), color=(1, 2, 3))
    with pytest.raises(ImageTooLargeError):
        ensure_image_limits(image, max_side=8)


def test_ensure_image_limits_rejects_pixel_count() -> None:
    image = Image.new("RGB", (10, 10), color=(1, 2, 3))
    with pytest.raises(ImageTooLargeError):
        ensure_image_limits(image, max_side=MAX_IMAGE_SIDE, max_pixels=50)


def test_read_upload_capped_returns_bytes() -> None:
    raw = b"abc123"

    async def _run() -> bytes:
        return await read_upload_capped(_FakeUpload(raw), max_bytes=100)

    assert asyncio.run(_run()) == raw


def test_read_upload_capped_rejects_oversize() -> None:
    raw = b"x" * 100

    async def _run() -> bytes:
        return await read_upload_capped(_FakeUpload(raw, chunk_size=16), max_bytes=50)

    with pytest.raises(ImageTooLargeError):
        asyncio.run(_run())


def test_max_upload_constant_is_positive() -> None:
    assert MAX_UPLOAD_BYTES >= 1_000_000


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
