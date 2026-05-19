---
round: R149
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
closed_note: 200ep over-training regression; closed-negative per plan
---
# R149 plan — td3_qr_lstm s54 200ep (test if longer horizon exceeds R72_w4 0.391)

**Status**: ACTIVE → CLOSED-NEGATIVE (over-training regression)
**Opened**: 2026-05-19
**Driver**: R142 (75ep) matched baseline 0.391. Test if 200ep exceeds.
**Parent**: CLM-0275 (R142 QR validated at 75ep).

## Result

- ep 75 trajectory matches R142 (same seed deterministic)
- ep 75 → ep 200: train_reward continues to improve (-3 → -2.3 ep 102)
- **best.pt = ep 102 ckpt, geo 0.1796 — REGRESSED 53% vs R142 0.385**
- final.pt = ep 200, geo 0.1640 — also regressed

Confirms **75 ep is sweet spot**, longer training hurts paper geo.

## Closed by

CLM-0285 (over-training regression headline).

## Command

```bash
LR=1e-4 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/train.py \
  --algo td3_qr_lstm --qr-n-quantiles 51 --episodes 200 --seed 54 \
  --hidden-size 64 --tau 0.001 --normalize-actions --lstm-lr-warmup-eps 5 \
  --save-dir results/r149_qr51_s54_200ep --final-eval
```
