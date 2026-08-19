from __future__ import annotations

import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ScriptGenerationError(Exception):
    pass


def estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    # Conservative approximation for French/English mixed content.
    return max(1, math.ceil(len(text) / 4))


def estimate_cost_cents(
    input_tokens: int,
    output_tokens: int,
    *,
    input_cents_per_million: int,
    output_cents_per_million: int,
) -> int:
    in_cost = (input_tokens / 1_000_000.0) * input_cents_per_million
    out_cost = (output_tokens / 1_000_000.0) * output_cents_per_million
    return int(math.ceil(in_cost + out_cost))


def _extract_response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        return "\n".join(parts).strip()
    return str(content or "").strip()


def _extract_usage(payload: dict[str, Any], prompt_text: str, output_text: str) -> dict[str, int]:
    usage = payload.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or estimate_tokens_from_text(prompt_text))
    output_tokens = int(usage.get("completion_tokens") or estimate_tokens_from_text(output_text))
    total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def build_script_prompt(preview: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("Tu es un redacteur de podcasts en francais.")
    lines.append("Produis un script naturel, concis et fluide.")
    lines.append(
        f"Contrainte de duree cible: {preview.get('duration_target_minutes', 10)} minutes maximum."
    )
    lines.append("Structure attendue: introduction, sections par categorie, transitions, conclusion.")
    lines.append("Si besoin, reste bref pour tenir la duree.")
    lines.append("\nArticles selectionnes:")

    for section in preview.get("sections", {}).get("category_sections", []):
        lines.append(f"- Categorie: {section.get('category_name')}")
        for brief in section.get("briefs", []):
            lines.append(
                "  - "
                + f"{brief.get('title')} | source={brief.get('source_title')} | lien={brief.get('link')}"
            )

    lines.append("\nRetourne uniquement le script final en francais.")
    return "\n".join(lines)


def _render_template(template: str, values: dict[str, Any]) -> str:
    try:
        return template.format(**values)
    except Exception:
        return template


def _deterministic_intro() -> str:
    return "Bonjour, voici votre point d'actualite du jour en version compacte et sans generation externe."


def _deterministic_conclusion() -> str:
    return "C'etait l'essentiel du jour. On se retrouve demain pour un nouveau point d'actualite."


def generate_script_with_deterministic_mode(
    *,
    preview: dict[str, Any],
    deterministic_global_settings: dict[str, Any],
    deterministic_category_settings: list[dict[str, Any]],
    per_episode_token_cap: int,
) -> dict[str, Any]:
    category_settings_map = {item["category_id"]: item for item in deterministic_category_settings}
    global_max_items = int(deterministic_global_settings.get("max_items_per_category_default", 3) or 3)
    global_min_items = int(deterministic_global_settings.get("min_items_per_category_default", 1) or 1)
    lines: list[str] = [_deterministic_intro()]
    sections = preview.get("sections", {})

    for index, category_section in enumerate(sections.get("category_sections", [])):
        category_id = category_section.get("category_id")
        category_name = category_section.get("category_name", "Categorie")
        settings = category_settings_map.get(category_id, {})
        templates = settings.get("templates") or {}
        lead_in_template = templates.get("leadIn") or f"En {{category_name}}, premier point: {{title}}."
        transition_out_template = templates.get("transitionOut") or "On passe au sujet suivant."
        briefs = category_section.get("briefs", [])
        effective_max_items = settings.get("max_items") or global_max_items
        effective_max_items = max(global_min_items, int(effective_max_items))
        briefs = briefs[:effective_max_items]

        lines.append(
            _render_template(
                lead_in_template,
                {
                    "category_name": category_name,
                    "title": briefs[0]["title"] if briefs else category_name,
                    "source_title": briefs[0]["source_title"] if briefs else "source inconnue",
                },
            )
        )

        for brief in briefs:
            lines.append(
                _render_template(
                    templates.get("impact") or "Point cle: {title} (source: {source_title}).",
                    {
                        "category_name": category_name,
                        "title": brief.get("title", ""),
                        "source_title": brief.get("source_title", ""),
                        "link": brief.get("link", ""),
                    },
                )
            )

        if index < len(sections.get("category_sections", [])) - 1:
            lines.append(
                _render_template(
                    transition_out_template,
                    {"category_name": category_name},
                )
            )

    if sections.get("conclusion") is not None:
        lines.append(_deterministic_conclusion())

    script = "\n".join(line for line in lines if line.strip())
    usage = {
        "input_tokens": 0,
        "output_tokens": estimate_tokens_from_text(script),
        "total_tokens": estimate_tokens_from_text(script),
    }
    if usage["total_tokens"] > per_episode_token_cap:
        raise ScriptGenerationError("Per-episode token cap exceeded by deterministic output")

    return {
        "script": script,
        "usage": usage,
        "raw": {
            "mode": "deterministic",
            "global_settings": deterministic_global_settings,
            "category_settings": deterministic_category_settings,
            "effective_max_items_per_category_default": global_max_items,
            "preview": preview,
        },
    }


def _generate_with_openai_compatible_api(
    *,
    prompt_text: str,
    api_url: str,
    api_key: str,
    api_model: str,
    max_retries: int,
    per_episode_token_cap: int,
) -> dict[str, Any]:
    if not api_key:
        raise ScriptGenerationError("Missing API key: set PODCAST_LLM_API_KEY")

    request_payload = {
        "model": api_model,
        "temperature": 0.5,
        "messages": [
            {"role": "system", "content": "You write French podcast scripts."},
            {"role": "user", "content": prompt_text},
        ],
    }
    encoded_payload = json.dumps(request_payload).encode("utf-8")

    last_error: str | None = None
    attempts = max(0, max_retries) + 1
    for _ in range(attempts):
        try:
            req = Request(
                api_url,
                data=encoded_payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=40) as response:
                payload = json.loads(response.read().decode("utf-8"))

            output_text = _extract_response_text(payload)
            usage = _extract_usage(payload, prompt_text, output_text)
            if usage["total_tokens"] > per_episode_token_cap:
                raise ScriptGenerationError(
                    "Per-episode token cap exceeded by model response"
                )
            return {
                "script": output_text,
                "usage": usage,
                "raw": payload,
            }

        except HTTPError as error:
            body = error.read().decode("utf-8", errors="ignore")
            last_error = f"HTTP {error.code}: {body[:500]}"
        except URLError as error:
            last_error = f"Network error: {error.reason}"
        except ScriptGenerationError:
            raise
        except Exception as error:  # pragma: no cover
            last_error = f"Unexpected error: {error}"

    raise ScriptGenerationError(last_error or "Script generation failed")


def generate_script_with_single_provider(
    *,
    provider: str,
    provider_adapter: str,
    prompt_text: str,
    api_url: str,
    api_key: str,
    api_model: str,
    max_retries: int,
    per_episode_token_cap: int,
) -> dict[str, Any]:
    if provider_adapter == "openai_compatible":
        return _generate_with_openai_compatible_api(
            prompt_text=prompt_text,
            api_url=api_url,
            api_key=api_key,
            api_model=api_model,
            max_retries=max_retries,
            per_episode_token_cap=per_episode_token_cap,
        )

    raise ScriptGenerationError(
        f"Unsupported provider adapter '{provider_adapter}' for provider '{provider}'"
    )
