---
round: R264
state: completed
type: research
opened: '2026-07-24'
closed: '2026-07-24'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R264 plan — common/differential-mode gated droop residual probe

**Status**: COMPLETED
**Opened**: 2026-07-24
**Driver**: R262 found only a static R201/droop Pareto trade-off; Q-0027 asks
whether state-selective droop injection can create synergy without retraining.
**Parent**: Q-0027, CLM-0510, CLM-0515

## TL;DR

Evaluate one pre-registered, physics-interpretable gate with three capacity
levels on real ANDES. The gate measures whether differential frequency error
is large relative to common-mode error and injects the droop correction only
then. Compare each result with the measured R262 static frontier and report
physical-frequency endpoints in addition to legacy `geo` and `cum_rf`.

## Snapshot at plan-time (oracle as of 2026-07-24)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0027 [opened R262] Can a state-dependent droop residual policy advance both dual metrics?

## Recently Closed (last 3)

- Q-0008 closed-negative @ R252, by CLM-0415 — verify paper-metric ranking at the 500-episode horizon
- Q-0021 closed-positive @ R252, by CLM-0231 — verify the current TGOV1 governor behavior
- Q-0005 closed-partial @ R186, by CLM-0350 — explain TD3-LSTM seed-50 collapse

## Discovery observation and leakage boundary

R262's frozen R201 endpoint is used as discovery evidence. For both canonical
load steps, the first 21%–23% of samples with

`rho = std(delta_f) / (abs(mean(delta_f)) + std(delta_f)) >= 0.05`

account for more than 99.7% of its accumulated per-step synchronisation loss.
That motivates the gate but means R264 LS1/LS2 are **not an independent test
set**. R264 may establish implementation feasibility and a mechanism signal;
it may not establish generalisation or publication-level superiority.

## Pre-registered controller

For each step, let `x_i = obs_i[1]`, the V4-normalised local frequency
deviation. Compute one shared gate:

`rho = std(x) / (abs(mean(x)) + std(x) + 1e-8)`

`alpha_t = alpha_cap * clip(rho / 0.05, 0, 1)`

`a_t = a_R201 + alpha_t * (a_droop_k10 - a_R201)`

The `0.05` full-scale ratio and all three capacities are frozen before any new
ANDES trajectory:

- `alpha_cap=0.25`
- `alpha_cap=0.50`
- `alpha_cap=1.00`

No threshold, exponent, time window, droop gain, checkpoint, scenario, or
metric will be changed after seeing these runs.

## Methodology

1. Add the reusable gated action function and per-step alpha telemetry beside
   the R262 convex-composition seam.
2. Add a separate physical-endpoint summariser without changing the frozen
   `paper_grade_axes.py` or its cited score.
3. Unit-test the exact mode-ratio equation, endpoint behavior, recurrent reset,
   frontier interpolation, and physical endpoint calculations.
4. Evaluate the three capacity levels with the frozen
   `results/r201_w1_hreg_tau005_s54` best checkpoint, droop k=10, seed 42,
   150 steps, canonical LS1+LS2, real ANDES in WSL.
5. Require 6/6 complete traces and explicit 50-Hz legacy/60-Hz physical
   provenance.
6. Compare gated `geo` at its measured `cum_rf` with piecewise-linear
   interpolation of the seven-point R262 static frontier.

## Primary and diagnostic endpoints

- Legacy diagnostics, unchanged: `geo`, `cum_rf`, LS1, LS2.
- Physical outcomes per scenario: worst-bus peak absolute deviation,
  VSG-mean peak absolute deviation, VSG-mean IAE, differential dispersion
  ISE/RMS, maximum sampled RoCoF, terminal worst-bus error, 0.05-Hz settling,
  action L1 effort, action total variation, and saturation fraction.
- Gate telemetry: mean/max alpha, active fraction, saturated fraction.

`geo` remains a paper-alignment diagnostic; no physical endpoint is folded
back into a new post-hoc composite.

## Pre-registered outcomes

- **STRONG DUAL WIN**: one gated controller has
  `geo > 0.4152387309` and `cum_rf > -0.0367117095`, strictly beating both
  R262 endpoints.
- **BALANCED FOLLOW-UP**: `geo >= 0.35` and `cum_rf >= -0.055`, the R262
  follow-up gate.
- **MECHANISM SIGNAL**: gated `geo` exceeds the interpolated static-frontier
  `geo` at the same `cum_rf` by at least `0.005`.
- **NEGATIVE**: all valid gated points have frontier lift below `0.005` and
  miss both stronger gates. Close this exact gate; do not tune it post hoc.
- **INVALID**: any trace is incomplete/failed, endpoint provenance is absent,
  R262 reference files cannot be reproduced, or tests/dual-metric lint fail.

Q-0027 closes positive only on STRONG DUAL WIN. It closes partial on a
BALANCED FOLLOW-UP or MECHANISM SIGNAL because held-out scenarios and
corrected recurrent training remain absent. It closes negative for this gate
on NEGATIVE; a differently justified learned residual would require a new
prospective question.

## Asset protection contract

- Do not modify V4 dynamics, `V4Config.paper_faithful`,
  `paper_grade_axes.py`, R201 checkpoints, or R262 artifacts.
- Do not call R201 a corrected recurrent policy; it is a frozen legacy
  mechanism probe.
- Add new R264 results under `results/r264_mode_gated_residual`.
- Refuse overwrite by default and close every ANDES session.

## Cross-references

- R261: recurrent Bellman alignment corrected after R201 was trained; dual
  50/60-Hz reporting introduced.
- R262 / CLM-0510: seven static blends form the measured comparison frontier.
- R263 / CLM-0515: this is the first goal selected by the durable programme.
- Q-0027: state-dependent residual/gating question under test.
