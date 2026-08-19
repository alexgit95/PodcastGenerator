from __future__ import annotations

import uuid
from datetime import datetime
import json
from typing import Any

from .db import get_connection, row_to_dict


def list_categories() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, description, enabled, default_weight, created_at, updated_at
            FROM categories
            ORDER BY name ASC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_category(payload: dict[str, Any]) -> dict[str, Any]:
    category_id = str(uuid.uuid4())
    name = payload["name"].strip()
    description = (payload.get("description") or "").strip()
    enabled = 1 if payload.get("enabled", True) else 0
    default_weight = int(payload.get("default_weight", 1))

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO categories (id, name, description, enabled, default_weight)
            VALUES (?, ?, ?, ?, ?)
            """,
            (category_id, name, description, enabled, default_weight),
        )
        row = conn.execute(
            "SELECT id, name, description, enabled, default_weight, created_at, updated_at FROM categories WHERE id = ?",
            (category_id,),
        ).fetchone()
    return row_to_dict(row)


def update_category(category_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    fields: list[str] = []
    values: list[Any] = []

    if "name" in payload:
        fields.append("name = ?")
        values.append(payload["name"].strip())
    if "description" in payload:
        fields.append("description = ?")
        values.append((payload["description"] or "").strip())
    if "enabled" in payload:
        fields.append("enabled = ?")
        values.append(1 if payload["enabled"] else 0)
    if "default_weight" in payload:
        fields.append("default_weight = ?")
        values.append(int(payload["default_weight"]))

    if not fields:
        return get_category(category_id)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(category_id)
    query = f"UPDATE categories SET {', '.join(fields)} WHERE id = ?"

    with get_connection() as conn:
        cursor = conn.execute(query, values)
        if cursor.rowcount == 0:
            return None
    return get_category(category_id)


def delete_category(category_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    return cursor.rowcount > 0


def get_category(category_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, description, enabled, default_weight, created_at, updated_at FROM categories WHERE id = ?",
            (category_id,),
        ).fetchone()
    return row_to_dict(row) if row else None


def list_sources() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, url, title, enabled, health_status, health_message, last_checked_at, last_success_at, created_at, updated_at
            FROM rss_sources
            ORDER BY title ASC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_source(payload: dict[str, Any]) -> dict[str, Any]:
    source_id = str(uuid.uuid4())
    url = payload["url"].strip()
    title = payload.get("title", "").strip() or url
    enabled = 1 if payload.get("enabled", True) else 0

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO rss_sources (id, url, title, enabled)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, url, title, enabled),
        )
        row = conn.execute(
            """
            SELECT id, url, title, enabled, health_status, health_message, last_checked_at, last_success_at, created_at, updated_at
            FROM rss_sources WHERE id = ?
            """,
            (source_id,),
        ).fetchone()
    return row_to_dict(row)


def update_source(source_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    fields: list[str] = []
    values: list[Any] = []

    if "url" in payload:
        fields.append("url = ?")
        values.append(payload["url"].strip())
    if "title" in payload:
        fields.append("title = ?")
        values.append((payload["title"] or "").strip())
    if "enabled" in payload:
        fields.append("enabled = ?")
        values.append(1 if payload["enabled"] else 0)

    if not fields:
        return get_source(source_id)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(source_id)
    query = f"UPDATE rss_sources SET {', '.join(fields)} WHERE id = ?"

    with get_connection() as conn:
        cursor = conn.execute(query, values)
        if cursor.rowcount == 0:
            return None
    return get_source(source_id)


def update_source_health(
    source_id: str,
    *,
    health_status: str,
    health_message: str | None,
    successful: bool,
) -> dict[str, Any] | None:
    query = """
        UPDATE rss_sources
        SET health_status = ?, health_message = ?, last_checked_at = CURRENT_TIMESTAMP,
            last_success_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE last_success_at END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """
    with get_connection() as conn:
        cursor = conn.execute(query, (health_status, health_message, 1 if successful else 0, source_id))
        if cursor.rowcount == 0:
            return None
    return get_source(source_id)


def delete_source(source_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM rss_sources WHERE id = ?", (source_id,))
    return cursor.rowcount > 0


def get_source(source_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, url, title, enabled, health_status, health_message, last_checked_at, last_success_at, created_at, updated_at
            FROM rss_sources WHERE id = ?
            """,
            (source_id,),
        ).fetchone()
    return row_to_dict(row) if row else None


def list_mappings() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT cs.category_id, cs.source_id, c.name AS category_name, s.title AS source_title, s.url AS source_url
            FROM category_sources cs
            JOIN categories c ON c.id = cs.category_id
            JOIN rss_sources s ON s.id = cs.source_id
            ORDER BY c.name ASC, s.title ASC
            """
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_mapping(category_id: str, source_id: str) -> bool:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO category_sources (category_id, source_id) VALUES (?, ?)",
            (category_id, source_id),
        )
        exists = conn.execute(
            "SELECT 1 FROM category_sources WHERE category_id = ? AND source_id = ?",
            (category_id, source_id),
        ).fetchone()
    return bool(exists)


def delete_mapping(category_id: str, source_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM category_sources WHERE category_id = ? AND source_id = ?",
            (category_id, source_id),
        )
    return cursor.rowcount > 0


def get_or_create_default_profile() -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, enabled, duration_target_minutes, max_item_age_hours,
                   per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone,
                   created_at, updated_at
            FROM generation_profiles
            ORDER BY created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if row:
            return row_to_dict(row)

        profile_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO generation_profiles (
                id, name, enabled, duration_target_minutes, max_item_age_hours,
                per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone
            ) VALUES (?, 'default', 1, 10, 48, 28000, 100, '0 8 * * 1,3,5', 'Europe/Paris')
            """,
            (profile_id,),
        )
        row = conn.execute(
            """
            SELECT id, name, enabled, duration_target_minutes, max_item_age_hours,
                   per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone,
                   created_at, updated_at
            FROM generation_profiles WHERE id = ?
            """,
            (profile_id,),
        ).fetchone()
    return row_to_dict(row)


