# 为什么直接调节 M/D 看起来是唯一成功的 VSG 多智能体路线？

## Executive verdict

不是因为数学已经证明“VSG 多智能体只能调节惯量 (M) 和阻尼/下垂 (D)”。更准确的结论是：

1. 仓库中只有早期的直接 M/D 家族获得了大规模、多变体训练；它确实提供了四个 VSG actor 直接控制各自物理参数的实现证据，但其“成功”受旧评价指标、较弱经典基线和循环 Bellman target 缺陷共同限制。
2. 其余路线并非大多属于“MARL 训练失败”。SAC-CTDE 是训练后塌缩；共享标量策略不是真正的分布式多智能体；三边分布式 TD3 完成了训练但没有超过匹配的强经典控制器；更多 model-first 与当前题目路线在训练前就因余量、信息、能量安全或模型保真度停止。
3. M/D 不是 VSG 或 grid-forming inverter 的唯一学习动作。文献与控制结构还支持有功/频率参考、无功/电压参考、虚拟阻抗、二次电压/频率补偿以及确定性控制器上的有界 residual。只是“多台 VSG + 每台一个去中心 actor + 非 M/D 动作”的直接文献明显更少。
4. Kundur 两区域系统很可能放大了问题：固定拓扑、四台近似对称装置和少数主导公共/区间模态，可能使四个 actor 的高维联合动作在输出上退化为少数有效方向；强经典控制又吸收了大部分剩余改善。但仓库尚未用输入—输出灵敏度的奇异谱或跨拓扑对照证明这一归因。

因此，若目标只是最快得到一组能收敛的多智能体曲线，直接 M/D 是当前工程阻力最小的路线；若目标是尽快完成一篇可信论文，继续做 M/D 算法 sweep 并不是最短路径。必须先证明存在“经典控制后仍有、局部可辨识、物理可执行”的多智能体增量。

## 1. Research questions and evidence boundary

- **RQ1：** 除直接 M/D 外，仓库中的多智能体训练是否大多失败？
- **RQ2：** 失败的根因是 MARL 的数学困难、Kundur 系统、动作端口，还是训练与评价设计？
- **RQ3：** VSG 多智能体是否只能调 M/D？
- **RQ4：** 哪个最小实验可以区分这些解释，并决定是否值得再次训练？

本报告分开使用两层证据：外部文献用于判断学界动作空间和一般 MARL 难点；仓库 claim 与 sealed result 只用于判断本项目已经验证了什么。仓库的负结果不外推为领域定理，外部论文的正结果也不转移为本项目证据。

## 2. 仓库中的“失败”需要重新分类

| 路线 | 是否真正多主体执行 | 是否完成神经训练 | 已验证结局 | 能否支持“数学上不可学” |
|---|---:|---:|---|---:|
| 早期每 VSG 直接 M/D 的 SAC/TD3/LSTM 家族 | 是，四 actor | 是，大量变体 | 旧综合指标曾为正；但强 droop 在论文同步指标上约优 47%，且循环策略受 R261 target 缺陷影响 | 否 |
| SAC-CTDE | 是，分散 actor、集中 critic | 是 | 75-episode 训练塌缩，`cum_rf=-0.1973` | 否；一次预算与实现下的经验失败 |
| 共享 TD3 与集中 TD3 的标量差动动作 | 否；多个输出最终聚合为一个标量 | 是 | 两者都优于零动作，但共享策略在两个主端点均明显弱于集中策略 | 否；反而说明集中解释已足够 |
| 三条物理边的 distributed TD3 residual | 是，但 actor 属于边而非 VSG | 是 | 强经典 edge controller 已有改善；learned centralized/distributed arms 均未同时超过经典基线的两主端点 | 否；证明该冻结动作与基线下无神经增量 |
| model-first residual headroom / local information | 尚无 MARL | 否 | outcome-seeing oracle 只有约 2% common、5.14% differential；局部 proxy 更弱且伤害 differential | 否；这是训练前余量/信息失败 |
| 当前每 VSG 直接 M/D formulation | 物理对象成立 | 否 | 强确定性控制相对零动作改善约 69.92%；best-of-nine oracle 仅再增 1.046%，低于 5% 门 | 否；仅否决该预训练屏幕 |
| 当前每 VSG power-reference/energy port | 四个 VSG-owned action | 否 | 所选确定性控制在全部 held-out 轨迹触发 ramp projection，STOP-UNSAFE-CONTROL | 否；动作安全失败，不是学习失败 |
| full-order source-model route | 目标是四 VSG actor | 否 | 16/16 控制记录模型保真门失败，最大 NRMSE 1.1387 对阈值 0.15 | 否；模型失败发生在控制设计前 |

