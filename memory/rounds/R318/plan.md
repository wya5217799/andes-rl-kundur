---
round: R318
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R318 plan - frozen scalar-grid rejection diagnosis

**Opened**: 2026-08-03
**Driver**: answer Q-0073 by decomposing R317's infeasible selections before
defining one controller-form repair.
**Parent**: CLM-0790; CLM-0795; Q-0073.

## TL;DR

Replay the already sealed R317 100-scalar grid for both arms without widening,
tuning, or running a new performance examination. Record each candidate's
maximum augmented pole radius; run the unchanged governed 32-case development
calculation only for candidates that meet the original `0.995` pole ceiling.
Classify pole-only, governor-only, mixed, conflict, or invalid rejection. Then
specify exactly one cause-matched controller-form repair for a future round.
Run no ANDES, EVAL, physical closed loop, distributed runtime, reward, agent,
or training work.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete - re-run render.py only after the round closes. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0073 [opened R317] Which frozen scalar candidates were rejected by the nominal augmented-pole gate versus the governed development traces, and can one analytically preconditioned timing or controller-form repair be defined without widening the outcome-seen grid?

## Recently Closed (last 3)

- Q-0072 closed-negative @ R317, by CLM-0795 - What constrained common/differential feedback law can be synthesized and rejected offline before closed-loop testing without hiding surrogate error in gain tuning?
- Q-0071 closed-positive @ R316, by CLM-0790 - What reduced-order plant surrogate and prospective residual envelope are sufficient before deterministic controller design?
- Q-0070 closed-positive @ R314, by CLM-0780 - Can one local/simplex predictor using R313 HP1 only as an added development operating point meet the unchanged response bounds on a newly sealed untouched operating-condition bank?

## Methodology

### Immutable replay authority

- Verify the R317 seal, controller result, analysis, provenance, plan, controller
  module, and parent R316 dynamic model by their existing sidecars and sealed
  hashes. R317 must remain `OFFLINE-CONTROLLER-NO-GO`, both arms must remain
  selection-infeasible, and its validity guards must remain all true.
- Restore the exact R317 averaged-DC inverse base gains and exact scalar list
  `{0.01, 0.02, ..., 1.00}`. Recompute the gain family from R316 only as an
  identity check; any difference is INVALID.
- Reuse the exact one-sample augmented pole equation, two models, 32 development
  cases, node governor, SOC update, limits, horizon, and first-zero-command
  timing. No bipolar or mismatch examination case is loaded.

### Candidate-level decomposition

- For each arm and scalar, record the maximum pole radius across `HS0` and
  `HS1` and `pole_pass = radius <= 0.995`.
- Only when `pole_pass` is true, run the unchanged 32 development cases and
  record finite output, governor interventions, node power/ramp/SOC extrema,
  and constraint violations. Record `governor_pass` only when every case is
  finite and violation-free.
- Do not calculate output-energy rankings, select another scalar, widen the
  grid, change a threshold, or run the conditional R317 examination.

### Cause-matched repair mapping

- Pole-only rejection: specify one future full-order observer-based discrete-
  time quadratic regulator synthesized directly on the one-sample-delay-
  augmented realization. It must preserve common/differential coordinates,
  full cross blocks, the physical node governor, and the same model authority;
  no zero-frequency inverse or scalar grid is reused.
- Governor-only rejection: specify one future constrained receding-horizon
  formulation on the same delayed model and unchanged physical limits. No
  limit relaxation or extra actuator authority is permitted.
- Mixed rejection: choose the pole-directed augmented controller first because
  a constraint repair cannot make a nominally unstable law admissible.
- Diagnostic conflict: if any candidate passes both gates, stop and repair the
  R317 selection implementation before any new controller form.

### Comparison and EVAL boundary

- This is a cause audit of two already rejected arms, not an efficacy
  comparison. Any arm contrast is descriptive and `QUALIFY`; no cross-feedback
  value is estimated.
- `EVAL-v2` is not applicable because no physical trace exists. Focused public-
  interface tests, deterministic replay, sidecars, and the formal diagnostic
  classifier own integrity.

## Gate

- `INVALID-REJECTION-DIAGNOSIS`: any sealed hash, identity, gain reconstruction,
  candidate count, deterministic replay, case contract, or no-EVAL guard fails.
- `DIAGNOSTIC-CONFLICT`: at least one frozen candidate passes both the pole and
  governed-development gates, contradicting R317's infeasible selection.
- `POLE-ONLY-REJECTION`: neither arm has a pole-feasible scalar. Close Q-0073
  with the augmented observer-based regulator as the sole eligible repair.
- `GOVERNOR-ONLY-REJECTION`: at least one scalar is pole-feasible in each arm,
  none passes the governor, and every rejection is attributable to declared
  node power/ramp/SOC or non-finite development behavior. Close Q-0073 with
  the constrained receding-horizon form as the sole eligible repair.
- `MIXED-REJECTION`: pole and governed-development causes coexist across arms
  or candidates, with no fully feasible scalar. Close Q-0073 and make only the
  augmented observer-based regulator eligible first.

Every non-invalid, non-conflict outcome remains model-only and authorizes only
one separately registered offline repair-design question. No physical or
learning gate is opened.

## Asset protection contract

- Preserve R306--R317 artifacts, especially every source sealed by R317. Do not
  edit the R317 controller module, runner, probe, tests, seal, or results.
- New assets are limited to the R318 plan/seal, one pure diagnostic probe, one
  stable runner, focused tests, create-only machine results with sidecars,
  manifest/feed/claim/verdict/question/navigation reconciliation.
- Keep the fixed conference title exactly unchanged. Its coordination,
  distributed-agent, and learning terms remain prospective.

## Cross-references

- Dynamic-model authority: CLM-0790.
- Rejected controller authority: CLM-0795.
- Active question: Q-0073.
