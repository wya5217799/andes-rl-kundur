# MARL 学习余量、算法选择与科研价值审计

**日期：** 2026-07-26  
**对象：** `andes-rl-kundur` 的多 VSG 频率控制主线  
**核心问题：** 当前 MARL 为什么没有稳定增益、还能怎样优化、是否值得作为论文研究问题

## 结论先行

1. **当前主要瓶颈不是 MARL 算法太旧，而是尚未证明强经典控制之上存在可部署的学习余量。**
   已验证的慢速储能有功 droop+PI 与简单 3 秒共同惯量脉冲已经构成很强的经典基线；
   快慢两层的收益是相加覆盖，不是需要复杂协调才能获得的“协同效应”。
2. **“用 MARL 在线调多台 VSG 的惯量/阻尼”是旧问题。** 2022 年的 TPWRS
   工作已经把并联 VSG 参数协调写成 Markov game 并使用多智能体 SAC；2024 年又有
   MADDPG 在线调整 VSG 惯量与阻尼。2026 年已经出现 MARL-DDPG 联合协调虚拟惯量
   与慢速负荷频率控制的直接近邻，以及拓扑感知 GNN-RL 虚拟惯量分配和鲁棒
   sim-to-real DRL。
3. **只把 SAC/TD3 换成 MAPPO、FACMAC 或新版 MADDPG，是旧问题换求解器，科研价值低。**
   算法可以改善收敛或信用分配，却不能制造不存在的物理控制余量。
4. **仍可能有意义的新问题**是：在能量可行、快慢执行器分离和共同/差分模态硬解耦
   的前提下，一个拓扑等变、受硬约束的微小 residual policy，能否在完全未见的
   拓扑、VSG 数量和扰动上，稳定打赢强经典控制，并且不增加失败、尾部风险和动作抖动。
5. **R277 是是否允许训练的最后一道低成本门。** 它让一个能看完整结果的 oracle
   在每个场景中挑选六个零和差分惯量方向，能力强于任何可部署策略。只有它在同步损失
   和前三秒区域间 IAE 两项上都取得至少 2% 的、置信区间明确的改善，而且全部安全/恢复
   guard 通过，才说明值得训练 MARL。

## 1. 当前实验事实

| 证据 | 客观结果 | 对 MARL 的含义 |
|---|---|---|
| R268 corrected TD3 residual | 16/16 完成且动作/安全 guard 通过，但 IAE 恶化 0.094756%，同步损失恶化 0.076495%，判定 NO-GO | 旧 checkpoint 或复杂网络不能替代正确目标与学习余量 |
| R274 slow droop+PI/storage | 24/24 完成；IAE 降 58.629118%，最后窗口共同频差降 77.290429%，全部物理约束通过 | 共同频率恢复需要真实有功/能量通道，不能靠调 M/D 解决 |
| R275 simple fast inertia pulse | RoCoF 降 28.373628%，峰值降 11.077230%，同步损失降 4.290160%，前三秒区域间 IAE 降 9.914721% | 简单透明规则已经覆盖大部分短时收益，成为 MARL 必须打赢的基线 |
| R276 four-arm factorial | 96/96 有效；六项指标均无至少 2% 的非加性协同，判定 ADDITIVE-ONLY | 快慢层都应保留，但没有证据表明它们必须由 MARL 联合协调 |
| R277 optimistic oracle | 进行中；协议固定为 24 场景 × 6 个零和方向，共 144 条新轨迹 | 这是差分惯量学习价值的上界，不是训练或论文正结果 |

因此，当前最准确的论文故事不是“HAWE/MARL 产生了巨大提升”，而是：

> 先按物理作用把共同频率恢复与差分同步、慢有功与快惯量分开；验证简单经典层的
> 独立作用；只让学习器处理经典控制无法解释且确实存在的微小差分残差。

仓库现有 `SACAgentCTDE` 是四个独立 actor 配一个集中式 double-Q critic；`--ctde`
只共享 critic，并没有绑定 actor 参数，也没有零和差分投影。因此它可作为新方法的
实现基础，但直接打开现有开关并不能得到下文建议的 projected shared-actor MASAC。

## 2. 当前 MARL 的主要问题

### 2.1 物理权限和目标错位

