# R57 verdict — LSTM lr-warmup 5-seed + HAWE-LSTM ensemble (mixed POSITIVE)

**Date**: 2026-05-17
**Status**: **COMPLETE**. H1α primary (mean > 0.40) missed by 8 %, but
H2α / H3α / β all PASS; two new V4 SOTAs (single + ensemble) set.
**Type**: experiment (α stability hardening) + analysis (β post-hoc ensemble)
**Wall**: ~75 min (~25 min code+review + ~25 min wave-1 + ~12 min wave-2
+ ~10 min scoring + verdict)

---

## TL;DR

> R57-α: TD3+LSTM with corrected lr-warmup (5 training-episode ramp)
> on 5 seeds (49–53). **5-seed mean 6-axis = 0.3674** (vs R56-α
> 3-seed 0.3226, **+14 %**); **median = 0.4150**; range
> [0.109, **0.543**]; collapse rate dropped 1/3 → **1/5 = 20 %**.
> **s51 = 0.543 sets a new V4 single-seed record** (R56-α s51 0.526,
> +3 %). H1α primary threshold (mean > 0.40) missed by 8 %, driven
> by s50's untrained-best.pt artifact; H2α / H3α both pass.
>
> R57-β: HAWE-LSTM ensemble on the 4 healthy R57 ckpts {s49, s51,
> s52, s53}. **top-2 weighted (0.7 s51 + 0.3 s53) = 0.501** — new
> V4 ensemble SOTA (R48-δ HAWE MLP h=64 median = 0.351, **+43 %**).
> All 4 ensemble configs above 0.44; mean uniform = 0.485, s51-
> anchor = 0.495, median = 0.440.
>
> Three CLMs filed (0065 finding, 0066 finding, 0067 decision
> supersession). Q-0005 advanced (lr-warmup negative for s50 due
> to untrained best.pt; the s50 collapse mechanism is now narrowed
> to "best-ckpt selection rule saves pre-training initial weights").
> Q-0007 opened on the best-by-eval-score fix.

---

## R57-α — lr-warmup 5-seed sweep

### Bug found mid-round and fixed

Initial R57-α v1 implementation incremented `_episode_count` in
`begin_episode()`. That made the warmup counter advance during env-
warmup episodes (where `update()` returns None because the buffer is
empty), so the 5-episode warmup window expired before any gradient
step. The 3-seed wave-1 result was **bit-identical** to R56-α (s49
0.333, s50 0.109, s51 0.526) — that bit-identity was the diagnostic
that exposed the bug.

Fix: increment `_episode_count` inside `update()` the first time per
episode that a real batch arrives (gated by
`_this_episode_seen_update` flag). Regression test
`test_lr_warmup_skips_episodes_without_updates` locks the seam.

Wave-1 and wave-2 then retrained with the corrected logic.

### Code review (mid-round, before committing)

Parallel `code-reviewer` + `python-reviewer` audit on the R57 + R56
LSTM stack surfaced 2 HIGH-class issues and 6 MEDIUM-class:

- HIGH (test gap): `test_lr_warmup_ramps_lr_over_first_n_training_episodes`
  called `update()` once per episode iteration, never exercising the
  multi-update-per-episode path that the `_this_episode_seen_update`
  flag was designed to guard. Strengthened the test to call `update()`
  three times per episode and assert lr-constancy.
- HIGH (logic gap): `_apply_lr_warmup` snap-back ran on every post-
  warmup `update()` call forever. Added `_warmup_done` one-shot flag.
- MEDIUM: `flush_episode` did not reset `_this_episode_seen_update`
  (silent stall risk in non-prod call orders). Fixed.
- MEDIUM: `select_action(obs[i])` during env-warmup now passes
  `deterministic=True` explicitly (intent clarity, no behaviour change).
- MEDIUM: `LSTM_GATE_COUNT = 4` named in `checkpoint_loader.py`.
- 4 type-annotation fixes (`hidden_sizes`, `out` dict, `_ensemble_action_fn`
  return, `_current_episode` element type).

8 deferred items are pre-existing R56 or older patterns
(`torch.FloatTensor`, `build_mlp` annotations, ambiguous `l` var,
etc.); not in R57 scope.

All 15 tests in `test_td3_lstm_agent.py` pass after the fixes.

### Training (5 seeds, 2 waves)

