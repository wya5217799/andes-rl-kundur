---
round: R372
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R372 plan — VSG-owned energy-port physical object gate

**Opened**: 2026-08-12
**Driver**: R371 established only a static power-to-torque contract; the real
ANDES plant must now prove zero-action equivalence, one-to-one signed
intervention, actual-power response, and achieved-power energy accounting
before any controller or training work.
**Parent**: CLM-0975, CLM-0990, CLM-0995, CLM-1000; R365, R369, R371

## TL;DR

Workload: `evidence`. Freeze one serial, non-learning, ten-arm, five-step ANDES
object gate. This round first completes a readiness return and seals one
create-only attempt; formal execution remains a separate continuation action.
No controller, reward, learning algorithm, checkpoint, tuning loop, or retry is
present.

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

### Research Supervisor readiness gate

- Decision: is the R371 design ready for one minimal real-ANDES physical object
  attempt without reopening the stopped M/D formulation or importing the
  independent ESD1 object?
- Scientific object: the four governor-free `GENCLS` VSGs `VSG_1..VSG_4` in
  unchanged V4, wrapped by `AndesVSGEnergyPortEnv`; each actor owns exactly one
  system-base incremental active-power request.
- Identified estimand: existence and correctness of the registered physical
  action path on this exact plant under a finite deterministic intervention
  bank. It is not controller efficacy, decoupling improvement, coordination,
  MARL value, stability, robustness, or population performance.
- Current owner: Ask Research Supervisor readiness gate. Engineering return is
  a tested classifier/runner, rehearsal record, capacity record, preflight, and
  immutable seal. Stop after `RUN-READY`; formal execution needs the next
  explicit continuation.

### TDD seams and engineering handoff

- Existing public plant seam: `AndesVSGEnergyPortEnv.reset/step`, confirmed by
  R371 and the active route. No protected V4/base implementation is edited.
- New scientific seam: `build_contract()` and `classify_records(records)` in
  one pure evaluation module. It classifies only complete frozen records.
- Stable execution adapter exposes exactly `rehearse`, `prepare`, and `execute`.
  It has no training, tuning, capacity resize, alternate bank, output-path, or
  retry command.
- Red-green slices cover: frozen arm schedule; passing complete synthetic bank;
  zero-equivalence stop; routing/sign/timing stop; electrical-response stop;
  energy-accounting stop; invalid execution; create-only runner; rehearsal;
  seal binding; and absence of training commands.

### Frozen plant and bank

- Plant: `AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)`,
  seed 42, `DISABLE_TOGGLER=1`, empty `delta_u={}`, default V4 config, no
  observation augmentation, and unchanged 0.2-s decision period.
- Bank has ten fresh-environment arms and five decisions per arm:
  `base_zero`, `port_zero`, then one positive and one negative arm for each
  actor in actor order. Signed arms hold a single request of `+0.04` or
  `-0.04` system pu on their named actor while all other requests are exact
  zero. The magnitude is within the R371-bound per-device power and one-step
  ramp limits and is not tuned against an outcome.
- `base_zero` runs public V4 with exact zero M/D actions. `port_zero` runs the
  wrapper with exact zero power requests. Every other arm runs the wrapper.
- Each row records time, identity, request, projected command, pref write and
  readback, actual `GENCLS.tm`, achieved incremental power, SOC, charged and
  discharged energy, electrical `P_es`, physical frequency, legacy M/D
  readback/action, constraint reasons, completion, and TDS status. Rewards are
  ignored.

### Prospective checks and classification

- `zero_action_equivalence`: `base_zero` and `port_zero` match time, omega,
  electrical power, M and D within the existing deterministic V4 regression
  tolerance `1e-9`; port requests, commands, achieved incremental powers, and
  energy changes are zero within the same tolerance.
- `identity_and_routing`: every arm retains four unique ordered VSG identities;
  only the named target receives a nonzero request, command, pref/torque
  residual, and SOC change. Non-target torque and SOC stay at baseline within
  `1e-9`.
- `sign_timing_and_torque`: the first controlled row already has the registered
  request sign; `pref-baseline = command/omega_sample`; actual torque matches
  the written pref; achieved power equals torque residual times trapezoidal
  endpoint speed, all within `1e-9` and with positive sampled speed.
- `electrical_response`: each signed arm changes the target VSG electrical
  active power relative to `port_zero` above the prospective floor
  `max(1e-9, 10 * zero-action electrical drift)`. The multiplier is inherited
  from the R365 finite intervention gate; the absolute floor is the existing
  V4 deterministic regression tolerance.
- `energy_accounting`: positive achieved power decreases only target SOC and
  accumulates discharged energy; negative achieved power increases only target
  SOC and accumulates charged energy. Independent recomputation from the
  registered system base, device energy, efficiencies, actual achieved power,
  and 0.2-s hold matches telemetry within `1e-9`.
- `validity`: all ten arms complete five decisions, time increments match 0.2 s
  within the existing `1e-6` ANDES timing audit tolerance, all values are
  finite, no TDS failure occurs, no object identity drifts, and every bound,
  SOC, legacy-zero-M/D, source, seal, and output-integrity guard passes.

