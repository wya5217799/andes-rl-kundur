---
round: R317
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R317 plan - offline cross-feedback synthesis gate

**Opened**: 2026-08-03
**Driver**: answer Q-0072 with one model-only controller synthesis and
rejection gate before any new physical closed-loop execution.
**Parent**: CLM-0790; Q-0072.

## TL;DR

Use the frozen R316 order-10 two-point realizations as development authority.
Synthesize one delayed static common/differential output-feedback law from the
averaged zero-frequency gain and compare it with the exact same construction
after deleting only common-to-differential and differential-to-common feedback
blocks. Freeze a one-scalar search, disturbance split, node-power governor,
finite empirical-mismatch stress, pole and performance gates before computing
any outcome. Stop at offline PASS, NO-GO, or INVALID. Run no ANDES, EVAL,
distributed runtime, reward, agent, or training work.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete - re-run render.py if a refreshed programme view is needed. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0072 [opened R316] What constrained common/differential feedback law can be synthesized and rejected offline before closed-loop testing without hiding surrogate error in gain tuning?

## Recently Closed (last 3)

- Q-0071 closed-positive @ R316, by CLM-0790 - What reduced-order plant surrogate and prospective residual envelope are sufficient before deterministic controller design?
- Q-0070 closed-positive @ R314, by CLM-0780 - Can one local/simplex predictor using R313 HP1 only as an added development operating point meet the unchanged response bounds on a newly sealed untouched operating-condition bank?
- Q-0069 closed-negative @ R313, by CLM-0775 - Can a coupling-retaining predictor fitted only on the valid R312 bank predict separately sealed unseen pulse amplitudes and operating conditions within prospective common/differential error bounds?

## Methodology

### Scientific object and causal timing

- Restore the unchanged R316 `HS0` and `HS1` order-10 realizations. They map
  four active-power coordinates (`common`, `edge_0`, `edge_1`, `edge_2`) to
  four inertia-weighted frequency coordinates at `0.2 s` sampling.
- Interpret the registered input shapes as matched-channel exogenous
  small-signal power disturbances. This is an offline regulator surrogate,
  not a physical load-path or robustness claim.
- Use the one-sample causal law `u[k] = -alpha K y[k-1]`. The first command is
  zero. No current output, future disturbance, physical holdout outcome, or
  joint neural information enters the law.
- Analyze unsaturated nominal poles with the exact augmented realization
  `[A, -B alpha K; C, -D alpha K]`. Simulations use the same delayed
  observation and the fixed governor below.

### Frozen synthesis and equal budget

- For each point compute `G0 = C (I-A)^-1 B + D`; reject as INVALID if a
  finite inverse cannot be formed or the averaged `G0` condition number
  exceeds `1e6`.
- The retained-cross base gain is the inverse of the equally weighted average
  `G0`. The matched baseline is the same matrix with only rows/columns between
  the common coordinate and the three differential coordinates set to zero;
  differential-to-differential terms remain unchanged.
- Each arm searches the same 100 scalar multipliers
  `alpha in {0.01, 0.02, ..., 1.00}`. The selected scalar is the feasible
  candidate minimizing worst-case normalized output energy, with mean
  normalized output energy as the first tie-break and smaller `alpha` as the
  second. No matrix entry is otherwise tuned.
- Development cases are both points, all four coordinates, both signs, and
  the registered impulse and triangle sequences. Each case runs for 50
  samples. The bipolar sequence and every mismatch-stressed case are hidden
  from scalar selection and used only by the locked offline examination.

### Fixed actuator and energy governor

- Convert coordinate requests to the four physical node requests with the
  frozen common-plus-tree incidence basis. At every sample apply the
  executable order: node ramp bound `0.072` system p.u., then node power bound
  `0.36` system p.u. Convert the projected node vector back to coordinates.
- Track four SOC states from the executed node power with `100 MVA`, `28 MWh`,
  `0.2 s`, `eta_C=eta_D=0.9848857802`, and the point's frozen initial SOC.
  Every state must remain in `[0.2, 0.8]`.
