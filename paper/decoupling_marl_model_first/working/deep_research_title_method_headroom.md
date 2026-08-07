# “解耦＋分布式多智能体”为什么在当前方法上失配：强基础控制之后的剩余学习空间诊断

状态：论文线专属深度研究工作稿；不构成实验新证据，也不改变正式门控结论。  
日期：2026-08-06  
对应论文线：`decoupling-marl-model-first`

## 摘要

本报告研究三个问题：当前会议论文题目中的“解耦导向”“并联虚拟同步机协调”和“多智能体强化学习”分别承诺了什么；现有模型优先方法为什么尚未兑现这些承诺；以及为什么强确定性控制之后会出现“神经网络没有优化空间”的现象。对控制、并联虚拟同步机、分布式二次控制、残差强化学习、多智能体学习和强化学习实验方法的一手文献进行交叉核验后，核心判断是：**当前困难不是单纯的网络容量或优化算法问题，而是题目承诺、受控对象、基础控制器的信息条件、残差动作空间和部署时可见信息没有对齐。** 本项目的正式结果进一步把这一判断分成两层：全信息、事后看见结果的理想残差仍存在很小的名义改进方向，但邻居局部信息无法把该方向稳定转化为联合改善。因此，现有证据只支持“当前残差形式和信息路径不值得训练”，不支持“神经网络普遍无用”。更严重的是，已经通过验证的基础控制器是全输出集中式控制器，而题目要求的是分布式多智能体协调；它可以作为上界诊断，却不能代替论文主张中的匹配分布式基线。若题目保持不变，就必须重新建立真实分布式基础控制、匹配信息和动作权限，并用新的非学习门证明仍有可学习空间；若不再增加这条证据链，题目应转向模型优先的剩余价值判别或集中式共同—差异坐标控制。

## 1. 引言

当前工作题目是 *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning*。这个题目同时包含四个容易被审稿人分别追问的对象：什么被解耦、哪些设备算“并联虚拟同步机”、协调是否在运行时真正分布式、强化学习是否产生了超过强基础控制的可测增量。

已有研究已经直接提出“multiple paralleled VSGs + distributed dynamic inertia-droop + multi-agent deep reinforcement learning”[5]。因此，仅仅把并联虚拟同步机、分布式控制和多智能体强化学习放进同一个系统，不足以形成新贡献。当前论文必须把新意落在更窄而可检验的机制上，例如共同—差异坐标下的交叉耦合测量、匹配信息预算的因果比较、训练前剩余价值门，或者受约束残差的安全继承。

本报告回答以下问题：

- **RQ1：**“解耦导向”和“分布式多智能体协调”最低需要哪些闭环证据，当前方法缺少什么？
- **RQ2：**强确定性控制之后，神经网络的有效优化空间通过哪些环节被压缩？
- **RQ3：**结合本项目 R344 和 R350 的正式结果，原题目应保留、重构还是降级？

## 2. 方法

检索在 2026-08-06 进行，覆盖五个视角：并联虚拟同步机功率耦合与振荡；微电网分布式二次控制；残差强化学习与模型控制结合；部分可观测多智能体学习与信用分配；强化学习的统计评价和实现混杂。主要关键词组合包括 `virtual synchronous generator + decoupling`、`paralleled VSG + oscillation`、`distributed secondary control + microgrid`、`residual reinforcement learning + controller`、`centralized training decentralized execution`、`partial observability + multi-agent credit assignment` 和 `deep RL statistical evaluation`。

只纳入能由正式出版页、会议论文页或作者公开稿核验标题、作者和结论边界的一手研究。最终语料包含 31 篇核心论文，其中解耦／分布式控制 10 篇，残差与安全学习 10 篇，多智能体可辨识性与实验评价 11 篇；部分论文横跨两个分支。内部事实只取自当前论文线的模型合同和正式实验报告 R344、R350。外部文献用于解释机制和既有工作，不用于升级内部证据。

证据类型及其用途如下：

