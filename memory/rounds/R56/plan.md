---
round: R56
state: active
opened: '2026-05-17'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R56 plan — LSTM recurrent actor (structural pivot vs hexagon ceiling)

**Date**: 2026-05-17
**Type**: experiment (architectural change — first pivot off the
hexagon, highest-confidence among 5 candidates listed in R55 verdict)
**Wall budget**: ~1 day (code complete + 3-seed CPU sweep + verdict)
**Confidence**: highest among remaining structural pivots — only
candidate where deterministic-eval policy is **internally**
time-varying with no exploration-noise dependency, so the R50/R55
noise-hijack channel cannot bottleneck training (verified
mechanically, not just empirically).

## Trigger

R49–R55 closed the cheap-and-medium-cost lever space against the
0.334/0.365/0.351 production triangle ceiling (CLM-0055/0054/0056).
Six independent attacks (obs aug, per-step anti-smoothness, SAC,
time-in-obs, warmstart-shared, windowed anti-smoothness) all failed,
each with the same eval-time pathology: **per-agent deterministic
action collapses to a near-constant setpoint** (dM_span 9–21 % of
paper, dD_util ≈ 0.001).

R55 verdict closes by enumerating 5 remaining structural pivots
(LSTM, deterministic-output reward, sparse end-of-episode, true
param-sharing, curriculum env). The handoff
`memory/handoffs/2026-05-17_R56_lstm-actor-implementation.md` argues
LSTM is the highest-confidence candidate because it makes π(obs_t,
h_t) structurally time-varying via the recurrent state, bypassing
the noise-induced reward channel.

## Hypothesis

A per-agent LSTMCell-based deterministic actor `π(obs_t, h_t)` will
either:

- **(H1, primary)** lift 3-seed mean 6-axis above 0.40 — the
  0.365 single-seed ceiling is policy-class-bounded, not
  environment-bounded;

- **(H2, secondary)** lift per-agent dM_span at eval to >30 % of
  paper while leaving 6-axis < 0.40 — falsifies the static-setpoint
  structural finding (a useful claim even without crossing 0.40);

- **(H3, floor)** mean ∈ [0.30, 0.40] with dM_span > 25 % — LSTM
  is neutral on 6-axis but moves the temporal-variance bottleneck,
  still a useful claim;

- **(H4, null)** mean < 0.20 OR seed collapse — LSTM does not help
  on V4 even with structural memory; bottleneck is genuinely the
  reward landscape, CLM-006N negative.

## Architectural decisions (frozen pre-coding)

| Decision | Choice | Source |
|---|---|---|
| Actor | `LSTMCell(obs_dim, hidden=64) + Linear(64, action_dim)` per agent | R48 h=64 sweet spot |
| Per-agent vs shared | Per-agent (4 independent) | Match V4 decentralized obs |
| Critic | Separate `LSTMCell(obs+action, hidden=64)` per Q1/Q2 | R2D2 convention |
| Sequence length L | 25 (half-episode) | Empirical TD3+RNN tradeoff |
| Burn-in B | 5 (no-grad warmup) | R2D2 hack |
| Batch size | 32 sequences | CPU memory + recurrent convention |
| Replay | Per-episode storage; sample random L-step subseqs stride 1 | Simplest correct path |
| Initial h | Zeros (train + eval) | Standard |
| Burn-in grad | Frozen | R2D2 |
| Action noise | σ=0.1 Gaussian (TD3 baseline unchanged) | Don't change two things |
| Optimizer | Adam, lr=1e-4 (vs 3e-4 baseline — RNN stability) | Conservative |
| Grad clip | max_norm=10 | RNN stability |
| Target nets | Polyak τ=0.005 on LSTM + Linear (both) | Match TD3 |
| Obs passed to actor | `obs_t` only (no prev_action concat) | R49 negative finding |

## File-by-file implementation

