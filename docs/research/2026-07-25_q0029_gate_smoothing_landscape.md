# 从物理信号到可部署门控：R265 动作变差的机制分解与 Q-0029 单机制选择

## Abstract

本调研回答一个已由项目证据限定的问题：R265 的 mode-ratio gate 在 20 条
prospectively sealed 扰动上，相对 static alpha=0.25 改善了物理
VSG-mean IAE 和 normalized synchronization loss 的均值，却把 action total
variation 推高 236.67%，应当怎样做最小、可证伪的机制修复。我们先对 20 条
原始轨迹做 retrospective、zero-ANDES 分解，再从 gain scheduling、VSG 动态
控制、switched/bumpless control、residual RL 与 safety filter 五条引文链核验
22 篇原始文献。轨迹重构达到数值精度，且 alpha telemetry 完全对齐；按项目
action-TV 口径，raw gate 的平均 TV 为 5.5063，其中固定当前 blend 权重下的
base-controller variation 为 1.6089，`delta alpha × controller disagreement`
项为 4.0641，两项因向量抵消产生 -0.1666 的不可加交互。switching 项占三角
上界 67.83%，并与逐场景总 TV 相关 0.9996。文献同时表明：端点控制器稳定或
convex blending 本身不保证 scheduled closed-loop 稳定；low-pass、hysteresis、
slew limiting 和 bumpless transfer 都有不同的延迟与证明责任；部署后外挂
filter 也不能继承原 learned policy 的性能。综合机制匹配、参数维数和可审计
保证，本调研条件性选择**只对共享 alpha 施加单参数、对称、逐步投影式 slew
limiter**，不平滑最终 action，不改变两个基控制器。该选择只冻结机制家族，
不从 R265 反推 rate；下一轮必须先用独立物理 rise-time 或执行器约束固定
`delta_alpha`，再打开全新 sealed bank。该 limiter 是一个有内部状态的新
控制器，必须重新检验物理主终点、action-TV、tail、failure 与 settling；若
失败，应关闭 hand-designed gate family，而不是在同一 bank 上再试第二个 rate。

## 1. Introduction

R265 已经排除了一个简单叙事：项目当前并非“没有物理门控信号”。冻结的
mode-ratio gate 相对 static alpha=0.25，使 physical VSG-mean IAE 的
ratio-of-means 改变 -4.3633%，normalized synchronization loss 改变
-1.8624%，两者 paired 95% interval 都在改善方向越过零；但 mean action-TV
增加 236.6691%，其 descriptive CVaR90 增加 448.0015%，故预注册总 verdict
为 negative。这个结果只能说明“状态选择信号与实现失败同时存在”，不能说明
平滑后仍保留收益，更不能说明 corrected recurrent algorithm 或 topology
generalisation。

现有文献也不允许把这个失败简化为“给 action 加个 filter”。Gain-scheduling
研究早已指出，局部或固定调度点的稳定性、鲁棒性与性能不会自动传递到整体
scheduled system [1], [2]；更直接地，常用 controller blending 在端点控制器
都稳定时仍可在中间调度点失稳 [3]。与此一致，VSG 研究一方面用动态 droop、
adaptive inertia/damping 和滤波状态改善噪声与暂态权衡 [4]–[8]，另一方面又
表明参数变化率、converter/line dynamics 和 rate limiter 本身都会改变稳定
裕度 [4], [5], [9]。因此，本项目需要的是机制诊断后的最小干预，而不是一个
“平滑总会更安全”的先验。

本报告冻结三个研究问题：

- **RQ1**：R265 action-TV 主要来自两个基控制器沿轨迹的自然变化，还是来自
  `delta alpha × controller disagreement`？
- **RQ2**：low-pass、slew/rate limiting、hysteresis/dwell 和 bumpless/
  governor 中，哪个机制最直接、参数最少、且最符合现有稳定性证据？
- **RQ3**：怎样把所选机制变成下一轮不可追逐 R265 的 prospective experiment
  contract，并为后续 bounded residual training 留下正确接口？

报告先说明检索与项目内分解方法，再建立机制 taxonomy，随后比较连续滤波、
硬 rate bound、hybrid switching 和 learning-time smoothing，最后逐一回答
三个 RQ。核心判断不是“slew limiter 最优”，而是：**在 R265 已测得 switching
项主导的条件下，alpha-only slew limiter 是当前最小的可证伪候选；其闭环价值
仍完全未被新数据确认。**

