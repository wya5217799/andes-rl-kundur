---
round: R254
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R254 plan — scalar s50 + phi_f alone (paper-term decomposition, backlog from R247 verdict)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (backlog from R247 verdict commitment; paper-term decomposition)
**Driver**: Paired with R253 (phi_d alone). R247 verdict committed to
"R250 candidate = scalar s50 + phi_f=100 alone" which was never
executed. R254 closes the third leg of the decomposition: does the
paper synchronization weight (phi_f=100, paper Eq.14 nominal) alone
rescue scalar+s50?
**Parent**: R247 verdict (CLM-0420), R253 (paired phi_d run).

## TL;DR

Train td3_lstm scalar at s50 with --phi-h 0 --phi-d 0 --phi-f 100
(only paper r_f at paper nominal weight + phi_abs=50). Compare to
R246/R247 (only-phi_abs / +phi_h, both 0.2346/0.2347 on geo).

## Pre-registered outcomes (DUAL-METRIC, per CLM-0430 policy)

| R254 geo | R254 cum_rf | interpretation |
|----------|-------------|----------------|
| ≥ 0.32  | -0.087 ± 0.003 | phi_f IS the load-bearing rescue (synchronization weight matters) |
| 0.25-0.32 | -0.090 ± 0.003 | phi_f helps partial; need combinations |
| ≈ 0.235 | -0.092 ± 0.001 (bit-identical to R246/R247) | no single paper term is the rescue; the contribution is distributed across all three |

Cross-tabbed with R253:
- If R253 alone rescues but R254 does not: r_d (damping smoothing) is the term.
- If R254 alone rescues but R253 does not: r_f (sync penalty) is the term.
- If BOTH rescue: redundant, both work.
- If NEITHER rescues: the contribution is truly distributed — need
  combinations, or paper-terms-together provide something no single
  term captures. This would strengthen the "hreg as minimal-correction
  drop-in" recommendation in the gauge-invariance memo.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0 --phi-f 100 \
    --save-dir results/r254_w1_scalar_phif_only_s50
```

## Cross-references

- R253 (paired phi_d alone run)
- R247 (CLM-0420 — phi_h ruled out)
- R246 (CLM-0435 → CLM-0435 — only-phi_abs baseline)
- R251 (CLM-0435 — scalar s50 full V4 baseline)
- CLM-0445 (R252 — paper-term contribution to cum_rf is uniformly 3-6%)
