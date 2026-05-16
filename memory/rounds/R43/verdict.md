# R43 verdict — Two-part follow-up to R41 (SAC norm + HAWE TD3 norm)

**Date**: 2026-05-17
**Status**: **COMPLETE**. Both parts executed and scored.
**Type**: experiment (α) + analysis (β)
**Wall**: ~25 min (β eval 30 s, α 3-seed training ~11 min wall via
3-parallel WSL, scoring + writeup the remainder)

---

## TL;DR

> **R43-α**: SAC + normalized penalty plateaus at multi-seed mean
> 6-axis = **0.117** (range [0.106, 0.136]), essentially identical
> to R41-A SAC phi=0 (0.117) and the R23-R27 SAC attractor (0.137).
> **2.35× worse than TD3 normalized** on the same reward shape.
> H3 is now **triple-confirmed**: SAC's entropy regularization
> defeats the reward-shape fix; algorithm choice is the load-bearing
> factor once reward asymmetry is removed. CLM-0047 production
> recommendation (TD3 + normalized) stands unchanged.
>
> **R43-β**: HAWE-style weighted ensemble (0.33/0.34/0.33) of the
> three R41-B TD3 normalized actors reaches 6-axis geo-mean =
> **0.310**, the **first non-lucky configuration past 0.30** in
> this project. +11 % over the best single seed (s51 = 0.280) and
> +13 % over the 3-seed mean (0.275). Cheap (~30 s eval) extension
> to the production setting; consider "TD3 norm 3-seed ensemble" as
> the recommended *inference-time* configuration on top of CLM-0047.

---

## Naming note

The handoff (`memory/handoffs/2026-05-17_post-R41.md`) labeled
these experiments **R42-α / R42-β**. By the time they ran, a
concurrent Codex session had already claimed R42 for an
infrastructure deepening pass (`paper_path`, `checkpoint_loader`,
`training_checks`, validate dedup; 2 of 5 commits landed at
46a9281 / 42948db). To avoid trampling that round's plan/verdict,
this work is filed under **R43** while keeping the **α/β**
sub-labels from the handoff. The result JSONs and score scripts
retain the `r42_` prefix in their filenames (`r42_alpha_*.json`,
`r42_beta_*.json`, `_r42_score_alpha_sac_norm.py`) because those
were named before the R42 conflict was discovered; renaming them
would have broken downstream provenance.

---

## Part α — SAC + normalized penalty (3 seeds × 75 ep)

Drop-in algorithm change from R41-B: `--algo sac --normalize-actions`
with default paper PHI weights. Same training infra, same eval
pipeline, same scoring (`paper_grade_axes` + geo-mean across
LS1+LS2). Score script: `scripts/_r42_score_alpha_sac_norm.py`.

| seed | LS1 | LS2 | 6-axis | dH_util | dD_util |
|------|------:|------:|--------:|---------:|---------:|
| 49 | 0.1178 | 0.1020 | 0.1096 | 0.0006 | 0.0017 |
| 50 | 0.1416 | 0.1301 | 0.1357 | 0.0197 | 0.0127 |
| 51 | 0.1180 | 0.0943 | 0.1055 | 0.0026 | 0.0026 |
| **mean** | — | — | **0.1169** | **0.0076** | **0.0057** |

Provenance: `results/research_loop/r42_alpha_sac_norm_sweep.json`,
`results/sac_norm_s{49,50,51}/agent_*_best.pt`,
`logs/r42_alpha_s{49,50,51}.log`.

### Where this lands

| Configuration | Mean 6-axis | Comment |
|---|---:|---|
| no_control | 0.104 | reference |
| R41-A SAC phi=0 | 0.117 | action-cost removal didn't help |
| **R43-α SAC normalized** | **0.117** | reward shape also doesn't help |
| R23-R27 SAC attractor | 0.137 | original observed band |
| R41-B TD3 normalized | 0.275 | **production setting** |
| HAWE w9802 (R34, ensemble-of-lucky-SAC) | 0.439 | inference-time ensemble |

### Implication — H3 triple-confirmation

The 0.137 multi-seed SAC attractor is now confirmed to be a SAC
property, not a reward-shape artefact. Three independent
data points:

1. **SAC + phi-paper attractor at 0.137** (R23-R27 baseline)
2. **SAC + phi-zero at 0.117** (R41-A — action cost removed entirely)
3. **SAC + normalized at 0.117** (R43-α — paper PHI preserved,
   penalty rescaled to O(1))

In all three, SAC plateaus in the 0.10–0.14 band. TD3, on the
*identical* reward shape (R40 phi=0 = 0.259, R41-B normalized =
0.275), is 2× higher. The mechanism: SAC's entropy regularization
produces high-variance action samples around the policy mean. With
the V4 narrow-target frequency control (max_df threshold 0.13 Hz,
settling-time fraction targets), this stochastic exploration
sprays the action across regions that destabilise control. TD3's
deterministic policy + low Gaussian exploration noise converges to
a single useful action direction and exploits it.

The dH/dD utilization columns reinforce this: SAC dH_util ≈ 0.008,
dD_util ≈ 0.006 — the actor is using < 1 % of the available action
range. TD3 normalized had ~5–15 % range utilization. SAC's entropy
keeps it stuck near zero action while penalizing wide actions; TD3
finds a non-zero useful action and commits.

