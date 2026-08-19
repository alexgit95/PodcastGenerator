## ADDED Requirements

### Requirement: Admin UI SHALL allow operators to fetch latest generated audio artifact
The admin UI MUST provide an action to retrieve the latest generated audio artifact, including artifacts produced by scheduled runs.

#### Scenario: Operator requests latest audio
- **WHEN** operator clicks "Recuperer le dernier audio genere"
- **THEN** UI resolves latest available audio metadata and displays a download action

#### Scenario: No audio available
- **WHEN** no latest audio can be resolved
- **THEN** UI displays a clear informational message without breaking other generation controls
