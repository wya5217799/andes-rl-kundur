---
round: R44
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R44 plan — HAWE weight-sweep (α) + Q-0001 G4 inertia rerun (β)

**Date**: 2026-05-17
**Type**: analysis (α) + experiment (β)
**Trigger**: R43-β established HAWE-3 uniform = 0.310 (first non-
lucky 6-axis past 0.30). Two follow-ups left over from R43:
1. Does anchored / non-uniform HAWE weighting push higher? Can it
   approach R41-C s52's lucky-tail single-seed 0.353?
2. Q-0001 (the only open question after R43) — does G4 inertia
   preservation (paper-faithful setting) change the headline
   ranking on which CLM-0005/0006/0007/0008 are based?

## Part α — HAWE weight sweep across phi0_200ep + norm actors

**Question**: Does adding the R41-C TD3 phi0 200ep actors (5 seeds,
single-seed range [0.187, 0.353], s52=0.353 is the historical
non-lucky max) to the ensemble — either alone or unioned with
R41-B TD3 norm 3-seed actors, or with s52-heavy weighting — beat
R43-β's 0.310?

**Method**: 5 ensemble configurations via `scripts/eval_ensemble.py`:
- HAWE-5 phi0_200ep s49–s53 uniform (0.2 each)
- HAWE-8 union: norm s49/50/51 + phi0_200ep s49–s53 uniform (0.125 each)
- HAWE-3 s52-anchored 50% (s52 + norm_s51 + norm_s49 weights 0.5/0.25/0.25)
- HAWE-3 s52-anchored 75% (0.75/0.125/0.125)
- HAWE-3 s52-anchored 90% (0.9/0.05/0.05)

Score with `paper_grade_axes.evaluate_trace`, geo-mean across
LS1+LS2.

**Predictions**:
- Uniform HAWE-5 / HAWE-8 ≈ 0.30: averaging weak + strong actors
  cancels out, no lift.
- Anchored sweeps: monotonic approach to s52 alone (0.353). The
  question is whether anchoring extracts ALL of s52's individual
  performance or leaves a complementarity bonus.

## Part β — Q-0001: G4 inertia paper-faithful rerun (no_control only)

**Question**: Does `V4Config.zero_g4_inertia=False` (paper-claimed
setting, currently pinned to True via CLM-0040 to preserve bit-
identical headline reproducibility) shift the no-control baseline
6-axis enough to flip any pairwise ranking against the established
headlines?

**Method**: `scripts/_r44_eval_no_control_g4preserved.py` — inline
zero-action eval with explicit `V4Config(zero_g4_inertia=False)`
injected into `AndesMultiVSGEnvV4(config=...)`. (Default
`paper_path.run_scenario` doesn't accept a config override; needed
a one-off script.)

**Pass criterion** (per Q-0001's own Candidates list): if the
G4-preserved no_control 6-axis stays in [0.09, 0.12], no headline
ranking flips and Q-0001 closes-negative. If it lands outside that
band, escalate to R21-single-seed rerun.

## Order

α runs first (5 evals × ~30 s each = ~2.5 min); β runs next
(~3-5 min for the ANDES TDS).

## Addresses Questions

- Q-0001 — G4 inertia paper-faithful (opened R37, untouched since)

## Out of scope

- Re-running R21 single-seed under G4 preserved: deferred unless
  Part β shows a > 0.05 shift on no_control.
- 22-ckpt H₀ sweep under G4 preserved: too expensive (~6 h × 4
  seeds); deferred to R45+ if Part β suggests it.
- Full headline regeneration: only if R21 single-seed under G4
  preserved drops below HAWE w9802 — would require paper revision.

## Side observation expected (already flagged in R43)

The current `paper_grade_axes` ranker (post-R30/R36 tuning) scores
no_control at 6-axis ≈ 0.094 — distinct from the headline
CLM-0008's R30-era 0.104. This is a separate ranker-drift issue,
NOT a Q-0001 finding. Note in R44 verdict for visibility but do
not file a correction against CLM-0008 in this round — it's
orthogonal to G4-vs-no-G4.
