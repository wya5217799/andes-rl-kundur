---
round: R52
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R52 plan — time-in-obs probe (give policy explicit phase info)

**Date**: 2026-05-17
**Type**: experiment (obs augmentation)
**Trigger**: R49/R50/R51 closed the three cheapest temporal-flatness
levers (obs aug, reward shape, algorithm change). CLM-0059's
structural finding: "any deterministic-mode policy on V4 +
decentralized + paper-faithful reward converges to static setpoint
because they lack trajectory-phase information." Test the cheapest
structural fix: add `t / T_episode` to obs so the deterministic
policy can output time-varying action without recurrent state.

## Setup

- New V4Config field `include_time_obs: bool = False` (default
  paper-faithful, mutually exclusive with `include_own_action_obs`
  via `__post_init__` check)
- Mirror the env-var entry point `INCLUDE_TIME_OBS=1` for fast
  research toggle (consistent with INCLUDE_OWN_ACTION_OBS path)
- base_env.py: when flag set, OBS_DIM += 1 and `_build_obs` appends
  `step_count / max(STEPS_PER_EPISODE, 1)` to slot -1
- V4 env constructor: late-enable from cfg, bump OBS_DIM
- train.py `obs_dim_with_optional_action`: extended to recognise
  the new env var and enforce mutual exclusion at the CLI layer

## Pre-flight

- Default `INCLUDE_TIME_OBS=0` → bit-identical regression: re-ran
  `eval_no_control.py` after the edits, LS1 max_df=0.189,
  LS2=0.168 unchanged (paper baseline preserved).
- First attempt at training failed because train.py's
  `obs_dim_with_optional_action` only handled INCLUDE_OWN_ACTION_OBS.
  Replay buffer was allocated with obs_dim=7 but env produced
  obs_dim=8; `ValueError: could not broadcast input array from
  shape (8,) into shape (7,)`. Fixed by extending the helper +
  the log print. Retry succeeded with `[obs] INCLUDE_TIME_OBS=1
  -> obs_dim 7 -> 8` printed at train start.

## Part α — 3 seed sweep at h=64 baseline

3 seeds × 75 ep,
`INCLUDE_TIME_OBS=1 python scripts/train.py --algo td3
--normalize-actions --episodes 75 --seed <S> --hidden-size 64
--save-dir results/td3_norm_h64_timeobs_s<S>`.

Same seeds (49/50/51) as R48-β baseline for direct comparison.

## Predictions

| outcome | 6-axis | interpretation |
|---|---:|---|
| ≥ 0.40 | strong win | phase info is the missing lever; new production |
| 0.35-0.40 | meaningful win | partial unlock; LSTM might do better |
| 0.32-0.35 | marginal | similar to baseline; time-in-obs not load-bearing |
| 0.20-0.32 | drop | adding dim hurts more than helps |
| ≪ 0.20 | catastrophic | obs space pollution / hijack-like effect |

**Diagnostic to watch**: per-agent dM_span %. If time-in-obs works,
this should jump from baseline 9-21 % toward 30 %+.

## Out of scope

- LSTM actor (~1 day impl, R53+ candidate)
- Windowed-horizon smoothness reward (~30 min impl, R53+ candidate)
- Curriculum disturbance magnitude (~2-3 hr impl)
- Combined time-obs + LAMBDA_SMOOTH sweep — first establish baseline
  result for time-obs alone

## Addresses

Structural temporal-flatness bottleneck identified by CLM-0057 (R49 obs
probe), CLM-0058 (R50 reward shape), CLM-0059 (R51 SAC algorithm) —
the cheapest remaining structural fix.
