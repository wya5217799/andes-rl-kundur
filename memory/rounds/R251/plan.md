---
round: R251
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R251 plan — scalar s50 FULL V4 reward (anchor missing baseline)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, baseline anchor for scalar seed-sensitivity claim)
**Driver**: Throughout R242/R246/R247/R248 we've been comparing
scalar+s50 results (R246 = 0.235, R247 = 0.235) to an ESTIMATED
baseline (~0.327 inferred from hreg s50). The **true measured
scalar s50 full-V4-reward baseline does not exist** in the project's
results directory. R251 closes this gap by directly measuring it.

**Parent**: R248 verdict (CLM-0425), R246 verdict (CLM-0410).

## TL;DR

Train td3_lstm scalar at s50 with **V4 default reward** (phi_h=0.0056,
phi_d=0.0056, phi_f=100, phi_abs=50) — same config as R72_w4 (s54
baseline) but at s50.

Outcomes determine R242/R246/R247 interpretation:
- **R251 ≈ 0.32-0.35**: scalar s50 baseline is ~0.33; R246 (-29%
  vs R251) is a real scalar-seed-sensitivity drop. CLM-0400/0410
  interpretation holds.
- **R251 ≈ 0.24-0.28**: scalar s50 ceiling itself is low; R246 is
  near-baseline, and the "scalar seed-sensitive vs paper terms"
  story collapses into "scalar has low ceiling at s50 regardless".
  Major narrative revision needed.
- **R251 < 0.10**: scalar at s50 doesn't train at all; even baseline
  collapses. Would mean R246 (0.235) is actually ABOVE baseline,
  which would be a third surprise.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0.0056 --phi-d 0.0056 --phi-f 100 --phi-abs 50 \
    --save-dir results/r251_w1_scalar_full_v4_s50
```

After:
```
python scripts/score_run.py --label r251_w1_scalar_full_v4 \
    --ckpt-dirs results/r251_w1_scalar_full_v4_s50 \
    --out-dir results/r251_w1_scalar_full_v4_s50
```

## Why this is critical

Until R251 lands, the entire R242/R246/R247 "scalar seed-sensitivity"
story rests on a comparison to an estimated baseline. Either the
story is real (R251 ≈ 0.32-0.35, paper claim 5 layer 3 stands) or
the story is an artifact of bad baseline estimation (R251 ≈ 0.24,
need to rewrite paper claim).

This is the experiment that should have been run FIRST in this thread,
before R242. Running now to close the loop honestly.

## Cross-references

- R246 (scalar s50 only-phi_abs = 0.2346 — what we've been
  interpreting against an estimated baseline)
- R249 (hreg s50 only-phi_abs = 0.3581 — same reward, different
  algo, gives algo-class anchor)
- R185 (hreg s50 full V4 = 0.3515 — same algo, different reward,
  gives reward-config anchor)
- R72_w4 (scalar s54 full V4 = 0.391 — same algo+reward, different
  seed, gives seed anchor)
- CLM-0425 (R248 2-patch necessity)
- CLM-0410 (scalar seed-sensitivity claim, pending R251 verification)
