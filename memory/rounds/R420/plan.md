---
round: R420
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R420 plan — 反馈环：目标修复轮（B1 束 + 动作强度项）

**Opened**: 2026-08-17
**Driver**: 反馈环（owner 指示不间断机制）。R419 实测把残余失败钉在
目标-判决不匹配：CD 目标无动作强度/无伤害条款。本轮单因素 = 给 CD
差模通道补上 R403 风格的逐步执行动作平方均值惩罚（权重 1.0 冻结）。
**Parent**: CLM-1245 (R419 端点翻转 + 残余定位)；R403 修复先例
（physical_costs_with_action_effort）；校准日志决策 2026-08-17。

## TL;DR

Workload: `evidence`。Training。唯一变化因子 = CD 差模成本 +=
1.0 × 逐步执行动作平方均值（R403 修复权重，冻结）；R419 束逐字保留
（9 槽增广、目标语义对齐、掩码修复、种子 401/402/403、43,200 步/组、
同超参/估计器/guard/checkpoint）。scalar 臂奖励不变，作轮内对照。
同轮限速诊断照记。预注册判定：任臂全部物理 guard 通过或分类翻转 →
目标-判决不匹配假设确认（CANARY-PASS 路径）→ 记录并按其证据更新手
稿（creative 条款）；仍 CANARY-FAIL → 报告（目标修复不足以翻判负，
残余因素进一步收窄）。预算：训练阶梯 rungs 1/2/4/8 后封存；9 shards
（arm|seed）共享驱动；串行 evaluate + classify。

## Methodology

### Mission boundary

- Outcome: 9 manifest（含限速诊断）+ 240 评估 + 24 确定性 record +
  formal_analysis（冻结分类 + 端点/消息增量/限速诊断表 + vs R419 中位
  对照）+ feed/claim/verdict/LINE 一致关闭。
- Authority: 反馈环（creative 条款；奖励塑形方向 = CLAUDE.md 突破
  方向之一，非算法扫荡）。
- Permitted: 新 runner `scripts/run_r420_objective_repair.py` + 测试、
  results 根 `results/research_loop/r420_objective_repair/`
  （create-only）、共享分片驱动、正常收尾。
- Forbidden: 改 R419/learner/契约模块；换算法；训练期访问评估剖面；
  scalar 臂奖励改动；动 paper-cited 资产。
- Terminal: formal_analysis.json 存在且 9+40 文件齐全。

### 冻结协议 (frozen-first)

- 奖励改动点：CD 臂每步 differential_cost = 差模成本 + 1.0 ×
  (1/4)Σ_i‖a_i‖²（执行后动作、归一化域）；common 通道与 Lagrange
  预算不变；scalar 臂奖励逐字不变。
- 其余 = R419 逐字（增广、投影语义、掩码、超参、种子、调度、诊断）。

## Gate

- 分类树 = 冻结 classify_canary。
- Outcomes (pre-registered, decision tree): CANARY-PASS 或任臂全 guard
  通过 = 假设确认 → 记录、按证据更新手稿、继续；仍 CANARY-FAIL =
  报告 + guard 分布 vs R419 对比；CANARY-INVALID = 调查。
- 对照表：端点中位 vs 确定性参照、消息增量、guard 失败分布（按 guard
  类型计数）与 R419 并列。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r420_objective_repair.py --shards tmp/andes/r420_train_shards.json --workers <ladder> --round R420` (9 train shards) + `... run_r420_objective_repair.py evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r420_objective_repair.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 每臂 1 步真实增广 rollout + replay store + learner update 演练（含 CD 臂带动作强度项的奖励路径）+ save/load roundtrip。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R420/capacity_evidence.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- R419/R410 资产只读（对照只读引用）；learner 字节不动（reward 在
  runner 计算）；paper-cited 资产只读；dirty worktree 保留。
- 新文件仅: run_r420 runner + tests、R420 results 根（create-only）、
  ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1245 (R419)：本轮的父证据与对照源。
- R403 修复先例（physical_costs_with_action_effort，weight 1.0）。
- `working/feedback_loop_deep_research_2026-08-17.md`；
  `working/gate_calibration_log.md`（决策记录）。
