## Why

The project needs a self-hosted podcast generation workflow on Raspberry Pi that stays extremely low cost while remaining usable in French. We also need an operator-friendly web interface to manage categories and RSS sources that feed each episode.

## What Changes

- Add a web UI to manage categories and RSS sources, including many-to-many category/source mapping.
- Add weighted multi-category episode composition from recent RSS items only.
- Add configurable total episode duration with deterministic overflow trimming rules.
- Add low-cost script generation through an economical French-capable API model, with strict cost guardrails.
- Add scheduling defaults for three episodes per week while allowing operator configuration.

## Capabilities

### New Capabilities
- `category-rss-management`: Manage categories, RSS sources, source health checks, and category-to-source mapping through a web UI.
- `episode-composition-policy`: Build multi-category episodes using weighted allocation, freshness limits, and duration control with deterministic trimming.
- `low-cost-script-generation`: Generate French scripts with an economical API and enforce token and budget caps to minimize recurring cost.

### Modified Capabilities
- None.

## Impact

- Affected systems: web UI, orchestration service, scheduling, and content selection pipeline.
- New dependency area: external LLM API for French script generation (economical tier).
- Data model impact: categories, RSS sources, mapping table, generation profile, and budget tracking.
- Operational impact: cost ceilings, article freshness filtering, and deterministic overflow handling.