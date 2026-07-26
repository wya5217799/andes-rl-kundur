# 从“复现 + 换算法”到可发表研究：ANDES 多 VSG 智能惯量–阻尼控制项目审计

## Executive verdict

本项目的原始对象不是 “VSD/JD”，准确术语是：

- **VSG**：virtual synchronous generator，虚拟同步发电机；
- **\(H\) / \(M=2H\)**：虚拟惯量或摆动方程惯性系数；
- **\(D\)**：虚拟阻尼或 inertia–droop 论文语境下的 droop/damping
  调节量。

项目的直接来源已经定位为 Yang 等人的论文：
*A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent
Deep Reinforcement Learning for Multiple Paralleled VSGs*，发表于 *IEEE
Transactions on Power Systems*，38(6), 5598–5612, 2023 [1]。原论文在修改版
Kundur 双区系统中布置 4 台储能 VSG，每台由一个 SAC agent 根据本地和两个
邻居的频率信息动态调整 \(\Delta H,\Delta D\)，目标是在总惯量/阻尼尽量不变
时重分配参数并抑制多 VSG 功率/频率振荡。

对用户提出的三个核心问题，结论如下。

1. **平台有这个功能吗？有，但只完成了“固定拓扑研究工作台”，没有完成
   “可验证跨拓扑安全智能控制平台”。** 当前代码能在 ANDES 上运行 4-agent
   VSG 惯量/阻尼控制，支持 SAC/TD3/多种 recurrent 变体、随机负荷扰动、
   通信丢失/延迟、物理频率端点、sealed bank、paired bootstrap、tail/failure
   统计和 residual/gate 组合。缺口是 variable-topology graph policy、真正的
   多系统训练/测试、安全投影/稳定性证书、完整 converter fidelity 和跨仿真器
   或 HIL 验证。
2. **研究问题有必要吗？核心电力问题很有必要；当前“AI 形式”不是必需条件。**
   低惯量系统中的频率支撑、并联 grid-forming converter/VSG 的协调、参数不匹配
   与振荡、通信不确定性和约束安全都是现实问题 [2]–[5]。但固定 Kundur 上每
   0.2 s 用任意神经网络改 \(H,D\) 并不是唯一、也未必是最可信的解；dynamic
   droop、adaptive control、MPC 和解析优化都有强基线 [6]–[8]。
3. **方向有价值吗？有，但论文价值取决于能否从“算法替换”转成“机制 + 安全
   + 泛化”。** 继续比较 SAC/TD3/PPO/LSTM/Transformer 在同一 4-VSG Kundur
   上谁的 reward 高，边际价值已经很低。当前更有竞争力的命题是：一个以 droop
   为物理先验、带有界 residual 与显式安全层、共享图参数的策略，何时以及为何
   能在未见扰动和未见网络拓扑上优于 tuned classical 与 strong learning
   baselines。

一句话判断：**不要放弃 VSG 智能惯量–阻尼方向；要放弃固定拓扑上的
algorithm zoo。**

## 1. Research questions

本报告冻结四个问题。

- **RQ1：** 原论文和当前项目到底控制什么，项目是否仍可称为复现？
- **RQ2：** 当前 ANDES 平台已经能支持哪些实验，哪些论文关键能力仍缺失？
- **RQ3：** 多 VSG 动态惯量–阻尼协调是真问题吗；AI 相对 classical control
  的必要性在哪里？
- **RQ4：** 怎样把现有资产组织成一篇更强的文章，什么结果应触发继续、降档或
  止损？

## 2. Methodology

### 2.1 五个对抗视角

调研没有从“找更强 RL 算法”出发，而从五个互相制衡的视角审计。

1. **source-paper fidelity**：核对 Yang2023 的物理目标、observation、
   action、reward、训练/测试集和扩展实验；
2. **platform capability**：读取当前 active `src/`、tests、evaluation、
   ADR 与最新 round，而不是按旧 README 推断；
3. **classical-control counterfactual**：检查 dynamic droop、adaptive
   VSG、MPC 是否已能解决问题，防止把“可用 AI”偷换成“必须 AI”；
4. **learning/safety frontier**：比较近年 TD3+RTDS、safe RL、multi-VSG
   PPO 和 topology-aware GNN–RL 的贡献门槛 [9]–[12]；
5. **publication/evidence**：按独立 seeds、sealed splits、failure/tail、
   physical metrics、stability 和 high-fidelity validation 审查主张强度
   [13]–[15]。

### 2.2 项目内证据

关键本地材料包括：

