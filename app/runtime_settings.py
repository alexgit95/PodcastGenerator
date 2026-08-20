from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULTS_PATH = ROOT_DIR / "config" / "podcast-generator.defaults.yaml"


class RuntimeSettingsError(Exception):
    pass


PROVIDER_ADAPTERS = {
    "openai": "openai_compatible",
    "openrouter": "openai_compatible",
    "custom-openai-compatible": "openai_compatible",
}


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if value.isdigit():
        return int(value)
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return value[1:-1]
    return value


def _simple_yaml_parse(text: str) -> dict[str, Any]:
    # Minimal YAML parser for this controlled defaults file (2-level maps + list values).
    root: dict[str, Any] = {}
    section_stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if stripped.startswith("- "):
            item = _parse_scalar(stripped[2:])
            container = section_stack[-1][1]
            if "__list__" not in container:
                container["__list__"] = []
            container["__list__"].append(item)
            continue

        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        while section_stack and indent <= section_stack[-1][0]:
            section_stack.pop()

        current = section_stack[-1][1]
        if not value:
            current[key] = {}
            section_stack.append((indent, current[key]))
        else:
            current[key] = _parse_scalar(value)

    def normalize(node: Any) -> Any:
        if isinstance(node, dict):
            if "__list__" in node and len(node) == 1:
                return [normalize(item) for item in node["__list__"]]
            return {key: normalize(value) for key, value in node.items() if key != "__list__"}
        if isinstance(node, list):
            return [normalize(value) for value in node]
        return node

    return normalize(root)


def load_runtime_settings() -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    if DEFAULTS_PATH.exists():
        defaults = _simple_yaml_parse(DEFAULTS_PATH.read_text(encoding="utf-8"))

    api_cfg = defaults.get("api", {})
    settings = {
        "api_provider": _first_non_empty(
            os.getenv("PODCAST_LLM_PROVIDER"),
            api_cfg.get("provider"),
            "openai",
        ),
        "api_url": _first_non_empty(
            os.getenv("PODCAST_LLM_API_URL"),
            api_cfg.get("baseUrl"),
            "https://api.openai.com/v1/chat/completions",
        ),
        "api_key": _first_non_empty(os.getenv("PODCAST_LLM_API_KEY"), ""),
        "api_model": _first_non_empty(
            os.getenv("PODCAST_LLM_MODEL"),
            api_cfg.get("model"),
            "gpt-4o-mini",
        ),
        "max_retries": _first_non_empty(
            os.getenv("PODCAST_LLM_MAX_RETRIES"),
            api_cfg.get("maxRetries"),
            "1",
        ),
        "max_prompt_chars": _first_non_empty(
            os.getenv("PODCAST_LLM_MAX_PROMPT_CHARS"),
            api_cfg.get("maxPromptChars"),
            "20000",
        ),
        # Pricing is expressed in euro-cents per 1M tokens.
        "input_cents_per_million": _first_non_empty(
            os.getenv("PODCAST_LLM_INPUT_CENTS_PER_MILLION"),
            api_cfg.get("inputCentsPerMillion"),
            "15",
        ),
        "output_cents_per_million": _first_non_empty(
            os.getenv("PODCAST_LLM_OUTPUT_CENTS_PER_MILLION"),
            api_cfg.get("outputCentsPerMillion"),
            "60",
        ),
    }
    return settings


def _parse_positive_int(value: Any, env_name: str) -> int:
    text = str(value).strip()
    if not text:
        raise RuntimeSettingsError(f"Missing value for {env_name}")
    try:
        parsed = int(text)
    except ValueError as error:
        raise RuntimeSettingsError(f"Invalid integer for {env_name}: '{text}'") from error
    if parsed <= 0:
        raise RuntimeSettingsError(f"{env_name} must be > 0")
    return parsed


def _parse_non_negative_int(value: Any, env_name: str) -> int:
    text = str(value).strip()
    if not text:
        raise RuntimeSettingsError(f"Missing value for {env_name}")
    try:
        parsed = int(text)
    except ValueError as error:
        raise RuntimeSettingsError(f"Invalid integer for {env_name}: '{text}'") from error
    if parsed < 0:
        raise RuntimeSettingsError(f"{env_name} must be >= 0")
    return parsed


def _parse_non_negative_float(value: Any, env_name: str) -> float:
    text = str(value).strip()
    if not text:
        raise RuntimeSettingsError(f"Missing value for {env_name}")
    try:
        parsed = float(text)
    except ValueError as error:
        raise RuntimeSettingsError(f"Invalid number for {env_name}: '{text}'") from error
    if parsed < 0:
        raise RuntimeSettingsError(f"{env_name} must be >= 0")
    return parsed


