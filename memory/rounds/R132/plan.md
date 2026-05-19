---
round: R132
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R132 plan — Fine-grain α-sweep [0.05–0.30] to locate warm-h_0 Pareto knee

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: [[CLM-0211]] (R121) found smooth-region α ∈ [0, 0.3] with
cliff at α≈0.4. α=0.1 gave -7% geo / +40% cum_rf — close to but
missing strict Pareto. R132 refines the smooth region with 6 α values
to find where geo crosses the −5% / −10% thresholds.
**Parent**: R121 / CLM-0211.

## TL;DR

α-sweep on R72_w4 SOTA, α ∈ {0.05, 0.10, 0.15, 0.20, 0.25, 0.30}, identical
LSTM-init scaling protocol to R121. 12 ANDES evals (~20 min wall under
3-slot contention). Report geo, cum_rf, and identify:
- **Strict Pareto knee** (largest α with geo ≥ baseline - 0.02)
- **Relaxed Pareto knee** (largest α with geo ≥ baseline × 0.90)

Output candidate "best-Pareto warm-h_0 α" for paper-metric-path SOTA
discussion.

## Cross-references

- [[CLM-0211]] (R121 — coarse α-curve cliff finding)
- [[CLM-0210]] (utilization range mechanism)
- [[CLM-0204]] (R112 naive warm-h_0)
- [[CLM-0188]] (R104 Q-side feasibility)
- [[CLM-0200]] (synthesis to be updated)
