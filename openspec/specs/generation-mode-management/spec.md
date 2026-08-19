# generation-mode-management Specification

## Purpose
TBD - created by archiving change ui-generation-mode-toggle. Update Purpose after archive.
## Requirements
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

### Requirement: Operator SHALL trigger manual script generation from the admin UI
The system MUST provide a manual generation action in the admin UI that invokes script generation without waiting for schedule execution.

#### Scenario: Manual generation trigger
- **WHEN** an operator clicks the manual generation action in the UI
- **THEN** the system sends a generation request and returns generation result status to the UI

### Requirement: Generated script SHALL be visible and copyable in the admin UI
The system MUST display the generated script text in the admin UI and MUST provide a copy action to copy the script content to clipboard.

#### Scenario: Display generated script
- **WHEN** manual generation succeeds
- **THEN** the UI shows the generated script text with associated run metadata

#### Scenario: Copy generated script
- **WHEN** an operator clicks the copy action for the generated script
- **THEN** the script text is copied to clipboard or a clear error message is displayed if clipboard permissions fail

