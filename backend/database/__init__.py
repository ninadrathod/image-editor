"""File-based SQLite store for The Local Studio preset metadata."""

from .db_ops import (
    add_preset,
    delete_preset,
    get_preset_by_id,
    get_preset_by_name,
    increment_used_count,
    increment_used_count_by_name,
    list_popular,
    list_presets,
    search_presets_by_keyword,
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
    "increment_used_count",
    "increment_used_count_by_name",
    "init_db",
    "list_popular",
    "list_presets",
    "search_presets_by_keyword",
    "seed_default_presets",
    "update_preset",
]
