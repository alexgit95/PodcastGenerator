## Context

The current project must remain cost-focused and operationally simple. We need the flexibility to use a provider other than OpenAI, but we do not want concurrent multi-provider logic.

## Goals / Non-Goals

**Goals:**
- Enforce one active provider at runtime.
- Allow provider selection through configuration.
- Preserve existing budget controls regardless of provider.
- Keep provider switching operationally simple (configuration + restart/redeploy).

**Non-Goals:**
- Simultaneous multi-provider routing.
- Automatic cross-provider failover.
- Weighted quality/cost dynamic routing.

## Decisions

1. **Single active provider contract**
   - Runtime MUST resolve exactly one provider configuration as active.
   - If provider configuration is invalid, generation requests fail fast with explicit error.

2. **Provider-agnostic settings model**
   - Configuration remains brand-agnostic through provider name, endpoint URL, API key, model, and pricing fields.
   - This keeps cost estimation reusable when changing provider.

3. **No cross-provider runtime routing**
   - Request path uses only the configured provider.
   - Provider switching is a deployment/configuration operation, not a per-request router decision.

4. **Cost guardrails remain first-class**
   - Per-episode token cap and monthly budget checks remain mandatory and provider-independent.

## Risks / Trade-offs

- **[Risk] Provider outage blocks generation** -> Mitigation: operator can switch provider via configuration and restart/redeploy.
- **[Risk] Manual provider switch mistakes** -> Mitigation: add configuration validation and clear startup diagnostics.
- **[Risk] Pricing drift per provider** -> Mitigation: keep pricing fields explicit and update operational docs when provider changes.
