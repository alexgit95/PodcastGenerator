## 1. Build Metadata Contract

- [x] 1.1 Add Dockerfile build arg for commit SHA.
- [x] 1.2 Persist commit SHA into runtime env variable.
- [x] 1.3 Wire GitHub Actions build step to pass `${{ github.sha }}`.

## 2. Backend Version Surface

- [x] 2.1 Add `GET /api/version` endpoint.
- [x] 2.2 Return stable payload with `commit_sha` and `commit_short` (fallback supported).

## 3. Admin UI Visibility

- [x] 3.1 Add header slot for version display.
- [x] 3.2 Load version metadata on page startup and render short SHA.
- [x] 3.3 Keep graceful fallback text if metadata is unavailable.

## 4. Validation

- [x] 4.1 Add/adjust tests for `/api/version`.
- [x] 4.2 Run full test suite.
