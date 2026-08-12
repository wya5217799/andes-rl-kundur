# Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning：从“算法叠加”到可证伪的物理解耦

## Abstract

并联虚拟同步发电机（Virtual Synchronous Generator, VSG）的“解耦”并不是单一问题：线路复阻抗会使有功与无功通道相互影响，馈线不匹配会造成稳态功率分配误差，虚拟惯量与下垂参数不匹配会激发机间功率振荡，而二次控制又必须在频率/电压恢复与比例分配之间协调。已有确定性方法分别通过复阻抗感知下垂、虚拟阻抗、前馈解耦、分布式平均、互阻尼和扩散控制处理这些问题；与此同时，深度强化学习（Deep Reinforcement Learning, DRL）和多智能体强化学习（Multi-Agent Reinforcement Learning, MARL）已被用于 VSG 参数自适应、并联 VSG 惯量—下垂协调以及并联逆变器功率分配。因此，简单地把 MARL 加到并联 VSG 上已不足以构成清晰的新问题。本文基于截至 2026 年 8 月 12 日的独立外部检索，将相关证据组织为“物理通道解耦—机间动态协调—分层分布式恢复—安全与泛化”四个互斥但相连的分支。综合证据表明：MARL 的合理位置不是替代内环或掩盖可解析耦合，而是在具有稳定性与约束保证的确定性基线上学习有界协调残差；其增量价值必须通过同权限强基线、未见拓扑、通信故障和实时/硬件实验来证伪。本文最后给出一套可执行的研究架构、评价指标、消融矩阵和停止门。

## 1. Introduction

并联逆变器的功率耦合首先是一个网络与控制共同决定的物理问题。复线路阻抗会破坏朴素的 \(P\!-\!f\) 与 \(Q\!-\!V\) 解耦假设，VSG 功率环的带宽和参数又会改变有功—无功闭环耦合，而并联 VSG 的虚拟定子、惯量、阻尼及下垂参数不一致会进一步造成暂态分配偏差和功率振荡 [1]–[3]。因此，“输出功率跟踪得更好”不自动等于“实现了解耦”。

学习控制与这一问题的交叉已经形成直接先例。Yang 等把多台并联 VSG 的惯量—下垂参数协调表述为 Markov game，并用基于 Soft Actor-Critic 的分布式 MARL 动态抑制功率振荡 [4]；Kang 等又以集中训练、分散执行方式自适应多 VSG 参数 [5]；Oboreh-Snapps 等则用 DRL 同时约束并联逆变器的输出电压与无功分配误差 [6]。三者所解决的对象分别更接近动态参数协调、频率稳定和稳态无功分配，不能被笼统归为同一种“解耦”。

本文不预设 MARL 优于确定性控制，而是回答三个研究问题：

- **RQ1：** 并联 VSG 文献中的“decoupling”具体对应哪些可分辨的物理耦合，现有确定性方法分别消除了什么、留下了什么？
- **RQ2：** DRL/MARL 在并联 VSG 协调中已经提供了哪些直接证据；相对于分布式、自适应和模型化控制，它的不可替代增量是什么？
- **RQ3：** 什么样的架构、基线、OOD 测试、安全门和硬件证据，才足以支持“decoupling-oriented MARL coordination”的科学主张？

本文的核心判断不是“MARL 无效”，而是：**现有证据只支持 MARL 作为有条件的自适应协调器；尚不足以支持其天然具有物理解耦、跨拓扑泛化或闭环安全性。最可辨识的研究路线，是让解析控制承担可证明的稳定与基本解耦，让 MARL 只使用剩余且有界的控制权限，并用独立物理指标检验其增量。**

## 2. Methodology

检索于 2026 年 8 月 12 日完成，且不使用任何本地仓库、项目文档、既有实验或内部结论。检索源包括 IEEE Xplore、Elsevier/ScienceDirect、IET/Wiley、Springer、MDPI、期刊与会议官方页面、作者机构知识库、OSTI/NREL、Crossref、OpenAlex、DOAJ、arXiv 和公开论文全文。检索时间跨度为 2000–2026 年：早期工作用于建立并联逆变器的物理与分布式控制基线，2020 年后的工作用于覆盖 VSG 学习控制、安全 RL、拓扑表征和实时验证。

检索分为四个彼此独立的视角：

1. **主流物理控制：** parallel inverter/VSG × complex impedance、power coupling、circulating current、power sharing、virtual impedance、decoupling；
2. **直接学习证据：** VSG/grid-forming inverter × DRL/MARL × inertia、damping、droop、frequency、reactive sharing；
3. **分布式协调：** microgrid × distributed secondary、consensus、DAPI、diffusion、communication delay/failure；
4. **批判性邻域：** safe RL、stability guarantee、topology generalisation、OOD、HIL/PHIL、MARL evaluation protocol。

每个视角均执行宽检索、术语窄化和引用链回溯。纳入标准是：题名、作者、年份和 venue 可独立核验；正文使用的技术结论能从摘要或可访问全文得到支持；研究对象与四个分支之一具有直接关系。只有元数据而无足够技术内容的论文，只用于题名级或验证层级判断。最终语料包含 38 项核心文献。检索未发现同时满足“并联 VSG、物理解耦、MARL、正式稳定性证书、未见拓扑 OOD、PHIL/物理多逆变器验证”六项条件的工作；这表示本次语料中的空白，不构成对全球文献绝对不存在的证明。