| 类型 | 本报告如何使用 | 不能推出什么 |
|---|---|---|
| 控制理论与闭环分析 | 界定“解耦”“分布式”“稳定性”的最低技术含义 | 不能证明本项目控制器已经满足条件 |
| 仿真或实验型控制论文 | 比较已有架构、观测和动作路径 | 不能证明其结论跨任务、跨拓扑成立 |
| 强化学习方法论文 | 解释残差、部分可观测、信用分配和训练方差 | 不能替代本项目的物理干预 |
| 本项目正式报告 | 判断当前路线是否授权训练及题目词是否有证据 | 不能推广为神经网络或多智能体方法的普遍结论 |

## 3. 分类框架：题目承诺、物理空间、信息空间和统计空间

本问题不能只按“经典控制对强化学习”二分。更有解释力的分类是四层：

1. **题目承诺层：**论文声称控制了什么对象、解决了什么耦合、以什么方式分布式执行。
2. **物理优化层：**在相同执行器、限制和场景下，基础控制之后是否仍存在材料性更优动作。
3. **信息可辨识层：**部署时的本地历史和邻居消息能否判断该动作的方向和幅值。
4. **统计训练层：**可实现增益是否高于仿真、场景和训练种子的波动。

可把有效学习空间写成一个诊断性关系，而不是数学定理：

\[
H_{\mathrm{effective}}
\approx
H_{\mathrm{physical}}
\times H_{\mathrm{information}}
\times H_{\mathrm{authority}}
\times H_{\mathrm{statistics}}.
\]

这里，第一项是基础控制后仍可改善多少；第二项是部署信息能否识别改善动作；第三项是安全投影后执行器是否仍能施加不同动作；第四项是这份增益能否从训练噪声中辨认。任一项接近零，扩大网络或增加训练步数都不会自动产生论文价值。

## 4. RQ1：题目中的三个技术词为什么尚未对齐

### 4.1 坐标分解不是动态解耦

把状态改写为共同运动和相对运动坐标，得到

\[
\begin{bmatrix}\dot x_c\\\dot x_d\end{bmatrix}
=
\begin{bmatrix}A_{cc}&A_{cd}\\A_{dc}&A_{dd}\end{bmatrix}
\begin{bmatrix}x_c\\x_d\end{bmatrix}
+Bu,
\]

只证明采用了新的可逆基底。只要交叉块 \(A_{cd}\) 和 \(A_{dc}\) 仍显著，一个方向的扰动仍会激发另一个方向，系统就没有被动态解耦。Wen 等[6]从有功—无功环的物理耦合机理出发设计补偿，并用仿真和实验验证交叉作用降低；Chen 等[8]则直接把构网变流器视为多输入多输出对象，反对未经验证地假设控制环已经解耦。Long 等[9]和 He、Yu[10]同样把线路、虚拟阻抗和弱网条件下的交叉影响纳入控制设计。共同结论是：真正的解耦贡献至少要说明耦合对象、耦合来源、闭环干预和交叉响应降低。

当前模型合同采用“decoupling-oriented”而不是“decoupled”，这是合理的降格：它允许保留真实交叉块。但当前正式状态只支持“共同／差异坐标揭示并保留耦合”，还没有证明控制器降低了注册的交叉耦合量。先前测得的共同／差异交叉增益与自增益之比约为 0.444，已经否定硬解耦叙事。故当前最安全的术语是 **common/differential-coordinate-structured** 或 **coupling-aware**；若坚持 **decoupling-oriented**，正文必须把“目标是降低哪个闭环交叉量”写成明确估计量并给出实验。

### 4.2 “分布式”由运行时因果路径决定

DAPI、分布式二次控制和无下垂分布式控制的共同特征不是“有多台设备”，而是每台设备用本地测量和有限邻居消息更新并施加自己的动作[1–4]。集中训练可以使用全局信息，但部署演员必须只依赖声明的本地或邻居信息；MADDPG、COMA 和 QMIX 的集中训练—分散执行框架都保留了这个边界[21–23]。

因此，下列对象不能混称：

