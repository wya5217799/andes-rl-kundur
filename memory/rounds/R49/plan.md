# R49 plan — System audit + R03 obs probe (INCLUDE_OWN_ACTION_OBS)

**Date**: 2026-05-17
**Type**: audit + experiment
**Trigger**: User requested a system-health check before R49 launch, plus
a deeper data analysis to identify the highest-ROI next experiment.

## Part audit — Training + evaluation system health

Before running another experiment, verify the pipeline is sound. Checks:
- `pytest tests/` (60 expected after R42 hotfix tests)
- `eval_no_control.py` (bit-identical guard, expect LS1=0.189 LS2=0.168)
- Re-eval `td3_norm_h64_s51` ckpt (expect 6-axis=0.365 from R48)
- ckpt schema audit (algo field, no log_alpha for TD3, net.0.weight shape)
- Action-magnitude inspection (verify "tiny actions" hypothesis)

## Part diagnostic — Action utilization deep-dive

Re-examine the R48-cited bottleneck "dH_utilization / dD_utilization
scores stay at 0.04–0.10 while LS1/LS2 frequency axes are 0.34–0.39".
Decompose what `paper_grade_axes._action_utilization` actually
measures, and characterise WHY our actors score low.

Hypothesis going in (revised twice during audit):
- v1 (pre-audit): "actions are tiny per step"  — **WRONG** (max |dM|≈145, max |dD|≈445 over 6s)
- v2 (mid-audit): "agents are uncoordinated, cross-agent mean cancels" — **PARTIALLY WRONG** (corr is mixed +0.04 to +0.46)
- v3 (post-audit): "**each agent's action is temporally flat** — per-agent dM_span ≈ 9–21 % of paper, dD_span ≈ 11–13 %" — **CORRECT**

The TD3 deterministic feed-forward policy converges to a near-static
setpoint per agent ("push initial, hold, end") rather than the
paper-target time-varying ramp.

## Part α — Test the R03 probe (INCLUDE_OWN_ACTION_OBS=1)

**Initial proposal** (A' in the user-facing menu): add `omega_dot` to
observations to give the actor freq-derivative info.

**Audit override**: `base_env.py:470` shows `omega_dot` is **already**
in obs as `o[2]` (local) and `o[3+MAX_NEIGHBORS+k]` (neighbours).
OBS_DIM=7 already = 3 (P, d_omega, omega_dot) + 2*MAX_NEIGHBORS=4
(neighbour d_omega + omega_dot). Adding more omega_dot is moot.

**Re-targeted lever**: `base_env.py:139-144` exposes
`INCLUDE_OWN_ACTION_OBS` env var that bumps OBS_DIM 7→9 and appends
the agent's own previous action `(delta_M_prev, delta_D_prev)` to its
observation. This probe was flagged in the post-R41 handoff as a
candidate but has not been tested in any prior round.

Hypothesis: with knowledge of its own last action, the actor can
intentionally vary action over time — e.g., learn "if I just pushed
+200, switch to 0 next step". Would directly address the temporal
flatness bottleneck.

**Method**: 3 seeds × 75 ep, TD3 `--algo td3 --normalize-actions
--hidden-size 64` with `INCLUDE_OWN_ACTION_OBS=1` env var set. Eval
also with env var set. Direct comparison to R48-β (same seeds, same
config, env var OFF, mean 0.334).

**Predictions**:
- ≥ 0.40 → R03 obs unlocks temporal variation; new production setting.
- ≈ 0.334 → R03 obs neutral; bottleneck isn't lack of info.
- ≪ 0.30 → R03 obs creates a "copy last action" loop; static-setpoint
  worsens.

## Pre-flight

`checkpoint_loader.load_agents` uses `AndesMultiVSGEnvV4.OBS_DIM`
(class attr = 7), not the instance attr that's bumped to 9 by the env
var. Inline workaround: construct TD3Agent directly with
`obs_dim = AndesMultiVSGEnvV4.OBS_DIM + 2`. Out-of-scope fix:
make load_agents read instance OBS_DIM or accept an `obs_dim=` kwarg
(R50+ infra commit).

## Addresses

- (no Q schema entry — R49 is exploration, no formal Question)

## Out of scope

- Modifying `paper_grade_axes._action_utilization` to a different
  metric (it's the paper-cited Asset 4, ranker is fixed)
- Adding fresh observation channels beyond R03 probe
- Recurrent policy (LSTM actor) — major arch change
- Reward shaping that explicitly rewards temporal action variation —
  R50 candidate if R49-α is negative
