# M/D decoupling MARL：action-effort 通道放置与 objective-to-gate gap 的结构性结论

> **用途**：给项目 owner / agent 的理论决策文档。本文只回答咨询材料的 **A1（§5）** 与 **A2（§6）**；不提前判定 R421 的 §7 机制类别，也不建议修改已冻结的 R421/R422 协议。
>
> **证据边界**：R419/R420 数字均按原材料中的三种子中位数作为描述性事实；R421/R422 尚未落地，因此所有关于它们的结论都写成可证伪的条件预测。

---

## 0. 结论先行

| 结论 | 类型 / 置信度 | 对项目解释的直接影响 |
|---|---|---|
| 冻结公式中的 `c_c` **不是纯 common-mode quadratic**：它精确包含 differential frequency 与 differential RoCoF 能量。 | 代数恒等式 / 高 | 当前 `(c_d,c_c)` 是“差分主目标 + common-protection surrogate”，不是正交模态成本分解。 |
| `effort = mean_i ‖a_i‖²` 是 **total executed-action energy**；它自身没有天然的 common/differential 归属。 | Parseval 恒等式 / 高 | 把同一个 `effort` 写进 `c_d` 或 `c_c`，不等于把动作物理地路由到 differential/common mode。 |
| R420 与 R422 不是干净的“通道位置”隔离：R420 的 effort 系数固定为 `1`，R422 的系数是动态 `λ`；按 `c_c += effort` 的字面代码语义，effort 还会进入 dual residual。`λ=1` 时两者的精确 cost-return scalarization 相同，但独立训练的 approximate critic heads 仍可给出不同数值梯度。 | 代数恒等式 / 高 | 即使 R422 优于 R420，也首先证明的是 **有效 effort 权重 / critic-head 归属**，以及在 modified `c_c^{422}` 被 dual 读取时的 **预算语义不同**；不能单独证明“common channel 是物理正确通道”。 |
| 按 R422 的字面定义，单 episode 若满足 sample budget `Σ_t(c_c+effort)≤3`，必然有平均 `effort≤0.1`；若忽略频率成本，8 个 normalized scalar action 的轨迹 RMS 不超过约 `0.2236`。按 CMDP 的 expected-budget 解释，相应结论是 `E[mean effort]≤0.1`，而非逐轨迹硬界。 | 必要条件 / 高 | 如果 realized effort 长期高于该量级，`λ` 会被持续向上推，R422 可能比 R420 **更强**地抑制有用 differential authority。 |
| `Σ_t c_c≤3` 的期望约束既不等价于单轨迹 peak/RoCoF/TV 约束，也不等价于 reference-relative、every-block 的 canary。 | CMDP 定义 + 反例 / 高 | R419 能改善 endpoints 而仍 36/36 action-stress fail，不是悖论；这是由约束函数、风险层级和评价集合不一致直接允许的。 |
| 一个 shared `λ` 对“一个 joint scalar constraint”是 KKT 正确的；问题不是 shared 本身，而是只有一个频率 surrogate multiplier，却没有对应 action RMS、TV、peak 等 guard 的独立约束与 multiplier。 | KKT 结构 / 高 | 不应把失败简单归因于“shared λ”；应区分 joint constraint 与 per-agent / per-metric constraints。 |
| 当前 actor 与 dual 甚至不在优化同一个时间加权约束：critic 使用 `γ=0.99` 的 discounted `Q_c`，dual 使用 30 步 undiscounted sum；最后一步在 actor 中权重约 `0.747`，在 dual 中仍为 `1`。 | 代数比较 / 高 | 除非二者近似成比例，否则现有更新不是同一个 Lagrangian 的严格 descent-ascent，经典 saddle-point 收敛结论不能直接套用。 |

**总判断**：

1. **A1 verdict**：对当前这个 total-action `effort`，common-channel placement 作为“物理模态归属”是 **theory-neutral**；R422 的符号主要由 actor-update 时的 `λ_eff`、动作的 differential 占比以及 slew/saturation 的有效 Jacobian 决定。
2. **A2 verdict**：objective-to-gate gap 是 **结构上必然可能** 的；当前 Lagrangian 只约束一个 discounted/undiscounted 还不完全一致的频率 surrogate，不可能自动购买 omitted、trajectory-level、reference-relative、every-block guards。

---

## 1. 固定事实与回答边界

### 1.1 采用的冻结事实

| Quantity（message arm vs deterministic reference） | R419 | R420：`c_d += effort` |
|---|---:|---:|
| off-diagonal endpoint ratio | `0.6954` | `2.3641` |
| disturbance-differential endpoint ratio | `0.7104` | `1.9440` |
| message increment | `+43.45% / +25.59%` | `−35.25% / −34.02%` |
| common-frequency guard failures / 36 | `19` | `36` |
| worst-peak guard failures / 36 | `28` | `34` |
| action-stress guard failures / 36 | `36` | `36` |
| scalar arm | isolation baseline | identical，支持单因素归因 |

R422 冻结为 `c_c += effort`，R421 冻结为 log-only rerun。本文不改变二者执行。

### 1.2 结论标签

- **[定理/恒等式，高置信]**：由冻结公式直接推出，不依赖训练结果。
- **[条件推论，高置信]**：条件成立时数学上成立；条件是否满足需日志确认。
- **[机制启发，中置信]**：符合小信号/LQ/CMDP 理论，但具体符号依赖未知 Jacobian、`λ` 或数据。
- **[经验预测，中置信]**：对 R422/R421 的可证伪方向预测，不视为已发生事实。

### 1.3 小信号假设边界

A1 的物理推导采用 swing-like 局部模型，假设网络约化后在工作点附近可写成对称 Laplacian-like coupling。ANDES 的完整 DAE、损耗、限幅和离散更新会造成偏离；因此“精确解耦”只在明确列出的对称/线性条件下成立。

---

## 2. 三个必须先澄清的代数事实

### 2.1 `c_c` 并非纯 common mode

令冻结的 normalized common basis vector 为

$$
q_0=\frac12\mathbf 1_4,
\qquad
U=\begin{bmatrix}q_0^T\\T\end{bmatrix},
\qquad UU^T=I_4.
$$

因为原材料定义 `c(x)=mean(x)`，所以

$$
q_0^Tx=2c(x),\qquad z=Tx.
$$

由 Parseval 恒等式：

$$
\frac14\|x\|_2^2
=\frac14\left[(q_0^Tx)^2+\|Tx\|_2^2\right]
=c(x)^2+\frac14\|z\|_2^2.
$$

因此冻结的 frequency 部分

$$
\operatorname{mean}_i\left(\frac{f_i-60}{\sigma_f}\right)^2
=\frac{c(x)^2}{\sigma_f^2}
+\frac{\|z\|_2^2}{4\sigma_f^2}.
$$

若以 `r_f` 表示四台 VSG 的 RoCoF 向量，同理：

$$
\operatorname{mean}_i\left(\frac{r_{f,i}}{\sigma_{rocof}}\right)^2
=\frac{c(r_f)^2}{\sigma_{rocof}^2}
+\frac{\|Tr_f\|_2^2}{4\sigma_{rocof}^2}.
$$

所以冻结公式实际上是

$$
\boxed{
 c_c=
 \frac{c(x)^2}{\sigma_f^2}
 +\frac{\|z\|^2}{4\sigma_f^2}
 +\frac{c(r_f)^2}{\sigma_{rocof}^2}
 +\frac{\|Tr_f\|^2}{4\sigma_{rocof}^2}
}
$$

而非只包含 mean-frequency direction 的纯 common cost。

**结论 [恒等式，高置信]**：`c_c` 应理解为 **common-protection channel / total unit frequency-energy surrogate**；它与 `c_d` 在 differential frequency 上重叠。忽略 `p` 与 RoCoF 项时，actor 对 `||z||²/σ_f²` 的总瞬时权重大致为

$$
\frac13+\frac{\lambda}{4},
$$

而不是只有 `c_d` 的 `1/3`。

这意味着“把 effort 放进 common channel 就不会与 differential objective 竞争”的强说法，在冻结公式下已经不成立。

---

### 2.2 `effort` 是 total action energy，不是 modal action energy

把四个 executed normalized 2-D actions 堆成

$$
A_t=
\begin{bmatrix}
 a_0^T\\a_1^T\\a_2^T\\a_3^T
\end{bmatrix}\in\mathbb R^{4\times2}.
$$

冻结 penalty 为

$$
e_t=\operatorname{mean}_i\|a_i\|_2^2
=\frac14\|A_t\|_F^2.
$$

定义 action common coordinate 与 differential coordinates：

$$
A_{c,t}=q_0^TA_t,\qquad A_{d,t}=TA_t.
$$

由 `U` 正交：

$$
\boxed{
 e_t
 =\frac14\|A_{c,t}\|_F^2
 +\frac14\|A_{d,t}\|_F^2
}
$$

