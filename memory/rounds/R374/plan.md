---
round: R374
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R374 plan — deterministic cross-coordinate decoupler gate

**Opened**: 2026-08-12
**Driver**: R373 proves bounded signed authority and nonzero cross-coordinate
response on the four VSG-owned energy ports, but no controller has yet reduced
that coupling. A permission-matched deterministic gate must precede MARL.
**Parent**: CLM-0975, CLM-0980, CLM-0990, CLM-1000, CLM-1005, CLM-1010;
R365, R366, R369, R371--R373

## TL;DR

Workload: `evidence`. Freeze one serial, non-learning comparison with a fresh
development bank and a separately held-out evaluation bank. Compare zero
feedback, local diagonal PI, and one development-selected distributed
common/differential coordinator on identical VSG ports, limits, timing, and
physical endpoints. This turn may implement, rehearse, and seal the design but
stops at `RUN-READY`; it does not execute the formal bank or train.

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

- Decision: can one selected distributed deterministic controller reduce both
  cross-coordinate response and disturbance-driven differential motion against
  zero feedback and a permission-matched local diagonal PI without common-mode
  or physical harm?
- Object: unchanged R373 four-port `AndesVSGEnergyPortEnv`; four agents are
  `VSG_1..VSG_4` at buses `[12,16,14,15]`. ESD1 and legacy M/D actions remain
  absent.
- Estimand: bounded efficacy of one selected controller instantiation on one
  held-out fixed-topology bank. This is not class superiority, stability,
  robustness, topology generalisation, communication attribution, or MARL.
- Comparison-identifiability decision: `QUALIFY`. All arms share plant,
  action coordinates, energy projection, limits, update rate, horizon, and
  evaluation data. Runtime neighbour information and the differential channel
  are the intended joint architecture contrast; the result cannot isolate
  messages alone or generalise beyond the selected gains and bank.

### Public seams and controller contract

- Seam 1: one stateful controller call consumes the four physical VSG
  frequencies, 0.2-s interval, and prior port projection; it returns four raw
  power requests plus auditable common/differential components.
- `local_diagonal_pi`: four independent states; each sees only own frequency
  and prior own projection. Gains fixed at `kp=2.0 system pu/Hz` and
  `ki=0.2 system pu/(Hz s)` from an implementation donor, not R373 outcomes.
- `distributed_cross_coordinate`: same local PI gains plus ring neighbour
  messages `{0:[1,3],1:[0,2],2:[1,3],3:[2,0]}`. A symmetric-Laplacian dynamic
  average-consensus estimate drives the common channel; `-ks L f` is the
  zero-sum differential channel. Candidate grid is exactly
  `ks in {0.5,1.0} system pu/Hz` by `kc in {0.5,1.0} 1/s`.
- For the distributed arm, the dynamic-average estimate is initialized from
  local error and preserves the fleet error mean under the symmetric graph;
  the raw differential request must sum to zero within `1e-12` every step.
- Total raw request is `u_c+u_d`; every arm then uses the unchanged R373 energy
  projection. Record requested/commanded common and differential components,
  projection distortion, SOC, achieved power, energy, saturation, and failure.

### Frozen banks

- Plant/seed: unchanged V4, seed 42, deterministic communication transport,
  toggler disabled, 50 decisions, 0.2 s per decision, one fresh environment per
  arm, reward ignored.
- Modes in device order: `common=[1,1,1,1]`,
  `inter_area=[1,1,-1,-1]`, `local_area_1=[1,-1,0,0]`, and
  `local_area_2=[0,0,1,-1]`. They are arithmetic coordinates, not eigenmodes.
- Development probe condition: `PQ_0 +0.35`; paired additive requests of
  `+/-0.025 system pu` per nonzero mode component. Development disturbances:
  `PQ_0 -0.75` and `PQ_1 +0.75`. Six arms (zero, diagonal, four distributed
  candidates) give 60 development trajectories.
- Held-out probe condition: `PQ_Bus14 -0.55` with the same paired mode
  injections. Held-out disturbances: `PQ_Bus14 +0.85` and
  `PQ_Bus15 -0.85`. Only zero, diagonal, and the development-selected
  distributed candidate run here, giving 30 held-out trajectories.
- Development and held-out labels, signs, amplitudes, modes, endpoints, and
  thresholds are frozen before any R374 physical outcome. R373 may justify the
  problem but may not select R374 gains, cases, endpoints, or thresholds.

### Endpoints and selection

- Paired probe response is one half of positive-minus-negative frequency
  trajectories projected into the four coordinates. Co-primary probe
  endpoints are absolute off-diagonal response energy and the off-diagonal to
  diagonal energy ratio; both must fall, so uniform attenuation alone cannot
  be called decoupling.
- Disturbance co-primary endpoint is integrated squared energy of the three
  differential coordinates. Settling is the earliest time after which all
  three remain within `0.01 Hz` for the rest of the horizon.
