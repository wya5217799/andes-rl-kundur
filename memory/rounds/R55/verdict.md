# R55 verdict — windowed-horizon FAILS; 6-failure hexagon closes cheap-lever space

**Date**: 2026-05-17
**Status**: **COMPLETE**. Hijack-resistance hypothesis from R50
verdict refuted; sixth consecutive negative attack confirms
structural ceiling.
**Type**: experiment (reward shaping, negative result with
mechanism correction)
**Wall**: ~25 min (~15 min code + 3 parallel trainings ~10 min wall
+ scoring)

---

## TL;DR

> Telescoping diff `(a[t] - a[t-10])²` (windowed) with λ=-100 at
> TD3 norm 75ep h=64 yields **mean 6-axis = 0.1104** — **identical
> to R50's W=1 result 0.110**. Training reward +89–+125 / agent
> (R50: +91), same hijack magnitude.
>
> The R50 verdict's "windowed-horizon could bypass noise hijack
> via averaging" hypothesis is **REFUTED**. Mechanism correction:
> per-step noise variance in `(a[t] - a[t-W])²` is **2σ²
> REGARDLESS of W** (both noise terms are independent draws).
> Policy-driven signal would scale with W only IF the deterministic
> policy drifted; it doesn't, because the noise-induced reward
> channel collapses the actor-gradient signal.
>
> **Sixth consecutive negative finding closes the cheap+medium
> lever space**:
> - R49 obs aug (-21 %)
> - R50 per-step anti-smoothness (-67 %)
> - R51 SAC stochastic policy (-68 %)
> - R52 time-in-obs (-19 %)
> - R54 warmstart-shared (-8 %)
> - R55 windowed anti-smoothness (-67 %, same as R50)
>
> CLM-0062. The 0.334 / 0.365 / 0.351 production triangle is now
> bounded by six independent attacks. Pushing past requires
> architectural change (LSTM actor, deterministic-output reward,
> sparse end-of-episode reward, true param-sharing, curriculum
> env) — none cheap, all ≥ 1-2 hr work, none guaranteed.

---

## Implementation (four-file edit)

| File | Change |
|---|---|
| `v4_config.py` | new field `smoothness_window: int = 1` with doc |
| `base_env.py` | env-var entry `SMOOTHNESS_WINDOW=N`, `_action_history_dM/dD` deques, reset clear, telescoping branch in r_smooth block |
| `andes_vsg_env_v4.py` | cfg.smoothness_window late-enable; **cfg.lambda_smooth override made conditional** (only if non-default 0.0) so env-var path keeps working |
| `scripts/train.py` | (unchanged — env var path used) |

Regression: `eval_no_control.py` with LAMBDA=-100 W=10 still
reproduces LS1=0.189 LS2=0.168 (no_control's zero action makes
smooth_pen=0 either way). Default `smoothness_window=1` preserves
paper-faithful behaviour.

## Results

| seed | LS1 | LS2 | **geo** | max_df | settling | dH_util | dD_util | dM_sp% | dD_sp% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 49 | 0.104 | 0.113 | 0.108 | 0.49 | 0.00 | 0.002 | 0.002 | 0.7 | 0.3 |
| 50 | 0.127 | 0.111 | 0.118 | 0.55 | 0.00 | 0.001 | 0.001 | 0.4 | 0.4 |
| 51 | 0.116 | 0.095 | 0.105 | 0.32 | 0.00 | 0.001 | 0.001 | 0.4 | 0.2 |
| **mean** | — | — | **0.1104** | 0.45 | 0.00 | 0.001 | 0.001 | 0.5 | 0.3 |

Direct comparison to R50 (same λ=-100, W=1):

| metric | R50 W=1 | R55 W=10 | Δ |
|---|---:|---:|---:|
| mean 6-axis | 0.110 | 0.110 | 0.000 |
| train reward | +91 / agent | +89 / agent | ~0 |
| eval dM_span | 0.5 % | 0.5 % | 0 |
| eval dD_util | 0.001 | 0.001 | 0 |
| max_df axis | 0.50 | 0.45 | −0.05 |
| settling | 0.00 | 0.00 | 0 |

**Identical hijack pattern**: actor collapses to near-constant
deterministic output at eval; training reward is dominated by
exploration noise; frequency control completely fails.

## Mechanism correction (vs R50 verdict's hypothesis)

R50 verdict point (b): *"Operate on a horizon longer than per-step
noise. Noise's per-step variance averages out over the window; only
the actor's policy-driven variation remains."*

Correction: this reasoning conflated two metrics. The per-step
diff at W=1 and telescoping diff at W=10 are BOTH of the form
`(a[t] - a[t-W])²`. The variance contribution from independent
noise draws is:

  Var[(noise[t] - noise[t-W])²] ≈ 2σ²  for ANY W ≥ 1.

