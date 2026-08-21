---
round: R394
state: aborted
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'analysis-invalid by CLM-1115: two residual instrumentation seams (global-address
  indexing into model-local arrays, Pref/Qref read before initialization)'
superseded_note: null
---
# R394 plan — science-identical PPVSM1 gate correction

**Opened**: 2026-08-14
**Driver**: R393's sole sealed attempt is analysis-invalid by CLM-1110 because of three instrumentation seams: the initial trace row read device variables through Model.get (KeyError for algebraic variables), the TDS horizon was never frozen to the registered 0.2 seconds, and the source snapshot was taken after TDS initialization when replaced static generators already read zero. Repair only those three evidence seams; the scientific bank, object, card, thresholds, and gates stay frozen.
**Parent**: CLM-1110; CLM-1105; Q-0110

## TL;DR

Re-run R393's exact single two-unit PPVSM1 arm under a new seal and create-only
root. Change only the initial-trace variable readback, the frozen 0.2-second
TDS horizon, and the pre-init source snapshot. All model equations, cards,
mapping, operating point, tolerances, drift ceilings, spectrum guards, and the
one-allowed-zero-mode rule remain exactly R393's. R393 stays immutable.

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0110 [opened R393] Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?

## Recently Closed (last 3)

- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?
- Q-0108 closed-positive @ R391, by CLM-1100 — Does the exact R389 four-REGF2 equilibrium contain a finite, numerically resolved positive-real mode in the ANDES reduced state matrix that reproduces across two independently initialized numerical arms without advancing simulation time?
- Q-0107 closed-negative @ R389, by CLM-1090 — Can four stock REGF2 VSM devices replace the four Kundur source models one-for-one and complete structurally clean native initialization plus a no-exogenous-action short trajectory without residual, convergence, finite-value, or electrical-guard failure?

## Methodology

### Frozen scientific object and bank

- Preserve R393's exact frozen contract: ANDES 2.0.0, unchanged packaged/
  derived Kundur static case, StaticGen 1-2 replaced by PPVSM1 at buses 1-2,
  StaticGen 3-4 static anchors, forbidden models absent, 100-MVA system base,
  900-MVA device rating, frozen PPVSM1 card, one serial arm.
- Preserve every gate: drift ceiling 2e-4 system pu over 0.2 s; any
  eigenvalue with Re > 1e-7 -> STOP-PPVSM1-POSITIVE-REAL; any root with
  |lambda| < 1e-6 beyond one allowed network common-angle degeneracy ->
  STOP-PPVSM1-NEUTRAL-DEGENERACY; complete valid pass -> PPVSM1-OBJECT-PASS.

### Evidence corrections (only these three)

1. **Initial trace row**: read each variable from its own numeric array
   (Bus.v, Pe, Qe, Id, Iq, INTw_y) via the variable's address, never through
   Model.get.
2. **Frozen horizon**: set system.TDS.config.tf to the registered
   tds_tf_seconds (0.2) alongside the tolerance before setup.
3. **Source snapshot**: capture the StaticGen p/q reference rows after power
   flow and before TDS.init, then compare Pref/Qref against that snapshot
   post-init.

### Independent correction classifier

Reuse R393's classifier unchanged. It validates the R394 record against the
frozen contract; any correction-schema, capture, or artifact-integrity defect
is ANALYSIS-INVALID.

## Gate

- ANALYSIS-INVALID: contract/schema, provenance, capture, unexpected
  execution, or artifact-integrity defect.
- STOP-PPVSM1-OBJECT-INIT: power flow, TDS init/test, residual, finite-value,
  or zero-input drift failure.
- STOP-PPVSM1-POSITIVE-REAL / STOP-PPVSM1-NEUTRAL-DEGENERACY: frozen spectrum
  guards.
- PPVSM1-OBJECT-PASS: complete valid pass of every guard; opens only a
  separately registered signed P/Q authority gate.

Exactly one formal bank is permitted. No automatic retry. A pre-seal defect
may be repaired prospectively and then rehearsed/sealed; any post-seal defect
aborts R394 and requires a separately authorized successor.

## Outcomes

Frozen magnitude meanings (identical to R393):

- Zero-input drift stays within 2e-4 system pu over 0.2 s -> stationarity
  passes; any breach -> STOP-PPVSM1-OBJECT-INIT.
- Every eigenvalue has Re <= 1e-7 -> no positive-real mode.
- At most one root with |lambda| < 1e-6 -> neutral-degeneracy guard passes.
- All guards pass -> PPVSM1-OBJECT-PASS; the leading real part and smallest
  nonzero root magnitude are archived for the authority round.

## 资产保护契约

R393's seal, attempt, execution, analysis, manifest, claim, feed, and verdict
remain immutable and read/hash-only; R383-R392 likewise. R394 adds only the
three evidence-seam corrections and one create-only single-arm result root.
It changes no model equation, card, mapping, operating point, threshold,
scientific gate, controller, or learning asset.

## Formal launch contract

- formal_entry: scripts/run_r394_ppvsm1_object_gate.py
- rehearsal_command: /home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r394_ppvsm1_object_gate.py rehearse
- rehearsal_scope: setup-only construction, two-unit mapping and forbidden-
  model checks, model-card readback, variable-array readback canary (the
  corrected seam), frozen-horizon readback, pre-init source snapshot canary,
  parent-chain (R393) hash checks; no PFlow, TDS, or EIG.
- rehearsal_checks: canonical contract equivalence; R393 seal-to-manifest
  chain; installed case/source/API identities; structural absence; native
  thread environment; create-only absence; capacity telemetry.
- capacity_evidence: memory/rounds/R394/capacity_evidence.json.
- host_process_budget: 1
- wsl_python_processes: 1
- native_threads_per_process: 1
- other_reserved_processes: 0

One WSL Python formal process runs the single arm; native numerical library
threads are pinned to 1; competing research processes are measured
immediately before seal and required 0.

- seal_command: /home/wya/andes_venv/bin/python scripts/run_r394_ppvsm1_object_gate.py prepare
- seal_path: memory/rounds/R394/formal_seal.json.
- formal_execute_command: from a clean scratch launch directory invoke
  /home/wya/andes_venv/bin/python <repo>/scripts/andes_scratch.py <repo>/scripts/run_r394_ppvsm1_object_gate.py execute --expected-seal-sha256 <sha256>.
- formal_output: create-only results/research_loop/r394_ppvsm1_object_gate.
- completion: one immutable execution, analysis, and manifest.
- retry: none automatically; post-seal defects require a successor.

## Cross-references

- Q-0110
- CLM-1110
- CLM-1105
- paper/converter_vsg_pq_decoupling/reports/R393.md
- paper/converter_vsg_pq_decoupling/working/route_contract.md#ppvsm1-successor-decision
