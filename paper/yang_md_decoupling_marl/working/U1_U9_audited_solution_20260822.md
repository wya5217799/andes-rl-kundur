# U1–U9 审计解答：Object A / Object B 解耦、学习语义与有限证书

日期：2026-08-22  
模式：`deep`  
证据根目录：`/mnt/data/gpt_pro_math_pack_20260822`

## 0. 结论总表

| 项目 | 最强有效结论 | 真值标签 | 三类归属 |
|---|---|---|---|
| U1 | 对命名类 `QY10`，30 步 Object B 浮点锥程序的最优 phase-I 松弛为 `0.0599381277797819>0`，且有可重放的正对偶下界；该类在声明数值容差内不可行 | **COMPUTATIONALLY VERIFIED** | paper-grade proposition（有限类数值证书） |
| U2 | 嵌套类估计量、四节点环 placebo 和 `3×3×2` 因子设计成立；但 R472 仍为 active，92 个训练 shard 和 108 个 checkpoint 评估尚未形成聚合结果 | **INCOMPLETE**（设计已证明，结果未产生） | paper-grade proposition（设计） |
| U3 | 有状态 slew projector 的最小 Markov 状态必须含上一执行动作；raw critic 与 executed critic 的等价条件、正确 replay/target 和别名反例均已证明；R460 实现检查通过 | **PROVED + COMPUTATIONALLY VERIFIED** | algebraic identity |
| U4 | 当前 expected common quadratic constraint 不可能推出逐 profile 物理 guard；对命名的 350-schedule 类，四 profile 精确穷举不可行，最佳仍超限 `0.0052693592` | **DISPROVED + COMPUTATIONALLY VERIFIED** | paper-grade proposition |
| U5 | 给出含平衡点、完整 `A/B/C/D`、ZOH、控制器和分母项的闭环总导数；R465 数值验证显示 A-only 归因漏掉 log-M 的 24.24% 和 log-D 的 21.39% | **PROVED + COMPUTATIONALLY VERIFIED** | algebraic identity |
| U6 | 精确 ZOH 分数延迟模型成立；201 个采样点上至 2 s 无单位圆越界，但不是连续区间或鲁棒稳定证书；非线性有限 bank 的 `r_d=0.95` 交叉在连续性条件下位于 `[0,0.025] s` | **COMPUTATIONALLY VERIFIED / INCOMPLETE margin** | paper-grade proposition（有限网格/有限 bank） |
| U7 | `f_u(0)=0` 只排除一阶项，不能单独排除纯 `u^2`；固定模式、零偏置、局部 Lipschitz 下，受控与零控制差在固定有限窗为 `O(ε²)`。R468 支持分段二次领先，但实现的归一化策略不可微 | **COMPUTATIONALLY SUPPORTED** | mechanism prediction |
| U8 | 给出 commutator 上界和 effective-stiffness Schur 上下界；R469 在 32 个局部模型、32768 个非零频点上全部包络成立。异质性本身不足以决定交叉响应；项目未构造物理可信的全状态 projector | **PROVED + COMPUTATIONALLY VERIFIED** | paper-grade proposition（代数核 + 项目数值实例） |
| U9 | R458 实际走 priority 1，唯一 winner `k3_112`；在固定 `eval_b/eval_c` 守卫全清，在 `eval_a/eval_d` 失败。因此只是 2/4 固定 profile 的有限 bank transfer witness，不是 50% 转移概率 | **COMPUTATIONALLY VERIFIED** | paper-grade proposition |

核心判断：U1、U3、U4、U5、U8、U9 已在各自声明范围内闭合；U6 只闭合了采样极点与有限 bank 性能阈值；U7 只支持分段局部机制；U2 尚无科学结果。

---

## 1. 证据边界与审计状态

1. 根仓库 `AGENTS.md` 已读取；默认分支上不存在 `NAVIGATION.md`，因此按 `AGENTS.md` 的 standalone 规则执行。
2. 两个上传分卷已按字节拼接为一个 ZIP。ZIP CRC 无错误；根 `SHA256SUMS` 的 2,973 项全部通过，失败数为 0。
3. 题面文件是：
   `tmp/yang_md_decoupling_marl/gpt_pro_unresolved_math_delta_20260821.md`。
4. 题面快照称 R458 尚未出结果，但包内后续封存证据已包含 R458、R460、R463–R469 和 active R472。按题面声明的证据优先级，后续 formal guards / claim cards / sealed results 覆盖旧快照。
5. 始终分离：
   - **Object A**：四个 GENCLS VSG 的有界局部 `δM_i,δD_i`，是乘性参数调制；
   - **Object B**：加性能量端口 + ring-edge bandpass；
   - 两者的 actuator、reference、window、bank 和 ratio 不可混合。
6. 物理端点均按 60 Hz；控制器语义仍冻结在 50 Hz 模型基准。common restoration、relative synchronization、inter-area differential motion 是不同 estimand。

下文中的“证明”仅指明确写出的数学命题；“计算验证”只覆盖列出的有限矩阵、频点、profile、seed 或 cone data。

---

# U1 — 有界 FIR-Youla 类证书

## U1.1 最强结论

令 Object B 的去 gauge 离散模型为

\[
 x_{k+1}=Ax_k+B_cu_k+B_ww_k,
 \qquad
 y_k=Cx_k+D_cu_k+D_ww_k,
\]

其中 `n=101`，采样周期 `T_s=0.2 s`，窗口 `N=30`。物理负反馈号为

\[
 u=-Ky.
\]

项目注册的命名类为

\[
Q(z)=\sum_{h=1}^{10}Q_hz^{-h},\qquad
Q_h=T_d^\top \widehat Q_hT_d,
\]

其中 `T_d∈R^{3×4}` 是正交差模基，`\widehat Q_h∈R^{3×3}`；故自由变量数为

\[
10\times3\times3=90,
\qquad
\Big(\sum_{h=1}^{10}\|\widehat Q_h\|_F^2\Big)^{1/2}\le1.
\]

该类记为 `QY10`，严格因果，无 locality 主张。

**定理（对封存浮点 cone data 的有限类证书）。** 对 R464 导出的 Object B 30 步 cone program，原 guard 全部满足等价于 phase-I 最优值 `t_*≤0`。封存原始锥数据的可重放 primal/dual 满足

\[
 t_*=0.0599381277797819,
\]

对偶目标

\[
 d=0.05993812777664842,
\]

数值残差总 allowance 为 `3.607393948876687e-10`，且 `d` 为其 `1.661535408×10^8` 倍。因此在声明的数值验证口径下，`t_*>0`，`QY10` 不可行。

这不是全 FIR、全线性、全神经网络或全非线性控制器不可行性。

## U1.2 为什么闭环约束对 Q 是仿射/凸的

对稳定控制通道 `P_c(z)`，R464 对有符号 plant `-P_c` 使用平凡双互素分解

\[
M=\widetilde M=V=\widetilde V=I,
\quad
N=\widetilde N=-P_c,
\quad
U=\widetilde U=0.
\]

在该号约定下，可取

\[
K_Q=Q(I-P_cQ)^{-1}.
\]

若 `y=P_cu+P_ww` 且 `u=-K_Qy`，则

\[
(I+P_cK_Q)^{-1}=I-P_cQ,
\]

从而

\[
 y=(I-P_cQ)P_ww,
 \qquad
 u=-QP_ww.
\]

所以有限窗输出与动作都是 Q 系数的仿射函数。严格因果 FIR 消除了同拍代数环；稳定 plant + stable Q 属于该 Youla 参数化的稳定闭环族。R464 在 30 个系数步上重算 Bezout 残差为 0。

把所有有限窗量写成

\[
 y(q)=y_0+Yq,\qquad u(q)=u_0+Uq,
\]

其中 `q∈R^90`。则：

- differential/cross energy：`||W(y_0+Yq)||_2≤sqrt(E_max)`，是 SOC；
- action RMS：二范数 SOC；
- common IAE、action TV：绝对值 epigraph 后为线性约束；
- peak、RoCoF、逐样本 action tube：无穷范数或成对线性约束；
- coefficient Frobenius ball：SOC；
- **精确 saturation fraction** 是基数函数，一般非凸。R464 没有伪装成凸约束，而是施加更强的逐样本 `|u_norm|≤0.69`，位于 clip `0.70` 内，因而保证零饱和。

