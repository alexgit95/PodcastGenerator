## ADDED Requirements

### Requirement: Audio generation mode SHALL support scheduled audio production
Scheduled runs MUST produce audio artifacts when script generation succeeds and audio mode allows execution.

#### Scenario: Scheduled run in local audio mode
- **WHEN** a scheduled run generates a script successfully and `audio_generation_mode` is `local`
- **THEN** the system runs local audio generation and stores a downloadable MP3 artifact

#### Scenario: Scheduled run in cloud mode without implementation
- **WHEN** a scheduled run generates a script successfully and `audio_generation_mode` is `cloud` but cloud synthesis is unavailable
- **THEN** the system marks audio stage as blocked with explicit reason and keeps script stage as succeeded

### Requirement: System SHALL expose latest successful audio artifact
The system MUST provide a stable way to retrieve metadata for the latest successful downloadable audio artifact.

#### Scenario: Latest audio exists
- **WHEN** at least one audio generation job has succeeded and its file exists
- **THEN** latest-audio retrieval returns job id, mode used, file name, and download URL

#### Scenario: No latest audio available
- **WHEN** no successful audio job exists or artifact file is missing
- **THEN** latest-audio retrieval returns an explicit unavailable/not-found status suitable for UI feedback
