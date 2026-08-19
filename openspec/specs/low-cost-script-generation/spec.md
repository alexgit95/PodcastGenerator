# low-cost-script-generation Specification

## Purpose
TBD - created by archiving change podcast-generator-low-cost-api. Update Purpose after archive.
## Requirements
### Requirement: Generate French scripts with economical API tier
The system MUST generate episode scripts in French using a cost-optimized external API model tier through exactly one configured provider at runtime.

#### Scenario: French script generation
- **WHEN** a generation job is launched
- **THEN** the returned script is in French and follows the configured episode structure

#### Scenario: Single configured provider path
- **WHEN** a generation job is launched
- **THEN** the request is executed only through the currently configured provider and not routed simultaneously to multiple providers

### Requirement: Enforce per-episode token cap
The system MUST enforce a maximum token budget per generation job.

#### Scenario: Job under cap
- **WHEN** estimated and actual token usage remain within the per-episode cap
- **THEN** the generation job completes normally

#### Scenario: Job over cap
- **WHEN** a generation step would exceed the per-episode token cap
- **THEN** the system stops additional generation calls and marks the job as budget-blocked

### Requirement: Enforce monthly API budget cap
The system MUST enforce a configurable monthly API spending cap.

#### Scenario: Budget available
- **WHEN** monthly spend is below configured cap
- **THEN** scheduled and manual jobs may proceed

#### Scenario: Budget exhausted
- **WHEN** monthly spend reaches or exceeds configured cap
- **THEN** the system blocks new generation jobs and exposes budget status in the UI

### Requirement: Keep default generation cadence at three episodes per week
The system MUST support scheduling and set a default cadence of three episodes per week.

#### Scenario: Default schedule
- **WHEN** a new generation profile is created without custom cadence
- **THEN** the system schedules three episodes per week by default

#### Scenario: Custom schedule
- **WHEN** an operator changes schedule settings
- **THEN** the system uses the custom cadence for future jobs

