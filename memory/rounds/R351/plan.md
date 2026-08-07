---
round: R351
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R351 plan - matched neighbour-edge deterministic execution gate

**Opened**: 2026-08-07
**Driver**: Replace the unfair privileged-information baseline premise with a
strictly endpoint-local deterministic three-edge execution seam before any
controller tuning or neural training.
**Parent**: CLM-0915; Q-0092; R344 centralized upper reference

## TL;DR

Implement and physically validate one public three-edge action seam shared by
the deterministic neighbour controller and any later neighbour policy. This
round tests locality, action identity, and physical constraints only; it does
not optimize performance or authorize training.

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0091 closed-negative @ R350, by CLM-0915 — Does the frozen deterministic bridge leave material, observable, and physically usable residual headroom before neural training?
- Q-0090 closed-positive @ R344, by CLM-0910 — Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?
- Q-0089 closed-positive @ R341, by CLM-0900 — Does the selected predictor preserve its registered waveform envelope on an untouched operating-point bank?

## Methodology

**Lane**: evidence. The work freezes a new deployed information/action
formulation and may execute ANDES. Offline implementation may proceed inside
this round, but no physical command is allowed before preflight, representative
capacity measurement, same-path rehearsal, and a create-only seal.

### Research Supervisor route card

- **Owner**: `decoupling-marl-model-first` only.
- **Input**: CLM-0915's formulation-bounded `NO-TRAINING` result, the frozen
  active-power tree basis, the local DAPI utilities, and the existing physical
  BESS projection/readback path.
- **Return artifact**: tested public edge interface, locality audit, sealed
  zero/signed physical canary, feed, bounded claim, and verdict.
- **Stop**: any undeclared joint information, global statistic, centralized
  action aggregation, action-dimension drift, physical-governor mismatch, or
  failed physical guard. No stop branch authorizes neural training.

### Ask Matt engineering work order

- **Academic goal**: make the deterministic baseline and future neighbour
  policy comparable at the deployed information, action, and constraint seam.
- **Scientific acceptance criterion**: three independently computed edge
  actions use endpoint-only observations and traverse the same incidence and
  physical constraint path; six signed directions work at both registered
  operating points.
- **Engineering blocker**: existing explicit DAPI returns four scalar node
  requests, while the future policy contract exposes three edge actions; the
  R344 controller additionally consumes joint outputs.
- **Authority/write scope**: R351 and Q-0092; add one reusable controller
  module, its public-interface tests, one R351 execution adapter, and R351
  artifacts. Do not alter R341/R344/R350 assets or protected paper-path code.
- **Verification**: targeted pytest, `round_preflight.py R351`, same-path WSL
  rehearsal, seal verification, then the exact sealed canary entry.
- **Engineering deliverable**: endpoint-only observation/action dataclasses,
  deterministic edge policy, matched headroom governor, auditable telemetry,
  and a create-only runner.
- **Return gate**: engineering returns to the research owner after tests and
  rehearsal; passing tests alone do not authorize physical execution or a
  scientific conclusion.

### TDD public seams

1. `LocalEdgeObservation -> normalized scalar edge action`: changing any
   non-endpoint value is impossible because it is absent from the interface.
2. `three normalized actions + endpoint bounds -> three executed edge flows +
   four node residuals`: orientation, slew, endpoint headroom, and exact
   command-level zero sum are observable outputs.
3. `base node request + governed edge residual -> existing physical power
   projection/readback`: the future policy must call this identical seam.

Each slice is red then green. Tests use worked literals and public behavior;
they do not mock controller internals.

### Comparison-identifiability gate

R351 has no performance estimand. Its zero-edge arm is an execution negative
control and its signed-edge arms are authority canaries. All arms freeze the
same local DAPI common backbone, three-edge basis, action scale, endpoint
headroom allocator, external projection, operating points, timing, and
physical guards. R344 is not numerically contrasted because it has joint
information and a four-coordinate action. A later performance round must
introduce a matched joint-information three-edge upper reference separately.

### Prospective canary inventory

- Registered points: `FV0`, `FV1` from R341; no point reconstruction or
  refitting.
- Zero arm: one equilibrium record per point with all three edge actions zero.
- Signed authority: each of the three tree edges at `+0.05` and `-0.05`
  system pu for five 0.2-second control intervals, followed by twenty recovery
  intervals, at both points: twelve records.
- Commands: edge flow is mapped through the frozen active-power incidence;
  the local DAPI common request is shared by all arms and is zero at the
  equilibrium canary.
- Physical guards reuse the R344 validated values: 0.2-second increments,
  time tolerance `1e-9` s, algebraic residual maximum `1e-6`, scheduled M/D
  tolerance `1e-10`, SOC range `[0.2,0.8]`, node power maximum `0.36` system
  pu, node ramp maximum `0.072` system pu per interval, required Line 8/G4,
  no external saturation, no internal limiter, and no solver fallback.
