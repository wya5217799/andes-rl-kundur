---
round: R458
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R458 plan — 开发集选一条守卫全清的分段方案，评估集样本外验证

**Opened**: 2026-08-21
**Driver**: R453 在 eval_b/c/d 找到守卫全清的分段方案，但该族 350 条候选只跑过
评估集，候选是 outcome-seeing 选的；样本内的 k3_116 不能当"直接动作接口存在
无代价解"的存在性证据。本轮把同一族候选跑在冻结的开发集上，按事先定死的
规则只选一条，再只在评估集上验证一次，消除 selection-on-evaluation 偏差。
**Parent**: CLM-1410 (R453), CLM-1355 (R439), CLM-1365 (R441), advisory M5。

## TL;DR

不训练、不换 learner、不换 grid。用 R452 冻结的 350 条候选序列、R439 的分段
执行语义、R452 的 guard 判定，在 dev_a/dev_b 上重跑候选+静态参照，按冻结规则
选唯一 winner；再在 eval_a..d 上只跑该 winner+静态参照，报告每条 eval profile
是否守卫全清及 transfer 计数。开发集物理量约为 R452 的一半，评估集只有 48 条
轨迹。

## Snapshot at plan-time (oracle as of 2026-08-21)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] finite-bank information-level margin program; R458 does not
  answer it.

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375.
- Q-0004 closed-negative @ R442, by CLM-1370.
- Q-0111 closed-negative @ R397, by CLM-1130.

## Methodology

### Frozen objects and identities

- 环境与动作对象与 R452/R453 逐字节同源：R416 直接 M/D 对象、V4 环境、
  4 VSG、0.2 s × 30 steps、seed 399、frozen estimators、`km3_kd2` 静态参照、
  350 条候选序列（K=2/3 穷举 + K=5 随机 200，序列 SHA
  `6f505fa569e5a22d8163da44a38292fecc433180cff7640fce6fff4984433962`）。
- 只重跑开发集 dev_a/dev_b；评估集 eval_a..d 只跑选中 winner 的 24 条候选轨迹
  与 24 条静态参照轨迹。
- 候选调度语义 = 每个分段一个 `LocalNeighbourMDExecution`，分段边界 reset
  projector（R439 冻结语义）；D 增益 = M 增益（diagonal grid，R439 冻结）。

### Selection (frozen, development-only)

- 对每个开发 profile：跑静态参照 + 350 候选（6 signed scenarios 每个），用
  R452 的 `candidate_guard` 生成 7 个相对 guard；不读任何 eval profile。
- 对候选 c 的每条开发 profile 判 `joint_guard_feasible` = valid 且两个端点
  improvement 都 >=5% 且 common(freq,peak,rocof) <=+3% 且 action(RMS,TV)<=+10%
  且 saturation<=5%。
- 冻结选择规则，按优先级：
  1. 若存在在 dev_a 与 dev_b 都 `joint_guard_feasible` 的候选，取其中
     两个 profile 的 `(disturbance_improvement + off_diagonal_improvement)` 之和
     最大的一个；并列取 `global_index` 最小的。
  2. 否则取在任一开发 profile 上 `joint_guard_feasible` 的候选中，可行 profile
     数最大、其次 improvement 和最大、再次 global_index 最小。
  3. 否则取全候选中最坏相对 guard 违约最小者（minimize 所有 7 个相对比相对其
     阈值的最大超出，正超出越少越好），并列取 global_index 最小。
- 选择产物 = `selection.json`，记 winner candidate_id / schedule / 走哪条
  priority 分支 / 开发集 per-profile guard 明细；只由开发集 shard 生成。

### Evaluation (frozen, winner-only)

- 对 eval_a..d 各跑静态参照 + winner 候选（6 signed scenarios 每个），报告
  per-profile 相对静态的 7 个 guard 明细与 `joint_guard_feasible`。
- transfer 计数 = 四条 eval profile 中 `joint_guard_feasible` 为真的条数。

## Theory intake

```
observable: development_selects_guard_clean
  source: results/research_loop/r458_dev_select_eval_validate/selection.json
  predicts: 开发集存在守卫全清候选（priority-1 或 priority-2 命中）才会使
            "开发集选 + 评估集验"的 winner 有 transfer 语义；priority-3 命中
            则声明为 fallback，不得称 guard-clean witness
observable: guard_clean_transfer_count
  source: results/research_loop/r458_dev_select_eval_validate/formal_analysis.json
  predicts: 样本外 winner 在至少一条 eval profile 上 joint_guard_feasible =>
            GUARD-CLEAN-TRANSFER；否则 NO-GUARD-CLEAN-TRANSFER
```

## Gate

- 完整性失败（source/seal/sidecar 漂移、candidate 序列不匹配、trajectory 数
  不符、任何 shard 非零或无效、开发集选择未完成）=> `CANARY-INVALID`，不重试。
- `GUARD-CLEAN-TRANSFER`：选择走 priority-1 或 priority-2，且 winner 在
  >=1 条 eval profile 上 `joint_guard_feasible`。
- `NO-GUARD-CLEAN-TRANSFER`：选择走 priority-1/2 但 transfer 计数 = 0。
- `FALLBACK-NO-WITNESS`：选择走 priority-3；不论 eval 结果只报 witness 缺位，
  并附 transfer 计数供描述性参考。
- 不主张任意控制器可行 / 结构不可能 / learner 成功 / 拓扑 / 稳定 / 部署。

## Formal launch contract

- formal_entry：`/home/wya/andes_venv/bin/python scripts/andes_scratch.py
  scripts/run_r458_dev_select_eval_validate.py <command>`（WSL）
- rehearsal_command：同上 `rehearse`；走 formal entry 的 same pre-attempt path。
- 两阶段共享驱动：phase1 = dev 候选 32 shard + 静态 2 shard；phase2 = 选择后
  eval 静态 4 shard + winner 4 shard。每 phase 用
  `scripts/soft_spot_shard_driver.py` 以 16 workers 驱动。
- capacity_evidence：`memory/rounds/R458/capacity_evidence.json`（同 R452 阶梯，
  每 rung 32 jobs，复测在 5%±2pp 边界才触发）。
- host_process_budget：17；wsl_python_processes：17；
  native_threads_per_process：1；other_reserved_processes：0。
- 不训练；每个进程原生数值库线程 = 1。

## 资产保护契约

- 只读：R439/R441/R452/R453 code/checkpoints/results/plans/seals、R416 契约、
  `md_decoupling_headroom.py`、V4 环境、`soft_spot_shard_driver.py`。
- 新建：R458 runner/tests/plan/seal/rehearsal/capacity、
  create-only `results/research_loop/r458_dev_select_eval_validate/`、正常
  feed/claim/manifest closeout。
- 不重写任何历史结果；不调 grid / 阈值 / learner / 调度语义。

## Cross-references

- R453 feed/CLM-1410；R439 feed/CLM-1355；R441 feed/CLM-1365；
  `working/route_owner_decision_advisory_unresolved_2026-08-21.md`；
  `working/soft_spot_experiment_program.md`。
