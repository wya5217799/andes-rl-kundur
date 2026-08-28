# 项目关闭后的实验与计算总计划

**对应论文：** *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning*

<a id="authority-and-closure"></a>

## 权限与关闭声明

> **PROJECT STATUS: CLOSED**
> **EXECUTION AUTHORITY: NONE**
> **DOCUMENT STATUS: FROZEN DOCUMENTARY BACKLOG**

- 本项目的实验侧已经结束；本文件不启动、不排队、也不暗示继续执行任何训练、ANDES 仿真、重放、离线统计、制图或数学计算。
- `ARTIFACTS.json` 中的 `active + canonical` 只表示这是当前应读取的计划版本，不表示其中任何工作处于 active execution。
- 本文件只把截至 2026-08-28 能识别出的实验、再分析、计算、复现与外部验证工作完整归档，供论文限制说明、审稿回复或未来独立项目参考。
- 任何条目的“优先级”“判据”“产物”都只是设计信息，不构成当前授权。不存在“上一项完成后自动进入下一项”的机制。
- 若未来确实重开，必须由 owner 明确重开研究线，原子领取新的 successor round，重新冻结 plan、代码、输入和判据，通过双审、preflight、rehearsal 与 seal，并另行给出正式执行授权。本文件不能替代其中任何一步。
- R478--R484 及其父资产保持只读；不得覆盖、回填、重判或把新的 post-hoc 结果冒充原注册结论。
- 本计划取代 2026-08-24 的可执行导向重验证计划作为该手稿线的 canonical `experiment-plan`；旧计划仅保留历史来源意义。

## 文档身份与使用边界

| 字段 | 值 |
|---|---|
| manuscript line | `yang-md-decoupling-marl` |
| plan date | 2026-08-28 |
| plan class | project-closure inventory / non-executable experiment specification |
| canonical predecessor | `corrected_md_revalidation_experiment_plan_20260824.md` |
| current evidence parents | R478, R480, R481, R482, R483, R484 |
| primary manuscript freeze | `manuscript/main.tex`, SHA-256 `33FE35DFEA68ACD12C729388FBA5A8F2A02E3A641875C43E31C66415D01834BD` |
| execution owner | none |
| evidence created by this document | none |
| automatic expiry/launch | none |

本文件中的 `A/B/C/D` 只是工作类别，不是 round、claim 或执行 wave：

- **A 类：** 只使用现有封存数据的再分析、计算、制图和复现整理；仍未获授权执行。
- **B 类：** 需要新闭环评估或 ANDES 轨迹，但不重新训练。
- **C 类：** 需要新训练，用于回答 corrected learner、reward 因果或训练预算问题。
- **D 类：** 面向物理可实现性、泛化和部署的外部有效性验证。

## 当前证据天花板

现有 R478--R484 只支持下面这个有界结论：在冻结的 50-Hz learner convention、注册训练预算、固定 comparator、四个 canary profiles 和精确注册 guard 下，aggregate endpoint qualification 与 complete-contract qualification 不等价。

现有证据不支持：

1. “MARL 普遍做不到并联 VSG coordination”；
2. “60-Hz-corrected learner 也会失败”；
3. “reward--contract mismatch 已被因果证明为唯一失败原因”；
4. “43,200 steps 已经收敛或更长训练不会改变结果”；
5. “110% action tolerance 对邻近阈值、其他 comparator 或硬件极限稳健”；
6. “四个 profiles 可代表某个随机总体的通过概率”；
7. “当前大惯量参数对应已验证的 converter/storage sizing”；
8. “结果已跨拓扑、通信缺陷、EMT、HIL 或硬件成立”。

因此，下面的工作不是把当前有界结论“补成正确”，而是分别决定能否提高论文说服力、扩大 claim 或建立工程外推。

## 总清单与必要性

