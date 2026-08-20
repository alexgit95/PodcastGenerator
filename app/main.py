from __future__ import annotations

import os
from flask import Flask, jsonify, render_template, request, send_file
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
    get_deterministic_category_setting,
    get_deterministic_global_settings,
    get_generation_job,
    get_latest_successful_audio_job,
    list_deterministic_category_settings,
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
    update_audio_generation_mode,
    update_deterministic_category_setting,
    update_deterministic_global_settings,
    update_generation_mode,
    update_generation_job,
    update_source,
    update_source_health,
)
from .runtime_settings import (
    RuntimeSettingsError,
    load_runtime_settings,
    validate_deterministic_category_settings,
    validate_deterministic_global_settings,
    validate_runtime_settings,
)
from .rss_collection import collect_fresh_items
from .rss_health import check_feed_health
from .audio_generation import AUDIO_OUTPUT_DIR, AudioGenerationError, generate_local_mp3
from .script_generation import (
    ScriptGenerationError,
    build_script_prompt,
    estimate_cost_cents,
    estimate_tokens_from_text,
    generate_script_with_deterministic_mode,
    generate_script_with_single_provider,
)
from .scheduling import ScheduleParseError, episodes_per_week_hint, next_run_times


app = Flask(__name__, template_folder="templates", static_folder="static")
ensure_database()
DEFAULT_PROFILE = get_or_create_default_profile()
try:
    RUNTIME_SETTINGS = validate_runtime_settings(
        load_runtime_settings(),
        generation_mode=DEFAULT_PROFILE.get("generation_mode", "llm"),
    )
except RuntimeSettingsError as error:
    raise RuntimeError(f"Invalid LLM provider configuration: {error}") from error


def _current_profile() -> dict:
    return get_or_create_default_profile()


def _build_version_payload() -> dict:
    commit_sha = str(os.getenv("PODCAST_BUILD_COMMIT_SHA", "unknown") or "unknown").strip() or "unknown"
    commit_short = commit_sha[:7] if commit_sha != "unknown" else "unknown"
    return {
        "commit_sha": commit_sha,
        "commit_short": commit_short,
        "source": "env",
    }


def _run_audio_generation_job(profile: dict, script_text: str, *, trigger_origin: str) -> tuple[dict, int]:
    audio_generation_mode = str(profile.get("audio_generation_mode", "local")).strip().lower() or "local"
    deterministic_global_settings = get_deterministic_global_settings(profile["id"]) or {}
    extractive_rules = deterministic_global_settings.get("extractive_rules") or {}
    try:
        category_pause_seconds = float(extractive_rules.get("categoryPauseSeconds", 0.6) or 0.0)
    except (TypeError, ValueError):
        category_pause_seconds = 0.6
    if audio_generation_mode != "local":
        job_id = create_generation_job(
            profile["id"],
            "audio_generation",
            "blocked",
            {
                "reason": "audio_mode_not_local",
                "mode_used": audio_generation_mode,
                "trigger_origin": trigger_origin,
            },
        )
        return (
            {
                "status": "audio_mode_blocked",
                "job_id": job_id,
                "mode_used": audio_generation_mode,
                "reason": "audio_mode_not_local",
                "trigger_origin": trigger_origin,
            },
            409,
        )

    job_id = create_generation_job(
        profile["id"],
        "audio_generation",
        "running",
        {
            "mode_used": audio_generation_mode,
            "trigger_origin": trigger_origin,
        },
    )
    try:
        audio_raw = generate_local_mp3(script_text, job_id, category_pause_seconds=category_pause_seconds)
    except AudioGenerationError as error:
        update_generation_job(
            job_id,
            "failed",
            {
                "error": str(error),
                "mode_used": audio_generation_mode,
                "trigger_origin": trigger_origin,
            },
        )
        return (
            {
                "status": "audio_generation_error",
                "job_id": job_id,
                "error": str(error),
                "mode_used": audio_generation_mode,
                "trigger_origin": trigger_origin,
            },
            502,
        )

    audio = {
        "status": "ok",
        "mode_used": audio_raw.get("audio_mode_used", audio_generation_mode),
        "download_url": audio_raw.get("audio_download_url"),
        "file_name": audio_raw.get("audio_file_name"),
        "format": audio_raw.get("audio_format", "mp3"),
        # Backward-compatible aliases
        "audio_download_url": audio_raw.get("audio_download_url"),
        "audio_file_name": audio_raw.get("audio_file_name"),
        "audio_format": audio_raw.get("audio_format", "mp3"),
        "audio_mode_used": audio_raw.get("audio_mode_used", audio_generation_mode),
        "trigger_origin": trigger_origin,
    }

    update_generation_job(
        job_id,
        "succeeded",
        {
            "mode_used": audio_generation_mode,
            "trigger_origin": trigger_origin,
            "audio": audio,
        },
    )
    return (
        {
            "status": "ok",
            "job_id": job_id,
            "audio": audio,
            "mode_used": audio_generation_mode,
            "trigger_origin": trigger_origin,
        },
        200,
    )


