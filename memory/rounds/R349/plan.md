---
round: R349
state: aborted
manuscript_line: decoupling-marl-model-first
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed analysis invalid: only six of sixteen oracle candidates passed the independent certificate; six were dimensionless-constraint-infeasible and four failed stationarity; retry forbidden'
superseded_note: null
---
# R349 plan - independently certified residual-headroom analysis

**Opened**: 2026-08-06
**Driver**: Answer Q-0091 without treating an SLSQP status flag as a proof of
minimum-norm optimality after R348 returned finite feasible candidates without
solver success certificates.
**Parent**: CLM-0910; Q-0091; aborted R345/R346/R347/R348

## TL;DR

Run the unchanged R348 fully normalized analysis once under a fresh seal, but
require an independent first-order certificate for every minimum-norm
candidate, regardless of the SLSQP status flag. The certificate is validated
only on analytic scratch problems before sealing. It cannot change a
candidate, threshold, case, estimator, or scientific gate. No simulator,
reward, policy, EVAL, distributed runtime, or neural training is allowed.

## Snapshot at plan-time (oracle as of 2026-08-06)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete - re-run render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0091 [opened R344] Does the frozen deterministic bridge leave material, observable, and physically usable residual headroom before neural training?

## Recently Closed (last 3)

- Q-0090 closed-positive @ R344, by CLM-0910 - Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?
- Q-0089 closed-positive @ R341, by CLM-0900 - Does the selected predictor preserve its registered waveform envelope on an untouched operating-point bank?
- Q-0087 closed-partial @ R339, by CLM-0890 - Which location-dependent input dynamics explain the upstream-load mismatch before any bridge repair?

## Methodology

**Lane**: evidence. R349 reads the protected R344 outcome bank and may dispose
Q-0091, so it owns one prospective create-only attempt and the complete
publication lifecycle only if the analysis is scientifically valid.

**Frozen parent chain**:

- R345 scientific contract payload SHA-256
  `6492c9a8b087eabcd41222b3bb246c167936e1e82f8de33b5de3a6daf41fd1ab`;
- R348 seal SHA-256
  `b95b75b97c82b2f04a0d356fc2b6771456e86f029deaf405e33ec8575fe24601`;
- R348 attempt SHA-256
  `9bc9718800fdc9c83ba60014536d4b50e3ce5ea82d75d8452f091ee6a9bb27bc`;
- R348 metadata-only oracle diagnostic SHA-256
  `6ffa94ed85d878805018f7ea9a947102ed96df2de46d276a627c4680a0167dc7`;
- R348 failure SHA-256
  `1bba71c77f6cc64da06077f572bd125a4322e37d61ac7d18a4ebb97791dec00f`.

R348 per-case solver status, feasibility residual, and iteration fields
authorize only the independent certificate below. They cannot change a
threshold, case, estimator, subgroup, or scientific interpretation.

**Unchanged science and numerics**: use exactly the R345 scientific contract
and R348 numerical formulation: the same R344/R341 frozen inputs, sixteen
paired scenarios, 32 complete records, 25 samples, zero-common three-edge
residual, optimistic response map, mismatch envelope, physical limits,
neighbour-local causal features, independent per-edge standardized ordinary
least squares, leave-one-scenario-out folds, projection, endpoints, 2% mean
improvement floor, one-sided 95% paired Student-t bound, and all registered
point/location/sign directionality gates. Preserve R347 relative feasibility
slacks and every R348 normalization, initial point, iteration budget,
function tolerance, original-unit `1e-8` feasibility check, and SLSQP call.
Include every scenario. R349 adds no candidate or tuning parameter.

**Single acceptance repair**: every returned minimum-norm candidate must be
finite and feasible in original units and must pass a solver-status-independent
certificate for `min ||z||_2^2` under dimensionless constraints `g(z) >= 0`.
The certificate:

1. sets both the active-set and optimality tolerances to
   `sqrt(1e-8) = 1e-4`, derived prospectively from the unchanged feasibility
   tolerance rather than an R348 value;
2. estimates the active-constraint Jacobian by central differences with step
   `cbrt(machine_epsilon) * max(1, abs(z_i))`;
3. obtains nonnegative multipliers from nonnegative least squares and requires
   the scale-normalized stationarity residual and complementarity residual to
   be at most `1e-4`;
4. applies the optimality certificate only to the convex endpoint, node-power,
   node-ramp, and lower-state-of-charge feasible-set constraints; every
   upper-state-of-charge constraint, which is not used in the convex
   sufficiency argument, must remain feasible in original units and strictly
   inactive by more than `1e-4` after dimensionless scaling;
5. accepts a candidate only when this independent certificate passes,
   regardless of whether SLSQP reports success or failure.

This is an acceptance certificate, not a second optimizer. It may not alter,
polish, restart, or replace the returned candidate. Before sealing, analytic
scratch tests must accept exact one- and multi-dimensional half-space
projections across fixed scales, an exact nonlinear convex-ball projection,
and duplicated active constraints; they must reject infeasible points,
feasible non-minima, complementarity failures, active nonconvex guards, and
invalid inputs.

**Execution**: implementation/tests precede the seal. Write one create-only
attempt, execute sixteen oracle jobs and sixteen local projection jobs with at
most sixteen single-thread Windows workers in one reused process pool, and
persist a metadata-only oracle diagnostic before any invalidity stop. A valid
attempt writes analysis and manifest sidecars. There is no retry, overwrite,
resizing, threshold edit, case drop, alternate estimator, or further repair in
R349.

**Execution readiness**: RUN-READY after source, test, preflight, and seal
checks pass. The host has valid measured capacity for 32 single-thread
processes; R349 has only sixteen ready jobs and no other manuscript execution
reservation, so sixteen workers is the binding useful maximum. Allow a
five-minute terminal-only observation envelope; do not tune from intermediate
outcomes.

**Engineering seam**: public independent certificate plus R349 probe and
adapter `prepare`/`analyse`. Tests freeze analytic certificate behavior,
unchanged nested scientific contract, source closure, create-only persistence,
sixteen-worker budget, terminal-only artifacts, and absence of
simulation/training/EVAL/reward/distributed commands.

## Gate

Any non-finite value, original-unit constraint violation, active nonconvex
guard, certificate failure, source drift, or integrity failure is
`ANALYSIS-INVALID` and has no scientific meaning. If and only if all sixteen
oracle candidates are independently certified, use the exact R345/R348
decision tree. `RESIDUAL-PROBE-ELIGIBLE` still requires every oracle physical
headroom guard plus oracle and held-out local passes for both endpoints under
nominal, mismatch-bounded, paired, and subgroup gates; it authorizes only one
separately sealed non-learning physical probe. Otherwise return `NO-TRAINING`
with the failed gates. Neural training, distributed runtime, and EVAL remain
false in every branch.

## 资产保护契约

R341/R344/R345/R346/R347/R348 sources, seals, attempts, failures,
diagnostics, traces, manifests, thresholds, controller, and paper evidence
remain byte-unchanged. Add only R349 plan/probe/adapter/tests, seal,
create-only results, and, if scientifically valid, feed, claim/question
disposition, verdict, and manuscript navigation reconciliation. No public
push.

## Cross-references

- CLM-0910
- Q-0091
- R345/R347/R348 `ANALYSIS-INVALID`
- R346 `RELAXATION-INVALID`
