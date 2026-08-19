## 1. Workflow Foundation

- [x] 1.1 Create GitHub Actions workflow file for CI/CD triggers (push branches/tags and PR to main).
- [x] 1.2 Add Python setup and dependency installation step in the test job.
- [x] 1.3 Add Python unit test execution step and artifact upload on failure/success.

## 2. Docker Publish Pipeline

- [x] 2.1 Add Docker Hub login using `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets.
- [x] 2.2 Add QEMU and Buildx setup for `linux/arm64` image build.
- [x] 2.3 Add branch tag sanitization logic for non-main branch pushes.
- [x] 2.4 Add push rules for non-main branch tag, `main` as `latest`, and git tag as `<tag>` + `latest`.

## 3. Dockerfile Versioning

- [x] 3.1 Add repository Dockerfile suitable for application runtime.
- [x] 3.2 Ensure workflow builds from versioned Dockerfile in repository root.
- [x] 3.3 Document Docker Hub secret prerequisites and expected tags in project docs.

## 4. Validation

- [x] 4.1 Validate OpenSpec change after workflow and Dockerfile updates.
- [x] 4.2 Run CI dry run checks (lint/tests locally where feasible) before merge.
