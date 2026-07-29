# 从 ICEMS 2026 到 SCI:VSG / 构网逆变器方向文献调研与创新点建议

**调研日期**:2026-07-29
**读者**:论文作者本人(决策用工作文档,非投稿文本)
**输入资产**:ICEMS 2026 会议论文 *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning* 及其 ANDES + Kundur 双区域 + RL 训练/封存评估管线(287 条 claims、264 轮实验,R280 终审 `CENTRALIZED-EXPLANATION-SUFFICIENT`)

---

## 摘要

本报告回答三个研究问题:虚拟惯量空间配置(inertia placement)的经典谱系与开放问题(RQ1);RL/MARL 用于 VSG/GFM 控制的现状、批评与方法论标杆(RQ2);在"第一篇 SCI、复用现有管线、目标中科院 2–3 区"约束下最值得投入的创新点候选(RQ3)。基于约 180 篇检索语料、逐条核验后的 40 余篇核心引用,主要结论是:**经典 inertia placement 谱系(ETH Dörfler 学派)与并联 VSG 学习控制文献之间存在一个明显的交汇空白——没有人用因果实验设计回答"虚拟惯量的空间差动配置为什么有效、增益由什么决定";而这恰好是作者现有资产(差动零和分配 + matched baseline + 封存扰动库)唯一能可信回答的问题。** 推荐以"学习版惯量空间配置 + 机理刻画 + 弱电网泛化"为主轴创新点,负结果(MARL 无增量价值)作为方法论贡献保留。

---

## 1. 引言与研究问题

作者的 ICEMS 2026 会议论文报告了一个诚实但反叙事的结果:在 Kundur 双区域系统上,集中式 TD3 actor 将同步损失降低 24.35%、区域间 IAE 降低 17.04%,参数共享 MARL 仅达 16.79% / 9.54%,且三种子一致——学习收益真实,但 MARL 架构无增量价值。升级为 SCI 期刊论文需要一个能站住的创新点。

由此冻结三个研究问题:

- **RQ1(谱系锚点)**:虚拟惯量空间配置在经典电力系统文献中的问题谱系是什么?已有结论、开放问题、与并联 VSG/构网变流器的关系?
- **RQ2(现状与批评)**:RL/MARL 用于 VSG/GFM 控制的文献现状如何?"学习是否有增量价值"与可复现性批评发展到什么程度?MARL vs 集中式的现有证据?
- **RQ3(创新点候选)**:沿弱电网/高 IBR、安全-稳定约束、机理刻画三条趋势轴,哪些创新点最适合"第一篇 SCI、复用现有管线、目标 2–3 区"?

**视角(angle)**:经典 inertia placement 谱系与学习控制文献的交汇;张力点在于"RL 有效"的宣称与增量价值/可复现性批评之间——作者的负结果在这个张力里是资产而非包袱。

## 2. 检索方法

五个检索视角经 Google Scholar 索引(经 scholar 数据源)执行:主流学派、批评视角、相邻领域(经典惯量配置)、方法论、应用与政策(电网规程)。每视角宽-窄两轮,共 10 组查询、约 180 条候选。全部拟引用条目经至少一次独立来源交叉核验(IEEE Xplore 记录、第三方综述引用列表、arXiv 全文);仅摘要可得的结论在文中标注证据等级。会话禁用子代理,视角串行执行。

**证据等级约定**(电力系统学科):①解析/理论结果 > ②线性化小信号分析 > ③时域仿真(封存评估 > 自评) > ④实验/HIL。本语料绝大多数为③,凡③仅自称"效果提升"而无独立评估库者,其结论强度一律下调一档表述。

## 3. 分类体系与文献证据

### 3.1 分支 A:经典 inertia placement 谱系(相邻领域,理论锚点)

该谱系回答"惯量放在网络的什么位置、放多少"这一优化问题,是低惯量系统研究里公认的基本问题之一。Milano 等 2018 年的奠基性综述将 inertia placement 列为低惯量系统核心挑战之一[1]。ETH 学派建立了谱系主干:Poolla、Bolognani、Dörfler 2017 年在网络化简线性模型上用 H2 范数刻画"虚拟惯量的最优空间分配",证明配置显著影响频率性能[2];Groß 等 2017 年将虚拟惯量与阻尼联合放置以提升系统韧性[3];Poolla、Groß、Dörfler 2019 年进一步区分 grid-forming 与 grid-following 两类虚拟惯量设备,给出放置与参数整定的联合方法,并指出 GFM 型惯量对降低发电机 RoCoF 峰值分布更有效[4]。Dörfler 与 Groß 2023 年的 Annual Review 将该谱系系统化为"低惯量系统控制"的标准参考[5]。