## 2. Methodology

### 2.1 检索范围与视角

检索于 2026-07-25 完成，采用 wide-to-narrow 两轮策略。第一轮分别覆盖：

1. gain scheduling、LPV interpolation、slow scheduling 与 bumpless transfer；
2. VSG/virtual inertia/damping 的 adaptive parameter、noise filtering、
   parameter-rate 与 converter stability；
3. residual RL、action smoothness、post-hoc safety filter 与 constrained
   control evaluation。

第二轮沿 Rugh–Shamma、Hespanha–Morse、Markovic、Mallada、Johannink 与
CAPS 引文链补足反例、近期 power-system rate-limiter 工作和 safety-filter
批评。纳入标准是：原始论文、正式 survey 或作者/机构开放版本；题名、作者、
年份与 venue 可交叉核验；正文只使用摘要或全文能支持的结论。仅有不充分
metadata 的结果不承担具体机制结论，无法确认的条目不进入 references。最终
语料为 22 篇，覆盖五个机制分支；这不是对所有 VSG adaptive control 的穷尽
survey，而是服务 Q-0029 的机制语料。

### 2.2 证据类型

| 证据类型 | 本报告中能支持什么 | 不能支持什么 |
|---|---|---|
| 项目 sealed trace 的 retrospective 分解 | 定位 R265 action-TV 的代数来源 | 不能估计 smooth gate 在新 bank 的效果 |
| gain-scheduling / switched-system 理论 | 说明调度率、插值与切换的稳定条件和反例 | 不能直接证明 black-box RL–droop blend |
| VSG small-signal / Lyapunov 分析 | 说明 inertia/damping 值及变化率会进入稳定裕度 | 不能跨模型移植具体 rate |
| VSG / converter time-domain 或 EMT 仿真 | 说明机制在指定模型和扰动下的动态 trade-off | 不能替代本项目 ANDES 与 sealed OOD 证据 |
| RL 实机/benchmark 结果 | 说明 smoothness regularisation 和 filter integration 的部署问题 | 不能建立电力系统稳定性 |
| survey / methodology | 建立机制边界与常见失败模式 | 不能充当本项目的效果证据 |

### 2.3 R265 action-TV 重构

项目内证据链固定为
[`R265 verdict`](../../memory/rounds/R265/verdict.md)、
[`sealed traces`](../../results/r265_sealed_gate_replication/traces) 与
[`ModeRatioGatedBlend` 实现](../../src/andes_rl_kundur/evaluation/hybrid.py)；
Q-0029 的判据以
[`Q-0029`](../../memory/questions/Q-0029.md) 为准。

设 gate 轨迹中的 learned action 为 \(p_t\)，droop action 为 \(s_t\)，
raw gate action 为

\[
u_t=(1-\alpha_t)p_t+\alpha_t s_t,\qquad 0\le\alpha_t\le 0.25.
\]

对 \(t\ge1\)，使用前一步 trace 中的 `delta_f_es` 重建 V4 observation 的
frequency slot，再按冻结的

\[
\rho_t=\frac{\operatorname{std}(x_t)}
{|\operatorname{mean}(x_t)|+\operatorname{std}(x_t)+10^{-8}},
\qquad
\alpha_t=0.25\operatorname{clip}\left(\frac{\rho_t}{0.05},0,1\right)
\]

计算 alpha。droop action \(s_t\) 由 `k=10` 的冻结公式得到，随后由

\[
p_t=\frac{u_t-\alpha_t s_t}{1-\alpha_t}
\]

解出 learned action。\(t=0\) 使用同场景独立 R201 和 droop trace 的初始动作
求 alpha；四个 controller 在 reset 后面对同一初始状态。重构 action 与原始
trace 的最大绝对误差为 \(1.11\times10^{-16}\)；20 条轨迹的 alpha mean 相对
已保存 telemetry 的最大绝对误差为 \(9.36\times10^{-9}\)，saturated fraction
误差为零。

对 action increment 使用恒等式

\[
\Delta u_t=
\underbrace{(1-\alpha_t)\Delta p_t+\alpha_t\Delta s_t}_{B_t:
\text{base variation}}
+
\underbrace{\Delta\alpha_t(s_{t-1}-p_{t-1})}_{S_t:
\text{switching-disagreement}}.
\]