phase-I 形式为

\[
\min_{q,t}t,
\qquad
g_j(q)\le t\quad(j=1,\ldots,m),
\qquad \|q\|_2\le1.
\]

原问题可行当且仅当 `t_*≤0`。

## U1.3 封存数值证书

- full state 102；唯一 angle gauge eigenvalue `0.9999999999999925`，输出范数 `5.23e-15`；
- quotient 101；谱半径 `0.9822868797051364`；
- cone：nonnegative 3070；SOC 维数 271、151、361、91；
- Clarabel 0.11.1，CVXPY 1.9.2，equilibration disabled，17 次迭代；
- primal residual `1.5393e-11`；dual stationarity `3.4221e-10`；两侧 cone violation 均为 0；
- primal-dual gap `3.1335e-12`；
- direct convolution 与 lift 最大差 `6.9389e-18`；
- `||q||_F=0.9999999999958379`；
- active original guard：differential energy residual `0.0599381277976363`；cross residual `0.059784513247914894`；common/action guards均为负残差。

## U1.4 文件、字段与缺失量

使用：

- `results/research_loop/r464_u1_qy10_certificate/contracts/class_contract.json`
- `.../checks/gauge_and_stability.json`
- `.../checks/bezout_check.json`
- `.../certificate/cone_data.npz`
- `.../certificate/primal_dual_unscaled.npz`
- `.../certificate/cone_schema.json`
- `.../checks/certificate_check.json`

仍缺：

- exact rational 或 interval-arithmetic 对偶证书；
- 从该局部线性模型转移到饱和 DAE 的 uniform remainder / exhaustive active-mode / IQC 证书；
- 对更长 FIR、不同 norm radius 或不同 disturbance bank 的结论。

## U1.5 机器检查算法与容差

对 canonical form `Ax+s=b, s∈K`：

```text
load A,b,c,x,s,z and cone schema
r_p = ||A x + s - b||_inf
r_d = ||A^T z + c||_inf
check s in K and z in K* block by block
p = c^T x
d = -b^T z
check p-d >= -tol_gap
recompute each original guard directly from q
allowance = registered function of r_p,r_d,cone/gap errors
accept infeasibility only if d - allowance > 0
```

本包实值远离零：`d-allowance≈0.059938127416`。建议重放门限：lift/Bezout `≤1e-10`，primal/dual residual `≤1e-8`，cone violation `≤1e-10`，并以 `d-allowance>0` 而非 solver status 作为结论门。

## U1.6 最小可证伪后续

当前 `QY10` 已闭合。最小升级是把同一对偶向量用 interval 或有理包络重验证；若扩大控制类，必须预先命名新 order/radius 并重新建 cone，不能把 QY10 结果外推。由于没有可行 witness，当前没有合法的“非线性 transfer”分支。

## U1.7 论文措辞

可写：

> For the sealed 30-step Object-B cone program, every ten-tap strictly causal differential Youla controller with coefficient Frobenius norm at most one requires a worst normalized guard relaxation of at least 0.0599381 within the declared numerical verification tolerances.

禁止：

- “all FIR/linear/neural controllers are infeasible”；
- “the nonlinear DAE is impossible to control”；
- “finite-window infeasibility proves instability”；
- “exact symbolic Farkas proof”。

---

# U2 — 邻居信息价值与有限学习成本

## U2.1 可识别量

令 `X` 表示本地信息，`N` 表示真实邻居信息，loss 越小越好。人口层 policy classes 满足

\[
\Pi_X\subseteq\Pi_{X,N}.
\]

对声明的 profile/scenario 分布 `\mathcal D`，定义

\[
J_X^*=\inf_{\pi\in\Pi_X}\mathbb E_{\theta\sim\mathcal D}J(\pi;\theta),
\quad
J_{XN}^*=\inf_{\pi\in\Pi_{XN}}\mathbb E J(\pi;\theta),
\]

以及固有信息价值

\[
I^*=J_X^*-J_{XN}^*\ge0.
\]

对固定算法、预算 `B`、训练随机性 `S`，令训练输出为 `\hat\pi_{c,B,S}`，定义

\[
J_{c,B}=\mathbb E_{S,\theta}J(\hat\pi_{c,B,S};\theta),
\qquad
L_{c,B}=J_{c,B}-J_c^*\ge0.
\]

则恒等式

\[
\boxed{
J_{X,B}-J_{XN,B}
=I^*+L_{X,B}-L_{XN,B}.}
\]

因此有限预算差不能单独识别 `I*`：真实信息即使有正固有价值，也可能因更难优化而表现更差；反之，正则化或优化偶然性也可产生有限预算优势。

## U2.2 四节点环 placebo 的构造与证明

令 agent `i∈Z_4`，两套独立 donor episode `e∈{0,1}`。真实有序邻居槽为

\[
N(i,e)=((i-1,e),(i+1,e)).
\]

注册 placebo 使用 `\pi(e)=1-e`：

\[
P(i,e)=((i,\pi(e)),(i+2,\pi(e))).
\]

### 语义配对全部改变

在四环中，`i` 的真实邻居是 `i±1`；`i` 和 `i+2` 分别是自身与对径节点，均不是语义邻居。episode 也被翻转。因此每个 recipient、每个 episode、两个槽位的 donor identity 都不等于真实邻居 pairing。

### 声明的 pooled marginals 保持

对每个槽位，映射

\[
\phi_1(i,e)=(i,1-e),
\qquad
\phi_2(i,e)=(i+2,1-e)
\]

都是有限集合 `Z_4×Z_2` 上的双射。故在 recipient/episode 全池化后，每个槽位的 node–episode 多重集合完全相同；在 donor tensor 以相同 scenario、feature、time 索引抽取时，每个 slot/feature/time 的经验边际 hash 也保持。

不保持的量包括 recipient-conditional 分布、真实邻接关系、两个槽的联合相关、跨时序相关和因果独立性。因此它是“匹配 pooled marginals、破坏 semantic pairing”的 placebo，不是 iid noise。

## U2.3 因子设计

冻结 18 个 cell：

\[
\text{actor source}\in\{0,P,N\},
\quad
\text{critic source}\in\{0,P,N\},
\quad
\text{reward}\in\{0,1\}.
\]

- `0`：消息槽置零；
- `P`：上述独立、scenario-matched placebo donor；
- `N`：同拍真实环邻居；
- reward 作为独立因子，不与 actor/critic access 同时改动。

主要配对 contrasts：

- `N-P`：在同维度、同 pooled marginals 下的语义 pairing 效应；
- `P-0`：无关输入通道带来的估计/优化负担；
- actor、critic、reward 的主效应与交互必须在另一因子固定时计算。

它们识别的是“该算法族、预算、donor 机制和冻结环境下的 source effect”，除非另行控制 `L_{c,B}`，否则不等于 `I*`。

## U2.4 不确定性与失败分支

训练 seed 是顶层独立单位；同一 seed 下的 profile/scenario trajectories 是嵌套重复测量。正确流程是：先在每个 seed 内形成成对 cell difference，再以 seed 为单位 bootstrap 或 t/随机化推断。多个 primary contrasts 用 Holm `α=0.05`；不得把 trajectory 数当成独立训练样本数。

支持有限预算真实语义价值需同时满足：

1. 固定 reward 和另一角色 source，held-out 上 `N-P` 为有利方向；
2. 置信区间下界越过预注册 `log(1.10)` materiality；
3. Holm 后仍显著；
4. half/final 不翻向，后期曲线稳定；
5. 所有 seed、执行动作语义、donor/reward/hash gates 通过。

反驳“该预算下有实质 source effect”：所有 gate 通过且 CI 排除 materiality。若 seed 缺失、half/final 翻向或无稳定，则只能是 `OPTIMIZATION-UNRESOLVED`；donor、初始化、reward 或 executed-action gate 失败则为 `FACTORIAL-INVALID`。

