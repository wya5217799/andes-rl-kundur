---
title: "从固定 3 秒硬切换到状态感知多时间尺度交接：面向 ICEMS 与后续期刊的 Deep Research"
created: 2026-07-30
cutoff: 2026-07-30
review_after: 2027-01-30
status: current
scope: cross-line
authority: derivative literature synthesis
---

# 从固定 3 秒硬切换到状态感知多时间尺度交接：问题不在“3”，而在开环交接

## 摘要

本报告研究现有“慢速 droop--PI 储能 + 前 3 秒公共惯量脉冲 +
固定窗口内差模残差”的方法是否真正解决了电源--负荷--储能的多时间尺度
耦合。检索覆盖截至 2026-07-30 的状态/事件触发控制、自适应 VSG、
储能能量管理、分层控制、安全/残差强化学习以及具有真实局部动作的 MARL，
并以当前仓库的有效证据边界为约束。综合结果表明：固定 3 秒可以作为冻结
基准，却不能支撑“一般性快慢协调”结论，因为控制器无法感知频率轨迹所处
阶段、慢层是否接管、差模是否仍活跃、储能是否具有裕度以及撤出动作是否
再次激发系统。最小且可证伪的改进不是 learned switching，而是一个
确定性的、带迟滞和驻留时间、支持无扰斜坡退出的状态交接监督器。只有当
这个经典监督器在匹配预算下优于固定窗口，才有理由训练受约束的 learned
residual。若要重新建立 MARL 的研究价值，还必须让代理保留不同的局部信息、
动作和物理约束；继续把四个输出聚合成同一个标量，无法识别多代理架构的
增量价值。

## 1. 研究问题

- **RQ1**：固定 3 秒快层退出遗漏了哪些状态耦合与跨时间尺度交接？
- **RQ2**：近年的哪些机制可以替代固定时间硬切分，同时保持约束、可解释性
  与可审核性？
- **RQ3**：对当前 ICEMS 稿件，最小的可证伪算法改动是什么；哪些扩展应留给
  后续期刊？

本报告的核心判断是：**3 秒的主要问题不是数值未经全局寻优，而是它把本应
由闭环状态决定的撤出过程外生化了。** 因此，扫描 2、3、4、5 秒只能检验
灵敏度，不能解决交接机制缺失。

## 2. 方法

### 2.1 检索视角

检索分成三个独立视角：

1. 主流控制：adaptive inertia/damping、状态/事件触发、BESS 频率支撑、
   multi-rate 与 hierarchical MPC；
2. 反例与安全：hybrid switching、hysteresis、dwell time、chatter、
   bumpless transfer、SOC/功率/电流限制与二次频率跌落；
3. 相邻学习架构：hierarchical/residual/safe RL、runtime projection，
   以及具有不同局部动作和信息的 CTDE/MARL。

检索以 2023--2026 年同行评议原始论文为主，保留少量直接定义问题的较早
论文。纳入条件是论文必须至少回答状态触发、交接、能量约束、安全残差或
真实多代理角色中的一个问题；只讨论市场调度、纯通信触发或没有可迁移
控制机制的论文不进入核心综合。最终核心语料为 22 篇论文。

### 2.2 证据类型

| 证据类型 | 能支持什么 | 不能自动支持什么 |
|---|---|---|
| 稳定性/驻留时间证明 | 在声明模型和假设下排除不稳定切换或 Zeno 行为 | 未建模储能、负荷和执行器下的整体安全 |
| HIL/PHIL/实验 | 切换连续性、设备滞后和参数自适应具有物理可实现性 | 多区域、未知拓扑或统计稳健性 |
| 多场景仿真 | 在给定模型、扰动和参数范围内的比较结果 | 部署、广义最优或因果上的 MARL 必要性 |
| 当前仓库的 sealed paired evidence | 固定 Kundur 问题内的控制权、增量和不确定性 | 文献方法已在本仓库成立 |

外部论文只提供设计依据；仓库中的 CLM-0590、CLM-0595 与 CLM-0610
继续决定现有实验事实。文献不覆盖或改写这些证据。

## 3. 耦合分类

现有方法同时涉及四类耦合，但只显式处理了其中一部分：

| 耦合轴 | 现有处理 | 缺失 |
|---|---|---|
| 共模--差模 | 指标分离；差模输入硬零和 | 输入零和不等于非线性输出解耦；固定一维区域方向 |
| 快--慢动态 | 快惯量与慢有功同时运行 | 撤出不看慢层积分器、实际功率、饱和和接管状态 |
| 功率--能量 | 慢层投影检查 SOC、能量、功率和 ramp | 快层门控不使用储能裕度；没有重复事件 readiness |
| 信息--动作 | 共享 actor 使用不同局部观测 | 四个输出被聚合成一个标量，代理没有可归责局部动作 |

这一区分解释了为什么已有结论并不矛盾：R276 的 `ADDITIVE-ONLY`
表明快慢层各自有用但没有测得非加性交互；R277 表明差模自适应目标存在；
R280 又表明在同一个单标量动作上，集中式 actor 比共享投票架构更强。
这些证据共同支持“问题存在，但当前 MARL 因子分解没有解决完整耦合”，
而不是“所有分层控制无效”或“所有 MARL 无效”。

## 4. 状态感知撤出与混杂交接

Liu 等的 adaptive-droop VSG 根据频率轨迹进入恢复阶段后撤出支撑，并在
频率再次偏离时恢复支撑；Wang 等则根据频差与 RoCoF 所处的加速/减速区域
连续调整惯量和阻尼，而 equilibrium-point assessment 进一步表明不同暂态
区域可能需要相反的惯量调整方向 [1,3,11]。这些研究虽然控制对象不同，却
共同说明同一件事：
撤出条件应绑定轨迹阶段，而不是统一时钟。Boyle 等与 Hosseini 等在风机
惯量恢复研究中进一步表明，支撑撤出会暴露尚未被其他资源接管的功率缺口，
从而产生第二次频率跌落 [2,5]。该机制不能直接等同于 VSG 参数撤出，但
足以构成必须验证的可迁移假设。

只把时钟换成单阈值也不充分。Li 等的 hysteresis switching 理论与 Liu 等
的 dynamic event-triggered LFC 都要求缓冲区、定时状态或正的事件间隔，
以避免抖振和 Zeno 行为 [9,10]；Feng 等在 variable-inertia 电网中的
event-triggered switching 同样依赖逐模式稳定性与足够慢的切换 [12]。
因此，一个合格的交接器至少需要 mode memory、不同的退出/重入阈值、
minimum dwell 和 switch-count audit。

在并联 VSG 场景，Shi 等的事件触发二次控制与 Gao 等的 adaptive mutual
damping 分别从低带宽协同和局部振荡抑制说明：代理间协调应对应一个明确的
动态通道或局部控制作用，而不是只有形式上的多节点 actor [24,25]。

最后，开关连续性本身是物理问题。Jiang 等在 GFL/GFM 储能变流器切换中
把参考阶跃与相角不连续识别为振荡来源，并以 tracking/latching 实现
bumpless transfer [13]。这与当前在 3 秒处把公共脉冲和差模残差同时置零
形成直接对照：该跳变是设计动作，不是闭环稳定或“已经 settle”的证据。

## 5. 能量感知的快慢层级

Huang 等、Zhang 等和 Liu 等都把 SOC、充放电能力或恢复状态纳入 VSG/BESS
控制；共同结论是储能的频率支撑不仅有瞬时功率边界，还有撤出后的 recovery
debt [4,14,15]。Zhang 等的 adaptive frequency regulation 还把频率、风功率
和 SOC 同时用于改变 MPC 权重与约束边界 [7]。这些工作多采用规则、模糊逻辑
或设备特定 envelope，不能
证明某个统一门控最优，却明确否定“只要最后 SOC 合规，能量状态就不必进入
控制决策”的看法。

更长时间尺度上，Oshnoei 等用 two-layer multiple-model MPC 处理不确定性、
SOC 与操作约束，Pei 等把频率支撑分配和后续 SOC 恢复放入不同层级 [6,8]。
Gerini 等此前的实验性 GFM-BESS 多服务框架也采用 day-ahead、intra-day
和 real-time 三阶段，并在实时层显式处理 converter capability [16]。
这些方法比固定窗口更完整，但它们同时改变模型、优化器、预测信息和控制
目标，不适合作为回答教授意见的第一个 ICEMS 补充实验。

因此，会议级改动应只回答“状态交接是否比固定交接更好”；multi-horizon
MPC、重复事件能量预算与 SOC recovery 协同属于后续期刊。

## 6. 学习与真正多代理结构

Lu 等和 Zhang 等分别用 SAC 与 MADDPG 在线调整 VSG 的惯量/阻尼，说明
state-to-parameter adaptation 在仿真中可行 [17,18]。但它们没有识别
“固定撤出是否是缺失机制”，也不能替代确定性门控基线。Feng 等的
stability-constrained learning 和 Yuan 等的 distributed safe RL 都把
学习控制限制在 Lyapunov/safety envelope 内 [19,20]；Chen 等的
physics-shielded MARL 则让 BESS 安全约束直接修改执行动作，而不是只放进
reward 或事后审计 [21]。这些工作共同支持：如果后续加入学习，学习器应是
经典控制之上的 bounded residual，并由独立投影/安全层约束。

真正具有可识别多代理价值的论文具有不同的局部动作或层级职责。Xue 等的
hierarchical safe DRL 在上层配网与下层 VPP 之间传递不同指令；Zhao 等的
attention MARL 让不同发电机保留独立控制输出和非局部信息交换 [22,23]。
这与当前“四个局部 actor 投票后执行同一个 \(q\)”不同。若执行层仍只有
一个标量，集中式 actor 使用联合观测通常是自然且更直接的表示，加入 GNN、
attention 或更多代理不会自动创造新的控制自由度。

## 7. 推荐架构

### 7.1 第一阶段：Handoff-Aware Smooth Supervisor

第一阶段保持慢 droop--PI、快层幅值、差模方向、物理投影和扰动定义不变，
只替换撤出边。定义公共频差 \(e_{c,k}=f_0-f_{c,k}\) 和滤波 RoCoF
\(\nu_{c,k}\)。最小恢复阶段判据为

\[
e_{c,k}\nu_{c,k}<-\epsilon
\]

连续满足 \(m\) 个采样，并已超过最小 on-time 后，允许门控变量
\(g_k\in[0,1]\) 按冻结 slew 下降；不允许阶跃归零。完整但仍确定性的
handoff residual 可写成

\[
\chi_k=\max\!\left(
\frac{|e_{c,k}|}{\epsilon_f},
\frac{|\nu_{c,k}|}{\epsilon_r},
\frac{|\Delta f_{\mathrm{AB},k}|}{\epsilon_d},
\frac{|P^\star_{\mathrm{slow},k}-P_{\mathrm{slow},k}|}{\epsilon_p}
\right).
\]

当 \(\chi_k\le1\) 持续 confirmation dwell 时退出；当
\(\chi_k\ge h>1\) 且满足 minimum off-time 时才重入。SOC、能量、
实际功率、saturation 和 anti-windup 状态不是 performance trigger，
而是独立 safety veto。达到最大支撑时长仍未完成交接，应记录为 retained
failure，不能自动视为成功。

执行量为

\[
c_k=0.25g_k,\qquad
\mathbf r_k=g_k q_k[1,1,-1,-1]^\mathsf T .
\]

第一阶段不应直接把已有 15-step actor 外推到更长窗口。先在冻结经典快层或
\(q=0\) 下验证交接机制；若机制成立，再进行全窗口策略训练。

### 7.2 第二阶段：Coupling-Aware Budgeted Residual

只有第一阶段通过后，才把算法扩展为：

1. 经典慢层产生 fleet-level 有功需求 \(P^\star_\Sigma\)；
2. 状态监督器产生 fast-support envelope \(g_k\) 和剩余 action budget；
3. 各设备根据局部频率、SOC、功率/能量 headroom 和实际执行误差产生局部
   分配；
4. 安全投影同时执行总有功守恒、零和差模、幅值、slew 和设备 feasibility；
5. 学习器只输出经典分配之上的 bounded residual。

若仍要比较集中式与 MARL，二者必须拥有相同的**向量动作**和物理投影；
区别只能是 joint observation 与 local/communicated observation。还必须
引入确实会使局部决策不同的 SOC/capacity/headroom 异质性。否则实验仍然
只能回答参数化差异，不能回答多代理协调价值。

### 7.3 不推荐的直接跳跃

- 不直接让 RL 学 on/off：它同时改变交接机制与函数逼近，无法归因。
- 不先加 GNN/attention：单标量执行层没有空间自由度供它利用。
- 不只扫 2--5 秒：这是敏感性分析，不是闭环交接。
- 不把 action clipping 当安全证明：saturation 和 current-limit 会改变
  有效闭环模型。
- 不同时改门控、reward、动作维度、观测和训练算法：会失去可识别性。

## 8. 前瞻实验阶梯与停止条件

### Gate A：固定窗口是否真是缺失机制

对照组：