| ID | 工作 | 新仿真 | 新训练 | 对当前有界结论是否必需 | 若完成可增加的证据 |
|---|---|---:|---:|---|---|
| A0 | 输入身份、哈希与批次纯度冻结 | 否 | 否 | 任何再分析的前置条件 | 可追溯的 secondary-analysis parent set |
| A1 | action RMS/TV ratio、margin 与全分布 | 否 | 否 | 逻辑上非必需；关闭 richer audit 的高优先级缺口 | 结论离 110% 边界有多远 |
| A2 | 邻近阈值曲线与 break-even threshold | 否 | 否 | 同上 | cutoff robustness，仍非硬件安全证据 |
| A3 | comparator 依赖性盘点与离线敏感性 | 条件性 | 否 | 非必需 | primary comparator 依赖范围 |
| A4 | reward cancellation 与 contract mismatch 诊断 | 否 | 否 | 非必需；高价值机制诊断 | 结构不约束与经验共现，不是因果 |
| A5 | convergence certificate 分解与 half--final 变化 | 否 | 否 | 非必需；限制解释所需 | “未建成 policy stationarity”的细化证据 |
| A6 | odd/even 与正负轨迹分解 | 否 | 否 | 非必需 | endpoint 对非线性/不对称响应的敏感性 |
| A7 | 预先固定选择规则的时域图 | 否 | 否 | 非必需；展示优先级高 | 直观控制现象，不增加总体推断 |
| A8 | source-effect estimand 与 interval 对齐 | 否 | 否 | 关闭 richer audit 的高优先级缺口 | 与 signed-rank target 相容的不确定度 |
| A9 | 未注册 factorial effects 的描述性分析 | 否 | 否 | 非必需 | 完整设计图景，仍为 post-hoc |
| A10 | 50/60 Hz、M/D、H、energy/headroom 单位与尺度计算 | 否 | 否 | 限制说明建议项 | 物理解释边界，不等于硬件验证 |
| A11 | common/differential coordinate 与局部数学敏感性 | 否 | 否 | 非必需 | 坐标选择与局部机制稳健性 |
| A12 | 环境锁、归档与 replay package | 否 | 否 | 当前结论非必需；外部复现 claim 必需 | 外部可复现性而非仅内部可追溯 |
| B1 | frozen policy 的 50→60 Hz input-rescaling 闭环敏感性 | 是 | 否 | 当前 audit 非必需 | 已训练网络的 deployment sensitivity |
| B2 | prospectively selected alternative comparator 评估 | 是 | 否 | 当前 audit 非必需 | comparator robustness |
| B3 | 历史 action-penalty checkpoints 的 prospective 评估 | 是 | 否 | 非必需 | 一个候选 mitigation 的评估证据 |
| C0 | 新训练前 feasibility/objective/routing gates | 条件性 | 条件性 | 所有 C 类的硬前置 | 设计可执行性，不产生性能结论 |
| C1 | 60-Hz-corrected learner 全量 matched retraining | 是 | 是 | 只有 corrected-learner capability claim 才必需 | 公平的 corrected learner 证据 |
| C2 | reward-aligned causal ablation | 是 | 是 | 只有 reward 因果 claim 才必需 | reward mismatch 的干预证据 |
| C3 | 43.2k→100k→200k training-budget sensitivity | 是 | 是 | 只有排除 undertraining 才必需 | 预算响应；不能自动证明全局收敛 |
| C4 | constraint-aware learner / projector / Lagrangian successor | 是 | 是 | 只有提出能满足完整 contract 的方法才需要 | 新方法证据，属于新论文对象 |
| C5 | scaling×reward×source 的完整因果 factorial | 是 | 是 | 当前论文完全不需要 | 分离 scaling、reward 与 source interaction |
| D1 | 物理 parameter card、storage/headroom sizing | 条件性 | 否 | 工程外推才需要 | 设备尺度与绝对 guard |
| D2 | cross-H、异质 M/D 与 operating-point bank | 是 | 条件性 | 参数泛化才需要 | 有限参数域稳健性 |
| D3 | unseen-topology / network-strength bank | 是 | 条件性 | topology-generalization 才需要 | 未见图与网络强度证据 |
| D4 | communication delay/loss/quantization | 是 | 条件性 | 通信鲁棒性才需要 | 信息通道退化证据 |
| D5 | noise、estimation、latency、slew、current、energy limits | 是 | 条件性 | safety/deployment 才需要 | 绝对物理约束证据 |
| D6 | prospectively sampled disturbance/profile population | 是 | 条件性 | 概率/可靠性语言才需要 | 对声明分布的统计覆盖 |
| D7 | EMT cross-simulator validation | 是 | 条件性 | EMT 适用性才需要 | switching/inner-loop 层证据 |
| D8 | controller-HIL / power-HIL / hardware test | 是 | 条件性 | 实时/部署语言才需要 | 时延、I/O、算力和设备层证据 |

## 所有未来工作的共同冻结规则

即使未来在另一个项目重开，所有条目也必须先满足这些共同规则：

1. **父输入固定。** 列出每个 checkpoint、profile card、comparator、脚本、依赖与结果根的 SHA-256；不允许“最新文件”这种漂移身份。
2. **原注册结论不回写。** 110%/103% primary decision、四个 registered source contrasts 和 R484 verdict 保持原样；新增分析必须标 `secondary`, `post-hoc descriptive` 或 `new prospective evidence`。
3. **独立单位正确。** learner inference unit 为 training seed；四个 profiles 在 seed 内聚合，不把 policy--profile blocks 当独立重复。四个固定 profiles 不产生 population probability claim。
4. **批次纯度。** 新 confirmatory training 必须 all-fresh；不得混用旧 checkpoint、optimizer、replay buffer、curve、evaluation row 或 outcome-selected seed。
5. **同时间 source intervention。** N/P 对照必须保持同一时刻、同一 source multiset 和 contemporaneous pool，只改变预注册 routing；先做 routing-only falsification，再允许训练。
6. **直接检验 materiality boundary。** 对 `log(1.10)` 等边界直接构造 null，不能用“对零显著”代替“超过实质边界”。
7. **目标语义门。** 任何 reward/loss/objective 修改必须写精确公式、单位和 aggregation，并在真实 learner 上用梯度方向 probe 验证惩罚确实使目标统计量下降。
8. **feasibility-before-training。** 先证明 comparator、action map、clamp、slew、guard 和仿真对象可行，再花训练预算。
9. **双审。** 同一冻结 plan 先做确认性 protocol review，再由不知道前一审结论的 adversarial reviewer 构造失败场景；P0/P1 全部关闭后方可 seal。
10. **一次执行。** 正式结果不可因 outcome 不理想而调阈值、换 comparator、补 seed 或重启；需要修复时进入新 successor round。

## A 类：现有封存数据上的再分析与计算

### A0. Secondary-analysis parent freeze

