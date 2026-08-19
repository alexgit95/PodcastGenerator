from __future__ import annotations


def is_prompt_cap_exceeded(estimated_prompt_tokens: int, per_episode_token_cap: int) -> bool:
    return estimated_prompt_tokens >= per_episode_token_cap


def is_monthly_budget_exhausted(spent_eur_cents: int, monthly_cap_eur_cents: int) -> bool:
    return spent_eur_cents >= monthly_cap_eur_cents


def would_exceed_monthly_budget(
    spent_eur_cents: int,
    request_cost_eur_cents: int,
    monthly_cap_eur_cents: int,
) -> bool:
    return (spent_eur_cents + request_cost_eur_cents) > monthly_cap_eur_cents
