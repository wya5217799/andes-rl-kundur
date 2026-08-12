---
round: R380
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R380 plan — four-VSG energy-port source-model gate

**Opened**: 2026-08-12
**Workload**: `evidence`
**Driver**: R376--R379 封死当前一阶阻尼族后，先为本线四个
`SynGen.pref/tm0` 能量端口建立当前对象自己的分输入源模型；模型不过门，不做
控制器设计、物理控制比较或训练。
**Parent**: CLM-1000, CLM-1005, CLM-1010, CLM-1040；PI 选择的新源模型路线。

## TL;DR

本轮只回答一个问题：当前四个独立 VSG 功率端口，能否在两个预先固定的
运行点产生一个源可追溯、控制与扰动分离、0.2 秒末端采样的全阶模型，并在
36 条全新小信号记录上复现四机频率响应。R341 只提供方法；其矩阵、运行点、
降阶模型、增益和结论全部禁用。正式对象为四个控制输入和三个共同可做正负
物理扰动的正基准负荷；默认有功为零的 `PQ_Bus15` 不伪造成可做中心差分的
负荷通道。通过只允许下一次纯离线控制器设计，不允许 ANDES 闭环、训练或
标题结论。

## Snapshot at plan-time (oracle as of 2026-08-12)

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

### 固定对象与运行点

- 平台：当前 modified-Kundur V4，`ZERO_G4_INERTIA=True`，默认 Toggler 关闭，
  四个 VSG 为 `VSG_1..VSG_4`，母线 `[12,16,14,15]`；旧 M/D 动作恒为零，
  无 ESD1。
- `P0`：当前默认平衡点；`PQ_Bus15` 有功基准保持 `0.0` system p.u.。
- `P1`：只在平衡前把 `PQ_Bus15` 有功基准固定为 `0.05` system p.u.，无功
  仍为零；其他模型、参数、拓扑和负荷不变。两点都必须重新通过 PFlow、TDS
  初始化、有限值、残差和设备身份守卫；失败为无效，不换点。
- 控制输入 `u_P[k]`：四个增量 system-p.u. 有功命令，位于可行域原生映射后、
  VSG 端口功率到转矩换算前。零余量点使用
  `delta_tm0 = diag(1/omega_star) delta_u_P`；正式残差回调必须逐次执行这个
  采样速度换算并恢复原值。
- 物理扰动 `d_P[k]`：`PQ_0/Ppf`、`PQ_1/Ppf`、`PQ_Bus14/Ppf` 三个增量
  有功负荷，正号表示需求增加，无功不变。三者在 P0/P1 都有正基准，允许
  固定状态中心差分和全新记录中的正负小扰动。`PQ_Bus15` 只定义 P1 运行点，
  不进入扰动输入；禁止把零负荷的负扰动改名为物理负荷。
- 输出 `y[k]`：四个 VSG 转速相对各自平衡值的 60-Hz 频率偏差，记录在每个
  0.2 秒保持区间末端。一个算术公共坐标和三个算术差分坐标只作报告视图，
  不删除交叉块，也不宣称特征模态。
- SOC、请求/命令/实现功率和能量结算继续作为端口守卫与读回；不把外部 SOC
  账本伪造成 ANDES DAE 的线性状态。

### 源模型构造

每点封存 installed ANDES 版本/源码/案例哈希、平衡 `x,y`、变量名和设备归属、
`Tf,f_x,f_y,g_x,g_y`。四个控制列与三个负荷列独立构造，不得写成
`B(u+d)`、`B_d=B_u M` 或由轨迹拟合。

- 固定状态中心差分步长为 `1e-4,1e-5,1e-6` system p.u.；每次正负求值后
  恢复端口、负荷、`x,y` 和残差状态。
- 每列两组相邻导数的相对 Frobenius 差都不超过 `1e-5`，分母为
  `max(||J||_F,1e-12)`；每个步长的带符号中点残差比不超过 `1e-6`。
  三档全部通过后固定使用 `1e-6` 导数，不能按验证误差选步长。
- 所有零 `Tf` 状态按名字折入代数块；增广代数块 reciprocal 2-norm condition
  至少 `1e-12`。Schur 消元不得用伪逆、匿名删行或删状态。
- 折叠后的连续状态矩阵与 installed ANDES 保留状态约化逐名字对齐：相对
  Frobenius 误差不超过 `1e-8`，最大绝对误差不超过 `1e-9`。
