---
round: R368
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds:
- R367
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R368 plan — output-safe successor for deterministic headroom

**Opened**: 2026-08-12
**Driver**: Complete the unchanged R367 scientific contract in a fresh formal
attempt after R367 failed before analysis solely because its progress printer
raised `BrokenPipeError` when the external output pipe closed.
**Parent**: Q-0103; CLM-0980; aborted R367

## TL;DR

Workload: `evidence`.  Preserve the R367 contract, controller, classifier,
scenarios, thresholds, serial budget, and no-training rule byte-for-byte.
Add one thin successor runner whose progress/final console output is best-effort
and cannot invalidate simulation.  Rehearse, remeasure, reseal, and execute one
new immutable attempt.  Do not reuse partial R367 records; none were published.

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

### Frozen scientific contract

- Import `build_contract`, `summarise_record`, `classify_summaries`, and the
  physical scenario-arm executor from the preserved R367 sources.  Assert the
  contract hash equals the prospectively registered R367 contract before every
  stage.  No scientific field may be changed in R368.
- Execute fresh zero-action plus nine frozen deterministic candidates over the
  same eight balanced strong development scenarios, 30 steps, seed 42,
  heterogeneous damping `(70,90,130,150)`, 60-Hz physical endpoints, identical
  action mapping, bounds, slew, and common-frequency guards.
- Keep the global 10% deterministic-efficacy threshold and the non-deployable
  best-of-nine oracle's 5% incremental-headroom, nonconstant-action, and
  distinct-candidate thresholds unchanged.  Training remains forbidden.
- Unit of analysis, inference ceiling, outcome-leakage limitation, comparison
  identifiability, classification tree, and stay-out claims are exactly R367.

### Failure diagnosis and bounded repair

- R367 created an immutable attempt and failed after 146.06 seconds with
  `BrokenPipeError: [Errno 32] Broken pipe`; no execution, analysis, or
  scientific endpoint artifact was written.  The failure arose when the
  external command pipe closed while the runner printed an operational count.
- The R368 runner writes no per-job console progress.  Its optional terminal
  message uses a public `safe_emit` seam that catches `BrokenPipeError` and
  redirects subsequent console output to the operating-system null device.
  Simulation and artifact writes never depend on stdout.
- R367 attempt/failure/seal/capacity artifacts remain immutable and excluded
  from R368 input except as the diagnosed engineering parent.  No partial
  trajectory, result, selection, or endpoint is reused.

### Ask Matt TDD seams

- Route: current-context `/tdd`; no new task or handoff.
- Public seam 1: `safe_emit` returns false rather than raising when stdout is a
  broken pipe.
- Public seam 2: successor contract identity equals the preserved R367
  scientific contract while round/output/provenance identities are fresh.
- Public seam 3: create-only rehearsal, capacity, seal, attempt, execution,
  analysis, and manifest paths reject replacement.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r368_deterministic_headroom.py execute --expected-seal-sha256 <sha256>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r368_deterministic_headroom.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`; verify the same plan/question,
  source/parent/contract hashes, installed ANDES/case, process, output-absence,
  and output-safe seam used by formal execution without a physical trajectory.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- wsl_python_processes: 1
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R368/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0
- One fresh five-step zero-action scenario measures wall time, resident memory,
  free disk, host/WSL memory, installed runtime, and competing processes.  It
  cannot inspect a scientific classification.
- Formal completion requires all 80 fresh scenario-arm records, summaries,
  decision, and manifest with sidecars.  There is no scientific early stop,
  retry, or training authority.  During the attempt monitor only process
  liveness and terminal artifact presence; never close its stdout pipe before
  completion and never inspect endpoints early.

## Gate

Use the unchanged R367 tree:
`DETERMINISTIC-AND-HEADROOM-PASS`,
`STOP-DETERMINISTIC-NO-EFFICACY`,
`STOP-NO-CONDITIONAL-HEADROOM`, or `ANALYSIS-INVALID`.
Any engineering/provenance failure is invalid and requires another successor;
no R368 retry is authorized.  Every branch keeps `training_authorized=false`.

## 资产保护契约

Keep all R367 files and artifacts byte-unchanged.  Keep protected environments,
old lines, old results, checkpoints, and training assets unchanged.  Add only
R368 lifecycle artifacts, a thin output-safe successor runner, focused tests,
fresh R368 results, and eventual current-line feed/claim/verdict/navigation.

## Cross-references

- R367 plan and immutable failure record: unchanged scientific contract and
  sole diagnosed engineering failure.
- CLM-0980/R366 and CLM-0975/R365: design and object prerequisites.
- `paper/paralleled_vsg_marl/ROUTE.md#phase-1--strong-deterministic-decoupling`.
