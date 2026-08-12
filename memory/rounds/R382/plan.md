---
round: R382
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-13'
closed: '2026-08-13'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R382 plan — bounded outcome-seeing power-port headroom witness

**Opened**: 2026-08-13
**Driver**: 在停止继续设计确定性控制器后，用最小有限候选族判断同一四个
功率端口上是否仍有足以支持后续学习问题的联合解耦余量。
**Parent**: CLM-1010（功率端口权限）, CLM-1050（两级冲洗方案开发集判停）

## TL;DR

本轮不是 R381 的后续参数调整，也不重开其余量门。它把 R381 的有效本地
控制轨迹只作为已冻结设计输入，生成一个有界、非因果、看完整结果的四候选
残差族；新物理执行只回答“该有限族能否在相同功率、爬坡、能量与时序约束
内发现至少 5% 的联合余量”。无论结果如何都不训练。

## Snapshot at plan-time (oracle as of 2026-08-13)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?

## Methodology

### 对象、比较和推断上限

- 同一修改 Kundur V4、四个 VSG 自有储能功率端口、0.2 秒更新、50 步、
  60 Hz 物理端点、旧 M/D 动作为零；沿用 R381 的十个开发条件与有效本地
  基线记录，不接触其未打开的评价集。
- 基线是 R381 的 `local_feasibility_native`。候选在每一步先重算同一个本地
  PI 基线，再通过 `map_residual_action` 只使用该基线到当前上下界的剩余
  headroom；外层投影必须恒等。
- 唯一额外权限是候选读取完整本地结果并按条件选择最优结果。因此比较门为
  `QUALIFY`：只识别冻结有限族的可达余量见证，不识别可部署控制器、全局
  最优、MARL 价值或算法类别。

### 冻结候选族

- 对每个本地基线记录，令每步差频为四机频率减去当步均值；向前移动 2 步
  （0.4 秒，末尾保持最后值），按整条记录最大绝对值归一化，再取负号形成
  非因果阻尼方向。
- 仅四个候选：幅值 `{0.25, 0.50}` 乘极性 `{-1,+1}`。每条序列严格零和、
  有时间变化、依赖四机协调状态；候选定义、顺序和生成算法在任何新物理
  结果可见前冻结。
- 十个条件各执行四个候选，共 40 条新轨迹。扰动条件逐条选差频能量最小的
  有效候选；每个探针坐标联合枚举正负记录的 16 种候选配对，在本坐标响应
  能量不少于本地基线 90% 的前提下选串扰能量最小者。

### 守卫、端点和判定

- 每条记录必须完成 50 步、无仿真失败、数值有限、旧 M/D 为零、SOC 在
  `[0.20,0.80]`、残差在 `[-0.50,0.50]` 且逐步零和、基线功率可行、
  requested=commanded、无外层投影或能量饱和、统一时序。
- 两个联合主门：组装 oracle 的平均扰动差频能量不高于本地的 `0.95`；探针
  绝对串扰能量和串扰/本坐标响应比均不高于本地的 `0.95`。
- 无害门：平均差频稳定时间不差于本地；每个扰动条件的公共频率积分绝对
  误差不高于本地的 `1.05`，最坏设备峰值和最大变化率不高于 `1.10`。
- 全部守卫和联合门通过 -> `BOUNDED-HEADROOM-WITNESS-PASS`，只说明同一
  端口有可检测的有限族余量，下一步仍须另行做本地信息可预测性门；否则 ->
  `STOP-NO-DETECTED-JOINT-HEADROOM`。缺记录或守卫失败 ->
  `ANALYSIS-INVALID`。任何分类均 `training_authorized=false`。

### 比较可识别性

- 动作坐标、物理可行集合、功率/爬坡/能量/SOC 限制、执行端口和时序一致。
- 信息与选择预算不一致且故意偏向 oracle：完整结果、每条件四候选、结果后
  选择。故只允许“有限候选族发现/未发现联合余量”；禁止“理论最大改善”、
  “没有任何学习空间”或“集中式/分布式优劣”。

## Formal launch contract

- `formal_entry`: `scripts/run_r382_bounded_headroom_witness.py`，正式物理命令
  只经 `scripts/andes_scratch.py` 在 WSL ANDES 2.0.0 执行。
- `rehearsal_command`: `/home/wya/andes_venv/bin/python
  scripts/andes_scratch.py scripts/run_r382_bounded_headroom_witness.py
  rehearse`；只检查来源/父产物哈希、安装环境、活动计划、输出不存在、合同
  闭合和竞争进程，不执行物理轨迹。
- `rehearsal_scope`: 与正式入口相同的 pre-attempt 校验路径；
  `rehearsal_checks`: 所有检查为真且 `physical_trajectory_executed=false`。
- `wsl_python_processes`: 1；`native_threads_per_process`: 1；
  `host_process_budget`: 1（该 create-only 串行尝试的硬上限）；
  `other_reserved_processes`: 0，发现其他研究 Python 进程即停。
- `capacity_evidence`: R381 以同一 plant/port/schema 串行完成 30 条、每条
  50 步的新轨迹用时 231.73587597103324 秒；按 40 条线性投影约 309 秒，
  乘既有 1.5 安全系数约 464 秒。预演重查主机、可用内存、磁盘、运行时和
  竞争进程；不新开并行隔离机制。
- seal 前只允许定向测试、纯函数候选生成/分类 canary 和上述零轨迹预演。
  seal 后首次 attempt 前失败则本轮 aborted；attempt 后不重试、不改候选、
  不改阈值、不补跑。

## Gate

一个问题：在 R381 本地基线和十个开发条件上，结果特权但功率权限匹配的
四候选时变残差族，能否同时给出至少 5% 的扰动差频能量改善和至少 5% 的
探针串扰改善，并通过物理与无害门？PASS 只开放信息门；STOP 结束当前功率
端口上的 MARL 实验路线并转入论文收束；INVALID 只允许新轮修复工程有效性。

## 资产保护契约

- 不变：R364-R381 的计划、封印、结果、claim、feed、verdict；V4/base env、
  功率端口、能量合同、动作映射、本地控制器、开发/评价条件和旧结果。
- 可新增：R382 纯候选/分类模块、稳定 runner、定向测试、create-only result
  root、seal/capacity/rehearsal、一个 feed/claim/verdict、manifest 与当前线导航。
- 禁止：读取 R381 未执行评价集、修改本地控制器、增加候选、结果后改阈值、
  重试、训练、旧结果覆盖、另一论文线写入或正文正面宣传。

## Cross-references

- CLM-1050 / R381：两级冲洗候选开发集判停；本轮不是重试该控制器。
- CLM-1010 / R373：四个 VSG 自有功率端口的权限和物理约束来源。
