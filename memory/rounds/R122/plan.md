---
round: R122
state: superseded
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: R142
abort_reason: null
superseded_note: distributional critic first-train superseded by R142 QR-LSTM (CLM-0275)
---
# R122 plan — Distributional critic (TD3-QR-LSTM) first training run

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "训练更好 agent, 别让我提醒你". CLM-0157(a) PRIORITY 1 R98
built `TD3QRLstmAgent` (51-quantile distributional critic, Dabney 2018
QR-DQN); R108 wired into train.py; R83 closed-NEGATIVE opened the gate.
**No session has trained it yet** — R122 is the first execution.
R120-R121 reserved by parallel sessions, R122 next free.
**Parent**: CLM-0157(a) candidate code-ready, R83 unlock.

## TL;DR

Train `td3_qr_lstm` (51 quantiles, quantile Huber loss) with R72_w4
same hyper + seed 54 + 75 ep. Falsifies "scalar Q regression caused
the plateau" hypothesis. Joint with R115 (reward) + R119 (action bound)
= 3 parallel ablations on the last untested mechanism axes.

## Methodology

```
LR=1e-4 python scripts/train.py \
    --algo td3_qr_lstm --qr-n-quantiles 51 \
    --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r122_w1_qr51_s54
```

ANDES WSL slot 3 of 3 (R115 + R119 + R122 = 3 concurrent).

## Gate criteria

- **CONFIRM (geo ≥ 0.42)**: distributional Q gives the policy extra
  information → lifts geo. Mechanism candidate "scalar Q regression"
  confirmed.
- **MARGINAL (geo ∈ [0.36, 0.42])**: distributional helps a bit.
- **REGRESS (geo < 0.36)**: distributional critic doesn't help; the
  scalar critic representation is not the ceiling. Confirms env/reward
  story per CLM-0190.

## Cross-references

- CLM-0157(a) (R98 prototype code, design rationale)
- CLM-0190 (R100 drift falsified; this is next axis)
- CLM-0144 (91-round plateau)
- R98 / R108 verdicts (code + wire)
