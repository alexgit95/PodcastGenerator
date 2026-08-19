## Why

The application currently depends on an LLM path for script generation, while product direction now requires a user-selectable non-LLM mode to minimize cost and remove provider dependency when needed. We need a clear runtime contract so operators can switch mode from the UI without breaking existing guardrails.

## What Changes

- Add a generation mode setting with two values: `llm` and `deterministic`.
- Add UI controls to view and update the active generation mode.
- Add deterministic (non-LLM) script generation behavior based on extractive selection plus editorial templates.
- Add deterministic configuration storage (global matrix and per-category overrides) and APIs to manage it.
- Keep existing budget and token guardrails behavior consistent across modes, while applying LLM provider validation only when mode is `llm`.
- Record the effective mode used for each generation job for observability.

## Capabilities

### New Capabilities
- `deterministic-script-generation`: Non-LLM script generation contract, including matrix-based timing/scoring and category overrides.
- `generation-mode-management`: Runtime mode selection and configuration APIs/UI for switching between `llm` and `deterministic`.

### Modified Capabilities
- `low-cost-script-generation`: Generation flow now supports two execution paths and must expose which path was used.
- `provider-config-contract`: Provider validation becomes mode-aware (strict in `llm`, bypassed in deterministic mode).

## Impact

- Affected backend modules: main routing, script generation services, runtime settings validation, repository/data access layer.
- Affected database schema: generation profile mode + deterministic configuration tables.
- Affected UI: settings surface for generation mode and deterministic matrix/category overrides.
- Affected docs/tests: operational runbook, API usage, unit/integration tests for both modes and configuration validation.
