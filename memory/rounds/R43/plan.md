# R43 plan — Two-part follow-up to R41 / CLM-0047

**Date**: 2026-05-17
**Type**: experiment (α) + analysis (β)
**Trigger**: R41 closed three sub-questions but informally raised
two more in its verdict footer (also flagged in
`memory/handoffs/2026-05-17_post-R41.md` R42-α / R42-β menu). The
handoff's "R42-α / R42-β" labels were anticipatory — by the time
this round ran, **R42 had already been claimed by a concurrent
Codex session** for an infrastructure deepening pass (`paper_path`,
`checkpoint_loader`, `training_checks`, validate dedup). This
round therefore re-uses the same experiment labels α/β but lands
under **R43** to avoid trampling Codex's R42 plan/verdict.

The two informal R41 follow-ups are schema-fied as **Q-0002**
(SAC norm vs TD3 norm) and **Q-0003** (HAWE ensemble of R41-B
TD3 norm actors).

## Part α — SAC + normalized penalty (Q-0002)

**Question**: Does SAC with `V4Config.action_penalty_mode =
"normalized"` reach the same 6-axis band as TD3 normalized (0.275)?
Or does it stay near the SAC attractor (~0.13)?

**Method**: 3 seeds × 75 episodes, SAC `--algo sac
--normalize-actions` with default PHI (paper Eq.14). Same hyper-
parameters as R41-B except the algorithm switch. Score via
`scripts/eval_ddic.py` + `paper_grade_axes.evaluate_trace`, geo-mean
across LS1+LS2. New helper `scripts/_r42_score_alpha_sac_norm.py`
mirrors `_r41_score_B_normalized.py` (kept the `_r42_` prefix to
match the handoff naming; no functional difference).

**Predictions** (from handoff):
- ≥ 0.20 → reward shape alone explains the trap; SAC is fine once
  reward asymmetry is fixed.
- ≈ 0.13 → H3 confirmed for the THIRD time (after R41-A SAC phi=0
  at 0.117 and R23-R27 SAC phi=paper at 0.137); SAC's entropy
  variance defeats the reward-shape fix.

## Part β — HAWE ensemble of R41-B TD3 normalized actors (Q-0003)

**Question**: Does inference-time weighted-ensemble averaging of
the three R41-B TD3 normalized actors push 6-axis past 0.30?
HAWE w9802 (R34, CLM-0007) reached 0.439 with an ensemble of
lucky SAC checkpoints; an ensemble of *reliably-trained* TD3
normalized actors is the cheapest test of "is ensembling a free
win on this problem?"

**Method**: `scripts/eval_ensemble.py` with `--ckpt-dirs
results/td3_norm_s{49,50,51} --suffixes best best best --weights
0.33 0.34 0.33 --agg weighted --label hawe_td3_norm`. Score with
`paper_grade_axes.evaluate_trace`, geo-mean across LS1+LS2.

**Pre-flight**: `eval_ensemble.py` was SAC-only (KeyError on
`log_alpha` when loading TD3 ckpts). Added `_detect_algo` helper
mirroring `eval_ddic.py`. This minimal patch landed first, then
Codex's R42 commit 2 (`refactor(agents): extract
checkpoint_loader.load_agents`) re-centralised the same detection
in a shared module. Either form supports the eval.

**Predictions**:
- ≥ 0.30 → ensembling is a free +5–10% over the 0.275 single-seed
  ceiling.
- ≈ 0.27 → ensemble doesn't help; individual actors converge to
  the same basin so averaging is redundant.
- > 0.40 → R41 actors are diverse enough to approach R21's lucky
  basin.

## Order

β runs first (~30 s eval, no training). α launches as 3 parallel
WSL training processes after β (max 3 WSL python — R23 hard limit).

## Addresses Questions

- Q-0002 — SAC norm vs TD3 norm (informal R41 → schema-fied R43)
- Q-0003 — HAWE TD3 norm > 0.30 (informal R41 → schema-fied R43)

## Out of scope

- SAC + normalized at longer training (75 ep was sufficient to
  observe attractor convergence).
- HAWE weight sweep (uniform-ish 0.33/0.34/0.33 matches CLM-0007's
  w9802 recipe; if non-uniform helps, a later round).
- Re-running R41-B to verify on the post-Codex-refactor codebase
  (the refactored `eval_ddic.py` / `eval_ensemble.py` keep the
  same trace JSON shape; provenance still cites R41 result JSONs).

## Risks

- **Concurrent R42 commits**: my eval_ensemble.py patch (~10 lines)
  could conflict with Codex's commit 1 (paper_path) / commit 2
  (checkpoint_loader). Resolution: my β eval ran *before* the
  refactor sequence completed; the saved JSON is the citable
  artefact. Whether the file still contains my `_detect_algo` is
  history — the eval is reproducible from any TD3-aware loader.
