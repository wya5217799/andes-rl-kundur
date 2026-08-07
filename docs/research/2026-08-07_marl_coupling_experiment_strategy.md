# 同一标题下两条多智能体路线的因果诊断与实验策略

**日期：** 2026-08-07  
**性质：** 跨论文线深度研究与实验设计建议；不是实验新证据，不改变任何正式结论，也不授权启动训练或物理仿真。  
**涉及论文线：** `paper/icems2026` 与 `paper/decoupling_marl_model_first`。

## 摘要

本报告回答三个问题：第一，ICEMS 路线从“并非真正多智能体”走到真实分布式执行后仍不如传统控制，是否说明研究思路错误；第二，模型优先路线的传统控制已经很强、局部神经残差没有通过训练门，是否说明多智能体没有研究空间；第三，在题目 *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning* 保持不变的条件下，下一步应怎样做实验。对两条论文线的当前正式证据和 2015--2026 年分布式电力控制、多智能体学习、残差学习与实验方法文献进行交叉核验后，结论是：**两条路线提出的问题都合理，但它们已经回答了不同问题。** ICEMS 的早期比较对象不具备真正分布式的运行时因果路径；后续匹配比较修复了这一点，并得到有效的负增量结果。它应作为会议稿的结论收口，而不应继续调参寻找正结果。模型优先路线的门控逻辑是合理的，但当前强基线使用全局信息，拟部署残差只使用邻居信息；因此现有负结论只否定当前残差形式与信息路径，尚未回答“同等局部信息下，多智能体是否优于最强分布式确定性控制”。保留题目不等于必须让多智能体胜出；它要求实验把物理余量、因果可预测性、局部信息价值、动作权限和学习优化依次分开。近期 ICEMS 论文不需要新控制实验；长期模型优先路线若继续，下一项应是新的、非学习的匹配分布式基础控制与信息价值门，只有通过后才训练。

## 1. 研究问题

- **RQ1：** 两条路线分别在哪一层失败：多智能体定义、物理可控空间、部署信息，还是学习算法？
- **RQ2：** 强传统控制之后，多智能体仍可能在哪些可验证条件下产生增量价值？
- **RQ3：** 不改变既定题目时，ICEMS 论文和长期模型优先研究应分别采取什么实验动作？

核心角度不是“传统控制与神经网络谁更强”，而是：**多智能体价值只有在剩余误差确实存在、独立动作能够改变它、局部或邻居信息能够识别正确动作、并且增益高于训练与仿真不确定性时才可辨认。**

## 2. 方法

内部事实只使用当前正式权威：ICEMS 的 `CLM-0905`／R338，以及模型优先线的 `CLM-0910`／R344 和 `CLM-0915`／R350。报告不复写测量表或正式结论全文；需要数值时应回到对应 claim、feed 和结果文件。

外部检索采用三个独立视角：

1. 电力系统主流视角：分布式控制、VSG／逆变器协调和 MARL 在什么条件下出现增益；
2. 反方与方法学视角：强基线、部分可观测、参数共享、信用分配、实现细节和少量种子如何改变算法排序；
3. 相邻控制视角：传统控制加残差学习何时有效，动作余量、安全投影和因果信息何时使学习失去对象。

纳入原始研究、正式出版页或作者公开稿；排除无法核验标题、作者或摘要结论的条目。最终综合语料为 17 项核心研究。外部文献用于解释机制和设计比较，不升级本项目证据。

## 3. 分类框架：四个必须分开的失败层

| 层 | 要回答的问题 | 失败意味着什么 |
|---|---|---|
| 物理余量 | 强控制后是否还存在具有实际意义的可改善误差？ | 当前任务没有值得学习的剩余目标 |
| 动作权限 | 独立设备动作是否保留足够方向、幅值、变化率、能量和秩？ | 网络即使知道答案也无法执行 |
| 信息价值 | 动作时刻可获得的局部、历史和邻居信息能否预测正确动作？ | 失败属于信息结构，不属于优化算法 |
| 学习与统计 | 在前三层通过后，策略能否稳定超过确定性局部规则？ | 此时才可以讨论算法、奖励、信用分配和训练方差 |

该分类比“单智能体／多智能体”标签更有辨识力。经典分布式平均控制已经能用局部测量和邻居通信完成频率恢复、有功分担和即插即用[2,3]；相反，电力系统 MARL 的优势经常表现为在线速度、模型不完整时的适应性或通信减少，而集中优化仍可能具有更好的物理性能[4--7]。因此，一个任务包含多台设备，并不自动意味着它需要多智能体学习。

## 4. ICEMS 路线：问题修复后得到的是有效负结果

