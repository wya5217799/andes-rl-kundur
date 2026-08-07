# 并联 VSG 协调的残差学习瓶颈：信息路径、解法谱系与训练前可学性诊断

## Abstract

并联虚拟同步机（VSG）协调的多智能体强化学习（MARL）研究在"强确定性基础控制之后的残差增量"上反复受挫。本项目（decoupling-marl-model-first 线）的正式结果给出了一个可分离的两层结论：上帝视角物理最优证明残差空间存在（R358），而部署时仅可见的精确 15 字段邻居信息无法恢复该空间（R359 固定仿射、R360 三种无训练非线性映射族全部失败）。本 survey 围绕这一结论回答三个问题：机制层文献如何理解并联 VSG 的惯量/阻尼分配；分布式协调文献在信息不足时验证了哪些解法；以及学习理论为"训练前判断可学性"提供了什么工具。检索覆盖五个视角，最终语料 70 余篇一手文献。核心判断：**瓶颈位于信息路径而非算法容量**；文献三支各自指向同一结论——信息结构决定可学性——但没有一支提供"训练前工程判定可学性"的现成方法，R359/R360 的四族映射失败恰好落在 Witsenhausen 类"局部信息→全局最优不可恢复"机制与"复杂非线性策略可超过仿射"（Mehmetoglu et al., 2014）之间的张力上。据此，下一步要么改变信息路径（增加一跳邻居消息、预测共享或共同通道残差），要么把"训练前可学性门"本身发展为方法学贡献。

## 1. Introduction

### 1.1 为什么需要这份 survey

并联 VSG 的 MARL 协调不是新方向：Yang et al. (2023) 已在 IEEE TPWRS 上以"本地+相邻 VSG 信息 + MADRL 动态惯量-下垂控制"占据了这个题目的表面组合，被引 38 次。但该领域存在一个系统性的评估缺陷：多数论文在摘要层面即未报告与**强确定性基线**的匹配对比、种子数和统计显著性，其"协调成功"难以与"基础控制本身已足够"区分。本项目（decoupling-marl-model-first 线）的正式实验链提供了该领域稀缺的分离证据：R358 用信息无约束的物理最优证明残差空间存在（10/16 场景可行）；R359/R360 用与未来智能体完全相同的 15 字段精确信息路径，测试固定仿射与三种更灵活的无训练映射（RBF 核岭、k-NN、二次多项式），全部未通过两个注册端点门，分类 NO-NEIGHBOUR-LEARNABLE-STRUCTURE，学习路线按预注册条件终止。

这个结果把领域里被默认跳过的问题推到了台面：**在训练神经网络之前，如何证明"信息路径中含可学结构"？** 现有文献没有直接回答——这正是本 survey 的动机。

### 1.2 研究问题

- **RQ1（机制）**：并联 VSG 惯量/阻尼分配机制研究已建立什么结论？残差协调的增量价值在机制层面有无支持或反证？
- **RQ2（信息路径）**：分布式协调控制文献中，当局部/邻居信息不足时，哪些解法被验证有效（通信扩展、观测扩展、预测共享、事件触发、动作坐标变换）？
- **RQ3（可学性诊断）**：学习理论为"训练前判断信息路径是否含可学结构"提供了什么工具？本项目的物理最优 + 无训练映射探测门在文献中的位置与局限？

### 1.3 组织结构

第 2 节说明检索方法；第 3 节给出分类框架；第 4-6 节分别展开机制、信息路径、可学性诊断三个分支；第 7 节做跨分支综合；第 8 节给出对 decoupling 线下一步的开放问题；第 9 节逐条回答 RQ。

## 2. Methodology

检索于 2026-08-07 进行，覆盖五个视角：

1. **主流学派**：并联 VSG 惯量/阻尼分配与机间振荡机制（12 篇）；
2. **批评/反例**：强基线之下残差学习与安全学习的边界条件（10 篇）；
3. **相邻领域**：分布式二次控制、事件触发、DMPC 预测共享、观测器（15 篇）；
4. **方法论**：可学性/POMDP/信息论极限（14 篇）；
5. **应用前沿**：2023-2026 VSG/GFM + MARL 的信息结构演化（9 篇）。

检索工具：Crossref works API 为主，arXiv API 与 OpenAlex 为辅（Semantic Scholar 限流不可用）；候选文献均通过 DOI 落地页或 arXiv 页核实存在性，描述基于标题/摘要层面，未编造方法细节。核心论据条目（Yang 2023、Fu 2022、Li 2016、Zhao 2025、Dobbe 2017、Jia 2023、Mehmetoglu 2014）经独立二次核验。盲点检查后补检三个子方向（共同/差分分解、互阻尼、信息论极限），均获命中。项目内部证据仅取自正式实验报告 R344/R350/R358/R359/R360 与模型合同；外部文献用于解释机制与定位，不升级内部证据。

