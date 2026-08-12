# 从同步电网频率控制到 VSG–储能有功端口：概念边界与当前路线判断

## 摘要

本文回答三个相互关联的问题：传统同步电网如何控制频率；惯量、阻尼和下垂参数是否为常数；在 VSG 系统中加入储能并直接控制有功功率，是否背离了 VSG 提供惯量的初衷。结论是：传统电网依靠“惯性响应—一次调频—二次调频—三次调度”的多层体系，而不是由一个固定增益完成控制。单台同步机的转动惯量在短时尺度上近似固定，但系统总惯量随在线机组组合变化；等效阻尼随负荷构成、运行点和控制器而变；下垂系数是可配置的控制参数。VSG 也不只是一个“惯量模块”，而是一类用内部电压相量和同步机式动态形成电网的变流器控制。虚拟惯量只有在直流侧存在可用功率和能量时，才能兑现成交流侧响应。因此，储能有功控制并不天然背离 VSG；若储能是同一 VSG 的能源端口，或其功率指令进入 VSG 的摆动功率平衡，它恰恰是虚拟惯量和频率支撑的物理实现。只有当储能作为独立的锁相跟网电流源运行时，才应将其称为储能快速频率响应或辅助阻尼，而不是 VSG 本身。对当前仓库路线而言，四个动作已进入四台 VSG 代理模型各自的有功参考/机械功率平衡，而非独立 ESD1 储能对象；概念上没有放弃 VSG，但模型仍是正序机电代理，尚不能等同于经过变流器、电池和限流验证的一体化 VSG–BESS。

## 1. 研究问题

本文冻结以下三个问题：

1. 普通同步电网的有功—频率控制由哪些层次组成？
2. \(J/H\)、\(M\)、\(D\)、下垂 \(R\) 或其增益 \(G_D=1/R\) 是否为常数？
3. VSG 增加储能并控制有功功率，是实现虚拟惯量的必要能源路径，还是已经变成了另一个研究对象？

这里将用户所说的“GD”同时按两种常见含义处理：一是 VSG 的惯量—阻尼参数 \(J/M,D\)；二是下垂增益 \(G_D=1/R\)。这几类量的物理性质不同，不能混为一个常数。

## 2. 调研方法与证据边界

本调研优先使用电网可靠性机构的控制指南、IEEE 论文和具有明确物理模型的原始研究。证据按四个主题交叉核验：同步电网频率层级、低惯量机理、grid-forming/VSG 定义、储能功率与能量约束。本文不把单一仿真论文的性能结果外推为行业共识，也不把当前仓库中的正序机电模型表述为完整变流器硬件。

## 3. 普通电网不是用一个参数控制，而是多层接力

### 3.1 有功—频率控制

一次负荷增加后，发电机的机械输入功率不会瞬间同步增加，电磁功率却立即改变，因而先出现机械—电气功率不平衡。随后各层依次接力 [1]–[4]：

| 层次 | 主要来源或控制器 | 典型尺度 | 作用与局限 |
|---|---|---:|---|
| 惯性响应 | 在线同步转子的动能；或具备能源余量的变流器快速响应 | 周期至数秒 | 限制初始频率变化率并延缓最低点；不能补偿持续能量缺口 |
| 一次调频 | 调速器下垂、频率敏感负荷、快速频率响应 | 数秒至约一分钟 | 制止频率继续下降并建立新平衡；通常保留稳态频差 |
| 二次调频 | 自动发电控制/负荷频率控制，根据频率和联络线偏差改变功率给定 | 数十秒至数分钟 | 恢复额定频率和计划联络线交换，并释放一次调频 |
| 三次控制 | 备用调用、再调度、机组组合和能量恢复 | 十几分钟至数小时 | 恢复备用和能量状态，为后续扰动重新准备 |

因此，同步机的惯量只负责最早的一棒。调速器改变原动机输入，二次控制再改变机组功率参考，三次调度则解决持续能源和备用问题。只增加惯量而没有后续功率补给，会使频率下降得更慢，却不能消除长期功率缺口。

### 3.2 无功—电压控制是另一条轴

同步机励磁系统和自动电压调节器控制端电压与无功功率，电力系统稳定器通过励磁通道增加机电振荡阻尼；变压器分接头、并联电容/电抗器和 FACTS 装置在更慢尺度上协调电压。频率具有较强的全系统耦合性，电压则更局部。VSG 若要完整模仿同步机，除了有功—频率通道，还应考虑电压相量、无功—电压调节、同步和限流，而不是只给摆动方程加一个惯量参数 [5]–[8]。

