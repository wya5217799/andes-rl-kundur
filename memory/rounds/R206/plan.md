---
round: R206
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R206 plan — SOTA hyper at s54 with --comm-fail 0.05 (robustness under comm failure)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, robustness axis)
**Driver**: All ensemble paths exhausted (R202/R205 don't beat single
0.4152). New direction: stress-test SOTA hyper under 5% communication
failure. Paper-relevant: real VSG deployments have imperfect inter-
agent comm. If SOTA hyper still gives >0.39 with comm_fail=0.05,
robust-to-deployment paper claim.
**Parent**: R201 verdict (single SOTA at perfect comm).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --comm-fail 0.05
(5% chance per step that an agent fails to receive others' messages).
Three outcomes:
- **ROBUST (geo ≥ 0.39)**: SOTA degrades gracefully (≤6%) under
  realistic comm failure; paper headline gains a deployment-robustness
  claim.
- **PARTIAL (0.30 ≤ geo < 0.39)**: SOTA partially degrades (6-25%);
  still viable but with caveat.
- **FRAGILE (geo < 0.30)**: SOTA depends heavily on perfect comm;
  paper must disclose this fragility.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --comm-fail 0.05 \
    --save-dir results/r206_w1_hreg_commfail005_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (single SOTA at comm_fail=0 = 0.4152)
- R72_w4 baseline (no comm_fail)
- CLM-0094 (hyper definition)