所以“除了家族 1，大部分多智能体训练都失败”不准确。正确说法是：**真正完成训练且满足多主体语义的路线很少；其中一条塌缩、一条没有超过强经典基线；其余多数在训练前被物理或证据门停止。**

## 3. 根因是不是数学上的？

### 3.1 MARL 确实有一般性的数学困难

独立学习时，其他 actor 的策略同时变化，使单个 actor 看到的转移和回报分布非平稳；共享回报又造成 credit assignment。Lowe 等指出多智能体 Q-learning 面临非平稳性，policy-gradient 方差随 agent 数增加 [6]；Kuba 等进一步定量分析了 agent 数与探索对梯度方差的贡献 [7]。这些机制可以解释训练变难，但不能解释“为什么只有 M/D 能学”，更不能仅凭一次塌缩证明某个控制问题不可学。

### 3.2 本项目真正需要检验的是三个更具体的数学条件

在同一基线控制器附近，把一段轨迹的动作扰动到评价输出的映射写成有限时域灵敏度矩阵

\[
\delta \mathbf y \approx \mathcal S_u\,\delta \mathbf u,
\qquad
\mathcal S_u = \frac{\partial(y_{0:T})}{\partial(u_{0:T})}.
\]

M/D 本身也不是普通的加性功率输入。在简化摆动关系

\[
M_i\dot\omega_i=P_i^*-P_{e,i}-D_i\omega_i
\]

中，参数变化的控制权依赖当前状态；在同步平衡点附近，\(\omega_i\) 与 \(\dot\omega_i\) 都接近零，M/D 的一阶灵敏度也会变弱。事件发生后近似有

\[
\frac{\partial\dot\omega_i}{\partial M_i}\approx-\frac{\dot\omega_i}{M_i},
\qquad
\frac{\partial\dot\omega_i}{\partial D_i}\approx-\frac{\omega_i}{M_i}.
\]

这意味着 M/D 是否可辨识取决于扰动激励、轨迹阶段和机间相干性，并非天然比所有动作更有控制权。多智能体学习要有可信增量，至少需要同时满足：

1. **控制秩：** \(\mathcal S_u\) 在目标的 common/differential 坐标上存在不太小的奇异值。若四 actor 的动作只映射为一个公共量或一个区间差量，多余 actor 在物理上不可辨识。
2. **剩余余量：** 强确定性基线之后，非部署 oracle 的相对提升
   \[
   H=\frac{J_{\mathrm{base}}-J_{\mathrm{oracle}}}{|J_{\mathrm{base}}|}
   \]
   必须大于实验噪声、模型误差和预注册最小效应。若 \(H\) 只有约 1%–2%，再好的神经网络也没有足够可发表的空间。
3. **局部可辨识性：** actor 的本地/邻居观测 \(o_i\) 必须足以预测有价值的条件动作。可用 oracle action 的交叉验证误差、条件方差或 `local policy` 与 `state-seeing oracle` 的价值差检验。若同一 \(o_i\) 对应相反的最优动作，去中心 policy 不可能稳定学到该映射。

只有当上述条件通过而训练仍系统失败，才应主要怀疑优化器、critic、探索和 credit assignment。仓库现有证据已经显示“余量小”和“局部 proxy 弱”的具体实例，却没有建立所有 VSG 动作的普遍不可学性。

## 4. Kundur 两区域系统扮演什么角色？

Kundur 并不是不适合 MARL 的系统，但当前固定版本可能不是一个容易证明 MARL 必要性的 benchmark。

