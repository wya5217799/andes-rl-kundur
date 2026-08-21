---
round: R422
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R422 plan — 反馈环：共模通道动作强度修复轮（与 R421 并行）

**Opened**: 2026-08-17
**Driver**: 反馈环（owner 指示不间断机制 + 2026-08-17 并发授权）。R420
（CLM-1250）实测：动作强度项放差模通道 = 负结果（端点回退、通信增益转
负、无伤害护栏恶化）；机制结论 = 该项放错了通道。本轮单因素 = 同一
R403 风格动作强度项（权重 1.0 冻结）从差模通道搬到**共模通道**，差模
通道回 R419 原样；R419 限速束逐字保留。scalar 臂奖励不变（轮内隔离对
照）。
**Parent**: CLM-1245 (R419)；CLM-1250 (R420 负结果)；校准日志
2026-08-17（owner 并发授权 + 总内存规则）。
**Concurrency**: 与 R421（B3 诊断，active）并行。owner 授权 2026-08-17：
R421 的 7 个进程（6 worker + 1 驱动）在本轮声明为
`other_reserved_processes: 7`；内存规则 = 本轮投影活训内存 + 声明保留
内存 + 3 GiB 系统底 ≤ WSL 总内存；阶梯在共享负载下实测，取全部记录有
效且内存安全的最大 rung（5% 边际链在共享负载下豁免）。

## TL;DR

Workload: `evidence`。Training。唯一变化因子 = 动作强度项通道：CD 共模
成本 += 1.0 × 逐步执行动作平方均值（R403 修复权重，冻结）；差模通道
回 R419 逐字；R419 束（9 槽增广、目标语义对齐、掩码修复、种子
401/402/403、43,200 步/组、同超参/估计器/guard/checkpoint）逐字保留。
scalar 臂奖励不变，作轮内对照。同轮限速诊断照记。预注册判定：任臂全部
物理 guard 通过或分类翻转 → 通道假设确认（CANARY-PASS 路径）→ 记录并按
证据更新手稿（creative 条款）；仍 CANARY-FAIL → 报告 + guard 分布与
R419/R420 三基座对照。预算：训练阶梯 rungs 1/2/4/8/12/16 后封存；
9 shards（arm|seed）共享驱动；串行 evaluate + classify。

## Methodology

### Mission boundary

- Outcome: 9 manifest（含限速诊断）+ 240 评估 + 24 确定性 record +
  formal_analysis（冻结分类 + 端点/消息增量/限速诊断表 + vs R419/R420
  三基座中位对照）+ feed/claim/verdict/LINE 一致关闭。
- Authority: 反馈环（creative 条款 + owner 并发授权 2026-08-17）。
- Permitted: runner `scripts/run_r422_common_channel_repair.py` + 测试、
  results 根 `results/research_loop/r422_common_channel_repair/`
  （create-only）、共享分片驱动、正常收尾。
- Forbidden: 改 R419/R420/learner/契约模块；换算法；训练期访问评估
  剖面；scalar 臂奖励改动；动 paper-cited 资产；影响 R421 封存资产。
- Terminal: formal_analysis.json 存在且 9+40 文件齐全。

### 冻结协议 (frozen-first)

- 奖励改动点：CD 臂每步 common_cost = 共模成本 + 1.0 × (1/4)Σ_i‖a_i‖²
  （执行后动作、归一化域）；差模通道与 Lagrange 预算结构不变；scalar
  臂奖励逐字不变。
- 其余 = R419 逐字（增广、投影语义、掩码、超参、种子、调度、诊断）。

## Gate

- 分类树 = 冻结 classify_canary。
- Outcomes (pre-registered, decision tree): CANARY-PASS 或任臂全 guard
  通过 = 通道假设确认 → 记录、按证据更新手稿、继续；仍 CANARY-FAIL =
  报告 + guard 分布与 R419/R420 对照；CANARY-INVALID = 调查。
- 对照表：端点中位 vs 确定性参照、消息增量、guard 失败分布（按 guard
  类型计数）与 R419/R420 并列。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r422_common_channel_repair.py --shards tmp/andes/r422_train_shards.json --workers <ladder> --round R422` (9 train shards) + `... run_r422_common_channel_repair.py evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r422_common_channel_repair.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 每臂 1 步真实增广 rollout + replay store + learner update 演练（含 CD 臂共模通道动作强度项奖励路径）+ save/load roundtrip。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R422/capacity_evidence.json
- host_process_budget: 24
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 7

## 资产保护契约

- R419/R420/R421 资产只读（对照只读引用）；learner 字节不动（reward 在
  runner 计算）；paper-cited 资产只读；dirty worktree 保留。
- 新文件仅: run_r422 runner + tests、R422 results 根（create-only）、
  ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1245 (R419)；CLM-1250 (R420)：本轮的父证据与对照源。
- R403 修复先例（physical_costs_with_action_effort，weight 1.0）。
- `working/feedback_loop_deep_research_2026-08-17.md`；
  `working/gate_calibration_log.md`（owner 并发授权 2026-08-17）。