| 运行时对象 | 准确称谓 | 能否支持“分布式多智能体” |
|---|---|---|
| 全局状态进入一个控制器，输出所有设备动作 | 集中协调 | 否 |
| 多个网络输出被聚合为一个共享标量，再统一映射 | 集中标量协调 | 否 |
| 每台设备只看本地量、无通信、独立动作 | 去中心化控制 | 有条件，但不是邻居协同 |
| 本地状态＋声明的邻居消息＋独立设备／边动作 | 分布式协调 | 是，仍需闭环证据 |
| 集中评论器训练，本地演员独立执行 | 集中训练、分散执行 | 是，前提是执行时不再需要全局服务 |

当前已经通过验证的 R344 控制器明确是“集中式、全输出、滚动优化控制器”。它能证明物理模型和受约束控制桥接有效，却不能证明本地信息充分、邻居通信有效或设备动作独立。因此，它只能是上界诊断和开发桥，不是题目中“distributed multi-agent coordination”的主基线。

### 4.3 “并联虚拟同步机”的受控对象和试验平台也有歧义

并联虚拟同步机文献通常直接调节每台虚拟同步机的惯量、下垂、虚拟阻抗或内部功率环，并研究参数不一致造成的机间功率振荡[5,7]。当前平台却是 Kundur 网络中四个空间分离、径向接入的虚拟同步机代理，与四个独立的 ESD1 储能注入成对存在；实际控制命令施加到单独的跟网型储能有功注入，而不是直接修改虚拟同步机内部控制律。

这不意味着外部储能不能帮助同步，但它使题目中的控制对象变得含混：论文究竟是在“协调虚拟同步机”，还是“用外部储能支撑网络化虚拟同步机群”？此外，这些设备不是典型的共同母线并联系统。若不在题目或系统图中澄清，审稿人可能把它视为对象错位。比“paralleled VSGs”更贴近当前平台的词是 **networked VSG proxies with distributed storage support**。

### 4.4 既有工作已经占据题目的表面组合

Yang 等[5]已经推导多台并联虚拟同步机参数失配与功率振荡的关系，并让每个智能体依据本地和相邻设备信息独立调节惯量—下垂参数。换言之，“并联虚拟同步机＋相邻信息＋多智能体强化学习＋分布式动态协调”已经是直接先例。

本论文若仍使用当前题目，贡献不能写成“首次把多智能体强化学习用于并联虚拟同步机协调”。可辨识的新意只能来自至少一项更具体的证据：

- 精确共同／差异坐标与保留交叉块的模型—实现一致性；
- 独立边动作与共同／差异自由度的物理权限证明；
- 在完全匹配的信息、动作和预算下，分离网络因子化与信息局部性的因果比较；
- 训练前证明“存在、可见、可执行、可统计辨认”的剩余学习空间；
- 受安全治理的残差如何继承确定性控制器的约束性质。

当前只有前两项的合同和部分有限场景证据，后面三项尚未完成。

## 5. RQ2：为什么强基础控制之后会“没有神经网络优化空间”

### 5.1 基础控制把同一指标的大部分误差已经消掉

残差学习的经典正面结果并非从“几乎没有问题”的基线中制造收益。Johannink 等[11]把接触和摩擦等模型难以描述的结构化误差留给残差策略；Silver 等[12]有意研究含模型失配、传感器噪声和控制器失调的“好但不完美”基线；Nagabandi 等[13]则利用模型控制的样本效率去弥补其明确存在的最终性能差距。三者共同前提是：剩余问题可重复、可观察且可执行。

R344 相对零控制已经使共同坐标误差平均降低约 95.51%，使差异坐标能量平均降低约 99.33%。这并不意味着数学上只剩 4.49% 和 0.67% 可改善，但说明残差面对的是一个尺度明显收缩、接近指标地板的任务。策略梯度依赖不同动作的优势差：

\[
\nabla J(\theta)
\propto
\mathbb E\!\left[
\nabla_\theta\log \pi_\theta(a\mid o)A(o,a)
\right].
\]

