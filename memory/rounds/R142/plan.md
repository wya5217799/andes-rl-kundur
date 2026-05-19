---
round: R142
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R142 plan — td3_qr_lstm seed=54 (multi-seed verification of R129)

**Status**: ACTIVE (training in WSL, ~30 min ETA on clean machine)
**Opened**: 2026-05-19
**Driver**: PI "继续". WSL restart cleaned all stale processes. R140 (AFE s54
cross-seed of R124) just relaunched; R142 = QR s54 to complete the cross-seed
matrix below. Final empirical answer to whether R98 critic-representation
prototypes collapse universally or only at seed s49.
**Parent**: CLM-0189 (R98 QR prototype), CLM-0255 (R124+R127+R129 collapse).

## TL;DR

`--algo td3_qr_lstm --seed 54` 75 ep. Same hyper as R72_w4 baseline + R129 (s49).
Together with R140 (AFE s54), R124 (AFE s49), R127 (QR+AFE s54), R129 (QR s49)
forms a 2×3 matrix to attribute collapse mechanism:

| Algo | s49 | s54 |
|---|---|---|
| td3_qr_lstm | R129 (0.0387 mixed attractor) | **R142 (this)** |
| td3_afe_lstm | R124 (0.0100 do-nothing) | R140 (in progress) |
| td3_qr_afe_lstm | — | R127 (0.0100 do-nothing) |
| (R72_w4 baseline) | — | 0.391 (bang-bang) |

## Gate

- CONFIRM collapse universal: R142 geo ≤ 0.10 → CLM-0263 mechanism is seed-
  independent, R98 prototypes structurally broken at 75-ep paper-faithful
- DIFFER by seed: R142 geo ≥ 0.30 → seed s49 was lottery loser, R129 was unlucky
- INTERMEDIATE: R142 geo ∈ (0.10, 0.30) → seed-fragile attractor escape

## Cross-references

- CLM-0255 (3-prototype collapse headline)
- CLM-0263 (do-nothing attractor mechanism, to-be-confirmed)
- R129 plan (s49 QR companion)
- R140 plan (s54 AFE companion)

## Command (running)

```bash
LR=1e-4 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/train.py \
  --algo td3_qr_lstm --qr-n-quantiles 51 --episodes 75 --seed 54 \
  --hidden-size 64 --tau 0.001 --normalize-actions --lstm-lr-warmup-eps 5 \
  --save-dir results/r142_w1_qr51_s54 --final-eval
```
