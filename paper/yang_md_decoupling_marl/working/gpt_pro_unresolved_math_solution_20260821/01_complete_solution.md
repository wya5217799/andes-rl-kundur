# R457 之后 U1–U9 未决数学问题：完整解答与严格边界

**对象**：`yang-md-decoupling-marl` 论文线  
**输入包**：`gpt_pro_unresolved_math_pack_20260821.zip`  
**解答日期**：2026-08-21  
**证据完整性**：随附核验脚本复算 `SHA256SUMS`，共检查 1,554 个条目，零失败。

---

## 总结论

九个问题中，**U2–U9 可以给出封闭的定理、反例、可识别量和机械验证方案**。U1 不能从现有上传包生成真正的数值 FIR-Youla/SLS 原始—对偶证书；这不是“求解器没找到”，而是**证书对象在数据层面未被确定**：R405 只导出了 DAE Jacobian，R447 只导出了若干闭环标量，R450 只导出了 0.3–0.5 Hz 频带上的返回比矩阵，没有导出 Object B 的完整离散 `A,B_c,B_w,C,D`、已验证 DCF/SLS 映射、FIR 类边界、有限窗提升矩阵和未缩放对偶点。因此，U1 的最强结论是一个严格的“不可实例化/不可核验”命题，并给出最小补充计算，不能把它写成控制器类不可行。

| 问题 | 最强有效结果 | 结论性质 |
|---|---|---|
| U1 | 给出一个精确定义的 10 阶严格因果 differential-only FIR-Youla 类和完整 SOCP 形式；证明现有包不足以生成可核验的可行或不可行证书 | paper-grade proposition |
| U2 | 给出 3×3×2 正交因子设计、严格改变四环每个语义邻居配对且保持经验边际的 placebo，以及“固有信息价值 + 有限学习代价差”的恒等分解 | paper-grade proposition |
| U3 | 给出最小增广 MDP、三种 critic 参数化的等价条件、历史别名反例、Bellman 偏差界和熵正则修正 | algebraic identity |
| U4 | 证明当前期望二次约束不能蕴含逐 profile 守卫；给出有限窗充分条件和精确 finite-bank phase-I 方案 | paper-grade proposition |
| U5 | 推导完整 `A/B/C/D + equilibrium + discretization + controller + headroom` 闭环灵敏度；证明 A/B/C/D 单项归因坐标依赖 | algebraic identity |
| U6 | 给出与 ZOH 数字控制一致的精确分数延迟提升；证明现有数据不能计算极点穿越/鲁棒稳定裕度；端点阈值只可定位于 0–0.2 s | paper-grade proposition |
| U7 | 推导零偏置 M/D 反馈的首个非零双线性/二阶 Volterra 映射，证明固定光滑模式下相对零动作差异为 `O(ε²)` | paper-grade proposition |
| U8 | 给出 commutator/Schur-complement 上界、带条件下界、DAE 扩展和双向反例；复算八个 profile 的 M/D 异质性投影量 | paper-grade proposition |
| U9 | 完整解释 priority 1/2/3 × transfer 0–4 的 15 个分支；证明四个固定 eval profile 只能形成有限库见证，不能给分布泛化界 | paper-grade proposition |

下文始终区分：**硬事实**＝上传包直接给出或随附脚本机械复算；**数学结论**＝在明确假设下证明；**仍缺数据**＝不从摘要标量反推未导出的矩阵或不确定性界。

---

# U1 — 有界 FIR-Youla/SLS 控制器类证书

## U1.1 结论

选择 **verified DCF/Youla** 路线。对一个新明确声明、但尚未在项目中封存的 10 阶严格因果 differential-only FIR-Youla 类，可以把固定线性模型上的差模能量、共模 IAE/峰值/RoCoF、动作 RMS/TV 写成仿射、线性锥或二阶锥约束；“饱和比例 ≤5%”在精确执行映射下是基数约束，通常不是 SOCP，除非采用“全程不饱和”的保守无穷范数约束、固定一个已知 piecewise-affine active mode，或改成 MISOCP/穷举 active modes。

现有包**不能**产出一个可核验的数值 primal witness 或正 dual/Farkas lower bound。最强合法判定是：

> **CERTIFICATE-NOT-IDENTIFIABLE-FROM-SHIPPED-ARTIFACTS**：当前证据不足以决定下面命名类在冻结 Object B 线性模型上可行还是不可行；任何数值“可行/不可行”结论都需要未导出的完整输入输出模型、DCF/SLS 恒等式、有限窗响应提升矩阵和原始尺度对偶变量。

这不是对该类不可行性的证明，也不是对所有控制器不可能性的证明。

## U1.2 选定的精确类、维数、单位与符号

硬事实：R447 给出 Object B 的状态维数 `n=102`、控制输入数 `m=4`、扰动输入数 `r=3`、频率输出数 `p=4`，采样周期由 R447/R450 冻结为 `T_s=0.2 s`。控制输入是 VSG 有功功率命令（system pu），控制器输出先是归一化命令，再由 frozen headroom 映射到 power command；输出是 60-Hz 物理频率。反馈号在 R450 中为

\[
 u=-K(z)y,
 \qquad L(z)=P_c(z)K(z),
 \qquad S(z)=(I+L(z))^{-1}.
\]

令

\[
 q_c=\frac{1}{2}\mathbf 1_4,\qquad
 P_c=q_cq_c^\top=\frac14\mathbf 1\mathbf 1^\top,\qquad
 P_d=I_4-P_c.
\]

在构造 DCF 前先固定无量纲坐标 `y_n=(f-60 Hz)/(1 Hz)`、`u_n=normalized command`。本解答选择下列**新设计输入**，不把它冒充仓库已封存的类：

\[
\boxed{
\mathcal Q_{Y10}
=
\left\{
Q(z)=\sum_{h=1}^{10}Q_hz^{-h}:
Q_h=P_dQ_hP_d,
\ \sum_{h=1}^{10}\|Q_h\|_F^2\le 1
\right\}.}
\]

说明：

1. `h=1,…,10`，因此严格因果，记忆长度 2 s；这是本解答为形成命名类而选的设计输入。
2. 在上述冻结 normalization 下，`Q_h` 是无量纲；若项目改用物理 I/O 坐标，必须把等价 unit-scaling matrix 一并封存，不能复用同一个数值 bound。
3. `Q_h=P_dQ_hP_d` 强制忽略纯共模测量并产生零和命令。每个 tap 在三维差模子空间中有 `3×3=9` 个实自由度，共 90 个自由度。
4. 这是 **Youla 参数的结构约束**；除非进一步验证 LFT realization 的 locality，不能把它写成“最终物理控制器严格 ring-local”。若论文必须保持 ring-edge 信息结构，应在 `Q_h` 或最终 `K(Q)` 上另加经验证的结构约束。

设冻结控制通道传递函数为

\[
P_{22}(z)=C(zI-A)^{-1}B_c+D_c\in\mathbb R^{4\times4},
\]

扰动通道为

\[
P_w(z)=C(zI-A)^{-1}B_w+D_w\in\mathbb R^{4\times3}.
\]

在一套系数级验证通过的 doubly-coprime factorization 下，采用包内 `c1_youlas_sls_certificate.md` 的同一约定：

\[
K(Q)=(\widetilde V+Q\widetilde N)^{-1}(\widetilde U+Q\widetilde M),
\]

且任一声明输出 `z` 对扰动 `w` 的闭环传递为

\[
T_{zw}(Q)=T_{11}+T_{12}QT_{21}.
\]

只有当 block Bézout identity 在**同一组哈希矩阵、同一反馈号、同一 realization**上按系数重算为真时，上述 affine map 才具有证书效力。

## U1.3 有限窗约束的精确锥形式

对 profile `s`，令 `q=vec(Q_1,…,Q_10)∈R^90`。固定初值、扰动、窗口、投影、quadrature 和 reference 后，有限窗堆叠响应必须由真实提升计算得到：

\[
y_{d,s}(q)=b_{d,s}+A_{d,s}q,
\qquad
y_{c,s}(q)=b_{c,s}+A_{c,s}q,
\qquad
u_s(q)=b_{u,s}+A_{u,s}q.
\]

### 差模与交叉端点

若 reference 能量 `E_{d,0,s}>0` 和 `E_{×,0,s}>0` 固定且与 `q` 独立，则 5% 改善要求为

\[
\|W_{d,s}^{1/2}(b_{d,s}+A_{d,s}q)\|_2
\le \sqrt{0.95E_{d,0,s}},
\]

\[
\|W_{\times,s}^{1/2}(b_{\times,s}+A_{\times,s}q)\|_2
\le \sqrt{0.95E_{\times,0,s}}.
\]

二者均为 SOC。若采用 R450 的宽松 cross 上限 `1.10`，只需把右端改为 `sqrt(1.10 E_ref)`；不能把两个口径混写。

### 共模 IAE、峰值与 RoCoF

记 `e_c(q)` 为共模频差样本，`D_t` 为一阶差分矩阵，采样周期 `T_s=0.2 s`：

\[
T_s\|e_c(q)\|_1\le1.03\,\mathrm{IAE}_{0,s},
\]

\[
\|e_f(q)\|_\infty\le1.03\,\mathrm{Peak}_{0,s},
\]

\[
\|D_te_f(q)/T_s\|_\infty\le1.03\,\mathrm{RoCoF}_{0,s}.
\]

`L1` 约束用正负 epigraph 变量写成线性规划约束；`L∞` 约束是成对线性不等式。

### 动作 RMS 与 TV

若 profile 有 `N_s` 个样本、4 个设备、2 个执行分量，按实际聚合定义构造对应权重矩阵，则

\[
\|W_{u,s}^{1/2}u_s(q)\|_2
\le1.10\sqrt{N_{\rm eff,s}}\,\mathrm{RMS}_{0,s}
\]

是 SOC；

\[
\|D_u u_s(q)\|_1\le1.10\,\mathrm{TV}_{0,s}
\]

是线性 epigraph 约束。`D_u` 必须包含仓库执行器采用的 boundary-aware 初始差分；否则 TV 口径不一致。

### 饱和比例和 headroom map

精确条件

\[
\frac1{N_um}\sum_j\mathbf 1\{|u_j(q)|\ge u_{\max,j}\}\le0.05
\]

是基数约束，一般非凸，不能诚实地写成纯 SOCP。可选的合法路径只有：

- **保守 SOCP/LP**：要求 `||u(q)||∞≤u_max−η`，从而饱和比例为 0；
- **固定 active mode**：若已证明整个候选 tube 内 clamp/headroom 分段不变，则执行映射仿射，继续使用 SOCP；
- **穷举所有相关 active modes**：每个 mode 解一个 SOCP，再取并集；
- **MISOCP**：用二元变量精确编码最多 5% 饱和样本。

`valid/completed/TDS failure` 是非线性执行属性，不由局部 LTI SOCP 自动保证。没有固定模式或统一 remainder/IQC bound 时，证书只能声明为冻结线性类的局部结果。

## U1.4 Phase-I 原始—对偶证书

把所有等式消元到 affine hull 后，写成统一 phase-I：

\[
\begin{aligned}
\min_{q,t,\eta}\quad & t\\
\text{s.t.}\quad & F_eq q=f_eq,\\
& \|A_iq+b_i\|_2\le c_i+t,\quad i\in\mathcal I_{soc},\\
& G_jq+g_j\le t\mathbf1,\quad j\in\mathcal I_{lin},\\
& \|W_qq\|_2\le1,\\
& t\ge \underline t.
\end{aligned}
\]

- 若独立重算得到 `t*≤−τ_feas`，相应 `q*` 是该命名类的可行 witness。
- 若一个原始尺度、dual-cone 可行的对偶点给出 `d*>τ_inf>0`，且原始—对偶 gap 与残差小于 `τ_inf` 的安全折扣，则证明**该精确类**不可行。
- “求解器返回 infeasible”而没有对偶点和未缩放重算，不是证书。

建议机械验证门槛（均为本解答的验证设计输入）：

1. Bézout/achievability coefficient residual `≤1e-10` 相对 Frobenius；
2. 原始等式残差 `≤1e-9(1+||data||)`；
3. cone violation `≤1e-9`；
4. dual stationarity residual `≤1e-9`；
5. unscaled relative duality gap `≤1e-8`；
6. 正下界至少大于 `10×` 全部数值残差和线性—非线性 discrepancy allowance；
7. 使用 80-bit/MPFR 或 interval arithmetic 重新评估正下界，避免仅依赖 solver scaling。

## U1.5 为什么当前包不能给证书

### 已有硬事实

- `results/research_loop/r405_homogenization_gate/linearization_matrices.json`：每个 profile 只有 `f_x(102×102), f_y(102×284), g_x(284×102), g_y(284×284), x0, y0, baseline_m0, baseline_d0`。
- `results/research_loop/r447_p1_complex_response/formal_analysis.json`：只给出维数、两种闭环的谱半径、频带能量和比值；未导出构造时使用的 `sampled_model.state_matrix/input_matrix/output_matrix`。
- `results/research_loop/r450_p2_delay_loop/formal_analysis.json`：导出 41 个 0.3–0.5 Hz 频点的 `L0_real/L0_imag`，没有全频 `P_c,P_w`、状态 realization 或 finite-window lifted map。
- `tmp/yang_md_decoupling_marl/c1_youlas_sls_certificate.md` 自身把 DCF、H、系数边界、response matrices、primal-dual point 和 nonlinear discrepancy 明确标为未产生。

### 缺失且不可由摘要标量恢复的量