- 全阶模型以零阶保持离散到 `Ts=0.2 s`；末端采样固定为
  `C_post=C A_zoh`、`D_post=C B_zoh + D`。持久化分离的
  `B_u,B_d,D_u,D_d`，不做降阶、极点投影、稳定化或数据拟合。
- 25 个采样的四控制输入 Markov 堆叠矩阵必须在
  `max(shape)*eps*sigma_max` 容差下数值秩为四；标量、公共量、边量或秩亏
  对象直接停止。

### 实现依赖与开发 canary

当前纯适配器只证明实现方向，不是科学证据。正式封存前由 Ask Matt 路由一个
同会话 `/implement`：测试先行地把
`evaluation/vsg_energy_port_source_bridge.py` 从硬编码四负荷修为本轮固定的
四控制/三负荷契约；新增 installed-ANDES 固定 `x,y` 可恢复残差适配器、
R380 runner、判定 probe 和定向测试。不得修改受保护 V4 环境。

实现完成后只在 P0 跑一次 DEVELOPMENT source-only canary，输出进
`tmp/r380_source_model_canary/`；它检查身份、恢复、三档差分、描述符约化和
末端采样链，不跑 TDS 轨迹，不参与阈值、选点或正式判定。失败即停在实现修复，
修复后仍须重新 preflight、rehearsal 和 seal；canary 不是正式入口 rehearsal。

### 全新非线性验证银行

封存后每点新建两条零输入重复、八条单 VSG 控制脉冲、六条单负荷脉冲和
两条控制/扰动联合脉冲，共 18 条；P0/P1 合计 36 条。每条 125 个 0.2 秒
样本，非零区间固定为 `k=5..9`，其余样本为零并恢复基准。

- 控制脉冲：每个 VSG 各 `+0.01/-0.01` system p.u.，其余控制端为零。
- 负荷脉冲：三个负荷各 `+0.02/-0.02` system p.u.，其余扰动端为零；生产
  负荷可行性检查必须在 seal 前拒绝任何负负荷。
- 联合正例：`u_P=[+0.01,0,0,0]`、`d_P=[0,+0.02,0]`。
- 联合负例：`u_P=[0,0,0,-0.01]`、`d_P=[0,0,-0.02]`。
- 每条 nonlinear 响应减同点第一条零轨迹；模型从零偏差状态出发，吃同一
  已实现 `u_P,d_P` 序列，并按末端采样对齐。第二条零轨迹只检查重复性。
- 每条记录硬守卫：端口/负荷身份、正负号、单位、请求=命令、外投影恒等、
  `pref/tm0` 读回、实现功率、M/D 零、负荷非负、事件时刻、PFlow/TDS、
  finite、125 步、源/案例/seal 哈希。任一失败先判无效，不读预测误差。

### 统计单位、阈值与识别边界

单位为一条点-输入-符号记录，采用逐条最坏值，不平均掩盖失败。对 32 条非零
记录，向量 NRMSE 定义为
`sqrt(sum_t ||e_t||2^2 / max(sum_t ||y_nl,t||2^2,1e-24))`，上限 `0.15`；
峰值归一残差定义为
`max_t ||e_t||2 / max(max_t ||y_nl,t||2,1e-12)`，上限 `0.20`。
同点两条零轨迹四频率最大差不超过 `1e-9 Hz`。模态频率和阻尼只可报告为
描述量，不进入本轮判定，避免事后选择识别器或模态匹配。

被比较对象是“封存的全阶源模型预测”与“同一点、同输入、同采样的非线性
ANDES 偏差响应”。模型离线获得完整四频率和精确已施加输入，属于特权诊断；
它不等于分布式执行。无控制器、学习器、调参、种子选择、模型阶数选择或验证
数据回流。最强可识别结论只覆盖当前拓扑、两个点、固定小脉冲和四频率输出。

## Gate

先守卫、再构造、后误差，首个适用结果即停：

1. `INVALID-OBJECT-OR-PORT`：身份、单位、正负号、负荷可行性、PFlow/TDS、
   恢复、哈希、重复性或其他硬守卫失败。不得读取预测误差。
2. `STOP-SOURCE-MODEL`：差分收敛、描述符条件、逐名字约化、有限值、分输入
   或四控制通道秩门失败。模型不成立，不换步长/点/通道。