- [Yang2023 4-agent 事实库](../paper/kd_4agent_paper_facts.md)；
- [ANDES-only 决策](../adr/0005-andes-only-drop-simulink-1to1.md)；
- [paper-strict / paper-faithful 边界](../adr/0002-paper-strict-vs-paper-faithful.md)；
- [当前 TPWRS programme](../../memory/RESEARCH_PROGRAM.md)；
- [2022–2026 publication landscape](2026-07-24_rl_vsg_publication_landscape.md)；
- [R261 recurrent correctness verdict](../../memory/rounds/R261/verdict.md)；
- [R265 sealed gate verdict](../../memory/rounds/R265/verdict.md)；
- [R266 gate-smoothing mechanism review](2026-07-25_q0029_gate_smoothing_landscape.md)。

### 2.3 证据边界

本报告是平台与研究战略审计，不是新算法实验。它不声称：

- 当前 policy 已经跨拓扑泛化；
- ANDES phasor-domain 结果已经证明 converter switching-level 可部署；
- R201 等 legacy recurrent checkpoint 代表修复 R261 target defect 后的性能；
- alpha slew 或任何新 gate 已经通过新 sealed bank；
- 任何期刊一定接收该工作。

## 3. RQ1：源论文、控制对象与“复现”的准确含义

### 3.1 原论文研究问题

Yang 等人不是简单地“增加系统总惯量”。其目标有两个并列部分 [1]：

1. 根据不同节点在扰动后的动态差异，实时重分配各 VSG 的惯量/阻尼；
2. 让系统总惯量和总阻尼调整尽量接近零，避免所有设备一起增加控制储备。

每个 agent 的 observation 为

\[
o_{i,t}=
(\Delta P_{es,i},\Delta\omega_i,\Delta\dot\omega_i,
\Delta\omega^c_{i,1},\Delta\omega^c_{i,2},
\Delta\dot\omega^c_{i,1},\Delta\dot\omega^c_{i,2}),
\]

即 7 维；action 为连续的

\[
a_{i,t}=(\Delta H_{es,i,t},\Delta D_{es,i,t}).
\]

4 个 agent 各自训练 actor/critic，只交换邻居频率与 RoCoF，不共享网络参数。
主实验包含 100 个随机训练场景和 50 个随机测试场景，另有通信失败、0.2 s
延迟、弱网/规模与 New England 39-bus/fault 扩展。原论文的仿真平台是
MATLAB–Simulink，不是 ANDES。

### 3.2 当前项目是什么层面的复现

当前项目保留了主要概念：

- 修改版 Kundur + 4 个 VSG/agent；
- 7 维 local-plus-neighbour observation；
- 两维惯量/阻尼 action；
- distributed SAC 原始 baseline；
- paper Eq.14–18 reward 与全局 `cum_rf` 的实现；
- 随机扰动、通信失败和延迟入口。

但它不是数值 1:1 复现：

- 原论文使用 MATLAB–Simulink；项目使用 ANDES；
- 原论文未公开足够的 wind/load/solver/inner-loop 参数，无法消除平台差异；
- V4 为保存历史可复现性固定了 `ZERO_G4_INERTIA=True`，并用低惯量
  `GENCLS` 代理风机/VSG 动态；
- V4 的历史 reward、频率基准和 11-axis evaluator 与 paper 存在已记录偏差；
- V5 只成功将 W2 升级为 REGCA1；G4+W2 全替换的配置曾出现 TDS 不收敛；
- active ANDES path 没有完成原论文全部 39-bus/fault 扩展。

因此论文中的准确表述应是：

> “A conceptually paper-anchored reimplementation on an independent
> open-source ANDES phasor-domain platform.”

不应写成：

> “An exact reproduction of Yang et al.”

这不是弱点。跨平台无法数字对齐本身可以成为 transparent reproducibility
背景，但不能作为新控制算法优越性的替代证据。

## 4. RQ2：平台现在有多少功能

### 4.1 已具备的功能