不同证据类型的可信范围如下。

| 证据类型 | 能支持的结论 | 不能单独支持的结论 |
|---|---|---|
| 解析模型与稳定性证明 | 指定模型、工作点和假设下的解耦/稳定条件 | 含饱和、限流、开关与保护的完整装置安全 |
| 离线时域仿真 | 给定模型和扰动集内的可行性与相对性能 | 未见工况、跨拓扑或 sim-to-real 泛化 |
| 实时数字仿真 / CHIL | 实时计算可行性、控制器时序和接口行为 | 功率级非理想性与真实能量/电流压力 |
| PHIL / 多逆变器实验 | 指定硬件、缩放和接口条件下的物理可实施性 | 其他额定值、拓扑和保护配置下的普遍有效性 |
| 多随机种子与预注册 OOD 评估 | 统计稳健性和分布外增量 | 未测试失效模式下的安全保证 |

## 3. Taxonomy：四种不能混写的“解耦”

本文以耦合的来源与评价对象为轴，而不是按算法名称分类。

| 分支 | 耦合来源 | 典型控制量 | 必须直接测量的结果 | 常见误判 |
|---|---|---|---|---|
| A. 功率通道耦合 | 线路 \(R/X\)、电压幅值、功角、功率环动态 | 虚拟阻抗、坐标变换、前馈补偿 | 交叉通道增益、\(P\) 激励引起的 \(Q\) 能量及反向量 | 只看各自 tracking error |
| B. 并机分配与环流 | 馈线/额定值不匹配、输出阻抗差异 | droop、虚拟电抗/电感、母线估计 | 比例分配误差、环流、电压降、谐波分配 | 把分配精度称为动态解耦 |
| C. 机间动态协调 | 惯量、阻尼、下垂和内环带宽不匹配 | 自适应惯量、互阻尼、扩散、MARL 参数协调 | 模态阻尼、振荡能量、频率一致性、暂态分配 | 只报告频率 nadir |
| D. 分层恢复与约束协调 | primary 偏差、多目标冲突、通信限制 | distributed secondary、DAPI、MPC、MARL residual | 频率/电压恢复、功率分配、通信与控制代价、约束违例 | 把 secondary restoration 当作 primary decoupling |

四个分支并非彼此独立的装置模块，而是互相施加边界。例如，增大虚拟阻抗可能改善分配，却带来更大电压降；增大虚拟惯量可能改善 RoCoF，却延长收敛或激发机间振荡；二次电压恢复可能破坏 primary 层的无功分配。因此，研究设计必须先固定“要消除的耦合”，再允许 MARL 优化剩余目标。

## 4. 物理功率解耦：阻抗、工作点与结构性权衡

### 4.1 复阻抗使朴素 \(P/Q\) 分工失效

Yao 等表明，复杂线路阻抗会使传统 droop 难以实现有效功率分配，并以复虚拟阻抗同时处理 \(P/Q\) 耦合和基波/谐波环流 [1]；Tuladhar 等更早通过实验说明线路阻抗不平衡和逆变器参数变化会直接破坏并联运行 [7]。与二者相比，Zhong 的 robust droop 进一步指出，常规准确比例分配依赖相同 per-unit impedance 与相同电压设定值，而放宽这些条件会暴露电压降与分配精度之间的权衡 [8]。这三项证据共同说明：耦合首先由网络与工作点决定，不能仅靠控制器标签判断。

对 VSG 而言，Wu 等给出功率环小信号模型、主动/无功环解耦条件和参数设计步骤，并以 10-kVA 原型验证 [2]；Li 等通过阻抗角坐标变换和改进 excitation control 处理 VSG 功率解耦 [9]；Wang 等则用 virtual complex impedance 匹配等效线路阻抗并按容量分配负载 [10]。三种路线分别依赖小信号带宽条件、变换/控制结构和在线等效阻抗塑形，适用条件不同，因此不能用一个平均 tracking 指标替代条件化比较。

### 4.2 虚拟阻抗既是解耦手段，也是新的约束来源

He 与 Li 通过小信号模型讨论 virtual impedance 在稳定、暂态和潮流性能之间的可选范围 [11]，而 He 等把基波与选定谐波的等效阻抗分别整形，以改善无功与谐波功率分配 [12]。Mahmood 等用稀疏通信调谐 adaptive virtual impedance；给定工作点调谐完成后，通信中断仍可保持准确分配，但负载在断讯后变化会降低精度 [13]。这些结果共同反对“把虚拟阻抗增大即可鲁棒解耦”的简单命题。

Rasool 等的 virtual parallel inductor 同时瞄准无功分配误差与电压控制精度，并给出 eigenvalue 分析和硬件实验 [14]；与固定/自适应串联虚拟阻抗 [11]–[13] 相比，它改变的是等效阻抗实现方式，而不是取消电压—分配—稳定性的多目标权衡。因此，MARL 若调节虚拟阻抗，至少必须同时报告母线电压偏差、控制 effort、峰值电流与稳定裕度，不能只报告 sharing error。

