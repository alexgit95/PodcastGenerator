# provider-config-contract Specification

## Purpose
TBD - created by archiving change single-provider-configurable. Update Purpose after archive.
## Requirements
### Requirement: Provider configuration is provider-agnostic
The system MUST expose provider-agnostic configuration fields for provider name, API URL, API key, model, and pricing inputs, and MUST enforce these fields only when generation mode is `llm`.

#### Scenario: Configure non-OpenAI provider for LLM mode
- **WHEN** operator sets provider name, endpoint, key, model, and pricing for a non-OpenAI provider and mode is `llm`
- **THEN** the system accepts configuration and uses it for LLM generation requests

#### Scenario: Deterministic mode without provider credentials
- **WHEN** profile mode is `deterministic` and provider key/model fields are absent
- **THEN** deterministic generation remains available and provider validation does not block startup/runtime

#### Scenario: Configure non-OpenAI provider
- **WHEN** operator sets provider name, endpoint, key, model, and pricing for a non-OpenAI provider
- **THEN** the system accepts configuration and uses it for generation requests

### Requirement: Cost estimation uses configured provider pricing
The system MUST estimate request cost using pricing values configured for the active provider.

#### Scenario: Provider pricing change
- **WHEN** operator updates provider pricing fields
- **THEN** subsequent generation requests use updated pricing for budget checks and cost reporting

### Requirement: Operational documentation includes provider selection and initialization examples
The system MUST provide complete operational documentation explaining how to select the single active provider and initialize required configuration values, with at least two concrete examples.

#### Scenario: Operator needs initial setup guidance
- **WHEN** operator reads the runtime/provider documentation
- **THEN** it explains required fields, selection flow, and restart/redeploy step after configuration change

#### Scenario: Operator needs concrete configuration samples
- **WHEN** operator reads configuration examples
- **THEN** documentation includes at least two provider initialization examples with provider name, endpoint URL, model, and pricing fields

