---
round: R369
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds:
- R368
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R369 plan — outcome-blind actuator-mapping reanalysis

**Opened**: 2026-08-12
**Driver**: Resolve R368's sole failed validity guard using an arithmetic-derived
tolerance, then apply the unchanged deterministic/headroom decision tree once
to the immutable complete bank.
**Parent**: Q-0103; CLM-0985; R368

## TL;DR

Workload: `evidence` because the reanalysis may resolve the current paper-line
gate.  Run no ANDES trajectory and no training.  Derive the mapping tolerance
from IEEE single-precision multiplication, alter only that one validity field
in an in-memory copy of the R367 contract, resummarize all immutable R368
records, and classify once with the preserved endpoints and thresholds.

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?
- Q-0100 closed-positive @ R363, by CLM-0965 — On the exposed development bank, does adding a common residual-power channel to the three-edge zero-common action basis enlarge the per-case physical action-space headroom, showing that the zero-common residual contract itself (rather than information) limits the R358 feasibility?

## Methodology

### Frozen inputs and exclusion

- Inputs are only the hashed R368 formal seal, complete execution, invalid
  analysis, and preserved R367 classifier/controller/environment sources.
- Assert every source/input hash before reading records.  Require the parent
  analysis to be `ANALYSIS-INVALID` with a complete bank and only row-validity
  failure; require every record complete and no simulator failure.
- R367/R368 performance summaries, candidate ranking, improvement values, and
  oracle selections are prohibited tolerance inputs.  The correction code
  reads raw records only after freezing the arithmetic bound below.
- No physical rerun, candidate change, endpoint change, scenario exclusion,
  threshold change, selection change, or training is authorized.

### Arithmetic-derived mapping tolerance

- The formal runner supplies each normalized action as `float32`.  The protected
  environment clips it without dtype promotion and NumPy 2.4.3 multiplies the
  scalar by decoder scales at most 600 using `float32`, then assigns the rounded
  product into a `float64` telemetry array.
- Under round-to-nearest IEEE binary32, multiplication error is at most one half
  unit in the last place.  For absolute decoded values at most 600, the largest
  relevant binade is `[512,1024)`, whose half-unit bound is `2^(9-24)=2^-15`.
- Freeze `mapping_atol = 2^-15 = 3.0517578125e-5` model units.  This bound is
  derived from dtype and decoder range, not from observed mapping discrepancies
  or any performance endpoint.  Keep relative tolerance zero.

### Single-pass reanalysis

- Deep-copy the R367 scientific contract and change only
  `decoder.mapping_atol` from the invalid parent value to the arithmetic bound.
  Emit a structural diff and fail if any other field differs.
- Resummarize every raw R368 record through the preserved summarizer, then call
  the preserved classifier exactly once.  Record parent and source hashes,
  corrected contract/hash, all summaries, classification, and no-training flag
  in one create-only `analysis.json` with a SHA-256 sidecar.
- Unit of analysis, aggregate deterministic threshold, common-frequency guard,
  saturation/bound/slew guards, oracle threshold, nonconstant-action rule,
  distinct-candidate rule, inference ceiling, and stay-out claims remain R367.

### Ask Matt TDD seams

- Route: current-context `/tdd`; no new task, prototype, or handoff.
- Public seam 1 returns the exact binary32 half-unit bound from decoder scale.
- Public seam 2 proves the corrected contract differs from the parent at one
  and only one JSON pointer.
- Public seam 3 rejects source/input drift, incomplete records, wrong parent
  invalidity, a second output, or any training flag.

## Gate

- If any input/hash/completeness/contract-diff/mapping guard fails, classify
  `ANALYSIS-INVALID` and leave Q-0103 open.
- Otherwise accept exactly the preserved classifier return:
  `DETERMINISTIC-AND-HEADROOM-PASS`,
  `STOP-DETERMINISTIC-NO-EFFICACY`, or
  `STOP-NO-CONDITIONAL-HEADROOM`.
- A positive return closes only the two pretraining mechanism gates; it does
  not authorize training until the separately registered learning comparison
  and its six budgets are frozen.  Either STOP closes Q-0103 negative and ends
  this formulation without an algorithm sweep.

## 资产保护契约

All R367/R368 sources, seals, results, feeds, claims, and verdicts stay
byte-unchanged.  Protected environment/config/training files and all other
paper lines stay unchanged.  Add only R369 plan/probe/tests/result, one
feed/claim/verdict, Q-0103 disposition, and current-line navigation.

## Cross-references

- CLM-0985/R368: complete bank quarantined by the mapping guard.
- CLM-0980/R366: unchanged design, endpoints, thresholds, and no-training rule.
- `paper/paralleled_vsg_marl/ROUTE.md#current-gate`.