## 5. 并联 VSG 的动态协调：确定性方法已经很强

并联 VSG 的动态问题不等同于静态 \(P/Q\) 耦合。Shi 等推导惯量匹配关系并用自适应策略处理并联过程中的振荡与比例分配 [15]；Fu 等根据本地频率与邻居平均频率的相对运动自适应调整惯量，给出 Lyapunov 证明，并以四 VSG OPAL-RT HIL 验证 [16]；同一研究线的 decentralized mutual damping 又通过机间频率差构造互阻尼 [17]。与纯 tracking 控制相比，这些方法直接作用于机间模态和能量交换，因而是 MARL 参数协调的强基线。

功率通道与动态模态也可以通过解析结构共同处理。Li 等在 magnitude-phase motion equation 框架下分析低惯量 RoCoF/frequency nadir 与弱阻尼振荡之间的关系，并用 reactive-power feedforward 改善 VSG 鲁棒性 [18]；Liu 等则以 virtual stator reactance 改善 basic VSG 的有功振荡、错误暂态分配和无功 sharing error [3]。前者强调单机/并网功率—电压耦合，后者直接处理并联 VSG，因此拟议方法不能只超过 conventional VSG，而必须与至少一种增强 VSG 和一种机间阻尼方法同权限比较。

分布式协调也不是 MARL 独有。Simpson-Porco 等的 distributed averaging controller 用最近邻通信恢复频率/电压并保持功率分配，提供 voltage stability analysis、通信故障与 plug-and-play 实验 [19]；Shafiee 等的 distributed secondary control 研究通信时延和丢包，并避免单一中央控制器失效 [20]；最新的 diffusion 路线同时结合互阻尼、adaptive virtual impedance 和平均电压恢复，直接针对并联 VSG 的振荡与分配 [21]。三者分别提供成熟实验基线、分布式容错基线和近期多 VSG 强基线。

**比较结论：确定性方法的优势不是“永远最优”，而是其物理作用、假设、稳定对象和失效模式较清楚。MARL 必须在这些结构仍然有效时证明额外收益，而不能只挑 basic droop/PI 作为弱对手。**

| 确定性路线 | 直接解决的问题 | 证据优势 | 对 MARL 的最低比较要求 |
|---|---|---|---|
| complex-impedance-aware droop / decoupling | \(P/Q\) 交叉作用、环流 | 模型 + 仿真/实验 [1], [2], [9] | 相同阻抗不确定性与控制带宽 |
| enhanced/adaptive virtual impedance | 分配误差、阻抗失配 | 小信号/特征根 + 实验 [11]–[14] | 同时报告电压降、电流和稳定裕度 |
| enhanced VSG / feedforward | 暂态分配、功率—电压响应 | 状态空间/解析 + 实验 [3], [18] | 同 sensing 与 actuator authority |
| adaptive inertia / mutual damping | 机间振荡、频率一致性 | Lyapunov + HIL [16], [17] | 同通信图和扰动集 |
| DAPI / distributed secondary / diffusion | 恢复、分配、容错 | 稳定分析、实验、通信故障 [19]–[21] | 同通信预算、时延和丢包 |

## 6. DRL/MARL 证据：直接先例存在，但问题仍然碎片化

### 6.1 单 VSG 参数自适应不等于多设备协调

Li 等将 virtual inertia 与 damping 设为 DRL 动作，以频率、有功和 RoCoF 构造观测与 reward [22]；Oboreh-Snapps 等用 TD3 加入 settling time，并给出 MATLAB/Simulink 与 RTDS 验证 [23]；Zhang 等虽然采用 MADDPG 同时调 \(J\) 与 \(D\)，研究对象仍是单个并网 VSG [24]。三者说明 actor–critic 可用于连续参数自适应，但“使用 multi-agent algorithm”与“多台 VSG 之间形成去中心协调”是不同主张。

单机证据还暴露了一个方法边界：这些策略通常把频率指标压缩进 reward，而不直接测量 \(P/Q\) 交叉通道或机间振荡模态 [22]–[24]。因此，把它们迁移到并联系统需要重新定义状态、动作、通信与物理评价，而不是简单复制算法。

### 6.2 直接并联 VSG/MARL 文献已经占据了“参数协调”新颖性

Yang 等已经把多台并联 VSG 的惯量—下垂协调表述为未知转移函数的 Markov game；每个 agent 使用本地与相邻 VSG 信息，通过 Soft Actor-Critic 动态抑制不同工况下的功率振荡 [4]。Kang 等进一步用中心 reward sharing 训练分散策略，在 IEEE 33-bus 模型上自适应多 VSG 参数 [5]。二者共同意味着，“用 MARL 动态调多 VSG 惯量/下垂以改善频率稳定”不是空白。

并联 VSG 的 DRL 功率分配同样已有直接证据。Oboreh-Snapps 等在 APEC 工作中用一个集中观察所有 IBDG 状态的 DRL agent 同时限制电压和无功分配误差 [6]，随后又用单一 TD3 agent 处理频率恢复与有功分配 [25]。这些论文与 per-VSG MARL 不同，但已经覆盖“用学习同时协调两类电气目标”的基本思路；若新工作只把 \(P/f\) 和 \(Q/V\) 分给两个 task agent，新颖性仍然不足。

