---
round: R365
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R365 plan — per-VSG object, information, and action-authority gate

**Opened**: 2026-08-12
**Driver**: Before reusing the legacy four-agent training form, verify that the
ANDES V4 candidate actually contains four independently actuated VSG objects
with causal local-neighbour information and measurable differential dynamics.
**Parent**: Q-0101; CLM-0970; R364

## TL;DR

Workload: `evidence`.  Execute one non-learning, eight-arm, six-second ANDES
intervention gate.  PASS requires all five object/action conditions on the
same V4 candidate and authorizes only a matched deterministic baseline;
otherwise return a typed STOP.  This round cannot start training or claim
controller, coordination, decoupling, or MARL performance.

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0100 closed-positive @ R363, by CLM-0965 — On the exposed development bank, does adding a common residual-power channel to the three-edge zero-common action basis enlarge the per-case physical action-space headroom, showing that the zero-common residual contract itself (rather than information) limits the R358 feasibility?
- Q-0099 closed-negative @ R362, by CLM-0960 — On the exposed development bank, does replacing the one-hop neighbour snapshot messages with frozen R341-model causal prediction trajectories (DMPC-style shared prediction) let a pre-registered tuning-free non-neural map family recover both registered endpoint gates, showing learnable structure that R359, R360, and R361 could not reach from endpoint-only or snapshot-message information?
- Q-0098 closed-negative @ R361, by CLM-0955 — On the exposed development bank, does extending the exact fifteen-field edge-actor information path with one-hop neighbour messages let a pre-registered tuning-free non-neural map family recover both registered endpoint gates, showing learnable structure that R359 and R360 could not reach from endpoint-only information?

## Methodology

### Research Supervisor design gate

- **Decision question**: does the current V4 candidate satisfy the minimum
  physical-object, information, differential-dynamics, and action-authority
  premises needed before any direct per-VSG M/D learner is meaningful?
- **Object**: four ANDES `GENCLS` VSG units with ordered identities
  `VSG_1..VSG_4`, buses `(12,16,14,15)`, runtime actors `0..3`, and a two-entry
  normalized action `(delta-M, delta-D)` per actor.
- **Identified estimand**: deterministic finite-probe existence and interface
  validity on this exact V4 plant and disturbance.  This is not an estimate of
  controller efficacy, a deterministic-method effect, message value, learning
  value, residual value, stability, robustness, or population performance.
- **Comparison-identifiability decision**: `QUALIFY`.  Paired same-disturbance
  counterfactuals identify whether each registered action reaches its declared
  device and whether the connected plant reacts above repeat-run numerical
  drift.  They do not identify an algorithm-family effect.

### TDD seams confirmed by the active route

The five accepted questions in `ROUTE.md#first-experiment` are the pre-agreed
test seams.  Tests may bind only to a new pure contract/classifier module and a
new stable R365 execution adapter.  Real-ANDES verification uses the existing
public `AndesMultiVSGEnvV4(config=...)`, `reset`, `step`, returned observation,
and returned `info` seams.  Protected `base_env.py`, `andes_vsg_env_v4.py`,
`train.py`, `v4_config.py`, and `paper_grade_axes.py` remain unchanged.

### Frozen plant and execution conditions

- Environment: `AndesMultiVSGEnvV4` with explicit default V4 configuration,
  `random_disturbance=False`, `comm_fail_prob=0`, `comm_delay_steps=0`, and all
  observation augmentations disabled.
- Disturbance: canonical `LS1_DELTA_U` imported from
  `andes_common.paper_constants`; `DISABLE_TOGGLER=1` removes the unrelated
  built-in line-trip event.
- Timing: 30 control decisions at 0.2 seconds, six seconds total after the
  disturbance.  Physical reporting uses `freq_hz_physical` and records the
  simulator's 60-Hz base rather than silently using the legacy 50-Hz label.
- No reward enters a gate.  No old checkpoint, trajectory, numerical result,
  claim, or six-axis composite enters the attempt.
