---
round: R423
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-17'
closed: '2026-08-17'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R423 plan — 反馈环：价值估计稳定性修复轮（修估价单因素）

**Opened**: 2026-08-17
**Driver**: 反馈环（owner 指示不间断机制）。R422（CLM-1265）实测：共模
通道动作强度项把共模 Lagrange 乘子顶到上限 10.0（6/6 组），护栏仍 36/36
失败——约束压力激活也不转化为合规；联合 R421（CLM-1255）读数（critic
loss 发散 24-126x、TD-error 5-11x、actor 梯度消失），残余定位到学习动力
学（估价发散），而非缺失奖励项。本轮单因素 = CD 臂 critic 梯度裁剪
（clip_grad_norm_, max_norm 1.0 冻结，bounded Deep Research 菜单 P3）；
scalar 臂逐字不变（轮内隔离对照 + 字节锚）。奖励 seam 逐字保留 R422
（共模动作强度项），否则 = R422 逐字。
**Parent**: CLM-1255 (R421 读数)；CLM-1265 (R422 负结果)；校准日志
2026-08-17 联合选轮条目。
**Concurrency**: 独占轮（同线无其他活动轮，other_reserved_processes: 0）。

## TL;DR

Workload: `evidence`。Training。唯一变化因子 = CD 臂 critic 更新路径的
价值估计稳定化修复：`torch.nn.utils.clip_grad_norm_`（max_norm=1.0 冻结，
bounded Deep Research 菜单 P3，见 `r423_value_estimation_repair_deep_research_2026-08-17.md`；
取菜单建议带 0.5-1.0 的上限，理由：直接封顶实测 24-126x critic-loss 发散、
经联合 critic 同时约束双通道、预算/Lagrange/奖励语义零改动、单行实现
风险最低；DR 首选的 PopArt 只归一化差模通道，而 R422 实测失败通道在共模，
且其运行时变尺度会引入 actor 目标混淆）。修复只落在 CD 臂子类
（`ClippedCriticSlewAwareCDMATD3`，独立模块），scalar 臂 learner 与奖励
逐字 R422（字节锚 SCALAR-BIT-IDENTICAL）；奖励 seam = R422 逐字（共模
动作强度项 weight 1.0）；R419 束（9 槽增广、掩码、种子 401/402/403、
43,200 步/组、同超参/估计器/guard/checkpoint）逐字。预注册判定：任臂全
guard 通过或分类翻转 → 修复确认（CANARY-PASS 路径）→ 记录并按证据更新
手稿（creative 条款）；仍 CANARY-FAIL → 报告 + 端点与 guard 分布对
R419/R420/R422 三基座对照 + 修复后 critic-loss 趋势读数（预注册 Q4/Q1
判据，见 Gate）。预算：独占阶梯 rungs 1/2/4/8/12/16（solo 5% 边际链 +
headroom 内存规则）后封存；9 shards 共享驱动单波；串行 evaluate +
classify。

## Methodology

### Mission boundary

- Outcome: 9 manifest（含 critic-loss 趋势与限速诊断）+ 240 评估 + 24
  确定性 record + formal_analysis（冻结分类 + 端点/消息增量/限速诊断表 +
  vs R419/R420/R422 三基座中位对照）+ critic-loss 趋势读数 +
  feed/claim/verdict/LINE 一致关闭。
- Authority: 反馈环（creative 条款；owner 并发授权 2026-08-17 硬件）。
- Permitted: 新 learner 模块（修复子类，独立文件）、runner
  `scripts/run_r423_value_estimation_repair.py` + 测试、results 根
  `results/research_loop/r423_value_estimation_repair/`（create-only）、
  共享分片驱动、正常收尾。
- Forbidden: 改 cd_matd3.py 字节（R419/R420/R422 seal 的 learner 源
  hash 依赖它逐字不变）；改 R419/R420/R422 runner/契约模块；换算法；训练
  期访问评估剖面；scalar 臂奖励或 learner 改动；动 paper-cited 资产。