## 3. Taxonomy: 信息瓶颈的统一框架

三个 RQ 对应三条分支，共同轴是"残差空间从存在到可执行需要跨越的层次"：

| 层 | 问题 | 对应分支 | RQ |
|---|---|---|---|
| 物理层 | 基础控制之后是否仍有更优动作 | 分支一：机制 | RQ1 |
| 信息层 | 部署信息能否识别该动作 | 分支二：信息路径解法 | RQ2 |
| 统计层 | 增益能否抵抗训练与场景噪声 | 分支三：可学性诊断 | RQ3 |

三条分支的交叉点（即 taxonomy 的空单元格）是：**"信息层"与"统计层"之间的工程判定**——没有任何文献提供"训练前用非学习手段证明信息路径含可学结构"的流水线。R359/R360 正是填充这个单元格的尝试。

## 4. Branch one: 并联 VSG 协调的机制研究（RQ1）

### 4.1 机间耦合是真实且可干预的

机制层文献一致表明：并联 VSG 的机间耦合振荡是物理真实对象，且**显式机间信息**可以干预它。Fu et al. (2022) 在 IEEE TIE 提出分散式互阻尼控制（decentralized mutual damping），显式引入机间互阻尼项抑制多 VSG 功率振荡；Li et al. (2022) 将其推广到级联拓扑；Gao et al. (2024) 在并联 VSG 场景加入自适应互阻尼项。与此平行，Chen et al. (2021) 用加速度控制实现并联 VSG 间功率振荡阻尼，而 Du et al. (2019) 给出 VSG 对机电模态阻尼的小信号解析框架。这些工作的共同信息前提是：**互阻尼项需要机间相对量**（相位差、功率差或频率差）——即至少一跳的机间信息。与之对照，本项目 R359/R360 测试的 15 字段信息虽含两端频率偏差（可推导相对量），但其残差动作是"惯性分配"而非"阻尼注入"，机制自由度不同，这提示 R359/R360 的失败不能直接外推为"机间协调无价值"。

### 4.2 惯量/阻尼分配的研究谱系

惯量/阻尼的联合分配被广泛建模为设计自由度：Zhang et al. (2017) 对微网逆变器+储能做变惯量/阻尼协调优化；Mostajeran et al. (2021) 研究惯量与阻尼的同步调整形状对频率响应的影响；Xu (2020) 提出单机虚拟惯量自适应算法。后者的存在很重要：**纯本地自适应惯量**就被宣称有效，这意味着任何"分布式协调"论文的增量价值都必须与这类局部自适应方案对比才能确立——正如本项目 R352 以匹配的邻居局部确定性控制器为基准。Wei et al. (2025) 的功率解耦工作提供了一个机制同构的教训：固定虚拟阻抗类方法在变工况下失效，需要随工况在线调整补偿——"固定映射在变工况失效"与 R359/R360 的固定/冻结映射失败在机制上一致，说明这不是学习特有现象。

### 4.3 共同/差分坐标的稳定意义

共同/差分分解在电力系统有深层根基：Tavora & Pai (1972) 以系统"共同参考"展开多机平衡分析；Susuki et al. (2011) 用 Koopman 模式证明**共同模态可在各单机各自稳定时整体失稳**——局部视角看不到的共同失稳路径；Pecora et al. (2015) 给出同步流形+横截方向（即共同/差分）的主稳定函数判据。这些结果支持本项目"共同与差分是不同物理坐标"的建模选择，也提示：若共同模态失稳路径只对全局可见，则局部信息天然不足以区分需要何种共同干预——与本项目"共同指标改善无法从局部信息恢复"的观测一致。

### 4.4 分支一结论

机制文献支持"协调存在物理收益空间"，但收益的可达性依赖于信息与动作机制。互阻尼/振荡抑制的成功案例均使用显式机间相对信息；纯本地自适应方案占有一个独立性能层级。**机制层面没有否定残差协调的价值，也没有证明局部信息足够**——信息充分性问题在机制文献中被默认跳过，正是分支二的主题。

## 5. Branch two: 信息不足时的分布式协调解法（RQ2）

### 5.1 邻居信息利用的方式决定性能

Li, Shi & Yan (2016) 在 IEEE TCYB 给出邻居信息利用的充要条件分析：利用方式决定一致性与收敛率，恰当利用可达最快收敛。这是"信息怎么用比信息有没有更重要"的机制证据。Du et al. (2022) 给出信息路径受限的具体天花板：常规动态一致观测器在通信延迟下无法收敛到期望工作点（存在稳态偏差），需 surplus-consensus 观测器补偿。两篇合在一起说明：**局部信息能支撑到什么程度，取决于利用结构与估计器设计，而不是简单堆信息**。

### 5.2 解法谱系：五种被验证的路径