项目 action-TV 是每步先对两个 action 维度取 L1、再对四个 agent 求均值、
最后对时间求和。因此报告
\(\sum_t\|B_t\|_1/4\)、\(\sum_t\|S_t\|_1/4\) 和
\(\sum_t(\|\Delta u_t\|_1-\|B_t\|_1-\|S_t\|_1)/4\)。最后一项是向量抵消，
三项不是因果可加 attribution；它只保证三者精确闭合。

## 3. Taxonomy：平滑对象比平滑器名字更重要

现有方案可按“修改什么”而不是按论文分为五类。

| 分支 | 修改对象 | 可直接给出的保证 | 主要代价 | 对 Q-0029 的位置 |
|---|---|---|---|---|
| 连续动态滤波 | raw alpha 或测量信号 | bounded input 下可保界；可衰减高频 | 持续相位滞后；时间常数需外部依据 | 有效候选，但不是最小干预 |
| slew/rate limiting | `delta alpha` 或 command derivative | `abs(delta alpha)` 硬上界 | limiter active 时滞后；可能改稳定裕度 | **首选候选** |
| hysteresis/dwell | 切换事件和切换频率 | 在特定 Lyapunov 假设下可限切换数/给 dwell | 路径依赖、至少双阈值、仍可大跳 | 与连续 ratio gate 不完全匹配 |
| bumpless/governor | controller state、reference 或约束可行性 | 模型成立时可优化 transient 或强制约束 | 模型、状态、权重、在线优化 | 理论邻域；当前过重 |
| training-time smooth/safe residual | learned mapping、executed action 与安全集 | 可让训练适应 filter；部分方法给约束保证 | 必须重训、增广 state、做安全模型 | 下一阶段，不属于本轮 frozen gate |

这个 taxonomy 有一个明确空单元：**当前没有工作直接证明一个 legacy recurrent
policy 与 droop 的 state-dependent convex gate，在 unseen disturbance 或 unseen
topology 上经过任意 post-hoc smoother 后仍保持性能或稳定。** Gain-scheduling
理论能说明为什么需要 scheduling-rate 条件 [2], [3]，VSG 理论能说明变化率
进入稳定裕度 [4], [5]，safe RL 能说明 filter 与 policy 分离会造成新行为
[20], [21]；但三者的交集仍需本项目自己建立。

## 4. RQ1：R265 是 switching-dominant，不是 base-controller-dominant

### 4.1 精确分解结果

下表是 20 条 R265 development trajectories 的场景均值，单位沿用 normalized
action-TV。

| 项 | 场景均值 | 相对实际 TV | 解释 |
|---|---:|---:|---|
| actual raw-gate TV | 5.506335 | 100.00% | 与 R265 summary 一致 |
| base variation \(\sum\|B_t\|_1/4\) | 1.608869 | 33.40% | 固定当前 alpha 时两个基动作的变化 |
| switching \(\sum\|S_t\|_1/4\) | 4.064090 | 70.03% | `delta alpha × previous disagreement` |
| norm interaction / cancellation | -0.166624 | -3.43% | L1 三角不等式下的抵消 |

switching 项占 \(\|B_t\|+\|S_t\|\) 三角上界的场景平均 67.83%，逐场景
actual TV 与 switching TV 的 Pearson correlation 为 0.99956，而与 base TV
的 correlation 为 -0.426。由于只有 20 个 development scenarios，本报告不把
correlation 写成总体推断；但其方向和量级足以通过 R266 预设的
switch-dominant routing gate。特别是 base variation 1.6089 与 R265 static
alpha=0.25 的 mean TV 1.6355 接近，而 raw gate 的 5.5063 多出的部分几乎全部
由 alpha trajectory 注入。

### 4.2 是少数跳变，还是持续 chatter

R265 的 \(|\Delta\alpha|\) median 为 0.00513，90th percentile 为 0.05484，
95th percentile 为 0.08538；每场景 149 个 transitions 中，alpha 增量符号
反转平均 74.35 次，说明高频往返真实存在。但 TV 并非由大量极小步均匀累积：
仅 22.25% 的 transitions 满足 \(|\Delta\alpha|>0.025\)，它们贡献 77.58%
的 switching TV；11.11% 满足 \(|\Delta\alpha|>0.05\)，贡献 55.31% 的
switching TV。换言之，R265 同时含 chatter 和大 slope，但 action-TV excess
更集中于相对少数的大 slope。

