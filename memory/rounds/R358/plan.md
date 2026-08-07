---
round: R358
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R358 plan - normalized quadratic physical-feasibility recovery

**Opened**: 2026-08-07
**Driver**: Recover Q-0095 after the sealed R357 cone solver failed
numerically before producing a physical decision.
**Parent**: Q-0095; CLM-0930; CLM-0935; R356; invalid R357 attempt

## TL;DR

Workload: `evidence`. Preserve R357 byte-for-byte. Inherit the six accepted
R356 relaxed-infeasibility certificates by monotonicity, then independently
solve only the ten relaxed-optimal candidates as normalized convex quadratic
programs under the unchanged common target and exact three-edge physical
limits. Read no holdout and run no simulator or training.

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0095 [opened R357] Do any exposed R356 candidates retain the unchanged joint target under the exact three-edge physical limits?

## Recently Closed (last 3)

- Q-0094 closed-negative @ R356, by CLM-0930 — Does the matched neighbour-local deterministic baseline leave material, neighbour-observable, and physically feasible residual headroom?
- Q-0093 closed-positive @ R352, by CLM-0925 — Does a tuned endpoint-local three-edge deterministic controller retain differential-synchronization value on an untouched disturbance-shape bank?
- Q-0092 closed-positive @ R351, by CLM-0920 — Can one deterministic three-edge controller execute from endpoint-only neighbour information through the future policy's exact physical governor?

## Methodology

### Frozen study object

- exactly the sixteen exposed R356 development cases and their unchanged
  identities, with six accepted relaxed-infeasible controls and ten
  relaxed-optimal candidates;
- the unchanged two-percent common- and differential-endpoint targets,
  twenty-five samples, three edge actions, base and previous node commands,
  node-power, node-ramp, energy, efficiency, and state-of-charge limits;
- zero holdout reads, zero new trajectories, zero ANDES, zero training, and
  zero distributed runtime.

The implementation canary has already exercised the exposed candidates while
diagnosing R357. Its outcomes are development-only, create no claim, and are
not treated as prospectively unseen. The formal run is a source-bound,
create-only reproducibility and certification pass over this exposed finite
set.

### Inherited negative controls

R356's six accepted relaxed primal-infeasibility certificates are sufficient
negative controls: adding physical constraints cannot restore feasibility to
a problem already infeasible after those constraints were removed. Verify the
complete R356 source, certificate, identity, and sidecar closure; do not solve
those six cases again or reinterpret their result.

### Normalized quadratic candidate problem

For each of the ten candidates, keep the common-coordinate absolute-error
epigraph and all node-power and node-ramp inequalities. Minimize the
differential squared-error ratio directly. This is equivalent to asking
whether its globally minimal value is at most `0.98`, but avoids R357's
ill-scaled second-order-cone interior update.

CVXOPT 1.3.3 runs serially with absolute, relative, and feasibility tolerances
`1e-10`, maximum iterations `200`, and acceptance tolerance `1e-8`. An
accepted positive case requires an optimal status, finite diagnostics, a
reconstructed witness within both endpoint and every physical bound, and
agreement between the solver objective and direct reconstruction. An accepted
negative case requires the same diagnostics plus a verified dual lower bound
strictly above the target. Any solver exception, unknown exit, ambiguous
target interval, reconstruction failure, or source drift fails closed.

State-of-charge rows remain omitted only when the frozen worst-path bound is
within the initial margin, followed by exact piecewise efficiency
reconstruction of every returned optimum.

### Authorized implementation

- keep `probes/physical_joint_endpoint_qp.py` as the reusable conclusion-
  affecting seam and keep its regression tests under `tests/`;
- add one stable create-only R358 adapter and focused execution-boundary tests;
- bind the complete implementation, package, R356 closure, and immutable R357
  failure closure into rehearsal and seal;
- do not modify an R357 source, artifact, threshold, result, feed, claim, or
  verdict.

## Outcomes

- `PHYSICAL-HEADROOM-FOUND`: every inherited control and candidate decision is
  accepted and at least one candidate has a verified physical witness. This
  closes Q-0095 only for the exposed finite linear-response cases and permits
  one separately registered neighbour-observability design question.
- `NO-PHYSICAL-HEADROOM`: all six inherited controls and all ten candidates
  have accepted infeasibility support. Stop the unchanged two-percent route.
- `ANALYSIS-INVALID`: any parent/source/identity drift, missing case, solver
  exception, unaccepted exit, ambiguous bound, or failed reconstruction.
  Preserve outputs and do not retry.

No branch authorizes holdout reading, nonlinear physical execution, ANDES,
neural training, distributed runtime, EVAL, target reduction, stability,
safety, topology, deployment, or paper-title validation.

## Formal launch contract

- `formal_entry`: `python scripts/run_r358_physical_joint_endpoint_qp.py analyse --expected-seal-sha256 <sha256>`.
- `rehearsal_command`: `python scripts/run_r358_physical_joint_endpoint_qp.py rehearsal`.
- `rehearsal_scope`: execute the formal pre-attempt verification path over
  all frozen parents, sources, installed solver, exact case identities,
  inherited proof closure, state-of-charge bounds, synthetic feasible and
  dual-infeasible examples, and the minimized R357 numerical regression,
  without solving the complete ten-case bank or creating a formal result.
- `rehearsal_checks`: sixteen identities; six inherited negative controls;
  ten candidate identities; zero holdout; accepted synthetic positive and
  negative decisions; minimized four-step regression returns accepted;
  source/parent equality; formal output absence; no ANDES or training.
- `worker_processes`: 1; `native_threads_per_process`: 1;
  `wsl_python_processes`: 0; execution is serial and create-only.
- `capacity_evidence`: the scratch ten-candidate quadratic canary completed in
  less than one minute in one Windows process; no long-horizon or physical
  workload exists in this gate.
- `host_process_budget`: one Windows Python process;
  `other_reserved_processes_at_plan`: zero. A conflicting formal process or
  missing dependency returns `HOLD` before seal.
- completion is one create-only `analysis.json` plus `manifest.json` and
  sidecars, or one create-only `failure.json` plus sidecar; retry is forbidden.

## Asset protection contract

R356 and R357 plans, rehearsals, seals, attempts, results, feeds, claims,
verdicts, sources, thresholds, and manifests remain byte-unchanged. In
particular, freeze the R357 plan `c099f45e...74573`, rehearsal
`ca4bcc0e...0c7`, seal `26b8babc...d758c`, attempt `58889a70...a5ad`,
failure `933ea85c...77fb`, verdict `2216ce3a...6f62`, feed
`ef21ab20...b71ae`, and claim `3a121635...dbe3`. Add only the generic
quadratic seam and tests, R358 adapter/tests, rehearsal, seal, formal result,
and required closeout artifacts. Do not edit another manuscript line or push
publicly.

## Cross-references

- Q-0095
- CLM-0930
- CLM-0935
- R356 relaxed feasibility decision
- R357 invalid formal attempt
