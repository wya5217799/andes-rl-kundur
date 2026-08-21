# C 类三项科学必要性研判（deep-research 裁决报告）

> 用途：抛开仓库内部政策（R86 平台期、ADR-0005），仅按科学必要性独立裁决
> 三个被排除的方向——换算法、跨仿真器（EMT）、更大拓扑——"值不值得研究，
> 还是现在这样挺好"。裁决结果已回写 `soft_spot_experiment_program.md`。
> 检索方式：web 检索（串行执行，无 scholarly API 子代理），存在性逐条核对；
> 内容级判断只建立在标题/摘要级证据与仓库内部证据上，未通读全文的条目
> 标注 [unconfirmed]，不作为裁决依据。

## 研究问题

- **RQ1（算法维度）**：对"direct-M/D 解耦 MARL"这一目标，换算法（尤其精确复现
  Yang 2023 的 SAC）是否可能实质改变结论？仓库 91 轮平台期结论能否直接迁移？
- **RQ2（跨仿真器）**：phasor-DAE 结论对"EMT 级"现象是否系统性失真？本论文
  的 claim 类型（相对护栏比值）是否要求 EMT 验证？
- **RQ3（拓扑维度）**：单 Kundur 拓扑对一篇会议评估论文是不是实质软肋？领域
  惯例与评审预期是什么？

## 分支一：算法维度（RQ1）

**外部证据。** Henderson et al. 的 *Deep Reinforcement Learning that
Matters*（AAAI 2018, arXiv:1709.06560）是算法敏感性问题的基准文献：算法、
超参、代码实现三者强烈交互，单一实现上的对比结论脆弱。这同时支持两件事：
(i) 单算法负结果**必须**限定为 bundle 级结论（本论文已做到）；(ii) 反过来，
"换一个算法必然同样失败"也不能从单算法失败推出——两边都不许外推。

**仓库内部证据。** CLM-0144/CLM-0149 的 91 轮平台期是**任务特异的**：它在
原始 V4 奖励目标（7 维观测、paper-equivalent 6-axis、geo 指标）上测得，机制
是"critic 表征学不出凹动作偏好，SAC/TD3/Transformer/LSTM 共享同一 TD 范式"。
而 R402/R410 的 canary 是**不同的科学对象**：不同奖励（物理成本+对偶乘子）、
不同动作接口（direct M/D + 状态化 slew）、不同 critic（twin joint 联合 critic）。
平台期结论能否迁移到该对象，**从未被验证**——所以"不许换算法"是策略选择，
不是已被证明的事实。

**领域惯例。** VSG 方向的 DRL 综述（*Deep and Reinforcement Learning in
Virtual Synchronous Generator: A Comprehensive Review*, Energies 2024,
17(11):2620, doi:10.3390/en17112620）显示领域内算法混杂（DQN/DDPG/SAC/PPO
等），**不存在**"负结果必须扫算法"的既定规范。参考方法 Yang et al.（TPWRS
2022, IEEE 9946410）用的是 MADRL-SAC，本论文的标量 TD3 已明示不是其精确
复现。

**裁决 RQ1：** 算法维度**不是**必须补的软肋——本论文的 claim 已经 bundle 级
限定，领域无算法扫描规范，且仓库平台期证据提示该对象上"换算法救活"的先验
概率不高（共享 TD 范式的机制解释）。但有一个**定点、非扫描**的高价值实验：
精确复现 Yang 2023 的 SAC 接口（因为它正是论文对位的文献 [1]），成本 = 一个
三种子 bundle（≈R410 规模）。结论：**建议从"禁止"降级为"可选的高优先级定点
实验"**，仅当"与 [1] 的直接对位"被认为值得加强时执行；广义算法扫描维持不必要。

## 分支二：跨仿真器 / EMT（RQ2）

**外部证据。** phasor 模型的适用边界是活跃研究方向：*Comparison of
Electromagnetic Transient and Phasor-based Simulation for the Stability of
Grid-Forming-Inverter-based Microgrids*（IEEE ISGT 2021,
10.1109/ISGT49243.2021.9372242）、*Comparative Modeling and Analysis of EMT
and Phasor RMS Grid-Forming Converters*（IEEE, doc 10342822）、*Phasor
Approximation Models Applicability Limits of Voltage Source Converters*
（IEEE, doc 11180621），以及 2026 年的 *When Can Phasor-Domain Device
Models Be Trusted for Electromechanical Stability Analysis of Grid-Forming
Converter-Dominated Microgrids?*（arXiv:2606.08082）——共识是：在**快速动态**
（RoCoF、内环/限流交互、锁相动态）上 phasor 模型可能失真，误差随动态快慢
变化。这与本论文的关切（RoCoF 护栏、动作 slew）存在潜在交集。

**claim 类型分析。** 关键区分：本论文所有头条结论是**相对护栏比值**（学习臂
÷ 确定性参照 ÷ 同一模拟器内的守卫），不是绝对稳定性/安全声明。同一模拟器内
的相对比较对 EMT-vs-phasor 的绝对偏差**部分免疫**；但"护栏天花板 103%/110%
在 EMT 下是否仍安全"这类问题，phasor 证据回答不了——而论文并未做此类声明
（§7 明示无 EMT/HIL）。

