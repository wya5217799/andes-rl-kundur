# R485 有限记录 TV/RMS 机制审计

## 结论

**总体处置：`QUALIFIED-DESCRIPTIVE-ONLY`。**

现有包足以给出一个可重放的、非光滑安全的有限记录证书，但不足以把两句现有机制语言解释成闭环或训练因果结论：

- “previous-action feedback amplifies TV” 按当前无修饰写法为 **`CURRENT-LANGUAGE-FAILS`**。可保留的内容是：在冻结观测的固定 24-policy、单 profile 网格上，把 actor 的两个 previous-action 输入槽替换为各 record 内均值后，48/48 个 channel-policy 单元的 raw-TV 仅保留实际值的 7.10%--20.46%。这是一项 actor-input 路径对比，不是闭环 feedback 因果效应。
- “a quasi-static actor setpoint retains RMS” 作为普遍机制或“dominant source”同样失败；作为明确定义的有限网格范数描述可以改写。固定 24-policy × 4-profile 网格中，constant-anchor/actual raw-RMS 在 141/192 个单元达到至少 0.90；M 为 54/96，D 为 87/96。它只表示聚合二范数接近，不表示输出随时间近似常数、anchor 接近时间均值，或 RMS 有唯一/主要来源。

固定 headline 未重判：121/208 endpoint-qualified，0/208 complete-contract。

## 来源与能力边界

- 精确输入 ZIP：`gpt_pro_r485_mechanism_math_20260901.zip`
- 实算 SHA-256：`530ed9942169f620c88ee14138d263a9271516b8366e1296006002378fe41410`
- 包 ID：`gpt_pro_r485_mechanism_math_20260901`
- ZIP 成员：31；manifest 载荷：30；全部大小与 SHA-256 匹配。
- 代表性对象：`an_cn_r0`, seed 501, final checkpoint，四个 profile、每个 6 records × 150 steps × 4 agents。
- 所有 ablation 均保留 sealed observations；没有 modified-controller plant observations，也没有随机抽样设计。

数值证书把存储的 float32 权重和输入解释为实系数，以 float64 做 ReLU 路径分割；路径根容差为 `1e-13`，并以 `1e-6` 将实网络端点绑定回生产 float32 actor。它不是区间算术或形式化证明；代数命题本身独立于该浮点实现。

---

## S1 — projector 与 TV/RMS

### 1. 标量投影器的等价形式

对任一分量，因 actor 的 `tanh` 已给出 `p,r∈[-1,1]`，外层 amplitude clip 在实数模型中冗余，故

\[
P_\delta(p,r)
=p+\operatorname{clip}_{[-\delta,\delta]}(r-p)
=\operatorname{clip}_{[p-\delta,p+\delta]}(r)
=\operatorname{med}(r,p-\delta,p+\delta).
\]

因此 `Pδ(p,r)` 总位于 `p` 与 `r` 之间，并有

\[
|P_\delta(p,r)-p|=\min\{|r-p|,\delta\},\qquad
|r-P_\delta(p,r)|=(|r-p|-\delta)_+.
\]

中位数对各输入在 `ℓ∞` 下是 1-Lipschitz，所以

\[
|P_\delta(p,r)-P_\delta(q,s)|
\le \max\{|p-q|,|r-s|\}.
\]

特别地，固定 previous action 时对 raw action 非扩张；固定 raw action 时对 previous action 也非扩张。分量求和或平方和即可得到相应向量界。

### 2. 递归投影器不是逐步差分收缩器

若两条 raw 路径从同一初值出发，上式递归给出

\[
\max_{k\le t}|p_k-\tilde p_k|
\le \max_{k\le t}|r_k-\tilde r_k|.
\]

但不能推出 `|p_t-p_{t-1}|≤|r_t-r_{t-1}|`。当 raw action 先发生超过两个 slew steps 的跃迁、随后保持不变时，projected action 会继续追赶：该时刻 raw increment 为零而 projected increment 非零。projector 会把 variation 延后和重新分配，而不是逐时刻消灭它。

### 3. 最强的递归 TV 不等式

对单个 record-agent-channel track，令

\[
V_t(x)=\sum_{k=0}^{t}|x_k-x_{k-1}|,
\qquad r_{-1}=p_{-1}=0.
\]

因为 `p_t` 位于 `p_{t-1}` 与 `r_t` 之间，

\[
|p_t-p_{t-1}|+|r_t-p_t|=|r_t-p_{t-1}|.
\]

归纳证明：若 `V_{t-1}(p)+|r_{t-1}-p_{t-1}|≤V_{t-1}(r)`，则

