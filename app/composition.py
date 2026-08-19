from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .rss_collection import CollectedItem


INTRO_SECONDS = 20
CONCLUSION_SECONDS = 40
TRANSITION_SECONDS = 10
BRIEF_SECONDS = 45


@dataclass
class Brief:
    item_key: str
    category_id: str
    category_name: str
    title: str
    link: str
    source_title: str
    published_at: datetime
    score: float


def _article_score(item: CollectedItem, now_utc: datetime) -> float:
    age_hours = max(0.0, (now_utc - item.published_at).total_seconds() / 3600.0)
    return max(0.0, 100.0 - age_hours)


def _allocate_initial_quota(weights: dict[str, int], budget_seconds: int) -> dict[str, int]:
    total_weight = sum(max(1, value) for value in weights.values())
    if total_weight == 0:
        return {key: 0 for key in weights}
    return {
        category_id: int((max(1, weight) / total_weight) * budget_seconds)
        for category_id, weight in weights.items()
    }


def _pick_briefs(
    items_by_category: dict[str, list[CollectedItem]],
    quota_seconds: dict[str, int],
) -> tuple[list[Brief], dict[str, int]]:
    now_utc = datetime.now(timezone.utc)
    used_keys: set[str] = set()
    selected: list[Brief] = []
    used_seconds_by_category: dict[str, int] = {key: 0 for key in quota_seconds}

    for category_id, items in items_by_category.items():
        target_seconds = quota_seconds.get(category_id, 0)
        for item in items:
            if used_seconds_by_category[category_id] + BRIEF_SECONDS > target_seconds:
                break
            if item.item_key in used_keys:
                continue
            used_keys.add(item.item_key)
            used_seconds_by_category[category_id] += BRIEF_SECONDS
            selected.append(
                Brief(
                    item_key=item.item_key,
                    category_id=item.category_id,
                    category_name=item.category_name,
                    title=item.title,
                    link=item.link,
                    source_title=item.source_title,
                    published_at=item.published_at,
                    score=_article_score(item, now_utc),
                )
            )

    return selected, used_seconds_by_category


def _redistribute_unused_quota(
    items_by_category: dict[str, list[CollectedItem]],
    weights: dict[str, int],
    selected: list[Brief],
    used_seconds_by_category: dict[str, int],
    budget_seconds: int,
) -> list[Brief]:
    used_keys = {brief.item_key for brief in selected}
    selected_by_category: dict[str, list[Brief]] = {}
    for brief in selected:
        selected_by_category.setdefault(brief.category_id, []).append(brief)

    consumed_seconds = len(selected) * BRIEF_SECONDS
    remaining_seconds = max(0, budget_seconds - consumed_seconds)
    now_utc = datetime.now(timezone.utc)

    while remaining_seconds >= BRIEF_SECONDS:
        candidates: list[tuple[float, str, CollectedItem]] = []
        for category_id, items in items_by_category.items():
            weight = max(1, weights.get(category_id, 1))
            for item in items:
                if item.item_key in used_keys:
                    continue
                score = _article_score(item, now_utc) + (weight * 0.01)
                candidates.append((score, category_id, item))
                break

        if not candidates:
            break

        candidates.sort(key=lambda row: row[0], reverse=True)
        _, category_id, item = candidates[0]
        used_keys.add(item.item_key)
        used_seconds_by_category[category_id] = used_seconds_by_category.get(category_id, 0) + BRIEF_SECONDS
        selected_by_category.setdefault(category_id, []).append(
            Brief(
            item_key=item.item_key,
                category_id=item.category_id,
                category_name=item.category_name,
                title=item.title,
                link=item.link,
                source_title=item.source_title,
                published_at=item.published_at,
                score=_article_score(item, now_utc),
            )
        )
        remaining_seconds -= BRIEF_SECONDS

    flattened: list[Brief] = []
    for category_id in sorted(selected_by_category.keys()):
        flattened.extend(selected_by_category[category_id])
    return flattened