- Every arm runs in a fresh environment with seed 42 and records device
  identity, bus, current observation, commanded normalized action, executed
  M/D and deltas, frequency, power, time, and failure state.

### Frozen eight-arm intervention bank

1. `zero_a` and `zero_b`: repeated homogeneous zero-action traces, used only
   to establish numerical repeatability floors and the paired baseline.
2. `single_0` through `single_3`: exactly one actor holds normalized
   `(delta-M, delta-D)=(+0.25,-0.10)` while the other three hold zero.
3. `fingerprint`: all four actors hold distinct bounded commands
   by cycling one positive `0.25` basis pulse through the ordered eight
   actor-channel coordinates during the first eight decisions, then returning
   to zero.  This makes the full action-to-readback rank identifiable without
   a common scalar.
4. `mismatch`: zero action with the explicit per-device damping baseline
   `(70,90,130,150)` and otherwise unchanged V4 physics.

The four `single_i` commands are constant over the short trace; the fingerprint
alone uses the frozen eight-step basis sequence.  This bank is an interface
intervention, not a tuned controller and not a performance comparison.

### Endpoints and numerical floors

- **Identity**: four unique VSG indices, four expected buses, and one-to-one
  actor/device ordering must hold before stepping.
- **Action mapping**: executed M/D must equal the frozen zero-centred decoder
  within `1e-9` device units.  In each single-agent arm all non-target M/D
  channels remain at baseline within `1e-9`; the fingerprint's complete
  normalized-action-to-readback map has rank eight.  Bounds and physical
  clamps must hold at every step.
- **Information**: each returned vector has exactly seven fields and equals,
  within `2e-6`, the same-step normalized local power/frequency/RoCoF plus the
  two declared ring-neighbour frequency/RoCoF values.  Communication is live,
  no global or augmented field is present, and source/config hashes freeze the
  no-delay construction path.
- **Noise floors**: separately for physical frequency and VSG active power,
  take ten times the maximum pointwise difference between `zero_a` and
  `zero_b`, with absolute floors `1e-7 Hz` and `1e-8 p.u.` respectively.
- **Network transmission**: every `single_i` must change at least one
  non-target VSG frequency or power relative to `zero_a` above its applicable
  frozen floor.
- **Differential dynamics**: the mismatch arm must have pairwise physical
  frequency spread and differential-frequency energy above repeat-run noise;
  at least one pairwise frequency or power differential must contain two
  above-floor direction reversals.  This is the qualitative oscillatory-mode
  premise, not a damping or decoupling improvement claim.
- **Validity**: all arms complete 30 steps at the declared timing without
  TDS failure, non-finite data, bound violation, or identity drift.

### Decision tree

- `PER-VSG-OBJECT-GATE-PASS`: every identity, mapping, information,
  differential-dynamics, network-transmission, bound, and validity check
  passes.  Only a separately registered strong deterministic baseline and
  residual-headroom/direct-MARL design gate becomes eligible.
- `STOP-OBJECT-MAPPING`: device identity, ordering, independent M/D readback,
  or rank fails.
- `STOP-INFORMATION-CONTRACT`: observation ownership, dimension, timing, or
  leakage guard fails.
- `STOP-NO-DIFFERENTIAL-DYNAMICS`: the registered mismatch lacks the required
  above-noise differential transient.
- `STOP-NO-ACTION-AUTHORITY`: one or more independent actions lack a
  network-transmitted effect above noise.
- `ANALYSIS-INVALID`: execution, hash, inventory, timing, numerical, or
  physical-bound integrity fails.  Preserve the attempt and do not repair or
  retry it in place.

### Navigation reconciliation

Before source sealing, update only this active line's navigation to reflect
the user's settled method choice: the first learning candidate is direct
per-VSG M/D MARL using the validated legacy four-agent form.  A deterministic
coordinator remains the mandatory strong baseline, but residual MARL is no
longer the default architecture and becomes an optional later ablation only.
This correction authorizes no training and carries no scientific result.