M/D 能改变 RoCoF、峰值、阻尼和同步轨迹，却没有持续补充能量、把共同频率恢复到
额定值的权限。早期把共同频率恢复失败归咎于算法，实际是 action authority 不足。
R274 已用独立储能有功通道验证了这一点。

### 2.2 没有先证明“需要学习”

R275 的固定 3 秒共同惯量脉冲已经很强；R276 又证明快慢收益主要是加法。若连知道
完整未来结果的 R277 oracle 都不能找到稳定差分增益，任何 MARL 训练都只会在随机
噪声中挑幸运种子。

### 2.3 信用分配与非平稳性

四台 VSG 的动作共同影响全局频率、区域间模态和同步损失。独立 actor 同时更新时，
每个 agent 看到的环境都在变化；共享团队 reward 又难以说明是哪台 VSG 的动作产生
收益。这会造成互相抵消、动作饱和或退化成固定空间模式。

### 2.4 部分可观测性

R277 oracle 能看完整轨迹后再选动作，而真实策略只能根据扰动早期的局部频率、RoCoF、
功率和邻居信息行动。即使 oracle 有收益，如果“该选哪个零和方向”无法由动作时刻的
观测预测，MARL 仍学不到。必须在正式 RL 前做因果 observability/label-predictability
审计。

### 2.5 种子敏感和昂贵样本

真实 ANDES DAE 轨迹计算慢，神经网络初始化、探索噪声和 replay 顺序都会放大方差。
早期 HAWE 记录主要保留了一个幸运 seed，不能证明加权本身有效。评价必须用多 seed
分布、预注册阈值和一次性 sealed bank，不能报告 best seed。

### 2.6 约束与稳定性

把功率、SOC、能量、M/D 范围、slew 和 converter capability 写成 reward penalty
不能保证约束。动作应先经过解析投影/安全层，训练还需报告 constraint activation、
失败和尾部风险；更高层级主张还需要稳定域或第二仿真器/HIL 证据。

### 2.7 对称性和拓扑没有被利用

四台同类 VSG 不应各自学习一套毫无联系的网络。独立 actor 浪费样本并容易学到
agent-ID 偏见。真正面向拓扑变化的方法应共享参数，并用图邻域表示电气耦合，而不是
在固定四机拓扑上堆更多 LSTM/Transformer。

## 3. 最新文献给出的边界

### 3.1 已经是旧问题的部分

