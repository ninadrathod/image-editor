"""Unit tests for `app.services.preset_search`."""

from __future__ import annotations

from pathlib import Path

from app.services.preset_search import MAX_SEARCH_QUERY_LEN, search_presets
from database.db_ops import add_preset
from database.init_db import init_db


def test_search_presets_empty_and_match(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    init_db(db)
    add_preset("alpha", "backend/presets/a.json", ["glow", "bw"], db_path=db)
    add_preset("beta", "backend/presets/b.json", ["warm"], db_path=db)

    assert search_presets("", db_path=db) == []
    assert search_presets("  ", db_path=db) == []

    hits = search_presets("glow", db_path=db)
    assert len(hits) == 1
    assert hits[0]["preset_name"] == "alpha"

    by_name = search_presets("beta", db_path=db)
    assert len(by_name) == 1
    assert by_name[0]["preset_name"] == "beta"


def test_search_presets_truncates_long_query(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    init_db(db)
    prefix = "a" * MAX_SEARCH_QUERY_LEN
    add_preset("long_kw", "backend/presets/a.json", [prefix], db_path=db)

    # Oversized needle is truncated to `prefix`, which still matches.
    hits = search_presets(prefix + ("b" * 10), db_path=db)
    assert len(hits) == 1
    assert hits[0]["preset_name"] == "long_kw"