也可写成均值—离差分解：

$$
 e_t
 =\left\|\frac14\sum_i a_i\right\|_2^2
 +\frac14\|TA_t\|_F^2.
$$

据此定义可直接从 action trace 计算的 modal fraction：

$$
\eta_d^a
=\frac{\sum_t\|TA_t\|_F^2}
       {\sum_t\|A_t\|_F^2},
\qquad
\eta_c^a=1-\eta_d^a.
$$

**结论 [恒等式，高置信]**：当前 `effort` 同时惩罚 common-coordinated action 与 spatially differential action。只有在 `η_d^a≈1` 时，才可近似把它解释为 differential-action penalty；只有在 `η_c^a≈1` 时，才可近似解释为 common-action penalty。

此外，penalty 作用于 normalized action，而不是 decoded `(ΔM,ΔD)` 的物理能量。即使两个 normalized 维度数值同尺度，`ΔM` 与 `ΔD` 对频率响应的局部灵敏度也通常不同；因此 `||a_i||²` 是 regularization norm，不是已证明的物理 control-energy metric。

---

### 2.3 R420 与 R422 的精确代数差异

只为消除 reward 符号与变量复写歧义，记 `c_c^0` 为 R419 中原始的 common-protection cost，`e_t=effort_t`。R422 的字面 modified cost 是 `c_c^{422}=c_c^0+e_t`。以下定义 base discounted cost-return：

$$
J_d=\mathbb E\sum_t\gamma^t c_d(t),\quad
J_c^0=\mathbb E\sum_t\gamma^t c_c^0(t),\quad
J_e=\mathbb E\sum_t\gamma^t e_t.
$$

则 actor 的 cost-side scalarization 为：

$$
\begin{aligned}
\text{R419}:&\quad J_d+\lambda J_c^0,\\
\text{R420}:&\quad J_d+J_e+\lambda J_c^0,\\
\text{R422}:&\quad J_d+\lambda(J_c^0+J_e)
             =J_d+\lambda J_c^0+\lambda J_e.
\end{aligned}
$$

所以

$$
\boxed{
L_{R422}-L_{R420}=(\lambda-1)J_e
}
$$

并且在 `λ=1` 时，R420 与 R422 的 **精确 cost-return scalarization 相同**。这不等于实际 learned actor gradient 必然相同：effort 被分配到不同 critic head 后，有限数据、函数逼近与 target scale 可使两个近似分解产生不同误差。

但 R422 还改变 dual residual。按 `c_c += effort` 的字面语义：

$$
\lambda\leftarrow
\operatorname{clip}\left[
\lambda+0.05\left(
\sum_{t=0}^{29}(c_c^0(t)+e_t)-3
\right),0,10\right].
$$

因为 `c_c^0,e_t≥0`，对任一满足 **sample budget** 的 episode 都有

$$
\frac1{30}\sum_t e_t\le0.1.
$$

若把 4 agents × 2 dimensions × 30 steps 的 normalized scalar actions 一起计算 RMS，则在假设 `c_c^0=0` 的最宽松情况下：

$$
\operatorname{RMS}_{scalar}(a^{exe})
\le\sqrt{0.05}\approx0.2236;
$$

实际 `c_c^0>0` 时界更紧。若把 dual ascent 解释为 CMDP 的 **expected constraint**，严格对应的是

$$
\mathbb E\!\left[\frac1{30}\sum_t e_t\right]\le0.1
$$

（同样还要扣除 `c_c^0` 的 budget share），它不推出每条 trajectory 的 RMS 都低于 `0.2236`。

> **实现语义检查**：上述 budget-coupling 结论按材料的字面定义 `c_c += effort`，即 dual residual 也读取修改后的 `c_c`。Agent 应在不改变 frozen run 的前提下核对实际代码路径；若 dual update 读取的是 base `c_c^0`，则 R422 不包含 effort-budget coupling，只剩动态 `λ` 权重与 critic-head 归属差异。

**结论 [恒等式/必要条件，高置信]**：R422 必然同时改变两件事，并可能再改变第三件事：

1. effort 从固定系数 `1` 变为动态系数 `λ`；
2. effort 被放入另一个 approximate critic head，改变该 head 的 target scale 与估计误差；
3. **若 dual update 读取 modified `c_c^{422}`**，effort 还会消耗 common budget `3.0`。

因此，无论是哪一种实际代码语义，R422 都不是纯粹的 channel-placement intervention。

---

## 3. A1 — action-effort penalty 应该放在哪个 channel？

### 3.1 A1.1：4-VSG 小信号 modal dynamics 与 `(ΔM_i,ΔD_i)` 的作用路径

#### 3.1.1 Swing-like parameter-varying model

在一个 action hold interval 内，采用局部模型

$$
\dot\delta=x,
\qquad
M(a)\dot x+D(a)x+L\delta=w,
$$

其中：

- `x=f−60∈R⁴`；
- `M(a)=diag(M_i(a_i))`，`D(a)=diag(D_i(a_i))`；
- `L` 是网络约化后的 coupling matrix；
- `w` 汇总 load disturbance 与 active-power imbalance，包括 `P_es` 的作用。

这与常见的 linear network-reduced swing model 一致；virtual inertia/damping 的位置与数值会改变 coherency、RoCoF、nadir 和 inter-area response，而其最优配置通常依赖网络结构与 disturbance location [Poolla–Bolognani–Dörfler, IEEE TAC 2017；Ademola-Idowu–Zhang, IEEE PESGM 2018]。

#### 3.1.2 冻结 `T` 下的 modal operator

令

$$
\nu=Ux=\begin{bmatrix}\xi_c\\z\end{bmatrix},
\qquad
\eta=U\delta,
\qquad \xi_c=q_0^Tx=2c(x).
$$

modal dynamics 为

$$
(UMU^T)\dot\nu+(UDU^T)\nu+(ULU^T)\eta=Uw.
$$

若 `m=(M_0,M_1,M_2,M_3)^T`，则

$$
UMU^T=
\begin{bmatrix}
\operatorname{mean}(m) & \frac12(Tm)^T\\
\frac12Tm & T\operatorname{diag}(m)T^T
\end{bmatrix}.
$$

`D` 完全同理：

$$
UDU^T=
\begin{bmatrix}
\operatorname{mean}(d) & \frac12(Td)^T\\
\frac12Td & T\operatorname{diag}(d)T^T
\end{bmatrix}.
$$

因此：

$$
\boxed{
\text{common–differential cross block vanishes}
\iff Tm=0\ \text{and}\ Td=0
}
$$

由于 `null(T)=span{1_4}`，在冻结的 **unweighted mean basis** 中，这等价于四台 VSG 的 `M_i` 全相等、`D_i` 全相等。若采用按 machine rating 加权的 common coordinate，可把条件放宽到参数按 rating 成比例；Paganini 与 Mallada 在该 proportionality 条件下得到 system-wide frequency 与 residual component 的解析分解，并说明 connectivity 增强时 aggregate approximation 更准确 [IEEE TAC 2020]。本项目冻结的是未加权均值，所以 profile 内的 `M_i,D_i` heterogeneity 会直接形成 cross blocks。

可定义两个可计算的 heterogeneity mixing index：

$$
\epsilon_M=\frac{\|Tm\|_2}{2\operatorname{mean}(m)},
\qquad
\epsilon_D=\frac{\|Td\|_2}{2\operatorname{mean}(d)}.
$$

`ε_M,ε_D≪1` 是 approximate common–differential decoupling 的必要量级条件之一；它不是充分条件，因为 `TLT^T` 仍可能在三个 differential coordinates 之间非对角。

#### 3.1.3 Network coupling 的作用

若 `L` 是对称 Laplacian-like matrix，则

$$
L\mathbf1=0,
\qquad
ULU^T=
\begin{bmatrix}
0&0\\0&TLT^T
\end{bmatrix}.
$$

所以网络 coupling 本身对 common–differential 的 cross block 为零；它主要决定 differential modal stiffness、damping ratio 与放大倍数。冻结 `T` 的三行只有在 two-area / within-area symmetry 足够好时才近似是 `L` 的 eigenvectors；否则三种 differential coordinates 之间仍耦合。网络 coupling、非均匀时间常数与同步条件之间的这种结构关系可参见 Dörfler–Bullo, SIAM JCO 2012。

- **弱 inter-area tie**：`T` 第一行对应的 inter-area direction 往往具有较小 eigenvalue、较大低频增益，因此 area-antisymmetric action/disturbance 对 endpoints 高度敏感。
- **强 connectivity**：提高 differential restoring strength，使 individual frequency residual 更接近 aggregate frequency；这与 Paganini–Mallada 的 robustness 结论一致。
- **注意**：strong connectivity 抑制 differential response，不会把任意 local parameter action 自动变成 common action。

