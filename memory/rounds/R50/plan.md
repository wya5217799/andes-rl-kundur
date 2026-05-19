---
round: R50
state: active
opened: '2026-05-16'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R50 plan — Anti-smoothness reward (exploit existing r_smooth with negative λ)

**Date**: 2026-05-17
**Type**: experiment (reward shaping)
**Trigger**: R49-α's R03 obs-probe negative finding (CLM-0057) concluded
that V4 actor's static-setpoint behaviour is NOT caused by missing
observation information. The next candidate lever is **reward shaping
to explicitly value temporal action variation**.

## The lever

`base_env.py:341-354` already implements an action-smoothness penalty
term, but gated on `LAMBDA_SMOOTH > 0.0`:

```python
r_smooth_sum = -self._lambda_smooth * smooth_pen
# smooth_pen = Σ_i [((dM_i - prev_dM_i)/dM_range)² + ((dD_i - prev_dD_i)/dD_range)²]
```

With LAMBDA_SMOOTH > 0 → penalises action change (rewards smoothness, R01
Phase A direction).
With LAMBDA_SMOOTH < 0 → would reward action change (anti-smoothness)
**but the guard `if > 0.0` blocks negative values**.

## Pre-flight (single-line guard fix)

Change `base_env.py:343` from `if self._lambda_smooth > 0.0:` to
`if self._lambda_smooth != 0.0:`. Default `LAMBDA_SMOOTH=0.0` stays
paper-faithful (term disabled). Non-zero values activate, with
arbitrary sign:
- positive → smoothness reward (R01 direction)
- negative → anti-smoothness / temporal-variation reward (this round)

Add inline comment crediting R50/CLM-0057.

## Part α — Single λ smoke-test at h=64

**Question**: Does rewarding action change (LAMBDA_SMOOTH=-100) at
the production setting (TD3 norm 75ep h=64) unlock the dD_util /
dM_util axes?

**Method**: 3 seeds × 75 episodes,
`LAMBDA_SMOOTH=-100 python scripts/train.py --algo td3
--normalize-actions --hidden-size 64 --episodes 75 --seed <S>`.
Same seeds (49/50/51) as R48-β for direct per-seed comparison.

**λ calibration**: Reward decomp at R48-β baseline shows r_f ~ 85%
of |total reward|, r_h+r_d ~ 15%. Typical smooth_pen raw value
~ 0.01 per step (per-agent dM swing ~5%). With λ=100, r_smooth raw
contribution ~ 1 per step vs typical r_f ~ -1 per step → comparable
magnitude. Starting value chosen to make smoothness term roughly
on par with frequency term (not dominate, not negligible).

**Predictions**:
- ≥ 0.40 → reward shaping unlocks temporal variation; potentially
  new production setting.
- ≈ 0.334 → reward magnitude not enough to change policy.
- ≪ 0.30 → smoothness reward overwhelms frequency control; calibration
  too aggressive.

## Risks

- **Reward magnitude mis-calibrated**: λ=-100 might be too strong
  (smoothness reward dominates, ignores frequency).
- **Exploration-noise hijack**: deep RL pitfall where high reward
  comes from exploration noise rather than deterministic policy
  output. If smoothness reward depends on per-step action change
  and exploration noise adds change, training reward is high
  regardless of actor's deterministic output. Critic learns
  nothing useful.
- **Reward function divergence from paper**: LAMBDA_SMOOTH != 0
  is a research-mode setting, not paper-faithful. Default stays
  0.0; same pattern as R41-B's normalized action_penalty_mode
  (CLM-0047) which kept paper baseline as default.

## Follow-up plan

- **If R50-α ≥ 0.40**: sweep λ ∈ {-10, -50, -100, -300, -1000} for
  per-axis calibration; promote to production if any λ value
  improves both 6-axis mean AND utilization without sacrificing
  frequency.
- **If R50-α ≈ 0.334**: try λ=-1000 (~10× larger) to break the
  static attractor.
- **If R50-α < 0.20**: clean negative finding (per-step
  exploration-noise hijack); abandon this reward-shaping approach;
  try alternative (SAC h=64, or recurrent actor).

## Addresses

- Bottleneck diagnosed in R48-β / R49: "per-agent dM span 9-21%
  of paper" — the temporal-flatness bottleneck (CLM-0057 context).

## Out of scope

- Expose LAMBDA_SMOOTH via V4Config field + train.py CLI (cleanup
  follow-up if results are positive)
- Smoothness reward computed on deterministic-policy output rather
  than noise-augmented action (would need restructuring of
  train.py to call actor in deterministic mode for reward calc)
- Multi-step horizon smoothness (variance over a window, not
  pairwise step diff)
- SAC h=64 (deferred to R51+ if R50 is negative)