早期 ICEMS 方案把多个局部输出集中聚合成一个标量动作。它可以研究共享因子化，却不能识别运行时独立执行的多智能体价值。COMA 和 MADDPG 等工作虽然允许训练期使用全局信息，但都把分散执行边界保留在部署演员及其独立动作上[14,15]；因此，审稿人指出“没有研究真正多智能体”是实验对象定义问题，而不是简单的写作措辞问题。

R338 修复了该问题：邻居局部执行器与联合信息单执行器使用相同的三维边动作、限制、训练预算和场景，并加入强传统控制。正式结论 `CLM-0905` 是 `NO-NEURAL-INCREMENT`。这不是实验失败，而是一个被正确识别的假设没有通过。电力文献同样没有给出“MARL 必然优于传统控制”的一般结论：Rozada 等[4]报告学习式分布频率控制在部分指标上有优势，但强传统分布式优化更平滑且成本更低；Cao 等[5]与 PowerNet[6]显示协同学习能够接近集中控制或超过所选传统基线，却仍受基线强度和仿真范围限制。

因此，ICEMS 线的正确动作是：

- 保留题目，因为题目描述被研究的方法，不承诺它必然优越；
- 在摘要、贡献、结果和结论中一致写成“真实分布式架构的受控比较与负增量结论”；
- 把早期标量共享因子化与后期三边独立执行明确分开，不能把两种动作空间合成一个正向 MARL 故事；
- 不再增加控制实验或结果导向调参。该论文线当前导航文件已经把“无需额外控制实验”列为收口条件。

## 5. 模型优先路线：合理的训练门，但还不是公平的 MARL 终局比较

残差学习文献的共同前提是“基础控制器有效但仍有结构化缺口”。Johannink 等[8]和 Silver 等[9]都让传统控制负责易建模部分，让策略只补难建模误差；Liu 等[10]进一步表明残差空间过小会够不到更优动作，过大则增加搜索难度，并且基础动作与残差相加后可能被物理边界裁剪。它们支持训练前测量余量，而不支持“有一个强基线就一定应该训练”。

本项目 R344 证明集中式确定性控制在有限银行上有效；R350 随后发现当前动作与信息路径下只有很小的理想剩余方向，而邻居局部代理与失配门均未通过，于是正式返回 `NO-TRAINING`。这个停止是合理的：继续更换网络或奖励，会把信息不足误写成优化失败。

但该结果仍有一个关键比较边界：基础控制使用全输出集中信息，拟部署残差只使用邻居局部信息。MARL 基准研究表明，简单独立或共享策略可以在多种任务上与更复杂的集中训练方法竞争，方法排序同时受参数共享、任务结构和实现细节影响[11--13]。所以 R350 能回答“当前局部残差不值得在集中上界之上训练”，不能回答“在同样局部信息与独立动作下，多智能体不如最强分布式传统控制”。

## 6. 跨线综合：标题可以保留，但两条线不能互相借证据

两条线表面上都讨论 MARL 与耦合，实际估计量不同：

| 论文线 | 已经回答的问题 | 不能推出的结论 | 当前动作 |
|---|---|---|---|
| ICEMS | 在已执行的固定系统、信息和三边动作下，学习架构是否超过强传统控制 | MARL 作为一类无效；所有分布式控制无价值 | 用负增量结果完成会议稿，不再跑新控制实验 |
| 模型优先 | 集中强控制后，当前零和边残差与邻居信息是否值得进入训练 | 同等信息下的分布式 MARL 无效；非线性或更丰富信息也必然失败 | 新立非学习问题，先匹配分布式基础控制和信息价值 |

题目不改带来的义务不是“训练出一个正结果”，而是正文必须让题目中的每个词都有对应证据：`decoupling-oriented` 对应明确的交叉耦合量及闭环变化；`coordination` 对应多个独立动作之间的协同；`multi-agent` 对应局部状态所有权、声明过的消息与独立执行；`reinforcement learning` 对应真实训练、固定预算和未见数据评价。第一条线已经有训练与真实分布式负结果；第二条线当前没有训练授权，不能把标题当作越过门槛的理由。

## 7. 推荐实验路线

### 7.1 ICEMS：不启动新实验

ICEMS 的近期任务是论文修订而不是科学探索。应把 R338 作为负增量和限制证据纳入现有论证，并完成证据、领域和编译检查。任何新奖励、新网络、新场景或新阈值都会开启新的因果对象，既不能修复已冻结结果，也会增加 4--6 页会议稿的叙事冲突。

### 7.2 模型优先第一步：匹配分布式基础控制的非学习物理门

下一项只回答一个问题：**在相同局部／邻居信息、相同三边向量动作、相同功率与能量限制下，一个真实分布式确定性控制器能否稳定工作，并且相对集中上界留下可解释的性能差距？**

