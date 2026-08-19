## Why

The manual script generation and copy workflow was implemented in the UI but was not explicitly captured in OpenSpec requirements. We need a retroactive spec update so behavior stays visible and testable.

## What Changes

- Add requirements for manual script generation controls in the admin UI.
- Add requirements for displaying generated script content and copy-to-clipboard support.
- Record this as a spec-only retroactive update (no new implementation work).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `generation-mode-management`: Add explicit requirements for manual generation trigger, script visibility, and copy action in the UI.

## Impact

- Affected OpenSpec artifacts: generation-mode-management spec only.
- No code changes required in this retroactive change.