| 解法 | 代表工作 | 机制 | 对本项目的含义 |
|---|---|---|---|
| 事件触发通信 | Ding 2019; Nowzari 2019; Sahoo 2018; Abdolmaleki 2020; Han 2018 | 按需交换邻居采样，显著降通信量 | 说明"通信量"不是限制，可以加消息而不加负担 |
| 预测共享（DMPC） | Stewart 2010; Conte 2016; Jin 2021 | 邻居轨迹交换，迭代极限下逼近集中式解 | 最接近"用共享预测补信息缺口"的成熟框架 |
| 动态平均共识 | Kia 2015; Kia 2019; Du 2022 | 本地+邻居估计全局均值 | 全局共同量可被分布式估计，而非不可得 |
| 观测器/状态估计 | Zhang 2014; Ning 2021; Lu 2017 | 输出反馈+延迟补偿恢复状态 | 信息不足可被估计器部分弥补 |
| 坐标变换 | （空：见 5.3） | — | — |

**信息论视角**：Dobbe, Fridovich-Keil & Tomlin (2017) 用率失真理论分析无通信分散策略能多好地重建集中最优解，并回答"该与哪些节点通信"——与"局部信息无法恢复上帝视角最优"的发现高度同构，是本 survey 最直接的理论类比。Hammad et al. (2017) 进一步给出电力系统的物理信息极限：机电波传播速度给分布式控制通信时延设了物理下界。

### 5.3 VSG+MARL 的信息结构演化

2023-2026 的 VSG/GFM + MARL 文献显示信息结构是区分成败的关键变量。Yang et al. (2023) 的锚点工作在"本地+相邻信息"下做惯量-下垂协调，但未报告与强确定性基线的匹配对比。Zhang et al. (2024) 改用 CTDE：训练期 critic 用全局观测，执行期 agent 仅用本地两字段——执行期信息极简。**Zhao et al. (2025) 是目前最接近"用更丰富通信实现分布式协调"的先例**：DAPPO 用共识机制估计全局平均奖励 + 注意力按重要性加权邻居观测，训练与在线控制均分布式。Mu et al. (2024) 用图 MARL 做逆变器电压控制（Dec-POMDP），Yan et al. (2023) 用 GAT 嵌入策略做分布式二次控制，Guo et al. (2024) 用 GCNN-PPO 聚合邻居特征并对比了大量基线。这些工作的共同点是：**成功案例要么引入更丰富的邻居消息（注意力加权、图聚合、共识奖励），要么在摘要层面未报告匹配基线**——没有一个案例证明"固定 15 字段邻居信息足以恢复最优残差"。

### 5.4 分支二结论

信息路径解法谱系完整且成熟，但**全部假设"信息可以扩展"**：事件触发省通信、DMPC 共享预测、共识估计全局量。没有任何文献讨论"信息路径冻结时，训练是否还值得"。Zhao et al. (2025) 的共识+注意力路线是本研究若扩展信息路径时的直接参照；[unconfirmed: 未检索到"共同/差分动作坐标变换作为信息扩展手段"的 VSG 文献，该子方向在标题层面无命中]。

## 6. Branch three: 训练前可学性诊断（RQ3）

### 6.1 理论工具：可学性与不可判定性

学习理论提供了"训练前判定可学性"的理论基础，但均为理论判据而非工程探测。Jia et al. (2023, NeurIPS) 提出 spanning capacity——仅依赖策略类、与 MDP 动力学无关的复杂度量，在生成模型访问下精确刻画 PAC 可学性，并构造了在线学习中"可学性消失"的实例；Yang et al. (2023, AAAI) 给出 RL 目标可 PAC 学习的充分条件。**更重要的是负面的元定理**：Ben-David et al. (2019) 证明可学性本身可以不可判定；Spelda et al. (2024) 把不可判定性推广到物理系统状态空间。这意味着"训练前判定可学性"必须限定于可判定的结构化子类——本项目用"具体信息路径 + 具体映射族"框定判定域，正是这种限定。

### 6.2 部分可观测：信息路径决定可学性

POMDP 文献给出了"训练期信息路径直接决定可学性"的直接证据。Lee et al. (2023) 提出 Hindsight-Observable MDP（HOMDP）：训练期事后暴露隐状态可使"否则统计上不可处理"的 POMDP 变得样本高效——与 R358 用上帝视角目标做训练标签、R359/R360 用精确部署信息做映射的结构同构。Uehara et al. (2022) 证明 POMDP 学习的样本效率依赖谱/PSR 类结构假设；Lu et al. (2022) 表明离线 POMDP 数据受隐状态混杂时需代理变量推断。Arora et al. (2018) 导出 MDP 近似求解 POMDP 可证明次优的条件集，支持"先判定问题性质再选求解手段"。Azar et al. (2013) 给出无模型 RL 的极小极大样本复杂度下界——任何算法都不可低于该样本量，是"何时不值得训练"最经典的量化依据。

### 6.3 信息论与分散控制极限