建议比较：

1. 零附加控制或冻结基础层；
2. 邻居局部的确定性分布式控制；
3. 全局信息的集中确定性控制，仅作为上界；
4. 不依赖观测的固定时间程序，检查闭环方法是否真的利用信息。

此轮不训练，不选择奖励，不讨论神经网络。四组共享动作坐标、限幅、变化率、能量、场景和评价端点。必须记录请求、投影命令、实际执行、饱和／安全过滤、通信内容与时延。若分布式控制本身不可行，先修复控制与信息合同；若它已经追平集中上界且没有材料性差距，则当前任务没有支持 MARL 的余量。

### 7.3 第二步：四级剩余价值门

只有分布式基础控制通过后，依次评估：

1. **受约束结果已知理想补偿**：回答物理上最多还能改善多少；
2. **全局信息因果补偿**：去掉未来结果，只使用动作时刻可得的全局信息；
3. **邻居信息因果补偿**：使用本地历史和冻结的一跳邻居消息；
4. **独立本地因果补偿**：不使用邻居消息，测量真正的协调增量。

停止树应在看结果前冻结：理想补偿无材料性收益，则停止；理想有效而全局因果无效，则缺少可预测状态或模型；全局因果有效而邻居无效，则信息结构不足；邻居有效而独立本地无效，才出现可由多智能体协调解决的候选缺口。每一级同时通过平均端点、场景子组、模型失配、尾部无伤害和物理约束门。

### 7.4 第三步：只有门通过后才做可识别的学习比较

正式训练使用同一分布式确定性基础层，并采用二维因子设计：

| 训练臂 | 网络组织 | 运行时信息 | 识别目的 |
|---|---|---|---|
| SN-J | 单网络 | 联合信息 | 单网络全信息参考 |
| SN-N | 单网络、按边屏蔽 | 与每个边相同的邻居信息 | 控制“信息相同但由一个网络托管” |
| MA-J | 独立／按角色策略 | 联合广播 | 控制网络因子化效应 |
| MA-N | 独立／按角色策略 | 邻居信息 | 真正分布式候选 |

所有训练臂共享物理动作、基础控制器、安全治理、网络容量等级、训练交互量、调参预算、种子政策和未见评价银行。另保留“分布式确定性基础层”和“固定时间程序”。这种设计能够把多网络因子化、运行时信息和学习增量分开；只比较 MARL 与一个集中网络无法识别原因。

统计上不预设“跑五个种子就够”。应由不看正式结果的开发方差决定种子数，报告区间、全部场景、稳健聚合、尾部和最差子组。MARL 只有在未见场景上同时超过分布式确定性基础层、通过安全与尾部门，并且 `MA-N` 相对 `SN-N` 或独立本地臂表现出预注册的协调增量时，才支持正面多智能体结论[13,16,17]。

### 7.5 如果仍然没有余量，怎样继续而不制造问题

不得削弱传统控制器来给神经网络制造收益。可以另立新问题，逐项测试物理上合理而非结果导向的难度来源，例如设备间预先冻结的 SOC、功率、爬坡或能量异质性，以及总扰动相同但位置不同的成对场景。文献中的网络化 MARL 增益通常来自模型不完整、局部影响、设备差异或通信限制[5--7]，而不是来自“代理数量”本身。每次只改变一个轴，并重新运行非学习的四级门。通信延迟、丢包和断链应在名义分布式控制与学习增量都通过后再测试，不能用来替代基本有效性。

## 8. 开放问题与明确边界

1. 当前尚无经正式验证、与拟部署 MARL 使用同等信息的强分布式确定性基础控制器。
2. 当前三边零和动作对共同频率通道的直接权限有限；若更换动作基，必须先做新的物理权限和秩检查。
3. 当前固定拓扑不能支持拓扑泛化。多运行点、参数异质性或线路强度变化也不等于未见图泛化。
4. 多智能体信用分配方法可能改善训练[14]，但只有信息与动作门先通过后才值得研究；它不能修复不可观测的目标。
5. 现有电力系统 MARL 证据以仿真为主[1,4--7,16]；题目不应被扩展为硬件、部署或安全认证主张。
6. 当前平台中的 VSG 代理与独立储能执行器并非天然等同于统一的并联构网设备；题目保持不变时，正文仍须明确物理对象和执行器边界。

## 9. 结论

**对 RQ1：** ICEMS 的初始问题在于比较对象不是真正分布式；R338 修复对象后得到有效负结果。模型优先路线的问题不在门控逻辑，而在当前集中基础控制与局部残差的信息不匹配，以及残差余量很小。两者都不能概括为“MARL 普遍失败”。