3. `STOP-MODEL-FIDELITY`：源构造有效，但任一单控制记录越过 `0.15/0.20`，
   或任一点无法完成全部有效记录。停止该模型路线。
4. `QUALIFY-DIAGNOSTIC-ONLY`：两点全部单控制记录通过，但任一单负荷或联合
   记录越界。只允许把控制端小信号模型作诊断；不允许控制器设计或物理执行。
5. `ALLOW-MODEL-BASED-DESIGN`：两点的构造、四通道秩、全部 32 条非零记录和
   两组零重复全部通过。仅允许另行 scratch 全阶/结构化控制器设计；物理控制
   比较仍须新 Gate B 契约和新 evidence round。

比较识别判定为 `ALLOW`，但只对上述窄模型保真结论成立。强限定：两个固定点、
一个拓扑、确定性小信号、全状态离线诊断。禁称控制器有效、动态解耦、分布式
协调、通信价值、MARL、稳定/安全、鲁棒、拓扑泛化、硬件或标题证据。

Kill rule：任何 INVALID、STOP 或 QUALIFY 都关闭本轮；不重试、不改点、幅值、
波形、步长、阈值、输出或模型阶数。ALLOW 也在源模型门停止，不顺带设计或跑
控制器。

## Formal launch contract

- formal_entry: `python scripts/andes_scratch.py scripts/run_r380_vsg_source_model_gate.py execute --expected-seal-sha256 <sha256>`
- rehearsal_command: `python scripts/andes_scratch.py scripts/run_r380_vsg_source_model_gate.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`; source/parent/runtime/case/point/bank/profile/output-absence 全路径；不得创建 formal attempt、seal、模型或轨迹
- rehearsal_checks: `source_hash,parent_hash,installed_package,installed_case,output_absence`
- wsl_python_processes: 1
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R379/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0

36 条乘 125 步共 4500 步，串行一进程；容量只借用 R379 同日当前主机快照和
成功的一进程实测锚，不借用其科学结果。正式结果根固定为
`results/research_loop/r380_vsg_source_model_gate/`，prepare/create-only seal
之前必须不存在。实现完成后实际运行 rehearsal；其输出和对应源码进入 seal。
seal 后、formal attempt 前若失败，本轮只能 aborted，修复须新轮重做。

### Pre-attempt correction log

- 2026-08-12：在任何 R380 ANDES 轨迹、rehearsal、seal 或 formal attempt
  产生前，删除了 `rehearse` 对尚未生成的最终 seal 哈希的循环依赖。rehearsal
  仍走 formal entry 的同一前置校验路径；`prepare` 随后把通过的 rehearsal
  及其源码哈希写入 create-only seal。科学对象、点、输入、验证银行、阈值、
  判定类别和停止条件均未改变。

## 资产保护契约

- 不变：R364--R379 全部计划、封存、结果、feed、claim、阈值和停止结论；
  当前标题、四 VSG 对象、能量端口、可行域映射、外投影恒等、0.2 秒采样、
  legacy M/D 零和无 ESD1 边界。
- R339/R341 仅可复用纯数学模块、差分/约化/采样方法和本计划明确冻结的阈值；
  禁止转移其矩阵、运行点、四负荷基线、降阶候选、轨迹、控制器或 claim。
- 允许新增/修改：R380 round 内文件；纯源桥的三负荷修正及测试；一个 live
  固定状态适配器；一个 R380 runner、一个判定 probe、定向测试；一个 create-only
  R380 result root；收尾所需 feed/claim/verdict/manifest/当前线导航。
- 禁止修改受保护 `andes_vsg_env_v4.py`、`base_env.py`、`train.py` 和
  `paper_grade_axes.py`；禁止覆盖旧文件；禁止训练、控制器合成/执行、增益或
  阶数搜索、随机臂、headroom、MARL 和正式重试。

## Cross-references

- CLM-1000：四 VSG/四 `pref/tm0` 端口与功率到转矩、实现功率结算契约。
- CLM-1005：有限物理端口身份、正负作用和零动作等价。
- CLM-1010：四端口公共/差分作用权与交叉响应存在。
- CLM-1040：当前一阶阻尼族停止；新源模型是不同机制，不是原族调参。
- `tmp/paralleled_vsg_marl/source_model_design_gate_draft.md`：被本计划修正并
  取代的临时草案，不是证据。
