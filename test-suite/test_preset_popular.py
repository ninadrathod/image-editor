"""Unit tests for `app.services.preset_popular`."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.preset_popular import (
    MAX_PRESET_NAME_LEN,
    PresetUseNotFoundError,
    list_popular_presets,
    record_preset_use,
)
from database.db_ops import add_preset
from database.init_db import init_db


def test_record_preset_use_increments_and_lists_desc(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    init_db(db)
    add_preset("alpha", "backend/presets/a.json", db_path=db)
    add_preset("beta", "backend/presets/b.json", db_path=db)

    first = record_preset_use("beta", db_path=db)
    second = record_preset_use("beta", db_path=db)
    third = record_preset_use("alpha", db_path=db)

    assert first["used_count"] == 1
    assert second["used_count"] == 2
    assert third["used_count"] == 1
    assert second["preset_id"] == first["preset_id"]

    ranked = list_popular_presets(db_path=db)
    assert [row["used_count"] for row in ranked] == [2, 1]
    assert [row["preset_name"] for row in ranked] == ["beta", "alpha"]
    assert ranked[0]["preset_id"] == first["preset_id"]
    assert ranked[1]["preset_id"] == third["preset_id"]


def test_record_preset_use_rejects_empty_and_unknown(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    init_db(db)
    add_preset("alpha", "backend/presets/a.json", db_path=db)

    with pytest.raises(ValueError, match="preset_name is required"):
        record_preset_use("  ", db_path=db)

    with pytest.raises(ValueError, match="too long"):
        record_preset_use("a" * (MAX_PRESET_NAME_LEN + 1), db_path=db)

    with pytest.raises(PresetUseNotFoundError, match="Unknown preset"):
        record_preset_use("missing", db_path=db)
