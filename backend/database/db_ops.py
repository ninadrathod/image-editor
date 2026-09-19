"""
CRUD helpers for the presets table in presets.db.

Keywords are stored as a JSON array string in SQLite and returned as list[str].
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

try:
    from .init_db import DB_PATH, init_db
except ImportError:  # running as a script inside backend/database/
    from init_db import DB_PATH, init_db

TABLE_NAME = "presets"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open a connection; create the DB/schema if missing."""
    if not db_path.is_file():
        init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _keywords_to_json(keywords: list[str] | None) -> str:
    cleaned: list[str] = []
    for item in keywords or []:
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return json.dumps(cleaned, ensure_ascii=False)


def _keywords_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item).strip() for item in data if str(item).strip()]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "preset_id": row["preset_id"],
        "preset_name": row["preset_name"],
        "preset_path": row["preset_path"],
        "keywords": _keywords_from_json(row["keywords"]),
        "created_date": row["created_date"],
    }


def add_preset(
    preset_name: str,
    preset_path: str,
    keywords: list[str] | None = None,
    *,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    """Insert a preset row. created_date is set by SQLite. Returns the new row."""
    name = preset_name.strip()
    path = preset_path.strip()
    if not name:
        raise ValueError("preset_name is required")
    if not path:
        raise ValueError("preset_path is required")

    with get_connection(db_path) as conn:
        cur = conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (preset_name, preset_path, keywords)
            VALUES (?, ?, ?)
            """,
            (name, path, _keywords_to_json(keywords)),
        )
        conn.commit()
        preset_id = int(cur.lastrowid)

    row = get_preset_by_id(preset_id, db_path=db_path)
    if row is None:
        raise RuntimeError("Insert succeeded but row could not be read back")
    return row


def get_preset_by_id(preset_id: int, *, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE preset_id = ?",
            (preset_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_preset_by_name(preset_name: str, *, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE preset_name = ?",
            (preset_name.strip(),),
        ).fetchone()
    return _row_to_dict(row) if row else None


def list_presets(*, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM {TABLE_NAME} ORDER BY preset_id ASC"
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def search_presets_by_keyword(
    query: str,
    *,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """
    Return presets whose `preset_name` or keywords contain `query`
    (case-insensitive substring). Empty/whitespace query returns [].
    """
    needle = (query or "").strip().lower()
    if not needle:
        return []

    matches: list[dict[str, Any]] = []
    for row in list_presets(db_path=db_path):
        name = str(row.get("preset_name") or "").lower()
        name_spaced = name.replace("_", " ")
        keywords = row.get("keywords") or []
        if (
            needle in name
            or needle in name_spaced
            or any(needle in str(kw).lower() for kw in keywords)
        ):
            matches.append(row)
    return matches


def update_preset(
    preset_id: int,
    *,
    preset_name: str | None = None,
    preset_path: str | None = None,
    keywords: list[str] | None = None,
    db_path: Path = DB_PATH,
) -> dict[str, Any] | None:
    """Partial update. Returns the updated row, or None if missing."""
    fields: list[str] = []
    values: list[Any] = []

    if preset_name is not None:
        name = preset_name.strip()
        if not name:
            raise ValueError("preset_name cannot be empty")
        fields.append("preset_name = ?")
        values.append(name)
    if preset_path is not None:
        path = preset_path.strip()
        if not path:
            raise ValueError("preset_path cannot be empty")
        fields.append("preset_path = ?")
        values.append(path)
    if keywords is not None:
        fields.append("keywords = ?")
        values.append(_keywords_to_json(keywords))

    if not fields:
        return get_preset_by_id(preset_id, db_path=db_path)

    values.append(preset_id)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            f"UPDATE {TABLE_NAME} SET {', '.join(fields)} WHERE preset_id = ?",
            values,
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    return get_preset_by_id(preset_id, db_path=db_path)


def delete_preset(preset_id: int, *, db_path: Path = DB_PATH) -> bool:
    """Delete by id. Returns True if a row was removed."""
    with get_connection(db_path) as conn:
        cur = conn.execute(
            f"DELETE FROM {TABLE_NAME} WHERE preset_id = ?",
            (preset_id,),
        )
        conn.commit()
        return cur.rowcount > 0


def seed_default_presets(*, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Insert known shipped presets if they are not already present."""
    defaults = [
        {
            "preset_name": "bw_bg_glowing_subject",
            "preset_path": "backend/presets/bw_bg_glowing_subject.json",
            "keywords": [
                "grayscale",
                "black and white",
                "glow",
                "outline",
                "subject",
                "border",
            ],
        },
    ]
    created: list[dict[str, Any]] = []
    for item in defaults:
        existing = get_preset_by_name(item["preset_name"], db_path=db_path)
        if existing is None:
            created.append(
                add_preset(
                    item["preset_name"],
                    item["preset_path"],
                    item["keywords"],
                    db_path=db_path,
                )
            )
    return created