def _parse_json_object(value: Any, env_name: str) -> dict[str, Any]:
    if value is None:
        raise RuntimeSettingsError(f"Missing value for {env_name}")
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if not text:
        raise RuntimeSettingsError(f"Missing value for {env_name}")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeSettingsError(f"Invalid JSON for {env_name}") from error
    if not isinstance(parsed, dict):
        raise RuntimeSettingsError(f"{env_name} must be a JSON object")
    return parsed


def validate_runtime_settings(settings: dict[str, Any], *, generation_mode: str = "llm") -> dict[str, Any]:
    normalized_mode = str(generation_mode).strip().lower() or "llm"
    if normalized_mode not in {"llm", "deterministic"}:
        raise RuntimeSettingsError(f"Unsupported generation mode '{generation_mode}'")

    settings["generation_mode"] = normalized_mode

    if normalized_mode == "deterministic":
        settings["api_provider"] = ""
        settings["provider_adapter"] = ""
        settings["api_url"] = ""
        settings["api_key"] = ""
        settings["api_model"] = ""
        settings["max_retries"] = 0
        settings["max_prompt_chars"] = _parse_positive_int(settings.get("max_prompt_chars"), "PODCAST_LLM_MAX_PROMPT_CHARS") if str(settings.get("max_prompt_chars", "")).strip() else 20000
        settings["input_cents_per_million"] = _parse_non_negative_int(settings.get("input_cents_per_million"), "PODCAST_LLM_INPUT_CENTS_PER_MILLION") if str(settings.get("input_cents_per_million", "")).strip() else 0
        settings["output_cents_per_million"] = _parse_non_negative_int(settings.get("output_cents_per_million"), "PODCAST_LLM_OUTPUT_CENTS_PER_MILLION") if str(settings.get("output_cents_per_million", "")).strip() else 0
        return settings

    provider = str(settings.get("api_provider", "")).strip().lower()
    if not provider:
        raise RuntimeSettingsError(
            "Missing provider selection: set PODCAST_LLM_PROVIDER to one supported provider"
        )

    adapter = PROVIDER_ADAPTERS.get(provider)
    if not adapter:
        supported = ", ".join(sorted(PROVIDER_ADAPTERS.keys()))
        raise RuntimeSettingsError(
            f"Unsupported provider '{provider}'. Supported providers: {supported}"
        )

    api_url = str(settings.get("api_url", "")).strip()
    if not api_url:
        raise RuntimeSettingsError("Missing provider endpoint: set PODCAST_LLM_API_URL")
    if not (api_url.startswith("http://") or api_url.startswith("https://")):
        raise RuntimeSettingsError(
            "Invalid provider endpoint: PODCAST_LLM_API_URL must start with http:// or https://"
        )

    api_model = str(settings.get("api_model", "")).strip()
    if not api_model:
        raise RuntimeSettingsError("Missing provider model: set PODCAST_LLM_MODEL")

    max_retries = _parse_non_negative_int(settings.get("max_retries"), "PODCAST_LLM_MAX_RETRIES")
    max_prompt_chars = _parse_positive_int(settings.get("max_prompt_chars"), "PODCAST_LLM_MAX_PROMPT_CHARS")
    input_cents_per_million = _parse_non_negative_int(
        settings.get("input_cents_per_million"),
        "PODCAST_LLM_INPUT_CENTS_PER_MILLION",
    )
    output_cents_per_million = _parse_non_negative_int(
        settings.get("output_cents_per_million"),
        "PODCAST_LLM_OUTPUT_CENTS_PER_MILLION",
    )

    settings["api_provider"] = provider
    settings["provider_adapter"] = adapter
    settings["api_url"] = api_url
    settings["api_model"] = api_model
    settings["max_retries"] = max_retries
    settings["max_prompt_chars"] = max_prompt_chars
    settings["input_cents_per_million"] = input_cents_per_million
    settings["output_cents_per_million"] = output_cents_per_million
    return settings