def _build_sections(briefs: list[Brief]) -> dict[str, Any]:
    grouped: dict[str, list[Brief]] = {}
    category_names: dict[str, str] = {}
    for brief in briefs:
        grouped.setdefault(brief.category_id, []).append(brief)
        category_names[brief.category_id] = brief.category_name

    ordered_category_ids = [key for key in sorted(grouped.keys()) if grouped[key]]
    transitions = []
    for index in range(max(0, len(ordered_category_ids) - 1)):
        from_id = ordered_category_ids[index]
        to_id = ordered_category_ids[index + 1]
        transitions.append(
            {
                "from": category_names[from_id],
                "to": category_names[to_id],
                "estimated_seconds": TRANSITION_SECONDS,
            }
        )

    return {
        "intro": {"estimated_seconds": INTRO_SECONDS},
        "category_sections": [
            {
                "category_id": category_id,
                "category_name": category_names[category_id],
                "briefs": [
                    {
                        "title": brief.title,
                        "link": brief.link,
                        "source_title": brief.source_title,
                        "published_at": brief.published_at.isoformat(),
                        "estimated_seconds": BRIEF_SECONDS,
                        "score": round(brief.score, 2),
                    }
                    for brief in grouped[category_id]
                ],
            }
            for category_id in ordered_category_ids
        ],
        "transitions": transitions,
        "conclusion": {"estimated_seconds": CONCLUSION_SECONDS},
    }


def _estimate_total_seconds(sections: dict[str, Any]) -> int:
    intro = sections.get("intro", {}).get("estimated_seconds", 0)
    conclusion = sections.get("conclusion", {}).get("estimated_seconds", 0) if sections.get("conclusion") else 0
    transitions = sum(part.get("estimated_seconds", 0) for part in sections.get("transitions", []))
    briefs = 0
    for category_section in sections.get("category_sections", []):
        briefs += sum(item.get("estimated_seconds", 0) for item in category_section.get("briefs", []))
    return intro + transitions + conclusion + briefs


def _trim_overflow(sections: dict[str, Any], target_seconds: int) -> dict[str, Any]:
    trim_log: list[str] = []

    # 1) Trim conclusion first.
    if _estimate_total_seconds(sections) > target_seconds and sections.get("conclusion"):
        sections["conclusion"] = None
        trim_log.append("conclusion")

    # 2) Then trim transitions.
    while _estimate_total_seconds(sections) > target_seconds and sections.get("transitions"):
        sections["transitions"].pop()
        trim_log.append("transition")

    # 3) Then trim lowest-priority briefs.
    if _estimate_total_seconds(sections) > target_seconds:
        briefs_with_ref: list[tuple[float, int, int]] = []
        for section_index, category_section in enumerate(sections.get("category_sections", [])):
            for brief_index, brief in enumerate(category_section.get("briefs", [])):
                briefs_with_ref.append((float(brief.get("score", 0.0)), section_index, brief_index))

        briefs_with_ref.sort(key=lambda row: row[0])
        while _estimate_total_seconds(sections) > target_seconds and briefs_with_ref:
            _, section_index, brief_index = briefs_with_ref.pop(0)
            section = sections["category_sections"][section_index]
            if brief_index < len(section["briefs"]):
                section["briefs"].pop(brief_index)
                trim_log.append("low_priority_brief")
                # Rebuild references after mutation.
                briefs_with_ref = []
                for s_idx, cat_section in enumerate(sections.get("category_sections", [])):
                    for b_idx, brief in enumerate(cat_section.get("briefs", [])):
                        briefs_with_ref.append((float(brief.get("score", 0.0)), s_idx, b_idx))
                briefs_with_ref.sort(key=lambda row: row[0])

    sections["category_sections"] = [
        section for section in sections.get("category_sections", []) if section.get("briefs")
    ]

    sections["trim_log"] = trim_log
    return sections


def build_episode_preview(
    items_by_category: dict[str, list[CollectedItem]],
    category_weights: dict[str, int],
    duration_target_minutes: int,
) -> dict[str, Any]:
    target_seconds = max(60, duration_target_minutes * 60)

    active_category_ids = [category_id for category_id, items in items_by_category.items() if items]
    active_weights = {category_id: category_weights.get(category_id, 1) for category_id in active_category_ids}

    transitions_budget = max(0, (len(active_category_ids) - 1) * TRANSITION_SECONDS)
    fixed_budget = INTRO_SECONDS + CONCLUSION_SECONDS + transitions_budget
    content_budget = max(BRIEF_SECONDS, target_seconds - fixed_budget)

    quota = _allocate_initial_quota(active_weights, content_budget)
    selected, used_seconds_by_category = _pick_briefs(items_by_category, quota)
    selected = _redistribute_unused_quota(
        items_by_category,
        active_weights,
        selected,
        used_seconds_by_category,
        content_budget,
    )

    sections = _build_sections(selected)
    sections = _trim_overflow(sections, target_seconds)

    return {
        "duration_target_minutes": duration_target_minutes,
        "duration_target_seconds": target_seconds,
        "estimated_total_seconds": _estimate_total_seconds(sections),
        "quota_seconds_by_category": quota,
        "used_seconds_by_category": used_seconds_by_category,
        "sections": sections,
    }