谱系的两个重要后续分支:(i)**惯量异质性的物理影响**——Adrees 与 Milanović 2019 年表明惯量的空间/组成异质性显著改变频率动态,给频率稳定分析提出明确指导[6];(ii)**运行层面的位置感知**——Tuo 与 Li 在 TPWRS 提出考虑 locational frequency stability 的安全约束机组组合[7],说明"位置"已从规划问题进入运行问题。2024–2025 年,放置问题延伸到 GFM 逆变器本体:Liyanage 等 2025 年提出考虑时空动态的 GFM 逆变器战略放置[8],Wang 等 2025 年从频域视角分析 GFM/GFL 混合系统中惯量的空间分布度量[9];2024 年 Xin 等则从小信号稳定与电网强度角度追问"系统到底需要多少 GFM"[10]。

**小结**:经典谱系给出的是**静态/准静态最优配置**(离线优化、线性模型);它没有回答"在扰动实时演化中,惯量的空间差动重分配能否以及如何提供超越静态最优的收益"——这正是学习控制可以切入、但尚未被可信回答的空档。

### 3.2 分支 B:并联 VSG 的交互、振荡与参数协调(作者的直接问题域)

并联 VSG 因参数失配产生有功环流与功率振荡是已知现象:Chen、Zhou、Wu、Blaabjerg 2021 年系统刻画了并联 VSG 逆变器的特性[11];VSG 低频振荡问题已有专门综述(2025)[12]。参数协调路线分两支:

- **经典自适应/协调控制**:Fu 等 2022 年用自适应虚拟惯量抑制多 VSG 电网功率振荡[13];Gao 等 2024 年提出含互阻尼项的并联 VSG 自适应控制[14]。
- **学习控制**:**与作者会议论文最接近的先行工作是 Yang、Yan、Chen、Chen、Wen 的 TPWRS 论文**(2023 年刊出,38(6):5598–5612)[15]:同样针对并联 VSG,先从简化频率响应模型推导振荡与惯量-下垂参数分布的关系,再将参数整定建模为 Markov 博弈,用基于 SAC 的 MADRL 分布式动态调节惯量-下垂参数抑制振荡,每 agent 仅用本地与相邻 VSG 信息。

Yang 等工作确认了该问题域在 TPWRS 级别的合法性,但据其摘要与第三方转述,它(i)未设置 size-matched 集中式学习基线以分离"MARL 架构"与"学习本身"的贡献,(ii)未分离总量惯量增益与空间重分配增益,(iii)评估与训练共用扰动分布。这三点正是作者管线已经解决的事[16]。

### 3.3 分支 C:RL/MARL 用于 VSG/GFM 控制(主流学派)

主流做法是用 DRL 在线自适应 VSG 参数:Li 等 2021 年较早将 VSG 控制形式化为 RL 问题[17];Oboreh-Snapps 等 2023 年用 TD3 控制 VSG[18];Lu 与 Zhuan 2024 年用 SAC 做参数自适应[19];2024 年已有专门综述梳理该方向[20]。2025–2026 年的新动向:(i)MARL 扩展到 GFM 微电网的惯量-阻尼特性优化——Ge 等 2026 年在 IEEE-13 节点微电网上用 MADRL 优化 grid node 惯量与 GFC 阻尼特性[21](与作者方向最近的第二篇先行工作);(ii)sim-to-real 与鲁棒性成为新卖点——Zeng 与 Sun 2026 年在 TPWRS 提出物理信息鲁棒 DRL 弥合 VSG 频率控制的 sim-to-real 鸿沟[22];(iii)异质 VSG 的 pinning 式惯量控制[23]。

**小结**:该分支产出量大且仍在增长,但贡献模式高度同质("新算法 + 自设场景 + 自评提升"),与分支 D 的批评形成直接张力。

### 3.4 分支 D:批评视角——增量价值、可复现性与 MARL 必要性

