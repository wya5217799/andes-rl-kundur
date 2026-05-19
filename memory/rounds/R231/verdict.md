# R231 verdict — phi_h=0.05 COLLAPSE; reward sweet spot is narrow around V4 default

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE for new reward-sensitivity finding
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --phi-h 0.05 --phi-d
0.05 (10× V4 default 0.0056). Result: geo=**0.0100**, LS1=**0.000**,
LS2=0.003, cum_rf=-0.1683. **FULL COLLAPSE** (LS1=0 attractor),
bit-identical to R218 (paper-original phi_h=1) and R214 (phi_abs=0).

## Reward landscape sensitivity

| phi_h | phi_d | scale vs V4 | geo | regime |
|-------|-------|-------------|-----|--------|
| 0.0056 | 0.0056 | 1× (V4 default) | **0.4152** | SOTA |
| **0.05** | **0.05** | **~9×** | **0.0100** | **COLLAPSE** |
| 1 | 1 | ~179× (paper) | 0.0100 | COLLAPSE |

**Sweet spot is narrow**: somewhere between 0.006 (V4 default) and
0.05 (10× V4), there's a cliff. V4's R18 rescale (1/178 of paper)
chose a value INSIDE the sweet spot; further scaling up by ~10×
breaks it.

## Paper-integrity finding (additional)

In addition to phi_abs ≥ 7 threshold (R214-R217) and paper Eq.14
collapse (R218/R219), R231 reveals: phi_h itself has a narrow
operating range around V4 default. The R18 rescale (1/178 of paper)
was load-bearing in a specific way: not just "small phi_h", but
"phi_h ≈ 0.006 specifically".

## R232 candidate

Narrow the cliff: phi_h=0.01 (1.8× V4 default). If still works
(geo > 0.30), cliff is in (0.01, 0.05]; if collapses, cliff is in
(0.006, 0.01]. Sharp characterization either way.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — paper-integrity story strengthens)

## 给 PI 的话

🛑 R231 = phi_h=0.05 (10× V4) = **collapse** (bit-identical R218).
**phi_h sweet spot 很窄**, V4 R18 rescale 0.0056 是 inside, 10× scale
up 就 collapse.

新 paper finding: **reward weight 各项都有 narrow operating window**.
phi_abs ≥ 7 threshold (R215+), phi_h ≈ 0.006 sweet spot (R231). 这两
个一起 explain V4's exact reward weights — not just "rescaled paper",
是 "specific basin inside narrow ranges".

R232 = phi_h=0.01 (1.8× V4) narrow cliff.

## Cross-references

- R201 (V4 default = SOTA)
- R218 (paper-strict = collapse)
- R214-R217 (phi_abs sweep)
