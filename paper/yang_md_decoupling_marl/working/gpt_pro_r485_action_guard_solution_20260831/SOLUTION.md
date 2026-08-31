# R485 action guard 构念有效性：完整数学审计与裁决

## 结论

**主裁决：`INTERNALLY-VALID-BUT-CONSTRUCT-LIMITED`。** 对应请求的分类标签是：

> **construct-limited command-activity metric**

更精确地说：

| 待判对象 | 结论标签 | 结论 |
|---|---|---|
| 冻结的 `R(a) <= 1.10 R(b)` 与 `V(a) <= 1.10 V(b)` 算术 | `COMPUTATIONALLY VERIFIED`（所附数据范围） | 候选与比较器在同一 normalized executed-command 坐标、同一 profile/record/time grid、同一聚合规则下比较；`0/208` 算术稳定且不是临界阈值现象。 |
| “该 conjunction 蕴含 physical actuator no-harm”这一普遍命题 | `DISPROVED / refuted_by_counterexample` | 既非物理无害的必要条件，也非充分条件。本文给出两个最小反例。 |
| R485 中这些策略实际上是否造成磨损、热、疲劳、能量或硬件伤害 | `INFORMATION INSUFFICIENT` | 输入包没有相应物理状态、传递函数、应力/损伤泛函或绝对安全阈值。 |
| 在新增明确物理桥接假设后，能否把 RMS/TV 当作 physical-stress proxy | `CONDITIONAL` | 可以；但注册的 `1.10` RMS 上限对二次能量只推出至多 `1.10² = 1.21` 倍，而不是 10% 物理能量上限。 |
| 冻结 `VALID-MIXED` 与 `121/208`, `0/208` | `UNCHANGED` | 应保留。需要撤回或改写的是 literal physical-harm / safety 解释，不是冻结计数。 |

因此，顶层问题中三个要求不能同时成立：该比值在固定 R485 数据上**数值条件良好**，但对 horizon、sampling rate、channel weighting 和非线性 normalization 并不普遍解释稳定，也不能由 P0–P8 推出物理无害。

---

## 0. 任务与来源覆盖

```text
Harness: GitHub OK | ref=main@5ff04507b7a84c374a5494a8c8883d9dd0c05946 | task=INTAKE+DELIVER | mode=deep | loaded=NAVIGATION.md, AGENTS.md, profiles/deep.md, harness/WORKFLOW.md, harness/VERIFICATION.md, harness/CONTEXT_POLICY.md, harness/CHAT_PROTOCOL.md
```

任务权威以输入包的 `manifest.json` 为准。它只列出一个开放问题：

`yang-r485-action-guard-construct-validity`。

`tmp/r485_math_questions_for_gpt_pro.md` 中另外两个统计/finite-roster prompt 是上下文材料，并未被本包 manifest 选为待解问题。本交付覆盖率为 **1/1 DONE**。

本审计没有重跑仿真、没有训练、没有更改阈值、没有改写冻结 `0/208`。包中 33 个 manifest 成员和 11 个 SHA256 sidecar 已实际校验；正式表中的 832 个 profile blocks、208 个 policy decisions、16 个 threshold-grid cells 已完整枚举；包内 4 个候选 raw profiles 与 4 个 deterministic-comparator raw profiles已独立重算 action RMS/TV 和 action-to-M/D 映射。

---

## 1. Dimensional audit：固定 R485 内可比，但只在 normalized-command 构念内可比

令 record 数为 `n`、每条 record 的样本数为 `T`、动作通道数为 `C`。R485 中

- `n = 6`；
- `T = 150`；
- `C = 8`，即 4 个 VSG × 2 个 normalized M/D command channels；
- `Δt = 0.2 s`；
- 每条 record 使用 `x[r,-1,c] = 0`。

注册指标为