| 层 | 当前能力 | 证据与判断 |
|---|---|---|
| ANDES closed loop | V4/V5 environment；0.2 s control；4 agents 同步给 action | 足以做 electromechanical transient 与 supervisory control feasibility |
| observation/action | local power、frequency、RoCoF、2-neighbour signals；两维 normalized inertia/damping action | 与源论文主结构一致 |
| communications | random dropout、forced link failure、integer-step delay | 足以做初步 cyber-physical robustness |
| disturbances | fixed LS1/LS2 + deterministic random load bank | 已能避免只看两张示意图 |
| algorithms | SAC、SAC-CTDE、TD3、LSTM、QR critic、AFE、warm-\(h_0\)、Transformer、ensemble | baseline 丰富；也证明“继续换算法”空间已被大量探索 |
| composition | droop、static blend、state-dependent residual gate | 已能做 physics-prior/residual mechanism probe |
| physical reporting | physical Hz、worst-bus peak、VSG-mean IAE、dispersion、RoCoF、settling、action L1/TV/saturation | 比原 paper 单一 `cum_rf` 更科学 |
| prospective evaluation | no-anchor bank、SHA-256 sealing、paired bootstrap、failure interval、worst/CVaR | 已具备高质量 confirmatory experiment 骨架 |
| reproducibility | 338 个 pytest cases 可收集；V4 real-ANDES bit-identical regression；claim/round ledger | 工程与审计资产很强 |

ANDES 本身并不是一个弱 simulator。官方能力包括 power flow、DAE time-domain
simulation、full eigenvalue analysis、可再生能源/储能模型和与商业软件的模型
验证 [2]。项目选 ANDES 作为 open-source system-level research backend 是
合理的。

### 4.2 只“部分具备”的功能

| 能力 | 当前状态 | 为什么仍不够 |
|---|---|---|
| paper fidelity | topology/observation/action 大体对齐；plant 与 reward 有偏差 | 只能做 independent reimplementation |
| high-fidelity renewable plant | V5 W2-only REGCA1 可运行 | 4 台受控 VSG 仍不是完整 converter inner-loop/limit/protection model |
| multi-system contract | 代码中留有 `kundur` / `ne39` contract | active `src` ANDES scenario 仍只有 Kundur；不是可训练 variable-size graph suite |
| safety | action clip、empirical failure/guard | box clipping 不等于 small-signal/large-signal stability 或 safe set |
| temporal robustness | recurrent policies、delay buffer | legacy recurrent headline受 R261 target defect 影响，修复后性能未建立 |
| generalisation | random load OOD 和同拓扑 line/plant 扰动 | 这属于 operating-condition robustness，不是 unseen-topology generalisation |

### 4.3 尚未具备的论文关键功能

1. **graph-native variable-size environment/interface**：节点、线路、电气参数和
   communication edges 还没有形成统一 policy input；
2. **multiple training graphs + entirely held-out graphs**：同一 Kundur 上换
   load bus 或断一条线不能支持 topology-general claim；
3. **shared graph policy**：当前每 agent 独立 actor，不能自然适配 VSG 数变化；
4. **explicit feasible region / safety filter**：没有从 eigenvalue、Lyapunov、
   ISS、CBF 或 invariant set 导出的 \(H,D,\dot H,\dot D\) 可行域；
5. **training/deployment consistency**：post-hoc gate/filter state 还未作为
   policy state 和训练 dynamics 的一部分；
6. **credible converter validation**：没有 PSCAD/EMT、RTDS、CHIL/PHIL 或
   至少另一独立 simulator 的 headline replication；
7. **energy/headroom/SOC contract**：action 变化目前主要受 normalized box
   限制，没有完整储能能量、current limit 和 thermal constraint。

因此平台成熟度可以概括为：

> **优秀的 fixed-topology algorithm/evaluation workbench；尚未成为
> topology-general, safety-certifiable VSG control testbed。**

## 5. RQ3：问题是否有必要，AI 是否有必要

### 5.1 核心物理问题是真问题

在高比例 inverter-based resource 系统中，传统同步机旋转惯量下降，frequency
nadir、RoCoF、振荡阻尼和不同 grid-forming devices 的交互变得重要。NREL 的
grid-forming roadmap 将 frequency control、protection、fault ride-through
和 modeling/validation 都列为规模化部署前必须解决的研究问题 [3]。并联 VSG
参数与网络/运行点不匹配时出现振荡，也正是 Yang2023 的解析与控制出发点 [1]。

动态 \(H,D\) 有实际吸引力：

- 扰动初期可能需要更强 inertia/RoCoF support；
- 随后需要足够 damping 且避免过慢恢复；
- 不同位置的 VSG 对 inter-area/differential mode 的参与度不同；
- 固定参数很难同时兼顾 noise、nadir、settling、control effort 和多个 operating
points [6]–[8]。

同时，\(H,D\) 的可调范围并不是任意 box：VSG parameter-constraint 工作已经
表明稳定性会限制参数组合 [4]。这使“先从物理分析得到 safe set，再让 learning
在其中优化”比“让 policy 自己从 reward 学会不失稳”更可信。