#### 3.1.4 `(ΔM,ΔD)` 是 parameter input，不是普通 additive input

对 nominal response `(x_0,\dot x_0)` 做一阶扰动：

$$
M_0\,\delta\dot x+D_0\,\delta x+L\,\delta\delta
=-\operatorname{diag}(\dot x_0)\,\delta m
 -\operatorname{diag}(x_0)\,\delta d.
$$

定义 state-dependent equivalent forcing

$$
r=\operatorname{diag}(\dot x_0)\delta m
  +\operatorname{diag}(x_0)\delta d,
$$

则 modal forcing 为

$$
-Ur=-\begin{bmatrix}q_0^Tr\\Tr\end{bmatrix}.
$$

这给出物理上更准确的“action 主要作用于哪个 mode”的判断：

$$
\eta_d^{phys}
=\frac{\sum_t\|Tr_t\|^2}
       {\sum_t\|r_t\|^2},
\qquad
\eta_c^{phys}=1-\eta_d^{phys}.
$$

必须强调两点：

1. 在静态 equilibrium 上 `x_0=\dot x_0=0`，parameter perturbation 的直接一阶 forcing 为零；其主要作用是改变后续 disturbance-to-frequency transfer operator。这是一个 bilinear / LPV 问题，而不是标准的 `Bu` additive LQR。
2. normalized action 的 modal fraction `η_d^a` 与物理 forcing fraction `η_d^{phys}` 不必相同，因为 decoder、`x_t,\dot x_t`、floors 和 saturation 会重新加权各 agent 与 `(M,D)` 维度。

#### 3.1.5 单 agent、协调 action 与 mode dominance

对于任意 per-agent effective forcing vector `r`：

- `r∝1_4`：`Tr=0`，是纯 common forcing；
- `1_4^Tr=0`：`q_0^Tr=0`，是纯 differential forcing；
- `r∝[1,1,-1,-1]^T`：纯 inter-area differential；
- `r∝[1,-1,0,0]^T` 或 `[0,0,1,-1]^T`：纯 intra-area differential。

单个 agent 的局部 forcing `r=αe_i` 在输入几何上满足

$$
(q_0^Tr)^2=\frac14α^2,
\qquad
\|Tr\|^2=\frac34α^2.
$$

即 differential:common 的 raw projection energy 为 `3:1`。但这不是 response-energy 的 `3:1`，因为 common/differential transfer gains、inter-area eigenvalue、M/D heterogeneity 与 limiter 会改变响应。

另外，**uniform parameter change 不等于 pure common action**。若 `δm=α1_4`，则

$$
U\operatorname{diag}(\delta m)U^T=αI_4,
$$

它不引入 mode mixing，却会同时重调 common 与全部 differential modes 的 inertia。只有等效 forcing 的 uniform pattern 才是 pure common excitation。

#### 3.1.6 A1.1 的结构条件总结

| 条件 | 主要结果 | 置信度 |
|---|---|---|
| `M_i=M`、`D_i=D`，`L` 对称 Laplacian | common 与 differential operator block-exact decoupled | 高 |
| 上述条件 + `T` 行是 `L` 的 eigenvectors | 三个 differential coordinates 也彼此解耦 | 高 |
| `ε_M,ε_D` 小、`TLT^T` 近对角 | frozen `T` 下 approximate modal decoupling | 中高 |
| weak inter-area tie | inter-area differential response 对 area-antisymmetric action 更敏感 | 中高 |
| strong connectivity + coherent states/actions | residual differential response被抑制；若 parameter actions 也协调，闭环 response 可呈 common-dominant，但 forcing projection 本身不由 connectivity 改写 | 中高 |
| local / heterogeneous / zero-sum action pattern | effective forcing通常偏 differential，并引入 common↔differential mixing | 中高 |
| slew/saturation/floors active | modal sensitivity随状态切换，以上线性结论只局部有效 | 高 |

---

### 3.2 A1.2：把 `effort` 放进不同 channel，实际实现了什么 objective？

#### 3.2.1 理想 block-diagonal LQ 情形

若同时满足：

1. dynamics 在 `(common,differential)` 中 block diagonal；
2. control allocation 也可写成彼此独立的 `u_c,u_d`；
3. objective 是 quadratic；
4. 无 saturation、floors、slew projection；
5. critic 精确，`λ` 在 actor 优化期间固定；

则理想目标可写成

$$
J=J_d(z,u_d)+J_c(\xi_c,u_c)
+\rho_d\|u_d\|_R^2+\rho_c\|u_c\|_R^2.
$$

在这个理想模型里，提高 `ρ_d` 会直接抬高 differential control authority 的代价，因此一般沿 differential state-energy 与 control-energy 的 Pareto frontier 移动；提高 `ρ_c` 则主要改变 common protection 的权衡。virtual inertia/damping 的 H2 设计文献同样显示 inertia、damping、nadir、RoCoF、settling/coherency 通常存在显式 trade-off，而不是“effort 越小所有指标都越好” [Poolla et al., 2017；Ademola-Idowu & Zhang, 2018]。

这是“differential-channel effort 与 `c_d` 在同一 mode 竞争”的**精确适用条件**。

#### 3.2.2 冻结实现为什么不满足该精确解释

冻结实现至少有六个断点：

1. `c_c` 本身含 differential frequency/RoCoF，两个 reward heads 不正交；
2. `effort` 是 total action norm，而不是 `||u_d||²` 或 `||u_c||²`；
3. `(ΔM,ΔD)` 是 parameter modulation，局部是 bilinear/LPV，而非固定 `B_c u_c+B_d u_d`；
4. `λ` 动态变化，且 R422 把 effort 写入 dual residual；
5. slew limiter 的 projection 是 piecewise affine，在 active boundary 上不可微或对 raw action 的局部增益为零；
6. decoded bounds、`M≥20,D≥10` 与 action saturation 使局部 quadratic model 分段失效。

所以实际可成立的只是条件近似：

> 当 `η_d^{phys}` 高、cross-mode mixing 小、limiter 不活跃、`λ` 近似常数时，penalizing total effort 会主要削弱 differential control authority，从而通常恶化 decoupling endpoints。

R420 的 endpoint 回归与 message increment 翻负与该近似一致，但三种子描述性结果不足以单独证明因果机制；它也可能包含 critic-head scale / approximation error 的贡献。

#### 3.2.3 R420 与 R422 的真正比较轴

从 §2.3：

- R420 effective effort coefficient：`1`；
- R422 effective effort coefficient：`λ`；
- 若 dual update 读取 modified `c_c^{422}`，R422 还要求 effort 与 base `c_c^0` 共用 budget `3`。

因此决定 R422 相对 R420 方向的首要参数不是“channel label”，而是：

$$
\boxed{
\lambda_{eff},\quad
\eta_d^{phys},\quad
K_E,\quad K_G,\quad \chi_a,\quad
\phi_{slew},\quad
\phi_{sat}
}
$$

为把“penalty coefficient”与“plant action authority”分开，设 nearby stationary-policy family 随 effective coefficient `ρ_e` 诱导一个局部 action-authority scale `s(ρ_e)`；在观测到的 final policy 处归一化为 `s=1`。定义 plant-side sensitivity：

$$
K_E=-\left.\frac{dE_{dec}(s)}{ds}\right|_{s=1},
\qquad
K_G=-\left.\frac{dG_{no\text{-}harm}(s)}{ds}\right|_{s=1},
$$

以及 coefficient-to-action response

$$
\chi_a=-\frac{ds}{d\rho_e},
$$

其中 `ρ_e` 是 effective effort coefficient。`K_E>0` 表示更多 action authority 会降低 decoupling endpoints；`K_G>0` 表示更多 authority 会降低 no-harm guard residual。若局部最优解对 quadratic regularization 正常响应，则 `χ_a>0`，于是

$$
\frac{dE_{dec}}{d\rho_e}\approx K_E\chi_a,
\qquad
\frac{dG_{no\text{-}harm}}{d\rho_e}\approx K_G\chi_a.
$$

这说明 endpoint 与 no-harm 的方向由 **signed plant sensitivity × policy response** 决定，而不是由 reward-head 名称决定。

这些量可用以下日志/模型代理：

- `λ_eff`：actor-update 时刻的 `λ` 中位数/均值，并报告 `λ=10` clip fraction；
- `η_d^a`：executed normalized action 的 modal fraction；
- `η_d^{phys}`：若保存 `x,RoCoF,ΔM,ΔD`，按 equivalent forcing 计算；
- `K_E,K_G`：优先由小信号闭环 Jacobian 或 existing logs 的 local regression 估计；若 sealing 规则允许额外探索性 evaluation，可对 final checkpoint 做小幅 action-scale finite difference，但必须标为 **post-hoc、非 canary、非 confirmatory**；
- `χ_a`：用 `λ` 变化与 executed action RMS / equivalent forcing magnitude 的局部响应估计；limiter active 时可能接近 0；
- `φ_slew`：raw action 被 rate projection 改写的比例；
- `φ_sat`：action/decoded parameter saturation fraction。