当基础控制已消掉大部分可重复误差时，可行动作之间的 \(A(o,a)\) 也会缩小。Ilyas 等[16]表明实际深度策略梯度估计可能与大样本近似的真实梯度严重失配；Henderson 等[17]和 Agarwal 等[18]则表明随机种子和有限重复足以让小幅改进难以解释。因此可条件性推断：在剩余收益只有几个百分点甚至千分级时，训练信号更容易低于估计方差。

### 5.2 当前残差动作先天不能直接控制共同通道

当前残差使用三条边流：

\[
u^d=B_a r,\qquad \mathbf 1^\mathsf T u^d=0.
\]

它严格保持车队命令的净有功为零，适合重新分配设备间相对功率并抑制差异运动，但不能直接增加或减少车队净有功。共同频率恢复主要由基础控制器的共同通道负责。残差只能通过当前仍存在的共同—差异交叉耦合，间接影响共同坐标误差。

这解释了一个看似矛盾的结果：题目把共同和差异协调都放进目标，而学习动作主要拥有差异自由度。全信息理想优化器仍能利用交叉耦合得到约 2% 的共同指标改善，但这不是一个强、直接、局部可辨认的控制通道。若论文希望学习器同时承担共同恢复，就必须增加有物理净功率权限的共同残差，并重新建立功率、能量和安全合同；若坚持零和边残差，共同通道应被明确归为基础控制责任，学习增量主要评价差异同步和资源分配。

### 5.3 全信息“有一点”不等于局部智能体“学得到”

R350 把这两层直接分开。事后知道完整结果的理想优化器，相对已控制轨迹，名义上仍能把共同指标改善约 2.00%、差异指标改善约 5.14%。共同端点因极小数值差没有越过严格的 2% 门槛，但即使忽略这条边界，后续局部信息和失配门仍然失败，因此最终判断不依赖这一点微小差额。

当只保留部署时的邻居局部信息，留出代理对共同指标只改善约 0.139%，并使差异指标恶化约 14.06%。这说明主要瓶颈不是“物理上完全没有更优动作”，而是 **相同的局部观测不足以稳定区分应当采取的残差方向**。若两个全局状态在局部看来近似相同却要求相反动作，增加网络深度不会恢复输入中缺失的信息。部分可观测表示的不可消除偏差[14]、多智能体环境的非平稳性[21]和信用分配困难[22–24]都与这一机制一致。

### 5.4 基础控制和学习残差拥有不对称的信息

当前比较还有一个必须正面承认的保守性：R344 基础控制器使用全输出集中信息，而 R350 检查的可部署残差只使用邻居局部信息。于是神经残差不是在与自己同等信息条件的基础控制上补缺，而是在尝试补一个已经使用更多信息的集中上界。

这对训练授权是一个合理的保守筛选：若连理想上界之上都没有稳定剩余，没必要大规模训练。但它不能回答论文真正的主问题——“局部多智能体残差是否优于同样只用局部／邻居信息的最强分布式确定性控制器”。因此，R350 的负结论对当前路线有效，却不能升级成“分布式多智能体没有价值”。

### 5.5 安全投影和失配鲁棒性进一步压缩可执行空间

实际执行是

\[
u_{\mathrm{exec}}
=
\operatorname{Proj}_{\mathcal U_{\mathrm{safe}}}
\!\left(u_{\mathrm{base}}+\delta u_\theta\right).
\]

网络输出不同并不保证物理动作不同；限幅、爬坡、荷电状态、电流和能量约束可能把多个输出投影到同一动作。Fujita、Maeda[19]说明动作边界会改变策略梯度的有效统计性质，Chow 等[20]则直接把安全可行集作为动作的状态相关限制。R350 已确认每个理想案例存在物理可行起点、局部投影也可行，所以当前失败不能简单归因于“执行器完全饱和”；但理想和局部方案的失配有界门均失败，说明小幅名义收益无法抵抗模型偏差。

### 5.6 因此，“没有空间”有三种完全不同的含义

| 层次 | 问题 | 当前证据 |
|---|---|---|
| 物理优化空间 | 全信息、事后最优、同约束动作还能否改善？ | 小但非零的名义方向 |
| 可学习信息空间 | 本地／邻居信息能否在留出案例中找到该方向？ | 当前路径失败 |
| 可发表统计空间 | 改进能否抵抗模型失配、场景差异和训练方差？ | 当前路径失败 |