- **可复现性**:ML 社区的不可复现来源综述[24]与真实世界 RL 挑战分析[25]已成为引用标准;电力领域综述开始把可复现性列为该方向的核心未决问题[26][27]。
- **MARL vs 集中式**:MARL 社区内部对"集中式训练是否必然优于分散执行"有系统对比(Lyu 等 2021,集中式 vs 分散式 critic 的对比研究)[28];**但在电力系统频率/VSG 控制语境下,未检索到以 size-matched 集中式学习基线 + 预封存评估库检验 MARL 增量价值的工作**——作者会议论文的实验设计在该语境下目前是唯一例[16]。电力 MARL 的主流仍默认"多 agent 架构天然合理"(电压控制领域的大量工作即如此[29])。
- **方法论标杆正在形成**:安全 RL 综述明确要求基线、消融与约束满足报告[27];VSG 方向出现 sim-to-real、物理信息鲁棒性等新基准要求[22]。

**小结**:批评视角不否定学习控制,它否定的是**不可信的证据**。作者的三种子、matched baseline、fresh bank 设计恰好是当前批评潮流所要求的东西——这是定位论文时最应放大的一点。

### 3.5 分支 E:趋势轴 1——弱电网 / 高 IBR 渗透率

弱电网下 GFM 的稳定性是 2024 年以来最活跃的主线:Xin 等 2024 年从电网强度与小信号稳定角度量化"需要多少 GFM"[10];GFM 在低短路比下的小信号失稳机理(含直流电容动态)[30]、GFM/GFL 混合系统的稳定评估[31]、GFM 能力提升与局限的批判性综述[32]相继出现。核心共识:**GFM 不是越多越好,其价值随电网强度非单调变化**——这为"惯量配置随电网强度自适应"提供了直接的物理动机。

### 3.6 分支 F:趋势轴 2——暂态稳定 / 故障穿越 / 限流

GFM 最根本的公认难题是大扰动下限流摧毁同步转矩:限流策略综述[33]、cross-forming 控制[34]、FRT 技术全面综述[35]、限流下暂态稳定增强[36]构成活跃前沿。该方向档次最高,但需要故障场景、限流模型与保护配合的全新建模——与作者现有资产(负荷扰动 + 小信号域)距离最远。

### 3.7 分支 G:趋势轴 3——安全 / 稳定可证的学习控制

Lyapunov/barrier 约束的 RL 已形成清晰谱系:Feng、Shi、Qu、Low 的稳定性约束 RL(分散式实时电压控制)[37];**与作者最近的是 Shuai、She、Wang、Li 2024 年在 J. Mod. Power Syst. Clean Energy 的安全 RL 工作:针对 GFM 逆变器频率调节,用 Lyapunov 函数构造值函数并采用 model-based RL 给出稳定保证**[38]。Su 等 2025 年的 Proceedings of the IEEE 综述将安全 RL 在电力系统的方法学系统化[27]。作者会议论文的 hard zero-sum、slew limit、有界动作设计是该谱系的"工程版"前置形态,存在自然的升级路径。

### 3.8 分支 H:应用与政策——惯量正在成为可采购的系统服务

政策面对该研究方向形成强牵引(均为官方/一手文件):ENTSO-E 2025 年 11 月发布 GFM 要求第二阶段技术报告,含 synthetic inertia 规格[39];英国 2023 年 10 月开辟稳定性市场采购 GFM 功能(含惯量供给)[39];德国 2026 年 1 月启动瞬时备用(即惯量)市场化采购[39];EirGrid/SONI 2026 年 2 月发布全岛 GFM 战略,规划"自愿—试验—强制"三阶段入电网规程[40];AEMO 2023 年发布 GFM 自愿规范[41];UNIFI 联盟 2024 年发布 GFM 规范 v2[42]。**惯量的"谁提供、在哪提供、提供多少"已从学术问题变为市场与规程问题**——这直接抬升 inertia placement 类研究的现实权重。

## 4. 跨分支综合:三个张力与一个空白

