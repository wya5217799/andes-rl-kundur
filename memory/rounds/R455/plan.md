---
round: R455
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: R456
abort_reason: 'sealed launch interface defect before any formal result: the shared shard
  driver invokes the fixed subcommand `shard`, while the sealed R455 runner exposed only
  `state-shard` and `eval-shard`; the launcher rejected the unsupported --command option,
  the R455 result root remained absent, and no algorithm evidence was produced'
superseded_note: null
---
# R455 plan — M1 双变量顶格的冻结状态库因果诊断

**Opened**: 2026-08-20  
**Driver**: R425/R427 的符号修正双变量在所有保留尾段都等于上限 10，且
RMS/TV 有符号残差持续为正；M1 咨询已证明这符合投影上升定律，但现有资产
不能区分上限不足、步长过大、梯度冲突、原始控制不响应或跨剖面聚合掩盖。
**Parent**: CLM-1290 (R425), CLM-1300 (R427), M1 advisory；本轮不替代
R425/R427 的正式训练证据。

## TL;DR

Workload: `evidence`，但属于 **checkpoint-local fixed-bank diagnostic**，不是
重新训练。冻结 R425 两个 CD 臂 × 三个种子的 final checkpoint；每个检查点在
四个 development profiles、每个六个场景、每场景 30 步上生成同一确定性状态
库（720 transitions/checkpoint，共 4,320）。以 checkpoint 内 terminal
`mu_rms=mu_tv=10` 为起点，在固定状态库上做 20 次 profile-balanced dual
replay，再以 fresh Adam、冻结 critic、全库 batch 做恰好 16 次 actor-only
更新。五个干预 cell：`U10_eta050`、`U100_eta050`、`U10_eta005`、
`U100_eta005`、`profile_U100_eta050`。前四个是 2×2 ceiling × step；第五个
对每个 development profile 独立积分 multiplier，并只加权该 profile 的样本。
每个 cell 继承完全相同的 checkpoint、状态/前动作/critic、fresh optimizer
初始化和更新次数。30 个干预后策略各自在四个独立 evaluation profiles × 六
场景 × 30 步物理确认（720 trajectories）。

本轮能判定投影更新定律、局部 multiplier 力量、梯度几何、固定状态上的原始
控制响应、聚合干预和独立剖面物理响应；因 R425 未保存原 optimizer/replay，
不得把本轮称为原训练轨迹复现、全局可行性搜索、KKT/不可行证书或策略类证书。

## Snapshot at plan-time (oracle as of 2026-08-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program
  certify or refute INFORMATION-LIMITED for the exact observation histories?
  本轮不回答该题。

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375.
- Q-0004 closed-negative @ R442, by CLM-1370.
- Q-0111 closed-negative @ R397, by CLM-1130.

## Methodology

### Mission and authority boundary

- Input checkpoints (read-only):
  `results/research_loop/r425_guard_constraints_signfix/train/{cd_matd3_no_message,cd_matd3_message}/seed{401,402,403}/final.pt`
  and their sha256 sidecars.
- Parent read-only inputs: R425 contract, `reference_action_stats.json`, training
  manifests (including last-20 residual/multiplier traces), deterministic evaluation
  records, and R425/R427 formal analyses.
- New implementation only:
  `src/andes_rl_kundur/agents/cd_matd3_dual_factorial.py`,
  `scripts/run_r455_m1_dual_saturation.py`, directed tests, R455 ledger/feed/claim,
  and create-only result root
  `results/research_loop/r455_m1_dual_saturation/`.
- Forbidden: edit parent runner/learner/checkpoints; train a new critic; regenerate
  parent training data; use evaluation profiles to select a cell; change reward,
  actor architecture, critic, action mapper/slew limit, scenario bank, guards, or
  thresholds after seal; interpret a failed cell as policy-class infeasibility.

### Frozen state banks

- Arms: `cd_matd3_no_message`, `cd_matd3_message`; seeds 401/402/403.
- Development profiles: `canary_dev_a..d`; six registered signed scenarios each;
  30 steps; deterministic actor; exact R425 observation mask and 9-slot prev-action
  augmentation; exact post-slew executed action.
- One create-only shard/checkpoint stores every transition's augmented observation,
  previous executed action, raw actor action, executed action, profile/scenario/step,
  next observation, done/TDS status, physical readback, action-energy/TV increments,
  and per-episode signed RMS/TV residuals using R425's hashed reference thresholds.
- Completeness: exactly 6 state shards, 144 trajectories, 4,320 transitions; zero
  TDS failures; finite arrays; action/mapper/slew checks all true. Any failure gives
  `CANARY-INVALID` and no intervention/evaluation launch.