所以，最准确的表述不是“神经网络没有任何优化空间”，而是：**当前确定性控制之后仅剩很小的名义物理余量；当前零和边残差和邻居局部信息不能稳定识别并鲁棒实现这份余量，因此不值得启动神经训练。**

## 6. RQ3：对会议论文题目和方法的判定

### 6.1 当前题目只能作为研究计划，不能作为已被证据支撑的论文标题

对现状的逐词判定如下：

| 题目词 | 当前状态 | 主要问题 |
|---|---|---|
| Decoupling-Oriented | **QUALIFY** | 有共同／差异坐标和耦合测量，但尚无闭环交叉作用降低证据 |
| Paralleled VSGs | **QUALIFY/RENAME** | 平台是网络化、空间分离的 VSG 代理＋单独跟网储能注入；若不明确宽义并联和外部支撑关系，容易被误解为共同母线 VSG 内环控制 |
| Coordination | **QUALIFY** | 集中确定性协调有效；分布式协调尚未执行 |
| Multi-Agent Reinforcement Learning | **BLOCK** | 没有训练、策略、奖励或分布式运行证据，且当前门正式返回不训练 |

因此，题目目前是一个前瞻性研究目标，不是证据已经支撑的会议论文标题。它还与 Yang 等[5]的既有标题和方法高度相邻，增加了新颖性压力。

### 6.2 三条可选路线

**路线 A：保留原题目，重建证据链。** 这是工作量最大但逻辑最完整的路线。先验证真正的邻居协同确定性控制器，使基础控制和残差拥有相同部署信息、相同边动作和相同限制；再分别计算全信息理想残差和邻居信息残差，定位信息损失；根据结果决定是否增加观测历史、邻居消息、资源异质性或共同残差权限。只有新非学习门通过后才训练。还需把平台从“paralleled”改为真实并联系统，或在题目中改成“networked”。

**路线 B：保留现有证据，转成模型优先的负结果／训练价值判别论文。** 贡献不再是“MARL 提升性能”，而是“在安全关键控制中，训练前如何证明剩余价值可见、可执行、可学习”。候选题目可为：

> *When Residual Learning Is Not Worth Training: A Model-First Headroom Gate for Networked VSG Coordination*

这条路线与 R344/R350 最一致，但会议是否接收方法学负结果需要再做场地选择和叙事设计。

**路线 C：去掉学习承诺，写共同—差异坐标的受约束控制论文。** 候选题目可为：

> *Common–Differential Coordinate Control of Networked VSG Proxies With Constrained Storage Support*

这条路线仍需清楚承认 R344 是集中控制，不能写成分布式；若想保留 distributed，仍需补一个真实分布式确定性控制器。

### 6.3 推荐判断

**短期会议论文建议优先路线 B；若题目被要求一字不改，则只能走路线 A，不能用当前结果直接写。** 原因不是负结果“不好看”，而是当前证据恰好揭示了一个有价值且可证伪的问题：什么时候根本不应训练神经网络。相比强行训练并从随机波动中挑增益，这一模型优先门更有方法学完整性。

## 7. 综合讨论：真正的矛盾不是经典控制与神经网络，而是三个上界互相错位

文献和项目结果共同指向三个上界：

1. **控制上界：**强确定性控制器已经消除了大部分注册误差。
2. **动作上界：**零和边残差主要拥有差异自由度，却被要求同时改善共同和差异指标。
3. **信息上界：**全输出集中基础控制使用的信息多于邻居局部残差。

这三个上界叠加，才产生“神经网络没有空间”的表象。只改变算法，例如从 PPO 换成 SAC、从单网络换成多网络，不会改变物理动作子空间，也不会补回不可见的全局状态。Yu 等[25]和 Engstrom 等[31]还说明，简单强基线和代码级实现差异可能比算法标签更影响结果；若没有匹配信息和动作的因果对照，即使训练出现小增益也难以归因于“多智能体”。