| 工作 | 设备/agent 关系 | 主要动作 | 主要目标 | 验证层级 | 没有建立的结论 |
|---|---|---|---|---|---|
| Yang et al. [4] | 每台 VSG 基于本地/邻居信息 | inertia、droop | 功率振荡抑制 | 时域数值结果 | 正式闭环安全、未见拓扑、PHIL |
| Kang et al. [5] | 多 VSG、中心 reward sharing | VSG 自适应参数 | 频率稳定 | IEEE 33-bus 仿真 | 物理 \(P/Q\) 解耦、硬件泛化 |
| Oboreh-Snapps et al. [6] | 单 agent、全局 IBDG 状态 | 电压相关参考/补偿 | 电压边界、无功分配 | 简单并联系统仿真 | MARL、per-device decentralization |
| Oboreh-Snapps et al. [25] | 单 agent、全局 IBDG 状态 | 有功/频率补偿 | 频率恢复、有功分配 | 双机 MATLAB/Simulink | 跨拓扑与 HIL |
| Oboreh-Snapps et al. [23] | 单 VSG、单 agent | inertia、damping | 频率动态 | RTDS | 多 VSG coordination |

### 6.3 邻近微电网 MARL 提供方法组件，不提供 VSG 结论

PowerNet 通过局部状态、邻居通信、spatial discount 和 action smoothing 改善多 DG 电压控制的可扩展性 [26]；Hu 等在两个时间尺度上协调有功与无功装置，并测试通信失效和 missing observations [27]；Guo 等把 inverter Volt-Var control 写成 constrained Markov game，以 safety projection 修正动作并以 state synchronization 处理通信时延 [28]。这些工作证明了局部消息、时空分解和安全层可以嵌入 MARL，但对象主要是配电网电压控制，不能直接外推到含 swing equation、inner-loop dynamics 和 current limiting 的并联 VSG。

Xia 等在 networked microgrids 中用安全模型监督分散经济频率控制 [29]，而 Guo 等在电压控制中使用显式 action projection [28]；两者都比纯 reward penalty 更接近可执行安全机制。然而，它们的保证与约束仍绑定各自模型，不能替代对完整 VSG 闭环的稳定与限流验证。

## 7. Safety, OOD and deployment：MARL 的主要证据缺口

### 7.1 稳定性必须来自可审计结构，而不是平均回报

Cui 等通过 Lipschitz constraints 构造指数稳定的分散电压控制器 [30]，Feng 等由显式 Lyapunov function 推出 monotone policy 的充分条件并以 monotone neural network 强制满足 [31]，Shuai 等把 model-based RL、Lyapunov region of attraction 与 Gaussian process uncertainty model 结合用于 grid-forming inverter frequency regulation [32]。三项证据共同表明：安全 RL 的有效保证来自受限策略类、可行域或 safety filter，而不是 RL 优化器本身。

相反，把“测试轨迹没有越界”称为稳定性，会把统计观察误写成闭环性质。同步与功率分配的经典结果能够明确给出同步解、可服务负载集合或 gain/setpoint 条件 [33], [34]；MARL 研究至少应说明其安全证书覆盖的是 reduced power model、averaged converter model、policy map，还是包含饱和、限流、保护和通信的完整 hybrid system。

### 7.2 跨规模不等于跨拓扑

Hossain 等用 graph convolution 把电网拓扑嵌入 DRL，并在拓扑变化下优于 fully connected baseline [35]；PowerNet 在不同规模 microgrid 上展示可扩展分散控制 [26]。但“在两个网络分别训练/测试”与“同一 policy 对未见节点数、接线图和线路参数零样本迁移”不同。并联 VSG 文献中，本次检索未发现严格的 leave-one-topology-out 证据。

对本主题而言，拓扑 OOD 至少应同时改变：VSG 数量、并联/网状接线、额定容量、线路 \(R/X\)、短路比、负载位置和通信图。若 policy 的输入维数固定，新增/删除 VSG 后必须重训，那么它提供的是多设备控制，不是 topology generalisation。

### 7.3 通信鲁棒性必须包含退化与恢复过程

现有工作分别测试了通信故障/plug-and-play [19]、时延/丢包 [20]、missing observations [27] 和 state synchronization [28]，但这些条件并不等价。MARL 评估应按 nominal、bounded delay、random dropout、burst loss、stale packet、network partition、完全断链和恢复过程逐级测试，并预先定义断链时是冻结动作、回退 deterministic baseline，还是切换 local-only policy。

只在训练中随机化固定 delay 并不能支持“通信鲁棒”。如果 CTDE 使用全局状态训练，还必须区分训练期信息与部署期信息，避免把 centralized critic 的便利误写成在线完全分散。

### 7.4 实时证据仍然断裂

单 VSG TD3 已有 RTDS 证据 [23]，确定性多 VSG adaptive inertia 已有 OPAL-RT HIL [16]，并联 VSG 传统解耦/分配方法也有原型或缩比实验 [2], [3], [12]–[14]。邻近配电控制领域甚至已有基于 PHIL 的 coordinated voltage regulation RL 研究 [36]。然而，本次语料没有发现把 per-VSG MARL、物理解耦指标、未见拓扑和 PHIL/物理并联逆变器同时结合的研究。

