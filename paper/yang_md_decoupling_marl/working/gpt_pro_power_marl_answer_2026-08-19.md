# 电力系统多智能体强化学习数据包：八问研究答复

**对象**：4-VSG 虚拟惯量/阻尼多智能体协调，ANDES 相量域，改进 Kundur 两区系统  
**依据**：`README.md`、`brief.md`、`feeds/R428–R432.md`、`data/*.json`、`source/v4_config.py`  
**答复日期**：2026-08-19  
**数值复核**：见同目录 `derive_numbers.py` 与 `derived_numbers.json`

---

## 0. 结论总览

| 问题 | 类型 | 核心结论 | 置信度 |
|---|---:|---|---:|
| A1 | A | R428 的主因不是缺少 `phi_abs` 或 slew 投影，而是**动作惩罚从物理量二次项到归一化小权重之间的巨大 value-scale 差异**；twin-Q 与梯度裁剪是次级稳定器。现有轮次不能给三因素精确因果份额。 | 0.90（主因排序）；0.70（因果份额） |
| A2 | A | `0.25/step` 投影只限制相邻增量，不限制长期偏置、RMS 或累计 TV。常值 0.2 已能在 TV=0 时违反全部 RMS 阈值；合法边界锯齿可达 RMS≈0.586。 | 0.99（不变集）；0.55（R431 具体波形诊断） |
| A3 | A | 乘子下降没有符号悖论：8640 个 episode 的更新恒等式误差为 0；前 18 个 episode 的平均成本均约 1.82–1.87<3，累计残差刚好把 `lambda` 从 1 推到 0。critic 发散不能直接翻转基于实测成本的 dual residual。 | 0.99 |
| M1 | M | 消息不是 common-frequency 通过的必要条件——no-message 也为 20/20；更受支持的作用是把“共同加速”与“局部/区间模态”分开，从而改善最差机组峰值和 RoCoF。 | 0.75 |
| M2 | M | total-energy 惩罚与**总 RMS 守卫**方向一致，但可能压制有益 common action；它也不直接约束 TV。是否“惩罚错模态”由 `eta_d^a` 决定，应改为 common/differential/变化率三权重而非只用一个 total 权重。 | 0.95（代数）；0.70（性能预测） |
| M3 | M | Pareto 边界可通过冻结 DAE 的轨迹灵敏度或直接配点计算；当前包缺少同一策略族的“端点—RMS/TV”成对数据，不能从 R431+R433-dev 数值定位边界。 | 0.95（框架）；0.45（当前边界位置） |
| P1 | P | 理想对称模型中，`Tm=Td=0` 是结构性精确解耦条件；非光滑执行器还要求每个活跃 PWA 单元的局部斜率向量同质。600/200 混合符号单元会把纯 differential raw action 注入 common 分量，因此全局精确模态保持一般不可能。 | 0.95（理想/PWA 命题）；0.55（真实 DAE 输出界） |
| P2 | P | 可给出强但可执行的充分条件：Markov 状态补齐投影状态、DAE 在紧集上良定、reward/log-density/alpha 有界、critic 输出与参数显式投影、目标网与 PopArt 尺度一致。此时 value 与 TD loss 有确定上界；要证明收敛还需投影 Bellman 算子收缩和多时间尺度。 | 0.98（有界性）；0.65（对深度 SAC 的收敛适用性） |

---

## 1. 证据审计与口径修正

### 1.1 证据优先级

本报告采用以下优先级：机器 JSON 的逐字段结果 > feed 的文字汇总 > brief 的压缩表述 > 机制推断。所有推断均与实测事实分开。

### 1.2 四处应在后续 seal / 论文中修正的口径

1. **R431 守卫计数存在两类文字冲突。**
   - `brief.md` 与 `feeds/R431.md` 写消息臂 action-stress 失败 16/20；但 `r431_sac_slew_formal_analysis.json#/classification/guard_failures` 给出 message 的 `action_rms_no_harm` 与 `action_variation_no_harm` 均为 20/20 失败，no-message 两项也均为 20/20 失败。
   - `brief.md` 的 M1 问题写 no-message worst-peak “只 5/20 过”，但同一 brief 的数据节、R431 feed 与机器 JSON 均表明它是 **5/20 失败、15/20 通过**。

   因而本报告以机器 JSON 为准。若“16/20”或“5/20 过”指另一种合并口径，应在 schema 中新增显式字段，不能由文字反推。

2. **R431 repair 元数据冲突。** R431 的方法与 row-valid 结果明确使用 slew 投影，但 JSON 的 `repair.no_slew_projection=true`。这应是从 R430 继承的陈旧元数据，不用于机制判断。

3. **R428 的“发散”应拆成两个概念。** R428 critic loss 为 `6.77e7–1.06e8` 的高值尺度，但 Q4/Q1=0.25–0.78，随训练下降；它是**value/target 尺度失配与策略熵塌缩**，不是按时间增长的数值发散。R432 的 Q4/Q1=6.24–30.48 才是明确的训练期 critic 动态发散。

4. **模态矩阵中的 0.707 是显示近似。** 若逐字使用 0.707，第二、三行范数平方为 0.999698，并非严格正交。证明中必须使用 `1/sqrt(2)`；该近似误差仅为 `3.02e-4`，不影响实验数量级，但影响“正交/Parseval”命题的严格表述。

另有两个低风险 schema 痕迹：R428/R430 顶层 `round` 正确，但嵌套 `classification.round` 为 `R401`。建议统一清理，避免自动审计误绑定。

---

# A 组：代数与数值机制

## A1. R428 collapse 的变量分解

**类型：A；置信度：0.90（主因），0.70（精确因果份额）**

### 结论

R428 的主导问题是**reward 中物理动作二次惩罚造成的巨大 Q/TD 尺度**，而不是缺少 `phi_abs`，也不是缺少 slew 投影。投影可由 R430 直接排除：R430 同样没有投影，却已把 critic loss 降到 O(1) 并保持下降。twin-Q 和 gradient clipping 能改善偏差与更新稳定性，但它们没有任何机制把一个 O(10^4) 的 Bellman 目标自动归一化到 O(1)，因此更可能是次级稳定器。

问题原文把 R428→R431 称为“三变量”，实际上至少同时改变了五项：

1. 加入 `50 r_abs`；
2. 动作惩罚从 paper-strict 物理尺度切换到历史归一化尺度，且 `phi_h,phi_d: 1 -> 0.0056`；
3. single critic + V target → twin-Q；
4. 无 gradient clip → max-norm 1；
5. 无投影 → slew 投影。

所以现有数据只能做**主因排序与排除**，不能给出严格的三因素方差分解。

### 1. `phi_abs=50` 不会从代数上缩小 value scale

适配 reward 中

\[
\Delta r_{abs}=-50\,d\omega_i^2\le 0.
\]

它只会让单步 reward 更负或不变。因此，“加入 `phi_abs` 直接把绝对 reward/TD target 变小”在符号上不成立。它的真正作用是改变**相对目标结构**：

- 对相干偏移 `domega=c*1`，同步项 `r_f=0`；
- 但 `r_abs=-c^2`，仍提供恢复 nominal frequency 的梯度。

