## MODIFIED Requirements

### Requirement: Generate French scripts with economical API tier
The system MUST generate episode scripts in French using the configured active generation mode, while keeping LLM generation available through exactly one configured provider at runtime.

#### Scenario: French script generation in LLM mode
- **WHEN** a generation job is launched and profile mode is `llm`
- **THEN** the returned script is in French and follows the configured episode structure using the single configured provider path

#### Scenario: French script generation in deterministic mode
- **WHEN** a generation job is launched and profile mode is `deterministic`
- **THEN** the returned script is in French and follows the configured episode structure without external LLM calls

#### Scenario: French script generation
- **WHEN** a generation job is launched
- **THEN** the returned script is in French and follows the configured episode structure

#### Scenario: Single configured provider path
- **WHEN** a generation job is launched
- **THEN** the request is executed only through the currently configured provider and not routed simultaneously to multiple providers

### Requirement: Enforce per-episode token cap
The system MUST enforce per-episode guardrails for generation requests and MUST block generation when estimated or actual usage exceeds the configured cap. The per-episode cap SHALL take precedence over any monthly projection or budget calculation.

#### Scenario: LLM job under cap
- **WHEN** profile mode is `llm` and estimated plus actual token usage remain within cap
- **THEN** the generation job completes normally

#### Scenario: LLM job over cap
- **WHEN** profile mode is `llm` and a generation step would exceed the per-episode token cap
- **THEN** the system stops additional provider calls and marks the job as budget-blocked

#### Scenario: Job under cap
- **WHEN** estimated and actual token usage remain within the per-episode cap
- **THEN** the generation job completes normally

#### Scenario: Job over cap
- **WHEN** a generation step would exceed the per-episode token cap
- **THEN** the system stops additional generation calls and marks the job as budget-blocked

### Requirement: Enforce monthly API budget cap
The system MUST enforce a configurable monthly API spending cap and MUST apply it consistently before generation in both modes. Monthly budget evaluation MAY use a simple projected cost calculation, but it MUST NOT override a per-episode cap breach.

#### Scenario: Budget available
- **WHEN** monthly spend is below configured cap
- **THEN** manual and scheduled jobs may proceed regardless of selected generation mode

#### Scenario: Budget exhausted
- **WHEN** monthly spend reaches or exceeds configured cap
- **THEN** the system blocks new generation jobs and exposes budget status in the UI

#### Scenario: Budget available
- **WHEN** monthly spend is below configured cap
- **THEN** scheduled and manual jobs may proceed

#### Scenario: Budget exhausted
- **WHEN** monthly spend reaches or exceeds configured cap
- **THEN** the system blocks new generation jobs and exposes budget status in the UI
