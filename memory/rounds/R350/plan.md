---
round: R350
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R350 plan - smooth convex residual-headroom analysis

**Opened**: 2026-08-06
**Driver**: Answer Q-0091 after R345-R349 failed numerically, without
mistaking solver status or an absolute-value kink for physical evidence.
**Parent**: CLM-0910; Q-0091; aborted R345/R346/R347/R348/R349

## TL;DR

Recompute all sixteen exposed R345 cases once with a prospectively frozen
smooth convex formulation, three fixed initializations, analytic derivatives,
and an independent first-order certificate. Preserve the R345 scientific
decision tree. This create-only round may authorize one later non-learning
physical residual probe, but never neural training, distributed runtime, or
EVAL.

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

**Lane**: evidence. R350 reads the protected R344 outcome bank and may advance
Q-0091, so the solver, decision logic, source closure, and one create-only
attempt are frozen before execution.

**Unchanged scientific contract**: use the exact R345 contract: R344/R341
inputs; sixteen paired scenarios and 32 complete records; 25 samples;
zero-common three-edge residual; optimistic response map; mismatch envelope;
physical limits; neighbour-local causal features; independent per-edge
standardized ordinary least squares; leave-one-scenario-out folds; projection;
both endpoints; 2% mean-improvement floor; one-sided 95% paired Student-t
bound; and every point/location/sign directionality gate. No scenario,
threshold, estimator, subgroup, or interpretation may change.

**Prospective numerical repair**:

1. Represent the common-coordinate absolute-value bound with one nonnegative
   epigraph value per sample and keep the differential endpoint as its exact
   convex quadratic inequality.
2. Solve the endpoint-only convex superset in edge actions normalized by the
   unchanged node-ramp scale, with analytic objective and constraint
   derivatives. Physical power, ramp, and state-of-charge limits are checked
   afterwards in original units, because any global superset optimum that is
   also physically feasible is a global optimum of the original subset.
3. Run exactly three predeclared starts: a smooth nonnegative two-slack
   feasibility stage, zero edge action, and the freshly recomputed R348
   candidate. Each uses SLSQP, 20,000 maximum iterations, function tolerance
   `1e-9`, original-unit feasibility tolerance `1e-8`, and an objective
   multiplied by the positive constant `1/sqrt(1e-8)` without changing its
   minimizer.
4. Reconstruct epigraph values from the returned common-coordinate magnitude
   and independently certify the smooth convex KKT conditions using analytic
   Jacobians, nonnegative least-squares multipliers, and active/optimality
   tolerance `sqrt(1e-8) = 1e-4`. Solver success is neither necessary nor
   sufficient.
5. Accept a start only when all values are finite, both endpoint targets and
   every physical bound pass in original units, and the independent
   certificate passes. Select the smallest physical edge-action norm among
   certified starts using a fixed deterministic tie rule. Zero accepted starts
   invalidates the entire analysis.

The implementation was developed before this evidence transition on one
public synthetic five-step small-scale regression. A terminal-only scratch
capacity check on the already exposed sixteen-case bank produced sixteen
certified physical-feasible selections using sixteen single-thread workers in
40.72 seconds. Those observations justify readiness and capacity only; they
are not R350 scientific results and cannot alter the frozen gate.

**Execution**: after tests, preflight, formal-entry rehearsal, and seal, write
one create-only attempt. Run sixteen oracle jobs and, only if every oracle job
has a certified selected start, sixteen unchanged neighbour-local projection
jobs in one reused sixteen-worker process pool. Persist a metadata-only oracle
diagnostic before any invalidity stop. A valid attempt writes analysis and
manifest with sidecars. No retry, overwrite, resizing, threshold edit, case
drop, alternate estimator, or source repair is allowed in R350.

## Formal launch contract

- `formal_entry`: `python scripts/run_r350_smooth_convex_residual.py analyse --expected-seal-sha256 <sha256>`
- `rehearsal_command`: `python scripts/run_r350_smooth_convex_residual.py rehearsal`
- `rehearsal_scope`: same formal-entry source/parent hashes, installed package,
  sixteen installed cases, exact three-start contract, and formal output
  absence; creates no attempt or result root
- `rehearsal_checks`: source closure, parent sidecars, plan identity, package
  import, case count/identity, native-thread environment, output absence
- `wsl_python_processes`: 0
- `windows_python_processes`: 17 maximum, including one launcher and sixteen
  process-pool workers
- `native_threads_per_process`: 1
- `capacity_evidence`: terminal-only scratch execution on this host completed
  sixteen three-start jobs with sixteen unique workers in 40.72 seconds
- `host_process_budget`: 32 single-thread Python processes
- `other_reserved_processes`: 0
- `binding_parallelism`: sixteen independent ready cases, hence sixteen workers
- `ETA`: about one minute; terminal-only hard observation envelope five minutes

**Execution readiness**: HOLD until source/tests, preflight, rehearsal, and
seal pass; then RUN-READY for exactly the formal entry above.

## Gate

Any source drift, integrity failure, missing case, non-finite value, zero
certified starts, original-unit physical violation, or certificate failure is
`ANALYSIS-INVALID` and has no scientific meaning. If and only if all sixteen
oracle selections pass, apply the unchanged R345 decision tree.
`RESIDUAL-PROBE-ELIGIBLE` requires every oracle physical-headroom guard plus
oracle and held-out neighbour-local passes for both endpoints under nominal,
mismatch-bounded, paired, and subgroup gates. It authorizes only one
separately sealed non-learning physical intervention. Every other valid branch
is `NO-TRAINING`. Neural training remains false in all R350 branches.

## Asset protection contract

R341/R344/R345/R346/R347/R348/R349 sources, seals, attempts, failures,
diagnostics, traces, manifests, thresholds, controller, and paper evidence
remain byte-unchanged. Add only R350 plan, reusable solver/certificate
extension, probe, adapter, tests, rehearsal, seal, create-only results, and, if
scientifically valid, feed, claim/question disposition, verdict, and selected
manuscript-line navigation reconciliation. No public push.

## Cross-references

- CLM-0910
- Q-0091
- R345/R347/R348/R349 `ANALYSIS-INVALID`
- R346 `RELAXATION-INVALID`
