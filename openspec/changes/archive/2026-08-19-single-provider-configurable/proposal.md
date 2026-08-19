## Why

The project needs explicit control over LLM integration complexity and recurring cost. We want one active provider at runtime, configurable by operator choice, without simultaneous multi-provider routing.

## What Changes

- Define a single-provider runtime policy where exactly one provider is active at a time.
- Define provider-agnostic configuration fields so the selected provider is not necessarily OpenAI.
- Keep existing budget guardrails (per-episode token cap and monthly budget cap) independent from provider brand.
- Prohibit simultaneous multi-provider request routing and automatic cross-provider fallback in this phase.

## Capabilities

### New Capabilities
- `single-provider-policy`: Runtime contract enforcing one and only one active LLM provider.
- `provider-config-contract`: Configuration contract for selecting provider endpoint/model/pricing without code-level provider coupling.

### Modified Capabilities
- `low-cost-script-generation`: Clarify that generation uses one configured provider at runtime and does not route simultaneously across providers.

## Impact

- Affected systems: runtime settings, script generation flow, operational documentation.
- Operational impact: provider switch happens via configuration and restart/redeploy.
- Scope control: avoids multi-provider orchestration complexity while preserving cost controls.