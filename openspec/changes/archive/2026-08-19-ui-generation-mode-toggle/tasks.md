## 1. Data Model and Persistence

- [x] 1.1 Add `generation_mode` to generation profiles with allowed values `llm|deterministic` and default `llm`.
- [x] 1.2 Create deterministic global settings persistence with validated defaults.
- [x] 1.3 Create deterministic category override persistence keyed by profile and category.
- [x] 1.4 Add repository methods to read/write mode, global deterministic settings, and category overrides.
- [x] 1.5 Seed default deterministic override rows when new categories are created.

## 2. Runtime and Generation Flow

- [x] 2.1 Refactor generation path to dispatch to `llm` or `deterministic` engine from one endpoint.
- [x] 2.2 Implement deterministic script assembly using extractive selection plus templates and existing composition constraints.
- [x] 2.3 Keep guardrail checks consistent and mode-safe (monthly cap always checked, LLM token/provider checks only for LLM path).
- [x] 2.4 Persist `mode_used` and relevant mode-specific metadata in generation job details.

## 3. Configuration Validation

- [x] 3.1 Make provider validation conditional on active mode so deterministic mode runs without provider credentials.
- [x] 3.2 Validate deterministic global settings ranges and required fields.
- [x] 3.3 Validate deterministic category override values and merge behavior with global defaults.

## 4. API and UI Settings

- [x] 4.1 Add API endpoints to read/update generation mode.
- [x] 4.2 Add API endpoints to read/update deterministic global settings and category overrides.
- [x] 4.3 Add UI controls to switch mode between LLM and deterministic.
- [x] 4.4 Add UI forms for deterministic matrix configuration and per-category overrides (Tech/Sport/Monde ready).

## 5. Test and Documentation

- [x] 5.1 Add tests for mode switching behavior and endpoint dispatch.
- [x] 5.2 Add tests for deterministic generation without LLM credentials.
- [x] 5.3 Add tests for validation errors on invalid mode/deterministic settings payloads.
- [x] 5.4 Update operational docs to explain how to use the new mode switch, how to configure the deterministic matrix and category overrides, and how to troubleshoot both modes.
