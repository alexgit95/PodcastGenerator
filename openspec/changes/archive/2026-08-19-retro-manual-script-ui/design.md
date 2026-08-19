## Context

The admin UI now includes a manual generation button and a script output panel with copy support. These behaviors are already in code and should be reflected in OpenSpec for future maintenance and testing.

## Goals / Non-Goals

**Goals:**
- Capture manual generation UI behavior as normative requirements.
- Capture script visibility and copy action behavior.

**Non-Goals:**
- Introduce new generation engines or API contracts.
- Change existing runtime/provider logic.

## Decisions

- Use a delta spec on `generation-mode-management` with ADDED requirements to avoid modifying existing requirement blocks.
- Keep this change documentation-only and retroactive.

## Risks / Trade-offs

- [Risk] Future code changes could diverge from requirements if not tested.
  -> Mitigation: Keep requirements scenario-driven so they are easy to test.