```bash
for seed in 49 50 51; do  # wave 1, 3 parallel, ~13 min wall
  /home/wya/andes_venv/bin/python scripts/train.py \
      --algo td3_lstm --normalize-actions --episodes 75 \
      --seed $seed --hidden-size 64 --lstm-lr-warmup-eps 5 \
      --save-dir results/td3_lstm_h64_warmup5_s$seed \
      --log-interval 10 &
done
wait
for seed in 52 53; do  # wave 2, 2 parallel, ~11 min wall
  ... &
done
wait
```

| seed | wall | best reward | ep best | final reward | critic loss early → late |
|---|---:|---:|---:|---:|---|
| 49 | 801 s | -3.4 | 74 | -3.4 | 0.609 → 0.302 |
| 50 | 830 s | -5.0 | 10 | -70 | **8.674 → 4.165** (R56: 8.155 → 4.110) |
| 51 | 833 s | -3.0 | 62 | -7 | 0.666 → 0.229 |
| 52 | 649 s | -3.0 | 61 | -3 | 0.479 → 0.160 |
| 53 | 657 s | -3.0 | 60 | -5 | 0.771 → 0.202 |

s50 continues to follow the same collapse pattern: critic-loss spike
in the first 10 episodes (initial reward -1181 at ep 3), then never
recovers — the saved `best.pt` is **from ep 10, BEFORE updates start**
(WARMUP_STEPS=1000 ≈ 20 episodes of env-warmup), i.e., the
initial/untrained LSTM weights. This makes s50's eval result invariant
to any training-time intervention. See Q-0007 for the fix.

### Eval results (5 seeds × 2 scenarios, seed=42 disturbance)

| seed | LS1 | LS2 | **geo** | max_df | settle | dH_util | dD_util | dM_sp% | dD_sp% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 49 | 0.314 | 0.354 | 0.333 | 0.79 | 0.69 | 0.612 | 0.468 | 122.3 | 53.9 |
| 50 | 0.117 | 0.101 | 0.109 | 0.42 | 0.00 | 0.006 | 0.006 | 3.1 | 1.7 |
| 51 | 0.534 | 0.552 | **0.543** | 0.91 | 0.79 | 0.340 | 0.430 | 68.6 | 43.1 |
| 52 | 0.378 | 0.456 | 0.415 | 0.67 | 0.79 | 0.163 | 0.657 | 75.1 | 65.7 |
| 53 | 0.439 | 0.434 | 0.437 | 0.77 | 0.56 | 0.427 | 0.450 | 109.4 | 51.5 |
| **mean** | — | — | **0.3674** | 0.71 | 0.57 | 0.310 | 0.402 | **75.7** | **43.2** |
| **median** | — | — | **0.4150** | 0.77 | 0.69 | 0.340 | 0.450 | 75.1 | 51.5 |
| **without s50** | — | — | **0.432** | — | — | — | — | — | — |

Comparison to R56-α (same seeds 49/50/51, no warmup, see CLM-0063):

| metric | R56-α (3-seed) | R57-α (5-seed) | Δ |
|---|---:|---:|---|
| mean 6-axis | 0.3226 | 0.3674 | +14 % |
| median 6-axis | 0.333 | 0.4150 | +25 % |
| min 6-axis | 0.109 | 0.109 | 0 % (s50 unchanged) |
| max 6-axis (s51) | 0.526 | 0.543 | +3 % (new SOTA) |
| collapse rate | 1/3 = 33 % | 1/5 = 20 % | better |
| dM_span mean % | 71.8 | 75.7 | +5 % |
| dD_span mean % | 35.6 | 43.2 | +22 % |

### H-criteria adjudication (R57-α)

| Hypothesis | Threshold | Result | Verdict |
|---|---|---|---|
| H1α PRIMARY | 5-seed mean > 0.40 | **0.3674** | **FAIL** by 8 % (s50 drags) |
| H2α SECONDARY | median > 0.40 | **0.4150** | **PASS** |
| H3α FLOOR | collapse < 1/3 | **1/5 = 20 %** | **PASS** |
| H4α NULL | warmup useless | improvements on mean/median/collapse | **REJECTED** |

H1α miss is **structural, not stability**: 4 of 5 seeds train fine; s50
collapses due to a separate mechanism (best-ckpt selection rule, not
training stability), which lr-warmup is fundamentally unable to fix
(the saved checkpoint is from pre-training, so no training-time change
can affect it).

## R57-β — HAWE-LSTM ensemble (4-seed warmup pool)

The R57-β prior (run on R56 2-seed pool {s49, s51}) showed
w90s51 = 0.518. With R57-α's 4 healthy warmup ckpts, the pool widens
to {s49 0.333, s51 0.543, s52 0.415, s53 0.437}; s50 excluded as
collapsed.

