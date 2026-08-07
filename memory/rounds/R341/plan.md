---
round: R341
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-05'
closed: '2026-08-05'
supersedes_rounds:
- R340
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R341 plan - staged fresh predictor validation

**Opened**: 2026-08-05
**Driver**: 先排除非法输入和短程硬伤，再分批回答 Q-0089，避免长跑末尾才首次得到可判断产物。
**Parent**: CLM-0890; CLM-0895; Q-0089

## TL;DR

不重跑 R340。先离线检查全输入库，再在已公开工况做 25 步开发短跑；短跑失败就停。通过后，才封存两个全新工况和 66 条正式记录。正式记录分三批，每批完成即生成不可覆盖的执行清单、哈希和离线判定；任何一条合格记录超过既定误差上限，就直接形成有效否定结果并停止。只有三批全部通过，才允许 `ALLOW-MODEL-GATE`。

论文标题保持 `Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning`。本轮不执行控制器、闭环、分布式智能体、奖励、训练或论文标题结论。

## Snapshot at plan-time (oracle as of 2026-08-05)

- Q-0089 open。R339 仅允许候选模型进入全新非线性验证。
- R340 completed INVALID：输入库与非负负荷守卫冲突；不得重试、复用其轨迹或读取部分误差。
- R340 的 60 条部分轨迹不进入模型选择、阈值、工况、波形或正式判定。
- 解决包已用于 R339/R340 的独立物理输入列、控制与扰动联合十二阶降阶、原阈值和新工况验证路线；本轮只修复其未检查输入物理可行性的工程缺口。

## Methodology

### Frozen model

保持 R339 的完整微分代数线性化、四个独立物理负荷输入、四个控制输入、联合十二阶降阶、`0.2 s` 采样、25 个 Markov 样本、八行八列、无极点投影及全部构造守卫。每个正式工况只从该工况平衡点导数生成候选模型；任何新非线性轨迹不得参与模型构造或选择。

### Gate 0 - offline bank feasibility

封存前必须让每条输入调用生产环境的 `TimedPQProfileContract`。汇总全部拒绝项后一次失败；不得复制或另造物理阈值。R340 原输入库必须在一秒级被拒绝四次；R341 库必须零拒绝。此检查不运行 ANDES，不生成科学数据。

### Gate 1 - exposed-point development canary

只用已公开的 HS0/HS1：设备 M/D 为 `177.5/88.75`、`202.5/101.25`；联络线比例 `1.10/1.35`；初始荷电状态 `0.41/0.51`。每点一个零输入，加四个负荷位置、正负方向、较高合法幅值、`ramp_hold_unit`，共 18 条、25 步。并发上限 16，原生数值线程均为一。

短跑产物只写 `tmp/r341_development_canary/`，身份固定为 DEVELOPMENT。若构造、物理守卫、完整线性模型或十二阶模型任一失败，停止本轮正式封存，Q-0089 保持 open；不得换结构、阶数、符号、阈值后原轮重试。通过只说明执行链可继续，不形成论文证据。

### Gate 2 - fresh formal bank

正式工况由已公开 HS 点与已公开 R340 点逐参数中点唯一确定，不使用任何轨迹误差：

- FV0: `vsg_m_device=183.75`, `vsg_d_device=91.875`, `tie_rx_scale=1.16`, `initial_soc=0.435`。
- FV1: `vsg_m_device=211.25`, `vsg_d_device=105.625`, `tie_rx_scale=1.40`, `initial_soc=0.535`。

新波形：

- `ramp_hold_unit=[0.25,0.50,0.75,1.00,1.00,0.75,0.50,0.25]`；
- `separated_pulse_unit=[1.00,0.50,0.00,0.00,0.00,0.50,1.00]`。

每个负荷通道的两个峰值幅度固定为
`min(0.03, 0.40*P0)` 与 `min(0.07, 0.80*P0)` system p.u.，其中 `P0` 是已注册初始有功负荷。故前三个位置仍为 `0.03/0.07`，Bus15 为 `0.02/0.04`。该公式只由 R340 暴露的物理守卫和基线决定，不读取预测误差。

每点：一个零输入，以及四位置、两波形、两幅值、正负方向的笛卡尔积；总计 66 条。每条 1000 步、200 秒。原事件语义、五个子步、物理读回、拓扑、基准值、坐标及代数残差守卫不变。

### Gate 3 - immutable staged execution

先完成两个零输入。随后顺序固定，结果不得改变后续输入：