### Ask Matt engineering handoff

- Add one pure R365 contract/classifier module, one stable create-only runner,
  and focused synthetic tests through the seams above.
- The runner exposes only `rehearse`, `measure-capacity`, `prepare`, and
  `execute`; it exposes no training, reward tuning, checkpoint, or alternate
  output command.
- Red-green verification, compilation, `git diff --check`, and project
  preflight are required before the physical attempt.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r365_per_vsg_object_gate.py execute --expected-seal-sha256 <sha256>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r365_per_vsg_object_gate.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`; verify the same plan/question,
  source, installed ANDES/case, contract, process, and output-absence guards
  used by formal execution without creating a physical trajectory.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- wsl_python_processes: 1
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R365/capacity_evidence_v2.json`
- host_process_budget: 1
- other_reserved_processes: 0
- rehearsal: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r365_per_vsg_object_gate.py rehearse`
- capacity: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r365_per_vsg_object_gate.py measure-capacity`
- seal: `/home/wya/andes_venv/bin/python scripts/run_r365_per_vsg_object_gate.py prepare`
- formal entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r365_per_vsg_object_gate.py execute --expected-seal-sha256 <sha256>`
- worker processes: 1; native numerical threads per process: 1; WSL Python
  processes: 1.  Serial execution is frozen because the bank is small and
  avoids whole-host contention.
- capacity evidence: `memory/rounds/R365/capacity_evidence.json`; one
  representative five-step trace measures wall time, memory, disk, installed
  runtime, and confirms no competing formal process.  It cannot inspect a
  scientific classification.
- formal outputs are create-only under
  `results/research_loop/r365_per_vsg_object_gate/`.  One immutable attempt is
  allowed; any collision, source drift, runtime drift, or active competing
  research process returns `HOLD` or `ANALYSIS-INVALID` without overwrite.
- Initial execution status: `HOLD` until implementation, focused tests,
  rehearsal, capacity record, source seal, and a second preflight all pass.

### Pre-attempt correction log

- The first create-only rehearsal correctly recorded
  `physical_trajectory_executed=false`, but its consumer incorrectly required
  that negative assertion to equal `true`; the capacity command stopped before
  importing or constructing the environment.  Preserve `rehearsal.json` and
  bind all later stages to `rehearsal_v2.json`, whose focused regression test
  requires all positive guards to pass and the physical-trajectory flag to
  remain false.  No scientific arm, capacity trace, or formal attempt existed
  when this correction was registered.
- The first capacity record completed its five-step representative trace but
  omitted the repository preflight's nested host-memory, WSL-memory, and
  empirical-anchor fields.  Preserve `capacity_evidence.json`; bind sealing
  to `capacity_evidence_v2.json`, which adds those resource fields and a
  schema-focused regression test.  The v1 trace was never scientifically
  classified and created no formal attempt.

## Gate

PASS only when all five prospective object/action questions are supported by
the complete immutable eight-arm bank.  Any one failed scientific gate is a
typed STOP; any integrity failure is `ANALYSIS-INVALID`.  No branch in R365
starts training.  A PASS changes the next eligible gate, not the manuscript's
scientific claims.

## 资产保护契约

All old manuscript feeds, claims, checkpoints, trajectories, results,
environment implementations, agents, trainers, deterministic controllers,
and protected evaluation code remain byte-unchanged.  Add only Q-0101/R365,
the active-line navigation correction, one R365 analysis seam, one stable
runner, focused tests, capacity/rehearsal/seal records, one create-only result
tree, and the eventual bound feed/claim/verdict.  Do not edit or execute a
frozen manuscript line and do not push publicly.

## Cross-references

- CLM-0970 / R364 fixed-title object-matched route reset.
- `paper/paralleled_vsg_marl/ROUTE.md#first-experiment`.
- Yang et al., DOI `10.1109/TPWRS.2022.3221439`, as object/action reference
  only; no numerical trajectory is a reproduction target.