若 `λ_eff<1`，R422 对 effort 的直接 actor pressure 小于 R420；若 `λ_eff>1`，则更大。若 `λ` 长期 clip at `10`，R422 的 nominal effort pressure 可达 R420 的十倍，不能再解释为“保护 common mode 的温和放置”。在理想凸 LQ 情形，降低 `ρ_e` 通常增加 action magnitude；因此 endpoint 恢复与 action-stress 改善并非同一方向的必然结果。

---

### 3.3 A1.3：R422 的可证伪预测

#### 3.3.1 预测表

| 假设 / 条件 | 两个 endpoint ratios | message increment | no-harm failures | action-stress failures | 关键日志预期 |
|---|---|---|---|---|---|
| **H_common-operational / lower-weight branch**：`η_d^{phys}` 高、`K_Eχ_a>0`、`λ_eff<1`、slew/sat 不主导 | 两者应从 R420 的 `2.3641/1.9440` **下降并向 R419 的 `0.6954/0.7104` 回归**；不要求必然低于 `1` | 从 `−35.25%/−34.02%` 向 `0` 或正值移动；若 communication 的价值来自 differential coordination，强版本预测恢复为正 | **由 `K_Gχ_a` 决定**：`K_Gχ_a>0` 时应少于 R420 的 `36/34`；约为 `0` 时近似不变；小于 `0` 时可反而变差 | 相对 R420，较弱 effort pressure 通常使 RMS **持平或上升**；TV 无确定方向，因此 `36/36` 仍可能保持，CANARY-PASS 不由 endpoint 恢复推出 | `median λ_actor<1`；`η_d` 高；`K_Eχ_a>0`；no-harm方向由 `K_Gχ_a` 给出；clip fractions低 |
| **H_budget-dominant / higher-weight branch**：dual 读取 modified cost，`Σ(c_c^0+effort)>3` 长期成立，`λ_eff>1` 或 clip at `10` | 与 R420 相当或更差；若 useful differential authority 被强压，两个 ratios 可继续上升 | 维持负值或更负 | 仍由 `K_Gχ_a` 决定；当 `K_Gχ_a>0`（动作同时保护 common且 regularization确实压低 authority）时通常更差 | RMS 较可能下降，但 TV/no-harm 仍可失败；canary 大概率仍 FAIL | `λ` 上升/高位循环/clip；平均 `effort>0.1−avg(c_c^0)`；动作幅值被压缩 |
| **H_null-placement**：控制 `λ_eff`、dual semantics、critic error 与 limiter 后，channel label 无额外作用 | R422 与 R420 在预注册聚合/CI下不可区分 | 仍约为负且不可区分 | failure profile 与 R420 近似 | 仍 `36/36` 或无实质变化 | `λ≈1`；effort 对 dual residual 的实际贡献可忽略，或实现读取 base `c_c^0`；value diagnostics相近 |
| **H_critic-head**：`λ≈1` 但移动 reward component 改变 value estimation | endpoints 可不同，但方向不由 modal theory决定 | 可变 | 可变 | 可变 | R421/R422 对应 head 的 Bellman residual、TD-error scale 或 critic loss发生差异；这属于 §7 后续机制层，不在本文提前定类 |


#### 3.3.2 支持与否的判据

R422 落地后应分三层陈述，不能跨层归因：

1. **operational superiority**：若两个 endpoint ratios 都显著低于 R420、message increment 向正方向恢复，则只能先说 “R422 intervention 优于 R420”。
2. **effective-weight explanation**：若同时 `λ_eff<1`，最保守且最强的解释是动态 multiplier 把 effort 权重降到 R420 的固定 `1` 以下，从而恢复 useful authority。此时 action RMS 相对 R420 持平或上升并不反常，action-stress 仍可能 `36/36`。
3. **critic-head / budget explanation**：若 `λ≈1` 但结果不同，检查 critic-head Bellman residual/scale；若 dual 读取 modified cost，再检查 effort 的 budget share。只有这些解释均不足，才能说 “head placement 可能有额外作用”。

要把结果上升为“**physical common-channel placement 被支持**”，至少还需要一个当前设计没有满足的 matched comparison：相同 effective effort coefficient、相同 dual residual、相同 critic approximation quality，并且 penalty 本身应分解为 `||A_c||²` 与 `||A_d||²` 而不是 total norm。由于冻结 R422 不具备这些隔离条件，它无论成功还是失败，都不能单独证明 total effort 在物理上属于 common mode。

no-harm 的符号另由 `K_Gχ_a` 决定：

- `K_Gχ_a>0`：effort 权重越大，common guards 越差；R422 若降低有效权重，应减少 R420 的 `36/34` failures；
- `K_Gχ_a≈0`：no-harm failure profile 可与 R420 近似不变；
- `K_Gχ_a<0`：降低 effort 权重反而可能增加 common excursion。

若 R422 恶化且 `λ>1`/clip，支持 over-regularization；只有确认 dual 读取 modified cost且 effort 显著占用预算时，才进一步命名为 budget-dominant。


#### 3.3.3 A1 一句话 verdict

> **Common-channel placement 对当前 total-action `effort` 是 theory-neutral；R422 在 useful action differential-dominant、`K_Eχ_a>0`、`λ_eff<1` 且 limiter 不主导时可以 operationally 优于 R420，但这种改善首先支持 lower effective effort weight，而不支持 physical common-mode placement。**

---

## 4. A2 — 为什么最小化 Lagrangian cost 不能购买 guard compliance？

### 4.1 A2.1：average constraint 与 trajectory / peak / every-block gate 的差距

#### 4.1.1 CMDP 中当前 dual update实际约束什么

对固定 policy `π`，定义单 episode 随机成本

$$
C_c(\tau)=\sum_{t=0}^{29}c_c(t).
$$

一次 episode 的 dual update 是对约束

$$
\mathbb E_{\tau\sim\pi}[C_c(\tau)]\le3
$$

的 stochastic approximation，而不是把每条 trajectory 投影到 `C_c(τ)≤3`。经典 CMDP Lagrangian 理论主要处理 expected discounted/average cumulative costs；CPO 的约束与性能界也属于 expected-return 层级 [Achiam et al., ICML 2017]。要控制 chance、CVaR 或 almost-sure safety，需要不同的 risk formulation 或 state augmentation [Altman, 1999；Chow et al., JMLR 2018；Sootla et al., ICML 2022；Tabas et al., L4DC 2023]。

#### 4.1.2 定理：一阶矩约束不推出单轨迹安全

**定理 [高置信]**：对任意非负随机变量 `C` 和预算 `B>0`，`E[C]≤B` 不推出 `C≤B` almost surely，也不推出任意非平凡的 peak constraint。

**自包含反例**：任选 `p∈(0,1)`，令

$$
C=\begin{cases}
B/p,&\text{概率 }p,\\
0,&\text{概率 }1-p.
\end{cases}
$$

则 `E[C]=B`，但 `P(C>B)=p`。因此 expected budget 可以由少量高代价轨迹与大量低代价轨迹平均满足。

Markov inequality 只能给出

$$
P(C\ge u)\le\frac{B}{u},
$$

对接近 `B` 的安全阈值几乎没有作用。

#### 4.1.3 用冻结数字实例化 `Σ c_c≤3`

若更强地假设 **每条轨迹** 都满足 `Σ_t c_c(t)≤3`，仍只能得到很松的 absolute L2-derived bounds。

因为 frequency term 含

$$
\frac14\sum_i\left(\frac{x_i}{0.15}\right)^2,
$$

将全部预算集中到一个时刻、一个 unit，可有

$$
|x_i|=0.15\sqrt{12}\approx0.5196\ \mathrm{Hz}
$$

而仍恰好消耗 `3`。若四台 unit 同步同幅，则 common excursion 可达

$$
|c(x)|=0.15\sqrt3\approx0.2598\ \mathrm{Hz}.
$$

RoCoF 同理：单 unit 可达

$$
\sqrt{12}\approx3.464\ \mathrm{Hz/s},
$$

四台 coherent RoCoF 可达 `sqrt(3)≈1.732 Hz/s`。

对 common-frequency IAE，若每轨迹预算真的成立，可由 Cauchy–Schwarz 得到

$$
\begin{aligned}
IAE_c
&=0.2\sum_{t=0}^{29}|c(x_t)|\\
&\le0.2\cdot0.15\sqrt{30\sum_t c_c(t)}\\
&\le0.2846\ \mathrm{Hz\cdot s}.
\end{aligned}
$$

这些界仍不能推出 no-harm：

