---
round: R64
state: active
opened: '2026-05-17'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R64 plan — Autonomous hyper sweep continuation: lr / explore_noise / hidden_size

**Date**: 2026-05-17
**Type**: hyper sweep wave 2
**Wall budget**: ~2.5 hr (5 waves × 20-30 min)

## Trigger

R63 closed with combo SOTA 3-seed -0.170 (+29.5pp vs paper DDIC).
User authorized continued autonomous sweep. R64 extends to additional
axes not yet tested.

## Waves

**W1** — lr sweep {1e-4, 3e-4 baseline, 5e-4, 1e-3} on R63 combo
**W2** — Boundary search lr {2e-3, 3e-3, 5e-3} to find ceiling
**W3** — 3-seed verify best lr + explore_noise pilot
**W4** — explore_noise 3-seed if pilot wins
**W5** — hidden_size {32, 48, 96} on lr=3e-3 combo

## Infrastructure

- `LR` env var override (train.py)
- `EXPLORE_NOISE` env var override (td3.py)

## Hypotheses

- **H_lr**: lr higher than paper default 3e-4 will lift paper-metric
- **H_explore**: smaller noise may improve final policy peak
- **H_hidden**: R48 U-curve at h=64 may shift under new hyper combo
