## ADDED Requirements

### Requirement: Operator SHALL manage generation mode from the application settings UI
The system MUST expose settings controls that allow an operator to view and update the active generation mode between `llm` and `deterministic`.

#### Scenario: Switch generation mode in UI
- **WHEN** an operator selects a valid mode and saves settings
- **THEN** the profile is updated and subsequent generation jobs use the selected mode

### Requirement: Generation mode SHALL be persisted and validated
The system MUST persist the selected generation mode and reject unsupported mode values.

#### Scenario: Invalid mode update
- **WHEN** an API request attempts to set a mode value outside `llm` and `deterministic`
- **THEN** the system rejects the request with a validation error and keeps previous mode

### Requirement: System SHALL expose deterministic settings management APIs
The system MUST provide API endpoints to read and update deterministic global settings and category-level overrides.

#### Scenario: Update deterministic category override
- **WHEN** an operator updates deterministic override values for a category
- **THEN** the system stores validated values for that category and applies them in later deterministic generation runs

### Requirement: New categories SHALL receive deterministic defaults
When a category is created, the system MUST create a deterministic category override record with default values so the UI has a baseline configuration available immediately.

#### Scenario: Create a new category
- **WHEN** an operator creates a new category
- **THEN** the system creates the category and a corresponding deterministic override record seeded with default values or explicit global fallbacks