这个分解是**诊断，不是反事实回放**。把历史 \(\Delta\alpha\) 离线截断后重新
相加，会忽略平滑器改变 action 后造成的闭环状态、下一步 observation、raw
alpha 和 controller disagreement 联动变化，因而不能预测任何候选 rate 的
真实效果。本报告刻意不做这种 post-hoc “伪仿真”，所有效果判断留给新的
sealed closed-loop bank。

这个诊断解释了为什么文献中的“continuous filter versus rate bound”不能仅靠
先验决定。Dynamic droop 和 adaptive VSG 工作表明一阶动态环节可在噪声、
同步速度与 nadir 之间调节 [6]–[8]；但 gain-scheduling 与 adaptive VSM 分析
更直接地把 scheduling/inertia variation rate 写入稳定条件 [2]–[4]。R265 的
数据又表明大 slope 贡献占主导，因此当前更需要对 `delta alpha` 给硬界，而
不是无条件地把所有 alpha 变化低通。

## 5. RQ2：为什么选择 alpha-only slew limiter

### 5.1 连续 low-pass：有理论先例，但会一直改写响应

Mallada 的 iDroop 和 Jiang 等人的 dynamic droop 都用显式动态状态摆脱
static droop 与 virtual inertia 的部分性能耦合；后者同时分析 step/stochastic
disturbance 和 measurement noise，指出 virtual inertia 可能显著放大噪声，而
dynamic droop 可在 noise rejection、synchronization speed 与 nadir 之间调节
[6], [7]。Gurski 等人的 adaptive VSG 则把一阶 filtered state 与 bounded
adaptive damping 结合 [8]。三者共同支持“有状态动态环节比直接微分或快速改
参数更可解释”，但都没有给 Kundur gate 的通用 time constant。

若使用

\[
\alpha_t^f=(1-\beta)\alpha_{t-1}^f+\beta\alpha_t^{raw},
\quad 0<\beta<1,
\]

bounded raw alpha 可保证 filtered alpha 仍在 \([0,0.25]\)，并给出
\(|\Delta\alpha_t^f|\le0.25\beta\)。但该 filter 对每一步都起作用，即使
raw gate 已足够慢，也会持续引入 lag。与此相对，slew limiter 在 raw slope
低于 bound 时完全透明。考虑到 R265 switching TV 的 77.58% 集中在
\(|\Delta\alpha|>0.025\) 的 22.25% transitions，当前更有理由只干预大 slope。

### 5.2 slew/rate limiting：对症且有硬界，但不是稳定性免费午餐

推荐的唯一候选是

\[
\alpha_0^{s}=\alpha_0^{raw},
\qquad
\alpha_t^{s}
=\operatorname{clip}\!\left(
\alpha_t^{raw},
\alpha_{t-1}^{s}-\delta_\alpha,
\alpha_{t-1}^{s}+\delta_\alpha
\right).
\]

因为 raw alpha 已在 \([0,0.25]\)，该递推保持相同区间并严格保证
\(|\Delta\alpha_t^s|\le\delta_\alpha\)。它只增加一个 controller state
和一个对称 rate，不改 `ratio_full_scale=0.05`、`alpha_cap=0.25`、R201、
droop 或 final action 的 box。相较 low-pass，它在不触发时透明；相较
hysteresis，它限制 jump magnitude 而非只限制 jump count；相较 command
governor，它不需要预测模型与在线优化。

这个选择不等于“rate limiting 增强稳定”。Shamma–Athans 和 Stilwell–Rugh
都表明 scheduling-rate 与 interpolation 需要独立稳定条件 [2], [3]；
Adachi–Awaya 则展示 actuator rate saturation 可增加 phase lag 并使高响应
闭环失稳 [10]。最直接的 power-system 反证来自 Alexakis 等人：其 smooth
rate-limiter model 能把 derivative bound 纳入 eigenvalue analysis，也在
converter case 中复现 rate-limiter-induced instability，并显示 rate-limited
PI 会出现 windup-like overshoot 和更长 settling [9]。因此，本项目只能声称
slew limiter 对 \(S_t\) 给硬界，不能声称它自动改善 frequency stability。

Alassi 等人在 black-start/grid synchronization 中用 rate limiter 使 reference
渐变 [11]，Alexakis 等人则说明同类机制既可消除 abrupt torque 引起的振荡，
也可在别的闭环中诱发不稳定 [9]。两项结果并不矛盾：rate limiting 的作用取决
于 limiter 所在环节、active fraction、plant bandwidth 与 controller state。
这正是下一轮必须把 `alpha_raw`、`alpha_executed`、`delta_alpha`、
intervention fraction 与物理响应一起保存的原因。

