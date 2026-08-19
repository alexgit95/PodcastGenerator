from __future__ import annotations

import os
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


def validate_runtime_settings(settings: dict[str, Any]) -> dict[str, Any]:
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