所以“怎样协调多个 VSG 的动态惯量/阻尼”是有意义的问题。

### 5.2 但“AI 必须在线改 H/D”不是已经成立的事实

三类反证必须正面处理。

**第一，classical dynamic controllers 已能表达很多 trade-off。** Dynamic
droop 可以在 noise rejection、synchronisation speed、nadir 与 steady-state
effort 之间调节 [6]；decentralized explicit MPC 可以直接约束 frequency nadir
与 RoCoF [7]；adaptive VSG/small-signal 方法可以按 operating mode 选参数 [8]。

**第二，RL 的优势场景必须被命名。** 只有在以下至少一项成立时，learning 才
有强理由：

- 精确模型不足，但可获得大量安全的离线/仿真交互；
- observation 是局部、延迟或缺失的，需要从历史推断 hidden state；
- topology、VSG 数、disturbance location 和 operating point 大幅变化；
- classical optimisation 在线求解过慢，而 learned policy 能近似映射；
- residual policy 只补偿 model mismatch，classical prior 保留基本稳定行为。

固定 4-node ring、两个 load step、已知 DAE、无约束证书的场景并不能自动满足
这些条件。

**第三，AI 会引入新的控制风险。**

- neural action 可能饱和、抖动或利用 reward 缺口；
- recurrent training/evaluation 容易出现 hidden-state 和 Bellman-target 错位；
- post-hoc filter 改变闭环 dynamics；
- average reward 会掩盖少量失稳；
- 无法解释的 policy 在 topology shift 和 protection event 下可能外推失败。

因此正确研究问题不是：

> “哪种 AI 算法控制 VSG 最好？”

而是：

> “在 tuned classical controller 已知且安全边界明确时，bounded learned
> residual 在哪些 differential-mode、uncertainty 和 topology regimes 中提供
> 可重复的附加价值，并在什么时候自动退回 classical prior？”

### 5.3 当前项目已经得到的最重要科学信号

| 项目证据 | 科学含义 |
|---|---|
| 多轮 SAC/TD3/LSTM/critic 变化没有稳定突破，critic 沿 action 轴趋向边界 | 瓶颈更像 objective/mechanism，而不是缺一个流行算法 |
| R201 与 tuned droop 在 `geo` / `cum_rf` 上处于 Pareto 两端 | learned 与 classical 捕获了不同 mode/metric，不存在单一“赢家” |
| paper `cum_rf` 只惩罚节点间频率差，不惩罚全体一起偏离 nominal | 必须分开 common-mode restoration 与 differential-mode synchronisation |
| R261 发现 recurrent target defect | legacy checkpoint 只能用于机制探索，不能证明 corrected algorithm |
| R265 gate 改善 physical mean，却使 action-TV CVaR90 大幅恶化 | 平均频率改善不等于可部署控制 |
| R266 将 gate TV 定位到 `delta alpha × controller disagreement` | 支持最小动态 rate-bound probe，也说明 post-hoc selector 是一个新控制器 |

这些结果看似“没有不断刷新 SOTA”，实际上比继续换算法更接近可发表的问题：
**为什么 learning 与 droop 各自在哪种 frequency mode 上有效，以及怎样在安全
边界内组合。**

## 6. 研究缺口与主论文命题

### 6.1 不再成立的弱缺口

以下单独拿出来都不足以成为强论文贡献：

- 第一次用 SAC/TD3/PPO 调 VSG \(H,D\)；
- 给 VSG controller 加 LSTM/Transformer；
- 在 Kundur 两个 load steps 上 reward 更高；
- 把 GNN 接到 observation 上；
- 只用 action clipping 就称为 safe RL；
- 同一网络断线后仍工作就称为 topology generalisation。

截至 2024–2026，已有 TD3+RTDS VSG 调参 [9]、small-signal-informed RL
[10]、带 Lyapunov/region-of-attraction 的 safe RL [11]、PSCAD 多 VSG PPO
[12] 以及 physics/spectral-sensitivity-informed GNN–RL [16]。新工作必须
超过“换 architecture”的门槛。

### 6.2 仍然有价值的窄缺口

本项目最可辩护的 gap 是：

> 在多 VSG 网络中，构造一个把 common-frequency restoration 与
> differential synchronisation 显式分解的 distributed controller；以 tuned
> droop 为物理先验，只学习有界 residual 和 state-dependent participation；
> 将 topology、电气/通信边与 temporal partial observability 纳入共享策略；
> 对 \(H,D\)、变化率、能量和稳定域施加显式约束；并在完全未见的网络、
> VSG 数和扰动组合上用 sealed statistics 证明何时有效、何时退回基线。

