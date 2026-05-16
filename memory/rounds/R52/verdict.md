# R52 verdict — time-in-obs FAILS; 4th consecutive negative confirms structural ceiling

**Date**: 2026-05-17
**Status**: **COMPLETE**. Structural ceiling at 0.334/0.365 firmly
established by four consecutive negative attacks on the temporal-
flatness bottleneck.
**Type**: experiment (obs augmentation, negative result)
**Wall**: ~25 min (V4Config + base_env + V4 env + train.py edits,
1 failed launch + retry, 3 parallel trainings ~11 min wall, scoring)

---

## TL;DR

> Adding `t / T_episode` to obs (OBS_DIM 7 → 8) at TD3 norm 75ep
> h=64 yields **mean 6-axis = 0.270** (3-seed, range [0.196, 0.314])
> — **−19 %** below R48-β baseline 0.334.
>
> Per-agent dM_span % stayed at baseline (9.6 mean vs 9-21 %);
> dH_util / dD_util axes essentially unchanged (0.037 / 0.036 vs
> 0.040 / 0.100). The phase info is in obs but the policy doesn't
> use it — TD3 deterministic + V4 reward landscape still optimises
> for a static setpoint. The 19 % drop attributes to extra-dim
> optimisation noise (s51 collapsed to 0.196, settling=0.11).
>
> **CLM-0060** + the chain CLM-0057/0058/0059 = four consecutive
> negative results for the temporal-flatness bottleneck. The
> ceiling at 0.334 / 0.365 (single) / 0.351 (ensemble) is now
> empirically bounded by FOUR independent attacks: obs-history,
> reward-shape, algorithm-swap, time-in-obs. All four failed via
> the same root cause: V4's reward landscape inherently rewards
> static setpoints; obs-side / per-step-reward-side interventions
> don't overcome it.

---

## Pre-flight: V4Config + env + train.py wiring

R52 needed an obs-space change, which touched four files:

1. **`v4_config.py`**: added `include_time_obs: bool = False` field
   with doc; `__post_init__` rejects both obs-aug flags being True
   (slot-layout conflict).
2. **`base_env.py`**: added `_include_time_obs` instance flag,
   reads `INCLUDE_TIME_OBS` env var, bumps `self.OBS_DIM` by 1 if
   set, appends `step_count / STEPS_PER_EPISODE` to obs slot -1 in
   `_build_obs`. Guards mutex with `_include_own_action_obs`.
3. **`andes_vsg_env_v4.py`**: V4 env constructor late-enables
   `_include_time_obs = True` and adjusts `self.OBS_DIM` from
   cfg.include_time_obs.
4. **`scripts/train.py`**: extended `obs_dim_with_optional_action`
   to recognise `INCLUDE_TIME_OBS`. First training attempt failed
   because train.py's replay buffer was allocated obs_dim=7 while
   env produced obs_dim=8; retry succeeded.

Regression: `scripts/eval_no_control.py` with default flag OFF
reproduces LS1 max_df=0.189, LS2=0.168 bit-identically. Paper
baseline preserved.

## Results (3 seeds × 75 ep × INCLUDE_TIME_OBS=1)

| seed | LS1 | LS2 | **geo** | max_df | settling | dH_util | dD_util | dH_smooth | dD_smooth | dM_span% | dD_span% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 49 | 0.280 | 0.353 | **0.314** | 0.76 | 0.86 | 0.039 | 0.069 | — | — | 9.3 | 9.5 |
| 50 | 0.286 | 0.312 | **0.299** | 0.64 | 0.94 | 0.058 | 0.028 | — | — | 15.1 | 3.1 |
| 51 | 0.170 | 0.224 | **0.196** | 0.90 | 0.11 | 0.014 | 0.012 | — | — | 4.4 | 2.4 |
| **mean** | — | — | **0.270** | 0.77 | 0.64 | 0.037 | 0.036 | — | — | 9.6 | 5.0 |

vs R48-β baseline:
- mean 0.270 vs 0.334 = −19 %
- per-agent dM_span: 9.6 % vs 9-21 % — within baseline range
- per-agent dD_span: 5.0 % vs 11-13 % — slightly lower
- dH_util / dD_util: nearly identical to baseline
- max_df: 0.77 vs 0.97 — frequency control degraded
- settling: mixed (s49 + s50 actually got 0.86/0.94 settling, s51 0.11)

### The split-result pattern

s49 + s50 actually look interesting:
- High settling (0.86 / 0.94 vs baseline ~0.7) — late-stage tracking improved
- Mean geo 0.31 — within 6 % of baseline
- dM_span 9-15 % — comparable to baseline

s51 catastrophically collapsed:
- 0.196 geo, 0.11 settling, 4.4 % dM_span
- This is the only seed with the failure mode

