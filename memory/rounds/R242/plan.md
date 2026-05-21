---
round: R242
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R242 plan — scalar (no hreg) + only phi_abs at s51 (cross-seed sister of R239)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, paper-integrity cross-seed matrix)
**Driver**: R239 demonstrated scalar + only phi_abs near-SOTA at s54
(0.3954). R241 (in flight) tests hreg + only phi_abs at s51. R242
completes the 2×2×2 algo × reward × seed cube by testing scalar +
only phi_abs at s51.
**Parent**: R239 (s54 sister), R241 (s51 hreg sister).

## TL;DR

Train `td3_lstm` scalar at s51 with --phi-h 0 --phi-d 0 --phi-f 0
(only phi_abs=50 active). Baseline reference R203_w1_s51 with full
reward = 0.3901. Predict: ~0.39 ± 1.5% noise.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 51 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0 --phi-f 0 \
    --save-dir results/r242_w1_scalar_onlyphiabs_s51
```

Score:
```
python scripts/score_run.py --label r242_w1_scalar_onlyphiabs \
    --ckpt-dirs results/r242_w1_scalar_onlyphiabs_s51 \
    --out-dir results/r242_w1_scalar_onlyphiabs_s51
```

## Pre-registered full 2×2×2 matrix (post R240+R241+R242)

| seed | algo \ reward | full        | only-phi_abs | paper-strict |
|------|---------------|-------------|---------------|---------------|
| s54  | hreg          | 0.4152 R201 | 0.4128 R238   | 0.010 R218    |
| s54  | scalar        | 0.391 R72   | 0.3954 R239   | **R240 ?**    |
| s51  | hreg          | 0.3901 R203 | **R241 ?**    | —             |
| s51  | scalar        | (baseline)  | **R242 ?**    | —             |

If R241, R242 are both near 0.39 (no collapse, no SOTA-pulldown) AND
R240 collapses (geo < 0.10), the paper-integrity claim becomes:
**universal across 2 seeds × 2 algorithms × 2 reward regimes (paper
Eq.14 inert / paper-strict collapse)**.

## Cross-references

- R239 (scalar + only phi_abs at s54 = 0.3954)
- R241 (hreg + only phi_abs at s51, in flight)
- R240 (scalar + paper-strict at s54, in flight)
- R203 (hreg full reward at s51 = 0.3901)
- CLM-0385 (R239 universal-inertness claim)
