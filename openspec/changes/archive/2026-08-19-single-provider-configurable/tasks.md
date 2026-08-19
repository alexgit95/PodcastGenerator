## 1. Runtime Policy

- [x] 1.1 Enforce a single active provider selection at startup/runtime.
- [x] 1.2 Add explicit runtime error when provider selection is missing or invalid.
- [x] 1.3 Ensure generation requests use only the selected provider path.

## 2. Configuration Contract

- [x] 2.1 Expose provider-agnostic fields for provider name, endpoint URL, API key, model, and pricing.
- [x] 2.2 Document provider switch procedure as configuration + restart/redeploy.
- [x] 2.3 Validate configuration values and emit actionable diagnostics.

## 3. Cost Guardrails Compatibility

- [x] 3.1 Keep per-episode token cap checks provider-independent.
- [x] 3.2 Keep monthly budget cap checks provider-independent.
- [x] 3.3 Ensure cost estimation uses active provider pricing fields.

## 4. Validation and Docs

- [x] 4.1 Add tests for single-provider execution behavior.
- [x] 4.2 Add tests for invalid provider configuration errors.
- [x] 4.3 Update operational docs to clarify no simultaneous multi-provider routing.
- [x] 4.4 Add complete provider selection and initialization documentation with at least two concrete provider examples.