1. 完整冻结 `A_d,B_c,B_w,C,D_c,D_w` 与精确 I/O normalization；
2. 基线闭环的可验证 DCF 或完整 output-feedback SLS achievability map；
3. 对应每个 profile/场景/窗口的 `A_i,b_i` 提升矩阵；
4. headroom/clamp active-mode 记录及其对扰动的固定性；
5. 未缩放 primal/dual arrays；
6. 从线性模型转到非线性 DAE 的统一 remainder/IQC bound。

这些量不是“可以用 R447 的 0.9065 比值补齐”的。一个频带能量标量和 41 个局部返回比频点对应无穷多种状态空间 realization 与窗外响应；它们可以具有相同已导出摘要，却在 6 s 峰值、TV、饱和和 FIR 类可行性上相反。因此证书结论在当前观测映射下不具可识别性。

## U1.6 最小补充计算

不是新训练。只需一次注册的线性化—提升—证书流水线：

```text
1. 在同一 Object B equilibrium 导出并哈希 A_d,B_c,B_w,C,D、T_s、headroom active mode。
2. 删除/固定角度 gauge；验证 baseline internal stability。
3. 构造 DCF，逐系数重算 block Bézout identity。
4. 对 Q_Y10 的 90 个基向量逐一生成所有 profile 的有限窗列 A_i；中心差分交叉核验。
5. 采用真实 R452 guard aggregation 组装 phase-I SOCP；对饱和选保守 L∞、固定模式或 MISOCP。
6. 导出 solver scaling 前后的 primal/dual；独立 checker 重算残差、gap 和 dual lower bound。
7. 若得 witness，在非线性 DAE 上只运行该一个 realization 及对称系数扰动；记录 active modes，估计统一 discrepancy。
```

**支持**：有 `t*<0` witness 或有经独立验证的 `dual lower bound>0`。  
**反驳**：任一 Bézout/achievability 恒等式不成立、response lift 与直接线性仿真不符、dual 重算不可行、或非线性执行切换出声明 mode。

## U1.7 论文安全措辞

**可写：**

> For the frozen linearized energy-port model, feasibility over a compact, strictly causal 10-tap differential Youla class can in principle be decided by a finite-horizon conic phase-I program once an exact DCF, lifted response matrices, and the actuator active mode are exported. The current artifact package does not contain those certificate-bearing arrays; therefore it supports neither a feasible witness nor an infeasibility certificate for that class. Any future certificate would remain local to the declared model, profile bank, horizon, coefficient bound, and actuator mode.

**禁止写：**

- “no controller can satisfy the guards”；
- “the FIR/Youla class is infeasible”；
- “R447/R450 proves stability or safety”；
- “finite-grid failure proves controller-class impossibility”；
- “linear certificate automatically transfers to nonlinear headroom execution”。

**分类：paper-grade proposition。**

---

# U2 — 因果有效的消息价值与有限学习代价设计

## U2.1 结论

采用 **actor source × critic source × reward** 的 `3×3×2` 完全因子设计：

\[
A,C\in\{0,P,N\},\qquad R\in\{0,1\}.
\]

- `0`：消息槽置零，网络输入维数保持不变；
- `P`：维数、经验边际和数值尺度保持，但消息来自非邻居、独立 donor trajectory 的 placebo；
- `N`：真实同时刻语义邻居消息；
- `R`：是否加入独立预定义的 neighbour-dependent reward term。

这样可在**固定 reward**下比较信息访问，在**固定信息访问**下比较 reward 项，避免 R451 把 actor、critic 和 reward 同时改变。它可以识别算法/预算特定的 authentic-vs-placebo 效应；只有在嵌套类全局最优或优化误差被独立界定时，才能进一步识别 population intrinsic information value。

## U2.2 Population policy classes 与精确 estimands

令 `X_t` 是本地可观测状态，`N_t` 是真实邻居信息，损失 `J(π)` 越小越好。定义

\[
\Pi_X=\{\pi(a|X)\},\qquad
\Pi_{X,N}=\{\pi(a|X,N)\}.
\]

通过令 `π(a|X,N)` 忽略 `N`，有严格嵌套

\[
\Pi_X\subseteq\Pi_{X,N}.
\]

population 最优值为

\[
J_X^*=\inf_{\pi\in\Pi_X}\mathbb E[J(\pi)],\qquad
J_{XN}^*=\inf_{\pi\in\Pi_{X,N}}\mathbb E[J(\pi)].
\]

固有信息价值定义为

\[
\boxed{I^*=J_X^*-J_{XN}^*\ge0.}
\]

对固定训练算法、预算 `B`、初始化/数据随机性 `S`，令 `\widehat\pi_{c,B,S}` 是训练结果：

\[
J_{c,B}=\mathbb E_S\mathbb E_{\rm eval}[J(\widehat\pi_{c,B,S})],
\qquad
L_{c,B}=J_{c,B}-J_c^*\ge0
\]

（后一不等式要求 `J_c^*` 对应同一 architecture-defined class）。则有恒等分解

\[
\boxed{
J_{X,B}-J_{XN,B}
=I^*+L_{X,B}-L_{XN,B}.}
\]

因此，一个有限预算 authentic-vs-no-message 差不能单独决定 `I*`。真实消息可能有正固有价值，却因更难优化而在有限预算下变差；也可能固有价值为零，但正则化/随机优化偶然改善。

Placebo 提供两个更贴近有限学习机制的量：

\[
\Delta_{\rm semantic,B}=J_{P,B}-J_{N,B},
\]

衡量同维度、同边际下真实语义配对的预算特定收益；

\[
\Delta_{\rm dimensional,B}=J_{P,B}-J_{0,B},
\]

衡量增加无关输入通道产生的估计/优化代价。二者仍是算法、architecture、预算和 donor 机制特定，不自动等于 `I*`。

## U2.3 四节点环的有效 placebo

编号 `i∈Z_4`。真实有序消息槽定义为

\[
N_i^{\rm true}(e,t)=\bigl[X_{i-1}(e,t),\ X_{i+1}(e,t)\bigr].
\]

先生成一个**独立、冻结且不读取目标 arm 结果**的 donor bank。对每个 matched scenario 至少有 `E≥2` 条独立 donor trajectories。取无不动点的 episode 置换

\[
\pi(e)=e+1\pmod E.
\]

定义 placebo：

\[
N_i^{P}(e,t)
=
\bigl[X_i(\pi(e),t),\ X_{i+2}(\pi(e),t)\bigr].
\]

### 命题 U2-P1：每个语义邻居配对都改变

对任意 `i`，真实左 donor 是 `i−1`，placebo 左 donor 是 `i`；真实右 donor 是 `i+1`，placebo 右 donor 是 `i+2`。模 4 下二者均不相等。因此四个 agent 的两个槽都不再使用其真实语义邻居。又因 `π(e)≠e`，placebo 不使用目标 trajectory 的同时刻状态。

### 命题 U2-P2：声明的经验边际被精确保持

对每一个槽、feature component 和时间 `t`，映射

\[
(i,e)\mapsto(i,\pi(e))
\quad\text{或}\quad
(i,e)\mapsto(i+2,\pi(e))
\]

都是 `Z_4×Z_E` 上的双射。因此在 pooled recipient×episode 样本上，每个槽的数值 multiset 完全不变，均值、方差、分位数和全部经验边际都精确保持。它不保证 recipient-conditional 或 joint temporal correlation 不变；这正是需要破坏的语义关联。

### 有效性条件

- donor bank 必须由独立随机种子产生，并在 arms 训练前冻结；
- scenario/profile/time index 要匹配，避免把负荷幅值等混入 placebo 差异；
- donor 不得来自目标 arm 的未来回报或选后轨迹；
- 若环境完全确定且不同 episode 字节相同，placebo 不再提供信息破坏，应增加独立 disturbance/noise seed；
- 不将 self/opposite donor 的物理相关性解释为完全统计独立，只把它作为“保边际、破真实邻接”的 negative control。

## U2.4 正交因子与可识别对比

18 个 cells 全部保持同一网络宽度、优化器、更新数、replay 容量、reward scale、环境 bank、slew projector 和 evaluation gate。初始化应在创建网络**之前**设 seed，最好对同一 seed 的 18 个 arms 从同一 base state dict 克隆。

主要对比均在固定另外两因子下进行：

\[
\begin{aligned}
\text{actor semantic effect}&: J_{A=N,C=c,R=r}-J_{A=P,C=c,R=r},\\
\text{critic semantic effect}&: J_{A=a,C=N,R=r}-J_{A=a,C=P,R=r},\\
\text{reward effect}&: J_{A=a,C=c,R=1}-J_{A=a,C=c,R=0},\\
\text{dimension cost}&: J_{A=P,C=c,R=r}-J_{A=0,C=c,R=r}.
\end{aligned}
\]

二阶/三阶 interaction 由标准 effect coding 或预注册线性模型识别。`N-vs-0` 只作为总算法差；因它同时改变语义和输入通道有效维度，不是纯信息值。

## U2.5 分层不确定性

**独立推断单位是 training seed**。profile、scenario 和 trajectory 位于 seed 内部，不得把它们当成额外独立训练复制。

对每个 seed `s` 先按冻结权重聚合 evaluation bank，得到 cell loss `Y_{s,a,c,r}`。构造 seed 内配对 contrast `D_s`，再用：

1. seed-cluster bootstrap；或
2. 对 `D_s` 做精确 paired sign-flip/randomization；或
3. 层级模型 `Y=μ_cell+b_seed+b_{seed,profile}+ε`，但置信结论仍由 seed 数决定。

共同环境随机数可以减少方差，但不增加样本量。只有 3–5 个 seeds 时，区间应报告为探索性；不能把几十条 scenario 轨迹伪装成几十个独立训练样本。

## U2.6 支持、反驳与不识别分支

### 支持真实消息的有限预算语义价值

在 reward、actor/critic 另一侧 access、初始化和预算固定时：

- authentic `N` 在预注册主要 endpoint 上稳定优于 placebo `P`；
- 差异在 held-out profiles 上保持；
- placebo 与 no-message 的差能解释额外维度代价；
- 随预算增加，`N-P` 不仅是早期随机波动。

### 反驳特定机制

- `N≈P` 且区间排除预注册 materiality：反驳“该消息内容在该算法/预算下有实质语义价值”；
- `P` 比 `0` 明显更差而 `N` 仅恢复这部分：支持“消息主要抵消维度代价”，不支持强固有价值；
- actor access 有效而 critic access 无效：只反驳该 critic-access mechanism，不是 universal critic irrelevance；
- seed 间符号剧烈翻转或训练损失未稳定：归类为 optimization-unresolved。

### 即使执行该设计仍不可识别

- 神经网络类的全局 `J*`，除非有独立全局下界/收敛证书；
- 任意 architecture、任意消息编码或任意拓扑的信息价值；
- 单个 feature 的因果贡献，除非另做 feature-level randomized ablation；
- 真实 deployment distribution 上的价值；
- reward shaping 与环境物理目标的规范性正确性。

## U2.7 机械执行合同

```text
for seed in preregistered_training_seeds:
    seed all RNGs before constructing any network
    base_state = initialize_once(seed)
    donor_bank = freeze_independent_donor_trajectories(seed + fixed_offset)
    for A in {zero, placebo, authentic}:
      for C in {zero, placebo, authentic}:
        for R in {base, base+neighbor_term}:
          clone base_state
          run identical update budget and replay protocol
          store executed-action-correct transitions from U3
          evaluate once on frozen held-out bank
aggregate within seed first
compute preregistered paired contrasts and seed-cluster intervals
```

数值检查：placebo 变换必须对每个 `(i,e,t,slot)` 检查 donor identity 不等于真实邻居；对每个 slot 校验输入 multiset 的 hash 与 authentic donor bank 对应 multiset 相同；所有 cell 的 reward hash 在固定 `R` 下相同。

## U2.8 论文安全措辞

**可写：**

> A crossed actor-access, critic-access, and reward design with a marginal-preserving non-neighbour placebo separates semantic message effects from input-dimensionality effects at a fixed training budget. The resulting contrasts remain algorithm- and budget-specific. They identify the population value of information only if optimization gaps for the nested policy classes are independently controlled.

**禁止写：**

- “messages are intrinsically valuable”仅凭有限训练 gap；
- “placebo proves messages are statistically independent”；
- “scenario count is the effective sample size”；
- “R410/R431 opposite signs form a causal comparison”；
- 使用 R451 的任何训练方向性输出。

**分类：paper-grade proposition。**

---

# U3 — Stateful slew projector 的正确 Bellman 语义

## U3.1 结论

若执行动作由

\[
v_t=P(v_{t-1},u_t)
\]

产生，则最小 Markov 状态必须至少包含 `z_t=(x_t,v_{t-1})`。若 headroom、SOC、clamp hysteresis 或通信缓存也影响执行，则这些内部状态也必须加入 `z_t`。在该增广状态上，raw-action critic `Q(z,u)` 和 executed-action critic `Q(z,v)` 都可合法；历史问题不是“critic 永远不能用 raw action”，而是**奖励和下一状态由 `v` 生成，却把缺少 `v_{t-1}` 的 `(x,u)` 当成 Markov state-action，或 target/replay 在 raw/executed 语义之间混用**。

## U3.2 最小增广 MDP

令原物理转移为 `p_x(dx'|x,v)`，奖励为 `r_x(x,v,x')`。定义

\[
\tilde p(dx',dv'|x,v^-,u)
=p_x(dx'|x,P(v^-,u))\,\delta_{P(v^-,u)}(dv').
\]

于是