- 两区域系统的频率动态往往由公共频率方向和少数区间振荡方向主导；slow coherency 和 system-wide/residual frequency 分解为这种低阶结构提供了理论依据 [11], [12]。这会使四个 VSG actor 的动作维数大于有效输出维数。
- 四台装置、固定拓扑和近对称参数减少了需要状态依赖协调的异质性。确定性 droop、DAPI、mutual damping 或边协调器容易直接对准主导模态。
- 如果训练和测试都来自同一拓扑、相近工作点与扰动族，神经网络的表示能力没有获得展示机会；它可能只在拟合一个低维控制律。
- 反过来，Kundur 的连续动态并不自动导致 MARL 失败。直接 M/D 的早期训练能运行，说明仿真接口和基本学习闭环是可工作的。

因此，“原因在 Kundur”目前只能作为**待检验机制假设**。需要比较灵敏度奇异谱和 residual headroom 在固定对称系统与异质参数、变化拓扑/工作点下是否显著变化。如果所有动作在固定 Kundur 上都低秩、低余量，而在异质/OOD 条件下出现新方向，才可把 benchmark 过于简单列为主因。

## 5. VSG 智能体并不只能够调节 M/D

| 学习动作家族 | 物理作用 | 直接 multi-VSG MARL 证据 | 与当前仓库的关系 |
|---|---|---|---|
| virtual inertia、damping、droop | 改变 swing-like 动态与频率/功率响应 | 最直接；Yang 等和 Kang 等均采用多 VSG 参数自适应 [1], [2] | 早期接口最成熟，但强基线与能量可行性仍需补齐 |
| active-power / torque / frequency-reference residual | 改变有功注入与二次频率协调 | 并联 inverter 的 DRL 有先例；一个双 VSG 原型以功能型 agents 输出 \(P_{\mathrm{ref}}\) 向量，但不是一机一 actor [5], [10] | 当前已有四个 VSG-owned port，但 ramp/energy 安全门未通过 |
| reactive-power / voltage-reference compensation | 改变电压与无功分配 | 并联 grid-forming inverter DRL 与更广泛 inverter MARL 有证据；同一双 VSG 原型输出 \(Q_{\mathrm{ref}}\) 向量 [4], [5], [10] | 需要含电压/无功内外环的真实 VSG 模型；GENCLS M/D 环境不足以支持此主张 |
| virtual resistance/inductance | 改变输出阻抗、P/Q 耦合、环流与分配 | 确定性 VSG 证据充分；RL/GFM 研究存在，但严格 multi-VSG MARL 尚稀疏 [9] | 需要 converter/line impedance 模型和电流/电压约束 |
| distributed secondary voltage/frequency action | 恢复频率/电压并协调设备 | PowerNet 等已证明非 M/D 的 inverter MARL [3] | 属于邻近证据，不可直接冒充并联 VSG 机间动态结果 |
| bounded residual over deterministic controller | 只学习经典模型难覆盖的条件增量 | 是一种跨领域成熟结构，不等于已在本项目成功 | 与当前证据最匹配，但先要通过余量、信息和安全门 |

结论应分两层：**VSG 控制在物理上绝不只含 M/D；但在“多台 VSG、每台一个 actor、只用本地/邻居信息、闭环动态协调”这一严格交集内，现有正面文献确实主要集中于 M/D 或 droop 参数自适应。** 这是一种研究集中和建模便利，不是数学必然性。

## 6. 为什么 M/D 在本仓库里最容易训练？

直接 M/D 同时满足了四个工程便利条件：

1. 动作直接写入现有同步机/VSG 等值模型，不需要另建 converter、DC energy、current limit 和 inner loop。
2. 参数连续、低维、有界；在扰动后的非零频差/RoCoF 轨迹上会直接影响频率与功率振荡，使 reward 获得可见的动作信号。它在同步点附近的一阶控制权反而会变弱。
3. 四台设备天然对应四个 actor，论文叙事与代码接口表面一致。
4. 早期综合指标同时奖励多种暂态行为，使 RL 比单一 droop 更容易表现为正；改用论文同步指标并加入强 droop 后，优势消失。

