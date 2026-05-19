---
round: R130
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R130 plan — Per-axis breakdown of CLM-0204 metric divergence (zero ANDES)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续科研". R128 post-mortem closed the warm-h_0 SOTA-fix track.
CLM-0204 reported aggregate metric divergence (-95.8% geo, +54% cum_rf)
but only qualitatively interpreted the cause ("non-smoothness"). R130
runs the 11-axis eval directly on R112's cached traces to identify the
specific killer axes.
**Parent**: CLM-0204 (R112), CLM-0233 (R128)

## TL;DR

`evaluate_trace` on 4 cached r112 trace JSONs (baseline LS1+LS2, warmh0
LS1+LS2). Report per-axis scores side by side.

Result: CLM-0204's qualitative "non-smoothness" reading is WRONG.
warm-h_0 is actually **smoother** (axes 4, 5 = 0.97-0.98 vs 0.24-0.69).
The real killers are:
- Axis 6 (dH_utilization) 0.197 → 0.006 (33× collapse)
- Axis 7 (dD_utilization) 0.651 → 0.007 (99× collapse)
- Axis 9 (agent_min_activity GATE) 1.000 → 0.083 (12× collapse, multiplicative)

These axes use range-of-action-relative-to-start. Warm-h_0 saturates at
step 0 and stays saturated → action span ≈ 0 → utilization 0.6%.

Physics-wise (cum_rf, max_df, settling) warm-h_0 is actually BETTER.
The 11-axis penalises CONSTANT SATURATED POLICIES via utilization /
activity gates, not via physics gates.

Zero ANDES. Zero WSL.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | Run `evaluate_trace` per-axis, compare baseline vs warmh0 | ~15 min |
| W2 | Write CLM-0238 + verdict + render | ~30 min |

Total wall ~45 min.

## 资源冲突 gate

R83/R85/R94/R110 done; R112 closed; R125-R128 mine and done. No conflict ✅
Reads only cached trace JSON ✅
Output: claim + verdict ✅

## 资产保护契约

不动: any code, V4, ckpt, test, R107/R109 artefacts.

新建:
- `memory/rounds/R130/{plan.md, verdict.md}`
- `memory/claims/CLM-0238.md`

## Cross-references

- CLM-0204 (R112 metric divergence aggregate) — parent; per-axis correction
- CLM-0233 (R128 post-mortem) — context
- CLM-0188 (R104 warm-h_0 feasibility Q-side)
- CLM-0238 (this round)