### 5.3 hysteresis/dwell：能减少 switch count，却不能解决连续 gate 的 slope

Hespanha–Liberzon–Morse 的 hierarchical hysteresis 能在特定 monitoring
signal、controller family 与 uncertainty 假设下约束有限区间内的 switch
次数，并与 average dwell-time 理论建立稳定性联系 [12], [13]。但同一工作也
指出固定 dwell-time 可能迫使坏 controller 继续工作到性能不可接受；对某些
非线性 plant，状态甚至可能在允许下次切换前逃逸 [12]。因此，减少切换频率
既不等于限制 jump magnitude，也不等于保留 transient performance。

VSG 证据进一步削弱了本项目对 hysteresis 的优先级。Markovic 等人指出
bang-bang inertia 的切换特性会导致 oscillatory behavior，而带 RoCoF
threshold 的 self-adaptive 策略仍有 discontinuous response [14]；其后续
continuous adaptive VSM 分析把 damping margin 与 maximum inertia-rate 联系，
且明确说明显式 switching 方法不在同一稳定性证明内 [4]。本项目的 raw alpha
本来就是连续 ratio，而非两个离散 mode；加入 hysteresis 至少需要 upper/lower
threshold 和路径状态，却仍不能对每次 alpha jump 给硬界，故不选。

### 5.4 bumpless transfer 和 governor：理论正确，但解决的是更重的问题

Hanus 等人的 conditioning technique 通过让 controller 感知实际 plant input
与期望 output 的差异，实现 anti-windup 与 bumpless transfer [15]；Zaccarian–
Teel 则更严格地指出，单纯让 plant input 连续并不足以保证好的 plant-output
transient，应相对 target closed-loop response 定义 \(L_2/l_2\) mismatch [16]。
这两项工作共同提醒：即使 Q-0029 把 action-TV 压下去，只要 physical IAE 或
sync loss 丢失，仍然是 negative。

不过，R265 的两个基 controller 在每一步都被调用，recurrent state 没有因
inactive mode 冻结；测得的主导项又是 `delta alpha × disagreement`，不是
controller state mismatch。因此完整 bumpless compensator 的模型、状态和
权重在当前阶段过重。Reference/command governor 能在模型和可容许集成立时
显式执行 state/input constraints [22]，但它更适合 P3 safety layer，而不是
P0 中只修一个 gate mechanism 的最小 pivot。

### 5.5 RL 证据：当前可测试 post-hoc gate，但未来必须训练/部署一致

Residual RL 的基本论据是把常规 feedback 能解决的结构保留为 prior，让 RL
只学习传统模型难以覆盖的 residual [17]；这支持项目长期的 droop-plus-bounded-
residual 方向，但不提供任意 residual 的稳定或 rate guarantee。CAPS 和
smooth/robust policy 工作则分别在 temporal/spatial action mapping 或局部
policy Lipschitz 上正则，能减少高频控制或增强 measurement-error robustness
[18], [19]，但它们约束的对象不是 Q-0029 当前的 scalar gate slope。

更关键的是 filter integration。Predictive safety filter 可以在模型、terminal
safe set 和可行性假设下修改候选 input 以保证 constraints [20]；Pizarro
Bejarano 等人却显示，只在 evaluation 时把 filter 挂到 controller 后面会因
二者分离而损害 performance/robustness，并可能产生 controller 反复撞 filter
的 chattering，把 filter 纳入 training 才能让 policy 适应 executed dynamics
[21]。因此，Q-0029 可以把 alpha-slew 当作一个**新 controller**做冻结评估，
但进入 corrected residual training 后，rate/safety state 必须进入 observation
或 transition，proposed/executed action 必须同时记录；不能把 test-time filter
说成原 policy 的无损修补。

## 6. Cross-branch synthesis：最小机制与最大论证责任必须同时成立

五个分支的共同结论不是“越平滑越好”，而是三条条件：

1. **先定位 smoothness failure 的生成项。** R265 已满足这个条件：
   switching-disagreement 项占主导；历史 CLM-0475 还表明 R201 本身比 droop
   k10 更平滑，故重新对 learned actor 加 generic smoothness penalty 不对症。
