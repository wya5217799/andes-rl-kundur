---
round: R38
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R38 plan — TD3 vs the 0.137 multi-seed attractor

**Date**: 2026-05-17
**Type**: algorithm experiment
**Trigger**: R37 refactor surfaced `_SACBase` + `BaseAgent` Protocol;
adding a new algorithm is now a single-file change. The R29–R33
findings established that **every** SAC variant (hparam sweep, reward
shaping, stochastic ensemble) lands in the 0.137 ± 0.005 attractor.
The architectural hypothesis (CLM-0014 follow-up) is that SAC's
entropy bonus is the cause — it pulls the actor toward near-zero
action regardless of starting point.

## Hypothesis

**H1**: TD3, which has no entropy regularization, will produce
multi-seed 6-axis distributions **not centred on 0.137**. Direction
of the shift is open (could be higher, could be lower or wider).

**H1-falsification**: 3 seeds × 75 episodes, mean 6-axis in
[0.10, 0.18] = H1 refuted (TD3 sits in the same attractor).

**H1-confirmation (weak)**: mean 6-axis < 0.10 or > 0.18.

**H1-confirmation (strong)**: any single seed > 0.30 reproducibly.

## Method

```bash
for seed in 49 50 51; do
  /home/wya/andes_venv/bin/python scripts/train.py \
    --algo td3 --episodes 75 --seed $seed \
    --save-dir results/td3_s${seed} \
    --log-interval 15
done
```

Run 3 seeds in parallel (≤3 ANDES processes per R23 hard limit).

Hyperparameters: TD3 defaults from `agents/td3.py`
(policy_noise=0.2, noise_clip=0.5, explore_noise=0.1, policy_delay=2,
gamma=0.99, tau=0.005). All other env / SAC-shared hyperparameters
identical to the SAC smoke baseline.

## Evaluation

`scripts/_r38_score_td3_sweep.py`:
1. Eval each `agent_*_best.pt` via `scripts/eval_ddic.py` on LS1 + LS2
2. Compute 6-axis geo-mean per seed via `paper_grade_axes`
3. Compare against reference distribution:
   - no_control = 0.104
   - multi-seed SAC attractor = 0.137 (R23–R27 mean)
   - SAC smoke (post-refactor, single seed) = 0.0454
   - R21 lucky basin = 0.444
   - HAWE w9802 = 0.439

## Decision rules (post-experiment)

| Outcome | Next action |
|---------|-------------|
| All 3 seeds < 0.10 | H1 refuted (TD3 even worse than SAC). Investigate critic Q overestimation. |
| All 3 seeds ∈ [0.10, 0.18] | H1 refuted (same attractor). Investigate why both SAC and TD3 converge here — likely env-side reward landscape, not algo-side. |
| At least 1 seed ∈ [0.18, 0.30] | H1 weakly confirmed. Extend to 5 seeds × 200 episodes. |
| At least 1 seed > 0.30 | H1 strongly confirmed. Extend training + add curriculum learning. |
| Any seed crashes (TDS divergence) | Investigate critic Q explosion (TD3 without entropy can be unstable). |

## Exit criteria

- All 3 training runs complete (no crashes)
- 6-axis scores logged for each seed
- Decision rule applied → R38 verdict written + new claim
