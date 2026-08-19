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


def generate_script_with_economical_api(
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