因此，MATLAB/Simulink 只能支持算法可行性，RTDS/CHIL 主要支持实时执行，PHIL 或多逆变器实验才开始接触功率接口、传感噪声、延迟、饱和和保护。证据层级必须写在结论里，不能用“real-time”模糊代替“physical”。

## 8. Cross-branch synthesis：MARL 何时才有不可替代增量

四个分支共同指向一个边界：**可解析、局部且结构稳定的耦合，应先由确定性控制消除；MARL 只应处理剩余的跨设备、非平稳、多目标协调。** 这不是为了限制算法，而是为了识别因果增量。若 MARL 同时获得更大的动作范围、全局观测、更高带宽和更多储能 headroom，那么性能改善无法归因于“多智能体学习”。

基于上述证据，本文推断最值得检验的架构是三层职责分离；这是研究设计建议，而不是已经由直接对照实验确立的最优架构：

1. **物理基础层：** 电流/电压内环、限流、anti-windup、basic VSG、complex-impedance-aware decoupling 或 enhanced virtual impedance。该层在没有学习器时也必须稳定。
2. **分布式协调层：** DAPI、mutual damping、diffusion 或另一种具有明确退化行为的 deterministic coordinator，维持频率/电压恢复和基本功率分配。
3. **有界 residual MARL 层：** 每台 VSG 的 actor 仅输出有限幅值、有限变化率的参数残差或参考值残差；动作先经过 safety projection，再与基础控制叠加。断讯、OOD detector 触发或证书失效时，残差平滑归零。

该架构把问题从“神经网络能否直接控制并联 VSG”改写为可证伪问题：在 deterministic controller 已经安全且相当强的条件下，MARL 是否利用局部与邻居信息，在未见拓扑/阻抗/通信条件下进一步降低物理交叉耦合和机间振荡，而不增加硬约束违例与控制压力？

评价 MARL 的价值还需要机制消融。至少比较 centralized controller、independent agents、MARL without communication、MARL with communication、memory/no-memory、constrained/unconstrained policy，以及同容量 non-learning residual。若去掉 learned communication 后性能不变，则“协调”贡献不成立；若同容量非学习 residual 同样有效，则收益来自额外控制权限而不是学习。

## 9. Falsifiable research programme

### 9.1 预注册假设

- **H1 — 物理解耦增量：** 在相同测量、动作幅值、带宽、通信和储能约束下，residual MARL 相对最佳 deterministic coordinator 显著降低交叉通道 interaction energy，而不恶化电压/频率稳态偏差。
- **H2 — 机间协调增量：** 在参数不匹配与扰动下，per-VSG MARL 显著降低主导机间模态的振荡能量和暂态分配误差，且优于 adaptive inertia、mutual damping 与 diffusion baseline。
- **H3 — 拓扑 OOD：** 使用共享参数或 graph/message-passing policy 的 MARL，在未见 VSG 数量和接线图上零样本保持预先设定的安全与性能阈值；固定维度 MLP policy 作为反事实。
- **H4 — 安全非劣化：** safety-constrained residual MARL 不增加任何 hard-constraint violation；若 safety layer 频繁接管，则即使最终轨迹安全，也拒绝“policy 本身可用”的命题。

### 9.2 物理指标

对一次仅改变 \(P^\star\) 的小扰动，定义归一化交叉作用：

\[
C_{P\rightarrow Q}
=
\frac{\int_0^T |\Delta Q(t)|\,dt}
{\int_0^T |\Delta P(t)|\,dt+\varepsilon}.
\]

对一次仅改变 \(Q^\star\) 或电压参考的扰动，类似定义

\[
C_{Q\rightarrow P}
=
\frac{\int_0^T |\Delta P(t)|\,dt}
{\int_0^T |\Delta Q(t)|\,dt+\varepsilon}.
\]

这两个指标必须与 closed-loop off-diagonal frequency-response magnitude、circulating-current RMS/peak、稳态 sharing RMSE、暂态 sharing error、主导模态 damping ratio、settling time、frequency nadir、RoCoF 和 bus-voltage deviation 联合报告。reward 可以使用其中部分量，但最终证据必须来自独立评估脚本，避免 reward hacking。

约束指标至少包括 converter current、DC-link/储能功率与能量、modulation limit、动作幅值/变化率、保护触发次数、safety-layer intervention rate、通信量、推理时延和控制 effort。只报告平均 reward 或最佳轨迹不合格。

### 9.3 训练—测试严格分离

| 维度 | 训练分布 | OOD 测试 |
|---|---|---|
| VSG 数量 | 例如 2–3 台 | 1、4、5 台及 plug-and-play |
| 电气拓扑 | 固定并联/少量径向图 | 未见径向、网状、线路切除与重构 |
| 线路 | 有限 \(R/X\) 与长度区间 | 区间外 \(R/X\)、强 mismatch、参数突变 |
| 装置 | 同额定值或有限异构 | 未见容量比、内环带宽、能量 headroom |
| grid strength | 训练 SCR 区间 | 更弱/更强网与 X/R 改变 |
| 扰动 | 负荷/参考阶跃 | 并机、模式切换、故障后恢复、组合扰动 |
| 通信 | nominal + 小时延 | jitter、burst loss、partition、完全断链与恢复 |
| 测量/执行 | 有限噪声与时延 | 噪声漂移、偏置、packet staleness、计算超时 |