2. **对真正的生成项给最窄保证。** alpha-only slew limiter 直接保证
   \(|\Delta\alpha|\)，不会重写两个基控制器；low-pass 对所有时刻起作用，
   hysteresis 只限 switch count，bumpless/governor 则引入更大的模型与参数面。
3. **不把局部保证升级为闭环保证。** Gain scheduling、VSG rate analysis 和
   safety-filter literature 都说明，新动态状态会改变 closed-loop behavior
   [2]–[4], [9], [20], [21]。Action-TV 通过只是一项 guard，不是 physical
   performance 或 stability verdict。

这也解释了一个看似矛盾的项目事实。R257 显示 droop k10 比 R201 action 更
reactive，却在 synchronization metric 上更好；R265 又显示 raw state gate
过度抖动。二者并不意味着“reactivity 好”或“smoothness 好”，而是说明需要
**有界的任务相关 reactivity**：static blend 太迟钝，raw gate 的 scheduling
rate 无界，目标是检验一个 rate-bounded gate 是否处于二者之间。若新 bank
证明不存在这样的区间，正确结论是关闭 hand-designed gate family，而不是
继续调阈值。

## 7. RQ3：下一轮 prospective experiment contract

### 7.1 冻结对象

下一轮只允许一个新 controller：

```text
alpha_raw = 0.25 * clip(rho / 0.05, 0, 1)
alpha_exec[0] = alpha_raw[0]
alpha_exec[t] = clip(
    alpha_raw[t],
    alpha_exec[t-1] - delta_alpha,
    alpha_exec[t-1] + delta_alpha,
)
u[t] = learned[t] + alpha_exec[t] * (droop[t] - learned[t])
```

保持 `ratio_full_scale=0.05`、`alpha_cap=0.25`、droop k10、R201 checkpoint、
V4 semantics 与 action box 不变。只 rate-limit alpha；不得 rate-limit final
action，因为后者会同时篡改 R201 和 droop 的固有动态。

本报告不从 R265 选择 `delta_alpha`。文献没有可跨系统照搬的通用 rate，
而 Alexakis 等人还指出 device-specific tuning 会影响 dynamics [9]。在生成
新 bank 前，下一 round plan 必须用以下二者之一固定单值：

- 明确的 physical/actuator gate full-scale rise-time \(T_r\)，令
  \(\delta_\alpha=\alpha_{cap}\Delta t/T_r\)；
- 经独立 small-signal/actuator analysis 得到的 rate bound。

不得在 R265 上扫描 `delta_alpha`，不得为追 action-TV 25% guard 反解 rate，
不得设置不同 rise/fall rate、deadband 或附加 hysteresis。若没有外部物理依据
确定单值，应判“尚不能 unseal”，而不是猜一个数。

### 7.2 新 bank 与比较

- 用新 seed 生成 no-anchor disturbance bank；写盘、hash 和 manifest 后才运行。
- confirmatory contrasts：`slew gate vs static alpha=0.25` 为主；
  `slew gate vs raw gate` 解释 smoothing effect。
- R265 只作 development/provenance，不进入 confirmatory interval。
- 同一场景 paired evaluation；controller order 继续轮换。
- 不做第二个 rate；若失败，关闭 hand-designed gate family。

### 7.3 终点与 decision rule

保持 Q-0029 的 co-primary：

- physical VSG-mean IAE；
- physical normalized synchronization loss。

保持 guards：

- failure / incomplete trace；
- worst-bus peak、max RoCoF、settling；
- mean 与 descriptive CVaR90；
- action L1、action-TV，且 action-TV CVaR90 相对 static 不得坏超过 25%。

新增 mechanism telemetry：

- `alpha_raw`、`alpha_exec`、`delta_alpha_exec`；
- rate-limit active fraction 和最长连续 active run；
- controller disagreement \(\|s_t-p_t\|_1\)；
- base/switch/interaction decomposition；
- max action slew、二阶差分/jerk 与高频 action energy。

只有两项 physical co-primary 都保留预声明改善方向、failure/tail/settling 不
回退，且 action-TV CVaR90 guard 通过，才允许进入 corrected multi-seed residual
training。Action-TV 通过但 physical gain 丢失是 negative；physical gain 保留
但 action-TV 仍失败也是 negative。这个判据落实了 bumpless literature 的核心
警告：plant input 更平滑不等于 plant output 更好 [16]。

## 8. Open problems and future directions

### 8.1 rate 的物理来源仍是空单元

