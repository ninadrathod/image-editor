"""
POST /api/blur — accept an image upload and return a blurred PNG.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.blur import apply_blur, is_allowed_image
from app.services.image_io import load_image, save_png_bytes

router = APIRouter(tags=["blur"])


@router.post("/blur")
async def blur_endpoint(file: UploadFile = File(...)):
    """
    Accept a multipart image upload, blur it, and return PNG bytes.
    """
    if not file.content_type or not is_allowed_image(file.content_type, file.filename):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPEG, PNG, WEBP, GIF, BMP, or TIFF).",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        image = load_image(raw)
        blurred = apply_blur(image)
        png_bytes = save_png_bytes(blurred)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process image: {exc}") from exc

    return Response(content=png_bytes, media_type="image/png")