- Terminal: formal_analysis.json 存在且 9+40 文件齐全。

### 冻结协议 (frozen-first)

- 修复点：CD 臂 critic 更新路径 —— `_critic_update` 覆盖在
  `ClippedCriticSlewAwareCDMATD3`（`src/andes_rl_kundur/agents/cd_matd3_vfix.py`），
  在 `loss.backward()` 与 `critic_optimizer.step()` 之间施加
  `torch.nn.utils.clip_grad_norm_(critic.parameters(), max_norm=1.0)`；
  其余 critic 计算逐字复制基类。max_norm=1.0 冻结（菜单 P3 建议带
  0.5-1.0 上限；1.0 封顶实测爆炸更新、保留健康早期更新）。
- 修复只落在 CD 臂子类；基类、scalar learner（
  `SlewAwareYangScalarTD3`）与 cd_matd3.py 字节逐字不变（R419/R420/R422
  seal 依赖）。奖励 seam（`_common_channel_costs`，共模 action-effort
  weight 1.0）逐字 R422。
- 锚：scalar 臂 3 组 checkpoint sha256 必须 == R422 同臂同种子
  （SCALAR-BIT-IDENTICAL；runner 在 finalization 机检，不匹配 =
  invalid_reason，组级 fail-closed）；确定性参照评估逐字不变。
- critic-loss 趋势：每 run 记录 per-update critic loss 到
  `critic_loss_trace.json`（log-only，不消耗 RNG），classify 按冻结
  读数规则算 Q1/Q4 中位（前/后 25% 有效 update）+ 比值，写入
  `formal_analysis.json#/critic_loss_readout`。
- 其余 = R422 逐字（增广、投影语义、掩码、超参、种子、调度、诊断）。

## Gate

- 分类树 = 冻结 classify_canary（同 R422）。
- Outcomes (pre-registered, decision tree): CANARY-PASS 或任臂全 guard
  通过 = 修复确认 → 记录、按证据更新手稿、继续；仍 CANARY-FAIL = 报告 +
  端点/guard 分布与 R419/R420/R422 对照 + critic-loss Q4/Q1 读数
  （预注册判据：修复后 critic loss Q4/Q1 < 3x = 发散被压制；否则发散
  持续）；CANARY-INVALID = 调查。
- 锚：scalar 臂 3 组 checkpoint sha256 == R422 同臂同种子（
  SCALAR-BIT-IDENTICAL，任何不匹配 = DRIFT）；确定性参照评估逐字不变。

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/soft_spot_shard_driver.py --runner scripts/run_r423_value_estimation_repair.py --shards tmp/andes/r423_train_shards.json --workers <ladder> --round R423` (9 train shards) + `... run_r423_value_estimation_repair.py evaluate` + `... classify`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r423_value_estimation_repair.py rehearse`
- rehearsal_scope: same-pre-attempt-path: authority checks + snapshot + 每臂 1 步真实增广 rollout + replay store + learner update 演练（含 CD 臂修复路径 critic clip + 共模动作强度奖励路径）+ save/load roundtrip。
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- capacity_evidence: memory/rounds/R423/capacity_evidence.json
- host_process_budget: 17
- wsl_python_processes: 17
- native_threads_per_process: 1
- other_reserved_processes: 0

## 资产保护契约

- R419/R420/R421/R422 资产只读（对照与锚只读引用）；`cd_matd3.py` 字节
  不动（修复子类在独立模块）；paper-cited 资产只读；dirty worktree 保留。
- 新文件仅: 修复 learner 模块 + tests、run_r423 runner + tests、R423
  results 根（create-only）、ledger/feed/手稿收尾文件。

## Cross-references

- CLM-1255 (R421)；CLM-1265 (R422)：本轮的父证据。
- `working/r423_value_estimation_repair_deep_research_2026-08-17.md`：
  修复菜单（bounded Deep Research）。
- `working/gate_calibration_log.md`（2026-08-17 联合选轮条目）。
