---
round: R456
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R456 plan — M1 双变量顶格诊断的封存调度接口 successor

**Opened**: 2026-08-20  
**Driver**: R455 在 seal 后、任何 formal result 产生前暴露了调度接口缺陷：
共享 driver 固定调用 `shard <id>`，R455 runner 仅提供 `state-shard`/
`eval-shard`，首次 launcher 被 argparse 拒绝且 R455 result 根不存在。本轮
唯一工程变化是增加 sealed `shard` 分派入口；科学合同、父资产、状态库、
factorial、阈值、物理束和终止规则逐字继承 R455。
**Parent**: R455 (aborted, no algorithm evidence), CLM-1290 (R425),
CLM-1300 (R427), M1 advisory。

## TL;DR

Workload: `evidence`，checkpoint-local fixed-bank diagnostic，不是重新训练。
冻结 R425 两个 CD 臂 × seeds 401/402/403；四个 development profiles × 六
场景 × 30 步生成 6 state shards（144 trajectories / 4,320 transitions）。从
checkpoint terminal `mu_rms=mu_tv=10` 出发做 20 次 profile-balanced dual
replay；五 cells = `U10_eta050`, `U100_eta050`, `U10_eta005`,
`U100_eta005`, `profile_U100_eta050`。每 cell 使用同一状态库、冻结 critic、
fresh Adam、全库 batch 做 16 次 actor-only updates，日志包含 value/RMS/TV
梯度范数、cosine/Gram、投影 active fraction、参数/动作/固定残差变化。30 个
干预 checkpoint 随后在四个独立 evaluation profiles × 六场景 × 30 步物理
确认（720 trajectories / 21,600 transitions）。

R425 未保存原 optimizer/replay，因此本轮不得称为训练轨迹复现、KKT/全局
可行性或策略类不可行证据。R455 capacity/rehearsal 只证明失败 seal 之前的代码
路径；R456 必须独立再跑 capacity、rehearsal、preflight 和 seal，不复用它们。

## Snapshot at plan-time (oracle as of 2026-08-20)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] finite-bank information-level margin program；本轮不回答。

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375.
- Q-0004 closed-negative @ R442, by CLM-1370.
- Q-0111 closed-negative @ R397, by CLM-1130.

## Methodology

### Single engineering change

- New entry `scripts/run_r456_m1_dual_saturation.py` imports and source-seals the
  R455 scientific runner, rebinds only R456-owned paths/round id, and exposes
  `shard <id>`: two fields (`arm|seed`) dispatch to formal state capture; three
  fields (`cell|arm|seed`) dispatch to formal evaluation.
- `prepare` seals both successor entry and imported R455 scientific source, the
  diagnostic module/tests, shared driver, parent R425 source/checkpoints and every
  parent JSON input. No wrapper or unsealed alternate launcher is permitted.
- Forbidden: any change to scientific cells, seeds, scenario banks, update counts,
  reward, actor/critic, mapper/slew, thresholds, R425/R427 assets, or outcome logic.

### Frozen state, dual and gradient contracts

- State capture exactly matches R425 deterministic actor semantics: joint critic
  observation, actor neighbor mask, 9-slot prev-action augmentation, post-slew action,
  physical readback and per-episode R425 RMS/TV residuals. Required: 6 shards, 24
  trajectories/checkpoint, 720 transitions/checkpoint, zero TDS failure, finite arrays,
  exact parent checkpoint hash.
- Projected law: `mu_next=clip(mu_pre+eta*g_pre,0,U)`. Positive/zero residual at U
  persists; negative residual must release. Parent last-20 identifiable transitions
  must replay exactly. Balanced replay gives aggregate and per-profile cells the same
  20 exposure steps; separate profile multipliers weight only matching samples.
- Each cell reloads the same parent checkpoint after seeds are set, constructs fresh
  Adam at parent actor lr, freezes critic/targets/lagrange, and performs exactly 16
  full-bank actor updates. No critic, target, dual, replay sampling or evaluation-based
  selection occurs within these updates.

### Physical confirmation and guards

- 30 intervention checkpoints × four evaluation profiles × six scenarios = 720
  trajectories. Use R425 `summarise_profile` unchanged and R425 deterministic summaries
  as reference.
- Guard thresholds: common IAE, worst peak, RoCoF <=1.03× reference; action RMS/TV
  <=1.10×; saturation <=0.05; minimum variation and VSG dispersion >1e-6. Endpoints
  are always reported and never waive a guard.
- Parent R425 evaluation is hash-verified and summarized offline, never re-run.

## Gate

Integrity failure (hash/source drift, inventory/count mismatch, TDS/mapping/slew/nonfinite,
critic/target mutation, parent-tail law mismatch, sidecar failure) => `CANARY-INVALID`.

Pre-registered mechanism rules, paired across six arm/seed checkpoints:

