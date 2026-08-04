---
round: R319
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R319 plan - delay-augmented observer LQR gate

**Opened**: 2026-08-03
**Driver**: answer Q-0074 with the sole controller-form repair admitted by
R318 before any physical closed-loop execution.
**Parent**: CLM-0790; CLM-0795; CLM-0800; Q-0074.

## TL;DR

Synthesize one full-order observer-based discrete-time quadratic regulator per
R316 operating point directly on the exact one-sample-delay augmentation. Use
one fixed Bryson-style normalization, no scalar grid, and no outcome-driven
tuning. Compare retained versus deleted common/differential transfer blocks
under identical delivered measurements, four-coordinate actions, node
governor, development/examination cases, mismatch transforms, and budgets.
Stop at model-only PASS, NO-GO, or INVALID. Run no ANDES, EVAL, physical closed
loop, distributed runtime, reward, agent, or training work.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete - re-run render.py only after the round closes. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0074 [opened R318] Can one full-order observer-based discrete-time quadratic regulator, synthesized directly on the one-sample-delay augmented realizations, pass offline pole, estimation, constraint, mismatch, and matched-comparison gates without reusing the rejected DC inverse or scalar grid?

## Recently Closed (last 3)

- Q-0073 closed-positive @ R318, by CLM-0800 - Which frozen scalar candidates were rejected by the nominal augmented-pole gate versus the governed development traces, and can one analytically preconditioned timing or controller-form repair be defined without widening the outcome-seen grid?
- Q-0072 closed-negative @ R317, by CLM-0795 - What constrained common/differential feedback law can be synthesized and rejected offline before closed-loop testing without hiding surrogate error in gain tuning?
- Q-0071 closed-positive @ R316, by CLM-0790 - What reduced-order plant surrogate and prospective residual envelope are sufficient before deterministic controller design?

## Methodology

### Scientific object and exact timing

- Restore the sealed R316 two-point order-10 retained-cross realizations and
  their 25-step Markov tensors. The known point label selects one controller;
  neither arm receives future disturbances or examination labels.
- For each realization define `z[k]=[x[k], y[k-1]]` with
  `A_z=[[A,0],[C,0]]`, `B_z=[[B],[D]]`, and delivered measurement
  `m[k]=[0,I]z[k]=y[k-1]`. The first measurement, estimate, and command are
  zero. This timing is identical in synthesis, pole checks, and simulation.
- At each step correct the predicted full-order estimate with the available
  delayed four-coordinate measurement, apply `u_raw=-K z_hat`, project through
  the unchanged node governor, and propagate the estimate with the executed
  action. The disturbance remains unmeasured.

### Single construction with no tuning grid

- Derive one output scale per point and coordinate from the retained model's
  zero-control 32-case development bank. Use pooled RMS with a fixed five-
  percent global floor. Both arms use these same scales.
- Use `W_y=diag(scale_y^-2)`. Derive four action scales from the unchanged
  physical node-power ceiling and common-plus-incidence basis, and use
  `W_u=diag(scale_u^-2)`. Include the model feedthrough through the generalized
  output-energy cost; solve one discrete Riccati equation per point and arm.
- Use a fixed observer covariance construction: process covariance is the
  augmented input matrix driven by independent `0.05` coordinate-power
  deviations plus a `1e-12` trace-scaled identity floor; measurement covariance
  is one percent of the retained-model output scales. Solve one dual discrete
  Riccati equation. No weight, covariance, pole, gain, or matrix entry is
  selected from performance outcomes.
- Require controller and corrected-observer nominal pole radii no greater than
  `0.995`. A synthesis failure or non-finite gain is a valid NO-GO when source
  and execution guards remain valid.

### Matched cross-deleted arm

- The retained arm uses each unchanged R316 realization. For the comparator,
  zero only the Markov blocks from common input to differential outputs and
  differential inputs to common output, then apply the unchanged order-10,
  8-by-8 ERA and `0.995` pole-projection rule.
- Execute both controllers on the same full retained-cross plant realization.
  Both receive the same delayed four-coordinate output, known point label,
  executed action feedback, horizon, disturbances, mismatch transforms, and
  estimator initialization. Both emit the same four coordinate actions and
  use the same node mapping, ramp/power/SOC limits, and post-processing.
