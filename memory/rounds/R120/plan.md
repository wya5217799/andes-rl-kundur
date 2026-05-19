---
round: R120
state: aborted
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: depended on R118; multi-seed moot after R118 superseded
superseded_note: null
---
# R120 plan — R118 multi-seed (s49) for statistical confidence

**Status**: ACTIVE — queued in wait-chain (auto-launch after R118 finishes)
**Opened**: 2026-05-19
**Driver**: PI "训练更好 agent" (sustained). If R118 (Toggler-OFF +
paper_strict_pure, s54) shows promising geo, multi-seed run (s49)
provides statistical confidence. Single-seed runs are noisy in R57-R85
history (R72_w4 sweet spot vs other R72 wave failures).
**Parent**: R118 (s54 lead).

## TL;DR

Identical to R118 except `--seed 49` (the R21 lucky-basin SAC seed,
historically the most informative non-s54 seed). If R118 + R120 both
break SOTA 0.391, the finding is robust. If only s54 wins, it's seed-
dependent (similar to R72_w4 narrow basin).

## Methodology

```bash
DISABLE_TOGGLER=1 python scripts/train.py --algo td3_lstm \
    --reward-config paper_strict_pure \
    --episodes 75 --seed 49 --hidden-size 64 --tau 0.001 \
    --lstm-lr-warmup-eps 5 --normalize-actions \
    --save-dir results/r120_toggler_off_paper_strict_s49 --final-eval
```

## Gate

After R114 + R118 + R120 all eval done:

| s54 geo (R118) | s49 geo (R120) | Interpretation |
|---|---|---|
| ≥ 0.45 | ≥ 0.45 | Both seeds win → 91-round plateau truly broken via Setup fixes; ROBUST |
| ≥ 0.45 | < 0.39 | s54 lucky, plateau persists statistically; like R21 lucky basin |
| < 0.39 | ≥ 0.45 | s49 better than s54; R72_w4 was sub-optimal seed; rethink seed selection |
| both < 0.39 | both < 0.39 | Setup fixes insufficient even with right seed; algo-level limit confirmed |

## Resource / conflict

- Wait-chains in single bash: R102 → R114 → R118 → R120
- R120 starts only after R118 process gone
- Total ETA from now: R102 (~10 min) + R114 (~30) + R118 (~30) + R120 (~30) = ~100 min
- WSL load at any moment: ≤ 1 from this chain + others' parallel runs

## 资产保护契约

- Same V4 env DISABLE_TOGGLER mechanism
- New ckpt dir: `results/r120_toggler_off_paper_strict_s49/`
- No other-file edits

## Cross-references

- R114 / R118 plans
- R21 (s49 lucky basin SAC geo 0.444) — historical s49 high water mark
- CLM-0094 (R72_w4 SOTA s54 baseline)
- `docs/paper/known_deviations_R85_to_R110.md`
