# 差异化备忘录：对 Yang 2023 / Ge 2026 两篇最近先行工作的防御

**日期**: 2026-07-29
**用途**: SCI 期刊扩展版手稿的引言定位段 + cover letter;决策用工作文档,非投稿终稿文本
**输入**: `paper/sci_upgrade_survey/REPORT.md`(已核验调研)、CLM-0610 (R280)、CLM-0615 (R281)、`memory/rounds/R280/verdict.md`、`memory/rounds/R281/verdict.md`
**证据等级注记**: 对 Yang/Ge 工作内容的描述基于摘要+第三方转述(调研 §2 已降格表述),投稿前建议通读两篇全文确认无遗漏;对我方工作的描述全部有 measured provenance(claim 级)。

---

## 1. 两篇必须防御的先行工作

### Yang et al., TPWRS 2023 [调研 ref 15]

- **全引**: Q. Yang, L. Yan, X. Chen, Y. Chen, J. Wen, "A distributed dynamic inertia-droop control strategy based on multi-agent deep reinforcement learning for multiple paralleled VSGs," *IEEE Trans. Power Syst.*, 38(6): 5598–5612, 2023.
- **做了什么**: 同样针对并联 VSG 振荡问题;先从简化频率响应模型推导振荡与惯量-下垂参数分布的关系,再把参数整定建模为 Markov 博弈,用 SAC 类 MADRL 分布式动态调节惯量-下垂参数;每 agent 仅用本地与相邻 VSG 信息。
- **与我们问题的距离**: 问题域相同(并联 VSG 参数协调抑振荡),方法论框架相同(MADRL 调惯量参数)。是审稿人第一个会问"你跟它差在哪"的工作。

### Ge et al., IEEE Trans. (early access) 2026 [调研 ref 21]

- **全引**: L. Ge, Y. Qi, Y. Guo, L. Hou, S. Wan, H. Bai et al., "A MADRL driven optimization framework for grid node inertia and grid-forming converter damping characteristics in microgrids," *IEEE Trans.* (early access), 2026.
- **做了什么**: 在 IEEE-13 节点微电网上用 MADRL 优化 grid node 惯量与 GFC 阻尼特性。
- **与我们问题的距离**: 把"惯量"从单机参数抬到"节点空间配置"层面,概念上离我们的 inertia placement 重构最近;必须用"空间配置"的措辞明确区分。

## 2. 差异化五维对照表

| 维度 | Yang 2023 / Ge 2026 | 本文(期刊扩展版) | 我方证据 |
|---|---|---|---|
| **科学问题** | "MADRL 能否调好 VSG 参数抑振荡"(算法先行,贡献=新算法+自设场景+自评提升) | "虚拟惯量的**空间差动配置**是否有真实因果增益、增益由什么物理机理决定、边界在哪"(机理先行,挂 Poolla/Dörfler placement 谱系) | 调研 §3.1/§4 空白陈述 |
| **基线可识别性** | 无 size-matched 集中式学习基线 → 无法判断所测 MARL 因子化相对集中式学习的代价 | 匹配观测/动作/奖励/训练量/调参预算的集中式 TD3 vs 参数共享标量 MARL vs 因果反馈律三方对照,3 个配对种子;结论只覆盖该标量因子化 | CLM-0610 (R280) |
| **总量 vs 空间解耦** | 惯量/下垂幅值自由调节,总量增益与空间重分配增益混杂 | 硬零和模态 q·[1,1,-1,-1],总惯量冻结 1400 → 纯空间重分配;学习动作仅标量 q 且有 slew 限幅 | CLM-0610;R281 plan 冻结合约 hash 11a4800123f48a33 |
| **评估完整性** | 训练与评估共用扰动分布(调研 §3.2,摘要级证据) | 预注册封存 fresh 24 场景库、completion  screening、不可变哈希、配对不确定度、全守卫(动作/储能/完成率/尾部) | CLM-0610 provenance;R279 formal seal |
| **机理刻画** | 无小信号/特征值层面的增益来源解释 | 冻结 plant 上 9 点静态分配扫描的 ANDES 特征值分析:经典区间模态阻尼比在学习器利用方向 +55%(满幅),非全局单调;VSG 本地模态服从 1/√M 折中;低惯量下敏感度翻倍 | CLM-0615 (R281) |

