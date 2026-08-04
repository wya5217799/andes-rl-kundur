---
round: R305
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R305 plan — convergence-adapter repair and gated topology matrix

**Opened**: 2026-08-03
**Driver**: Q-0061; R304 was invalid before modal identification because the
runner coerced the multi-element `PFlow.run()` return to a scalar boolean.
**Parent**: CLM-0730; CLM-0720; CLM-0665.

## TL;DR

Repair only the ANDES convergence adapter, keep the R304 topology/action/modal
contract unchanged, and require one nominal/q0 canary before any matrix
expansion. A valid canary opens at most three disjoint static EIG shards; it
does not open time-domain evaluation or neural training.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0061 [opened R304] Do stable network configurations create locally observable topology-information value for genuine zero-sum VSG vector-inertia coordination?

## Recently Closed (last 3)

- Q-0060 closed-positive @ R303, by CLM-0725 — Does heterogeneous BESS headroom make independent projection leak a zero-sum differential residual into the common-power coordinate?
- Q-0059 closed-partial @ R302, by CLM-0720 — Can architecture-aware EVAL-v2 audit genuine vector distributed traces, and does current evidence justify neural distributed-agent training beyond 2Kv?
- Q-0058 closed-negative @ R301, by CLM-0715 — Can the sampled neighbour relative-RoCoF residual yield a prospective gain-sufficiency or stability-margin rule beyond the validated 2Kv baseline?

## Methodology

- Reuse the frozen R304 pure classifier, topology set, action library, mode
  band, branch matching, materiality thresholds, EVAL profile, and outcome
  labels without numerical changes.
- Create a new R305 execution adapter and seal. After `PFlow.run()`, set the
  convergence guard only from scalar `system.PFlow.converged`; serialize the
  raw return by type/shape only and never coerce it to `bool`.
- Add a unit seam proving a multi-element `PFlow.run()` return cannot control
  the convergence verdict and that the scalar model state does.
- Stage A canary: run only nominal/q0. Require all registered plant, topology,
  PFlow, TDS-init, EIG-run, residual, finite-spectrum and positive-real guards,
  plus an identified inter-area mode and valid sidecar.
- If and only if the canary passes, run the remaining 20 cells in three
  disjoint WSL shards. Each shard is create-only and source-hash bound. Do not
  inspect directional/modal endpoints until every cell and shard sidecar is
  present.
- Run the already-frozen `vector_inertia` EVAL engineering check against the
  R305 seal. It must remain `EXTERNAL_AUTHORITY_REQUIRED`.
- One final analysis verifies the seal, all sources, canary, 21 cells, three
  shard manifests and sidecars before applying the unchanged R304 classifier.

## Comparison-identifiability contract

- Information: this round estimates only whether the nondeployable per-topology
  static oracle changes across nominal, Line_0-out and Line_9-out. It does not
  yet compare centralized and distributed controllers.
- Action: every cell uses the same four-VSG total inertia and the same
  three-edge-to-four-node zero-sum differential coordinate; damping and active
  power do not change.
- Execution and budget: same ANDES plant build, setter path, initialization,
  EIG routine, action count and topology count for every branch.
- Estimand: configuration-conditioned static allocation headroom over q0.
  Centralized oracle selection is an upper bound, not a deployable controller.
- Inference ceiling: at most `STATIC-TOPOLOGY-VALUE-*`; no pure-architecture,
  strict-local-discovery, dynamic-performance, MARL, stability, safety or
  topology-generalization conclusion.

## Gate

Canary failure -> `INVALID-CANARY`, stop without matrix expansion. Complete
matrix guard failure -> `INVALID-TOPOLOGY-GATE`. Valid matrix with fewer than
two distinct oracle actions, maximum headroom below 5%, or mean headroom below
2% -> `NO-STATIC-TOPOLOGY-VALUE`. Material static value plus failed EVAL ->
`STATIC-TOPOLOGY-VALUE-EVAL-NOT-READY`; material value plus passed EVAL ->
`STATIC-TOPOLOGY-VALUE-EVAL-READY`. Only the last label may authorize a new
12-case matched classical information gate. Neural training is false for every
R305 outcome.

### Outcomes

- `INVALID-CANARY`: adapter or plant/EIG guards fail on nominal/q0; stop and
  interpret no modal endpoint.
- `INVALID-TOPOLOGY-GATE`: canary passed but final sealed matrix is incomplete
  or any registered cell/branch/integrity guard fails; interpret no direction.
- `NO-STATIC-TOPOLOGY-VALUE`: matrix valid but fails the prospective distinct-
  oracle or 5% maximum / 2% mean headroom materiality gate; stop Q-0061 and do
  not train.
- `STATIC-TOPOLOGY-VALUE-EVAL-NOT-READY`: static value passes but the execution
  audit is not ready; repair EVAL only, no time-domain comparison or training.
- `STATIC-TOPOLOGY-VALUE-EVAL-READY`: authorize only a separately sealed
  12-case classical information gate; training remains blocked.

## 资产保护契约

- R304 seal, cells, analysis, feed, claim and verdict are immutable read-only
  invalid evidence. R305 creates a separate seal and result root.
- Current ICEMS and SCI manuscript lines remain read-only; R305 is future work.
- No change to V4 plant, R304 pure classifier, topology candidates, action
  values, thresholds, mode band, EVAL authority, controller, trainer or
  manuscript prose after the R305 seal.
- R305 may add only its runner, focused tests, create-only artifacts,
  feed/claim/verdict and programme governance.

## Cross-references

- CLM-0730 — R304 execution-adapter invalidity and training block.
- CLM-0720 — EVAL readiness is necessary but not efficacy authority.
- CLM-0665 — public topology setter and full EIG validity guards.
