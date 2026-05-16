# R57 plan — Stabilise + ensemble the R56 LSTM win (α + β)

**Date**: 2026-05-17
**Type**: experiment (α: stability hardening) + analysis (β: post-hoc ensemble)
**Wall budget**: ~80 min (~30 min code + ~24 min training + ~5 min scoring + ~20 min verdict)

## Trigger

R56 (CLM-0063) established TD3+LSTM as the first structural attack
that breaks the R49–R55 six-failure hexagon, with **s51 = 0.526** as
a new V4 single-seed record. But two issues blocked a clean H1 PASS
and the CLM-0064 production decision:

1. **s50 collapsed** (6-axis 0.109, dM_span 3.1 %, critic-loss
   initial spike 15× larger than s49/s51) → 1/3 collapse rate is
   unacceptable for a paper headline. Q-0005 opened to investigate.

2. **HAWE-LSTM ensemble untested** — R44-α / R48-δ showed HAWE
   consensus across MLP-actor seeds beats the single-seed best;
   the analog test for LSTM seeds was deferred to R57+.

Additionally, while building the R56 eval path I patched
`paper_path.deterministic_actor_action_fn` to reset recurrent hidden
state at `step == 0`, but **the parallel ensemble code in
`scripts/eval_ensemble.py:_ensemble_action_fn` has the same bug
unfixed** — this blocks R57-β until patched.

## Hypotheses

### α — lr-warmup hypothesis

LSTM early-training instability is the standard recurrent-RL value-
bootstrap explosion. The fix in the literature is **lr warmup**:
ramp the optimizer's learning rate from a small initial value
(e.g., 1e-5) up to the target (1e-4) over the first few episodes
while the LSTM hidden states stabilise. This prevents the early
critic-loss spike from corrupting the LSTM weights.

**Predictions**:

- **H1α PRIMARY**: 5-seed mean 6-axis > 0.40 with lr-warmup
  (vs R56-α 3-seed mean 0.3226 without warmup). Collapse rate
  drops from 1/3 → ≤1/5.
- **H2α SECONDARY**: per-seed median 6-axis > 0.40 (less sensitive
  to single-seed tails).
- **H3α FLOOR**: collapse rate strictly < 1/3 (improvement over
  R56-α even if mean threshold missed).
- **H4α NULL**: warmup has no effect; collapse rate ≈ 1/3 → s50-
  type collapse is intrinsic to the policy class, not the lr
  schedule. CLM-0065 negative.

### β — HAWE-LSTM ensemble hypothesis

R44-α / R48-δ established that median- or weighted-mean-aggregating
multiple MLP actors per-step beats the single-seed best for the
ensemble dimension. The analog for LSTM:

- **mean / median** across {s49, s51} (the 2 converged R56 ckpts)
- **weighted** 90 % s51 + 10 % s49 (R44-α "anchor" pattern)

**Predictions**:

- **H1β PRIMARY**: at least one ensemble config exceeds s51 0.526
  (new ensemble SOTA) — unlikely given the s49/s51 strength gap,
  but the anchor pattern showed this can happen for skewed pools.
- **H2β SECONDARY**: at least one config matches R48-δ HAWE 0.351
  on the production-ensemble dimension — useful if R57-α succeeds
  and ensemble across 5 lr-warmup seeds becomes viable.