训练 topology、调参 topology 和最终报告 topology 必须彼此分离；同一测试集不能反复用于选择 checkpoint。每个算法使用相同总环境交互数、wall-clock 调参预算和网络容量级别，并报告全部随机种子、失败 run、置信区间和 effect size。

### 9.4 强基线与公平权限

最低比较链为：

\[
\text{conventional VSG}
\rightarrow
\text{complex-impedance decoupling}
\rightarrow
\text{enhanced/adaptive virtual impedance}
\rightarrow
\text{enhanced VSG}
\rightarrow
\text{adaptive inertia or mutual damping}
\rightarrow
\text{DAPI/diffusion coordinator}
\rightarrow
\text{residual MARL}.
\]

所有方法必须具有相同的测量集合、邻居范围、动作上下限、控制更新率、通信预算和可用储能。若某个 baseline 因实现原因缺少等价权限，应同时报告“原始版本”和“权限匹配版本”，不能用弱实现制造 MARL 优势。

### 9.5 必需消融

1. deterministic baseline only；
2. baseline + random residual；
3. baseline + tuned linear/non-learning residual；
4. independent RL agents；
5. MARL without messages；
6. MARL with messages；
7. MARL with graph/shared-parameter policy；
8. unconstrained MARL；
9. safety-projected residual MARL；
10. full model去掉每一项 reward/observation/action。

MARL 评价容易受到随机种子、调参预算和 baseline 实现影响。Gorsane 等对 75 篇 cooperative MARL 论文的 meta-analysis 发现足以质疑真实进展速度的评价不一致，并提出标准化协议 [37]；Dulac-Arnold 等则把 partial observability、delays、offline data、safety 和 non-stationarity 列为 real-world RL 的核心挑战 [38]。因此，本研究的主结果必须是预注册 OOD 物理指标与失败率，而不是单一 seed 的回报曲线。

### 9.6 证据阶梯与停止门

1. **解析/离线门：** basic closed loop 稳定；action bounds 和 safety projection 定义完成；若 residual authority 接近零或 deterministic baseline 已达噪声地板，停止训练。
2. **同分布门：** MARL 必须超过强 deterministic baseline；若预注册主要指标的置信区间跨零，拒绝 H1/H2。
3. **OOD 门：** 在未见 topology、agent count、\(R/X\)、SCR 和通信故障下通过硬约束；否则主张限于训练附近工况。
4. **机制门：** MARL with communication 必须超过 independent agents 与等容量 non-learning residual；否则不能声称 multi-agent coordination 增量。
5. **实时门：** CHIL/RTDS 中满足固定步长、推理时限和 packet timing；否则不进入功率级测试。
6. **物理门：** PHIL 或多逆变器实验重复主要 OOD 趋势，并完整报告接口算法、放大器时延、缩放误差、保护与失败试验。邻近领域的 PHIL RL 研究 [36] 可作为实施参考，但不能替代本对象的验证。

## 10. Open problems and future directions

### 10.1 完整闭环的稳定证书

现有 safe RL 主要在简化 voltage/frequency dynamics 上构造 Lipschitz、monotone 或 Lyapunov 约束 [30]–[32]，而 VSG 装置还包含内环、限流、饱和、采样、PWM/平均模型差异和保护状态切换。真正的开放问题不是“给 reward 加一个安全罚项”，而是确定哪些 residual action set 能在这些 hybrid dynamics 下保持 forward invariance 或可恢复性。

### 10.2 数量可变的 per-VSG policy

直接并联 VSG MARL 仍以固定设备数和固定输入维度为主 [4], [5]，而 PowerNet 与 topology-embedded DRL 只在邻近电压控制中提供可扩展/拓扑表征证据 [26], [35]。需要验证共享 actor、message passing 或 permutation-equivariant policy 是否真的能在未见 VSG 数量上零样本运行，而不是仅减少训练参数。

### 10.3 解耦与能量可行性的联合评价

更激进的惯量、阻尼、虚拟阻抗或 residual reference 可能通过额外储能功率和峰值电流换取更小振荡。现有 VSG DRL 文献多强调频率动态 [22]–[24]，并联分配文献多强调 error [6], [25]；二者均需要与 DC-side energy headroom、thermal/current limits 和保护动作联合评价，否则“解耦改善”可能只是控制压力转移。

### 10.4 通信图与电气图不一致

DAPI、distributed secondary 和 MARL 常使用邻居信息 [4], [19], [20], [26]，但通信邻居不必等于电气邻居。需要单独研究两张图的错配、异步更新、分区和恢复；尤其要区分性能下降、失稳和安全回退三种结果。

### 10.5 可复现的动态 VSG benchmark

Power-system RL 已有电压/拓扑 benchmark，但缺少同时包含多 VSG averaged/switching dynamics、current limiting、保护、通信、可变拓扑和统一强基线的公开环境。没有这一层，跨论文 reward 与百分比不能直接比较，所谓 SOTA 很容易来自不同控制权限或不同模型精度。

