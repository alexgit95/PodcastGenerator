## MODIFIED Requirements

### Requirement: Generate French scripts with economical API tier
The system MUST generate episode scripts in French using a cost-optimized external API model tier through exactly one configured provider at runtime.

#### Scenario: French script generation
- **WHEN** a generation job is launched
- **THEN** the returned script is in French and follows the configured episode structure

#### Scenario: Single configured provider path
- **WHEN** a generation job is launched
- **THEN** the request is executed only through the currently configured provider and not routed simultaneously to multiple providers
