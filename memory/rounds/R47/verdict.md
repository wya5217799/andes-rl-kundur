# R47 verdict — HAWE cap robust + TD3 norm 200ep plateau

**Date**: 2026-05-17
**Status**: **COMPLETE**. Both parts executed and scored.
**Type**: analysis (α) + experiment (β)
**Wall**: ~35 min (α: 2 ensemble evals + score; β: 3 × 200ep TD3
norm training in parallel ~28 min + per-seed eval/score)

---

## TL;DR

> **R47-α**: HAWE caps at single best actor — CLM-0050 confirmed
> robust to aggregation variant. Top-3-individuals uniform = 0.315;
> median = 0.342. Neither beats the R44-α s52-anchored 90 %
> asymptote (0.347) or s52 alone (0.353). Median ≫ uniform
> (+0.028) because median preserves the strongest-actor signal
> when 2/3 agree; uniform always averages. **No aggregation
> strategy unlocks a complementarity bonus past max(individual)
> for the current actor pool.**
>
> **R47-β**: TD3 normalized 200-ep mean = **0.269** (range
> [0.215, 0.297]) ≈ R41-B 75-ep mean 0.275 (range [0.267, 0.280]).
> Per-seed: s49 +0.018, s50 +0.030, **s51 −0.065 (collapse)**.
> Net mean slightly worse, variance widens 6×. CLM-0046's "TD3
> training plateaus at 75 ep" hypothesis now generalised to the
> normalized-reward regime — **75 ep is the optimal stop point
> for TD3 norm**; extending to 200 ep is net-zero on mean and
> introduces the late-training-collapse failure mode (1 of 3
> seeds, 23 % drop).

---

## Round-number note

Started under the informal label "R46-α / R46-β" before noticing
Codex's parallel session had already taken **R45** (Q-0001
escalation, made moot by my R44 close-negative) and **R46**
(architectural deepening Phase A, Q-0004 opened for Phase B
deferral). To avoid trampling either round, my research is filed
under **R47**. The result JSONs retain `r46_*` filenames where
they were named before the conflict was discovered (no functional
impact — these are reproducible by re-running the score scripts).

---

## Part α — Top-3 HAWE + median (CLM-0050 stress-test)

Three TD3 actors held individual 6-axis scores:
- `td3_phi0_200ep_s52`: **0.353** (R41-C lucky tail)
- `td3_phi0_200ep_s50`: 0.289 (R41-C mid)
- `td3_norm_s51`: 0.280 (R41-B best of norm)

Two ensemble configurations via `scripts/eval_ensemble.py`,
scored by `paper_grade_axes.evaluate_trace` geo-mean across
LS1+LS2.

| Variant | aggregation | weights | LS1 | LS2 | **geo** |
|---|---|---|---:|---:|---:|
| R43-β baseline (3 norm uniform) | weighted | 1/3 each | 0.260 | 0.371 | 0.310 |
| R44-α s52-anchored 90 % | weighted | 0.9 / 0.05 / 0.05 | 0.300 | 0.403 | **0.347** |
| **R47-α top-3 uniform** | weighted | 0.33 / 0.34 / 0.33 | 0.252 | 0.393 | 0.315 |
| **R47-α top-3 median** | median | (n/a) | 0.300 | 0.391 | **0.342** |
| s52 alone (R41-C single seed) | n/a | n/a | 0.305 | 0.408 | 0.353 |

### Pre-flight fix

Codex's R42 post-review hotfix (commit `74704fe`) changed
`agents/checkpoint_loader.load_agents` to keyword-only `suffix=`,
but `scripts/eval_ensemble.py` (Codex's own refactor commit
`42948db` had centralised the call) still passed `suf` positionally
on line 95. The 1-character fix:

```python
# Before (broken since 74704fe)
all_actors = [load_agents(Path(cd), suf) for cd, suf in zip(...)]
# After
all_actors = [load_agents(Path(cd), suffix=suf) for cd, suf in zip(...)]
```

