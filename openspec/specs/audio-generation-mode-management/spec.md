# audio-generation-mode-management Specification

## Purpose
TBD - created by archiving change audio-generation-mode-management. Update Purpose after archive.
## Requirements
### Requirement: Operator SHALL manage audio generation mode from the application settings UI
The system MUST expose settings controls that allow an operator to view and update the active audio generation mode between `local` and `cloud`.

#### Scenario: Switch audio mode in UI
- **WHEN** an operator selects a valid audio mode and saves settings
- **THEN** the profile is updated and subsequent audio generation jobs use the selected mode

### Requirement: Local audio generation SHALL use Piper for French TTS
The system MUST use Piper as the local text-to-speech engine when audio generation mode is `local`.

#### Scenario: Local mode generation
- **WHEN** an audio generation job runs in `local` mode
- **THEN** the system produces French speech using Piper

### Requirement: Local audio generation SHALL support configurable pauses between category sections
The system MUST support a deterministic global setting that controls how much silence is inserted between category sections in locally generated audio.

#### Scenario: Category pause enabled
- **WHEN** local audio generation receives a script with section boundaries and `extractive_rules.categoryPauseSeconds` is greater than `0`
- **THEN** the audio pipeline inserts silence of the configured duration between synthesized sections before producing the final MP3

#### Scenario: Category pause disabled
- **WHEN** `extractive_rules.categoryPauseSeconds` is `0`
- **THEN** the local audio pipeline skips inter-section silence insertion while still producing a valid MP3 artifact

### Requirement: Audio generation SHALL produce MP3 output
The system MUST produce a final MP3 file as the deliverable audio artifact for a generated episode.

#### Scenario: Successful audio generation
- **WHEN** an audio generation job completes successfully
- **THEN** the system stores an MP3 file and exposes its location through the job result or associated metadata

### Requirement: Generated MP3 SHALL be visible and downloadable from the script area in the admin UI
The system MUST display the generated MP3 artifact alongside the generated script area and provide a download action from the same screen.

#### Scenario: Download generated MP3
- **WHEN** an audio generation job completes successfully
- **THEN** the admin UI shows the MP3 artifact near the script output and allows the operator to download it without leaving the page

### Requirement: Audio mode SHALL remain independent from script mode
The system MUST allow audio generation mode to be configured independently from script generation mode.

#### Scenario: Mixed configuration
- **WHEN** script generation mode and audio generation mode are set to different values
- **THEN** the system applies both settings independently without forcing them to match

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

