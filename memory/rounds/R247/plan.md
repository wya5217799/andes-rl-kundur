---
round: R247
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R247 plan — scalar s50 + phi_h alone (decompose which paper term rescues scalar)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, R246 follow-up, paper-term decomposition)
**Driver**: R246 (scalar s50 + only phi_abs) = 0.2346, **~-28% from
estimated baseline**. paper Eq.14 terms (phi_h, phi_d, phi_f) are
NOT inert for scalar at s50 (and s51, per R242). R247 tests: does
just **phi_h alone** (inertia smoothing) rescue scalar+s50 back
toward baseline? If yes, paper r_h is the load-bearing term for
scalar in seed-sensitive basins, and hreg's hidden-state
regularization provides equivalent stability.

**Parent**: R246 verdict (CLM-0410), R236 (hreg phi_h decomposition).

## TL;DR

Train td3_lstm scalar at s50 with --phi-h 0.0056 (paper r_h
nominal scaled per R18) --phi-d 0 --phi-f 0 (only phi_h + phi_abs).
Outcomes:
- **rescue (geo ≥ 0.32)**: phi_h IS the load-bearing rescue. paper
  r_h ≈ hreg-provided stability for scalar. Decisively identifies
  inertia-smoothing as the missing term.
- **partial (0.25 ≤ geo < 0.32)**: phi_h helps but not fully; phi_d
  also contributes. Would motivate R248 = phi_d alone.
- **no help (geo ≈ 0.23)**: phi_h doesn't rescue; phi_d or phi_f is
  the load-bearing term. R248+ would test those alone.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0.0056 --phi-d 0 --phi-f 0 \
    --save-dir results/r247_w1_scalar_phih_only_s50
```

After:
```
python scripts/score_run.py --label r247_w1_scalar_phih_only \
    --ckpt-dirs results/r247_w1_scalar_phih_only_s50 \
    --out-dir results/r247_w1_scalar_phih_only_s50
```

## Decision tree (paper-Sec.IV-D-contribution-5 implications)

| R247 outcome | What it means | Next round |
|--------------|---------------|------------|
| ≥ 0.32 (rescue) | r_h is the rescue → hreg = r_h-equivalent | Done; write up |
| 0.25-0.32 (partial) | r_h helps; r_d may also | R248 = scalar s50 + phi_d alone |
| ≈ 0.23 (no help) | r_h not the answer | R248 = scalar s50 + phi_d / phi_f alone |

## Cross-references

- R246 (scalar s50 only phi_abs = 0.2346 — baseline for R247 comparison)
- R242 (scalar s51 only phi_abs = 0.3003)
- R236 (hreg phi_h=phi_d=0 = bit-identical to R201 — establishes
  phi_h+phi_d inert for hreg)
- R237 (hreg phi_f=0 = -0.6%, phi_f also inert for hreg)
- R201 (hreg full SOTA)
- CLM-0410 (R246 scalar seed-sensitivity finding)
