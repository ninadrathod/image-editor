"""
Load and encode images with Pillow.
"""

from io import BytesIO

from PIL import Image


def load_image(raw: bytes) -> Image.Image:
    """Decode image bytes into a Pillow Image (fully loaded into memory)."""
    image = Image.open(BytesIO(raw))
    image.load()
    return image


def save_png_bytes(image: Image.Image) -> bytes:
    """Encode an image as PNG bytes."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
