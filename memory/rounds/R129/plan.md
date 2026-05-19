---
round: R129
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R129 plan — td3_qr_lstm seed=49 (multi-seed verification of R122 single-seed QR)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "训练更好 agent, 别让我提醒你". R122 (td3_qr_lstm s54) launched
by other session, single-seed only. R129 adds the multi-seed verification at
s49 — required to distinguish "QR breaks plateau" from "QR is s54-lottery".
Parallel and orthogonal to R124 (afe s49) + R127 (qr+afe stacked s54).
**Parent**: CLM-0189 (R98 QR prototype), R108 train.py dispatch.

## TL;DR

Run `--algo td3_qr_lstm --seed 49` 75 ep. R122/R123/R124/R127/R129 form a
4-cell A/B matrix on critic-representation interventions × 2 seeds:

| Algo | s54 | s49 |
|---|---|---|
| td3_qr_lstm (a) | R122 | **R129 (this)** |
| td3_afe_lstm (b) | R123 | R124 |
| td3_qr_afe_lstm (a+b stacked) | R127 | — |

Cross-seed verdict comes from R122+R129 (QR) and R123+R124 (AFE).

## Command

```bash
LR=1e-4 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/train.py \
    --algo td3_qr_lstm --qr-n-quantiles 51 \
    --episodes 75 --seed 49 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r129_w1_qr51_s49 \
    --final-eval
```

## Gate

- CONFIRM (geo ≥ 0.42): QR robust seed 49 + 54, plateau-breaker candidate
- MARGINAL [0.36, 0.42]: QR consistent moderate lift, additive with AFE viable
- REGRESS (< 0.36 or ~0.39): QR s54 lottery, doesn't generalise
- COLLAPSE (< 0.20): R56 s50 / R57 collapse pathology under QR

## 资源冲突 gate

WSL currently 7 processes after R124 + R127 + others; adding R129 = 8.
Memory 19 GB free, ANDES TDS single-core, 8 cores / 32 = 25% — safe.

## 资产保护契约

不动: src/ / V4 / train.py / R57+ ckpt / existing tests.
新建: `results/r129_w1_qr51_s49/` + plan/verdict + 1 CLM (combined with R124).

## Cross-references

- R98 / R108 verdicts (prototype + dispatch)
- CLM-0189 (R98 QR prototype) — R129 second execution
- R122 plan (s54 QR primary, R129 multi-seed pair)
- R124 plan (parallel multi-seed AFE)
- R127 plan (stacked QR+AFE)
