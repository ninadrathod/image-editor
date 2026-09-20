"""Initialize the presets SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATABASE_DIR = Path(__file__).resolve().parent
DB_PATH = DATABASE_DIR / "presets.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the original schema (existing DBs)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(presets)").fetchall()}
    if not cols:
        return
    if "ar" not in cols:
        conn.execute(
            "ALTER TABLE presets ADD COLUMN ar TEXT NOT NULL DEFAULT 'non-square'"
        )
    if "text_input" not in cols:
        conn.execute(
            "ALTER TABLE presets ADD COLUMN text_input TEXT NOT NULL DEFAULT 'no'"
        )
    if "default_text" not in cols:
        conn.execute(
            "ALTER TABLE presets ADD COLUMN default_text TEXT NOT NULL DEFAULT ''"
        )
    if "text_character_limit" not in cols:
        conn.execute(
            "ALTER TABLE presets ADD COLUMN text_character_limit "
            "INTEGER NOT NULL DEFAULT 0"
        )


def init_db(db_path: Path = DB_PATH) -> Path:
    """Create the database file and apply schema.sql. Returns the db path."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
        migrate_schema(conn)
        conn.commit()

    return db_path


if __name__ == "__main__":
    path = init_db()
    print(f"Database ready: {path}")