这个 gap 的关键不是 “GNN + RL”，而是四个可检验连接：

1. **mode ↔ objective**：common 与 differential mode 各有物理端点；
2. **physics prior ↔ residual**：RL 只修正 droop 无法覆盖的部分；
3. **topology ↔ shared policy**：同一组参数处理不同图和 VSG 数；
4. **safety set ↔ executed action**：训练和部署都经过同一个有状态 safety layer。

### 6.3 建议冻结的主假设

> **H\***：相对 tuned droop、pure RL、fixed blend 和 size-matched non-graph
> residual，一个 physics- and safety-constrained graph residual policy 能在
> entirely unseen network topology、VSG count、disturbance location 和
> communication graph 上，同时降低 common-mode physical frequency error
> 与 differential synchronisation loss，并保持 failure、tail risk、
> \(H,D\) range/rate、energy/headroom 和 settling guards。

这个假设是可证伪的：任一 co-primary 或 safety guard 失败都不允许宣布成功。

## 7. RQ4：怎样做成更好的文章

### 7.1 四阶段论文路线

| 阶段 | 要回答的唯一问题 | 必须产出 | Kill / pivot |
|---|---|---|---|
| P0 correctness | evaluator、frequency basis、recurrent target 和 sealed protocol 是否可信 | corrected baselines、physical endpoints、multi-seed uncertainty | corrected RL 若不优于 tuned droop，停止宣称算法 SOTA |
| P1 residual mechanism | bounded residual 是否在可解释 mode 上提供增益 | pure RL/droop/fixed blend/residual/gate ablation；mechanism telemetry | 连续两次 well-powered negative，关闭该 gate/residual family |
| P2 topology generalisation | graph sharing 是否在 entire unseen graphs 上优于 matched MLP | multi-graph training、held-out graphs/VSG counts、zero-/few-shot results | 只在同一 Kundur outage 有效，不得称 topology general |
| P3–P4 safety/fidelity | 增益能否在约束、故障和更高 fidelity 下保留 | safe set/stability result、EMT/PSCAD/RTDS/HIL 或第二 simulator | 无安全或高 fidelity，只能降到 simulation-method paper |

Q-0029 的 alpha-slew 工作只属于 P0/P1 之间的机制清理。它可以决定
hand-designed gate 是否值得保留，但不应成为最终论文 headline。

### 7.2 推荐 controller architecture

\[
u_t =
\Pi_{\mathcal U_{\mathrm{safe}}(x_t,G)}
\left[
u_{\mathrm{droop}}(x_t)
+ g_\theta(x_{0:t},G)\odot \Delta u_\theta(x_{0:t},G)
\right].
\]

其中：

- \(u_{\mathrm{droop}}\)：按每个系统公平调参的 stabilising prior；
- \(\Delta u_\theta\)：有界 residual，只控制 \(\Delta H,\Delta D\)；
- \(g_\theta\)：mode-aware participation/gate，common mode 接近零时应退回 prior；
- graph encoder：节点含 local dynamic/state/headroom，edge 含 electrical 与
  communication 信息，参数跨 agent/graph 共享；
- temporal encoder：仅在 delay/partial observability ablation 证明有用时保留；
- \(\Pi_{\mathcal U_{\mathrm{safe}}}\)：同时限制 value、rate、energy/current
  和 stability-relevant region；其 state 必须进入 training dynamics。

Residual learning 本身不是新概念 [17]，predictive safety filtering 也已有
成熟框架 [18]。论文贡献必须来自它们与 multi-VSG mode/topology/stability
结构的具体结合和新证据。

### 7.3 最小可信实验矩阵

**Systems**

- anchor：modified Kundur 4-VSG；
- development systems：至少两个不同 topology/size 的 network；
- sealed topology test：至少一个训练从未出现的完整系统和未见 VSG count；
- high-fidelity subset：PSCAD/EMT、RTDS 或独立 simulator 上复现一个
  headline mechanism。

**Disturbances**

- load size/sign/bus/onset time；
- renewable penetration、base inertia/damping、headroom；
- communication delay/dropout/graph change；
- line/generator outage、fault 和 clearing time；
- measurement noise/bias、parameter error；
- compound/multi-event cases。

**Baselines**

