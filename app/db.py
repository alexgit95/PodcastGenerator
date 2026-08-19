from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "podcast.db"
SCHEMA_PATH = ROOT_DIR / "database" / "schema.sql"


def ensure_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema_sql)
        connection.commit()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}
