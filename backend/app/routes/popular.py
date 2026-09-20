"""
POST /api/presets/use — increment popular.used_count for a downloaded preset.
GET  /api/presets/popular — list popular rows (used_count descending).
"""

from fastapi import APIRouter, Form, HTTPException

from app.services.preset_popular import (
    PresetUseNotFoundError,
    list_popular_presets,
    record_preset_use,
)

router = APIRouter(tags=["popular"])


@router.post("/presets/use")
def record_preset_use_endpoint(
    preset_name: str = Form(..., min_length=1, max_length=64),
):
    """Increment used_count for the given preset_name (download click)."""
    try:
        row = record_preset_use(preset_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PresetUseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"preset_id": row["preset_id"], "used_count": row["used_count"]}


@router.get("/presets/popular")
def list_popular_endpoint():
    """Return popular rows ordered by used_count descending."""
    return list_popular_presets()
