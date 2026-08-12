---
round: R378
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds:
- R377
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R378 plan — settling-rule correction and conditional held-out

**Opened**: 2026-08-12
**Driver**: Correct the single R377 rule defect that made its development
selection unsatisfiable, reanalyse the immutable 60-record R377 development
execution, and execute the 30-record held-out bank only if a candidate is
selected.
**Parent**: CLM-1030 (R377 stop), CLM-1025 (R376 stop), Gate B-2 contract

## TL;DR

R378 is a result-blind correction round, not a new controller search. The
R377 development rule required the candidate's mean differential settling
time to be at least one `dt` (0.2 s) below the local arm; the executed
records show every arm (including the local arm) at the registered settling
floor of 1.2 s, so that rule is unsatisfiable. R378 changes exactly one rule
— settling improvement becomes "no worse than the local arm" — and proves
via a validator that the corrected contract differs from the sealed R377
contract only in the round id. It reanalyses the immutable R377 development
records with the unchanged summarizer and the corrected selection rule. A new
30-record held-out execution is permitted only if that reanalysis selects an
eligible candidate. Training remains forbidden.

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?

## Methodology

### Registered scientific object

- The four-VSG feasibility-native object, energy ports, action map, banks,
  endpoints, thresholds, seeds, and execution discipline are exactly those
  sealed by R377 (Gate B-2 contract), with one rule change:
  `development_settling_dt_improvement` is replaced by the corrected rule
  "candidate settling <= local settling" in both development selection and
  held-out classification.
- The R377 development execution is a read-only input. Its performance
  fields remain forbidden until the R378 seal is fixed.

### Result-blind rule correction

The correction implementation starts from the sealed R377 contract and
permits exactly the round id difference (`R377 -> R378` plus the declared
`correction_scope`). An independent validator proves semantic equality of
every other contract field. The corrected selection/classification functions
reuse the unchanged R377 summarizer; only the settling comparison changes.

### Immutable development reanalysis

Only after the corrected contract and parent-artifact hashes are sealed may
the runner read the R377 development performance records. It verifies the
recorded SHA-256 sidecars, copies no records, mutates no parent artifact, and
applies the unchanged R377 summarization with the corrected selection rule to
the 60 immutable records.

### Conditional held-out execution

- If development analysis is invalid, stop as `ANALYSIS-INVALID`.
- If no candidate meets the corrected development gate, stop as
  `STOP-DEVELOPMENT-NO-CANDIDATE`; execute zero new physical trajectories.
- If exactly one candidate is selected, execute the sealed 30-record
  evaluation bank once with the unchanged R377 runtime.
- Classify held-out evidence with the corrected classification (settling no
  worse than local, all other R377 thresholds unchanged). Terminal classes
  keep the Gate B-2 taxonomy; a valid positive result requires the selected
  candidate to clear every registered primary, no-harm, and guard criterion.
- Formal retry is false. A retained failure or completed analysis closes
  R378.

### Capacity and launch contract

- Reused development work: 60 records / 3000 environment steps from the
  immutable R377 artifacts; no new execution.
- Maximum new work: 30 held-out records / 1500 environment steps,
  conditional on development selection.
- Runtime anchor: R377 completed 60 records in 449.2381028229138 s. The
  half-sized held-out bank has a 224.619 s point estimate and a 336.929 s
  upper planning estimate at safety factor 1.5.
- Whole-host budget: one WSL Python process, one native thread per numerical
  library, no concurrent research Python process, no competing paper-line
  reservation.
- Rehearsal entry:
  `/home/wya/andes_venv/bin/python scripts/run_r378_gate_b2_correction.py rehearse`.
- Seal entry:
  `/home/wya/andes_venv/bin/python scripts/run_r378_gate_b2_correction.py prepare`.
- Sole formal ANDES entry:
  `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r378_gate_b2_correction.py execute --expected-seal-sha256 <sha256>`.
- Before formal launch: focused Windows and WSL tests, Ruff, diff check,
  R378 round preflight, capacity evidence, rehearsal, and seal verification
  must all pass.

## Gate

One question: under the corrected settling rule, does the immutable R377
development evidence yield a valid eligible high-pass damping candidate, and,
if so, does that candidate clear the frozen held-out primary and no-harm
gate?

- `ANALYSIS-INVALID`: identity/provenance/hash/contract violation or malformed
  analysis; no scientific performance interpretation.
- `STOP-DEVELOPMENT-NO-CANDIDATE`: valid corrected development analysis but no
  eligible candidate; no held-out execution and no training.
- A retained Gate B-2 held-out stop class: development selects a candidate,
  but the one-shot held-out analysis does not clear all frozen criteria.
- `DETERMINISTIC-DECOUPLING-PASS`: the selected candidate clears all frozen
  held-out criteria. This authorises only the next registered non-learning,
  time-varying-headroom gate; it does not authorise MARL training.

## 资产保护契约

- Protected and immutable: all R364-R377 sources, plans, seals, executions,
  analyses, feeds, claims, hashes; the R377 development execution in
  particular is read-only input whose performance fields stay forbidden
  until the R378 seal is fixed.
- Allowed additions only: one R378 correction module, one R378 create-only
  runner, focused tests, R378 round records, the R378 result root, and the
  required claim/feed/navigation records after terminal analysis.
- No controller gain, action bound, observation, disturbance, scenario bank,
  endpoint, threshold (other than the corrected settling rule), selection
  rule (other than settling), or physical model may change in R378.
- No overwrite and no formal retry. Every formal artifact is create-only and
  hash-bound.

## Cross-references

- CLM-1030 / R377: terminal stop caused by the unsatisfiable settling-floor
  rule; the high-pass diagnostics are descriptive, not efficacy.
- CLM-1025 / R376: stopped Laplacian-sync family; context for the successor
  law.
- R377 sealed contract, plan, seal, and immutable development execution are
  the only performance-bearing parent artifacts.
