## Context

The application already generates French scripts and exposes UI controls for script mode. The missing piece is the audio stage: operators want to choose between a lightweight local TTS path and a cloud TTS path from the same interface.

On Raspberry Pi, the local path must be practical. Piper is the best fit because it is lightweight, fast enough for constrained hardware, and has usable French voices.

## Goals / Non-Goals

**Goals:**
- Separate audio generation mode from script generation mode.
- Use Piper as the preferred local TTS engine.
- Produce MP3 output locally.
- Surface the generated MP3 in the same admin area as the script output so it can be downloaded immediately.
- Allow a cloud audio path as a configurable alternative.

**Non-Goals:**
- Redesigning script generation.
- Implementing podcast feed publication in this change.
- Supporting multiple local TTS engines at once.

## Decisions

### 1) Separate script and audio modes
- Decision: Treat script generation and audio generation as two independent settings.
- Rationale: Operators may want different combinations, such as local script + cloud audio or LLM script + local audio.
- Alternative considered: one combined mode. Rejected because it couples unrelated concerns.

### 2) Piper for local French TTS
- Decision: Use Piper as the default local TTS engine.
- Rationale: It is lightweight and fits Raspberry Pi constraints better than heavier local TTS stacks.
- Alternative considered: Coqui TTS. Rejected for this target because it is heavier operationally.

### 3) MP3 as final output
- Decision: Convert local TTS output to MP3 for the final user-facing artifact.
- Rationale: MP3 is the most practical delivery format for podcast playback and storage.
- Alternative considered: exposing only WAV. Rejected because it is less convenient for distribution.

### 4) MP3 download in script area
- Decision: Show the generated MP3 in the same admin area that already displays the generated script.
- Rationale: This keeps the operator flow in one place and makes it obvious where to retrieve the episode artifact.

### 5) Cloud audio remains optional
- Decision: Keep a cloud TTS path available as an operator choice.
- Rationale: Some deployments may prioritize quality or convenience over full locality.

## Risks / Trade-offs

- [Risk] Local French voice quality may vary by Piper model.
  -> Mitigation: document the recommended French voice/model and keep cloud fallback available.

- [Risk] MP3 conversion adds an extra dependency.
  -> Mitigation: isolate conversion as a separate step and keep output path explicit.

- [Risk] Users may confuse script mode and audio mode.
  -> Mitigation: UI labels and docs must keep both modes visually separate.

## Migration Plan

1. Add a new audio mode setting and persistence.
2. Expose audio mode controls in the UI.
3. Implement Piper-based local TTS pipeline.
4. Add MP3 output storage and job metadata.
5. Keep cloud path available as fallback.

Rollback:
- Switch audio mode back to cloud if the local path is not stable.
- Disable the local Piper path without impacting script generation.