- gate 阈值是 `1.03×reference`，而不是上述 absolute constants；材料未给 reference 的数值，无法建立包含关系；
- 实际 dual 约束的是期望，不是每轨迹；
- `c_c` 在时间和 units 上做平方和，允许 spike concentration；
- worst-unit peak 与 mean-square 之间只有很松的维数因子；
- action RMS/TV 完全不在 `c_c` 中。

#### 4.1.4 训练 feasible set 与 canary feasible set 没有包含关系

当前训练约束近似定义

$$
\mathcal F_{train}
=\{\pi:\mathbb E_{train}[\sum_t c_c(t)]\le3\}.
$$

canary 则近似是多个 deterministic/reference-relative 条件的交集：

$$
\mathcal F_{gate}
=\bigcap_{profile,arm,seed}
\left\{
\begin{array}{l}
IAE_c\le1.03IAE_{ref},\\
peak\le1.03peak_{ref},\\
RoCoF\le1.03RoCoF_{ref},\\
RMS_a\le1.10RMS_{ref},\\
TV_a\le1.10TV_{ref},\\
saturation/anti\text{-}collapse\ conditions
\end{array}
\right\}.
$$

没有给出、也不存在由冻结定义自动产生的

$$
\mathcal F_{train}\subseteq\mathcal F_{gate}.
$$

这里还有三个层级错位：

1. **metric mismatch**：sum of squared frequency/RoCoF vs IAE/peak/RMS/TV；
2. **risk mismatch**：expected episode cost vs trajectory-level / worst metric；
3. **population mismatch**：一个 fixed policy 的 trajectory distribution vs every profile × every training seed 的 algorithm-reliability gate。

训练 seed 是“训练算法产生哪个 policy”的随机性，不是固定 policy 下的普通 environment trajectory 随机性。标准 CMDP constraint 本身不约束所有训练 seed 都收敛到 feasible policy。

#### 4.1.5 A2.1 结论

> R419 的 `0.6954/0.7104` 说明 `c_d`-aligned endpoints 可以改善；`36/36` action-stress fail 说明 omitted guard 没有随之改善。两者完全可以同时成立，不构成 Lagrangian 理论反例。

---

### 4.2 A2.2：shared λ、episodic lag、TD3 critics 下哪些 saddle-point 性质还成立？

#### 4.2.1 理想 CMDP convergence 需要的条件

经典 constrained actor–critic 的局部收敛结论通常要求：

- objective 与 constraint 使用同一个 discounted 或 average functional；
- policy-induced Markov chain 稳定/遍历，状态是 Markov；
- constraint feasible，常配合 Slater-like strict feasibility；
- critic 估计在 actor/dual 看来足够快且渐近无偏；
- critic、actor、dual 使用严格分离的 stochastic-approximation timescales 与递减步长；
- 参数有界，gradient noise 满足标准条件；
- policy class 能表示所需解。

Bhatnagar 与 Lakshmanan在 long-run average CMDP 中证明的是这类受控条件下的 almost-sure local convergence [JOTA 2012]；该结论不能直接转移到 fixed-step、deep nonlinear、off-policy replay、clipped-double-Q 的 TD3。

#### 4.2.2 一个此前未显式写出的 primal–dual objective mismatch

actor 的 `Q_c` 使用 `γ=0.99`：

$$
J_c^\gamma(\pi)=\mathbb E\sum_{t=0}^{29}\gamma^t c_c(t).
$$

但 dual residual 使用 undiscounted sum：

$$
G_c^1(\pi)=\mathbb E\sum_{t=0}^{29}c_c(t)-3.
$$

所以实际 vector field 近似为

$$
\theta\leftarrow\theta-\alpha\nabla_\theta
[J_d^\gamma+\lambda J_c^\gamma],
\qquad
\lambda\leftarrow\Pi[\lambda+\beta G_c^1].
$$

除非 `J_c^γ` 与 `G_c^1` 在 policy family 上成比例，否则这不是同一个标量 Lagrangian 的 gradient descent-ascent。`γ^29≈0.747`，即最后一步在 actor common critic 中比 dual residual 少约 `25.3%` 权重；对 30-step horizon 不是严格可忽略项。

**结论 [高置信]**：当前实现没有标准 single-Lagrangian saddle-point interpretation。它仍可能经验收敛到某个 fixed point，但不能援引经典 CMDP convergence 作为 guard guarantee。

R422 中同样存在：actor 对 effort 使用 discounted `λJ_e^γ`，dual 对 effort 使用 undiscounted `Σe_t`。

#### 4.2.3 shared multiplier 是否错误？

若只有一个 joint constraint

$$
g_c(\theta_1,\theta_2,\theta_3,\theta_4)\le0,
$$

正确的 joint Lagrangian 是

$$
\mathcal L=J_d+\lambda g_c,
$$

每个 actor 接收

$$
\nabla_{\theta_i}J_d+\lambda\nabla_{\theta_i}g_c.
$$

因此 **一个 shared `λ` 对一个 shared scalar constraint 是 KKT 正确的**。把同一个 joint constraint 机械复制成四个 per-agent multipliers 不会自动更正确，反而可能重复计罚。

需要 per-agent / vector multipliers 的情况是：

- guard 本身是 `g_i≤0` 的四个独立约束；
- gate 取 `max_i`，需要 epigraph 或 per-unit constraints；
- 每个 profile 有独立必须满足的 reference-relative bound；
- action RMS/TV 与 frequency no-harm 是不同约束。

所以本项目的主要结构问题是 **constraint vector 被压缩成了单个 `c_c` surrogate**，不是 shared `λ` 这个事实本身。

#### 4.2.4 episodic dual update 的预期 dynamics

“每 episode 更新 λ”本身并非错误：episode RMS、TV、peak 的 residual 只有轨迹结束后才完整可知。问题在于固定 gain、30-step feedback delay、actor/critic 持续变化以及缺乏严格 timescale separation。

| λ dynamics | 成立条件 | 可观察表现 |
|---|---|---|
| **收敛到有限值** | constraint feasible；actor 对 λ 单调响应；critic 误差小；primal/dual functional 一致；dual 比 actor 慢；步长足够小/递减 | `Σc_c−3` 围绕 0 缩小，λ 不触顶，actor/critic loss稳定 |
| **极限环 / overshoot** | fixed-step integral-like dual、episode delay、actor 与 dual 同量级变化 | λ 与 episode cost 反相振荡；constraint satisfaction 与 endpoint performance交替；Stooke et al. 2020 讨论了标准 Lagrangian update 的 oscillation/overshoot，Moskovitz et al. 2023 说明普通 ascent-descent 可只有 average convergence 而无 last-iterate convergence |
| **向上 drift / clip at 10** | budget infeasible；policy class无法响应；Q 误差使 actor低估实际 cost；若 dual 读取 modified cost，R422 中 effort 本身即可造成超预算 | `λ=10` fraction上升，constraint residual仍正，动作或endpoint未按预期改善 |
| **向下 drift / clip at 0** | policy过度保守或 critic pessimism；实际 cost长期低于预算 | common pressure消失，primary `c_d` 主导；可能恢复 differential endpoints但牺牲 guard margin |
| **高噪声随机游走** | episode sample variance大、训练distribution非平稳、固定 dual step较大 | λ 与 cost 无清晰相位关系，seed间差异大 |

#### 4.2.5 TD3 overestimation 如何影响 λ

`λ` 的更新直接使用 realized `c_c`，不是 Q estimate。因此 Q bias **不直接**进入 dual update；它通过 actor 间接作用：

1. 对 negative-cost rewards，Q overestimation 意味着 Q “不够负”，即 future cost 被低估；
2. actor 选择实际 cost 更高的动作；
3. episode 结束后 realized `Σc_c` 推高 `λ`；
4. actor 再在有偏 Q landscape 上响应更大的 `λ`。

这可产生 λ 上升、cost 不降、actor loss 看似改善的错位。TD3 的 twin minimum 旨在限制 overestimation，但 deep function approximation error 并未被理论消除 [Fujimoto et al., ICML 2018]。

**诊断边界**：§7 的 `Bellman-residual mean Q4 > 1.25×Q1` 只能认定 **value-estimation failure**。若日志不是 signed residual，仅凭 residual magnitude 不能把它进一步命名为 overestimation。要声称 overestimation，应看到 reward-Q 的 signed `Q−target>0`（或等价的 cost-Q 低估）以及/或者 growing twin-Q gap。

#### 4.2.6 slew limiter 的作用

执行 action 可抽象为

$$
a_t^{exe}=\Pi_{\mathcal A(a_{t-1}^{exe})}(a_t^{raw}),
$$

其中 feasible set 同时含 `[-1,1]` 与每步 `0.25` rate bound。

R419 把 previous executed action 加入 actor state，并对齐 target/online post-projection semantics，修复了关键 Markov/state mismatch；但以下问题仍存在：