## 4. 哪些参数近似恒定，哪些不是

### 4.1 \(J\)、\(H\) 与 \(M\)：单机短时近似固定，系统层面不是常数

同步机摆动方程常写为

\[
J\omega_0\dot{\Delta\omega}
=\Delta P_m-\Delta P_e-D\Delta\omega,
\]

或在标幺值下写成

\[
2H\dot{\Delta\omega}_{pu}
=\Delta P_m-\Delta P_e-D\Delta\omega_{pu}.
\]

\(J\) 由转子和同轴机械系统的质量与几何决定；对一台轴系不变的同步机，在一次事件的短时间内可近似看作物理常数。\(H\) 是额定转速下储存动能相对于机组容量的归一化量，也通常作为固定机组参数。

但系统总动能为

\[
E_{k,\mathrm{sys}}(t)
=\sum_{i\in\mathcal G_{\mathrm{online}}(t)}H_iS_i,
\]

所以系统等效惯量会随机组启停、同步调相机状态、区域分割和电力电子资源比例变化。把 Kundur 仿真窗口中的 \(M\) 固定，是冻结运行点的模型选择，不代表现实电网的聚合惯量永远不变 [1], [3], [9]。

### 4.2 \(D\)：通常是等效线性化斜率，不是材料常数

\(D\) 可能汇总机械摩擦、阻尼绕组、电气阻尼、频率敏感负荷和未显式建模控制的贡献。若表示负荷阻尼，可写成运行点附近的斜率

\[
D_L=\left.\frac{\partial P_L}{\partial \omega}\right|_{\mathrm{op}}.
\]

感应电机、泵、风机、恒功率电力电子负荷和变频器负荷的比例改变时，这个斜率也会改变。工程小信号模型常在一个运行点把 \(D\) 冻结为常数，是为了可分析与可仿真；它不是跨季节、跨负荷构成和跨扰动幅值都精确不变的物理量 [1], [4], [9]。

### 4.3 下垂 \(R\) 或 \(G_D=1/R\)：可配置，但实际响应还受余量限制

下垂关系可写成

\[
R_i=-\frac{\Delta f/f_0}{\Delta P_i/P_{i,\mathrm{base}}},
\qquad G_{D,i}=\frac{1}{R_i}.
\]

它是调速器或变流器控制器的设定值，不是自然常数。运行中通常在一段时间内保持固定，但可以按机组类型、地区要求和运行策略重新配置。即使面板上的 \(R_i\) 不变，实际一次响应还取决于死区、上调余量、阀门和温度限制、爬坡率、原动机时延与电厂上层控制。因此，固定下垂只等于固定控制斜率，不等于系统在所有事件中都有固定的有效频率响应 [1], [2]。

### 4.4 VSG 的 \(J_v,D_v,R_v\)：软件参数，可以固定，也可以调度

VSG 中的虚拟惯量和虚拟阻尼是控制参数。早期 synchronverter/VSM 研究已经明确展示了这些参数的可选择性，后续研究还研究了时变惯量、自适应惯量和联合惯量—阻尼设计 [6], [10], [11]。所以“固定 \(M/D\)”是常见实现，不是 VSG 的定义要求；反过来，参数可以变化也不意味着一定应该用强化学习调节。若系统对这些参数缺乏足够灵敏度，或强控制器已经耗尽可改善余量，在线调参仍可能没有价值。

## 5. 低惯量理解中需要补上的两点

用户的主线判断是正确的：大量同步机退出后，电网可直接看到的旋转动能减少，扰动后的频率变化通常更快 [3], [9]。但需要两点修正。

第一，风机并非没有旋转质量。其叶轮、齿轮箱和发电机储存了动能，但电力电子接口和控制通常把机械转速与电网频率解耦；若不通过专门控制释放，这部分动能不会自动表现为同步惯性。光伏本身没有旋转动能，但可通过直流储能或预留发电余量提供快速有功响应。

第二，低惯量问题不只等于“缺少一个 \(H\)”。变流器比例增加还改变同步方式、短路强度、故障电流、限流后的非线性行为、控制器相互作用和电压支撑。因此，GFM/VSG 的职责比“增加惯量”更宽 [5], [8], [12], [16]。

## 6. VSG 究竟提供什么

更准确地说，VSG/VSM 是 grid-forming 控制的一类，而不是所有 GFM 的同义词。其核心是让变流器维护内部电压幅值与相角，使用同步机式功率—频率动态与其他电源同步，并参与有功/无功分担。惯性响应只是其中一个可设计特性。droop-based GFM、VSG/VSM 和 virtual oscillator control 都可形成电网，但内部动态不同 [5], [7], [8]。

