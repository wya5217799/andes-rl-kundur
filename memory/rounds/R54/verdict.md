# R54 verdict — warmstart-shared FAILS; FIVE-failure pentacle confirms ceiling

**Date**: 2026-05-17
**Status**: **COMPLETE**. Fifth consecutive negative attack on the
temporal-flatness bottleneck confirms the 0.334/0.365/0.351
structural ceiling.
**Type**: experiment (initialization probe, negative result with
informative axis trade-off)
**Wall**: ~15 min (3 parallel trainings ~11 min + scoring)

---

## TL;DR

> Warmstart-shared from s51's agent_0 actor (the strongest single
> non-lucky source, geo 0.365) into all 4 agents of fresh training
> at h=64 norm 75ep yields **mean 6-axis = 0.306** (3 seeds,
> range [0.298, 0.321]) — **−8 %** below R48-β baseline (0.334).
>
> But the result is uniquely informative — first probe with a
> useful axis-level pattern:
> - settling axis: **0.88** (vs baseline ~0.70) — **+25 % up** via
>   shared-init inheritance from s51's settling profile
> - cross-agent corr_dD: **+0.32** (vs baseline +0.15) — coordination
>   materially up
> - dD_util / dD_span: slight uplift (+17 % / +28 % range)
> - max_df axis: **0.79** (vs baseline 0.97) — **−19 % down**;
>   uniform behaviour misses each agent's local frequency peak
>
> Reveals a V4-internal axis trade-off: **shared/coordinated
> behaviour helps settling+coordination but hurts max_df**. Two
> axes are structurally in tension.
>
> CLM-0061. Fifth round in the negative-finding pentacle:
> R49 obs aug / R50 reward / R51 algorithm / R52 time-in-obs /
> R54 shared init — all fail to break 0.334. The structural
> ceiling is now extensively bounded.

## Round number note

This work was originally numbered R53 in session draft, but
Codex committed R53 ("memory hygiene dogfood", commit `4e7a335`)
while these trainings ran. Renumbered to R54 to avoid collision;
result JSON files retain the `r53_*` prefix from when they were
named (no functional impact, reproducible by re-running scoring).

---

## Setup

`--warmstart-shared results/td3_norm_h64_s51/agent_0_best.pt
--warmstart-mode actor_and_critic` — loads s51's agent_0 weights
into all 4 agents of fresh training. After init, agents train
independently and diverge through per-agent gradients.

3 seeds: 49, 50, 52 (matched s49+s50 to R48-β baseline; s52 fresh
because warmstart-from-self for s51 adds little).

## Results

| seed | LS1 | LS2 | **geo** | max_df | settling | dH_util | dD_util | dM_sp % | dD_sp % | corr_dM | corr_dD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 49 | 0.264 | 0.337 | **0.298** | 0.82 | 0.86 | 0.040 | 0.133 | 10.4 | 16.7 | +0.26 | +0.32 |
| 50 | 0.288 | 0.312 | **0.299** | 0.70 | 0.89 | 0.074 | 0.126 | 36.6 | 14.2 | −0.07 | +0.34 |
| 52 | 0.298 | 0.345 | **0.321** | 0.85 | 0.89 | 0.029 | 0.092 | 10.4 | 11.4 | −0.08 | +0.29 |
| **mean** | — | — | **0.306** | 0.79 | 0.88 | 0.048 | 0.117 | 19.1 | 14.1 | +0.04 | **+0.32** |

vs R48-β baseline (fresh init):
- mean 0.306 vs 0.334 = **−8 %**
- Range tight [0.298, 0.321] vs baseline [0.295, 0.365] — no
  high tail, but also no low tail
- settling axis: 0.88 vs ~0.70 = **+25 %**
- dD_util: 0.117 vs 0.100 = +17 %
- dD_span: 14.1 % vs 11-13 % = within and above range
- max_df: 0.79 vs 0.97 = **−19 %**
- corr_dD: +0.32 vs ~+0.15 = **+0.17 in raw correlation**

### Per-seed comparison to fresh

