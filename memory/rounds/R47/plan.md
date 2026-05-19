---
round: R47
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R47 plan — HAWE ceiling sharpening (α) + TD3 norm 200ep gap-fill (β)

**Date**: 2026-05-17
**Type**: analysis (α) + experiment (β)
**Trigger**: R44 left two specific holes:
1. R44-α's "HAWE caps at single best actor" claim was based on the
   s52-anchored 50/75/90 weight sweep. Two aggregation variants
   were untested: top-3-individuals uniform (average the 3
   strongest single actors instead of s52 + 2 anchors) and median
   (consensus-picking instead of weighted mean). If either
   exceeds 0.347, CLM-0050's "cap" framing needs softening.
2. The R41-B (TD3 norm 75ep) × R41-C (TD3 phi=0 200ep) interaction
   was untested: training length × reward shape. R41-C showed 200ep
   phi=0 ≈ 75ep phi=0 (CLM-0046 plateau). Whether the plateau
   generalises to normalized rewards — or whether the right reward
   shape unlocks longer-training improvement — is open.

Round-number note: this work was started under the informal label
"R46-α / R46-β" before discovering Codex's parallel session had
already taken R45 (Q-0001 escalation, since rendered moot by R44)
and R46 (architectural deepening Phase A, Q-0004 opened). To avoid
trampling either round, my research is filed as **R47**. The
result JSON files retain `r46_*` filenames where they were named
before the conflict was discovered.

## Part α — HAWE top-3 + median (CLM-0050 stress-test)

**Question**: Do top-3-individuals (s52, s50_phi0_200ep, s51_norm)
uniform-weighted or median-aggregated beat the R44-α s52-anchored
90 % asymptote (0.347)?

**Method**: 2 evals via `scripts/eval_ensemble.py`:
- `--agg weighted --weights 0.33 0.34 0.33` (top-3 uniform)
- `--agg median` (top-3 median, no weights)

**Pre-flight**: Codex's R45 commit 2 (34f5d9f) dropped back-compat
aliases in eval_ddic / eval_ensemble; later, Codex's R42 post-
review hotfix (74704fe) changed `checkpoint_loader.load_agents` to
keyword-only `suffix=`. `eval_ensemble.py` line 95 still called
`load_agents(Path(cd), suf)` positionally — a regression. Patched
to `load_agents(Path(cd), suffix=suf)` as a 1-character fix
(`scripts/eval_ensemble.py:95`).

**Predictions**:
- top-3 uniform ≈ 0.30 (the strongest non-s52 actors are ~0.28,
  averaging pulls back toward the mean).
- top-3 median ≈ 0.33–0.34 (median preserves consensus, may
  approach R44-α 90 % anchor).

## Part β — TD3 normalized 200ep gap-fill (CLM-0046 generalisation)

**Question**: Does extending TD3 normalized training from 75 ep
(R41-B mean 0.275) to 200 ep improve the multi-seed mean, or does
the R41-C 75-vs-200 plateau (CLM-0046) generalise to normalized
rewards too?

**Method**: 3 seeds × 200 episodes, TD3 `--algo td3
--normalize-actions --episodes 200`. Same seeds as R41-B (49, 50,
51) for direct per-seed comparison. Score via the same
`paper_grade_axes.evaluate_trace` geo-mean pipeline used in R41-B
and R44.

**Predictions**:
- Same plateau as R41-C: 200ep mean ≈ 75ep mean (~0.275). Range
  may widen.
- Or: 200ep mean is materially > 75ep mean. This would refute
  CLM-0046's "training plateaus" hypothesis for normalized rewards.
- Or: 200ep mean is materially < 75ep mean (overfitting). Worst
  case but observable.

## Order

α runs first (~1 min, 2 quick evals + score). β was kicked off in
parallel (3 background WSL training processes, ~28 min wall via
3-parallel) before α was reviewed; β scoring then waits for the
last seed.

## Addresses

Sharpens CLM-0050 (HAWE cap robust to aggregation variants) and
CLM-0046 (training-length plateau generalises across reward shapes).

## Out of scope

- HAWE with R47-β actors added to the pool (would test whether
  fresh 200ep normalized actors are complementary to the existing
  pool; deferred to R48+ if any 200ep actor scores high).
- Q-0004 (AndesBaseEnv absorption) — Codex's, not mine.
- Curriculum / PPO / observation augmentation — bigger experiments
  for later rounds.

## Risks

- **Concurrent Codex commits on src/utils**: Codex's R45 / R46 work
  has been mid-edit during this round. Strategy: commit R47 via
  `git commit -- <explicit paths>` so the staging area's Codex
  files don't ride along (same approach used in R44).
- **eval_ensemble.py 1-char regression**: the keyword-arg fix is
  load-bearing for α and must persist. The change is on a line
  Codex has touched; if Codex's next commit reverts it, R47-α
  results stay valid (already produced JSON) but future evals
  break.