这能防止策略只追求邻居同步而忽略全系统共同偏频，却不能解释为何 critic loss 从 `~1e8` 变成 `~1`。在没有逐步 reward trace 的情况下，`phi_abs` 对总 reward 方差的实际贡献不能精确估计。

### 2. 动作惩罚尺度的变化足以解释数量级

根据 `source/v4_config.py` 的定义注释与 R430 元数据，paper-strict 物理惩罚为

\[
r_h^{strict}=-\left(\frac{\overline{\Delta M}}{2}\right)^2,
\qquad
r_d^{strict}=-(\overline{\Delta D})^2,
\]

而适配线按 brief 使用

\[
r_h^{adapt}=-\left(\frac{\overline{\Delta M}}{600}\right)^2,
\qquad
r_d^{adapt}=-\left(\frac{\overline{\Delta D}}{600}\right)^2,
\]

并再乘 `0.0056`。对应的二次系数为：

\[
\begin{aligned}
k_M^{strict}&=1/4, & k_M^{adapt}&=0.0056/600^2=1.5556\times10^{-8},\\
k_D^{strict}&=1,   & k_D^{adapt}&=0.0056/600^2=1.5556\times10^{-8}.
\end{aligned}
\]

于是严格到适配的系数比为

\[
\frac{k_M^{strict}}{k_M^{adapt}}=1.607\times10^7,
\qquad
\frac{k_D^{strict}}{k_D^{adapt}}=6.429\times10^7.
\]

即便暂时忽略 physical→normalized，只看 `1 -> 0.0056`，单步动作项也缩小 178.57 倍；若 TD 残差同比例缩放，MSE 可缩小约

\[
178.57^2=3.189\times10^4.
\]

R428 的 q1 critic loss 范围为 `6.774e7–1.056e8`，对应 TD 残差 RMS

\[
\sqrt{L_Q}=8.23\times10^3\sim1.03\times10^4.
\]

R431 同一读数为 `1.827–2.365`，残差 RMS 仅 `1.35–1.54`。这与 reward coefficient 的跨多个数量级变化一致。

一个仅用于量级直觉的换算是：若 `sqrt(L_Q)~10^4` 近似表示长期 Q 尺度，则在 `gamma=0.99` 下对应的持续单步尺度约为 `(1-gamma)Q~100`。物理动作平方项很容易达到该量级；这不是证明，因为 loss 不是 Q 的直接观测，但数量级相容。

### 3. R430 排除了“投影是训练稳定主因”

R430 没有 slew 投影，却有：

- q1 critic loss `1.56–2.31`；
- Q4/Q1 `0.0108–0.0172`；
- alpha 约 `0.005`；
- 训练稳定，但评估轨迹因 slew 违规而 invalid。

因此投影是**执行可行性修复**，不是 R428 value-scale 修复的必要条件。它仍可能通过改变 replay 中的状态分布间接影响后续训练，但不是从 R428 到稳定 critic 的必要变量。

### 4. twin-Q 与 gradient clipping 的角色

- **twin-Q/min target**主要抑制过估计偏差。对本项目全为负 reward 的情形，`min(Q1,Q2)`甚至可能使目标更负；它不做尺度归一化。
- **gradient clipping**把单次参数更新范数限制住，但不约束 target、Q 输出或长期参数漂移。它能阻止一次异常 batch 造成大跳变，不能保证持续大 target 下的 value 有界。
- R428 的 loss 很大但 Q4/Q1<1，说明训练并非简单“梯度一步步爆炸”；更像网络正在拟合一个极大的 target，同时 actor/alpha 尺度严重失衡。

故合理排序为：

\[
\text{动作 reward 尺度} \gg \text{gradient clip / target结构} > \text{slew投影（对训练尺度）}.
\]

### 5. auto-alpha 为何在两组中方向相反

常见 SAC 温度损失写为

\[
J(\log\alpha)=
-\mathbb E\left[\log\alpha\,\bigl(\log\pi(a|s)+\mathcal H_{target}\bigr)\right].
\]

梯度下降等价于：

- 若 `E[log pi + H_target] > 0`，则提高 `alpha`；
- 若该量 `<0`，则降低 `alpha`。

二维动作常用 `H_target=-2`。R428 的平均 `log pi=+10.36~+10.90`，则括号约为 `+8.36~+8.90`，所以 alpha 必然向上并撞到 5.0。连续分布的 differential entropy 可以为负；正的平均 log-density 正是极窄分布的表现。

reward 缩放为什么会影响它？固定策略下，若 reward 与 Q 同乘 `c`，最大熵最优策略近似满足

\[
\pi^*(a|s)\propto \exp\{Q(s,a)/\alpha\}.
\]

真正决定集中度的是 `Delta Q/alpha`。当

\[
\frac{\max_a Q(s,a)-\min_a Q(s,a)}{\alpha_{max}}\gg1,
\]

策略会接近 delta；alpha 虽被目标熵推高，也因上限无法恢复足够温度。R428 的 critic 残差尺度约 `10^4`、`alpha_max=5`，虽不能把 residual 等同于 action gap，但足以说明二者可能相差数千倍。

反之，R431 的 Q/target 处于 O(1) 尺度，entropy 项在 actor objective 中不再被完全淹没，alpha 可向下到 floor。数据包未提供 R431 的 `mean_log_pi`，所以“其最终熵高于目标”的具体数值不能从现有字段验证。

### 6. 最小因果裁决实验

建议采用冻结 harness 的分层消融，而不是只做 R428/R431 端点对比：

1. 固定 single critic、无 clip、无投影，只改 reward：strict physical → strict-rescaled → normalized、分别 `phi_abs=0/50`；
2. 在已稳定的 reward 上做 single/twin × clip off/on；
3. 最后只切换投影，并把 projector state 加入 critic state，区分执行分布效应与 POMDP 效应。

每组至少记录单步 reward 分项分位数、TD target、Q 值、TD residual、actor `Delta Q/alpha`、log-std、log-pi 与 alpha gradient residual。仅看 critic loss 不足以做精确归因。

---

## A2. 动作应力超标的投影不变集

**类型：A；置信度：0.99（集合结论），0.55（R431 具体波形）**

### 结论

是的。`|Delta a|<=0.25` 只禁止单步跳变，不能抑制：

- 长时间保持较大偏置导致的高 RMS；
- 以合法斜率往返形成的高累计 total variation；
- actor 与隐藏 projector state 之间的追赶/极限环。

因此 R431 在全部行 slew-valid 的同时动作 RMS/TV 超标，完全不矛盾。

### 1. 投影算子与精确可达集合

对任一动作分量，令 raw command 为 `v_t`、executed action 为 `u_t`、`delta=0.25`：

\[
u_t=\operatorname{clip}\left(
 u_{t-1}+\operatorname{clip}(v_t-u_{t-1},-\delta,\delta),
 -1,1
\right).
\]

若 `u_0 in [-1,1]`，归纳可得

\[
|u_t|\le1,\qquad |u_t-u_{t-1}|\le\delta.
\]

反向也成立：任意满足上述两个条件的序列，只需令 `v_t=u_t`，投影后仍为原序列。故有限时域内的可达集合恰为

\[
\mathcal U_\delta=
\{u_{0:T}:\|u_t\|_\infty\le1,
\ \|u_t-u_{t-1}\|_\infty\le\delta\}.
\]

