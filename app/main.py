from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from sqlite3 import IntegrityError

from .db import ensure_database
from .composition import build_episode_preview
from .guardrails import (
    is_monthly_budget_exhausted,
    is_prompt_cap_exceeded,
    would_exceed_monthly_budget,
)
from .repository import (
    add_monthly_spend,
    create_generation_job,
    current_month_key,
    create_category,
    create_mapping,
    create_source,
    delete_category,
    delete_mapping,
    delete_source,
    get_monthly_spend,
    get_or_create_default_profile,
    get_source,
    list_recent_generation_jobs,
    list_category_source_bindings,
    list_categories,
    list_mappings,
    list_sources,
    update_category,
    update_default_profile_duration,
    update_default_profile_schedule,
    update_generation_job,
    update_source,
    update_source_health,
)
from .runtime_settings import load_runtime_settings
from .rss_collection import collect_fresh_items
from .rss_health import check_feed_health
from .script_generation import (
    ScriptGenerationError,
    build_script_prompt,
    estimate_cost_cents,
    estimate_tokens_from_text,
    generate_script_with_economical_api,
)
from .scheduling import ScheduleParseError, episodes_per_week_hint, next_run_times


app = Flask(__name__, template_folder="templates", static_folder="static")
ensure_database()
RUNTIME_SETTINGS = load_runtime_settings()


def _compose_preview_from_payload(payload: dict, profile: dict):
    requested_category_ids = payload.get("category_ids")

    try:
        duration_target_minutes = int(payload.get("duration_target_minutes", profile["duration_target_minutes"]))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "duration_target_minutes must be an integer"}), 400)
    if duration_target_minutes <= 0:
        return None, (jsonify({"error": "duration_target_minutes must be > 0"}), 400)
    max_item_age_hours = int(profile["max_item_age_hours"])

    bindings = list_category_source_bindings(requested_category_ids)
    if not bindings:
        preview = {
            "duration_target_minutes": duration_target_minutes,
            "estimated_total_seconds": 0,
            "sections": {
                "intro": {"estimated_seconds": 0},
                "category_sections": [],
                "transitions": [],
                "conclusion": None,
                "trim_log": [],
            },
            "message": "No active category/source mapping available",
            "max_item_age_hours": max_item_age_hours,
        }
        return preview, None

    weights: dict[str, int] = {}
    for binding in bindings:
        weights[binding["category_id"]] = max(1, int(binding["default_weight"]))

    items_by_category = collect_fresh_items(bindings, max_item_age_hours)
    preview = build_episode_preview(items_by_category, weights, duration_target_minutes)
    preview["max_item_age_hours"] = max_item_age_hours
    return preview, None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/categories")
def api_list_categories():
    return jsonify(list_categories())


