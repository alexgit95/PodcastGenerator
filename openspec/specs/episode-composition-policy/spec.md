# episode-composition-policy Specification

## Purpose
Define how episode composition budgets and filters content across categories before script generation.
## Requirements
### Requirement: Compose episodes from multiple categories
The system MUST generate each episode from multiple selected categories.

#### Scenario: Multi-category episode request
- **WHEN** an episode is generated with at least two active categories
- **THEN** the system includes content from all selected categories according to weighting rules

### Requirement: Allocate category contribution by weight
The system MUST allocate each category contribution using configurable per-category weights.

#### Scenario: Weighted allocation
- **WHEN** categories have configured weights
- **THEN** the system computes each category quota proportionally to its weight over the sum of active weights

#### Scenario: Missing quota due to sparse category
- **WHEN** a category cannot fill its quota with valid items
- **THEN** the system redistributes the unused quota across remaining categories proportionally

### Requirement: Enforce configurable freshness limit
The system MUST only use RSS items published or updated within the active freshness window.

#### Scenario: Fresh item selected
- **WHEN** a source item is within the active freshness window at collection time
- **THEN** the item is eligible for episode composition

#### Scenario: Stale item excluded
- **WHEN** a source item is older than the active freshness window
- **THEN** the item is excluded from episode composition

#### Scenario: Deterministic mode freshness source
- **WHEN** generation mode is `deterministic`
- **THEN** the active freshness window is read from deterministic global settings (`freshness_hours_max`)

#### Scenario: LLM mode freshness source
- **WHEN** generation mode is `llm`
- **THEN** the active freshness window is read from profile runtime settings (`max_item_age_hours`)

### Requirement: Support configurable total episode duration
The system MUST allow operators to increase or decrease the episode duration target through the web interface.

#### Scenario: Increase target duration
- **WHEN** an operator raises the duration target
- **THEN** the next generated episodes use the new target value

#### Scenario: Decrease target duration
- **WHEN** an operator lowers the duration target
- **THEN** the next generated episodes use the reduced target value

### Requirement: Support configurable per-article estimated duration
The system MUST support configurable estimated seconds per article for preview budgeting and per-brief estimated duration.

#### Scenario: Per-article duration configured
- **WHEN** an operator sets a deterministic per-article target duration
- **THEN** composition quota allocation and brief estimated seconds use this configured value

### Requirement: Trim overflow using deterministic priority
The system MUST trim generated episode structure in this strict order when estimated duration exceeds the target: conclusion, transitions, then lowest-priority briefs.

#### Scenario: First overflow step
- **WHEN** estimated duration exceeds target
- **THEN** the system removes or shortens the conclusion before changing other sections

#### Scenario: Second overflow step
- **WHEN** overflow remains after conclusion trimming
- **THEN** the system removes or shortens transitions before reducing briefs