- no extra control / fixed VSG；
- tuned droop；
- adaptive inertia/damping 与 dynamic droop；
- PI/MPC 或另一个强 model-based controller；
- Yang2023 SAC/DDIC；
- corrected MLP SAC/TD3/PPO；
- size-matched non-graph residual；
- full graph residual + safety method。

所有方法使用同一 observation/action information budget 和 matched tuning
budget；不能拿精调 proposed method 对默认 baseline。

**Ablations**

- MLP vs GNN；
- memoryless vs temporal；
- pure RL vs residual；
- residual without/with gate；
- safety projection off/on；
- electrical edges vs communication edges；
- common/differential objective components；
- training with vs without filter/safety state。

**Statistics**

- headline controller 至少 10 个独立 training seeds（预算不足时 5 个只能算
  exploratory）；
- 每个 policy 在同一个大规模 paired held-out scenario bank；
- median、IQM、95% interval、probability of improvement、performance
  profile、failure interval、worst/CVaR；
- checkpoint selection 和 primary operating point 在打开 sealed test 前冻结
  [13]–[15]。其中 IQM、performance profile 与 stratified interval 的采用直接
  对应 Agarwal 等人的 few-run RL 统计建议 [14]。

### 7.4 论文端点

不要把 `geo` 或 reward 当 primary outcome。推荐：

- **co-primary common mode**：physical VSG-mean/COI IAE、peak、settling；
- **co-primary differential mode**：normalized synchronisation loss、
  dispersion ISE、inter-area mode damping；
- **safety guards**：failure/incomplete TDS、worst-bus peak、RoCoF、constraint
  violations、protection threshold；
- **actuation guards**：action L1/energy、TV、max slew、saturation、SOC/headroom；
- **tail**：worst-case、CVaR90/95 和 conditional failure severity；
- **generalisation**：seen vs unseen graph effect、zero-/few-shot transfer gap。

`cum_rf` 可保留为 source-paper-comparable differential metric；11-axis `geo`
可保留为 historical/paper-alignment dashboard，但二者都不应承担 overall
control quality。

### 7.5 三档可发表结果

| 实际结果 | 合理叙事 | 现实投稿层级 |
|---|---|---|
| corrected multi-seed + sealed disturbance，只在 Kundur 有效 | 严谨 single-system adaptive/residual control | EPSR、IET GTD、IEEE Access 等更现实 |
| multiple systems + unseen topology + mechanism ablation + explicit constraints | topology-generalising physics-informed control | IJEPES、SEGAN、JMPCE 等有竞争力 |
| 上述全部 + stability/safety result + cross-simulator/HIL/RTDS + lasting system insight | 系统级动态与安全贡献 | 可认真尝试 TPWRS |

期刊名只表示 evidence band，不是接收预测。TPWRS headline 必须是 power-system
insight，例如：

> “Learning is beneficial only in differential-mode regimes with sufficient
> controller disagreement; a bounded graph residual improves these regimes
> while a certified gate recovers droop behaviour elsewhere.”

“Graph-TD3 的 score 更高”不够。

### 7.6 可用的论文题目

1. *Physics- and Safety-Constrained Graph Residual Control for
   Topology-Generalizing Dynamic Inertia–Damping Coordination of Multiple VSGs*
2. *When Does Learning Improve Droop? Mode-Aware Residual Control of Multiple
   VSGs Under Unseen Network Topologies*
3. *From Synchronisation Reward to Physical Frequency Safety: A Reproducible
   Multi-System Benchmark for Learning-Based VSG Coordination*

第 1 个适合主方法论文；第 2 个最强调机制；第 3 个只在方法最终失败、但
benchmark/negative evidence 足够系统时作为 pivot。

## 8. 90-day decision sequence

这不是按日历承诺，而是按依赖关系排序。

1. **先关闭 P0。** 完成 Q-0029 的 single-rate prospective test 或按 kill
   rule 关闭 hand-designed gate；修复后重训至少 TD3-LSTM 与 memoryless
   TD3/SAC，禁止继续引用 legacy recurrent 作为算法证据。
2. **冻结 paper endpoint protocol。** common/differential co-primary、
   safety/actuation guards、seeds、bootstrap/CVaR 与 checkpoint selection
   一次性写入 preregistration。
3. **建立 classical floor。** tuned droop、dynamic droop/adaptive
   inertia-damping 与一个 MPC/PI baseline 必须公平调参。
4. **做最小 residual test。** 先在 Kundur 检验 bounded residual 是否有
   mechanism gain；若没有，GNN 不会凭空创造价值。