def _compose_preview_from_payload(payload: dict, profile: dict):
    requested_category_ids = payload.get("category_ids")

    try:
        duration_target_minutes = int(payload.get("duration_target_minutes", profile["duration_target_minutes"]))
    except (TypeError, ValueError):
        return None, (jsonify({"error": "duration_target_minutes must be an integer"}), 400)
    if duration_target_minutes <= 0:
        return None, (jsonify({"error": "duration_target_minutes must be > 0"}), 400)
    max_item_age_hours = int(profile["max_item_age_hours"])
    brief_seconds = 45

    generation_mode = str(profile.get("generation_mode", "llm")).strip().lower() or "llm"
    if generation_mode == "deterministic":
        deterministic_global_settings = get_deterministic_global_settings(profile["id"]) or {}
        extractive_rules = deterministic_global_settings.get("extractive_rules") or {}
        try:
            max_item_age_hours = int(deterministic_global_settings.get("freshness_hours_max", max_item_age_hours))
        except (TypeError, ValueError):
            max_item_age_hours = int(profile["max_item_age_hours"])
        try:
            brief_seconds = int(extractive_rules.get("briefSecondsTarget", 45) or 45)
        except (TypeError, ValueError):
            brief_seconds = 45

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
    preview = build_episode_preview(
        items_by_category,
        weights,
        duration_target_minutes,
        brief_seconds=brief_seconds,
    )
    preview["max_item_age_hours"] = max_item_age_hours
    return preview, None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/version")
def api_version():
    return jsonify(_build_version_payload())


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


@app.get("/api/settings/mode")
def api_get_generation_mode():
    profile = _current_profile()
    return jsonify({"generation_mode": profile.get("generation_mode", "llm")})


@app.put("/api/settings/mode")
def api_update_generation_mode():
    payload = request.get_json(silent=True) or {}
    generation_mode = str(payload.get("generation_mode", "")).strip().lower()
    if generation_mode not in {"llm", "deterministic"}:
        return jsonify({"error": "generation_mode must be llm or deterministic"}), 400

    try:
        next_runtime_settings = validate_runtime_settings(
            load_runtime_settings(),
            generation_mode=generation_mode,
        )
    except RuntimeSettingsError as error:
        return jsonify({"error": str(error)}), 400

    profile = _current_profile()
    updated = update_generation_mode(profile["id"], generation_mode)
    if not updated:
        return jsonify({"error": "profile not found"}), 404

    global RUNTIME_SETTINGS
    RUNTIME_SETTINGS = next_runtime_settings
    return jsonify(updated)


@app.get("/api/settings/audio-mode")
def api_get_audio_generation_mode():
    profile = _current_profile()
    return jsonify({"audio_generation_mode": profile.get("audio_generation_mode", "local")})


@app.put("/api/settings/audio-mode")
def api_update_audio_generation_mode():
    payload = request.get_json(silent=True) or {}
    audio_generation_mode = str(payload.get("audio_generation_mode", "")).strip().lower()
    if audio_generation_mode not in {"local", "cloud"}:
        return jsonify({"error": "audio_generation_mode must be local or cloud"}), 400

    profile = _current_profile()
    updated = update_audio_generation_mode(profile["id"], audio_generation_mode)
    if not updated:
        return jsonify({"error": "profile not found"}), 404
    return jsonify(updated)


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


@app.get("/api/settings/deterministic")
def api_get_deterministic_settings():
    profile = _current_profile()
    global_settings = get_deterministic_global_settings(profile["id"])
    category_settings = list_deterministic_category_settings(profile["id"])
    return jsonify(
        {
            "generation_mode": profile.get("generation_mode", "llm"),
            "global": global_settings,
            "categories": category_settings,
        }
    )


@app.put("/api/settings/deterministic/global")
def api_update_deterministic_global_settings():
    payload = request.get_json(silent=True) or {}
    try:
        validated = validate_deterministic_global_settings(payload)
    except RuntimeSettingsError as error:
        return jsonify({"error": str(error)}), 400

    profile = _current_profile()
    updated = update_deterministic_global_settings(profile["id"], validated)
    if not updated:
        return jsonify({"error": "profile not found"}), 404
    return jsonify(updated)