Decision tree:

- `PHYSICAL-ENERGY-PORT-OBJECT-PASS`: all checks pass. This authorizes only a
  successor bounded actuator-authority/deterministic-design gate.
- `STOP-ZERO-ACTION-DRIFT`: wrapper zero action changes the V4 trajectory or
  energy ledger above the frozen tolerance.
- `STOP-PORT-ROUTING`: identity, one-to-one target isolation, pref resolution,
  or non-target invariance fails.
- `STOP-TORQUE-POWER-SEMANTICS`: sign, timing, sampled-speed conversion,
  actual-torque readback, or achieved-power identity fails.
- `STOP-NO-ELECTRICAL-RESPONSE`: a correctly routed signed torque input lacks
  target electrical-power response above the frozen floor.
- `STOP-ENERGY-ACCOUNTING`: SOC or charge/discharge energy disagrees with
  achieved power or changes a non-target device.
- `ANALYSIS-INVALID`: execution, timing, completeness, source/seal, numerical,
  output, or runtime integrity fails. Preserve the attempt; no in-place patch
  or retry is authorized.

### Experiment efficiency card inputs

- Stage: formal physical object gate, frozen not started after `prepare`.
- Jobs/dependencies: one ordered bank inside one WSL Python process; rehearsal
  precedes seal, and seal precedes formal attempt. No ready work exists outside
  that sequence, so concurrency one is an intentional hard cap rather than a
  derived throughput budget.
- Representative capacity anchor: R365 measured the same V4 reset plus five
  decisions on this host at one process/one native thread in
  `memory/rounds/R365/capacity_evidence_v2.json`. The current rehearsal must
  verify its hash, same installed ANDES/case, same 32-logical-processor and
  33,518,587,904-byte physical-memory host identity, current WSL available
  memory, current disk free space, and absence of another research Python run.
- Artifact cost is measured prospectively by serializing the complete empty-
  value schema for the frozen 50-row bank during rehearsal; launch requires
  current free disk to exceed that measured payload and all fixed seal/result
  metadata. No scientific value is inspected.
- Completion is a complete immutable ten-arm attempt plus analysis and
  manifest. Engineering invalidity interrupts only for declared source/runtime
  drift, active competing research process, output collision, non-finite or
  failed execution, memory/disk safety failure, or integrity error. Retry count
  is zero.
- Operational progress only: process existence and terminal artifact presence.
  The expected duration is quick (below the skill's approximately five-minute
  class) based on ten serial copies of the measured R365 five-step anchor; wait
  once near completion rather than polling scientific fields.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r372_energy_port_object_gate.py execute --expected-seal-sha256 <sha256>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r372_energy_port_object_gate.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`; verify plan/parent/source hashes,
  installed ANDES/case, contract closure, current host resources, competing
  processes, output absence, projected artifact bytes, and zero physical
  trajectory without creating a formal attempt or result.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, contract_closed, capacity_anchor, current_host, competing_process_absence, artifact_fit, physical_trajectory_executed_false
- wsl_python_processes: 1
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R372/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0
- seal: `/home/wya/andes_venv/bin/python scripts/run_r372_energy_port_object_gate.py prepare`
- Formal outputs are create-only under
  `results/research_loop/r372_energy_port_object_gate/`; one attempt, zero
  automatic retries, and no alternate output path are authorized.
- Initial readiness: `HOLD` until implementation, focused tests, project
  preflight, real same-path rehearsal, capacity record, source seal, repeated
  preflight, Ruff, and `git diff --check` pass.

## Gate

This continuation stops at readiness. `RUN-READY` requires every plan,
implementation, test, rehearsal, capacity, source/runtime, resource,
create-only, and preflight check above plus an immutable seal. `MEASURE-FIRST`
is allowed only if the current rehearsal reveals a named resource unknown that
can be resolved without a scientific trajectory. Any authority, contract,
runtime, capacity, source-drift, process-conflict, or safe-measurement blocker
returns `HOLD`. Passing readiness does not execute the formal attempt.

## 资产保护契约

- Byte-unchanged: `base_env.py`, `andes_vsg_env_v4.py`, V4 configuration,
  storage environment, training/agent code, old checkpoints, old results,
  prior claims/feeds/verdicts, and every other manuscript line.
- Allowed additions: one pure R372 classifier, one stable R372 runner, focused
  tests, R372 rehearsal/capacity/seal records, and the reserved future
  create-only result root. No feed/claim/verdict/navigation update occurs
  before terminal scientific output exists.
- No ESD1 instance, controller, reward, training, checkpoint, tuning, topology
  variation, communication failure, or old outcome enters the gate.

## Cross-references

- `CLM-0975`: four V4 VSG identities and public physical reporting.
- `CLM-0990`: direct per-VSG M/D learning remains stopped.
- `CLM-0995`: energy-port direction selected only with object repair.
- `CLM-1000`: static actor/VSG/port, power-to-torque, and energy contract.
- `paper/paralleled_vsg_marl/ROUTE.md#current-gate`: active physical gate and
  immediate stop conditions.