\[
R(x)=\left(\frac{1}{nTC}\sum_{r=1}^{n}\sum_{t=0}^{T-1}\sum_{c=1}^{C}x_{rtc}^{2}\right)^{1/2},
\]

\[
V(x)=\sum_{r=1}^{n}\sum_{t=0}^{T-1}\frac1C\sum_{c=1}^{C}|x_{rtc}-x_{r,t-1,c}|.
\]

源码定位：

- `src/andes_rl_kundur/evaluation/md_decoupling_headroom.py:400-412,462-464`；
- guard conjunction：`src/andes_rl_kundur/evaluation/r484_tail_guard.py:337-377`；
- frozen `m=1.10`：同文件 `DEFAULT_THRESHOLDS` 与 `memory/rounds/R485/config.json`。

### 1.1 numerator / denominator commensurability

在每个固定 profile 内，candidate `a` 和 deterministic comparator `b`：

1. 都读取 `action_norm` 的同一 `(4,2)` executed-action slots；
2. 都有相同的 6 个 scenarios、150 个 samples、0.2 s grid；
3. 都用相同的 zero-to-first convention、channel averaging 和 record aggregation；
4. 都通过相同 action bounds、slew 和 actuator-mapping checks；
5. 都由同一 decoder 映射到 `delta_M`, `delta_D`, `M_es`, `D_es`。

所以 `R(a)/R(b)` 与 `V(a)/V(b)` 是合法的、无量纲的 **normalized executed-command activity ratios**。这里没有发现 candidate 与 comparator 之间的单位、时间网格、通道数量或 aggregation 实现错配，故不属于 arithmetic-level 的 `fatal metric mismatch`。

但这只证明“相同 normalized command coordinates 中可比”。它不自动证明这些 coordinates 对 physical wear / energy / fatigue 等量具有相同权重。特别是：

- `M` 与 `D` 是不同物理/控制语义的通道，却在一个无量纲平均中等权；
- 不同 VSG/通道的硬件额定值、热容量、带宽和损伤权重未提供；
- normalized-to-physical decoder 是非对称且带 clamp 的，不是统一线性比例。

源码中的 pre-clamp decoder 对每个 M/D normalized coordinate 实际是

\[
g(x)=\begin{cases}
600x,&x\ge 0,\\
200x,&x<0,
\end{cases}
\]

随后 `M`、`D` 分别有 lower clamp。因而相同的 normalized magnitude 在正负方向可以对应 3 倍 physical parameter excursion，二次量则可相差 9 倍。`actuator_mapping_pass` 只证明这个 decoder 被正确执行，并不证明 normalized RMS/TV 就是物理应力。

---

## 2. Scaling audit：`R` 与 `V` 不具有相同的尺度律

### 2.1 records

若把每条 record 完整复制 `k` 次：

\[
R(x^{(k\text{ records})})=R(x),\qquad
V(x^{(k\text{ records})})=kV(x).
\]

因此 raw `V` 是 record 总和，不是 per-record average。R485 中 candidate 与 comparator 都固定为 6 records，所以当前比值不受影响；跨不同 record roster 时，未经归一化的 `V` 不能直接比较。

### 2.2 channels

若把所有通道逐一等值复制 `k` 次，因为两项指标都按 channel count 平均，

\[
R\text{ 不变},\qquad V\text{ 不变}.
\]

但新增不同活动水平或不同物理权重的通道会改变二者。等权平均还有两个解释风险：

- 单个关键 actuator 的高应力可以被其余 7 个低活动通道稀释；
- `M`、`D` 或不同设备之间没有给出可把它们合并成一个 physical-stress scalar 的权重。

### 2.3 common scalar normalization

对所有 candidate 和 comparator 通道使用同一 zero-centered scalar `s`：

\[
R(sx)=|s|R(x),\qquad V(sx)=|s|V(x).
\]

因此共同 scalar normalization 会在比值中抵消。

但若使用 channel-specific scale `s_c`、sign-specific scale、affine offset、deadband、clamp 或 hysteresis，则一般不抵消：