1. `sentinel`: 两点、Bus7/Bus8、`ramp_hold_unit`、两幅值、正负方向，共 16 条；
2. `local`: 两点、Bus14/Bus15、`ramp_hold_unit`、两幅值、正负方向，共 16 条；
3. `second-wave`: 两点、四位置、`separated_pulse_unit`、两幅值、正负方向，共 32 条。

零输入和每批各自 create-only 落盘：执行记录、压缩轨迹、逐文件哈希、批清单、批分析。批分析只在该批及对应零输入全部完成后离线运行。通过时自动进入下一批；不得改源代码、模型、阈值、输入或顺序。有效预测失败立即停止后续批次并关闭 Q-0089 negative。运行/哈希/物理守卫失败为 INVALID；已完成批次保留，只允许形成明确限定到该前缀的事实，不能把 Q-0089 判为通过。

## Outcomes

每条扰动记录分别比较完整采样模型和十二阶模型与同工况非线性零输入差值：

- total NRMSE `<=0.15`；
- peak-normalized vector residual `<=0.20`。

首个适用结果：

- `INVALID`: seal/source/runtime/process/event/hash/物理守卫/确定性重放失败；
- `BLOCK-CONSTRUCTION`: 新工况候选构造失败；
- `BLOCK-FULL-LINEARIZATION`: 任一合格记录的完整模型越界；
- `BLOCK-REDUCTION`: 完整模型全通过但十二阶模型任一记录越界；
- `ALLOW-MODEL-GATE`: 构造及 66 条记录全部通过。

任一 BLOCK 是有效消极结果，不修补本轮。ALLOW 只允许另开确定性物理桥问题，不允许直接进入学习。

## Efficiency and timing

- 离线可行性：小于 1 秒，并发 1，不轮询。
- 开发短跑：预计 5--15 分钟；16 个整机 Python 进程上限；完成后一次检查。
- 正式构造：预计 2--5 分钟。
- 正式首批：按 R340 实测长轨迹速度，预计 30--70 分钟；产出首个可否证结论。
- 正式全批：预计 3--4 小时。运行中只监测进程、批完成数、失败文件、CPU、内存；轮询 20--30 分钟。每批边界再离线分析，不读取未完成记录误差。

## Formal launch contract

- formal_entry: `python scripts/andes_scratch.py scripts/run_r341_staged_fresh_model_validation.py execute --expected-sha256 <validation-seal>`
- rehearsal_command: `python scripts/andes_scratch.py scripts/run_r341_staged_fresh_model_validation.py rehearse-validation --expected-sha256 <validation-seal>`
- rehearsal_scope: sealed source/parent/runtime/case/candidate/input-feasibility/output-absence path; no formal attempt or nonlinear trajectory
- rehearsal_checks: source and parent hashes, installed package and case, candidate hash, all 66 production profile contracts, create-only output absence
- development_canary: `python scripts/andes_scratch.py scripts/run_r341_staged_fresh_model_validation.py canary --expected-sha256 <development-seal>`
- construction_entry: `python scripts/andes_scratch.py scripts/run_r341_staged_fresh_model_validation.py construct --expected-sha256 <construction-seal>`
- wsl_python_processes: 16
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R341/host_capacity.json`
- host_process_budget: 16
- other_reserved_processes: 0

Seal 前必须实际运行同路径 rehearsal。正式结果根为 `results/r341_staged_fresh_model_validation/`，必须不存在。任何 formal attempt 创建后的工程失败均保留；原轮不重试。

## Asset protection

- 不变：R316/R336/R339/R340 全部资产与结果、Q-0089、CLM-0890/0895、论文标题、模型阶数、阈值、事件语义。
- 新增：R341 plan/seals/host capacity；一个 R341 runner、一个纯分析 probe、通用输入库可行性检查及定向测试；正式结果只进 R341 新根。
- 禁止：读取 R340 部分预测误差；覆盖旧文件；控制器、闭环、智能体、训练、评估、拓扑变化、稳定性或安全性结论。

## Stop

开发短跑失败即停；否则在首个有效 BLOCK、首个 INVALID 或全部 66 条通过时停。按 feed gate、claim/question、verdict、LINE/ARTIFACTS、清单、validate/render/tests/repo health 正式收尾。

## Cross-references

- `memory/questions/Q-0089.md`
- `memory/claims/CLM-0890.md`
- `memory/claims/CLM-0895.md`
- `memory/rounds/R339/verdict.md`
- `memory/rounds/R340/verdict.md`
- `docs/adr/0013-candidate-before-validation-and-capacity-bound-long-horizon.md`