\[
z_t=(x_t,v_{t-1}),\qquad
v_t=P(v_{t-1},u_t),\qquad
z_{t+1}=(x_{t+1},v_t).
\]

包内 repaired implementation 的 registered componentwise projector 为

\[
P(v^-,u)=\operatorname{clip}_{[-1,1]}
\left(v^-+\operatorname{clip}_{[-\delta,\delta]}
(\operatorname{clip}(u)-\operatorname{clip}(v^-))\right),
\quad\delta=0.25.
\]

源：`src/andes_rl_kundur/agents/cd_matd3.py::project_slew_torch`。

## U3.3 三种 critic 表示

### 1. Raw-action critic

\[
Q^u(z,u)=\mathbb E\left[r+\gamma V(z')\mid z,u,
 v=P(z,u)\right].
\]

合法条件：`z` 完整、`P` 确定、raw action 的任何额外成本也包含在 reward 中。由于多个 raw `u` 可映射到同一 `v`，若 reward/transition 只依赖 `v`，则 `Q^u` 在每个 projector preimage 上应相等。

### 2. Executed-action critic

\[
Q^v(z,v),\qquad v\in\mathcal V(z)
=
[\max(-1,v^--\delta),\min(1,v^-+\delta)]^m.
\]

若 actor 仍输出 raw `u`，训练 actor 时必须通过 `v=P(z,u)` 把梯度传入 critic；target 也必须对 target raw action 做同一 projector。严格写法是 `Q(z,v)`。若物理 reward/transition 只依赖 `(x,v)`，且 `v` 本身成为下一步的 projector memory，则在可行 state-action pairs 上可把 critic 压缩为 `Q(x,v)`：旧的 `v^-` 只约束当前 `v` 是否可行，不再影响给定 `v` 后的转移。包内 repaired TD3 路径采用这一压缩语义：actor 读取 augmented state，replay 存 previous/executed action，target 以当前 executed action作为下一步 `previous` 再投影 target actor 输出，而 critic 评估 `(x,executed action)`。

### 3. Two-action critic

`Q(z,u,v)` 在 `v=P(z,u)` 确定时冗余。只有 projector 随机、部分未知，或 reward 明确惩罚 raw command 与 executed command 的差异时，保留二者才有额外信息。

### 等价条件

定义 push-forward policy

\[
\pi_v(\cdot|z)=P(z,\cdot)_\#\pi_u(\cdot|z).
\]

若所有转移和物理 reward 只依赖 `v`，则

\[
Q^u(z,u)=Q^v(z,P(z,u)).
\]

raw 与 executed 表示在期望回报上等价；但它们的 policy entropy 和函数逼近几何不等价。

## U3.4 正确 replay 与 SAC/TD3 target

完整 tuple：

\[
(x_t,v_{t-1},u_t,v_t,r_t,x_{t+1},d_t),
\]

或等价地

\[
(z_t,u_t,v_t,r_t,z_{t+1},d_t).
\]

若 critic 输入 executed action，可不保存 raw `u_t`，但为审计 projector 和 latent entropy 最好保存。TD3 target：

\[
\begin{aligned}
u'&=\pi_{\bar\theta}(z')+\epsilon,\\
v'&=P(v_t,u'),\\
y&=r+\gamma(1-d)\min_j Q_{\bar\phi_j}(z',v').
\end{aligned}
\]

SAC executed-action target 应为

\[
y=r+\gamma(1-d)
\left[\min_j Q_{\bar\phi_j}(z',v')
-\alpha\log\pi_v(v'|z')\right].
\]

若实际使用 `log π_u(u'|z')`，优化的是 latent raw-command entropy，而不是物理执行动作 entropy，必须明确声明。

## U3.5 历史不一致的最小反例

取一个无物理状态的标量系统，`x_{t+1}=v_t`，raw action 固定 `u_t=0`，slew limit `δ=0.25`：

\[
P(1,0)=0.75,\qquad P(-1,0)=-0.75.
\]

同一个观测—raw-action `(x=0,u=0)` 可产生两个不同下一状态和不同 reward（例如 `r=v`）。因此不存在单值 Markov kernel `p(x'|x,u)`，也不存在正确的 `Q(x,u)`。随附脚本机械复算该反例。

更强地，从边界 `v^-=-1` 请求 `u=1` 时，执行为 `v=-0.75`，raw/executed 差为 `1.75`。所以“raw 与 executed 很接近”也不是由 0.25 slew 自动保证。

如果把 `v^-` 加入 state，并始终把 projector 视作环境一部分，则 raw-action critic 本身不再不一致。历史 limitation 的准确措辞必须包含“缺失 projector state 或 action semantics 混用”。

## U3.6 Bellman 偏差界

设错误 surrogate 把 raw `u` 当成直接执行动作。假设：

\[
|r(x,u)-r(x,v)|\le L_r\|u-v\|,
\]

物理转移在 Wasserstein-1 下满足

\[
W_1(p(\cdot|x,u),p(\cdot|x,v))\le L_p\|u-v\|,
\]

且后续 value 是 `L_V`-Lipschitz。则一步 Bellman operator 误差满足

\[
\left|\mathcal T_{raw}V-\mathcal T_{exec}V\right|
\le (L_r+\gamma L_pL_V)\|u-P(v^-,u)\|.
\]

若最大一步误差为 `ε_B`，两个收缩算子的固定点满足

\[
\|Q_{raw}-Q_{exec}\|_\infty
\le\frac{\varepsilon_B}{1-\gamma}.
\]

轨迹特定界为

\[
|G_{raw}-G_{exec}|
\le\sum_{t=0}^{N-1}\gamma^t
(L_r+\gamma L_pL_V)\|u_t-v_t\|.
\]

包内没有 `L_r,L_p,L_V`，所以不能给数值 bias bound；可给出的无条件结果是上面的 aliasing counterexample。

## U3.7 熵正则

clamp/slew projector 是 many-to-one：大量 raw actions 映射到同一边界 executed action。push-forward `π_v` 通常包含连续部分和边界原子，不能用普通可逆 change-of-variables 的单一 density 表示。若继续奖励 `H(π_u)`，actor 可以在同一物理动作的 preimage 内扩散 raw command，获得熵奖励却不增加物理探索。

首选方案是直接参数化 feasible executed interval：

\[
v=l(z)+(h(z)-l(z))\frac{\tanh \xi+1}{2},
\]

其中 `l=max(-1,v^-−δ)`、`h=min(1,v^-+δ)`，并使用对应 Jacobian 修正。这样除数值端点外是近乎一一映射。另一合法方案是保留 raw entropy，但明确它是“command-generator entropy”，不把它解释为 executed-action entropy。

## U3.8 最小验证合同

### 一步测试

1. 对 `v^-∈{-1,-0.5,0,0.5,1}` 和 raw grid 比较 NumPy runtime projector 与 Torch projector，最大绝对误差 `≤1e-7`；
2. 检查 replay 的 `next_prev_action == executed_action`；
3. 固定 exogenous seed，相同 `(z,u)` 必须给相同 `v,r,z'`；
4. 删除 `v^-` 后运行上述 `u=0, v^-=±1` 反例，必须检测到 two-valued transition；
5. 若用 raw critic，检查同一 `z` 下映射到同一 `v` 的 raw preimages 的 target 相同。

### 多步测试

1. 用保存的 raw sequence 从初始 `v_{-1}` 递推重构整条 executed sequence，逐步误差 `≤1e-7`；
2. 在一个 3–5 步确定性 toy MDP 上穷举所有 raw actions，比较手算 return 与 TD target，误差 `≤1e-6`；
3. 检查 actor update 的 critic 输入是投影后 action；
4. SAC 若声称 executed entropy，检查分布 parameterization 和 log-density 对 feasible interval 一致。

## U3.9 论文安全措辞

**可写：**

> A stateful slew limiter makes the previous executed command part of the Markov state. A raw-command critic is valid only on this augmented state with the projection included in the transition kernel; an executed-command critic is equivalent after push-forward of the policy. Omitting the previous executed command aliases distinct transitions and makes a critic trained on raw commands Bellman-inconsistent.

**禁止写：**

- “raw-action critics are always invalid”；
- “R431 bias equals某个数值”而没有 Lipschitz/trace；
- “raw entropy equals physical exploration entropy”；
- “slew limit 0.25 means raw-executed error≤0.25”。

**分类：algebraic identity。**

---
# U4 — 训练约束集与 trajectory-level 物理守卫集

## U4.1 结论

当前 learner 的 expected episodic quadratic common-cost 约束不能保证进入 R452/R453 的逐 profile guard set。原因有三层：

1. **期望约束不蕴含逐 profile 约束**；
2. 当前 budget 没有按 reference-relative guard 阈值校准；
3. common quadratic cost 根本不包含两个 endpoint improvement、动作 RMS、TV、饱和比例和 execution validity。

可以对 common IAE/peak/RoCoF 推导有限窗充分条件，但按 eval bank 的最紧 reference，单 episode common budget 需不高于约 `9.4211×10^-4` 才能通过该粗上界同时保证三项；当前 registered budget 是 `3.0`，相差约 3,184 倍，而且即使把 budget 降到该值，仍不能约束动作与端点。因此当前 feasible set inclusion 不成立。

最小对齐方案是：在一个**命名且可机械评估的有限 policy/controller 类**上，直接最小化所有固定 profile/seed 的最大 normalized guard violation；训练可以用平滑 surrogate，但 phase-I 和最终 gate 必须使用原始 guard 公式。

## U4.2 两个 feasible sets

### 训练 feasible set

包内 `cd_matd3_canary.py` 定义：

- `σ_f=0.15 Hz`；
- `σ_p=0.25 pu`；
- `σ_RoCoF=1 Hz/s`；
- `γ=0.99`；
- common episode budget `B_c=3.0`；
- Lagrange multiplier update step `0.05`，clip 到 `[0,10]`。

每步 common cost 为

\[
c_c(t)=\frac14\sum_{i=1}^4
\left(\frac{f_i(t)-60}{0.15}\right)^2
+\frac14\sum_{i=1}^4
\left(\frac{\dot f_i(t)}{1}\right)^2.
\]

若实际 constraint 使用未折扣 episode sum，则

\[
\mathcal F_{train}
=
\left\{\pi:
\mathbb E_{S,P,\Xi}\left[\sum_{t=0}^{N-1}c_c^\pi(t)\right]
\le3
\right\}.
\]

若 critic target 内隐含 discount，则应另声明 discounted 版本；不能在证明中把 discounted 和 undiscounted 混为同一个集合。differential cost 是被优化目标，不是 hard guard。

### 注册守卫 feasible set

R452 的固定阈值为：两个 endpoint 各改善至少 5%，common 三项相对 reference 不恶化超过 3%，动作 RMS/TV 不恶化超过 10%，饱和比例不超过 5%，且 candidate/reference 都 `valid=True`：

\[
\mathcal F_{guard}
=\bigcap_{p\in\mathcal P}\bigcap_{s\in\mathcal S_p}
\left\{\pi:
\begin{array}{l}
(E_{d,0}-E_d^\pi)/E_{d,0}\ge0.05,\\
(E_{\times,0}-E_\times^\pi)/E_{\times,0}\ge0.05,\\
\mathrm{IAE}_c^\pi\le1.03\mathrm{IAE}_{c,0},\\
\mathrm{Peak}^\pi\le1.03\mathrm{Peak}_0,\\
\mathrm{RoCoF}^\pi\le1.03\mathrm{RoCoF}_0,\\
\mathrm{RMS}_u^\pi\le1.10\mathrm{RMS}_{u,0},\\
\mathrm{TV}_u^\pi\le1.10\mathrm{TV}_{u,0},\\
\mathrm{SatFrac}^\pi\le0.05,\quad valid.
\end{array}
\right\}.
\]

单位分别是 `Hz²·s`/注册能量单位、`Hz·s`、`Hz`、`Hz/s`、normalized action、normalized-action variation 和无量纲比例。守卫是 finite-bank、reference-relative、逐 profile 的交集；训练约束是分布平均、绝对 normalization 的一个二次矩。

## U4.3 不包含性的最小反例

### 反例 1：期望约束不保证逐 profile

取两个 profiles，坏 profile 概率 `ε>0`。策略在普通 profile 上 common cost 为 0，在坏 profile 上为 `3/ε`。则期望恰为 3，属于 `F_train`；但坏 profile 的 peak/IAE 可任意大，因而不属于 `F_guard`。这证明任何仅对 mixture expectation 的约束都不能推出逐 profile maximum，除非另加 almost-sure/robust 条件。

### 反例 2：即使 common cost 很小，也不约束端点与动作

构造两个 policy 产生完全相同的 `f_i(t)` 和 RoCoF，因此 common cost 相同；其中一个输出高频零均值动作，在物理模型中被一个无效/被截断通道吸收。它可具有任意大的 TV 或饱和比例，而 common cost 不变。类似地，差模 endpoint 可以恶化而平均频率保持相同。因此不存在只依赖当前 `c_c` 的函数 `B`，使 `C_c≤B` 自动推出全部七个 guard。

## U4.4 common 三项的有限窗充分条件

假设每个 30-step episode 都满足未折扣

\[
\sum_{t=0}^{29}c_c(t)\le B.
\]

由每个非负项不超过总和，任一设备、任一样本有

\[
|f_i(t)-60|\le2\sigma_f\sqrt B,
\qquad
|\dot f_i(t)|\le2\sigma_{\dot f}\sqrt B.
\]

对共模 `\bar e_t=(1/4)Σ_i(f_i-60)`，Jensen 与 Cauchy–Schwarz 给出