def update_default_profile_duration(duration_target_minutes: int) -> dict[str, Any]:
    profile = get_or_create_default_profile()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE generation_profiles
            SET duration_target_minutes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (duration_target_minutes, profile["id"]),
        )
        row = conn.execute(
            """
            SELECT id, name, enabled, duration_target_minutes, max_item_age_hours,
                   per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone,
                   created_at, updated_at
            FROM generation_profiles WHERE id = ?
            """,
            (profile["id"],),
        ).fetchone()
    return row_to_dict(row)


def list_category_source_bindings(category_ids: list[str] | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT c.id AS category_id,
               c.name AS category_name,
               c.default_weight,
               s.id AS source_id,
               s.title AS source_title,
               s.url AS source_url,
               s.enabled AS source_enabled,
               c.enabled AS category_enabled
        FROM categories c
        JOIN category_sources cs ON cs.category_id = c.id
        JOIN rss_sources s ON s.id = cs.source_id
        WHERE c.enabled = 1 AND s.enabled = 1
    """
    args: list[Any] = []
    if category_ids:
        placeholders = ",".join(["?"] * len(category_ids))
        query += f" AND c.id IN ({placeholders})"
        args.extend(category_ids)
    query += " ORDER BY c.name ASC, s.title ASC"

    with get_connection() as conn:
        rows = conn.execute(query, args).fetchall()
    return [row_to_dict(row) for row in rows]


def current_month_key() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def get_monthly_spend(profile_id: str, month_key: str | None = None) -> dict[str, Any] | None:
    resolved_month_key = month_key or current_month_key()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, profile_id, month_key, spent_eur_cents, hard_cap_eur_cents, updated_at
            FROM monthly_api_spend
            WHERE profile_id = ? AND month_key = ?
            """,
            (profile_id, resolved_month_key),
        ).fetchone()
    return row_to_dict(row) if row else None


def add_monthly_spend(profile_id: str, amount_eur_cents: int, hard_cap_eur_cents: int) -> dict[str, Any]:
    if amount_eur_cents < 0:
        raise ValueError("amount_eur_cents must be >= 0")
    month_key = current_month_key()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO monthly_api_spend (profile_id, month_key, spent_eur_cents, hard_cap_eur_cents)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(profile_id, month_key)
            DO UPDATE SET
                spent_eur_cents = monthly_api_spend.spent_eur_cents + excluded.spent_eur_cents,
                hard_cap_eur_cents = excluded.hard_cap_eur_cents,
                updated_at = CURRENT_TIMESTAMP
            """,
            (profile_id, month_key, amount_eur_cents, hard_cap_eur_cents),
        )
        row = conn.execute(
            """
            SELECT id, profile_id, month_key, spent_eur_cents, hard_cap_eur_cents, updated_at
            FROM monthly_api_spend
            WHERE profile_id = ? AND month_key = ?
            """,
            (profile_id, month_key),
        ).fetchone()
    return row_to_dict(row)


def update_default_profile_schedule(schedule_cron: str, timezone: str) -> dict[str, Any]:
    profile = get_or_create_default_profile()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE generation_profiles
            SET schedule_cron = ?, timezone = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (schedule_cron, timezone, profile["id"]),
        )
        row = conn.execute(
            """
            SELECT id, name, enabled, duration_target_minutes, max_item_age_hours,
                   per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone,
                   created_at, updated_at
            FROM generation_profiles WHERE id = ?
            """,
            (profile["id"],),
        ).fetchone()
    return row_to_dict(row)


def create_generation_job(profile_id: str, job_type: str, status: str, details: dict[str, Any] | None = None) -> str:
    job_id = str(uuid.uuid4())
    details_json = json.dumps(details or {}, ensure_ascii=True)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO generation_jobs (id, profile_id, job_type, status, details_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, profile_id, job_type, status, details_json),
        )
    return job_id


def update_generation_job(job_id: str, status: str, details: dict[str, Any] | None = None) -> bool:
    details_json = json.dumps(details or {}, ensure_ascii=True)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE generation_jobs
            SET status = ?, details_json = ?, finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, details_json, job_id),
        )
    return cursor.rowcount > 0


def list_recent_generation_jobs(limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, profile_id, job_type, status, started_at, finished_at, details_json
            FROM generation_jobs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (max(1, min(100, limit)),),
        ).fetchall()

    parsed: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row)
        try:
            item["details"] = json.loads(item.get("details_json") or "{}")
        except json.JSONDecodeError:
            item["details"] = {}
        parsed.append(item)
    return parsed