- Common/no-harm endpoints: common-frequency IAE, worst-device peak, maximum
  finite-difference RoCoF, incomplete/TDS failure, saturation, command L1/TV,
  achieved energy, SOC range, and projection common/differential distortion.
- Development eligibility versus diagonal PI: both probe co-primary ratios and
  mean differential-energy ratio at most `0.98`; common IAE ratio at most
  `1.05`; no incomplete run, TDS failure, saturation, SOC violation, nonfinite
  value, or zero-sum violation. Select the smallest product of the three
  primary ratios, then lower `ks`, then lower `kc`. No eligible candidate stops
  before held-out execution.

### Held-out decision tree

- `DETERMINISTIC-DECOUPLING-PASS`: selected distributed arm has both probe
  ratios at most `0.95` versus each baseline; mean differential-energy ratio at
  most `0.95` versus each baseline; every disturbance differential-energy
  ratio at most `1.10`; mean settling no slower than each baseline and at least
  one 0.2-s earlier than diagonal PI; common IAE at most `1.05`, peak and RoCoF
  at most `1.10` versus the better baseline; all physical guards pass.
- `STOP-DEVELOPMENT-NO-CANDIDATE`: no frozen candidate passes development.
- `STOP-NO-CROSS-DECOUPLING`: held-out absolute or normalized cross response
  misses its threshold.
- `STOP-NO-DIFFERENTIAL-BENEFIT`: disturbance energy or settling misses.
- `STOP-COMMON-MODE-HARM`: common IAE, peak, or RoCoF guard misses.
- `STOP-UNSAFE-CONTROL`: execution, energy, SOC, saturation, zero-sum, or
  projection-integrity guard misses.
- `ANALYSIS-INVALID`: bank identity, completeness, source/seal, timing,
  numerical, development-selection, or artifact-integrity check fails.
- Every terminal class keeps `training_authorized=false`. Only a PASS permits a
  successor non-learning time-varying headroom gate; it does not permit MARL.

### Experiment-efficiency inputs

- One ordered 90-arm bank, 4500 environment steps, one WSL Python process, one
  native thread, no process pool, no retry, and no resize. Development is
  completed and classified before the runner may instantiate held-out arms;
  the held-out data are never used for candidate selection.
- Capacity anchor: sealed R373 used the same environment and port in one
  process. Rehearsal scales its measured wall time and output bytes with a 1.5
  safety factor, carries forward its successful serial memory-fit guard, and
  requires current available WSL memory to remain at least 80% of that anchor,
  and verifies host resources, competing-process absence, installed ANDES/case
  identity, output absence, and source hashes.
- Formal outputs are create-only under
  `results/research_loop/r374_deterministic_decoupling/`. Monitoring may inspect
  process existence and artifact presence only, never development ranking or
  held-out endpoints before terminal completion.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r374_deterministic_decoupling.py execute --expected-seal-sha256 <sha256>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r374_deterministic_decoupling.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`; bind plan, R373 parent, controller,
  classifier, runner, tests, installed runtime/case, host resources, competing
  processes, output absence, artifact projection, and closed comparison
  contract without a physical step.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, active_plan, contract_closed, capacity_ready, competing_process_absence, artifact_fit, physical_trajectory_executed_false
- capacity_evidence: `memory/rounds/R374/capacity_evidence.json`
- wsl_python_processes: 1
- native_threads_per_process: 1
- host_process_budget: 1
- other_reserved_processes: 0
- seal_command: `/home/wya/andes_venv/bin/python scripts/run_r374_deterministic_decoupling.py prepare`
- Rehearsal writes only `memory/rounds/R374/rehearsal.json` and
  `capacity_evidence.json`. Initial readiness is `HOLD` until implementation,
  focused tests, V4 regression, project preflight, same-path rehearsal, Ruff,
  `git diff --check`, and immutable seal all pass.

## Gate

This turn stops at readiness. `RUN-READY` means only that the prospective
comparison and one immutable attempt are executable and identifiable for the
bounded claim. It does not mean the controller works and does not authorize
formal execution, training, reward tuning, algorithm selection, or manuscript
claims. Any contract/source/runtime/capacity/output mismatch returns `HOLD`.

## 资产保护契约

- Byte-unchanged: protected V4/base/config/train/ranker assets; R371--R373
  port, results, claims, feeds, seals, and verdicts; storage/ESD1 assets; agent
  and training code; old checkpoints; every other manuscript line.
- Allowed additions: one reusable cross-coordinate controller module, one pure
  R374 classifier, one create-only R374 runner, focused tests, and R374
  readiness/seal records.
- No ANDES trajectory, training, feed, claim, verdict, `LINE.md`, `ROUTE.md`, or
  `ARTIFACTS.json` update is permitted before a terminal formal result.

## Cross-references

- `CLM-1010`: bounded common/differential authority and nonzero cross response.
- `CLM-1005`: physical four-port object contract.
- `CLM-1000`: achieved-power energy and torque semantics.
- `CLM-0980`: permission-matched deterministic comparison requirement.
- `CLM-0990`: stopped direct M/D formulation remains excluded.
