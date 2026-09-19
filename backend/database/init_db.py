"""Initialize the presets SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATABASE_DIR = Path(__file__).resolve().parent
DB_PATH = DATABASE_DIR / "presets.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"


def init_db(db_path: Path = DB_PATH) -> Path:
    """Create the database file and apply schema.sql. Returns the db path."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
        conn.commit()

    return db_path


if __name__ == "__main__":
    path = init_db()
    print(f"Database ready: {path}")