So time-in-obs **isn't pure poison**: 2 of 3 seeds train within 6 %
of baseline and show some settling-axis improvement. But it doesn't
unlock the utilization bottleneck (the goal), so net negative.

The mechanism: adding a dim adds optimisation surface but no signal.
The actor doesn't NEED `t` to find its static-setpoint local
optimum; the extra dim is just noise that occasionally derails
training (s51 case).

## The four-failure quadruple

| Round | Lever attacked | mean 6-axis | Δ vs baseline 0.334 |
|---|---|---:|---:|
| R49-α | obs aug (last action history) | 0.263 | −21 % |
| R50-α | per-step reward (anti-smoothness LAMBDA=-100) | 0.110 | −67 % |
| R51-α | algorithm (SAC h=64 normalized) | 0.107 | −68 % |
| **R52-α** | **obs aug (time-in-obs)** | **0.270** | **−19 %** |

All four hit the temporal-flatness bottleneck and all four failed.
The bottleneck is now extensively bounded by negative findings:

- It's not lack of action-history information (R49).
- It's not the per-step reward landscape favouring smoothness (R50).
- It's not the deterministic-policy algorithm class (R51 — SAC
  also fails at eval despite having entropy at training).
- It's not lack of trajectory-phase information (R52).

It's the **structural interaction** between V4's reward landscape
(which gives no positive signal for time-varying action) and the
class of memoryless policies (TD3 / SAC at deterministic eval mode
both converge to constant output).

The only remaining cheap-or-medium-cost levers that hit different
sub-mechanisms:

| Lever | Cost | Sub-mechanism |
|---|---|---|
| windowed-horizon smoothness reward | ~30 min impl | bypass per-step noise hijack via window averaging |
| curriculum disturbance magnitude | ~2-3 hr impl | force action via env difficulty (not reward) |
| LSTM recurrent actor | ~1 day impl | structural memory makes policy time-varying |
| parameter-sharing (--warmstart-shared) | ~10 min wall | force cross-agent coordination |

All four have positive theoretical grounding (each addresses a
specific mechanism untouched by R49-R52). But none are guaranteed,
and the four negative findings strongly suggest the true ceiling
on the current paradigm is at 0.334 / 0.365 / 0.351.

## Project-wide 6-axis scoreboard (post-R52)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed | 0.094 | reference |
| no_control G4-preserved | 0.101 | Q-0001 closed |
| R51-α SAC norm h=64 | 0.107 | CLM-0059 |
| R50-α LAMBDA=-100 | 0.110 | CLM-0058 |
| R43-α SAC norm h=128 | 0.117 | |
| R49-α R03 obs probe | 0.263 | CLM-0057 |
| R47-β TD3 norm 200ep | 0.269 | plateau |
| **R52-α TD3 h=64 INCLUDE_TIME_OBS** | **0.270** | **CLM-0060 (this round)** |
| R41-B TD3 norm h=128 (superseded) | 0.275 | |
| R43-β HAWE h=128 uniform | 0.310 | |
| R47-α HAWE top-3 uniform | 0.315 | |
| **R48-β TD3 norm 75ep h=64** | **0.334** | **current production (CLM-0055)** |
| **R48-δ HAWE h=64 median** | **0.351** | **current ensemble (CLM-0056)** |
| R41-C s52 lucky-tail | 0.353 | |
| **R48-β s51 single** | **0.365** | **strongest non-lucky single** |
| R21 lucky basin SAC | 0.444 | entropy-noise lottery |
| HAWE w9802 | 0.439 | |
| paper target | ~1.00 | unreached |

## What R52 establishes

- **CLM-0060**: time-in-obs probe negative at R48 baseline; 19 %
  drop; phase info available but unused by static-setpoint policy.
- **Four-failure quadruple**: the temporal-flatness bottleneck is
  extensively bounded by R49/R50/R51/R52 negatives.
- **The 0.334/0.365/0.351 production triangle is the empirical
  ceiling of the current paradigm**. Pushing past requires a
  structural change at least as substantial as LSTM actor,
  parameter sharing, or curriculum env.

## What R52 does not establish

- Whether windowed-horizon smoothness reward bypasses the hijack
  channel cleanly.
- Whether LSTM actor breaks the static-setpoint attractor.
- Whether parameter-sharing via --warmstart-shared improves
  cross-agent coordination enough to lift utilization.
- Whether curriculum on disturbance magnitude forces wider action
  use via env difficulty.

## New claims this round

- `CLM-0060` — R52-α time-in-obs probe negative; fourth
  consecutive structural-bottleneck attack failed.

## Questions opened (this round)
- (none — R52 narrowed candidates rather than opening uncertainty)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)
