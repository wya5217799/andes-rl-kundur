# R287 之后的拓扑信息价值门

日期：2026-07-30
状态：跨论文可复用的研究决策原文；不是 measurement-of-record 或第二套 ledger
权限边界：定义 prospective gate；正式 question、round、claim、feed 与结果仍由项目 ledger 和 sealed artifacts 持有

## Decision

先测量 topology information 的可实现价值上限，再决定是否训练图策略。
直接实施“谱灵敏度 GNN-RL”不具有稳健新颖性；Gate 0 未通过时终止该路线。

## 1. 执行结论

**Idea Evaluator 结论：`ACCEPT WITH MAJOR REVISIONS`。**

原始方案“拓扑感知的谱灵敏度 GNN-RL，用于虚拟惯量空间分配”应按新颖性直接淘汰。Eshun、Fatemi 与 Fattahi（2026）已经把特征值灵敏度、虚拟惯量配置、物理约束 ST-GNN、RL、约束投影和变化拓扑/未见故障整合在同一框架中。继续沿这个标题和方法链做，极易成为结构性重复。

修订后保留的研究问题是：

> **在相同动作、信息、训练和计算预算下，显式拓扑信息是否对未见网络配置中的虚拟惯量差分控制具有不可由经典规则或非图策略替代的增量价值？**

下一轮不应直接训练 GNN。先做一个无需训练或仅需离线小规模优化的 **Topology-Information Value Gate（拓扑信息价值门）**。只有同时观察到：

1. 完美拓扑信息存在具有工程意义的可实现上限；
2. 不同拓扑确实要求不同的空间动作；
3. 经典谱/灵敏度规则不能回收大部分上限；
4. 当前冻结控制器在预注册的网络配置上出现可重复、非偶然的 regret；

才允许进入图策略阶段。

## 2. 为什么现在需要 Deep Research

R287 已经证明冻结 centralized TD3 在一个 Kundur 拓扑、一个走廊阻抗代理轴上能保持增益，但它没有改变节点—边关系，因此不能当作 topology intervention，也不能说明拓扑输入是否有价值。

定向检索发现：

- Eshun et al. 已经覆盖“谱灵敏度 + ST-GNN + RL + 虚拟惯量 + 变化拓扑”的直接方法链，构成原始方案的主要新颖性致命项。
- Buire et al. 表明虚拟惯量和阻尼的较优分配可能强烈依赖拓扑；但 Poolla et al. 又给出在特定模型和指标假设下存在闭式或鲁棒分配结果，说明“拓扑必然重要”不能作为未经检验的前提。
- Falconer and Mones 在 OPF 上发现固定拓扑时 GNN/CNN 相对 FCNN 的效用有限，而拓扑变化时 GNN 才有明显优势。这直接支持“先证明信息价值，再选择架构”。
- de Jong et al. 在拓扑控制中比较了 FCNN、同质 GNN 和异质 GNN，并发现表示方式和 OOD 划分都会改变结论；“用了 GNN”本身不是充分归因。

因此，Deep Research 的作用不是为 GNN 背书，而是发现一个可判死、能和最近工作区分的证据问题。

## 3. 最近工作与剩余差异轴

