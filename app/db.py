from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "data" / "podcast.db"
SCHEMA_PATH = ROOT_DIR / "database" / "schema.sql"


DETERMINISTIC_SCORING_WEIGHTS = '{"freshness":0.45,"sourceCredibility":0.30,"textRichness":0.15,"diversity":0.10}'
DETERMINISTIC_EXTRACTIVE_RULES = '{"maxSentencesPerItem":2,"minSentenceChars":40,"maxSentenceChars":220,"stripQuotesIfLong":true}'
DETERMINISTIC_TRIM_POLICY = '{"order":["conclusion","transitions","lowestPriorityItem"],"stepSec":15,"hardFloorSec":540}'
DETERMINISTIC_FALLBACK_POLICY = '{"ifTooShortAdd":["whyItMatters","watchNext"],"ifNoItems":"skipCategoryAndRebalance"}'


def _table_has_column(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _ensure_schema_migrations(connection: sqlite3.Connection) -> None:
    if not _table_has_column(connection, "generation_profiles", "generation_mode"):
        connection.execute(
            "ALTER TABLE generation_profiles ADD COLUMN generation_mode TEXT NOT NULL DEFAULT 'llm'"
        )
    if not _table_has_column(connection, "generation_profiles", "generation_mode"):
        raise RuntimeError("Failed to create generation_mode column")

    if not _table_has_column(connection, "generation_profiles", "audio_generation_mode"):
        connection.execute(
            "ALTER TABLE generation_profiles ADD COLUMN audio_generation_mode TEXT NOT NULL DEFAULT 'local'"
        )
    if not _table_has_column(connection, "generation_profiles", "audio_generation_mode"):
        raise RuntimeError("Failed to create audio_generation_mode column")

    connection.execute(
        "UPDATE generation_profiles SET audio_generation_mode = 'local' WHERE audio_generation_mode IS NULL OR audio_generation_mode = ''"
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS deterministic_settings_global (
          profile_id TEXT PRIMARY KEY,
          version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
          target_duration_sec INTEGER NOT NULL DEFAULT 600 CHECK (target_duration_sec BETWEEN 120 AND 3600),
          speech_rate_wpm INTEGER NOT NULL DEFAULT 155 CHECK (speech_rate_wpm BETWEEN 100 AND 220),
          freshness_hours_max INTEGER NOT NULL DEFAULT 48 CHECK (freshness_hours_max > 0),
          max_items_per_category_default INTEGER NOT NULL DEFAULT 3 CHECK (max_items_per_category_default BETWEEN 1 AND 10),
          min_items_per_category_default INTEGER NOT NULL DEFAULT 1 CHECK (min_items_per_category_default BETWEEN 1 AND 10),
          scoring_weights_json TEXT NOT NULL,
          extractive_rules_json TEXT NOT NULL,
          trim_policy_json TEXT NOT NULL,
          fallback_policy_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS deterministic_settings_category (
          profile_id TEXT NOT NULL,
          category_id TEXT NOT NULL,
          enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
          weight INTEGER NOT NULL DEFAULT 1 CHECK (weight > 0),
          max_items INTEGER CHECK (max_items IS NULL OR (max_items BETWEEN 1 AND 10)),
          templates_json TEXT,
          scoring_override_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (profile_id, category_id),
          FOREIGN KEY (profile_id) REFERENCES generation_profiles(id) ON DELETE CASCADE,
          FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
        """
    )

    profile_rows = connection.execute("SELECT id FROM generation_profiles").fetchall()
    for row in profile_rows:
        profile_id = row[0]
        connection.execute(
            """
            INSERT OR IGNORE INTO deterministic_settings_global (
              profile_id,
              version,
              target_duration_sec,
              speech_rate_wpm,
              freshness_hours_max,
              max_items_per_category_default,
              min_items_per_category_default,
              scoring_weights_json,
              extractive_rules_json,
              trim_policy_json,
              fallback_policy_json
            ) VALUES (?, 1, 600, 155, 48, 3, 1, ?, ?, ?, ?)
            """,
            (
                profile_id,
                DETERMINISTIC_SCORING_WEIGHTS,
                DETERMINISTIC_EXTRACTIVE_RULES,
                DETERMINISTIC_TRIM_POLICY,
                DETERMINISTIC_FALLBACK_POLICY,
            ),
        )

    category_rows = connection.execute("SELECT id FROM categories").fetchall()
    for profile_row in profile_rows:
        profile_id = profile_row[0]
        for category_row in category_rows:
            category_id = category_row[0]
            connection.execute(
                """
                INSERT OR IGNORE INTO deterministic_settings_category (
                  profile_id,
                  category_id,
                  enabled,
                  weight,
                  max_items,
                  templates_json,
                  scoring_override_json
                ) VALUES (?, ?, 1, 1, NULL, NULL, NULL)
                """,
                (profile_id, category_id),
            )


def ensure_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema_sql)
        _ensure_schema_migrations(connection)
        connection.commit()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}
