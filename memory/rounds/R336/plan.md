---
round: R336
state: completed
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R336 plan - pre-execution verifier repair and unchanged package execution

## TL;DR

Answer Q-0086 with the already frozen R335 four-channel physical disturbance
package. Preserve every scientific choice, operating point, physical channel,
waveform, threshold, ordering rule, classifier, controller exclusion, and stop
condition. Repair only the installed-case verifier that stopped R335 before a
formal attempt existed, then re-seal and execute once.

## Authority and workload

- Workload: `evidence`. R336 will create the physical trajectories that R335
  did not start.
- Direct question: `memory/questions/Q-0086.md`.
- Failure authority: `memory/rounds/R335/pre_execution_failure.md` and the R335
  sealed contract. The failure was a missing dictionary member in pre-run
  verification, not a scientific result.
- Scientific authority and frozen design: the complete methodology, bank,
  identification, gates, outcome tree, exclusions, and stopping conditions in
  the R335 seal. The conference title remains byte-for-byte unchanged.
- Research Supervisor route and Ask Matt work order remain the R335 route: one
  package-adequacy question, pure decision seam, test-first repair, no
  literature branch, controller, training, or manuscript drafting.

## Methodology

Use a thin successor adapter. It imports the sealed R335 implementation,
changes only round/event/output identity to R336, includes itself and its tests
in source closure, and replaces the faulty installed-runtime verifier with the
already audited R334 official-case lookup plus hash check. It does not alter
the physical runner, parallel record executor, fitting code, analysis code, or
classification logic.

## Frozen scientific contract

- Points remain HS0 development and untouched HS1 holdout with device M/D
  `177.5/88.75` and `202.5/101.25`, tie R/X scales `1.10/1.35`, initial SOC
  `0.41/0.51`, 0.2-second periods, five subdivisions, and 25 recorded periods.
- Channels remain exactly `PQ_0@Bus7`, `PQ_1@Bus8`, `PQ_Bus14@Bus14`, and
  `PQ_Bus15@Bus15`, with common P/Q baselines `11.59/-0.735`, `15.75/-0.899`,
  `2.48/0.0`, and `0.05/0.0` system p.u.
- Bank remains one zero plus four channels times two signs times two waveforms
  per point: 34 records total. Profiles remain `impulse=[0.05]` and
  `triangle=[0.02,0.04,0.05,0.04,0.02]`, with exact baseline restoration.
- HS0 still fits one unregularized fully cross-coupled four-by-four coordinate
  map jointly across both waveforms and signs. Persist and hash that fit before
  starting HS1; apply it unchanged to HS1.
- Four isolated records may run concurrently inside one split with native
  numerical-library threads fixed to one. Registered record order is
  deterministic. HS0, persisted fit, and HS1 remain strictly serial.

## Frozen gates and outcomes

- Validity gates remain: exact source/parent/identity/inventory/order/reward
  boundaries; readback/restore within `1e-12`; zero actuator power and
  residual thresholds `1e-6`; signal-to-drift at least `10`; signed midpoint
  at most `0.10`; NRMSE at most `0.15`; peak vector residual at most `0.20`;
  node-column sum `-1 +/- 0.20`; rank four; smallest/largest singular ratio at
  least `0.10`; deterministic two-pass analysis.
- Outcomes remain exactly `INVALID-PHYSICAL-DISTURBANCE-PACKAGE`, `BLOCK`,
  `QUALIFY`, and `ALLOW`, with the meanings frozen in R335.
- No reward enters action, fitting, selection, training, classification, or a
  claim. No controller, closed loop, distributed runtime, training, EVAL,
  topology change, stability/safety claim, or title-result claim is allowed.

## Verification and stopping conditions

- Test first that the successor uses R336 identity, retains the 34-record
  contract and title boundary, binds the official case through the R334
  verifier, includes successor sources, and leaves scientific logic imported
  rather than copied or changed.
- Run focused and inherited regression tests, lint, compilation, source
  closure, preflight, and a direct WSL runtime-verifier check. Then create a new
  seal. Formal outputs are create-only; the attempt marker precedes any
  trajectory; interruption or post-attempt failure forbids retry.
- Execute the bank exactly once, analyse twice deterministically, then run the
  independent evidence and power-system audits before any claim registration.
- Stop after the package judgment. Even `ALLOW` authorizes only a separately
  sealed deterministic physical-bridge question.

## Cross-references

- Direct question: `memory/questions/Q-0086.md`.
- Pre-execution failure: `memory/rounds/R335/pre_execution_failure.md`.
- Frozen predecessor seal:
  `memory/rounds/R335/disturbance_package_seal.json`.
- Narrow physical parent: `memory/claims/CLM-0880.md`.
- Immutable dynamic-model parent: `memory/claims/CLM-0790.md`.