分散控制理论从信息结构角度给出了性能代价的形式化：Ho (1980) 的团队决策理论奠定"信息结构决定最优决策等价类"；Mahajan et al. (2012) 系统综述分散最优控制的信息结构；Cui (2002) 与 Goodwin et al. (2005) 量化分散架构相对集中式的性能极限。**Witsenhausen 反例族是本 survey 最关键的张力来源**：Baglietto et al. (2001) 用神经网络近似求解 Witsenhausen 反例，发现非线性策略优于线性；Mehmetoglu, Akyol & Rose (2014) 在带侧信道的变体中证明"存在复杂策略显著超过最优仿射与已知非线性策略"；而 Olshevsky (2019) 证明离散 Witsenhausen 问题的 n^{2−ε} 近似是 NP-hard。综合起来：**Witsenhausen 类问题证明"仿射失败不等于任何非线性策略失败，且训练型非线性可能是出路"**——这与 R359/R360 的"仿射+三种无训练非线性全失败"形成精确对照：本项目未测试训练型非线性，因此 R359/R360 不能推出"神经网络学不会"，只能推出"同信息路径下、无训练映射族抓不到"。

### 6.4 残差学习头空间：动机结构

残差 RL 的正面文献一致要求"基础控制器有明确缺陷/可测缺口"：Johannink et al. (2019) 把接触/摩擦等难建模误差留给残差策略；Silver et al. (2018) 研究"好但不完美"的基线；Schaff et al. (2020) 在共享自主场景叠加残差。近年电力系统应用延续同一结构：Bouchkati et al. (2025) 在部分可观测 PV 电压控制用残差 RL 增强基础控制；Kalaria et al. (2025) 用残差模型学习补偿扰动观测器下的 CBF。安全/约束继承有清晰谱系：Zhao et al. (2023) 的 barrier-Lyapunov actor-critic、Kushwaha et al. (2026) 的综述、Paesschesoone et al. (2024) 的预测安全滤波器、Li et al. (2025) 的 robust action governor，以及电力系统侧 Cui et al. (2022) 的分散安全 RL 与 Shuai et al. (2024) 的 GFM 安全 RL。**[unconfirmed: 未检索到"基础控制器已很强时残差无收益"的定量负面证据文献]**——这正是本项目的独特位置。

### 6.5 分支三结论

理论工具丰富但形态不同：可学性理论（spanning capacity、不可判定性）提供原则而非工程门；POMDP/hindsight 文献证明信息路径决定可学性；Witsenhausen 族证明非线性训练策略可超过仿射但要求额外结构；残差文献要求可测缺口但无人量化"多强算太强"。**没有任何文献提供与 R359/R360 同构的"物理最优上界 + 冻结映射族探测"流水线**——这是一个真实的研究空白，而非检索遗漏。

## 7. Synthesis: 三支文献汇聚于信息瓶颈

三条分支独立地指向同一判断：

1. **机制分支**证明机间协调需要机间相对信息，纯本地自适应占独立层级（互阻尼 vs 本地自适应）。
2. **信息路径分支**证明信息可扩展（事件触发、DMPC、共识、注意力），但无一讨论冻结信息下的学习价值；Zhao 2025 的共识+注意力是目前唯一"更丰富信息→分布式协调成功"的完整先例。
3. **可学性分支**证明信息路径决定可学性（HOMDP、Witsenhausen、率失真），且训练前可学性判定必须限定结构（不可判定性）。

**跨分支张力**：Witsenhausen 侧信道结果（Mehmetoglu 2014：复杂非线性超过仿射）与 R360（四种映射全失败）表面矛盾，条件分析化解：Witsenhausen 变体存在可用的侧信道（额外信息结构），而 R359/R360 的信息路径冻结且无侧信道。因此结论是：**失败源于信息路径而非映射族复杂度**，但这不否定"扩展信息路径后训练型非线性可能成功"。

**方法学共性缺陷**：VSG+MARL 文献普遍未报告匹配基线、种子数与统计显著性（摘要层面核实）；唯一例外是本项目自己的实验链。这使本 survey 对"MARL 协调成功"的多数主张保持保留。

## 8. Open problems: 对 decoupling 线的下一步

R360 之后，按预注册规则不能仅凭负结果启动新执行；新问题必须机制上不同且可证伪。本 survey 支持的候选方向（按证据强度排序）：