## U2.5 当前证据状态

R470 因把正常终止误判为 TDS failure 而工程中止。R471 形成 6 个 donor/base bundle 和 16 个完整、哈希一致的 43,200-step shards，但外部 session ceiling 中断 launcher，没有科学聚合。

R472 当前仍为 `state: active`：

- 复用且只复用 16 个完整 R471 shards；
- 明确排除全部 half-only shards；
- 尚需 92 个训练 shards；
- 完成后评估全部 108 个 half/final checkpoints；
- 18 cells × seeds 401–406；每个 43,200 physical steps；24 dev + 24 held-out scenarios。

所以包内不存在 `U2-SOURCE-EFFECT-SUPPORTED` 或 `NOT-SUPPORTED` 的合法结果。

## U2.6 文件、字段与缺失量

使用：

- `memory/rounds/R472/plan.md`
- `memory/rounds/R460/plan.md`
- `paper/yang_md_decoupling_marl/reports/R460.md`
- `results/research_loop/r460_u3_execution_semantics/checks/verification_report.json`

缺失：R472 的 92 个新训练 shard、108 checkpoint evaluations、aggregate、Holm/CI、optimization gates 和最终 verdict。没有这些量，任何 message-value 数值都不可报告。

## U2.7 机器检查算法

```text
for each seed:
    verify donor/base hashes and P marginal hashes
    verify all 18 cells use identical environment, optimizer, budget, reward factor
    verify U3 executed-action replay/critic semantics
    aggregate 24 dev and 24 held-out scenarios within seed
    compute paired log-loss contrasts N-P, P-0 for fixed other factors
check half/final sign and late-curve stabilization
bootstrap paired seed vectors; seed is resampling unit
apply Holm(alpha=.05) to preregistered primary contrasts
apply 10% materiality gate
emit exactly one of SUPPORTED / NOT-SUPPORTED / OPTIMIZATION-UNRESOLVED / FACTORIAL-INVALID
```

## U2.8 最小新实验与措辞

在既有冻结合同下，最小合法实验就是完成 R472；分析任何 partial endpoint 都会破坏 immutable reuse 与预注册 aggregate。完成后：

- 支持 observable：held-out `N-P` 下界 > `log(1.10)` 且优化 gates 通过；
- 反驳 observable：CI 排除该 materiality；
- 未收敛时不能把 null 解释为无信息价值。

可写：

> The factorial separates authentic neighbour pairing from a marginal-matched placebo and from zeroed channels at a fixed reward. Its estimand is a finite-budget, algorithm-specific source effect; intrinsic population information value additionally requires control of optimization gaps.

禁止：

- “neighbour messages are intrinsically valuable/useless”；
- “R472 已支持/反驳消息价值”；
- “trajectory-level n 代替 training-seed n”；
- “有限预算差等于 policy-class optimum 差”；
- “推广到新拓扑或任意 MARL”。

---

# U3 — 有状态 slew projector 的 Bellman 语义

## U3.1 增广 MDP

令 `x_t` 为物理/观测充分状态，raw action 为 `u_t`，上一 executed action 为 `v_{t-1}`，投影器为

\[
v_t=P(v_{t-1},u_t).
\]

最小状态至少为

\[
z_t=(x_t,v_{t-1}).
\]

若 headroom、SOC、hysteresis、cache 或 limiter mode 也有记忆，必须继续加入。若物理转移为 `p_x(dx'|x,v)`，则

\[
\boxed{
\widetilde p(dx',dv'\mid x,v^-,u)
=p_x(dx'\mid x,P(v^-,u))
\,\delta_{P(v^-,u)}(dv').}
\]

下一状态是 `z_{t+1}=(x_{t+1},v_t)`。

## U3.2 critic 表示的等价条件

若 reward 和 transition 对 raw command 的依赖仅通过 `v=P(z,u)`，且没有额外 raw-command penalty，则

\[
Q^u(z,u)=Q^v(z,P(z,u)).
\]

因此：

- raw critic `Q^u(z,u)` **可以合法**，但 `z` 必须含 projector state，且环境/target 明确执行 P；
- executed critic `Q^v(z,v)` 也合法，actor 和 target 必须先投影；
- 若 reward 同时惩罚 raw command、通信包或 projection gap，需用 `Q(z,u,v)` 或把相应量并入 state/reward，简单等价失效。

many-to-one P 下，合法 raw critic 应在每个 preimage fiber `P_z^{-1}(v)` 上取相同环境价值；有限函数逼近不一定自动学到该不变性。

## U3.3 replay 与 target

推荐 replay tuple：

\[
(x_t,v_{t-1},u_t,v_t,r_t,x_{t+1},d_t).
\]

对 TD3：

\[
u' = \bar\pi(z')+\epsilon,
\quad
v'=P(v_t,u'),
\]

\[
y=r+\gamma(1-d)\min_j\bar Q_j(z',v').
\]

对保留 raw-policy entropy 的 SAC：

\[
y=r+\gamma(1-d)
\left[
\min_j\bar Q_j(z',v')-\alpha\log\pi(u'\mid z')
\right],
\quad v'=P(v_t,u').
\]

这里的 entropy 只能称 `raw_policy_entropy_regularizer`。

## U3.4 别名与偏差

若删除 `v_{t-1}`，相同 `(x_t,u_t)` 可生成不同执行动作。以 scalar slew limit `δ=0.25`、`u_t=0` 为例：

\[
P(1,0)=0.75,
\qquad
P(-1,0)=-0.75.
\]

故不存在由 `(x,u)` 唯一决定的 transition；在 off-policy replay 中，隐藏 actuator-state 的条件分布还会随 behavior policy 改变，普通 Bellman operator 不再固定。

若另外假设 reward 对 action 为 `L_r`-Lipschitz，transition 在 Wasserstein-1 下为 `L_p`-Lipschitz，value 为 `L_V`-Lipschitz，则把 executed action 错当 raw action的一步 Bellman误差有界为

\[
\left|T_{raw}V-T_{exec}V\right|
\le
(L_r+\gamma L_pL_V)
\|u-P(v^-,u)\|.
\]

若右端一致上界为 `ε_B`，两个收缩 fixed point 的 sup-norm 差不超过

\[
\frac{\epsilon_B}{1-\gamma}.
\]

包内没有历史 R431 replay，也没有 `L_r,L_p,L_V`，所以不能给历史 bias 数值。

## U3.5 entropy 的变化

clamp/slew 是 many-to-one 映射；push-forward `\pi_v=P_\#\pi_u` 通常包含内部连续密度和边界原子。一般不存在一个普通可逆 Jacobian 公式使 `H(π_u)=H(π_v)`。raw policy 可在同一物理动作的 preimage 内扩散，增加 raw entropy 而不增加物理探索。

若要 executed-action entropy，应直接参数化可行区间

\[
[l(z),h(z)]
=
[\max(-1,v^- -\delta),\min(1,v^-+\delta)]
\]

并对该近一一映射计算密度；否则必须保留 raw entropy 标签。

## U3.6 R460 验证

- 24 trajectories × 30 steps = 720 transitions；全部完成，无 TDS failure；
- NumPy/Torch projector 最大误差 `5.960464477539063e-08≤1e-7`；
- runtime reconstruction、replay continuity、critic action identity、physical M/D mapping 最大误差均为 0；
- toy hand-return 与 recursive TD target 差 0（门限 `1e-6`）；
- 删除 previous action 的 toy next-state gap 为正；项目摘要值约 `0.43750003`；
- 新 bank 上 R431 checkpoint 的 raw/projected gap只是 retrospective diagnostic，不是历史 replay bias。

## U3.7 文件、算法与后续

文件：

- `paper/yang_md_decoupling_marl/reports/R460.md`
- `results/research_loop/r460_u3_execution_semantics/checks/verification_report.json`
- 同目录 semantic tests、raw traces 和 replay inventory。

最小验证合同：

