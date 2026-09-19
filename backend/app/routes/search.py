"""
GET /api/presets/search — find presets by name or keyword substring.
"""

from fastapi import APIRouter, Query

from app.services.preset_search import search_presets

router = APIRouter(tags=["search"])


@router.get("/presets/search")
def search_presets_endpoint(
    q: str = Query(
        "",
        max_length=64,
        description="Substring to match against preset_name or keywords",
    ),
):
    """
    Search `preset_name` and `keywords` for a case-insensitive substring match.
    Returns a list of preset metadata rows (may be empty).
    """
    rows = search_presets(q)
    return [
        {
            "preset_name": row["preset_name"],
            "keywords": row["keywords"],
        }
        for row in rows
    ]
