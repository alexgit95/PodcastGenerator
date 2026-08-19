## ADDED Requirements

### Requirement: Deterministic generation SHALL produce a complete French episode script without external LLM calls
When generation mode is `deterministic`, the system MUST assemble the final script from collected content using deterministic selection and templates, without issuing external LLM API requests.

#### Scenario: Deterministic generation request
- **WHEN** a generation job is launched and profile mode is `deterministic`
- **THEN** the system returns a French script assembled from deterministic rules and no LLM provider call is executed

### Requirement: Deterministic generation SHALL support matrix configuration with global defaults and category overrides
The system MUST support deterministic matrix settings at profile level and category-level overrides for weighting, item count limits, and editorial templates.

#### Scenario: Category override present
- **WHEN** deterministic generation runs for a category with override values
- **THEN** override values are applied for that category and global defaults are used for missing fields

### Requirement: Deterministic generation SHALL preserve composition constraints
The system MUST enforce configured duration target, freshness limit, and trim order while composing deterministic scripts.

#### Scenario: Deterministic output overflow
- **WHEN** assembled deterministic output exceeds target duration budget
- **THEN** the system trims content using configured priority order until the output is within allowed bounds
