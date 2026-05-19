---
round: R250
state: aborted
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: warmstart-shared CLI flag not implemented for td3_lstm_hreg (LSTM-actor
  state_dict differs from MLP-actor). Cannot transfer R201 ckpt this way. Closed as
  aborted; no compute wasted (failed at startup before training began).
superseded_note: null
type: research
---
# R250 plan — warmstart from R201 SOTA ckpt + fine-tune at s50 (transfer learning rescue)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, transfer-learning novel angle)
**Driver**: R185 (hreg from-scratch at s50) = 0.3515 (-15% vs s54 SOTA).
R250 tests if **warmstart from R201 s54 ckpt** + fine-tune at s50
recovers SOTA-level performance. If geo ≥ 0.40, transfer learning
is a clean rescue path for unlucky seeds. **Novel angle**: previously
untested in autonomous loop.
**Parent**: R185 (s50 from-scratch), R201 (SOTA ckpt source).

## TL;DR

Train td3_lstm_hreg at s50 starting from R201 ckpt as initialization.
Three outcomes:
- **TRANSFER RESCUE (geo ≥ 0.40)**: warmstart lifts s50 to SOTA-level;
  paper claim: "cross-seed transfer learning rescues unlucky seeds".
- **PARTIAL (0.36 ≤ geo < 0.40)**: improves over from-scratch
  (R185 0.3515) but doesn't fully reach SOTA.
- **NO BENEFIT (geo ≈ 0.35)**: warmstart re-trains to s50's local
  basin; equivalent to from-scratch.
- **REGRESS (geo < 0.30)**: warmstart hurts (initial policy mismatched
  to s50 dynamics).

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --warmstart-shared results/r201_w1_hreg_tau005_s54/agent_0_best.pt \
    --warmstart-mode actor_and_critic \
    --save-dir results/r250_w1_hreg_warmstart_s50
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R185 (hreg s50 from-scratch = 0.3515)
- R201 (s54 SOTA ckpt source = 0.4152)
- R204 (R201 hyper at s50 from-scratch = 0.3481)