现有文献能说明 scheduling rate 必须有界 [2]–[4]，也能给 power-system rate
limiter 的可线性化模型 [9]，但没有研究为本项目的 normalized alpha 提供
通用 rate。下一步真正缺的不是更多 smoothing families，而是从 actuator、
VSG parameter dynamics 或 small-signal stability 得到可解释 \(T_r\)。

### 8.2 legacy checkpoint 机制与 corrected algorithm 必须分开

R265/R266 只能证明 legacy R201 参与的 hand-designed composition 机制。Residual
RL 文献支持保留 physical prior [17]，CAPS/smooth policy 文献支持在 training
中塑造 learned mapping [18], [19]；但 corrected recurrent target、multi-seed
training 和 training-time rate/safety layer 仍未验证。不得把 smooth gate 的
任何结果写成 corrected recurrent performance。

### 8.3 stability analysis 需要从经验 guard 升级

当前 action-TV、RoCoF 和 failure 是 empirical safety evidence，不是 stability
certificate。P2/P3 应把 droop closed loop 加 bounded residual 视为受扰系统，
研究 ISS/robust invariant set、LPV rate-dependent Lyapunov 或 predictive
safety filter；同时借鉴 Alexakis 等人的 smooth rate-limiter state，把 limiter
显式纳入 eigenvalue 或 nonlinear analysis [9], [20]。

### 8.4 topology generalisation 仍完全未被本轮触及

所有 R265/R266 数值都来自 modified Kundur topology。即使 Q-0029 positive，
它也只建立 residual mechanism 的 feasibility。Topology-general claim 仍需
multiple training graphs、entirely held-out systems/VSG counts/communication
graphs 和 size-matched non-graph ablation；line outage on Kundur 只能算 robustness。

## 9. Conclusion

**RQ1：action-TV 来自哪里？** R265 是明确的 switching-dominant case。20 条
轨迹的 action 和 alpha 可精确重构；base variation 平均 1.6089，switching-
disagreement 平均 4.0641，后者占三角上界 67.83%，与逐场景实际 TV 相关
0.9996。这个结论是 R265 development diagnosis，不是新 bank 的效果证据。

**RQ2：选哪个机制？** 条件性选择 alpha-only、对称、单参数 slew limiter。
它对主导项 \(\Delta\alpha(s-p)\) 给最窄的硬界，在 limiter 不 active 时不改
raw gate；low-pass 持续引入 lag，hysteresis/dwell 不能限制 jump magnitude，
bumpless/governor 对当前问题过重。文献同时明确反驳“rate limiting 自动稳定”：
limiter 可能引入 phase lag、windup-like transient 甚至 instability，因此它
必须作为新 controller 重新验证。

**RQ3：怎样避免下一轮变成 post-hoc tuning？** 在新 bank 生成前，用独立
physical rise-time 或 small-signal/actuator analysis 固定唯一
`delta_alpha`；不在 R265 扫 rate，不改变 0.05/0.25，不滤 final action。新
sealed bank 只比较 static、raw gate 和这一 smooth gate，并保留 physical
co-primary、failure/tail/settling 与 action-TV guard。一次失败即关闭
hand-designed gate family。

本调研对项目的贡献不是宣布一个新算法，而是把 Q-0029 从“试一个平滑器”
收敛为可推翻的机制命题：**若对 alpha slope 给一个事先固定的物理硬界，仍
无法同时保留 R265 的两项物理均值方向并把 action-TV tail 拉回 guard，则
hand-designed state gate 不值得继续；项目应转向 training/deployment
一致的 bounded learned residual 与显式 safety layer。**

## References

[1] Wilson J. Rugh, Jeff S. Shamma, “Research on Gain Scheduling,”
*Automatica*, 36(10), 1401–1425, 2000.

[2] Jeff S. Shamma, Michael Athans, “Guaranteed Properties of Gain Scheduled
Control for Linear Parameter-Varying Plants,” *Automatica*, 27(3), 559–564,
1991.

[3] Daniel J. Stilwell, Wilson J. Rugh, “Stability Preserving Interpolation
Methods for the Synthesis of Gain Scheduled Controllers,” *Automatica*, 36(5),
665–671, 2000.

[4] Uros Markovic, Zhongda Chu, Petros Aristidou, et al., “LQR-Based
Adaptive Virtual Synchronous Machine for Power Systems With High Inverter
Penetration,” *IEEE Transactions on Sustainable Energy*, 10(3), 1501–1512,
2019.

