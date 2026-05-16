# R48 verdict — Hidden-size sweep: new production setting h=64

**Date**: 2026-05-17
**Status**: **COMPLETE**. Four-point hidden-size curve characterised
+ HAWE re-run on the new sweet spot.
**Type**: experiment (hyperparameter sweep)
**Wall**: ~50 min (3 sweeps × 10 min training + scoring + HAWE)

---

## TL;DR

> **Hidden-size has a clean inverted-V curve with peak at 64**
> for TD3 normalized 75ep on V4. Mean 6-axis (seeds 49/50/51):
> h32 = 0.255, **h64 = 0.334**, h128 = 0.275 (R41-B baseline),
> h256 = 0.250. Hidden=64 delivers **+21 %** over the default
> at zero extra training cost.
>
> Best single seed: **s51 h64 = 0.365** — exceeds R41-C's
> prior single-seed maximum (s52 phi=0 200ep = 0.353).
>
> Best multi-seed reproducible ensemble:
> **HAWE-3 h64 median = 0.351** — beats R44-α 0.347
> (which had depended on the lucky-tail s52 anchor) and
> R43-β 0.310 (h128 uniform).
>
> **CLM-0047's production setting is superseded** by CLM-0055:
> use TD3 norm 75ep `--hidden-size 64` going forward.

---

## The hidden-size U-curve

| hidden | layer-0 weight shape | mean | range | std |
|---:|:---|---:|---:|---:|
| 32 | (32, 7) | 0.2546 | [0.231, 0.277] | 0.020 |
| **64** | (64, 7) | **0.3346** | [0.295, 0.365] | 0.030 |
| 128 (R41-B baseline) | (128, 7) | 0.275 | [0.267, 0.280] | 0.007 |
| 256 | (256, 7) | 0.250 | [0.211, 0.278] | 0.030 |

Three observations:

1. **Inverted-V with single peak at h=64**. Both smaller (32) and
   larger (128, 256) capacities underperform.
2. **The "default is over-parameterised" story is clean**. V4
   obs_dim is 7. h=128 layer-0 has 128×7 + 128 = 1024 weights; the
   network has 5+ such layers (4 hidden × 2 nets × 2 critics for
   TD3). With only 75 episodes × 50 steps × 4 agents = 15000
   on-policy samples per agent, the gradient signal is sparse
   relative to the parameter count.
3. **Variance asymmetry**. h128 has the *tightest* std (0.007) —
   it's the most "stable" but at a lower mean. h64 trades
   tightness (std 0.030) for headroom; all three seeds end above
   0.27, with one reaching 0.365.

Per-seed (h128 → h64):

| seed | h128 | h64 | Δ |
|---|---:|---:|---:|
| 49 | 0.278 | 0.295 | +0.017 |
| 50 | 0.267 | 0.341 | **+0.074** |
| 51 | 0.280 | 0.365 | **+0.085** |

All seeds improve, two materially. No seed collapses (unlike R47-β
200ep where s51 dropped −0.065). h64 is also faster to train
(~610s vs ~640s for h128 on the same hardware).

## R48-δ: HAWE on the new actors

With three stronger actors (0.295 / 0.341 / 0.365), HAWE was
re-evaluated with the same three aggregation schemes used in R47-α
+ R44-α:

| aggregation | weights | LS1 | LS2 | **geo** |
|---|---|---:|---:|---:|
| uniform | 0.33 / 0.34 / 0.33 | 0.289 | 0.376 | 0.330 |
| **median** | (consensus) | 0.337 | 0.365 | **0.351** |
| s51-anchored | 0.25 / 0.25 / 0.5 | 0.288 | 0.383 | 0.332 |

Median = **0.351** beats every prior ensemble result:
- R43-β h128 uniform: 0.310
- R47-α h128/h128/phi0 median: 0.342
- R44-α s52 90 % anchored: 0.347

Three things to note:

1. **HAWE still caps below max(individual)** (single best s51 =
   0.365 > median ensemble 0.351). CLM-0050/0052/0056 chain is now
   quintuple-confirmed.
2. **Median dominates uniform** when all three actors are strong:
   uniform pulls toward the per-actor mean (0.334 here), but
   median picks the *consensus* — which lands closer to the strong
   end because 2/3 of the actors agree most of the time near the
   high-Q action region.
3. **0.351 is now the recommended multi-seed reproducible setting**.
   The 0.347 R44-α result depended on the lucky-tail single seed
   (s52 phi=0 200ep at 0.353); the 0.351 R48-δ is from a uniformly
   well-trained pool, no lucky tail required.

## Pre-flight: load_agents kwarg