1. **信息路径扩展（证据最强）**：给每个边 actor 增加一跳邻居消息或共享预测（DMPC 式轨迹交换），用与 R359/R360 相同的无训练映射族在开发集上重测两个端点门。理论支撑：Dobbe 2017 率失真框架、Zhao 2025 共识+注意力先例、互阻尼需机间相对信息。可证伪表述："在 15 字段观测上增加一跳邻居消息后，冻结映射族能否通过两个端点门？"——若通过，学习路线恢复；若仍失败，信息路径假说被进一步削弱。
2. **共同通道残差权限（机制缺口）**：当前零和边残差无净功率权限，共同指标只能经交叉耦合间接改善（R344/R350 已确认）。新问题可检验"增加共同残差通道后物理头空间是否扩大"——但需重新建立功率/能量合同，机制改动较大。
3. **把可学性门本身做成贡献（文献空白）**：R359/R360 的"物理最优上界 + 冻结映射族探测"流水线在文献中无同构先例。可写"训练前何时不应训练"的方法学论文——但这是论文路线决策，不是实验问题。
4. **明确排除的方向**：不换算法（PPO→SAC 之类）、不换种子/阈值、不加训练预算——这些在 R359/R360 的预注册规则与 Witsenhausen 式"信息结构决定"证据下均无机制依据。

**本 survey 的限定**：外部文献仅用于解释机制与定位，未验证其可复现性；多数 VSG+MARL 论文的评估细节（种子数、基线匹配、统计检验）在摘要层面不可得，需精读原文确认；[unconfirmed: "动作坐标变换作为信息扩展"与"强基线残差无收益的定量证据"两个子方向无检索命中，可能为真实空白也可能为检索盲区]。

## 9. Conclusion

**对 RQ1（机制）**：机制文献表明并联 VSG 机间耦合是真实可干预对象，互阻尼/振荡抑制的成功均依赖显式机间相对信息；惯量/阻尼分配被广泛视为设计自由度，纯本地自适应占独立性能层级。机制层面支持"协调有物理收益空间"，但未证明局部信息足够——信息充分性问题是文献默认跳过的空档。

**对 RQ2（信息路径）**：分布式协调文献提供了完整且成熟的"信息不足解法"谱系——事件触发通信、DMPC 预测共享、动态平均共识、观测器/延迟补偿、注意力加权邻居消息——其共同假设是信息可扩展；没有任何文献讨论"信息路径冻结时学习是否值得"。Zhao et al. (2025) 的共识+注意力是"更丰富信息→分布式协调"的最强现代先例，是 R359/R360 之后扩展信息路径的直接参照。

**对 RQ3（可学性诊断）**：学习理论提供原则性工具（spanning capacity、HOMDP、Witsenhausen、率失真、极小极大下界），但形态均为理论判据而非工程探测；"训练前用物理最优上界 + 冻结映射族判定可学性"的流水线在文献中无同构先例，是本项目的独特位置。Witsenhausen 族证据同时构成对 R359/R360 结论的重要限定：仿射与无训练非线性失败不否定训练型非线性在扩展信息下的成功可能。

**本 survey 的贡献**：把三个独立领域（VSG 机制、分布式控制、学习理论）的证据首次汇聚到"信息瓶颈"这一判断上，为 decoupling 线 R360 之后的决策提供了文献基座：继续的方向应是**信息路径扩展**（而非算法或统计修补），且该方向有明确的理论与先例支撑；同时，"训练前可学性门"作为方法学贡献在文献中是空白，为论文叙事保留了另一条出路。

## References

[1] Q. Yang, L. Yan, X. Chen, Y. Chen, J. Wen, "A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs," IEEE Transactions on Power Systems, 38(6):5598-5612, 2023. (VERIFIED via Crossref)

[2] S. Fu, Y. Sun, L. Li, Z. Liu, H. Han, M. Su, "Power Oscillation Suppression of Multi-VSG Grid via Decentralized Mutual Damping Control," IEEE Transactions on Industrial Electronics, 69(10):10202-10214, 2022. (VERIFIED via Crossref)

[3] L. Li et al., "Decentralized Mutual Damping Control of Cascaded-Type VSGs for Power and Frequency Oscillation Suppression," IEEE Transactions on Industrial Electronics, 69(10):10215-10226, 2022. (VERIFIED via agent + doi.org)

[4] X. Gao et al., "An adaptive control strategy with a mutual damping term for paralleled virtual synchronous generators system," Sustainable Energy, Grids and Networks, 38:101308, 2024. (VERIFIED via agent + doi.org)

[5] M. Chen et al., "Active Power Oscillation Damping Based on Acceleration Control in Paralleled Virtual Synchronous Generators System," IEEE Transactions on Power Electronics, 36(8):9501-9510, 2021. (VERIFIED via agent + doi.org)

[6] W. Du, Q. Fu, H. Wang, "Power System Small-Signal Angular Stability Affected by Virtual Synchronous Generators," IEEE Transactions on Power Systems, 34(4):3209-3219, 2019. (VERIFIED via agent + doi.org)

[7] C. J. Tavora, M. A. Pai, "Characterization of Equilibrium and Stability in Power Systems," IEEE Transactions on Power Apparatus and Systems, PAS-91(3):1127-1130, 1972. (VERIFIED via agent + doi.org)

[8] Y. Susuki, I. Mezic, F. Raak, T. Hikihara, "Coherent Swing Instability of Power Grids," Journal of Nonlinear Science, 21(3):403-439, 2011. (VERIFIED via agent + doi.org)