这个集合没有比 `RMS<=1` 更强的绝对幅值保证，也没有低于 `(T-1)delta` 的逐分量累计 TV 保证。30 步 episode 中，单分量累计变化上界仍为 `29×0.25=7.25`。

### 2. RMS 的偏置—方差分解

若动作维数为 `d=8`，时间均值为 `mu`，时间协方差为 `Sigma`，则

\[
\operatorname{RMS}^2
=\frac1{Td}\sum_t\|u_t\|_2^2
=\frac{\|\mu\|_2^2+\operatorname{tr}\Sigma}{d}.
\]

所以 RMS 高有两种互不相同的来源：

- **高偏置**：动作稳定地停在离零较远的位置；
- **高波动**：均值接近零，但在正负方向频繁运动。

slew 投影只对后者的瞬时斜率设上界，对两者都不设足够小的能量界。

### 3. 两个构造性反例

**反例 1：无抖动也会 RMS 失败。** 取所有时刻 `u_t=0.2`：

\[
RMS=0.2,\qquad TV=0.
\]

四个 profile 的 110% RMS 阈值只有：

| profile | `1.1 × RMS_ref` |
|---|---:|
| dev-a | 0.108370 |
| dev-b | 0.147185 |
| dev-c | 0.097829 |
| dev-d | 0.134320 |

所以常值 0.2 在完全不抖动的情况下已全部失败。这说明“RMS 高”不能自动归因于边界 chatter。

**反例 2：合法边界锯齿同时 RMS、TV 高。** 序列

`-1,-0.75,...,0.75,1,0.75,...,-0.75`

每一步恰好变化 0.25，完全满足投影，但一周期

\[
RMS=0.58630,
\qquad \operatorname{mean}|\Delta u|=0.25.
\]

它证明 rate bound 不能阻止持续往返运动。harness 的 `tv_ref_scenario_mean` 聚合定义未在包中展开，因此不能把其 0.32–0.51 与单分量 0.25 直接比较；但累计/跨维聚合 TV 显然可以大于 0.25。

### 4. 隐藏 projector state 会使 actor 看到 POMDP

执行转移依赖 `u_{t-1}`。若 actor/critic observation 不含该量，则存在两条历史：物理观测相同、上一执行动作不同，对同一 raw command 得到不同 `u_t` 与不同下一状态。因此 actor 的 7-slot 观测一般不是 Markov state。

可能后果是：

- actor 反复输出远离当前 `u_{t-1}` 的目标；
- projector 每步只移动 0.25，形成持续 execution mismatch；
- 物理状态反馈滞后后 actor 反向修正，产生合法但高 TV 的极限环；
- saturation/rate-active 区域中 actor gradient 学到的是被截断后的间接效果。

但数据包没有 R431 的 raw/executed 全轨迹，且 feed 明确指出训练日志里的 `slew_diagnostics` 是 raw tanh 幅值诊断，不是权威 per-step slew/TV。因此“边界附近持续抖动确实发生”目前只能列为假设，不能作为已证事实。

### 5. 下一轮必须记录的可观测量

- 每代理、每 M/D 分量的 raw mean、sampled raw action、post-clip 与 post-slew executed action；
- `u_{t-1}`、rate-limit active、box-limit active、physical lower-clamp active；
- `raw-executed` mismatch 及其持续时间；
- 每 profile/seed 的动作均值、标准差、RMS、累计 TV、符号切换次数、边界驻留率；
- common/differential action 能量和按事件窗口的功率谱；
- 参考控制器使用完全相同聚合定义计算的上述量。

这能把“高偏置”“高频 chatter”“慢速边界巡航”“投影状态隐藏”四种机制分开。

---

## A3. 乘子衰减的 dual-ascent 分析

**类型：A；置信度：0.99**

### 结论

乘子到 0 是 frozen update 对**实际负平均 residual**的正确响应，不是 critic 把 dual residual 的符号算错。8640 个 episode 全部满足

\[
lambda_{k+1}=\Pi_{[0,10]}\bigl(lambda_k+0.05(C_k-3)\bigr)
\]

且最大复算误差为 0。六组在第 18 个 episode 首次触 0，因为前 18 个 episode 的累计 `sum(C_k-3)` 都略小于 -20，恰好抵消初值 1。

“6–33% episode 超预算”是 tail probability，不等于 `E[C]>3`。六组全时域均值均低于 3，所以一个只约束期望 episode cost 的乘子可以长期接近 0，同时保留大量单 episode 违反。

### 1. 数值复核

| 运行 | Q4/Q1 | 前18回合平均 C | 前18累计 residual | 全期平均 C | `C>3` | 最终 lambda |
|---|---:|---:|---:|---:|---:|---:|
| msg-401 | 9.81 | 1.8604 | -20.5135 | 1.6261 | 241/1440=16.7% | 0.0000 |
| msg-402 | 8.19 | 1.8669 | -20.3959 | 2.2452 | 480/1440=33.3% | 0.1182 |
| msg-403 | 6.24 | 1.8615 | -20.4926 | 1.6025 | 247/1440=17.2% | 0.0956 |
| no-msg-401 | 9.37 | 1.8202 | -21.2366 | 1.3689 | 148/1440=10.3% | 0.0000 |
| no-msg-402 | 30.48 | 1.8650 | -20.4308 | 1.1069 | 81/1440=5.6% | 0.0000 |
| no-msg-403 | 6.71 | 1.8475 | -20.7456 | 1.9215 | 387/1440=26.9% | 0.0000 |

因为从 `lambda_0=1` 到 0 需要

\[
0.05\sum_{k=1}^{18}(C_k-3)\le-1
\iff
\sum_{k=1}^{18}(C_k-3)\le-20,
\]

表中六组都满足，并全部在 episode 18 首次触零。

它也不是严格“单调后永久为零”。触零之后，六组分别有 105–848 个 episode 的 lambda 又大于 0，最大反弹 0.167–0.698。投影到零加上低均值成本使其大部分时间贴底，但超预算回合仍会把它短暂推高。

### 2. discount/undiscount 错配的实际作用

30 步、`gamma=0.99` 的权重和为

\[
\sum_{t=0}^{29}\gamma^t
=\frac{1-0.99^{30}}{1-0.99}
=26.02996.
\]

相对 undiscounted 30 步总和，其均匀成本权重仅为

\[
26.02996/30=0.867665.
\]

最后一步权重为 `0.99^29=0.74717`。因此错配会导致：

- actor 的 cost critic 对后段成本最多低估约 25.3%；
- actor 可把成本从早期移向后期而降低 discounted objective，但 dual 看见的总和不变；
- 若错误地把“discounted budget=3”和“undiscounted budget=3”当成同一阈值，均匀成本下前者等价于 undiscounted 3.458，而真正的 undiscounted 3 只对应 discounted 2.603。

但这里 actor 通常只使用 `lambda Q_c`，预算 3 进入 dual 而不进入 actor gradient，所以错配更准确的描述是**时间权重不一致**，不是简单阈值换算。它能解释成本时序迁移和 actor/dual 目标不一致，不能在实际 `C_k<3` 时把 dual update 变成正向。

### 3. critic 发散能否使 dual residual 符号错乱

按冻结公式，dual residual 使用 rollout 的实测

\[
C_k=\sum_{t=0}^{29}c_c(t),
\]