- Yang 等在 TPWRS 中已经把并联 VSG 的惯量/下垂参数协调写成 Markov game，
  使用局部及相邻 VSG 信息和多智能体 SAC。因此“并联 VSG + MARL + 动态 M/D”
  不能再作为新问题。[IEEE TPWRS, DOI 10.1109/TPWRS.2022.3221439](https://ieeexplore.ieee.org/document/9946410/)
- Zhang 等使用 CTDE/MADDPG，根据频差和角频率变化率在线调节 \(J,D\)。因此
  “用 MADDPG 代替 SAC 调惯量阻尼”也已有直接工作。
  [Energies 2024](https://www.mdpi.com/1996-1073/17/24/6421)
- 2026 年的 Ali 等已经使用 CTDE MARL-DDPG 同时优化 virtual inertia control
  与 load-frequency control，并声称快慢层协调收益。因此“MARL 联合快惯量与慢恢复”
  已有非常直接的近邻。
  [Computers & Electrical Engineering 2026](https://www.sciencedirect.com/science/article/abs/pii/S0045790626002533)
- 2026 年已有 spectral sensitivity + spatio-temporal GNN + RL 的实时虚拟惯量
  分配。因此“第一次用 GNN-RL 做拓扑感知惯量分配”也不能主张。
  [Sustainable Energy, Grids and Networks 2026](https://www.sciencedirect.com/science/article/abs/pii/S2352467726000500)
- 2026 年 TPWRS 工作已经把物理不确定集和 robust Bellman operator 用于 VSG
  频率控制的 sim-to-real gap。因此单独增加 domain randomization/robust RL
  也不够成为核心创新。
  [IEEE TPWRS 2026, DOI 10.1109/TPWRS.2026.3658809](https://doi.org/10.1109/TPWRS.2026.3658809)

### 3.2 可借鉴但不能照搬的 MARL 方法

| 方法 | 优点 | 对本项目的适配判断 |
|---|---|---|
| MAPPO | 简单、强基线；集中 critic 可缓解非平稳性 | on-policy；真实 ANDES 样本昂贵，不宜作为第一训练器，但应作为后续算法对照 |
| MASAC / CTDE-SAC | off-policy replay、连续动作、熵探索，项目已有 CTDE-SAC 基础 | **若 R277 阳性，最低实现成本的首选**；需要改成真正共享 actor、差分投影和正确 reward |
| FACMAC | 连续合作控制；factored centralized critic 与 joint policy gradient 针对信用分配 | 适合作为协调型对照；四 agent 时复杂度收益未必大，不应先于结构修正 |
| HAPPO/HATRPO | 顺序更新、异构 agent 的单调改进思路 | 当前 VSG 高度同质，顺序异构更新不是首要矛盾 |
| constrained MARL | 把 reward 与 constraint cost 分开，使用 safety critic/拉格朗日变量 | 可处理难以解析的长期约束；已有明确解析边界的 M/D、功率和 SOC 应优先硬投影 |

MAPPO 的原始研究表明，实现细节、critic 输入、value normalization、clip 和数据复用
都会显著影响结果，不能把算法名字当作保证。
[MAPPO paper](https://arxiv.org/abs/2103.01955)

FACMAC 用 factored centralized critic 和 joint policy gradient 处理合作连续动作，
比逐 agent 梯度更直接地处理联合动作。
[NeurIPS 2021](https://papers.neurips.cc/paper_files/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract.html)

安全 MARL 的近期工作把电网控制写成 constrained Markov game，并用独立 cost
估计与自适应拉格朗日乘子处理长期约束，说明单一 reward penalty 不够可靠。
[IJCAI 2024](https://arxiv.org/html/2405.08443v2)

网络感知 MARL 可以让 critic 只接收 \(\kappa\)-hop 邻域，降低输入和通信规模，并已
在 114-DG 系统上与 MASAC/MATD3 结合。但这主要解决大规模拓扑问题，不会自动改善
当前固定四机任务。
[Network-aware MARL](https://arxiv.org/html/2312.04371v1)

一项 2026 年两区域 microgrid-cluster 研究在其特定模型上直接比较 DDPG、TD3 和
SAC，报告 SAC 的训练最稳定、最终 reward 最高。该结果不能当作跨环境的算法排名，
但与本项目优先复用 off-policy SAC 而不是重新开发 on-policy 方法的工程选择一致。
[Applied Sciences 2026](https://www.mdpi.com/2076-3417/16/13/6685)

## 4. 若 R277 阳性，推荐的最小可发表方法

### 4.1 控制结构

\[
u = u_{\text{slow classical}} + u_{\text{fast common classical}}
    + P_{\perp}u_{\theta},
\qquad
P_{\perp}=I-\frac{1}{N}\mathbf{1}\mathbf{1}^{\mathsf T}.
\]

- 慢层：保留已验证的 droop+PI/storage，负责共同频率恢复与能量；
- 快速共同模态：保留 R275 的透明 3 秒惯量脉冲，负责 RoCoF/峰值；
- 学习器：只输出很小的差分惯量 residual，经过零和投影后不改变 fleet-mean
  inertia；D 暂时固定；
- 所有动作再经过 M/D 范围、幅值、slew、功率、SOC、能量与 capability 硬限制。

这属于 residual control：把已能可靠解决的部分交给经典控制，只学习剩余部分。
Residual RL 的基本思想早已有先例，因此创新必须来自电力模态分解、物理合同和
跨拓扑证据，而不是 “residual” 这个名字。
[Residual RL](https://arxiv.org/abs/1812.03201)

### 4.2 策略与 critic

- 使用一套 **parameter-shared actor** 服务所有同类 VSG；
- actor 输入为本地频差、RoCoF、功率、剩余 headroom/SOC、相对邻居特征以及
  disturbance phase；不要先上 LSTM，先用短历史堆叠确认因果可观测；
- centralized critic 在训练时看到全局物理状态、所有 projected joint actions
  和拓扑；执行时 actor 只用允许的局部/邻域信息；
- 固定拓扑可先用小型 MLP；只有进入多拓扑训练时才换 message-passing/GNN；
- 若必须严格分布式地保证零和，可把 residual 表示成邻边上的反对称 flow，再在
  每个节点汇总，而不是依赖一个全局 mean-subtraction 通信器。

### 4.3 推荐算法顺序

1. **先做可观测性筛选，不训练 RL。** 用 R277 oracle 的候选标签，检验仅凭动作时刻
   可用信息能否预测正确差分方向；与 majority/fixed-direction 基线比较。如果接近
   随机，说明是 information gap，不是算法 gap。
2. **Projected parameter-sharing MASAC**：复用项目现有 CTDE-SAC 与 replay
   基础，加入共享 actor、零和/安全投影和物理 reward。这是最省样本、最少新代码的
   第一选择。
3. **FACMAC 作为信用分配对照**：只有 MASAC 明显卡在 joint credit assignment
   时再实现。
4. **MAPPO 作为简单稳健性对照**：不作为首个昂贵训练器；若 off-policy 结果对 replay
   或 critic 过拟合，再用 MAPPO 复核。
5. 每个算法至少 5 个训练 seed；先 development bank 选一次协议，再在 sealed bank
   一次评估。不得使用 HAWE 或 best-seed 选模。

### 4.4 reward 与 gate

训练目标只对齐学习器真正负责的差分量：

\[
r_t =
-w_s\lVert P_{\perp}\Delta f_t\rVert_2^2
-w_a |f_{\text{area1},t}-f_{\text{area2},t}|
-w_u\lVert u^\perp_t\rVert_2^2
-w_{\Delta u}\lVert u^\perp_t-u^\perp_{t-1}\rVert_2^2.
\]

共同频率、RoCoF、峰值、恢复和 storage 指标不是靠不断改 reward 权重“调出来”，
而是作为不可越过的评估 guard。正式成功必须同时满足：

- 相对 R274+R275 经典基线，两项差分 primary endpoint 都至少改善 2%，95% 上界
  小于 0；
- common/restoration/tail 不恶化到预注册边界；
- 完成率、动作幅值/速率/TV、功率、SOC、能量和 capability 全部通过；
- 多 seed 中位数有效，而不是单个 seed 有效；
- 最终还要在完全未参与训练的拓扑/VSG 数量上保留收益。

## 5. R277 的决策树

### LEARNING-GAP-PRESENT

两项差分指标都过门，且全部 guard 通过：

1. 冻结 R277 揭示的动作空间与指标，不再调 oracle；
2. 做因果可观测性分类测试；
3. 可预测时实现 projected shared-actor MASAC；
4. 用 FACMAC/MAPPO 作为有限对照，而不是大规模算法扫榜；
5. 固定拓扑通过后立刻转向多系统、held-out topology 和约束/稳定性。

### LEARNING-GAP-PARTIAL

只有一项指标过门：

- 暂不训练；
- 检查动作基底、测量信息或物理机制为什么只能影响一个差分端点；
- 只有新的前瞻机制实验同时解决两项，才重新开放训练。

### NO-RL-NEEDED

乐观 oracle 仍不能同时过门：

- 关闭固定 Kundur 上的 MARL 提分路线；
- 不再换算法、调 reward、堆网络或筛幸运 seed；
- 论文保留“解耦 + 强经典控制 + 严格消融”的事实；
- 若必须保留 MARL，只能作为负面对照，不得声称它是收益来源；
- 后续研究转向 topology shift、通信限制、SOC 饱和、连续扰动或不同 actuator，
  这些场景必须先各自证明 classical gap。

### INVALID

若轨迹、hash、completion 或物理合同失败，只修完整性并按原 seal resume；不得根据
已看见结果改变候选库、幅值或门槛。

## 6. 科研价值判断

### 当前宽泛问题

> “用 MARL 动态调多台 VSG 的惯量和阻尼，以改善频率和振荡。”

这是**有工程意义但学术上已经较旧**的问题。若只在固定 Kundur 上更换算法并报告
更好均值，属于旧问题换方法，创新弱，也极易再次把随机种子当贡献。

### 建议冻结的新问题

> 在能量可行的快慢执行器架构中，将共同频率与差分同步模态显式分离后，受硬物理约束、
> 参数共享且拓扑等变的差分 residual policy，能否在未见拓扑、未见 VSG 数量和未见
> 扰动下，稳定提供强经典控制无法达到的收益；该收益在什么可观测性、通信和能量边界内
> 存在？

这是**有意义、可证伪的科研问题**，因为它不预设 AI 一定有效，并同时回答：

- 学习到底补了哪个物理缺口；
- 为什么不是经典控制、随机 seed 或 reward 偏差；
- 哪些约束和拓扑变化下增益仍存在；
- 何时应明确判定“不需要 MARL”。

不过，这仍不是天然的 TPWRS 贡献。固定四机正结果最多支持较窄的方法论文；若要达到
更高层级，需要多系统/未见拓扑、稳定或安全论证、第二仿真器/EMT/RTDS/HIL，以及
可复现的多 seed 与尾部风险证据。

## 7. 对现有 digest/论文主线的处理

- “Decoupling-Oriented” 可以保留，而且比 HAWE 更符合当前证据；
- 解耦应明确写成 **共同/差分模态解耦 + 快惯量/慢有功执行器解耦**；
- HAWE 降为历史负面消融，不再作为主方法；
- “with MARL” 只能在 R277 阳性、可观测性通过且多 seed residual 真正打赢经典基线
  后写成贡献；
- 若 R277 判定 NO-RL-NEEDED，正文不能继续暗示 MARL 带来提升。digest 标题是否暂时
  不改是投稿策略问题，但最终论文的标题、摘要和结论必须与证据一致。

## 参考原始文献

1. Q. Yang et al., “A Distributed Dynamic Inertia-Droop Control Strategy Based on
   Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs,”
   *IEEE Transactions on Power Systems*, 2023.
   https://doi.org/10.1109/TPWRS.2022.3221439
2. D. Zhang et al., “Adaptive Control of VSG Inertia Damping Based on MADDPG,”
   *Energies*, 2024. https://doi.org/10.3390/en17246421
3. H. Ali et al., “Intelligent multi-agent reinforcement learning type-2 fuzzy
   control for coordinated virtual inertia and load frequency regulation in
   interconnected microgrids,” *Computers & Electrical Engineering*, 2026.
   https://doi.org/10.1016/j.compeleceng.2026.111181
4. “Spectral sensitivity and physics informed GNN-RL for real time power grid
   stability,” *Sustainable Energy, Grids and Networks*, 2026.
   https://doi.org/10.1016/j.segan.2026.102168
5. L. Zeng and M. Sun, “Bridge the Sim-to-Real Gap in Virtual Synchronous
   Generator-Based Frequency Control With Robust Deep Reinforcement Learning,”
   *IEEE Transactions on Power Systems*, 2026.
   https://doi.org/10.1109/TPWRS.2026.3658809
6. C. Yu et al., “The Surprising Effectiveness of PPO in Cooperative,
   Multi-Agent Games,” 2021/2022. https://arxiv.org/abs/2103.01955
7. B. Peng et al., “FACMAC: Factored Multi-Agent Centralised Policy Gradients,”
   *NeurIPS*, 2021.
   https://papers.neurips.cc/paper_files/paper/2021/hash/65b9eea6e1cc6bb9f0cd2a47751a186f-Abstract.html
8. Y. Qu, C. Ma, and J. Wu, “Safety Constrained Multi-Agent Reinforcement
   Learning for Active Voltage Control,” *IJCAI*, 2024.
   https://arxiv.org/html/2405.08443v2
9. H. Xu, J. Zheng, and G. Qu, “A Scalable Network-Aware Multi-Agent
   Reinforcement Learning Framework for Decentralized Inverter-based Voltage
   Control,” 2023. https://arxiv.org/html/2312.04371v1
10. T. Johannink et al., “Residual Reinforcement Learning for Robot Control,”
    2018. https://arxiv.org/abs/1812.03201
11. L. I. Minchala-Avila and M. Tostado-Véliz, “Enhancing Virtual Inertia
    Control in Microgrid Clusters: A Novel Frequency Response Model Based on
    Deep Reinforcement Learning,” *Applied Sciences*, 2026.
    https://doi.org/10.3390/app16136685