### Exact update-law and balanced replay

For each constraint component:

`mu_next = clip(mu_pre + eta * g_pre, 0, U)`.

- Algebra tests include positive, zero and negative residuals at the ceiling; any
  negative residual that does not release the ceiling is `CANARY-INVALID`.
- Parent-tail audit replays every available aligned R425 last-20 trace and verifies
  all recorded ceiling persistence events where the prior multiplier and residual
  are identifiable. This is a mechanics audit only, not recovery of missing history.
- Intervention weights use the fixed bank's profile-balanced mean residuals. Starting
  from the checkpoint's terminal multiplier, repeat exactly 20 dual steps. Aggregate
  cells use the mean over four equally weighted profile means; profile cell updates
  four separate multipliers from the four profile means for the same 20 steps. This
  equalizes exposure count and isolates aggregation from sample-count imbalance.
- Factor cells:
  1. `U10_eta050`: U=10, eta=0.05, aggregate;
  2. `U100_eta050`: U=100, eta=0.05, aggregate;
  3. `U10_eta005`: U=10, eta=0.005, aggregate;
  4. `U100_eta005`: U=100, eta=0.005, aggregate;
  5. `profile_U100_eta050`: U=100, eta=0.05, four profile multipliers.

### Gradient decomposition and actor intervention

- Load the sealed checkpoint anew per cell; torch/numpy seeds are set before agent
  construction. Discard any constructor optimizer state and instantiate fresh Adam
  with the parent actor learning rate for each actor. Critic, target networks and
  lagrange are frozen and byte-checked before/after.
- Full 720-row state bank is the batch. For each actor and each of 16 updates log
  objective/value component `-mean(Q_d + lambda*Q_c)`, RMS component
  `mean(row^2)`, TV component `mean(abs(row-prev_row))`, their unweighted gradients,
  weighted constraint gradient, total gradient, norms, pairwise cosines/Gram matrix,
  post-slew Jacobian active fraction, and parameter/action deltas. No stochastic
  minibatch selection and no critic/target/dual update occurs during these 16 steps.
- Aggregate cells use scalar replayed mu values. The profile cell computes a
  profile-weighted per-sample constraint loss; profile `dev_x` uses only `mu_x`.
- Save create-only intervention checkpoint and JSON after step 16. Recompute fixed-bank
  actions and RMS/TV residuals using the stored previous action (state held fixed).
  These are local-response observables, not counterfactual trajectories.

### Independent physical confirmation

- Evaluate each of 30 intervention checkpoints on the untouched
  `canary_eval_a..d` profiles, six scenarios/profile, 30 steps: exactly 720 physical
  trajectories / 21,600 transitions. No development result may remove a registered
  cell or change the evaluation bank.
- Use R425 `summarise_profile` verbatim. Compare each cell/arm/seed/profile with the
  frozen deterministic R425 reference using the original thresholds: common IAE and
  worst peak/RoCoF <= 1.03× reference; action RMS/TV <= 1.10×; saturation <=0.05;
  minimum variation and per-VSG dispersion >1e-6. Endpoints are reported, never used
  to waive a guard.
- Parent checkpoint performance is recomputed from the state-independent R425 sealed
  evaluation records, not rerun; its hashes are verified. Physical confirmation is
  descriptive paired evidence across the six checkpoints, not population inference.

## Gate

Integrity gates precede all mechanism labels. Missing/hash-drifted parent input,
incomplete/nonfinite bank, TDS failure, mapper/slew violation, frozen critic drift,
cell-count mismatch, formal sidecar failure, or ceiling-release algebra failure gives
`CANARY-INVALID` and stops downstream launch.

Prospective mechanism observables (paired by arm/seed):

1. **CEILING-LIMITED-LOCAL**: versus `U10_eta050`, `U100_eta050` must (a) end with
   RMS and/or TV multiplier >10 in at least 5/6 checkpoints, (b) increase the matching
   weighted constraint-gradient norm by >=10%, (c) reduce the matching fixed-bank
   residual by >=5% in at least 4/6 without reversing the median, and (d) improve at
   least one matching evaluation action-stress metric by >=5% in at least 4/6 paired
   profile aggregates without new TDS/mapping failure. This supports a local truncated-
   penalty limitation only; it is not a feasibility claim.
2. **STEP-CONTROLS-TRANSIT**: at U=10 the two eta cells are algebraically identical
   while residuals stay nonnegative, and at U=100 eta=.05 moves farther from 10 than
   eta=.005 in all finite pairs. If the lower step alone improves physical guards,
   report `STEP-SENSITIVE-LOCAL`; do not call it the explanation of ceiling persistence.