- **H3β FLOOR**: 90 % s51 + 10 % s49 weighted ≥ 0.50 (anchor
  preserves s51's quality with minor smoothing).
- **H4β NULL**: every ensemble configuration < 0.45 → HAWE
  drags s51 down, ensemble path is dead-end for LSTM seeds.

## Implementation plan

### α — lr-warmup (~20 min)

- `src/.../agents/td3_lstm.py`:
  - constructor arg `lr_warmup_eps: int = 0` (0 = no warmup)
  - track `self._episode_count` (incremented by `begin_episode`)
  - track `self._target_lr` (the configured target)
  - on each `update()`, if `_episode_count <= lr_warmup_eps`,
    set `param_groups[0]['lr'] = target_lr * (eps / lr_warmup_eps)`
- `scripts/train.py`:
  - `--lstm-lr-warmup-eps` CLI flag (default 0)
  - pass through to `TD3LSTMAgent` constructor in the `td3_lstm` branch
- `tests/test_td3_lstm_agent.py`:
  - new test verifying lr ramps from `target_lr/warmup_eps` at ep 1
    to `target_lr` at ep `warmup_eps`

### β — patch eval_ensemble.py (~10 min)

- `scripts/eval_ensemble.py`:
  - `_ensemble_action_fn` must call `agent.begin_episode()` for each
    recurrent agent across all ckpt sets when `step == 0`
- `tests/test_paper_path.py` (or new file):
  - regression test on `_ensemble_action_fn` analog — verify
    recurrent reset across scenario boundaries

### Training (~24 min wall)

Wave 1 (3 parallel): seeds 49, 50, 51 with `--lstm-lr-warmup-eps 5`
Wave 2 (2 parallel): seeds 52, 53 with `--lstm-lr-warmup-eps 5`

### Scoring (~5 min total)

- `scripts/_r57_score_lstm_warmup.py` (mirror `_r56_score_lstm.py`,
  5-seed loop): per-seed 6-axis + dM_span + dD_span + dD_util +
  corr — same diagnostic set
- HAWE-LSTM eval via `scripts/eval_ensemble.py` (now LSTM-aware) on
  R56 ckpts {s49, s51}:
  - `--agg mean` (uniform 2-actor)
  - `--agg median` (= mean for n=2, but tested for sanity)
  - `--agg weighted --weights 0.9 0.1` (s51-anchored, R44-α pattern)
  - separate paper-grade-axes evaluation on each output

## Risk register

| Risk | Mitigation |
|---|---|
| lr-warmup helps s50 specifically but breaks s49/s51 | low — warmup only modifies first 5 ep, post-warmup is identical to R56 |
| 5-seed wave-2 schedule clashes with wave-1 leftovers | use explicit `wait` between waves |
| HAWE-LSTM with mean drags s51 down too far | tested explicitly via 90/10 weighted as fallback |
| eval_ensemble.py patch breaks the MLP path | unit test covers both recurrent and non-recurrent paths |
| Codex parallel session lands competing R57 | already reserved atomically (R57 dir created) |

## Success criteria (pre-registered)

R57 overall verdict is **POSITIVE** iff any of:
- H1α passes (5-seed mean > 0.40)
- H1β passes (some ensemble > s51 0.526)
- Collapse rate strictly improves (< 1/3) AND another stability
  diagnostic (e.g., critic-loss initial spike) improves measurably

R57 verdict is **NEGATIVE** iff:
- H4α + H4β both trigger (warmup useless AND ensemble drags down)
- This would mean LSTM at h=64/75ep is fundamentally limited at the
  single-config level; further work would need 200-ep, larger
  hidden, or different policy class.

## Schema plan (post-R57)

Expected:
- **CLM-0065** R57-α lr-warmup 5-seed result (positive or negative)
- **CLM-0066** R57-β HAWE-LSTM ensemble result
- Possibly **CLM-0067** decision: if H1α passes, escalate CLM-0064 from
  "candidate" to firm production recommendation; supersede CLM-0055/
  0056 on numerical dimension too (not just framing)

Potential:
- Q-0005 → closed-positive iff H1α/H3α pass, OR closed-negative iff H4α
- Q-0006 unchanged (LSTM × anti-smoothness is a separate round)
- **Q-0007** "longer training (200 ep) — does it tighten the variance
  further?" — only opened if H3α passes but H1α fails (collapse rate
  improves but mean still < 0.40)

## What R57 does not establish

- Q-0006 (LSTM + anti-smoothness) remains open — separate round
- Other 3 R55 structural pivots (deterministic-mean smoothness,
  sparse end-of-ep, true param sharing, curriculum) untouched
- Q-0004 (env refactor) infrastructure debt unaddressed
- Long training (200 ep) for LSTM untested