| Step | File | Change | Test |
|---|---|---|---|
| 1 | `src/andes_rl_kundur/agents/networks.py` | Add `RecurrentActor` + `RecurrentCritic` | unit: time-varying output given fixed obs |
| 2 | `src/andes_rl_kundur/agents/replay_buffer.py` | Add `SequenceReplayBuffer` | unit: shape (B, T, dim), short-episode padding |
| 3 | `src/andes_rl_kundur/agents/td3_lstm.py` (new) | `TD3LSTMAgent` mirroring `TD3Agent` with sequence update loop, burn-in + L-step backprop, `algo='td3_lstm'` ckpt tag | unit: grad flows to `actor.lstm.weight_ih_l0`; save/load roundtrip |
| 4 | `scripts/train.py` | Branch on `args.algo == 'td3_lstm'`: build agents, recurrent rollout maintaining h across an episode, per-episode `add_episode` instead of step-level `buffer.add` | (covered by E2E run) |
| 5 | `src/andes_rl_kundur/evaluation/paper_path.py` | `deterministic_actor_action_fn` maintains per-agent h across steps in one scenario; reset on new closure | unit: 2-scenario test, h reset between scenarios |
| 6 | `src/andes_rl_kundur/agents/checkpoint_loader.py` | `algo == 'td3_lstm'` branch | (covered by eval) |
| 7 | `tests/test_v4_env_regression.py` | (unchanged — must stay green at 1e-9) | run existing |

## Risk register

| Risk | Mitigation |
|---|---|
| LSTM NaN/Inf grad explosion | grad clip 10 + lr 1e-4 |
| Sequence buffer memory | 200 ep × 50 step × 9 floats × 4 agents ≈ 1.5 MB — fine |
| Per-episode update too slow on CPU | profile after first run; reduce G or seq_len if >40 min/seed |
| Hidden-state reset bug at eval scenario boundary | unit test on 2-scenario back-to-back |
| Codex parallel R56 collision | already reserved atomically via `reserve_round.py` |
| LSTM works but ≠ better than baseline | acceptable verdict (H4 closes structural-pivot menu by one) |

## Success criteria (pre-registered)

- **Primary (CLM-006N positive, H1)**: 3-seed mean 6-axis > 0.40
  at h=64 norm 75ep TD3+LSTM
- **Secondary (CLM-006N supporting, H2)**: per-agent dM_span at
  eval > 30 % of paper (vs 9–21 % baseline)
- **Floor (still claimable, H3)**: mean ∈ [0.30, 0.40] AND dM_span > 25 %
- **Null (CLM-006N negative, H4)**: mean < 0.20 OR any-seed collapse

## Training command

```bash
for seed in 49 50 51; do
  INCLUDE_OWN_ACTION_OBS=0 INCLUDE_TIME_OBS=0 \
  /home/wya/andes_venv/bin/python scripts/train.py \
      --algo td3_lstm \
      --normalize-actions \
      --episodes 75 \
      --seed $seed \
      --hidden-size 64 \
      --save-dir results/td3_lstm_h64_s$seed \
      --log-interval 10 &
done
wait
```

3 parallel WSL processes (project rule: max 3 parallel ANDES TDS).
Wall budget per seed: ~15–25 min (recurrent CPU overhead × 75 ep
× G=10 grad steps × 32 batch × 30 seq).

## Eval command (after training)

```bash
for seed in 49 50 51; do
  /home/wya/andes_venv/bin/python scripts/score_run.py \
      --ckpt-dir results/td3_lstm_h64_s$seed \
      --tag r56_alpha_lstm_s$seed
done
```

Output: `results/research_loop/r56_alpha_lstm.json` consolidating
3 seeds × 2 load-step scenarios; also per-agent `delta_M` /
`delta_D` time series for the dM_span diagnostic.

## Schema plan (post-R56)

Expected:
- **CLM-0063** TD3+LSTM h=64 norm 75ep 3-seed result (positive or negative)
- **CLM-0064** decision: if H1, make LSTM the new production recommendation (supersede CLM-0055); if H2/H3 only, supersede on dM_span dimension only; if H4, no decision claim

Potential:
- **Q-0005** "LSTM + R50/R55 anti-smoothness reward combination" — only opened if H1 hits
- **Q-0006** "LSTM ablation: LSTM-actor + MLP-critic, MLP-actor + LSTM-critic" — only opened if H1 hits big (mean > 0.45)
- Closes nothing from the open-Q ledger directly (this round attacks
  the structural ceiling, not a previously-open question)

## What R56 does not establish

- Whether option (1) from R55 (smoothness on deterministic-policy
  output) works — orthogonal lever, separate round.
- Whether sparse end-of-episode std reward learns through TD3 — option
  (2) from R55.
- Whether curriculum disturbance shifts the basin.
- Whether shared-parameter LSTM (single network across 4 agents)
  works.
