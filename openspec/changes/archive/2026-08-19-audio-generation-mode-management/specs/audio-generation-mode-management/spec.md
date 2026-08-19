## ADDED Requirements

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