\[
\begin{aligned}
V_t(p)+|r_t-p_t|
&=V_{t-1}(p)+|r_t-p_{t-1}|\\
&\le V_{t-1}(p)+|r_{t-1}-p_{t-1}|+|r_t-r_{t-1}|\\
&\le V_t(r).
\end{aligned}
\]

所以对每个 channel 汇总所有 records 和 agents 后，

\[
\operatorname{TV}_c(p)
+\sum_{n,i}|r_{n,T-1,i,c}-p_{n,T-1,i,c}|
\le \operatorname{TV}_c(r).
\]

这比“单步 map 非扩张”强：它直接证明生产 projector **不能增加本项目定义的累计 channel TV**。源码中的 conservative float32 `nextafter` 只把可能越过 slew 边界的舍入值向 previous action 拉回，仍保持区间性质；附带 checker 又在八个代表性 profile-channel 路径上逐一验证了该不等式。

代表性四 profile 的 projected/raw TV 比为 0.36065--0.44417，raw 与 projector replay 最大误差均为 0。它们量化了这些 sealed paths 上的严格 attenuation；`1-ratio` 不能解释成“projector 的机制份额”。

TV 命题也没有 RMS 推论。代表性 `canary_eval_d` 的 D channel 中，projected RMS 反而高于 raw RMS；因此 projector 可降低累计 TV，同时因状态记忆改变 RMS。

**S1 处置：`CERTIFIED-BOUNDED-MECHANISM`，仅限给定 projector、TV 定义和记录重置。**

---

## S2 — additive decomposition 不可识别

令 `J` 为某个 channel 的 RMS 或 TV，定义两个二元因素：

- `O=1/0`：actual observations / within-record mean observations；
- `P=1/0`：actual previous-action inputs / within-record mean previous-action inputs。

四个应有单元为

\[
v_{00}=C,\quad v_{10}=F,\quad v_{01}=B,\quad v_{11}=A,
\]

其中现有 full-grid 数据给出 `A,F,C`，但缺少 `B`（fixed observations + actual previous inputs）。标准 Möbius 分解是

\[
\alpha_O=F-C,\quad
\alpha_P=B-C,\quad
\alpha_{OP}=A-F-B+C,
\]

且 `A-C=α_O+α_P+α_OP`。只要把未知 `B` 改为另一个可行值，`α_P` 与 interaction 就同时变化，而已观测的 `A,F,C` 完全不变。因此不存在由三个单元唯一决定的 additive mechanism decomposition。

同理，对称 Shapley allocation

\[
\phi_O=\tfrac12[(F-C)+(A-B)],\qquad
\phi_P=\tfrac12[(B-C)+(A-F)]
\]

也依赖缺失的 `B`。`A-C=(A-F)+(F-C)` 是精确的 ordered telescoping contrast，但它把 interaction 全部按所选顺序分配，不能冒充唯一贡献。

### Range-only sharp bounds

若只知道 `B∈[L,U]`，则

\[
\frac{F-C+A-U}{2}\le\phi_O\le\frac{F-C+A-L}{2},
\]

\[
\frac{A-F+L-C}{2}\le\phi_P\le\frac{A-F+U-C}{2}.
\]

在当前 bounded sequence class 中：

- raw RMS：`L=0, U=1`；
- raw channel TV：`L=0, U=6×4×(1+149×2)=7176`；
- projected channel TV 另有 slew-only 上界 `6×4×150×0.25=900`。

这些界在仅使用幅值/长度信息时是 sharp 的，但通常很宽。若要得到 actor-specific 更窄界，必须读取缺失 checkpoint/path 或提供经验证的网络约束；不能从 `A,F,C` 猜出。

### 可用但必须声明的替代物

1. **Metric contrast bounds**：RMS 是归一化二范数，TV 是带固定零初值的半范数，因此
   \[
   |\operatorname{RMS}(x)-\operatorname{RMS}(y)|\le\operatorname{RMS}(x-y),
   \qquad
   |\operatorname{TV}(x)-\operatorname{TV}(y)|\le\operatorname{TV}(x-y).
   \]
   checker 对每个代表性 profile/channel 计算并验证这些界。
2. **代表性 declared Shapley**：完整 checkpoint/traces 允许重构代表性 `B`，也允许用 `A,F,E,I` 对 previous-input 与 projector 做一个完整 2×2 表。`math_result.json` 给出这些 allocation；它们只是指定基线和顺序平均后的 frozen-path accounting，不是物理或训练因果份额。
3. **full-grid extension**：其余 23 checkpoints/traces 不在包内，故 full-grid 四单元 allocation 为 `DATA-UNDECIDABLE`。