\[
T_s\sum_{t=0}^{N-1}|\bar e_t|
\le T_s\sigma_f\sqrt{NB}.
\]

若一个 profile summary 聚合 `R` 条 scenario records，充分条件为

\[
B\le
\min\left\{
\left(\frac{1.03\,\mathrm{Peak}_0}{2\sigma_f}\right)^2,
\left(\frac{1.03\,\mathrm{RoCoF}_0}{2\sigma_{\dot f}}\right)^2,
\left(\frac{1.03\,\mathrm{IAE}_0}{RT_s\sigma_f\sqrt N}\right)^2
\right\}.
\]

随附脚本使用 R452 的四个 eval reference、`R=6,N=30,T_s=0.2` 复算：

| profile | IAE 充分 B | peak 充分 B | RoCoF 充分 B | 三项共同充分 B |
|---|---:|---:|---:|---:|
| eval_a | 0.80998 | 0.026013 | **0.0009421** | **0.0009421** |
| eval_b | 0.50488 | 0.033172 | 0.007090 | 0.007090 |
| eval_c | 1.03908 | 0.045314 | 0.002075 | 0.002075 |
| eval_d | 0.62317 | 0.064018 | 0.016084 | 0.016084 |

这些是保守的充分界，不是必要界；它们只覆盖 common 三项。最紧值来自 eval_a 的 RoCoF reference。`B=3` 对单设备 peak 给出的粗上界是 `2×0.15×sqrt(3)=0.5196 Hz`，而 eval_a guard peak 约 `0.04839 Hz`，显然没有 inclusion certificate。

## U4.5 最小对齐 constrained objective

对固定 profile/seed bank，定义每个 guard 的 dimensionless violation：

\[
\begin{aligned}
g_{d,p,s}(\pi)&=0.05-\frac{E_{d,0}-E_d^\pi}{E_{d,0}},\\
g_{\times,p,s}(\pi)&=0.05-\frac{E_{\times,0}-E_\times^\pi}{E_{\times,0}},\\
g_{iae,p,s}(\pi)&=\frac{\mathrm{IAE}_c^\pi}{\mathrm{IAE}_{c,0}}-1.03,
\end{aligned}
\]

其余按 R458 `_guard_margin` 同样定义。最小 phase-I 为

\[
\boxed{
\min_{\pi\in\Pi,t}\ t
\quad\text{s.t.}\quad
 g_{j,p,s}(\pi)\le t
\quad\forall j,p,s.}
\]

- `t≤0` 给出 finite-bank witness；
- 对有限 350 schedule 类，穷举无 `t≤0` 即证明该有限集合内无 witness；
- 对 U1 的凸 FIR 类，正 dual lower bound 可证明该凸类不可行；
- 对神经网络类，局部 optimizer 的 `t>0` 不能区分 infeasibility 与 optimizer failure。

训练阶段可用 log-sum-exp 平滑 `max`、Huber 平滑 absolute value，或 primal-dual minibatch 近似；但最终判定必须回到 exact finite-bank guard。若真正目标是随机 profile distribution，可采用 CVaR/chance constraint，但这需要显式分布和置信水平，不能替代现有固定 gate。

### 非光滑项

- peak/max、IAE/TV 的 absolute value：非光滑但可用 subgradient/epigraph；
- saturation fraction：不连续基数函数；
- `valid/TDS failed`：离散 failure indicator；
- state-dependent headroom/clamp：piecewise smooth，在 mode boundary 不可微；
- reference ratio：reference 为正且冻结时可微；reference 接近零时必须设物理下界而不是用任意 `1e-12` 支撑论文结论。

## U4.6 R456 的正确整合

R456 在 6 个 checkpoint-local shards 中发现 RMS constraint/value gradient material conflict 的 support count 为 4；TV 对应 count 为 2，未达到其支持判定。它说明**在该冻结诊断切片**，优化 differential value 与降低 RMS violation 的方向经常冲突，可解释部分 dual pressure；它不是 KKT 证书、不是全局 infeasibility，也不能证明所有训练都会发生冲突。

在 aligned phase-I 中，应同时记录每个 guard gradient 与 objective gradient 的 cosine、projected step 后真实 guard 改变量，以及 multiplier 是否因 exploratory/final gap 不一致而 pin cap。若 exact finite-bank phase-I 找到 witness，则历史 gradient conflict 只是优化路径问题；若 convex class 有正 dual bound，才可升级为类内不可行。

## U4.7 最小新实验

1. 固定一个命名类：优先使用 350 finite schedules 或 U1 的凸 FIR 类；
2. 直接计算 exact `g_{j,p,s}`，不要通过 reward 重构；
3. 解 phase-I 或穷举；
4. 导出最优 `t`、全部 active guards、witness/dual；
5. 若使用 neural policy，只把 phase-I 当搜索目标，不能把局部失败解释为类不可行。

**支持 inclusion**：对所有 bank 元素机械验证 `g≤0`。  
**反驳 inclusion**：找到一个 training-feasible policy/profile 使任一 exact guard `g>0`；当前定义已有一般反例。

## U4.8 论文安全措辞

**可写：**

> The episodic common-mode quadratic constraint is not an inner approximation of the registered trajectory-level guard set. It controls an expected normalized second moment, whereas the gate is a profile-wise intersection of reference-relative endpoint, peak, RoCoF, action-stress, saturation, and validity constraints. A finite-bank max-violation phase-I program is required to distinguish a guard-clean witness from optimizer failure in a named controller class.

**禁止写：**

- “common budget 3 guarantees no harm”；
- “dual saturation proves infeasibility”；
- “4/6 gradient conflicts are universal”；
- “training reward equals evaluation gate”；
- “未找到 neural policy 就证明没有 feasible policy”。

**分类：paper-grade proposition。**

---

# U5 — 完整闭环 M/D 灵敏度

## U5.1 结论

R449 的 `dA_d/dρ` 分解只覆盖完整导数的一部分。完整导数必须同时包括 equilibrium、DAE reduction、`A/B/C/D`、ZOH discretization、controller realization、headroom active mode 和 reference denominator。总闭环 transfer/energy derivative 是坐标不变量；把结果拆成 “A-channel、B-channel、C-channel” 的单项贡献一般依赖状态坐标，尤其当 similarity transform 随 `ρ` 变化时。因此可以报告 total derivative 和按物理端口定义的 counterfactual blocks，不能把 A-only term 称为唯一 failure cause。

现有包不能导出 R405 reduction error interval，也不能给 MIMO gain/phase margin：缺少全 Nyquist 频带 return ratio、open-loop unstable pole count、完整 sampled matrices 和 operator-norm uncertainty。

## U5.2 精确 MIMO 传递导数

令 `ρ∈{log M,log D}`，固定复频点 `z=e^{jωT_s}`，

\[
R(z,\rho)=(zI-A(\rho))^{-1}.
\]

控制和扰动通道：

\[
P_c=C R B_c+D_c,
\qquad
P_w=C R B_w+D_w.
\]

反馈为 `u=-Ky`，故

\[
L=P_cK,\qquad S=(I+L)^{-1},\qquad G=SP_w.
\]

由

\[
R_\rho=R A_\rho R
\]

得到

\[
\begin{aligned}
(P_c)_\rho={}&C_\rho RB_c+CR A_\rho RB_c+CR(B_c)_\rho+(D_c)_\rho,\\
(P_w)_\rho={}&C_\rho RB_w+CR A_\rho RB_w+CR(B_w)_\rho+(D_w)_\rho.
\end{aligned}
\]

又有

\[
L_\rho=(P_c)_\rho K+P_cK_\rho,
\qquad
S_\rho=-SL_\rho S,
\]

因此完整闭环导数为

\[
\boxed{
G_\rho=S\left[(P_w)_\rho-L_\rho G\right].}
\]

该式包含 reference controller 对 `ρ` 的变化；若 controller 参数被冻结，`K_ρ=0`，但其状态 realization 与 headroom gain 是否随 `ρ` 变仍需分别检查。

## U5.3 有限频带能量与 ratio derivative

令 `W_o(ω)\succeq0` 是差模输出权，`W_i(ω)\succeq0` 是扰动权，quadrature 权重 `w_l>0` 固定：

\[
E(\rho)=\sum_{l=1}^{L}w_l
\operatorname{tr}\left[
G_l^*W_{o,l}G_lW_{i,l}
\right].
\]

若权重与频点不随 `ρ` 变，则

\[
\boxed{
E_\rho=2\operatorname{Re}
\sum_lw_l\operatorname{tr}
\left[G_l^*W_{o,l}(G_l)_\rho W_{i,l}\right].}
\]

对 candidate/reference 比值

\[
r(\rho)=\frac{E_K(\rho)}{E_L(\rho)},\qquad E_L>0,
\]

有

\[
\boxed{
\frac{r_\rho}{r}
=\frac{(E_K)_\rho}{E_K}
-\frac{(E_L)_\rho}{E_L}.}
\]

这正是 R449 应扩展到所有通道后的 total log sensitivity。R449 的 candidate/reference A-channel 项符号相反且幅值相近，只说明 A-only 局部 attribution 为 `MIXED`；它不决定 total derivative 的符号。

## U5.4 equilibrium 与 index-1 DAE reduction

设 equilibrium 满足

\[
F(\xi,\rho)=0,
\qquad \xi=(x,y),
\]

且 Jacobian `F_ξ` 可逆于固定 gauge/active mode，则

\[
\xi_\rho=-F_\xi^{-1}F_\rho.
\]

所有 `f_x,f_y,g_x,g_y` 的 `ρ` 导数必须是沿 equilibrium manifold 的 total derivative，而不是固定 `x0,y0` 的偏导。

对 index-1 DAE

\[
\dot x=f(x,y,u,w;\rho),\qquad0=g(x,y,u,w;\rho),
\]

在 `g_y` 可逆时

\[
A_r=f_x-f_yg_y^{-1}g_x,
\qquad
B_r=f_u-f_yg_y^{-1}g_u.
\]

例如

\[
\begin{aligned}
(A_r)_\rho={}&(f_x)_\rho-(f_y)_\rho g_y^{-1}g_x
+f_yg_y^{-1}(g_y)_\rho g_y^{-1}g_x
-f_yg_y^{-1}(g_x)_\rho.
\end{aligned}
\]

所有项均应使用 total derivatives。R405/R446 的 `cond(g_y)≈1.14×10^6` 表明直接形成 inverse 风险较高；实现应使用带 pivoting 的 solve/SVD、报告 backward residual 和 reciprocal condition estimate。

## U5.5 ZOH 离散化与 Fréchet derivative

不要用 `A^{-1}(A_d-I)B`，因为 `A` 可含 gauge/近零模式。构造 augmented matrix

\[
\mathcal M=\begin{bmatrix}A_c&B_c&B_w\\0&0&0\\0&0&0\end{bmatrix}T_s,
\]

则

\[
\exp(\mathcal M)=
\begin{bmatrix}A_d&B_{c,d}&B_{w,d}\\0&I&0\\0&0&I\end{bmatrix}.
\]

用 matrix exponential 的 Fréchet derivative

\[
D\exp(\mathcal M)[\mathcal M_\rho]
\]

一次得到 `A_d,ρ,B_c,d,ρ,B_w,d,ρ`。SciPy `expm_frechet`、block-exponential identity 或 Schur–Parlett 均可；验证方式是与中心差分/complex-step（无 clipping 时）交叉检查。

## U5.6 headroom 与 controller derivative

若 power input 是

\[
B_{phys}(\rho)H(x_0,\mathrm{SOC},V,\rho)u_n,
\]

则

\[
(B_c)_\rho=(B_{phys})_\rho H+B_{phys}H_\rho.
\]

`H_ρ` 只有在固定 headroom active mode 内存在。若 `min/max/clamp` 的 active branch 改变，经典导数不存在，应报告 one-sided derivative、Clarke generalized derivative 或 mode-specific interval。

controller 若由状态空间 `(A_K,B_K,C_K,D_K)` 组成，最稳健的做法是先构造完整 closed-loop augmented matrix，再对该矩阵做 total derivative；不要分别对高阶 transfer polynomial 求系数差分。

## U5.7 稳定实现：线性求解与 adjoint

每个频点不显式求 inverse：

```text
Xc = solve(zI - A, Bc)
Xw = solve(zI - A, Bw)
Pc = C @ Xc + Dc
Pw = C @ Xw + Dw
S_Pw = solve(I + Pc @ K, Pw)              # G

Xc_rho = solve(zI - A, A_rho @ Xc + Bc_rho)
Xw_rho = solve(zI - A, A_rho @ Xw + Bw_rho)
Pc_rho = C_rho @ Xc + C @ Xc_rho + Dc_rho
Pw_rho = C_rho @ Xw + C @ Xw_rho + Dw_rho
L_rho = Pc_rho @ K + Pc @ K_rho
G_rho = solve(I + Pc @ K, Pw_rho - L_rho @ G)
```

对许多参数 `ρ`，可从标量 energy objective 反向构造 adjoint solves，避免每个参数重复完整求解。必须记录每个频点 `cond(zI-A)` 和 `cond(I+P_cK)`；接近奇异时，导数虽数学存在也可能数值不可靠。

## U5.8 为什么分项 attribution 坐标依赖

令 `x=T(ρ)\bar x`。变换后

\[
\bar A=T^{-1}AT,
\]

其导数为

\[
\bar A_\rho=T^{-1}A_\rho T
+T^{-1}AT_\rho-T^{-1}T_\rho T^{-1}AT.
\]

后两项是 similarity connection/commutator；它们可在 “A-term” 与 `B/C` terms 之间重新分配数值，而总 transfer derivative 不变。因此“候选变化主要来自 A”不是坐标不变命题。更安全的物理分解是依次冻结：

