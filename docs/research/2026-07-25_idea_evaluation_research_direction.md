# ANDES 多 VSG 项目：下一研究方向评估

日期：2026-07-25

评估对象不是“继续换一种强化学习算法”，也不是把 R264 的手工 gate
直接包装成方法，而是从现有代码、250 轮实验记录和最新文献中选择一个新的、
可证伪的论文主命题。

### 1. First impression

- Paper type: **Novel Method**，同时包含一个受控的 **New Setting**
  （整张未见网络拓扑上的多 VSG 分散控制）。
- One-sentence story: **以调优 droop 为稳定先验，训练一个参数共享、模态感知、
  有界且受速率约束的图残差策略，在完全未见的 VSG 网络上联合调节惯量与阻尼，
  同时改善公共频率恢复和 VSG 间同步，而不恶化尾部风险与动作可实现性。**

建议题目：

> **Mode-Decomposed Rate-Safe Graph Residual Control for Distributed
> Multi-VSGs under Unseen Network Topologies**

中文可称：

> **面向未见网络拓扑的模态分解、速率安全共享图残差控制**

#### 为什么选择这个方向

现有证据先排除了三个诱人的错误方向：

| 候选 | 项目证据 | 处理 |
|---|---|---|
| 固定 Kundur 上继续更换 SAC/TD3/RNN/Transformer | R57–R82 共 91 个算法、超参数和架构试验均未超过 0.391 基线；Transformer 为 0.010，双层 LSTM 为 0.161（[CLM-0144](../../memory/claims/CLM-0144.md)） | **停止**，只能作为基线或故障消融 |
| 把现有手工 mode-ratio gate 当论文方法 | 新封存 bank 上 IAE 均值改善 4.36%、同步损失均值改善 1.86%，但动作 TV 均值增加 236.67%、TV 尾部增加 448.00%（[CLM-0525](../../memory/claims/CLM-0525.md)） | **数据已否定当前版本**，不能作为主方法 |
| 只写“GNN-RL 调虚拟惯量” | 2026 年已出现谱灵敏度、physics-informed ST-GNN、RL、投影与拓扑变化的一体化工作 | **新颖性不足**，必须换成多 VSG 联合 \(H,D\)、模态分解、分散执行和整图 OOD 的窄命题 |
| 模态感知、速率安全的共享图残差 | 项目已有 residual seam、CTDE 雏形、物理端点、封存评测；但 graph policy 与多系统环境尚未实现 | **选中，但须先做杀伤性 vertical slice** |

#### 明确、可证伪的研究目标

在完全未参与训练、调参和模型选择的网络拓扑上，与：

1. 调优 droop；
2. 参数量和交互预算匹配的非图共享 MLP residual；
3. 固定拓扑 CTDE/RL；

进行配对比较。只有同时满足下列条件，才接受主命题：

- 相对三者中的最强基线，physical VSG-mean IAE 均值至少下降 5%，且分层配对
  bootstrap 95% 区间上界低于 0；
- normalized synchronization loss 均值至少下降 3%，且 95% 区间上界低于 0；
- worst-bus peak 与 sampled RoCoF 的 CVaR90 不恶化超过 5%；
- action-TV CVaR90 不恶化超过 25%，无 \(H,D\) 值域、速率和仿真完成性违规；
- 图策略必须在整张未见图上优于 size-matched non-graph policy；否则“拓扑泛化”
  贡献被否定。

阈值是建议的预注册版本，不是根据结果追出来的目标。最终数值应在打开任何
held-out graph 之前冻结。

### 2. Fatal-flaws audit (early gate)

| # | Flaw | Severity | Defense |
|---|---|---|---|
| 1 | **F1 新颖性碰撞**：如果论文写成“physics-informed GNN-RL for virtual inertia”，它与 Eshun 等 2026 的工作高度重合；单纯加入图网络、谱特征或安全投影不能构成新方法 | **MAJOR** | 把唯一主命题收窄为“多 VSG 联合 \(H,D\) 的公共/差分模态残差 + 分散共享 actor + 动作速率可实现性 + 整图 OOD”。直接把 Eshun2026 纳入最近基线或差异消融，不宣称首次 GNN-RL |
| 2 | **F6 当前平台不能验证核心 claim**：环境固定四台 VSG、固定两邻居观测槽和固定四节点通信环；仓库中没有可训练的多系统 graph suite，因此现在不能声称 topology generalisation | **MAJOR** | 先做最小 vertical slice：可变 \(N\) graph contract、两类训练图、一张完全封存的测试图、共享无记忆 actor、matched MLP baseline。若不能在 8–12 周内得到正向整图结果，停止 graph thesis，转 benchmark/audit 论文 |

