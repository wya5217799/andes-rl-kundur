# 实验研究价值研判（deep-research，会议论文校准版）

> 对象：已完成的 R399–R410 实验线（强确定性基线 + 有限 oracle、三臂 MARL
> canary 全部违反物理护栏、修复后的干净负消息对比、能量端口建设性伴生
> 结果），投 ICEMS 2026 会议。校准前提（owner 指定）：这是会议论文，
> 价值天花板按会议档算，投入产出比按会议档裁。
> 方法：web 检索串行执行，存在性逐条核；内容级未通读处标注
> [unconfirmed]，不作裁决依据。

## 研究问题

- **RQ1**：在 VSG-MARL 文献版图里，这套"物理端点 + 护栏优先 + 有界负结果
  + 干净消息对比"的评估有没有占住一个真实缺口？
- **RQ2**：领域是否已有"奖励≠解耦、消息对比可识别性"的评估标准，还是
  方法学本身就是贡献？
- **RQ3**：能量端口伴生结果本身有多少独立价值？
- **RQ4（校准）**：按会议论文的含金量，哪些实验值得在投稿前做，哪些是
  期刊档的过度投入？

## 分支一：VSG-MARL 主流的形态（RQ1 的对照面）

领域主流是**正结果 + 奖励导向**：VSG 方向 DRL 综述（Energies 2024,
17(11):2620）收录的算法混杂（DQN/DDPG/SAC/PPO），评估普遍以训练奖励或
频率偏差改善为终点；Yang 2023（TPWRS）用 MADRL-SAC 学惯性-下垂参数，报告
正面协同。解耦本身是活跃话题，但形态是**方法设计**：并联 VSG 相位协调
控制（IEEE 10344393）[unconfirmed]、摆动方程模拟 + 功率解耦策略（IEEE
7854751）[unconfirmed]、并联 VSG 稳定性与低频振荡抑制（IET
10.1049/enc2.70036）[unconfirmed]。这些工作都在"提出一种能解耦的控制器"，
**没有一篇以"护栏裁决 + 有界负结果"为主叙事**。以"直接 M/D 接口上的
MARL 学习路线经物理护栏评估判定失败 + 干净消息消融"为关键词组合检索，
未发现直接重叠工作——按检索口径报告为"no directly overlapping work
retrieved"，不等于证明无重叠。

**RQ1 裁决**：负结果 + 护栏评估的定位在 VSG-MARL 里是**真实但窄**的缺口。
会议档价值成立，但新颖性主张必须写成"未检索到直接重叠"，不能写成
"首次"。

## 分支二：评估方法学的先例密度（RQ2）

单项先例都存在：MARL 评估协议（Gorsane 2022，已引）、RL 结果对报告细节
的敏感性（Henderson, AAAI 2018）、种子功效分析（Colas 1806.08295 /
1904.06979）、reward hacking 基准（EvilGenie, arXiv:2511.21654）、风电
场 RL 奖励设计研究（S2666546826001187）、电网 RL 安全综述与运行时
safety shielding（arXiv:2604.14032；"RL Meets the Power Grid" 综述）。
但注意一个分野：领域的"安全"几乎全部是**训练期/执行期屏蔽（shielding）**
——把护栏当成**控制机制**；我们的护栏是**评估工具**——物理端点 + 守卫
天花板 + 奖励不进判决门，用来给负结果定案。这个"护栏当裁判"的组合
没有检索到直接先例。

**RQ2 裁决**：单项无新意，组合有辨识度。会议档最可引用的一个点：
**自我审计发现对照组信息合同被破坏后，降级叙述并花钱重做**——这是
论文里最"不寻常"的做法，值得在投稿材料里突出（一句话级），而不是
闷在 Limitations 里。

## 分支三：建设性伴生结果（RQ3）

带通阻尼的 VSG 控制**早已存在**（Barcellona & Huo, "Control strategy of
virtual synchronous generator based on virtual impedance and band-pass
damping", IEEE 7525999）。我们的 K=3.5 带通在"可行性原生能量端口"上的
实现**不是新技术**，其价值纯属逻辑作用：证明联合目标区非空、把负结果
钉死在"直接 M/D 接口"的范围内。