- **问题：** 后续结果是否只来自 R483/R484 允许的父对象，且没有混入旧 bug-tainted、development、fresh-only 或不同 horizon 数据？
- **输入：** R478--R484 reports、R483 training/eval/checkpoint manifests、R484 30-s raw blocks、当前 guard implementation、当前 manuscript freeze。
- **方法：** 建立 create-only manifest，记录文件计数、相对路径、大小、SHA-256、round/claim 身份、bank、horizon、seed、arm、profile 和 exclusion reason；逐项验证现有 `.sha256` sidecar。
- **硬排除：** pre-R478 directional evidence、R482 未纳入论文的候选 checkpoints、6-s 与 30-s pooling、fresh 与 canary pooling、development selection rows、任何 scratch/spot-check 输出。
- **产物：** `secondary_parent_manifest.json`、验证日志、无重复/缺失/越界报告。
- **停止规则：** 一个 required parent 缺失、hash mismatch、身份冲突或 batch impurity 即停止；不允许 available-case 继续。
- **解锁/不解锁：** 只解锁 A1--A11 的可执行资格；本身不增加论文证据。

### A1. Action RMS/TV ratio、margin 与分布

- **问题：** 832 个 policy--profile blocks 的 action guard 失败离 1.10 comparator-relative boundary 有多远？
- **输入：** A0 通过后的 R484 learned trajectories 与同 profile direct-M/D references；metric implementation 必须与 R484 完全同源。
- **计算：** 对每个 block 分别重算
  \[
  \rho_{\mathrm{RMS}}=\frac{\mathrm{RMS}(a_{\mathrm{learned}})}{\mathrm{RMS}(a_{\mathrm{direct}})},\qquad
  \rho_{\mathrm{TV}}=\frac{\mathrm{TV}(a_{\mathrm{learned}})}{\mathrm{TV}(a_{\mathrm{direct}})},
  \]
  其中 TV 保留原实现的“从零动作到首步”的起点语义。记录 ratio、`ratio-1.10` margin、分子、分母和 denominator validity。
- **聚合：** block-level 只作描述；policy-level 以四个 profiles 等权聚合，并同时报告 `4/4` complete-contract status。报告 min、Q1、median、Q3、max、ECDF、log-scale distribution 和 endpoint-qualified 子集；不把 832 当独立样本做 p-value。
- **判据：** 重新计算的 1.10 Boolean 必须逐格复现 R484 原判定；任何不一致先判分析实现失败，不解释结果。
- **产物：** machine JSON、CSV、ratio distribution figure、endpoint-improvement--action-stress scatter/Pareto figure、完全可复现脚本、逐文件 hash。
- **解锁：** 只能说明 margin 大小和 cutoff proximity。
- **不解锁：** 不把 1.10 变成 hardware/safety limit，不改变原注册 verdict。

### A2. 邻近阈值与 break-even sensitivity

- **问题：** `0/208` complete-contract headline 在邻近经验阈值下是否保持？
- **冻结网格：** frequency no-harm multiplier `{1.00, 1.03, 1.05, 1.10}`；action RMS/TV multiplier `{1.10, 1.20, 1.50, 2.00}`。原注册点 `1.03/1.10` 始终单独标注为 primary。
- **连续量：** 对每个 policy 计算在其他 guard 固定时使四 profiles 全部通过的最小 action multiplier
  \[
  \tau_p^*=\max_{b\in\mathcal B_p}\max(\rho_{\mathrm{RMS},b},\rho_{\mathrm{TV},b}),
  \]
  仅当该 policy 的全部 non-action guards 已通过时，`tau_p^*` 才是 complete-contract break-even；否则记 `NA`，只把它解释为 action-guard break-even。报告 roster-level pass curve，而不是只展示人为挑选的网格。
- **控制：** 除被扫描阈值外，endpoint、finite、frequency、peak、RoCoF、mapping、bound、slew 等 guard 全部固定；不得因看到结果再增加“刚好翻转”的阈值。
- **统计：** 所有结果为 deterministic sensitivity table；不需要显著性检验，不产生 population pass probability。
- **产物：** threshold surface、policy pass curve、每个翻转的 exact reason。
- **解锁/不解锁：** 解锁 cutoff robustness 描述；不解锁绝对安全或行业合规。

### A3. Comparator dependence

- **问题：** action-stress 结论是否只对当前 development-selected direct-M/D comparator 成立？
- **阶段 A3a：** 盘点 R481/R484 是否已经存在与 learned policies 完全同 profile、同 horizon、同 action metric 的其他 deterministic references。只有身份兼容的 reference 可离线计算。
- **阶段 A3b：** 任何 alternative comparator 必须按 canary-blind 规则预先固定：沿用历史 development ranking 与 deterministic tie-break，或完整报告所有预先存在的 deterministic laws，不得根据 learned canary outcome 选“最有利” comparator。
- **输出：** primary comparator 结果保持主位；alternative rows 明标 sensitivity。报告每种 comparator 下 ratio margins、threshold curve 和结论翻转。
- **路由：** 若没有同对象 raw trajectories，A3 停在“数据不足”，转入 B2；不得用不同 horizon/bank 的旧数字拼接。
- **不解锁：** alternative comparator sensitivity 不能重写原注册 comparator verdict。

### A4. Reward--contract mismatch 与 cancellation index

- **问题：** fleet-mean action penalty 是否在结构上允许 agent 间抵消，且这种抵消是否与 action RMS/TV failure 共现？
- **解析部分：** 对每个时刻分别定义
  \[
  C_M=1-\frac{(\frac14\sum_m\Delta M_m)^2}{\frac14\sum_m(\Delta M_m)^2},\qquad
  C_D=1-\frac{(\frac14\sum_m\Delta D_m)^2}{\frac14\sum_m(\Delta D_m)^2}.
  \]
  分母为零时记 `NA`，不得以零填充。由 Jensen inequality 给出 `0<=C<=1` 的条件和 equality cases。