- Signed guard: request and command profiles within `1e-12` system pu; correct
  achieved sign; terminal achieved error no more than 5% of `0.05`; requested
  and commanded fleet imbalance within `1e-12`; achieved terminal imbalance
  no more than 5% of command L1. Exact achieved neutrality is not claimed.

### Formal launch contract

- `formal_entry`: `python scripts/run_r351_matched_distributed_bridge.py execute-canaries --expected-seal-sha256 <sha256>` through `scripts/andes_scratch.py` in WSL.
- `rehearsal_command`: `python scripts/run_r351_matched_distributed_bridge.py rehearse` through the same WSL adapter.
- `rehearsal_scope`: installed package and case identity, R341 point assets,
  R351 source closure, exact fourteen-record inventory, native-thread settings,
  scratch isolation, and formal-output absence; no physical trajectory.
- `rehearsal_checks`: source hashes, parent sidecars, plan/question identity,
  imports, inventory, WSL/POSIX identity, output absence, and create-only paths.
- `wsl_python_processes`: 2 maximum, including the launcher/parent and one
  process-pool worker.
- `native_threads_per_process`: 1 for every formal process.
- `host_process_budget`: 2 single-thread WSL Python processes for R351's
  frozen envelope; the host exposes 32 logical processors.
- `other_reserved_processes`: 0 at the 2026-08-07 capacity measurement and
  rechecked immediately before seal.
- `capacity_evidence`: `memory/rounds/R351/capacity_measurement.json` records
  one representative zero record and one representative signed record using
  two unique processes with maximum overlap 2; both completed in 4.47 seconds,
  the process guard passed, and scientific outcomes were not inspected.
- `ETA`: about one minute for fourteen records at the measured 0.447 records/s;
  terminal-only hard observation envelope five minutes.

### Experiment-efficiency card

- **Decision**: `HOLD` until the capacity-bound final rehearsal and create-only
  seal pass; then `RUN-READY` for the exact fourteen-record entry only.
- **Stage/run state**: implementation, targeted tests, preflight, plumbing
  rehearsal, and representative capacity measurement passed; no formal attempt
  or seal exists.
- **Stop state**: terminal after one sealed fourteen-record canary or the first
  prospectively classified invalid/physical-guard stop.
- **Jobs**: two zero plus twelve signed; no optimizer, training, or formal
  performance bank.
- **Plumbing evidence**: existing R344 WSL bridge and R294--R300 distributed
  utilities are reusable, but do not establish R351 capacity or matched action
  identity.
- **Capacity evidence**: two representative records completed with two unique
  single-thread processes, maximum overlap 2, 4.47 seconds elapsed, and all
  operational/physical validity checks passing. This authorizes a formal
  budget of two, not any larger rung.
- **Authorized next action**: capacity-bound final rehearsal, create-only seal,
  and then the exact sealed canary. No resize, retry, tuning, or training.

### Outcomes

- **Every structural and physical guard passes**:
  `DISTRIBUTED-EDGE-EXECUTION-ELIGIBLE`; close Q-0092 positive and authorize
  only a new deterministic tuning/comparison question.
- **Any undeclared information field, nonlocal influence, wrong edge order,
  action-dimension drift, or governor mismatch**:
  `INVALID-DISTRIBUTED-EDGE-CONTRACT`; stop without physical interpretation.
- **The contract is intact but any DAE, timing, sign, tracking, power, ramp,
  energy, state-of-charge, external-saturation, internal-limiter, or neutrality
  guard fails**: `DISTRIBUTED-EDGE-PHYSICAL-GUARD-FAIL`; preserve the attempt
  and stop without tuning.
- **Any incomplete record, source/seal mismatch, non-finite value, missing
  point, or execution exception**: `INVALID-DISTRIBUTED-EDGE-EXECUTION`; retain
  failure artifacts and do not retry in R351.

## Gate

`DISTRIBUTED-EDGE-EXECUTION-ELIGIBLE` requires every test, locality audit,
rehearsal check, seal check, zero record, signed record, and physical guard to
pass. Integrity or information/action mismatch returns
`INVALID-DISTRIBUTED-EDGE-CONTRACT`. A valid plant/constraint failure returns
`DISTRIBUTED-EDGE-PHYSICAL-GUARD-FAIL`. No branch trains a policy. A pass
authorizes only a separately registered deterministic tuning/comparison round.

## Asset protection contract

R341/R344/R350 sources, seals, attempts, traces, results, feeds, claims,
questions, thresholds, and verdicts remain byte-unchanged. Add only Q-0092,
R351 plan/implementation/tests/adapter/rehearsal/seal/create-only canary
artifacts, and, after a valid terminal result, the R351 feed, claim, verdict,
manifest registration, and selected manuscript-line navigation refresh. No
public push.

## Cross-references

- CLM-0915
- Q-0092
- R344 centralized upper reference
