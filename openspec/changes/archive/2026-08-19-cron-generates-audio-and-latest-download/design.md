## Context

The application currently supports manual script generation and manual audio generation. Scheduling settings exist, but operators now require unattended execution to produce audio artifacts as part of scheduled runs.

A complete scheduled run must therefore perform:
1) script generation
2) audio generation (if script succeeded)

Operators also need a simple and reliable way to retrieve the latest generated audio, including cron-produced files.

## Goals / Non-Goals

**Goals:**
- Cron produces script and then audio in one run flow.
- Script success and audio success/failure are independently visible.
- UI button retrieves the latest successful audio artifact.

**Non-Goals:**
- Redesigning scheduling UX.
- Supporting multiple queued audio artifact versions in one-click UI picker.
- Implementing cloud audio synthesis internals if still unavailable.

## Decisions

### 1) Scheduled flow is two-stage and ordered
- Decision: execute audio stage only after script stage succeeds.
- Rationale: audio stage requires script text.

### 2) Failure isolation between stages
- Decision: script success remains valid even if audio stage fails.
- Rationale: preserves useful output and diagnostic clarity.

### 3) Latest audio retrieval uses successful audio jobs only
- Decision: "latest audio" targets the most recent `audio_generation` job with `succeeded` status and downloadable artifact.
- Rationale: avoids broken links and ambiguous error states.

### 4) Audio mode policy in scheduled runs
- Decision: scheduled behavior respects configured audio mode.
- Local mode: generate MP3 locally.
- Cloud mode (if not implemented): mark audio stage as blocked with explicit reason while keeping script success.
- Rationale: consistent runtime contract with current mode semantics.

## Risks / Trade-offs

- [Risk] Cron run latency increases due to audio generation step.
  -> Mitigation: expose stage-level status and duration in jobs metadata.

- [Risk] Latest-audio lookup can fail if artifact file was purged while job exists.
  -> Mitigation: API returns explicit "not found" result and UI fallback message.

- [Risk] Cloud mode may be configured without implementation support.
  -> Mitigation: explicit blocked status and operator-visible reason.

## Migration Plan

1. Add backend orchestration for scheduled script->audio chain.
2. Add latest-audio lookup contract and endpoint.
3. Add UI button + state messages for latest-audio retrieval.
4. Add tests for successful chain, blocked cloud stage, and latest-audio retrieval.

Rollback:
- Disable scheduled audio stage while retaining script scheduling.
- Keep latest-audio endpoint/UI action dormant behind feature toggle if needed.