1. **张力一(分支 A vs C)**:经典谱系有"空间配置重要"的解析证据[2][4][6],学习控制文献却几乎只把惯量当标量参数在线调节[17][18][19];把"空间差动配置"当作一等公民并用学习控制器实时执行、且评估可信的工作,未检索到。
2. **张力二(分支 C vs D)**:学习控制论文宣称的增益,按分支 D 的方法论标杆大多不可信(无 matched baseline、无种子-扰动方差分解);作者的负结果[16]是目前该问题域唯一满足批评者要求的证据,这本身就是可发表的方法论贡献。
3. **张力三(分支 B vs E/G)**:并联 VSG 学习协调[15][21]均不考虑电网强度变化与稳定证书;而趋势轴 E、G 各自独立繁荣,**三者(并联协调 × 弱电网 × 稳定约束)尚无交汇工作**。

**空白陈述(本报告的核心判断)**:虚拟惯量空间差动配置的实时学习控制——以因果实验设计分离总量/空间增益、以解析/小信号方法解释机理、以弱电网扫描界定泛化边界——在现有文献中没有对应物。它同时落在经典谱系的延长线(可引 Poolla/Dörfler 谱系)、趋势轴的交点(弱电网 + 安全约束)、以及批评潮流的正面(可信证据)。

## 5. 开放问题(whitespace 清单)

- OP1:差动惯量重分配的增益由什么物理量决定(电气距离、惯量异质度、扰动位置、电网强度)?[unconfirmed: 无数理刻画工作被检索到]
- OP2:MARL 在频率/惯量协调中何时有增量价值(通信约束?部分可观?规模?)——现有负结果仅覆盖理想通信双区域场景[16]。
- OP3:惯量空间配置随 SCR/渗透率变化的自适应规律——静态放置[8][9]与在线标量调节[17–19]之间的中间形态。
- OP4:学习控制器的稳定证书在并联 VSG 场景的最小代价形式(工程约束 vs Lyapunov 证书的换算)[38]。

## 6. 结论:研究问题逐一回答

**RQ1**:inertia placement 是有谱系、有权威、仍在生长的基本问题(§3.1);其解析结论限于静态/线性设定,"实时空间差动重分配"的增益与机理未被回答——它是作者工作最硬的可挂靠锚点。
**RQ2**:RL-VSG/MARL-GFM 文献量大、同质化、正被可复现性与增量价值批评重塑;电力语境下 MARL-vs-集中式的因果检验缺失,作者的会议论文设计是该方向的孤例,负结果具有独立发表价值。
**RQ3**:见 §7。

## 7. 创新点候选与推荐(RQ3 的可执行答案)

| 候选 | 内容 | 复用资产 | 新增工作 | 风险 | 档次预期 |
|---|---|---|---|---|---|
| **C1(主推)** | **学习版惯性空间配置**:把问题陈述从"MARL 协调并联 VSG"重构为"虚拟惯量空间差动配置——增益机理与边界";对接 Poolla 谱系与 OP1 | 全部(差动零和、matched baseline、封存库、192 轨迹) | 参数化窄扫描(惯量异质度/扰动位置/电气距离)+ Kundur 线性化小信号机理段 + 文献谱系重写 | 低-中 | 3 区稳,2 区可期 |
| C2 | 弱电网泛化轴:SCR/渗透率扫描,问"差动配置增益何时塌掉"(对接 OP3、Xin 等问题[10]) | 管线 90% | 系统强度改造 + 一轮训练/评估 | 中 | 单独成文偏薄,建议并入 C1 作验证轴 |
| C3 | 稳定证书升级:hard zero-sum/slew → Lyapunov/barrier 证书(对接 OP4、Shuai[38]) | 约束设计 | 理论推导 + 构造 Lyapunov 候选 | 中-高 | 加分项,建议作 C1 的一节而非主轴 |
| C4 | FRT/暂态稳定(分支 F) | 少量 | 全新故障/限流建模与管线再验证 | 高 | 不建议第一篇 SCI |

**推荐结构**:C1 为主轴、C2 为其泛化验证段、C3 视进度作为一节。论文骨架 = "经典谱系提出空间配置问题(引[2][4][6])→ 我们用因果实验证明实时差动配置确有增益(沿用[16]证据)→ 小信号分析解释增益来源与决定量 → 弱电网扫描给出边界 → (可选)约束设计向稳定证书的工程逼近"。**差异化要点(对 Yang[15] 与 Ge[21] 两篇最近先行工作的防御)**:他们没有 matched 集中式基线、没有总量/空间解耦、没有预封存评估,你有;他们没有机理刻画,你新增。