def validate_deterministic_global_settings(settings: dict[str, Any]) -> dict[str, Any]:
    validated = {
        "version": _parse_positive_int(settings.get("version", 1), "DETERMINISTIC_VERSION"),
        "target_duration_sec": _parse_positive_int(settings.get("target_duration_sec", 600), "DETERMINISTIC_TARGET_DURATION_SEC"),
        "speech_rate_wpm": _parse_positive_int(settings.get("speech_rate_wpm", 155), "DETERMINISTIC_SPEECH_RATE_WPM"),
        "freshness_hours_max": _parse_positive_int(settings.get("freshness_hours_max", 48), "DETERMINISTIC_FRESHNESS_HOURS_MAX"),
        "max_items_per_category_default": _parse_positive_int(settings.get("max_items_per_category_default", 3), "DETERMINISTIC_MAX_ITEMS_PER_CATEGORY_DEFAULT"),
        "min_items_per_category_default": _parse_positive_int(settings.get("min_items_per_category_default", 1), "DETERMINISTIC_MIN_ITEMS_PER_CATEGORY_DEFAULT"),
        "scoring_weights": _parse_json_object(settings.get("scoring_weights", {}), "DETERMINISTIC_SCORING_WEIGHTS"),
        "extractive_rules": _parse_json_object(settings.get("extractive_rules", {}), "DETERMINISTIC_EXTRACTIVE_RULES"),
        "trim_policy": _parse_json_object(settings.get("trim_policy", {}), "DETERMINISTIC_TRIM_POLICY"),
        "fallback_policy": _parse_json_object(settings.get("fallback_policy", {}), "DETERMINISTIC_FALLBACK_POLICY"),
    }

    if not (120 <= validated["target_duration_sec"] <= 3600):
        raise RuntimeSettingsError("DETERMINISTIC_TARGET_DURATION_SEC must be between 120 and 3600")
    if not (100 <= validated["speech_rate_wpm"] <= 220):
        raise RuntimeSettingsError("DETERMINISTIC_SPEECH_RATE_WPM must be between 100 and 220")
    if not (1 <= validated["max_items_per_category_default"] <= 10):
        raise RuntimeSettingsError("DETERMINISTIC_MAX_ITEMS_PER_CATEGORY_DEFAULT must be between 1 and 10")
    if not (1 <= validated["min_items_per_category_default"] <= 10):
        raise RuntimeSettingsError("DETERMINISTIC_MIN_ITEMS_PER_CATEGORY_DEFAULT must be between 1 and 10")
    if validated["min_items_per_category_default"] > validated["max_items_per_category_default"]:
        raise RuntimeSettingsError("DETERMINISTIC_MIN_ITEMS_PER_CATEGORY_DEFAULT must be <= max_items_per_category_default")

    extractive_rules = dict(validated["extractive_rules"])
    brief_seconds_target = _parse_positive_int(
        extractive_rules.get("briefSecondsTarget", 45),
        "DETERMINISTIC_BRIEF_SECONDS_TARGET",
    )
    if not (5 <= brief_seconds_target <= 180):
        raise RuntimeSettingsError("DETERMINISTIC_BRIEF_SECONDS_TARGET must be between 5 and 180")

    category_pause_seconds = _parse_non_negative_float(
        extractive_rules.get("categoryPauseSeconds", 0.6),
        "DETERMINISTIC_CATEGORY_PAUSE_SECONDS",
    )
    if not (0 <= category_pause_seconds <= 5):
        raise RuntimeSettingsError("DETERMINISTIC_CATEGORY_PAUSE_SECONDS must be between 0 and 5")

    alignment_enabled_raw = extractive_rules.get("durationAlignmentEnabled", False)
    alignment_enabled = bool(alignment_enabled_raw)

    extractive_rules["briefSecondsTarget"] = brief_seconds_target
    extractive_rules["categoryPauseSeconds"] = round(category_pause_seconds, 2)
    extractive_rules["durationAlignmentEnabled"] = alignment_enabled
    validated["extractive_rules"] = extractive_rules

    return validated


def validate_deterministic_category_settings(settings: dict[str, Any]) -> dict[str, Any]:
    validated = {
        "enabled": bool(settings.get("enabled", True)),
        "weight": _parse_positive_int(settings.get("weight", 1), "DETERMINISTIC_CATEGORY_WEIGHT"),
        "max_items": settings.get("max_items"),
        "templates": _parse_json_object(settings.get("templates", {}), "DETERMINISTIC_CATEGORY_TEMPLATES") if settings.get("templates") is not None else {},
        "scoring_override": _parse_json_object(settings.get("scoring_override", {}), "DETERMINISTIC_CATEGORY_SCORING_OVERRIDE") if settings.get("scoring_override") is not None else {},
    }
    if validated["max_items"] is not None:
        max_items = _parse_positive_int(validated["max_items"], "DETERMINISTIC_CATEGORY_MAX_ITEMS")
        if not (1 <= max_items <= 10):
            raise RuntimeSettingsError("DETERMINISTIC_CATEGORY_MAX_ITEMS must be between 1 and 10")
        validated["max_items"] = max_items
    return validated
