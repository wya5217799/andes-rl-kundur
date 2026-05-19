---
round: R116
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R116 plan — Obs-gradient ascent at h=0 (R104 complement)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "一直干活". R107-W2 (CLM-0193) tested random obs. R116
tests OPTIMISED obs: is there ANY obs direction that unlocks step-0
saturation at h=0? Critical control for warm-h_0 necessity claim.
**Parent**: CLM-0193, CLM-0188, CLM-0183

## TL;DR

R72_w4 SOTA × 4 agents × 50 init obs × 500-step Adam ascent on obs
(||obs|| penalty above 5.0).

Result: max ||a||* = 41% of max. Median lift +23.8 pp (10% → 34%).
Even with obs pushed to ||obs||=5.3 (off-manifold absurd) the LSTM
at h=0 cannot saturate. Warm-h_0 is the ONLY architectural fix path.

Zero ANDES. Zero WSL.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | `r116_obs_grad_at_h0.py` + run | ~20 min |
| **W2** | Verdict + CLM-0212 + render | ~15 min |

Total wall ~35 min.

## 资源冲突 gate

R83 / R94 / R102 / R110 (WSL): R116 zero ANDES ✅
ckpt R72_w4 read-only: ✅
Output: `results/r116_obs_grad_at_h0/` new namespace ✅

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / R57+ ckpt / R86-R115 artefacts / any test.

新建:
- `scripts/r116_obs_grad_at_h0.py`
- `results/r116_obs_grad_at_h0/summary.json`
- `memory/rounds/R116/{plan.md, verdict.md}`
- `memory/claims/CLM-0212.md`

## Cross-references

- CLM-0193 (R107 obs-norm independence — random obs) — R116 complements
- CLM-0188 (R104 warm-h_0 N=9 universal)
- CLM-0183 (R99 N=1 feasibility)
- CLM-0212 (this round)