- projection active 时，`∂a^{exe}/∂a^{raw}` 可为 0，边界处不可微；
- frequency consequence 有 plant delay，`λ` 只在 episode 后看到 aggregate effect；
- `λ` 不直接看到 action RMS/TV；
- per-step slew bound 只能给 `|Δa|≤0.25`，不推出 `TV≤1.10×reference`，因为 reference 的 TV 可能远小于该物理上界；
- raw action 频繁撞 projection 可造成 executed action 的高 TV 或长期高幅值，而 common frequency cost未必等比例变化。

因此 slew-aware state repair 是 necessary representation repair，但不是 action-stress constraint。

---

### 4.3 A2.3：frequency-only Lagrangian 为什么不能绑定 action-stress？

#### 4.3.1 非 coercivity 命题

在某条 nominal trajectory 附近，令 `\mathcal G` 表示 executed action sequence 到 frequency/RoCoF trajectory 的局部 input–output Jacobian。若存在非零方向 `v` 满足

$$
\mathcal Gv=0
\quad\text{或}\quad
\|\mathcal Gv\|\ll\|v\|,
$$

则沿 `u+αv` 增加动作可以显著提高 action RMS/TV，而 frequency-only cost 几乎不变。于是不存在仅由 frequency cost 自动推出的 action norm bound，除非另行证明 `\mathcal G` 对所有可行动作方向具有统一的 lower singular-value / coercivity bound。

在多 agent、parameter modulation、network redundancy、saturation 与 slew projection 下，这种全局 coercivity 没有被材料建立；因此 frequency Lagrangian 对 action-stress 无保证。

这是结构性命题，不要求存在精确 nullspace：near-null directions 已足以让 reference-relative `1.10×` guard 失败。

#### 4.3.2 固定 `effort` 不是 dual variable

R420/R422 的 `1.0·effort` 是固定 regularizer。真正的 RMS constraint dualization 应包含三部分：

1. 与 guard 同定义的 constraint statistic；
2. reference-relative threshold；
3. 根据 constraint residual 自适应更新的 multiplier。

例如对 profile `p`，令 `a^{gate}` 表示 **guard 实际读取的 action trace**：若 gate 用 executed normalized action，则 `a^{gate}=a^{exe}`；若 gate 用 decoded `(ΔM,ΔD)`、逐 VSG 值或其他聚合，必须原样采用其单位与 aggregation，不能用 reward 中的 normalized norm 代替。于是：

$$
g_{RMS}(\tau,p)
=RMS^2(a^{gate};\tau)
-[1.10\,RMS_{ref}(p)]^2,
$$

$$
g_{TV}(\tau,p)
=TV(a^{gate};\tau)
-1.10\,TV_{ref}(p).
$$

理论上的 vector Lagrangian 应写成

$$
\boxed{
\mathcal L
=J_d
+\lambda_c G_c
+\mu_{RMS}G_{RMS}
+\mu_{TV}G_{TV}
+\cdots
}
$$

并有

$$
\mu_{RMS}^{k+1}
=\Pi_+\left[
\mu_{RMS}^k+\beta_k g_{RMS}(\tau_k,p_k)
\right],
$$

$$
\mu_{TV}^{k+1}
=\Pi_+\left[
\mu_{TV}^k+\beta_k g_{TV}(\tau_k,p_k)
\right].
$$

所以更精确的回答是：

> 当 guard 与 reward 使用同一 executed normalized trace 时，`mean_i||a_i||²` 才是与 RMS numerator 直接相关的 **constraint feature**；固定权重 `1.0` 仍不是缺失的 dual variable。缺失的是与 frozen RMS threshold、单位和 aggregation 严格对齐的 `μ_RMS`，而 TV 还需要独立的 `μ_TV`。

#### 4.3.3 multiplier 应 shared 还是 per-agent？何时更新？

| Guard 结构 | 理论 multiplier 结构 | 合理更新时间 |
|---|---|---|
| 全局 joint action RMS | 一个 shared `μ_RMS` | episode end；RMS² 可由逐步平方和累计 |
| 全局 joint action TV | 一个 shared `μ_TV` | episode end；previous executed action 已使 increment 可累计 |
| per-VSG RMS/TV | `μ_{RMS,i}`, `μ_{TV,i}` | episode end |
| worst-unit peak/RoCoF | per-unit constraints 或 epigraph/max formulation | peak statistic完成后；若要求 almost-sure/instantaneous，需要 running-max state、pointwise 或 risk formulation |
| every-profile reference-relative guard | per-profile vector multiplier或 robust/chance/CVaR formulation | 按 profile episode 更新；不能由跨 profile average 代替 |
| every-training-seed canary | 这是 training-algorithm reliability criterion，不是单 policy CMDP constraint | 需要跨 seed evaluation；普通 trajectory dual 无法直接保证 |

“per-step 更新 multiplier”只有在 constraint residual 本身是 per-step/instantaneous 且定义一致时才自然。对 episode RMS/TV/peak，episode-level update并不错误；应优先保证 objective functional 一致与 timescale separation，而不是机械提高更新频率。

#### 4.3.4 对冻结实验的边界

上述 notation 是对 **下一非冻结决策点和论文 theory section** 的结构建议，不是修改 R421/R422 的指令。当前 frozen runs 应按预注册协议完成。

---

### 4.4 A2.4：用 R421 per-update log 区分三个解释

#### 4.4.1 对齐 §7 的诊断表

§7 的冻结 readout 会强制给出四类之一；其中没有“objective-to-gate mismatch”这一类。因此，winning class 识别的是 **training-side proximal pathology**，而 wrong-level 是把 training residual、`λ` 与 final guards 联合起来得到的 **cross-layer inference**。两者可以同时成立。将 optimization、value estimation 与 sampling/coverage 分开诊断的总体方法与 Fu et al., ICML 2019 的 bottleneck decomposition 一致，但本文严格服从 §7 已冻结的阈值和类别。

| 候选解释 | §7 中应出现的主要 observable | λ / realized cost 的辅助表现 | 能否被该 observable 证伪 |
|---|---|---|---|
| **λ at the wrong level / objective-to-gate mismatch**：training surrogate被控制，但它不是 gate | §7 没有一对一 class；四个 pathology ratio 单独都不能确认或排除它 | `λ` 有界，training residual `Σc_c−3` 接近 0 或为负，但 final action RMS/TV、peak 等 guard仍失败；guard residual 与 λ/training residual脱钩 | 若 training residual长期严重为正、`λ` clip，且 winning class 显示强 actor/Q/coverage pathology，则不能把 wrong-level写成唯一主因；但 metric mismatch仍客观存在 |
| **actor fails to optimize/respond to constrained objective** | winning class 为 `policy stagnation`：`actor gradient-norm mean Q4 < 0.5×Q1` | λ 上升或触顶，但 executed actions与 `c_c` 对 λ 的变化不敏感 | actor grad稳定不等于 policy class一定可表示 optimum；严格“representation insufficiency”不能仅靠现有日志完全证明 |
| **Q/value estimation dominates** | winning class 为 `value-estimation failure`：`Bellman-residual mean Q4 > 1.25×Q1`；可能伴随 critic optimization异常 | actor loss/Q看似改善，realized `c_c` 不改善，λ 被动上升 | 若 Bellman residual未触发且 signed bias不正，则 overestimation解释被削弱 |
| **optimization failure（critic）** | winning class 为 `optimization failure`：`critic_loss Q4 > 3×Q1` | Q/actor/λ 可一起变得不稳定 | 若该 frozen rule 未获胜则不应把它作为首要 §7 机制 |
| **exploration collapse** | winning class 为 `exploration collapse`：`TD-error std` 或 `sampled-state-variance Q4 < 0.5×Q1` | actor grad下降可能是coverage问题而非policy optimum | 若该 frozen rule 未获胜则不应把它作为首要 §7 机制 |

#### 4.4.2 一个重要的可识别性限制

R421 的 frozen observables 能较好地区分：

- critic optimization failure；
- generic value-estimation failure；
- policy stagnation；
- exploration collapse。

但它不能严格区分：

- actor 已收敛到 policy-class 内局部 optimum；
- decentralized deterministic actor class 根本不包含 constrained optimum。

后者需要 policy-class feasibility/KKT residual 或更直接的 `action sensitivity to λ` 检查。现有日志中可用的最接近 proxy 是：`λ` 明显变化时，actor gradient 和 executed action distribution 是否仍几乎不变。本文不据此提前选择 §7 的 B 类别。

#### 4.4.3 A2 的可证伪预测

