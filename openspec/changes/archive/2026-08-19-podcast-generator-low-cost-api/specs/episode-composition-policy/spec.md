## ADDED Requirements

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

### Requirement: Enforce 48-hour freshness limit
The system MUST only use RSS items published or updated within the last 48 hours.

#### Scenario: Fresh item selected
- **WHEN** a source item is within 48 hours at collection time
- **THEN** the item is eligible for episode composition

#### Scenario: Stale item excluded
- **WHEN** a source item is older than 48 hours
- **THEN** the item is excluded from episode composition

### Requirement: Support configurable total episode duration
The system MUST allow operators to increase or decrease the episode duration target through the web interface.

#### Scenario: Increase target duration
- **WHEN** an operator raises the duration target
- **THEN** the next generated episodes use the new target value

#### Scenario: Decrease target duration
- **WHEN** an operator lowers the duration target
- **THEN** the next generated episodes use the reduced target value

### Requirement: Trim overflow using deterministic priority
The system MUST trim generated episode structure in this strict order when estimated duration exceeds the target: conclusion, transitions, then lowest-priority briefs.

#### Scenario: First overflow step
- **WHEN** estimated duration exceeds target
- **THEN** the system removes or shortens the conclusion before changing other sections

#### Scenario: Second overflow step
- **WHEN** overflow remains after conclusion trimming
- **THEN** the system removes or shortens transitions before reducing briefs
