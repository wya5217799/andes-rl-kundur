# R50 verdict — Anti-smoothness reward FAILS (exploration-noise hijack)

**Date**: 2026-05-17
**Status**: **COMPLETE**. Reward-shaping lever tested and refuted.
**Type**: experiment (reward shaping, negative result)
**Wall**: ~15 min (1-line guard fix + 3 parallel trainings + scoring)

---

## TL;DR

> Setting `LAMBDA_SMOOTH=-100` (negate the existing r_smooth term so
> per-step action change is *rewarded*) at TD3 norm 75ep h=64
> **collapses the 6-axis to 0.110** (−67 % below R48-β baseline
> 0.334), drops *below* the SAC attractor 0.137 and approaches
> no-control 0.094.
>
> Mechanism: **exploration-noise hijack**. The training reward
> averages **+91 per agent per episode** (vs baseline −2) because
> exploration noise (σ ≈ 0.1 Gaussian) generates per-step action
> variation regardless of the actor's deterministic output. The
> critic cannot learn to credit useful policy choices over
> useless ones — both yield identical reward through the same
> noise channel. The deterministic policy at eval time collapses
> to a near-constant setpoint per agent (span 0.3 - 0.7 %, far
> worse than baseline's 9 - 21 %); frequency control failed
> entirely (max_df 0.18 - 0.19 Hz, settling = 0).
>
> Together with R49-α (R03 obs probe negative), this closes the
> two cheapest candidate levers for the per-agent temporal-flatness
> bottleneck. CLM-0058.

---

## Pre-flight: one-line guard fix

`base_env.py:343` previously gated the smoothness term on
`if self._lambda_smooth > 0.0:`, silently ignoring negative values.
Changed to `!= 0.0` so non-zero LAMBDA_SMOOTH activates regardless
of sign. Default 0.0 stays paper-faithful. Inline comment credits
R50/CLM-0057.

## Setup

3 seeds × 75 episodes, `--algo td3 --normalize-actions
--hidden-size 64`, `LAMBDA_SMOOTH=-100` set in shell at train time.
Same seeds (49/50/51) as R48-β for direct per-seed comparison.

Training reward decomposition during R50-α (from logs):
- Total reward: **+91 per agent per episode** at episode 70/75
- Compare R48-β baseline: ≈ −2 per agent per episode

The training reward signal is **positive 50×** larger than baseline,
entirely driven by the per-step r_smooth term being maxed by
exploration noise. This is the warning sign that exploration noise
has hijacked the learning channel.

## Results

| seed | LS1 | LS2 | **geo** | dH_util | dD_util | dH_smooth | dD_smooth | settling | dM_span% | dD_span% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 49 | 0.104 | 0.113 | **0.108** | 0.002 | 0.002 | 0.987 | 0.993 | 0.00 | 0.7 % | 0.3 % |
| 50 | 0.127 | 0.111 | **0.118** | 0.001 | 0.001 | 0.990 | 0.993 | 0.00 | 0.4 % | 0.4 % |
| 51 | 0.116 | 0.095 | **0.105** | 0.001 | 0.001 | 0.994 | 0.997 | 0.00 | 0.4 % | 0.2 % |
| **mean** | — | — | **0.110** | 0.001 | 0.001 | 0.990 | 0.994 | 0.000 | 0.5 % | 0.3 % |

vs R48-β baseline (mean 0.334, range [0.295, 0.365], dH_util ~ 0.04,
dD_util ~ 0.10, dM_span ~ 9-21 %, dD_span ~ 11-13 %, settling ~ 0.7).

### Direction of every axis is wrong

| axis | direction | R48-β baseline | R50-α | comment |
|---|---|---:|---:|---|
| dH_util | wanted UP | 0.04 | 0.001 | collapsed |
| dD_util | wanted UP | 0.10 | 0.001 | collapsed |
| dM_span % | wanted UP | 9-21 % | 0.5 % | collapsed |
| dD_span % | wanted UP | 11-13 % | 0.3 % | collapsed |
| dH_smooth | preserved OK | 0.72 | 0.99 | "improved" (actor maximally smooth) |
| dD_smooth | preserved OK | 0.72 | 0.99 | "improved" |
| settling | preserved OK | 0.7 | 0.00 | catastrophic — never settles |
| max_df | preserved OK | 0.97 | ≈0.4 | frequency control failed |

The actor learned a degenerate **near-constant setpoint per agent**
policy, producing eval-time max_df = 0.18 - 0.19 Hz (paper target
0.13). The smoothness axis went UP because the actor barely changes
its action (consistent with paper-smoothness target of 0), but every
other axis fell.

## Mechanism — exploration-noise hijack

Reading the training and eval data together:

1. During training, TD3 adds exploration noise (Gaussian σ ≈ 0.1)
   to actions before applying them. So even if the actor outputs a
   constant action, the env sees actions that change by ~10 % per
   step.
2. The smoothness term is computed on the env-applied action (with
   noise), not on the deterministic actor output: `smooth_pen =
   Σ ((delta_M[t] - delta_M[t-1])/dM_range)²`.
3. With λ = -100, this gives a per-step reward of ~ +1 to +4 just
   from the noise channel. Over 50 steps × 4 agents, that's
   +200 to +800 per episode "free" reward, regardless of actor
   choice.
4. The critic sees: "any actor output yields high reward". Q-values
   for different actor outputs converge to similar values. Actor
   gradient toward policy improvement collapses.
5. The actor's deterministic output (no noise) becomes whatever
   trivial setpoint minimises the *other* reward terms (r_f, r_h,
   r_d) — i.e., the static-setpoint baseline behaviour, but with
   no incentive to even react to disturbances (because all rewards
   are negative).
6. At eval time, no exploration noise → action span collapses to
   near zero → utilization scores collapse, smoothness "wins"
   trivially, frequency control fails.

This is a clean instance of a known deep-RL pitfall: when reward
signal correlates more with exploration noise than with actor
output, on-policy reward decouples from deterministic-policy
performance and the learning signal collapses.

## Implication for future rounds

Naive per-step anti-smoothness reward is unworkable on TD3 + V4.
Any reward shaping for temporal action variation must address the
hijack pathway, e.g. one of:

- **(a) Compute the smoothness reward on the deterministic-policy
  output, not the noise-augmented env action.** Requires
  restructuring `step()` to query `actor.deterministic_forward(obs)`
  separately for reward calc.
- **(b) Operate on a horizon longer than per-step noise.** E.g.,
  reward standard deviation of actions across a sliding window of
  ~10 steps. Noise's per-step variance averages out over the
  window; only the actor's policy-driven variation remains.
- **(c) Switch to a stochastic policy (SAC).** SAC's entropy IS
  the policy variation — the entropy term is computed on the
  policy distribution, not the executed action, so there's no
  noise-hijack channel. But CLM-0048 showed SAC underperforms
  TD3 by ≈ 0.18 (0.117 vs 0.275). May or may not be net positive
  at h=64.
- **(d) Recurrent policy (LSTM actor) with explicit time-varying
  output.** Provides temporal variation as a structural property
  of the policy, not a reward-shaping target. Major arch change.

## Project-wide 6-axis scoreboard (post-R50)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed | 0.094 | reference |
| no_control G4-preserved | 0.101 | Q-0001 closed (R44) |
| **R50-α TD3 norm h=64 LAMBDA=-100** | **0.110** | **anti-smoothness FAILS (CLM-0058)** |
| R43-α / R41-A SAC | 0.117 | H3 |
| SAC multi-seed attractor | 0.137 | |
| R40 TD3 phi=0 75ep | 0.259 | |
| R49-α R03 obs probe (h=64) | 0.263 | obs probe failed (CLM-0057) |
| R47-β TD3 norm 200ep | 0.269 | plateau |
| R41-B TD3 norm 75ep h=128 (superseded) | 0.275 | old prod (CLM-0047) |
| R43-β HAWE h=128 uniform | 0.310 | |
| R44-α HAWE s52 90% | 0.347 | |
| **R48-β TD3 norm 75ep h=64** | **0.334** | **current production** |
| **R48-δ HAWE h=64 median** | **0.351** | **current ensemble** |
| R41-C s52 single seed | 0.353 | lucky-tail |
| R48-β s51 h=64 single | 0.365 | strongest non-lucky single |
| R21 lucky basin SAC | 0.444 | |
| HAWE w9802 | 0.439 | |
| paper target | ~1.00 | unreached |

## What R50 establishes

- **CLM-0058**: anti-smoothness reward at LAMBDA_SMOOTH=-100
  catastrophically fails on TD3+V4 via exploration-noise hijack
  mechanism. The training-reward signal decouples from
  deterministic-policy performance, leading to degenerate
  constant-setpoint policies at eval.
- **Together with R49-α / CLM-0057**: the two cheapest "directly
  attack temporal flatness" levers (obs augmentation and naive
  reward shaping) both fail. Remaining options are structurally
  more expensive: deterministic-output smoothness reward,
  windowed-horizon reward, stochastic policy, or recurrent
  actor.
- **base_env.py guard fix** (line 343, `> 0.0` → `!= 0.0`):
  enables negative LAMBDA_SMOOTH globally. Stays inert at default
  0.0 (paper-faithful baseline preserved).

## What R50 does not establish

- Whether smaller |λ| values (e.g., -1, -10) avoid the noise
  hijack. Plausible but untested. The hijack scales with λ, so
  smaller λ might leave a usable signal-to-noise ratio.
- Whether windowed-horizon smoothness reward works. Untested.
- Whether SAC at h=64 + normalized escapes the static attractor
  (CLM-0048 showed SAC underperforms at h=128).
- Whether recurrent actor helps.

## New claims this round

- `CLM-0058` — R50-α anti-smoothness reward LAMBDA=-100 fails:
  mean 0.110, exploration-noise hijack mechanism documented.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)
