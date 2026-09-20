"""
Record and list preset download/use counts (`popular` table).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from database.db_ops import increment_used_count_by_name, list_popular
from database.init_db import DB_PATH

MAX_PRESET_NAME_LEN = 64


class PresetUseNotFoundError(LookupError):
    """Raised when increment targets an unknown preset_name."""


def record_preset_use(
    preset_name: str,
    *,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """
    Increment `used_count` for the named preset.
    Empty name → ValueError. Unknown name → PresetUseNotFoundError.
    """
    name = (preset_name or "").strip()
    if not name:
        raise ValueError("preset_name is required")
    if len(name) > MAX_PRESET_NAME_LEN:
        raise ValueError("preset_name is too long")

    path = DB_PATH if db_path is None else db_path
    row = increment_used_count_by_name(name, db_path=path)
    if row is None:
        raise PresetUseNotFoundError(f"Unknown preset: {name}")
    return row


def list_popular_presets(*, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Return popular rows sorted by used_count descending."""
    path = DB_PATH if db_path is None else db_path
    return list_popular(db_path=path)