**裁决 RQ2：** 对本论文的 claim，EMT 验证**不是必要项**；对"泛化到真实装置"
的未来主张，它是**必要项**。另需澄清：ADR-0005 禁的是"Simulink 1:1 数字
对账"（已证 ROI 为零），与"EMT 抽查 phasor 失真"是**两个不同的问题**——
后者从未被 ADR 否定，只是在当前资源约束下不优先。裁决：维持"不做"，
但理由从"政策禁止"改为"当前 claim 类型不需要 + 资源约束"；作为远期扩展项
登记。

## 分支三：拓扑维度（RQ3）

**外部证据。** 场景/拓扑泛化是电力 RL 公认的开放问题：*Toward emergency load
frequency control: A policy-transfer deep reinforcement learning framework*
（Neurocomputing, 2026）、*Learning-driven load frequency control for
islanded microgrid using graph networks-based deep reinforcement learning*
（Frontiers in Energy Research, 2024, 10.3389/fenrg.2024.1517861）、LFC 综述
（*LFC strategies for future power grids*, 2025）——单场景策略跨场景退化被反复
报道，政策迁移/图网络正是为此提出的解法。这证实：**如果**本论文声称跨拓扑
有效，单 Kundur 就是致命软肋；**但论文没有**——§7 把拓扑泛化列为范围外，
claim 全部限定"one modified Kundur topology"。

**裁决 RQ3：** 单拓扑不是本论文的有效性软肋（claim 已限定），是**影响力**
软肋（结论的外推边界窄）。评审若挑刺，攻击点只会是"你有没有声称泛化"——
没有，就站得住。同规模拓扑变体（线路开断/阻抗变化，程序清单 A2）以近零
计算成本把"限定"变成"轻微加固"，性价比最高；**更大电网不必要**，与你的
直觉一致，也与"政策迁移是独立研究问题、需要专门方法"的文献判断一致。

## 跨分支综合

三个方向的共同模式：**每个方向的"必要性"都取决于 claim 的强度，而本论文
的 claim 强度恰好都收在证据以内。** 算法：bundle 级限定；EMT：无绝对安全
声明；拓扑：无泛化声明。因此"现在这样挺好"在**当前论文的论证完整性**意义
上成立。真正会把这些方向变成必需品的，只有三种升级：(i) 想把负结果升级为
"对 SAC 也成立"（→ 定点 SAC 复现）；(ii) 想对真实装置说安全（→ EMT/HIL）；
(iii) 想说方法在别的电网也成立（→ 政策迁移研究）。这些都是**下一步论文**
的问题，不是 ICEMS 这篇的问题。

## 结论（逐 RQ）

- **RQ1**：不必须。领域无扫描规范；平台期证据提示换算法先验收益低且不可
  迁移；唯一值得的定点实验是 Yang-2023-SAC 精确复现，属可选加固。
- **RQ2**：对当前 claim 不必须；EMT 是"泛化到装置"主张的前置条件，与
  ADR-0005 的 Simulink 对账禁令是两回事。维持不做，理由已更正。
- **RQ3**：不是有效性软肋（claim 已限定），是影响力软肋；A2 同规模变体足以
  加固，更大电网不必要。

## 对程序清单的修订（已执行）

- C1 由"政策禁止"改为"定点 SAC 复现 = 可选高价值实验（非扫描）；广义算法
  扫描维持不必要（文献+机制双重理由）"。
- C2 由"政策禁止"改为"当前 claim 不需要；作为远期扩展登记（区别于 ADR-0005）"。
- C3 由"政策禁止"改为"owner 成本约束维持；A2 覆盖实际关心的轴"。

## References（存在性已核；内容级未通读处已标注）

1. P. Henderson et al., "Deep Reinforcement Learning that Matters," AAAI 2018,
   arXiv:1709.06560 — https://mlanthology.org/aaai/2018/henderson2018aaai-deep/
2. Q. Yang et al., "A Distributed Dynamic Inertia-Droop Control Strategy Based
   on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs,"
   IEEE TPWRS, 2022 — https://ieeexplore.ieee.org/document/9946410
3. "Deep and Reinforcement Learning in Virtual Synchronous Generator:
   A Comprehensive Review," Energies 17(11):2620, 2024,
   doi:10.3390/en17112620 — https://www.mdpi.com/1996-1073/17/11/2620
4. "Comparison of Electromagnetic Transient and Phasor-based Simulation for
   the Stability of Grid-Forming-Inverter-based Microgrids," IEEE ISGT 2021 —
   https://ieeexplore.ieee.org/document/9372242
5. "Comparative Modeling and Analysis of EMT and Phasor RMS Grid-Forming
   Converters Under Different Power System Dynamics," IEEE —
   https://ieeexplore.ieee.org/document/10342822
6. "Phasor Approximation Models Applicability Limits of Voltage Source
   Converters," IEEE — https://ieeexplore.ieee.org/document/11180621
7. "When Can Phasor-Domain Device Models Be Trusted for Electromechanical
   Stability Analysis of Grid-Forming Converter-Dominated Microgrids?,"
   arXiv:2606.08082 — https://scirate.com/arxiv/2606.08082
8. "Toward emergency load frequency control: A policy-transfer deep
   reinforcement learning framework with dynamic exploration,"
   Neurocomputing, 2026 — https://www.sciencedirect.com/science/article/abs/pii/S0925231226014463
9. "Learning-driven load frequency control for islanded microgrid using graph
   networks-based deep reinforcement learning," Frontiers in Energy Research,
   2024, doi:10.3389/fenrg.2024.1517861 — https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2024.1517861/full
10. "LFC strategies for future power grids: A survey on intelligent,
    data-driven, and resilient techniques," 2025 —
    https://www.sciencedirect.com/science/article/pii/S2590174525005938
