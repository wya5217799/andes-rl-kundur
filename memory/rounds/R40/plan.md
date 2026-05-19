---
round: R40
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R40 plan — CLM-0043 extreme-case validation via PHI_H=PHI_D=0

**Date**: 2026-05-17
**Type**: hypothesis validation (cheap ablation)
**Trigger**: R38/CLM-0043 claims the V4 reward landscape's
500–1000× action-cost asymmetry is the structural cause of the
0.137 multi-seed attractor. Before designing a proper "normalized
action penalty" reward variant (R41 candidate), test the extreme
case: set the action-penalty weights to **zero** and see whether
the actor starts using the action range.

## Hypothesis (sharper than R38)

**H2-extreme**: With PHI_H = PHI_D = 0 (action is free), TD3 will
learn a policy that uses a meaningful fraction of the action range
(dH/dD utilisation > 0.10 on the paper-grade-axes scale, vs the
0.003–0.010 we saw at PHI_H=PHI_D=0.0056).

**Falsification signals** (any of):
- dH/dD utilisation still < 0.05 → action cost was not the binding constraint
- 6-axis still < 0.10 → other axes dominate the failure
- Training crashes from runaway Q values

**Confirmation signal**: dH/dD utilisation > 0.10 across all 3 seeds,
AND 6-axis mean > 0.137 (above the previous SAC attractor).

## Method

Reuse the existing CLI seam — the V4Config injection from CLM-0042
already supports `--phi-h 0 --phi-d 0`. No code change required.

```bash
for seed in 49 50 51; do
  /home/wya/andes_venv/bin/python scripts/train.py \
    --algo td3 --episodes 75 --seed $seed \
    --phi-h 0.0 --phi-d 0.0 \
    --save-dir results/td3_noactioncost_s${seed} \
    --log-interval 15
done
```

Run in parallel (≤3 ANDES processes; R23 hard limit). 3 TD3 seeds
first; SAC variant deferred to R41 if H2-extreme confirmed.

## Evaluation

Same 6-axis ranker on `agent_*_best.pt`. Compare against R38's
PHI_H=PHI_D=0.0056 TD3 baseline:

| Reference | Mean 6-axis | dH_util | dD_util |
|-----------|-------------|---------|---------|
| no_control | 0.104 | 0 | 0 |
| SAC attractor (R23-R27) | 0.137 | low | low |
| **TD3 phi_paper (R38)** | **0.084** | **0.003-0.010** | **0.003-0.010** |
| **TD3 phi_zero (R40)** | **?** | **?** | **?** |

## Decision rules

| Outcome | Next round |
|---------|-----------|
| 6-axis < 0.11 AND util < 0.05 | Hypothesis falsified. Investigate other constraints (e.g. action smoothness term LAMBDA_SMOOTH, env-side physics). |
| 6-axis ∈ [0.11, 0.20] AND util > 0.10 | H2 weakly confirmed. R41: implement normalized penalty (cleaner than phi=0 which has no smoothing). |
| 6-axis > 0.20 AND util > 0.20 | H2 strongly confirmed. R41: normalized penalty + multi-seed sweep + extended training. |
| Crashes from Q-explosion | Tighter explore_noise + lower lr; consider Q clipping. |

## Why this is cheap

- No code change (V4Config supports the flag already)
- 3 parallel WSL processes (no new infra)
- ~10–15 min wall time
- Result either validates CLM-0043 or surfaces a deeper constraint
- Either outcome is publishable insight