不使用 `Q_c`。所以只要日志公式与实现一致，critic 发散不能改变 `C_k-3` 的符号。数据中的零误差更新恒等式直接排除了选项 **(b)**。

critic 发散可以造成的是：actor 收到的 `nabla_a Q_c` 方向和尺度不可靠，因而对 lambda 的响应弱、噪声大，甚至局部反向；这可能解释“lambda 变化却没有系统改善 cost”。但它不是 lambda 首次衰减至零的必要解释。选项 **(a)** 也尚未由现有字段证明，因为没有 `dC/dlambda` 干预数据或 actor gradient alignment。

更准确的结论是：

> 乘子衰减由真实 episode residual 的负均值造成；期望约束已在平均意义上松弛，但 tail violation 很高。critic 发散使 actor 难以形成稳定的约束响应，却不污染 dual residual 本身。

### 4. 可证伪实验

1. **公式闭环审计**：继续逐回合记录 `C_undisc`、`C_disc`、`lambda_pre/post`，assert 更新误差为 0。
2. **时序迁移检验**：记录 `c_c(t)` 的时间质心；若 mismatch 是主因，增大 lambda 后成本会系统性向后段移动。
3. **lambda 干预**：冻结 actor，在相同状态 batch 上令 lambda 取 `{0,0.1,0.5,1}`，检查 actor update 后实测 `Delta C/Delta lambda`。若为正，才支持“反向响应”。
4. **critic 梯度裁决**：比较 `nabla_a Q_c` 与有限差分 rollout cost gradient 的夹角。
5. **对齐目标**：把 cost critic 改为 undiscounted finite-horizon/`gamma_c=1`（加 time-to-go 状态），或 dual 改为同一 discounted residual；若 cost 与 lambda 关系恢复，支持 mismatch 机制。
6. **改变约束类型**：若真正关心 6–33% 的超预算尾部，应使用 chance/CVaR 或每 profile guard，不应期待均值 CMDP 自动消除 tail。

---

# M 组：机制预测与实验裁决

## M1. 邻居消息为何改善频率守卫

**类型：M；置信度：0.75**

### 结论与前提修正

机器 JSON 显示 no-message 也通过 common-frequency 20/20，因此“邻居消息让 common-mode 恢复从不可学变为可学”不受数据支持。更强、且与数据一致的命题是：

> 邻居频率与 RoCoF 帮助每个代理把共同加速分量与局部/区间 differential 分量分离，并让多代理动作在首峰阶段更同相、在振荡阶段更具模态选择性；因此 message 臂把 worst-peak 从 15/20 提到 20/20，并把 RoCoF 失败从 16/20 降到 4/20。

### 1. 局部观测的不可辨识性

对频率向量 `f in R^4`，写成

\[
f=q_0 f_0+T^T f_d.
\]

单个代理只看 `f_i` 与 `dot f_i` 时，每个标量都同时含 common 与多个 differential 模态；同一个 `f_i` 可由“全系统共同偏频”或“局部机组偏离、全局均值正常”产生。两者需要不同控制：前者需要各 VSG 同向提供惯量/阻尼，后者需要差分阻尼而非全体同向推力。

邻居 slot 可构造近似充分统计量：

\[
\hat f_{0,i}=\frac{f_i+\sum_{j\in\mathcal N_i}f_j}{1+|\mathcal N_i|},
\qquad
\hat f_{d,i}=f_i-\hat f_{0,i},
\]

RoCoF 同理。第一项近似共同趋势，第二项是局部图 Laplacian 残差。即使局部邻域均值不等于全局 `q_0` 模态，它仍显著减少 common/differential 混叠，并提供扰动传播方向与远端相位信息。

### 2. 具体机制预测

预期 message policy 分两个时间窗口工作：

- **扰动后首峰窗口**：依据邻居 RoCoF 的共同符号，多个代理更早、更同相地提高合适的 M/D，降低最差机组峰值与 RoCoF；
- **后续振荡窗口**：依据 `f_i-mean(neighbor f)` 与相对 RoCoF，输出与 differential 速度反相的阻尼动作，避免某一代理过冲。

这解释了为什么 common-frequency integral 两臂都能通过，而 message 对最差机组峰值和 RoCoF 的收益更明显：积分指标对短时局部峰值不如 worst-unit/RoCoF 敏感。

### 3. 可证伪预测

| 假设为真时 | 应观察到的结果 | 能推翻它的结果 |
|---|---|---|
| 消息主要提供邻域共同趋势 | 固定本地 slot，message actor 对邻居均值的有限差分 Jacobian 显著且跨代理符号一致 | 对邻居均值敏感度接近 0，或随机打乱均值不影响动作/守卫 |
| 消息使首峰动作更协调 | 扰动后前几步 common action 能量、跨代理动作相关性上升，动作起始时延下降 | message/no-message 的时延与 common 相位无差异 |
| 消息用于 differential damping | ringdown 中 `T A_t` 与 `T RoCoF_t` 显著负相关，modal energy 衰减更快 | differential action 与 modal state 无稳定相位关系 |
| 只需邻居均值，不需身份/拓扑 | 把各邻居 slot 替换为相同均值，性能基本保留；保持均值但置换身份也不恶化 | 均值保留仍明显退化，说明策略使用位置/传播信息 |
| 消息的因果贡献真实 | eval 时 zero/shuffle/delay message 会按剂量恶化 worst-peak/RoCoF | 干预不改变指标，说明收益来自训练随机性或其他混杂 |

### 4. 下一轮 seal 的可观测量

- 所有 actor 输入 slot、邻居 mask、邻居身份/拓扑顺序；
- 每代理频率、RoCoF、扰动位置与发生时刻；
- raw 与 executed M/D action、projector active/mismatch；
- `q0^T A_t`、`T A_t`、`eta_d^a(t)`，并按首峰/振荡/恢复窗口汇总；
- 动作 onset latency、跨代理相关矩阵、与 common/differential 频率及 RoCoF 的相位/互谱；
- policy 对本地值、邻居均值、邻居差值的有限差分 Jacobian；
- zero、shuffle、identity permutation、mean-only、delay/noise 五种 counterfactual eval 的全部 guards。

---

## M2. R433 total penalty 的 modal 陷阱

**类型：M；置信度：0.95（代数），0.70（端点预测）**

### 结论

R433 的 total action penalty 并非简单“方向错误”：当前动作守卫本身就是 total RMS/TV，因此对总幅值做惩罚与 RMS 目标直接一致。问题在于它把 common 与 differential action 以同一价格压缩，可能牺牲频率恢复所需的有益 common action；同时 `a^2` 不直接惩罚时间变化，不能保证 TV 守卫通过。

最合理的下一步不是把 total 项完全替换为 differential 项，而是使用

\[
\lambda_0 E_0^a+
\lambda_d E_d^a+
\lambda_{\Delta}\|A_t-A_{t-1}\|_F^2,
\]

并通过 `eta_d^a` 与性能灵敏度分别定权。

### 1. Parseval 分解

令 `A in R^{4x2}` 为四代理的 executed M/D action。由于 `U=[q0^T;T]` 正交，

\[
\|A\|_F^2
=\|q_0^T A\|_F^2+\|T A\|_F^2.
\]

定义

\[
E_0^a=\frac14\|q_0^T A\|_F^2,
\quad
E_d^a=\frac14\|T A\|_F^2,
\quad
\eta_d^a=\frac{E_d^a}{E_0^a+E_d^a}.
\]

