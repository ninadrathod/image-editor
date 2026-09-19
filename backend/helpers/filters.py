"""
Pillow filter ops used by the JSON preset step runner.
"""

from __future__ import annotations

from typing import Sequence

from PIL import Image, ImageEnhance, ImageFilter

from extract_subject import extract_subject as rembg_extract_subject


def _as_rgba(image: Image.Image) -> Image.Image:
    return image.convert("RGBA")


def _as_rgb(image: Image.Image) -> Image.Image:
    return image.convert("RGB")


def extract_subject_layers(image: Image.Image) -> tuple[Image.Image, Image.Image]:
    """
    Return (subject_rgba, background_rgb).

    Background replaces the subject region with a heavy blur so later filters
    don't double the original subject underneath the cutout.
    """
    original = _as_rgb(image)
    subject = rembg_extract_subject(original)
    mask = subject.getchannel("A")
    blurred = original.filter(ImageFilter.GaussianBlur(radius=40))
    background = Image.composite(blurred, original, mask)
    return subject, background


def brightness(image: Image.Image, amount: float = 1.0) -> Image.Image:
    base = _as_rgb(image)
    out = ImageEnhance.Brightness(base).enhance(float(amount))
    if image.mode == "RGBA":
        out = out.convert("RGBA")
        out.putalpha(image.getchannel("A"))
    return out


def color(image: Image.Image, amount: float = 1.0) -> Image.Image:
    base = _as_rgb(image)
    out = ImageEnhance.Color(base).enhance(float(amount))
    if image.mode == "RGBA":
        out = out.convert("RGBA")
        out.putalpha(image.getchannel("A"))
    return out


def contrast(image: Image.Image, amount: float = 1.0) -> Image.Image:
    base = _as_rgb(image)
    out = ImageEnhance.Contrast(base).enhance(float(amount))
    if image.mode == "RGBA":
        out = out.convert("RGBA")
        out.putalpha(image.getchannel("A"))
    return out


def overlay(
    image: Image.Image,
    rgb: Sequence[int] = (255, 200, 110),
    alpha: float = 0.2,
) -> Image.Image:
    base = _as_rgb(image)
    color_layer = Image.new("RGB", base.size, tuple(int(c) for c in rgb))
    out = Image.blend(base, color_layer, alpha=float(alpha))
    if image.mode == "RGBA":
        out = out.convert("RGBA")
        out.putalpha(image.getchannel("A"))
    return out


def grayscale(image: Image.Image) -> Image.Image:
    gray = _as_rgb(image).convert("L").convert("RGB")
    if image.mode == "RGBA":
        gray = gray.convert("RGBA")
        gray.putalpha(image.getchannel("A"))
    return gray


def glow_border(
    image: Image.Image,
    rgb: Sequence[int] = (0, 255, 200),
    width: int = 8,
    blur: float = 12.0,
) -> Image.Image:
    """Add a soft colored glow around an RGBA subject's alpha edge."""
    subject = _as_rgba(image)
    alpha = subject.getchannel("A")

    # MaxFilter size must be odd
    dilate = max(3, int(width) * 2 + 1)
    if dilate % 2 == 0:
        dilate += 1
    glow_mask = alpha.filter(ImageFilter.MaxFilter(size=dilate))
    glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(radius=float(blur)))

    glow = Image.new("RGBA", subject.size, (*tuple(int(c) for c in rgb), 0))
    glow.putalpha(glow_mask)
    return Image.alpha_composite(glow, subject)


def glow_line_border(
    image: Image.Image,
    color: Sequence[int] | None = None,
    rgb: Sequence[int] | None = None,
    width: int = 4,
    blur: float = 1.5,
) -> Image.Image:
    """
    Draw a glowing outline around the subject only (ring), without filling the body.

    Accepts `color` or `rgb` as [R, G, B].
    """
    from PIL import ImageChops

    subject = _as_rgba(image)
    tint = color if color is not None else rgb
    if tint is None:
        tint = (0, 255, 200)
    tint_rgb = tuple(int(c) for c in tint)

    alpha = subject.getchannel("A")
    dilate = max(3, int(width) * 2 + 1)
    if dilate % 2 == 0:
        dilate += 1

    # Outer silhouette minus subject fill → border ring only
    outer = alpha.filter(ImageFilter.MaxFilter(size=dilate))
    ring = ImageChops.subtract(outer, alpha)
    if float(blur) > 0:
        ring = ring.filter(ImageFilter.GaussianBlur(radius=float(blur)))

    line = Image.new("RGBA", subject.size, (*tint_rgb, 0))
    line.putalpha(ring)
    # Subject stays on top so its pixels are not tinted by the glow
    return Image.alpha_composite(line, subject)


def composite(base: Image.Image, overlay: Image.Image) -> Image.Image:
    """Paste overlay (with alpha) on top of base."""
    bottom = _as_rgba(base)
    top = _as_rgba(overlay)
    if top.size != bottom.size:
        top = top.resize(bottom.size, Image.Resampling.LANCZOS)
    return Image.alpha_composite(bottom, top)