**S2 处置：`QUALIFIED-DESCRIPTIVE-ONLY`；唯一 additive mechanism decomposition 被证明不可识别。**

---

## S3 — ReLU–tanh previous-input 路径证书

### 1. 非 kink 点的 Jacobian

写四个 hidden matrices 为 `W1,…,W4`，mean head 为 `W5`，`W1,P` 为第一层对应两个 previous-action slots 的列。若所有 hidden preactivations 非零，则

\[
J_P\pi(x)
=D_{\tanh}W_5D_4W_4D_3W_3D_2W_2D_1W_{1,P},
\]

其中 `Dℓ=diag(1_{zℓ>0})`，`D_tanh=diag(1-π(x)^2)`。

在 ReLU kink `z=0`，方向导数不是任选一个普通 Jacobian；必须递归使用

\[
D\operatorname{ReLU}(z;\dot z)=
\begin{cases}
\dot z,&z>0,\\
0,&z<0,\\
\max(\dot z,0),&z=0.
\end{cases}
\]

Clarke generalized Jacobian 可由各 kink 对角元取 `[0,1]` 的矩阵乘积凸包作外包，但一个固定 active-set Jacobian 不能跨越多个 kink 使用。

### 2. 精确的分段路径量

对每个 sealed state，固定 observation，并沿 previous inputs 到 record 内均值 anchor 的直线

\[
x(s)=[o;(1-s)p+s q],\qquad 0\le s\le1.
\]

有限 ReLU 网络在该线段上存在有限分割 `0=s0<…<sK=1`，使每段 mean head 都是仿射函数

\[
\mu_c(s)=a_{k,c}s+b_{k,c}.
\]

因为 `tanh` 在每段单调，定义

\[
C_c(x,p,q)=
\sum_{k=0}^{K-1}
\left|	anh(a_{k,c}s_{k+1}+b_{k,c})-	anh(a_{k,c}s_k+b_{k,c})\right|.
\]

则

\[
|\pi_c(o,q)-\pi_c(o,p)|\le C_c(x,p,q).
\]

`C_c` 是该一维 actor path 的总变差，而不是只在起点线性化；折点由相邻单侧仿射段显式处理。若 `p≠q`，可报告有限路径 gain `C_c/||q-p||_2`。

### 3. 代表性执行结果

checker 对 14,400 个 state segments 全部构造路径分割：

- 14,398/14,400 条线段跨越至少一个 hidden kink；每条路径的 hidden-linear piece 数为 1--333，中位数 42；
- 存储点上没有 float64 重构的精确零 preactivation，但有 1 个绝对值不超过 `1e-7`，最小 margin 为 `7.49e-9`，故不应声称 active-set 鲁棒；
- previous-input local Jacobian spectral norm 的中位数为 1.7830，最大 13.0674；按权重谱范数相乘的全局上界却为 731.37--930.19，明显过松；
- kink-aware path-variation gain 的最大值为 M 7.8398、D 7.5415；
- 分段 telescoping 最大误差 `4.44e-15`，64 个固定抽样点的手写 Jacobian 与 PyTorch double autograd 最大差 `2.67e-15`；
- float64 real-network 与生产 float32 endpoint 的最大差 `5.40e-7`，纳入端点误差后所有生产输出差均满足 path bound。

这证明代表性 checkpoint 的 previous-input sensitivity 可以在 finite record 上被计算和审计；它不证明这种 sensitivity 导致 plant trajectory、endpoint 或 training outcome。

其余 23 checkpoints 的同类证书不能由 summary ratios 反推。最小缺失对象是：每个 checkpoint 的四个 actor state dict，以及对应的 canonical observations、previous-executed-action arrays 和 record boundaries。若要升级成闭环反事实，还需要不存在于本包中的 action-dependent plant transition/observation map 与 modified-controller trajectories。

**S3 处置：代表性路径为 `CERTIFIED-BOUNDED-MECHANISM`；24-policy 全覆盖为 `DATA-UNDECIDABLE`。**

---

## S4 — quasi-static RMS 语言

把 `(record,agent)` 合并为索引 `j`，每条长度为 `T`。令实际 raw action 为 `a_{j,t}`，时间均值为 `m_j`，constant-anchor actor 输出为随时间不变的 `q_j`。则精确恒等式为

\[
\operatorname{RMS}(a)^2
=\mathbb E_j[m_j^2]+\mathbb E_j\operatorname{Var}_t(a_{j,t}),
\]

