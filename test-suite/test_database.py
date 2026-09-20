"""Unit tests for backend/database preset metadata (SQLite)."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database.db_ops import (  # noqa: E402
    add_preset,
    delete_preset,
    get_preset_by_id,
    get_preset_by_name,
    list_presets,
    search_presets_by_keyword,
    seed_default_presets,
    update_preset,
)
from database.init_db import init_db  # noqa: E402


def test_init_and_crud(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    init_db(db)

    row = add_preset(
        "demo",
        "backend/presets/demo.json",
        ["glow", "subject"],
        db_path=db,
    )
    assert row["preset_id"] == 1
    assert row["preset_name"] == "demo"
    assert row["preset_path"] == "backend/presets/demo.json"
    assert row["keywords"] == ["glow", "subject"]
    assert row["ar"] == "non-square"
    assert row["created_date"]

    by_id = get_preset_by_id(1, db_path=db)
    assert by_id is not None
    assert by_id["preset_name"] == "demo"

    by_name = get_preset_by_name("demo", db_path=db)
    assert by_name is not None
    assert by_name["preset_id"] == 1

    updated = update_preset(1, keywords=["outline", "bw"], db_path=db)
    assert updated is not None
    assert updated["keywords"] == ["outline", "bw"]

    square = update_preset(1, ar="square", db_path=db)
    assert square is not None
    assert square["ar"] == "square"

    assert list_presets(db_path=db)[0]["preset_name"] == "demo"
    assert delete_preset(1, db_path=db) is True
    assert get_preset_by_id(1, db_path=db) is None


def test_seed_default_presets_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    init_db(db)
    first = seed_default_presets(db_path=db)
    second = seed_default_presets(db_path=db)
    assert len(first) == 1
    assert first[0]["preset_name"] == "bw_bg_glowing_subject"
    assert first[0]["ar"] == "non-square"
    assert second == []
    assert len(list_presets(db_path=db)) == 1


def test_search_presets_by_keyword(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    init_db(db)
    add_preset("glow_look", "backend/presets/a.json", ["glow", "outline"], db_path=db)
    add_preset("warm_look", "backend/presets/b.json", ["warm", "sunset"], db_path=db)

    assert search_presets_by_keyword("", db_path=db) == []
    assert search_presets_by_keyword("   ", db_path=db) == []

    glow = search_presets_by_keyword("GLOW", db_path=db)
    assert len(glow) == 1
    assert glow[0]["preset_name"] == "glow_look"

    partial = search_presets_by_keyword("out", db_path=db)
    assert [r["preset_name"] for r in partial] == ["glow_look"]

    by_name = search_presets_by_keyword("warm_look", db_path=db)
    assert [r["preset_name"] for r in by_name] == ["warm_look"]

    by_name_spaced = search_presets_by_keyword("warm look", db_path=db)
    assert [r["preset_name"] for r in by_name_spaced] == ["warm_look"]

    assert search_presets_by_keyword("missing", db_path=db) == []


def test_add_preset_stores_ar_and_rejects_invalid(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    init_db(db)

    square = add_preset(
        "square_look",
        "backend/presets/square.json",
        ar="square",
        db_path=db,
    )
    assert square["ar"] == "square"

    try:
        add_preset("bad", "backend/presets/bad.json", ar="wide", db_path=db)
    except ValueError as exc:
        assert "ar must be" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid ar")


def test_migrate_adds_ar_column_to_existing_db(tmp_path: Path) -> None:
    db = tmp_path / "presets.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            """
            CREATE TABLE presets (
                preset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                preset_name TEXT NOT NULL UNIQUE,
                preset_path TEXT NOT NULL UNIQUE,
                keywords TEXT NOT NULL DEFAULT '[]',
                created_date TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "INSERT INTO presets (preset_name, preset_path, keywords) "
            "VALUES ('legacy', 'backend/presets/legacy.json', '[]')"
        )
        conn.commit()

    init_db(db)
    row = get_preset_by_name("legacy", db_path=db)
    assert row is not None
    assert row["ar"] == "non-square"