因此，早期结果更像是“动作接口、reward 和模型恰好对齐”，而不是“神经网络发现了只有它能发现的多智能体规律”。

## 7. 一个能区分根因的最小决定性实验

不要先训练新算法。先在同一 held-out scenario bank、同一四 actor 权限、同一 common/differential 独立指标下，对两个动作端口做无训练诊断：

- **A：** per-VSG (M/D) residual；
- **B：** per-VSG、经过相同幅值/速率/能量投影的 active-power reference residual。

每个端口按顺序测四件事：

1. 用小脉冲/有限差分估计 \(\mathcal S_u\)，报告 singular spectrum、有效秩和各 actor 对 common/differential 输出的独立贡献。
2. 在匹配强确定性基线上计算 constrained outcome-seeing oracle headroom；没有至少预注册的 5% 双端点改善就停止。
3. 用严格 train/validation split 拟合 `local/neighbor observation → oracle action`，并与 state-seeing upper bound 比较；局部映射无方向一致性就停止。
4. 检查所有候选动作的 ramp、energy、current/voltage 与稳定回退；任何硬约束系统性触发就停止。

诊断逻辑如下：

| 观察结果 | 主因判断 | 后续动作 |
|---|---|---|
| M/D 有秩、有余量，power-reference 低秩或不安全 | 动作端口/物理实现是主因 | 不训练 B；修动作或换控制目标 |
| 两者都有秩和余量，但局部映射不可预测 | 信息结构是主因 | 改消息/观测；不是换 TD3/SAC |
| 两者通过三门，MARL 仍跨 seed 失败 | 优化、critic 或 credit assignment 是主因 | 才比较 CTDE、counterfactual critic、参数共享 |
| 两者在固定 Kundur 都低余量，但异质/OOD bank 有余量 | benchmark 过于简单/对称是主因 | 把异质与 topology shift 写入研究问题 |
| 强经典控制在全部 bank 都吸干余量 | 论文题目与真实问题错位 | 改写成边界/负结果或确定性控制论文 |

这个实验比“把所有 20 条算法再横向跑一遍”更有信息量，因为它首先回答有没有可学习目标；算法排行榜只能在目标、权限、基线与指标完全一致后才有意义。

## 8. 对尽快完成论文的决策

### 8.1 若必须保留多 VSG MARL 正结果

直接 M/D 是目前唯一接近 train-ready 的动作，但不能复用旧 checkpoint 来声称正确算法证据，也不能只报告旧综合指标。至少需要：修正后的训练实现、四个真实 actor、匹配强 droop/adaptive inertia/mutual damping、同一权限、独立同步与能量指标、多 seed 和 held-out bank。其风险是文献新颖性已被 Yang 等直接占据，而且仓库现有证据预示经典基线可能仍胜出。

### 8.2 若“结束论文”优先于保留正面算法叙事

最快、最诚实的成稿方向是把结论写成**适用边界**：在该四 VSG Kundur benchmark、匹配经典先验与冻结权限下，分布式神经策略没有建立增量；进一步的 model-first gates 显示余量、局部信息、动作安全与模型保真度会在训练前否决若干看似合理的 formulation。这可以形成方法学/负结果论文，但题目不能继续暗示 MARL 已取得性能优势。

### 8.3 当前不建议做的事

- 不做 20 条历史算法的直接总排名：它们的动作对象、指标、基线、代码版本和证据等级不同。
- 不把所有 pretraining STOP 叫作“MARL 训练失败”。
- 不因 M/D 容易训练就认定它是唯一物理动作。
- 不在固定 Kundur 上继续算法优先 sweep，除非上述 rank–headroom–information 三门已经通过。

## 9. Answer to the research questions

**RQ1：除家族 1 外，大部分多智能体训练是否失败？** 不是。真正的训练案例很少；其中 CTDE 塌缩，三边 actor 无经典增量，而更多路线没有训练。

**RQ2：根因是否在数学上？** 有数学机制，但不是一个已证明的“不可能定理”。当前最强证据指向低 residual headroom、局部信息不足、动作可行性和低维有效控制方向；一般 MARL 的非平稳、梯度方差与 credit assignment 是次一级候选。