R433 的 total penalty 与 `E_0^a+E_d^a` 成正比。若目标仅是 differential energy，则其数值过惩罚倍数为

\[
\frac{E_0^a+E_d^a}{E_d^a}=\frac1{\eta_d^a}.
\]

- `eta_d^a=0.8`：total 比 pure differential 大 25%，common 占 20%；
- `eta_d^a=0.5`：大 2 倍；
- `eta_d^a=0.2`：大 5 倍，80% 惩罚落在 common。

梯度污染比能量比例更敏感：common 与 differential 梯度范数比为

\[
\sqrt{\frac{1-\eta_d^a}{\eta_d^a}}.
\]

即使 `eta=0.8`，common 梯度仍为 differential 梯度的 0.5，不能自动视为可忽略。

### 2. R433-dev 数字说明“相对降幅规则”不足以保证绝对 guard

四个 110% RMS 阈值为 `0.0978–0.1472`。R433-dev：

| lambda_p | action RMS | 相对 baseline 降幅 | 相对最宽松阈值 dev-b |
|---:|---:|---:|---:|
| 1 | 0.3211 | 0.0% | 2.18× |
| 5 | 0.2640 | 17.8% | 1.79× |
| 10 | 0.2206 | 31.3% | 1.50× |
| 20 | 0.1752 | 45.4% | 1.19× |

从 baseline 0.3211 降到各 profile 的 110% 阈值，需要 54.2%–69.5% 的绝对降幅；`lambda=10` 的开发规则只要求相对 baseline 下降 20%，因此没有逻辑上保证 guard 可过。即使 `lambda=20`，若训练 RMS 与 eval guard RMS 可直接比较，也仍高于全部阈值。

这里必须保留边界：dev 的 8640-step aggregate RMS 与四个 eval profile 的 guard 统计可能不是同一分布/聚合口径，所以上表是**尺度预警**，不是 R433 最终 guard 预测。

### 3. 可证伪性能预测

**预测 A：若 `eta_d^a` 低。** total penalty 主要压 common action。随着 lambda 增大，应先看到 common-frequency、worst-peak 或 RoCoF 恶化；RMS 下降但端点不一定同比改善，甚至因非对称 decoder/参数异质性导致 differential endpoint 反弹。`eta_d^a` 可能机械上升，因为分母中的 common 能量先被压掉。

**预测 B：若 `eta_d^a` 高。** total 与 differential penalty 数值更接近。若原 differential action 中有大量无效 chatter，适度 lambda 可能同时降低 RMS/TV 并维持甚至改善端点；若 differential action 是实现 0.635/0.590x 的必要控制，则端点会随 RMS 下降而上升。

**预测 C：仅有 `a^2` 可能只修 RMS。** 对固定小幅但频繁反向的动作，RMS 可较低而 TV 高。若 R433 只改变幅值、不改变频谱/符号切换，`action_variation_no_harm` 仍会失败。

### 4. 最有判别力的实验

在相同 seed、训练预算与 RMS 降幅下比较三种正则：

1. total：`lambda ||A||^2`；
2. modal：`lambda_d ||TA||^2 + lambda_0 ||q0^T A||^2`；
3. modal+rate：再加 `lambda_Delta ||A_t-A_{t-1}||^2`。

不要按相同 lambda 比，而要按**matched executed RMS**或 matched action cost 比。若 total 在相同 RMS 下显著损害 common guards，而较小 `lambda_0` 的 modal 方案保留性能，就验证“total 压错有益 common 模态”。

### 5. 所需可观测量

- executed action 的 `E0^a, Ed^a, eta_d^a`，M 与 D 分开；
- 首峰、ringdown、稳态三个窗口的 modal RMS、TV、PSD；
- decoded physical `Delta M/Delta D` 能量，按正/负 decoder 分支统计；
- 每个 penalty 分项的即时 reward 与 actor gradient 范数；
- 端点、common-frequency、worst-peak、RoCoF、RMS、TV 的 lambda 曲线；
- 在 matched RMS 下 total/modal/modal+rate 的比较。

---

## M3. 端点与动作应力的可计算 Pareto 边界

**类型：M；置信度：0.95（可计算框架），0.45（本系统边界位置）**

### 结论

有限时域、动作有界且 DAE 解连续时，端点指标与动作应力之间必然存在 Pareto 前沿，并可由直接轨迹优化、伴随灵敏度或局部线性化求得。当前数据包不能数值定位该前沿：R431 有端点与 guard pass/fail，却没有逐 profile 的实际 RMS/TV；R433-dev 有训练 RMS，却没有同 checkpoint 的端点与 guard。因此不能用 0.635/0.590 和 0.2206 拼成一个 Pareto 点。

### 1. 严格定义

对 profile `p`，令冻结 DAE 与投影生成轨迹 `x_p(u)`。定义归一化性能与应力：

\[
J_p(u)=\max\left\{
\frac{J_{dist,p}(u)}{J_{dist,p}^{ref}},
\frac{J_{off,p}(u)}{J_{off,p}^{ref}}
\right\},
\]

\[
S_p(u)=\max\left\{
\frac{RMS_p(u)}{RMS_p^{ref}},
\frac{TV_p(u)}{TV_p^{ref}}
\right\}.
\]

鲁棒 Pareto 值函数可定义为

\[
V(\rho)=
\min_{u\in\mathcal U_{0.25}}
\max_p J_p(u)
\quad\text{s.t.}\quad
S_p(u)\le\rho,\ \forall p.
\]

`V(rho)` 单调不增。存在同时满足端点优于参照与动作 guard 的控制器，当且仅当

\[
V(1.1)<1
\]

（若允许碰阈值则用 `<=1`）。由于动作序列集合紧、连续 DAE/指标下目标连续，最优解存在；PWA 投影不破坏连续性，只使导数分段。

### 2. 局部可计算形式

在基准轨迹附近，把两个 endpoint 所依赖的输出堆叠为 `y`，动作序列堆叠为 `u`：

\[
y(u)=y_0+Gu+O(\|u\|^2),
\]

其中 `G` 是冻结 DAE 的 trajectory sensitivity。取性能权重 `W`、动作权重 `R`，局部问题为

\[
\min_u\ \|W^{1/2}(y_0+Gu)\|_2^2
\quad\text{s.t.}\quad
\|R^{1/2}u\|_2\le\rho,
\quad u\in\mathcal U_{0.25}.
\]

忽略 box/slew 时，加权和解为

\[
u_\lambda=
-(G^T W G+\lambda R)^{-1}G^T W y_0,
\]

扫 `lambda>=0` 即得局部 Pareto 曲线。加入 slew、box 和多 profile 后是线性化下的凸 QCQP/QP；若跨 decoder/PWA 单元，则用 sequential convex programming 或直接 collocation。

### 3. 同时可行的可检验条件

令

\[
\widetilde G=W^{1/2}G R^{-1/2}.
\]

三个条件控制能否以小动作改善端点：

1. **可控残差**：`W^{1/2}y0` 在 `Range(tilde G)` 外的分量必须已经小于目标阈值，否则无论动作多大都不能满足端点；
2. **最小控制能量**：达到目标输出集合所需的最小 `||R^{1/2}u||` 必须低于 `1.1×` 参照预算，并且解满足 slew/box；
3. **灵敏度条件数**：相关模态上的 `sigma_min(tilde G)` 越大、条件数越好，单位动作对 endpoint 的改善越高，Pareto 前沿越向左下。