VSG 的软件惯量不会产生能量。若频率下降时需要增加交流侧有功输出，则必须满足

\[
\Delta E_{\mathrm{source}}
=\int_{t_0}^{t_1}\Delta P_{ac}(t)\,dt,
\]

并同时服从直流侧功率、SOC、爬坡率、变流器电流和电压限制。能量可来自电池、超级电容、飞轮、直流母线电容、风机转子，或风光预留的有功余量。NERC 的 GFM 与快速频率响应报告均强调：控制形式不创造功率和能量，响应能力取决于实时 headroom 及物理限制；其面向 BESS 的建议进一步把直流母线储能视为 BESS 实现 GFM 属性的必要前提 [3], [5], [17]。物理 VSM–BESS 实验也表明，即便设置相同的等效惯量常数，VSM 与同步机的完整瞬态仍不必完全相同 [18]。

## 7. 为什么“控制有功功率”不等于背离惯量

把虚拟摆动方程写成

\[
M_v\dot{\Delta\omega}
=\Delta P_{\mathrm{ref}}-\Delta P_e-D_v\Delta\omega,
\]

可以看出两类动作的区别：

- 调 \(M_v,D_v\)：改变内部振荡器把功率失衡映射为频率/相角动态的方式；
- 调 \(P_{\mathrm{ref}}\)：直接改变虚拟“原动机”或直流能源向摆动功率平衡提供的有功输入。

从外部电网看到的惯性样响应本来就是快速有功功率交换。按常见符号约定，其目标形状近似为

\[
\Delta P_{\mathrm{support}}
\approx-K_{\dot f}\dot{\Delta f}-K_f\Delta f.
\]

前一项具有 inertia-like 特征，后一项更接近阻尼或下垂。积分或更慢的 \(P_{\mathrm{ref}}\) 调节则更接近二次恢复。因而，有功功率是惯性功能的外在执行量；问题不在“有没有控制有功”，而在“由谁生成电压相角、功率指令进入哪一个物理端口、能量从哪里来，以及论文把它称为什么” [3], [5], [13], [15]。

直接 \(P_{\mathrm{ref}}\) 和调节 \(M/D\) 可能在某些小信号条件下产生相似频率响应，但不全局等价。前者是加性功率/转矩输入，通常动作权威更直接；后者是参数化、状态相关的动态作用，接近同步点时灵敏度可能很弱。两者在内部相角、饱和、限流、直流能量、因果性、无功和电压行为上可能明显不同 [7], [13]。

## 8. “VSG＋储能有功控制”的三种架构

| 架构 | 谁形成电压相角 | 储能功率进入哪里 | 是否仍可称 VSG | 论文安全表述 |
|---|---|---|---|---|
| A. 一体化 VSG/GFM–BESS | 同一 VSG/GFM 控制器 | 同一变流器直流能源端口或摆动方程的 \(P_{\mathrm{ref}}\) | 是；储能是虚拟原动机和能量来源 | energy-constrained VSG/GFM active-power reference；storage-backed VSG |
| B. VSG 加辅助储能控制 | VSG 保持形成电压；辅助储能可能由另一控制器执行 | 额外的有功支撑、阻尼或二次恢复通道 | 整体可称 storage-assisted VSG system，但辅助控制本身不一定是 VSG | storage-assisted frequency support/damping of a VSG system |
| C. 独立 GFL 储能 | 储能通过锁相环跟随已有电网 | 独立电流源式有功注入 | 储能本身不是 VSG/GFM | BESS fast frequency response 或 distributed storage active-power control |

这一区分解释了为何同样是“储能输出有功”，学术含义可以完全不同。A 没有偏离 VSG，反而把虚拟惯量的能量来源补完整；B 是混合架构，需分清每项贡献；C 改变了控制对象，不能再把储能智能体的动作称为 VSG 惯量/阻尼优化 [5], [12]–[14], [17]–[20]。Gerini 等在电网级 GFM–BESS 实验中证明，上层优化产生有功设定并不会自动取消 GFM 身份；关键是该设定被转换为同一 GFM 变流器的可行控制状态 [19]。Zuo 等在相同 BESS 上比较 GFM 与 GFL 控制，也说明相近的有功—频率服务并不代表相同的同步结构和动态对象 [20]。

## 9. 对当前仓库路线的具体判断

### 9.1 旧 Model-First 储能线确实改变了对象

