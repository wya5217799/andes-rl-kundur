---
round: R245
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R245 plan — scalar + only phi_abs + 150ep (push scalar SOTA via longer training)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, scalar+inert-paper improvement)
**Driver**: R239 (scalar + only phi_abs at 75ep) = 0.3954, **+1.1%
above R72_w4 baseline 0.391**. Could longer training push scalar
SOTA higher? Test 150ep version.
**Parent**: R239 verdict.

## TL;DR

Train td3_lstm scalar at s54 with --phi-h 0 --phi-d 0 --phi-f 0 for
**150 episodes**. Three outcomes:
- **PUSH (geo > 0.40)**: longer training + paper-Eq.14-inert helps;
  potentially new scalar SOTA approaching hreg level.
- **PLATEAU (0.39 ≤ geo ≤ 0.40)**: scalar plateaus around 0.395.
- **REGRESS (geo < 0.39)**: over-training for scalar; 75ep is right.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 150 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0 --phi-f 0 \
    --save-dir results/r245_w1_scalar_onlyphiabs_150ep_s54
```

ANDES WSL ~30 min train + ~5 min eval.

## Cross-references

- R239 (scalar + only phi_abs at 75ep = 0.3954)
- R72_w4 (scalar baseline)
- R191 (hreg 200ep regress)
