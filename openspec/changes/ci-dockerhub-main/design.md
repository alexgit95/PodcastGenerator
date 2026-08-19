## Context

The repository currently lacks a versioned Dockerfile and CI workflow for container publishing. The target runtime is Raspberry Pi, so ARM64 image output is mandatory. The team already uses a branch/tag based Docker publishing model in another project and wants the same behavior adapted for Python.

## Goals / Non-Goals

**Goals:**
- Define a CI workflow that runs tests before build-and-push.
- Publish Docker images to Docker Hub for `linux/arm64`.
- Use `main` as the reference branch for pull request validation and `latest` publication.
- Keep branch and tag image semantics consistent with the existing Java project pattern.
- Version the Dockerfile in the repository as build source-of-truth.

**Non-Goals:**
- Managing deployment from Docker Hub to production host.
- Building non-container artifacts.
- Introducing additional CI providers.

## Decisions

1. **Two-stage GitHub Actions pipeline**
   - Stage A: test job for Python unit tests.
   - Stage B: Docker build-and-push job that depends on test success and runs on push only.
   - Rationale: preserve quality gate before publication.

2. **Reference branch is `main`**
   - Pull request validation targets `main`.
   - Push on `main` publishes `latest` tag.
   - Rationale: explicit release branch policy.

3. **Tag strategy**
   - Branch push (non-main): publish `<sanitized-branch-name>`.
   - Push on `main`: publish `latest`.
   - Git tag push: publish `<git-tag>` and `latest`.
   - Rationale: parity with current team workflow and traceable builds.

4. **ARM64 build with Buildx and QEMU**
   - Configure QEMU + Buildx and build `linux/arm64` image.
   - Rationale: runtime compatibility with Raspberry Pi.

5. **Versioned Dockerfile requirement**
   - CI MUST use repository Dockerfile at workflow execution time.
   - Rationale: reproducibility and auditability.

## Risks / Trade-offs

- **[Risk] Missing Docker Hub secrets** -> Mitigation: document required secrets and fail fast in workflow.
- **[Risk] ARM64 build performance on hosted runners** -> Mitigation: keep image slim and add cache strategy later if needed.
- **[Risk] Branch name collisions after sanitization** -> Mitigation: keep deterministic sanitizer and optionally append short SHA in future iteration.
- **[Risk] `latest` overwritten by tags/main** -> Mitigation: keep this behavior explicit and documented as intended release policy.