旧路线使用与 VSG 分开的 ESD1 储能对象和边/聚合控制。其学习或确定性动作直接作用于独立储能有功，而不是四台 VSG 各自的内部 \(M/D\) 或功率平衡。因此，该路线更准确的含义是“含 VSG 系统中的分布式储能协调”，而不是“一台 VSG 一个智能体”。若保留原 VSG 多智能体题目，控制对象与题目会错位。

### 9.2 当前四端口继承线在概念上没有放弃 VSG

当前实现与旧 ESD1 路线不同。R371–R373 的证据表明：四个动作分别写入四个 governor-free GENCLS VSG 代理的 `SynGen.pref`/`tm` 功率平衡端口；旧 (M/D) 动作固定为零；能量账本根据实际转矩与转速结算；没有另行实例化独立 ESD1。由此，当前动作可解释为每台 VSG 自有的、受能量约束的虚拟原动机/有功参考端口。

因此，这条线并非“VSG 不做惯量，另加一块电池做 unrelated control”。更准确的物理解释是：VSG 的内部同步机式动态仍负责频率/相角关系，储能端口负责向每台 VSG 的功率平衡兑现可用的有功功率。

### 9.3 但当前模型还不能称为经过验证的一体化 VSG–BESS

R371–R373 同时限定：当前端口是正序 GENCLS 的机电机械转矩代理加外部能量账本，没有建模变流器内环、直流母线、电池动态、无功/电压控制、热约束、保护与硬件限流。因此，当前论文最安全的对象表述是：

> four VSG-owned, energy-constrained active-power-reference ports in a positive-sequence electromechanical proxy

而不应直接升级为“已验证的实际一体化 VSG–BESS 控制器”。R375 发现冻结的确定性功率参考控制触发爬坡投影，R382 又没有建立固定题目所要求的联合解耦余量；所以本概念澄清不能重启已经停止的训练，也不能补出当前缺失的 MARL 证据。

## 10. 综合回答与研究含义

1. 普通电网的频率控制不是靠固定的 (G,D) 或 (M,D)，而是惯性、一次、二次、三次控制分层接力。
2. 单机 (J/H) 在短时近似固定；系统惯量随在线机组变化；(D) 是运行点相关的等效参数；下垂 (R) 或 (G_D) 是可配置的控制设定。
3. VSG 的本质不只是“增加惯量”，而是用变流器形成电压相角并以同步机式动态参与同步、功率分担、频率和电压支撑。
4. 虚拟惯量的外在效果就是快速有功交换；储能为它提供真实能量。因此“一体化 VSG 控制储能有功”在物理上通常不是偏离，而是把能量来源补全。
5. 真正偏离发生在对象层：如果神经网络只控制一个独立 GFL 储能装置，而四台 VSG 本身没有各自的动作端口，就不能继续把结果称为四 VSG 多智能体控制。
6. 当前仓库的四个 VSG-owned power ports 在概念上通过了这一对象区分，但未通过最终控制价值门，也未达到完整变流器/BESS 物理保真度。因此，论文当前的核心困难不是“用了有功功率所以不再是 VSG”，而是“现有代理模型和实验尚未证明四智能体学习在强基线之上存在可发表增量”。

## 11. 开放问题

后续若重构题目或实验，需要先选择并冻结架构 A、B、C，而不是再从算法开始：

1. 四个储能是否物理上位于四个 VSG 的同一直流侧，并由同一 GFM/VSG 电压相角控制器驱动？
2. 智能体动作是 (M/D)、VSG 内部 (P_{\mathrm{ref}})，还是独立 GFL BESS 的 (P) 指令？
3. 论文要证明 inertia-like response、阻尼、一次调频、二次恢复，还是区域解耦？不同目标需要不同时间尺度、指标和能量预算。
4. 正序 GENCLS 代理得到正结果后，能否在包含直流源、变流器限流和电压/无功环节的更高保真模型中保持？
5. 在同一动作权限、信息和约束下，强经典控制到非学习 oracle 是否仍有足够余量？若无，继续训练不会解决对象层问题。

## 12. 结论

把 VSG 理解成“增加一个虚拟惯量常数”过于狭窄。同步机惯性本身就是动能经有功功率通道释放；VSG 要复制这种行为，也必须连接真实能源和受约束的功率端口。储能不是对 VSG 的背叛，而往往是 VSG 频率响应得以兑现的能源基础。论文是否仍属于 VSG，取决于控制架构和动作归属，而不是是否出现了 (P_{\mathrm{ref}})。对当前路线，最准确的判断是：对象概念仍可保持为 VSG-owned active-power control，但证据只到机电代理与有界功率端口，且当前固定题目的联合学习增量仍未建立。

## 参考文献

