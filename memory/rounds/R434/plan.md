---
round: R434
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-19'
closed: '2026-08-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R434 plan — 学习臂拓扑变体评估（owner 批准, 纯评估, 不重训）

**Opened**: 2026-08-19
**Driver**: owner 批准 2026-08-19（"尽量提高硬件利用率" + 审稿风险分析第 1 项）;
R413 (CLM-1225) 的 12 变体拓扑库只测了构造性控制器（Object B）; 学习臂
（Object A, 论文主角 SAC 消息臂）只在固定拓扑上评估过——R431/R433 feed
Limits 明写 "No claim about other topologies"。本轮把 R433 训练出的两个 SAC
臂（cd_matd3_message / cd_matd3_no_message, seeds 401-405）在 R413 冻结的
10 个 EIG 健全变体上按 R433-verbatim 评估协议重评估。纯评估：无训练、无
learner/reward 改动、无调参、无新 bank。**无人值守启动**: owner 预授权
（2026-08-19 铁律: 09:00 后 agent 停止, 仿真自动跑满硬件）; R433 gate
（pause branch / CANARY-INVALID）由自动化强制, 任一触发即停、请示 owner。
**Parent**: R433 (trained checkpoints + nominal eval records),
R413/CLM-1225 (variant bank + EIG soundness), R431/CLM-1315 (nominal
guard/endpoint baseline)。

## TL;DR

Workload: `evidence`; frozen evaluation-only round on R433-trained SAC
checkpoints. Single factor vs the nominal eval: the topology. Ten
EIG-sound frozen variants from R413/CLM-1225; nominal variant is the
harness-identity anchor (rows must reproduce R433 eval rows exactly).

## Methodology

- Runner `scripts/run_r434_sac_topology_variants.py` = R433 评估路径逐字
  复制 + 单 seam（`R434-SEAM`）: per-profile env 经 R413 冻结
  `TopologyVariantEnvV4.build_variant_env_class` 建于变体拓扑（outage 只走
  `apply_line_outage()`, impedance 只走 ANDES `Line.set`）; 记录落
  `OUT/eval/<variant>/...`; 每条记录带 `variant_id`。drift 测试剥 seam 断言
  每个非 seam 叶语句与冻结 R433 源逐字节一致（R431/R428 模式）。
- 变体库: R413/CLM-1225 冻结 12 变体中的 10 个 EIG 健全变体
  （`EIG_SOUND_VARIANTS` 冻结; out_Line_7_12 / out_Line_9_15 为 case-level
  非健全均衡, 按 R413 判定排除, 只引不跑）。rehearsal 的
  eig_soundness_reference_probe 把列表钉在 R413 sealed
  `formal_analysis.json#/eig_passing_variants`。
- 协议: 与 R433 评估逐字一致 — 确定性评估 + slew 投影（project=True）+
  冻结估计器（`summarise_profile`）与冻结守卫（`_common_guard`/
  `_stress_guard`, 3%/10% 容差）+ 同变体 local-neighbour 确定性参照。
  每变体: 2 臂 × 5 种子 × 4 评估 profile + 参照 = 44 条记录; 10 变体
  = 110 eval shards。
- **nominal anchor（预注册）**: 变体 nominal 的评估行必须与 R433 评估记录
  逐字节一致（同 checkpoint、同 env 种子、同确定性协议）——harness 身份
  强锚（R413 base-case anchor 同款）。不一致 → 停, 诊断, 本轮不重试。
- checkpoint 一致性: 每 (arm, seed) 全部 10 变体的记录引用同一 final.pt
  sha256, 且等于 R433 `final.pt.sha256` 侧车。
- 容量: reuse R433 capacity evidence（R431 rung-16 链, RUN-READY）after
  fresh no-other-process snapshot; 冻结 15 workers（wsl 16, budget 16,
  reserved 0）。

## Frozen scientific contract

1. 评估对象: R433 训练出的两个 SAC 臂 × seeds 401-405（post-training
   final.pt, 只读）。
2. 变体: R413/CLM-1225 的 10 个 EIG 健全变体（冻结列表）。
3. 协议: R433-verbatim（确定性 + 投影 + 冻结估计器/守卫 + 同变体参照）。
4. 无训练 / 无 reward 改动 / 无调参 / 无新 bank / 无其它臂。

