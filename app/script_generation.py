from __future__ import annotations

import random
import json
import math
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ScriptGenerationError(Exception):
    pass


logger = logging.getLogger(__name__)


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


def _deterministic_intro(*, preview: dict[str, Any], randomize: bool = False) -> str:
    sections = preview.get("sections", {}) if isinstance(preview, dict) else {}
    category_sections = sections.get("category_sections", []) if isinstance(sections, dict) else []
    category_count = len(category_sections)
    duration_minutes = int(preview.get("duration_target_minutes", 10) or 10) if isinstance(preview, dict) else 10
    seed = f"intro:{duration_minutes}:{category_count}"
    variants = [
        "Bonjour, voici votre point d'actualité du jour, en version claire et directe.",
        "Bienvenue dans ce bulletin express: l'essentiel des actualités en quelques minutes.",
        "Bonjour à tous, on démarre avec les informations à retenir dans cette édition rapide.",
        "Place au tour d'horizon du jour: les faits marquants, sans détour.",
        "Voici votre synthèse d'actualité: points clés, contexte utile et suite à surveiller.",
    ]
    return _pick_variant(variants, seed, randomize=randomize)


def _deterministic_conclusion(*, preview: dict[str, Any], randomize: bool = False) -> str:
    sections = preview.get("sections", {}) if isinstance(preview, dict) else {}
    category_sections = sections.get("category_sections", []) if isinstance(sections, dict) else []
    brief_count = sum(len(section.get("briefs", [])) for section in category_sections)
    seed = f"conclusion:{brief_count}:{len(category_sections)}"
    variants = [
        "C'était l'essentiel à retenir aujourd'hui. Rendez-vous au prochain point d'actualité.",
        "Fin de cette édition: on se retrouve très vite pour la prochaine mise à jour de l'actualité.",
        "C'est la fin de ce récap. Merci de votre écoute et à bientôt pour la suite des informations.",
        "On clôture ce bulletin ici. Prochain rendez-vous pour suivre l'évolution de ces sujets.",
        "Voilà pour les brèves du jour. À la prochaine édition pour un nouveau tour d'horizon.",
    ]
    return _pick_variant(variants, seed, randomize=randomize)


def _word_count(text: str) -> int:
    if not text:
        return 0
    return len([token for token in text.replace("\n", " ").split(" ") if token.strip()])


def _align_brief_text_length(
    text: str,
    *,
    category_name: str,
    title: str,
    source_title: str,
    target_words: int,
) -> str:
    # Keep a sane cap to avoid exploding script size on very high settings.
    safe_target_words = max(18, min(180, int(target_words)))
    aligned = text.strip()
    fillers = [
        "Le point a surveiller est l'effet concret sur les acteurs concernes dans les prochains jours.",
        "A court terme, l'enjeu est de verifier si cette annonce se traduit en decisions ou en resultats mesurables.",
        f"Dans la rubrique {category_name}, ce sujet ouvre un suivi utile pour confirmer la tendance observee.",
        "La prochaine etape sera de confronter cette information aux prochaines publications de reference.",
    ]

    filler_index = 0
    while _word_count(aligned) < safe_target_words and filler_index < 16:
        aligned = f"{aligned} {fillers[filler_index % len(fillers)]}".strip()
        filler_index += 1
    return aligned