`scripts/eval_ddic.py` calls `checkpoint_loader.load_agents` with
no `hidden_sizes=` override, so it loads with the
`config.HIDDEN_SIZES` default `[128, 128, 128, 128]`. h32/64/256
ckpts fail with `RuntimeError: Error(s) in loading state_dict ...
size mismatch for net.0.weight: copying a param with shape
torch.Size([N, 7]) from checkpoint, the shape in current model is
torch.Size([128, 7])`.

Workaround used: inline Python calling
`load_agents(ckpt, suffix='best', hidden_sizes=(N,)*4)` directly,
then `paper_path.run_scenario(...)` and
`paper_grade_axes.evaluate_trace(...)`. JSON files saved with the
same `td3_norm_h{N}_s{seed}_load_step_{1,2}.json` naming so future
re-scoring is straightforward.

**Out-of-scope follow-up** (R49+): patch `eval_ddic.py` and
`eval_ensemble.py` to take a `--hidden-size` CLI flag and forward
it to `load_agents`. This is an infra commit, not research; defer.

---

## Project-wide 6-axis scoreboard (post-R48)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed (current ranker) | 0.094 | reference |
| no_control G4-preserved | 0.101 | Q-0001 closed-negative (R44) |
| R43-α SAC normalized | 0.117 | H3 triple-confirmed |
| R41-A SAC phi=0 | 0.117 | |
| SAC multi-seed attractor (R23-R27) | 0.137 | |
| R40 TD3 phi=0 (75 ep, h128) | 0.259 | |
| R47-β TD3 norm 200 ep (h128) | 0.269 | plateau, +variance |
| R41-C TD3 phi=0 200 ep (5 seeds, h128) | 0.268 | |
| **R41-B / superseded — TD3 norm 75 ep h128** | 0.275 | old production |
| R43-β HAWE h128 uniform | 0.310 | old reproducible ensemble |
| R47-α HAWE h128/h128/phi0 median | 0.342 | |
| R44-α HAWE s52-anchored 90 % | 0.347 | hybrid with lucky tail |
| **R48-δ HAWE h64 median (3-seed)** | **0.351** | **new reproducible ensemble** |
| R41-C s52 single seed (h128, 200ep, phi=0) | 0.353 | prior lucky single-seed max |
| **R48-β TD3 norm 75 ep h64 3-seed mean** | **0.334** | **new production single-seed** |
| **R48-β TD3 norm 75 ep h64 s51 single** | **0.365** | **new strongest non-lucky single actor** |
| R21 lucky basin (SAC single seed, h128) | 0.444 | entropy-noise lottery |
| HAWE w9802 (R34, lucky SAC ensemble) | 0.439 | inference-time recovery |
| paper target | ~1.00 per axis | unreached |

---

## What R48 establishes

- **CLM-0054**: U-curve for hidden-size at 32/64/128/256 on TD3
  norm 75ep; clean peak at 64.
- **CLM-0055**: New production single-seed setting = TD3 norm
  75ep `--hidden-size 64`. Supersedes CLM-0047 (h128 default).
- **CLM-0056**: HAWE-3 h64 median = 0.351, new reproducible
  ensemble; HAWE single-best cap quintuple-confirmed.
- **The 0.35 → 1.0 per-axis gap shrinks but doesn't close**:
  R48 narrows the gap from R41-B's 0.275 to 0.334 (single-seed
  mean) / 0.351 (ensemble) / 0.365 (best single). Still 2.7×
  below the paper per-axis target.

## What R48 does not establish

- Whether even-finer hidden-size grid (e.g. 48, 80, 96) finds
  something better than 64. The 32→64→128 monotonic shape
  suggests 64 is a real local optimum, but 48 or 80 might be
  fractionally better.
- Whether **batch-size** sweep at h=64 yields additional gain.
  Untouched. Likely R49 candidate.
- Whether **learning rate** sweep helps. CLI doesn't currently
  expose LR; would need a `config.py` edit + train.py threading.
- Whether **more seeds** (52-58 at h=64) finds another lucky
  s51-style single seed > 0.40.
- Whether a different **algorithm** (PPO, A2C) at h=64
  outperforms TD3.

## New claims this round

- `CLM-0054` — Hidden-size U-curve finding (h32/64/128/256 data
  points, 3-seed mean).
- `CLM-0055` — Decision: production single-seed setting now TD3
  norm 75ep h64. **Supersedes `CLM-0047`** — `validate.py --fix`
  auto-flips CLM-0047 to status=superseded with `superseded_by:
  CLM-0055`.
- `CLM-0056` — HAWE on h64 actors yields 0.351 median, new
  reproducible ensemble high; HAWE single-best cap still holds.

## Questions opened (this round)
- (none — R48 narrows production-setting space rather than
  opening new uncertainty)

## Questions closed (this round)
- (none — Q-0004 belongs to Codex's R46 and remains open for the
  next WSL session)

## Questions advanced (this round, status unchanged)
- (none)