[1] North American Electric Reliability Corporation, *Primary Frequency Control Reliability Guideline*, Version 4.0, 2023.

[2] North American Electric Reliability Corporation, *Balancing and Frequency Control*, 2021.

[3] North American Electric Reliability Corporation, *Fast Frequency Response Concepts and Bulk Power System Reliability Needs*, 2020.

[4] ENTSO-E/UCTE, *Policy 1: Load-Frequency Control and Performance*, 2009.

[5] North American Electric Reliability Corporation, *Grid Forming Technology: Bulk Power System Reliability Considerations*, 2021.

[6] Q.-C. Zhong and G. Weiss, “Synchronverters: Inverters That Mimic Synchronous Generators,” *IEEE Transactions on Industrial Electronics*, vol. 58, no. 4, pp. 1259–1267, 2011.

[7] S. D'Arco and J. A. Suul, “Equivalence of Virtual Synchronous Machines and Frequency-Droops for Converter-Based MicroGrids,” *IEEE Transactions on Smart Grid*, vol. 5, no. 1, pp. 394–395, 2014.

[8] N. Hatziargyriou et al., “Definition and Classification of Power System Stability—Revisited & Extended,” *IEEE Transactions on Power Systems*, vol. 36, no. 4, pp. 3271–3281, 2021.

[9] A. Ulbig, T. S. Borsche, and G. Andersson, “Impact of Low Rotational Inertia on Power System Stability and Operation,” *IFAC Proceedings Volumes*, vol. 47, no. 3, pp. 7290–7297, 2014.

[10] J. Alipoor, Y. Miura, and T. Ise, “Power System Stabilization Using Virtual Synchronous Generator With Alternating Moment of Inertia,” *IEEE Journal of Emerging and Selected Topics in Power Electronics*, vol. 3, no. 2, pp. 451–458, 2015.

[11] D. Li, Q. Zhu, S. Lin, and X. Y. Bian, “A Self-Adaptive Inertia and Damping Combination Control of VSG to Support Frequency Stability,” *IEEE Transactions on Energy Conversion*, vol. 32, no. 1, pp. 397–398, 2017.

[12] B. Kroposki et al., *Research Roadmap on Grid-Forming Inverters*, National Renewable Energy Laboratory, 2020.

[13] A. Poolla, D. Groß, and F. Dörfler, “Placement and Implementation of Grid-Forming and Grid-Following Virtual Inertia and Fast Frequency Response,” *IEEE Transactions on Power Systems*, vol. 34, no. 4, pp. 3035–3046, 2019.

[14] M. Torres L., L. A. C. Lopes, L. A. Morán T., and J. R. Espinoza C., “Self-Tuning Virtual Synchronous Machine: A Control Strategy for Energy Storage Systems to Support Dynamic Frequency Control,” *IEEE Transactions on Energy Conversion*, vol. 29, no. 4, pp. 833–840, 2014.

[15] R. Eriksson, N. Modig, and N. Elkington, “Synthetic Inertia Versus Fast Frequency Response: A Definition,” *IET Renewable Power Generation*, vol. 12, no. 5, pp. 507–514, 2018.

[16] A. Tayyebi, F. Dörfler, F. Kupzog, Z. Miletic, and W. Hribernik, “Grid-Forming Converters—Inevitability, Control Strategies and Challenges in Future Grids Application,” *IEEE Journal of Emerging and Selected Topics in Power Electronics*, vol. 8, no. 2, pp. 1779–1790, 2020.

[17] North American Electric Reliability Corporation, *The Need for Widespread Implementation of Grid Forming Technology in All Future Registered Battery Energy Storage Resources*, 2023.

[18] M. A. U. Khan et al., “Experimental Assessment and Validation of Inertial Behaviour of Virtual Synchronous Machines,” *IET Renewable Power Generation*, vol. 16, no. 9, pp. 1897–1907, 2022.

[19] F. Gerini, Y. Zuo, R. Gupta, E. Vagnoni, R. Cherkaoui, and M. Paolone, “Optimal Grid-Forming Control of Battery Energy Storage Systems Providing Multiple Services: Modeling and Experimental Validation,” *Electric Power Systems Research*, vol. 212, article 108567, 2022.

[20] Y. Zuo, Z. Yuan, F. Sossan, A. Zecchino, R. Cherkaoui, and M. Paolone, “Performance Assessment of Grid-Forming and Grid-Following Converter-Interfaced Battery Energy Storage Systems on Frequency Regulation in Low-Inertia Power Grids,” *Sustainable Energy, Grids and Networks*, vol. 27, article 100496, 2021.