**RQ3：是否只有调 M/D 才能得到 VSG 多智能体结果？** 不是。M/D 只是当前仓库和直接文献中最成熟、最易训练的接口。非 M/D 的 per-VSG MARL 在学界更稀疏、在仓库中尚未通过训练前物理门。

**RQ4：问题是否在 Kundur 两区域系统？** 部分可能在，但尚未证实。决定性证据应是动作灵敏度有效秩、经典控制后的 oracle headroom、局部条件可辨识性，以及这些量在对称固定 Kundur 与异质/OOD bank 之间的变化。

## References

[1] Qiufan Yang, Linfang Yan, Xia Chen, et al., “A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs,” IEEE Transactions on Power Systems, 2023.

[2] Seokjun Kang, Yoongun Jung, Deokki You, et al., “Enhancing Frequency Stability With Decentralized Adaptive Control Using Multi-Agent Deep Reinforcement Learning of Multi-VSGs,” International Journal of Electrical Power & Energy Systems, 2025.

[3] Dong Chen, Kaian Chen, Zhaojian Li, et al., “PowerNet: Multi-Agent Deep Reinforcement Learning for Scalable Powergrid Control,” IEEE Transactions on Power Systems, 2022.

[4] Daner Hu, Zhenhui Ye, Yuanqi Gao, et al., “Multi-Agent Deep Reinforcement Learning for Voltage Control With Coordinated Active and Reactive Power Optimization,” IEEE Transactions on Smart Grid, 2022.

[5] Oroghene Oboreh-Snapps, Sophia A. Strathman, Jonathan Saelens, et al., “Addressing Reactive Power Sharing in Parallel Inverter Islanded Microgrid Through Deep Reinforcement Learning,” IEEE Applied Power Electronics Conference and Exposition, 2024; and “Simultaneous Frequency Regulation and Active Power Sharing in Islanded Microgrid Using Deep Reinforcement Learning,” IEEE Kansas Power and Energy Conference, 2024.

[6] Ryan Lowe, Yi Wu, Aviv Tamar, et al., “Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments,” Advances in Neural Information Processing Systems, 2017.

[7] Jakub Grudzien Kuba, Muning Wen, Linghui Meng, et al., “Settling the Variance of Multi-Agent Policy Gradients,” Advances in Neural Information Processing Systems, 2021.

[8] Rihab Gorsane, Omayma Mahjoub, Ruan John de Kock, et al., “Towards a Standardised Performance Evaluation Protocol for Cooperative MARL,” Advances in Neural Information Processing Systems, 2022.

[9] Yang Li, Fei Deng, Rong Qi, Hui Lin, “Adaptive Virtual Impedance Regulation Strategy for Reactive and Harmonic Power Sharing Among Paralleled Virtual Synchronous Generators,” International Journal of Electrical Power & Energy Systems, 2022.

[10] Oroghene Oboreh Snapps, Jonathan W. Kimball, Jonathan Saelens, et al., “Advanced Multi-Agent Reinforcement Learning Strategy for Power Regulation in Standalone Microgrids,” in Smart Grids—Innovations for a Sustainable Future, 2025.

[11] Diego Romeres, Florian Dörfler, Francesco Bullo, “Novel Results on Slow Coherency in Consensus and Power Networks,” European Control Conference, 2013.

[12] Fernando Paganini, Enrique Mallada, “Global Analysis of Synchronization Performance for Power Systems: Bridging the Theory-Practice Gap,” IEEE Transactions on Automatic Control, 2020.

## Repository evidence used

- `CLM-0320`: SAC-CTDE convergence failure.
- `CLM-0445`: old RL versus strong droop dual-metric correction.
- `CLM-0495`: recurrent Bellman-target implementation correction.
- `CLM-0610`: shared scalar factorization versus centralized explanation.
- `CLM-0905`: genuine distributed edge actor versus strong classical controller.
- `CLM-0915`: oracle headroom and neighbour-local information failure.
- `CLM-0990`: current direct M/D conditional-headroom stop.
- `CLM-1020`: VSG-owned energy-port safety stop.
- `CLM-1045`: full-order source-model fidelity stop.