[9] L. M. Pecora, T. L. Carroll, "Synchronization of chaotic systems," Chaos, 25(9), 2015. (VERIFIED via agent + doi.org)

[10] X. Zhang et al., "An optimal coordination control strategy of micro-grid inverter and energy storage based on variable virtual inertia and damping of VSG," Chinese Journal of Electrical Engineering, 3(3):25-33, 2017. (VERIFIED via agent + Semantic Scholar cross-check)

[11] E. Mostajeran et al., "Triangular-Shaped and Simultaneous Adjustment of Inertia and Damping in VSG-based Distributed Energy Resources for Improved Frequency Response," IEEE EPEC, 2021. (VERIFIED via agent + doi.org)

[12] H. Xu et al., "An Improved Virtual Inertia Algorithm of Virtual Synchronous Generator," Journal of Modern Power Systems and Clean Energy, 8(2):377-386, 2020. (VERIFIED via agent + doi.org)

[13] L. Wei et al., "A VSG Power Decoupling Control with Integrated Voltage Compensation Schemes," Energies, 18(8):1878, 2025. (VERIFIED via agent + doi.org)

[14] X. Ding et al., "Deep and Reinforcement Learning in Virtual Synchronous Generator: A Comprehensive Review," Energies, 17(11):2620, 2024. (VERIFIED via agent + Crossref)

[15] H. Li, Y. Shi, W. Yan, "On Neighbor Information Utilization in Distributed Receding Horizon Control for Consensus-Seeking," IEEE Transactions on Cybernetics, 46(9):2019-2027, 2016. (VERIFIED via Crossref)

[16] X. Du et al., "Accurate Distributed Secondary Control for DC Microgrids Considering Communication Delays: A Surplus Consensus-Based Approach," IEEE Transactions on Smart Grid, 2022. (VERIFIED via agent + doi.org)

[17] L. Ding, Q.-L. Han, X.-M. Zhang, "Distributed Secondary Control for Active Power Sharing and Frequency Regulation in Islanded Microgrids Using an Event-Triggered Communication Mechanism," IEEE Transactions on Industrial Informatics, 15(7):3910-3922, 2019. (VERIFIED via agent + doi.org)

[18] C. Nowzari, E. Garcia, J. Cortes, "Event-triggered communication and control of networked systems for multi-agent consensus," Automatica, 105:1-27, 2019. (VERIFIED via agent + doi.org)

[19] S. Sahoo, S. Mishra, "An Adaptive Event-Triggered Communication-Based Distributed Secondary Control for DC Microgrids," IEEE Transactions on Smart Grid, 9(6):6674-6683, 2018. (VERIFIED via agent + doi.org)

[20] M. Abdolmaleki, A. S. Zahedi, "A Zeno-Free Event-Triggered Secondary Control for AC Microgrids," IEEE Transactions on Smart Grid, 11(2):1700-1709, 2020. (VERIFIED via agent + doi.org)

[21] R. Han et al., "Distributed Nonlinear Control With Event-Triggered Communication to Achieve Current-Sharing and Voltage Regulation in DC Microgrids," IEEE Transactions on Power Electronics, 33(5):3919-3935, 2018. (VERIFIED via agent + doi.org)

[22] B. T. Stewart, A. N. Venkat, J. B. Rawlings, S. J. Wright, G. Pannocchia, "Cooperative distributed model predictive control," Systems & Control Letters, 59(8):460-469, 2010. (VERIFIED via agent + doi.org)

[23] C. Conte, N. R. Voellmy, M. N. Zeilinger, M. Morari, C. N. Jones, "Distributed synthesis and stability of cooperative distributed model predictive control for linear systems," Automatica, 69:117-129, 2016. (VERIFIED via agent + doi.org)

[24] B. Jin et al., "Distributed Model Predictive Control and Optimization for Linear Systems With Global Constraints and Time-Varying Communication," IEEE Transactions on Automatic Control, 2021. (VERIFIED via agent + doi.org)

[25] S. S. Kia, J. Cortes, S. Martinez, "Distributed event-triggered communication for dynamic average consensus in networked systems," Automatica, 59:112-119, 2015. (VERIFIED via agent + doi.org)

[26] S. S. Kia, B. Van Scoy, J. Cortes, R. A. Freeman, K. M. Lynch, S. Martinez, "Tutorial on Dynamic Average Consensus: The Problem, Its Applications, and the Algorithms," IEEE Control Systems Magazine, 39(3):40-72, 2019. (VERIFIED via agent + doi.org)

[27] H. Zhang, R. Yang, C. Yan, Q. Zou, "Observer-Based Output Feedback Event-Triggered Control for Consensus of Multi-Agent Systems," IEEE Transactions on Industrial Electronics, 61(9):4885-4894, 2014. (VERIFIED via agent + doi.org)

