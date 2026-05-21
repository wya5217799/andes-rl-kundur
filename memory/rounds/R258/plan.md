---
round: R258
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R258 plan — Sync-only RL training (phi_abs=0) to test droop k=10 reward parity

**Status**: ACTIVE
**Opened**: 2026-05-20
**Driver**: 3 consecutive probe-first rounds (R255/R256/R257) narrowed the RL
cum_rf plateau mechanism to **smooth-but-loud RL vs reactive-and-titrated
droop k=10**. CLM-0470 over-actuation finding + CLM-0475 smoothness inversion
+ CLM-0445 Pareto trade-off together point to one mechanism-motivated
training experiment: **train RL with droop k=10's reward philosophy (sync
only, no transient damping)**. Concrete: drop phi_abs to 0, keep phi_f=100.
If RL with droop-mirroring reward beats droop k=10 on cum_rf → paper 7th
contribution candidate (CLM-0445). If RL collapses → phi_abs is structural
stabilizer.
**Parent**: CLM-0445 (paper 7th contribution candidate), CLM-0455 (phi_f
load-bearing), CLM-0470 (over-actuation), CLM-0475 (smoothness inversion).

## TL;DR

Single ANDES WSL training (~13 min). td3_lstm scalar, seed=50, 75ep,
phi_f=100, phi_abs=0 (vs R254 baseline phi_abs=50). All other settings
identical to R254 for clean controlled comparison. Score via standard
`score_run.py` (dual-metric geo + cum_rf).

## Snapshot at plan-time (oracle as of 2026-05-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing

## Recently Closed (last 3)

- Q-0008 closed-negative @ R252, by CLM-0415
- Q-0021 closed-positive @ R252, by CLM-0231
- Q-0005 closed-partial @ R186, by CLM-0350

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0 --phi-f 100 --phi-abs 0 \
    --save-dir results/r258_w1_scalar_phif_only_no_phiabs_s50

python scripts/score_run.py \
    --ckpt-dirs results/r258_w1_scalar_phif_only_no_phiabs_s50
```

Direct comparison to R254 (same hyper + same seed; difference = phi_abs
from 50 to 0). R254 result: geo=0.2655, cum_rf=-0.0878.

## Pre-registered outcomes

| Pre-reg | Interpretation |
|---------|----------------|
| cum_rf < -0.05 AND geo > 0.20 | **STRONG WIN** — RL with droop-mirror reward beats current plateau; paper-7th-contribution candidate confirmed |
| -0.07 < cum_rf < -0.05 AND geo > 0.20 | **PARTIAL WIN** — meaningful cum_rf improvement without geo collapse |
| -0.09 < cum_rf < -0.07 AND geo ≈ 0.20-0.27 | **NEUTRAL** — phi_abs=0 doesn't matter much; mechanism elsewhere |
| cum_rf ≥ -0.09 AND geo < 0.10 | **COLLAPSE** — phi_abs is structural stabilizer; can't drop |
| Any other | record outcome, characterize separately |

## Gate

| Outcome | Decision |
|---------|----------|
| STRONG WIN | Reserve R259 to verify on additional seeds (s49, s51) + cross-scenario; if robust → paper section update |
| PARTIAL WIN | Reserve R259 with phi_abs sweep (5, 10, 25) to find Pareto optimum |
| NEUTRAL | Pivot to R259 = hybrid RL+droop warm-start (CLM-0470 candidate c) |
| COLLAPSE | Close R258 + log "phi_abs is structural"; pivot R259 to warm-start path |

## 资产保护契约

**No env code touched** — `--phi-abs 0` is an existing CLI flag (train.py:113).
This is a CONFIG choice, not env modification. No paper-cited asset
modification per CLAUDE.md rule.

**Cross-platform**:
- Run training in WSL ANDES (per `docs/eng-notes/NOTES_ANDES.md`)
- All paths absolute, ASCII output
- Save dir `results/r258_w1_scalar_phif_only_no_phiabs_s50` (mirrors R254 naming convention)

**Dual-metric required**: score_run.py emits both `geo` (11-axis) and
`cum_rf` (paper §IV-C). Both must be in verdict per CLM-0430 lint policy.

**V4 regression**: no env change, so V4 1e-9 contract preserved.

## Cross-references

- CLM-0445 (R252 — paper 7th contribution candidate explicitly proposed:
  "RL trained with cum_rf directly as reward (or hybrid RL+droop) might
  Pareto-dominate")
- CLM-0455 (R254 — phi_f=100, phi_abs=50 → geo=0.2655, cum_rf=-0.0878)
- CLM-0470 (R256 — over-actuation mechanism)
- CLM-0475 (R257 — smoothness inversion; both LAMBDA_SMOOTH directions dead)
- R246 plan/verdict (phi_abs=50, phi_f=0 → geo=0.2346, cum_rf=-0.0917 —
  the opposite end of the phi configuration space)
- R248 plan/verdict (phi_h=phi_d=1.0 paper-strict → collapse; defines
  the catastrophic-collapse boundary)
- `scripts/train.py` (--phi-abs flag, default 50.0)
- `docs/eng-notes/NOTES_ANDES.md` (WSL ANDES protocol)