- The two arms have identical inputs, four-dimensional actions, node map,
  limits, timing, horizon, cases, tuning count, and objective. Both receive
  all four delayed coordinates; the baseline's deleted blocks are a frozen
  controller-structure restriction, not an information-delivery difference.

### Frozen mismatch examination

- Use the R316 empirical envelope only as a finite additive output stress, not
  as a stochastic uncertainty set or robust-stability certificate.
- For every bipolar case apply five locked examination modes: zero mismatch;
  `+0.15 y`; `-0.15 y`; a `0.15` signed coordinate reflection; and a `0.15`
  common/differential coordinate exchange. The transforms have unit spectral
  norm, so the injected sequence respects the registered total-response
  `0.15` envelope and the `0.20` pointwise ceiling.
- Performance is measured on the stressed output. The controller has no
  access to the mismatch label or future samples.

### Comparison-identifiability gate

- Planned decision: `ALLOW` for the narrow contrast between these two frozen
  one-scalar delayed-feedback constructions. The single load-bearing
  difference is retaining versus deleting common/differential feedback blocks.
- Identified estimand: finite-bank output-energy value of those feedback blocks
  under the same full retained-cross plant models, governor, tuning budget,
  disturbances, and mismatch transforms.
- Stay out: all-controller-family superiority, robust MPC or DAPI value,
  physical closed-loop efficacy, recursive feasibility, voltage/current
  safety, decentralized execution, communication, agent or MARL value,
  topology generalization, deployment, and robust-stability certification.

### EVAL rule

`EVAL-v2` is not run: R317 creates no physical trace bank, and presenting
synthetic state-space traces to the physical-trace diagnostic would be a scope
error. Public-interface unit tests, deterministic replay, artifact hashes,
and the formal probe own software and evidence integrity for this round.

## Gate

- `INVALID-OFFLINE-CONTROLLER`: any source identity/hash, matrix shape,
  invertibility, deterministic replay, case-count, governor, artifact, or
  comparison-contract guard fails. Interpret no controller metric; permit
  only one cause-specific implementation repair.
- `OFFLINE-CONTROLLER-NO-GO`: execution is valid but either arm has no feasible
  scalar, any selected nominal augmented pole radius exceeds `0.995`, any
  examination case is non-finite or violates node power/ramp/SOC, the retained
  arm fails to reduce every examination case's output energy by at least `2%`
  relative to zero control, or it fails to reduce both mean and worst-case
  examination energy by at least `2%` relative to the matched baseline.
  - Pole failure: open one bounded controller-form/timing diagnosis; do not
    widen the scalar grid after seeing the result.
  - Constraint failure: open one governor/feasibility diagnosis; do not relax a
    physical limit.
  - Absolute performance failure: reject this static law before ANDES.
  - Matched-comparison failure: reject the cross-feedback value claim for this
    law; do not generalize to decoupling as a class.
- `OFFLINE-CONTROLLER-PASS`: all validity, pole, constraint, absolute, and
  matched-comparison gates pass. Close Q-0072 and authorize only a separately
  sealed physical deterministic closed-loop bank. R317 itself authorizes no
  ANDES control run, distributed runtime, reward, agent, or training.

The `2%` floor is the manuscript line's already declared minimum practical
improvement floor. No threshold, grid, case, mismatch transform, comparison,
or interpretation changes after the first R317 controller outcome is computed.

## Asset protection contract

- Preserve R306--R316 artifacts, all paper-cited plant/runtime assets, the
  model-first environment, and the sealed R316 runner and validator.
- New assets are limited to the R317 plan/seal, one reusable pure controller
  module, one formal probe, one stable runner, focused tests, create-only
  machine results with sidecars, feed, claim, verdict, question/navigation
  reconciliation, and manifest entry.
- Do not create or edit a physical trace. Do not run WSL ANDES. Do not edit
  another manuscript line.
- Keep the working title exactly `Decoupling-Oriented Coordination of
  Paralleled VSGs With Multi-Agent Reinforcement Learning`; its coordination
  and learning terms remain prospective.

## Cross-references

- Dynamic-model and mismatch authority: CLM-0790.
- Active question: Q-0072.
- Manuscript contract: `paper/decoupling_marl_model_first/working/model_contract.md`.
