from __future__ import annotations

import uuid
from datetime import datetime
import json
from typing import Any

from .db import get_connection, row_to_dict


DETERMINISTIC_SCORING_WEIGHTS = {"freshness": 0.45, "sourceCredibility": 0.30, "textRichness": 0.15, "diversity": 0.10}
DETERMINISTIC_EXTRACTIVE_RULES = {
    "maxSentencesPerItem": 2,
    "minSentenceChars": 40,
    "maxSentenceChars": 220,
    "stripQuotesIfLong": True,
    "briefSecondsTarget": 45,
    "durationAlignmentEnabled": False,
}
DETERMINISTIC_TRIM_POLICY = {
    "order": ["conclusion", "transitions", "lowestPriorityItem"],
    "stepSec": 15,
    "hardFloorSec": 540,
}
DETERMINISTIC_FALLBACK_POLICY = {
    "ifTooShortAdd": ["whyItMatters", "watchNext"],
    "ifNoItems": "skipCategoryAndRebalance",
}


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def _seed_deterministic_category_default(conn, profile_id: str, category_id: str) -> None:
    conn.execute(
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


def _ensure_profile_default_deterministic_settings(conn, profile_id: str) -> None:
    conn.execute(
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
            _json_text(DETERMINISTIC_SCORING_WEIGHTS),
            _json_text(DETERMINISTIC_EXTRACTIVE_RULES),
            _json_text(DETERMINISTIC_TRIM_POLICY),
            _json_text(DETERMINISTIC_FALLBACK_POLICY),
        ),
    )


def _parse_json_field(raw_value: Any, default: Any) -> Any:
    if raw_value is None:
        return default
    if isinstance(raw_value, (dict, list)):
        return raw_value
    text = str(raw_value).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


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
        profile_rows = conn.execute("SELECT id FROM generation_profiles").fetchall()
        for profile_row in profile_rows:
            _seed_deterministic_category_default(conn, profile_row[0], category_id)
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
            SELECT id, name, enabled, generation_mode, audio_generation_mode, duration_target_minutes, max_item_age_hours,
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
                id, name, enabled, generation_mode, audio_generation_mode, duration_target_minutes, max_item_age_hours,
                per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone
            ) VALUES (?, 'default', 1, 'llm', 'local', 10, 48, 28000, 100, '0 8 * * 1,3,5', 'Europe/Paris')
            """,
            (profile_id,),
        )
        _ensure_profile_default_deterministic_settings(conn, profile_id)
        category_rows = conn.execute("SELECT id FROM categories").fetchall()
        for category_row in category_rows:
            _seed_deterministic_category_default(conn, profile_id, category_row[0])
        row = conn.execute(
            """
            SELECT id, name, enabled, generation_mode, audio_generation_mode, duration_target_minutes, max_item_age_hours,
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
            SELECT id, name, enabled, generation_mode, audio_generation_mode, duration_target_minutes, max_item_age_hours,
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
            SELECT id, name, enabled, generation_mode, audio_generation_mode, duration_target_minutes, max_item_age_hours,
                   per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone,
                   created_at, updated_at
            FROM generation_profiles WHERE id = ?
            """,
            (profile["id"],),
        ).fetchone()
    return row_to_dict(row)


def update_generation_mode(profile_id: str, generation_mode: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE generation_profiles
            SET generation_mode = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (generation_mode, profile_id),
        )
        if cursor.rowcount == 0:
            return None
        row = conn.execute(
            """
            SELECT id, name, enabled, generation_mode, audio_generation_mode, duration_target_minutes, max_item_age_hours,
                   per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone,
                   created_at, updated_at
            FROM generation_profiles WHERE id = ?
            """,
            (profile_id,),
        ).fetchone()
    return row_to_dict(row) if row else None


def get_generation_mode(profile_id: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT generation_mode FROM generation_profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
    return row[0] if row else None


def get_audio_generation_mode(profile_id: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT audio_generation_mode FROM generation_profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
    return row[0] if row else None


def update_audio_generation_mode(profile_id: str, audio_generation_mode: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE generation_profiles
            SET audio_generation_mode = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (audio_generation_mode, profile_id),
        )
        if cursor.rowcount == 0:
            return None
        row = conn.execute(
            """
            SELECT id, name, enabled, generation_mode, audio_generation_mode, duration_target_minutes, max_item_age_hours,
                   per_episode_token_cap, monthly_api_budget_eur_cents, schedule_cron, timezone,
                   created_at, updated_at
            FROM generation_profiles WHERE id = ?
            """,
            (profile_id,),
        ).fetchone()
    return row_to_dict(row) if row else None


def get_deterministic_global_settings(profile_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT profile_id, version, target_duration_sec, speech_rate_wpm, freshness_hours_max,
                   max_items_per_category_default, min_items_per_category_default,
                   scoring_weights_json, extractive_rules_json, trim_policy_json, fallback_policy_json,
                   created_at, updated_at
            FROM deterministic_settings_global
            WHERE profile_id = ?
            """,
            (profile_id,),
        ).fetchone()
    if not row:
        return None
    result = row_to_dict(row)
    result["scoring_weights"] = _parse_json_field(result.pop("scoring_weights_json"), DETERMINISTIC_SCORING_WEIGHTS)
    result["extractive_rules"] = _parse_json_field(result.pop("extractive_rules_json"), DETERMINISTIC_EXTRACTIVE_RULES)
    result["trim_policy"] = _parse_json_field(result.pop("trim_policy_json"), DETERMINISTIC_TRIM_POLICY)
    result["fallback_policy"] = _parse_json_field(result.pop("fallback_policy_json"), DETERMINISTIC_FALLBACK_POLICY)
    return result


