---
round: R373
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R373 plan — bounded VSG energy-port actuator-authority gate

**Opened**: 2026-08-12
**Driver**: R372 proved the four VSG-owned ports exist, but not that their
bounded power can influence the common and three differential frequency modes
over a disturbed dynamic horizon; this must be established before selecting or
tuning a deterministic coordinator.
**Parent**: CLM-0975, CLM-0990, CLM-1000, CLM-1005; R365, R369, R371, R372

## TL;DR

Workload: `evidence`. Freeze one serial, non-learning, 30-arm ANDES authority
bank over three preregistered conditions. Paired signed constant interventions
identify a four-by-four physical mode-response matrix, while duplicated zero
arms measure deterministic numerical noise. This continuation implements and
tests the classifier and create-only runner, performs a no-trajectory
rehearsal, and seals one formal attempt. It stops at `RUN-READY`; it does not
execute the formal bank, design a controller, or train.

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

### Research Supervisor design gate

- Decision: can one prospective experiment distinguish useful bounded
  authority on the validated four VSG-owned power ports from mere setpoint
  write-through, numerical drift, unsafe energy use, or post-outcome action
  selection?
- Scientific object: the unchanged R372 four-port V4 object. Each fresh arm
  uses `AndesVSGEnergyPortEnv`; the independent GFL ESD1 object and stopped
  inertia/damping action path remain absent.
- Estimand: the paired signed dynamic response from each registered input mode
  to common/differential VSG frequency and electrical-power modes on the fixed
  finite bank. This is actuator authority only, not controller efficacy,
  decoupling improvement, communication value, MARL value, robustness, or
  population inference.
- Primary owner: Ask Research Supervisor `Design` gate. Ask Matt routes the
  bounded engineering return through a small test-first implementation. The
  return is accepted only when plan, pure classifier, runner, tests,
  no-trajectory rehearsal, capacity record, preflight, and immutable seal agree.

### Frozen conditions and action modes

- Plant: unchanged `AndesMultiVSGEnvV4`, seed 42,
  `random_disturbance=False`, `comm_fail_prob=0`, `comm_delay_steps=0`,
  `DISABLE_TOGGLER=1`, default 0.2-s decision period, and 40 decisions per arm.
- Conditions are fixed before outcomes: nominal (`delta_u={}`), a +0.5-system-pu
  load increment at `PQ_Bus14`, and the same increment at `PQ_Bus15`. They are
  a bounded design bank, not a sealed generalization population.
- Device order is `VSG_1..VSG_4` at buses `[12, 16, 14, 15]`. Four linearly
  independent input/output coordinates are fixed in that order:
  `common=[1,1,1,1]`, `inter_area=[1,1,-1,-1]`,
  `local_area_1=[1,-1,0,0]`, and `local_area_2=[0,0,1,-1]`.
- Each condition has two fresh exact-zero repeats plus positive and negative
  constant interventions on every mode: ten arms per condition, 30 total.
  Every nonzero component is exactly 0.04 system pu. This is within the R371
  per-device power and first-step ramp limits and is inherited from the
  outcome-blind R372 intervention magnitude, not selected from this outcome.
- Rewards are ignored. Every row retains identity, request, projected command,
  pref/torque readback, achieved incremental power, SOC and energy, saturation,
  physical frequency, electrical VSG power, legacy M/D action, time,
  completion, and TDS status.

### Prospective analysis

- Projection of a four-device signal `x` on mode `b` is
  `(b^T x)/(b^T b)`. For each condition and input mode, the central signed
  response is one half of the positive-minus-negative projected trajectory.
  This yields a full four-input/four-output response matrix without selecting a
  favorable action after outcome access.
- `execution_validity`: all-and-only 30 arms complete 40 finite decisions;
  identities, condition payloads, 0.2-s timing, request schedules, source/seal
  hashes, and zero legacy M/D action match the contract with no TDS failure.
- `zero_repeatability`: duplicated zero arms match in frequency, electrical
  power, achieved power, command, and SOC within 1e-9. Their maximum drift
  defines the empirical noise term for all response floors.
- `bounded_energy_safe`: commands remain inside the 0.04-component request,
  the measured first-step slew remains below the registered port ramp,
  saturation and constraint lists remain empty, SOC stays inside `[0.2,0.8]`,
  and independently recomputed charge/discharge/SOC ledgers agree within 1e-9.
- `achieved_power_authority`: every signed mode keeps the requested projected
  sign and at least 0.035 system pu projected achieved-power magnitude.
- `electrical_mode_authority`: every diagonal signed electrical-power response
  has RMS above `max(1e-6 system pu, 10 * zero-repeat drift)`.