1. equilibrium shift；
2. physical plant port map；
3. controller realization；
4. headroom map；
5. reference denominator；

并将每个 block 定义为完整 I/O transfer counterfactual，而不是裸矩阵元素范数。

## U5.9 有限差分误差与当前不可用 interval

中心差分

\[
D_hF=\frac{F(\rho+h)-F(\rho-h)}{2h}
\]

在 `F∈C³` 且 active mode 固定时满足

\[
|D_hF-F'(\rho)|
\le\frac{h^2}{6}\sup_{|s-\rho|\le h}|F'''(s)|
+O\left(\frac{\epsilon_{mach}\,\mathrm{scale}(F)}{h}\right).
\]

用 `h,h/2` 做 Richardson：

\[
D_R=\frac{4D_{h/2}-D_h}{3},
\qquad
\widehat e=\frac{|D_{h/2}-D_h|}{3}.
\]

检查 `ρ±h` 的 equilibrium residual、active-mode hash 和 spectral branch 一致。若任一 mode 改变，不使用二阶 truncation 声明。

当前不能给 R405 reduced-model approximation interval，因为缺少：

- Jacobian entry error bounds；
- `g_y^{-1}` 的绝对 scale/singular-value bound；
- reduced-vs-nonlinear operator norm discrepancy；
- active-mode tube；
- finite-window remainder bound。

R450 的 5.38% 是**一个 zero-delay endpoint ratio seam**，不是 `||ΔA||`、`||ΔG||∞` 或统一 uncertainty norm，不能传播成所有频率/参数的 interval。

## U5.10 margin 与 failure-cause 边界

不能从 supplied data 得到 nominal gain margin、phase margin 或 robust stability margin。MIMO margin 至少需要：

1. 明确 loop break 和 normalization；
2. 全部 `ω∈[0,π/T_s]` 的 return ratio `L(e^{jω})`，而非 0.3–0.5 Hz 的 41 点；
3. open-loop unstable pole count/离散 Nyquist winding；
4. delay/plant uncertainty 的 operator-norm 或 structured uncertainty set；
5. gauge/neutral modes 的处理。

也不能给 unique failure cause：R449 已证明 A-only candidate/reference terms 为 mixed，且其他通道未计算。

## U5.11 最小新计算

导出完整 Object B sampled model 和连续 precursor；对 `ρ±h,±h/2`：重新解 equilibrium、记录 active modes、用 Fréchet derivative离散化、构造两种 controller closed loops、计算全频 `G,G_ρ` 和 finite-window energy。对 total derivative做中心差分/Richardson交叉验证。支持条件是 relative discrepancy 在预注册容差内且 active mode 不变；反驳是 mode switch、condition number 爆炸或 total derivative 与 direct finite difference 不一致。

## U5.12 论文安全措辞

**可写：**

> The sensitivity of the candidate-to-reference energy ratio contains equilibrium, plant input/output, discretization, controller, headroom, and reference-denominator terms. The previously reported state-matrix-only contributions are mixed and are not a coordinate-invariant causal attribution. A complete total derivative requires the exported sampled input/output model and fixed actuator mode.

**禁止写：**

- “M/D failure is caused by A_d alone”；
- “5.38% is a robust uncertainty bound”；
- “min return difference in 0.3–0.5 Hz is a phase margin”；
- “spectral radius summary proves stability”；
- “centered difference is accurate”而不检查 mode 与 conditioning。

**分类：algebraic identity。**

---

# U6 — 分数延迟与局部稳定/鲁棒裕度

## U6.1 结论

R450 的合法强结论仍是**端点退化曲线**：非线性 `r_d` 在 0、1、2 samples 分别为 `0.9389468, 0.9502788, 0.9893271`，因此在响应关于 delay 连续的假设下，`r_d=0.95` 至少有一个交点位于 `[0,0.2 s]`。线性插值给约 `0.19508 s`，但这只是 HYPOTHETICAL interpolation，不是测得阈值。

当前包不能计算第一 destabilizing delay，也不能给 phase/robust stability margin：只有局部频带 `L0(jω)`，没有全频 loop、连续 plant/ZOH split、完整 closed-loop realization、gauge-reduced pole set或 uncertainty norm。R450 的 `min σ(I+z^{-n}L0)>0` 只在扫描频带上成立，不是 Nyquist stability certificate。

## U6.2 与 `T_s=0.2 s` 一致的精确分数延迟

假设数字控制器每 `T_s` 更新，输出经 ZOH 保持，通信/执行延迟为

\[
\tau=mT_s+\delta,
\qquad m\in\mathbb Z_{\ge0},\quad0\le\delta<T_s.
\]

连续 plant

\[
\dot x=A_cx+B_cu_{del}(t)
\]

在第 `k` 个采样间隔中，前 `δ` 秒使用 `u_{k-m-1}`，后 `T_s−δ` 秒使用 `u_{k-m}`。精确 sampled update 是

\[
\boxed{
x_{k+1}=A_dx_k+B_1(\delta)u_{k-m-1}+B_0(\delta)u_{k-m},}
\]

其中

\[
A_d=e^{A_cT_s},
\]

\[
B_1(\delta)=\int_0^\delta e^{A_c(T_s-s)}B_c\,ds,
\qquad
B_0(\delta)=\int_\delta^{T_s}e^{A_c(T_s-s)}B_c\,ds.
\]

`δ=0` 时 `B_1=0,B_0=B_d`，退化为整数 `m` sample delay；`δ→T_s` 时转为 `m+1` sample delay。该构造是基于 ZOH 的 exact lifting，不需要 undocumented Padé。

如果只有离散频率响应，可以形式上乘 `e^{-jωτ}` 描述连续 sinusoid phase lag；但非整数 `z^{-τ/T_s}` 不是唯一的因果有限维离散 rational operator。没有 intersample model 时，不能用任意 Padé/Thiran realization 的极点当作项目稳定裕度。

## U6.3 第一 destabilizing delay 的正确计算

获得 `A_c,B_c`、controller realization 和 delay memory 后，对每个 `τ` 构造 augmented closed-loop matrix `A_cl(τ)`。由于系统可能含角度 gauge/控制器积分 neutral mode，先固定 gauge 或只在声明的 detectable/stabilizable quotient 上判稳定。

算法：

```text
for each interval tau in [m Ts, (m+1) Ts):
    compute B0(delta), B1(delta) by block exponential/Frechet-safe formulas
    assemble exact augmented A_cl(tau), including m+1 command memory blocks
    compute ordered Schur form/eigenpairs
    match branches to previous tau by eigenvalue distance + eigenvector MAC
    monitor log|lambda_j(tau)| for non-gauge branches
    when a simple branch changes sign around |lambda|=1:
        bisect/Brent solve log|lambda_j(tau)|=0
        verify eigen-residual and branch conditioning
```

对简单 eigenvalue，左右 eigenvectors `w,v` 归一化后

\[
\lambda'(\tau)=\frac{w^*A_{cl}'(\tau)v}{w^*v},
\qquad
\frac{d}{d\tau}\log|\lambda|
=\operatorname{Re}\frac{\lambda'}{\lambda}.
\]

必须报告 `|w*v|^{-1}`；接近 repeated/defective crossing 时，一阶 branch derivative 不可靠，应使用 invariant subspace/pseudospectral analysis。

建议证书条件：全频/全部非 gauge modes，eigen residual `≤1e-9||A||`，交点 bracket 宽度达到声明精度，且 crossing transversality 的 interval 不含 0。

## U6.4 三类“裕度”不可混写

1. **Nominal local stability delay margin**：第一非 gauge pole 穿越单位圆的 `τ_stab`；当前不可计算。
2. **Robust stability margin**：在指定结构化不确定性集合中所有 plant 都稳定的最大 `τ`；需要 small-gain/IQC/μ 等 uncertainty description；当前不可计算。
3. **Empirical nonlinear endpoint threshold**：有限 bank 上 `r_d(τ)=0.95` 的 crossing；它是性能阈值，不是 pole crossing。

R450 只支持第 3 类的粗 bracket。

## U6.5 5.38% seam discrepancy 的正确传播

R450 记录 zero-delay linear/nonlinear relative error `0.0538019`。非线性 zero-delay ratio 距 0.95 的相对余量只有

\[
(0.95-0.9389468)/0.9389468\approx1.177\%.
\]

所以该 seam 已大于 threshold margin，线性曲线不能单独判定 fractional endpoint crossing。更重要的是，该误差只在 `τ=0`、一个 scalar endpoint 上测得；没有证据表明

\[
|r_{nl}(\tau)-r_{lin}(\tau)|\le0.0538\,|r_{nl}(\tau)|
\]

对所有 `τ` 成立。即使把 5.38% 作为保守 uniform design assumption，也只能形成 endpoint uncertainty band，不能形成 stability uncertainty，因为它不是 return-ratio norm。

要做 robust stability，最少需要 `||W_2ΔW_1||∞≤1` 或 structured `Δ` 的频域界，并在全频验证 `μ<1`/small-gain；当前 scalar seam 不满足这一类型。

## U6.6 endpoint crossing 的最少新增点

已有符号：

\[
r_d(0)-0.95<0,
\qquad
r_d(0.2)-0.95>0.
\]

若只假设连续，不假设单调，新增一个 `τ=0.1 s` 点即可把“至少一个 crossing”定位到宽度 0.1 s 的某个子区间；每次二分都保留一个符号相反的区间。要把区间宽度压到 `η`，所需新增点数为

\[
\boxed{n=\left\lceil\log_2\frac{0.2}{\eta}\right\rceil.}
\]

例如：`η=0.05 s` 需 2 点，`0.025 s` 需 3 点，`0.01 s` 需 5 点，`0.005 s` 需 6 点。每个 fractional delay 点必须使用上面的 exact ZOH split 或实际 runtime fractional transport，不得用未声明 Padé。

若任何中点恰等于 0.95，交点已直接观测；若曲线不连续（例如 active-mode jump），IVT bracket 失效，应改报 mode boundary 和 one-sided values。

## U6.7 现有数据为何不足以计算极点 crossing

- R450 `band_rows` 只有 0.304–0.5 Hz 的 41 个 `L0` 矩阵；Nyquist 区间到 `2.5 Hz`，且需要 winding/open-loop poles；
- R447 只给 closed-loop spectral radius 标量，不能 branch track；
- exact sampled `A,B,C` 和 continuous precursor 未导出；
- 结构性 unit eigenvalue/gauge 未标记；
- 5.38% 不是 matrix uncertainty；
- `min return difference sigma` 在三个整数 delay、局部频带上为正，不排除其他频率的 encirclement/pole crossing。

## U6.8 最小新实验

**性能阈值最小实验**：运行 `τ=0.1 s` 非线性 point，随后按目标精度二分；每点复用相同 30 records，报告 `r_d,r_cross,guards,active-mode hash`。支持/refute 只针对 endpoint crossing bracket。

**稳定裕度最小计算**：导出 continuous/ZOH plant 与完整 controller，构造 fractional-delay augmented matrix，扫描和 branch-track 全部非 gauge poles；再以 nonlinear small perturbation 仅验证 crossing 附近局部 behavior。若没有 uncertainty set，只能报 nominal local margin。

## U6.9 论文安全措辞

**可写：**

> On the registered nonlinear bank, the differential-energy threshold of 0.95 is bracketed between zero and one 0.2-s sample delay, assuming continuity of the fractional-delay execution map. This is a finite-bank performance boundary. The available band-limited return-ratio data do not determine a pole-crossing, phase-margin, or robust-stability delay margin.

**禁止写：**

- “delay margin is 0.2 s”；
- “r_d=0.95 marks instability”；
- “positive min return difference on 0.3–0.5 Hz proves stability”；
- “5.38% seam is a robust model uncertainty”；
- 未声明 realization 的 Padé/Thiran 极点结论。

**分类：paper-grade proposition。**

---
# U7 — 零一阶之后的二阶/双线性 M/D authority

## U7.1 结论

R446 已在注册同步平衡点证明八个 M/D 命令的 reduced additive first-order columns 全为零：

\[
B_{u,r}=f_u-f_yg_y^{-1}g_u=0.
\]

这不等于“控制完全无效”。在固定光滑 active mode 下，M/D 调节改变 `1/M` 与 `D/M`，其首个非零局部作用是**状态依赖/扰动依赖的双线性项**。若 disturbance 幅值为 `ε`，策略在平衡点零偏置且局部 Lipschitz，则 `x=O(ε)`、`u=O(ε)`，由 M/D 造成的相对零动作响应差为 `O(ε²)`。additive energy-port 输入在通常的非退化通道上可在 `O(ε)` 起作用。因此可证明一个局部 order disadvantage；但没有导出的二阶 tensor、有限窗 lifted singular value 和统一 active-mode tube，不能给冻结模型上的数值比例，更不能推出全局 controller impossibility。

## U7.2 从 swing equation 得到双线性项

用偏差坐标 `ω=ω_0+\Delta\omega`。对四个 VSG，写成矩阵形式：

\[
M(u_M)\dot{\Delta\omega}
=r(x,y,w)-D(u_D)\Delta\omega,
\]

其中

\[
M(u_M)=M_0+\sum_{j=1}^4u_{M,j}M_j,
\qquad
D(u_D)=D_0+\sum_{j=1}^4u_{D,j}D_j.
\]

在同步平衡点 `r(0,0,0)=0, Δω=0`。Neumann 展开

\[
M(u_M)^{-1}
=M_0^{-1}
-M_0^{-1}\Delta M M_0^{-1}
+O(\|u_M\|^2).
\]

代入并保留一阶状态/扰动与一阶动作的乘积：

\[
\begin{aligned}
\dot{\Delta\omega}
={}&M_0^{-1}\bigl[r_xx+r_yy+r_ww-D_0\Delta\omega\bigr]\\
&-M_0^{-1}\Delta M M_0^{-1}
\bigl[r_xx+r_yy+r_ww-D_0\Delta\omega\bigr]\\
&-M_0^{-1}\Delta D\,\Delta\omega
+O(3).
\end{aligned}
\]

第二行是 inertia-command 与状态/扰动的双线性项；第三行是 damping-command 与速度偏差的双线性项。因为平衡点括号内残差为零且 `Δω=0`，对 `u` 的直接一阶偏导为零，与 R446 一致。

## U7.3 index-1 DAE 的一般形式

原系统：

\[
\dot x=f(x,y,u,w),\qquad0=g(x,y,u,w),\qquad y=h(x,u,w)
\]

其中 `g_y` 在固定 gauge/active mode 内可逆。隐函数导数为

\[
h_x=-g_y^{-1}g_x,
\qquad h_u=-g_y^{-1}g_u,
\qquad h_w=-g_y^{-1}g_w.
\]

定义 reduced vector field

\[
\bar f(x,u,w)=f(x,h(x,u,w),u,w).
\]

R446 已给出

\[
\bar f_u(0,0,0)=0.
\]

首个输入相关 tensor 为

\[
N_j=\frac{\partial^2\bar f}{\partial x\,\partial u_j}(0),
\qquad
E_j=\frac{\partial^2\bar f}{\partial w\,\partial u_j}(0).
\]

输出若依赖动作，也定义

\[
R_j=\frac{\partial^2\bar h_o}{\partial x\,\partial u_j}(0),
\qquad
S_j=\frac{\partial^2\bar h_o}{\partial w\,\partial u_j}(0).
\]

因此局部 reduced bilinear realization 为

\[
\boxed{
\dot x=Ax+B_ww+
\sum_{j=1}^{8}u_j(N_jx+E_jw)+R_3(x,u,w),}
\]

\[
\boxed{
y=Cx+D_ww+
\sum_{j=1}^{8}u_j(R_jx+S_jw)+H_3(x,u,w),}
\]

其中在 `C²/C³` 光滑和固定 mode 下，remainder 对总小量至少为三阶。`N_j,E_j` 应由 composite reduced map 的 implicit automatic differentiation 或混合有限差分直接得到，不能只对 `f_u` 的裸 DAE 行求差分。

## U7.4 二阶 Volterra 响应

令 disturbance 为 `w=ε\hat w`，零偏置反馈局部展开为

\[
u=Kx+Lw+O(\|(x,w)\|^2),
\qquad u(0,0)=0.
\]

令

\[
x=\epsilon x_1+\epsilon^2x_2+O(\epsilon^3).
\]

一阶项：

\[
\dot x_1=Ax_1+B_w\hat w,
\qquad
x_1(t)=\int_0^te^{A(t-s)}B_w\hat w(s)ds.
\]

动作一阶项 `u_1=Kx_1+L\hat w`。与 zero-action baseline 相比，控制诱导的二阶项满足

\[
\dot{\delta x}_2
=A\delta x_2+
\sum_j u_{1,j}(N_jx_1+E_j\hat w),
\]

故

\[
\boxed{
\delta y^{(2)}(t)=
C\int_0^te^{A(t-s)}
\sum_j u_{1,j}(s)
\left[N_jx_1(s)+E_j\hat w(s)\right]ds
+
\sum_j u_{1,j}(t)(R_jx_1(t)+S_j\hat w(t)).}
\]

这是首个 M/D feedback Volterra kernel。系统自身的 quadratic nonlinearities 也产生 `O(ε²)`，但在“同一 disturbance、同一 baseline，只切换零偏置 M/D feedback”的差分中，它们的共同部分应被分离；否则不能把全部二阶响应归因于 actuation。

## U7.5 `O(ε²)` 成立和失效的条件

### 成立条件

1. equilibrium 与 DAE active mode 固定；
2. `f,g,output,headroom,policy` 在邻域内至少 `C²`；
3. policy 零偏置，且 `||u||≤K(||x||+||w||)`；
4. disturbance family 按 `ε` 线性缩放；
5. horizon 固定，局部解存在且保持在 Taylor tube；
6. initial condition 不随控制 arm 产生 `O(ε)` 差异。

则

\[
\|y_{MD}(\epsilon)-y_0(\epsilon)\|=O(\epsilon^2).
\]

### 可能变成 `O(ε)` 或无 Taylor 标度

- policy 有非零平衡偏置 `u_0`：它把 `A` 改成 `A+Σu_{0,j}N_j`，对 disturbance 的差是 `O(ε)`；
- clamp/slew/headroom 在 `ε→0` 附近切 mode；
- deadband、sign、relay、事件触发、保护逻辑不光滑；
- `g_y` 失去可逆性或接近 singular bifurcation；
- horizon 随 `1/ε` 增长，secular accumulation 破坏固定窗标度；
- additive disturbance 本身触发离散 topology/limit event。

所以 `O(ε²)` 是局部 fixed-mode 命题，不应写成任意扰动下的全局弱 authority。

## U7.6 有限窗 reachability/energy bound

连续时间下，令 convolution operator

\[
(\mathcal T_Aq)(t)=\int_0^te^{A(t-s)}q(s)ds,
\]

其有限窗 `L2→L2` 增益为 `||T_A||_{2,T}`。定义

\[
\bar N=\left(\sum_j\|N_j\|_2^2\right)^{1/2},
\quad
\bar E=\left(\sum_j\|E_j\|_2^2\right)^{1/2},
\quad
\|u\|_\infty\le\bar u.
\]

忽略高阶 remainder 时：

\[
\|\delta x\|_{2,T}
\le\|\mathcal T_A\|_{2,T}\,
\bar u\left(\bar N\|x\|_{2,T}+\bar E\|w\|_{2,T}\right).
\]

输出：

\[
\boxed{
\|\delta y\|_{2,T}
\le
\left(\|C\|\|\mathcal T_A\|_{2,T}+\bar R\right)
\bar u\bar N\|x\|_{2,T}
+
\left(\|C\|\|\mathcal T_A\|_{2,T}+\bar S\right)
\bar u\bar E\|w\|_{2,T}.}
\]

registered normalized amplitude bound 可取 `\bar u≤1`，slew 每 sample 0.25 进一步限制可达 action sequence；但仅用 `\bar u=1` 是全幅局部上界，不自动产生 `ε²`。对零偏置 feedback，`\bar u≤K_uε` 且 `||x||,||w||=O(ε)`，右端即 `O(ε²)`。

离散 30-step 窗口可直接构造 bilinear lifted recursion：

\[
x_{k+1}=A_dx_k+B_dw_k+\sum_ju_{j,k}(N_{j,d}x_k+E_{j,d}w_k),
\]

在注册 amplitude/slew polytope 上用 interval/convex relaxation 计算上界；若需要 exact finite family，可穷举 R439/R452 schedule sequence。

## U7.7 与 additive energy-port 的局部定量比较

additive port 的一阶 lifted map记为

\[
y_p^{(1)}=\mathcal H_pu_p.
\]

若在声明 disturbance/action subspace 上

\[
\sigma_{min}(\mathcal H_p)\ge\underline\sigma_p>0,
\]

且 M/D 二阶输出满足 `||δy_MD||≤C_MD ε²`，而 additive command `||u_p||=c_pε`，则

\[
\frac{\|\delta y_{MD}\|}{\|y_p^{(1)}\|}
\le
\frac{C_{MD}}{\underline\sigma_pc_p}\epsilon.
\]

因此比值随 `ε→0` 至少线性趋零。这是可发表的局部 order comparison，但当前包没有：

- `N_j,E_j,R_j,S_j`；
- additive lifted map `H_p`；
- `σ_min(H_p)`；
- fixed-mode radius/remainder constant；
- 相同 actuator normalization 下的 admissible command scaling。

所以不能给冻结模型的数值 disadvantage，也不能把 Object A 与 Object B 的现有 endpoint ratios 直接相除。

## U7.8 收敛的 tensor probe

对任意状态方向 `v` 和动作基向量 `e_j`，mixed derivative-vector product：

\[
N_jv\approx
\frac{
\bar f(hv,+\eta e_j,0)-
\bar f(hv,-\eta e_j,0)-
\bar f(-hv,+\eta e_j,0)+
\bar f(-hv,-\eta e_j,0)
}{4h\eta}.
\]

对 disturbance 方向 `d`：

\[
E_jd\approx
\frac{
\bar f(0,+\eta e_j,hd)-
\bar f(0,-\eta e_j,hd)-
\bar f(0,+\eta e_j,-hd)+
\bar f(0,-\eta e_j,-hd)
}{4h\eta}.
\]

机械合同：

1. 使用至少三组 `(h,η)`，同时减半；
2. 四个角点分别解 algebraic equations，报告 `||g||∞`；
3. 检查 active-mode hash 完全相同；
4. 用 solve/SVD，不形成 `g_y^{-1}`；
5. 比较 Richardson extrapolation，预期光滑中心格式误差约四分之一；
6. 用随机 `v,d` 与 canonical basis，检查 tensor symmetry/linearity；
7. 将自动微分的 implicit Hessian-vector product 与 finite difference 交叉核验；
8. 若 cancellation 后数值接近 machine precision，提高精度而非宣称零 tensor。

R446 的 `cond(g_y)≈1.143819×10^6` 要求特别报告 backward error。建议 acceptance：DAE residual `≤1e-9`、不同 step extrapolated tensor 相对差 `≤1%` 或绝对低于预注册 materiality；这些是新实验容差，不是现有证据。

## U7.9 最小新实验

在 R446 同一 equilibrium：

1. 对八个动作、选定的 reduced state/disturbance basis 运行 mixed tensor probe；
2. 构造 30-step bilinear lifted map；
3. 对 disturbance amplitudes `ε,ε/2,ε/4` 运行零动作与零偏置 M/D feedback；
4. 计算 `||Δy||/ε²` 是否收敛到有限非零常数，以及 `||Δy||/ε` 是否趋零；
5. 同时运行 additive energy-port 小信号 command，检查其 `||Δy||/ε` 是否趋有限非零；
6. 全程记录 active modes。

**支持**：M/D normalized quadratic slope 稳定、线性 slope 趋零，additive linear slope 非零。  
**反驳**：M/D 线性 slope 非零且不是数值/偏置；或 mode 在缩小 `ε` 时仍切换，说明 fixed-mode expansion 不适用。

## U7.10 论文安全措辞

**可写：**

> At the registered synchronous equilibrium, direct M/D commands have zero additive first-order reduced-state columns. Under a fixed smooth DAE mode and a zero-bias Lipschitz feedback law, their leading disturbance-dependent authority is bilinear, so the controlled-minus-zero-action response is second order in disturbance amplitude over a fixed local horizon. A quantitative comparison with additive power actuation requires the mixed derivative tensors and the additive port's lifted singular values.

**禁止写：**

- “M/D control has no authority”；
- “all M/D controllers are inferior”；
- “zero first-order B column proves global impossibility”；
- 把不同 actuator/reference/bank 的现有 ratios 直接组成 causal effect；
- 在 mode switch 下声称 `O(ε²)`。

**分类：paper-grade proposition。**

---

# U8 — 异质性与 DAE/network asymmetry 下的近似共模/差模分离

## U8.1 结论

可以给出两类有效界：

1. 一般线性系统的 **commutator-resolvent 上界**：cross transfer 由 common projector 与 dynamics 的不对易程度、输入/输出 misalignment 和 resolvent conditioning 共同控制；
2. swing dynamic-stiffness 模型的 **Schur-complement 精确表达和条件上/下界**。

仅用 M/D heterogeneity 数值不能给非平凡统一 bound：大异质性可因整体 inertia/damping scale、短窗口或输出 rank 而产生任意小 cross energy；很小异质性可在近共振/重复模态处因 resolvent 爆大而产生巨大 cross transfer。因此论文不能暗示 universal Bode/product trade-off。

## U8.2 一般 commutator identity

令状态空间 common projector `P`，`Q=I-P`，resolvent

\[
R(s)=(sI-A)^{-1}.
\]

由 inverse commutator identity：

\[
[R,P]=R[A,P]R.
\]

又因 `QPP=0`：

\[
\boxed{
QRP=QR[A,P]RP.}
\]

故

\[
\boxed{
\|QRP\|_2
\le\|QR\|_2\,\|[A,P]\|_2\,\|RP\|_2
\le\|R\|_2^2\epsilon_A,}
\]

其中 `ε_A=||[A,P]||₂`。这解释了两项缺一不可：结构 asymmetry 小，且 resolvent 不能在目标频率病态。

## U8.3 含输入/输出 misalignment 的上界

设状态 common/differential projectors 为 `P_x,Q_x`，输入为 `P_u`，输出 differential projector 为 `Q_y`。定义

\[
\epsilon_A=\|[A,P_x]\|,
\quad
\epsilon_B=\|Q_xBP_u\|,
\quad
\epsilon_C=\|Q_yCP_x\|,
\quad
\epsilon_D=\|Q_yDP_u\|.
\]

cross transfer

\[
G_{dc}=Q_y\left[C(sI-A)^{-1}B+D\right]P_u.
\]

把 `BP_u=P_xBP_u+Q_xBP_u` 分解，并在 common-aligned 部分使用 commutator identity，可得保守界

\[
\boxed{
\begin{aligned}
\|G_{dc}\|
\le{}&\epsilon_D
+\epsilon_C\|R\|\|P_xBP_u\|\\
&+\|Q_yCQ_x\|\|R\|^2\epsilon_A\|P_xBP_u\|\\
&+\|Q_yC\|\|R\|\epsilon_B.
\end{aligned}}
\]

若输入/输出严格 projector-compatible，`ε_B=ε_C=ε_D=0`，只剩由 `||Q_yCQ_x||·||R||²·ε_A·||P_xBP_u||` 控制的项。

## U8.4 swing dynamic stiffness 的精确 cross block

对二阶 reduced swing model：

\[
M\ddot\theta+D\dot\theta+\omega_nL\theta=Bp,
\]

定义

\[
Z(s)=s^2M+sD+\omega_nL.
\]

取 orthonormal common/differential basis `T=[q_c,T_d^T]`，其中 `q_c=1_4/2`，包内 manuscript 的 `T_d` 为三行差模基。变换后

\[
\widetilde Z=T^TZT=
\begin{bmatrix}
z_{cc}&z_{cd}\\
z_{dc}&Z_{dd}
\end{bmatrix}.
\]

若 `Z_dd` 和 common Schur complement

\[
S_c=z_{cc}-z_{cd}Z_{dd}^{-1}z_{dc}
\]

可逆，则 block inverse 给出

\[
\boxed{(Z^{-1})_{dc}=-Z_{dd}^{-1}z_{dc}S_c^{-1}.}
\]

对 common power input 到 differential frequency `ω=sθ`，若 input/output 完全对齐：

\[
G_{dc}(s)=-sZ_{dd}^{-1}z_{dc}S_c^{-1}b_c.
\]

因此

\[
\boxed{
\frac{|s|\,|b_c|\,\|z_{dc}\|}{\|Z_{dd}\|\,|S_c|}
\le\|G_{dc}(s)\|
\le
\frac{|s|\,|b_c|\,\|Z_{dd}^{-1}\|\,\|z_{dc}\|}{|S_c|}.}
\]

下界需要观测完整 differential vector、common input scalar不被额外投影消去；一般低秩输出下界可为零。

## U8.5 M/D heterogeneity 的显式量

若 `Lq_c=0` 且网络在 common/differential 坐标中 balanced，则

\[
z_{dc}=s^2T_dMq_c+sT_dDq_c.
\]

在 `s=jω`、实对角 `M,D` 下，一项为实、一项为纯虚，故

\[
\boxed{
\|z_{dc}(j\omega)\|_2^2
=\omega^4\delta_M^2+\omega^2\delta_D^2,}
\]

其中

\[
\delta_M=\|T_dMq_c\|_2,
\qquad
\delta_D=\|T_dDq_c\|_2.
\]

对四个 diagonal entries，这两个量正好等于 population standard deviation：

\[
\delta_M=\sqrt{\frac14\sum_i(M_i-\bar M)^2},
\qquad
\delta_D=\sqrt{\frac14\sum_i(D_i-\bar D)^2}.
\]

随附脚本从 R405 `baseline_m0/baseline_d0` 复算：

| profile | `δ_M` | `CV_M` | `δ_D` | `CV_D` |
|---|---:|---:|---:|---:|
| canary_dev_a | 41.2311 | 0.2062 | 31.6228 | 0.3162 |
| canary_dev_b | 41.2311 | 0.2062 | 31.6228 | 0.3162 |
| canary_dev_c | 29.1548 | 0.1458 | 22.3607 | 0.2236 |
| canary_dev_d | 29.1548 | 0.1458 | 22.3607 | 0.2236 |
| canary_eval_a | 43.3013 | 0.2112 | 38.4057 | 0.3658 |
| canary_eval_b | 43.3013 | 0.2112 | 38.4057 | 0.3658 |
| canary_eval_c | 33.5410 | 0.1720 | 28.6138 | 0.3093 |
| canary_eval_d | 43.3013 | 0.2112 | 36.0555 | 0.3606 |

这些只确定 `z_dc` 的 heterogeneity numerator；包内没有 `Z_dd,S_c,b_c` 的可核验频率矩阵，所以不能从表中计算 cross-transfer 数值界。

## U8.6 有限窗离散 bound

离散系统 Markov parameter `H_k=CA^{k-1}B`。identity

\[
[A^k,P]=\sum_{j=0}^{k-1}A^j[A,P]A^{k-1-j}
\]

给出

\[
\|[A^k,P]\|
\le k\|A\|^{k-1}\epsilon_A.
\]

若 I/O 完全 aligned，并以 `H_\ell=CA^\ell B`（`\ell=0,1,…`）编号，则

\[
\|Q_yH_\ell P_u\|
\le\|Q_yCQ_x\|\,\|P_xBP_u\|\,\epsilon_A
\sum_{j=0}^{\ell-1}\|A^j\|\,\|A^{\ell-1-j}\|,
\]

其中 `\ell=0` 的 cross block 为 0；若只用谱范数粗化，可再以 `\ell\|A\|^{\ell-1}` 上界该求和。

对有限输入 `u_0,…,u_{N-1}`，可由 block Toeplitz lift `\mathcal H_{dc,N}` 得

\[
E_{dc,N}=\|W^{1/2}\mathcal H_{dc,N}u\|_2^2
\le\|W^{1/2}\mathcal H_{dc,N}\|_2^2\|u\|_2^2,
\]

并用上述每个 block 的 bound 形成显式上界。若 `||A||>1`，该粗界很快变松；更紧实现应使用 ordered Schur/resolvent 或直接 block-Toeplitz singular values。

## U8.7 singular frequency 与 repeated mode

下列条件使 bound 失效或极松：

- `S_c(jω)` 接近 0：common resonance；
- `σ_min(Z_dd(jω))` 接近 0：differential resonance；
- repeated/defective modes 使 resolvent/pseudospectrum 远大于 eigenvalue distance；
- `g_y` 近 singular，DAE Schur complement 放大网络 asymmetry；
- output rank 低，使下界被投影 annihilate；
- direct feedthrough cross block 未计入；
- projector 与实际 inertia-weighted common coordinate 不匹配。

因此报告 heterogeneity 时必须同时报告 conditioning factor；单独 `CV_M/CV_D` 不是 cross-energy predictor。

## U8.8 从 ODE 扩展到 index-1 DAE

DAE 线性化：

\[
\begin{bmatrix}\dot x\\0\end{bmatrix}
=
\begin{bmatrix}f_x&f_y\\g_x&g_y\end{bmatrix}
\begin{bmatrix}x\\y\end{bmatrix}
+
\begin{bmatrix}f_u\\g_u\end{bmatrix}u.
\]

在 `g_y` uniformly invertible 且 active mode 固定时：

\[
A_r=f_x-f_yg_y^{-1}g_x,
\qquad
B_r=f_u-f_yg_y^{-1}g_u.
\]

输出若为 `o=h_xx+h_yy+h_uu`：

\[
C_r=h_x-h_yg_y^{-1}g_x,
\qquad
D_r=h_u-h_yg_y^{-1}g_u.
\]

把 `A_r,B_r,C_r,D_r` 代入 U8.2–U8.6 即可。扩展成立的必要审计项：

1. common/differential projector 作用于明确的 reduced frequency coordinates；
2. `g_y^{-1}` 在整个 profile tube 上有 singular-value 下界；
3. algebraic input/output leakage 纳入 `ε_B,ε_C,ε_D`；
4. network asymmetry 在 Schur reduction 后重算，不能只看原始 Laplacian；
5. gauge 被固定。

R405 只给 `cond(g_y)`，没有统一 `σ_min(g_y)` 与 perturbation norm，故不能形成 numerical DAE robustness bound。

## U8.9 两个反例

### 大异质性、任意小有限窗 cross energy

取固定相对异质的 `M_0,D_0`，令

\[
M=cM_0,\qquad D=cD_0,
\]

`CV_M,CV_D` 保持不变，绝对标准差随 `c` 增大；对固定非零频率和固定网络 `L`，

\[
Z^{-1}(jω)=
\left[c(-ω^2M_0+jωD_0)+\omega_nL\right]^{-1}=O(c^{-1}).
\]

所以 `G_dc=jωZ^{-1}B=O(c^{-1})`，有限窗 cross energy 可趋 0，尽管异质性很大。低秩输出 annihilation 还可使 cross energy 精确为 0。

### 小异质性、巨大 cross response

考虑稳定二阶 resolvent block

\[
A_\epsilon=
\begin{bmatrix}-\delta&\epsilon\\0&-\delta\end{bmatrix},
\]

common-to-differential cross at `s=0` 量级为 `ε/δ²`。令 `ε=δ^{3/2}`，则 asymmetry `ε→0`，但 cross transfer `1/\sqrt\delta→∞`。根因是 repeated/near-resonant conditioning，而不是 heterogeneity 本身。

两例证明：没有 resolvent/Schur conditioning 和 I/O rank，不能从 heterogeneity 单独推导非平凡双边 bound。

## U8.10 最小新计算

对每个 R405 profile 导出 gauge-fixed reduced `A_r,B_r,C_r,D_r`：

1. 构造 `P_c,P_d` 并计算 `ε_A,ε_B,ε_C,ε_D`；
2. 在注册 6 s finite window 构造 exact cross Toeplitz lift，算 `||H_dc||₂` 和 energy；
3. 扫描 0–Nyquist，计算 `||R||,σ_min(Z_dd),|S_c|`；
4. 比较 commutator upper bound 与实际 cross transfer；
5. 对 homogeneous projection 和小 perturbation 做 first-order scaling；
6. 检查 DAE `g_y` singular values 与 active mode。

**支持**：cross response 随 `ε_A` 在 conditioning 有界区间内按界缩放。  
**反驳**：bound 被实际值突破（说明漏了 I/O/direct/algebraic leakage）或 conditioning 接近 singular，使 bound 无信息。

## U8.11 论文安全措辞

**可写：**

> Approximate common/differential separation is controlled jointly by projector commutators, input/output alignment, and resolvent conditioning. In the balanced swing reduction, M/D heterogeneity enters the off-diagonal dynamic-stiffness block explicitly, but it does not alone bound finite-window cross energy. Near resonances or algebraic singularities can amplify arbitrarily small asymmetry, while large heterogeneity can yield small cross energy under weakly responsive scaling or output projection.

**禁止写：**

- “heterogeneity necessarily increases cross energy”；
- “homogenization always improves decoupling”；
- “存在 universal Bode/product lower bound”；
- “CV_M/CV_D 足以预测 endpoint”；
- 将 exact homogeneous Proposition 1 无条件延伸到 DAE/不平衡网络。

**分类：paper-grade proposition。**

---

# U9 — R458 dev-selection / eval-transfer 的无 laundering 解释

## U9.1 结论

R458 的选择规则在代码中与计划一致：只用 `dev_a/dev_b`，先选在两个 dev 都 guard-clean 的候选；否则选只在一个 dev guard-clean 的候选；若一个都没有，则选七个 guard 中最坏 violation 最小的 fallback。评估阶段只运行这一条 winner 于 `eval_a..d`。

这一设计消除了“在 eval 350 条里看结果后再挑 winner”的直接 selection-on-evaluation，但仍有**development multiple comparison**：winner 的 dev improvement 是 350 条最大化后的乐观样本内值，不能作为无偏效果或 p-value。eval 结果是一个冻结 schedule 在四个固定 profiles 上的有限库事实；没有随机 profile sampling model 时，`k/4` 不是 transfer probability，也没有 distribution-free confidence interval。

## U9.2 冻结 lexicographic rule 的代码级核验

`run_r458_dev_select_eval_validate.py` 对每个 candidate 汇总：

- `feasible_count`：在两个 dev profiles 上 `joint_guard_feasible` 的数量；
- `improvement_sum`：只对可行 dev profile 累加两个 endpoint improvements；
- `worst_margin`：所有 dev profiles、七个 relative guards 的最大 violation；负值表示均满足。

选择：

\[
\text{P1 pool}=\{c: feasible\_count=2\},
\]

若非空，按 `(-improvement_sum, global_index)` 排序；

\[
\text{P2 pool}=\{c: feasible\_count=1\},
\]

若 P1 空而 P2 非空，按 `(-feasible_count,-improvement_sum,global_index)` 排序；

否则 P3 在全部候选中按 `(worst_margin,global_index)` 排序。

注意 P2 中 `feasible_count` 都等于 1，所以第一排序项形式上冗余但不改变规则。P3 的 `worst_margin` 包含 endpoint、common、action 和 saturation 共 8 个字典键吗？代码 `_guard_margin` 实际返回 endpoint_d、endpoint_x、common_frequency、worst_peak、rocof、action_rms、action_tv、saturation，共 **8 个 scalar margins**；计划文字称“7 个相对 guard”，其含义是七类判据中 endpoint 类含两个分量。正式报告应按代码列出八个 scalar residual，避免计数歧义。

Gate：

- branch 3：无论 eval 结果，`FALLBACK-NO-WITNESS`；
- branch 1/2 且 transfer count≥1：`GUARD-CLEAN-TRANSFER`；
- branch 1/2 且 count=0：`NO-GUARD-CLEAN-TRANSFER`；
- integrity failure：`CANARY-INVALID`。

## U9.3 development multiple comparison 的准确影响

350 candidates 在 dev 上被比较，winner 的

\[
\max_c \sum_{p\in dev} improvement_{c,p}
\]

具有 winner's curse。即使每条 schedule 的真实效果相同，最大样本内值也偏高。该偏差影响：

- winner 的 dev improvement magnitude；
- dev feasibility count 的选择稳定性；
- 任何基于 dev 的 nominal p-value/CI。

它**不**污染冻结 winner 在未读取 eval 时的 deterministic eval pass/fail；因此无需为“固定四 profile 的存在性事实”做多重比较校正。但如果团队查看 eval 后改 selection rule、阈值、grid 或再次选 winner，则 eval 也被用于选择，原 gate 失效。

另一个隐含层面是候选 family 本身由历史研究设计产生；所有结论都应条件于“冻结的 350 schedule class”，不能升级为任意 piecewise controller。

## U9.4 15 个分支的精确解释

### Priority 1：winner 在 dev_a 和 dev_b 都 guard-clean

| eval transfer count | gate | 能建立什么 | 不能建立什么 |
|---:|---|---|---|
| 0 | NO-GUARD-CLEAN-TRANSFER | 该 350 类中存在一条两-dev witness，但它在四个固定 eval profiles 全部失败 | 不证明类整体不泛化，更不证明任意控制器不可能 |
| 1 | GUARD-CLEAN-TRANSFER | 同一预选 schedule 在两个 dev 和恰一个固定 eval profile guard-clean | 不给 transfer probability 或 topology generalization |
| 2 | GUARD-CLEAN-TRANSFER | 在两个 dev 和两个固定 eval profiles guard-clean | 同上 |
| 3 | GUARD-CLEAN-TRANSFER | 在两个 dev 和三个固定 eval profiles guard-clean | 同上 |
| 4 | GUARD-CLEAN-TRANSFER | 最强 finite-bank witness：在两个 dev 与全部四个固定 eval profiles guard-clean | 仍不是任意 profile、分布、拓扑或稳定性证明 |

### Priority 2：没有双-dev witness，winner 只在一个 dev guard-clean

| eval transfer count | gate | 能建立什么 | 限制 |
|---:|---|---|---|
| 0 | NO-GUARD-CLEAN-TRANSFER | 一条单-dev witness，四个 eval 全失败 | development robustness 已较弱；不推类不可行 |
| 1 | GUARD-CLEAN-TRANSFER | 单-dev 选出的 schedule 在一个固定 eval profile guard-clean | 有限库 partial transfer |
| 2 | GUARD-CLEAN-TRANSFER | 在两个固定 eval profiles guard-clean | 同上 |
| 3 | GUARD-CLEAN-TRANSFER | 在三个固定 eval profiles guard-clean | 同上 |
| 4 | GUARD-CLEAN-TRANSFER | 在全部四个固定 eval profiles guard-clean，尽管另一 dev profile 不通过 | 不能隐去 dev failure；不称“development-robust” |

### Priority 3：两个 dev 上均无 guard-clean candidate

| eval transfer count | gate | 能建立什么 | 正确措辞 |
|---:|---|---|---|
| 0 | FALLBACK-NO-WITNESS | 冻结 class 在 dev 无 witness，fallback 在四 eval 也均失败 | “no development witness in the 350-schedule class” |
| 1 | FALLBACK-NO-WITNESS | fallback 偶然/描述性地在一个固定 eval profile pass | 不称 guard-clean transfer witness |
| 2 | FALLBACK-NO-WITNESS | 描述性 pass 两个 eval profiles | 同上 |
| 3 | FALLBACK-NO-WITNESS | 描述性 pass 三个 eval profiles | 同上 |
| 4 | FALLBACK-NO-WITNESS | fallback 在四 eval 都 pass，但两个 dev 均不 pass | 报“eval-bank passes of a development-infeasible fallback”；gate 不升级 |

P3 的 eval pass 仍是客观 finite-bank observation，但它不回答预注册的“从 guard-clean development witness 转移”问题，因此 gate 坚持 fallback。

## U9.5 有效分析单位与四 profile 的统计边界

R458 不训练；schedule 是唯一固定 intervention。每个 profile 的六个 signed scenarios 被算法汇总成一个 guard 判定。它们是同一 profile metric 的组成部分，不是独立 transfer replicates。因而报告单位是：

\[
K=\sum_{p\in\{eval_a,b,c,d\}}
\mathbf1\{winner\ guard\mbox{-}clean\ on\ p\}.
\]

这些 profiles 是预先固定而非从明确总体 iid 抽样，所以最强结果是 `K of 4 fixed profiles`。不存在 distribution-free lower confidence bound；也不能把 `K/4` 称为估计的泛化概率。

若**额外假设**四 profiles 是某个分布的 iid exchangeable samples，才可计算 binomial interval。95% Clopper–Pearson 区间会非常宽：

| K/4 | 假设 iid 后的 95% CP 区间（仅示意，当前设计不授权） |
|---:|---:|
| 0/4 | [0, 0.6024] |
| 1/4 | [0.0063, 0.8059] |
| 2/4 | [0.0676, 0.9324] |
| 3/4 | [0.1941, 0.9937] |
| 4/4 | [0.3976, 1] |

即使 4/4，在 iid 假设下下界也只有约 0.398；这进一步说明不能从四个固定 profiles 宣称高 transfer probability。

## U9.6 为什么只是 finite-bank witness

成功分支只证明：

1. winner 属于冻结 350 schedule family；
2. selection 只读两个固定 dev profiles；
3. 同一 winner 在 `K` 个固定 eval profiles 上满足 R452 exact guards；
4. 执行对象、拓扑、estimator、horizon、action map 与 R458 frozen contract 相同。

它不覆盖：

- 350 类之外的 controller；
- 随机 profile distribution；
- 新 topology 或 grid strength；
- learner 可否训练出该 schedule；
- local/global stability；
- HIL/EMT/deployment safety；
- Object B 或其他 actuator。

## U9.7 未来可量化 transfer probability 的设计

保持 R458 gate 不变，另开 successor experiment：

1. 事先定义 profile generator `D`：参数范围、相关性、固定 topology 或 topology strata、扰动 bank、active-mode admissibility；
2. 用独立 RNG 生成并永久冻结 `m_dev` 和 `m_test` profiles；
3. 只在 dev 上选择 schedule/hyperparameters；test 只运行一次；
4. 每个 test profile 产生一个预注册 binary success；
5. 在 iid/exchangeability 假设下用 exact binomial lower bound；若 profile 有 strata，用分层估计或最坏 strata bound；
6. 根据目标 `p0` 和置信度预先做样本量设计；
7. 若需要 topology generalization，必须从 topology distribution 独立采样，不能只改变参数。

还可使用多个独立 bank replicates 做 nested selection-evaluation：每个 outer split 内重新只用 dev 选择，outer test 永不参与调参。有效独立单位仍是 outer profile/bank，而不是 trajectory。

## U9.8 机械核验

随附脚本输出 branch×count 的 verdict table。正式 R458 完成后，应检查：

```text
selection.json hash exists
selection reads only dev shard hashes
winner candidate_id occurs once in frozen candidate sequence
priority branch recomputes exactly from all 350 dev rows
all four eval files contain only static + same winner
transfer_count equals number of eval joint_guard_feasible == true
branch/verdict mapping matches code
no result file or threshold timestamp predates/follows an unauthorized reselection
```

支持 selection integrity 的 observables 是 `candidate_sequence_sha256`、`selection_sha256`、winner global index、dev/eval trajectory counts 和 per-profile exact guards。任何 eval-informed rerun、winner mismatch 或 threshold drift 都使 causal transfer interpretation invalid。

## U9.9 论文安全措辞

**可写：**

> One schedule was selected from the frozen 350-member family using only two development profiles and was then evaluated once on four fixed evaluation profiles. A passing result is a guard-clean transfer witness for that schedule on the reported finite bank. Because the evaluation profiles are fixed rather than sampled from a declared population, the transfer count does not estimate a distributional success probability or support topology generalization.

**禁止写：**

- “out-of-sample success rate = K/4”作为总体概率；
- “R458 proves the controller class is feasible/infeasible”；
- “4/4 proves robust generalization”；
- 隐去 priority-2 的 dev failure；
- 把 priority-3 的 eval pass 改写成预注册 guard-clean transfer witness；
- 读 eval 后修改 selection rule 再沿用原 gate。

**分类：paper-grade proposition。**

---

# 证据路径与仍缺量总表

| U | 使用的主要仓库路径/字段 | 仍缺量 |
|---|---|---|
| U1 | R405 `linearization_matrices.json::{f_x,f_y,g_x,g_y}`；R447 dimensions/energy ratio；R450 `band_rows`；`c1_youlas_sls_certificate.md` | Object B 完整 sampled I/O matrices、DCF/SLS、FIR sealed bound、lift、primal/dual、nonlinear mode bound |
| U2 | R451 `algorithm_audit.json` 四项 fatal/high findings；R410/R431/R438 只作背景 | 新实验 outcomes；global policy optima；足量 independent training seeds |
| U3 | `src/.../agents/cd_matd3.py::{project_slew_torch,_SlewAwareReplayRing,_target_actions}`；R451 audit raw/executed finding | 历史 raw replay traces 与 Lipschitz constants，故无数值 bias |
| U4 | `cd_matd3_canary.py::reward_contract`；R452 `candidate_guard` 和四个 profile static refs；R456 gradient conflict | neural policy class global phase-I certificate；所有 train/eval per-seed traces |
| U5 | R405 DAE Jacobians；R447/R449/R450 summaries | 完整 A/B/C/D 及 derivatives、equilibrium manifold、headroom modes、全频 loop、model error norm |
| U6 | R450 nonlinear ratios、sample period、band L0、min return difference、5.38% seam | continuous/ZOH precursor、full loop、pole branches、uncertainty set、fractional nonlinear points |
| U7 | R446 exact zero columns、h-grid、`cond(g_y)` | mixed second derivatives、bilinear lift、additive port singular values、fixed-mode radius/remainder |
| U8 | manuscript projectors/Proposition 1；R405 M/D profiles、DAE Jacobians | reduced A/B/C/D、network asymmetry matrices、resolvent/Schur conditioning、output rank |
| U9 | R458 `plan.md`；`run_r458...py::{_guard_margin,select,classification}`；R452 thresholds；R453 finite-grid counts | R458 尚未产生任何 outcome；profile sampling distribution不存在 |

---

# 一页式最终表

| ID | 类型 | headline result | 置信度 | 什么会反驳/改变结论 |
|---|---|---|---|---|
| U1 | paper-grade proposition | 现包无法识别任何 FIR-Youla/SLS primal/dual certificate；给出精确 10-tap 类与 SOCP/MISOCP 边界 | 高 | 导出完整模型、DCF/lift 并产生可独立核验 witness 或正 dual bound |
| U2 | paper-grade proposition | 3×3×2 因子与 bijective donor placebo 可分离 semantic effect 和 dimension/finite-learning effect；population value仍需优化 gap | 高 | placebo marginal hash不等、donor 与目标轨迹相关、reward/access 未正交、优化 gap 有独立相反证据 |
| U3 | algebraic identity | 最小 Markov state 含 previous executed action；省略它会产生同 `(x,u)` 两个转移 | 很高 | projector 实际无状态，或环境已经把全部 projector state 纳入 `x` 且 raw语义全程一致 |
| U4 | paper-grade proposition | 当前 expected common quadratic constraint 不是 registered guard set 的内近似 | 很高 | 训练约束改为 exact逐 profile全部 guard，或证明一个覆盖所有 guard 的充分 bound |
| U5 | algebraic identity | total sensitivity 必须含 A/B/C/D、equilibrium、discretization、controller、headroom、denominator；分项归因坐标依赖 | 很高 | 完整导数重算显示某物理端口 counterfactual 在坐标不变定义下独占全部作用 |
| U6 | paper-grade proposition | `r_d=0.95` 只被 bracket 在 0–0.2 s；无稳定裕度可识别 | 高 | 完整 fractional-delay realization + 全 pole branch tracking 给出 crossing；新增 nonlinear points收窄 endpoint bracket |
| U7 | paper-grade proposition | fixed smooth mode、zero bias 下 M/D leading effect为双线性，controlled-minus-zero-action=`O(ε²)` | 高（条件性） | 缩幅实验出现稳定非零 `O(ε)` 项且排除偏置/mode switch/数值误差 |
| U8 | paper-grade proposition | cross separation由异质性、I/O leakage和 resolvent conditioning共同决定；heterogeneity alone无统一 bound | 很高 | 在额外限定 compact/conditioned model class 后可建立更强统一界；这不会反驳当前一般反例 |
| U9 | paper-grade proposition | R458 成功最多是冻结 schedule 在 K/4 固定 profiles 的 finite-bank witness，无分布概率 | 很高 | 另有明确 iid profile generator 与独立 test sample，可支持概率区间；原 R458 语义不变 |

---

# 最终可执行顺序

1. **立即可做且价值最高**：先修 U3 replay/Bellman contract，再执行 U2 的合法 factorial；否则消息实验仍被 action semantics 污染。
2. **论文理论补强**：把 U7 的 `O(ε²)` 命题与 U8 的 conditioning-bound 写入理论段，严格限定 fixed-mode/local assumptions。
3. **控制器类可行性**：按 U1 导出 Object B sampled matrices 和 DCF/lift，运行 phase-I；在此之前不得写类不可行。
4. **性能/稳定分离**：U6 先用 0.1 s fractional nonlinear point 收窄 endpoint crossing；稳定 margin 另走 full realization/pole tracking。
5. **训练与 gate 对齐**：U4 用 exact finite-bank max-violation phase-I 作为 feasibility-before-training；neural training只做 witness search。
6. **R458 完成后**：按 U9 表直接分类，不根据 outcome 修改措辞或阈值。