### 4. 物理参数如何移动前沿

- **网络耦合强度**没有“越强越好”的普遍单调性。更强耦合可提高远端可控性，也可增强 common/differential 混合。真正有利的是目标模态对应的 action-to-output 传递奇异值大、交叉模态泄漏小。
- **扰动位置**若靠近可控 VSG、且投影到高可控模态，所需动作小；若主要激发弱可控区间模态或远端无执行器节点，前沿恶化。
- **600/200 decoder 非对称**使方向依赖效率相差 3 倍。相同物理 `Delta q` 在正支所需 normalized action 是负支的 1/3，二次 action energy 仅 1/9。若最优控制大多需要正支，前沿改善；若需要负支或撞物理下限，前沿恶化。
- **消息**不改变集中式物理可达前沿，但会放宽去中心化的信息约束，使 MARL 更接近该前沿；隐藏 projector state 则会使实现点远离前沿。
- **M 与 D 的时间角色**不同：M 更影响首峰/RoCoF，D 更影响振荡衰减。若 penalty 不分窗口与通道，会在错误时段压掉高边际价值动作。

### 5. 下一轮最小数据矩阵

至少对 `lambda_p in {0,5,10,20}`，每个 seed/profile 同时保存：两个 endpoint、五个 guards 的原始 ratio、RMS、TV、modal RMS/TV、正负 decoder 占比。用 bootstrap 得到 `V(rho)` 的置信带。若需要物理而非经验前沿，再从 ANDES 导出轨迹 Jacobian/adjoint `G` 并解 robust QCQP。

---

# P 组：论文级命题

## P1. 非光滑执行器下的模态解耦必要条件

**类型：P；置信度：0.95（理想/PWA 结构命题），0.55（真实 ANDES 输出下界）**

以下证明把 brief 中的 `0.707` 替换为精确的 `1/sqrt(2)`。

### 命题 1：对角参数矩阵的 common/differential 交叉块

令

\[
q_0=\frac12[1,1,1,1]^T,
\qquad
U=\begin{bmatrix}q_0^T\\T\end{bmatrix},
\qquad UU^T=I_4.
\]

对任意 `x in R^4`，记 `xbar=(1/4)1^T x`。则

\[
U\,\operatorname{diag}(x)\,U^T
=
\begin{bmatrix}
\bar x & \frac12(Tx)^T\\
\frac12 Tx & T\operatorname{diag}(x)T^T
\end{bmatrix}.
\]

**证明。** 左上角为

\[
q_0^T\operatorname{diag}(x)q_0
=\frac14\sum_i x_i=\bar x.
\]

左下角为

\[
T\operatorname{diag}(x)q_0
=\frac12Tx.
\]

其余块直接相乘即得。证毕。

因此 common/differential 交叉块范数相对 common 对角块的比值恰为

\[
\frac{\|Tx\|_2/2}{\bar x}
=\frac{\|Tx\|_2}{2\bar x}
=:\epsilon_x.
\]

又因为 `Null(T)=span{1}`，有

\[
Tx=0 \iff x=\bar x\,1.
\]

所以对 inertia 与 damping，`epsilon_M=epsilon_D=0` 当且仅当参数同质。

### 命题 2：理想对称约化模型的结构性必要性

考虑理想线性摆动/约化模型，其网络、电气、输入与输出算子在 U 基下本来就是 block diagonal，且 common 子系统可通过输入产生局部线性无关的 `(omega_0,dot omega_0)` 轨迹。则 common 子空间对所有 common 输入保持不变，当且仅当

\[
Tm=0,\qquad Td=0.
\]

**证明。** 在 U 基下，令 differential state 初值与输入均为 0。由命题 1，differential 方程中由 common 轨迹产生的残差至少含

\[
b_M\dot\omega_0+b_D\omega_0,
\quad
b_M=\frac12Tm,
\quad
b_D=\frac12Td.
\]

若 common 子空间对所有可激励 common 轨迹不变，该残差必须对一组局部线性无关的 `(omega_0,dot omega_0)` 恒为 0，故 `b_M=b_D=0`，即 `Tm=Td=0`。反之，若二者为 0，且其他算子已 block diagonal，common/differential 方程互不含对方变量，故精确解耦。证毕。

**假设边界。** 若只考察单一固定指数轨迹，可能出现 `b_M dot omega_0+b_D omega_0` 偶然抵消；因此必要性是“对所有充分丰富的 common 输入/轨迹”的结构命题，不是单一测试波形的辨识结论。

### 命题 3：PWA 非光滑执行器的局部必要条件

令 raw action 到 executed physical adjustment 的映射为局部 Lipschitz、连续 piecewise-affine：

\[
g(a;h)=S_k a+c_k
\]

其中 `h` 包含上一执行动作/active set；在可微单元 k 内，当前动作 Jacobian `S_k=diag(s_k)`。若要求执行器在该单元对任意一阶扰动都不发生 common/differential 混合，则必要且充分条件为

\[
q_0^T S_k T^T=0
\iff Ts_k=0
\iff s_{k,1}=s_{k,2}=s_{k,3}=s_{k,4}.
\]

**证明。** 对 `diag(s_k)` 应用命题 1，其 common/differential 交叉块为 `(1/2)(Ts_k)^T`。交叉块为 0 当且仅当 `Ts_k=0`，而 `Null(T)=span{1}`。证毕。

在 kink 上，用 Clarke generalized Jacobian `partial_C g`。若要求所有方向的一阶模态保持，则必须对每个 `S in partial_C g` 都有 `Ts=0`。因此不同代理处于不同 decoder 符号、不同 saturation 或不同 slew active set 时，结构条件通常失败。

### 600/200 decoder 的直接反例

取 `x>0`，raw action

\[
a=(x,-x,0,0)^T,
\qquad q_0^T a=0,
\]

是纯 differential。非对称解码后

\[
g(a)=(600x,-200x,0,0)^T,
\]

其 common 坐标为

\[
q_0^Tg(a)=\tfrac12(600x-200x)=200x\ne0.
\]

因此只要运行会跨越混合正负分支，raw-action 空间中的全局精确 modal preservation 不可能。若所有代理始终处于相同分支且 active status 一致，局部斜率同质，才可能在该单元恢复一阶模态保持。

### 能否给出只依赖 `epsilon_M,epsilon_D` 的统一阈值

**不能给出系统无关的正阈值。** 原因是输出 leakage 还依赖：网络模态传递增益、激励频率、控制器抵消、输出选择与共振。很小的 heterogeneity 可在高增益频率产生大输出；很大的 heterogeneity 也可在某一特定输出/频率被零点或控制器抵消。

但可以给出两个严格、可用的条件化版本。

#### 版本 A：算子级近似解耦

若“delta-近似解耦”定义为质量与阻尼矩阵的 normalized cross block 分别不超过 `delta_M,delta_D`，则由命题 1：

\[
\epsilon_M\le\delta_M,
\qquad
\epsilon_D\le\delta_D
\]

是必要且充分条件。这是结构矩阵层面的精确结论，不等同于输出 endpoint 的界。