The signal that scales with W is `(policy[t] - policy[t-W])²`. But
this signal exists only if the policy drifts systematically over
W steps. In our problem the deterministic policy is static-setpoint
(established by R49–R54), so policy_diff ≈ 0 at all W.

Result: at any W, the smoothness reward is noise-dominated.
λ=-100 turns this into a per-step bonus of ~ +1 to +4 / step
regardless of W, driving training reward up to +91 / agent /
episode while the actor's deterministic component collapses to
constant (because Q-value is flat across actor outputs).

The hijack channel does not have a window-size-based escape
hatch. The only escapes are:

1. **Compute the smoothness term on the DETERMINISTIC actor output**
   (the mean, before noise is added). This is hijack-immune
   because noise doesn't enter the reward at all. Requires
   refactoring env.step interface to receive both (mean_action,
   noisy_action). ~1-2 hr work.
2. **Sparse end-of-episode reward** based on episode-aggregated
   action statistics (e.g., std over the trajectory). Per-step
   reward is unchanged. ~30 min impl but TD3 sparse-reward
   learning is unreliable.
3. **LSTM recurrent actor** — policy is structurally time-varying
   because hidden state encodes trajectory phase. Deterministic
   eval naturally varies. ~1 day work.

## Project-wide 6-axis scoreboard (post-R55)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed | 0.094 | reference |
| no_control G4-preserved | 0.101 | Q-0001 closed |
| R51-α SAC norm h=64 | 0.107 | CLM-0059 |
| **R55-α TD3 h=64 λ=-100 W=10** | **0.110** | **CLM-0062 (this round)** |
| R50-α LAMBDA=-100 W=1 | 0.110 | CLM-0058 |
| R43-α SAC norm h=128 | 0.117 | |
| R49-α R03 obs probe | 0.263 | CLM-0057 |
| R52-α time-in-obs | 0.270 | CLM-0060 |
| R54-α warmstart-shared | 0.306 | CLM-0061 |
| R43-β HAWE h=128 uniform | 0.310 | |
| **R48-β TD3 norm 75ep h=64** | **0.334** | **production single-seed (CLM-0055)** |
| **R48-δ HAWE h=64 median** | **0.351** | **production ensemble (CLM-0056)** |
| R41-C s52 lucky-tail | 0.353 | |
| **R48-β s51 single** | **0.365** | **strongest non-lucky** |
| R21 lucky basin SAC | 0.444 | entropy-noise lottery |
| HAWE w9802 | 0.439 | |
| paper target | ~1.00 | unreached |

## The six-failure hexagon

| Round | Lever | mean | Δ | Distinct mechanism |
|---|---|---:|---:|---|
| R49 | obs aug (action history) | 0.263 | −21 % | self-reinforcing static loop |
| R50 | reward (per-step anti-smoothness) | 0.110 | −67 % | exploration-noise hijack |
| R51 | algorithm (SAC h=64) | 0.107 | −68 % | deterministic-eval-setpoint |
| R52 | obs (time-in-obs) | 0.270 | −19 % | phase info unused |
| R54 | init (warmstart-shared) | 0.306 | −8 % | uniformity vs peak-tracking |
| **R55** | **reward (windowed anti-smoothness)** | **0.110** | **−67 %** | **hijack is W-independent (R50 corrected)** |

Six distinct lever classes attacked, six failures. The bottleneck
is structural to the V4 environment + memoryless policy class +
paper-faithful reward function. The ceiling at 0.334 / 0.365 /
0.351 is rock-solid.

## What R55 establishes

- **CLM-0062**: windowed anti-smoothness reward (W=10) yields the
  same hijack-collapsed result as per-step (W=1); window size
  doesn't escape the noise-hijack channel.
- **Mechanism correction**: R50 verdict point (b)
  ("windowed-horizon hijack-resistant") was based on incorrect
  noise-variance analysis. Per-step noise variance contribution
  to telescoping diff is 2σ² independent of W.
- **Six-failure hexagon**: closes the cheap+medium-cost lever
  space for temporal-flatness bottleneck. Pushing past requires
  one of the three architectural pivots (deterministic-output
  reward, LSTM, sparse end-of-episode), all ≥ 1-2 hr work.

## What R55 does not establish

- Whether smoothness on deterministic-policy output works
  (option (a) in CLM-0058's leverage list).
- Whether LSTM recurrent actor breaks the static-setpoint attractor.
- Whether sparse end-of-episode std reward learns through TD3.
- Whether curriculum disturbance shifts the basin.

## New claims this round

- `CLM-0062` — R55-α windowed anti-smoothness (W=10) identical to
  R50 W=1; hijack-resistance hypothesis refuted; mechanism
  correction documented.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)
