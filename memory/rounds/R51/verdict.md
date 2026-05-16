# R51 verdict — SAC h=64 FAILS; structural bottleneck identified

**Date**: 2026-05-17
**Status**: **COMPLETE**. Third consecutive negative result clarifies
the structural nature of the temporal-flatness bottleneck.
**Type**: experiment (algorithm comparison)
**Wall**: ~15 min (~10 min training in parallel + scoring)

---

## TL;DR

> SAC + normalized + h=64 reaches **mean 6-axis = 0.107** (3-seed,
> range [0.094, 0.118]), fractionally WORSE than SAC h=128 (0.117,
> CLM-0048). The "capacity confound" hypothesis is refuted.
>
> Critical insight from the diagnostic: SAC's eval-time `deterministic=True`
> outputs the policy mean. Per-agent dM_span = 0.7 %, dD_span = 0.3 %
> — same static-setpoint behaviour as TD3 + R50 anti-smoothness failure
> (also 0.3-0.5 %). **SAC's entropy term provides exploration variation
> during training, not policy-internal temporal variation at eval.**
>
> Together with CLM-0057 (R03 obs probe negative) and CLM-0058
> (anti-smoothness reward negative), R51 closes the THIRD cheap
> candidate for the temporal-flatness bottleneck. **Structural
> finding**: any deterministic-mode policy on V4 + decentralized
> obs + paper-faithful reward converges to static setpoint
> regardless of training algorithm, obs augmentation, or
> reward-shaping experiments. CLM-0059.

---

## Setup

3 seeds × 75 episodes, `--algo sac --normalize-actions
--hidden-size 64`. Same seeds (49/50/51) as R48-β TD3 baseline.
Goal: isolate the SAC algorithm effect from h-size effect — the
CLM-0048 SAC failure was at h=128, which CLM-0054 showed is
over-parameterised; perhaps at h=64 (the TD3 sweet spot) SAC's
entropy + capacity-appropriate net would unlock something.

## Results

| seed | LS1 | LS2 | **geo** | max_df | settling | dH_util | dD_util | dM_span% | dD_span% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 49 | 0.104 | 0.113 | 0.108 | 0.49 | 0.00 | 0.002 | 0.002 | 0.7 % | 0.3 % |
| 50 | 0.127 | 0.111 | **0.118** | 0.55 | 0.00 | 0.001 | 0.001 | 0.4 % | 0.4 % |
| 51 | 0.115 | 0.078 | 0.094 | 0.46 | 0.00 | 0.003 | 0.003 | 1.1 % | 0.4 % |
| **mean** | — | — | **0.107** | 0.50 | 0.00 | 0.002 | 0.002 | 0.7 % | 0.3 % |

vs reference:
- **R48-β TD3 h=64 baseline**: 0.334, max_df=0.97, dH_util≈0.04,
  dD_util≈0.10, dD_span≈12 %
- CLM-0048 SAC h=128: 0.117 (SAC attractor)
- R50-α LAMBDA=-100 fail: 0.110, dD_span=0.3 %
- no_control: 0.094

### Three immediate observations

1. **SAC h=64 ≈ SAC h=128** (0.107 vs 0.117). The capacity-confound
   hypothesis from R51 plan is refuted. CLM-0048's structural-SAC
   finding stands.
2. **SAC h=64 ≈ R50 anti-smoothness fail** (0.107 vs 0.110). Both
   achieve dM_span ≈ 0.5 % and produce static-setpoint deterministic
   policies. Different failure mechanisms, same end state.
3. **max_df axis drops to 0.50** (from 0.97 in TD3 h=64). SAC's
   entropy noise during training prevents the policy from
   precision-tracking the disturbance peak — even max_df (the
   "easy" axis that TD3 nearly saturates) becomes a gap.

### The key insight

The deterministic eval mode collapses ALL three "attack temporal
flatness" experiments into the same failure pattern:

| round | lever | mean | dM_span % | dD_span % | mechanism |
|---|---|---:|---:|---:|---|
| R48-β baseline | (none) | 0.334 | 9-21 | 11-13 | static setpoint (mild) |
| R49-α | INCLUDE_OWN_ACTION_OBS | 0.263 | 19 (mixed) | 4.6 | static setpoint (self-reinforced) |
| R50-α | LAMBDA_SMOOTH=-100 | 0.110 | 0.5 | 0.3 | static setpoint (noise hijack) |
| **R51-α** | **SAC h=64** | **0.107** | **0.7** | **0.3** | **static setpoint (policy mean)** |