@app.put("/api/settings/deterministic/categories/<category_id>")
def api_update_deterministic_category_settings(category_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = validate_deterministic_category_settings(payload)
    except RuntimeSettingsError as error:
        return jsonify({"error": str(error)}), 400

    profile = _current_profile()
    updated = update_deterministic_category_setting(profile["id"], category_id, validated)
    if not updated:
        return jsonify({"error": "category not found"}), 404
    return jsonify(updated)


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
    generation_mode = str(profile.get("generation_mode", "llm")).strip().lower() or "llm"

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

    per_episode_cap = int(profile["per_episode_token_cap"])

    if generation_mode == "deterministic":
        deterministic_global_settings = get_deterministic_global_settings(profile["id"])
        deterministic_category_settings = list_deterministic_category_settings(profile["id"])
        job_id = create_generation_job(
            profile["id"],
            "script_generation",
            "running",
            {
                "duration_target_minutes": preview.get("duration_target_minutes"),
                "mode_used": generation_mode,
                "prompt_truncated": False,
            },
        )

        try:
            generation = generate_script_with_deterministic_mode(
                preview=preview,
                deterministic_global_settings=deterministic_global_settings or {},
                deterministic_category_settings=deterministic_category_settings,
                per_episode_token_cap=per_episode_cap,
            )
        except ScriptGenerationError as error:
            app.logger.exception(
                "Script generation failed in deterministic mode",
                extra={
                    "job_id": job_id,
                    "mode_used": generation_mode,
                    "duration_target_minutes": preview.get("duration_target_minutes"),
                },
            )
            update_generation_job(job_id, "failed", {"error": str(error), "mode_used": generation_mode})
            return jsonify({"status": "generation_error", "error": str(error)}), 502

        usage = generation["usage"]
        estimated_cost = 0
        updated_spend = add_monthly_spend(profile["id"], estimated_cost, monthly_cap)
        update_generation_job(
            job_id,
            "succeeded",
            {
                "mode_used": generation_mode,
                "usage": usage,
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
                "mode_used": generation_mode,
                "prompt_truncated": False,
                "cost": {
                    "estimated_request_cost_eur_cents": estimated_cost,
                    "month_key": updated_spend["month_key"],
                    "spent_eur_cents": updated_spend["spent_eur_cents"],
                    "cap_eur_cents": updated_spend["hard_cap_eur_cents"],
                },
            }
        )

    prompt_text = build_script_prompt(preview)
    max_prompt_chars = int(RUNTIME_SETTINGS["max_prompt_chars"])
    prompt_truncated = False
    if len(prompt_text) > max_prompt_chars:
        prompt_text = prompt_text[:max_prompt_chars]
        prompt_truncated = True

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
                "mode_used": generation_mode,
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
                    "mode_used": generation_mode,
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
            "mode_used": generation_mode,
        },
    )

    try:
        generation = generate_script_with_single_provider(
            provider=str(RUNTIME_SETTINGS["api_provider"]),
            provider_adapter=str(RUNTIME_SETTINGS["provider_adapter"]),
            prompt_text=prompt_text,
            api_url=str(RUNTIME_SETTINGS["api_url"]),
            api_key=str(RUNTIME_SETTINGS["api_key"]),
            api_model=str(RUNTIME_SETTINGS["api_model"]),
            max_retries=int(RUNTIME_SETTINGS["max_retries"]),
            per_episode_token_cap=per_episode_cap,
        )
    except ScriptGenerationError as error:
        app.logger.exception(
            "Script generation failed in provider mode",
            extra={
                "job_id": job_id,
                "mode_used": generation_mode,
                "provider": str(RUNTIME_SETTINGS["api_provider"]),
                "provider_adapter": str(RUNTIME_SETTINGS["provider_adapter"]),
                "provider_api_url": str(RUNTIME_SETTINGS["api_url"]),
                "provider_model": str(RUNTIME_SETTINGS["api_model"]),
                "estimated_prompt_tokens": estimated_prompt_tokens,
                "prompt_truncated": prompt_truncated,
            },
        )
        update_generation_job(job_id, "failed", {"error": str(error), "mode_used": generation_mode})
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
            "mode_used": generation_mode,
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
            "mode_used": generation_mode,
            "prompt_truncated": prompt_truncated,
            "cost": {
                "estimated_request_cost_eur_cents": estimated_cost,
                "month_key": updated_spend["month_key"],
                "spent_eur_cents": updated_spend["spent_eur_cents"],
                "cap_eur_cents": updated_spend["hard_cap_eur_cents"],
            },
        }
    )


@app.post("/api/generate/audio")
def api_generate_audio():
    payload = request.get_json(silent=True) or {}
    script_text = str(payload.get("script_text", "")).strip()
    if not script_text:
        return jsonify({"error": "script_text is required"}), 400

    profile = get_or_create_default_profile()
    response_payload, response_status = _run_audio_generation_job(profile, script_text, trigger_origin="manual")
    return jsonify(response_payload), response_status


