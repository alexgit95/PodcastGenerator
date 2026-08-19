## 1. Data Model and Configuration

- [x] 1.1 Define entities for categories, RSS sources, category-source mappings, generation profiles, and budget tracking.
- [x] 1.2 Add persistence schema and migrations for many-to-many mapping and source health metadata.
- [x] 1.3 Add configuration fields for duration target, category weights, per-episode token cap, and monthly budget cap.

## 2. Category and RSS Management UI

- [x] 2.1 Implement category CRUD views with enable/disable controls.
- [x] 2.2 Implement RSS source CRUD views with enable/disable controls.
- [x] 2.3 Implement category-to-source mapping UI with many-to-many assignment.
- [x] 2.4 Implement RSS source health check action and status display.

## 3. Collection and Composition Engine

- [x] 3.1 Implement RSS collection pipeline that filters items by 48-hour freshness.
- [x] 3.2 Implement multi-category weighted quota allocation and redistribution logic.
- [x] 3.3 Implement duplicate detection and cross-category de-duplication for selected items.
- [x] 3.4 Implement duration-target handling with configurable increase/decrease controls.
- [x] 3.5 Implement deterministic overflow trimming order: conclusion, transitions, lowest-priority briefs.

## 4. Low-Cost API Generation Guardrails

- [x] 4.1 Integrate economical French-capable API model for script generation.
- [x] 4.2 Enforce per-episode token cap with early stop and explicit blocked status.
- [x] 4.3 Enforce monthly spending cap with automatic generation lockout.
- [x] 4.4 Add retry and prompt-size limits to prevent cost drift.

## 5. Scheduling, Observability, and Validation

- [x] 5.1 Implement scheduling defaults for three episodes per week with operator override.
- [x] 5.2 Expose job status, budget status, and source health in operator-facing UI.
- [x] 5.3 Add automated tests for freshness filtering, weighted allocation, and overflow trimming behavior.
- [x] 5.4 Add automated tests for per-episode and monthly budget guardrails.
