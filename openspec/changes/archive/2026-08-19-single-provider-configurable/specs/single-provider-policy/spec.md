## ADDED Requirements

### Requirement: Exactly one LLM provider is active at runtime
The system MUST execute script generation against exactly one configured provider for a running instance.

#### Scenario: Valid active provider
- **WHEN** runtime configuration defines one provider selection
- **THEN** generation requests are executed only against that provider

#### Scenario: Missing provider selection
- **WHEN** runtime configuration has no valid provider selection
- **THEN** generation requests fail with a clear configuration error

### Requirement: No simultaneous multi-provider routing
The system MUST NOT send one generation request to multiple providers in parallel or sequence within the same request execution path.

#### Scenario: Generation request execution
- **WHEN** a script generation request is processed
- **THEN** only the configured provider path is used for that request

### Requirement: Provider switch is an operator configuration action
The system MUST treat provider changes as configuration updates requiring service restart or redeploy to take effect.

#### Scenario: Provider switch
- **WHEN** operator changes provider configuration
- **THEN** the service uses the new provider only after restart/redeploy
