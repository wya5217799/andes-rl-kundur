---
round: R154
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R154 plan — Cross-seed R72_w4 hyper at s49, for cross-seed ensemble

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究" autonomous. CLM-0280 (R153/R152 HAWE finding) opens
"cross-seed ensembles (need s49/s51 ckpts trained with same hyper); likely
larger gain than same-seed ensemble" as #1 follow-up. ANDES slot now free
(R149 just finished, collapsed to 0.18).
**Parent**: CLM-0280 (R153 HAWE plateau breaker, R152 independent verify).

## TL;DR

Train td3_lstm with R72_w4 exact hyper (lr=1e-4 clamp, tau=0.001, h=64,
warmup_eps=5, normalize-actions, 75 ep) at **seed 49** (vs s54 for R72_w4
canonical). Single ANDES wave ~15 min. Then offline ensemble eval:

- 3-way **cross-seed**: {R72_w4_s54, R72_w4_hyper_s49, R142_s54} mean agg
- 4-way **cross-seed + cross-algo**: {R72_w4_s54, R72_w4_hyper_s49,
  R142_s54, R143_s54} mean agg

Hypothesis: cross-seed averaging gives larger lift than cross-algo same-
seed (ensemble theory: independent training trajectories produce more
diverse policies than algorithm variants on same seed).

## Methodology

```
LR=1e-4 python scripts/train.py \
    --algo td3_lstm \
    --episodes 75 --seed 49 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r154_w1_r72w4hyper_s49
```

Followed by eval_ensemble.py mean-agg over {s54-baseline, s49-new, R142_s54}.

## Gate criteria

- **BREAKTHROUGH (geo ≥ 0.43)**: cross-seed dominates. New SOTA.
- **STRONG (geo ∈ [0.41, 0.43])**: cross-seed > cross-algo same-seed.
- **PARITY (geo ∈ [0.39, 0.41])**: cross-seed ~ cross-algo (still useful).
- **NULL (geo < 0.39)**: cross-seed underperforms; CLM-0280's hypothesis
  refuted.

## Cross-references

- CLM-0280 / R153 (HAWE plateau breaker)
- CLM-0144 (91-round plateau)
- CLM-0094 (R72_w4 canonical SOTA at s54)
- Q-0005 (R56 LSTM seed-50 collapse) — s49 chosen to avoid s50 collapse risk