The "static setpoint at eval" attractor is **invariant** under:
- Training algorithm switch (TD3 → SAC)
- Observation augmentation (omega_dot already present, last-action
  added)
- Per-step reward shaping (smoothness penalty / bonus)
- Hidden-size variation (h=64 / h=128 both give static-mode policies)

This is genuinely structural. What it implies: the only remaining
ways to unlock temporal variation at eval are:

1. **Recurrent state (LSTM actor)**. The policy itself becomes
   time-varying because its hidden state encodes the trajectory
   phase. Even in deterministic eval, the policy output changes
   with time because the hidden state changes.
2. **Windowed / episode-level reward shaping** (~30 min impl).
   Replace per-step `|action - prev_action|²` with a window-statistic
   like `std(action over 5-step window)`. Per-step noise variance
   averages out as `1/window`; only the policy-driven trajectory
   shape survives. Theoretically hijack-resistant.
3. **Curriculum disturbance** (~2-3 hr impl). Harder disturbances
   force the optimal control policy to have larger temporal range;
   the policy then carries that range to easier disturbances too.
4. **Time-as-observation**. Add `t / T_episode` to obs (one dim).
   Gives the policy explicit phase info. Cheapest if it works
   (~30 min impl, no recurrence needed).

## Project-wide 6-axis scoreboard (post-R51)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed | 0.094 | reference |
| no_control G4-preserved | 0.101 | Q-0001 closed (R44) |
| **R51-α SAC norm h=64** | **0.107** | **SAC fails again, capacity confound refuted (CLM-0059)** |
| R50-α LAMBDA=-100 | 0.110 | anti-smoothness fail (CLM-0058) |
| R43-α SAC normalized h=128 | 0.117 | CLM-0048 |
| SAC attractor (R23-R27) | 0.137 | |
| R49-α R03 obs probe | 0.263 | obs aug fail (CLM-0057) |
| R47-β TD3 norm 200ep | 0.269 | plateau |
| R41-B TD3 norm 75ep h=128 (superseded) | 0.275 | |
| R43-β HAWE h=128 uniform | 0.310 | |
| R47-α HAWE top-3 uniform | 0.315 | |
| **R48-β TD3 norm 75ep h=64** | **0.334** | **current production (CLM-0055)** |
| **R48-δ HAWE h=64 median** | **0.351** | **current ensemble (CLM-0056)** |
| R41-C s52 single seed (lucky) | 0.353 | |
| **R48-β s51 h=64 single** | **0.365** | **strongest non-lucky single** |
| R21 lucky basin | 0.444 | |
| HAWE w9802 | 0.439 | |
| paper target | ~1.00 | unreached |

## What R51 establishes

- **CLM-0059**: SAC h=64 fails the same way SAC h=128 failed;
  capacity-confound refuted; the deterministic-eval-setpoint
  attractor is invariant to algorithm choice.
- **Triple-negative for the temporal-flatness bottleneck**:
  R49 (obs aug), R50 (reward shape), R51 (algorithm change) all
  produce the same static-setpoint deterministic policy. The
  bottleneck is structural, not surface.
- **Remaining lever shortlist** (3 candidates): (a) windowed-
  horizon reward, (b) curriculum disturbance, (c) recurrent
  actor / time-in-obs.

## What R51 does not establish

- Whether windowed reward bypasses the hijack channel cleanly.
- Whether time-as-obs (cheapest structural fix) helps.
- Whether LSTM actor unlocks new ground.
- Whether the paper's reported utilization scores were achieved
  through a different action-space or env that's incompatible
  with our V4 setup.

## New claims this round

- `CLM-0059` — R51-α SAC h=64 = 0.107 (vs SAC h=128 0.117);
  capacity-confound refuted; deterministic-eval-setpoint attractor
  is structurally invariant to algorithm/obs/reward changes.

## Questions opened (this round)
- (none — R51 narrowed the lever shortlist rather than opening new
  uncertainty)

## Questions closed (this round)
- (none — Q-0004 remains Codex's)

## Questions advanced (this round, status unchanged)
- (none)