## Pre-registered decision tree

1. 任一变体缺行或行无效（TDS 失败 / 非有限 / actuator 映射失败）→ 该变体
   CANARY-INVALID, 保留产物, 本轮不重试。
2. 任一臂在任一变体上全守卫通过（20 块 0 失败, 含动作应力守卫）→
   **pause branch**: 停, 先请示 owner, 不得自行注册任何泛化 / 通用 SAC
   claim。
3. 否则按每变体守卫块分布 + 端点 + 消息对比报告有界端点: 消息臂的
   common-frequency / worst-peak 通过与消息对比在 X/10 变体上保持 →
   才可写拓扑泛化的有界陈述（逐变体数据住 results, feed 只挂 claim id）。
4. 只做同协议对比: R434-nominal vs R433（anchor 逐字节）, 跨变体相对
   nominal。
5. 不授权: 任何重训 / 新变体 / 其它臂 / 其它环境 / 算法改动 / 第三次 SAC
   尝试。

## Capacity and execution card

- 先例证据: R433 capacity evidence（R431 rung-16 链, RUN-READY,
  selected_workers 15）; R434 reuse after fresh no-other-process snapshot
  （owner rule 2026-08-19: check hardware at task start/end, saturate the
  host）。
- Frozen budget: `host_process_budget: 16`, `wsl_python_processes: 16`
  （15 workers + 1 driver）, `native_threads_per_process: 1`,
  `other_reserved_processes: 0`（R433 波次结束后才 seal/launch）。总
  16 <= 32 logical CPUs; 内存: 16 × 0.944 GiB + 3 GiB OS ≈ 18 GiB
  <= 27 GiB WSL MemTotal。
- Ready jobs: 110 eval shards 一波 workers=15（~35-40 min）, 然后串行
  classify。

Execution readiness 按 capacity/rehearse/prepare 顺序; rehearsal 含全部
R434 probes 后 RUN-READY。Sealed concurrency immutable。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r434_sac_topology_variants.py reuse-capacity` → `rehearse` → `prepare` → `shards` → `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r434_sac_topology_variants.py --shards tmp/andes/r434_eval_shards.json --workers 15 --round R434` → `classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r434_sac_topology_variants.py rehearse`
- rehearsal_scope: same-pre-attempt-path; source/parent/runtime/output guards + `variant_env_probe`（outage + impedance 变体上 30 步真实物理步, 突变已应用 + TDS 健康）+ `eig_soundness_reference_probe`（钉 R413 sealed 列表）+ `nominal_env_probe`（nominal 变体 env 身份 == 冻结构造）+ `checkpoint_source_probe`（R433 final.pt 存在 + 侧车一致）; 无 formal artifact
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, variant_env_probe, eig_soundness_reference_probe, nominal_env_probe, checkpoint_source_probe
- capacity_evidence: memory/rounds/R434/capacity_evidence.json
- host_process_budget: 16
- wsl_python_processes: 16
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- Byte-unchanged/read-only: R433/R431/R430/R429/R428/R413 sources, seals,
  results, claims, feeds; `sac.py`, V4 env, classifier, estimators,
  `per_vsg_md.py`, R433 trained checkpoints 与 eval 记录。
- New only: R434 runner/tests（verbatim 复制 + 声明 seam + drift/direction
  测试）, R434 lifecycle artifacts, create-only R434 results 与收尾
  ledger/feed/claim。
- Dirty worktree preserved; no reset/clean/stage/commit; no manuscript
  prose。

## Gate calibration target

- 记录: nominal-anchor 门、EIG 引用门（不重跑）、pause 条件是否
  太硬/太软/刚好。无门在 attempt 内放松。

## Cross-references

- R433（checkpoints + nominal eval records）, R413/CLM-1225（变体库 +
  EIG 健全性）, R431/CLM-1315（nominal 守卫/端点基线）, R430/CLM-1310,
  R428/CLM-1305。
- Workflow authority: `paper/yang_md_decoupling_marl/LINE.md`, owner order
  2026-08-19, `CLAUDE.md`, `skills/kundur-round/SKILL.md`。
