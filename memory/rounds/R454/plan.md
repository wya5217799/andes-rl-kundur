---
round: R454
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R454 plan — M4 残差恒等点局部几何与 checkpoint 向量场审计

**Opened**: 2026-08-20
**Driver**: R436 只证明 residual SAC 的端点接近确定性 bandpass anchor；
它没有测恒等残差的一阶/二阶物理回报变化、critic action gradient、一次
actor update 或投影局部 Jacobian，不能区分局部最优、critic 失真、更新停滞
与投影压制。
**Parent**: CLM-1345 (R436), advisory M4。

## TL;DR

Workload: `evidence`。Eval/diagnostic only, no training continuation. Along a
fixed four-direction orthonormal residual basis and raw-actor amplitudes
`0.10,0.03,0.01`, execute symmetric physical-return probes around the exact
bandpass anchor and all ten sealed R436 checkpoints on the three frozen R436
training conditions. Separately measure twin-critic action gradients, a
disposable fresh-optimizer fixed-state actor step, and the residual mapper's
active branch derivative. Classify only the registered slice.

## Snapshot at plan-time (oracle as of 2026-08-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->

- R436 checkpoint inventory: two arms × seeds 401--405, each `final.pt` with a
  matching sidecar. Checkpoints contain actor/critic/critic-target/temperature,
  but no replay buffer or optimizer state.
- Therefore `fresh_optimizer_fixed_state_probe` is a diagnostic vector-field
  probe, never the original next R436 update.

## Methodology

### Frozen object and directions

- Import the sealed R436 runner and reuse its nominal environment,
  `BandpassArmController(k=3.5)`, residual scale 0.70, feasibility-native action
  mapper, joint observation, reward, checkpoint loader, 50-step horizon,
  `gamma=0.99`, and exactly the three `TRAINING_CONDITIONS`.
- Orthonormal joint raw-residual directions:
  `c=[1,1,1,1]/2`, `d1=[1,-1,0,0]/sqrt(2)`,
  `d2=[1,1,-2,0]/sqrt(6)`, and
  `d3=[1,1,1,-3]/sqrt(12)`. Maximum Gram error must be `<=1e-12`.
- Raw-actor perturbations are `epsilon in [0.10,0.03,0.01]`. At every step,
  the mapper receives `0.70*(raw_checkpoint + sign*epsilon*direction)` for a
  checkpoint surface, or `0.70*sign*epsilon*direction` for the anchor surface.
  All raw values must stay in `[-1,1]`; no clipping is allowed.

### Physical surfaces and counts

- Anchor: each condition executes one zero trajectory plus four directions ×
  three amplitudes × two signs = 25; total 75. The same physical trajectory is
  scored under both exact R436 message/no-message reward definitions.
- Checkpoints: ten checkpoints × three conditions × 25 trajectories = 750.
  Each checkpoint uses its own information mask and reward definition.
- Total formal physical execution is exactly 825 trajectories in 33 shards:
  three anchor-condition shards and thirty checkpoint-condition shards. Zero is
  reused only within one surface/condition after exact reset/input identity.
- Store full step rows: joint observations, deterministic raw actor output,
  perturbation, scaled residual, controller/baseline/mapped action, feasible
  bounds, positive/negative headroom, selected mapper branch, external
  projection identity, frequency/energy-port rows, reward components, and
  undiscounted plus gamma-discounted return. Critic output is never used as
  physical return.

### Registered local-geometry rule

For each arm-reward definition and direction, first average the three paired
condition returns equally, then compute

`g(e) = mean_c[J_c(+e)-J_c(-e)]/(2e)` and
`h(e) = mean_c[J_c(+e)-2J_c(0)+J_c(-e)]/e^2`.

The primary surface is gamma-discounted return; undiscounted return is
secondary. Define `S=max(1,mean_c(abs(J_c(0))))` and `e_min=0.01`.

- A slope is stable/material when `g(0.03)` and `g(0.01)` have the same
  nonzero sign, relative drift is at most 25%, and
  `e_min*abs(g(0.01))/S >= 1e-3`. Every leave-one-condition-out pair must keep
  that sign and achieve at least `5e-4` under its own scale.
- Curvature is stable/material by the analogous sign/drift and leave-one-out
  rules, using `0.5*e_min^2*abs(h(0.01))/S` with thresholds `1e-3` and `5e-4`.
- `IDENTITY-NOT-STATIONARY`: either reward definition has any material stable
  slope; the improving sign is the sign of `g`.
- Otherwise `IDENTITY-POSITIVE-CURVATURE`: any direction has material stable
  positive curvature.
- Otherwise `IDENTITY-LOCAL-MAX-SUPPORTED-ON-REGISTERED-SLICE`: every direction
  for both reward definitions has an immaterial slope and material stable
  negative curvature.
- Otherwise `IDENTITY-LOCAL-GEOMETRY-INCONCLUSIVE`.

### Checkpoint mechanism diagnostics

- On every unperturbed checkpoint trajectory, retain visited per-agent states
  and deterministic raw actions. Compute `grad_a_q1` and `grad_a_q2`. Select
  the lower critic; when `abs(q1-q2) <= 1e-8*max(1,abs(q1),abs(q2))`, use the
  average subgradient. Aggregate the four agent gradients onto the registered
  directions.
