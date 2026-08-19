## ADDED Requirements

### Requirement: System SHALL expose build commit metadata through API
The system MUST provide a read-only endpoint that returns build commit metadata for runtime introspection.

#### Scenario: Commit metadata available
- **WHEN** build metadata env variables are set
- **THEN** `GET /api/version` returns `commit_sha` and `commit_short` derived from build metadata

#### Scenario: Commit metadata unavailable
- **WHEN** build metadata env variables are missing
- **THEN** `GET /api/version` returns fallback values and still responds successfully

### Requirement: Admin UI SHALL display current build commit in header
The admin configuration page MUST show a visible build version marker in the top header area.

#### Scenario: Header commit display
- **WHEN** the admin page loads
- **THEN** the UI calls the version API and renders the short commit SHA in the header

#### Scenario: Header fallback display
- **WHEN** version API data is unavailable or unknown
- **THEN** the UI renders a fallback label without blocking other page features
