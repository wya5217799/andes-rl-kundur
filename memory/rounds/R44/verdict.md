# R44 verdict — HAWE weight-cap + Q-0001 closed-negative

**Date**: 2026-05-17
**Status**: **COMPLETE**. Both parts executed and scored.
**Type**: analysis (α) + experiment (β)
**Wall**: ~12 min (α: 5 ensemble evals × ~30 s + scoring; β: one
no-control eval + scoring)

---

## TL;DR

> **R44-α**: HAWE weight-sweep on the V4 env caps at the strongest
> single actor. Across 5 ensemble schemes, best result = **0.347**
> at (0.9, 0.05, 0.05) on (s52, norm_s51, norm_s49) — monotonic
> approach to s52 single seed (0.353) without exceeding it. The
> R43-β +11 % uplift was a tight-distribution artefact; once one
> actor (s52 = 0.353) is materially stronger than peers (others
> ~0.27), the ensemble pulls back toward the mean and only heavy
> weighting on s52 recovers it.
>
> **R44-β**: Q-0001 closed-negative. G4-preserved no_control
> 6-axis = **0.101** vs G4-zeroed = 0.094 under the same post-R30
> ranker. Delta +8 %, inside Q-0001's own pass-criterion band
> [0.09, 0.12]. No headline ranking flips (R21 / HAWE w9802 lead
> no_control by 4×+; an 8 % baseline sensitivity cannot move any
> pairwise ranking). G4 setting is **not load-bearing** for the
> paper's leaderboard.

---

## Part α — HAWE weight sweep

5 ensemble configurations via `scripts/eval_ensemble.py`, scored
by `paper_grade_axes.evaluate_trace` geo-mean across LS1+LS2.

| Variant | weights | LS1 | LS2 | **geo** | dH_util | dD_util |
|---|---|---:|---:|---:|---:|---:|
| HAWE-3 norm uniform (R43-β baseline) | 1/3 each | 0.260 | 0.371 | **0.310** | 0.039 | 0.070 |
| HAWE-5 phi0_200ep uniform | 0.2 each | 0.245 | 0.389 | 0.309 | 0.036 | 0.115 |
| HAWE-8 union uniform | 0.125 each | 0.248 | 0.380 | 0.307 | 0.036 | 0.094 |
| HAWE-3 s52-anchored 50% | 0.5 / 0.25 / 0.25 | 0.286 | 0.397 | 0.337 | 0.042 | 0.104 |
| HAWE-3 s52-anchored 75% | 0.75 / 0.125 / 0.125 | 0.293 | 0.391 | 0.338 | 0.043 | 0.116 |
| **HAWE-3 s52-anchored 90%** | **0.9 / 0.05 / 0.05** | 0.300 | 0.403 | **0.347** | 0.061 | 0.122 |
| s52 alone (R41-C single seed, reference) | 1.0 | 0.305 | 0.408 | 0.353 | 0.075 | 0.128 |

Two patterns:

1. **Uniform schemes don't help past R43-β.** Adding mediocre
   phi0_200ep seeds (s49 0.247, s51 0.187) into a uniform-5 or
   uniform-8 ensemble averages the result back to ~0.31. R43-β's
   uniform-3 over the *narrow-distribution* TD3 norm actors
   happened to land near the per-actor mean already.

2. **Anchored schemes monotonically approach the strongest actor.**
   With s52 (0.353) held at 50 / 75 / 90 % weight and the two
   diverse anchors at 25/25, 12.5/12.5, 5/5, the geo-mean rises
   0.337 → 0.338 → 0.347, asymptoting at s52 alone (0.353). No
   crossover, no super-strongest behaviour.

### Implication

HAWE-style averaging is **performance-preserving, not performance-
amplifying** for this problem. It does not extract additional
6-axis lift from "complementary errors" the way model-averaging
does in image classification. R34's HAWE w9802 = 0.439 reached
its score because R21 alone was 0.444 — the ensemble preserved a
lucky single-seed.

Practical upshot: for production deployment, **pick the strongest
single actor** (currently s52 phi0_200ep, single-seed 0.353).
Multi-seed ensembling adds noise robustness but trades the upper
tail of the multi-seed distribution. The R43-β 0.310 ensemble
remains the best multi-seed **reproducibly-trained** configuration
(every seed is in a tight band), while the 0.347 anchored ensemble
is a hybrid: lucky-seed-anchored, mostly-reliable. Both are valid
endpoints for different operational profiles.

---

## Part β — Q-0001 G4 inertia paper-faithful rerun

Inline no-control eval via
`scripts/_r44_eval_no_control_g4preserved.py`, which explicitly
constructs `V4Config(zero_g4_inertia=False)` and injects it into
`AndesMultiVSGEnvV4(config=...)`. `paper_path.run_scenario` does
not currently accept a config override (default is
`V4Config.paper_faithful()` baked in), so a one-off script was
written rather than refactoring the shared helper.

### Results

| Configuration | LS1 max_df | LS2 max_df | LS1 overall | LS2 overall | **geo** |
|---|---:|---:|---:|---:|---:|
| no_control G4-zeroed (current default, CLM-0040 pin) | 0.189 | 0.168 | 0.1141 | 0.0770 | **0.0938** |
| no_control G4-preserved (paper-claimed setting) | 0.182 | 0.169 | 0.1172 | 0.0874 | **0.1012** |
| **delta (preserved − zeroed)** | −0.007 | +0.001 | +0.003 | +0.010 | **+0.0074 (+8 %)** |

