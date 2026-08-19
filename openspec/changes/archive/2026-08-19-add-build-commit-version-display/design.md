## Context

The admin page is the primary operational interface. Operators need to quickly identify which Git revision is running, especially after deployments and during bug triage.

The chosen approach is build-time metadata injection, because production containers generally do not include the `.git` directory.

## Goals / Non-Goals

**Goals:**
- Show a commit identifier in the admin header.
- Ensure metadata is available in Docker/CI deployments.
- Keep local development behavior safe (`unknown` fallback).

**Non-Goals:**
- Full release management UI.
- Git tag/changelog browsing in UI.
- Runtime shelling out to `git` in production.

## Decisions

### 1) Build-time commit injection (CI)
- Decision: pass Git SHA from workflow to Docker build args.
- Rationale: deterministic and portable in containerized runtime.

### 2) Dockerfile env contract
- Decision: promote build arg to runtime env (`PODCAST_BUILD_COMMIT_SHA`).
- Rationale: backend can read this directly without filesystem assumptions.

### 3) Backend API for UI consumption
- Decision: add `GET /api/version` returning commit metadata.
- Rationale: UI stays decoupled from build internals and can be extended later.

### 4) Header display with fallback
- Decision: show short SHA in header; fallback to `unknown`.
- Rationale: always renders meaningful status, avoids blank or broken UI.

## Risks / Trade-offs

- [Risk] Local runs outside CI may not set commit env.
  -> Mitigation: fallback to `unknown` and keep endpoint stable.

- [Risk] Workflow drift could forget build arg in future edits.
  -> Mitigation: include this in CI contract spec and tests/inspection checklist.

## Migration Plan

1. Add Dockerfile build arg/env for commit SHA.
2. Pass SHA from GitHub Actions Docker build step.
3. Add backend version endpoint.
4. Render commit short SHA in admin header.

Rollback:
- Remove header rendering while keeping endpoint non-breaking.
- Revert build arg wiring without impacting core app flows.
