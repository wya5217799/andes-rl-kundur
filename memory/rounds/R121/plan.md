---
round: R121
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R121 plan — Constrained warm-h_0: α-sweep for Pareto improvement

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: User "继续研究, 一直干活, 优化 agent". [[CLM-0204]] (R112)
found warm-h_0 lifts cum_rf +54% but crushes geo -96% — metrics
disagree in sign at full saturation. R121 sweeps α ∈ {0.0, 0.1, 0.3,
0.5, 0.7, 1.0} where (h_init, c_init) = α × (h*, c*) to find a Pareto
improvement (geo preserved AND cum_rf improved).
**Parent**: R112 / CLM-0204; R104 / CLM-0188.

## TL;DR

6 α values × 2 scenarios = 12 ANDES rollouts (~2 min ideal, ~5-10 min
under 3-slot contention). For each α:
- Build (h_init, c_init) = α × (h*, c*) where (h*, c*) is the
  R104/R112 grad-ascent argmax (per-agent, computed once)
- Roll out LS1 + LS2 deterministic with this warm h_init
- Score canonical 6-axis geo + paper cum_rf

Find α such that geo ≥ 0.371 (baseline 0.391 − 0.02 noise band) AND
cum_rf > -0.068 (baseline). If exists → constrained warm-h_0 is a real
agent optimisation (Pareto improvement); if not → confirms geo/cum_rf
anticorrelation in warm-h_0 search direction.

## Why this is meaningful

Naive warm-h_0 (R112 α=1.0) gives geo-cum_rf sign disagreement.
Logical hypothesis: somewhere in α ∈ (0, 1) lies a sweet spot where
the step-0 ‖a‖ lift is enough to improve cum_rf but not so much that
geo crashes. R121 maps this Pareto frontier in 6 points.

If sweet spot exists: future "learned h_init MLP" architectures (R104's
Q-0022 proposal) should be designed with output-norm constraint at this
α scale (e.g. ‖h_init‖ ≤ 0.5 × ‖h*‖).

If no sweet spot: the geo metric punishes any step-0 lift; warm-h_0
is structurally incompatible with 6-axis paper-grade evaluation; R104
finding stays as forensic.

## Methodology

`scripts/r121_constrained_warm_h0.py`. Phase 1 grad-ascent reuses R99
/ R104 / R112 recipe (500 Adam steps lr=0.05). Phase 2 α sweep reuses
R112's custom rollout-with-warmed-h_init code with α-scaled (h, c).

Eval is canonical: `evaluation/summary.score_trace_files`.

## Gate criteria

| α giving | Implication |
|---|---|
| geo ≥ 0.371 AND cum_rf > -0.068 | Pareto improvement, constrained warm-h_0 valid |
| geo dominates (decreasing in α) AND cum_rf improves (increasing in α) | clean tradeoff curve, no sweet spot |
| Non-monotone in α | mechanism more complex; further analysis |
| All α catastrophic | execution bug or grad-ascent unstable; investigate |

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建: `scripts/r121_constrained_warm_h0.py`,
`results/r121_constrained_warm_h0/`,
`memory/rounds/R121/{plan.md, verdict.md}`, 1 CLM (next free ≥ 0205).

## Cross-references

- [[CLM-0204]] (R112 — naive warm-h_0 metric divergence finding)
- [[CLM-0188]] (R104 — universal Q-side architectural slack)
- [[CLM-0200]] (synthesis — to be updated with R121 result)
- R99 plan (grad-ascent methodology source)
- R104 plan (universal feasibility on 9 ckpts)