## 3. 我们能说、他们不能说的一句话

> **在匹配条件下,我们有可复现的多种子证据表明学习收益真实存在,且收益来源可以被一个半解析机理(差动分配→区间模态阻尼)有界地解释;他们展示了 MADRL 可行,但无法排除"收益来自学习本身而非架构、来自总量而非空间、来自训练分布过拟合"三种平凡解释。**

## 4. 诚实边界(手稿里绝不能越过的线)

1. **不写"分配创造阻尼"**:R281 判定为 MECHANISM-PARTIAL,全局单调被 U 型上翘打破;机理段只能写成有界经验陈述——"差动分配在学习控制器利用的方向上实质提升经典区间模态阻尼(+55%@满幅,非全局单调);VSG 本地模态服从 1/√M 折中;低惯量系统敏感度放大"。
2. **不宣称 MARL 无用**:负结果仅覆盖理想通信、双区域、4 VSG 场景;对 Yang 的分布式执行设定(local+neighbor 信息)要表述为"在理想通信下集中式已足够,通信受限场景下分散执行的代价-收益留作开放问题"(对应调研 OP2)。
3. **不贬低对方工程贡献**:Yang 的分布式执行、Ge 的微电网多节点场景是我们没有覆盖的;定位措辞用"互补+更严格的因果证据",不用"他们做错了"。
4. **不宣称泛化**:当前机理仅在线性化改造 Kundur 双区域上成立,无拓扑/跨仿真器证据(R281 scope limit 已记)。
5. **慢共模恢复回路不在机理内**:R274 droop+PI 慢层不在 DAE 内,机理段不得暗示解释慢恢复。

## 5. 引言定位段草稿(英文,可直接改写进 Introduction)

> The closest prior works formulate paralleled-VSG coordination as a multi-agent learning problem: Yang et al. [X] derived oscillation–parameter relations from a simplified frequency-response model and tuned inertia–droop parameters distributedly via SAC-based MADRL, while Ge et al. [Y] optimized grid-node inertia and grid-forming damping in a microgrid with MADRL. Both demonstrate feasibility, but three questions remain open: (i) how a specific multi-agent factorization compares with size-matched centralized learning; (ii) whether the gain comes from adjusting the *amount* of virtual inertia or its *spatial allocation*—total inertia was unconstrained; and (iii) whether the reported gains survive evaluation on disturbances disjoint from training. This paper addresses these questions on a modified Kundur two-area system: under a hard zero-sum spatial mode with frozen total inertia, a matched centralized learner improves synchronization loss by 24.3% and inter-area IAE by 17.0% on a sealed fresh disturbance bank, while the tested parameter-shared scalar factorization provides meaningful but inferior performance; and a small-signal eigenvalue study explains where the gain comes from—differential allocation materially raises the classical inter-area mode damping ratio in the direction the learned controllers exploit.

## 6. Cover letter 差异化段草稿(英文)

> This submission is not another "RL tunes VSG" paper. Relative to the two nearest works (Yang et al., TPWRS 2023; Ge et al., 2026), its contributions are complementary and orthogonal: (1) a controlled evaluation design—size-matched centralized baseline, frozen zero-sum spatial mode, pre-registered sealed disturbance bank, paired multi-seed uncertainty—that isolates total-inertia from spatial-allocation gains and benchmarks one shared scalar factorization against centralized learning; (2) a semi-analytic mechanism characterization (eigenvalue-based) of *why* spatial differential allocation helps and how its sensitivity scales with system inertia; and (3) an honestly retained result—the parameter-shared scalar policy improves on the fixed reference but remains inferior to centralized TD3—which we believe is itself a methodological contribution of interest to the readership.

## 7. 投稿前核对清单

- [ ] 通读 Yang 2023 全文(IEEE Xplore 9946410),确认其评估扰动与训练分布关系、是否有我们遗漏的基线
- [ ] 通读 Ge 2026 全文(IEEE Xplore 11471279),确认其惯量"空间"含义与我们 placement 重构的确切差异
- [ ] 两篇的最新被引与勘误状态
- [ ] 引言中引用编号 [X]/[Y] 落位
- [ ] 若 Q-0043 (SCR 扫描) 完成,在 §5 草稿补"弱电网边界"一句