5. **再构建 graph interface。** 将 electrical graph、communication graph、
   node capacity/headroom 与 action semantics 标准化；至少三个 train/dev
   graphs，一个 entirely held-out graph。
6. **安全层同步进入训练。** 从 small-signal/eigenvalue 或 robust
   invariance 得到初始 feasible set；value/rate/energy 约束全部可 telemetry。
7. **最后买 publication tier。** 先做 cross-topology；只有其通过才投入
   PSCAD/RTDS/HIL 或第二 simulator。

## 9. Stop conditions

项目应继续，但必须有明确止损。

- corrected multi-seed RL 在 physical endpoints 上不优于 tuned classical：
  停止 “better RL algorithm” 主张，转 negative/reproducibility 或 benchmark；
- residual 在两次 well-powered prospective tests 中都不能同时改善
  common/differential outcomes：
  关闭 residual mechanism，不加更多 gate；
- GNN 只在训练图或同图 outage 有效：
  删除 topology-general claim，降为 robust fixed-topology method；
- safety layer 只能减少平均 violation，不能给 hard/empirical tail guarantee：
  不使用 “safe”；
- high-fidelity model 显示 phasor-domain gain 消失：
  把 ANDES 结果定位为 screening，不做 deployment claim；
- 效果只存在于 `geo` 或 post-hoc 选出的 metric：
  判 negative。

## 10. Self-adversarial audit

### 10.1 最强反对意见

1. **“既然 classical control 已经成熟，为什么需要 RL？”**  
   本报告同意这个质疑。未来实验必须让 tuned dynamic droop/MPC 成为真正
   baseline，并把 RL 的优势限定为 model mismatch、partial observability、
   fast approximation 或 topology transfer。

2. **“ANDES 不是 EMT，VSG 实现太简化。”**  
   正确。ANDES 适合 system-level electromechanical screening、large-network
   DAE 和 eigenanalysis [2]，不够验证 inner-loop switching/current limiting。
   主论文必须至少 cross-simulator；否则只做 supervisory phasor-domain claim。

3. **“GNN 也可能只是 architecture decoration。”**  
   正确。必须以 entirely unseen graphs 和 size-matched MLP ablation 证明；
   只在固定 topology 提分就删除 GNN headline。

4. **“项目已经跑了太多轮，容易 researcher overfitting。”**  
   正确。历史 LS1/LS2 和 R265 都只能是 development evidence；新的核心结论
   必须使用预先 materialize/hash 的 bank 与未见 topology。

5. **“当前最好结果含 legacy bug，研究基础不可靠。”**  
   正确。R261 之后的 corrected retraining 是 prerequisite，不是可选优化。

### 10.2 未解决前提

- \(\Delta H,\Delta D\) 的实际执行速度、储能 current/headroom 与热约束尚未
  从设备模型导出；
- graph split 怎样避免同构/参数泄漏尚未定义；
- small-signal safe set 怎样扩展到 large disturbance 尚未确定；
- 训练多个 ANDES systems 的计算预算与 simulator parallelism 尚未评估；
- 通信 graph 与 electrical graph 应该双图还是合并图，需要 matched ablation；
- source paper 的部分 Simulink 参数不可恢复，不能成为严格 numerical target。

## 11. Conclusion

**RQ1：项目是什么？** 它是对 Yang2023 “4 台并联 VSG、distributed SAC 动态
调 \(H,D\)”思想的 ANDES 独立重实现，不是 Simulink 数值复刻。

**RQ2：平台有功能吗？** 有。固定 Kundur 上的 multi-agent training/evaluation、
communications、physical endpoints、sealed statistics 和可复现审计已经很强；
但 graph multi-system、explicit safety、converter fidelity 与 cross-simulator
验证尚缺。

**RQ3：问题有必要吗？** 多 VSG 协调、低惯量频率支撑和参数失配振荡是重要
问题；“AI 必须在线调 \(H,D\)”不是前提，而应由 tuned classical baselines、
OOD topology 和 safety evidence 共同检验。

**RQ4：怎样发更好的文章？** 停止 algorithm-only sweep，先修 correctness，
再做 droop-prior bounded residual；只有 residual mechanism 在 physical
co-primary 上成立后，才加 shared graph policy、显式 safe set 和跨 simulator
验证。真正有 TPWRS 潜力的贡献是**何时、为何、在什么安全边界内 learning 能
跨拓扑改善 multi-VSG dynamics**，不是某个 neural architecture 的分数。

## References

