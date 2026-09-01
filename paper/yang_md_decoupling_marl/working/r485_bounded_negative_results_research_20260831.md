# R485 有界负结果论文：可发表性、根因实验与写作边界

**日期：** 2026-08-31
**状态：** working research note；不属于 R485 evidence、claim、verdict 或手稿资产
**范围：** 只研究方法学、期刊要求和已发表案例；未读取或判断 R485 结果，未检查运行进程，也不建议在当前 active round 内启动任何实验

## 结论先行

R485 即使得到阴性或混合结果，也**可能支撑一篇完整论文**。关键不是结果“好不好”，而是它是否给出了一个可信、对同行有用的边界：在预先固定的系统、控制权限、信息结构、训练预算、比较器和测试分布内，某项设计没有带来超过预设最小有用幅度的改进，或者只在明确条件下有效。

这类论文成立需要同时满足四件事：

1. 实验和实现有效，失败不是数据缺失、代码错误、基线失常或控制通道根本没有起作用；
2. 估计的不确定性足够小，能够排除一个事先有工程含义的最小有用效果，而不只是得到 `p > 0.05`；
3. 结论严格限定到被测试的因果对象和实验范围，不把一个系统、一个预算或一种共享策略说成整个 MARL/控制范式；
4. 论文贡献被写成“识别边界、纠正比较、提供可复现证据或改变技术选择”，而不是“我们尝试了但没成功”。

**是否必须补根因实验取决于主张，不取决于结果符号。** 若论文只主张“在这个冻结条件下没有建立实用增益”或“可排除至少为 \(\delta\) 的增益”，根因实验通常是可选扩展；若标题、摘要或讨论要说“失败是因为 X”，或者当前阴性结果也可能由训练不足、执行器饱和、信息缺失、奖励错配、基线失真等竞争解释造成，则需要能区分这些解释的诊断或干预实验。

因此，在看到 R485 的最终 validity、effect interval 和 factorial pattern 之前，不能直接决定“补”或“不补”。可执行的判定规则是：

| R485 最终状态 | 论文能说什么 | 是否补实验 |
|---|---|---|
| 完整且有效；效果上界低于预设最小有用增益 \(\delta\) | 有界负结果 | **不为发表自动补**；机制只作可选扩展 |
| 完整且有效；不同 factor/endpoint 形成稳定、预先定义的交互 | 有界混合结果与适用边界 | 通常不补；只有因果解释是主贡献时才做定向诊断 |
| 完整且有效；区间同时容许重要收益和重要损害 | “未建立优势”，但不能称“无实用增益” | 若目标仍是强负结论，优先补独立 seeds/precision，而非盲目找机制 |
| 基线、positive control、控制权限或训练机会不成立 | 结果不具诊断性 | 先修复验证；这不是科学根因实验 |
| execution/integrity/design 无效 | 不能作科学结论 | 必须修复或重做；不可写成负结果 |

## 1. 期刊真正要求的不是正结果，而是明确的知识贡献

IEEE PES 2026 Author's Kit 没有一条“阴性结果自动可收”的政策。它要求 Transactions 论文质量高且对技术知识有明确贡献；列举的可接受贡献包括“对当前技术有用的数据和经验，并反映技术需要怎样改变”。这给有界负结果留下空间，但门槛仍是**技术知识增量**，而不是结果符号。官方说明还要求摘要准确陈述研究设计、主要结果以及数据允许得出的结论。

对 R485，适合投稿的贡献表达应是以下一种或几种：

- 一个被广泛默认但此前没有被公平检验的增益，在强比较器和冻结预算下没有成立；
- factorial design 把“整体无优势”分解成了哪些 factor 有效、哪些没有，以及交互发生在哪里；
- 结果识别了控制结构的适用边界或证明复杂度没有换来达到工程阈值的收益；
- 透明的 seeds、分布、失败率、物理指标和计算成本改变了后续技术选择；
- 一个常用评价方式会制造表面优势，而更严格的 paired/interval analysis 改变了结论。

单独的“所有均值都差不多”不够。PES 的门槛意味着论文必须回答：**这个结果让电力系统控制研究者今后少犯什么错误、少做什么无效工作，或者怎样改变设计选择？**

