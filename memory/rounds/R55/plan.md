# R55 plan — Windowed-horizon anti-smoothness reward

**Date**: 2026-05-17
**Type**: experiment (reward shaping, hijack-resistance hypothesis test)
**Trigger**: R49/R50/R51/R52/R54 (CLM-0057–61) all failed to break
the temporal-flatness ceiling at 0.334. R50 verdict (CLM-0058)
hypothesised that the noise-hijack mechanism could be evaded by
operating on a horizon longer than per-step exploration noise scale
(point (b) in the remaining-levers list). R55 tests this: switch
the existing r_smooth term from per-step diff `(a[t] - a[t-1])²` to
telescoping diff `(a[t] - a[t-W])²` with W=10.

## Theoretical analysis (BEFORE running)

Hypothesised noise-resistance of telescoping diff:
- Per-step (W=1) noise contribution: noise[t] and noise[t-1] are
  independent draws of σ=0.1; Var(diff) = 2σ² ≈ 0.02.
- Telescoping (W=10) noise contribution: noise[t] and noise[t-10]
  still independent; Var(diff) = 2σ² ≈ 0.02 (same!).
- Policy-driven signal at W=1: per-step systematic change ~ 0.005
  (small).
- Policy-driven signal at W=10: cumulative drift over 10 steps,
  potentially much larger IF policy is non-constant.

**Concern**: if the policy never drifts (static-setpoint
attractor), policy signal stays ~0 regardless of W, leaving only
the noise floor. Noise variance is independent of W. So telescoping
might not improve signal-to-noise after all.

## Setup

3 seeds × 75 ep,
`LAMBDA_SMOOTH=-100 SMOOTHNESS_WINDOW=10 python scripts/train.py
--algo td3 --normalize-actions --episodes 75 --seed <S>
--hidden-size 64 --save-dir results/td3_norm_h64_winsm_s<S>`.

Same seeds (49/50/51) as R48-β and R50-α for direct comparison.
Same λ=-100 to isolate the window-effect from λ-magnitude effect.

## Implementation

Four-file edit:
1. `v4_config.py`: new `smoothness_window: int = 1` field
2. `base_env.py`: env-var entry point, `_action_history_dM/dD`
   deques, telescoping branch in r_smooth block, reset clear
3. `andes_vsg_env_v4.py`: cfg.smoothness_window late-enable + made
   cfg.lambda_smooth override conditional (only if non-default 0.0)
   so env-var path keeps working
4. (no train.py change — env var path)

Default `smoothness_window=1` preserves R01/R50 per-step behaviour
(paper-faithful baseline). Regression: `eval_no_control.py` with
LAMBDA=-100 W=10 still produces LS1=0.189, LS2=0.168 bit-identically
(no_control's zero action makes smooth_pen=0 either way).

## Predictions

| outcome | 6-axis | interpretation |
|---|---:|---|
| > 0.30 | win | telescoping unlocks policy drift; new direction |
| 0.20-0.30 | partial | reduced hijack but not eliminated |
| ≈ 0.11 (= R50 W=1) | identical to W=1 | hijack-resistance hypothesis refuted; W is irrelevant |
| < 0.11 | worse | telescoping makes things worse somehow |

**Diagnostic to watch**: training reward magnitude. R50 (W=1) hit
+91 / agent (vs −2 baseline). If R55 still hits ~+91, hijack is
still active.

## Round-number note

This work is numbered R55 because Codex's parallel session took
R53 (memory hygiene) while my R54 (warmstart-shared) ran. So this
round skips R55 directly. No prior R55 from anyone (checked git
log + memory/rounds/ at start).

## Out of scope

- True parameter sharing (~1-2 hr)
- Deterministic-output smoothness reward (~1-2 hr actor-env
  refactor)
- LSTM actor (~1 day)
- Sparse end-of-episode reward
- Curriculum disturbance

## Addresses

Tests the R50/R52-noted "windowed-horizon" lever explicitly. If
this also fails, the 6-failure hexagon closes the cheap+medium
cost lever space entirely.
