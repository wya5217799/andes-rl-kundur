---
round: R192
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R192 plan — scalar at s54 + seed-offset=100 (test if SOTA seed depends on offset)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, R190 follow-up)
**Driver**: R190 isolated offset=100 as the sole cause of s49 rescue.
Open question: does offset affect s54 (the SOTA seed) too? Three outcomes:
- ≈0.391 (matches R72_w4 baseline): s54 is a stable basin, offset is
  a bad-seed-only knob
- ≠0.391: ALL seeds are offset-dependent; SOTA selection needs joint
  seed+offset reporting
- Drastically different (collapse or much higher): even s54 has a
  bad-RNG-path failure mode; SOTA claim needs offset disclosure

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 54 --seed-offset 100 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --save-dir results/r192_w1_scalar_s54_offset100
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R72_w4 baseline: scalar s54 offset=0 = 0.391 (R72/CLM-0123)
- R190 verdict (env-side mechanism at s49)
- R188 verdict (env-side at s49, with hreg)
- CLM-0350 (Q-0005 closed-partial)