#### 版本 B：给定频率与 DAE 传递增益的不可实现界

对 harmonic common 速度 `omega_0(t)=Re{z_0 e^{j Omega t}}`，异质性产生的 differential forcing 为

\[
f_d=(j\Omega b_M+b_D)z_0.
\]

因 `b_M,b_D` 为实向量，交叉项在复范数中消失：

\[
\frac{\|f_d\|_2}{|z_0|}
=
\sqrt{(\Omega\bar M\epsilon_M)^2+(\bar D\epsilon_D)^2}.
\]

若真实约化 DAE 从该 forcing 到所测 differential output 的最小增益为 `mu_d(Omega)>0`，其他网络非对称/控制器/非光滑抵消总量上界为 `kappa(Omega)|z_0|`，则

\[
\frac{\|y_d\|}{|z_0|}
\ge
\mu_d(\Omega)
\left[
\sqrt{(\Omega\bar M\epsilon_M)^2+(\bar D\epsilon_D)^2}
-\kappa(\Omega)
\right]_+.
\]

若右侧大于目标 leakage `delta`，则该 `delta`-近似解耦不可能。等价必要条件是

\[
\sqrt{(\Omega\bar M\epsilon_M)^2+(\bar D\epsilon_D)^2}
\le
\kappa(\Omega)+\frac\delta{\mu_d(\Omega)}.
\]

这是所求“超过则不可能”的条件化界；它不能在没有 `mu_d,kappa` 时化成一个只含 epsilon 的数字。

### 与真实 ANDES DAE 的差距：需要哪些 Jacobian

ANDES 应在每个冻结 operating point 上写成广义/半显式 DAE：

\[
F(\dot x,x,z,m,d)=0,
\qquad
G(x,z,m,d)=0.
\]

需要导出：

\[
F_{\dot x},F_x,F_z,F_m,F_d,
\qquad
G_x,G_z,G_m,G_d,
\]

以及 measured output Jacobian、decoder/projector 的普通或 Clarke Jacobian。若 `G_z` 可逆，消去 algebraic state 后形成 reduced pencil

\[
j\Omega E_r-A_r,
\]

再把 VSG frequency/parameter 子空间投影到 U 基，计算：

- baseline network/electrical common-differential 交叉块；
- M/D heterogeneity 的参数灵敏度；
- `H_d(jOmega)` 及 `mu_d(Omega)`；
- controller/actuator 可提供的最大抵消 `kappa(Omega)`。

在完成这一步前，“homogeneous M,D 对真实 ANDES 足够/必要”不能无条件宣称，因为网络本身可能不完全对称，也可能存在动态抵消或不可观输出。

---

## P2. coupled M/D 调制下 SAC critic 不发散的充分条件

**类型：P；置信度：0.98（有界性定理），0.65（深度 SAC 收敛应用）**

### 结论

可以给出一个不依赖动作是 additive 还是 bilinear/LPV 的**critic value/loss 有界性充分条件**。关键不是 twin-Q 或 gradient clip 单独存在，而是：

1. 物理 DAE 在所有允许动作下良定且状态保持在紧集；
2. 把上一 executed action/projector active state 纳入 Markov state；
3. reward、alpha 与 log-density 有界；
4. critic 输出与参数显式投影到紧集，target network 也投影；
5. normalization/PopArt 与 actor 的 Q/alpha 尺度一致。

这些条件保证 Q 与 TD loss 不可能数值发散。若还要求参数收敛到固定点，需要更强的 projected Bellman contraction、回归强凸性与 actor/critic/target 多时间尺度；普通 nonlinear deep SAC 的 twin-Q+Polyak+clip 本身不满足该全局证明。

### 定理 1：soft twin-Q 的有界不变集

考虑增广 Markov state `s`，包含物理状态和 projector memory。假设：

**H1（物理良定）**：对所有 `s` 与 projected action `a`，index-1 DAE 有唯一下一状态，且转移保持在紧集 `S`；M/D 保持正且有上界，代数 Jacobian 在该集上非奇异。

**H2（reward 有界）**：经过固定无量纲化或有界变换后

\[
|r(s,a)|\le R.
\]

**H3（温度与密度有界）**：

\[
0\le\alpha\le A,
\qquad
|\log\pi(a|s)|\le L.
\]

这需要硬约束 entropy target 项，例如使用截断/裁剪的 pre-tanh latent、log-std 上下界、tanh Jacobian 数值下限，并对最终 `log pi` 或 `alpha log pi` 显式裁剪；仅限制 log-std 不能对无界 Gaussian latent 给出全局硬界。

**H4（critic/target 输出投影）**：两个 online/target critic 均满足

\[
|Q_i(s,a)|\le B
\]

并对参数做紧集投影。可用 `B*tanh(f_theta/B)`、最后一层裁剪或 projected SGD 实现。取

\[
B\ge\frac{R+\gamma A L}{1-\gamma}.
\]

**H5（target 更新保持集合）**：target 参数的 Polyak 更新后再次投影，或架构本身保证输出界。

SAC target 为

\[
Y=r+\gamma\left[
\min_{i=1,2}\bar Q_i(s',a')-
\alpha\log\pi(a'|s')
\right].
\]

则 `|Y|<=B`，每个 critic 的平方 TD loss 满足

\[
(Q_i-Y)^2\le4B^2.
\]

因此 critic value、target 与 loss 都不能发散。

**证明。** 由 H2–H4：

\[
|Y|
\le R+\gamma(B+AL)
\le B,
\]

最后一步正是 B 的取值条件。又 `|Q_i|<=B`，故 `|Q_i-Y|<=2B`，平方后得结论。`min` 对 sup norm 为 1-Lipschitz，不扩大界。证明与转移对 action 的代数形式无关；bilinear/LPV 只进入 H1 的良定性。证毕。

**解释。** 这是“不会爆”的强保证，不是“学到最优策略”的保证。若 B 取得过小，会产生 clipping bias；上式给出一个不截断真实 bounded Bellman 不变集的充分下界。

### 定理 2：固定策略 critic 收敛的附加条件

在定理 1 基础上，再假设：

1. 固定策略 `pi` 下的 projected fitted operator `F=Pi T_pi` 在所用范数中为 `kappa<1` 的收缩；tabular/精确可实现情形可取 `kappa=gamma`；
2. 每轮 critic 回归有唯一解，例如线性特征满秩并加 ridge，使目标强凸；
3. replay 对相关状态动作充分覆盖，随机噪声二阶矩有界；
4. online critic 步长满足 Robbins–Monro 条件，target network 在更慢时间尺度更新；
5. actor 与 alpha 再慢一个时间尺度，并投影到紧参数集。

则固定 actor 时 critic 迭代跟踪唯一 regularized soft Bellman fixed point；多时间尺度下，actor/alpha 可在 critic 平衡流形上收敛到一个局部 stationary point。

这类结论与 target-network 理论中的“投影 + ridge + 时间尺度”一致。对普通深度非线性网络，`Pi T` 未知是否收缩、回归非凸，因此不能把 R431 的经验稳定直接升级为全局收敛定理。

### 为什么 gradient clipping、twin-Q、target network 单独不够