- **轨迹部分：** 对每个 policy/profile/sign/pair-kind 计算 time-integrated fleet-mean penalty、componentwise energy、cancellation index、action TV、saturation fraction 与 A1 ratios；先在 block 内聚合，再在 seed 内四 profiles 等权聚合。
- **关联分析：** 报告 rank correlation、分层散点和 endpoint-qualified/非-qualified 的描述性差异；不使用 profile blocks 伪造样本量。
- **因果边界：** 允许写“legacy reward does not constrain componentwise magnitude or TV, and the stored trajectories are consistent with cancellation/action stress co-occurrence”。禁止写“该 reward 已被证明导致 832/832 failure”。因果结论必须等 C2。
- **产物：** algebra note、machine summary、cancellation/action-stress figure、claim-boundary note。

### A5. Convergence certificate 与预算内学习状态

- **问题：** 208 cells 未通过 certificate 的具体原因是什么；43,200 steps 内是否存在 loss stability、policy drift 与 performance change 的分离？
- **输入：** R483 `full_curves.npz`、`adaptive_trace.json`、half/final checkpoints 和 matched evaluations。
- **计算：** 逐 gate 报告 actor loss、critic loss、alpha、gradient、TDS validity、fixed-state action-probe drift 的 pass/fail 与 margin；画全体分布和预先固定的代表曲线。
- **half--final：** 对每 seed/arm/profile 计算 half→final endpoint、action RMS/TV、guard status 和 action-probe drift 变化；生成 paired transition table。
- **plateau 规则：** 可报告最后固定窗口的 slope/variance 作为描述性诊断，但不得以“曲线看平”宣称 convergence。当前数据若仍有 policy-output drift，只能写“registered budget did not establish stationarity”。
- **解锁：** 更精确地限定 undertraining alternative explanation。
- **不解锁：** 不排除 100k/200k 的变化，不证明局部或全局最优；排除 undertraining 必须做 C3。

### A6. Odd/even 与 per-sign response

- **问题：** 注册 odd endpoint 是否隐藏显著的非线性或正负不对称响应？
- **定义：** 对相对 nominal 的同一 signed pair，计算
  \[
  x_{\mathrm{odd}}=\frac{x^+-x^-}{2},\qquad
  x_{\mathrm{even}}=\frac{x^++x^-}{2}.
  \]
- **计算：** 对 common、differential、localized probes 分别报告 odd/even energy、even-to-odd ratio、正负轨迹各自 IAE/peak/RoCoF，以及异常 sign pair 清单。
- **主次：** 原 odd endpoint 和 raw physical guards 保持 primary；even/per-sign 只作 post-hoc nonlinear diagnostic，不重新裁决 R484。
- **完整性：** 正负任一轨迹缺失、时间轴不匹配或 nominal 定义不一致，则该 pair invalid；不做单边替代。
- **产物：** paired-response summary、supplement figure/table、flip audit。

### A7. Representative time-domain figure

- **问题：** 能否直观看到“endpoint 改善但 M/D 命令高应力”的控制现象？
- **选择规则：** 使用冻结 roster 中“按 arm、seed、profile 词典序排序后的第一个 aggregate-endpoint-qualified 但 complete-contract-failed policy”，并取其第一个 canary profile；direct comparator 使用同一 profile。该规则在绘图前写入 manifest，禁止手工选最好、最坏或最漂亮曲线。
- **面板：** 四台 VSG 的 `Delta f_i(t)`；common/differential coordinate；`M_i(t)`；`D_i(t)`；两类 normalized action；必要时附 comparator overlay 与 guard boundary。
- **校验：** 图中的每条线从 raw arrays 重建；figure data 单独导出并与 source block hash 绑定；caption 明确该图是 deterministic example，不代表分布。
- **产物：** vector PDF、PNG preview、figure-data JSON/CSV、selection manifest。
- **不解锁：** 单例图不增加总体统计结论。

### A8. Source-effect estimand、test 与 interval 对齐

- **问题：** 现有 exact signed-rank materiality decision 是否有同一 target 上的 effect estimate 和 interval？
- **单位：** 对四个预注册 effect 中的每一个，先在每个 seed 内按注册规则对 profiles 和 nuisance levels 等权聚合，形成 26 个 seed-level contrast values；即每项检验 `n=26`，四个 effects 构成 Holm family，而不是四个 observations。不对 policy--profile rows 直接推断。
- **primary test：** 保留对 `log(1.10)` boundary-centred effect 的 exact one-sided Wilcoxon signed-rank test 与四项 Holm family，不改变方向、ties/missingness 规则或原判定。
- **相容估计：** 报告 seed-level location pseudomedian 的 Hodges--Lehmann estimate，并用 signed-rank inversion 构造 exact interval。若需要 familywise interval，预先选择 Holm-compatible closed-testing inversion；若实现未获独立验证，则退回保守的四项 Bonferroni simultaneous one-sided bounds，并明确其保守性。
- **分离：** `Delta_geo` mean-log transformation 继续标 descriptive；不得拿 rank-based p-value 给 mean effect 背书。
- **horizon：** 6-s 与 30-s effects 分表、分 family 报告，绝不 pooling。
- **验证：** 用小样本穷举/已知例验证 test inversion；tie、zero 或 symmetry assumption 不满足时按 plan 报 invalid/assumption-limited，不切换 asymptotic fallback。
- **产物：** aligned estimate table、interval algorithm tests、machine JSON、原/Holm decision reproduction。