**对 RQ2：** 强传统控制不是 MARL 的敌人，而是必要零假设。只有强控制后仍有可执行、可观测、可统计辨认的结构化缺口，并且邻居协同比独立本地策略有额外价值时，MARL 才有研究对象。

**对 RQ3：** 题目可以保持不变。ICEMS 线应停止新控制实验并用现有负增量证据完成论文；模型优先线若继续，下一步是匹配分布式确定性基础控制的非学习物理门，随后是理想、全局因果、邻居因果和独立本地四级剩余价值门。只有这些门通过，才启动四臂匹配学习比较。任何未通过都应保留为有边界的否定结论，而不是通过削弱基线、换算法或挑场景把结果改成正值。

## References

[1] Qiufan Yang, Linfang Yan, Xia Chen, Yin Chen, Jinyu Wen, “A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs,” IEEE Transactions on Power Systems, 2023.

[2] John W. Simpson-Porco, Qobad Shafiee, Florian Dörfler, Juan C. Vasquez, Josep M. Guerrero, Francesco Bullo, “Secondary Frequency and Voltage Control of Islanded Microgrids via Distributed Averaging,” IEEE Transactions on Industrial Electronics, 2015.

[3] Florian Dörfler, John W. Simpson-Porco, Francesco Bullo, “Breaking the Hierarchy: Distributed Control and Economic Optimality in Microgrids,” IEEE Transactions on Control of Network Systems, 2016.

[4] Estefanía Rozada, Dimitra Apostolopoulou, Eduardo Alonso, “Deep Multi-Agent Reinforcement Learning for Cost-Efficient Distributed Load Frequency Control,” IET Smart Grid, 2021.

[5] Di Cao, Weihao Hu, Junbo Zhao, Qi Huang, Zhe Chen, Frede Blaabjerg, “Data-Driven Multi-Agent Deep Reinforcement Learning for Distribution System Decentralized Voltage Control With High Penetration of PVs,” IEEE Transactions on Smart Grid, 2021.

[6] Dong Chen, Kaian Chen, Zhaojian Li, Tianshu Chu, Rui Yao, Feng Qiu, Kaixiang Lin, “PowerNet: Multi-Agent Deep Reinforcement Learning for Scalable Powergrid Control,” IEEE Transactions on Power Systems, 2022.

[7] Han Xu, Jialin Zheng, Guannan Qu, “A Scalable Network-Aware Multi-Agent Reinforcement Learning Framework for Decentralized Inverter-Based Voltage Control,” arXiv:2312.04371, 2023.

[8] Tobias Johannink, et al., “Residual Reinforcement Learning for Robot Control,” IEEE International Conference on Robotics and Automation, 2019.

[9] Tom Silver, Kelsey Allen, Josh Tenenbaum, Leslie Kaelbling, “Residual Policy Learning,” arXiv:1812.06298, 2018.

[10] Qiong Liu, Ye Guo, Lirong Deng, Haotian Liu, Dongyu Li, Hongbin Sun, “Residual Deep Reinforcement Learning With Model-Based Optimization for Inverter-Based Volt-Var Control,” IEEE Transactions on Sustainable Energy, 2025.

[11] Georgios Papoudakis, Filippos Christianos, Lukas Schäfer, Stefano V. Albrecht, “Benchmarking Multi-Agent Deep Reinforcement Learning Algorithms in Cooperative Tasks,” NeurIPS Datasets and Benchmarks, 2021.

[12] Chao Yu, et al., “The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games,” Advances in Neural Information Processing Systems, 2022.

[13] Logan Engstrom, et al., “Implementation Matters in Deep Policy Gradients: A Case Study on PPO and TRPO,” International Conference on Learning Representations, 2020.

[14] Jakob Foerster, Gregory Farquhar, Triantafyllos Afouras, Nantas Nardelli, Shimon Whiteson, “Counterfactual Multi-Agent Policy Gradients,” AAAI Conference on Artificial Intelligence, 2018.

[15] Ryan Lowe, Yi Wu, Aviv Tamar, Jean Harb, Pieter Abbeel, Igor Mordatch, “Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments,” Advances in Neural Information Processing Systems, 2017.

[16] Rihab Gorsane, Omayma Mahjoub, Ruan John de Kock, Roland Dubb, Siddarth Singh, Arnu Pretorius, “Towards a Standardised Performance Evaluation Protocol for Cooperative MARL,” Advances in Neural Information Processing Systems, 2022.

[17] Guodong Guo, Mengfan Zhang, Yanfeng Gong, Qianwen Xu, “Safe Multi-Agent Deep Reinforcement Learning for Real-Time Decentralized Control of Inverter-Based Renewable Energy Resources Considering Communication Delay,” Applied Energy, 2023.