[5] Junru Chen, Terence O’Donnell, “Parameter Constraints for Virtual
Synchronous Generator Considering Stability,” *IEEE Transactions on Power
Systems*, 34(3), 2479–2481, 2019.

[6] Enrique Mallada, “iDroop: A Dynamic Droop Controller to Decouple Power
Grid’s Steady-State and Dynamic Performance,” *Proceedings of the IEEE
Conference on Decision and Control*, 4957–4964, 2016.

[7] Yan Jiang, Richard Pates, Enrique Mallada, “Dynamic Droop Control in
Low-Inertia Power Systems,” *IEEE Transactions on Automatic Control*, 66(8),
3518–3533, 2021.

[8] Erico Gurski, Roman Kuiava, Filipe Perez, et al., “A Novel VSG with
Adaptive Virtual Inertia and Adaptive Damping
Coefficient to Improve Transient Frequency Response of Microgrids,” *Energies*,
17(17), 4370, 2024.

[9] Zaint A. Alexakis, Panos C. Papageorgiou, Antonio T. Alexandridis, et al.,
“Smooth Rate Limiter Model for Power System Stability
Analysis and Control,” *IEEE Transactions on Power Systems*, 40(4), 3611–3614,
2025.

[10] Takehiro Adachi, Ichiro Awaya, “Stabilization of Motion Control System
with Rate Limiter Using Linear Reference Model,” *Transactions of the JSME*,
81(829), 15-00052, 2015.

[11] Abdulrahman Alassi, Khaled Ahmed, Agusti Egea-Alvarez, et al.,
“Modified Grid-Forming Converter Control for Black-Start and
Grid-Synchronization Applications,” *Proceedings of the International
Universities Power Engineering Conference*, 1–5, 2021.

[12] João P. Hespanha, Daniel Liberzon, A. Stephen Morse, “Hysteresis-Based
Switching Algorithms for Supervisory Control of Uncertain Systems,”
*Automatica*, 39(2), 263–272, 2003.

[13] João P. Hespanha, A. Stephen Morse, “Stability of Switched Systems with
Average Dwell-Time,” *Proceedings of the IEEE Conference on Decision and
Control*, 2655–2660, 1999.

[14] Uros Markovic, Nicolas Früh, Petros Aristidou, et al.,
“Interval-Based Adaptive Inertia and Damping Control of a Virtual Synchronous
Machine,” *Proceedings of IEEE Milan PowerTech*, 1–6, 2019.

[15] Raymond Hanus, Michel Kinnaert, Jean-Luc Henrotte, “Conditioning
Technique, a General Anti-Windup and Bumpless Transfer Method,” *Automatica*,
23(6), 729–739, 1987.

[16] Luca Zaccarian, Andrew R. Teel, “The L2 (l2) Bumpless Transfer Problem for
Linear Plants: Its Definition and Solution,” *Automatica*, 41(7), 1273–1280,
2005.

[17] Tobias Johannink, Shikhar Bahl, Ashvin Nair, et al., “Residual
Reinforcement Learning for Robot Control,” *Proceedings of the IEEE
International Conference on Robotics and Automation*, 6023–6029, 2019.

[18] Siddharth Mysore, Bassel Mabsout, Renato Mancuso, et al.,
“Regularizing Action Policies for Smooth Control with Reinforcement Learning,”
*Proceedings of the IEEE International Conference on Robotics and Automation*,
1810–1816, 2021.

[19] Qianli Shen, Yan Li, Haoming Jiang, et al., “Deep
Reinforcement Learning with Robust and Smooth Policy,” *Proceedings of the
International Conference on Machine Learning*, PMLR 119, 8707–8718, 2020.

[20] Kim Peter Wabersich, Melanie N. Zeilinger, “A Predictive Safety Filter for
Learning-Based Control of Constrained Nonlinear Dynamical Systems,”
*Automatica*, 129, 109597, 2021.

[21] Federico Pizarro Bejarano, Lukas Brunke, Angela P. Schoellig, “Safety
Filtering While Training: Improving the Performance and Sample Efficiency of
Reinforcement Learning Agents,” *IEEE Robotics and Automation Letters*, 10(1),
788–795, 2025.

[22] Emanuele Garone, Stefano Di Cairano, Ilya Kolmanovsky, “Reference and
Command Governors for Systems with Constraints: A Survey on Theory and
Applications,” *Automatica*, 75, 306–328, 2017.