```text
1. projector parity on boundary/raw grids: max error <= 1e-7
2. replay next_prev_action == executed_action exactly
3. fixed exogenous seed: identical (z,u) -> identical (v,r,z')
4. delete v_prev and verify two-valued transition exists
5. replay full raw sequence and reconstruct executed sequence: <=1e-7
6. 3–5 step toy exhaustive return vs TD recursion: <=1e-6
7. actor and target Q inputs must be projected actions
```

最小后续是今后训练时强制保存 replay；历史 R431 无法补算。

可写：

> A stateful slew limiter makes the previous executed command part of the Markov state. A raw-command critic is valid only on this augmented state with the projection included in the transition kernel; an executed-command critic is equivalent after deterministic push-forward.

禁止：“raw-action critic 永远无效”“R431 bias 等于某个新 bank 数字”“raw entropy 等于 executed entropy”。

---

# U4 — 训练约束集与 trajectory guard 集

## U4.1 两个集合

当前 common quadratic cost 为

\[
c_c(k)=\frac14\sum_{i=1}^4
\left(\frac{f_i(k)-60\,\mathrm{Hz}}{0.15\,\mathrm{Hz}}\right)^2
+
\frac14\sum_{i=1}^4
\left(\frac{\dot f_i(k)}{1\,\mathrm{Hz/s}}\right)^2.
\]

注册 budget 为 3，`γ=0.99`。必须分别写清未折扣 episode 版本

\[
\mathcal F_{train}^{undisc}
=
\left\{\pi:\mathbb E\sum_{k=0}^{N-1}c_c^\pi(k)\le3\right\}
\]

和折扣版本

\[
\mathcal F_{train}^{disc}
=
\left\{\pi:\mathbb E\sum_{k=0}^{N-1}\gamma^kc_c^\pi(k)\le3\right\};
\]

两者不能混用。

固定 bank 的 guard 集是对每个 profile/seed 的交集：

\[
\begin{aligned}
&E_d^\pi\le0.95E_{d,0},\qquad
E_\times^\pi\le0.95E_{\times,0},\\
&IAE_c^\pi\le1.03IAE_{c,0},\quad
Peak^\pi\le1.03Peak_0,\quad
RoCoF^\pi\le1.03RoCoF_0,\\
&RMS_u^\pi\le1.10RMS_{u,0},\quad
TV_u^\pi\le1.10TV_{u,0},\\
&SatFrac^\pi\le0.05,\qquad valid/completed.
\end{aligned}
\]

单位分别是 `Hz²·s`（或注册能量单位）、`Hz·s`、`Hz`、`Hz/s`、normalized action RMS、normalized-action variation 和无量纲比例。

## U4.2 不包含性的证明

### 反例 A：期望不推出逐 profile

取坏 profile 概率 `ε`。令策略在普通 profile 上 cost 0，在坏 profile 上 cost `3/ε`，则期望 budget 恰为 3，但坏 profile 的 peak/IAE 可任意大。因此 mixture expectation 不能推出 profile-wise maximum，除非增加 almost-sure/robust 条件。

### 反例 B：common cost 不控制差模与动作

写

\[
f_i-60=\bar e+d_i,
\qquad \sum_i d_i=0.
\]

固定 `\bar e` 即固定 common cost 的主要频率部分，但 `d_i` 可改变 differential endpoint。另可令动作在无效、被剪裁或 common-null 通道中高频振荡，使物理 common trajectory 不变而 TV/saturation 任意增大。因此不存在仅由当前 `c_c` 和某个 budget 推出的完整七项 guard inclusion。

故

\[
\boxed{\mathcal F_{train}\nsubseteq\mathcal F_{guard}.}
\]

## U4.3 common 三项的保守充分界

若**每条单独 record**满足未折扣

\[
\sum_{k=0}^{N-1}c_c(k)\le B,
\]

则

\[
|f_i(k)-60|\le2(0.15)\sqrt B,
\qquad
|\dot f_i(k)|\le2(1)\sqrt B.
\]

令 `\bar e_k=(1/4)\sum_i(f_i-60)`，由 Jensen/Cauchy：

\[
T_s\sum_{k=0}^{N-1}|\bar e_k|
\le T_s(0.15)\sqrt{NB}.
\]

若 profile summary 汇总 `R` 条 records，则要用 `R` 倍 IAE 上界。用 `R=6,N=30,T_s=0.2` 与四个 eval reference，三项共同最紧充分 budget 是

\[
B\le 0.0009421116622729003,
\]

而当前 budget 为 3，相差约 3184 倍。该界极保守，只保证 common IAE/peak/RoCoF；即使满足，也不保证 endpoint、RMS、TV、saturation 或 validity。若约束是 discounted，必须用 `γ^{-k}` 加权重新推导，不能沿用此未折扣界。

## U4.4 对齐的 phase-I

定义 dimensionless exact residual `g_{j,p,s}(π)`，负值通过、正值违规：

\[
\min_{\pi\in\Pi,t}t,
\qquad
 g_{j,p,s}(\pi)\le t
 \quad\forall j,p,s.
\]

- `t≤0`：finite-bank guard-clean witness；
- 有限类：穷举可证明类内可行/不可行；
- 凸类：正对偶下界可证明不可行；
- neural class：局部 optimizer 的 `t>0` 不能区分类不可行与优化失败。

非光滑项：peak/max、IAE/TV absolute value；saturation fraction 是不连续基数；valid/TDS 是离散 indicator；headroom/clamp 在 mode boundary 不可微。训练可用平滑 surrogate，但最终 gate 必须重算原始 guard。

R456 的 RMS value/constraint gradient conflict 在 6 个 checkpoint 中支持 4 个，只说明该冻结切片存在局部方向冲突，不是 KKT、全局不可行或普遍机制。

## U4.5 R463 精确有限类结论

对同一 350 schedules × 4 profiles × 8 scalar residuals，共 11,200 次 guard 评估：

- 125 candidates 含 invalid/nonfinite row，严格保留为 `+∞`；
- 225 candidates 全有限；
- 无 candidate 在四 profile 上全 guard-clean；
- winner `k3_112`，global index 137，schedule `[(3,3),(1.5,1.5),(1.5,1.5)]`；
- `t=0.005269359206972579`；
- active guard：`eval_a` boundary-aware action TV，超允许限度 0.526936%；
- 次要正 residual：`eval_d` differential endpoint `0.001551280089695739`；
- runner-up `k3_111`，`t=0.01738548340202506`，差 `0.01211612419505248`。

这只证明命名 350-schedule 类在四固定 profile 上不可行。

## U4.6 文件、算法、后续与措辞

文件：

- `results/research_loop/r463_u4_guard_audit/phase_i/candidate_residuals.jsonl`
- `.../exact_enumeration_result.json`
- `.../independent_reconstruction.json`
- `.../constraints/r431_training_constraint_export.json`
- `.../constraints/r456_intervention_export.json`

算法：独立重算 physical metrics；reference denominator 必须有限且 `>1e-12`；invalid row 置 `+∞` 而非删除；逐 candidate 取 32 residual 最大值；按 `(t,global_index)` 排序；再从 raw JSONL 独立重建。

最小后续：若研究 neural policy，直接以 exact max-residual phase-I 搜索并保留多启动/下界；没有全局证书时只能报告“找到/未找到 witness”，不能报告类不可行。

可写：

> The episodic common-mode quadratic constraint is not an inner approximation of the registered profile-wise guard set. Exact enumeration further shows that no member of the sealed 350-schedule class satisfies all guards over the four fixed profiles.

禁止：“budget 3 保证 no harm”“dual saturation 证明不可行”“350 个 schedule 代表所有 policy”“4/6 gradient conflicts 是普遍规律”。

---

# U5 — 完整闭环 M/D 灵敏度

## U5.1 精确总导数

对 `z=e^{jωT_s}`，离散模型维数为

- `A∈R^{101×101}`；
- `B_c∈R^{101×4}`，控制输入；
- `B_w∈R^{101×3}`，负荷扰动；
- `C∈R^{4×101}`，四个 60-Hz frequency outputs；
- `D_c∈R^{4×4}`, `D_w∈R^{4×3}`。

定义