\[
\operatorname{RMS}(a-q)^2
=\mathbb E_j\operatorname{Var}_t(a_{j,t})
+\mathbb E_j(m_j-q_j)^2.
\]

而

\[
\operatorname{RMS}(q)^2=\mathbb E_j q_j^2.
\]

因此 `RMS(q)/RMS(a)≈1` 只说明两个聚合能量接近。它既不控制 `Var_t(a)`，也不控制 `m-q`；由于 actor 非线性，`π(mean input)` 一般不等于 `mean π(input)`。聚合还会掩盖 record/agent/channel 异质性。

代表性八个 profile-channel 单元中，实际 raw RMS 的 temporal-variance energy fraction 为 37.45%--51.23%，尽管相应 anchor/actual RMS ratios 多数接近 1。这直接否定了“ratio near one ⇒ temporal dynamics negligible”。

full-grid 的精确有限计数为：

- 全部：141/192（73.4375%）达到至少 0.90；0/192 不高于 0.50；
- M：54/96（56.25%），median 0.91550；
- D：87/96（90.625%），median 0.98710；
- 总体范围 0.70149--1.19516，故 constant-anchor norm 有时也高于 actual norm。

可写“constant-anchor inputs retain comparable aggregate RMS in many fixed cells, especially D”；不能写“quasi-static setpoint is the dominant RMS source”。

**S4 处置：`QUALIFIED-DESCRIPTIVE-ONLY`；dominant-source 结论拒绝。**

---

## S5 — 推断分类

| 类别 | 本包支持的内容 | 不能升级为何种结论 |
|---|---|---|
| Exact replay / exact finite computation | exact package hashes；代表性 raw/projector replay；projector TV 不等式实例；固定 JSON rows 的重新汇总；给定 row multisets 下 action-cost 不变 | 不能自动成为外部复现或独立审稿 |
| Finite-grid descriptive | 24-policy profile-a previous-input ratios；24×4 RMS ratios；代表性四-profile projection/reward/intervention | 不能给 superpopulation probability、置信区间或“通常所有政策” |
| Actor-path intervention | fixed-prev raw、constant-anchor raw、recursive fixed-prev projected、straight previous-input path certificate，全部 frozen observations | 不能叫 modified controller 的 plant counterfactual |
| Unidentified | modified-controller observations/endpoints；训练原因；新增 TV loss 的效果；唯一 root cause；retraining benefit；stability/safety/hardware harm | 本包没有所需 transition map、trajectories、training interventions 或物理状态 |

24 policies 是固定的 8 arms × 3 seeds 网格，不是声明的随机样本。因此 48/48、141/192 等是有限集合的精确比例；不应附加二项抽样置信区间或人群概率解释。

reward reordering 只识别：对所给相同行 multiset，注册 action-cost 完全不变，而 combined TV 可显著变化。它不能识别“缺少 TV term 导致训练失败”或“加入 TV term 将改善结果”。

**S5 处置：`QUALIFIED-DESCRIPTIVE-ONLY`。**

---

## S6 — 最小论文替换

推荐直接采用 `manuscript_patch.tex`。它含一个 displayed equation、102 个英文 prose words，且明确使用 `post-hoc`、`frozen-observation`、`finite-grid` 与 non-causal boundary。该段应放 Discussion 或 exploratory supplement，不应成为第四项主要贡献。

不建议保留以下无修饰表达：

- `previous-action feedback amplifies TV`；
- `a quasi-static actor setpoint is the dominant source of RMS`；
- 任何 `root cause`、`closed-loop effect`、`safe intervention` 或 `training would improve` 语言。

---

## 执行验证

返回的 `verify_finite_record_certificate.py`：

1. 验证 exact ZIP SHA-256、31-member set、30 条 manifest payload hashes 与 checkpoint hash；
2. 从 checkpoint 重建四个 `GaussianActor(9,2,[128,128,128,128])`；
3. 重放四个代表性 profiles 的 raw actor 与 production projector；
4. 重算 full-grid JSON rows 的比例、分位数和计数；
5. 验证 TV residual theorem、RMS Pythagorean identities、metric contrast bounds；
6. 重构缺失代表性 factorial cell 和 declared Shapley allocations；
7. 构造全部 14,400 条 ReLU path partitions，并检查 telescoping、endpoint bounds 与 autograd；
8. 与 `math_result.json#/numerical_certificate` 做递归数值比对，失败时非零退出。

最终命令、runtime、stdout SHA-256 与 exit status 记录在 `math_result.json#/verification`。本次实际运行通过；这仍不替代项目所有者要求的独立 reconstruction/replay。