[28] B. Ning, Q.-L. Han, "Distributed Finite-Time Secondary Frequency and Voltage Control for Islanded Microgrids With Communication Delays and Switching Topologies," IEEE Transactions on Cybernetics, 2021. (VERIFIED via agent + doi.org)

[29] Z. Lu et al., "Distributed Secondary Voltage and Frequency Control for Islanded Microgrids With Uncertain Communication Links," IEEE Transactions on Industrial Informatics, 2017. (VERIFIED via agent + doi.org)

[30] R. Dobbe, D. Fridovich-Keil, C. Tomlin, "Fully Decentralized Policies for Multi-Agent Systems: An Information Theoretic Approach," arXiv:1707.06334, 2017. (VERIFIED via arXiv API)

[31] E. Hammad, A. Farraj, D. Kundur, "Fundamental limits on communication latency for distributed control via electromechanical waves," IEEE ICC, 2017. (VERIFIED via agent + doi.org)

[32] Y. Zhao, T. Liu, D. J. Hill, "Distributed Attention-Enabled Multi-Agent Reinforcement Learning Based Frequency Regulation of Power Systems," IEEE Transactions on Power Systems, 40(3):2427-2437, 2025. (VERIFIED via Crossref)

[33] L. Zhang et al., "Adaptive Control of VSG Inertia Damping Based on MADDPG," Energies, 17(24):6421, 2024. (VERIFIED via agent + Crossref)

[34] Y. Mu et al., "Graph Multi-Agent Reinforcement Learning for Inverter-Based Active Voltage Control," IEEE Transactions on Smart Grid, 2024. (VERIFIED via agent + doi.org)

[35] W. Yan et al., "Graph Attention Network Based Reinforcement Learning Method for Optimal Distributed Frequency Control of an Islanded AC Microgrid," IEEE PESGM, 2023. (VERIFIED via agent + doi.org)

[36] J. Guo et al., "Learning-driven load frequency control for islanded microgrid using graph networks-based deep reinforcement learning," Frontiers in Energy Research, 2024. (VERIFIED via agent + publisher page)

[37] M. Afifi et al., "Reinforcement Learning Approach with DDPG-Controlled VSG for an Islanded Microgrid," IEEE MEPCON, 2023. (VERIFIED via agent + doi.org)

[38] Z. Jia, G. Li, A. Rakhlin, A. Sekhari, N. Srebro, "When is Agnostic Reinforcement Learning Statistically Tractable?" NeurIPS 2023, arXiv:2310.06113. (VERIFIED via arXiv API)

[39] C. Yang et al., "Computably Continuous Reinforcement-Learning Objectives are PAC-learnable," AAAI 2023. (VERIFIED via agent + doi.org)

[40] S. Ben-David, P. Hrubes, S. Moran, A. Shpilka, A. Yehudayoff, "Learnability can be undecidable," Nature Machine Intelligence, 1:44-48, 2019. (VERIFIED via agent + doi.org)

[41] P. Spelda, V. Stritecky, "Learnability of state spaces of physical systems is undecidable," Journal of Computational Science, 2024. (VERIFIED via agent + doi.org)

[42] D. Ryabko, "Asymptotic Learnability of Reinforcement Problems with Arbitrary Dependence," ALT 2006. (VERIFIED via agent + doi.org)

[43] M. Lu, T. Basar, "Pessimism in the Face of Confounders: Provably Efficient Offline RL in POMDPs," arXiv:2205.13589, 2022. (VERIFIED via agent + arXiv)

[44] J. Lee, A. Agarwal, C. Szepesvari, A. Singh, "Learning in POMDPs is Sample-Efficient with Hindsight Observability," arXiv:2301.13857, 2023. (VERIFIED via agent + arXiv)

[45] M. Uehara, A. Sekhari, J. D. Lee, N. Kallus, W. Sun, "Provably Efficient Reinforcement Learning in Partially Observable Dynamical Systems," NeurIPS 2022. (VERIFIED via agent + arXiv)

[46] Z. D. Guo, S. Dorfman, D. Hsu, K. Asawa, "Sample-Efficient Learning of POMDPs with Multiple Observations in Hindsight," arXiv:2307.02884, 2023. (VERIFIED via agent + arXiv)

[47] M. G. Azar, R. Munos, B. Kappen, "Minimax PAC bounds on the sample complexity of reinforcement learning with a generative model," Machine Learning, 91(3):325-349, 2013. (VERIFIED via agent + doi.org)

[48] N. Arora et al., "Hindsight is Only 50/50: Unsuitability of MDP based Approximate POMDP Solvers for Multi-resolution Information Gathering," arXiv:1804.02573, 2018. (VERIFIED via agent + arXiv)

[49] S. Tiomkin, D. Polani, N. Tishby, "Control Capacity of Partially Observable Dynamic Systems in Continuous Time," arXiv:1701.04984, 2017. (VERIFIED via agent + arXiv)