**目标期刊候选**(按语料中同类工作的发表地推断;中科院分区每年浮动,投稿前务必查当年 LetPub/官方表):IJEPES、Electric Power Systems Research、IET Generation Transmission & Distribution、IET Renewable Power Generation、Journal of Modern Power Systems and Clean Energy、IEEE Access(保底)。[unconfirmed: 未逐一核实当年分区]

**给 PI 的话(verbatim 建议写入手稿 cover letter 思路)**:本文不是又一篇"RL 调 VSG"论文;它回答经典 inertia placement 文献留下的实时配置问题,并用满足当前可复现性批评标准的证据回答;负结果(MARL 无增量)作为方法论贡献如实保留。

## 8. 能力降级与局限说明

- 会话禁用子代理,五视角串行执行;覆盖完整性依赖关键词设计,可能遗漏非英文与未被 Scholar 索引的工作。
- IEEE 正文付费墙,多数结论基于摘要 + 第三方综述转述,已按 §2 证据等级降格表述;引文被引数为 Google Scholar 近似值,随时间变化。
- 未检索中文核心/学位论文库;未核实期刊当年中科院分区。

## 参考文献(均经独立交叉核验)

[1] F. Milano, F. Dörfler, G. Hug, D. J. Hill, G. Verbič, "Foundations and challenges of low-inertia systems," PSCC, 2018.
[2] B. K. Poolla, S. Bolognani, F. Dörfler, "Optimal placement of virtual inertia in power grids," IEEE Trans. Smart Grid, 2017.
[3] D. Groß, S. Bolognani, B. K. Poolla, F. Dörfler, "Increasing the resilience of low-inertia power systems by virtual inertia and damping," IREP, 2017.
[4] B. K. Poolla, D. Groß, F. Dörfler, "Placement and implementation of grid-forming and grid-following virtual inertia and fast frequency response," IEEE Trans. Power Syst., 2019.
[5] F. Dörfler, D. Groß, "Control of low-inertia power systems," Annu. Rev. Control Robot. Auton. Syst., 2023.
[6] A. Adrees, J. V. Milanović, "Effect of inertia heterogeneity on frequency dynamics of low-inertia power systems," IET Gener. Transm. Distrib., 2019.
[7] M. Tuo, X. Li, "Security-constrained unit commitment considering locational frequency stability in low-inertia power grids," IEEE Trans. Power Syst., 38(5):4134–4147, 2023.
[8] C. Liyanage, L. Meegahapola et al., "Strategic placement of grid-forming inverters considering spatiotemporal dynamics and composite stability index," IEEE Open J., 2025.
[9] Z. Wang, Y. Shan, Y. Zhu, R. Liu, Y. Gu, "Spatio-temporal frequency distribution analysis in systems with grid-forming and grid-following inverters," IEEE Access, 2025.
[10] H. Xin, C. Liu, X. Chen, Y. Wang et al., "How many grid-forming converters do we need? A perspective from small signal stability and power grid strength," IEEE Trans. Power Syst., 2024.
[11] M. Chen, D. Zhou, C. Wu, F. Blaabjerg, "Characteristics of parallel inverters applying virtual synchronous generator control," IEEE Trans. Smart Grid, 12(6), 2021.
[12] Y. Wang et al., "Low-frequency oscillation in power grids with virtual synchronous generators: A comprehensive review," Renew. Sustain. Energy Rev., 207:114921, 2025.
[13] S. Fu et al., "Power oscillation suppression in multi-VSG grid with adaptive virtual inertia," Int. J. Electr. Power Energy Syst., 2022.
[14] X. Gao, D. Zhou, A. Anvari-Moghaddam, F. Blaabjerg, "An adaptive control strategy with a mutual damping term for paralleled virtual synchronous generators system," Sustain. Energy Grids Netw., 38:101308, 2024.
[15] Q. Yang, L. Yan, X. Chen, Y. Chen, J. Wen, "A distributed dynamic inertia-droop control strategy based on multi-agent deep reinforcement learning for multiple paralleled VSGs," IEEE Trans. Power Syst., 38(6):5598–5612, 2023.
[16] Y. Wei, Y. Wang, Z. Xu, "Decoupling-oriented coordination of paralleled VSGs with multi-agent reinforcement learning," ICEMS 2026(作者会议论文).
[17] Y. Li, W. Gao, S. Huang, R. Wang, W. Yan et al., "Data-driven optimal control strategy for virtual synchronous generator via deep reinforcement learning approach," J. Mod. Power Syst. Clean Energy, 9(5):919–929, 2021.
[18] O. Oboreh-Snapps, B. She, S. Fahad et al., "Virtual synchronous generator control using twin delayed deep deterministic policy gradient method," IEEE Trans. Energy Convers., 39(2):214–228, 2023.
[19] C. Lu, X. Zhuan, "Adaptive control for virtual synchronous generator parameters based on soft actor critic," 2024.
[20] Deep and reinforcement learning in virtual synchronous generator: A comprehensive review, 2024.
[21] L. Ge, Y. Qi, Y. Guo, L. Hou, S. Wan, H. Bai et al., "A MADRL driven optimization framework for grid node inertia and grid-forming converter damping characteristics in microgrids," IEEE Trans.(early access), 2026.
[22] L. Zeng, M. Sun, "Bridge the sim-to-real gap in virtual synchronous generator-based frequency control with robust deep reinforcement learning," IEEE Trans. Power Syst., 2026.
[23] T. Hu, W. Liu, X. Zhang, "Reinforcement learning-based virtual inertia pinning control for heterogeneous VSGs," IEEE Trans. Sustainable Energy, 2026.
[24] Sources of irreproducibility in machine learning: A review, 2022.
[25] G. Dulac-Arnold et al., "Challenges of real-world reinforcement learning: definitions, benchmarks and analysis," Mach. Learn., 2021.
[26] Deep reinforcement learning for power converter control: A comprehensive review of applications and challenges, IEEE Trans.(2025).
[27] T. Su, T. Wu, J. Zhao, A. Scaglione et al., "A review of safe reinforcement learning methods for modern power systems," Proc. IEEE, 2025.
[28] X. Lyu, Y. Xiao, B. Daley, C. Amato, "Contrasting centralized and decentralized critics in multi-agent reinforcement learning," arXiv:2102.04402, 2021.
[29] 例:D. Cao et al., "Data-driven multi-agent deep reinforcement learning for distribution system decentralized voltage control with high penetration of PVs," IEEE Trans. Smart Grid, 2021.
[30] Q. Liu, M. Zhan, X. Yao et al., "Small-signal weak-grid instability of grid-forming converters considering DC-capacitor voltage dynamics," IET Power Electron., 2026.
[31] Small-signal stability assessment and enhancement of grid-following/grid-forming hybrid systems, 2025.
[32] Grid forming converters for low inertia systems − capabilities and limitations: A critical review, 2025.
[33] A. Ordoño Murillo, A. Sánchez Ruiz et al., "Current limiting strategies for grid forming inverters under low voltage ride through," Renew. Sustain. Energy Rev., 202:114657, 2024.
[34] X. He, M. A. Desai, L. Huang et al., "Cross-forming control and fault current limiting for grid-forming inverters," IEEE Trans., 2024(arXiv:2404.13376).
[35] A. J. Aliyu, R. Kannan, "Comprehensive review of fault ride-through techniques for grid-forming inverters," Eng. Res. Express, 2025.
[36] Transient stability-enhancing method for grid-forming inverters under current limiting, 2025.
[37] J. Feng, Y. Shi, G. Qu, S. H. Low et al., "Stability constrained reinforcement learning for decentralized real-time voltage control," IEEE Trans. Control Netw. Syst., 2023.
[38] H. Shuai, B. She, J. Wang, F. Li, "Safe reinforcement learning for grid-forming inverter based frequency regulation with stability guarantee," J. Mod. Power Syst. Clean Energy, 2024.
[39] ENTSO-E Phase II technical report on GFM requirements(2025-11,含 synthetic inertia 规格);GB 稳定性市场(2023-10);德国瞬时备用市场化采购(2026-01)——经 arXiv:2607.22274v1 §1.2 转述核验.
[40] EirGrid/SONI, "All-Island Grid Forming Strategy," 2026-02.
[41] AEMO, "Voluntary specification for grid-forming inverters," 2023.
[42] UNIFI Consortium, "Specifications for grid-forming inverter-based technologies, v2," 2024.

---
*生成方式说明:本报告由 deep-research 流程产出(五视角串行检索 + 逐条交叉核验 + 对抗性自审),语料 CSV 存于 `paper/sci_upgrade_survey/corpus/`。*
