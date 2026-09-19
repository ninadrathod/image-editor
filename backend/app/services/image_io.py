"""
Load and encode images with Pillow.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

# Caps for untrusted HTTP uploads (apply-preset / blur).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MiB
MAX_IMAGE_SIDE = 8000
MAX_IMAGE_PIXELS = 25_000_000  # e.g. ~5000×5000

# Apply once so decode rejects oversized images without per-request global mutation.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class ImageTooLargeError(ValueError):
    """Raised when upload bytes or decoded dimensions exceed configured limits."""


async def read_upload_capped(
    file: Any,
    *,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> bytes:
    """Read an upload in chunks; reject once size exceeds `max_bytes`."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ImageTooLargeError(
                f"Upload exceeds maximum size of {max_bytes} bytes."
            )
        chunks.append(chunk)
    return b"".join(chunks)


def ensure_image_limits(
    image: Image.Image,
    *,
    max_side: int = MAX_IMAGE_SIDE,
    max_pixels: int = MAX_IMAGE_PIXELS,
) -> Image.Image:
    """Reject images that are too wide/tall or have too many pixels."""
    width, height = image.size
    if width > max_side or height > max_side:
        raise ImageTooLargeError(
            f"Image dimensions {width}×{height} exceed maximum side length {max_side}."
        )
    if width * height > max_pixels:
        raise ImageTooLargeError(
            f"Image has {width * height} pixels; maximum is {max_pixels}."
        )
    return image


def load_image(
    raw: bytes,
    *,
    max_side: int = MAX_IMAGE_SIDE,
    max_pixels: int = MAX_IMAGE_PIXELS,
) -> Image.Image:
    """Decode image bytes into a Pillow Image (fully loaded into memory)."""
    image = Image.open(BytesIO(raw))
    image.load()
    return ensure_image_limits(image, max_side=max_side, max_pixels=max_pixels)


def save_png_bytes(image: Image.Image) -> bytes:
    """Encode an image as PNG bytes."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
