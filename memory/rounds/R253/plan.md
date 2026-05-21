---
round: R253
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R253 plan — scalar s50 + phi_d alone (paper-term decomposition, backlog from R247 verdict)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (backlog from R247 verdict commitment; paper-term decomposition)
**Driver**: R247 verdict (CLM-0420) ruled out phi_h alone as scalar+s50
rescue (bit-identical to R246 only-phi_abs). R247 verdict explicitly
committed to follow-up: "R249 candidate = scalar s50 + phi_d alone"
which was never executed (R249 actually ran hreg+only-phi_abs at s50
instead, per autonomous-loop drift). R253 now closes the decomposition
commitment: does phi_d (paper r_d damping smoothing) alone rescue
scalar+s50?
**Parent**: R247 verdict (CLM-0420), R246 (CLM-0410 → CLM-0435 anchor).

## TL;DR

Train td3_lstm scalar at s50 with --phi-h 0 --phi-d 0.0056 --phi-f 0
(only paper r_d + phi_abs=50). Compare to:
- R246 (only-phi_abs) = geo 0.2346, cum_rf -0.0917
- R247 (+phi_h alone) = geo 0.2347, cum_rf -0.0917 (bit-identical to R246)
- R251 (full V4 baseline) = geo 0.2662, cum_rf -0.0878

## Pre-registered outcomes (DUAL-METRIC, per CLM-0430 policy)

| R253 geo | R253 cum_rf | interpretation | next action |
|----------|-------------|----------------|-------------|
| ≥ 0.32   | -0.087 ± 0.003 | phi_d IS the load-bearing rescue | done; CLM closes decomposition |
| 0.25-0.32 | -0.090 ± 0.003 | phi_d helps but partial; phi_f may also | R254 = phi_f alone |
| ≈ 0.235 | -0.092 ± 0.001 (bit-identical to R246/R247) | phi_d also not the answer | R254 = phi_f alone |

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0.0056 --phi-f 0 \
    --save-dir results/r253_w1_scalar_phid_only_s50
```

Score:
```
python scripts/score_run.py --ckpt-dirs results/r253_w1_scalar_phid_only_s50
```
(smart defaults auto-derive --label and --out-dir per CLM-0440 follow-up)

## Comparison baselines (MEASURED, per CLM-0435 policy)

Use `baselines.py` (must be measured, NOT cross-algo-ratio-derived):
- `r251_w1_scalar_full_v4_s50` (geo 0.2662, cum_rf -0.0878 — full V4)
- `r246_w1_scalar_onlyphiabs_s50` (geo 0.2346, cum_rf -0.0917 — gauge-fix alone)
- `r247_w1_scalar_phih_only_s50` (geo 0.2347, cum_rf -0.0917 — +phi_h)

## Cross-references

- R247 (CLM-0420 — phi_h ruled out, this round completes phi_d branch)
- R246 (CLM-0410, superseded by CLM-0435 — R246 only-phi_abs anchor)
- R251 (CLM-0435 — scalar s50 full baseline anchor)
- CLM-0430 (dual-metric audit — outcomes table includes cum_rf thresholds)
- CLM-0445 (R252 — establishes that paper Eq.14 terms uniformly cost
  3-6% cum_rf when removed; R253 tests whether THIS specific term
  contributes to that 3-6%)
