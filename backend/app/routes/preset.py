"""
POST /api/apply-preset — apply a DB-named preset to an uploaded image.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

from app.services.blur import is_allowed_image
from app.services.image_io import (
    ImageTooLargeError,
    load_image,
    read_upload_capped,
    save_png_bytes,
)
from app.services.preset import (
    PresetAspectRatioError,
    PresetBusyError,
    PresetFileMissingError,
    PresetNotFoundError,
    PresetPathUnsafeError,
    run_preset_job,
)

router = APIRouter(tags=["preset"])


@router.post("/apply-preset")
async def apply_preset_endpoint(
    preset_name: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Accept a preset name (presets.preset_name) and image upload; return PNG bytes.
    """
    name = (preset_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="preset_name is required.")

    if not file.content_type or not is_allowed_image(file.content_type, file.filename):
        raise HTTPException(
            status_code=400,
            detail="File must be an image (JPEG, PNG, WEBP, GIF, BMP, or TIFF).",
        )

    try:
        raw = await read_upload_capped(file)
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        image = load_image(raw)
        result = await run_preset_job(image, name)
        png_bytes = save_png_bytes(result)
    except PresetBusyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PresetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PresetFileMissingError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PresetPathUnsafeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PresetAspectRatioError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except Image.DecompressionBombError as exc:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds maximum allowed pixel count.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not apply preset: {exc}",
        ) from exc

    return Response(content=png_bytes, media_type="image/png")
