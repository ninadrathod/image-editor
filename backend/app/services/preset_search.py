"""
Search preset metadata by name or keyword (SQLite `presets` table).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from database.db_ops import search_presets_by_keyword
from database.init_db import DB_PATH

# Cap query length to keep search cheap and predictable.
MAX_SEARCH_QUERY_LEN = 64


def search_presets(
    query: str,
    *,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Return preset rows whose name or keywords contain `query` (case-insensitive).
    Empty query → []. Excessively long queries are truncated.
    Matches keep newest-first `list_presets` order.
    """
    text = (query or "").strip()
    if not text:
        return []
    if len(text) > MAX_SEARCH_QUERY_LEN:
        text = text[:MAX_SEARCH_QUERY_LEN]

    path = DB_PATH if db_path is None else db_path
    return search_presets_by_keyword(text, db_path=path)
