## Why

The project needs a reproducible CI/CD path to test Python code and publish ARM64 Docker images to Docker Hub for Raspberry Pi deployment. A versioned Dockerfile and `main` as the reference branch are required to standardize build behavior and release tagging.

## What Changes

- Add a GitHub Actions workflow for Python test execution on pull requests targeting `main`.
- Add a GitHub Actions workflow stage to build and push Docker images to Docker Hub on push events.
- Add deterministic image tagging policy for branch pushes, `main`, and git tags.
- Add explicit multi-arch build setup focused on `linux/arm64`.
- Add a versioned Dockerfile in the repository and make CI depend on it.

## Capabilities

### New Capabilities
- `github-actions-docker-publish`: CI workflow that runs tests and publishes Docker images to Docker Hub with branch/main/tag logic.
- `versioned-dockerfile-contract`: Repository-level Dockerfile contract required by CI build-and-push steps.

### Modified Capabilities
- None.

## Impact

- Affected systems: GitHub Actions, Docker Hub registry, repository build conventions.
- New operational dependencies: Docker Hub secrets in repository settings.
- Release impact: image tagging semantics become standardized (`branch`, `latest`, git tag).