| 工作 | 已覆盖内容 | 对本项目的约束 |
|---|---|---|
| [Eshun et al., 2026](https://www.sciencedirect.com/science/article/pii/S2352467726000500) | 谱灵敏度、虚拟惯量空间配置、物理约束 ST-GNN、RL、变化拓扑和未见故障 | 原始“谱 GNN-RL”方法方案失去新颖性；只能研究其未充分隔离的因果必要性 |
| [Buire et al., 2026](https://www.sciencedirect.com/science/article/pii/S0142061526004199) | 在网状、辐射和随机辐射网络中优化 GFM 惯量/阻尼，报告强拓扑依赖 | “拓扑影响分配”本身不是新贡献；必须比较经典优化 |
| [Poolla et al., 2017](https://arxiv.org/abs/1510.01497) | 线性网络模型、H2 指标、局部/闭式结果及最坏扰动鲁棒分配 | 构成“拓扑信息没有额外决策价值”的强零假设 |
| [Tuo and Li, 2021](https://arxiv.org/abs/2110.11497) | 基于 Fiedler 模态的虚拟惯量配置 | 谱/模态方法必须进入经典基线 |
| [Falconer and Mones, 2022](https://arxiv.org/abs/2110.00306) | 系统比较 FCNN/CNN/GNN；固定拓扑下图模型效用有限，变化拓扑下才显现优势 | 必须把 topology information 与 graph architecture 分开检验 |
| [de Jong et al., 2025](https://arxiv.org/abs/2501.07186) | FCNN、同质 GNN、异质 GNN；同一节点集上的 OOD 网络配置 | 表示和 OOD 定义必须预注册；同节点线路状态不能夸大为跨图泛化 |
| [Authier et al., 2024](https://www.sciencedirect.com/science/article/pii/S037877962400703X) | 物理约束 GNN 用于多配电网重构/调度 | 跨图输入和物理约束已有先例，但控制对象不同 |
| [Jacob et al., 2024](https://www.nature.com/articles/s41467-024-49207-y) | 图 RL 与 MLP-RL 用于配电网故障恢复 | 图编码的控制收益已有先例，但不是虚拟惯量动态分配，也不是统一跨图策略 |

本轮检索没有核验到同时满足以下全部条件的直接重叠工作：

1. 虚拟惯量/阻尼的动态差分控制；
2. 经典分配、拓扑知情非图模型和图模型的匹配比较；
3. 只操纵真实拓扑信息，其余容量、训练、观测和动作预算保持一致；
4. 完全预留的网络配置或基础图；
5. DAE 时域物理端点、失败保留、配对不确定性和尾部风险。

这只能表述为“在本轮限定检索中未找到直接重叠”，不能作为已证明的新颖性结论。

## 4. Idea Evaluator

### 4.1 类型

这是一个 **Novel Problem / causal necessity** 研究，而不是 Novel Method 研究。核心贡献应是严格证明或否定拓扑信息的必要性，而不是发明另一种 GNN。

### 4.2 致命项

| 项目 | 等级 | 处理 |
|---|---|---|
| F1 新颖性 | 原方案 FATAL；修订方案 MAJOR | 淘汰直接谱 GNN-RL，改成因果信息价值门 |
| F3 基线 | MAJOR | 必须包含 topology-blind robust、谱/模态、灵敏度、当前冻结控制器、匹配非图模型 |
| F4 可证伪性 | 修订后 PASS | 预注册 kill/pivot gate |
| F6 数据/评估泄漏 | MAJOR | topology selection、可解性筛选和阈值必须在看动态端点前冻结 |
| F8 范围 | 原方案 MAJOR | 当前只做 Gate 0，不同时做 GNN、理论、安全和跨仿真器 |

### 4.3 五维评分

| 维度 | 分数（10 分制） | 判断 |
|---|---:|---|
| Higher | 6 | 机制问题清楚，但尚无本项目直接证据 |
| Faster | 4 | 完整图策略较慢；Gate 0 可显著缩短错误路线 |
| Stronger | 9 | 预注册 topology intervention、匹配基线和失败保留可形成强证据 |
| Cheaper | 7 | 先用冻结控制器和小型动作库，避免直接训练 |
| Broader | 7 | 若通过，可自然接到 P2 topology generalisation；若不通过，也能给出可信负结论 |

### 4.4 范式探针

- First principles：通过。先问图信息是否必要，不把架构当作前提。
- Elephant in the room：通过。多数工作没有把拓扑信息、参数共享、模型容量和图归纳偏置分开。
- Technology cycle：部分通过。GNN 已成熟，问题不在“能否使用”，而在“是否值得使用”。
- Hamming importance：部分通过。对本项目路线选择重要，但必须避免把小 Kundur 配置实验夸大成普适结论。

## 5. 建议授权的问题

候选 question 文本：

> **Q-CANDIDATE — 在预注册、非孤岛且电气上不同的 Kundur 网络配置中，完美拓扑信息相对统一 topology-blind 鲁棒分配是否产生具有工程意义的动态控制价值；若有，经典谱/灵敏度规则能否回收该价值，从而使学习策略仍无必要？**

该问题在 PI 明确授权前不得分配正式 Q/R/CLM ID。

## 6. Gate 0：无需训练的拓扑信息价值门

### 6.1 Gate 0A：只做结构与可解性预检

在不读取候选动态端点的前提下：

1. 从不同走廊、区域内线路和耦合强度位置生成 6–12 个候选线路状态。
2. 剔除孤岛、潮流不收敛、执行器集合改变或明显违反基础运行约束的候选。
3. 用预先声明的电气距离、关键模态参与度和走廊位置选择 3–4 个差异最大的合法配置。
4. 冻结 topology ID、节点/边表、参数、文件哈希和选择理由。

这一步只确定实验对象，不运行或查看 paper-facing 时域结果。

### 6.2 Gate 0B：冻结控制器与分配库的 sealed screen

保持 R287 的：

- 24 个配对场景；
- 当前 q0 和冻结 centralized TD3；
- 动作、功率、能量、速率和饱和预算；
- 物理端点、配对 bootstrap、tail 指标和 retained-failure 规则。

新增一个在看结果前冻结的低维分配库：

1. q0 / uniform；
2. 当前冻结 centralized TD3；
3. topology-blind robust allocation：在开发拓扑上求得、对所有测试拓扑共用；
4. slow-mode / Fiedler / eigen-sensitivity 规则；
5. finite-difference 或 time-domain constrained sensitivity 规则；
6. per-topology offline oracle：每个拓扑从同一候选库中事后选最佳，仅作为 perfect-information upper bound，不得称作可部署控制器。

### 6.3 主要 estimands

1. **Frozen-policy retention**：冻结 centralized TD3 相对 q0 的增益，在各拓扑相对 nominal 的保持率。
2. **Topology-information headroom**：per-topology oracle 与最佳 topology-blind robust allocation 的配对差。
3. **Classical recovery fraction**：经典谱/灵敏度规则回收 headroom 的比例。
4. **Topology × controller interaction**：控制器排序或相对收益是否随拓扑发生可重复变化。
5. **Physical validity**：前三秒区间 IAE、相对同步、频率/振荡端点、动作/能量/速率/饱和、失败率和尾部风险。

最小工程效应和统计阈值必须在正式 plan 中依据测量精度、R287 变异和工程意义注册；本备忘录不事后发明数值。

### 6.4 预注册停止规则

- **NO-TOPOLOGY-VALUE**：oracle headroom 未超过预注册最小工程效应，或配对区间不排除无实质价值。停止 topology-conditioned learner 和 GNN 路线。
- **CURRENT-POLICY-ROBUST**：冻结 TD3 在所有合法配置上保持增益，排序不反转，tail/guard 不恶化。停止近期拓扑算法开发；将 P2 延后。
- **STATIC-CLASSICAL-SUFFICIENT**：拓扑信息有价值，但谱/灵敏度规则回收了预注册的大部分 headroom。采用经典规则，不训练 learner。
- **TOPOLOGY-LEARNING-JUSTIFIED**：headroom 稳定且有工程意义，不同拓扑要求不同动作，经典规则留下稳定 regret，冻结策略出现可重复退化。仅在此时授权下一阶段。
- 任何 retained failure、哈希失配、拓扑与 seal 不一致或执行器集合变化：停止，不删除、不自动重试该证据。

## 7. Gate 1：只有 Gate 0 通过才允许

Gate 1 必须把“信息价值”和“图架构价值”分开：

| 因素 | 水平 |
|---|---|
| topology information | 无 / 有 |
| relational inductive bias | 非图 / 图 |

建议匹配组：

1. topology-blind shared MLP 或 DeepSets；
2. 接收同等 topology descriptor/flattened adjacency 的非图模型；
3. 使用 identity 或 shuffled adjacency 的 GNN；
4. 使用真实邻接和边参数的 GNN；
5. 经典谱规则；
6. 冻结经典控制器 + 学习 residual。

所有学习组必须保持数据、训练算法、actor/critic、动作、奖励、投影、步数、种子、调参预算和近似参数量一致。

因果判据：

- 真实邻接不优于 shuffled/identity：否定“图结构产生增益”。
- topology-aware MLP 匹配 GNN：信息有价值，但 GNN 非必要。
- topology-blind shared policy 匹配 GNN：收益来自参数共享或正则化，不来自拓扑。
- GNN 只改善 ID、未改善 held-out configuration：否定 topology-generalisation 主张。
- 经典规则匹配学习：停止 RL 扩展。

## 8. OOD 术语与主张边界

必须分别报告：

1. operating OOD：同一图上的未见负荷/扰动；
2. contingency/configuration OOD：同一节点集上的完全预留线路状态；
3. structural OOD：训练和调参均未见的不同基础图、节点数或 VSG 数。

Gate 0 在当前固定输入维度下最多支持第 2 类“未见网络配置”，不能写成完整 structural topology generalisation。项目 P2 的最终出口仍要求完全 held-out graphs、VSG counts 和 communication graphs。

## 9. 仓库实现前置条件

当前 ANDES V4 环境在 `andes_vsg_env_v4.py::_build_system()` 中直接构建扩展 Kundur 拓扑，仓库尚无可复用的 topology-variant contract。正式开轮前应先做一个最小、单一职责的拓扑配置层，而不是在新脚本中散布线路开断和环境变量：

- `topology_id` 与规范化节点/边表；
- 线路状态和电气参数；
- 连通性/孤岛检查；
- 潮流/TDS 可解性预检；
- 固定执行器和观测维度检查；
- 规范化序列化与 SHA256；
- 与 scenario seal、trace sidecar 和分析 provenance 的绑定。

第一阶段只使用相同节点数和相同 VSG 集合，避免未授权地改变控制器接口。跨节点数/跨基础图属于后续 P2，不应混入 Gate 0。

## 10. 能力、成本与风险

| 项目 | 评估 |
|---|---|
| Gate 0 计算 | 低到中；复用冻结 controller bank，无训练 |
| 工程量 | 中；主要在 topology contract、连通性/可解性预检和经典 allocation library |
| 数据风险 | 低；仿真生成，但必须防止 topology selection 看见端点 |
| 最大科学风险 | topology intervention 太轻，oracle headroom 近零 |
| 最大归因风险 | 把线路状态鲁棒性、拓扑信息价值和 GNN 架构价值混成一个结论 |
| 最大范围风险 | 同时加入安全证书、跨仿真器、不同 VSG 数和新 RL 算法 |

用户尚未声明下一轮可用 wall time、WSL 并发和允许的总 traces，因此这里只能判断 Gate 0 原理可行，不能承诺工期或矩阵规模。

## 11. 最终路由

1. 当前 SCI 线、R287、CLM-0650 和论文草稿保持只读。
2. 本备忘录保持在 `tmp/`，不进入事实层和 `ARTIFACTS.json`。
3. PI 若同意候选 question，才把问题写入研究 programme/priority question，并用原子工具预留 ID。
4. 正式 plan 先注册 Gate 0A/0B、阈值、候选选择规则和 seal。
5. Gate 0 未通过：关闭拓扑学习路线，不开 GNN。
6. Gate 0 通过：另开 Gate 1，执行严格匹配的 topology-information × architecture 因果试验。

## 12. 一句话给 PI

**不要直接做 GNN：先用冻结控制器、经典谱分配和 per-topology oracle 测出“知道拓扑”到底值多少钱；若这个价值不大或经典规则已经吃掉，就立即杀掉拓扑学习路线，只有剩余 regret 稳定且有工程意义时才训练图策略。**

## 13. R288-R290 执行更新

- R288 的 simple-graph 单线筛选不可执行：
  `results/r288_topology_information/FEED.md`。
- R289 的首个 multigraph 矩阵因执行完整性失败而无效：
  `results/r289_topology_information/FEED.md`。
- R290 证明直接写 `.u.v` 会破坏初始化，但合法 setter 下 Line_2/q0
  仍有正实部模态：`results/r290_topology_initialization/FEED.md`。

当前决定：Q-0047 关闭为 partial，不训练图策略，也不把这些诊断写入
当前 SCI 证据链。若未来重开，必须新建问题，并在 seal 前预注册
q0 初始化和小信号可行性筛选；导航只保留这些 feed 指针，不复制数值。
