---
round: R410
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-16'
closed: '2026-08-16'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R410 plan — R402 消息对比单因素修复复跑

**Opened**: 2026-08-16
**Driver**: owner 决策
(`working/route_owner_decision_message_repair_2026-08-16.md`)：手稿不得带着
R402 的消息对比洞（nominal no-message 臂 actor 更新吃未掩码邻居槽）交付；
在终稿截止前以单因素修复复跑 matched 对比并把验证结果写回手稿。
**Parent**: CLM-1155/CLM-1160 (R402 canary 及其容量证据)；
`working/r402_causal_validation_final_bundle/` (审计认定掩码合同缺陷)。

## TL;DR

Workload: `evidence`。唯一变化因子 = `cd_matd3_no_message` 的 actor 邻居掩码
在在线/目标/更新三条路径内强制执行（learner 修复 + runner 构造器单行）。
其余全部逐字复用 R402 契约：三臂 × 种子 401/402/403 共 9 组训练（43,200
交互步/组）、同一 8-profile 分区（4 dev + 4 eval）、同一超参/奖励/估计器/
guard/checkpoint 规则。标量与 message 臂代码路径 bit-identical，作为 R402
数值的漂移锚。容量：预封存阶梯 rungs 1/2/4/8 + R402 实测训练 worker RSS
锚 (944,214,016 B) 半内存规则；实测阶梯选中 rung 4（rung 8 边际吞吐不足
5%），封存预算 5 进程（4 worker + launcher）。全量投影 ≈ 5.5 小时。

## Snapshot at plan-time (oracle as of 2026-08-16)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?
- Q-0110 closed-positive @ R396, by CLM-1125 — Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?
- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?

## Methodology

### Mission boundary

- Outcome: 9 训练 manifest + 240 评估 record + 24 确定性参照 record +
  formal_analysis 分类 + 消息增量对比表 + feed/claim/verdict/LINE/手稿一致
  关闭。
- Authority: owner 决策 (2026-08-16)；本轮消费 R402 契约并施加唯一修复。
- Permitted: learner 掩码修复 + 测试、R410 执行 runner + 测试、R410 seal/
  rehearsal/容量证据、results 根 `results/research_loop/r410_message_repair/`、
  分析探针（消息增量表）、正常 ledger/feed/手稿收尾。
- Forbidden: 除掩码外的任何 learner/runner/reward/估计器改动；换算法；新
  未见 bank；动 R402 结果根或 R402 记录；改写标题/摘要主张。
- Terminal: formal_analysis.json 分类为三者之一且消息增量表存在；随后按
  预注册分支处理手稿并关闭本轮。

### 剖面分区复用（本轮的显式授权例外）

- 复用 R402 的同一 8-profile 分区（`evaluation/cd_matd3_canary.py` 冻结
  剖面 canary_dev_a..d / canary_eval_a..d）。理由：消息增量的可识别性要求
  剖面/种子/估计器与 R402 完全一致；这是同一对象的单因素对比，不是新泛化
  主张。复用由 owner 决策明示授权，评估 record 写入全新 R410 结果根
  （create-only，与 R402 产物无碰撞）。

### 实现（本轮新增）

- `src/andes_rl_kundur/agents/cd_matd3.py`（修）：
  `_JointTD3Base.__init__` 增 `actor_neighbour_mask` 旗标；新增
  `_actor_obs_row()`；`act`/`_target_actions`/CDMATD3.update/
  YangScalarTD3.update 全部经它取行。mask=False 时返回原切片（bit-
  identical），标量与 message 臂数值路径不变。新增 2 定向测试
  （tests/test_cd_matd3_learner.py，现 11/11 绿）。
- `scripts/run_r410_message_repair.py`（新）：R402 逻辑的独立 R410 适配器。
  CLI = measure-capacity / rehearse / prepare / train / evaluate / classify。
  构造器处 `actor_neighbour_mask=(arm_id == "cd_matd3_no_message")`。
  load_seal 额外校验 learner 源码哈希（封住单因子）。4 定向测试绿。
- 容量阶梯（runner 内 measure-capacity）：rungs 1/2/4/8、每 rung 4 个代表
  性开发零动作任务；选 rung 规则 = 5% 边际吞吐 + 半 WSL 内存；每 worker
  RSS 下限取 R402 实测锚 944,214,016 B（`capacity_evidence_v2.json`
  projected_training_worker_memory_bytes），阶梯只能上抬不能下调。

### 并行与容量

