---
round: R273
state: completed
opened: '2026-07-26'
closed: '2026-07-26'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R273 plan — attribute R272 baseline TDS failures before controller work

**Status**: ACTIVE
**Opened**: 2026-07-26
**Driver**: Determine whether R272's shared zero-support failures belong to
the Kundur disturbance envelope or are introduced by the zero-command ESD1
DAE, then make the smallest correctness optimization justified by that cause.
**Parent**: CLM-0570
**Question**: Q-0035
**Reserved claim**: CLM-0575

## TL;DR

R272's large complete-pair frequency signal is not interpretable until the
matched baseline's 3/20 TDS failures are attributed.  R273 performs a
completion-only differential experiment between original V4 and the
identical-DAE zero-support storage environment.  It freezes the three shared
failures and four signed/location controls from the immutable R272 bank,
retains every row, records solver/DAE initialization state, and makes no PI,
gain, capacity, placement, topology, or learning change.

If both plants fail the same registered cases, R273 maps the positive-Bus14
completion boundary and may add a reusable feasibility-screen contract for a
future bank, but it will not rerun the authority experiment.  If only the
storage DAE fails, R273 may implement one test-first initialization/model
repair and rerun the same diagnostic rows under a new source hash.  Mixed or
unresolved evidence stops without optimization.

## Snapshot at plan-time (oracle as of 2026-07-26)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-run render.py if you want to refresh STATE.md, but -->
<!-- keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify
  1e-9 bit-identical from WSL before landing.
- Q-0026 [opened R260] Will the Archive Index actually be queried
  (lazy-extraction loop signal)?
- Q-0035 [opened R272] Are R272's formal TDS failures caused by the
  disturbance envelope or by the added zero-support ESD1 DAE?

## Recently Closed (last 3)

- Q-0034 closed-partial @ R272, by CLM-0570 — the active-power gate is
  INVALID at bank level; complete-pair improvements are diagnostic only.
- Q-0033 closed-positive @ R271, by CLM-0565 — current M/D-only proxies
  require explicit power/energy authority for sustained restoration.
- Q-0032 closed-negative @ R270, by CLM-0555 — the current M/D library has
  no material common-mode IAE margin above droop.

## Falsifiable objective

Using completion and solver diagnostics only, determine whether R272's
matched zero-support TDS failures are caused by an infeasible disturbance
envelope, by the added zero-command ESD1 DAE, or by both, before any further
active-power controller comparison.

## Methodology

## Public seams and feedback loop

The PI has already authorized the Q-0035 diagnostic and the existing R272
public environment seams:

1. `AndesMultiVSGEnvV4.reset()` / `step()` for original V4.
2. `AndesMultiVSGEnvV4Storage.reset()` /
   `step(..., bess_power_request_pu=zeros)` for identical-DAE zero support.
3. A reusable R273 evaluator/CLI that returns one immutable row per
   plant/scenario with completion, requested/completed steps, last simulator
   time, TDS failure, initialization state, DAE dimensions/model counts,
   frozen hashes, and captured solver diagnostics.

The first red-capable loop is the 10-step `random_00` differential integration
test in WSL.  It asserts that a zero-command storage DAE should not introduce
an extra failure relative to original V4 and reports both arms explicitly.
The same command is then tightened into the reusable diagnostic runner.  No
mocking is permitted; ANDES is the system boundary.

## Frozen inputs

### Plants

- `original_v4`: unchanged `AndesMultiVSGEnvV4`.
- `storage_zero`: unchanged `AndesMultiVSGEnvV4Storage` using the R272
  actuator contract and an all-zero BESS request on every step.
- Both use environment seed 42, zero normalized M/D action, M=200, D=100,
  unchanged 0.2-s control timing, unchanged solver configuration, and the
  same disturbance definition.

### Attribution cases

The immutable R272 bank SHA-256 remains
`184d1233b0e75482b444e513857c3d28dc7d7af2f7fe9d0a59ba09da146901c7`.
No new random case is selected.

| Role | Scenario | Disturbance | R272 zero-support status |
|---|---|---|---|
| shared failure | random_00 | PQ_Bus14 +2.2000 pu | 6/300 failed |
| shared failure | random_05 | PQ_Bus14 +2.2772 pu | 6/300 failed |
| shared failure | random_10 | PQ_Bus14 +2.1841 pu | 6/300 failed |
| small positive control | random_01 | PQ_Bus14 +0.4419 pu | 300/300 |
| small negative control | random_11 | PQ_Bus14 -0.6458 pu | 300/300 |
| large negative control | random_16 | PQ_Bus14 -2.1415 pu | 300/300 |
| location control | random_09 | PQ_Bus15 +2.1086 pu | 300/300 |

The three failure rows test reproducibility.  The controls separate sign,
magnitude, and bus location without using any droop+PI endpoint.

### Core budget and order

- Feedback loop: at most 4 ten-step trajectories.
- Core attribution: exactly 14 rows = 7 scenarios x 2 plants, 300 requested
  steps each; failed rows still count.
- Scenario order is the table order.  Plant order alternates by scenario to
  avoid a systematic execution-order confound.