def upsert_deterministic_global_settings(profile_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO deterministic_settings_global (
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET
              version = excluded.version,
              target_duration_sec = excluded.target_duration_sec,
              speech_rate_wpm = excluded.speech_rate_wpm,
              freshness_hours_max = excluded.freshness_hours_max,
              max_items_per_category_default = excluded.max_items_per_category_default,
              min_items_per_category_default = excluded.min_items_per_category_default,
              scoring_weights_json = excluded.scoring_weights_json,
              extractive_rules_json = excluded.extractive_rules_json,
              trim_policy_json = excluded.trim_policy_json,
              fallback_policy_json = excluded.fallback_policy_json,
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                profile_id,
                int(payload.get("version", 1)),
                int(payload.get("target_duration_sec", 600)),
                int(payload.get("speech_rate_wpm", 155)),
                int(payload.get("freshness_hours_max", 48)),
                int(payload.get("max_items_per_category_default", 3)),
                int(payload.get("min_items_per_category_default", 1)),
                _json_text(payload.get("scoring_weights", DETERMINISTIC_SCORING_WEIGHTS)),
                _json_text(payload.get("extractive_rules", DETERMINISTIC_EXTRACTIVE_RULES)),
                _json_text(payload.get("trim_policy", DETERMINISTIC_TRIM_POLICY)),
                _json_text(payload.get("fallback_policy", DETERMINISTIC_FALLBACK_POLICY)),
            ),
        )
        row = conn.execute(
            """
            SELECT profile_id, version, target_duration_sec, speech_rate_wpm, freshness_hours_max,
                   max_items_per_category_default, min_items_per_category_default,
                   scoring_weights_json, extractive_rules_json, trim_policy_json, fallback_policy_json,
                   created_at, updated_at
            FROM deterministic_settings_global
            WHERE profile_id = ?
            """,
            (profile_id,),
        ).fetchone()
    return row_to_dict(row) if row else None


def update_deterministic_global_settings(profile_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    return upsert_deterministic_global_settings(profile_id, payload)


def list_deterministic_category_settings(profile_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT dsc.profile_id, dsc.category_id, c.name AS category_name, dsc.enabled, dsc.weight,
                   dsc.max_items, dsc.templates_json, dsc.scoring_override_json,
                   dsc.created_at, dsc.updated_at
            FROM deterministic_settings_category dsc
            JOIN categories c ON c.id = dsc.category_id
            WHERE dsc.profile_id = ?
            ORDER BY c.name ASC
            """,
            (profile_id,),
        ).fetchall()
    parsed: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row)
        item["templates"] = _parse_json_field(item.pop("templates_json"), {})
        item["scoring_override"] = _parse_json_field(item.pop("scoring_override_json"), {})
        parsed.append(item)
    return parsed


def upsert_deterministic_category_setting(
    profile_id: str,
    category_id: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO deterministic_settings_category (
              profile_id, category_id, enabled, weight, max_items, templates_json, scoring_override_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id, category_id) DO UPDATE SET
              enabled = excluded.enabled,
              weight = excluded.weight,
              max_items = excluded.max_items,
              templates_json = excluded.templates_json,
              scoring_override_json = excluded.scoring_override_json,
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                profile_id,
                category_id,
                1 if payload.get("enabled", True) else 0,
                int(payload.get("weight", 1)),
                payload.get("max_items"),
                _json_text(payload.get("templates", {})) if payload.get("templates") is not None else None,
                _json_text(payload.get("scoring_override", {})) if payload.get("scoring_override") is not None else None,
            ),
        )
        row = conn.execute(
            """
            SELECT dsc.profile_id, dsc.category_id, c.name AS category_name, dsc.enabled, dsc.weight,
                   dsc.max_items, dsc.templates_json, dsc.scoring_override_json,
                   dsc.created_at, dsc.updated_at
            FROM deterministic_settings_category dsc
            JOIN categories c ON c.id = dsc.category_id
            WHERE dsc.profile_id = ? AND dsc.category_id = ?
            """,
            (profile_id, category_id),
        ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    item["templates"] = _parse_json_field(item.pop("templates_json"), {})
    item["scoring_override"] = _parse_json_field(item.pop("scoring_override_json"), {})
    return item


def update_deterministic_category_setting(
    profile_id: str,
    category_id: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    return upsert_deterministic_category_setting(profile_id, category_id, payload)


def get_deterministic_category_setting(profile_id: str, category_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT dsc.profile_id, dsc.category_id, c.name AS category_name, dsc.enabled, dsc.weight,
                   dsc.max_items, dsc.templates_json, dsc.scoring_override_json,
                   dsc.created_at, dsc.updated_at
            FROM deterministic_settings_category dsc
            JOIN categories c ON c.id = dsc.category_id
            WHERE dsc.profile_id = ? AND dsc.category_id = ?
            """,
            (profile_id, category_id),
        ).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    item["templates"] = _parse_json_field(item.pop("templates_json"), {})
    item["scoring_override"] = _parse_json_field(item.pop("scoring_override_json"), {})
    return item


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