### Q-0001 closure

Q-0001's own Candidates section laid out:

> "no_control rerun (cheapest, ~5 min): rerun the no-control
> baseline with `ZERO_G4_INERTIA=False`; compare max_df / cum_rf /
> 6-axis vs 0.104. If 6-axis stays in [0.09, 0.12], headline
> ranking is robust to G4 — answer is closed-negative on changing
> the headline."

G4-preserved no_control 6-axis = **0.1012** — inside [0.09, 0.12].
Pass criterion met. **Q-0001 closes-negative**: headline ranking
is robust to G4 preservation.

Pairwise check (sanity-grade, not requiring single-seed rerun):

- R21 lucky single seed = 0.444 (4.4× G4-zeroed no_control, 4.4×
  G4-preserved no_control). Survives 8 % baseline shift trivially.
- HAWE w9802 = 0.439 (4.7× G4-zeroed, 4.3× G4-preserved). Same.
- SAC multi-seed attractor = 0.137 (1.5× G4-zeroed, 1.4× G4-
  preserved). Same.
- TD3 norm 3-seed mean = 0.275 (2.9× G4-zeroed, 2.7× G4-
  preserved). Same.

An 8 % shift on the baseline does not threaten any of these
ratios. The follow-up candidates (R21-single-seed rerun, 22-ckpt
H₀ sweep, full headline regeneration) — all listed in Q-0001 —
are NOT necessary.

### Side observation (out-of-scope for this claim)

Under the current post-R30/R36 ranker, no_control G4-zeroed scores
0.094, but CLM-0008 (R30 headline) cites 0.104. That's a -0.010
absolute drift in the ranker output between R30 and now,
unrelated to G4. The relative ranking among headlines stays
intact, so CLM-0008's 0.104 still serves its role as the
historical anchor for the leaderboard. A correction-type claim
against CLM-0008 is **not** filed here — it would be a separate
"ranker drift" finding for a future round.

---

## Comparison: project-wide 6-axis scoreboard (post-R44)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed (R44-β current ranker) | 0.094 | reference; CLM-0008 R30 cited 0.104 |
| no_control G4-preserved (R44-β) | 0.101 | Q-0001 closed-negative |
| R43-α SAC normalized | 0.117 | H3 triple-confirmed |
| R41-A SAC phi=0 | 0.117 | H3 confirmed |
| SAC multi-seed attractor (R23-R27) | 0.137 | original observation |
| R40 TD3 phi=0 (75 ep) | 0.259 | broke trap (extreme) |
| R41-C TD3 phi=0 (200 ep, 5 seeds mean) | 0.268 | ceiling confirmed |
| **R41-B / CLM-0047 TD3 normalized 3-seed mean** | **0.275** | production single-seed setting |
| **R43-β HAWE TD3 norm 3-seed uniform** | **0.310** | reproducible ensemble |
| R44-α HAWE s52-anchored 50% | 0.337 | hybrid lucky+stable |
| R44-α HAWE s52-anchored 75% | 0.338 | |
| **R44-α HAWE s52-anchored 90%** | **0.347** | hybrid asymptote |
| R41-C s52 single seed (200 ep) | 0.353 | lucky-tail best non-lucky single |
| R21 lucky basin (SAC single seed) | 0.444 | entropy-noise lottery |
| HAWE w9802 (ensemble of lucky SAC) | 0.439 | inference-time recovery |
| paper target | ~1.00 per axis | unreached |

---

## What R44 establishes

- **HAWE caps at single best actor** (CLM-0050). Adding seeds
  beyond the best one only helps when those seeds are
  performance-comparable; once one is materially stronger, the
  ensemble strictly degrades toward the mean. No magic
  complementarity bonus.
- **Q-0001 closed-negative** (CLM-0051). The G4 inertia setting
  produces an ~8 % shift on the no-control baseline — well within
  Q-0001's pass band. No headline ranking flips. The pin to
  `ZERO_G4_INERTIA=True` (CLM-0040) can remain in place
  indefinitely for bit-identical paper reproducibility without
  jeopardising any conclusion that the leaderboard depends on.

## What R44 does not establish

- **Whether the 0.35 → 1.0 per-axis gap is closable**. Unchanged
  by R44. Open paths: curriculum learning, PPO via on-policy base,
  observation augmentation (R03 INCLUDE_OWN_ACTION_OBS), env-side
  rebalance.
- **Whether non-anchor weight optimisation can beat 0.347**.
  Only uniform / s52-anchored schemes tested. A proper weight
  optimisation (e.g. coordinate ascent on per-seed weights with
  LS1+LS2 holdout) is open.
- **Whether the post-R30 ranker drift on no_control (0.094 vs
  0.104) extends to other headlines**. Not measured. CLM-0008
  remains the R30-era anchor.

## New claims this round

- `CLM-0050` — R44-α: HAWE weight-sweep caps at single best actor;
  best ensemble 6-axis 0.347 (s52 90 %) ≈ s52 alone 0.353.
- `CLM-0051` — R44-β: G4-preserved no_control 6-axis 0.101 vs
  G4-zeroed 0.094 (+8 %); no headline ranking flips; Q-0001
  closes-negative.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- `Q-0001` (closed-negative by CLM-0051) — Headline ranking is
  robust to G4 inertia preservation (8 % shift inside the
  question's pass band).

## Questions advanced (this round, status unchanged)
- (none)