- `frequency_mode_authority`: every diagonal signed physical-frequency response
  has RMS above `max(1e-6 Hz, 10 * zero-repeat drift)` and its first five-step
  signed mean is positive. Off-diagonal matrix entries are reported for later
  controller design but cannot rescue a failed diagonal mode.
- Control stress is descriptive at this gate: command L1 device-seconds, total
  variation including the zero-to-first-command jump, maximum slew, energy,
  SOC excursion, saturation, and failure counts. No controller-improvement
  threshold is applied.

Decision tree:

- `BOUNDED-ENERGY-PORT-AUTHORITY-PASS`: all six registered checks pass. This
  authorizes only prospective selection and tuning of one permission-matched
  deterministic coordinator on the same port contract.
- `STOP-AUTHORITY-NOISE`: duplicated zero trajectories exceed the frozen
  repeatability tolerance.
- `STOP-UNSAFE-ACTUATION`: bounds, slew, saturation, energy, SOC, or legacy-M/D
  guards fail.
- `STOP-NO-ACHIEVED-POWER-AUTHORITY`: signed achieved port power is too small or
  directionally inconsistent.
- `STOP-NO-ELECTRICAL-AUTHORITY`: a registered action mode lacks electrical
  output response above the outcome-blind noise floor.
- `STOP-NO-RELEVANT-DYNAMIC-AUTHORITY`: a registered common/differential action
  mode lacks directionally consistent frequency response above that floor.
- `ANALYSIS-INVALID`: execution, completeness, identity, timing, numerical,
  source/seal, or output integrity fails. Preserve the attempt; no retry or
  alternate bank is authorized.

### Experiment-efficiency inputs

- Jobs/dependencies: one ordered 30-arm bank in one WSL Python process. The
  duplicated zero arms and paired signs share frozen conditions but not runtime
  state, so within-attempt parallelism is deliberately disabled to avoid
  nondeterministic solver/resource effects.
- Capacity anchor: R372 executed the same environment/wrapper on this host in
  one process and one native thread. The rehearsal binds the R372 formal
  execution and capacity hashes, installed ANDES/case identity, current host
  resources, competing research-process absence, and projected output bytes.
  Wall time is projected by registered environment-step count rather than an
  algorithm estimate.
- Formal outputs are create-only under
  `results/research_loop/r373_energy_port_authority/`; one attempt, zero
  automatic retries, no alternate output path, and no capacity resize.
- Operational monitoring may inspect only process existence and artifact
  presence. It may not inspect mode responses or scientific classification
  before the attempt completes.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r373_energy_port_authority.py execute --expected-seal-sha256 <sha256>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r373_energy_port_authority.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`; bind plan, parent, source,
  installed runtime/case, current resources, competing processes, output
  absence, artifact projection, and closed contract without a physical step.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, active_plan, contract_closed, capacity_ready, competing_process_absence, artifact_fit, physical_trajectory_executed_false
- capacity_evidence: `memory/rounds/R373/capacity_evidence_v2.json`
- wsl_python_processes: 1
- native_threads_per_process: 1
- host_process_budget: 1
- other_reserved_processes: 0
- seal_command: `/home/wya/andes_venv/bin/python scripts/run_r373_energy_port_authority.py prepare`.
- Rehearsal executes no physical trajectory and writes only
  `memory/rounds/R373/rehearsal_v2.json` and `capacity_evidence_v2.json`.
  The preserved first readiness pair omitted the preflight schema's explicit
  successful-concurrency fields and therefore has no launch authority.
- Initial readiness is `HOLD` until implementation, focused tests, project
  preflight, same-path no-trajectory rehearsal, source/runtime/resource checks,
  Ruff, `git diff --check`, and immutable seal all pass.

## Gate

This turn stops at readiness. `RUN-READY` means the prospective design is
identifiable and one immutable formal attempt is sealed. It does not mean the
actuator has passed, a deterministic controller is authorized, or training is
authorized. Any contract, implementation, source, parent, runtime, capacity,
process-conflict, output-collision, or preflight mismatch returns `HOLD`.

## 资产保护契约

- Byte-unchanged: protected V4/base/config assets, active-power and energy-port
  implementation, storage/ESD1 assets, agent/training code, old checkpoints,
  prior result/claim/feed/verdict assets, and every other manuscript line.
- Allowed additions before execution: one pure R373 authority classifier, one
  create-only R373 runner, focused tests, and R373 readiness/seal records.
- No feed, claim, verdict, `LINE.md`, `ROUTE.md`, or `ARTIFACTS.json` update is
  permitted before a terminal formal result exists.

## Cross-references

- `CLM-0975`: four physical VSG identities and independent runtime object.
- `CLM-0990`: direct M/D formulation remains stopped.
- `CLM-1000`: VSG-owned power/torque/energy implementation contract.
- `CLM-1005`: finite physical port object gate; not authority or control value.