### A9. 完整 factorial 的 post-hoc 描述

- **问题：** 未进入注册 family 的 reward main、actor×reward 和 actor×critic×reward effects 是什么方向与量级？
- **计算：** 在与注册四项完全相同的 seed-level log-ratio coordinate 上，补齐三项 effects；同时给出全部七个 factorial effects 的统一 descriptive table。
- **身份：** 三项新增 effects 标 `post-hoc descriptive / hypothesis-generating`；不加入原 Holm family，不事后制造 confirmatory p-value。
- **输出：** estimate、bootstrap/leave-one-seed-out stability 仅作描述；如果报告 interval，必须与 target 一致并明确非 confirmatory。
- **解释边界：** source intervention 同时改变 routing authenticity、optimization 和 dependence structure，仍不得称 pure neighbour semantic information value。

### A10. 物理单位、50/60 Hz 与参数尺度计算

- **问题：** 当前 controller/plant base、M/D/H 与动作尺度在数学和工程上分别代表什么？
- **unit ledger：** 逐字段列 device base、system base、controller nominal frequency、plant nominal frequency、normalized observation/action、runtime M/D readback、reported physical endpoint；写出每次转换方程并证明只转换一次。
- **scaling audit：** 解析比较 50-Hz learner convention 与 60-Hz physical endpoint/direct-law calibration，列出哪些量受 `60/50` 影响、哪些不受影响；不得把解析差异冒充闭环反事实。
- **inertia/energy：** 对每台机组计算 `H=M/2`，再用 `E=H*S_n` 将等效惯量常数映射到能量尺度；进一步计算在给定效率、允许 state-of-charge 窗口和支撑时长下的 storage/headroom requirement。所有假设单独列出并做 range sensitivity。
- **damping/action：** 将 normalized `Delta M/Delta D`、clamp 和 slew 映射到 runtime parameter change；只有获得设备额定功率、电流、DC-link/储能与控制更新率时，才允许提出 absolute action guard。
- **外部依据：** 若要比较工程常见范围，必须另做 source-bounded literature/standard review；当前 project calibration 不自动成为 Yang benchmark 或 hardware design。
- **产物：** unit/base table、equation audit、parameter-scale notebook/report、assumption ledger。

### A11. 坐标与局部数学敏感性

- **common coordinate：** 比较注册 arithmetic mean、fixed-baseline inertia-weighted COI 和 instantaneous-M-weighted sensitivity；后者不得偷偷替换 primary estimator。
- **differential coordinate：** 保留注册 two-area orthonormal basis，同时在 outcome-blind 的 corrected equilibrium 上构造 nominal modal/coherency subspace；冻结 mode order、complex-pair handling、phase/sign 与 projection。
- **比较量：** subspace angles、endpoint rank、policy qualification flips、same-profile comparator ratios。
- **局部数学：** 复核 zero-action M/D invariant、folded first-order channel、corrected-base local M/D tensors 和必要的 finite nonlinear ladder；严格分开 algebraic identity、linearized prediction 与 time-domain evidence。
- **边界：** 坐标敏感性只能说明 finite bank 上的表示稳健性；不能推广到未见 topology 或 DAE 全局定理。

### A12. 外部复现与归档

- **问题：** 能否从独立机器由一个稳定入口重建 manuscript tables/figures 和 primary decisions？
- **内容：** versioned source snapshot、208 checkpoint identities、profile/parameter cards、case files、16-shard/trajectory manifest、Python/ANDES/OS/solver lock、CPU/thread assumptions、regeneration commands、licenses、expected hashes 和失败诊断。
- **环境：** 优先 container 或完整 lockfile；如果 ANDES/WSL/solver 不能容器化，提供可验证的 layered environment specification 和 installed-case hash。
- **存储：** public DOI repository 或 access-controlled deposit；若仍为 local-only，论文只能写 internal traceability，不写 unrestricted reproducibility。
- **replay gate：** 在干净目录、无仓库缓存的环境执行一次 source extraction→build→figure/table regeneration；不得运行新 scientific experiment来填缺口。
- **产物：** archive manifest、access identifier、environment lock、replay report。

## B 类：需要新闭环评估、但不重新训练

### B1. Frozen-policy 50→60 Hz input-rescaling sensitivity

- **问题：** 已训练的 50-Hz networks 在 deployment 时若对相关 observation 做已声明的 60-Hz rescaling，闭环结果如何变化？
- **对象：** checkpoint 权重完全冻结；只改变明确列出的 observation adaptation；plant、profiles、actions、horizon、comparator、guards 和 seeds 固定。
- **设计：** 若只做 8 arms×1 seed，结果必须标 engineering diagnostic，不能用于关闭公平性质疑。若要与现有 208-policy family 对称比较，应评估全部 8 arms×26 seeds×4 profiles，并用 paired seed-level analysis。
- **必要性：** 旧 trajectory 不能离线生成这个闭环反事实，因为动作改变后 plant state 和后续 observations 会共同变化；必须新跑 ANDES。
- **判据：** 报 endpoint、完整 guard、A1 ratios 和 50→60 paired change；不重新选择 comparator 或阈值。
- **解锁：** frozen network 的 input-scaling/deployment sensitivity。
- **不解锁：** 不回答“从一开始按 60 Hz 训练会怎样”；该问题属于 C1。

### B2. Prospectively fixed alternative comparator evaluation

