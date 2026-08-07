---
round: R356
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R356 plan - independent joint-target feasibility diagnosis

**Opened**: 2026-08-07
**Driver**: Decide whether the terminal R355 `ANALYSIS-INVALID` hides a valid
scientific no-headroom result because a truly infeasible joint endpoint target
was treated as an oracle-integrity failure.
**Parent**: Q-0094; terminal R355; R352 development pairs; R341 point models

## TL;DR

Freeze one independent second-order-cone feasibility diagnosis on the sixteen
already exposed R355 development cases. Keep the R355 two-percent joint target,
case identities, response models, information boundary, and all parent data
unchanged. Remove physical action constraints only for this diagnosis, creating
a strict superset of the original feasible set: if even that relaxed problem
is independently certified infeasible for one case, the registered residual
target cannot support training. Do not read holdout, lower the target, rerun
R355, train, or simulate.

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete - re-run render.py if navigation needs refreshing. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0094 [opened R353] Does the matched neighbour-local deterministic baseline leave material, neighbour-observable, and physically feasible residual headroom?

## Recently Closed (last 3)

- Q-0093 closed-positive @ R352, by CLM-0925 - Does a tuned endpoint-local three-edge deterministic controller retain differential-synchronization value on an untouched disturbance-shape bank?
- Q-0092 closed-positive @ R351, by CLM-0920 - Can one deterministic three-edge controller execute from endpoint-only neighbour information through the future policy's exact physical governor?
- Q-0091 closed-negative @ R350, by CLM-0915 - Does the frozen deterministic bridge leave material, observable, and physically usable residual headroom before neural training?

## Methodology

**Lane**: evidence. R356 changes formal result classification and may close
Q-0094. It creates no new physical trajectory and uses no holdout or training.

### Frozen parent chain

- closed R355 plan SHA-256:
  `6c2e2980ca47f687e92750cce20cfbea693567b77afee279af5be434e5c362ae`;
- R355 rehearsal SHA-256:
  `6e9e2afefe3d779a9e1b4b5589cc9fb6c07f12e6c3473ea738a28e4661637f3c`;
- R355 seal SHA-256:
  `bc70a3287a2fa29657af0963a3be2f53733517581c89dd23d8ba3ec35a59d97d`;
- R355 attempt SHA-256:
  `049ffd31e24c30f31e20ab19271136bd966f630a42f0a45291af28101e737dcd`;
- R355 analysis SHA-256:
  `66f1d797fe0cdd40724afef396df35866ed4570019bf3860bd7ab9c87f5edc24`;
- R355 manifest SHA-256:
  `7642965a16f9207aff274f0d7e2b5179618d4ff61dac2148aa4abfdd8b1d1647`;
- R355 adapter SHA-256:
  `dd9fe7cf84f50d9258d275e9087692581c2a2cb0976e6c7b6773b0323fcb1e18`.

R355 validly executed its frozen analysis but returned `ANALYSIS-INVALID`
because seven development cases had no certified fixed start. Its holdout was
not read and training was false. R356 does not reinterpret R355 as valid; it
answers a separately frozen diagnostic question.

### Independent feasibility object

For each of the same sixteen development cases, use the R341 linear response
map and solve only the two unchanged endpoint requirements:

- common-coordinate absolute-error sum no greater than 98 percent of baseline;
- differential-coordinate squared-error sum no greater than 98 percent of
  baseline.

Represent the common absolute value with an epigraph and the differential
quadratic bound as a second-order cone. Edge actions remain the same three
independent coordinates over the same twenty-five steps. Omit power, ramp,
state-of-charge, estimator, and neighbour-information restrictions. This
strictly relaxes the original action problem; infeasibility here implies
infeasibility in the original physically constrained problem, while feasibility
here does not establish physical feasibility or residual headroom.

Use CVXOPT 1.3.3 `socp`, serially, with absolute, relative, and feasibility
tolerances `1e-10` and maximum iterations 100. A primal-infeasible status is
accepted only when its infeasibility-certificate residual is finite and no
greater than `1e-8`. An optimal status is accepted only when primal and dual
infeasibilities, relative gap, common-target violation, and differential-target
violation are finite and no greater than `1e-8`.

### Authorized implementation

- Add one analysis seam in `probes/`, one stable execution adapter in
  `scripts/`, and focused public-interface tests.
- Bind the complete R355 terminal chain, R341/R352 parents, package closure,
  installed CVXOPT version, exact case identity, and R356 sources.
- The public analysis seam accepts one base-output matrix, one response map,
  and one improvement fraction, and returns solver status plus independent
  residuals. Tests use analytic feasible and infeasible constructions.
- No R353-R355 source, result, threshold, case, model, trace, or ledger
  artifact may change.

## Outcomes

- `NO-TRAINING`: at least one development case has an accepted independent
  primal-infeasibility certificate at the unchanged two-percent joint target.
  This closes Q-0094 negative for the registered formulation. It authorizes no
  holdout read, physical residual probe, training, or large simulation.
- `CLASSIFIER-REPAIR-ELIGIBLE`: all sixteen relaxed cases are accepted optimal.
  This authorizes only one separately registered classifier-repair successor;
  it does not authorize training.
- `ANALYSIS-INVALID`: any parent, identity, dependency, source, solver status,
  certificate residual, numerical residual, process, or artifact check fails.
  Preserve artifacts and do not retry.

Lowering two percent to one percent is an exploratory sensitivity observation
and is excluded from every formal R356 decision. Training, distributed-agent
execution, ANDES, EVAL, deployment, stability, safety, robustness, topology,
and title validation remain false in every branch.

## Formal launch contract

- `formal_entry`: `python scripts/run_r356_joint_endpoint_feasibility.py analyse --expected-seal-sha256 <sha256>`.
- `rehearsal_command`: `python scripts/run_r356_joint_endpoint_feasibility.py rehearsal`.
- `rehearsal_scope`: same-pre-attempt-path; verify R355 terminal/source hashes,
  R341/R352 parents, package closure, CVXOPT 1.3.3, sixteen exact development
  identities, synthetic feasible/infeasible solver smoke, and formal-output
  absence without creating an attempt or result.
- `rehearsal_checks`: sixteen development cases, zero holdout reads, source and
  parent equality, both synthetic statuses with accepted residuals, result
  absent, attempt absent, ANDES absent, and training absent.
- `worker_processes`: 1; `native_threads_per_process`: 1;
  `wsl_python_processes`: 0; all are hard caps.
- `capacity_evidence`: the scratch implementation solved seven independent
  cases in less than three seconds when run concurrently; formal execution is
  serial in one process and is expected to finish within one minute.
- `host_process_budget`: one Windows Python process;
  `other_reserved_processes_at_plan`: zero. Readiness re-measures host capacity
  immediately before seal and launch; conflict returns `HOLD`.
- Completion is one create-only `analysis.json` plus `manifest.json` and
  sidecars, or one create-only `failure.json` plus sidecar. Retry is forbidden.

## Asset protection contract

R341/R350/R351/R352/R353/R354/R355 plans, sources, questions, claims, seals,
attempts, failures, results, traces, manifests, feeds, verdicts, thresholds,
and line evidence remain byte-unchanged. Add only R356 plan, probe, execution
adapter, focused tests, rehearsal, seal, formal results, and required closeout
artifacts. Do not edit another manuscript line or push publicly.

## Cross-references

- Q-0094
- R355 `ANALYSIS-INVALID`
- R352 matched neighbour-local parent
- R341 point models