未发现选中方向的 CRITICAL flaw。需要特别区分：

- **现有 raw gate 作为主方法**已经被自身数据否定，若继续以它为核心，结论必须是
  Reject and Pivot；
- **训练内生的 bounded graph residual**尚未实现和测试，属于未证实机制，不等于
  已被 raw gate 的失败否定。

#### 真实检索得到的五篇最近工作

| 最近工作 | 已覆盖的轴 | 仍可保留的差异轴 |
|---|---|---|
| Yang, Yan, Chen, Chen, Wen, 2023, “A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs” ([DOI](https://doi.org/10.1109/TPWRS.2022.3221439)) | 多 VSG、动态惯量/阻尼、分布式 SAC、邻居信息 | 固定系统；不是共享可变图策略；没有整图 OOD 和显式动作速率安全层 |
| Oboreh-Snapps et al., 2024, “Virtual Synchronous Generator Control Using Twin Delayed Deep Deterministic Policy Gradient Method” ([DOI](https://doi.org/10.1109/TEC.2023.3309955)) | TD3 自适应虚拟惯量/阻尼，并有实时仿真验证 | 不是多 VSG 整图迁移问题；不是公共/差分模态的共享 residual |
| Shuai, She, Wang, Li, 2025, “Safe Reinforcement Learning for Grid-forming Inverter Based Frequency Regulation with Stability Guarantee” ([期刊页](https://www.mpce.info/mpce/home), [DOI](https://doi.org/10.35833/MPCE.2023.000882)) | Lyapunov/ROA 意义下的安全 RL、模型与参数不确定性 | 侧重单 GFM/VSG 的安全控制；不处理多 VSG 的拓扑共享和模态协调 |
| Kang, Jung, You, Jang, 2025, “Enhancing Frequency Stability with Decentralized Adaptive Control Using Multi-Agent Deep Reinforcement Learning of Multi-VSGs” ([论文页](https://www.sciencedirect.com/science/article/pii/S0142061525009226), [DOI](https://doi.org/10.1016/j.ijepes.2025.111374)) | 多 VSG、分散 PPO、共享奖励、PSCAD 场景验证 | 仍以固定测试系统为主；没有整张 held-out graph、droop residual 和速率安全主命题 |
| Eshun, Fatemi, Fattahi, 2026, “Spectral Sensitivity and Physics Informed GNN-RL for Real Time Power Grid Stability” ([论文页](https://www.sciencedirect.com/science/article/pii/S2352467726000500), [DOI](https://doi.org/10.1016/j.segan.2026.102168)) | 谱灵敏度、ST-GNN、RL、虚拟惯量分配、投影、拓扑变化 | **最接近**；其对象是更广义的电网级预测与资源分配。可保留的窄差异是：多 VSG 亚秒级联合 \(H,D\)、局部通信下分散执行、公共/差分同步模态、动作速率可实现性、整图 zero-shot/few-shot |

结论不是“没有人做过”，而是：

> **宽版本已经拥挤；只有窄版本仍值得做。**

### 3. Lifecycle and capability match

| Aspect | User's input | Assessment |
|---|---|---|
| Idea category | 基于物理先验的新控制结构、图共享策略、OOD 实验 | **Innovative Technique**，附带 Frontier Exploration |
| Lifecycle | 项目当前仍在 P0 evidence repair，graph 和 safety 尚未落地 | TPWRS 完整包约 **12–18 个月**；收窄的 ANDES 多拓扑论文约 **6–9 个月** |
| Weekly effective hours | 用户未提供 | 不能据此标 Green；以上周期按 **每周 15–25 个有效科研小时**规划，若低于 10 小时应缩成 benchmark/audit |
| Applied implementation | 仓库已显示 Python、PyTorch、ANDES、训练和可复现实验工程能力 | **Green** |
| Control/stability theory | 有物理指标和机理分析，但未见可复用的多系统安全域、Lyapunov 或鲁棒稳定证明 | **Yellow**；需要导师/合作者或把第一篇限制为 stability-screened empirical guarantee |
| Multi-system graph engineering | 当前核心路径是固定 \(N=4\)、固定观测槽、固定通信图 | **Red → Yellow**，必须先过 vertical slice |
| Fit | 方法有价值，但当前能力与最终命题之间仍有明显工程和理论缺口 | **Yellow** |

生命周期判断依据是近年相关论文已经从“单一 RL 算法调参”推进到 safe RL、
PSCAD/RTDS 验证和 topology-aware GNN。该判断已结合最新文献，但仍应由用户和导师
按本课题组实际工时、理论支持与外部仿真资源复核。

### 4. Five-dimension radar

| Dimension | Score 1-10 | Evidence | Lift suggestion |
|---|---:|---|---|
| Higher | **7** | **部分实测、核心方法未确认。** R265 说明状态依赖组合能把 IAE 均值降 4.36%、同步损失均值降 1.86%，但 raw gate 因 TV 失败，不能把这些收益归因给拟议的 learned graph residual | 用训练内生 residual、fixed blend、raw gate、matched MLP、graph residual 做因果消融；以两个物理 co-primary endpoint 而非 `geo` 定胜负 |
| Faster | **5** | **无充分依据。** 神经策略可能推理很快，但仓库没有端到端 inference latency、控制周期余量或与 MPC/优化器的计时对比 | 不把速度写成 headline；若要升分，报告 CPU 单步时延、P99、随 VSG 数的 scaling 和安全投影开销 |
| Stronger | **8** | **机制型，尚未由新方法数据确认。** droop fallback、有界 residual、速率限制、sealed tails、通信故障和整图 OOD 都直接针对现有 failure modes；仓库已有物理端点与 CVaR/失败率基础 | 决定性实验是“整图 holdout + 低惯量/延迟/掉线/线路退出 + CVaR + failure interval”，并要求所有约束在推理时而非仅 reward 中满足 |
| Cheaper | **6** | **机制型，尚未确认。** 参数共享图策略理论上可减少每个网络重新训练一个 actor 的成本，但多系统训练本身可能比当前固定 Kundur 昂贵 | 报告达到同等性能所需的 ANDES interactions、GPU/CPU 小时和 few-shot 样本；否则不要宣称 cheaper |
| Broader | **8** | **机制型，尚未由数据确认。** 可变 \(N\) 与显式 node/edge 表示允许跨 VSG 数、线路和通信图迁移，这正是当前固定四节点代码不能做的事 | 必须封存整张未见图，并用 size-matched non-graph policy 排除“只是参数共享或训练数据更多”的解释 |

论文应重点强调：

1. **Stronger**：OOD、尾部风险、掉线/延迟与动作可实现性；
2. **Broader**：整图而不是同一 Kundur 上的负荷扰动泛化；
3. **Higher**：公共频率恢复与差分同步两个物理目标同时改善。

不要把 Faster 当主要贡献。Strong/Broader 的 8 分均为机制评分，只有通过下面的
decisive experiment 才能保留。

#### 决定性 vertical-slice 实验

先不使用 LSTM，不做大规模算法搜索，只实现一个共享、无记忆 message-passing
actor。以完全相同的训练交互量和参数量比较：

1. tuned droop；
2. bounded residual MLP；
3. graph residual，不输入公共/差分模态特征；
4. mode-decomposed graph residual；
5. 第 4 项加固定的值域/速率投影。

训练只看两类图；第三张图在架构、损失、阈值和 checkpoint 选择全部冻结后打开。
建议 pilot 用 3 个独立训练 seed、每个 graph-scenario bank 至少 40 个场景；正式结果
扩展到至少 5 个 seed，并对 graph、seed、scenario 做分层 bootstrap。

**Kill gate**：

- graph residual 若不能在未见图上同时优于 matched MLP 的 IAE 与同步损失，
  停止 topology thesis；
- residual 若不能优于 tuned droop 且守住 tail/action guards，停止 RL thesis；
- mode decomposition 若不能优于同容量 graph residual，保留图 residual 但删除
  mode-aware 新颖性；
- 任一结论若只在 `geo` 上成立而物理端点不成立，判负。

### 5. Paradigm-shift probe

| Probe | Yes or No | Rationale |
|---|---|---|
| First Principles | **Yes** | 挑战“每个固定系统单独训练一个端到端策略、用单一 reward 排名”的默认假设；把控制拆成 droop prior、公共模态恢复和差分模态同步 |
| Elephant in the Room | **Yes** | adaptive VSG RL 常回避整图泛化、动作参数能否快速实现、尾部失败率和结果对 seed/metric 的脆弱性；本项目已经用负结果直接观察到这些问题 |
| Technology Cycle | **Partial / No** | GNN、RL 和 ANDES 都已成熟，不能靠“技术刚出现”支撑 novelty；真正机会来自把 graph representation 与严格封存评测、残差控制组合到正确问题上 |
| Hamming's Rule | **Yes, conditional** | 若同一个分散控制器能在未见 VSG 网络上安全协调 \(H,D\)，会显著提高学习控制的可移植性；若只能在 Kundur 上多拿几分，则不会改变领域 |

Disruptive potential: **possible（3 个正向 probe，但仍待整图实验）**。

它的范式潜力来自“从 per-case policy tuning 转向可迁移、可审计的 residual controller”，
而不是来自“用了 GNN”。值得继续按 first-principles 和 elephant-in-the-room 的方式
打磨，但不应在尚无多图证据时使用 “general” 或 “safe” 的标题。

### 6. Feasibility

| Risk | Level | Mitigation |
|---|---|---|
| Compute | **Medium** | 当前硬件为 16C/32T Windows 工作站、RTX 5070 Laptop 8 GB；ANDES 规定单 session、最多 3 个 WSL Python 进程。小型 message-passing actor 可装入显存，瓶颈更可能是串行 TDS。先用少量 graph vertical slice 和 probe-first kill gate，正式 study 再估算交互预算 |
| Data | **Medium–High** | 不需要私有实测数据，但仓库当前只有活动 Kundur 场景；必须构造并审计多个 ANDES 动态系统、VSG 挂接、扰动语义和通信图，防止同构或参数泄漏 | 先定义 graph split protocol，再建 case；整图 hash，训练/开发/测试系统严格分离；记录 VSG 数、线路、运行点、故障和通信图 |
| Engineering | **High** | 当前环境和 CTDE 都假定固定 \(N\) 和拼接维度；graph actor、graph critic、joint replay、mask/batch、case adapter 都是实质重构 | 保留 V4 bit-identical 路径，新建 graph contract；先无记忆共享 actor，再考虑 recurrence；每个新 seam 都用合成 graph unit test 和单步 ANDES parity test |
| Timeline | **High** | 同时做 residual、GNN、多系统、安全证明、外部仿真和论文会造成 scope explosion | 第一篇只承担“mode-decomposed rate-safe graph residual + whole-graph OOD”；正式非线性稳定证明与 HIL/RTDS 作为后续 gate，不与 graph vertical slice 同时开工 |

#### 哪些核心代码能复用

1. [`evaluation/hybrid.py`](../../src/andes_rl_kundur/evaluation/hybrid.py)
   已定义 droop、blend 和 state-dependent controller seam，可演化成
   `prior + bounded residual + rate projection + fallback`；但 raw gate 不能原样复用为主方法。
2. [`evaluation/physical_endpoints.py`](../../src/andes_rl_kundur/evaluation/physical_endpoints.py)
   已有 physical IAE、同步损失、RoCoF、settling 和 action-TV，基本覆盖主 endpoint。
3. [`evaluation/sealed_bank.py`](../../src/andes_rl_kundur/evaluation/sealed_bank.py)
   已有 bank hash、无 anchor 检查、paired bootstrap、failure interval、worst/CVaR，
   是未来 whole-graph sealed evaluation 的直接基础。
4. [`agents/sac_ctde.py`](../../src/andes_rl_kundur/agents/sac_ctde.py)
   已证明项目能支持 centralized training / decentralized execution，但当前 critic 通过
   `obs_dim * N + action_dim * N` 固定拼接，只能作为重构起点。

#### 哪些核心代码必须重构

1. [`env/andes/andes_vsg_env_v4.py`](../../src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py)
   固定 `N_AGENTS=4`、VSG buses 和四节点 ring；应保留为 anchor，不在原类上硬塞可变图。
2. [`env/andes/base_env.py`](../../src/andes_rl_kundur/env/andes/base_env.py)
   观测是 7 维固定 slot，每台只容纳两个邻居。新路径应输出 node features、
   electrical edges、communication edges、edge attributes 和 masks。
3. [`scripts/train.py`](../../scripts/train.py)
   当前主要构建 \(N\) 个独立 actor；新路径需要一个共享 graph actor、joint graph
   transition buffer 和 graph critic/coordinator。
4. 现有 recurrent baseline 受历史 target-alignment defect 与 hidden-state drift 影响。
   [`agents/td3_lstm.py`](../../src/andes_rl_kundur/agents/td3_lstm.py) 已修 target history，
   但新方向第一版应使用无记忆 actor，避免把 recurrence correctness 与 graph claim
   混成一个实验。

#### 推荐执行顺序

| 阶段 | 目标 | 时间估计（15–25 有效小时/周） | 停止条件 |
|---|---|---:|---|
| 0 | 完成当前 Q-0029：只测一个有独立物理依据的 alpha slew；成功也只作为 prior/baseline | 2–4 周 | 新 sealed bank 判定后关闭或保留 hand-gate family |
| 1 | 在固定 Kundur 上训练 corrected bounded residual，证明不是 raw blending artifact | 6–10 周 | 不能同时守住物理收益和 action guards 就停止 RL residual |
| 2 | 建 variable-\(N\) graph contract、共享 actor、matched MLP 和一张 sealed whole graph | 8–12 周 | graph 不胜 matched MLP 就停止 topology claim |
| 3 | 扩展多图、多 seed、通信/线路/低惯量 stress 和分层统计 | 8–12 周 | tail/failure 或 OOD 结论不稳则降级论文 |
| 4 | 加 stability-screened projection；有资源时做第二仿真器或 HIL/RTDS 复核 | 3–6 个月 | 无独立高保真证据时不投 TPWRS headline |

当前 [`memory/RESEARCH_PROGRAM.md`](../../memory/RESEARCH_PROGRAM.md) 的阶段顺序是
P0 evidence repair → P1 residual → P2 topology → P3 safety → P4 high fidelity。
这与本次评价一致。需要修正的不是总方向，而是**论文叙事和范围**：不要提前把
五个阶段包装成一个已经成立的方法。

### 7. Verdict

**Accept with Revisions — worth pursuing, pending the validation experiment.**

保留的版本：

> **研究“公共/差分模态怎样决定多 VSG 动态 \(H,D\) 残差的空间分配，并用共享局部
> 图策略和显式速率投影，使该机制在整张未见网络上仍成立”。**

拒绝的版本：

> “再换一个更强 RL/GNN，在 Kundur 四机上得到更高分。”

#### 推荐的论文贡献，只保留三项

1. **系统机理**：公共频率恢复与 VSG 间差分同步需要不同的 \(H,D\) 调节作用，
   解释何时 residual 应介入，而不是只报告 reward。
2. **单一控制结构**：tuned droop prior + shared local graph residual + explicit
   value/rate projection；graph、mode 和 projection 是同一控制结构的必要消融，
   不是三篇方法拼盘。
3. **可信证据**：整张未见 graph、匹配预算的 non-graph baseline、physical
   co-primary endpoints、分层区间、tail/failure、delay/dropout stress。

Top three actions to take first:

1. **先关闭 Q-0029**：只冻结一个有独立 rise-time/small-signal 依据的 alpha slew，
   用新 sealed bank 判定；失败就关闭 hand-designed gate family，成功也只作为
   future residual 的 prior/baseline。
2. **写 graph vertical-slice 的预注册与接口设计**：固定四个 matched controllers、
   两类训练图、一张完全 held-out 图、相同参数量/交互量、物理 co-primary endpoint
   和 kill gate；不要先训练。
3. **实现无记忆共享 graph actor 的最小闭环**：保留 V4 bit-identical anchor，
   先证明 variable-\(N\) graph contract、joint replay、decentralized action 和
   sealed whole-graph evaluation；vertical slice 不过就转写
   “VSG-RL objective validity and reproducibility benchmark” 作为较低风险论文。