[1] Qiufan Yang, Linfang Yan, Xia Chen, et al., “A Distributed Dynamic
Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning
for Multiple Paralleled VSGs,” *IEEE Transactions on Power Systems*, 38(6),
5598–5612, 2023.

[2] Hantao Cui, Fangxing Li, Kevin Tomsovic, “Hybrid Symbolic-Numeric Framework
for Power System Modeling and Analysis,” *IEEE Transactions on Power Systems*,
36(2), 1373–1384, 2021.

[3] Yashen Lin, Joseph Eto, Brian Johnson, et al., *Research Roadmap on
Grid-Forming Inverters*, NREL/TP-5D00-73476, 2020.

[4] Junru Chen, Terence O’Donnell, “Parameter Constraints for Virtual
Synchronous Generator Considering Stability,” *IEEE Transactions on Power
Systems*, 34(3), 2479–2481, 2019.

[5] Uros Markovic, Zhongda Chu, Petros Aristidou, et al., “LQR-Based Adaptive
Virtual Synchronous Machine for Power Systems With High Inverter Penetration,”
*IEEE Transactions on Sustainable Energy*, 10(3), 1501–1512, 2019.

[6] Yan Jiang, Richard Pates, Enrique Mallada, “Dynamic Droop Control in
Low-Inertia Power Systems,” *IEEE Transactions on Automatic Control*, 66(8),
3518–3533, 2021.

[7] Ognjen Stanojev, Uros Markovic, Petros Aristidou, et al., “MPC-Based Fast
Frequency Control of Voltage Source Converters in Low-Inertia Power Systems,”
*IEEE Transactions on Power Systems*, 37(4), 3209–3220, 2022.

[8] Saber D’Arco, Jon Are Suul, Olav B. Fosso, “A Virtual Synchronous Machine
Implementation for Distributed Control of Power Converters in SmartGrids,”
*Electric Power Systems Research*, 122, 180–197, 2015.

[9] Oroghene Oboreh-Snapps, Buxin She, Shah Fahad, et al., “Virtual Synchronous
Generator Control Using Twin Delayed Deep Deterministic Policy Gradient
Method,” *IEEE Transactions on Energy Conversion*, 39(1), 214–228, 2024.

[10] Oumayma Benhmidouch, Nabil Moufid, Ali Ait-Omar, et al., “A Novel
Reinforcement Learning Policy Optimization Based Adaptive VSG Control
Technique for Improved Frequency Stabilization in AC Microgrids,” *Electric
Power Systems Research*, 230, 110269, 2024.

[11] Hang Shuai, Buxin She, Jinning Wang, Fangxing Li, “Safe Reinforcement
Learning for Grid-forming Inverter Based Frequency Regulation with Stability
Guarantee,” *Journal of Modern Power Systems and Clean Energy*, 13(1), 79–86,
2025.

[12] Seokjun Kang, Yoongun Jung, Deokki You, Gilsoo Jang, “Enhancing Frequency
Stability with Decentralized Adaptive Control Using Multi-Agent Deep
Reinforcement Learning of Multi-VSGs,” *International Journal of Electrical
Power & Energy Systems*, 172, 111374, 2025.

[13] Peter Henderson, Riashat Islam, Philip Bachman, et al., “Deep Reinforcement
Learning That Matters,” *Proceedings of the AAAI Conference on Artificial
Intelligence*, 32(1), 2018.

[14] Rishabh Agarwal, Max Schwarzer, Pablo Samuel Castro, et al., “Deep
Reinforcement Learning at the Edge of the Statistical Precipice,” *Advances in
Neural Information Processing Systems*, 34, 29304–29320, 2021.

[15] Andrew Patterson, Samuel Neumann, Martha White, et al., “Empirical Design
in Reinforcement Learning,” *Journal of Machine Learning Research*, 25(318),
1–63, 2024.

[16] Sefa Eshun, Makan Fatemi, Salar Fattahi, “Spectral Sensitivity and Physics
Informed GNN-RL for Real Time Power Grid Stability,” *Sustainable Energy,
Grids and Networks*, 46, 102168, 2026.

[17] Tobias Johannink, Shikhar Bahl, Ashvin Nair, et al., “Residual
Reinforcement Learning for Robot Control,” *Proceedings of the IEEE
International Conference on Robotics and Automation*, 6023–6029, 2019.

[18] Kim Peter Wabersich, Melanie N. Zeilinger, “A Predictive Safety Filter for
Learning-Based Control of Constrained Nonlinear Dynamical Systems,”
*Automatica*, 129, 109597, 2021.