- **gradient clipping**只保证单次 `||Delta theta||` 有界；固定步长下参数仍可长期漂移到无穷。必须配合参数/输出投影或 coercive regularization。
- **twin-Q**降低过估计，不限制 reward/target 尺度，也不保证两个 critic 不共同漂移。
- **Polyak target**减慢反馈环，但普通形式不自动给全局收敛；理论保证通常还需要 projection、ridge、线性/收缩假设。
- **reward clipping**能给有界性，却可能改变任务排序；在 SAC 中即使只做正比例缩放，也会改变 Q/alpha 比，除非 alpha 同比例缩放或 actor 使用未归一化 Q。

### PopArt 的正确接入方式

令网络预测 normalized value `z=w^T h+b`，物理 Q 为

\[
Q=\sigma z+\mu.
\]

当 running statistics 从 `(mu,sigma)` 更新到 `(mu',sigma')` 时，为保持所有未归一化 Q 不变，应调整最后一层：

\[
w'=\frac\sigma{\sigma'}w,
\qquad
b'=\frac{\sigma b+\mu-\mu'}{\sigma'}.
\]

训练 target 使用

\[
\hat Y=(Y-\mu)/\sigma.
\]

PopArt 解决的是 target 跨数量级和随策略变化的问题，正适合 R428/R431 的 value-scale 差异。但需满足：

- `sigma` 有 floor/ceiling，统计更新抗异常值；
- target 与 online 使用一致统计或明确同步；
- actor 若使用**未归一化 Q**，alpha 保持物理尺度；
- actor 若使用 normalized Q，则必须使用 `alpha_tilde=alpha/sigma`，否则 entropy/Q 比再次失配。

PopArt 不会自动解决 off-policy bootstrapping、POMDP、critic nonconvexity 或坏的 physical transition。

### 对 R431 的判定

R431 已满足一部分实践稳定条件：normalized reward、twin-Q、target network、gradient cap、alpha bounds、M/D 正下限、executed slew projection；并且实测 critic loss 健康下降。

但它未满足上述定理的完整前提：

- actor observation 不含 projector state，Markov 性不保证；
- 未见 critic 输出/参数显式投影；
- 未见 PopArt/target normalization；
- 深度 off-policy 回归非凸；
- 未提供 reward/TD target/log-density 的全程硬界审计。

所以可写成“在测试预算上经验稳定”，不能写成“理论保证不发散”。

### 推荐的工程组合

1. state 加入上一 executed M/D、rate/box active flags；
2. reward 各分项固定无量纲化，并记录分位数；
3. PopArt 或 robust target standardization，actor 使用 unnormalized Q；
4. twin-Q + projected target network + ridge/weight decay；
5. critic 输出界与参数范数 projection，gradient clip 仅作额外保险；
6. alpha 按 Q 物理尺度设置动态上界，记录 `Delta Q/alpha`；
7. 若要论文级收敛证明，先在线性 critic/冻结 actor 的 ANDES local model 上验证 projected Bellman contraction，再扩展多时间尺度。

---

## 2. 建议写入下一轮 seal 的统一观测协议

为一次性裁决 A2、A3、M1、M2、M3，建议每个环境步保存以下最小字段：

### 2.1 状态、消息与执行器

- 本地及全部邻居的 frequency、RoCoF、mask/identity；
- raw actor mean、sample、pre-tanh log-std、log-pi；
- post-box、post-slew、post-decoder、post-physical-clamp 动作；
- previous executed action、各 active-set flag、execution mismatch。

### 2.2 模态量

- `q0^T f, Tf, q0^T RoCoF, T RoCoF`；
- `q0^T A, TA, E0^a, Ed^a, eta_d^a`，M/D 分开；
- 首峰、ringdown、恢复窗口的 RMS、TV、PSD、相位与互谱。

### 2.3 SAC 数值量

- reward 每个分项及总和；
- `Q1,Q2,target,min-Q,TD residual` 的分位数；
- actor 的 action-gap proxy、`Delta Q/alpha`；
- alpha residual `log pi + H_target`；
- critic/actor gradient norm：clip 前与 clip 后；
- PopArt `mu,sigma` 或其他 target normalization 状态。

### 2.4 CMDP 量

- 每步 `c_c(t)`、discounted 与 undiscounted episode sum；
- `lambda_pre/post` 与复算 residual；
- cost critic 预测、有限差分 rollout cost、两者 action gradient 夹角；
- tail 指标：`P(C>3)`、CVaR、各 profile guard。

### 2.5 必做 counterfactual

- message：zero、shuffle、identity permutation、mean-only、delay/noise；
- penalty：total/modal/modal+rate，按 matched RMS 比较；
- reward：strict、strict-rescaled、normalized，`phi_abs` 独立开关；
- projector state：actor/critic 均不可见、仅 critic 可见、二者均可见。

---

## 3. 最终判断

1. **R428 的核心教训是尺度，不是“精确 SAC 天生不稳定”。** 该轮的 loss 高而下降，说明算法在追逐极大 target；动作物理二次项、固定 alpha ceiling 与 entropy regularization 尺度共同造成近 delta 策略。不能把它概括为 single critic 单因素失败。
2. **R431 的投影修复了可执行性，不会自动修复动作经济性。** slew-valid 与 RMS/TV no-harm 是两个不同约束层次。
3. **R432 的 dual 机制本身按公式工作。** 真正问题是均值约束与 tail guard 不一致、discount 时序不一致，以及发散 cost critic 让 actor 不能可靠响应 lambda。
4. **消息收益更像模态可辨识与动作协调，而非 common-frequency 从 0 到 1 的可学性跃迁。** no-message 已通过 common integral；差异集中在 worst-unit peak 与 RoCoF。
5. **R433 的单一 total-energy 项可能不够。** 它对 RMS 有效，但未针对 TV，也未区分 common/differential 的边际价值；开发选择标准更是相对降幅，而 guard 是绝对参照。
6. **论文级下一步应从“经验 reward 调参”转向两个可计算对象：**真实 DAE 的 modal sensitivity `G/H_d`，以及带动作约束的 robust Pareto 值函数 `V(rho)`。

---

## 4. 参考文献

### 数据包内证据

- `README.md`; `brief.md`。
- `feeds/R428.md`, `R430.md`, `R431.md`, `R432.md`。
- `data/r428_c1_sac_formal_analysis.json`。
- `data/r430_adapted_sac_formal_analysis.json`。
- `data/r431_sac_slew_formal_analysis.json`。
- `data/r431_reference_action_stats.json`。
- `data/r432_diagnostics/*.json`。
- `data/r433_dev_lambda.json`。
- `source/v4_config.py`。

### 外部理论背景

1. Haarnoja, T., Zhou, A., Abbeel, P., Levine, S. **Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor.** ICML, PMLR 80, 2018.
2. van Hasselt, H., Guez, A., Hessel, M., Mnih, V., Silver, D. **Learning Values across Many Orders of Magnitude.** NeurIPS 2016; arXiv:1602.07714.（PopArt）
3. Geist, M., Scherrer, B., Pietquin, O. **A Theory of Regularized Markov Decision Processes.** ICML, PMLR 97, 2019.
4. Zhang, S., Yao, H., Whiteson, S. **Breaking the Deadly Triad with a Target Network.** ICML, PMLR 139, 2021.
5. Yang et al. **A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs.** IEEE Transactions on Power Systems, DOI: 10.1109/TPWRS.2022.3221439.
