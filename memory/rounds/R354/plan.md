---
round: R354
state: aborted
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed pre-attempt invocation invalid: inherited load_seal default
  rebound to R353 rehearsal instead of sealed R354 rehearsal; no analysis_attempt
  or result root created; source-bound retry forbidden'
superseded_note: null
---
# R354 plan - certificate-compatible matched residual-headroom recovery

**Opened**: 2026-08-07
**Driver**: Recover the unchanged R353 analysis after its sealed attempt became
`ANALYSIS-INVALID` solely because the result serializer requested fields absent
from the current `MinimumNormCertificate` object.
**Parent**: CLM-0925; Q-0094; aborted R353; R341/R352 parents; R350 gate grammar

## TL;DR

Freeze a create-only successor to R353. Keep the complete R353 scientific
contract, parent inventories, thresholds, information pattern, estimator,
governor, staged holdout rule, and single-process budget unchanged. Add only a
certificate serializer that records the fields actually exposed by the sealed
minimum-norm certificate type. A valid result may decide Q-0094; training stays
forbidden in every R354 branch.

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

**Lane**: evidence. R354 is the required separately reserved, re-preflighted,
and re-sealed successor to the terminal R353 attempt. It creates no new ANDES
trajectory and runs no training.

### Frozen failure chain

- R353 seal SHA-256:
  `b58d3521d6cffff781da72e3bf6baa175426b2f94d8c130fd982c5b0478decc0`;
- R353 attempt SHA-256:
  `6c3f22c184e682e97f7497b372440edd4a782bfb1e72bcddf2750674dafe8d86`;
- R353 failure SHA-256:
  `09e2c55e7c6d7db532135c18333ef7a9ebae349fa6a933384e1a312e2b79b33d`;
- R353 adapter SHA-256:
  `63b7880684ee892f35cc30f2476ba0d8f6021214bbd3f1553303f82d32f98c4e`;
- R353 probe SHA-256:
  `37fa859d588b392fbb1fa63d5242aeccf998a2d33aa0a29020dac79793b8482b`;
- current certificate implementation SHA-256:
  `9dc24a0189c1d29368b7bd4da0a8c21a02a108ea214c5bf8ca303e6664ad69f8`.

The R353 terminal failure is exactly `AttributeError: 'MinimumNormCertificate'
object has no attribute 'message'`. The sealed class instead exposes
`valid`, `feasible`, `reason`, `active_constraint_count`,
`maximum_constraint_violation`, `stationarity_residual`,
`complementarity_residual`, `optimality_tolerance`, and `multipliers`.

### Authorized recovery

- Add one R354 probe adapter that serializes only those actual certificate
  fields and delegates all case construction, optimization, projection,
  estimator fitting, statistics, and decision logic to the byte-unchanged
  R353 implementation.
- Add one R354 execution adapter and focused tests. The adapter must bind the
  R353 failure chain, the unchanged R353 implementation, the complete R341/R352
  parents, the current package closure, and the new R354 files.
- No R353 file, parent artifact, threshold, scenario, endpoint, subgroup,
  causal feature, fit split, governor, or decision rule may change.
- The corrected serializer is descriptive only. It cannot alter certificate
  validity, solver selection, residual actions, endpoints, or any gate.

### Unchanged scientific contract

- Development and holdout each contain the same sixteen R352 zero/local pairs;
  the joint-information arm remains excluded.
- The oracle is the same R350-certified three-start minimum-norm residual over
  25 steps. Each residual uses zero common coordinate and three edge
  coordinates through the same physical headroom projection.
- Each edge estimator sees only its two endpoint frequency deviations and
  RoCoFs, its own previous edge flow, endpoint previous achieved and commanded
  powers, endpoint state of charge, and endpoint voltages. The first two
  residual actions remain zero and their rows remain excluded from fitting.
- One standardized affine least-squares estimator per edge is selected only
  from development data and is never refit on holdout.
- Endpoints remain lower-is-better common-coordinate IAE and differential-
  coordinate energy. Unit remains scenario.
- Each endpoint and candidate requires mean improvement at least `0.02`, a
  one-sided 95% paired upper bound below zero, every point/channel/sign subgroup
  mean below zero, and maximum single-scenario ratio no greater than `1.05`.
- Holdout is read only if the unchanged development gate passes. The holdout
  model-adequacy tolerance remains `1e-8`.

### Formal launch contract

- `formal_entry`: `python scripts/run_r354_certificate_compatible_residual_headroom.py analyse --expected-seal-sha256 <sha256>`.
- `rehearsal_command`: `python scripts/run_r354_certificate_compatible_residual_headroom.py rehearsal`.
- `rehearsal_scope`: execute the exact formal pre-attempt verification path,
  including R353 failure/source closure, R341/R352 parent/package hashes,
  installed inputs, case identities, and formal-output absence; create no
  attempt or formal result.
- `rehearsal_checks`: sixteen development pairs, sixteen holdout pairs, source
  and parent equality, corrected serializer smoke check, result root absent,
  attempt absent, ANDES absent, and training absent.
- `worker_processes`: 1; `native_threads_per_process`: 1. Both are intentional
  hard caps inherited from R353. `wsl_python_processes`: 0.
- `capacity_evidence`: the identical R350 solver bank measured sixteen oracle
  jobs with 164.6016596 seconds serial work; R353 reached the first serializer
  after about seven seconds before failure. R354 adds negligible serialization
  work and retains the single-process budget.
- `host_process_budget`: one Windows Python process for this analysis;
  `other_reserved_processes_at_plan`: zero, measured before implementation.
  Readiness re-measures shared-host use immediately before sealing and launch;
  any conflict returns `HOLD` rather than changing the frozen one-process cap.
- Expected wall time is about three to six minutes. Monitor only process state,
  terminal artifact presence, and resource safety; do not inspect intermediate
  scientific outputs.
- Completion is one create-only `analysis.json` plus `manifest.json` and valid
  sidecars, or one create-only `failure.json` plus sidecar. Retry is forbidden.

## Outcomes

The following exhaustive outcomes are preregistered before rehearsal, sealing,
or any R354 result exists:

- `RESIDUAL-PROBE-ELIGIBLE`: every unchanged R353 scientific and integrity gate
  passes. This authorizes only one separately registered non-learning physical
  residual intervention; it does not authorize training directly.
- `NO-TRAINING`: execution is valid but any scientific gate fails. Close Q-0094
  negative for this formulation and do not start neural or large-scale work.
- `ANALYSIS-INVALID`: any source, parent, serializer, inventory, causality,
  numerical, certificate, process, or artifact integrity check fails. Preserve
  the attempt and do not interpret direction or retry.

Training, distributed-agent execution, EVAL, deployment, stability, safety,
robustness, topology, and title-term validation are false in every R354 output.

## Asset protection contract

R341/R350/R351/R352/R353 plans, sources, questions, claims, seals, attempts,
failures, results, traces, manifests, feeds, verdicts, thresholds, and line
evidence remain byte-unchanged. Add only the R354 plan, probe adapter, execution
adapter, focused tests, rehearsal, seal, formal results, and required closeout
artifacts. Do not edit another manuscript line or push publicly.

## Cross-references

- CLM-0925
- Q-0094
- R353 `ANALYSIS-INVALID`
- R350 residual gate grammar
- R352 matched neighbour-local parent
