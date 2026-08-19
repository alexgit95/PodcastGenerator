## 1. Scheduled Script+Audio Orchestration

- [x] 1.1 Define scheduled run contract with ordered stages: script then audio.
- [x] 1.2 Ensure audio stage executes only when script stage succeeds.
- [x] 1.3 Record stage-level success/failure metadata in generation jobs.
- [x] 1.4 For cloud mode without implementation, mark audio stage blocked with explicit reason.

## 2. Latest Audio Retrieval Contract

- [x] 2.1 Add backend lookup for latest successful audio job.
- [x] 2.2 Expose endpoint returning latest audio download metadata and status.
- [x] 2.3 Handle missing artifact files with explicit not-found response.

## 3. Admin UI Action

- [x] 3.1 Add button: "Recuperer le dernier audio genere".
- [x] 3.2 Display link/state for latest available audio artifact.
- [x] 3.3 Display clear fallback message when no audio is available.

## 4. Validation

- [x] 4.1 Add tests for scheduled script->audio success path.
- [x] 4.2 Add tests for scheduled audio blocked path in cloud mode.
- [x] 4.3 Add tests for latest-audio endpoint behavior.
- [x] 4.4 Run full test suite.
