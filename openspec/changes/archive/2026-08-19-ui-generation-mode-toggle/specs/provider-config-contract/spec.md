## MODIFIED Requirements

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
