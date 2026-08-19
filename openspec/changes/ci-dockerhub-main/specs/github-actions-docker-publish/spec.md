## ADDED Requirements

### Requirement: Validate pull requests targeting main
The system MUST run Python test validation on pull requests targeting the `main` branch.

#### Scenario: Pull request to main
- **WHEN** a pull request targets `main`
- **THEN** the workflow runs the Python test job and reports pass/fail status

### Requirement: Publish images only on push events
The system MUST run Docker image publication only for push events after successful test completion.

#### Scenario: Push after tests pass
- **WHEN** a push event occurs and the test job succeeds
- **THEN** the build-and-push job runs

#### Scenario: Pull request event
- **WHEN** the event is a pull request
- **THEN** the build-and-push job is skipped

### Requirement: Build ARM64 images for Raspberry Pi compatibility
The system MUST build and push images for `linux/arm64` using Buildx and QEMU.

#### Scenario: Docker build execution
- **WHEN** the build-and-push job executes
- **THEN** it configures QEMU and Buildx and builds the `linux/arm64` image

### Requirement: Apply deterministic tag policy
The system MUST apply event-based image tags with the following policy: non-main branch push uses sanitized branch name, push on `main` uses `latest`, and git tag push uses both `<git-tag>` and `latest`.

#### Scenario: Push on non-main branch
- **WHEN** a push is made to a branch other than `main`
- **THEN** the image is pushed with a sanitized branch tag

#### Scenario: Push on main branch
- **WHEN** a push is made to `main`
- **THEN** the image is pushed with `latest`

#### Scenario: Push of git tag
- **WHEN** a git tag is pushed
- **THEN** the image is pushed with both the git tag and `latest`

### Requirement: Authenticate to Docker Hub via repository secrets
The system MUST authenticate to Docker Hub using repository secrets before pushing images.

#### Scenario: Publish phase starts
- **WHEN** the build-and-push job starts
- **THEN** it logs in using `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets
