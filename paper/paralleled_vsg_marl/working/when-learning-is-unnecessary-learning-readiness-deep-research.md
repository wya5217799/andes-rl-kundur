# 什么时候根本没有必要学习：强经典控制之后的学习必要性与 VSG/MARL 训练前审计

## 摘要

在控制问题中，强化学习（RL）或多智能体强化学习（MARL）是否值得训练，通常被当作算法选择问题：选择 TD3、SAC、MAPPO，调整奖励，再观察训练能否超过基线。本调研考察一个更早、也更根本的问题：在给定物理对象、动作端口、信息结构、约束和评价目标后，是否存在足够大的、可部署且可学习的性能增量，使训练本身具有科学和工程意义？本调研围绕三个研究问题展开：强经典控制何时会耗尽学习增量；哪些训练前诊断能够区分无控制余量、信息不足、数据不足和算法失败；这些诊断能否在 VSG/GFM 分布式控制中构成独立的方法学贡献。

跨控制理论、系统辨识、残差学习、安全强化学习和电力电子控制的证据表明，不存在“强经典控制必然使神经网络无用”的一般定理。更准确的条件性结论是：当结构化模型足够准确、经典控制器与学习器具有相同权限和约束、主要可控模态已被有效控制、测试分布又缺少不可消除的模型失配时，学习器面对的是一个幅值小、信噪比低、信息依赖弱且容易被统计波动淹没的残差问题。反之，在模型失配、时变工况、未建模非线性、部分可观测、计算时延或策略类受限等条件下，学习仍可能有实质价值。

本调研据此合成一个五门训练前协议：动作—输出权威、数据可辨识性、部署信息价值、强基线后的因果余量、以及统计可学习性与安全回退。单项工具已有充分先例，但本轮检索没有发现 VSG/GFM/MARL 原始研究把这些门串成一套允许给出 `NO-TRAINING` 的前瞻性协议。该方向具有方法学研究价值，但若要成为有说服力的论文，必须同时包含一个被正确拒绝训练的案例和一个通过门控、训练后确有增量的对照案例；只有固定 Kundur 系统上的负结果不足以验证整个方法。

## 1. 引言与研究问题

经典控制与学习控制之间并非简单的替代关系。在线性二次调节器（LQR）等结构明确的问题上，模型式方法可以比模型自由方法用更少样本达到相同控制质量 [7]；在接触、摩擦和模型失配难以显式描述的机器人任务中，经典控制解决已知结构、RL 只学习剩余误差，反而能提高样本效率和真实系统性能 [10]。这两个看似相反的结果共同指出：关键不是“神经网络是否更强”，而是“经典控制之后还剩下什么，以及这些剩余是否能被当前动作和信息识别”。

在 VSG/GFM 文献中，这个问题尤其重要。现有学习工作常把固定 droop、固定 inertia/damping 或无控制作为主要基线 [19,20]；与此同时，LQR、自适应优化、集中或分散 MPC、局部全状态反馈等非学习方法已经能动态调节 VSG 参数或直接控制 converter power injection [21–24]。如果两类方法的动作权限、信息、限幅、能量预算和运行周期不匹配，那么“学习优于经典控制”与“经典控制压缩了学习价值”都可能只是比较合同不一致的产物。

本调研回答三个问题：

1. **RQ1：** 哪些理论与实验机制解释了强经典控制之后学习增量接近零？
2. **RQ2：** 哪些训练前诊断能够区分无控制权、无可部署余量、信息不足、数据不足和算法优化失败？
3. **RQ3：** 把这些诊断整合为 VSG/MARL 的 learning-readiness assessment，是否具有独立研究价值；若有，最低需要怎样的实验闭环？

调研角度不是反对学习，而是把“学习是否必要”变成可证伪的前置条件。目标读者是电力系统、控制与机器学习审稿人。

## 2. 方法

本轮检索于 2026 年 8 月完成。检索分为三条相互独立的视角：

- **主流与反方视角：** 比较 model-based、model-free、residual RL 和强经典控制，寻找“无增量”和“存在增量”的条件性证据；
- **方法论视角：** 检索 controllability、observability、system identification、value of information、oracle gap、safe policy improvement 和统计评估；
- **VSG/GFM 应用视角：** 检索 inertia/droop 学习、power-reference 控制、distributed MPC、adaptive VSG、GFM controllability 与多智能体分解。

纳入的技术性结论只使用同行评议论文、正式会议论文或作者公开的原始论文。对于只能访问摘要的 Yang 等工作 [20]，只使用元数据和摘要能够直接支持的事实，不推断其未公开的基线强度、随机种子或消融结果。对于“尚未发现统一协议”的判断，采用检索限定语：它表示在本轮关键词、引文追踪和可访问文献中未找到直接重合工作，不构成绝对的首创性证明。

### 2.1 证据类型与可支持结论

| 证据类型 | 代表工作 | 可以支持 | 不能支持 |
|---|---|---|---|
| 线性控制与样本复杂度理论 | Moore [1]；Tu 与 Recht [7] | 特定模型类中的可控性、有效方向和模型式样本优势 | 一般非线性深度 MARL 必然无效 |
| 信息论与决策理论 | Majumdar 与 Pacelli [4]；Soleymani 等 [5] | 给定传感器或通信合同下的性能上界和信息价值 | 增加观测必然改善有限样本神经网络训练 |
| 残差学习实验 | Johannink 等 [10]；Silver 等 [11] | 基线存在系统性缺陷时，残差学习可有价值 | 任意不完美基线都存在可学残差 |
| 安全改进与评估理论 | Laroche 等 [14]；Berkenkamp 等 [15]；Agarwal 等 [17] | 低置信区域回退、受限安全保证、统计比较原则 | 将保证无条件迁移到非线性 VSG 全阶模型 |
| VSG/GFM 仿真与实验 | Li 等 [19]；Stanojev 等 [22]；Koiwa 等 [23]；Chen 等 [24] | 具体动作端口和控制结构下的可实现能力 | 证明所有 VSG 或所有拓扑上的普遍优越性 |

## 3. 分类：学习价值消失与重新出现的五个层面

现有证据可以组织为五个互不替代的层面。它们也是后续训练前门控的理论来源。

### 3.1 物理动作权威：名义动作维数不等于有效控制维数

对有限时域输出 (y_{0:H}) 和动作 (u_{0:H})，可定义局部响应矩阵

\[
S_H=\frac{\partial\operatorname{vec}(y_{0:H})}
{\partial\operatorname{vec}(u_{0:H})}.
\]

其奇异值描述不同动作组合能够在多大程度上改变任务输出。Moore 的平衡实现把 controllability 与 observability 统一到 Hankel singular values 中 [1]；Chen 等则直接在 GFM power loops 上研究 controllability Gramian，并在通过可控性分析后设计只使用本地测量的全状态反馈 [24]；Markovic 等的 adaptive VSM 进一步表明，当 inertia/damping 端口在模型中具有明确权威时，LQR 已可形成动态参数反馈 [21]。这些工作共同说明：控制器设计之前应先确认动作端口是否真正作用于目标动态。

在并联或多区域系统中，四个 agent 并不自动产生四个有价值的协调方向。若主要扰动和奖励只激励 common frequency 与一个 inter-area differential mode，多路设备动作可能在任务输出上高度共线。此时增加 actor 数量只增加优化自由度，不增加实际任务自由度。需要强调的是，**低秩不等于无价值**：一个低维方向仍可能对关键指标有很大影响；真正接近数学障碍的是在明确有限时域或线性化合同中，目标相关方向具有精确零响应。

### 3.2 数据可辨识性：有控制权不等于当前数据能识别它

即使 (S_H) 在理论上有秩，训练数据也可能没有充分激励这些方向。线性或特征线性辨识中，探针特征 Gramian

\[
G_N=\sum_{t=1}^{N}\phi_t\phi_t^{\top}

\]

的最小特征值和预测置信宽度反映数据是否覆盖各方向。Simchowitz 等说明单轨迹线性系统辨识的难度受系统动态与激励共同决定，甚至某些更不稳定系统反而更容易辨识 [2]；Mania 等进一步表明，具有已知特征结构的非线性系统需要主动探索所有相关特征方向 [3]。

因此，“动作能改变系统”与“critic 能从现有轨迹识别动作效果”是两个不同命题。Virginillo 等在 power-system dynamic parameter identification 中用 numerical Fisher information matrix 检查参数可辨识性 [30]，提供了电力系统近邻先例。强经典控制会把状态约束在狭小区域，通常提高安全性，却也可能减少残差动作的自然激励。结果是：真实余量可能很小，而估计方差并不会按同样比例缩小，学习信号更容易被仿真噪声、工况差异和随机种子吞没。

### 3.3 决策信息价值：全局存在好动作不等于局部 agent 能选出来

Majumdar 与 Pacelli 用 task-relevant information 给定传感器条件下的最优期望回报建立上界 [4]；Soleymani 等在网络化控制的特定 Gauss–Markov 模型中证明，只有当信息包的 value of information 非负时才值得传输 [5]。这些工作并不直接给出 VSG MARL 算法，却提供了一个重要逻辑：**信息的价值来自它能否改变最优决策，而不是观测维数本身。**

对同一动作和约束，可定义全信息因果最优代价 (J^*_{\mathrm{full}}) 与部署信息下的因果最优代价 (J^*_{\mathrm{local}})。信息损失为

\[
\Delta_{\mathrm{info}}=J^*_{\mathrm{local}}-J^*_{\mathrm{full}}\ge 0.
\]

若全信息 controller 明显改善、局部或邻居信息 controller 却不能改善，问题首先在 information pattern，而不是 MARL credit assignment。Losapio 等已经用数据估计 power-grid state-action 关联并构造潜在可分解子问题 [29]，但该工作主要服务于分解和后续学习，并未同时检查强非学习基线之后还有没有性能余量。

### 3.4 强基线后的可部署余量：经典控制“吸收价值”的真正含义

令 (J_b) 为与学习器具有相同动作、限幅、能量、信息和运行周期的强基线代价，且代价越小越好。定义

\[
\Delta_{\mathrm{deploy}}=J_b-J^*_{\mathrm{local}}.
\]

这表示部署时真正可利用的最大增量。再用特权模型、全状态或未来信息构造不可部署上界 (J^*_{\mathrm{priv}})，则

\[
\Delta_{\mathrm{physical}}=J_b-J^*_{\mathrm{priv}},
\qquad
\Delta_{\mathrm{physical}}
=\Delta_{\mathrm{deploy}}+Delta_{\mathrm{info}}

\]

仅在三个 oracle 的动作与约束完全一致时成立。这里的“deployable causal oracle headroom”是本调研基于 performance-difference、信息价值和 residual RL 文献合成的诊断量，不是现有文献中的统一标准术语。

强经典控制吸收学习价值，不是神经网络被控制器“压制”，而是以下机制叠加：

1. **主模态已被占用。** Droop、LQR、MPC 或 distributed secondary control 已处理 common frequency 和主 inter-area mode；剩余动作只作用于弱模态。
2. **残差幅值收缩。** 性能函数在强基线附近趋于平坦，最优 residual action 小，任何函数逼近误差都占据更大相对比例。
3. **因果相关性收缩。** 状态偏差被快速压低后，局部观测与最优残差之间的 mutual information 或可预测关系随之减弱。
4. **物理投影吞噬残差。** Ramp、energy、current 和 voltage guard 会把 nominal neural action 投影回可行集合；网络输出变化不再等于 achieved action 变化。
5. **评价转为 Pareto trade-off。** 一个学习器可能改善 frequency deviation，却恶化 active-power oscillation；把多指标压成单一 reward 会制造“总分胜出”，但不能证明全面增量。
6. **增量低于统计分辨率。** 当真实提升与 seed 方差、场景差异或数值误差同量级，算法排序不稳定。Henderson、Agarwal 和 Gorsane 等分别表明，少量运行、点估计和不一致评估会显著削弱 RL/MARL 比较的可信度 [16–18]。

这种机制在 model-based 与 model-free 比较中有直接先例。Tu 与 Recht 在 LQR 上证明，简单 model-based 方法可用更少样本达到同等控制质量 [7]；Koryakovskiy 等发现，当不确定性可以通过辨识消除时，NMPC 更有优势，只有不可消除模型误差越过特定 break-even point 后，model-free RL 才开始占优 [8]；Lin 等在 adaptive cruise control 中也发现，无模型误差时长时域 MPC 与 DRL 接近，而模型失配扩大后 DRL 的相对优势才出现 [9]。这些结论都不是“模型式永远更强”，而是把学习价值定位在模型缺陷和部署条件上。

### 3.5 可学习性与安全回退：有余量仍可能学不到

即使 (\Delta_{\mathrm{deploy}}>0)，深度 MARL 仍可能因为探索不足、离线数据覆盖差、奖励错误、critic 偏差、非平稳性或信用分配而失败。Kakade 与 Langford 的 performance-difference lemma 表明策略差异取决于新策略占用分布下的 baseline advantage [6]；这也意味着只在 baseline 数据分布上估计残差，不能保证覆盖改进策略会访问的区域。

Residual RL 的正结果恰好说明这一层面的条件性。Johannink 等让经典反馈控制处理已知刚体结构，让 RL 处理接触和摩擦等难建模残差 [10]；Silver 等在 partial observation、noise、model misspecification 和 controller miscalibration 下研究 residual policy [11]。与之相对，Cheng 等的 control regularization 揭示了明确的 bias–variance trade-off：靠近控制先验可以降低方差和保持稳定性，但先验若本身次优，过强正则会阻止策略到达更优区域 [12]。LEOC 则在运行点附近使用稳定线性 controller、远离运行点时增加 learned policy 权重 [13]，把学习价值明确放在条件变化而不是名义区域。

因此，oracle 有余量但 RL 失败并不能反推无余量。更有区分力的设计是先监督拟合 oracle action：若监督策略能改善而 RL 不能，主要问题在探索、奖励或优化；若监督策略也不能改善，则需检查策略表示、信息和动作投影。低置信区域应回退到 baseline；SPIBB、安全 model-based RL 与 shielding 等工作为这种保守改进提供了不同假设下的先例 [14,15]，但其理论保证不能直接无条件移植到全阶 VSG 非线性仿真。

## 4. VSG/GFM 文献中的真实比较边界

### 4.1 学习调节 inertia/droop：自然，但不是唯一动作

Li 等把 virtual inertia 和 damping factor 定义为学习动作，并以频率、RoCoF 和有功响应构造奖励 [19]；Yang 等进一步把多个并联 VSG 的 dynamic inertia-droop control 表述为使用本地和邻居信息的多智能体学习问题 [20]。这说明 M/D 是与 swing-equation 机理对齐、软件上容易暴露的低维动作，但并不证明它是 VSG 智能体的唯一物理端口。

同一类自适应能力也可以由非学习控制实现。Markovic 等用 LQR-based adaptive VSM 调节惯量和阻尼 [21]；Koiwa 等在线优化 inertia/damping，并用电路模型保证 current limit，且进行了实验比较 [23]。因此，若学习论文只比较 fixed M/D，就证明了“动态参数优于固定参数”，还没有证明“学习优于强 adaptive control”。

### 4.2 Power-reference 与 GFM power-loop 控制：强经典替代路线已经存在

Stanojev 等的 centralized/decentralized MPC 直接控制 GFM converter power injections，显式处理 frequency nadir、RoCoF 和能量约束，并在 IEEE 39-bus 高保真 DAE 模型上验证 [22]。Chen 等从 MIMO power-loop controllability 出发，使用本地量测实现 full-state feedback 并进行实验验证 [24]。这两项工作说明：不调 M/D 也能形成物理明确、分布式或本地执行的 GFM 控制对象。

对应的学习价值应来自不同的比较维度。例如 Feng 等的 linear-plus-neural controller 在时变惯量场景上明显优于 optimized linear controller，同时达到接近 finite-horizon LQR 的性能；其贡献不是“超过知道全时域系统与惯量轨迹的 LQR”，而是用实时可计算策略逼近特权上界 [25]。Cui 等则说明非线性学习策略可以超过 optimal linear droop [26]，但这仍不能自动推导出其优于 nonlinear MPC 或所有 adaptive controller。

### 4.3 强比较常产生条件性优势，而非全面胜出

Wu 等的 GFM deep synchronization controller 改善频率指标，但论文报告的 active-power IAE 中 droop 为 0.190、学习器为 0.197 [27]。Stanojev 等在 fast frequency control 中比较 RL 与 equivalent MPC；RL 在线计算更快，但两者控制周期并不完全一致，论文也指出在相同时间步下行为接近 [31]。Liu 等在 inverter Volt–Var control 中进一步显示，residual RL 的收益依赖近似模型与真实系统之间的缺口，同时残差动作空间过窄会排除最优动作，过宽又增加学习难度 [28]。

这些结果的共同含义不是“学习赢”或“经典赢”，而是：学习价值必须被绑定到模型误差、计算时延、策略类、分布变化或某个特定 Pareto 端点。只在固定名义场景上比较一个综合 reward，会把这些条件抹掉。

## 5. 提议的五门 learning-readiness protocol

综合上述证据，训练前应按顺序执行五个门。后一个门不能补救前一个门的失败。

| Gate | 核心问题 | 最小诊断 | GO 条件 | NO-TRAINING 含义 |
|---|---|---|---|---|
| G1 物理权威 | 动作能改变目标输出吗？ | 对称有限差分、(S_H) 奇异值、achieved-action audit、约束投影率 | 至少存在与论文目标对齐且可重复的有效方向 | 当前动作/对象/约束合同没有足够权威；不是算法失败 |
| G2 数据可辨识 | 现有轨迹能区分这些方向吗？ | 探针 Gramian、bootstrap 奇异值、局部模型置信宽度 | 关键方向的效应大于估计不确定性 | 当前场景或探针不足；应改实验激励，不应先换网络 |
| G3 信息价值 | 部署信息能选择正确动作吗？ | full-state causal oracle 与 local/neighbor causal oracle 比较；oracle-action predictability | 局部/邻居历史保留实质可部署增量 | 物理上有好动作，但当前 agent 看不出来；应改信息结构 |
| G4 基线余量 | 强匹配基线后还有多少价值？ | 同权限、同约束 baseline 与 causal oracle 的 (\Delta_{\mathrm{deploy}}) 和置信区间 | 余量超过 practical threshold，且多端点 no-harm 可满足 | 强基线已耗尽该合同下的实质增量；停止算法 sweep |
| G5 可学习与安全 | 余量能被稳定学到吗？ | oracle imitation、centralized learner、distributed learner、coverage、seeds、fallback | 监督和集中式先成功；分布式训练有统计增量并可安全回退 | 前门通过而 RL 失败时，才归因优化、奖励、credit 或 nonstationarity |

一个可操作的停止规则是

\[
\operatorname{UCB}(\Delta_{\mathrm{deploy}})
\le \varepsilon_{\mathrm{practical}}
\quad\Longrightarrow\quad
\text{NO-TRAINING}.
\]

若 (\operatorname{LCB}(\Delta_{\mathrm{deploy}})>0)，但余量与统计置信宽度同量级，正确结论是“当前实验分辨率不足”，不是“RL 失败”。这里必须使用 causal、deployable oracle；知道未来扰动的 outcome-seeing oracle 只能作为不可实现的绝对上界，不能直接授权 MARL。

### 5.1 原因分解判决树

1. **Full-state causal oracle 也不优于 baseline：** 无实质控制余量，停止学习；重新审视 benchmark、动作或题目。
2. **Full-state oracle 有余量，local/neighbor oracle 无余量：** 信息结构失败；研究通信、记忆或观测，不研究网络深度。
3. **Local oracle 有余量，但监督拟合失败：** 表示能力、数据覆盖或动作投影失败。
4. **监督拟合成功，centralized RL 失败：** 奖励、探索、critic、训练预算或实现失败。
5. **Centralized RL 成功，distributed RL 失败：** 才主要指向 credit assignment、nonstationarity 或 coordination information。
6. **名义 Kundur 无余量，异质运行点、拓扑或 OOD 有余量：** 学习价值来自 condition-dependent adaptation；论文应以跨条件适应为主线，而不是固定拓扑 SOTA。

## 6. 该方向是否构成独立论文

### 6.1 已有部分与可能的新贡献

单独做 controllability、Fisher information、安全过滤或 state-action factorization，创新性有限：这些部分分别有 Chen [24]、系统辨识文献、safe RL [14,15] 和 Losapio [29] 等先例。Residual RL 也早已提出“已知结构交给经典控制、未知部分交给学习” [10,11]。

本轮检索未找到一篇 VSG/GFM/MARL 原始论文同时完成以下四件事：

- 让经典与学习方法使用完全匹配的动作、信息、约束和周期；
- 在训练前测量任务相关的物理有效秩与 achieved action；
- 用 causal oracle 分解 physical headroom 与 deployable information headroom；
- 当强基线后的可部署余量不足时，正式给出可复现的 `NO-TRAINING` 结论。

因此，可能的新贡献不是“发现 RL 有时没用”，而是：

> 一套在投入 MARL 训练前，前瞻性判断是否存在物理可实现、信息可支持、强非学习控制尚未耗尽、且统计上可辨认的性能机会的 learning-readiness assessment。

这一表述应保留“本轮检索所见”“据可访问文献”等限定；在投稿前仍需进行系统性 novelty search，不能轻率写成 first-ever。

### 6.2 最低可发表证据闭环

只有负例不够。一个有说服力的方法学论文至少需要三部分：

1. **NO-TRAINING 案例：** 固定或简单系统中，强匹配 baseline 与 causal oracle 差距低于 practical threshold；不同 RL 算法即使训练也不能稳定产生实质增量。
2. **GO-TRAINING 案例：** 引入有物理依据的异质性、参数漂移、拓扑变化、时延或难建模非线性，使 G1–G4 全部通过；随后简单 learner 获得可重复增量。
3. **预测有效性：** 门控结论必须在训练之前冻结，并且能预测后续 learner 成败；否则协议只是对既有结果的事后解释。

还应加入 matched adaptive/LQR/MPC/distributed baseline、多个运行点和扰动、至少一个 unseen topology 或 OOD 条件、多随机种子区间估计、performance profile、所有物理端点与 no-harm guard。若没有 GO 案例，该工作更像严谨的 bounded negative result 或方法提案，难以证明门控具有选择力。

## 7. 对当前 VSG/Kundur 研究线的含义

当前最重要的含义不是立刻重新训练 M/D MARL，也不是继续寻找“传统控制上一定存在的神经残差”。Residual learning 的文献前提本来就是存在系统性、可观测且可重复的 baseline defect；当 baseline 已接近当前任务合同的可实现上界时，残差不是被训练器藏起来了，而可能根本低于实用与统计阈值。

因此，当前线的下一步如果服务于“尽快完成现有论文”，应优先保持已有停止结论的边界，不因本调研重新开启算法 sweep。若另立方法学方向，则最小新增工作不是 TD3/SAC/MAPPO 比较，而是构造一个严格 causal oracle，并寻找一个有明确工程依据、能够使 headroom 从 `NO-TRAINING` 转为 `GO-TRAINING` 的对照环境。候选变化应来自现实的不确定性或分布变化，而不是为了让 RL 赢而人为削弱经典基线。

这也回答了“是否只能走 M/D”的问题：不是。M/D 是低维且物理对齐的动作，但 adaptive M/D 已有强经典方法；power-reference、auxiliary damping、distributed secondary control 和 GFM MIMO power-loop 也可以形成多智能体端口。真正决定是否值得学习的是动作权威、可部署信息和剩余余量，而不是动作名称。

## 8. 开放问题

1. **非线性时变系统中的有效秩。** 线性 Gramian 与有限差分奇异值如何在故障切换、限幅和动作投影下形成稳健指标？
2. **Causal oracle 的构造。** 如何避免 outcome-seeing oracle 高估部署能力，同时又不把某个弱 controller family 错当作上界？
3. **Practical threshold 的定义。** 余量阈值应由控制指标、统计分辨率、能量成本、部署风险和计算成本共同确定，而不能任意设为某个百分比。
4. **多指标 Pareto headroom。** 频率、同步、有功振荡、能量和安全约束之间的余量如何用 Pareto front 而非单一 reward 表达？
5. **从一个 benchmark 推广。** 一套 readiness protocol 是否能跨 Kundur、IEEE 39-bus、微电网和 EMT 模型保持相同的预测意义？
6. **训练成本的价值核算。** 即使 learner 略优于 baseline，离线数据、仿真、调参、验证和认证成本是否超过其生命周期收益？

## 9. 结论

**对 RQ1：** 强经典控制不会在一般数学意义上消灭神经网络价值。它通过控制主要可控模态、缩小状态与残差幅值、降低局部观测对最优残差的可预测性、触发物理投影，并把剩余改善压到统计分辨率附近，使学习增量在特定合同下接近零。模型准确、约束匹配且工况稳定时，model-based control 往往更高效；不可消除模型误差、时变条件或未建模非线性出现后，学习价值可能重新出现。

**对 RQ2：** 不能用一次 RL 失败判断“无需学习”。需要依次检查动作—输出权威、数据可辨识性、部署信息价值、强匹配基线后的 causal oracle headroom、以及可学习性与安全回退。只有这些门都通过后，分布式训练失败才主要指向 MARL 的 credit、nonstationarity 或优化问题。

**对 RQ3：** 深度调研是必要的，因为该问题具有独立的方法学潜力，而且能阻止继续无效的算法 sweep。本轮文献支持把贡献定位为“可否决训练的 learning-readiness protocol”，而不是“证明 RL 不必要”。但要把它变成强论文，必须增加一个前瞻性 GO 案例，与当前 NO-TRAINING 类型案例形成对照；否则只能形成边界清楚的负结果或方法提案。

## 参考文献

[1] B. C. Moore, “Principal Component Analysis in Linear Systems: Controllability, Observability, and Model Reduction,” *IEEE Transactions on Automatic Control*, 1981.

[2] M. Simchowitz, H. Mania, S. Tu, M. I. Jordan, and B. Recht, “Learning Without Mixing: Towards a Sharp Analysis of Linear System Identification,” *Conference on Learning Theory*, 2018.

[3] H. Mania, M. I. Jordan, and B. Recht, “Active Learning for Nonlinear System Identification with Guarantees,” *Journal of Machine Learning Research*, 2022.

[4] A. Majumdar and V. Pacelli, “Fundamental Performance Limits for Sensor-Based Robot Control and Policy Learning,” *Robotics: Science and Systems*, 2022.

[5] T. Soleymani, J. S. Baras, S. Hirche, and K. H. Johansson, “Value of Information in Feedback Control: Global Optimality,” *IEEE Transactions on Automatic Control*, 2023.

[6] S. Kakade and J. Langford, “Approximately Optimal Approximate Reinforcement Learning,” *International Conference on Machine Learning*, 2002.

[7] S. Tu and B. Recht, “The Gap Between Model-Based and Model-Free Methods on the Linear Quadratic Regulator: An Asymptotic Viewpoint,” *Conference on Learning Theory*, 2019.

[8] I. Koryakovskiy, M. Kudruss, R. Babuška, W. Caarls, C. Kirches, K. Mombaur, J. P. Schlöder, and H. Vallery, “Benchmarking Model-Free and Model-Based Optimal Control,” *Robotics and Autonomous Systems*, 2017.

[9] Y. Lin, J. McPhee, and N. L. Azad, “Comparison of Deep Reinforcement Learning and Model Predictive Control for Adaptive Cruise Control,” *IEEE Transactions on Intelligent Vehicles*, 2021.

[10] T. Johannink et al., “Residual Reinforcement Learning for Robot Control,” *IEEE International Conference on Robotics and Automation*, 2019.

[11] T. Silver, K. Allen, J. Tenenbaum, and L. Kaelbling, “Residual Policy Learning,” arXiv preprint, 2018.

[12] R. Cheng, A. Verma, G. Orosz, S. Chaudhuri, Y. Yue, and J. Burdick, “Control Regularization for Reduced Variance Reinforcement Learning,” *International Conference on Machine Learning*, 2019.

[13] N. Zhang and N. Capel, “LEOC: A Principled Method in Integrating Reinforcement Learning and Classical Control Theory,” *Learning for Dynamics and Control*, 2021.

[14] R. Laroche, P. Trichelair, and R. Tachet des Combes, “Safe Policy Improvement with Baseline Bootstrapping,” *International Conference on Machine Learning*, 2019.

[15] F. Berkenkamp, M. Turchetta, A. Schoellig, and A. Krause, “Safe Model-Based Reinforcement Learning with Stability Guarantees,” *Advances in Neural Information Processing Systems*, 2017.

[16] P. Henderson et al., “Deep Reinforcement Learning That Matters,” *AAAI Conference on Artificial Intelligence*, 2018.

[17] R. Agarwal, M. Schwarzer, P. S. Castro, A. C. Courville, and M. G. Bellemare, “Deep Reinforcement Learning at the Edge of the Statistical Precipice,” *Advances in Neural Information Processing Systems*, 2021.

[18] R. Gorsane, O. Mahjoub, R. J. de Kock, R. Dubb, S. Singh, and A. Pretorius, “Towards a Standardised Performance Evaluation Protocol for Cooperative MARL,” *Advances in Neural Information Processing Systems*, 2022.

[19] Y. Li et al., “Data-Driven Optimal Control Strategy for Virtual Synchronous Generator via Deep Reinforcement Learning Approach,” *Journal of Modern Power Systems and Clean Energy*, 2021.

[20] Q. Yang, L. Yan, X. Chen, Y. Chen, and J. Wen, “A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs,” *IEEE Transactions on Power Systems*, 2023.

[21] U. Markovic, Z. Chu, P. Aristidou, and G. Hug, “LQR-Based Adaptive Virtual Synchronous Machine for Power Systems with High Inverter Penetration,” *IEEE Transactions on Sustainable Energy*, 2019.

[22] O. Stanojev, U. Markovic, P. Aristidou, G. Hug, D. Callaway, and E. Vrettos, “MPC-Based Fast Frequency Control of Voltage Source Converters in Low-Inertia Power Systems,” *IEEE Transactions on Power Systems*, 2022.

[23] K. Koiwa, A. Tomabechi, T. Zanma, and K.-Z. Liu, “Dynamic Optimisation of Virtual Synchronous Generator to Enhance Stability of Power System,” *IET Smart Grid*, 2024.

[24] M. Chen, D. Zhou, A. Tayyebi, E. Prieto-Araujo, F. Dörfler, and F. Blaabjerg, “On Power Control of Grid-Forming Converters: Modeling, Controllability, and Full-State Feedback Design,” *IEEE Transactions on Sustainable Energy*, 2024.

[25] J. Feng, M. Muralidharan, R. Henriquez-Auba, P. Hidalgo-Gonzalez, and Y. Shi, “Stability-Constrained Learning for Frequency Regulation in Power Grids with Variable Inertia,” *IEEE Control Systems Letters*, 2024.

[26] W. Cui, Y. Jiang, and B. Zhang, “Reinforcement Learning for Optimal Primary Frequency Control: A Lyapunov Approach,” *IEEE Transactions on Power Systems*, 2023.

[27] Z. Wu, M. Zhang, B. Fan, Y. Shi, and X. Guan, “Deep Synchronization Control of Grid-Forming Converters: A Reinforcement Learning Approach,” *IEEE/CAA Journal of Automatica Sinica*, 2025.

[28] Q. Liu, Y. Guo, L. Deng, H. Liu, D. Li, and H. Sun, “Residual Deep Reinforcement Learning With Model-Based Optimization for Inverter-Based Volt-Var Control,” *IEEE Transactions on Sustainable Energy*, 2025.

[29] G. Losapio, D. Beretta, M. Mussi, A. M. Metelli, and M. Restelli, “State and Action Factorization in Power Grids,” *ECML PKDD Workshop*, 2024.

[30] A. Virginillo, A. Derviškadić, and M. Paolone, “Identification of Power System Dynamic Model Parameters Using the Fisher Information Matrix,” *IEEE Transactions on Power Systems*, 2025.

[31] O. Stanojev, O. Kundacina, U. Markovic, E. Vrettos, P. Aristidou, and G. Hug, “A Reinforcement Learning Approach for Fast Frequency Control in Low-Inertia Power Systems,” *North American Power Symposium*, 2021.