1. 固定 3 秒矩形门控；
2. recovery-phase gate：只用 \(e_c,\nu_c\)；
3. full handoff gate：增加差模与 slow requested--actual gap。

冻结项：慢控制器、快层幅值、扰动 bank、求解器、物理端点、最大幅值和
slew。任何阈值只根据 measurement resolution、控制周期和 actuator contract
预注册，不能看正式结果调节。

建议 co-primary：

- 绝对时间窗 \(3\)--\(10\) 秒的 worst-bus frequency IAE；
- \(3\)--\(10\) 秒 common-frequency secondary peak。

保留现有 RoCoF、worst-bus peak、同步损失、inter-area IAE、full-horizon
restoration、final-window error、SOC、功率/能量、completion、tail risk 和
constraint guards。新增 switch count、minimum inter-switch time、
boundary-aware total variation、release time 与 remaining budget。

公平性要求：adaptive gate 的公共惯量 action-L1 不得超过固定窗口的预注册
预算，或把额外预算单列为 co-primary cost；否则收益可能只是“用了更多
控制量”。

**Kill gate**：若 recovery-phase gate 相对固定 3 秒没有明确 paired benefit，
或收益伴随差模、尾部、TV/slew、储能或恢复伤害，停止 learned gate 和 MPC
扩展。若 full handoff gate 不优于 frequency/RoCoF-only gate，删除额外状态。

### Gate B：学习是否有增量

仅在 Gate A 为正时训练 full-window bounded residual，并对比：

- deterministic gate + \(q=0\)；
- deterministic gate + causal classical differential law；
- deterministic gate + centralized residual；
- deterministic gate + shared/local residual。

所有 seeds 预定义，使用新 held-out bank，禁止 best-seed/checkpoint 选择。
若确定性门控与集中 residual 已解释收益，MARL 不进入主张。

### Gate C：MARL 是否可识别

只有在引入 per-device actions、局部 feasibility 和异质 SOC/headroom 后，
才比较 centralized 与 parameter-shared local policies。成功标准不应只看
nominal mean performance，还要看通信受限、局部观测缺失、规模变化或
拓扑变化下是否存在集中式表示无法低成本获得的价值。该 Gate 属于期刊范围。

## 9. 对当前 ICEMS 稿件的决策

现有论文无需因为文献而宣布“实验无效”：固定 3 秒仍是一个经过冻结的有效
基准，现有 shared-vs-centralized 负向结果也仍成立。必须撤回或避免的是
“算法已经解决一般快慢耦合”与“MARL 架构提供增量价值”的表述。

如果教授要求在会议稿中增加一个新的因果结果，Gate A 是唯一建议的最小
补充实验。它直接回答教授指出的时间硬分割，并且不会把问题扩成新的算法
大杂烩。若 Gate A 通过，论文主线应转为“可审核的状态交接 + 受约束差模
分配”，MARL 架构比较降为次要结果；若 Gate A 不通过，则保留 3 秒为
bounded benchmark，明确承认尚未解决一般耦合，不再继续堆学习模块。

## 10. 结论

- **RQ1**：固定 3 秒遗漏了轨迹阶段、慢层接管、差模持续、储能 readiness、
  执行器模式与重复事件等闭环状态；并在退出处引入人为跳变。
- **RQ2**：最可靠的替代顺序是 deterministic state trigger、hysteresis、
  dwell time、bumpless slew 与独立 safety veto；multi-horizon MPC 和
  safe/residual RL 是后续层，而不是第一步。
- **RQ3**：ICEMS 最小实验是 gate-only causal ablation。真正的 MARL
  改进必须保留 per-agent vector actions 与局部约束；在单标量聚合问题上，
  集中式控制更强并不意外。

检索没有发现一篇论文同时覆盖 common/differential 分解、平滑状态交接、
显式储能能量契约、可归责的多代理局部动作和前瞻封存的多区域统计评估。
这是一个有价值的交叉空白，但不是穷尽性 novelty 证明。

## References

[1] J. Liu et al., “Adaptive-Droop-Coefficient VSG Control for Cost-Efficient Grid Frequency Support,” *IEEE Transactions on Power Systems*, 2024.

[2] J. Boyle, T. Littler, and A. M. Foley, “Coordination of Synthetic Inertia From Wind Turbines and Battery Energy Storage Systems to Mitigate the Impact of the Synthetic Inertia Speed-Recovery Period,” *Renewable Energy*, 2024.

