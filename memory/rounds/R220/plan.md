---
round: R220
state: aborted
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: Training killed mid-flight by session compaction (R219 turn). Batch-size
  axis was low-priority speculation; not worth re-running. Replaced by R221 testing
  phi-max axis instead.
superseded_note: null
type: research
---
# R220 plan — SOTA hyper at batch_size=64 (untested axis)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, untested CLI axis)
**Driver**: Untested single-axis variation of R201 SOTA. Default
batch size is ~32 (config); R220 tries 64. Larger batch may tighten
gradient estimates, potentially yielding +0.5-1% on SOTA.
**Parent**: R201 (SOTA).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --batch-size 64.
Three outcomes:
- **NEW SOTA (geo > 0.4152)**: larger batch tightens; new headline.
- **PARITY (0.40 ≤ geo ≤ 0.4152)**: batch size is robust.
- **REGRESS (geo < 0.40)**: 64 over-smooths or under-samples
  recurrent sequences.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --batch-size 64 \
    --save-dir results/r220_w1_hreg_bs64_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (SOTA at default batch)
- R213 (gamma=0.999 = same as 0.99)
- R200 (lr=5e-5 collapse)
