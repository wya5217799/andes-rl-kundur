# R48 plan — Hidden-size sweep on TD3 normalized 75ep

**Date**: 2026-05-17
**Type**: experiment (hyperparameter sweep)
**Trigger**: R47 nailed down three "training-side levers don't help"
findings:
- R47-α: HAWE aggregation choice doesn't break the single-best cap
- R47-β: longer training (200 ep) doesn't help, may collapse seeds
- R44-β: G4 inertia setting doesn't affect ranking

What remained un-probed: **network architecture**. R41-B's
production setting (TD3 norm 75ep) ran with the default
`HIDDEN_SIZES = [128, 128, 128, 128]` from `config.py`. V4 has
`obs_dim = 7` per agent — small. The default 128-wide × 4-deep
network may be materially over- or under-parameterised for this
problem. R48 sweeps hidden-size at 32 / 64 / 128 / 256 to find the
sweet spot, with the same seeds (49/50/51) as R41-B for direct
comparison.

## Parts

### α — hidden=256 (over-capacity test)

**Question**: Does a larger network help? Many RL benchmarks default
to 256-wide; this tests whether V4 is bottlenecked by capacity at
the 128 default.

**Method**: 3 seeds × 75 episodes, TD3 `--algo td3
--normalize-actions --hidden-size 256`.

**Prediction**: ≥ 0.30 if 128 is undersized; ≈ 0.275 if neutral;
< 0.275 if over-parameterised on V4's small obs space.

### β — hidden=64 (under-capacity test)

**Question**: Does a smaller network help? 64-wide × 4-deep is a
3.4× reduction in parameter count. If V4 is over-parameterised at
128, 64 should improve mean and tighten variance.

**Method**: 3 seeds × 75 episodes, TD3 `--algo td3
--normalize-actions --hidden-size 64`.

**Prediction**: Either ≈ 0.275 (neutral, 128 was fine) or > 0.275
(smaller helps regularise on small obs space).

### γ — hidden=32 (very-small)

**Question**: If β shows smaller is better, does even smaller win?

**Method**: 3 seeds × 75 episodes, TD3 `--algo td3
--normalize-actions --hidden-size 32`. Only run if β is
interesting.

**Prediction**: Either monotonic continuation of β's trend, or a
plateau/U-shape if 64 is the sweet spot.

### δ — HAWE on h64 actors (bonus, if β yields actors > 0.30)

**Question**: Does the HAWE-3 ensemble of the h64 actors beat
R44-α's 0.347 anchored asymptote? With stronger single actors, the
ensemble cap rises proportionally.

**Method**: `eval_ensemble.py`-equivalent inline scoring (the
checkpoint_loader.load_agents currently requires explicit
`hidden_sizes` kwarg; `eval_ensemble.py` doesn't expose this so
inline Python is faster than patching). Three configs: uniform
(0.33/0.34/0.33), median, s51-anchored 0.5.

**Prediction**: Median HAWE on h64 ≥ 0.35 if h64 actors are
materially stronger than h128 (which R47-α showed cap at 0.347).

## Order

Sequential: α first (15 min), then β (15 min), then decide if γ
needed (15 min), then δ (1 min). All ckpts saved under
`results/td3_norm_h{N}_s{seed}/` for traceability. Each step uses
3 parallel WSL processes (max-concurrency cap).

## Pre-flight

`scripts/eval_ddic.py` (and the inline-helper-equivalent
`paper_path.run_scenario`-based scoring) uses the default
`HIDDEN_SIZES = [128, 128, 128, 128]` when calling
`checkpoint_loader.load_agents`. For non-128 ckpts, this fails
with state_dict shape mismatch (`size mismatch for net.0.weight:
copying a param with shape torch.Size([N, 7]) from checkpoint, the
shape in current model is torch.Size([128, 7])`). Workaround: call
`load_agents(..., hidden_sizes=(N, N, N, N))` directly in Python
and use `paper_path.run_scenario` + `paper_grade_axes.evaluate_trace`
for scoring. Not refactoring `eval_ddic.py` to take a CLI flag in
this round — out of scope; would be a separate infra commit.

## What R48 decides

- If h64 wins on mean and variance: **supersede CLM-0047** with a
  new production setting (TD3 norm 75ep h64). Document the
  hidden-size finding as the deepest single-lever improvement
  observed since R41-B.
- If h64 is neutral / worse: confirms 128 is the right capacity;
  the per-axis gap is not a network-architecture problem.
- Either way: write up the four-point hidden-size curve as a
  reference for future hyper-parameter work.

## Out of scope

- batch_size sweep (saved for R49+ if h-size finding is positive)
- learning rate sweep (CLI doesn't expose; would need config edit)
- TD3 target-smoothing noise / delayed-update freq
- Combined (h, ep, bs) sweep — premature optimisation
- Codex's R45 / R46 Q-0004 work — different track