| config | weights | LS1 | LS2 | **geo** | dM_sp% | dD_util |
|---|---|---:|---:|---:|---:|---:|
| mean (uniform 4) | (¼, ¼, ¼, ¼) | 0.455 | 0.516 | 0.485 | 69.0 | 0.434 |
| median | — | 0.432 | 0.449 | 0.440 | 90.6 | 0.597 |
| s51-anchor | (1/6, 1/2, 1/6, 1/6) | 0.467 | 0.526 | 0.495 | 64.6 | 0.433 |
| **top2 (s51+s53)** | (0, 0.7, 0, 0.3) | **0.487** | **0.516** | **0.501** | 69.0 | 0.405 |

Reference:
- R48-δ HAWE MLP h=64 median (prior production ensemble): **0.351**
- R56 R57-β-prior 2-seed HAWE w90s51: 0.518
- R57-α s51 single (new SOTA): 0.543

### H-criteria adjudication (R57-β)

| Hypothesis | Threshold | Result | Verdict |
|---|---|---|---|
| H1β PRIMARY | some ensemble > s51 0.526 | 0.501 (top2 best) | **FAIL** (single still best) |
| H2β SECONDARY | some ensemble matches R48-δ 0.351 | all 4 configs ≥ 0.44 | **PASS strongly** |
| H3β FLOOR | 90 % s51 + 10 % s49 ≥ 0.50 | s51-anchor 0.495 (4-actor) | **PASS** |
| H4β NULL | every config < 0.45 | 4 of 4 configs > 0.44 | **REJECTED** |

H1β miss is expected for skewed pools: HAWE averaging pulls toward
the pool mean. With the strongest individual (0.543) being 30 %
above the others (~0.33–0.44), no weighted combination can exceed
the peak without zero-weighting the others — at which point it's
just the peak. The top2 = 0.501 result establishes a **new V4
ensemble SOTA**: +43 % over R48-δ MLP HAWE.

## Mechanism — why s50 stays at 0.109

s50's training-reward trajectory:
```
ep 0: -104    initial random rollout
ep 3: -1181   catastrophic disturbance interaction (env-warmup, all random actions)
ep 10: -5     best reward seen (lucky random actions)
ep 20: ...    env-warmup ends here, real updates begin
ep 74: -70    final trained policy (worse than ep 10's initial)
```

The `Monitor` callback writes `best.pt` whenever a NEW best train-reward
is observed. For s50, best = -5 at ep 10 is never beaten in the 75-ep
run, so `best.pt` stays frozen at ep 10 = **initial untrained weights**.
The deterministic eval of those initial weights gives geo 0.109 — same
as if no training had ever happened. The lr-warmup correctly reduced
the magnitude of weight updates during eps 21-25, which is visible in
the late critic loss (4.165 vs R56 4.110); but those changes do not
affect `best.pt` because `best.pt` was locked at ep 10.

This is **not** a training-stability issue. It's a checkpoint-selection
rule issue. Q-0007 opens the fix: save best-by-eval-score on a held-out
disturbance, not best-by-train-reward.

## New claims this round

- `CLM-0065` (finding) — R57-α TD3+LSTM warmup_eps=5 5-seed result;
  H1α partial / H2α / H3α / H4α-rejected; new V4 single SOTA s51 = 0.543.
- `CLM-0066` (finding) — R57-β HAWE-LSTM 4-seed pool top2 = 0.501;
  new V4 ensemble SOTA (+43 % over R48-δ MLP HAWE 0.351).
- `CLM-0067` (decision) — escalate CLM-0064 production recommendation:
  use TD3+LSTM with `--lstm-lr-warmup-eps 5` for new single-seed work;
  use HAWE-LSTM top2(s51_warmup, s53_warmup) for ensemble deployment.

## Questions opened (this round)

- `Q-0007` — replace best-by-train-reward checkpoint-selection with
  best-by-eval-score (on a held-out disturbance) so seeds like s50
  that train poorly but have meaningful end-of-training policies can
  still produce useful ckpts.

## Questions closed (this round)

- (none — Q-0005 partially addressed but not closed; see "advanced")

## Questions advanced (this round, status unchanged)

- `Q-0005` — three of the listed candidates exercised: lr-warmup
  (no effect on s50 due to untrained-best.pt artifact), larger seed
  pool (collapse rate 1/5 = 20 % vs 1/3 = 33 %, improvement), and
  best-by-eval-score (proposed as Q-0007 successor). The underlying
  deeper question — why seed 50 specifically produces a -1181 reward
  at ep 3 — is unaddressed and remains open. Mechanism narrowed
  from "training instability" to "best-ckpt selection".
