---
round: R355
state: aborted
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed analysis invalid: 7 of 16 development scenarios had no fixed
  R350 start pass the independent oracle certificate; candidate endpoints were not
  evaluated, holdout was not read, and training/residual probe remained unauthorized;
  retry forbidden'
superseded_note: null
---
# R355 plan - pre-attempt rehearsal-binding recovery

**Opened**: 2026-08-07
**Driver**: Recover the unchanged Q-0094 analysis after the sealed R354 command
failed before creating an attempt because the inherited seal loader's Python
default argument still named the R353 rehearsal path.
**Parent**: CLM-0925; Q-0094; aborted R353/R354; R341/R352 parents; R350 gate grammar

## TL;DR

Freeze a create-only successor to R354. Keep the complete R354 scientific
contract, corrected certificate serializer, parent inventories, thresholds,
information pattern, estimator, governor, staged holdout rule, and one-process
budget unchanged. Add only an invocation adapter that explicitly supplies the
current rehearsal path when the inherited formal entry loads its seal. A valid
result may decide Q-0094; training remains forbidden in every branch.

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

**Lane**: evidence. R355 is a separately reserved, re-preflighted, and
re-sealed successor to R354. It creates no new ANDES trajectory and runs no
training.

### Frozen R354 pre-attempt failure

- R354 rehearsal SHA-256:
  `9b9fe79d1909ac0cf54c7a33c22cef26af774530433542bdd135906089d635e8`;
- R354 seal SHA-256:
  `8526f9bbbf3ff4066236b085c61a6f3d067393e3de89354cbe1e66b5ffefa563`;
- R354 adapter SHA-256:
  `357ed93d5a82f3627fb73d5c080a4207c68480db64c711f09f0823bc69728f44`;
- R354 certificate probe SHA-256:
  `3799d2e7c6e22a0922176d280d8a633dcf60d087cc8aec91283fb24092ac46c0`;
- R354 focused tests SHA-256:
  `a53733b79b3915a52cbff2894d555dbcb606981af1e98c2bb7d4c973813206cd`;
- closed R354 plan SHA-256:
  `ed79efbd68df702baf5e7855c45c4b956dc76883bb6a8f05d784ed5c5c7c1b49`.

The R354 command failed in `load_seal` with `RuntimeError: R353 contract,
source, or parent drift`. No R354 result root or `analysis_attempt.json` was
created. A read-only comparison proved that contract and parents matched and
that the explicit R354 rehearsal snapshot matched the seal; only the inherited
`load_seal.__kwdefaults__["rehearsal_path"]` still pointed to R353.

### Authorized recovery

- Add one R355 invocation adapter and focused tests.
- Explicitly bind the current round's rehearsal path while the unchanged R353
  formal entry calls its seal loader.
- Bind the complete R354 seal/rehearsal/failure identity, the R353 failure
  chain, all R341/R352 parents, the current package closure, and R355 sources.
- No serializer, case construction, optimization, projection, estimator,
  statistic, endpoint, subgroup, threshold, governor, or decision rule changes.
- No R353 or R354 sealed source is edited.

### Unchanged scientific contract

- Development and holdout each contain the same sixteen R352 zero/local pairs;
  the joint-information arm remains excluded.
- The oracle remains the R350-certified three-start minimum-norm residual over
  25 steps, with zero common coordinate and three edge coordinates through the
  same physical headroom projection.
- Each edge estimator sees only the same endpoint-local neighbour information.
  The first two residual actions remain zero and excluded from fitting.
- One standardized affine least-squares estimator per edge is selected only on
  development and never refit on holdout.
- The endpoints, scenario unit, 0.02 materiality threshold, one-sided 95%
  paired bound, subgroup rule, 1.05 worst-case ratio, staged holdout, and
  `1e-8` model-adequacy tolerance remain identical to R354.

### Formal launch contract

- `formal_entry`: `python scripts/run_r355_rehearsal_binding_residual_headroom.py analyse --expected-seal-sha256 <sha256>`.
- `rehearsal_command`: `python scripts/run_r355_rehearsal_binding_residual_headroom.py rehearsal`.
- `rehearsal_scope`: same-pre-attempt-path; exercise R354 failure/source
  closure, R341/R352 parent/package hashes, case identities, serializer smoke,
  explicit current-rehearsal binding, and formal-output absence without
  creating an attempt or result.
- `rehearsal_checks`: sixteen development pairs, sixteen holdout pairs, source
  and parent equality, implicit inherited seal-load smoke through the current
  rehearsal binding, result absent, attempt absent, ANDES absent, training
  absent.
- `worker_processes`: 1; `native_threads_per_process`: 1;
  `wsl_python_processes`: 0. These are hard caps unchanged from R354.
- `capacity_evidence`: R350 measured 164.6016596 seconds total serial oracle
  work for the same sixteen jobs. R355 changes only pre-attempt path binding;
  expected wall time remains about three to six minutes.
- `host_process_budget`: one Windows Python process;
  `other_reserved_processes_at_plan`: zero. Readiness re-measures the host
  immediately before seal and launch. A conflict returns `HOLD`.
- Completion is one create-only `analysis.json` plus `manifest.json` and
  sidecars, or one create-only `failure.json` plus sidecar. Retry is forbidden.

## Outcomes

- `RESIDUAL-PROBE-ELIGIBLE`: every inherited scientific and integrity gate
  passes. This authorizes only one separately registered non-learning physical
  residual intervention, not training directly.
- `NO-TRAINING`: execution is valid but any scientific gate fails. Close
  Q-0094 negative and do not start neural or large-scale work.
- `ANALYSIS-INVALID`: any source, parent, invocation, serializer, inventory,
  causality, numerical, certificate, process, or artifact integrity check
  fails. Preserve the attempt and do not interpret direction or retry.

Training, distributed-agent execution, EVAL, deployment, stability, safety,
robustness, topology, and title validation are false in every R355 output.

## Asset protection contract

R341/R350/R351/R352/R353/R354 plans, sources, questions, claims, seals,
attempts, failures, results, traces, manifests, feeds, verdicts, thresholds,
and line evidence remain unchanged after R354 closeout. Add only the R355 plan,
invocation adapter, focused tests, rehearsal, seal, formal results, and required
closeout artifacts. Do not edit another manuscript line or push publicly.

## Cross-references

- CLM-0925
- Q-0094
- R353 `ANALYSIS-INVALID`
- R354 pre-attempt invocation failure
- R350 residual gate grammar
- R352 matched neighbour-local parent
