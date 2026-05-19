---
round: R212
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R212 plan — hreg SOTA hyper at 100ep (between 75 SOTA and 200 regress)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, horizon basin refinement)
**Driver**: Horizon basin so far:
- 50ep collapse (R199 LS1=0)
- 75ep SOTA 0.4152 (R201)
- 200ep regress 0.3161 (R191)

What about 100ep? Could be slightly higher than 75ep (more refinement
without over-training) or slightly lower (over-training started). Fills
the horizon basin map.

**Parent**: R199 (50ep collapse), R201 (75ep SOTA), R191 (200ep regress).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54+offset=0 for **100 episodes**.
Three outcomes:
- **HIGHER (geo > 0.4152)**: 100ep is slightly better; new SOTA;
  search continues toward 90/110ep.
- **EQUIVALENT (0.40 ≤ geo ≤ 0.4152)**: 75-100ep basin is flat;
  pick 75ep for compute efficiency.
- **REGRESS (geo < 0.40)**: over-training starts before 100ep; 75ep
  is the true optimum.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 100 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r212_w1_hreg_100ep_s54
```

ANDES WSL ~20 min train + ~5 min eval.

## Cross-references

- R201 (75ep SOTA 0.4152)
- R191 (200ep regress 0.3161)
- R199 (50ep collapse 0.0672)