Landed as part of R47 commit. `eval_ddic.py` and `eval_all_seeds.py`
both already use `suffix=`; eval_ensemble.py was the only laggard.

### Observations

1. **Top-3 uniform = 0.315** (basically R43-β + 0.005). Uniform
   averaging strong + medium + medium-strong pulls the result back
   toward the per-actor mean (0.353 + 0.289 + 0.280) / 3 = 0.307.
2. **Top-3 median = 0.342** (within 0.005 of R44-α 90 % anchor at
   0.347). Median is "auto-anchored" toward consensus; when s52's
   policy differs from both norm actors, median picks the norm
   side and gives up s52's lift, but when 2/3 agree median follows.
3. **Neither beats s52 alone (0.353).** The HAWE ceiling for this
   actor pool is firmly capped at max(individuals).

### Implication

CLM-0050 stands. The "no complementarity bonus" finding is robust
across:
- Uniform aggregation (R43-β, R44-α uniform variants, R47-α
  top-3 uniform): 0.307 – 0.315
- Anchored weighted (R44-α 50/75/90 %): 0.337 – 0.347
- Median (R47-α): 0.342

Practical: the only way past 0.347 is to **train a stronger single
actor**. HAWE is performance-preserving, not performance-amplifying.

---

## Part β — TD3 normalized 200-ep gap-fill (CLM-0046 generalisation)

R41-C established that TD3 phi=0 200ep mean (0.268) ≈ 75ep mean
(0.259) — training-length plateau on the PHI=0 reward shape
(CLM-0046). R41-B established TD3 normalized 75ep mean = 0.275
(production setting, CLM-0047). The 200ep × normalized cell was
empty.

3 seeds × 200 episodes, `--algo td3 --normalize-actions
--episodes 200`. Same seeds as R41-B (49, 50, 51) for direct
per-seed comparison.

| seed | R41-B 75ep LS1 | R41-B 75ep LS2 | R41-B geo | R47-β 200ep LS1 | R47-β 200ep LS2 | R47-β geo | Δ |
|------|---:|---:|---:|---:|---:|---:|---:|
| 49 | 0.254 | 0.305 | **0.278** | 0.276 | 0.318 | **0.296** | **+0.018** |
| 50 | 0.223 | 0.320 | **0.267** | 0.250 | 0.351 | **0.297** | **+0.030** |
| 51 | 0.285 | 0.275 | **0.280** | 0.173 | 0.266 | **0.215** | **−0.065** |
| **mean** | — | — | **0.275** | — | — | **0.269** | **−0.006** |
| **std** | — | — | **0.007** | — | — | **0.039** | **6×** |

### Observations

1. **Mean unchanged**, fractionally lower (0.269 vs 0.275).
2. **Variance widens 6× on the std** (0.007 → 0.039). Range
   stretches from [0.267, 0.280] to [0.215, 0.297].
3. **s49 + s50 gain modestly** (+0.018, +0.030) — longer training
   refines their already-decent policies.
4. **s51 collapses 23 %** (0.280 → 0.215). Late-training policy
   drift on V4's narrow-target frequency control — exactly the
   "training plateau is the right place to stop" failure mode.
5. **No new lucky tail**: best 200ep seed (s50 = 0.297) is below
   the R41-C s52 phi=0 200ep lucky-tail max (0.353).

### Implication

CLM-0046's plateau hypothesis was framed as a phi=0 finding. R47-β
generalises it: **TD3 on V4 plateaus at 75 ep regardless of
reward-cost shape**. The 200ep cell adds nothing on the mean and
risks the s51-style collapse. Operational recommendation:
**continue using 75 ep as the production training length**; do
not extend.

This also closes off a candidate path for the "0.35 → 1.0 per-axis
gap": longer training alone won't get there. The remaining open
paths are:
- New algorithm (PPO, curriculum learning)
- New observation augmentation (R03 INCLUDE_OWN_ACTION_OBS)
- New reward augmentation (multi-step horizon, frequency
  derivative term, etc.)