## 11. Conclusion

**RQ1：并联 VSG 的“解耦”是什么？**  
证据支持四类不同问题：线路复阻抗导致的 \(P/Q\) 通道耦合、馈线不匹配导致的功率分配与环流、VSG 参数不匹配导致的机间动态振荡，以及分层控制中的恢复—分配—约束协调。它们需要不同指标和基线，不能用单一 reward 或 tracking error 合并。

**RQ2：MARL 已经提供了什么？**  
直接文献已经证明，MARL 可以动态协调并联 VSG 的 inertia/droop 参数，DRL 可以处理并联逆变器的有功/无功分配，邻近微电网文献也展示了局部通信、CTDE、安全投影和图表征。然而，证据主要来自固定拓扑仿真；“MARL 用于并联 VSG”本身不再是充分的新颖性，现有工作也没有建立天然解耦、跨拓扑泛化或完整闭环安全。

**RQ3：什么研究仍然值得做？**  
值得做的是一条更严格的 hybrid route：以 complex-impedance-aware/enhanced VSG 和 distributed deterministic coordinator 保证基本稳定与可解释控制，让 per-VSG MARL 只输出可投影、可撤销的有界 residual；用独立交叉耦合指标、强基线、未见拓扑、通信失效、机制消融和 CHIL→PHIL 阶梯检验增量。若 MARL 不能在相同权限下超过 adaptive inertia、mutual damping、DAPI 或 diffusion，负结果同样有科学价值：它会给出学习协调的适用边界，而不是笼统否定 MARL。

## References

[1] Wei Yao, Min Chen, J. Matas, et al., “Design and Analysis of the Droop Control Method for Parallel Inverters Considering the Impact of the Complex Impedance on the Power Sharing,” IEEE Transactions on Industrial Electronics, 2011.

[2] Heng Wu, Xinbo Ruan, Dongsheng Yang, et al., “Small-Signal Modeling and Parameters Design for Virtual Synchronous Generators,” IEEE Transactions on Industrial Electronics, 2016.

[3] Jia Liu, Yushi Miura, Hassan Bevrani, et al., “Enhanced Virtual Synchronous Generator Control for Parallel Inverters in Microgrids,” IEEE Transactions on Smart Grid, 2017.

[4] Qiufan Yang, Linfang Yan, Xia Chen, et al., “A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs,” IEEE Transactions on Power Systems, 2023.

[5] Seokjun Kang, Yoongun Jung, Deokki You, et al., “Enhancing Frequency Stability With Decentralized Adaptive Control Using Multi-Agent Deep Reinforcement Learning of Multi-VSGs,” International Journal of Electrical Power & Energy Systems, 2025.

[6] Oroghene Oboreh-Snapps, Sophia A. Strathman, Jonathan Saelens, et al., “Addressing Reactive Power Sharing in Parallel Inverter Islanded Microgrid Through Deep Reinforcement Learning,” IEEE Applied Power Electronics Conference and Exposition, 2024.

[7] Anand Tuladhar, Hua Jin, Tom Unger, et al., “Control of Parallel Inverters in Distributed AC Power Systems With Consideration of Line Impedance Effect,” IEEE Transactions on Industry Applications, 2000.

[8] Qing-Chang Zhong, “Robust Droop Controller for Accurate Proportional Load Sharing Among Inverters Operated in Parallel,” IEEE Transactions on Industrial Electronics, 2013.

[9] Bin Li, Lin Zhou, Xirui Yu, et al., “Improved Power Decoupling Control Strategy Based on Virtual Synchronous Generator,” IET Power Electronics, 2017.

[10] Lei Wang, Tiecheng Li, Xuekai Hu, et al., “Power Decoupling Control of Paralleled Virtual Synchronous Generators Based on Virtual Complex Impedance,” Energy Reports, 2023.

[11] Jinwei He, Yunwei Li, “Analysis, Design, and Implementation of Virtual Impedance for Power Electronics Interfaced Distributed Generation,” IEEE Transactions on Industry Applications, 2011.

[12] Jinwei He, Yunwei Li, Josep M. Guerrero, et al., “An Islanding Microgrid Power Sharing Approach Using Enhanced Virtual Impedance Control Scheme,” IEEE Transactions on Power Electronics, 2013.

[13] Hisham Mahmood, Dennis Michaelson, Jin Jiang, “Accurate Reactive Power Sharing in an Islanded Microgrid Using Adaptive Virtual Impedances,” IEEE Transactions on Power Electronics, 2015.

[14] Aazim Rasool, Shah Fahad, Xiangwu Yan, et al., “A Virtual Parallel Inductor Approach for Mitigating Reactive Power Sharing Error in a VSG Controlled Microgrid,” IEEE Systems Journal, 2023.

[15] Kai Shi, Cheng Chen, Yuxin Sun, et al., “Rotor Inertia Adaptive Control and Inertia Matching Strategy Based on Parallel Virtual Synchronous Generators System,” IET Generation, Transmission & Distribution, 2020.

[16] Siqi Fu, Yao Sun, Zhangjie Liu, et al., “Power Oscillation Suppression in Multi-VSG Grid With Adaptive Virtual Inertia,” International Journal of Electrical Power & Energy Systems, 2022.

