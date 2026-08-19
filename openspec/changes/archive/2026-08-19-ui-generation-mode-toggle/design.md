## Context

The current application has one generation path centered on LLM calls with provider configuration validated at startup. Product now requires a runtime switch in the UI to allow either LLM generation or deterministic non-LLM generation while preserving existing category weighting, freshness filtering, trimming behavior, and budget observability.

Constraints:
- Existing API consumers expect the current `/api/generate/script` contract.
- Cost guardrails (per-episode token cap and monthly spend cap) must remain predictable.
- Single-provider policy remains valid when mode is `llm`.
- Deterministic mode must work even when LLM credentials are absent.

## Goals / Non-Goals

**Goals:**
- Introduce a persisted generation mode: `llm` or `deterministic`.
- Add UI and APIs to read/update generation mode.
- Add deterministic script generation pipeline driven by a configurable matrix (global + per-category overrides).
- Keep one generation endpoint and return a mode marker for observability.
- Apply provider validation only when mode is `llm`.

**Non-Goals:**
- Building an automatic mode router or hybrid blended generation in a single request.
- Adding new external NLP/ML infrastructure in this first iteration.
- Redesigning category and RSS management flows.

## Decisions

### 1) Single endpoint, dual engine dispatch
- Decision: Keep `/api/generate/script` as the public generation endpoint and dispatch internally to either LLM engine or deterministic engine based on persisted mode.
- Rationale: Avoid API breaking change and reduce UI/API complexity.
- Alternative considered: Separate endpoints per mode. Rejected because it duplicates guardrail and job flow logic.

### 2) Persisted generation mode at profile level
- Decision: Add `generation_mode` to `generation_profiles` with allowed values `llm` and `deterministic`.
- Rationale: Mode belongs to operational profile settings and can be changed from UI without redeploy.
- Alternative considered: Environment variable only. Rejected because the user explicitly needs UI control.

### 3) Deterministic configuration split (global + category overrides)
- Decision: Store deterministic matrix in a global table and category override table.
- Rationale: Global defaults reduce duplication; category overrides support Tech/Sport/Monde customization.
- Alternative considered: One big JSON blob per profile. Rejected due to weak validation and harder selective updates.

### 4) Mode-aware provider validation
- Decision: Runtime provider checks remain strict for `llm`; deterministic mode bypasses provider key/url/model requirements.
- Rationale: Deterministic path must run without LLM credentials while preserving strict fail-fast behavior for LLM mode.
- Alternative considered: Always validate provider at startup. Rejected because it blocks deterministic-only deployments.

### 5) Shared guardrail framing with mode-specific cost behavior
- Decision: Keep the per-episode cap as the primary blocking guardrail. Monthly budget enforcement is derived by a simple cost projection or estimated spend calculation, but it must never override a per-episode cap breach.
- Rationale: Per-episode cap is the immediate execution constraint; monthly spend is a planning/operational constraint that should not mask an over-budget episode.
- Decision: Deterministic mode records zero external API spend and includes mode metadata.
- Rationale: Prevents accidental LLM charges in deterministic-only deployments while preserving observability.

## Risks / Trade-offs

- [Risk] Deterministic output quality may feel less natural than LLM output.
  -> Mitigation: Add configurable templates and category-level overrides; include documentation and defaults optimized for Tech/Sport/Monde.

- [Risk] Startup/runtime validation complexity increases.
  -> Mitigation: Centralize mode-aware validation in settings layer and cover with dedicated tests for invalid configurations.

- [Risk] Data model growth may complicate future migrations.
  -> Mitigation: Introduce explicit schema versioning field for deterministic settings and keep JSON fields constrained to scoped payloads.

- [Risk] Operators may confuse mode switch effects.
  -> Mitigation: UI help text and API response include `mode_used`; docs clarify immediate effect and restart expectations only for provider changes.

## Migration Plan

1. Add schema changes:
- `generation_profiles.generation_mode` with default `llm` and CHECK constraint.
- `deterministic_settings_global` table keyed by `profile_id`.
- `deterministic_settings_category` table keyed by (`profile_id`, `category_id`).

2. Seed deterministic global defaults for existing profiles.

3. Add repository methods and API routes for mode and deterministic settings.

4. Seed a default deterministic category override row when a new category is created so the UI always has an editable baseline for Tech/Sport/Monde-style configuration.

5. Implement deterministic generation engine and dual-mode dispatcher.

6. Update UI settings views and forms.

7. Rollout:
- Deploy migration first.
- Deploy application update.
- Keep default mode `llm` to preserve current behavior.

Rollback:
- Switch profile mode back to `llm` if deterministic path has issues.
- If full rollback required, use schema rollback script to remove new deterministic tables and reconstruct `generation_profiles` without the new column.

## Open Questions

- Should deterministic jobs consume per-episode cap as a hard text-size budget (character/token estimate) or be excluded from token cap semantics entirely?
- Should mode changes be audit-logged in generation jobs or a dedicated settings history table?
- Do we want per-profile presets for category matrices (for example, weekday vs weekend format) in scope now or later?
