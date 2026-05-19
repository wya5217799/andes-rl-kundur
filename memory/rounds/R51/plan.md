---
round: R51
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R51 plan — SAC h=64 normalized (test stochastic policy on the hijack-immune lever)

**Date**: 2026-05-17
**Type**: experiment (algorithm comparison at h=64)
**Trigger**: R49 + R50 closed the two cheapest "directly attack
temporal flatness" levers via the same root cause — exploration-noise
hijack of the per-step learning signal (CLM-0057, CLM-0058). The
remaining cheap candidate that **structurally avoids the hijack
channel** is to use a stochastic policy where the variation comes
from the policy distribution itself, not from added exploration
noise.

## Why SAC h=64 is the right next probe

- CLM-0048 already tested SAC + normalized at h=128 → mean 0.117
  (≪ TD3's 0.275). Concluded SAC has structural disadvantage on V4.
- But R48 (CLM-0054) showed h=128 is **over-parameterised** for V4
  (obs_dim=7, h=64 sweet spot, +21 % over h=128 for TD3 norm).
- The SAC test at h=128 may have been confounded by capacity, not by
  algorithm. Re-testing at h=64 isolates the algorithm effect.
- SAC's entropy term IS the policy distribution variation. Smoothness
  reward / utilization metric depend on action variation. If
  stochastic policy is the right tool, SAC h=64 should at minimum
  improve utilization scores even if total 6-axis doesn't beat
  TD3.

## Setup

3 seeds × 75 episodes,
`python scripts/train.py --algo sac --normalize-actions
--episodes 75 --seed <S> --hidden-size 64
--save-dir results/sac_norm_h64_s<S>`.

Same seeds (49/50/51) as R48-β for direct comparison.

## Predictions

| outcome | 6-axis mean | interpretation |
|---|---:|---|
| **≥ 0.30** | better than CLM-0048 baseline (0.117) and approaching TD3 h=64 (0.334) | SAC works at h=64; the original SAC-bad finding was capacity-confounded |
| 0.20-0.30 | meaningful improvement over CLM-0048 but still below TD3 | SAC h=64 is partially recovered; capacity was a factor but not the only one |
| 0.13-0.20 | similar to SAC attractor (0.137) | SAC's entropy variance defeats narrow-target frequency control regardless of capacity |
| < 0.13 | worse than CLM-0048 | h=64 hurts SAC for unknown reason |

## Critically, look at utilization axes

Even if 6-axis total < 0.334 baseline, **if dH/dD_utilization scores
rise meaningfully** (e.g., 0.05 → 0.20+), it would support the
"stochastic policy gives temporal variation" hypothesis. That would
unlock cross-algorithm HAWE: TD3 h=64 (strong frequency) + SAC h=64
(better utilization) might exceed either alone.

## Follow-up plan

- **R51 ≥ 0.30**: build on. R52 = SAC + CTDE h=64 (shared critic;
  uses existing `--ctde` flag, SAC-only by `train.py:195-196`
  guard). Test if coordinated stochastic policies break the 0.351
  ensemble cap.
- **R51 < 0.30 but utilization improved**: R52 = cross-algorithm
  HAWE of {TD3 h=64 s49/50/51, SAC h=64 s49/50/51}. Test diversity-
  driven complementarity.
- **R51 ≪ 0.30 and utilization unchanged**: SAC is structurally bad
  on V4 (capacity was not the confound). Pivot away from
  stochastic-policy direction. R52 = windowed-horizon smoothness
  reward (~30 min impl) — averages out per-step noise so hijack
  channel is suppressed.

## Out of scope

- TD3 + CTDE (no existing class; `--ctde` is SAC-only by guard at
  train.py:195. Building TD3AgentCTDE is ~1-2 hr work; deferred to
  R53+ if R52 closes the SAC direction)
- LSTM actor (~1 day impl)
- Curriculum disturbance magnitude (~2-3 hr impl)

## Pre-flight

- Codex's R45 V4Config refactor + checkpoint_loader auto-detect
  (commits `1fd945b`, `a8e762a`) means load_agents auto-detects
  hidden_size from ckpt; no inline workaround needed.
- env var `LAMBDA_SMOOTH=0` is the default (paper-faithful), but
  R50 also added it as a `V4Config.lambda_smooth` field — train.py
  default leaves it 0.

## Addresses

- The "temporal-flatness bottleneck" diagnosed in R48-β / R49 / R50
- Confounding factor between CLM-0048 (SAC at h=128) and h-size
  effect documented in CLM-0054