反过来，不能为了制造学习空间故意削弱基础控制器。残差学习正面文献的合理做法是把学习任务绑定到一个真实且结构化的缺口，例如难建模接触、模型失配、异质资源分配或安全优化器的快速近似[11–13,29,30]。对当前项目，更合理的候选缺口是：运行点和资源异质性造成的局部配置误差、模型失配下的差异阻尼分配，或分布式优化器在有限通信迭代下的剩余，而不是让网络重新学习已经被集中模型控制解决的共同恢复。

## 8. 开放问题与下一步研究边界

1. **匹配分布式基础控制的空缺。** 当前没有一个已验证的邻居局部确定性控制器作为学习基线。下一轮必须先回答这个非学习问题，不能直接训练。
2. **共同残差权限的空缺。** 若共同指标仍是学习目标，需要证明非零净功率残差的物理必要性、安全权限和能量来源；否则把学习目标限定到差异同步。
3. **观测历史和邻居消息的可辨识性。** 需要用留出案例检验短历史、扰动估计或增加一跳消息能否显著优于常数和线性代理，而不是先选深网络。
4. **单动作通道的因果干预。** 固定其他动作，逐边改变一个动作，验证每个自由度对共同／差异指标的灵敏度高于数值和场景噪声。
5. **分布式真实性。** 若未来训练通过，必须测试延迟、丢包、断链和陈旧消息；理想全局通信不能被称为分布式鲁棒性。
6. **新颖性定位。** 与 Yang 等[5]相比，必须在同一段内明确“我们不再提出一般的 MARL 调参，而是提出训练前可证伪的剩余价值门和匹配执行比较”。
7. **统计材料性。** 新训练若被授权，应根据预实验方差反推种子数，报告区间、性能分布和稳健聚合，而不是单次最好轨迹。

## 9. 结论

**对 RQ1：**当前“decoupling-oriented”只有坐标和机制分析基础，尚无闭环解耦证据；“distributed multi-agent”没有运行时证据；“paralleled VSGs”与现有网络化代理＋单独储能执行器存在对象歧义。题目四个词并未被同一条证据链支撑。

**对 RQ2：**神经网络没有训练价值的直接原因不是表达能力，而是强集中基础控制已大幅压缩剩余误差，零和边残差对共同指标只有间接权限，邻居局部信息又无法稳定识别全信息理想残差，模型失配和训练方差进一步吞没小增益。

**对 RQ3：**R350 有效地阻止了当前残差形式和信息路径的训练，但不能证明多智能体强化学习作为一类方法无效。若保留原题目，必须从真实分布式基础控制和匹配信息比较重新开始；若不补新证据，最诚实且最有研究价值的会议方向是模型优先的“何时不应训练”方法论文。

## References

[1] John W. Simpson-Porco, et al., “Secondary Frequency and Voltage Control of Islanded Microgrids via Distributed Averaging,” IEEE Transactions on Industrial Electronics, 2015.

[2] Florian Dörfler, John W. Simpson-Porco, Francesco Bullo, “Breaking the Hierarchy: Distributed Control and Economic Optimality in Microgrids,” IEEE Transactions on Control of Network Systems, 2016.

[3] Ali Bidram, et al., “Distributed Cooperative Secondary Control of Microgrids Using Feedback Linearization,” IEEE Transactions on Power Systems, 2013.

[4] Vahidreza Nasirian, et al., “Droop-Free Distributed Control for AC Microgrids,” IEEE Transactions on Power Electronics, 2016.

[5] Qiufan Yang, et al., “A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs,” IEEE Transactions on Power Systems, 2023.

[6] Tiliang Wen, et al., “Power Coupling Mechanism Analysis and Improved Decoupling Control for Virtual Synchronous Generator,” IEEE Transactions on Power Electronics, 2021.

[7] Meng Chen, et al., “Active Power Oscillation Damping Based on Acceleration Control in Paralleled Virtual Synchronous Generators System,” IEEE Transactions on Power Electronics, 2021.

[8] Meng Chen, et al., “Generalized Multivariable Grid-Forming Control Design for Power Converters,” IEEE Transactions on Smart Grid, 2022.

