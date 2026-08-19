## Context

We are building a self-hosted podcast generator running in containers on Raspberry Pi. The primary business constraint is minimizing recurring cost. The product must support French script generation while letting operators manage content sources by category from a web interface.

## Goals / Non-Goals

**Goals:**
- Provide a graphical interface to manage categories and RSS sources.
- Support many-to-many mapping between categories and RSS sources.
- Generate multi-category episodes from fresh content only (max 48h old).
- Allow operators to increase or decrease total episode duration target.
- Enforce low-cost operation through API budget and token caps.
- Apply deterministic trimming when generated content exceeds duration target.

**Non-Goals:**
- Real-time live streaming.
- Fully autonomous publishing without operator review.
- Premium high-cost model tiers for script generation.

## Decisions

1. **Economical API for French script generation**
   - We will use a cost-optimized model tier that supports French.
   - Rationale: best quality/cost balance versus fully local generation on Pi.
   - Alternative considered: fully local LLM/TTS composition. Rejected due to lower quality and higher operational complexity on constrained hardware.

2. **Episode composition is weighted multi-category**
   - Each category has a configurable weight used to allocate duration or word budget.
   - Rationale: reflects editorial priorities while keeping automatic balancing.
   - Alternative considered: equal distribution. Rejected because it cannot express editorial priorities.

3. **Freshness hard limit of 48 hours**
   - Only RSS items newer than 48 hours are eligible.
   - Rationale: keeps episodes timely and reduces processing of stale data.
   - Alternative considered: no strict freshness. Rejected due to reduced relevance.

4. **Configurable episode duration target**
   - Operators can increase or decrease target duration from the web UI.
   - Default target remains 10 minutes for cost control.
   - Rationale: operational flexibility while keeping low-cost defaults.

5. **Deterministic overflow trimming policy**
   - Trim order on overflow: conclusion first, then transitions, then lowest-priority briefs.
   - Rationale: preserves core information while meeting target duration.
   - Alternative considered: regenerate full script repeatedly. Rejected because it increases token cost.

6. **Cost guardrails are hard limits**
   - Per-episode token budget and monthly API budget are mandatory limits.
   - On limit breach, generation stops and reports actionable status.
   - Rationale: explicit protection for the primary project priority.

## Risks / Trade-offs

- **[Risk] RSS feeds vary in quality and structure** -> Mitigation: validate feed health, show status in UI, and skip invalid feeds with clear diagnostics.
- **[Risk] API output length variance may exceed target** -> Mitigation: estimate duration from token/word budgets before generation and apply deterministic trimming.
- **[Risk] Sparse content in one category within 48h** -> Mitigation: redistribute unused quota to other categories proportionally by remaining weights.
- **[Risk] Cost drift from retries and prompt growth** -> Mitigation: strict retry cap, prompt size caps, and monthly budget hard-stop.