3. **GRADIENT-CONFLICT**: a constraint gradient has cosine <=-0.25 against the value
   gradient and weighted norm >=10% of the value-gradient norm in >=4/6 checkpoints
   at step 0, with the same median sign over actors; report separately for RMS/TV.
4. **PRIMAL-NONRESPONSE-LOCAL**: weighted constraint gradient is finite and >=10% of
   value norm but after 16 updates relative action RMS change <1e-3 and matching
   fixed-bank residual improvement <1% in >=4/6 checkpoints. Projection suppression
   is named only if active derivative fraction <0.10 in the same pairs.
5. **AGGREGATION-MASK-LOCAL**: versus aggregate `U100_eta050`, profile-specific duals
   reduce the worst-profile fixed-bank residual by >=5% and improve its paired physical
   action-stress metric by >=5% in >=4/6 checkpoints, without worsening either endpoint
   or common-frequency IAE by >3% versus that aggregate cell. Otherwise aggregation is
   not identified as the cause on this local intervention.
6. **TESTED-CELL-GUARD-FEASIBLE**: any cell passes every frozen physical guard for all
   four profiles in >=2/3 seeds of an arm and has no worse aggregate endpoints than its
   parent checkpoint. This is only a witness for the tested checkpoint-local update.

Multiple local mechanisms may co-occur. If integrity passes but none meets its frozen
threshold, the classification is `M1-DEEP-CAUSE-INCONCLUSIVE`. Regardless of outcome,
the exact ceiling-persistence law is reported separately. No outcome authorizes a new
training run, threshold retune, cell addition, retry, or policy-class infeasibility claim.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r455_m1_dual_saturation.py --shards tmp/andes/r455_m1_state_shards.json --workers 16 --round R455`，随后同 runner 的 `intervene`、30 个 eval shards 与 `aggregate`。
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r455_m1_dual_saturation.py rehearse`
- rehearsal_scope: same-pre-attempt-path；同一真实 R425 checkpoint、真实 development profile、ANDES 环境、状态增广、slew projector、actor/critic 计算、dual pure function 和 save/load 路径；不写 formal result 根。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, ceiling_release_law, gradient_decomposition, frozen_networks, checkpoint_roundtrip
- capacity_evidence: `memory/rounds/R455/capacity_evidence.json`
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0
- WSL/ANDES only through `/home/wya/andes_venv/bin/python scripts/andes_scratch.py`.
- Rehearsal: authority/hash checks; output absence; one real development trajectory;
  exact residual and ceiling-release checks; one actor's step-0 decomposition and one
  fresh update/save-load; parent source/checkpoint hashes.
- Capacity: fresh representative 30-step physical-trajectory ladder, 32 tasks at
  rungs 1/2/4/8/12/16, one launcher; total-memory rule and other-process inventory;
  selected workers and process budget are frozen only after measurement.
- Formal phases: `prepare`; six state shards; `intervene` (offline, serial, 30 cells);
  30 evaluation shards with the sealed worker count; `aggregate`.
- Expected physical cost: rehearsal 1 + capacity 192 + formal 864 trajectories.
  Capacity/rehearsal trajectories are never evidence and cannot be reused formally.
- All formal JSON/PT artifacts are create-only and carry sha256 sidecars; formal seal
  hashes plan, runner, learner, tests, parent inputs and launch contract before any
  formal state shard.

## 资产保护契约

- R425/R427 and all earlier results/checkpoints/runners/learners are read-only.
- No edits to manuscript-cited artifacts or unrelated dirty worktree files.
- After seal, R455 plan/runner/learner/tests are immutable; only create-only results
  and normal lifecycle/feed/claim/LINE/ARTIFACTS/manifest closeout may be added.
- A terminal failure preserves every artifact and bounded meaning; no retuning,
  threshold change, algorithm swap or outcome-driven retry.

## Cross-references

- `paper/yang_md_decoupling_marl/working/vsg_failure_math_advisory_20260820/problems/M1_dual_saturation.md`
- `tmp/yang_md_decoupling_marl/m1_dual_saturation_execution_draft.md`
- `paper/yang_md_decoupling_marl/reports/R425.md` (CLM-1290)
- `paper/yang_md_decoupling_marl/reports/R427.md` (CLM-1300)
- M4 R454 establishes that a separate SAC zero-residual observation is dominated by
  its explicit residual penalty; it is not pooled with this CD-MATD3 dual diagnosis.