\[
R=(zI-A)^{-1},
\quad
P_c=CRB_c+D_c,
\quad
P_w=CRB_w+D_w.
\]

控制器 `K(z,ρ)` 在负反馈 `u=-Ky` 下给出

\[
L=P_cK,
\quad
S=(I+L)^{-1},
\quad
G=SP_w.
\]

对 `ρ∈{\log M,\log D}`：

\[
R_ρ=RA_ρR,
\]

\[
(P_c)_ρ=C_ρRB_c+CRA_ρRB_c+CR(B_c)_ρ+(D_c)_ρ,
\]

`P_w` 同理，且

\[
L_ρ=(P_c)_ρK+P_cK_ρ,
\]

\[
\boxed{G_ρ=S\big[(P_w)_ρ-L_ρG\big].}
\]

该式自动包含 reference/candidate 分母、headroom 和 controller realization，只要它们的 `ρ` 依赖进入 `B,C,D,K`。

对有限频带二次能量

\[
E(ρ)=\sum_\ell w_\ell
\operatorname{tr}
\left(G_\ell^*W_oG_\ell W_i\right),
\]

有

\[
E_ρ=2\operatorname{Re}\sum_\ell w_\ell
\operatorname{tr}
\left(G_\ell^*W_o(G_\ell)_ρW_i\right),
\]

若 weights 依赖 `ρ` 再加对应导数。candidate/reference ratio 满足

\[
\boxed{
\frac{d}{dρ}\log\frac{E_K}{E_R}
=\frac{(E_K)_ρ}{E_K}-\frac{(E_R)_ρ}{E_R}.}
\]

30-step Toeplitz lift用同一 Frobenius/trace公式，不能与 frequency-band energy 混为同一量。

## U5.2 平衡点、DAE 和 ZOH

若 equilibrium 由 `F(ξ,ρ)=0` 决定，固定 gauge 后

\[
ξ_ρ=-F_ξ^{-1}F_ρ.
\]

对 index-1 DAE

\[
\dot x=f(x,y,u,ρ),\qquad0=g(x,y,u,ρ),
\]

若 `g_y` 可逆，

\[
A_r=f_x-f_yg_y^{-1}g_x,
\quad
B_r=f_u-f_yg_y^{-1}g_u.
\]

求导必须包含 `ξ_ρ` 和

\[
(g_y^{-1})_ρ=-g_y^{-1}(g_y)_ρg_y^{-1}.
\]

ZOH 采用增广矩阵指数

\[
\exp\left(
T_s\begin{bmatrix}A_c&B_c\\0&0\end{bmatrix}
\right)
=
\begin{bmatrix}A_d&B_d\\0&I\end{bmatrix},
\]

导数用 matrix-exponential Fréchet derivative；不能使用要求 `A_c` 可逆的 `A_c^{-1}(A_d-I)B_c` 作为通用公式。

数值实现应解线性方程 `(zI-A)X=B` 和 `(I+P_cK)Y=P_w`，避免显式求逆；每个频点记录 `cond(zI-A)`、`cond(I+P_cK)`。

## U5.3 归因是否不变量

在 `ρ`-dependent similarity `x'=T(ρ)x` 下，`A_ρ,B_ρ,C_ρ` 各项会增加 `T_ρ` 产生的交换子项；所以把总导数拆成“A channel、B channel、C channel”不是坐标不变量。物理端口 transfer `G(ρ)` 及其总导数是 invariant；若要机制归因，应定义可复现实物 counterfactual blocks，而不是把某个矩阵导数称为唯一原因。

## U5.4 R465 数值结果

固定模式的 13 个点：`ρ=0,±0.04,±0.02,±0.01`，M 与 D 两族共用 nominal。

- nominal band energy ratio `E_bandpass/E_PI=0.8740574911094813`；
- 完整 log-ratio derivative：
  - log-M：`0.4464230763636614`；
  - log-D：`0.052224462496277685`；
- R449 A-only：`0.33821534585850266`、`0.04105111192922409`；
- omitted residual：`0.10820773050515875`（24.2388%）和 `0.011173350567053597`（21.3949%）；
- 30-step ratio `0.9957864563449452`；其 log derivatives 为 `0.01624364445922999`、`0.003366236754435481`；
- max `cond(zI-A)=2.0214698e6`；bandpass `cond(I+L)≈1.365`；local PI 最大约 `1.23901e5`；均低于注册 `1e12`；
- generic random-MIMO derivative 独立检查相对误差 `6.8768e-10`。

所有点 active-mode/name hash 相同；equilibrium residual `<7.24e-9`。

## U5.5 误差界、缺失量与算法

三层 centered differences 可用：

\[
D_h=\frac{F(ρ+h)-F(ρ-h)}{2h},
\quad
R_h=\frac{4D_{h/2}-D_h}{3}.
\]

在五阶光滑下，`R_h` 为四阶；用两级 Richardson 时，较细结果的 a posteriori truncation estimate 约为 `|R_{h/2}-R_h|/15`。前提是 active mode、gauge 和 coordinate names 不变。

缺失：从 reduced local model 到原 nonlinear DAE 的 uniform derivative/remainder interval；大扰动 mode switch；鲁棒 uncertainty set；MIMO Nyquist crossing 或 certified return-difference margin。因此 supplied energy sensitivity 不能推出 gain margin、phase margin、robust margin或唯一 failure cause。

机器流程：重建每个 `ρ` 的 equilibrium→DAE Schur reduction→ZOH→controller/headroom→closed loop；检查 mode hash；对所有数组做 Richardson；用 Fréchet 公式与直接 rebuild 双重校验；能量分子分母分别求导；记录 conditioning；若任一 mode/hash/condition gate 失败，只报告 one-sided/piecewise derivative。

## U5.6 论文措辞

可写：

> At the sealed fixed-mode Object-B equilibrium, the complete band-energy log-ratio derivatives are 0.446423 for common log-M and 0.0522245 for common log-D. Direct rebuilds validate these derivatives, while A-only attribution omits 24.24% and 21.39% of the respective totals.

禁止：“A 是唯一原因”“矩阵分量归因具有坐标不变性”“能量导数就是 gain/phase margin”“该局部导数解释全局 nonlinear failure”。

---

# U6 — 分数延迟与局部稳定/鲁棒边界

## U6.1 精确 ZOH 分数延迟

令

\[
τ=mT_s+δ,
\quad m\in\mathbb N,
\quad0\leδ<T_s,
\quad T_s=0.2\,s.
\]

在 interval `[kT_s,(k+1)T_s)` 内，前 `δ` 秒仍执行旧命令 `u_{k-m-1}`，其余执行 `u_{k-m}`。因此

\[
\boxed{
x_{k+1}=A_dx_k+B_1(δ)u_{k-m-1}+B_0(δ)u_{k-m}}
\]

其中

\[
B_1(δ)=\int_0^δe^{A(T_s-s)}B\,ds,
\quad
B_0(δ)=\int_δ^{T_s}e^{A(T_s-s)}B\,ds.
\]

`B_1(0)=0,B_0(0)=B_d`；`δ→T_s` 时无缝转到下一整数延迟。用 block exponential 计算，不引入 Padé/Thiran 近似。

R467 将 101-state plant、8-state controller 和 40-state command memory 组成固定 149-state `A_cl(τ)`。

## U6.2 极点跟踪

对简单 eigenvalue `λ(τ)`，左右 eigenvectors `w,v` 满足 `w^*v=1`：