- **触发：** A3 发现没有同 bank/horizon 的 alternative comparator raw trajectories，但论文仍希望声称 comparator robustness。
- **选择：** 只能用 canary-blind development bank 预先选择零动作、原 direct-M/D winner 和预注册的 alternative law roster；tie-break 在执行前固定。
- **设计：** 在与 R484 相同的四 profiles、30-s horizon、signed scenarios 和 guard implementation 上生成 references；learned checkpoints 保持冻结。
- **输出：** 每个 comparator 下的 action ratios、threshold curve、complete-contract roster 和 conclusion-flip matrix。
- **边界：** 这是新 prospective evaluation evidence，不能并入原 R484 primary comparator decision。

### B3. 既有 action-penalty checkpoints 的 prospective evaluation

- **对象：** 仓库中报告存在、但当前论文明确排除的 R482 action-penalty candidate checkpoints；执行前必须重新核对数量、hash、训练身份和 exclusion status，不能假设完整。
- **问题：** 候选 action penalty 是否在同一 R484 contract 下改变 RMS/TV stress 与 endpoint trade-off？
- **设计：** 使用同一 comparator、profiles、horizon、guards 和 deterministic metric code；所有 checkpoints 一次性进入新 successor evaluation round。
- **推断：** 若训练设计与 primary learner 除 penalty 外还有差异，只能称候选 mitigation evaluation，不能称 reward causal ablation。
- **停止：** parent identity 不完整、checkpoint recurrent-target defect、任何 canary leakage 或 metric mismatch 即不执行。

## C 类：需要新训练的实验

### C0. 所有新训练的硬前置

1. corrected 60-Hz observation/action/unit contract 通过 zero/nonzero/reset/readback invariants；
2. deterministic comparator 在同一对象上先通过全 guard feasibility；
3. reward/loss 精确公式、单位、aggregation、coefficient-selection bank 和梯度方向 probe 冻结；
4. N/P routing 在每个 time/slot/scenario 上证明同一 source multiset、fixed-point-free、非真实邻居、same contemporaneous pool；
5. seed、base state、profile、checkpoint、training budget 和 missing-cell policy 冻结；
6. all-fresh batch；任何旧 optimizer/replay/checkpoint carryover 为零；
7. 独立 confirmatory reviewer 与 adversarial reviewer 均无 P0/P1；
8. measured capacity、disk、memory、process/thread budget、rehearsal、seal 和 owner launch authorization 全部存在。

任一项不满足即停止，不能靠“先跑几个看看”跨过。

### C1. 60-Hz-corrected learner matched retraining

- **问题：** 在从训练开始就采用一致 60-Hz controller scaling 时，冻结 learner family 是否仍出现 endpoint/complete-contract separation？
- **60-Hz 绝对性能设计：** 8 source-factor arms×26 seeds，208 个 all-fresh 60-Hz cells；可描述 corrected learner 在冻结 reward、budget 和 finite bank 下的结果。历史 50-Hz bank 只能作 descriptive reference，不能构成 scaling 的 causal paired contrast。
- **scaling 因果设计：** 若目标是估计 50→60 effect，必须在同一批次训练 scaling `{50,60}`×8 arms×26 paired seeds，共 416 个 all-fresh cells；两侧除 scaling 外的 routing、reward、budget、profiles、comparator、metric code 与环境必须完全相同。
- **判据：** primary 仍为 complete-contract pass 和 registered source contrasts；只有 416-cell same-batch 设计可报告 causal 50→60 paired effects。
- **claim：** 208-cell 版本只支持 corrected learner 的 finite-design 描述；416-cell 版本才支持 scaling effect。
- **边界：** 仍然只覆盖原 reward 和 43,200-step budget；不能同时关闭 reward mismatch 或 undertraining。

### C2. Reward-aligned causal ablation

- **问题：** 直接优化 componentwise action magnitude 与 variation 是否会降低 guard stress，而不破坏 endpoint？
- **legacy arm：** 原 fleet-mean penalty 保持不变。
- **aligned arm 候选公式：**
  \[
  r_{\mathrm{act},t}=-\lambda_M\frac14\sum_m\left(\frac{\Delta M_{m,t}}{M_s}\right)^2
  -\lambda_D\frac14\sum_m\left(\frac{\Delta D_{m,t}}{D_s}\right)^2
  -\lambda_{TV}\frac18\sum_{m,c}|a_{m,c,t}-a_{m,c,t-1}|.
  \]
  `M_s,D_s`、首步 previous action、clipping 与所有 `lambda` 必须在 development-only bank 固定；梯度 probe 必须证明三项分别降低目标统计量。
- **最低因果 slice：** fixed authentic actor/critic source、固定 reward-access condition、26 paired seeds，legacy vs aligned 两臂；除 reward 外全部相同。
- **完整 factorial 版本：** 若要保持 source-effect 外推，则在 8 source arms 上交叉 reward-contract factor，共 8×2×26 cells；不得用最低 slice 推断 source interaction。
- **primary outcomes：** action RMS/TV ratios、complete-contract pass、endpoint non-inferiority、saturation/slew、cancellation index。
- **claim：** matched intervention 可支持 reward 设计的因果作用；A4 只能提供机制动机。

### C3. Training-budget sensitivity