[9] Bo Long, et al., “Enhancement of Power Decoupling for Virtual Synchronous Generator: A Virtual Inductor and Virtual Capacitor Approach,” IEEE Transactions on Industrial Electronics, 2023.

[10] Lina He, Shiwen Yu, “Systematic Decoupling Grid-Forming Control for Utility-Scale Inverter-Based Distributed Energy Resources in Weak Distribution Grids,” IEEE Open Access Journal of Power and Energy, 2024.

[11] Tobias Johannink, et al., “Residual Reinforcement Learning for Robot Control,” IEEE International Conference on Robotics and Automation, 2019.

[12] Tom Silver, et al., “Residual Policy Learning,” arXiv:1812.06298, 2018.

[13] Anusha Nagabandi, et al., “Neural Network Dynamics for Model-Based Deep Reinforcement Learning with Model-Free Fine-Tuning,” IEEE International Conference on Robotics and Automation, 2018.

[14] Vincent François-Lavet, et al., “On Overfitting and Asymptotic Bias in Batch Reinforcement Learning with Partial Observability,” Journal of Artificial Intelligence Research, 2019.

[15] Tom Staessens, Tom Lefebvre, Guillaume Crevecoeur, “Optimizing Cascaded Control of Mechatronic Systems through Constrained Residual Reinforcement Learning,” Machines, 2023.

[16] Andrew Ilyas, et al., “A Closer Look at Deep Policy Gradients,” International Conference on Learning Representations, 2020.

[17] Peter Henderson, et al., “Deep Reinforcement Learning That Matters,” AAAI Conference on Artificial Intelligence, 2018.

[18] Rishabh Agarwal, et al., “Deep Reinforcement Learning at the Edge of the Statistical Precipice,” Advances in Neural Information Processing Systems, 2021.

[19] Yasuhiro Fujita, Shin-ichi Maeda, “Clipped Action Policy Gradient,” International Conference on Machine Learning, 2018.

[20] Yinlam Chow, et al., “Safe Policy Learning for Continuous Control,” Conference on Robot Learning, 2021.

[21] Ryan Lowe, et al., “Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments,” Advances in Neural Information Processing Systems, 2017.

[22] Jakob Foerster, et al., “Counterfactual Multi-Agent Policy Gradients,” AAAI Conference on Artificial Intelligence, 2018.

[23] Tabish Rashid, et al., “QMIX: Monotonic Value Function Factorisation for Deep Multi-Agent Reinforcement Learning,” International Conference on Machine Learning, 2018.

[24] Kyunghwan Son, et al., “QTRAN: Learning to Factorize with Transformation for Cooperative Multi-Agent Reinforcement Learning,” International Conference on Machine Learning, 2019.

[25] Chao Yu, et al., “The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games,” Advances in Neural Information Processing Systems, 2022.

[26] Haotian Liu, Wenchuan Wu, “Online Multi-Agent Reinforcement Learning for Decentralized Inverter-Based Volt-VAR Control,” IEEE Transactions on Smart Grid, 2021.

[27] Dong Chen, et al., “PowerNet: Multi-Agent Deep Reinforcement Learning for Scalable Powergrid Control,” IEEE Transactions on Power Systems, 2022.

[28] Han Xu, Jialin Zheng, Guannan Qu, “A Scalable Network-Aware Multi-Agent Reinforcement Learning Framework for Decentralized Inverter-Based Voltage Control,” arXiv:2312.04371, 2023.

[29] Qiong Liu, et al., “Residual Deep Reinforcement Learning With Model-Based Optimization for Inverter-Based Volt-Var Control,” IEEE Transactions on Sustainable Energy, 2024.

[30] Zixiao Ma, Qianzhi Zhang, Zhaoyu Wang, “Safe and Stable Secondary Voltage Control of Microgrids Based on Explicit Neural Networks,” IEEE Transactions on Smart Grid, 2023.

[31] Logan Engstrom, et al., “Implementation Matters in Deep Policy Gradients: A Case Study on PPO and TRPO,” International Conference on Learning Representations, 2020.
