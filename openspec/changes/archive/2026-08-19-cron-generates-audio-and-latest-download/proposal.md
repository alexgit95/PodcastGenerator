## Why

Operators want scheduled runs to produce a complete deliverable (script + audio), not script-only output. Today, audio generation is manually triggered from the UI, which breaks unattended cron workflows.

Additionally, operators need a direct way to retrieve the latest generated audio artifact, including artifacts produced by scheduled runs.

## What Changes

- Extend scheduled generation behavior so cron runs chain script generation then audio generation.
- Define clear success/failure semantics between script and audio stages.
- Add a UI action to retrieve the latest successful audio artifact regardless of origin (manual or cron).
- Add backend contract to resolve and expose the latest downloadable audio job.

## Capabilities

### Modified Capabilities
- `audio-generation-mode-management`: Scheduled flows must produce audio when script generation succeeds.
- `generation-mode-management`: Admin UI includes action to fetch latest audio artifact.

### New Capabilities
- `scheduled-audio-orchestration`: Deterministic orchestration and status handling for cron script+audio pipeline.

## Impact

- Affected backend: scheduled pipeline orchestration, latest-audio lookup endpoint/query.
- Affected UI: "Recuperer le dernier audio genere" action and status messaging.
- Affected jobs metadata: explicit stage traceability for script and audio outcomes.
- Affected tests: integration/behavior tests for cron orchestration and latest artifact retrieval.