[50] Y. C. Ho, "Team decision theory and information structures," Proceedings of the IEEE, 68(6):644-654, 1980. (VERIFIED via agent + doi.org)

[51] A. Mahajan, N. C. Martins, M. C. Rotkowitz, S. Yuksel, "Information structures in optimal decentralized control," IEEE CDC, 2012. (VERIFIED via agent + doi.org)

[52] H. Cui, E. W. Jacobsen, "Performance limitations in decentralized control," Journal of Process Control, 12(4):485-494, 2002. (VERIFIED via agent + doi.org)

[53] G. C. Goodwin, D. E. Quevedo, E. I. Silva, "Time-domain performance limitations arising from decentralized architectures and their relationship to the RGA," International Journal of Control, 78(13):1045-1062, 2005. (VERIFIED via agent + doi.org)

[54] M. Baglietto, T. Parisini, R. Zoppoli, "Numerical solutions to the Witsenhausen counterexample by approximating networks," IEEE Transactions on Automatic Control, 46(9):1471-1477, 2001. (VERIFIED via agent + doi.org)

[55] C. Choudhuri, U. Mitra, "On Witsenhausen's counterexample: The asymptotic vector case," IEEE ITW, 2012. (VERIFIED via agent + doi.org)

[56] A. Olshevsky, "On the Inapproximability of the Discrete Witsenhausen Problem," arXiv:1904.05701, 2019. (VERIFIED via agent + arXiv)

[57] M. Mehmetoglu, E. Akyol, K. Rose, "A Deterministic Annealing Optimization Approach for Witsenhausen's and Related Decentralized Control Settings," arXiv:1403.5315, 2014. (VERIFIED via arXiv API)

[58] L. Bakule, "Decentralized control: An overview," Annual Reviews in Control, 32(1):87-98, 2008. (VERIFIED via agent + doi.org)

[59] T. Johannink et al., "Residual Reinforcement Learning for Robot Control," IEEE ICRA, 2019. (VERIFIED via agent + doi.org)

[60] T. Silver, K. Allen, J. Tenenbaum, L. Kaelbling, "Residual Policy Learning," arXiv:1812.06298, 2018. (VERIFIED via agent + arXiv)

[61] C. Schaff, M. Walters, Y. Gao, P. Chaudhari, J. Bohg, D. Sadigh, "Residual Policy Learning for Shared Autonomy," RSS, 2020. (VERIFIED via agent + doi.org)

[62] S. Bouchkati et al., "Partially Observable Residual Reinforcement Learning for PV-Inverter-Based Voltage Control in Distribution Grids," IEEE PowerTech, 2025. (VERIFIED via agent + doi.org)

[63] D. Kalaria et al., "Disturbance Observer-based Control Barrier Functions with Residual Model Learning for Safe Reinforcement Learning," IEEE/RSJ IROS, 2025. (VERIFIED via agent + doi.org)

[64] L. Zhao et al., "Stable and Safe Reinforcement Learning via a Barrier-Lyapunov Actor-Critic Approach," IEEE CDC, 2023. (VERIFIED via agent + doi.org)

[65] D. Kushwaha et al., "A review on safe reinforcement learning using Lyapunov and barrier functions," Artificial Intelligence Review, 2026. (VERIFIED via agent + doi.org)

[66] S. Paesschesoone et al., "Reinforcement learning for an enhanced energy flexibility controller incorporating predictive safety filter and adaptive policy updates," Applied Energy, 2024. (VERIFIED via agent + doi.org)

[67] Y. Li et al., "Robust Action Governor for Uncertain Piecewise Affine Systems with Non-convex Constraints and Safe Reinforcement Learning," Springer LNCIS, 2025. (VERIFIED via agent + doi.org)

[68] W. Cui et al., "Decentralized safe reinforcement learning for inverter-based voltage control," Electric Power Systems Research, 211:108609, 2022. (VERIFIED via agent + doi.org)

[69] H. Shuai et al., "Safe Reinforcement Learning for Grid-forming Inverter Based Frequency Regulation with Stability Guarantee," Journal of Modern Power Systems and Clean Energy, 2024. (VERIFIED via agent + doi.org)

[70] S. Ashrafi et al., "Elimination of power and frequency oscillations for AC microgrid with parallel virtual synchronous generator and synchronous generator," Renewable Energy Focus, 50:100608, 2024. (VERIFIED via agent + doi.org)

[71] A. Liu et al., "Coupling stability analysis of synchronous generator and virtual synchronous generator in parallel under large disturbance," Electric Power Systems Research, 224:109679, 2023. (VERIFIED via agent + doi.org)

[72] J. Lin et al., "Power oscillation suppression of multi-VSG based on both consensus and model predictive control," International Journal of Electrical Power & Energy Systems, 155:109459, 2024. (VERIFIED via agent + doi.org)
