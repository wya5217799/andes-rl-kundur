# 补证后的允许结论与永久边界

## 证据层级

| 层级 | 含义 | 示例 |
|---|---|---|
| `MATH` | 与项目数值无关的恒等式/反例 | U3 Markov state、U5 transfer derivative、U8反例 |
| `CODE-BOUND` | 与某个源码语义绑定 | projector/replay实现一致 |
| `MODEL-BOUND` | 与冻结线性/DAE equilibrium绑定 | U1 certificate、U5 derivative、U6 pole margin |
| `BANK-BOUND` | 与固定有限 profile/scenario bank绑定 | exact guards、R458 K/4 |
| `ALGO-BUDGET-BOUND` | 与算法/架构/seed/预算绑定 | U2 message effect |
| `DISTRIBUTION-BOUND` | 与声明抽样分布和独立test绑定 | transfer probability interval |
| `DEPLOYMENT-BOUND` | HIL/EMT/保护/硬件和现场条件 | 当前包不覆盖 |

任何论文句子必须标到其中一个层级，不能跳级。

## U1

### 补证后允许

- “在冻结 Object B 线性模型、指定 profile bank、固定 active mode、严格因果 10-tap differential Youla 类和给定 coefficient bound 内，找到一个满足全部列明约束的 witness。”
- 或“经未缩放正对偶下界核验，该精确类在该问题上不可行。”

### 仍禁止

- no controller can satisfy；
- MARL/所有FIR/所有动态控制器不可能；
- 线性 certificate 自动保证 nonlinear safety；
- ring-local，除非 LFT locality另证。

## U2

### 补证后允许

- “在预注册 adapted-SAC architecture、训练预算、seed population与固定 held-out bank 下，真实邻居消息相对保边际非邻居 placebo 的 paired effect 为……。”

### 仍禁止

- messages are intrinsically/universally valuable；
- 由有限预算差直接等同 `I*`；
- 任意拓扑/编码/部署分布外推；
- 把 trajectory 数当训练独立样本数。

## U3

### 补证后允许

- “当前实现把 previous executed action纳入 actor state，并以 executed action训练/target critic，逐步trace和toy MDP核验通过。”
- 若原 replay存在：“历史 raw/executed mismatch导致的冻结 transition target差为……”

### 仍禁止

- 原 replay缺失时给精确历史bias；
- raw-action critic永远非法；
- raw entropy等于physical exploration entropy。

## U4

### 补证后允许

- “对命名的350 schedule family / QY10类和固定 bank，存在/不存在 exact guard-clean witness。”
- “当前 quadratic expected cost不是registered guard set内近似。”

### 仍禁止

- common budget 3保证安全；
- neural optimizer失败证明policy class infeasible；
- finite-bank guard-clean等于部署安全。

## U5

### 补证后允许

- “在固定 mode和equilibrium邻域，完整 candidate/reference ratio total derivative为……，并与direct finite difference在误差范围内一致。”
- 可报告按预定义物理端口 counterfactual 的变化。

### 仍禁止

- A-channel是唯一failure cause；
- 坐标依赖分项当作物理不变量；
- 局部频带返回差当phase margin；
- scalar seam当operator uncertainty。

## U6

### 补证后允许

- 性能数据足够时：“finite-bank `r_d=0.95` crossing位于某 bracket。”
- 完整 pole tracking足够时：“冻结线性模型的 nominal local first destabilizing delay为某 bracket/value。”
- 有正式 uncertainty set时才可报告 robust delay margin。

### 仍禁止

- endpoint crossing等于instability；
- 0.2 s直接称delay margin；
- Padé/Thiran未声明 realization 的极点结论；
- 5.38% scalar seam证明robust stability。

## U7

### 补证后允许

- “在注册 equilibrium、fixed smooth mode、zero-bias feedback和固定 horizon下，M/D controlled-minus-zero-action响应呈二阶amplitude scaling；additive port在声明子空间呈一阶scaling。”
- 可报告局部 tensor/operator norm和finite-window bound。

### 仍禁止

- M/D没有authority；
- 所有M/D controller都不如additive；
- local order disadvantage外推到大扰动/切mode；
- 不同对象现有ratio直接相除。

## U8

### 补证后允许

- “对指定 profile，实际 finite-window cross gain为……，commutator/I-O/Schur上界为……；bound在conditioning为……时有效。”
- “heterogeneity numerator单独不足以预测cross energy。”

### 仍禁止

- heterogeneity必然增加cross energy；
- homogenization总能改善decoupling；
- universal Bode/product lower bound；
- 无full-state projector仍报告 `[A,P_x]` 数值。

## U9

### 补证后允许

- priority 1/2：“从350条冻结family中仅用两个dev profiles选出一条schedule，并在四个固定eval profiles中的K个通过exact guards。”
- priority 3：只报告development无witness和描述性eval passes。

### 仍禁止

- success probability = K/4；
- 4/4证明robust generalization；
- 350类可行/不可行外推到任意controller；
- 隐去priority-2的另一dev failure；
- priority-3升级为transfer witness。

## 最终真实性表述建议

报告中应使用类似：

> All project-specific numerical claims are tied to content-hashed raw matrices or trajectories and are independently recomputed. Mathematical identities are distinguished from model-bound, finite-bank, algorithm-budget, and distributional statements. Missing historical replay, absent uncertainty descriptions, mode changes, or failed certificates are reported as unresolved rather than filled by inference.