[17] Siqi Fu, Yao Sun, Lang Li, et al., “Power Oscillation Suppression of Multi-VSG Grid via Decentralized Mutual Damping Control,” IEEE Transactions on Industrial Electronics, 2022.

[18] Chang Li, Yaqian Yang, Nenad Mijatović, et al., “Frequency Stability Assessment of Grid-Forming VSG in Framework of MPME With Feedforward Decoupling Control Strategy,” IEEE Transactions on Industrial Electronics, 2022.

[19] John W. Simpson-Porco, Qobad Shafiee, Florian Dörfler, et al., “Secondary Frequency and Voltage Control of Islanded Microgrids via Distributed Averaging,” IEEE Transactions on Industrial Electronics, 2015.

[20] Qobad Shafiee, Josep M. Guerrero, Juan C. Vásquez, “Distributed Secondary Control for Islanded Microgrids—A Novel Approach,” IEEE Transactions on Power Electronics, 2014.

[21] Chenglong Huang, Chunhui Liang, Renjie Liu, et al., “Coordinated Control Strategy for Parallel Virtual Synchronous Generators Based on Diffusion Algorithm,” Sustainable Energy Technologies and Assessments, 2026.

[22] Yushuai Li, Wei Gao, Weihang Yan, et al., “Data-Driven Optimal Control Strategy for Virtual Synchronous Generator via Deep Reinforcement Learning Approach,” Journal of Modern Power Systems and Clean Energy, 2021.

[23] Oroghene Oboreh-Snapps, Buxin She, Shah Fahad, et al., “Virtual Synchronous Generator Control Using Twin Delayed Deep Deterministic Policy Gradient Method,” IEEE Transactions on Energy Conversion, 2024.

[24] D. J. Zhang, Jing Zhang, Yu He, et al., “Adaptive Control of VSG Inertia Damping Based on MADDPG,” Energies, 2024.

[25] Oroghene Oboreh-Snapps, Sophia A. Strathman, Jonathan Saelens, et al., “Simultaneous Frequency Regulation and Active Power Sharing in Islanded Microgrid Using Deep Reinforcement Learning,” IEEE Kansas Power and Energy Conference, 2024.

[26] Dong Chen, Kaian Chen, Zhaojian Li, et al., “PowerNet: Multi-Agent Deep Reinforcement Learning for Scalable Powergrid Control,” IEEE Transactions on Power Systems, 2022.

[27] Daner Hu, Zhenhui Ye, Yuanqi Gao, et al., “Multi-Agent Deep Reinforcement Learning for Voltage Control With Coordinated Active and Reactive Power Optimization,” IEEE Transactions on Smart Grid, 2022.

[28] Guodong Guo, Mengfan Zhang, Yanfeng Gong, et al., “Safe Multi-Agent Deep Reinforcement Learning for Real-Time Decentralized Control of Inverter Based Renewable Energy Resources Considering Communication Delay,” Applied Energy, 2023.

[29] Yang Xia, Yan Xu, Yu Wang, et al., “A Safe Policy Learning-Based Method for Decentralized and Economic Frequency Control in Isolated Networked-Microgrid Systems,” IEEE Transactions on Sustainable Energy, 2022.

[30] Wenqi Cui, Jiayi Li, Baosen Zhang, “Decentralized Safe Reinforcement Learning for Inverter-Based Voltage Control,” Electric Power Systems Research, 2022.

[31] Jie Feng, Yuanyuan Shi, Guannan Qu, et al., “Stability Constrained Reinforcement Learning for Decentralized Real-Time Voltage Control,” IEEE Transactions on Control of Network Systems, 2024.

[32] Hang Shuai, Buxin She, Jinning Wang, et al., “Safe Reinforcement Learning for Grid-Forming Inverter Based Frequency Regulation With Stability Guarantee,” Journal of Modern Power Systems and Clean Energy, 2025.

[33] John W. Simpson-Porco, Florian Dörfler, Francesco Bullo, “Synchronization and Power Sharing for Droop-Controlled Inverters in Islanded Microgrids,” Automatica, 2013.

[34] Johannes Schiffer, Roméo Ortega, Alessandro Astolfi, et al., “Conditions for Stability of Droop-Controlled Inverter-Based Microgrids,” Automatica, 2014.

[35] Ramij Raja Hossain, Qiuhua Huang, Renke Huang, “Graph Convolutional Network-Based Topology Embedded Deep Reinforcement Learning for Voltage Stability Control,” IEEE Transactions on Power Systems, 2021.

[36] Gilberto Darbali-Zamora, Mario Jimenez Aparicio, et al., “Reinforcement-Learning Control for Coordinated Voltage Regulation in Distribution Systems Using a Power Hardware-in-the-Loop Platform,” IEEE Access, 2026.

[37] Rihab Gorsane, Omayma Mahjoub, Ruan John de Kock, et al., “Towards a Standardised Performance Evaluation Protocol for Cooperative MARL,” Advances in Neural Information Processing Systems, 2022.

[38] Gabriel Dulac-Arnold, Nir Levine, Daniel J. Mankowitz, et al., “Challenges of Real-World Reinforcement Learning: Definitions, Benchmarks and Analysis,” Machine Learning, 2021.