\[
λ'=w^*A_{cl}'v,
\qquad
\frac{d}{dτ}\log|λ|
=\operatorname{Re}\frac{λ'}{λ}.
\]

数值上应使用 ordered Schur subspaces/cluster matching；重复或 defective 分支不能靠单个 eigenvector identity。每个候选 crossing 应输出：bracket、单位圆残差、eigen residual、`1/|w^*v|` 和局部 pseudospectral/condition 信息。

## U6.3 R467 能证明什么

201 个点 `τ=0,0.01,…,2.00 s`：

- 每一点 149 个 poles 均严格在单位圆内；
- `τ=0` 最大模 `0.9822551826663134`；
- 全网格最大模 `0.9874374896272871`，位于 `τ=2 s`；
- 最大 normalized eigen residual `1.0435e-14`；
- endpoint augmented-matrix seam mismatch `1.08e-11≤1e-8`。

所以合法结论是：

\[
\rho(A_{cl}(τ_j))<1
\quad\text{for all 201 sampled }τ_j.
\]

不合法结论是“连续区间 `[0,2]` 稳定”或“delay margin >2 s”，因为 0.01-s 网格未排除相邻点间 leave-and-return；重复簇的 branch overlap 也非常病态。连续证书需要 interval enclosure、Lipschitz/pseudospectral bound 或 adaptive Schur-subspace crossing search。

## U6.4 非线性有限 bank 阈值

实际 transport 的 differential-energy ratios：

\[
\begin{array}{c|ccccc}
τ(s)&0&0.025&0.05&0.1&0.2\\\hline
r_d&0.9389467911&0.9540298868&0.9517400663&0.9622288075&0.9502787849
\end{array}
\]

若 `r_d(τ)` 在 `[0,0.025]` 连续，则中值定理给出至少一个 `r_d=0.95` 交叉；没有单调性，所以只能说“存在于该区间”，不能说唯一或线性下降。下一最小点 `τ=0.0125 s` 可把一个 continuity-qualified bracket 宽度减半；若要识别“第一交叉”，还需更密 adaptive grid 或单调性证据。

该性能阈值不是稳定边界。局部 pole grid 至 2 s 与几十毫秒性能退化可以同时成立。

## U6.5 鲁棒性与 5.38% seam

robust stability 需要完整频率 uncertainty set，例如 `Δ` 的 norm bound、IQC 或 structured `μ` 模型，并验证 small-gain/μ 条件。记录的 5.38% 是一个零延迟标量 endpoint discrepancy，不是 `||Δ(jω)||_∞`，不能合法传播成 pole、phase 或 robust delay margin。

MIMO nominal phase margin也需要明确的 return ratio/Nyquist eigenlocus或 disk margin定义；当前数据只提供特定 digital controller 的 exact-delay closed-loop poles和有限 bank endpoint。

## U6.6 文件、算法与措辞

文件：

- `results/research_loop/r467_u6_fractional_delay/linear/all_pole_scan.npz`
- `.../linear/pole_tracking_report.json`
- `.../nonlinear/fractional_bisection.json`
- `paper/yang_md_decoupling_marl/reports/R467.md`

机器算法：用 block exponential 生成 B0/B1；构建固定维数 augmented matrix；全谱 Schur/eig；检查 `||Av-λv||/(||A||||v||)≤1e-9`；cluster matching；发现符号变化后 bisection；若 eigenvalue multiple，切换 invariant subspace 和 pseudospectrum。非线性阈值只用完整 trajectories、固定 reference 和 raw elapsed-time transport。

可写：

> On the registered 201-point nominal Object-B scan, all poles remain inside the unit circle through 2 s. Separately, the finite nonlinear bank places at least one continuity-qualified `r_d=0.95` crossing between 0 and 25 ms.

禁止：“robust delay margin 2 s”“连续区间稳定已证明”“25 ms 是稳定极限”“5.38% scalar seam 是 H∞ uncertainty norm”。

---

# U7 — 零一阶后的二阶/双线性 M/D authority

## U7.1 必须修正的逻辑点

R446 证明在同步平衡点

\[
\bar f_q(0,0,0)=f_q-f_yg_y^{-1}g_q=0
\]

（8 个 M/D physical parameter directions）。这只排除 additive first-order term；**不能推出纯二次项为零**。反例是 `\dot x=q^2`：一阶导数为 0，但首项是纯 `q^2`。

因此一般 Taylor 展开必须写成

\[
\begin{aligned}
\bar f(x,q,w)=&Ax+B_ww
+\sum_{j=1}^8q_j(N_jx+E_jw)\\
&+\frac12F_{qq}[q,q]
+\text{pure }x,w\text{ quadratic terms}
+O(3),
\end{aligned}
\]

输出同理：

\[
\bar h=Cx+D_ww+
\sum_jq_j(R_jx+S_jw)
+\frac12H_{qq}[q,q]+O(3).
\]

只有在固定 smooth mode 下验证

\[
\bar f(0,q,0)=0,
\qquad
\bar h(0,q,0)=0
\]

对所有邻近 q 恒成立，才能推出所有 pure-q derivatives 消失，使 mixed bilinear term 成为首项。对惯量/阻尼在同步零频差平衡上的物理解释，这个条件合理，但必须作为 family invariance 假设或单独机械验证，不能由 `f_q=0` 代替。

## U7.2 `O(ε²)` 的充分条件

考虑 disturbance amplitude `ε`，零控制 baseline 满足在固定有限 horizon

\[
\|x^0\|,\|w\|=O(ε).
\]

若 zero-bias feedback `q=κ(o)` 满足 `κ(0)=0` 且局部 Lipschitz，则 `q=O(ε)`。于是 mixed terms `qx,qw` 和 pure `q^2` 都是 `O(ε²)`。在 `A` 的有限步传播有界、remainder uniformly quadratic 且 active mode 不变时，离散 Grönwall 给出

\[
\max_{k\le N}\|x_k^q-x_k^0\|
+
\|y^q-y^0\|_{2,[0,N]}
\le C_Nε^2.
\]

该结论是“quadratic-leading”，不自动是“bilinear-only”。若 projector/decoder 在零点不连续、active mode 以 `O(ε)` 距离跨阈值，或 zero bias 失败，则可出现 `O(ε)` 甚至跳变项。

## U7.3 index-1 DAE mixed tensors

对

\[
\dot x=f(x,y,q,r),\qquad0=g(x,y,q,r),
\]

固定 mode 且 `g_y` 可逆时，先做 Schur reduction，再对 physical q 求导。R468 直接导出 sampled mixed tensors：

\[
N=\frac{\partial A_d}{\partial q}
\in\mathbb R^{8\times101\times101},
\]

\[
E=\frac{\partial B_d}{\partial q}
\in\mathbb R^{8\times101\times7},
\]

\[
R=\frac{\partial C_d}{\partial q}
\in\mathbb R^{8\times4\times101},
\quad
S=\frac{\partial D_d}{\partial q}
\in\mathbb R^{8\times4\times7}.
\]

七个 additive inputs 是四个 energy-port commands + 三个 load disturbances。离散 mixed model为

\[
x_{k+1}=Ax_k+Br_k+
\sum_jq_{j,k}(N_jx_k+E_jr_k)+\cdots,
\]

\[
y_k=Cx_k+Dr_k+
\sum_jq_{j,k}(R_jx_k+S_jr_k)+\cdots.
\]

## U7.4 有限窗 bound 与 additive 比较

令 `ζ` 堆叠 30 步所有独立 pseudo-input products `(q_jx,q_jr)`。R468 的 open bilinear lift

\[
H_b\in\mathbb R^{120\times25920},
\quad y_b=H_bζ.
\]

故

\[
\|y_b\|_2\le\sigma_{max}(H_b)\|ζ\|_2.
\]

从封存 `bilinear_lift.npz` 独立重算

\[
\sigma_{max}(H_b)=0.2577502705571717.
\]

差模 additive lift

\[
H_p\in\mathbb R^{90\times90},
\]

full rank，

\[
\sigma_{min}(H_p)=0.011765446147099425,
\quad
\sigma_{max}(H_p)=0.23408038942298523.
\]

把 bilinear 输出逐时刻投影到同一三维差模 basis，得到

\[
H_{b,d}=(I_{30}\otimes T_d)H_b
\in\mathbb R^{90\times25920},
\qquad
\sigma_{max}(H_{b,d})=0.25774851541137045.
\]

若 additive direction 未被输出湮灭，则

\[
\frac{\|y_{MD}\|}{\|y_{EP}\|}
\le
\frac{\sigma_{max}(H_{b,d})}{\sigma_{min}(H_p)}
\frac{\|ζ\|}{\|p\|}
=21.90724535124527\frac{\|ζ\|}{\|p\|}.
\]

但 `ζ` 是 product pseudo-input，不是与 additive `p` 同单位的 raw command。要变成物理 M/D-vs-energy-port 数字，还缺同一 action normalization、policy feedback derivative、state/disturbance amplitude bound 和 remainder radius。因此只能证明局部阶次劣势：若 `\|p\|=Θ(ε)` 而 `\|ζ\|=O(ε²)`，ratio 为 `O(ε)`；不能据此声称全局不可行。

更一般的有限窗 bound 应保留 pure `q²`：

\[
\|\Delta y\|
\le
C_{xq}\|q\|\|(x,w)\|
+C_{qq}\|q\|^2
+C_3\|(x,w,q)\|^3.
\]

## U7.5 R468 结果与不可微接口

- Object A equilibrium：`M=400,D=100`，101 quotient states，`T_s=0.2 s`；
- 49 linearizations，M base step 4，D base step 1，连续减半两次；
- h/2 vs h/4 tensor 最大相对差 `1.88e-5`；
- exact-ZOH Fréchet/direct：A `2.85e-7`，B `3.33e-7`；
- max equilibrium residual `7.233433011496495e-9`：通过项目 `1e-8`，未通过外部建议 `1e-9`；
- R444 12/12 blocks：`||Δy_MD||/ε` 向下，最后两级 `||Δy_MD||/ε²` 相差 2.59%–8.40%，低于 20% gate；
- additive first-order lift 非零；
- 实现 controller 零 bias，但左右 observation derivatives 最大相差 8，decoder 两侧 slope 为 200 和 600。

因此 smooth normalized-policy Taylor theorem **不适用**；合法的是 physical-parameter tensors + 分段 finite-ladder quadratic-leading evidence。

## U7.6 文件、算法、后续与措辞

文件：

- `results/research_loop/r468_u7_local_taylor/tensors/mixed_tensors.npz`
- `.../lifts/bilinear_lift.npz`
- `.../lifts/additive_lift.npz`
- `.../checks/verification_report.json`
- `.../checks/policy_and_decoder.json`
- `.../scaling/amplitude_scaling.json`

FD 算法：固定 physical parameter units 和 mode hash；三层 central differences；要求 h/2/h/4 relative `≤1%` 或 absolute near-zero；DAE residual项目门 `≤1e-8`；exact-ZOH derivative `≤1e-5` relative；finite ladder 最后两级二次补偿差 `≤20%`。必须同时测试 `\bar f(0,q,0)=0` 的 family identity，才能删去 pure-q²。

最小后续：分别估计 controller/decoder 两侧方向导数，构建 piecewise closed-loop Volterra kernel；增加更小 `ε/2` 点并保持 mode hash；给出 uniform remainder radius。没有这些量，不给闭环定量 disadvantage 常数。

可写：

> At the registered equilibrium, complete physical M/D mixed tensors converge and the sealed nonlinear amplitude ladder is quadratic-leading, whereas additive energy-port actuation has a nonzero first-order lift. The implemented normalized controller is piecewise, so no single smooth normalized-policy Taylor theorem is asserted.

禁止：“`f_u=0` 蕴含没有 `u²`”“全局 `O(ε²)`”“21.91 是直接物理性能比”“bilinear open lift 就是 closed-loop Volterra kernel”“direct M/D 对所有控制器都无效”。

---

# U8 — 异质性/网络不对称下的近似 common–differential separation

## U8.1 通用 commutator bound

设 state projector `P_x` 表示 common subspace，`Q_x=I-P_x`；输入/输出 projectors 为 `P_u,Q_y`。令

\[
R(s)=(sI-A)^{-1}.
\]

交换子恒等式为

\[
\boxed{R P_x-P_xR=R[A,P_x]R.}
\]

定义

\[
\epsilon_A=\|[A,P_x]\|,
\quad
\epsilon_B=\|Q_xBP_u\|,
\quad
\epsilon_C=\|Q_yCP_x\|,
\quad
\epsilon_D=\|Q_yDP_u\|.
\]

将 `BP_u=P_xBP_u+Q_xBP_u` 分解并应用上式，得到一个充分上界

\[
\boxed{
\begin{aligned}
\|Q_yG(s)P_u\|
\le{}&\epsilon_D
+\epsilon_C\|R\|\|P_xBP_u\|\\
&+\|Q_yC\|\|R\|^2\epsilon_A\|P_xBP_u\|\\
&+\|Q_yC\|\|R\|\epsilon_B.
\end{aligned}}
\]

当 resolvent 接近奇异、projector 不物理可信或 output annihilation 发生时，该界可极松或不可用。R469 正确地拒绝给 101-state 不对称 network coordinates 任意 padding 一个四设备 projector，因此 `ε_A/B/C` 在项目数值层面标记 unavailable。

## U8.2 effective dynamic-stiffness Schur bound

项目使用 transfer-derived

\[
Z_{eff}(s)=sG_{uu}(s)^{-1}.
\]

在 common/differential basis 下写

\[
Z=
\begin{bmatrix}
z_{cc}&z_{cd}\\
z_{dc}&Z_{dd}
\end{bmatrix},
\quad
S_c=z_{cc}-z_{cd}Z_{dd}^{-1}z_{dc}.
\]

若 `Z_dd` 可逆且 `S_c≠0`，则

\[
(Z^{-1})_{dc}=-Z_{dd}^{-1}z_{dc}S_c^{-1}.
\]

因 `G=sZ^{-1}`，对单位 common input：

\[
\boxed{
\frac{|s|\,\|z_{dc}\|}{\|Z_{dd}\|\,|S_c|}
\le
\|G_{dc}\|
\le
\frac{|s|\,\|Z_{dd}^{-1}\|\,\|z_{dc}\|}{|S_c|}.}
\]

若额外 observation/input map 非等距，要乘相应最小/最大 singular values；下界需要 full-rank/non-annihilation 条件。

在理想 balanced swing 部分，`q_c=1_4/2`，差模基 `T_d`：

\[
z_{dc}(jω)
=-ω^2T_dMq_c+jωT_dDq_c,
\]

因此

\[
\|z_{dc}\|^2
=ω^4\delta_M^2+ω^2\delta_D^2,
\]

其中 `δ_M=||T_dMq_c||`、`δ_D=||T_dDq_c||`。但真实 network asymmetry 可以在 `δ_M=δ_D=0` 时仍产生非零交叉项。

## U8.3 为什么异质性本身不能给 universal law

1. 固定相对异质性/CV，同时把所有动态 stiffness 乘大尺度 `c`，inverse response 可趋小；所以“大异质性”不强迫大 finite-window cross energy。
2. 令 `σ_min(Z_dd)` 或 `|S_c|` 逼近 0，任意小 `z_dc` 都可被放大；所以“小异质性”不保证小 response。
3. 特定 finite window、输入和输出可能与 cross mode 正交或发生抵消，large parameter mismatch 仍可产生小观测能量。

因此必须同时报告 asymmetry、resolvent/Schur conditioning、input/output rank 和 window。

## U8.4 DAE 扩展

对 index-1 DAE，只在 `g_y` uniformly invertible、active mode/gauge 固定时，把 Schur-reduced `A_r,B_r,C_r,D_r` 代入上述 bound；必须保留 algebraic feedthrough。若 `g_y` 接近奇异，reduction condition number 进入 bound；跨 mode 时单一 smooth bound 失效。

## U8.5 R469 项目结果

- 8 profiles × `α∈{0,0.25,0.5,1}` = 32 models；
- 每个 101 quotient states、4 energy-port inputs、3 load inputs、4 frequency outputs；
- 1025 frequencies（DC–2.5 Hz），32768 个非零频点；
- 30-step scalar-common→3-differential lifts；
- block reconstruction 最大误差 `1.8048e-16`；
- direct impulse/lift 最大误差 `3.4694e-17`；
- 32768/32768 points 上 actual cross norm 均落在 Schur lower/upper bounds 内；最小 upper slack `2.7545e-5`，最小 lower slack `1.5803e-5`；upper/actual 比 1.22–3.85；
- max resolvent condition `1.6351551602528666e6`，低于 `1e12` flag；
- homogeneous profile 的 30-step cross-lift norm 已为 0.0401–0.0455，说明 network-asymmetry intercept；fully heterogeneous 为 0.0554–0.0989；
- normalized incremental spread 0.009495–0.316208，不支持 universal linear heterogeneity law；
- full-state projector 状态：`NOT-COMPUTED-BY-DESIGN`。

## U8.6 文件、算法与措辞

文件：

- `results/research_loop/r469_u8_separation_bound/bounds/bound_table.csv`
- `.../scaling/heterogeneity_scaling.json`
- `.../checks/verification_report.json`
- `.../contracts/full_state_projector_unavailable.json`

机器算法：验证 input/output projectors 对称、幂等、完备；对每个 model/frequency 用 solve 计算 G 和 Z；检查 `cond≤1e12`、`Z_dd`/`S_c` 可逆；直接 block inversion 重建；逐行验证 `lower-tol≤actual≤upper+tol`；独立 impulse recursion 验证 finite lift。不得在未知 network states 上任意复制设备 projector。

最小后续：只有在构造并证明一个物理 device-permutation representation 后，才计算 full-state commutator；否则继续使用 I/O bound。可增加更小 α 点测试局部线性，但不能用其替代 conditioning terms。

可写：

> The registered local common-to-differential maps satisfy pointwise effective-stiffness Schur bounds. Nonzero homogeneous intercepts and profile-dependent scaling show that M/D heterogeneity alone is insufficient; network asymmetry and conditioning are essential.

禁止：“全状态 commutator 已计算”“异质性与 cross response 存在 universal linear/Bode law”“local finite-window bound 证明 nonlinear/robust separation”“推广到新拓扑”。

---

# U9 — R458 的 dev selection / eval transfer

## U9.1 冻结选择规则

对 350 个 schedules，在 `dev_a/dev_b` 各计算 exact guard。

1. **Priority 1**：若有 candidate 在两 dev 都 guard-clean，在该池中最大化两 dev 的 `(differential improvement + off-diagonal improvement)` 总和；并列取最小 `global_index`。
2. **Priority 2**：若无 priority 1，取只在一个 dev guard-clean 的 candidate；按 feasible profile 数、improvement sum、最小 index 排序。由于该池 feasible count 都为 1，第一个 key 实际冗余。
3. **Priority 3**：若没有任何 dev guard-clean candidate，最小化所有 dev guard 的最坏相对违规；并列取最小 index。该分支是 fallback，不是 witness。

开发数据筛选 350 个候选，winner 的 dev improvement magnitude 存在 winner's curse / selection optimism；但只要 eval 从未参与选择或 reselection，固定 eval 的 pass/fail 没有被开发 selection 直接污染。

## U9.2 分支解释

| selection branch | eval transfer count `k` | 合法解释 |
|---|---:|---|
| P1 | 0 | 两 dev 的有限类 witness，但四固定 eval 无 guard-clean transfer |
| P1 | 1–4 | 同一 schedule 从两 dev 转移到 `k` 个**点名的固定 eval profiles**；k 仅描述 |
| P2 | 0 | 仅一个 dev witness，固定 eval 无 transfer |
| P2 | 1–4 | 从一个 dev witness 到 k 个固定 eval profiles 的有限 bank transfer |
| P3 | 任意 | `FALLBACK-NO-WITNESS`；即使碰巧有 eval pass，也不能把 selection rule 称为 guard-clean witness procedure |
| 任意 | integrity fail | `CANARY-INVALID`，不得解释 outcome |

## U9.3 实际 R458 结果

- candidate pool：both 1，one 3，none 346；
- priority branch 1；
- 唯一 winner `k3_112`，global index 137；
- schedule `[(3,3),(1.5,1.5),(1.5,1.5)]`；
- `eval_a`：endpoint improvements 12.0533%、7.5833%，但 action TV fail；
- `eval_b`：8.0215%、7.4997%，全部 guard pass；
- `eval_c`：12.0167%、5.2981%，全部 guard pass；
- `eval_d`：differential improvement 4.8526% < 5%，故 fail；off-diagonal 9.9584%；
- classification：`GUARD-CLEAN-TRANSFER`，transfer count 2。

因此最强陈述是：在冻结 350-schedule Object A 类中，一个仅用两 dev profiles 选出的 schedule，在两个点名的固定 eval profiles 上守卫全清，在另外两个失败。

## U9.4 统计边界

unit of analysis 是 profile；每 profile 的 6 signed scenarios 是嵌套固定 cases，不是 6 个独立 profile 样本。四个 eval profiles 也不是从声明分布 iid 抽样，因此：

- 不能称 `2/4=50% transfer probability`；
- 不能使用 binomial CI、generalization bound 或 topology probability；
- 只能列出四行 deterministic finite-bank outcome。

未来若要概率：先声明 profile/topology/disturbance generator `\mathcal D`；冻结独立 dev/test；选择一次；对 m 个独立 test profiles 只评估一次；以 profile 为 Bernoulli unit，预注册 exact binomial/Clopper–Pearson 或 stratified cluster estimator。该设计不改变 R458 的既有 gate，只创建新证据对象。

## U9.5 文件、算法与措辞

文件：

- `results/research_loop/r458_dev_select_eval_validate/selection.json`
- `.../formal_analysis.json`
- `memory/rounds/R458/plan.md`
- `paper/yang_md_decoupling_marl/reports/R458.md`

机器检查：验证 candidate sequence hash；重算 700 dev rows；按冻结 lexicographic key 选择；确认 eval 文件时间/hash 未进入 selection；只评估 winner；重算 4 个 joint guards；输出 failing guard；不计算概率。

可写：

> Within the frozen 350-schedule direct-M/D family, one schedule selected using only two development profiles is guard-clean on both development profiles and on two of four fixed evaluation profiles; the remaining two fail for action variation and differential-energy improvement, respectively.

禁止：“50% transfer probability”“robust/topology generalization”“learner 能发现该 schedule”“任意 controller class 可行”“稳定、安全、部署”。

---

# 10. 综合审计结论

1. **完整闭合**：U3 的 Bellman 语义、U4 的不包含性、U5 的总导数、U8 的一般代数界；U1/U4/U9 另有各自有限类或有限 bank 的可重放证书。
2. **只能限定陈述**：U6 没有连续/鲁棒稳定 margin；U7 没有 smooth normalized-policy theorem 或全局 remainder；U1 没有 nonlinear transfer。
3. **尚未完成**：U2。R472 的 active plan、16 个可复用完整 shards 和 92 个缺失 shards 不能替代最终 aggregate。
4. **关键纠错**：`f_u(0)=0` 不排除 pure `u²`；任何“bilinear-only”主张都必须额外验证邻近参数下 equilibrium/output family invariance。
5. **禁止跨对象合并**：Object A 的 direct M/D finite-bank result与 Object B 的 energy-port linear certificates不能汇总成一个统一性能 ratio 或因果比较。
6. **出版级总边界**：目前可以发表的是命名模型、命名控制类、命名频带/窗口、固定 profile bank 与明确数值容差下的局部/有限结论；不能升级为 MARL 成功、普遍消息价值、控制器类全局不可能、稳定、安全、拓扑泛化或部署结论。

## 11. 关键证据索引

- 题面：`tmp/yang_md_decoupling_marl/gpt_pro_unresolved_math_delta_20260821.md`
- U1：`paper/yang_md_decoupling_marl/reports/R464.md`
- U2：`memory/rounds/R472/plan.md`
- U3：`paper/yang_md_decoupling_marl/reports/R460.md`
- U4：`paper/yang_md_decoupling_marl/reports/R463.md`
- U5：`paper/yang_md_decoupling_marl/reports/R465.md`
- U6：`paper/yang_md_decoupling_marl/reports/R467.md`
- U7：`paper/yang_md_decoupling_marl/reports/R468.md`
- U8：`paper/yang_md_decoupling_marl/reports/R469.md`
- U9：`paper/yang_md_decoupling_marl/reports/R458.md`