1. **支持 wrong-level/objective-to-gate gap**：无论 §7 最终选中哪一类，只要 `λ` 有界、training residual `Σc_c−3` 接近 0 或为负，而 action RMS/TV、peak 等 guard仍失败，就直接支持“training constraint 与 gate 不同层级”。若 winning class 的异常幅度很强，则应写成 **structural mismatch 与 training pathology 并存**，而不是把前者写成唯一机制。
2. **支持 actor-side failure**：frozen winning class 为 policy stagnation，且 λ 上升时 executed action/cost 对其不响应；Bellman residual与coverage没有更强的 competing signal。该结果支持“actor未响应”，但现有日志仍不能严格区分局部停滞与 policy-class representation insufficiency。
3. **支持 Q-dominant failure**：frozen winning class 为 value-estimation failure；若还要称为 overestimation，必须有 signed positive reward-Q residual、cost-Q低估或等价证据。
4. **若 winning class 为 exploration collapse 或 critic optimization failure**：按冻结 §7 decision tree 进入相应后续问题，不在 A2 中越级指定更细机制；objective-to-gate mismatch 仍作为独立的定义层事实保留。

#### 4.4.4 A2 一句话 verdict

> **当前 Lagrangian 只可能约束一个与 `c_c` 对齐的 expected surrogate；由于 metric、risk、reference、population、discounting 和 omitted-action constraints 均与 canary 不一致，它在理论上不具备推出 guard compliance 的充分条件。**

---

## 5. R421/R422 落地后的无歧义读取顺序

以下只要求读取已冻结产物，不改变 run。

### 5.1 先读 R422 的实现语义、`λ` 与 budget，而不是先看“通道标签”

先核对 dual update 读取的是 modified `c_c^0+effort` 还是 base `c_c^0`。随后按顺序计算：

1. `median/mean λ` at actor updates；
2. `λ=0` 与 `λ=10` clip fractions；
3. `Σ_t c_c^0`、`Σ_t effort`，以及在 modified-cost 语义下的 `Σ_t(c_c^0+effort)`；
4. normalized scalar action RMS；只有 dual 读取 modified cost 时，才与 sample-budget 必要界 `0.2236` 对照；
5. `η_d^a`，如数据允许再算 `η_d^{phys}`；
6. `χ_a` proxy：`λ` 与 executed RMS / equivalent forcing magnitude 的局部响应；
7. 可由 existing logs / small-signal model得到时，报告 `K_E,K_G`；任何额外 action-scale evaluation 只作为 post-hoc，不进入 canary；
8. slew-active 与 saturation fractions。

读取规则：

- **R422 优于 R420且 `λ_eff<1`**：结论优先写成“effective effort weight reduced”，不是“common mode正确”。
- **R422 差于/等于 R420且 `λ_eff>1` 或 clip**：支持 over-regularization；只有 dual 读取 modified cost 且 effort 显著占用预算时，进一步称为 budget-dominant。
- **R422 与 R420不同但 `λ≈1`**：查看 critic-head Bellman residual/scale；差异更可能来自 approximate decomposition，而非 modal routing。
- **R422 action RMS改善但 TV仍失败**：符合 `||a||²` 只对应 magnitude、不对应 variation 的理论预测。

### 5.2 再把 R421 读成“优化层是否正常”

1. 先应用冻结四分类阈值和 winning-class 规则，不改优先级或阈值；
2. 独立检查 `λ` 是否有界、training residual 是否接近 0，以及 guard residual 是否仍大；这一步判定 objective-to-gate mismatch，可与任一 winning class 并存；
3. 若 winning class 为 value-estimation failure：只称 generic value failure，除非有 signed bias；
4. 若 winning class 为 policy stagnation：检查 λ 变化与 action response；
5. 若 winning class 为 exploration collapse / optimization failure：保留 §7 的机制问题，不在论文中把 R420/R422 单独解释成 reward-theory结论。

### 5.3 建议生成的 post-hoc 表

| arm/seed/profile | endpoint ratios | message increment | guard failures | `median λ` | λ clip | `Σc_c^0` | `Σeffort` | `η_d^a` | `χ_a` proxy | `K_E/K_G` proxy | slew-active | saturation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

该表能把“物理 modal action”“effective regularization strength”“dual feasibility”“value failure”四个解释轴分开。

---

## 6. 可直接用于论文/agent 的表述

### 6.1 推荐的核心论断

> The frozen action-effort term is a total executed-action norm rather than a modal control-energy term. Under the orthonormal frame used for evaluation, it decomposes exactly into common-coordinated and differential action components. Moreover, the nominal common-channel cost contains differential frequency and RoCoF energy. Consequently, moving the same effort term from `c_d` to `c_c` does not constitute pure physical modal routing: it changes the effort coefficient from `1` to the learned multiplier `λ`, changes the critic-head decomposition, and—if the dual update reads the modified `c_c^{422}`—makes effort consume the common episodic budget.

> The guard failures are not inconsistent with constrained-MDP theory. The dual update targets an expected episodic quadratic surrogate, whereas the canary requires reference-relative peak, IAE, action RMS and total-variation conditions on every evaluation block. No implication from the former feasible set to the latter is established; action-stress metrics are absent from the constraint altogether.

### 6.2 不应写入论文的过强表述

- 不要写：“R422 证明 action effort 应属于 common mode。”
- 不要写：“differential-channel penalty 直接惩罚 differential action。”冻结 penalty 是 total action norm。
- 不要写：“shared λ 导致 multi-agent constraint failure。”一个 joint constraint 配一个 shared λ 本身正确。
- 不要写：“固定 effort weight 就是 action-stress 的 dual variable。”它没有 threshold residual，也不覆盖 TV。
- 不要写：“Bellman residual 上升证明 TD3 overestimation。”没有 signed bias 时只能叫 value-estimation failure。
- 不要写：“endpoints 改善意味着 safety/no-harm 改善。”canary 明确把 guard barrier 与 endpoint ranking 分开。

### 6.3 最短决策摘要

1. **R420 的坏结果与“过度惩罚 useful differential authority”一致，但不是唯一机制。**
2. **R422 的比较必然被 `λ` 与 critic-head 归属 confounded；若 dual 读取 modified cost，还被 budget confounded。先读实现语义和 λ，再读 endpoints。**
3. **当前 `c_c` 不是纯 common mode，当前 `effort` 也不是 pure differential/common action。**
4. **action-stress 需要独立、reference-aligned 的 RMS/TV constraint statistics 和 multipliers；固定 effort 只是一项 regularizer。**
5. **无论 R421 选中哪一类，只要 training surrogate 已被控制而 guards 仍失败，objective-to-gate mismatch 都成立；winning class 再解释并存的 training-side pathology。**

---

## 7. 给 agent 的执行清单（不修改 frozen runs）

- [ ] 保留 R421/R422 frozen protocol 与预注册判据，不重跑参数搜索。
- [ ] 在结果解析代码中加入 `c_c` 的 exact common/differential decomposition。
- [ ] 对 executed action trace 计算 `η_d^a`；有足够状态/decoder数据时计算 `η_d^{phys}`。
- [ ] 从 existing logs 估计 `χ_a`；可由小信号模型得到时报告 `K_E,K_G`。额外 action-scale evaluation 必须标为 post-hoc，不能进入 sealed canary。
- [ ] 核对 R422 的 dual update 究竟读取 modified `c_c^0+effort` 还是 base `c_c^0`；只报告实际代码语义，不从 brief 的命名反推实现。
- [ ] 若 dual 读取 modified `c_c^{422}`，报告 actor-update 时的 `λ` 分布、clip fraction 与 `Σeffort` budget share；若读取 base `c_c^0`，将 R422 标为 multiplier-weighted、但非 budget-coupled。
- [ ] 明确检查 critic 的 discounted objective 与 dual 的 undiscounted residual，不把它们称为严格同一个 saddle problem。
- [ ] 将 R421 frozen winning class 与 “wrong-level / actor / Q” 的跨层解释表自动化输出；不要把 winning class 本身误当成 objective-to-gate mismatch 已被排除。
- [ ] 只有在 dual 确认读取 modified `c_c^{422}` 时，才把 R422 称为 **multiplier-weighted, budget-coupled effort placement**；否则称为 **multiplier-weighted critic-head placement**。两种情况都避免称为纯 common-mode penalty test。
- [ ] 核对 action RMS/TV guard 使用 normalized executed、decoded `(ΔM,ΔD)` 还是其他 trace；下一非冻结 formulation 必须复用完全相同的单位与 aggregation。
- [ ] 下一非冻结 theory formulation 中，把 action RMS 与 TV 写成两个独立 guard-aligned constraints；是否实现由 owner 决定，不影响当前 runs。

---

## 8. References