@app.post("/api/categories")
def api_create_category():
    payload = request.get_json(silent=True) or {}
    if not payload.get("name"):
        return jsonify({"error": "name is required"}), 400
    try:
        category = create_category(payload)
    except (IntegrityError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(category), 201


@app.put("/api/categories/<category_id>")
def api_update_category(category_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        category = update_category(category_id, payload)
    except (IntegrityError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    if not category:
        return jsonify({"error": "category not found"}), 404
    return jsonify(category)


@app.delete("/api/categories/<category_id>")
def api_delete_category(category_id: str):
    deleted = delete_category(category_id)
    if not deleted:
        return jsonify({"error": "category not found"}), 404
    return ("", 204)


@app.get("/api/rss-sources")
def api_list_sources():
    return jsonify(list_sources())


@app.post("/api/rss-sources")
def api_create_source():
    payload = request.get_json(silent=True) or {}
    if not payload.get("url"):
        return jsonify({"error": "url is required"}), 400
    try:
        source = create_source(payload)
    except (IntegrityError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(source), 201


@app.put("/api/rss-sources/<source_id>")
def api_update_source(source_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        source = update_source(source_id, payload)
    except (IntegrityError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    if not source:
        return jsonify({"error": "source not found"}), 404
    return jsonify(source)


@app.delete("/api/rss-sources/<source_id>")
def api_delete_source(source_id: str):
    deleted = delete_source(source_id)
    if not deleted:
        return jsonify({"error": "source not found"}), 404
    return ("", 204)


@app.post("/api/rss-sources/<source_id>/health-check")
def api_source_health(source_id: str):
    source = get_source(source_id)
    if not source:
        return jsonify({"error": "source not found"}), 404

    result = check_feed_health(source["url"])
    updated = update_source_health(
        source_id,
        health_status="healthy" if result.healthy else "error",
        health_message=result.message,
        successful=result.healthy,
    )
    if not updated:
        return jsonify({"error": "source not found"}), 404
    return jsonify(updated)


@app.get("/api/mappings")
def api_list_mappings():
    return jsonify(list_mappings())


@app.post("/api/mappings")
def api_create_mapping():
    payload = request.get_json(silent=True) or {}
    category_id = payload.get("category_id")
    source_id = payload.get("source_id")
    if not category_id or not source_id:
        return jsonify({"error": "category_id and source_id are required"}), 400
    try:
        create_mapping(category_id, source_id)
    except IntegrityError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"ok": True}), 201


@app.delete("/api/mappings")
def api_delete_mapping():
    category_id = request.args.get("category_id")
    source_id = request.args.get("source_id")
    if not category_id or not source_id:
        return jsonify({"error": "category_id and source_id query params are required"}), 400
    deleted = delete_mapping(category_id, source_id)
    if not deleted:
        return jsonify({"error": "mapping not found"}), 404
    return ("", 204)


@app.get("/api/settings/duration-target")
def api_get_duration_target():
    profile = get_or_create_default_profile()
    return jsonify(
        {
            "duration_target_minutes": profile["duration_target_minutes"],
            "max_item_age_hours": profile["max_item_age_hours"],
        }
    )


@app.put("/api/settings/duration-target")
def api_update_duration_target():
    payload = request.get_json(silent=True) or {}
    if "duration_target_minutes" not in payload:
        return jsonify({"error": "duration_target_minutes is required"}), 400
    try:
        duration_target_minutes = int(payload["duration_target_minutes"])
    except (TypeError, ValueError):
        return jsonify({"error": "duration_target_minutes must be an integer"}), 400
    if duration_target_minutes <= 0:
        return jsonify({"error": "duration_target_minutes must be > 0"}), 400

    profile = update_default_profile_duration(duration_target_minutes)
    return jsonify(
        {
            "duration_target_minutes": profile["duration_target_minutes"],
            "max_item_age_hours": profile["max_item_age_hours"],
        }
    )


@app.post("/api/compose/preview")
def api_compose_preview():
    payload = request.get_json(silent=True) or {}
    profile = get_or_create_default_profile()
    preview, error_response = _compose_preview_from_payload(payload, profile)
    if error_response:
        return error_response
    return jsonify(preview)


@app.get("/api/budget-status")
def api_budget_status():
    profile = get_or_create_default_profile()
    cap = int(profile["monthly_api_budget_eur_cents"])
    spend = get_monthly_spend(profile["id"], current_month_key())
    spent = int(spend["spent_eur_cents"]) if spend else 0
    remaining = max(0, cap - spent)
    return jsonify(
        {
            "month_key": current_month_key(),
            "spent_eur_cents": spent,
            "cap_eur_cents": cap,
            "remaining_eur_cents": remaining,
            "blocked": spent >= cap,
        }
    )


@app.post("/api/generate/script")
def api_generate_script():
    payload = request.get_json(silent=True) or {}
    profile = get_or_create_default_profile()

    monthly_cap = int(profile["monthly_api_budget_eur_cents"])
    current_spend = get_monthly_spend(profile["id"], current_month_key())
    spent_cents = int(current_spend["spent_eur_cents"]) if current_spend else 0
    if is_monthly_budget_exhausted(spent_cents, monthly_cap):
        blocked_job = create_generation_job(
            profile["id"],
            "script_generation",
            "blocked",
            {
                "reason": "monthly_api_budget_exhausted",
                "spent_eur_cents": spent_cents,
                "cap_eur_cents": monthly_cap,
            },
        )
        return (
            jsonify(
                {
                    "status": "budget_blocked",
                    "job_id": blocked_job,
                    "reason": "monthly_api_budget_exhausted",
                    "spent_eur_cents": spent_cents,
                    "cap_eur_cents": monthly_cap,
                }
            ),
            409,
        )

    preview, error_response = _compose_preview_from_payload(payload, profile)
    if error_response:
        return error_response

    prompt_text = build_script_prompt(preview)
    max_prompt_chars = int(RUNTIME_SETTINGS["max_prompt_chars"])
    prompt_truncated = False
    if len(prompt_text) > max_prompt_chars:
        prompt_text = prompt_text[:max_prompt_chars]
        prompt_truncated = True

    per_episode_cap = int(profile["per_episode_token_cap"])
    estimated_prompt_tokens = estimate_tokens_from_text(prompt_text)
    if is_prompt_cap_exceeded(estimated_prompt_tokens, per_episode_cap):
        blocked_job = create_generation_job(
            profile["id"],
            "script_generation",
            "blocked",
            {
                "reason": "prompt_tokens_exceed_cap",
                "estimated_prompt_tokens": estimated_prompt_tokens,
                "per_episode_token_cap": per_episode_cap,
            },
        )
        return (
            jsonify(
                {
                    "status": "token_cap_blocked",
                    "job_id": blocked_job,
                    "reason": "prompt_tokens_exceed_cap",
                    "estimated_prompt_tokens": estimated_prompt_tokens,
                    "per_episode_token_cap": per_episode_cap,
                }
            ),
            409,
        )

    job_id = create_generation_job(
        profile["id"],
        "script_generation",
        "running",
        {
            "estimated_prompt_tokens": estimated_prompt_tokens,
            "duration_target_minutes": preview.get("duration_target_minutes"),
            "prompt_truncated": prompt_truncated,
        },
    )

    try:
        generation = generate_script_with_economical_api(
            prompt_text=prompt_text,
            api_url=str(RUNTIME_SETTINGS["api_url"]),
            api_key=str(RUNTIME_SETTINGS["api_key"]),
            api_model=str(RUNTIME_SETTINGS["api_model"]),
            max_retries=int(RUNTIME_SETTINGS["max_retries"]),
            per_episode_token_cap=per_episode_cap,
        )
    except ScriptGenerationError as error:
        update_generation_job(job_id, "failed", {"error": str(error)})
        return jsonify({"status": "generation_error", "error": str(error)}), 502

    usage = generation["usage"]
    estimated_cost = estimate_cost_cents(
        usage["input_tokens"],
        usage["output_tokens"],
        input_cents_per_million=int(RUNTIME_SETTINGS["input_cents_per_million"]),
        output_cents_per_million=int(RUNTIME_SETTINGS["output_cents_per_million"]),
    )

    if would_exceed_monthly_budget(spent_cents, estimated_cost, monthly_cap):
        update_generation_job(
            job_id,
            "blocked",
            {
                "reason": "monthly_cap_would_be_exceeded",
                "spent_eur_cents": spent_cents,
                "estimated_request_cost_eur_cents": estimated_cost,
                "cap_eur_cents": monthly_cap,
            },
        )
        return (
            jsonify(
                {
                    "status": "budget_blocked",
                    "job_id": job_id,
                    "reason": "monthly_cap_would_be_exceeded",
                    "spent_eur_cents": spent_cents,
                    "estimated_request_cost_eur_cents": estimated_cost,
                    "cap_eur_cents": monthly_cap,
                }
            ),
            409,
        )

    updated_spend = add_monthly_spend(profile["id"], estimated_cost, monthly_cap)
    update_generation_job(
        job_id,
        "succeeded",
        {
            "usage": generation["usage"],
            "estimated_request_cost_eur_cents": estimated_cost,
            "spent_eur_cents": updated_spend["spent_eur_cents"],
            "cap_eur_cents": updated_spend["hard_cap_eur_cents"],
        },
    )
    return jsonify(
        {
            "status": "ok",
            "job_id": job_id,
            "script": generation["script"],
            "usage": usage,
            "preview": preview,
            "prompt_truncated": prompt_truncated,
            "cost": {
                "estimated_request_cost_eur_cents": estimated_cost,
                "month_key": updated_spend["month_key"],
                "spent_eur_cents": updated_spend["spent_eur_cents"],
                "cap_eur_cents": updated_spend["hard_cap_eur_cents"],
            },
        }
    )


@app.get("/api/settings/schedule")
def api_get_schedule_settings():
    profile = get_or_create_default_profile()
    schedule_cron = str(profile["schedule_cron"])
    timezone = str(profile["timezone"])
    try:
        next_runs = next_run_times(schedule_cron, timezone, count=5)
        per_week = episodes_per_week_hint(schedule_cron)
    except ScheduleParseError:
        next_runs = []
        per_week = None

    return jsonify(
        {
            "schedule_cron": schedule_cron,
            "timezone": timezone,
            "episodes_per_week_hint": per_week,
            "next_runs": next_runs,
        }
    )


@app.put("/api/settings/schedule")
def api_update_schedule_settings():
    payload = request.get_json(silent=True) or {}
    schedule_cron = str(payload.get("schedule_cron", "")).strip()
    timezone = str(payload.get("timezone", "")).strip()
    if not schedule_cron or not timezone:
        return jsonify({"error": "schedule_cron and timezone are required"}), 400

    try:
        _ = next_run_times(schedule_cron, timezone, count=1)
    except ScheduleParseError as error:
        return jsonify({"error": str(error)}), 400

    profile = update_default_profile_schedule(schedule_cron, timezone)
    return jsonify(
        {
            "schedule_cron": profile["schedule_cron"],
            "timezone": profile["timezone"],
            "episodes_per_week_hint": episodes_per_week_hint(profile["schedule_cron"]),
            "next_runs": next_run_times(profile["schedule_cron"], profile["timezone"], count=5),
        }
    )


@app.get("/api/jobs")
def api_list_jobs():
    return jsonify(list_recent_generation_jobs(limit=20))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
