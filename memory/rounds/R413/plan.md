---
round: R413
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds:
- R412
superseded_by_round: null
abort_reason: null
superseded_note: 'R412 (same A2 protocol) aborted on a sealed-runner defect: eig_gate
  crashed on the two init-divergent variants instead of recording a gate failure.
  This round re-runs the identical frozen protocol with the graceful-failure fix and
  a failure-path rehearsal.'
---
# R413 plan — A2 拓扑变体鲁棒性（R412 后继，同协议）

**Opened**: 2026-08-17
**Driver**: soft-spot program A2 后继轮。R412 以 aborted 终止（封存 runner
缺陷：两个初始化发散变体在 EIG 门崩溃而非记录失败）；本轮回跑同一冻结
协议，runner 带优雅失败修复，rehearsal 增加失败路径演练。
**Parent**: CLM-1195 (R408 Q-ENTRY)、CLM-1210 (R409 HELDOUT-PASS)、
CLM-1220 (R411 A1)；R412 abort 记录（校准日志 2026-08-17）。

## TL;DR

Workload: `evidence`。Eval-only。协议与 R412 逐字相同（见其 plan，本文件
只声明增量）：冻结变体库 N=12（nominal + 6 开断 + 5 阻抗），开断经
`apply_line_outage()`，每变体先过 CLM-0665 EIG 硬门（全值记录）再在
R408 disclosed development bank 复评 K=3.5 带通 + zero/local 参照，阈值
= R409（r_d≤0.95、r_cross≤1.10、全 R379 guards），nominal = 基案例锚
（1e-6 相对复现 R408 0.938947/0.539791）。**两处修复增量**：
(1) `eig_gate` 全路径 try/except——初始化/谱失败记录为门失败（failure
字段 + passed=False），绝不崩溃；(2) rehearsal 同时演练 nominal 通过
路径与三个代表性变体的失败/通过路径。分片 12、共享驱动、容量阶梯同
R412 规则；预算阶梯后冻结。

## Methodology

### Mission boundary

- Outcome: `formal_analysis.json`（hashed）= per-variant EIG gate 全值 +
  per-variant r_d/r_cross/guards + pass/fail 表 + 基案例锚判定；随后
  feed/claim/verdict/LINE 一致关闭。
- Authority: soft-spot program A2（creative mode）；R412 abort 后按
  creative 条款自动续走后继轮（校准日志已记）。
- Permitted: 新 runner `scripts/run_r413_topology_robustness.py` + 测试
  （`tests/test_run_r413_topology_robustness.py`）、results 根
  `results/research_loop/r413_topology_robustness/`（create-only）、复用
  共享分片驱动与 R408/R372 harness 导入（只读）、正常收尾。
- Forbidden: 改 R408/R409 runner/契约/gate_b3 模块/R379 资产；训练；
  换控制器/阈值/guard；变体库封存后改动；动 paper-cited 资产；读取
  R412 放弃产物作为证据（全新执行）。
- Terminal: 12 variants × (eig_gate.json + records.json) 落盘 +
  formal_analysis.json 存在。

### 冻结协议 (frozen-first)

- 与 R412 逐字相同：TOPOLOGY_VARIANTS 12 项、变异注入（env 子类覆写
  `_build_system`）、EIG 门、R408 development bank、per-variant 判定、
  基案例锚、分片规则。
- EIG 门失败语义（修复）：reset/PFlow/TDS.init/EIG/guard 任一步异常 →
  `failure` 字段记录异常类型与消息，`passed=false`，其余门字段保留
  默认 False；变体照常记录，不终止 shard。
- rehearsal 增量：nominal 1 条完整记录 + nominal EIG 门通过 + 三变体
  （out_Line_4、out_Line_7_12、out_Line_9_15）EIG 门全路径演练（无论
  通过或优雅失败，必须返回良构 payload）。

## Gate

- 与 R412 相同（CLM-0665 EIG 硬门 + R409 端点阈值 + 有界 per-variant
  表 + nominal 锚 + 预注册失败 flag）。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r413_topology_robustness.py --shards tmp/andes/r413_shards.json --workers <ladder> --round R413` (12 shards, driver = launcher, budget 内) + `... run_r413_topology_robustness.py classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r413_topology_robustness.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + nominal 变体 1 条完整记录（同 job loop）+ nominal EIG 门通过路径 + 三变体 EIG 门失败/通过路径演练（不创建 formal artifact）。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R413/capacity_evidence.json
- host_process_budget: 9
- wsl_python_processes: 9
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- 与 R412 相同。R412 结果根（aborted）只读、不进证据；R412 的
  formal_seal.json 保留为审计记录。

## Cross-references

- CLM-1195 (R408)、CLM-1210 (R409)、CLM-1220 (R411)；R412 plan（协议
  真源）+ R412 abort reason；`working/soft_spot_experiment_program.md`
  A2 + owner 决策；SKILL.md §2/§4；CLM-0665。