**RQ3 裁决**：独立价值≈0；作为论文内部的反例装置价值高。表述必须守住
"demonstrates feasibility for a distinct action basis"，绝不能说"novel
controller"。这是最容易在评审手里翻车的点——技术有先例，一旦措辞越级
就是硬伤。

## 分支四：会议档投入产出比（RQ4）

| 实验 | 对 ICEMS 的价值 | 档位裁决 |
|---|---|---|
| A1 幅度阶梯 | 保护核心数字的线性假设，便宜 | **投稿前做** |
| A2 拓扑变体 | 预答评审对建设性结果的第一问 | **投稿前做** |
| A4 额外未见数据 | 建设性结果加厚一层 | 投稿前做（可选） |
| A3 规则池扩充 | 加固"无余量"，边际 | 可选 |
| B1 限速器修复包 | 高价值但**不对称赌博**：若仍是 CANARY-FAIL 对论文只加一句话；若翻转则截稿前重写全文 | **投稿后做** |
| B2 5 种子 | 统计推断是期刊档要求，会议评审不要求 | 期刊扩展 |
| B3 诊断日志 | 内部机制问题，不进会议正文 | 期刊扩展 |
| C1-SAC 复现 | 只在想强化"对位 [1]"时值得 | 期刊扩展 |
| C2/C3 | 超出会议范畴 | 不做 |

**RQ4 裁决**：投稿前只做 A1+A2（+可选 A4）——全部是只读重评估、几小时、
直接加固论文两条承重结果；B 类全部押后到期刊扩展。B1 尤其不能投稿前做：
它的下行风险（翻转叙事、截稿前返工）不对称地大于上行收益（多一句话）。

## 综合结论（逐 RQ）

- **RQ1**：占了一个真实但窄的负结果缺口；会议档够用。
- **RQ2**：单项有先例、组合有辨识度；"自我审计 + 干净重做"是最值得
  亮出来的一行。
- **RQ3**：技术无新意，只当反例装置用；措辞必须死守。
- **RQ4**：投稿前 A1+A2（+A4），其余全部期刊化。
- **总评**：作为会议论文，价值**成立且不虚高**——它不是靠大数字，而是
  靠"别人都在报好消息时，一篇把护栏当裁判、把自己查出的漏洞修掉重测
  的负结果"。这类论文在 ICEMS 的接受面比"又一个改进 X% 的正结果"更稳，
  因为它不依赖任何一条脆弱的性能主张。

## References（存在性已核；[unconfirmed] 未通读）

1. "Deep and Reinforcement Learning in Virtual Synchronous Generator: A
   Comprehensive Review," Energies 17(11):2620, 2024.
2. Q. Yang et al., TPWRS 2022 (IEEE 9946410).
3. A. Barcellona, S. Huo, "Control strategy of virtual synchronous
   generator based on virtual impedance and band-pass damping," IEEE
   7525999.
4. "Research on Parallel Power Conversion Systems Based on Virtual
   Synchronous Generator Phase Coordination Control," IEEE 10344393
   [unconfirmed].
5. "A novel virtual synchronous generator control strategy based on
   improved swing equation emulating and power decoupling method," IEEE
   7854751 [unconfirmed].
6. "Stability analysis of parallel virtual synchronous generators and
   suppression of low-frequency oscillations," IET 10.1049/enc2.70036
   [unconfirmed].
7. "EvilGenie: A Reward Hacking Benchmark," arXiv:2511.21654.
8. "Reward design for deep Reinforcement Learning driven wind farm
   control," ScienceDirect S2666546826001187 [unconfirmed beyond title].
9. "Hierarchical Reinforcement Learning with Runtime Safety Shielding for
   Power Grid Operation," arXiv:2604.14032 [unconfirmed beyond abstract].
10. "Reinforcement Learning Meets the Power Grid: A Contemporary Survey
    with Emphasis on Safety and Multi-Agent Challenges" [unconfirmed
    beyond title].
11. P. Henderson et al., "Deep Reinforcement Learning that Matters," AAAI
    2018, arXiv:1709.06560.
12. C. Colas et al., arXiv:1806.08295; arXiv:1904.06979.
13. R. Gorsane et al., "Towards a standardised performance evaluation
    protocol for cooperative MARL," NeurIPS 2022.
