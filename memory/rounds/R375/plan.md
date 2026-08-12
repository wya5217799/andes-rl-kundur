---
round: R375
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R375 plan — deterministic-decoupling identity correction gate

**Opened**: 2026-08-12
**Driver**: Correct the single sealed identity-contract defect that made R374 analytically invalid, then reanalyse its immutable development records before authorising any new held-out physical execution.
**Parent**: CLM-1015, R374, CLM-1010, R373

## TL;DR

R375 is a result-blind correction round, not a new controller search. It changes
only the classifier's expected VSG identifiers from the invalid storage-style
labels `ES1..ES4` to the runtime-and-plan identifiers `VSG_1..VSG_4`; buses,
controller family, gains, scenario banks, endpoints, thresholds, seeds, and
selection rules remain frozen. After a sealed correction contract is created,
R375 reanalyses the immutable 60-record R374 development execution. A new
30-record held-out execution is permitted only if that reanalysis is valid and
selects an eligible distributed candidate. Training remains forbidden.

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

- Four separately actuated VSG agents, ordered exactly as
  `VSG_1, VSG_2, VSG_3, VSG_4`, at buses `12, 16, 14, 15`.
- The R374 zero controller, local diagonal PI controller, and four distributed
  cross-coordinate candidates are retained without modification.
- Candidate gains remain the Cartesian product
  `k_s in {0.5, 1.0}` and `k_c in {0.5, 1.0}`.
- Development/evaluation scenario definitions, 50-step horizon, `dt=0.2`,
  seed 42, endpoints, metrics, thresholds, selection order, and terminal
  classification rules remain those sealed by R374.
- There is no neural residual, reward optimisation, policy update, replay
  buffer, or training trajectory in this round.

### Result-blind identity correction

The correction implementation shall start from the sealed R374 contract and
permit exactly two administrative differences: `round` becomes `R375`, and
`expected_vsg_idx` becomes `VSG_1..VSG_4`. An independent validator shall prove
that all remaining contract fields are semantically equal. It shall also prove,
without reading performance arrays, that the R374 plan identity, every runtime
record identity, and the corrected classifier identity agree on both VSG order
and bus order. Any other difference or any identity disagreement is terminal
`ANALYSIS-INVALID`.

### Immutable development reanalysis

Only after the corrected contract and parent-artifact hashes have been sealed
may the runner read the R374 development performance records. It shall verify
the recorded SHA-256 sidecars, copy no records, mutate no parent artifact, and
apply the unchanged R374 summarisation and development-selection functions to
the 60 immutable records under the corrected identity contract.

### Conditional held-out execution

- If development analysis is invalid, stop as `ANALYSIS-INVALID`.
- If no candidate meets the frozen development gate, stop as
  `STOP-DEVELOPMENT-NO-CANDIDATE`; execute zero new physical trajectories.
- If exactly one candidate is selected by the frozen rule, execute the sealed
  30-record evaluation bank once, using the unchanged R374 runtime and the
  corrected identity contract.
- Classify held-out evidence with the unchanged R374 rules. A valid positive
  result requires the selected distributed controller to clear every registered
  efficacy, decoupling, no-harm, completion, and identity threshold. Other
  valid terminal outcomes retain the R374 stop taxonomy.
- Formal retry is false. A retained failure or completed analysis closes R375.

### Capacity and launch contract

- Reused development work: 60 records / 3000 environment steps from immutable
  R374 artifacts; no new execution.
- Maximum new work: 30 held-out records / 1500 environment steps, conditional
  on development selection.
- Runtime anchor: R374 completed 60 records in 447.5055512560066 s. The
  one-half-sized held-out bank therefore has a 223.753 s point estimate and a
  335.630 s upper planning estimate at safety factor 1.5.
- Whole-host budget: one WSL Python process, one native thread per numerical
  library, no concurrent research Python process, no competing paper-line
  reservation.
- Capacity evidence is written to `memory/rounds/R375/capacity_evidence.json`
  and must validate before sealing.
- Rehearsal entry:
  `/home/wya/andes_venv/bin/python scripts/run_r375_deterministic_decoupling_identity_correction.py rehearse`.
- Seal entry:
  `/home/wya/andes_venv/bin/python scripts/run_r375_deterministic_decoupling_identity_correction.py prepare`.
- The sole formal ANDES entry is
  `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r375_deterministic_decoupling_identity_correction.py execute --expected-seal-sha256 <sha256>`.
- Before formal launch: targeted Windows and WSL tests, Ruff, diff check,
  R375 round preflight, rehearsal, and seal verification must all pass.

## Gate

The round answers one question: after correcting only the classifier identity,
does immutable R374 development evidence yield a valid eligible distributed
controller, and, if so, does that controller clear the frozen held-out gate?

- `ANALYSIS-INVALID`: identity/provenance/hash/contract violation or malformed
  analysis; no scientific performance interpretation.
- `STOP-DEVELOPMENT-NO-CANDIDATE`: valid corrected development analysis but no
  eligible candidate; no held-out execution and no training.
- A retained R374 held-out stop class: development selects a candidate, but the
  one-shot held-out analysis does not clear all frozen criteria.
- `DETERMINISTIC-DECOUPLING-PASS`: the selected distributed controller clears
  all frozen held-out criteria. This authorises only the next registered
  non-learning, time-varying-headroom gate; it does not authorise MARL training.

## 资产保护契约

- Protected and immutable: all R373/R374 sources, plans, seals, executions,
  analyses, failures, feeds, claims, and hashes; all existing controller,
  environment, bridge, and energy-port implementations.
- Allowed additions only: one R375 correction/validation module, one R375
  create-only runner, focused tests, R375 round records, the R375 result root,
  and the required claim/feed/navigation records after terminal analysis.
- The R374 development execution is read-only input. Its performance fields
  remain forbidden until the R375 seal is fixed.
- No controller gain, action bound, observation, disturbance, scenario bank,
  endpoint, threshold, selection rule, or physical model may change in R375.
- No overwrite and no formal retry. Every formal artifact is create-only and
  hash-bound.

## Cross-references

- CLM-1015 / R374: retained analytical invalidity caused by classifier identity
  drift after all 60 development trajectories completed.
- CLM-1010 / R373: four-VSG runtime identity and authority parent.
- R374 sealed formal contract and immutable development execution are the only
  performance-bearing parent artifacts.