@app.post("/api/generate/scheduled")
def api_generate_scheduled():
    script_response = app.make_response(api_generate_script())
    script_status = int(script_response.status_code)
    script_payload = script_response.get_json(silent=True) or {}
    script_job_id = script_payload.get("job_id")

    if script_status != 200 or not script_payload.get("script"):
        return (
            jsonify(
                {
                    "status": "script_stage_incomplete",
                    "script_stage": {
                        "status": script_payload.get("status", "failed"),
                        "http_status": script_status,
                        "job_id": script_job_id,
                        "mode_used": script_payload.get("mode_used"),
                        "reason": script_payload.get("reason") or script_payload.get("error"),
                    },
                    "audio_stage": {
                        "status": "skipped",
                        "reason": "script_stage_not_succeeded",
                    },
                }
            ),
            script_status,
        )

    profile = get_or_create_default_profile()
    audio_payload, audio_status = _run_audio_generation_job(
        profile,
        script_payload.get("script", ""),
        trigger_origin="scheduled",
    )

    script_stage = {
        "status": "succeeded",
        "http_status": script_status,
        "job_id": script_job_id,
        "mode_used": script_payload.get("mode_used"),
    }
    if script_job_id:
        existing_script_job = get_generation_job(script_job_id)
        if existing_script_job:
            details = dict(existing_script_job.get("details") or {})
            details["trigger_origin"] = "scheduled"
            details["audio_stage"] = {
                "status": "succeeded" if audio_status == 200 else ("blocked" if audio_status == 409 else "failed"),
                "job_id": audio_payload.get("job_id"),
                "mode_used": audio_payload.get("mode_used"),
                "reason": audio_payload.get("reason") or audio_payload.get("error"),
            }
            update_generation_job(script_job_id, str(existing_script_job.get("status") or "succeeded"), details)

    audio_stage = {
        "status": "succeeded" if audio_status == 200 else ("blocked" if audio_status == 409 else "failed"),
        "http_status": audio_status,
        "job_id": audio_payload.get("job_id"),
        "mode_used": audio_payload.get("mode_used"),
        "reason": audio_payload.get("reason") or audio_payload.get("error"),
    }

    if audio_status == 200:
        audio_stage["audio"] = audio_payload.get("audio")

    return jsonify(
        {
            "status": "ok" if audio_status == 200 else "partial_success",
            "mode_used": script_payload.get("mode_used"),
            "script": script_payload.get("script"),
            "script_stage": script_stage,
            "audio_stage": audio_stage,
        }
    )


@app.get("/api/generate/audio/latest")
def api_get_latest_audio():
    profile = get_or_create_default_profile()
    latest_job = get_latest_successful_audio_job(profile["id"])
    if not latest_job:
        return jsonify({"status": "not_found", "error": "No successful audio job available"}), 404

    details = latest_job.get("details") or {}
    audio = details.get("audio") if isinstance(details.get("audio"), dict) else {}
    trigger_origin = str(details.get("trigger_origin") or audio.get("trigger_origin") or "manual")
    mode_used = str(audio.get("mode_used") or audio.get("audio_mode_used") or details.get("mode_used") or "local")
    file_name = str(audio.get("file_name") or audio.get("audio_file_name") or f"{latest_job['id']}.mp3")
    download_url = str(audio.get("download_url") or audio.get("audio_download_url") or f"/api/generation-jobs/{latest_job['id']}/audio")
    audio_format = str(audio.get("format") or audio.get("audio_format") or "mp3")

    artifact_path = AUDIO_OUTPUT_DIR / file_name
    if not artifact_path.exists():
        return (
            jsonify(
                {
                    "status": "not_found",
                    "error": "Latest audio artifact file is missing",
                    "job_id": latest_job["id"],
                    "reason": "audio_artifact_missing",
                }
            ),
            404,
        )

    return jsonify(
        {
            "status": "ok",
            "job_id": latest_job["id"],
            "mode_used": mode_used,
            "trigger_origin": trigger_origin,
            "file_name": file_name,
            "download_url": download_url,
            "format": audio_format,
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


@app.get("/api/generation-jobs/<job_id>/audio")
def api_download_generation_audio(job_id: str):
    mp3_path = AUDIO_OUTPUT_DIR / f"{job_id}.mp3"
    if not mp3_path.exists():
        return jsonify({"error": "audio file not found"}), 404
    return send_file(mp3_path, as_attachment=True, download_name=f"{job_id}.mp3", mimetype="audio/mpeg")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