1. `CEILING-LIMITED-LOCAL` for RMS or TV requires U100 vs U10: multiplier >10 in
   >=5/6, weighted gradient norm +>=10% in >=4/6, fixed residual improvement >=5%
   in >=4/6, and matching physical stress improvement >=5% in >=4/6.
2. `STEP-CONTROLS-TRANSIT` requires U10 eta cells identical while residuals remain
   nonnegative and U100 eta=.05 farther from 10 than eta=.005 in all six pairs.
3. `GRADIENT-CONFLICT` requires median actor cosine(value,constraint)<=-0.25 and
   median weighted/value norm ratio >=10% in >=4/6, separately for RMS/TV.
4. `PRIMAL-NONRESPONSE-LOCAL` requires material constraint gradient but relative
   action RMS delta <1e-3 and fixed residual improvement <1% in >=4/6. Projection is
   blamed only when active derivative fraction <0.10 in the same supported pairs.
5. `AGGREGATION-MASK-LOCAL` requires profile dual vs aggregate U100/.05 to improve
   worst-profile fixed and physical stress by >=5% in >=4/6, while endpoint and common
   IAE harm each <=3%.
6. `TESTED-CELL-GUARD-FEASIBLE` requires all physical guards on all four profiles in
   >=2/3 seeds of an arm and aggregate endpoints no worse than its parent checkpoint.

Multiple tags may co-occur; none met => `M1-DEEP-CAUSE-INCONCLUSIVE`. No outcome
authorizes tuning, retry, new training or infeasibility claims.

## Theory intake

M1 advisory 提出的“dual ceiling / step size / gradient conflict / primal
nonresponse / aggregation masking”仅作为待证机制。以下可观测量逐项对应上面的
预注册规则；本清单只把既有判断写成 lint 可读格式，不新增或改动阈值：

```
observable: replay_dual_path
  definition: 五个 cell 的逐步 mu、预更新 residual 与 exact projected-law error
  source: results/research_loop/r456_m1_dual_saturation/interventions/*/intervention.json
  predicts: U100 相对 U10 的 ceiling 规则，或 eta=.005 相对 eta=.05 的 transit 规则
observable: actor_gradient_geometry
  definition: value/RMS/TV gradient norm、weighted/value ratio 与 cosine，六个 checkpoint 分别判断
  source: results/research_loop/r456_m1_dual_saturation/interventions/*/intervention.json
  predicts: cosine <= -0.25 且 weighted/value ratio >= 0.10 in >=4/6 supports GRADIENT-CONFLICT
observable: actor_response
  definition: action relative RMS delta、fixed-bank residual improvement 与 projection active derivative fraction
  source: results/research_loop/r456_m1_dual_saturation/interventions/*/intervention.json
  predicts: material gradient 但 action delta <1e-3 且 improvement <1% in >=4/6 supports PRIMAL-NONRESPONSE-LOCAL
observable: profile_and_physical_guard_response
  definition: profile-dual vs aggregate fixed/physical stress，以及四 evaluation profiles 的完整 guard table
  source: results/research_loop/r456_m1_dual_saturation/formal_analysis.json
  predicts: Gate rules 5-6 的 AGGREGATION-MASK-LOCAL 或 TESTED-CELL-GUARD-FEASIBLE
```

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r456_m1_dual_saturation.py --shards tmp/andes/r456_m1_state_shards.json --workers 16 --round R456`，随后 `intervene`，同 driver + `tmp/andes/r456_m1_eval_shards.json`，最后 `aggregate`。
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r456_m1_dual_saturation.py rehearse`
- rehearsal_scope: same-pre-attempt-path；真实 R425 checkpoint/development profile/ANDES/增广/slew/gradient/save-load，并额外由定向测试和 CLI dry dispatch 覆盖共享 driver 的固定 `shard` 入口；不写 formal result 根。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, shard_interface, ceiling_release_law, gradient_decomposition, frozen_networks, checkpoint_roundtrip
- capacity_evidence: `memory/rounds/R456/capacity_evidence.json`
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

Fresh capacity ladder: rungs 1/2/4/8/12/16，32 representative 30-step
trajectories/rung；17 is prospective upper budget and seal is forbidden unless the
fresh R456 evidence selects 16 workers, is memory-safe, and reports no undeclared load.

## 资产保护契约

- R425/R427/R455 assets read-only；R455 remains aborted with no result root.
- New only: R456 wrapper/test, R456 ledger evidence, create-only
  `results/research_loop/r456_m1_dual_saturation/`, normal feed/claim closeout.
- After R456 seal, plan/wrapper/imported scientific runner/module/tests immutable.
  Terminal failure preserves artifacts and ends the round without retune/retry.

## Cross-references

- R455 aborted plan + seal (engineering history only; no algorithm evidence).
- `paper/yang_md_decoupling_marl/working/vsg_failure_math_advisory_20260820/problems/M1_dual_saturation.md`.
- `paper/yang_md_decoupling_marl/reports/R425.md` (CLM-1290) and R427 (CLM-1300).
- R454/CLM-1415 remains separate SAC residual-objective evidence and is not pooled.