来源：[IEEE PES Author's Kit, Part 2，2026-05 修订](https://ieee-pes.org/publications/authors-kit/preparation-and-submission-of-transactions-papers/)，[PES abstract requirements](https://ieee-pes.org/publications/authors-kit/information-for-authors-of-ieee-power-energy-society-transactions-papers/)。

## 2. 可发表的 bounded negative result 必须满足什么

### 2.1 先固定“负掉的到底是什么”

至少要明确：

- **因果对象：** 比较的是哪一种结构、信息模式、动作映射、参数共享方式或控制器，而不是笼统的“MARL”；
- **目标总体：** 哪个系统、频率、工况/扰动 bank、拓扑和 horizon；
- **训练制度：** from-scratch 还是 checkpoint、预算、调参权限和 seed population；
- **比较器：** 经典控制器、单 actor、集中式/共享策略或其他 arm 的实际信息与控制权限是否公平；
- **estimand：** 每个 primary endpoint 的效果定义、方向和独立实验单位；
- **成功阈值：** 什么幅度才足以改变工程决策。

一个安全的核心句式是：

> 在 [系统/工况总体]、[信息与动作权限]、[训练预算] 和 [冻结比较器] 下，方法 A 相对 B 未建立超过 \(\delta\) 的 [primary endpoint] 改进。

句子里的每个方括号都是 claim boundary，不能在摘要里消失。

### 2.2 “不显著”不等于“没有效果”

令 \(\theta\) 表示候选方法相对比较器的改进，正值更好；令 \(\delta>0\) 表示**最小有用效果**（SESOI, smallest effect size of interest）。不同结果支持不同强度的结论：

| 结果形态 | 允许的解释 |
|---|---|
| 传统 superiority test 未显著，区间很宽 | 只可说“未建立优势” |
| \(\theta\) 的上置信界低于 \(\delta\) | 可说“排除了至少为 \(\delta\) 的实用增益” |
| 整个预设置信区间落在 \([-\delta,\delta]\) | 可说“在预设容差内 practically equivalent” |
| 整个区间位于不利方向，且超过 harm margin | 可说“在该范围内更差/有害” |
| 区间同时覆盖重要收益和重要损害 | inconclusive，不能称为负证据 |

Schuirmann 的 Two One-Sided Tests（TOST）把“等效”作为一个独立假设问题，而不是在传统差异检验失败后补做 power 解释。Lakens 等进一步说明，等效边界必须代表最小有意义效果，而不是看完数据后挑一个刚好能过的阈值。TOST 在双侧等效边界、每侧显著性水平 \(\alpha\) 下，与 \((1-2\alpha)\) 置信区间完全落入边界相对应；若项目使用其他 interval/bootstrap 规则，应在 unblinding 前固定，不要机械混用阈值。

对 R485 最有用的区分是：

- **弱负结论：** 没有建立优势；
- **强有界负结论：** 排除了事先定义的、足以改变工程选择的优势；
- **等效结论：** 差异被限制在双侧实际容差内；
- **机制负结论：** 不仅没有优势，而且有干预证据解释为什么。

前三者依次需要更强的精度，第四种还需要额外的因果证据。

来源：[Schuirmann 1987, original TOST paper](https://doi.org/10.1007/BF01068419)，[Lakens, Scheel, and Isager 2018](https://doi.org/10.1177/2515245918770963)。

### 2.3 有效性必须先于结果方向

有界负结果至少要有以下 validity evidence：

1. **完整性：** 所有预注册 arms/seeds/endpoints 都按规则完成；缺失和失败没有被 outcome-dependent 地删除；
2. **实现正确：** 单元/集成检查、artifact lineage、单位和符号、观测转换、动作路由及 comparator 实现都能被复核；
3. **基线有能力：** 强基线在其设计域内表现正常，不能靠弱基线制造“大家都一样”；
4. **干预真的发生：** factor 改变了它声称改变的观测、动作、训练或物理通道；如果所有 arms 都被同一饱和/投影压成相同行为，endpoint null 不能区分算法；
5. **统计单位正确：** training seeds、scenario rows、time samples 不可互相冒充独立样本；
6. **不确定性可见：** 报告 effect sizes、intervals、每 seed/工况分布、失败率和 tail/guardrail，而不是只有平均 reward；
7. **多重比较受控：** primary contrast、co-primary endpoints、factorial main effects/interactions 和 sensitivity analyses 分层清楚；
8. **结果不可选择：** seeds、thresholds、horizon、metrics、checkpoint 和 stopping rule 不能因结果而改变。

Henderson 等在 AAAI 2018 直接展示：只改 random seeds、hyperparameters、环境或 codebase，RL 排名就可能改变；他们要求多个 seeds、uncertainty/significance analysis、公开完整实现和 evaluation details。Agarwal 等在 NeurIPS 2021 则展示少量 runs 下 point estimate 会给出与 interval analysis 不同的结论，并建议 confidence intervals、performance profiles 和更稳健的 aggregate measures。二者共同说明：没有 uncertainty 的“负均值”与没有 uncertainty 的“SOTA 均值”同样不可靠。

来源：[Henderson et al. 2018, full AAAI paper](https://doi.org/10.1609/aaai.v32i1.11694)，[Agarwal et al. 2021, NeurIPS paper](https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html)。

### 2.4 边界本身要有外部价值

一个结果可以只对一个冻结 benchmark 有效，但论文必须解释这个 benchmark 为什么承载一个真实技术问题。应报告而不是隐藏：

- 一个 test system，不代表其他 grid/topology；
- 一个冻结 scenario bank，不代表开放世界 generalization；
- 一个 information pattern，不代表所有 centralized/decentralized MARL；
- 一个 action authority 和 feasibility mapping，不代表方法在其他执行器上也无效；
- 一个训练预算，只能约束该 budget 下的 learnability/performance；
- 一个 simulator，不自动支持 hardware、cross-simulator 或 deployment claim。

边界越诚实，负结果越可信。把结论写小不会削弱论文；如果这个小边界正好切断一个流行但无证据的默认假设，反而是明确贡献。

## 3. 哪些失败只是 inconclusive

以下任一情况都不能直接升级为科学负结果：

### 3.1 精度不够

- 置信区间同时容许超过 \(\delta\) 的收益和实质损害；
- 只报 `p > 0.05` 或 “Holm 后不显著”，没有效果区间；
- equivalence margin 在看结果后定义；
- 更多 bootstrap replicates 被误当成更多独立 seeds。

这时最直接的补充不是“找原因”，而是增加真正独立的实验单位，或者把 claim 降为“未建立优势”。

### 3.2 算法没有得到公平成功机会

- baseline 没复现其应有性能，或不同 arms 的 tuning effort 不对等；
- 训练曲线仍明显上升、预算没有任何独立依据，却宣称结构性无效；
- observation/action/reward 的实现可能错，或转换只对某些 arms 生效；
- 控制动作在 projector、saturation 或 rate limit 后几乎相同；
- 所有方法都失败在 simulator 初始化、数值收敛或不可控工况。

这类问题属于 internal validity。先做 correctness/positive-control 修复；不能把修复称为“寻找科学根因”。

### 3.3 设计没有识别论文想说的对象

- 比较了 shared-policy 或 centralized execution，却下结论说 fully decentralized MARL；
- 一个 reward/composite metric 无改善，却下结论说物理性能无改善；
- 一个 bank 上无改善，却说没有 generalization；
- factorial 存在强 interaction，却只报 pooled main effect；
- training seed 与 evaluation scenario 的层级被混合，造成 pseudo-replication；
- controller-specific failures 被删掉后只分析共同成功样本。

正确做法是缩小 claim、显式报告 interaction/failure，或补真正识别目标对象的实验。

### 3.4 outcome-dependent rescue

结果出来后换主指标、挑 checkpoint、改阈值、加最有利的 horizon、删异常 seed，都会让“负结果”变成探索性发现。Nosek 等将 preregistration 的作用定义为在观察 outcome 前固定问题和分析，从而区分 confirmatory 与 exploratory work。任何 post-hoc 诊断仍可以做，但必须单列为 exploratory 或作为下一轮预注册 replication，不能回写成原实验的先验检验。

来源：[Nosek et al. 2018, PNAS](https://doi.org/10.1073/pnas.1708274114)。

## 4. 根因/机制实验何时必要，何时只是可选扩展

### 4.1 必须补的情况

只有下列目标存在时，机制实验才是硬要求：

1. **论文要使用因果语言。** 标题或主结论出现 “because”、“mechanism”、“bottleneck”、“caused by”、“根本原因是”；
2. **竞争解释会推翻 endpoint 结论。** 例如训练不足、actor 没收到有效信息、动作被 clipping、奖励与物理目标错配、基线 implementation 不一致；
3. **当前结果本身不具诊断性。** 所有 arms 输出相同是算法等效，也可能是执行器权限被压平；
4. **factorial interaction 是论文中心但无法解释。** 若结果只在某一 source/factor 组合出现，需要有可观察量或干预把交互映射到具体链条；
5. **主张跨越了测试条件。** 若想把一个 budget-specific null 解释成 capacity/expressivity ceiling，需要预算或容量干预；若想说是 physical authority ceiling，需要权限/约束干预。

最低有效的机制实验不是“再跑一些”，而是能区分至少两个竞争解释的实验：

| 竞争解释 | 最小有信息量的诊断 |
|---|---|
| 实现或训练根本不起作用 vs 方法确实无增益 | positive-control task/arm；确认目标代码能在已知可学条件下产生预期差异 |
| 预算不足 vs 结构无增益 | 预注册 budget extension 或 learning-curve saturation test；只对关键 contrast，不全量搜参 |
| 物理权限不足 vs policy 没学会 | action-before/after-projector、saturation/energy/slew 占用；必要时做单一 authority perturbation |
| 信息没有价值 vs learner 未利用信息 | 保持其余条件不变的 information ablation/permutation，加上行为或梯度响应 observable |
| reward 改善但物理端点无改善 | 同一 trajectory 的 reward-to-physical endpoint decomposition；必要时做 reward-term ablation |
| 平均无效但某些工况有效 | 预先定义的 factor × condition interaction、performance profile 和 failure map |

这些实验应在新 protocol 中先写 competing hypotheses、可判别 prediction 和 stopping rule。一个不能改变解释或决策的“更多实验”没有价值。

### 4.2 不必补的情况

若以下条件已满足，根因可以诚实列为 limitation/future work：

- validity 完整，baseline 与 positive control 正常；
- primary contrast 的 uncertainty 足够排除 \(\delta\)；
- 论文只承诺 performance boundary，不承诺 mechanism；
- factorial 已直接给出可行动的边界，例如某 factor 的 main effect/interaction 在预设范围内稳定；
- 补实验只会扩大到新 topology、simulator、hardware 或 algorithm family，而这些不在当前 claim 中；
- 新实验会变成 outcome-guided tuning，无法保留原先 confirmatory 性质。

“不知道为什么没有增益”不会自动毁掉一篇严谨的 benchmark/falsification paper。相反，伪造一个看似完整的 post-hoc 故事会降低可信度。

### 4.3 可选但高回报的机制扩展

在 bounded negative 已成立后，最值得补的是**一个窄而决定性的机制 probe**，而不是另一个大 sweep。优先顺序：

1. 复用已产出的 telemetry，定位 observed action、constraint occupancy、energy/saturation 和 physical endpoint chain；
2. 做一个 single-factor intervention，验证最主要的竞争解释；
3. 仅在该干预会改变标题/摘要主张时才扩大 seeds；
4. 把新结果标为 diagnostic replication，不与原 confirmatory factorial 混池。

## 5. 可直接用于论文的叙事结构

### 5.1 推荐主线

1. **现实问题：** 复杂学习结构常被默认会因更强分工/信息而改进控制，但在强 classical/architectural comparator、物理约束和随机训练下，这个增益没有被严格界定。
2. **可证伪问题：** 在冻结系统、信息、动作权限、预算和 bank 下，目标结构能否超过预设的 minimum useful effect？哪些 factor 改变结果？
3. **公平设计：** 用同一比较器、同一 scenario distribution、独立 seeds、完整失败处理和 outcome-blind analysis；说明为什么每个 arm 都有成功机会。
4. **先给 effect distribution：** 每个 primary endpoint 的 paired/factorial effect、interval、seed distribution、failure/guardrails；不要先给 “significant/not significant”。
5. **再给边界图：** 哪些 factor、endpoint、time regime 或 condition 支持/不支持收益；mixed result 是结果，不是噪声。
6. **机制证据分级：** 直接干预可用 causal language；仅 telemetry correlation 则写 “consistent with”；没有 probe 就明确保留 competing explanations。
7. **技术后果：** 在当前范围内，复杂度、训练成本或部署风险没有换来超过 \(\delta\) 的收益，因此未来研究应改变 formulation/authority/benchmark，而不是继续同一结构的小调参。

### 5.2 一个适合有界负结果的标题逻辑

标题应包含对象和边界，而不是宣布整个领域失败。例如：

- *When [Factorized/Distributed Design] Does Not Add Control Value: A Seed-Resolved Factorial Study on [Bounded System]*
- *Bounding the Incremental Value of [Target Design] Under Fixed Information and Actuation in [System]*
- *No Practically Meaningful Gain from [Target Design] on a Frozen [Control Task]: Evidence, Interactions, and Limits*

若只有“未建立优势”而没有排除 \(\delta\)，第三种标题过强，应改成 *A Rigorous Reassessment of...* 或 *Evidence Does Not Establish...*。

### 5.3 论文中的 claim ceiling

#### Level A：仅未建立优势

> Across the preregistered comparison, we did not establish a reliable improvement of A over B; the uncertainty interval still permits effects of engineering relevance.

不能写 “A has no benefit”。

#### Level B：排除最小有用增益

> Under the tested system, information pattern, action constraints, training budget, and frozen scenario bank, the upper confidence bound excludes an improvement of at least \(\delta\) on the primary endpoint.

这是最适合“完整但负面”的主张。

#### Level C：practical equivalence

> The preregistered equivalence analysis places the effect within \([-\delta,\delta]\), supporting practical equivalence for this endpoint under the tested conditions.

只有双侧边界与 interval rule 预先固定时才能用。

#### Level D：混合结果

> The incremental value was conditional on [factor/condition] and did not persist across [other preregistered endpoints/conditions]; therefore the evidence supports a scoped interaction rather than a general advantage.

不要把 primary failure 用 secondary win 抵消。

#### Level E：机制

> The intervention changed [mechanistic observable] and the endpoint in the predicted direction while holding [controls] fixed, supporting X as a mechanism within the tested model.

没有干预时只能写：

> The telemetry pattern is consistent with X, but does not distinguish it from Y and Z.

### 5.4 明确禁止的越界句式

- “MARL does not work for power-system control.”
- “M/D decoupling is ineffective.”
- “The negative result proves there is no effect.”
- “The fundamental cause is limited actuation/information”——如果没有对应干预；
- “The method generalizes poorly”——如果测试 bank/topology 没有 unseen-population 设计；
- “All methods are equivalent”——如果只是 superiority test 不显著；
- “More training cannot help”——如果没有 budget intervention 或足够强的 saturation evidence。

## 6. 六个最贴近、可借鉴的高质量论文/指南案例

以下不是凭标题或摘要筛选；本研究核对了正文中的设计、结果与限制。它们不是都属于电力系统，但共同覆盖 R485 需要的 statistical boundary、RL variance、strong baseline、mechanism attribution 和 power-system mixed outcome。

### 案例 1：Lakens, Scheel, and Isager (2018) — 把“没显著”升级为可检验的效果上限

**正文做了什么：** 详细给出 TOST、SESOI 的确定途径、五类 worked examples 和报告方法；明确区分传统 null-hypothesis test 与 equivalence test。

**可借鉴：** R485 若要说“没有实用增益”，必须先给工程上有含义的 \(\delta\)，再用 interval/equivalence 规则排除它。最小有用幅度可以来自 operational tolerance、历史 baseline variability、成本收益门槛或先验 paper claim，但不能来自当前结果。

**不可照搬：** 心理学中的标准化 effect-size 经验阈值不应直接移植到电力指标；R485 的 \(\delta\) 必须由物理/控制决策解释。

来源：[final open-access article](https://doi.org/10.1177/2515245918770963)。

### 案例 2：Agarwal et al. (2021) — 小样本 RL 也能做诚实而有信息量的比较

**正文做了什么：** 在 Atari 100k、ALE、Procgen 和 DeepMind Control Suite 上重新审查已有 ranking，展示 point estimates 与 uncertainty-aware analysis 会给出不同结论；提出 stratified bootstrap intervals、interquartile mean 和 performance profiles，并公开 `rliable`。

**可借鉴：** 阴性/混合 R485 不应压成一个平均值。应显示 interval、seed-level distribution、win probability/performance profile、tail/failure 和 factor interaction。多 arm 排名不稳定本身可以是结论，但必须显示 uncertainty。

**不可照搬：** 该文的多-task stratified bootstrap 与 R485 的 seed/factor/scenario 层级未必相同；resampling unit 必须服从 R485 的实际实验单位。

来源：[NeurIPS 2021 paper and supplement](https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html)。

### 案例 3：Mania, Guy, and Recht (2018) — 用强简单基线否定“复杂方法天然更有价值”

**正文做了什么：** Augmented Random Search 用 static linear policies 在 MuJoCo 上达到与复杂 RL 方法竞争的结果；作者不仅按当时常见的 3-seed protocol 比较，还进一步做 100 random seeds 和 hyperparameter sensitivity，发现更严格评价下自身方法的表现也更差、方差很大，并把结论限制到现有 benchmark/evaluation methodology。

**同行评议原文给出的额外教训：** Reviewer 1 认为 100-seed、简单基线和彻底评估使结果对 RL benchmark 很有价值；Reviewer 2/3 同时质疑 algorithm tweaks、task generality、baseline omissions 和论文到底要贡献算法还是评价批判。也就是说，强负结果会被接受，但叙事必须只选一个主对象，不能从“简单基线竞争”跳成“复杂 RL 普遍没用”。

**可借鉴：** R485 的 classical/simple comparator 不是配角，而可能是负结果论文的中心；同时必须主动报告 R485 自身的 sensitivity 和 scope limits。

来源：[NeurIPS 2018 full paper](https://proceedings.neurips.cc/paper/2018/hash/7634ea65a4e6d9041cfd3f7de18e334a-Abstract.html)，[official reviewer reports](https://proceedings.neurips.cc/paper_files/paper/2018/file/7634ea65a4e6d9041cfd3f7de18e334a-Reviews.html)。

### 案例 4：Tucker et al. (2018) — 优秀根因型负结果的完整模板

**正文做了什么：** 先用 total-variance decomposition 指出 action-dependent baseline 理论上可减少的 variance component；再在近似可解析的 LQG 和 continuous-control tasks 中测量各 variance component；随后审查先前论文的公开代码，修复 implementation issues，区分 biased/unbiased variants，并发现先前 gains 来自 implementation bias、poor value-function fitting 和 sample reuse，而不是宣称的机制；最后提出 horizon-aware value function 并验证改进。

**可借鉴：** 如果 R485 要解释根因，最强结构是“理论/可观察分解 → 近可解析 positive control → 代码与实现审计 → 单一干预 → endpoint 响应”。这比在负结果后做大规模超参搜索更有说服力。

**不可照搬：** 作者明确说各 variance component 的相对大小 problem-specific；他们的机制结论只覆盖 tested continuous-control domains 和相应 implementations。

来源：[ICML 2018 full paper](https://proceedings.mlr.press/v80/tucker18a.html)。

### 案例 5：Engstrom et al. (2020) — 用 factorial ablation 把“算法差异”还原成实现差异

**正文做了什么：** 列出 PPO implementation 中九类 code-level optimizations，对其中四类做全组合 ablation；构造 PPO-MINIMAL、PPO-NOCLIP 和 TRPO+；除最终 reward 外，还测量 KL divergence 和 ratio trust-region violations。结果显示，PPO 相对 TRPO 的大部分 reward gain 来自辅助 implementation choices，而非核心 clipping alone，且这些 choices 改变了算法实际工作方式。

**可借鉴：** R485 若 factorial 本身已经把 source/architecture/physical factor 分开，应先利用这些预设 contrasts 与内部 observables；它们可能已经构成 mechanism evidence，不需要另起一个无界 sweep。

**不可照搬：** 该文因计算限制只对选定 optimizations 做 full ablation；其结论仍限定到 PPO/TRPO、tested tasks 和 implementations。

来源：[published ICLR 2020 paper](https://arxiv.org/pdf/2005.12729)。

### 案例 6：Nematshahi et al. (2023) — 最贴近电力系统的 mixed-result 写法

**正文做了什么：** 在 IEEE 14-bus 与 Illinois 200-bus AVC 上，用 DQN/DDPG、五个不同 training seeds、共同 test set，向训练 simulator 注入单线路 8%/20% 和全线路 \([-20\%,20\%]\) impedance errors；分别评价 voltage correction 与 loss。结果显示 voltage recovery 在测试中保持成功，但 model inaccuracy 影响 loss reduction。论文因此不是简单“robust/not robust”，而是按 endpoint 给出 mixed boundary。

**可借鉴：** 对 R485，应分开 common-frequency restoration、relative synchronization、inter-area/physical endpoint、control effort/energy 与 failure；一个 endpoint 的 robust 不得替代另一个 endpoint 的 deterioration。

**需要比该案例更严格之处：** 该文只用五个 agents/seeds，主要依赖 moving-average curves，没有 equivalence margin、完整 uncertainty 或 multiplicity framework，且部分“real-world suitability”语言比 simulator evidence 更宽。应借它的 power-system factor perturbation 和 endpoint separation，不应照搬其 claim ceiling。

来源：[IET Generation, Transmission & Distribution 2023 full article](https://doi.org/10.1049/gtd2.13001)。

## 7. 对 R485 是否补实验的决策清单

在 final artifacts 可读后，只需回答下面七个问题：

1. R485 是否被最终分类为 design-valid、execution-complete、integrity-valid？
2. primary contrast、primary endpoints 和 multiplicity family 是否在结果前固定？
3. baseline/positive control 是否证明 learner、信息与动作通道有成功机会？
4. 每个 primary effect 的 interval 是否排除事先有工程含义的 \(\delta\)？
5. mixed pattern 是否由预设 factor interaction 支持，而不是看结果后分组？
6. 论文主张是 performance boundary，还是要声称 root cause？
7. 候选补充实验是否能区分两个会改变结论的 competing explanations？

对应建议：

- **1–5 均是，6 为 performance boundary：** 不需要为了“论文完整”补实验；直接写 bounded negative/mixed paper。
- **1–3 是，但 4 否：** 当前是 inconclusive；若强负结论值得追求，补独立 seeds/precision，不先做机制 sweep。
- **1–4 是，6 为 root cause，且 7 有明确设计：** 做一个窄的预注册 diagnostic experiment。
- **1–3 任一否：** 先处理 validity，不能把修复动作写成科学补实验。
- **7 否：** 停止扩展，把机制列为 limitation；无判别力的更多实验只增加故事空间。

## 8. 当前仍未解决的不确定性

本 note 没有读取 R485 结果，因此以下问题仍需由 final R485 evidence 回答：

- R485 是否已有 outcome-independent、工程可解释的 \(\delta\)/materiality threshold；
- 当前 26-seed 设计对各 primary contrast 的 interval 是否足以排除该 \(\delta\)；
- factorial main effects/interactions 的独立单位与配对结构如何进入最终 interval；
- baseline competence、action authority、saturation、energy/slew 和 information-use observables 是否已有足够证据；
- mixed result 若出现，是否属于 predeclared interaction 还是 post-hoc subgroup；
- 目标期刊最终 novelty 判断：PES policy 允许“有用数据/经验改变技术”的贡献类型，但不保证任何负结果稿件被接收；
- 若需要 root-cause claim，哪一个 competing explanation 最值得做单一判别实验。

## 主要一手来源

### 官方期刊/会议规范

- IEEE PES, *Preparation and Submission of Transactions Papers*, revised May 2026: <https://ieee-pes.org/publications/authors-kit/preparation-and-submission-of-transactions-papers/>
- IEEE PES, *Information for Authors of PES Transactions Papers*: <https://ieee-pes.org/publications/authors-kit/information-for-authors-of-ieee-power-energy-society-transactions-papers/>

### 统计与研究设计原始/方法论文

- Schuirmann (1987), original TOST comparison: <https://doi.org/10.1007/BF01068419>
- Lakens, Scheel, and Isager (2018), equivalence testing and SESOI: <https://doi.org/10.1177/2515245918770963>
- Nosek et al. (2018), preregistration and confirmatory/exploratory separation: <https://doi.org/10.1073/pnas.1708274114>

### 同行评议案例

- Henderson et al. (2018), *Deep Reinforcement Learning That Matters*: <https://doi.org/10.1609/aaai.v32i1.11694>
- Agarwal et al. (2021), *Deep Reinforcement Learning at the Edge of the Statistical Precipice*: <https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html>
- Mania, Guy, and Recht (2018), paper and official reviews: <https://proceedings.neurips.cc/paper/2018/hash/7634ea65a4e6d9041cfd3f7de18e334a-Abstract.html>, <https://proceedings.neurips.cc/paper_files/paper/2018/file/7634ea65a4e6d9041cfd3f7de18e334a-Reviews.html>
- Tucker et al. (2018), *The Mirage of Action-Dependent Baselines in Reinforcement Learning*: <https://proceedings.mlr.press/v80/tucker18a.html>
- Engstrom et al. (2020), *Implementation Matters in Deep Policy Gradients*: <https://arxiv.org/pdf/2005.12729>
- Nematshahi et al. (2023), *Deep reinforcement learning based voltage control revisited*: <https://doi.org/10.1049/gtd2.13001>