- A critic direction is material when
  `e_min*abs(mean_grad)/max(1,mean_abs_qmin) >= 1e-3`. It is sign-comparable
  only when the matching checkpoint physical slope is stable/material.
  `CRITIC-FLAT` requires at least 8/10 checkpoints to have no material critic
  direction. `CRITIC-MISALIGNED` requires at least six comparable cells and
  sign agreement below 60%; otherwise report `CRITIC-ALIGNED` or
  `CRITIC-NOT-DIAGNOSTIC` as applicable.
- `fresh_optimizer_fixed_state_probe`: clone each checkpoint; seed sampling
  deterministically; form the saved-critic actor loss on all stored zero-
  trajectory states; take one fresh Adam step at R436 LR. A checkpoint moves
  when relative actor-parameter change is at least `1e-7` and deterministic
  raw-action RMS change is at least `1e-6`. At least 8/10 moving gives
  `FRESH-UPDATE-MOVES`; at least 8/10 below both thresholds gives
  `FRESH-UPDATE-FIXED`; otherwise `FRESH-UPDATE-MIXED`.
- Mapper derivative per raw residual is `0.70*positive_headroom` on the
  positive branch and `0.70*negative_headroom` on the negative branch.
  `PROJECTION-SUPPRESSED` requires at least 95% of visited device-step branches
  to have absolute derivative `<=1e-6` pu/raw-unit; otherwise
  `PROJECTION-NOT-SUPPRESSED`.

## Theory intake

```
observable: anchor first variation on the registered residual slice
  definition: stable/material centered discounted-return slope under the frozen rule
  source: results/research_loop/r454_m4_residual_local_audit/formal_analysis.json#/anchor_geometry
  predicts: a nonzero slope refutes identity stationarity on this slice
observable: anchor second variation on the registered residual slice
  definition: stable/material centered discounted-return curvature after slope immateriality
  source: same file #/anchor_geometry
  predicts: all-negative curvature supports only slice-bounded local maximality
observable: checkpoint critic/update/projection diagnostics
  definition: registered critic sign, fresh fixed-state step, and mapper branch tags
  source: same file #/mechanisms
  predicts: separates critic flatness or mismatch, update motion, and projection suppression
```

## Gate

### Outcomes

- Scientific classifications are exactly the four anchor-geometry branches and
  the three separate mechanism tags above. Endpoint metrics remain secondary.
- `CANARY-INVALID` takes precedence on any checkpoint/source/seal/hash drift,
  non-orthonormal basis, missing pair, incomplete 825-trajectory inventory,
  nonfinite return/gradient/update, raw action outside bounds, projection
  identity failure, wrong condition/direction/amplitude, or parent checkpoint
  byte drift after diagnostics.
- No branch may be called a full Hessian certificate, the original next SAC
  update, or a proof of SAC/global optimality.

## Experiment efficiency card

- Execution readiness: `MEASURE-FIRST` until directed tests, same-entry
  rehearsal, and a fresh full-trajectory capacity ladder pass; then `RUN-READY`
  only after seal.
- Jobs: 33 independent 25-trajectory shards -> verified aggregation and ten
  offline checkpoint diagnostics -> serial classification.
- Capacity ladder: 32 representative full 50-step anchor trajectories at each
  rung `1/2/4/8/12/16`; retain all rung records, require all valid, one native
  thread/process, and memory safety. Freeze the highest safe rung with accepted
  marginal throughput.
- Prospective ceiling: 16 workers + one launcher,
  `host_process_budget=17`, `wsl_python_processes=17`,
  `native_threads_per_process=1`, `other_reserved_processes=0`; replace with
  fresh measured selection before seal if different.
- Monitor only processes, completed shards, hashes, counts, and engineering
  failures until all physical shards pass; do not inspect slopes or tags early.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r454_m4_residual_local_audit.py --shards tmp/andes/r454_m4_shards.json --workers <sealed> --round R454`, then the same runner `aggregate` after 33/33 sidecars verify.
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r454_m4_residual_local_audit.py rehearse`
- rehearsal_scope: same-pre-attempt-path verification plus one real checkpoint,
  one condition, one direction/amplitude `+/-/0` triplet, critic gradients,
  mapper branches, and disposable actor update; no formal output.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, basis, symmetric formulas, checkpoint immutability, projection identity, finite critic/update.
- capacity_evidence: `memory/rounds/R454/capacity_evidence.json`
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- Read-only: R436 runner/seal/checkpoints/results/feed/claim and all existing
  learner/environment/controller/action-map assets.
- New only: R454 runner/test, rehearsal/capacity/seal, 33-shard list, hashed
  result root, feed/claim/verdict, and normal manifest/line pointers.
- No checkpoint overwrite, replay reconstruction, optimizer-state claim,
  training continuation, reward/controller/profile/amplitude adaptation,
  topology expansion, threshold tuning, or result-driven retry.

## Cross-references

- CLM-1345; advisory M4; R436 runner/formulas/seal/checkpoints.