R21's lucky single-seed at 0.444 is therefore **quadruple-confirmed**
as an entropy-noise discovery: SAC trajectories that happen, by
random chance, to find a high-Q action region before the critic
pulls them back to zero. No SAC config tested here approaches it
reproducibly.

---

## Part β — HAWE ensemble of R41-B TD3 normalized actors

Loaded `results/td3_norm_s{49,50,51}/agent_*_best.pt` via the
TD3-aware path in `scripts/eval_ensemble.py` (`_detect_algo`,
added pre-flight as a 1-line patch; Codex's commit 2 later
re-centralised the same logic in `agents/checkpoint_loader.py`).
Ran with `--agg weighted --weights 0.33 0.34 0.33 --label
hawe_td3_norm` against LS1+LS2 at `--seed 42`.

| Scenario | max_df (Hz) | paper_grade_axes overall |
|---|---:|---:|
| load_step_1 | 0.105 | 0.2596 |
| load_step_2 | 0.080 | 0.3705 |
| **geo-mean** | — | **0.3101** |

dH_util mean 0.039, dD_util mean 0.070.

Provenance: `results/research_loop/r42_beta_hawe_td3_norm.json`
(written by an inline scorer call), and
`results/research_loop/eval_v4_baseline/hawe_td3_norm_load_step_{1,2}.json`
(eval traces).

### Comparison

| Config | 6-axis | vs HAWE TD3 norm | Comment |
|---|---:|---:|---|
| R41-B s49 (single best individual) | 0.278 | −0.032 | best of the three input actors |
| R41-B s50 | 0.267 | −0.043 | middle |
| R41-B s51 | 0.280 | −0.030 | best of the three |
| **R41-B 3-seed mean** | 0.275 | −0.035 | production single-seed baseline |
| **R43-β HAWE TD3 norm** | **0.310** | — | weighted ensemble |
| R21 lucky basin | 0.444 | +0.134 | unmatched |
| HAWE w9802 (lucky SAC ensemble) | 0.439 | +0.129 | unmatched |

### Implication

HAWE-style ensembling buys **+0.030 6-axis** (+11 % over the best
single seed) on top of reliably-trained TD3 normalized actors.
This is a free win at inference time — the three actors are
already trained (~30 min total), and the ensemble eval takes
~30 s. The 0.310 result is the **first non-lucky configuration**
in this project to cross 0.30.

It does **not** approach R21 / HAWE-w9802 (both ≈ 0.44). The gap
to R21 is 1.43×, to the paper's per-axis ≈ 1.0 target is ~3×.
Closing those gaps remains an open R44+ direction.

The lift suggests the three R41-B actors are not converging to
*identical* policies despite tight 6-axis variance (std 0.007).
Each must occupy a slightly different basin of the V4 reward
landscape, and the weighted average exploits the complementarity.

---

## What R43 establishes

- **H3 closed for the third time**. SAC plateau at 0.13 band is
  an algorithmic property, not a reward-shape artefact. Closes
  Q-0002 negatively.
- **HAWE on TD3 normalized works**. First non-lucky configuration
  past 0.30. Closes Q-0003 positively.
- **TD3 normalized actors are complementary at the 30 bp level**.
  Despite tight per-seed std (0.007), ensembling lifts the result
  +0.030 — non-trivial complementarity exists.

## What R43 does not establish

- **R21 / HAWE-w9802 reachability without entropy lottery**: the
  0.44 band remains a SAC-entropy phenomenon. R43-β at 0.31 is
  still 1.4× below it.
- **Whether non-uniform HAWE weights help**: only the
  0.33/0.34/0.33 recipe was tested. A weight sweep (per-actor
  cross-validation on a held-out scenario) might extract more.
- **Whether longer SAC normalized training (200+ ep) escapes the
  0.13 attractor**: based on R41-C TD3 200ep showing flat plateau,
  this seems unlikely, but not directly tested.
- **Closing 0.31 → 1.00 per axis**: untouched. Curriculum
  learning, PPO via on-policy base, paper-faithful G4 inertia
  (Q-0001) remain candidates.

## New claims this round

- `CLM-0048` — R43-α: SAC + normalized penalty 3-seed mean
  0.117; H3 triple-confirmed; algorithm choice is the load-bearing
  factor once reward asymmetry is fixed.
- `CLM-0049` — R43-β: HAWE weighted ensemble of R41-B TD3
  normalized actors reaches 6-axis 0.310; first non-lucky config
  past 0.30; +11 % over the best single seed.

## Questions opened (this round)
- (none — both informal R41 follow-ups now schema-fied and
  closed)

## Questions closed (this round)
- `Q-0002` (closed-negative by CLM-0048) — SAC + normalized does
  NOT match TD3 normalized; algorithm matters even at correct
  reward shape.
- `Q-0003` (closed-positive by CLM-0049) — HAWE ensemble of R41-B
  TD3 norm actors DOES exceed 0.30 (= 0.310, +11 % over best
  individual).

## Questions advanced (this round, status unchanged)
- (none)
