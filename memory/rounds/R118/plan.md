---
round: R118
state: superseded
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: R113
abort_reason: null
superseded_note: Toggler-Line_8 ablation closed-negative by CLM-0215 (R113)
---
# R118 plan — Toggler-OFF + paper_strict_pure retrain (D1 + D3 combined fix)

**Status**: ACTIVE — queued in wait-chain (auto-launch after R114 finishes)
**Opened**: 2026-05-19
**Driver**: PI "训练更好 agent" (2nd request). Combines two paper-deviation
fixes simultaneously: R110 Toggler-OFF (D3, CLM-0194) + R105 paper-pure
reward (D1, CLM-0191/0192). Tests whether removing BOTH paper-deviation
sources simultaneously breaks R72_w4 SOTA 0.391.
**Parent**: CLM-0191/0192 (reward divergence), CLM-0194 (Toggler), R114
(Toggler-OFF only test, in queue).

## TL;DR

Same as R114 but adds `--reward-config paper_strict_pure` flag which
sets `phi_abs=0, phi_h=phi_d=1.0` (paper Eq.14 literal). With
DISABLE_TOGGLER=1 V4 env, this is the cleanest paper-faithful training
setup attempted in R57-R85+ history. If geo > R114 geo, paper-pure
reward + cleaner scenario combine to break plateau.

## Methodology

```bash
DISABLE_TOGGLER=1 python scripts/train.py --algo td3_lstm \
    --reward-config paper_strict_pure \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.001 \
    --lstm-lr-warmup-eps 5 --normalize-actions \
    --save-dir results/r118_toggler_off_paper_strict_s54 --final-eval
```

## Gate

After R114 + R118 final_eval results:

| R114 geo | R118 geo | Interpretation |
|---|---|---|
| < 0.4 | < 0.4 | both fixes ineffective; plateau is algo/architecture, not setup |
| < 0.4 | ≥ 0.4 | paper-pure reward critical; Toggler-OFF alone insufficient |
| ≥ 0.4 | ≥ 0.4 + Δ vs R114 ≥ 0.05 | both fixes additive; combination is the cleanest |
| ≥ 0.4 | < 0.4 | paper-pure reward DEGRADES on Toggler-OFF; R72_w4 reward was Toggler-compensating |
| ≥ 0.45 | ≥ 0.45 | 🚨 91-round plateau broken via setup fix; R57-R85 rebaseline needed |

Most interesting outcome: R114 ≈ SOTA + R118 > R114 → reward is the
load-bearing fix, Toggler doesn't matter for RL agent.

## Resource conflict gate

- R114 will be active (training, ~25 min after R102 done)
- R118 wait-chain: starts only after R114 process gone
- WSL load: at R114 active, R118 wait-pending = same load as R114 alone
- Other windows' R83/R100/R103 will likely finish during this window

## 资产保护契约

- Same V4 env edit as R114 (DISABLE_TOGGLER env var, default OFF)
- New ckpt dir: `results/r118_toggler_off_paper_strict_s54/`
- New round dir: `memory/rounds/R118/`
- No edits to V4Config / agents / train.py / paper_grade_axes / tests/
- R72_w4 ckpt + all prior ckpts: not touched

## Cross-references

- R114 plan (precedes in wait-chain)
- CLM-0191/0192 (reward divergence — D1 fix)
- CLM-0194 (Toggler — D3 fix)
- Q-0024 (paper_strict_pure retrain question — R118 covers it but on cleaner Toggler-OFF scenario)
- `docs/paper/known_deviations_R85_to_R110.md` (consolidation)