- **问题：** registered budget 未通过 policy-stationarity certificate 是否主要因为训练不足？
- **设计：** 若回答当前 R483 的 undertraining alternative，只能冻结原 50-Hz contract 并改变 budget；若研究 60-Hz learner 的 budget response，则不得回推 R483。连续 budget ladder 为 `43,200→100,000→200,000`，使用同一 training stream 的预定 checkpoints，不能在结果变好时提前停、在结果不好时临时延长。
- **样本：** 若要描述整个冻结 family 的 budget response，使用全部 8 arms×26 seeds；小于该规模只能标 exploratory。
- **分析：** seed-level repeated measures；报告 endpoint、complete contract、A1 ratios、certificate gates、fixed-state probe drift 与 last-window slopes。对多 budgets 的 primary comparison 和 multiplicity 在执行前冻结。
- **停止：** numerical instability、data corruption 或预注册 safety/compute stop 可终止；performance 不理想不是停止/重调理由。
- **边界：** 未见改进只能写“tested budget extension did not establish a material improvement”，不能写“undertraining 已被排除”；预算内稳定也不等于全局最优或“MARL 上限”。

### C4. Constraint-aware successor learner

- **问题：** 能否在 policy/action map 内直接保证或优化 complete contract，而不是只在事后审计？
- **候选路径：** differentiable action smoothing、rate-limited projector、constrained/Lagrangian SAC 或 control-barrier/safety layer；一次 round 只选择一个科学变化。
- **前置：** 先证明 deterministic feasible set 非空；写出 projector/Lagrangian 的数学对象、约束单位、可行域和失败行为；做 objective semantic probe 与 constraint residual tests。
- **开发/确认分离：** coefficient/hyperparameter 只在 development profiles 和 development seeds 上选；冻结后用全新 confirmatory seeds/profiles。
- **比较：** matched corrected learner、legacy learner 与 deterministic direct-M/D；同时报告 endpoint、所有 guards、constraint violations 和 intervention frequency。
- **定位：** 这是新方法对象与潜在新论文，不是当前 audit paper 的补丁。

### C5. Scaling×reward×source 完整因果 factorial

- **问题：** scaling mismatch、reward mismatch 与 actor/critic source interventions 是否存在交互，谁能解释 complete-contract failure？
- **最低结构：** scaling `{50,60}`×reward contract `{legacy,aligned}`×冻结 authentic source configuration×26 seeds，共 104 all-fresh cells，只回答 scaling/reward 与交互。
- **完整结构：** 上述 2×2 与 8 个 source arms 交叉，共 832 all-fresh cells；用于同时恢复 source main/interactions。
- **分析：** seed 内 matched factorial contrasts；提前冻结 primary family、materiality boundaries、multiplicity、missing-cell invalidation 和 power。
- **限制：** 成本极高，且研究问题已超出当前论文；不得把它描述成“投稿前补实验”。

## D 类：物理、泛化与部署证据梯

### D1. Physical parameter card 与 storage/headroom sizing

- 从真实 converter rating、DC source/storage、允许能量窗口、current limit、power headroom、update rate 和 thermal duration 出发定义 `H/M/D` 可行范围。
- 把 comparator-relative guard 转换为设备绝对 amplitude/slew/energy/current guard；没有设备数据时保留为 numerical stress regime。
- 先做静态 sizing 与 worst-case energy balance，再决定是否值得仿真；静态不可行直接停止。

### D2. Cross-H、异质参数与 operating-point bank

- 预先冻结 lower/nominal/upper H、D、device-rating heterogeneity、load level、renewable penetration 和 operating point；采用 factorial 或 space-filling design，不按结果补点。
- 每个 profile 先做 equilibrium/linearization/guard-feasibility，再做 30-s nonlinear evaluation；若学习器需要适配，明确 zero-shot、fine-tune 或 retrain，三者不可混称。
- 只对实际测试的有限域作 robustness claim。

### D3. Unseen topology 与 network strength

- 构造训练/开发完全未见的 line outage、corridor reactance、area coupling 和 network-strength identities；若没有 unit-valid SCR conversion，只称 reactance/corridor proxy。
- graph identities、disturbances 与 controller information pattern 在训练前冻结；zero-shot 与 retraining 分开。
- 至少三个以上独立 unseen graph families 才讨论 topology generalization；单图只是 case study。

### D4. Communication impairment

- 因子：fixed/random delay、packet loss、burst loss、quantization、asynchrony、stale packet、clock jitter。
- source intervention 仍保持 same-time counterfactual；若研究 stale information，必须作为单独 timing factor，不能与 routing authenticity 混在一个 P arm。
- 先测 deterministic communication fallback 与 fail-safe，再测 learner；报告 instability、missing-data policy 和 fallback activations。

### D5. Measurement、actuation 与 safety limits

- 加入 PMU/estimator noise、RoCoF filtering、sensor bias、observation latency、actuator deadband、rate limit、saturation、current limit、DC-link/storage energy和 thermal duration。
- 所有 guard 改为绝对物理单位，并由设备/标准/设计依据给出；经验 comparator-relative threshold 不能代替。
- 任何 safety claim 需要 worst-case violation、duration、recovery 和 fail-safe evidence，不只报告平均 reward。

### D6. Population-level disturbance/profile study

- 先声明 profile 生成分布、参数支持集、相关结构、排除规则和独立采样单位；再做 sample-size/power 或置信区间设计。
- development、selection、canary、final holdout 使用不同随机身份；final bank 看过后不得降格为 development。
- 只有这样才能报告 pass probability、failure rate 或 reliability interval；当前四个固定 profiles 永远只代表 `4/4` finite-bank result。

### D7. EMT cross-simulator validation

- 把 phasor-domain plant、converter inner loops、PWM/average model、current control、PLL/GFM implementation、sampling和 protection 映射到 EMT model。
- 先做 equilibrium/steady-state、zero-action、step-response 和 deterministic comparator cross-simulator agreement，再评估 learner。
- 报告模型差异而非强求 bit-identical；预注册哪些差异会阻断结论迁移。

