## Why

We now want to generate an MP3 locally on Raspberry Pi when possible, while still allowing a cloud TTS fallback from the UI. The application currently stops at text generation, so we need a clear contract for the audio stage before implementation.

## What Changes

- Add an audio generation mode setting with two values: `local` and `cloud`.
- Add UI controls to choose the audio mode independently from the script generation mode.
- Define Piper as the preferred local TTS engine for French audio generation.
- Add a local audio output pipeline that produces MP3 files from the generated script.
- Expose the generated MP3 in the same admin area as the script so operators can download it immediately.
- Keep the cloud audio path as an optional alternative for operators who prefer external TTS.

## Capabilities

### New Capabilities
- `audio-generation-mode-management`: Runtime selection and UI management for local vs cloud audio generation.
- `local-audio-generation-pipeline`: Local TTS pipeline using Piper to produce MP3 output.

### Modified Capabilities
- `generation-mode-management`: Clarify that script generation mode is separate from audio generation mode.

## Impact

- Affected UI: new audio mode selector and status surface.
- Affected UI: generated MP3 download action next to the script output area.
- Affected backend: audio generation workflow, MP3 output handling, and job metadata.
- Affected dependencies: local TTS engine (Piper) and MP3 conversion tooling.
- Affected storage: audio file output directory/volume for generated MP3 episodes.
