from __future__ import annotations

import os
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULTS_PATH = ROOT_DIR / "config" / "podcast-generator.defaults.yaml"


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
        "api_url": os.getenv("PODCAST_LLM_API_URL", "https://api.openai.com/v1/chat/completions"),
        "api_key": os.getenv("PODCAST_LLM_API_KEY", ""),
        "api_model": os.getenv("PODCAST_LLM_MODEL", "gpt-4o-mini"),
        "api_provider": os.getenv("PODCAST_LLM_PROVIDER", str(api_cfg.get("provider", "economical-fr"))),
        "max_retries": int(os.getenv("PODCAST_LLM_MAX_RETRIES", str(api_cfg.get("maxRetries", 1)))),
        "max_prompt_chars": int(os.getenv("PODCAST_LLM_MAX_PROMPT_CHARS", str(api_cfg.get("maxPromptChars", 20000)))),
        # Pricing defaults in euro-cents per 1M tokens for an economical tier.
        "input_cents_per_million": int(os.getenv("PODCAST_LLM_INPUT_CENTS_PER_MILLION", "15")),
        "output_cents_per_million": int(os.getenv("PODCAST_LLM_OUTPUT_CENTS_PER_MILLION", "60")),
    }
    return settings