1. **Paganini, F.; Mallada, E.** “Global Analysis of Synchronization Performance for Power Systems: Bridging the Theory-Practice Gap.” *IEEE Transactions on Automatic Control*, 65(7):3007–3022, 2020. DOI: `10.1109/TAC.2019.2942536`. 相关结论：在参数 proportionality 条件下分解 system-wide frequency 与 residual；connectivity 增强时 aggregate model 更准确。
2. **Poolla, B. K.; Bolognani, S.; Dörfler, F.** “Optimal Placement of Virtual Inertia in Power Grids.” *IEEE Transactions on Automatic Control*, 62(12):6209–6220, 2017. DOI: `10.1109/TAC.2017.2703302`. 相关结论：linear network-reduced model 中 virtual inertia placement 与 coherency/H2 performance 依赖网络结构，优化一般非凸。
3. **Dörfler, F.; Bullo, F.** “Synchronization and Transient Stability in Power Networks and Nonuniform Kuramoto Oscillators.” *SIAM Journal on Control and Optimization*, 50(3):1616–1642, 2012. DOI: `10.1137/110851584`. 相关结论：网络参数、异质时间常数与 coupling 对同步的结构作用。
4. **Ademola-Idowu, A.; Zhang, B.** “Optimal Design of Virtual Inertia and Damping Coefficients for Virtual Synchronous Machines.” *2018 IEEE Power & Energy Society General Meeting (PESGM)*, 2018, IEEE document 8586187. 相关结论：virtual inertia/damping 的 regularized H2 design 显式形成 nadir、RoCoF、settling 等 competing objectives。
5. **Altman, E.** *Constrained Markov Decision Processes*. Chapman & Hall/CRC, 1999. 相关结论：CMDP 的 expected cumulative/average constraints、Lagrangian 与 randomized policies 基础。
6. **Achiam, J.; Held, D.; Tamar, A.; Abbeel, P.** “Constrained Policy Optimization.” *Proceedings of the 34th International Conference on Machine Learning*, PMLR 70:22–31, 2017. 相关结论：expected-return constraints 下的 near-constraint satisfaction bound，条件不同于 almost-sure peak guard。
7. **Chow, Y.; Ghavamzadeh, M.; Janson, L.; Pavone, M.** “Risk-Constrained Reinforcement Learning with Percentile Risk Criteria.” *Journal of Machine Learning Research*, 18(167):1–51, 2018. 相关结论：chance/CVaR constraints 与 expected cumulative cost 的区别及对应 Lagrangian methods。
8. **Bhatnagar, S.; Lakshmanan, K.** “An Online Actor–Critic Algorithm with Function Approximation for Constrained Markov Decision Processes.” *Journal of Optimization Theory and Applications*, 153:688–708, 2012. DOI: `10.1007/s10957-012-9989-5`. 相关结论：在 long-run average CMDP 与 stochastic-approximation 条件下的局部 almost-sure convergence。
9. **Stooke, A.; Achiam, J.; Abbeel, P.** “Responsive Safety in Reinforcement Learning by PID Lagrangian Methods.” *Proceedings of the 37th International Conference on Machine Learning*, PMLR 119:9133–9143, 2020. 相关结论：标准 multiplier update 的 integral-control 解释，以及 oscillation/overshoot。
10. **Moskovitz, T.; O’Donoghue, B.; Veeriah, V.; Flennerhag, S.; Singh, S.; Zahavy, T.** “ReLOAD: Reinforcement Learning with Optimistic Ascent-Descent for Last-Iterate Convergence in Constrained MDPs.” *Proceedings of the 40th International Conference on Machine Learning*, PMLR 202:25303–25336, 2023. 相关结论：普通 gradient descent-ascent 可在 average 意义收敛而 last iterate 持续在 reward/constraint 间振荡。
11. **Fujimoto, S.; van Hoof, H.; Meger, D.** “Addressing Function Approximation Error in Actor-Critic Methods.” *Proceedings of the 35th International Conference on Machine Learning*, PMLR 80:1587–1596, 2018. 相关结论：actor–critic 中 function approximation error 与 overestimation；twin minimum/target delay 用于缓解而非证明消除。
12. **Fu, J.; Kumar, A.; Soh, M.; Levine, S.** “Diagnosing Bottlenecks in Deep Q-learning Algorithms.” *Proceedings of the 36th International Conference on Machine Learning*, PMLR 97:2021–2030, 2019. 相关结论：通过分解 optimization、value estimation、sampling/coverage 等因素诊断 deep Q-learning bottlenecks。
13. **Sootla, A.; Cowen-Rivers, A. I.; Jafferjee, T.; Wang, Z.; Mguni, D. H.; Wang, J.; Ammar, H.** “Saute RL: Almost Surely Safe Reinforcement Learning Using State Augmentation.” *Proceedings of the 39th International Conference on Machine Learning*, PMLR 162:20423–20443, 2022. 相关结论：almost-sure safety 需要把 safety budget/state 纳入 Markov state 与 objective，而非仅依赖普通 expected cost。
14. **Tabas, D.; Zamzam, A. S.; Zhang, B.** “Interpreting Primal-Dual Algorithms for Constrained Multiagent Reinforcement Learning.” *Proceedings of the 5th Annual Learning for Dynamics and Control Conference*, PMLR 211:1205–1217, 2023. 相关结论：standard C-MARL penalty 只给较弱 safety notion；chance/CVaR 需要不同 penalty interpretation。

---

## Appendix A — 可直接复用的公式索引

### A.1 State modal decomposition

$$
q_0=\frac12\mathbf1_4,
\quad U=[q_0^T;T],
\quad q_0^Tx=2c(x),
\quad z=Tx.
$$

### A.2 `c_c` exact decomposition

$$
c_c=
\frac{c(x)^2}{\sigma_f^2}
+\frac{\|z\|^2}{4\sigma_f^2}
+\frac{c(r_f)^2}{\sigma_{rocof}^2}
+\frac{\|Tr_f\|^2}{4\sigma_{rocof}^2}.
$$

### A.3 Action effort exact decomposition

$$
e_t=\frac14\|A_t\|_F^2
=\frac14\|q_0^TA_t\|_F^2
+\frac14\|TA_t\|_F^2.
$$

### A.4 Modal M/D cross blocks

$$
UMU^T=
\begin{bmatrix}
mean(m)&\frac12(Tm)^T\\
\frac12Tm&Tdiag(m)T^T
\end{bmatrix},
$$

`D` 同理；cross blocks 消失 iff `Tm=Td=0`。

### A.5 Physical action forcing proxy

$$
r_t=diag(\dot x_t)\Delta m_t+diag(x_t)\Delta d_t,
\qquad
\eta_d^{phys}=\frac{\sum_t\|Tr_t\|^2}{\sum_t\|r_t\|^2}.
$$

### A.6 R420/R422 difference

$$
L_{R420}=J_d+J_e+\lambda J_c^0,
\quad
L_{R422}=J_d+\lambda J_c^0+\lambda J_e,
\quad
L_{R422}-L_{R420}=(\lambda-1)J_e.
$$

### A.7 R422 necessary budget condition

$$
\frac1{30}\sum_t effort_t\le0.1,
\qquad
RMS_{normalized\ scalar}\le0.2236
\quad(c_c^0=0\text{ 的最宽松 sample-budget 情况}).
$$

若 dual 表示 expected CMDP constraint，则只得到相应的期望二阶矩界，不得到逐轨迹 RMS 硬界。

> 本节还以 dual update 实际读取 modified `c_c^0+effort` 为条件；若代码读取 base `c_c^0`，该 budget condition 不适用。

### A.8 Guard-aligned action constraints

$$
g_{RMS}=RMS^2(a^{gate})-(1.10RMS_{ref})^2,
$$

$$
g_{TV}=TV(a^{gate})-1.10TV_{ref}.
$$

---

## Appendix B — 最终可证伪命题清单

1. 若 R422 的两个 endpoint ratios 相对 R420改善，但 `λ_eff<1`，则改善主要支持 **lower effective effort weight**，不单独支持 modal common placement。
2. 若 dual 读取 modified cost，且 R422 `λ` 高频 clip at `10`、`Σeffort` 单独已接近/超过 `3`，则 endpoint恶化支持 **budget-dominant over-regularization**。
3. 若 `η_d^a` 与 `η_d^{phys}` 都低，则“R420惩罚了 useful differential action”解释被削弱。
4. 若 R421 所有 failure thresholds均不触发，而 action-stress仍全失败，则 **wrong-level / omitted constraints** 获得最强支持。
5. 若 Bellman residual threshold触发但没有 signed positive bias，则只能报告 **value-estimation failure**，不能报告 overestimation。
6. 若 actor gradient collapse且 λ 上升时 executed action不变，则支持 actor-side stagnation；若 sampled-state variance也collapse，应按冻结规则优先保留 exploration-collapse 解释。
7. 即使 R422 action RMS改善，TV仍可失败；若 TV也稳定改善，则说明 magnitude regularization通过 slew dynamics产生了额外间接效应，而非理论必然。
8. 两个 endpoint改善不推出 CANARY-PASS；只有所有 36 blocks 的所有 guards通过才构成 canary success。