- More aggressive hyper-parameter search (hidden_size, batch_size,
  learning rates) at 75 ep

---

## Comparison: project-wide 6-axis scoreboard (post-R47)

| Configuration | 6-axis | Note |
|---|---:|---|
| no_control G4-zeroed (current ranker) | 0.094 | reference; CLM-0008 cited 0.104 |
| no_control G4-preserved | 0.101 | Q-0001 closed-negative (R44) |
| R43-α SAC normalized | 0.117 | H3 triple-confirmed |
| R41-A SAC phi=0 | 0.117 | |
| SAC multi-seed attractor (R23-R27) | 0.137 | |
| R40 TD3 phi=0 (75 ep) | 0.259 | |
| R41-C TD3 phi=0 (200 ep, 5 seeds) | 0.268 | plateau |
| **R47-β TD3 normalized (200 ep, 3 seeds)** | **0.269** | **new — plateau generalised** |
| **R41-B / CLM-0047 TD3 normalized 75 ep 3-seed mean** | **0.275** | production single-seed setting |
| **R43-β HAWE TD3 norm 3-seed uniform** | **0.310** | reproducible ensemble |
| R47-α HAWE top-3 uniform | 0.315 | |
| R47-α HAWE top-3 median | 0.342 | |
| R44-α HAWE s52 anchored 50 / 75 / 90 % | 0.337 / 0.338 / **0.347** | hybrid asymptote |
| R41-C s52 single seed (200 ep) | 0.353 | lucky-tail best non-lucky single |
| R21 lucky basin (SAC single seed) | 0.444 | entropy-noise lottery |
| HAWE w9802 (ensemble of lucky SAC) | 0.439 | inference-time recovery |
| paper target | ~1.00 per axis | unreached |

---

## What R47 establishes

- **CLM-0050 confirmed robust** to aggregation variant choice
  (uniform / weighted-anchored / median): HAWE caps at single best
  actor regardless of mixing strategy. (CLM-0052)
- **CLM-0046 generalised** from phi=0 to normalized: TD3 on V4
  plateaus at 75 ep training, independent of reward-cost shape.
  Extending to 200 ep is net-zero or slightly negative on mean,
  and risks a 20 %+ single-seed collapse. (CLM-0053)
- **Practical settling of the production setting**: TD3 norm 75 ep
  remains the recommended training cell. HAWE-3 norm uniform
  (0.310) remains the recommended ensemble. Anchored ensembling
  toward a lucky-tail single seed (R44-α 0.347) is the upper
  hybrid; pure single-best (R41-C s52 0.353) is the upper
  non-lucky-ensemble bound.

## What R47 does not establish

- Whether **new algorithms** (PPO, curriculum) close the 0.35 →
  1.0 gap. Untouched.
- Whether **hyper-parameter search** at 75 ep finds a different
  basin. Untouched.
- Whether **observation augmentation** (e.g. action history,
  derivative terms) unlocks per-axis improvement. Untouched.
- Whether the **s51 200ep collapse** repeats with other seeds or
  is idiosyncratic. Only one seed showed the failure mode; a
  longer sweep would be needed to characterise the prevalence.

## New claims this round

- `CLM-0052` — R47-α: HAWE single-best-actor cap holds across
  aggregation variants (top-3 uniform 0.315, median 0.342, both
  below R44-α anchor 0.347 and s52 alone 0.353).
- `CLM-0053` — R47-β: TD3 normalized 200-ep mean 0.269 ≈ 75-ep
  mean 0.275; variance widens 6×; one seed collapses 23 %.
  Generalises CLM-0046's plateau to normalized rewards; 75 ep is
  the empirically optimal stop point.

## Questions opened (this round)
- (none — both inquiries were extensions of existing claims, not
  new open uncertainties)

## Questions closed (this round)
- (none — Q-0004 belongs to Codex's R46 and remains open for the
  next WSL session)

## Questions advanced (this round, status unchanged)
- (none)