- One real-ANDES process at a time.  `--resume` may reuse a row only when
  every scenario, plant, contract, source, plan, runner, environment, and
  solver hash matches.
- No endpoint other than completion/solver/initialization diagnostics enters
  the classification.

## Required diagnostics and provenance

Every row must retain:

- scenario identity and exact `delta_u`;
- plant identity and environment seed;
- requested/completed step count, `tds_failed`, last completed simulator
  time, wall time, and captured ANDES termination text;
- power-flow/setup success;
- DAE differential/algebraic dimensions, finite-state checks, relevant model
  counts, nominal-frequency metadata, solver configuration, and hashes of
  initial DAE vectors when available;
- exact M/D values and, for `storage_zero`, zero requested/commanded/actual
  power plus unchanged SOC/energy;
- R272 bank/contract hashes, repository head, package versions, plan/source/
  runner hashes, per-row SHA-256, and an immutable summary/provenance pair.

The first seal is written after code/tests/preflight and before the first core
row.  Development feedback-loop rows use a separate namespace and cannot
determine the final classification alone.

## Ranked hypotheses

These predictions are registered before running the differential loop:

1. **H1 — disturbance-envelope infeasibility.**  If the large positive
   Bus14 load steps exceed the plant/solver feasibility envelope, original V4
   and storage-zero will fail the same three cases at similar simulator times,
   while all four signed/location controls complete.
2. **H2 — zero-command storage DAE confound.**  If the added PV/ESD1 states
   cause the failure, original V4 will complete one or more shared-failure
   cases that storage-zero fails under identical disturbances.
3. **H3 — mixed cause.**  If both mechanisms contribute, at least one failure
   is shared but another differs by plant, or the completion boundary differs
   materially between plants.
4. **H4 — runner/order nondeterminism.**  If initialization or execution order
   causes the symptom, pinned repeated feedback-loop rows will disagree.

## Conditional optimization

### If H1 is supported

Do not change the controller or force extreme cases to converge.  Map the
positive-Bus14 60-s completion boundary for both plants with a deterministic
four-iteration bisection between the registered complete point 0.4419 pu and
failed point 2.1841 pu.  Each midpoint is derived only from prior completion,
not performance.  Retain both plant rows at every midpoint.

R273 may then add a reusable, test-first feasibility-screen contract that:

- separates scenario-generation evidence from controller evaluation;
- retains every screened failure and reports the excluded fraction;
- stratifies by sign and location;
- freezes the feasible envelope before any controller trace;
- never silently drops an infeasible scenario.

It must not generate or evaluate a new authority bank in R273.

### If H2 is supported

Minimize the DAE difference, write a failing WSL integration test at the
existing reset/step seam, implement only the smallest initialization/model
fix, preserve default V4 bit-identically, and rerun the same 14 rows under a
new seal.  Capacity, placement, gains, timing, solver settings, and scenario
inputs remain frozen.

### If H3 or H4 is supported

Instrument only the boundary that distinguishes the remaining hypotheses.
No optimization is allowed until a deterministic cause is isolated.

## Gate

- **ENVELOPE-INFEASIBLE**: both plants reproduce all three registered
  failures, both complete all four controls, completion vectors match, and
  provenance is valid.
- **STORAGE-DAE-CONFOUND**: original V4 completes at least one registered
  shared-failure case that storage-zero deterministically fails, with all
  frozen inputs and provenance matching.
- **MIXED**: deterministic completion vectors differ but at least one
  registered failure is common to both plants.
- **UNRESOLVED/INVALID**: nondeterminism, initialization/provenance mismatch,
  missing diagnostics, or inconsistent repeat evidence prevents attribution.

The boundary-map/repair evidence is secondary to this primary attribution.
No R273 outcome opens Gate 2 or supports a controller-performance claim.

## Verification

- `python memory/tools/round_preflight.py R273`
- `python memory/tools/dual_metric_lint.py`
- focused Windows tests for pure diagnostic/serialization behavior
- focused WSL tests for real V4/storage differential behavior
- existing V4 1e-9 regression
- `python -m pytest tests -q`
- Ruff on every new/changed Python file
- exact artifact/hash audit
- `python memory/tools/validate.py`
- `python memory/tools/render.py`
- `python memory/tools/research_goal.py --json`

## Asset protection

- Preserve every R272 bank, contract, seal, log, trace, summary, provenance,
  and the stopped first-seal artifacts.
- Preserve default V4 behavior, historical checkpoints/results, legacy 50-Hz
  control semantics, and explicit 60-Hz physical reporting.
- Add only R273-specific evaluator/test/result namespaces.
- Preserve all unrelated tracked and untracked user changes.
- No staging, commit, push, PR, manuscript, figure, RL, GNN, topology,
  stability-certificate, cross-simulator, or HIL work.

## Cross-references

- Q-0035
- CLM-0570 — R272 active-power gate INVALID
- CLM-0575 — reserved R273 attribution finding
- `memory/rounds/R272/verdict.md`
- `results/r272_active_power_authority_v2/active_power_authority_summary.json`
- `docs/adr/0006-dual-frequency-reporting-preserve-v4.md`
