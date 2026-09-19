"""File-based SQLite store for image-editor preset metadata."""

from .db_ops import (
    add_preset,
    delete_preset,
    get_preset_by_id,
    get_preset_by_name,
    list_presets,
    seed_default_presets,
    update_preset,
)
from .init_db import DB_PATH, init_db

__all__ = [
    "DB_PATH",
    "add_preset",
    "delete_preset",
    "get_preset_by_id",
    "get_preset_by_name",
    "init_db",
    "list_presets",
    "seed_default_presets",
    "update_preset",
]