- 封存预算（实测阶梯冻结）：host_process_budget=5、wsl_python_processes=5
  （4 worker + launcher）、native_threads_per_process=1、
  other_reserved_processes=0。阶梯 rung 决策见
  `memory/rounds/R410/capacity_evidence.json`：rungs 1/2/4 通过 5% 边际
  吞吐，rung 8 未达边际门槛被拒（内存规则一直安全，R402 同机实测
  8×约 920 MB = 7.03 GB ≤ 半内存）。
- 预算在 seal 冻结，封存后不得改。

## Gate

- 分类树 = R402 冻结分类器 `classify_canary`（bank 完整有效 →
  common/动作/饱和/非恒定/独立守卫全过 → message 增量 → seed 一致 →
  优于确定性参照 → 奖励不参与）。结果 `CANARY-PASS/FAIL/INVALID` 语义与
  R402 相同。
- **主预注册测量（本轮新增）**：修复后 no-message 臂 vs message 臂的
  两端点 seed 中位增量（沿用 R402 的 `full_method_improvement_vs_comparators`
  同一计算）。这是运行时消息对比的**第一个干净单因素测量**，正负号一律
  如实报告，并在分类结果语境下解释。
- **漂移锚（预注册）**：标量与 message 臂路径未变，其新中位端点比值必须
  在 1e-6 相对容差内复现 R402 记录（4.12/2.92、5.09/3.30）。偏差 = DRIFT，
  暂停对比解释并调查，不静默继续。
- **暂停分支（预注册，owner 检查点）**：若 (a) 修复后 no-message 臂任一
  seed-profile 块通过全部物理 guard、(b) 分类翻转 R402 结论（如
  CANARY-PASS）、或 (c) 漂移锚超差且无法归因，则本轮在 claim gate 暂停，
  等 owner 决定手稿如何重构；feed 仍照实写。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r410_message_repair.py train --arm <arm> --seed <seed>` (9 次, 4 并发 worker + launcher) + `... evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r410_message_repair.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + source/parent/runtime snapshot + per-arm real 1-step env rollout through the fixed learner (mask exercised) + save/load roundtrip; no formal artifacts created.
- rehearsal_checks: active_plan, active_line, contract_closed, output_absence, source_hash, parent_hash, installed_package, installed_case
- capacity_evidence: memory/rounds/R410/capacity_evidence.json
- host_process_budget: 5
- wsl_python_processes: 5
- native_threads_per_process: 1
- other_reserved_processes: 0

## 执行修正（owner 授权，2026-08-16，只改并发不改科学契约）

- Owner 在训练第二波期间指示充分利用 CPU。依据 R402/CLM-1160 修正先例
  （容量修正：只改并发数，臂/种子/步数/奖励/判据契约逐字不变），本轮登记
  以下执行修正：
- **评估分片并行**：评估 seam 由单进程 `evaluate` 改为按 (arm, seed) 分片
  进程，每片仍调用封存 runner 的同一 `_evaluate_arm_seed` 函数（同代码路径、
  同 create-only 输出路径），分片驱动为临时编排
  `tmp/andes/r410_eval_shard.py`（不进封存源码清单）。
- **并发账**：末组训练（1 worker）与最多 3 个评估分片重叠 = 4 worker +
  1 launcher，恰等于封存预算 5 进程，不超。评估记录内容与顺序不变；
  分类器只读全部落盘的哈希记录，不感知评估并行度。
- 判定树、guard、估计器、剖面、种子、预算上限全部不变。

## 资产保护契约

- 保留 dirty worktree；不 reset/clean/stage/commit；不覆盖其他线资产。- R402 runner/结果/记录/契约模块全部只读；`evaluation/cd_matd3_canary.py`
  不动；R398–R409 资产只读。
- paper-cited 资产（`base_env.py`、`andes_vsg_env_v4.py`、`train.py`、
  `paper_grade_axes.py`）只读。
- learner 修复是唯一进入 src 的改动；R403 的 `FixedWeightCDMATD3` 不动。
- 正式输出 create-only；崩溃 quarantine 保留；评估不重试；分类只读输入。

## Cross-references

- CLM-1155 (R402)：被修复的历史 canary；新轮与其数值做漂移锚对比
  （锚值来源 `results/research_loop/r402_cd_matd3_canary/` 的
  formal_analysis.json 与 endpoint_table.json）。
- CLM-1160 (R402)：容量扩容授权先例；R410 用其 RSS 锚。
- `working/route_owner_decision_message_repair_2026-08-16.md`：本轮唯一授权。
- `working/r402_causal_validation_final_bundle/IMPORT_NOTE.md`：缺陷认定与
  "no retraining required" 审计结论（owner 以正确性优先推翻，改按本计划
  修复复跑）。