- The sole attributed factor is retaining versus deleting those transfer
  blocks in the controller/observer synthesis model. Different internal
  realization coordinates and resulting gains are deterministic consequences
  of that factor, not extra information or budget.

### Development and examination split

- Development contains both points, four coordinates, both signs, and the
  frozen impulse and triangle sequences: 32 cases per arm, 50 samples each.
  It checks synthesis, poles, finite output/estimate/action, governor
  feasibility, and finite normalized innovation energy. It selects nothing.
- Only if both arms pass development, run the unchanged 16 bipolar base cases
  under the five R317 mismatch transforms: 80 examination cases per arm. The
  full retained model remains the executed plant and mismatch labels are not
  delivered to the controller.
- Preserve the R317 node ramp `0.072`, node power `0.36`, SOC `[0.2,0.8]`,
  point initial SOC values, 50-step horizon, and two-percent practical floor.

### Comparison-identifiability gate

- Planned decision: `ALLOW` for the finite-bank effect of retaining the named
  transfer blocks in this one fixed observer-LQR construction. The arms share
  deployment information, action coordinates and feasible set, execution,
  cases, model order, synthesis count, tuning count of zero, and evaluation
  data budget.
- Identified estimand: examination output-energy value of the retained transfer
  blocks relative to the matched cross-deleted synthesis model, under the
  frozen reduced-model plant, governor, timing, and empirical mismatch bank.
- Stay out: controller-family superiority, causal value of decoupling as a
  class, physical closed-loop efficacy, robust stability, voltage/current
  safety, distributed execution or communication value, agent or MARL value,
  topology generalization, HIL, and deployment.

### EVAL rule

`EVAL-v2` is not run because R319 creates no physical trace bank. Feeding
synthetic reduced-model traces to that physical-trace diagnostic would be a
scope error. Public-interface tests, deterministic replay, create-only hashes,
and the formal classifier own software and evidence integrity.

## Gate

- `INVALID-OBSERVER-LQR`: any sealed source/hash, model shape, exact timing,
  case count, cross-deletion, matched-information/action/budget, deterministic
  replay, no-examination-on-development-failure, artifact, or no-EVAL guard
  fails. Interpret no controller metric.
- `OBSERVER-LQR-NO-GO`: execution is valid but either arm cannot synthesize
  finite gains; either nominal controller or corrected-observer pole exceeds
  `0.995`; any development or examination output, estimate, innovation, or
  action is non-finite; any governed trace violates node power/ramp/SOC; the
  retained arm fails to improve every examination case by at least two percent
  versus zero control; or it fails to improve both mean and worst examination
  energy by at least two percent versus the matched comparator.
- `OBSERVER-LQR-PASS`: every validity, synthesis, pole, estimation, constraint,
  absolute, and matched-comparison gate passes. Close Q-0074 and authorize only
  one separately sealed physical deterministic closed-loop question. R319
  itself authorizes no ANDES run, distributed implementation, reward, agent,
  or training.

No threshold, weight formula, covariance formula, case, mismatch transform,
comparison, or interpretation changes after the first R319 controller outcome
is computed.

## Asset protection contract

- Preserve R306--R318 artifacts and every source sealed by R316--R318. Do not
  edit the existing dynamic-reduction or static-feedback modules, runners,
  probes, tests, seals, or results.
- New assets are limited to the R319 plan/seal, one reusable pure observer-LQR
  module, one formal probe, one stable runner, focused tests, create-only
  machine results with sidecars, manifest/feed/claim/verdict/question and
  navigation reconciliation.
- Do not create or edit a physical trace. Do not run WSL ANDES. Do not edit
  another manuscript line.
- Keep the fixed conference title exactly unchanged. Its coordination,
  distributed-agent, and learning terms remain prospective.

## Cross-references

- Dynamic-model and mismatch authority: CLM-0790.
- Static-law rejection authority: CLM-0795.
- Cause-localization authority: CLM-0800.
- Active question: Q-0074.
