---
round: R133
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R133 plan — Magnitude-PI re-eval at D5-fair action bounds (dm_max=600)

**Status**: DONE
**Opened**: 2026-05-19
**Driver**: PI "继续科研, 有问题就优化". CLM-0233 (R102 follow-up audit) found
R72_w4 SOTA was trained at `dm_max=600, dm_min=-200` (2× paper Eq.12); R85/R102
magnitude-PI ran on V4Config DEFAULT (dm_max=300). The "1.50× RL advantage
over magnitude-PI" was potentially **inflated by handicapping the classical
baseline with smaller action range**.
**Parent**: CLM-0094 R72_w4 SOTA + CLM-0186/0230/0232 RL advantage chain +
CLM-0233 D5 finding.

## TL;DR

Re-eval magnitude-PI (R102 winning gains Kp_M=2, Kp_D=5 + 2 scaled variants)
on V4Config(dm_max=600, dm_min=-200) to give true apples-to-apples comparison
vs R72_w4 SOTA (CLM-0094, trained at same bounds).

If best mag-PI geo ≥ 0.391 at D5-fair → SOTA = mag-PI when matched on action
bounds; algorithm advantage vanishes. If ≈ 0.260 → wider bounds don't help
classical, RL has real algorithmic advantage independent of D5.

## Methodology (zero new code on V4)

- V4 env with `V4Config(dm_max=600.0, dm_min=-200.0, dd_max=600.0, dd_min=-200.0)`
- 3 magnitude-PI gain combos: R102 best (2, 5), scaled 2× (4, 10), scaled 4× (8, 20)
- Same LS1+LS2, seed=42, steps=150, paper_grade_axes 11-axis
- Fresh no_control reference at D5-fair bounds (axis 8 dependency)

## Wave plan + ETA

W1: 3 combo × 2 scen × ~2 min = ~12 min wall.

## Resource conflict gate

R133 launched while ~10 other WSL python processes active. Used new
`scripts/r133_mag_pi_d5_fair.py`. Read-only on V4 env, no mutation.

## Cross-references

- CLM-0094 R72_w4 SOTA (geo 0.391, trained at dm_max=600)
- CLM-0186/0230 (RL advantage claims, R102 mag-PI 0.260 baseline)
- CLM-0233 D5 (action bound discovery)
- R102 plan / verdict (precedent grid pattern)