\[
R(Sx)^2=\frac1{nTC}\sum s_c^2x_{rtc}^2,
\]

\[
V(Sx)=\sum_{r,t}\frac1C\sum_c |s_c|\,|\Delta x_{rtc}|
\]

只在线性、zero-centered、相同权重条件下保持简单比例。affine shift 会改变 RMS；TV 的内部差分虽消去共同 offset，但 zero-to-first 项不会消去。

对于当前 pre-clamp decoder，标量斜率位于 `[200,600]`。在不发生 clamp 且暂时忽略 M/D 单位混合时，最多只能得到粗界

\[
\frac13\frac{R(a)}{R(b)}\le \frac{R(g(a))}{R(g(b))}\le 3\frac{R(a)}{R(b)},
\]

TV 也有同样的 factor-3 粗界。即使 normalized ratio 通过 `1.10`，decoded-command ratio 仍只可粗略上界为 `3.30`；发生 clamp 后下 Lipschitz 界消失，relative ratio 可能进一步失真。

### 2.4 horizon

若从 `T` 延长到 `T'`，则

\[
R_{T'}^2=\frac{T R_T^2+\text{appended mean-square mass}}{T'},
\]

\[
V_{T'}=V_T+\text{appended path length}.
\]

所以没有与 horizon 无关的统一缩放律：

- 短脉冲后长期为零：horizon 扩大 4 倍时 RMS 降为 1/2，而 TV 基本不变；
- 长时间保持常值：TV 只记录初始跳变，不随 dwell time 增长，但热/能量可能继续累积；
- 持续震荡：RMS 可保持不变，TV 随震荡次数近似线性增长。

所附 checker 对一个单脉冲例子实际验证：horizon 扩大 4 倍，`R` factor = `0.5`，`V` factor = `1.0`。

### 2.5 sampling interval / action rate

当物理 horizon `H=TΔt` 固定且均匀采样时，

\[
R^2=\frac{1}{nCH}\sum x_{rtc}^2\,\Delta t,
\]

可视为 continuous-time RMS 的 Riemann approximation。

`V` 没有 `Δt` 因子。若底层 command path 是 bounded variation，采样足够细时它可以收敛到 continuous total variation；但这需要底层连续路径、相同滤波和充分带宽。对于 sample-level jitter

\[
x_k=\varepsilon(-1)^k,
\]

固定 `H` 下

\[
V\approx 2\varepsilon H/\Delta t,
\]

会随 action update rate 近似按 `1/Δt` 增长，而 RMS 仍为 `ε`。所附 checker 将样本数翻倍时，RMS factor = `1.0`，TV factor = `2.0526`。

**结论：** 在冻结 `n,T,C,Δt` 下比值可解释；跨 horizon、sampling rate 或 channel roster 时，除非增加 continuous-time、filtering 和 weighting 假设，否则解释不稳定。

---

## 3. Conditioning audit：不是“小 denominator 炸比值”

令 `q=A/B`，`B>0`。若测量扰动满足

\[
\widehat A=A(1+e_A),\qquad \widehat B=B(1+e_B),\qquad |e_B|<1,
\]

则

\[
\frac{|\widehat q-q|}{q}
\le
\frac{|e_A|+|e_B|}{1-|e_B|}.
\]

因此 ratio 的一阶 relative condition number 是有限的；真正危险的是 `B=0` 或与数值误差同量级。这里均不成立。

包内数据给出：

| 项目 | comparator | candidate / 全体 ratio |
|---|---:|---:|
| action RMS | profile-level `0.0547–0.0709` | representative candidate `0.39–0.49`; 832-block ratio `min/median/max = 5.748/7.014/9.918` |
| action TV | profile-level `1.58–3.20` | representative candidate `189–216`; 832-block ratio `min/median/max = 48.548/85.097/140.251` |
| registered cap | — | `1.10` |

最接近阈值的 block 仍然：

- RMS ratio 是上限的 `5.2256` 倍；保持 comparator 不变时，candidate RMS 至少要下降 `80.863%` 才到 `1.10`；
- TV ratio 是上限的 `44.1348` 倍；candidate TV 至少要下降 `97.734%` 才到 `1.10`。

此外，registered slew limit 为每 step 每 coordinate `0.25`，故

\[
V\le 6\times150\times0.25=225.
\]

代表性 candidate 的 `V≈189–216`，约占理论上限的 `84%–96%`；comparator 的 `V≈1.58–3.20`，约占 `0.7%–1.4%`。这说明 candidate 在该**命令活动指标**上确实持续大幅变化，而不是浮点误差或接近零分母造成的假象。

数值结论是稳健的；但“变化很多”仍不等于“物理伤害很大”。

---

## 4. Construct audit：guard 精确建立了什么

注册 conjunction 精确建立的命题仅为

\[
(R(a),V(a))\le_{\mathrm{componentwise}}1.10\,(R(b),V(b)),
\]

其中 `a,b` 是相同冻结 profile 上的 normalized executed commands。

它可以合理命名为：

> deterministic-comparator-relative normalized command-amplitude and command-path-length guard

它不能仅凭 P0–P8建立：

- actuator travel、force、current、power、energy；
- thermal load、fatigue、wear、maintenance life；
- resonance-weighted stress 或 bandwidth-limited motion；
- absolute safe operating region；
- hardware / HIL / deployment safety；
- 对 unseen seeds、profiles、topologies 的 no-harm；
- stochastic deployment 的行为。

最后一点尤其需要纠正：`config.json` 说明 SAC 训练 policy 是 stochastic，但 evaluation policy 是 `deterministic_mean`。所以当前 action RMS/TV 描述的是冻结 deterministic evaluation traces，不是 stochastic deployment distribution。

### 4.1 为什么 TV 可被“无害 jitter”支配

TV 是 command path length。若 actuator 有 deadband、低通滤波或 update commands 只改变软件参数而不直接产生对应机械/热运动，高频 normalized jitter 可造成很大的 `V`，但 physical output 很小。相反，若 actuator 能跟踪该 jitter，它也可能确实有害。没有传递函数时，两种解释都与 P0–P8 相容。

### 4.2 为什么 RMS/TV 仍可能漏掉物理伤害

即使二者都低，仍可能存在：

- 方向非对称的 actuator gain；
- 单通道 peak 或关键设备高权重；
- 长时间恒定 command 引发的热积累，而 TV 只记录一次跳变；
- 频率位于 resonance band，RMS/TV 相同但动态应力不同；
- state-dependent load、hysteresis、backlash、saturation dwell；
- comparator 本身已超过绝对安全阈值。

因此 comparator-relative command activity 不是 absolute safety certificate。

---

## 5. 两个最小反例

### 5.1 physically benign but ratio-failing

取最小维度 `n=T=C=1`，`m=1.10`，令

\[
b=\varepsilon,\qquad a=2\varepsilon,
\]

其中 `ε=0.1`。此时

\[
R(a)/R(b)=V(a)/V(b)=2>1.10,
\]

两项 guard 都失败。

定义一个具有 deadband `δ=0.25` 的 physical actuator map：

\[
g(x)=0\quad\text{当 }|x|\le\delta,
\]

并定义 physical harm `H(x)=g(x)^2`。因为 `|a|=0.2`、`|b|=0.1` 均在 deadband 内，

\[
H(a)=H(b)=0.
\]

candidate 物理上完全不比 comparator 有害，却被两项 ratio 拒绝。因此 guard 不是 physical no-harm 的必要条件。

### 5.2 ratio-passing but physically harmful

仍取最小维度 `n=T=C=1`，令

\[
a=+1,\qquad b=-1.
\]

则

\[
R(a)=R(b)=1,\qquad V(a)=V(b)=1,
\]

所以两项 registered guard 都通过。

使用包内实际的 pre-clamp decoder：

\[
g(+1)=+600,\qquad g(-1)=-200.
\]

取 physical quadratic command stress

\[
H(x)=g(x)^2.
\]

则

\[
H(a)=360000,
\qquad
H(b)=40000,
\qquad
H(a)/H(b)=9.
\]

选一个绝对安全上限 `H_max=100000`，则 comparator 安全而 candidate 有害；baseline 可选得足够高使 lower clamp 不激活。candidate 在 normalized RMS/TV 上完全通过，却在这个与实际 decoder 相容的 physical-stress model 下失败。

因此 guard 也不是 physical no-harm 的充分条件。

这两个反例共同严格反驳了“P0–P8 蕴含 physical no-harm ordering”的普遍命题。它们不声称 R485 的真实硬件一定遵循 deadband 或二次 stress model；它们证明的是：输入信息不足以排除这些模型，所以物理蕴含不能从现有 premises 推出。

---

## 6. 在什么额外假设下可以成为 physical-stress proxy

### 6.1 必要的抽象桥梁

若要从 guard 推出某个声明的 physical harm functional `H`，至少必须证明或校准：存在明确 `κ` 使所有 admissible trajectories 满足

\[
R(a)\le mR(b),\;V(a)\le mV(b)
\quad\Longrightarrow\quad
H(a)\le \kappa H(b).
\]

若要声称“无增害”，应有 `κ<=1`；若允许某个相对容忍度，必须把 `κ` 明写。P0–P8 没有提供该 bridge。

### 6.2 一个可证明的具体 sufficient theorem

增加以下假设：

1. **相同线性、zero-centered physical map：** 每个通道 `u=sx`，`s>0`，candidate 与 comparator 共用；无 sign asymmetry、deadband、clamp、hysteresis 或 channel-dependent weights。若通道增益不同，则 registered metric 已按真实 physical weights 重写。
2. **相同 time grid / filter / actuator bandwidth：** 两类 controller 的 commands 经同一已知路径作用于同一 physical variable，sampling 足以表示该路径。
3. **命名物理量：**
   \[
   E(x)=k_E\Delta t\sum_{r,t,c}u_{rtc}^2
   \]
   表示二次 effort/energy proxy，
   \[
   W(x)=k_W\sum_{r,t,c}|u_{rtc}-u_{r,t-1,c}|
   \]
   表示 cumulative travel/wear proxy。
4. **无遗漏损伤项：** physical harm 取
   \[
   H(x)=\alpha E(x)+\beta W(x),\qquad \alpha,\beta\ge0,
   \]
   不依赖未测峰值、频谱、温度状态、cross-channel coupling 或历史。
5. **absolute comparator certificate：** 若要推出 safety，而不仅是 relative stress，需要 comparator 有独立安全余量。

则相同 `n,T,C,Δt` 下可严格推出

\[
\frac{E(a)}{E(b)}=\frac{R(a)^2}{R(b)^2}\le m^2,
\]

\[
\frac{W(a)}{W(b)}=\frac{V(a)}{V(b)}\le m.
\]

对 `m=1.10`：

\[
E(a)\le1.21E(b),\qquad W(a)\le1.10W(b),
\]

并且

\[
H(a)
\le \alpha m^2E(b)+\beta mW(b)
\le m^2H(b)=1.21H(b).
\]

所以即使在这组理想假设下，registered `1.10` RMS multiplier 对二次 energy/stress 允许的是 **21%** 增长。它不能被写成“物理应力至多增加 10%”。若要获得 absolute safety，还需

\[
H(b)\le H_{\max}/1.21.
\]

上述假设没有被输入包建立；事实上当前 sign-asymmetric decoder 和 clamps 明确违反最简单的统一线性 map 假设。因此“valid physical-stress proxy”只能是一个额外建模后的 `CONDITIONAL` 结果，而不是 R485 当前结论。

---

## 7. Final verdict

### 7.1 请求的三类标签

| 标签 | 是否适用于当前 R485 | 理由 |
|---|---|---|
| `fatal metric mismatch` | **否，就冻结 metric arithmetic 而言** | candidate/reference 的 normalized coordinates、roster、time grid、channel aggregation 和 decoder execution 一致；`0/208` 可复算。 |
| `construct-limited command-activity metric` | **是，主裁决** | 比值可靠测量 comparator-relative normalized command amplitude/path length，但没有物理伤害 bridge。 |
| `valid physical-stress proxy under explicit assumptions` | **仅条件成立** | 需线性/加权 actuator map、动态带宽、损伤泛函与 comparator safety margin；当前均未提供。 |

需要强调一个边界：如果论文把这两项指标直接定义成 literal physical-stress / safety certificate，那么该**物理语义**是被反例推翻的，必须撤回；但这不等于冻结 metric、计数或 `VALID-MIXED` 算术无效。

### 7.2 对 `0/208` 的最强可辩护解释

`0/208` 精确表示：

> 在冻结 R485 finite benchmark 中，没有一个 policy/seed cell 同时满足两个 aggregate endpoint 和全部注册 profile guards；其中所有 832/832 policy/profile blocks 都未满足 deterministic comparator 的 `1.10×` normalized executed-command RMS 上限，也都未满足 `1.10×` summed normalized-command total-variation 上限。

它不表示：

- 208 个 policy 都造成了 physical harm；
- failure probability 是 100%；
- learned control 普遍不安全或不可能；
- comparator 是经硬件认证的安全基线；
- candidate 的能量、磨损、温度或疲劳一定高出相同比例。

### 7.3 对冻结分类的影响

`VALID-MIXED` 保持不变，因为冻结 mapping 只依赖：

- `121/208 > 0` 个 policy/seed cells 同时满足两个 aggregate endpoints；
- `0/208` 通过注册 complete contract。

应修改的是 paper-facing 名称和 claim ceiling：把 `physical/action no-harm guard` 收窄为类似

> `registered frequency-performance and comparator-relative normalized command-activity guard`

除非另有独立 physical-stress model 和安全校准。

---

## 8. 可直接用于论文的句子

### 8.1 推荐英文句子

> On the frozen R485 benchmark, 121 of 208 policy–seed cells met both aggregate endpoint targets, but none met the preregistered complete contract: all 832 policy–profile blocks exceeded the deterministic comparator’s 1.10 ceilings for both normalized executed-command RMS and summed normalized-command total variation. These action terms quantify comparator-relative command activity and do not establish actuator wear, energy, thermal or fatigue stress, hardware safety, or deployment no-harm.

### 8.2 推荐中文句子

> 在冻结 R485 benchmark 中，121/208 个 policy–seed cells 同时达到两个 aggregate endpoints，但 0/208 满足预注册 complete contract；所有 832 个 policy–profile blocks 均超过 deterministic comparator 的 1.10 倍 normalized executed-command RMS 与 summed normalized-command total-variation 上限。上述 action 指标仅刻画比较器相对的 normalized command activity，不构成 actuator wear、energy、thermal/fatigue stress、hardware safety 或 deployment no-harm 证据。

### 8.3 禁止或必须撤回的更强表述

1. “All learned policies were physically harmful or unsafe.”
2. “The 1.10 action guard proves that physical actuator stress cannot increase by more than 10%.”
3. “R485 proves that MARL cannot safely control the Kundur/VSG system.”
4. “0/208 estimates a 100% failure probability on new seeds or profiles.”
5. “The deterministic comparator is a certified safe hardware baseline.”

---

## 9. Prospective/secondary diagnostic：不追溯改变 R485

以下只可作为未来注册或 sealed-data secondary analysis，不得替换 R485 primary metric、不得把 `0/208` 事后改成通过：

- 分开报告 decoded `ΔM` 与 `ΔD`，不把不同物理语义的通道无权重混合；
- 使用额定值/单位校准的 channel weights；
- 根据 actuator bandwidth 先定义 command-to-physical-output transfer model；
- 报告 `Δt` 加权二次 effort/energy、physical path length、peak、dwell、saturation duty、thermal state、fatigue/rainflow 或其他领域认可的 stress functional；
- 使用 absolute safe limits 或经认证 comparator margin，而不只使用相对比值；
- 在任何新结论前重新预注册 metric、threshold、horizon、sampling/filtering 和 claim。

逻辑上，未来 metric 与当前 frozen verdict 是不同 proposition。新增诊断可以说明“为什么旧 metric 失败”或“物理上是否真的有害”，但不能 retroactively 改写旧 proposition 的真值。

---

## 10. Verification provenance 与证据边界

实际执行：

```text
python /mnt/data/r485_solution_build/verification.py \
  --input-zip /mnt/data/r485_gpt_pro_action_guard_20260831.zip \
  --json-out /mnt/data/r485_solution_build/DERIVED_RESULTS.json \
  > /mnt/data/r485_solution_build/verification-output.txt \
  2> /mnt/data/r485_solution_build/verification-stderr.txt
```

执行环境：CPython 3.13.5；exit status `0`；stderr 为空。

实际检查范围：

- 输入 ZIP SHA256：`66a4ae492810e4d64254966a7acfe75a751f93d50138adbcc54f6ce2d5cf68fd`；
- 33/33 manifest hashes；
- 11/11 `.sha256` sidecars；
- 1/1 selected problem roster；
- 832/832 formal profile blocks；
- 208/208 policy decisions 和 break-even rows；
- 16/16 threshold-grid cells；
- 4 candidate + 4 comparator raw profile files，共 48 records、7200 step rows、57600 action coordinates；
- raw `action_norm -> delta_M/delta_D -> M_es/D_es` mapping；
- scaling identities与两个 counterexamples。

证据边界：本 checker 没有重新执行 ANDES 仿真，也没有从 848 个 raw profile files 全量重建正式分析；输入包只包含 8 个 raw profile files。对 832 blocks 的结论是完整枚举 sealed `formal_analysis.json` / post-run audit 中的正式 decision tables，并对包内代表性 raw files 做独立 formula-level recomputation。它足以验证本构念审计所用的冻结计数、ratio range、公式和反例，不构成独立物理硬件验证。

---

## 11. Obligation closure

| Obligation | 状态 | 结论 |
|---|---|---|
| G0 commensurability | `PROVED` | 固定 R485 normalized-command numerator/denominator 同坐标、同 roster、同 grid、同 aggregation。 |
| G1 scaling | `PROVED + CHECKED` | records、channels、horizon、`Δt`、normalization 的尺度律已导出并用 checker 例证。 |
| G2 conditioning | `PROVED + COMPUTATIONALLY VERIFIED` | denominator 非零，ratio 远离 `1.10`；不是 numerical-instability result。 |
| G3 physical implication | `REFUTED` | 必要性与充分性各有最小反例。 |
| G4 added assumptions | `CONDITIONAL THEOREM PROVED` | 在线性 calibrated map + named stress functional + comparator safety margin 下成立。 |
| G5 interpretation of `0/208` | `PROVED` | 仅支持 frozen complete metric failure；不支持 harm/safety/probability/generalization。 |
| G6 prospective metric | `CLOSED` | 已明确标为 prospective/secondary；不能 retroactively 改变 R485。 |

**最终状态：全部 1/1 manifest-selected problems solved；无开放数学义务。物理硬件结论保持 `INFORMATION INSUFFICIENT`，这是来源语义边界，不是未完成的数学步骤。**
