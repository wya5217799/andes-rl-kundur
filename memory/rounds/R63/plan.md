# R63 plan — Hyper sweep autonomous mode (N_SUBSTEPS / grad_clip / batch_size + combo)

**Date**: 2026-05-17
**Type**: hyper sweep (autonomous mode per user grant)
**Wall budget**: ~3 hr (4 waves × 45 min wall each)

## Trigger

R62 PI briefing + user reply "下一个大目标，找到最优参数，一切决策不用问了".
Full autonomy on hyper exploration. Baseline: TD3 h64+Q7 s50 V4 paper_faithful = -0.167 paper-metric.

R63 chooses 4 single-axis sweeps + 1 combo wave:

## Waves

**W1 — N_SUBSTEPS {1, 3, 10}** (default 5). Tests ODE integration precision.
**W2 — MAX_GRAD_NORM {0.5, 5, 10}** (default 1.0). Tests gradient clipping.
**W3 — batch_size {128, 512, 1024}** (default 256). Tests minibatch effect.
**W4 — Combo of W1+W2+W3 winners** (3-seed: s49/s50/s51).

Each axis at 1 seed (s50) for kill-switch decision. Best axis values
combined in W4 + 3-seed verify.

## Infrastructure additions

- `N_SUBSTEPS` env var override (base_env.py)
- `MAX_GRAD_NORM` env var override (sac_base.py)

## Hypotheses

- **H1**: One axis gives >5% paper-metric lift
- **H2**: Combo > each axis alone (additive)

## Schema plan

- CLM-0085 (decision/S) — Hyper sweep landscape
- CLM-0086 (finding/V) — N_SUBSTEPS=3 wins
- CLM-0087 (finding/V) — gc=0.5 wins
- CLM-0088 (finding/V) — bs=512 sweet spot
- CLM-0089 (finding/V) — Combo 3-seed new SOTA