### D8. HIL 与硬件

- 依次为 controller-HIL、power-HIL、实验台；每一级先测 deterministic comparator、I/O timing、jitter、dropout、compute deadline、quantization 和 emergency fallback。
- learner deployment 固定 checkpoint 与 runtime；禁止在线学习在安全验证中改变对象。
- 报告 missed deadlines、worst-case latency、constraint violation、保护动作与恢复，不以均值掩盖尾部风险。

## 依赖顺序（仅用于归档理解，不构成队列）

1. A0 是所有 A 类工作的共同前置。
2. A1 完成后才有 A2；A3 先盘点，数据不足才可能进入 B2。
3. A4--A11 可在 A0 后相互独立，但所有结论必须保持 post-hoc/diagnostic 身份。
4. B1/B2/B3 都需要新的 evaluation successor round，彼此不自动授权。
5. C0 是所有新训练的硬 gate；C1 只解决 scaling，C2 只解决 reward，C3 只解决 budget。
6. 若要同时归因 scaling 与 reward，必须用 C5，不能把 C1、C2 的分开结果事后拼成 interaction claim。
7. D1 的静态物理可行性先于 D2--D8；D7 先于 D8。

## Claim-to-work 映射

| 想说的话 | 最低所需工作 | 即使完成仍不能说 |
|---|---|---|
| 失败不是刚好卡在 110% | A0+A1+A2 | 110% 是安全/行业阈值 |
| reward 结构允许 cancellation，轨迹中也共现 | A0+A4 | reward 是唯一因果原因 |
| reward 改造导致 action stress 降低 | C0+C2 | 对其他 topology/设备也成立 |
| 50-Hz convention 影响 frozen checkpoints | B1 | 60-Hz 从头训练仍失败/成功 |
| 60-Hz-corrected learner 在当前 contract 下表现如何 | C0+C1 | MARL 普遍能力上限 |
| 43,200 steps 不是主要瓶颈 | C0+C3 | 已到全局最优 |
| primary result 对 comparator 稳健 | A3；不足时 B2 | 对任意合理 comparator 稳健 |
| signed-rank decision 有相容 effect/interval | A0+A8 | mean-log effect 获得同一个 p-value |
| current calibration 有工程意义 | A10+D1 | 已验证真实硬件 |
| topology/communication/EMT/HIL 稳健 | D3/D4/D7/D8 各自完成 | 未测试层级也成立 |

## 明确不再续跑的历史路线

下列对象不因本总计划而恢复：

- pre-R478 bug-tainted positive evidence；
- aborted、invalid、superseded 或 tuning-only rounds；
- 不属于当前 direct-M/D audit thesis 的 energy-port learning branch；
- outcome-visible comparator retuning；
- 为了让表格更好看而补少量 seeds、换阈值或换 endpoint；
- 把 R482 candidate checkpoints 直接并入 R484；
- 把 6-s/fresh/deterministic 结果与 30-s/canary/learned 结果 pooled；
- 在当前项目中做无上限的算法、reward 或 hyperparameter sweep。

这些路线若未来被重新提出，必须作为新的研究对象重新证明必要性，不能从旧计划继承执行资格。

## 若未来另立项目时的正式流程

下面只是流程记录，不是当前操作指令：

1. owner 明确一条可证伪 objective、claim ceiling 与 stop condition；
2. 运行 session context，确认没有冲突 active round；
3. 原子领取新 successor round，选择 `evidence` lane；
4. 从本文件只拷贝相关工作项，重新写 prospective `memory/rounds/R<N>/plan.md`，不得把整份 backlog 当活计划；
5. 冻结 parent hashes、公式、sample size、seed/profile identities、comparators、thresholds、统计与 missingness；
6. 运行 confirmatory + adversarial 双审，先清 P0/P1；
7. 完成 preflight、objective semantic probes、routing falsification、formal-entry rehearsal、capacity/disk 证明与 seal；
8. owner 对具体 sealed attempt 另行授权；
9. 一次性执行，结果 create-only，逐文件 sidecar 和 archive manifest；
10. 先写 canonical feed，再做 evidence audit 与 power-system audit，最后注册 claim/verdict；
11. 新证据只通过 manuscript mapping 进入论文，不覆盖原 R478--R484 身份。

## 本计划的完成判据

- 已覆盖 reviewer 指出的 scaling、reward、threshold、H/physical scale、convergence、odd/even、factorial inference、source interpretation、time-domain presentation 和 reproducibility 问题。
- 已纳入旧计划仍有科学意义的 coordinate/local-math、comparator、constraint-aware、topology、communication、EMT 与 HIL work。
- 每一项都给出问题、输入/设计、输出、判据或边界，并明确是否需要新仿真/训练。
- 当前有界论文、richer audit closure、corrected learner、causal redesign 与 deployment claims 的最低证据要求互不混淆。
- 全文没有执行命令、当前 round、自动队列或隐含授权；project-closed 状态在开头和结尾重复确认。

<a id="decision"></a>

## 最终决定

本项目不再执行上述任何实验或计算。当前论文若继续提交，只能按现有 R478--R484 支持的 guard-first frozen-design audit 结论提交，并诚实保留未完成 A/B/C/D 工作对应的限制。若不接受这些限制，就应停止该 claim，而不是在当前项目里补跑。

本文件产生的唯一成果是一个完整、可追溯、不可自动执行的研究 backlog；它不产生新证据，也不改变任何已封存结论。