def _pick_variant(variants: list[str], seed: str, *, randomize: bool = False) -> str:
    if not variants:
        return ""
    checksum = sum(ord(char) for char in (seed or ""))
    if randomize:
        # Keep selection stable-ish around content seed while allowing run-to-run variation.
        jitter = random.randint(0, len(variants) - 1)
        return variants[(checksum + jitter) % len(variants)]
    return variants[checksum % len(variants)]


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
    speech_rate_wpm = int(deterministic_global_settings.get("speech_rate_wpm", 155) or 155)
    extractive_rules = deterministic_global_settings.get("extractive_rules") or {}
    brief_seconds_target = int(extractive_rules.get("briefSecondsTarget", preview.get("brief_seconds", 45)) or 45)
    duration_alignment_enabled = bool(extractive_rules.get("durationAlignmentEnabled", False))
    intro_conclusion_randomized = bool(extractive_rules.get("introConclusionRandomized", True))
    words_per_brief_target = max(15, min(180, int((speech_rate_wpm * brief_seconds_target) / 60)))
    lines: list[str] = [_deterministic_intro(preview=preview, randomize=intro_conclusion_randomized)]
    sections = preview.get("sections", {})

    for index, category_section in enumerate(sections.get("category_sections", [])):
        category_id = category_section.get("category_id")
        category_name = category_section.get("category_name", "Categorie")
        settings = category_settings_map.get(category_id, {})
        templates = settings.get("templates") or {}
        lead_in_template = templates.get("leadIn") or templates.get("intro") or "En {category_name}, voici les informations a retenir."
        default_transition_templates = [
            "On passe au sujet suivant.",
            "On continue avec le point suivant.",
            "Autre information a retenir.",
            "Passons maintenant a la suite.",
            "On enchaine avec le prochain sujet.",
        ]
        transition_out_template = templates.get("transitionOut") or templates.get("transition")
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
            default_impact_templates = [
                "Fait du jour: {title}.",
                "A retenir aujourd'hui: {title}.",
                "Ce que dit l'actualité: {title}.",
                "Point de situation: {title}.",
                
                "Lecture rapide: {title}.",
                "En bref: {title}.",
                "A surveiller: {title}.",
                
                "Ce qu'il faut suivre : {title}.",
            ]
            default_impact_template = _pick_variant(
                default_impact_templates,
                f"{brief.get('item_key', '')}:{category_id}:{brief.get('title', '')}",
            )
            impact_line = _render_template(
                templates.get("impact") or default_impact_template,
                {
                    "category_name": category_name,
                    "title": brief.get("title", ""),
                    "source_title": brief.get("source_title", ""),
                    "link": brief.get("link", ""),
                },
            )
            if duration_alignment_enabled:
                impact_line = _align_brief_text_length(
                    impact_line,
                    category_name=category_name,
                    title=str(brief.get("title", "")),
                    source_title=str(brief.get("source_title", "")),
                    target_words=words_per_brief_target,
                )
            lines.append(impact_line)

        if index < len(sections.get("category_sections", [])) - 1:
            resolved_transition_template = transition_out_template or _pick_variant(
                default_transition_templates,
                f"{category_id}:{index}",
            )
            lines.append(
                _render_template(
                    resolved_transition_template,
                    {"category_name": category_name},
                )
            )

    if sections.get("conclusion") is not None:
        lines.append(
            _deterministic_conclusion(
                preview=preview,
                randomize=intro_conclusion_randomized,
            )
        )

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
            "effective_brief_seconds_target": brief_seconds_target,
            "duration_alignment_enabled": duration_alignment_enabled,
            "intro_conclusion_randomized": intro_conclusion_randomized,
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
    for attempt in range(1, attempts + 1):
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
            logger.warning(
                "Script generation provider request failed with HTTP error",
                extra={
                    "provider_api_url": api_url,
                    "provider_model": api_model,
                    "http_status": error.code,
                    "attempt": attempt,
                    "attempts_total": attempts,
                    "response_body_preview": body[:500],
                },
            )
        except URLError as error:
            last_error = f"Network error: {error.reason}"
            logger.warning(
                "Script generation provider request failed with network error",
                extra={
                    "provider_api_url": api_url,
                    "provider_model": api_model,
                    "attempt": attempt,
                    "attempts_total": attempts,
                    "network_reason": str(error.reason),
                },
            )
        except ScriptGenerationError:
            raise
        except Exception as error:  # pragma: no cover
            last_error = f"Unexpected error: {error}"
            logger.exception(
                "Unexpected script generation provider error",
                extra={
                    "provider_api_url": api_url,
                    "provider_model": api_model,
                    "attempt": attempt,
                    "attempts_total": attempts,
                },
            )

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
