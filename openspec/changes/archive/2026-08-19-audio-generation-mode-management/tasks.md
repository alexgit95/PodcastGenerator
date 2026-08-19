## 1. Audio Mode Contract

- [x] 1.1 Add persisted audio generation mode with allowed values `local|cloud`.
- [x] 1.2 Add UI controls to select audio mode independently from script mode.
- [x] 1.3 Document that audio mode and script mode are separate settings.

## 2. Local Audio Pipeline

- [x] 2.1 Implement Piper-based French TTS for local audio generation.
- [x] 2.2 Convert local TTS output to MP3.
- [x] 2.3 Persist the MP3 file path or equivalent metadata in the audio job result.
- [x] 2.4 Add a download action for the generated MP3 in the same admin area that shows the script.

## 3. Cloud Fallback

- [x] 3.1 Define cloud audio generation configuration and dispatch.
- [x] 3.2 Allow switching between local and cloud audio without changing script mode.

## 4. Validation and Docs

- [x] 4.1 Add tests for audio mode switching behavior.
- [x] 4.2 Add tests for local MP3 generation metadata.
- [x] 4.3 Add tests for independent script/audio mode selection.
- [x] 4.4 Update operational docs to explain Piper, local MP3 output, and cloud fallback.