[3] J. Wang and X. Zhang, “Transient Virtual Inertia Optimization Strategy for Virtual Synchronous Generator Based on Equilibrium Point State Assessment,” *International Journal of Electrical Power & Energy Systems*, 2024.

[4] Y. Huang et al., “Virtual Synchronous Generator Adaptive Control of Energy Storage Power Station Based on Physical Constraints,” *Energy Engineering*, 2023.

[5] S. A. Hosseini et al., “Coordinating Demand Response and Wind Turbine Controls for Alleviating the First and Second Frequency Dips in Wind-Integrated Power Grids,” *IEEE Transactions on Industrial Informatics*, 2024.

[6] S. Oshnoei et al., “A Novel Virtual Inertia Control Strategy for Frequency Regulation of Islanded Microgrid Using Two-Layer Multiple Model Predictive Control,” *Applied Energy*, 2023.

[7] J. Zhang et al., “An Adaptive Frequency Regulation Strategy With High Renewable Energy Participating Level for Isolated Microgrid,” *Renewable Energy*, 2023.

[8] M. Pei et al., “Hierarchical Control Strategy of Wind-Storage Frequency Support for SOC Recovery Optimization and Arbitrage Revenue,” *Applied Energy*, 2024.

[9] Z. Li et al., “Guaranteed Dwell-Times of Hysteresis Switching for Switched Nonlinear Systems via Switching Characteristic Indices,” *SIAM Journal on Control and Optimization*, 2023.

[10] G. Liu et al., “Hybrid Dynamic Event-Triggered Load Frequency Control for Power Systems With Unreliable Transmission Networks,” *IEEE Transactions on Cybernetics*, 2023.

[11] L. Wang et al., “Adaptive Inertia and Damping Coordination Control for Grid-Forming VSG to Improve Transient Stability,” *Electronics*, 2023.

[12] J. Feng et al., “Online Event-Triggered Switching for Frequency Control in Power Grids With Variable Inertia,” *IEEE Transactions on Power Systems*, 2025.

[13] G. Jiang et al., “Disturbance-Free Switching Control Strategy for Grid-Following/Grid-Forming Modes of Energy Storage Converters,” *Electronics*, 2025.

[14] X. Zhang et al., “Fuzzy Adaptive Virtual Inertia Control of Energy Storage Systems Considering SOC Constraints,” *Energy Reports*, 2023.

[15] Y. Liu et al., “Integrated Control Strategy of BESS in Primary Frequency Modulation Considering SOC Recovery,” *IET Renewable Power Generation*, 2024.

[16] F. Gerini et al., “Optimal Grid-Forming Control of Battery Energy Storage Systems Providing Multiple Services: Modeling and Experimental Validation,” *Electric Power Systems Research*, 2022.

[17] C. Lu and X. Zhuan, “Adaptive Control for Virtual Synchronous Generator Parameters Based on Soft Actor Critic,” *Sensors*, 2024.

[18] D. Zhang et al., “Adaptive Control of VSG Inertia Damping Based on MADDPG,” *Energies*, 2024.

[19] J. Feng et al., “Stability-Constrained Learning for Frequency Regulation in Power Grids With Variable Inertia,” *IEEE Control Systems Letters*, 2024.

[20] Z. Yuan, C. Zhao, and J. Cortés, “Reinforcement Learning for Distributed Transient Frequency Control With Stability and Safety Guarantees,” *Systems & Control Letters*, 2024.

[21] P. Chen et al., “Physics-Shielded Multi-Agent Deep Reinforcement Learning for Safe Active Voltage Control With Photovoltaic/Battery Energy Storage Systems,” *IEEE Transactions on Smart Grid*, 2023.

[22] L. Xue et al., “Privacy-Preserving Multi-Level Co-Regulation of VPPs via Hierarchical Safe Deep Reinforcement Learning,” *Applied Energy*, 2024.

[23] Y. Zhao, T. Liu, and D. J. Hill, “Distributed Attention-Enabled Multi-Agent Reinforcement Learning Based Frequency Regulation of Power Systems,” *IEEE Transactions on Power Systems*, 2025.

[24] M. Shi et al., “Frequency Restoration and Oscillation Damping of Distributed VSGs in Microgrid With Low Bandwidth Communication,” *IEEE Transactions on Smart Grid*, 2021.

[25] X. Gao et al., “An Adaptive Control Strategy With a Mutual Damping Term for Paralleled Virtual Synchronous Generators System,” *Sustainable Energy, Grids and Networks*, 2024.
