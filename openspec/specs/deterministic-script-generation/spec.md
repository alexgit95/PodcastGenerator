# deterministic-script-generation Specification

## Purpose
Define deterministic script generation behavior and configurable controls used to tune item density and output length without external LLM calls.
## Requirements
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

### Requirement: Deterministic matrix SHALL expose configurable per-item duration target
The system MUST support a deterministic global setting that defines target seconds per article (`briefSecondsTarget`) and MUST apply it in composition preview budgeting.

#### Scenario: Operator sets seconds per article
- **WHEN** an operator updates deterministic global settings with `extractive_rules.briefSecondsTarget`
- **THEN** preview composition uses this value to compute category quotas and per-brief estimated duration

#### Scenario: Invalid seconds per article rejected
- **WHEN** `extractive_rules.briefSecondsTarget` is outside supported bounds
- **THEN** the system rejects the update with a validation error

### Requirement: Deterministic generation SHALL support optional duration alignment in script text
The system MUST support an optional deterministic setting (`extractive_rules.durationAlignmentEnabled`) that expands deterministic brief text to better match configured per-item duration.

#### Scenario: Alignment enabled
- **WHEN** `durationAlignmentEnabled` is true during deterministic generation
- **THEN** generated brief text is expanded toward the target words derived from speech rate and seconds per article

#### Scenario: Alignment disabled
- **WHEN** `durationAlignmentEnabled` is false
- **THEN** deterministic generation uses base templates without alignment-driven expansion

### Requirement: Deterministic freshness limit SHALL follow matrix global settings
When generation mode is `deterministic`, the freshness filter used for item collection MUST use deterministic global freshness (`freshness_hours_max`).

#### Scenario: Deterministic freshness applied
- **WHEN** deterministic composition starts
- **THEN** source items older than `freshness_hours_max` are excluded from eligibility