| seed | R48-β fresh | R54 warmsh | Δ |
|---|---:|---:|---:|
| 49 | 0.295 | 0.298 | +0.003 (essentially unchanged) |
| 50 | 0.341 | 0.299 | **−0.042** (lost s50's strong-tail) |
| 51 | 0.365 | — | (warmstart source) |
| 52 | — | 0.321 | (new fresh seed) |

s49 nearly unchanged. s50 lost 4 % — warmstart shifted s50's
trajectory off its fresh-init basin. s52 (fresh comparison) at
0.321 is a respectable new data point.

### The axis trade-off

This is the FIRST probe in R49-R54 to produce a clean structural
trade-off rather than a uniform failure:

| axis direction | R48-β baseline | R54 warmsh | Δ |
|---|---:|---:|---:|
| max_df (want HIGH) | 0.97 | 0.79 | **−0.18** |
| settling (want HIGH) | ~0.70 | 0.88 | **+0.18** |
| dH_util (want HIGH) | 0.040 | 0.048 | +0.008 |
| dD_util (want HIGH) | 0.100 | 0.117 | +0.017 |
| dH_smooth (want HIGH) | ~0.75 | similar | ~0 |
| dD_smooth (want HIGH) | ~0.70 | similar | ~0 |

Settling axis went UP and max_df axis went DOWN by similar
magnitudes (0.18 each). Cross-agent coordination (corr_dD) doubled
from 0.15 to 0.32. The mechanism:

- **Shared init → similar early-training trajectories** for all 4
  agents (same starting weights + similar local obs structure)
- **Uniform behaviour helps consistency-driven axes** (settling,
  coordination): all agents settle similarly because they react
  similarly
- **Uniform behaviour hurts peak-tracking axes** (max_df): each
  agent's frequency PEAK varies per bus; identical agents can't
  track the local maximum individually

This is a V4-internal **structural trade-off** between:
- "consistent across agents" (drives settling + coordination up)
- "individually optimal per agent" (drives max_df up)

The 6-axis geo-mean penalises whichever side gets shorter — going
all-in on either fails to dominate.

## The FIVE-failure pentacle

| Round | Lever attacked | mean 6-axis | Δ vs 0.334 | Distinct mechanism |
|---|---|---:|---:|---|
| R49-α | obs aug (last action) | 0.263 | −21 % | self-reinforcing static loop |
| R50-α | reward (anti-smoothness) | 0.110 | −67 % | exploration-noise hijack |
| R51-α | algorithm (SAC h=64) | 0.107 | −68 % | deterministic-eval-setpoint invariant |
| R52-α | obs aug (time-in-obs) | 0.270 | −19 % | phase info unused by policy |
| **R54-α** | **init (warmstart-shared)** | **0.306** | **−8 %** | **uniformity vs peak-tracking trade-off** |

All five share the same outer wall: V4 reward landscape + memoryless
policy class converge to deterministic-eval-setpoint policies that
hit the production triangle (0.334 / 0.365 / 0.351) but no higher.

## Project-wide 6-axis scoreboard (post-R54)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed | 0.094 | reference |
| no_control G4-preserved | 0.101 | Q-0001 closed |
| R51-α SAC norm h=64 | 0.107 | CLM-0059 |
| R50-α LAMBDA=-100 | 0.110 | CLM-0058 |
| R43-α SAC norm h=128 | 0.117 | |
| R49-α R03 obs probe | 0.263 | CLM-0057 |
| R47-β TD3 norm 200ep | 0.269 | plateau |
| R52-α TD3 h=64 INCLUDE_TIME_OBS | 0.270 | CLM-0060 |
| R41-B TD3 norm h=128 (superseded) | 0.275 | |
| **R54-α TD3 h=64 warmstart-shared** | **0.306** | **CLM-0061 (this round)** |
| R43-β HAWE h=128 uniform | 0.310 | |
| R47-α HAWE top-3 uniform | 0.315 | |
| **R48-β TD3 norm 75ep h=64** | **0.334** | **production single-seed** |
| **R48-δ HAWE h=64 median** | **0.351** | **production ensemble** |
| R41-C s52 lucky-tail | 0.353 | |
| **R48-β s51 single** | **0.365** | **strongest non-lucky** |
| R21 lucky basin SAC | 0.444 | entropy-noise lottery |
| HAWE w9802 | 0.439 | |
| paper target | ~1.00 | unreached |

## What R54 establishes

- **CLM-0061**: warmstart-shared from strongest actor across 3
  seeds yields 0.306 mean (-8 %); settles and coordinates better
  but loses on max_df.
- **V4 structural trade-off**: uniformity (helps settling +
  coordination) vs individual peak-tracking (helps max_df) are
  in tension. Going all-in on either is net-negative.
- **Five-failure pentacle**: the ceiling at 0.334 / 0.365 / 0.351
  is now bounded by five independent attacks (obs / reward /
  algorithm / phase / init).

## What R54 does not establish

- Whether true parameter sharing (all 4 agents call ONE actor at
  every step) would resolve the trade-off — requires SharedTD3Agent
  wrapper (~1-2 hr impl).
- Whether windowed-horizon reward (~30 min impl) avoids the noise
  hijack and unlocks utilization.
- Whether LSTM actor (~1 day) breaks the deterministic-eval-setpoint
  attractor structurally.
- Whether curriculum disturbance (~2-3 hr) shifts the policy basin
  by changing env difficulty.

## What this implies for direction

After five negative attacks attacking five distinct mechanisms,
the rational pivots are:

1. **Accept the ceiling** and harden the production package:
   - Document 0.334 / 0.365 / 0.351 as the reproducible bound
   - Write ablation tables (R49-R54 negatives ARE the ablations)
   - Move to paper writing using the existing material
2. **Commit to expensive structural change**:
   - LSTM recurrent actor (~1 day)
   - SharedTD3Agent wrapper for true parameter sharing (~1-2 hr)
   - Curriculum env (~2-3 hr) — only one not yet probed in spirit
3. **Try the cheapest untested lever**:
   - Windowed-horizon smoothness reward (~30 min impl)
   - Theoretically hijack-resistant; if it also fails, the
     structural finding is six-bounded.

## New claims this round

- `CLM-0061` — R54-α warmstart-shared 0.306 mean (-8%);
  uniformity/peak-tracking axis trade-off documented.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)
