## ADDED Requirements

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
