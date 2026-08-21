---
title: "受限动作与部分信息下的稳健残差余量：严格定义、证书与训练前判定"
source: "gpt_pro_residual_headroom_math_problem.md"
status: "严格修订版：已闭合动态非预见性与误差依赖；数值求解仍需项目数据包"
---

# 受限动作与部分信息下的稳健残差余量


> **严格修订说明**
>
> - 命题 3 已改为基于动作施加前信息前缀的当前可延续动作集合，并补充有限动态场景树的非预见等价性。
> - 稳健物理可行域统一改为 $\mathcal A_{s,\Delta}(B)$；只有项目明确声明误差不影响物理状态和约束时才退化为 $\mathcal A_{s,0}(B)$。
> - 数值数据清单改为“现有文件可提取 / 基于既有矩阵必须重算 / 当前限制下不可补齐”三类，不假定允许新仿真或训练。

> 本文严格按照附件“最终交付物”的顺序组织。核心目标不是直接选择强化学习算法，而是在冻结确定性控制器后，先判断是否存在具有非平凡性能余量、物理可行、因果可识别且在模型误差下仍有效的分布式残差控制问题。
>
> 当前附件只给出数学合同、已有证据摘要和项目文件路径，并未附带逐场景数值矩阵或这些项目文件本身。因此本文只做符号修订、可复现数值方案和数据状态分级；不假定允许新仿真或训练，也不把未核验的项目字段视为已经存在。
>
> 本修订版重点纠正两点：信息不可能性必须在决策时刻基于信息前缀和当前可延续动作，而不能由完整动作序列集合不相交直接推出；响应误差若进入物理状态、观测或约束，稳健可行域必须写成 $\mathcal A_{s,\Delta}(B)$。

## 1. 修正后的严格问题定义

### 1.1 核心数学问题复述

核心问题不是“选哪一种强化学习算法”，而是：

> 在冻结确定性控制器后，给定节点动作基 $B$、因果分布式信息结构 $\mathcal I$、物理约束和响应模型误差集合，是否存在**同一个预先确定的因果策略**，能够在所有注册场景和允许的模型误差下保持物理可行，并使公共坐标与差分坐标同时获得至少 $2\%$ 的改进？

必须依次区分：

$$
\text{节点动作存在}
\Rightarrow
\text{给定动作基可表达}
\Rightarrow
\text{给定信息可识别}
\Rightarrow
\text{给定函数族可实现}
\Rightarrow
\text{模型误差下仍有效}.
$$

附件将任务定义为训练前的存在性与可识别性判定，而不是直接选择神经网络或强化学习算法。

### 1.2 维度、时序与误差语义

令

$$
n=4,
\qquad
T=25,
\qquad
K_B:=I_T\otimes B\in\mathbb R^{4T\times mT}.
$$

附件给出的名义有限时域性能响应为

$$
y_{s,\Delta}(a)
=
y_s^0+(G_s+\Delta^y)K_Ba,
$$

其中

$$
y_s^0\in\mathbb R^{4T},
\qquad
G_s,\Delta^y\in\mathbb R^{4T\times4T},
\qquad
a\in\mathbb R^{mT}.
$$

这里把完整不确定性实现仍记为 $\Delta\in\mathcal U_s$，而 $\Delta^y$ 表示其中作用于性能输出响应矩阵的分量。为了判断稳健物理可行性和因果可实现性，还必须声明同一个 $\Delta$ 是否进入物理状态、观测和约束。一般闭环模型写成

$$
x_{s,\Delta,k+1}
=
f_{s,k,\Delta}
\bigl(x_{s,\Delta,k},p_{s,k}^0+Ba_{s,\Delta,k}\bigr),
$$

$$
o_{q,k}^{s,\Delta,\pi}
=
h_{q,s,k,\Delta}
\bigl(x_{s,\Delta,0:k},a_{s,\Delta,0:k-1}^{\pi}\bigr),
$$

$$
g_{s,k,\Delta}
\bigl(x_{s,\Delta,k},p_{s,k}^0+Ba_{s,\Delta,k},a_{s,\Delta,k}\bigr)
\le0.
$$

必须在数据合同中从以下三种语义中选择一种，不能混用：

1. **仅评价误差**：$\Delta^y$ 只改变离线性能评价，不改变实际物理状态、运行时观测或物理约束。此时 $\mathcal A_{s,\Delta}(B)=\mathcal A_{s,0}(B)$，且观测历史不因 $\Delta$ 改变。
2. **测量或输出误差**：$\Delta$ 不改变物理状态和约束，但会改变策略能够看到的频率、电压或其他观测。此时物理可行域可保持 $\mathcal A_{s,0}(B)$，但信息滤过和策略产生的动作依赖 $\Delta$。
3. **对象一致误差**：$\Delta$ 同时影响性能输出、物理状态、观测或约束。此时必须使用 $\mathcal A_{s,\Delta}(B)$，并在每个不确定性分支上重新展开状态、观测和约束。

附件只把 $\Delta_s$ 称为响应模型误差，没有说明它属于上述哪一种。因此，本文后续的稳健定义采用最一般的 $\mathcal A_{s,\Delta}(B)$；只有在项目合同明确声明“仅评价误差”时，才可化简为与 $\Delta$ 无关的 $\mathcal A_s(B)$。

$G_s$ 和所有 $\Delta^y$ 应与实际采样时序一致并具有因果块下三角结构。若存在同一采样时刻的直接通道，则必须采用以下二者之一：

1. $a_k$ 使用动作施加前的信息 $\mathcal F_{k^-}$；
2. 当前观测不包含由 $a_k$ 产生的同刻输出。

否则 $a_k=\pi(\mathcal F_k)$ 与响应矩阵的对角块会形成代数环。

定义选择矩阵

$$
C_c\in\mathbb R^{T\times4T},
\qquad
C_d\in\mathbb R^{3T\times4T},
$$

使得

$$
y_c=C_cy,
\qquad
y_d=C_dy.
$$

公共—差分变换虽然可逆，但不得删除动态响应矩阵中的公共—差分交叉块；零和节点功率仍可能通过动态交叉耦合影响公共坐标。

### 1.3 误差依赖的物理可行域

节点残差功率为

$$
u=K_Ba,
\qquad
p_s=p_s^0+K_Ba.
$$

对完整不确定性实现 $\Delta$，定义

$$
\boxed{
\mathcal A_{s,\Delta}(B)
=
\left\{
\begin{array}{l|l}
a &
\begin{array}{l}
\exists x_{0:T}\text{ 满足 }x_{k+1}=f_{s,k,\Delta}(x_k,p_{s,k}^0+Ba_k),\\
 g_{s,k,\Delta}(x_k,p_{s,k}^0+Ba_k,a_k)\le0,\quad k=0,\ldots,T-1,\\
 a\text{ 满足边动作、公共通道和其他坐标专属约束}
\end{array}
\end{array}
\right\}.
}
$$

它包含节点功率、爬坡、能量、SOC、电流、电压、保护和执行约束。若允许四个节点直接独立选择 $u_k$，把去掉动作坐标专属限制后、由同一状态和约束合同定义的节点动作集合记为 $\mathcal U_{s,\Delta}^{\rm node}$；它是第 2 节全动作余量使用的物理集合。名义集合记为

$$
\mathcal A_{s,0}(B).
$$

若项目确认 $\Delta$ 只改变性能评价，则

$$
\mathcal A_{s,\Delta}(B)=\mathcal A_{s,0}(B),
\qquad\forall\Delta\in\mathcal U_s.
$$

若 $\Delta$ 只改变观测而不改变物理状态和约束，上式仍可成立，但策略动作 $a_{s,\Delta}^{\pi}$ 一般会因为观测不同而变化。若 $\Delta$ 改变 SOC、电压、电流或保护边界，则继续使用 $\mathcal A_s(B)$ 会漏掉稳健物理失效，是不正确的。

为保证有限维优化中的最优值可达到，通常需要假设每个相关的 $\mathcal A_{s,\Delta}(B)$ 非空、闭且有界；零动作是否属于该集合必须逐分支验证，不能仅由名义可行性推断。

### 1.4 因果分布式策略及内生观测

动作坐标或动作块 $q$ 在时刻 $k$ 使用动作施加前的信息

$$
\mathcal F_{q,k}^{s,\Delta,\pi}
=
\sigma\!\left(
 o_{q,0:k}^{s,\Delta,\pi},
 m_{q,0:k}^{s,\Delta,\pi}
\right),
$$

并满足

$$
a_{q,k}^{s,\Delta,\pi}
=
\pi_{q,k}
\left(
\mathcal F_{q,k}^{s,\Delta,\pi}
\right).
$$

上标 $\pi$ 不能省略为纯粹形式问题：若动作影响后续状态和观测，则信息历史由系统、误差和既往策略共同生成。策略函数 $\pi_{q,k}$ 必须在所有场景和误差分支上是同一个映射，只允许输入值随分支变化。

还必须要求：

- $\pi_{q,k}$ 对相应信息前缀可测；
- 消息 $m_{q,k}$ 由允许的历史因果地产生；
- 通信方向、延迟、带宽、量化和丢包规则被固定；
- 场景编号、运行点编号、扰动位置与符号、未来输出、最终指标和离线最优标签不得作为运行时输入；
- 非预见性按每个动作块分别施加，而不是只对拼接后的集中式动作施加。

对于 $B_+$，还必须定义公共动作 $c_k$ 的控制主体和信息前缀。仅写“$B_+,\mathcal I_{\rm local}$”并不能确定 $c_k$ 是集中式、共识式、广播式还是由某一节点产生。

### 1.5 性能指标和统一标量化

令

$$
z_{c,s,\Delta}(a)=C_cy_{s,\Delta}(a),
\qquad
z_{d,s,\Delta}(a)=C_dy_{s,\Delta}(a).
$$

定义

$$
J_{c,s,\Delta}(a)
=
\Delta t\,\|z_{c,s,\Delta}(a)\|_1,
$$

$$
J_{d,s,\Delta}(a)
=
\Delta t\,\|z_{d,s,\Delta}(a)\|_2^2.
$$

若沿用附件中的固定基线归一化，必须有

$$
J_{c,s,0}(0)>0,
\qquad
J_{d,s,0}(0)>0.
$$

定义

$$
L_{s,\Delta}(a)
=
\max\left\{
\frac{J_{c,s,\Delta}(a)}{J_{c,s,0}(0)},
\frac{J_{d,s,\Delta}(a)}{J_{d,s,0}(0)}
\right\}.
$$

则公共和差分同时提高至少 $\epsilon$ 等价于

$$
L_{s,\Delta}(a)\le1-\epsilon.
$$

如果项目的模型误差门使用“同一误差分支下的零残差基线”作为分母，则必须把分母改为 $J_{j,s,\Delta}(0)$。附件没有明确这一点，数值包中必须保存精确归一化规则。若对象一致误差还会改变零残差轨迹，则仅写固定 $y_s^0$ 也不再充分，应提供 $y_{s,\Delta}^0$ 或证明零残差基线不受该误差影响。

### 1.6 名义与稳健可行策略集

令 $a_{s,\Delta}^{\pi}$ 表示同一个策略 $\pi$ 在分支 $(s,\Delta)$ 上由闭环观测历史产生的完整动作序列。分别定义名义可行策略集

$$
\Pi_{\rm ad}^{0}(B,\mathcal I)
=
\left\{
\pi\in\Pi(\mathcal I):
 a_{s,0}^{\pi}\in\mathcal A_{s,0}(B),
\quad\forall s
\right\},
$$

以及稳健可行策略集

$$
\boxed{
\Pi_{\rm ad}^{\rm rob}(B,\mathcal I)
=
\left\{
\pi\in\Pi(\mathcal I):
 a_{s,\Delta}^{\pi}\in\mathcal A_{s,\Delta}(B),
\quad\forall s,\ \forall\Delta\in\mathcal U_s
\right\}.
}
$$

严格的 worst-case 余量为

$$
\boxed{
\epsilon_{\rm wc}^{\star}(B,\mathcal I)
=
\sup_{\pi\in\Pi_{\rm ad}^{\rm rob}(B,\mathcal I)}
\inf_{\substack{s\in\mathcal S\\
\Delta\in\mathcal U_s}}
\left[
1-L_{s,\Delta}
\bigl(a_{s,\Delta}^{\pi}\bigr)
\right].
}
$$

等价地，

$$
V_{\rm wc}(B,\mathcal I)
=
\inf_{\pi\in\Pi_{\rm ad}^{\rm rob}}
\sup_{s,\Delta}
L_{s,\Delta}
\bigl(a_{s,\Delta}^{\pi}\bigr),
\qquad
\epsilon_{\rm wc}^{\star}=1-V_{\rm wc}.
$$

若 $\Delta$ 影响观测，则不同误差分支上的动作允许因已观测信息不同而不同；但在尚未被允许信息区分的分支上，动作必须满足非预见约束。不能把上述量替换成逐误差独立选择动作的

$$
\forall\Delta\ \exists a_{s,\Delta},
$$

因为它允许控制器预先知道误差实现。

### 1.7 量词顺序

| 对象 | 正确量词 | 未来与误差信息 |
|---|---|---|
| 逐场景 outcome-seeing oracle | $\forall s\,\exists a_s$；若连误差实现也看见，则 $\forall s,\Delta\,\exists a_{s,\Delta}$ | 可使用完整结果，只是上界 |
| 场景内固定稳健开环动作 | $\forall s\,\exists a_s\,\forall\Delta:\ a_s\in\mathcal A_{s,\Delta}(B)$ | 不根据误差观测调整 |
| 因果集中式控制器 | $\exists\pi_{\rm cen}\,\forall s,\Delta$ | 仅用所有已到达的全局信息 |
| 因果分布式控制器 | $\exists(\pi_q)_q\,\forall s,\Delta$ | 每个动作块只用自己的允许信息前缀 |
| 有限动态场景树 | $\exists\{a_{q,k}^{\omega}\}$，满足每个分支约束与全部非预见等式 | 与树上因果策略等价 |

关键区别仍是

$$
\forall s\,\exists a_s
\quad\not\Rightarrow\quad
\exists\pi\,\forall s,
$$

但还要进一步注意：两个场景的**完整可行动作序列集合不相交**，并不自动推出因果策略不可能。一个因果策略可以先选择相同当前动作，待后续观测分离后再采用不同后缀。信息不可能性必须在某个决策时刻检查共同信息前缀下的当前可延续动作，或直接求解带非预见约束的动态场景树。

### 1.8 名义、物理和稳健可行

应使用以下不同谓词：

- **名义输出可行**：在 $\Delta=0$ 下存在动作满足性能目标，可能尚未加入设备约束；
- **名义物理可行**：在 $\Delta=0$ 下，动作属于 $\mathcal A_{s,0}(B)$ 并满足性能目标；
- **稳健输出可行**：同一个非预见策略在所有 $\Delta$ 下满足性能目标，但尚未声明物理约束是否随 $\Delta$ 变化；
- **稳健物理可行**：对所有 $s,\Delta$，闭环动作满足 $a_{s,\Delta}^{\pi}\in\mathcal A_{s,\Delta}(B)$，并满足性能目标；
- **仅评价包络通过**：固定动作或固定轨迹在一组离线输出误差变换下通过指标，不等价于对象一致的稳健物理可行。

因此，名义性能可行不蕴含物理可行；逐误差分别存在动作不蕴含存在统一非预见策略；仅有输出误差包络也不能证明 SOC、电压、电流和保护约束在误差下仍安全。

### 1.9 Gate-faithful 定义

worst-case 定义不能替代项目注册的统计门。令

$$
x_{j,s,\nu}(\pi)
=
\eta_{j,s,\nu}(\pi),
\qquad
\nu\in\{\mathrm{nom},\mathrm{err}\},
$$

其中 $\mathrm{err}$ 可以是注册的有限误差包络结果，而不一定等于完整集合 $\mathcal U_s$ 上的最坏值。

令 $r\in\mathcal R$ 枚举所有预注册门，并令

$$
\Gamma_r(x)
$$

表示对应统计函数，例如：

$$
\Gamma_r^{\rm LCB}
=
\overline x_r
-
\kappa_r\,\widehat{\operatorname{SE}}_r,
$$

$$
\Gamma_r^{\rm subgroup}
=
d_r\overline x_{r,\rm subgroup},
$$

$$
\Gamma_r^{\rm noharm}
=
\min_{s\in\mathcal S_r}x_s+\delta_r.
$$

这里不能默认正态近似、$t$ 检验、bootstrap、权重或显著性水平；必须使用注册实现中的精确定义。

令

$$
\Pi_{\rm ad}^{\rm gate}(B,\mathcal I)
=
\left\{
\pi:
\pi\text{ 在注册 gate 实际评价的每个分支上满足相应物理可行合同}
\right\}.
$$

若 error 结果只是对名义轨迹的离线评价变换，则该集合可退化为 $\Pi_{\rm ad}^{0}$；若 error 分支代表对象一致误差，则必须使用相应分支上的 $\mathcal A_{s,\Delta}(B)$，即采用 $\Pi_{\rm ad}^{\rm rob}$ 的相应限制。

定义

$$
\boxed{
\epsilon_{\rm gate}^\star
=
\sup_{\pi\in\Pi_{\rm ad}^{\rm gate}}
\sup\left\{
\epsilon:
\Gamma_r\!\left(
\{x_{j,s,\nu}(\pi)\}
\right)
\ge b_r(\epsilon),
\quad\forall r\in\mathcal R
\right\}.
}
$$

其中：

- 联合均值门通常令 $b_r(\epsilon)=\epsilon$；
- 方向性门通常令 $b_r(\epsilon)=0$；
- 最坏场景不伤害门可能令 $b_r=-\delta_r$。

它与 worst-case 余量没有一般的大小关系：

- worst-case 直接把场景视为对手；
- gate 是有限样本统计判定，包含均值、方差、样本量和预定义子组；
- 所有样本均为正仍可能因置信界惩罚而失败；
- 个别样本为负也可能在允许的 no-harm 容差下通过均值门；
- 有限误差包络通过不等价于对整个 $\mathcal U_s$ 稳健。

---

## 2. 五种余量及其单调关系

以下全部使用同一个归一化联合损失 $L$，并把名义可行与稳健可行分开。

### 2.1 全动作物理余量

令四个节点在名义模型下可独立选择残差功率

$$
u_s\in\mathcal U_{s,0}^{\rm node}.
$$

把节点动作下的输出与联合损失定义为

$$
y_{s,\Delta}^{\rm node}(u)
=
y_s^0+(G_s+\Delta^y)u.
$$

由该输出按第 1.5 节同样定义 $J_{c,s,\Delta}^{\rm node}(u)$ 与 $J_{d,s,\Delta}^{\rm node}(u)$，并令

$$
L_{s,\Delta}^{\rm node}(u)
=
\max\left\{
\frac{J_{c,s,\Delta}^{\rm node}(u)}{J_{c,s,0}(0)},
\frac{J_{d,s,\Delta}^{\rm node}(u)}{J_{d,s,0}(0)}
\right\}.
$$

定义

$$
V_{\rm full}
=
\inf_{\{u_s\in\mathcal U_{s,0}^{\rm node}\}_{s\in\mathcal S}}
\max_{s\in\mathcal S}
L_{s,0}^{\rm node}(u_s),
$$

$$
\epsilon_{\rm full}=1-V_{\rm full}.
$$

每个 $u_s$ 可由 outcome-seeing oracle 逐场景独立选择。因此该量只测量冻结基线到名义全节点动作最优值的距离，不包含信息限制。

### 2.2 动作基余量

给定动作基 $B$，定义

$$
V_{\rm basis}(B)
=
\inf_{\substack{a_s\in\mathcal A_{s,0}(B)\\s\in\mathcal S}}
\max_s L_{s,0}(a_s),
$$

$$
\epsilon_{\rm basis}(B)=1-V_{\rm basis}(B).
$$

其量词仍是 $\forall s\,\exists a_s$，所以它检查动作方向和名义物理约束，但不检查统一因果策略是否存在。

### 2.3 信息可恢复余量

允许所有满足指定信息生成规则的可测因果策略，但不限制函数表达形式：

$$
V_{\rm information}(B,\mathcal I)
=
\inf_{\pi\in\Pi_{\rm ad}^{0}(B,\mathcal I)}
\max_s
L_{s,0}(a_{s,0}^{\pi}),
$$

$$
\epsilon_{\rm information}=1-V_{\rm information}.
$$

这里必须通过信息前缀或动态场景树施加非预见约束，不能用逐场景完整动作标签的静态拟合代替。

### 2.4 函数族可实现余量

给定

$$
\Pi_0(\mathcal I)\subseteq\Pi(\mathcal I),
$$

例如仿射、核方法或固定结构模型，定义

$$
V_{\rm family}(B,\mathcal I,\Pi_0)
=
\inf_{\pi\in\Pi_0(\mathcal I)\cap\Pi_{\rm ad}^{0}(B,\mathcal I)}
\max_s
L_{s,0}(a_{s,0}^{\pi}),
$$

$$
\epsilon_{\rm family}=1-V_{\rm family}.
$$

### 2.5 稳健可实现余量

在同一函数族下加入完整误差集合、误差依赖的物理可行域和误差依赖的观测：

$$
V_{\rm robust}
=
\inf_{\pi\in\Pi_0(\mathcal I)\cap\Pi_{\rm ad}^{\rm rob}(B,\mathcal I)}
\sup_{\substack{s\in\mathcal S\\\Delta\in\mathcal U_s}}
L_{s,\Delta}(a_{s,\Delta}^{\pi}),
$$

$$
\epsilon_{\rm robust}=1-V_{\rm robust}.
$$

若项目只提供仅评价误差包络，则由该包络计算出的量应另记为 $V_{\rm envelope}$，不能直接命名为对象一致的 $V_{\rm robust}$。

### 2.6 单调关系

若满足：

1. 名义全节点动作集合包含给定基 $B$ 产生的名义物理可行动作；
2. 任意名义因果策略产生的逐场景动作序列都是动作基 oracle 可选择的序列；
3. $\Pi_0(\mathcal I)\subseteq\Pi(\mathcal I)$；
4. $0\in\mathcal U_s$，且 $\Delta=0$ 分支的状态、观测、约束和损失正是前四层使用的名义模型；
5. 所有层使用同一场景集合、归一化规则和标量化；

则可行决策集合逐层缩小，且稳健目标的上确界包含名义分支。因此

$$
\boxed{
V_{\rm full}
\le
V_{\rm basis}
\le
V_{\rm information}
\le
V_{\rm family}
\le
V_{\rm robust}.
}
$$

等价地，

$$
\boxed{
\epsilon_{\rm full}
\ge
\epsilon_{\rm basis}
\ge
\epsilon_{\rm information}
\ge
\epsilon_{\rm family}
\ge
\epsilon_{\rm robust}.
}
$$

这里必须分别使用 $\Pi_{\rm ad}^{0}$ 与 $\Pi_{\rm ad}^{\rm rob}$。若名义信息余量错误地直接在稳健策略集上优化，$\Delta_{\rm robust}$ 会被提前混入信息或函数族缺口，分解不再具有诊断意义。

对 gate margin 也可得到同样的集合单调性，但前提是每一层使用完全相同的注册统计门，仅改变动作、信息、函数族或不确定性集合。

## 3. 性能缺口分解

定义

$$
\Delta_{\rm basis}
=
V_{\rm basis}-V_{\rm full},
$$

$$
\Delta_{\rm information}
=
V_{\rm information}-V_{\rm basis},
$$

$$
\Delta_{\rm family}
=
V_{\rm family}-V_{\rm information},
$$

$$
\Delta_{\rm robust}
=
V_{\rm robust}-V_{\rm family}.
$$

则每一项均非负，且

$$
\boxed{
V_{\rm robust}-V_{\rm full}
=
\Delta_{\rm basis}
+
\Delta_{\rm information}
+
\Delta_{\rm family}
+
\Delta_{\rm robust}.
}
$$

由于 $\epsilon=1-V$，也有

$$
\epsilon_{\rm full}-\epsilon_{\rm robust}
=
\Delta_{\rm basis}
+
\Delta_{\rm information}
+
\Delta_{\rm family}
+
\Delta_{\rm robust}.
$$

冻结基线的零残差动作满足

$$
L_s(0)=1,
$$

因此可定义

$$
V_{\rm baseline}=1.
$$

基线距离全动作最优值的联合差距为

$$
\boxed{
H_{\rm baseline\to full}
=
V_{\rm baseline}-V_{\rm full}
=
1-V_{\rm full}
=
\epsilon_{\rm full}.
}
$$

这一项必须单独报告。若 $\epsilon_{\rm full}$ 本身很小，则主要原因是基线已接近受约束最优值；此时即使动作、信息和函数族完全不受限，也没有足够余量。

还应同时报告两个单指标上界：

$$
H_{c,\rm full}
=
1-
\inf_{\{u_s\}}
\max_s
\frac{J_{c,s}(u_s)}{J_{c,s}(0)},
$$

$$
H_{d,\rm full}
=
1-
\inf_{\{u_s\}}
\max_s
\frac{J_{d,s}(u_s)}{J_{d,s}(0)}.
$$

因为“两个指标分别可大幅改善”不代表存在同一个动作使两个指标同时改善。

---

## 4. 动作子空间命题与证明

令

$$
z_{c,s}^0=C_cy_s^0,
\qquad
H_{c,s}^{B}
=
C_cG_sK_B.
$$

定义场景 $s$ 的物理可达公共输出修正集合

$$
\mathcal K_{c,s}^{B}
=
\left\{
H_{c,s}^{B}a:
a\in\mathcal A_{s,0}(B)
\right\}.
$$

### 命题 1：动作子空间公共指标上界

假设：

1. $J_{c,s,0}(0)>0$；
2. $\mathcal A_{s,0}(B)$ 非空、紧，且包含零动作；
3. 使用名义响应矩阵 $G_s$。

则场景 $s$ 的最大公共指标改进满足

$$
\boxed{
\sup_{a\in\mathcal A_{s,0}(B)}
\eta_{c,s}(a)
=
1-
\frac{
\operatorname{dist}_1
\left(
-z_{c,s}^0,
\mathcal K_{c,s}^{B}
\right)
}{
\|z_{c,s}^0\|_1
}.
}
$$

因此最大联合改进满足

$$
\boxed{
\epsilon_{s,\rm joint}^\star(B)
\le
1-
\frac{
\operatorname{dist}_1
\left(
-z_{c,s}^0,
\mathcal K_{c,s}^{B}
\right)
}{
\|z_{c,s}^0\|_1
}.
}
$$

对所有场景的 worst-case 物理余量进一步满足

$$
\epsilon_{\rm phys}^\star(B)
\le
\min_s
\left[
1-
\frac{
\operatorname{dist}_1
\left(
-z_{c,s}^0,
\mathcal K_{c,s}^{B}
\right)
}{
\|z_{c,s}^0\|_1
}
\right].
$$

#### 证明

由定义，

$$
J_{c,s,0}(a)
=
\Delta t
\left\|
z_{c,s}^0+H_{c,s}^{B}a
\right\|_1.
$$

因此

$$
\inf_{a\in\mathcal A_{s,0}(B)}
J_{c,s,0}(a)
=
\Delta t\,
\operatorname{dist}_1
\left(
-z_{c,s}^0,
\mathcal K_{c,s}^{B}
\right).
$$

除以

$$
J_{c,s,0}(0)=\Delta t\|z_{c,s}^0\|_1
$$

即可得到等式。联合改进不可能超过其中任一单指标的最大改进，故得到联合上界。

### 4.1 可计算的对偶证书

若 $\mathcal A_{s,0}(B)$ 是凸紧集，令其支撑函数为

$$
h_{\mathcal A}(v)
=
\sup_{a\in\mathcal A_{s,0}(B)}v^\mathsf Ta.
$$

根据 $L_1$ 距离的对偶表示，

$$
\operatorname{dist}_1
\left(
-z_c^0,
\mathcal K_c^B
\right)
=
\max_{\|q\|_\infty\le1}
\left[
-q^\mathsf Tz_c^0
-
h_{\mathcal A}
\left(
(H_c^B)^\mathsf Tq
\right)
\right].
$$

任何满足 $\|q\|_\infty\le1$ 的向量都给出一个可验证下界，从而给出公共改进的上界证书。

若暂时去掉物理约束，只考虑可达子空间

$$
\mathcal R_{c,s}^B
=
\operatorname{Range}(H_{c,s}^B),
$$

则

$$
\operatorname{dist}_1(-z_c^0,\mathcal R_c^B)
=
\max_{\substack{
\|q\|_\infty\le1\\
(H_c^B)^\mathsf Tq=0
}}
-q^\mathsf Tz_c^0.
$$

因此只要找到

$$
(H_c^B)^\mathsf Tq=0,
\qquad
-q^\mathsf Tz_c^0>0,
$$

就获得一个明确的“不可达公共输出分量”证书。

### 4.2 SVD 投影证书

令 $P_{\mathcal R}$ 是到

$$
\mathcal R=\operatorname{Range}(H_c^B)
$$

的正交投影，则

$$
\operatorname{dist}_1(-z_c^0,\mathcal R)
\ge
\operatorname{dist}_2(-z_c^0,\mathcal R)
=
\|(I-P_{\mathcal R})z_c^0\|_2.
$$

故

$$
\boxed{
\epsilon_{c,s}^\star(B)
\le
1-
\frac{
\|(I-P_{\mathcal R})z_{c,s}^0\|_2
}{
\|z_{c,s}^0\|_1
}.
}
$$

该量可以直接由 $H_c^B$ 的 SVD 计算。

### 4.3 有限动作预算增益上界

若

$$
\mathcal A_{s,0}(B)
\subseteq
\{a:\|a\|_{\mathsf A}\le\rho_s\},
$$

则由反三角不等式，

$$
\|z_c^0+H_c^Ba\|_1
\ge
\|z_c^0\|_1-\|H_c^Ba\|_1.
$$

所以

$$
\boxed{
\epsilon_{c,s}^\star(B)
\le
\min\left\{
1,
\frac{
\rho_s
\|H_c^B\|_{\mathsf A\to1}
}{
\|z_{c,s}^0\|_1
}
\right\}.
}
$$

这给出了由有限时域增益和动作预算直接得到的上界。

### 4.4 联合目标的几何不可行证书

定义完整输出修正集合

$$
\mathcal K_s^B
=
\left\{
G_sK_Ba:
a\in\mathcal A_{s,0}(B)
\right\},
$$

以及达到 $\epsilon$ 联合改进所需的修正集合

$$
\mathcal T_s(\epsilon)
=
\left\{
v:
\begin{aligned}
&\Delta t\|C_c(y_s^0+v)\|_1
\le
(1-\epsilon)J_{c,s,0}(0),\\
&\Delta t\|C_d(y_s^0+v)\|_2^2
\le
(1-\epsilon)J_{d,s,0}(0)
\end{aligned}
\right\}.
$$

场景 $s$ 在动作基 $B$ 下可行，当且仅当

$$
\mathcal K_s^B\cap\mathcal T_s(\epsilon)\ne\varnothing.
$$

若两个集合闭、凸且不相交，则存在分离超平面 $q$，满足

$$
\sup_{v\in\mathcal K_s^B}q^\mathsf Tv
<
\inf_{w\in\mathcal T_s(\epsilon)}q^\mathsf Tw.
$$

这就是动作子空间和性能目标之间的几何失败证书，其数值形式等价于相应 LP、QP 或 SOCP 的对偶不可行证书。

### 4.5 $B_e$ 与 $B_+$ 的结构区别

给定

$$
B_e=
\begin{bmatrix}
1&0&0\\
-1&1&0\\
0&-1&1\\
0&0&-1
\end{bmatrix},
$$

有

$$
\operatorname{rank}(B_e)=3,
\qquad
\operatorname{Range}(B_e)
=
\{u\in\mathbb R^4:\mathbf1^\mathsf Tu=0\}.
$$

所以每个时刻

$$
\mathbf1^\mathsf Tu_k=0.
$$

在公共—差分输入坐标下，响应可写成

$$
\begin{bmatrix}
y_c\\y_d
\end{bmatrix}
=
\begin{bmatrix}
G_{cc}&G_{cd}\\
G_{dc}&G_{dd}
\end{bmatrix}
\begin{bmatrix}
u_c\\u_d
\end{bmatrix}.
$$

$B_e$ 强制 $u_c=0$，因此公共输出只能通过交叉块 $G_{cd}$ 被间接影响。不能把 $G_{cd}$ 设为零，但如果其有限时域增益小、秩不足或方向与 $-y_c^0$ 错位，公共改进上界就会很小。

加入

$$
B_+=[\,\mathbf1_4,\ B_e\,]
$$

后，

$$
\operatorname{rank}(B_+)=4,
$$

因而它在线性代数意义上张成整个节点动作空间：

$$
\operatorname{Range}(B_+)=\mathbb R^4.
$$

公共通道增加的是原动作空间中完全缺失的净功率方向，而不是简单增加一个函数输出维度。

---

## 5. 信息不可识别命题与证明

本节区分两类结论：条件方差给出对离线 oracle 动作的平均逼近下界；真正的因果不可能性证书必须作用在某个决策时刻的信息前缀和当前可延续动作上，或由带非预见约束的动态场景树直接给出。

### 命题 2：条件方差下界

令随机变量 $Z$ 表示场景或场景—误差样本，$A^\star=A^\star(Z)\in\mathbb R^d$ 是唯一的离线最优动作序列，且

$$
\mathbb E\|A^\star\|_2^2<\infty.
$$

令 $\mathcal I$ 为策略可用信息生成的 $\sigma$-代数，$Q\succeq0$ 为确定性矩阵。则

$$
\boxed{
\inf_{\pi:\,\mathcal I\text{-可测}}
\mathbb E\left[
\|\pi(\mathcal I)-A^\star\|_Q^2
\right]
=
\mathbb E\left[
\operatorname{tr}\!\left(
Q\operatorname{Cov}(A^\star\mid\mathcal I)
\right)
\right].
}
$$

一个最优预测器为 $\pi^\star(\mathcal I)=\mathbb E[A^\star\mid\mathcal I]$ 在 $Q$ 的非零子空间上的投影。

#### 证明

令 $\mu(\mathcal I)=\mathbb E[A^\star\mid\mathcal I]$。由

$$
A^\star-\pi=(A^\star-\mu)+(\mu-\pi)
$$

展开二次型并取条件期望。因为

$$
\mathbb E[A^\star-\mu\mid\mathcal I]=0,
$$

交叉项消失，从而

$$
\mathbb E[
\|A^\star-\pi\|_Q^2\mid\mathcal I
]
=
\operatorname{tr}\!\left(
Q\operatorname{Cov}(A^\star\mid\mathcal I)
\right)
+
\|\mu-\pi\|_Q^2.
$$

第二项由 $\pi=\mu$ 最小化。

### 5.1 从动作误差转换为性能损失

若统一标量损失 $\ell_Z(a)$ 在最优点附近满足

$$
\ell_Z(a)-\ell_Z(A^\star)
\ge
\frac12\|a-A^\star\|_Q^2,
$$

则

$$
\inf_{\pi}
\mathbb E[
\ell_Z(\pi)-\ell_Z(A^\star)
]
\ge
\frac12
\mathbb E\left[
\operatorname{tr}\!\left(
Q\operatorname{Cov}(A^\star\mid\mathcal I)
\right)
\right].
$$

若该下界按与 $V$ 相同的归一化单位写为 $R_{\mathcal I}$，则

$$
V_{\rm information}
\ge
V_{\rm basis}+R_{\mathcal I}.
$$

但这仍是对“恢复某个离线最优序列”的平均风险下界。只有在 $Q$ 与实际性能损失之间存在已验证的强凸或误差界关系，并且策略空间使用正确的适应性约束时，才能把它转成性能不可能性结论。

$Q$ 可来自平滑标量化损失的 Hessian，或 $\epsilon$-约束问题在唯一 KKT 点处的拉格朗日 Hessian。由于 $\max\{J_c/J_c^0,J_d/J_d^0\}$ 在两个指标并列活跃时可能不可微，不能未经处理直接声称存在唯一 Hessian。

### 5.2 适应过程版本

若

$$
A^\star=(A_0^\star,\ldots,A_{T-1}^\star),
\qquad
Q=\operatorname{diag}(Q_0,\ldots,Q_{T-1}),
$$

则对适应于信息滤过 $(\mathcal F_k)$ 的过程，

$$
\inf_{\pi_k\in L^2(\mathcal F_k)}
\mathbb E
\sum_{k=0}^{T-1}
\|\pi_k-A_k^\star\|_{Q_k}^2
=
\sum_{k=0}^{T-1}
\mathbb E
\operatorname{tr}\!\left(
Q_k\operatorname{Cov}(A_k^\star\mid\mathcal F_k)
\right).
$$

若 $Q$ 有跨时间块，正确对象是完整 oracle 序列到“所有适应过程组成的闭子空间”的 $Q$-加权投影距离，而不是逐时条件方差的简单求和。

### 5.3 随机权重与非唯一最优解

若 $Q=Q(Z)$ 不是 $\mathcal I$-可测，令

$$
M(\mathcal I)=\mathbb E[Q\mid\mathcal I],
\qquad
b(\mathcal I)=\mathbb E[QA^\star\mid\mathcal I].
$$

条件最优预测器满足

$$
\pi^\star=M^\dagger b
$$

加上 $M$ 零空间中的任意分量；最小风险为

$$
\mathbb E\left[
(A^\star)^\mathsf TQA^\star
-b^\mathsf TM^\dagger b
\right],
$$

前提是 $b\in\operatorname{Range}(M)$ 几乎处处成立。

若最优动作不唯一，令 $Z=(s,\Delta)$ 并记 $\mathcal A_Z(B):=\mathcal A_{s,\Delta}(B)$，定义

$$
\mathcal A_Z^\star
=
\operatorname*{argmin}_{a\in\mathcal A_{Z}(B)}\ell_Z(a)
$$

并研究

$$
R_{\rm set}(\mathcal I)
=
\inf_{\pi:\mathcal I\text{-可测}}
\mathbb E\left[
 d_Q^2\bigl(\pi(\mathcal I),\mathcal A_Z^\star\bigr)
\right].
$$

单个求解器返回的最优标签不足以表示该集合。

### 5.4 当前可延续动作集合

固定决策时刻 $k$、一个已经执行且满足此前非预见约束的共同策略前缀 $\bar\pi_{0:k-1}$，以及终端分支 $\omega=(s,\Delta)$。令 $\bar a_{0:k-1}^{\omega}$ 是该策略前缀在分支 $\omega$ 上实际产生的动作前缀；不同分支上其他控制主体的既往动作可以不同。对动作块 $q$，定义达到联合目标 $\epsilon$ 的**当前可延续动作集合**

$$
\boxed{
\mathcal C_{q,k}^{\epsilon}
(\omega\mid\bar a_{0:k-1}^{\omega})
=
\operatorname{proj}_{a_{q,k}}
\left\{
 a_{k:T-1}:
 \begin{array}{l}
 (\bar a_{0:k-1}^{\omega},a_{k:T-1})
 \in\mathcal A_{s,\Delta}(B),\\
 L_{s,\Delta}
 (\bar a_{0:k-1}^{\omega},a_{k:T-1})
 \le1-\epsilon
 \end{array}
\right\}.
}
$$

该集合只投影到**当前动作块**，而不是比较完整动作序列。定义中允许未来后缀针对分支单独优化，因此它是实际因果可延续集合的外近似。正因为它更宽松，若这种外近似已经互不相容，所得不可能性证书是可靠的。

如果需要精确而非宽松的有限场景判定，则必须把未来分支放入动态场景树，并对所有未来信息节点继续施加非预见约束；见命题 3(b)。

### 命题 3：信息前缀别名与动态场景树不可能性

设 $\bar\pi_{0:k-1}$ 是一个共同的因果策略前缀，并令 $\bar a_{0:k-1}^{\omega_i}$ 是它在分支 $\omega_i$ 上产生的分支特定动作前缀。假设两个分支在动作块 $q$ 处生成相同的动作前信息前缀

$$
H_{q,k}^{\omega_1}
=
H_{q,k}^{\omega_2}
=
h.
$$

#### (a) 当前可延续动作集合证书

若

$$
\boxed{
\mathcal C_{q,k}^{\epsilon}
(\omega_1\mid\bar a_{0:k-1}^{\omega_1})
\cap
\mathcal C_{q,k}^{\epsilon}
(\omega_2\mid\bar a_{0:k-1}^{\omega_2})
=
\varnothing,
}
$$

则不存在任何确定性、对 $\mathcal F_{q,k}$ 可测的因果分布式策略，能够延续该策略前缀并在两个分支上同时达到目标 $\epsilon$。

更一般地，对同一信息前缀的分支纤维

$$
\Omega_{q,k}(h)
=
\{\omega:H_{q,k}^{\omega}=h\},
$$

若

$$
\bigcap_{\omega\in\Omega_{q,k}(h)}
\mathcal C_{q,k}^{\epsilon}
(\omega\mid\bar a_{0:k-1}^{\omega})
=
\varnothing,
$$

则该前缀下不存在可行的当前动作块。

该结论是**相对于给定可达策略前缀的局部不可能性**。要排除整个策略类，必须在根信息节点得到空交，或证明每个候选策略都会到达某个空交前缀；否则它只排除该前缀的所有延续。

#### (b) 有限动态场景树等价性

考虑一个有限动态场景树，并令 $\nu_{q,k}(\omega)$ 表示分支 $\omega$ 在时刻 $k$ 对动作块 $q$ 所对应的**动作前信息节点标识**。该标识必须由注册的观测、消息、延迟和量化规则定义；若观测取决于既往动作，树及其节点必须按动力学递归生成，不能从基线日志一次性固定。

对每个终端分支 $\omega$、动作块 $q$ 和时刻 $k$ 建立变量 $a_{q,k}^{\omega}$，在每个分支上施加：

- 误差依赖的状态方程和观测方程；
- $a^{\omega}\in\mathcal A_{s,\Delta}(B)$；
- $L_{s,\Delta}(a^{\omega})\le1-\epsilon$；
- 非预见约束

$$
\nu_{q,k}(\omega)=\nu_{q,k}(\omega')
\quad\Longrightarrow\quad
 a_{q,k}^{\omega}=a_{q,k}^{\omega'}.
$$

在树的信息节点映射、通信规则和分支动力学均被完整给定的条件下，存在一个在该有限树上达到目标 $\epsilon$ 的确定性因果分布式策略，当且仅当上述场景树可行性问题有解。

#### 证明

对于 (a)，相同信息前缀下，确定性可测策略必须给动作块 $q$ 选择同一个当前值 $v=\pi_{q,k}(h)$。若策略在分支 $\omega_i$ 上最终达到目标，则该策略实际产生的后缀证明

$$
v\in
\mathcal C_{q,k}^{\epsilon}
(\omega_i\mid\bar a_{0:k-1}^{\omega_i}),
\qquad i=1,2.
$$

因此成功策略要求 $v$ 属于两个集合的交集；交集为空即矛盾。这个论证没有把完整动作序列集合不相交误当成因果不可能性。

对于 (b)，任意因果策略在每个树分支上诱导一组动作变量，并因信息前缀相同而自动满足非预见等式，所以得到一个可行场景树解。反过来，给定可行场景树解，在每个实际出现的信息节点上把策略定义为该节点共享的动作值；非预见等式保证定义良好，分支约束保证该策略在树上物理可行并达到性能目标。

### 5.5 距离与 Lipschitz 证书

令两个当前可延续动作集合为 $C_1,C_2$，且

$$
d=\operatorname{dist}(C_1,C_2)>0.
$$

若两个前缀完全相同，任何共同当前动作到至少一个集合的距离不小于 $d/2$。

若前缀不完全相同，但动作块策略满足

$$
\|\pi_{q,k}(h_1)-\pi_{q,k}(h_2)\|
\le
L_\pi\|h_1-h_2\|,
$$

而

$$
\operatorname{dist}(C_1,C_2)
>
L_\pi\|h_1-h_2\|,
$$

则不存在该 Lipschitz 常数下的策略同时达到两个分支目标。若允许当前动作距离各自集合至多为 $\tau_1,\tau_2$，充分不可能条件变为

$$
\operatorname{dist}(C_1,C_2)
>
L_\pi\|h_1-h_2\|
+\tau_1+\tau_2.
$$

以上集合必须基于动作施加前的信息前缀，并在给定既往动作前缀下计算。只比较完整 oracle 动作序列、最终最优标签或终端指标，不能单独形成因果别名证书。

## 6. 最大 $\epsilon$ 的优化算法或伪代码

### 6.1 名义物理 oracle 的 SOCP/QCQP

对给定 $B$，令

$$
H_s^B=G_sK_B.
$$

引入归一化最坏损失变量 $\rho$，使 $\epsilon=1-\rho$。对每个场景引入

$$
a_s,
\quad z_{c,s},
\quad z_{d,s},
\quad t_{c,s}\ge0,
$$

以及功率、SOC 和其他物理辅助变量。求解

$$
\begin{aligned}
\min_{\rho,\{a_s,\ldots\}}
\quad & \rho\\
\text{s.t.}\quad
&z_{c,s}=C_c(y_s^0+H_s^Ba_s),&&\forall s,\\
&z_{d,s}=C_d(y_s^0+H_s^Ba_s),&&\forall s,\\
&-t_{c,s}\le z_{c,s}\le t_{c,s},&&\forall s,\\
&\Delta t\,\mathbf1^\mathsf Tt_{c,s}
\le\rho J_{c,s,0}(0),&&\forall s,\\
&\Delta t\,\|z_{d,s}\|_2^2
\le\rho J_{d,s,0}(0),&&\forall s,\\
&a_s\in\mathcal A_{s,0}(B),&&\forall s,\\
&\rho\ge0.
\end{aligned}
$$

差分约束是凸二次约束，也可写成旋转二阶锥。最优值给出

$$
\epsilon_{\rm phys}^{\star}(B)=1-\rho^\star.
$$

分别取 $B=I_4,B_e,B_+$ 可计算全动作、零和边动作和公共扩充动作的名义物理余量。固定 $2\%$ 时令 $\rho=0.98$，可提取可行见证或对偶不可行证书。

### 6.2 SOC、效率和非凸物理约束

若采用线性 SOC 模型，SOC 约束是线性的。若采用充放电效率分段模型，可引入

$$
p=p^+-p^-,
\qquad p^+,p^-\ge0,
$$

及相应线性状态更新。但若没有证明最优解不会同时充放电，连续模型只是松弛。要声称精确，必须有精确性证明、注册吞吐惩罚，或使用二进制变量形成 MILP/MISOCP。

电压、电流和保护约束若来自非凸 AC 模型，也不能直接称为 SOCP；必须明确使用的是注册线性模型、锥松弛还是保守外近似。

### 6.3 鲁棒对应形式：先确定误差语义

#### 情形 A：仅评价误差

如果 $\Delta$ 只进入

$$
y_{s,\Delta}(a)=y_s^0+(G_s+\Delta^y)K_Ba
$$

而不改变状态、观测和物理约束，则同一开环动作满足

$$
a_s\in\mathcal A_{s,0}(B)
$$

即可。对有限误差集合，直接为每个误差样本复制性能约束是精确的。对多面体误差集合，只有在相关最坏约束关于误差为凸函数且误差以仿射方式进入时，检查全部极点才是精确的。

#### 情形 B：误差改变观测但不改变物理约束

此时仍可有

$$
\mathcal A_{s,\Delta}(B)=\mathcal A_{s,0}(B),
$$

但动作必须写成 $a_{s,\Delta}^{\pi}$，并通过动态场景树体现何时能够从观测中区分误差分支。对每个动作块 $q$ 加入

$$
\nu_{q,k}(\omega)=\nu_{q,k}(\omega')
\Longrightarrow
 a_{q,k}^{\omega}=a_{q,k}^{\omega'}.
$$

只给每个误差分支独立优化动作会把 $\exists\pi\,\forall\Delta$ 错写成 $\forall\Delta\,\exists a_\Delta$。

#### 情形 C：对象一致误差

若误差还改变 SOC、电压、电流、功率边界或保护约束，则对每个分支必须复制完整状态与物理约束，并使用

$$
a_{s,\Delta}^{\pi}\in\mathcal A_{s,\Delta}(B).
$$

稳健场景树变量包括

$$
\{x_{s,\Delta,k},o_{q,k}^{s,\Delta},a_{q,k}^{s,\Delta}\},
$$

同时施加误差依赖的动力学、观测方程、物理约束、性能约束和非预见约束。若只有输出响应误差矩阵而没有误差依赖的状态和观测模型，就只能计算“输出包络下的性能稳健性”，不能计算对象一致的稳健物理余量。

#### 一般凸误差集合

对范数球、椭球或一般凸集合，应使用支撑函数、S-lemma、鲁棒对偶化或约束生成。唯一正确的锥形式取决于：误差块结构、时间耦合、是否保持因果、是否进入物理状态和观测、以及不同约束对误差的凸性。在 $\mathcal U_s$ 未明确定义前，不能宣称存在唯一的“鲁棒 SOCP”。

### 6.4 对偶不可行证书

固定 $\epsilon$ 后，将连续凸问题写成

$$
Ax+b\in\mathcal K.
$$

在强不可行情形，若存在

$$
\lambda\in\mathcal K^\star,
\qquad
A^\mathsf T\lambda=0,
\qquad
b^\mathsf T\lambda<0,
$$

则 $\lambda$ 是锥 Farkas 证书。报告时至少保存：原始残差、对偶残差、锥成员误差、严格负裕量、求解器容差和独立重算结果。

若模型含整数变量，连续对偶射线不是完整的整数不可行证书；但若原问题的凸松弛已经不可行，该松弛证书仍能证明原整数问题不可行。

### 6.5 信息层的动态场景树算法

对有限场景—误差树，直接建立分支变量：

1. 对每个终端分支 $\omega=(s,\Delta)$ 和每个时刻建立状态、观测和动作变量；
2. 按注册时序展开状态、观测、消息和物理约束；
3. 对每个动作块 $q$，凡两个分支被注册信息树分到同一个动作前信息节点，就加入

   $$
   a_{q,k}^{\omega}=a_{q,k}^{\omega'};
   $$

4. 在每个终端分支加入联合性能目标；
5. 求解最大 $\epsilon$ 或固定 $\epsilon$ 的可行性问题。

该问题可行时，分支动作给出有限树上的因果策略见证；不可行时，若模型连续凸，可提取包含非预见约束乘子的对偶证书。

为定位最早的信息冲突，可固定一个共同策略前缀；它在各分支上产生相应的 $\bar a_{0:k-1}^{\omega}$。随后对每个分支重复求解并投影得到

$$
\mathcal C_{q,k}^{\epsilon}
(\omega\mid\bar a_{0:k-1}^{\omega}).
$$

若同一信息前缀对应的这些集合交集为空，即得到命题 3(a) 的局部证书。

如果观测随动作内生变化，仅有基线观测日志不足以构造精确场景树。必须已有可用于任意候选动作的观测生成模型、完整线性提升矩阵，或预先保存的分支树。当前不允许新仿真时，若这些对象没有保存，应把信息层结果标记为“现有数据不可判定”，而不是用静态完整动作标签代替。

### 6.6 不允许新仿真或训练时的求解流程

```text
输入：仅限已经保存的项目文件和矩阵

0. 误差语义审计
   - 判断 Delta 是仅评价误差、测量误差，还是对象一致误差
   - 判断零残差基线是否也受 Delta 影响
   - 未明确时，不计算对象一致 robust margin

1. 直接提取数据合同
   - 场景索引、T、dt、坐标变换、动作基、单位和堆叠顺序
   - 物理约束、信息时序、通信规则、统计 gate

2. 核验现有数值对象
   - y0_s、G_s、基线功率与初始状态
   - 误差集合/误差样本
   - 完整观测历史或观测生成模型
   - 缺项不通过汇总指标反推

3. 只做确定性重算，不做新仿真
   - 计算 H_s^B、SVD、投影残差和增益上界
   - 重解 I4、Be、B+ 的 LP/QP/SOCP
   - 提取最大 epsilon、见证、活跃约束和对偶证书

4. 信息前缀检查
   - 若已有动态观测模型/场景树：加入非预见约束并求解
   - 计算当前可延续动作集合及其交集
   - 若只有基线日志：最多报告该日志上的经验别名筛查，不能声称因果不可能

5. 稳健检查
   - 仅评价误差：复制性能约束或做鲁棒对偶化
   - 对象一致误差：必须同时复制状态、观测和物理约束
   - 缺少这些模型时停止，不外推

6. gate-faithful 重算
   - 使用既有逐场景结果和精确注册规则重算均值、LCB、子组和 no-harm

7. 输出
   - 已从现有文件直接提取的事实
   - 由现有矩阵确定性重算的结果
   - 因缺少已保存对象而当前不可计算的量
```

上述流程不训练任何策略，也不生成新的非线性轨迹。凸优化重解、矩阵分解、统计门重算和对偶证书验证均属于对既有数据的确定性后处理。

## 7. 对五种竞争假设的证据表

| 假设 | 当前证据支持什么 | 当前证据反对什么 | 仍缺少什么 | 不新增仿真/训练下的最小区分计算 |
|---|---|---|---|---|
| 1. 确定性基线已接近受约束最优 | 基线相对配对零控制，公共指标平均降低约 $95.51\%$，差分指标平均降低约 $99.33\%$；零和边 oracle 的公共额外名义改进也仅在约 $2\%$ 附近。 | $B_+$ 在相同 16 个开发场景上全部得到联合 $2\%$ 的离线物理解，说明小余量不能全部归因于基线饱和。 | $B=I_4$ 的全动作名义最优值、绝对指标和 Pareto 前沿。 | 若 $y_s^0,G_s$ 与物理数据已保存，重解 $B=I_4$ 的凸 oracle；否则当前不可计算。 |
| 2. 零和动作基与公共目标错位 | 6/16 场景在去掉物理和信息限制、允许边动作无界后仍无法达到联合 $2\%$；加入公共通道后 16/16 物理可行。 | 其余 10/16 场景在 $B_e$ 下仍有物理解，因此错位不是每个场景都完全不可控。 | 响应矩阵、目标修正方向、旧/新动作约束和原始对偶证书。 | 从已保存矩阵计算可达子空间投影、SVD 和联合锥分离证书，并比较 $B_e$ 与 $B_+$。 |
| 3. 局部或邻居信息不足 | 已测试局部、邻居状态和预测消息映射均未恢复 oracle 方向；公共平均改进未通过，差分指标恶化。 | 有限函数族失败不能推出所有可测策略失败；完整 oracle 动作序列不相交也不能直接推出因果不可能。 | 动作施加前的信息前缀、消息时序、误差依赖观测模型，以及可计算的当前可延续动作集合。 | 若已有动态场景树或观测生成模型，施加非预见约束并计算 $\mathcal C_{q,k}^{\epsilon}$；若只有基线日志，只能做经验筛查，不能给出一般不可能证书。 |
| 4. 已测试函数族表达能力不足 | 仿射、RBF、kNN、二次和多种一跳消息映射均未通过注册指标组。 | 动作基或信息瓶颈可能更早发生，不能单独归因于函数表达能力。 | 先验不受函数族限制的动态信息可行值 $V_{\rm information}$。 | 先求带非预见约束的有限树最优值，再在同一数据和 gate 上评估既有函数族；不进行新训练。 |
| 5. 名义改进被模型误差吞噬 | 零和边 oracle 有名义改进，但公共和差分的模型误差包络门未通过。 | 名义公共余量本身接近阈值，且部分场景动作基已不可行，误差不一定是唯一原因。 | 误差语义、完整 $\mathcal U_s$、是否存在 $\mathcal A_{s,\Delta}(B)$、误差是否改变观测和零残差基线。 | 若仅评价误差样本已保存，可重算 envelope margin；只有已有对象一致状态/观测/约束模型时，才能重算真正的 robust margin。 |

当前证据最强地支持“$B_e$ 存在结构性动作方向限制”。它尚不足以证明 $B_+$ 下的局部信息必然不足，也不足以证明模型误差对物理安全的影响，因为附件没有声明误差是否进入物理状态、观测和约束。

## 8. 最小结构扩充方案

### 8.1 严格优化目标

令候选动作结构和信息结构分别为 $B'$ 和 $\mathcal I'$。定义

$$
\min_{B',\mathcal I'}
\quad
C_B(B',B_e)
+\lambda C_I(\mathcal I',\mathcal I_{\rm local})
$$

满足

$$
\epsilon_{\rm robust}^\star(B',\mathcal I')\ge0.02.
$$

$C_B$ 应衡量新增动作维度、净功率权限和净能量权限；$C_I$ 应衡量通信 bit/s、轮数、延迟、量化精度和估计状态维数。连续实数消息若没有量化合同，不能被当作固定低通信成本。

### 命题 4：$B_+$ 在无坐标专属限制时等价于全节点动作

因为

$$
B_+=[\mathbf1_4,B_e],
\qquad
\operatorname{rank}(B_+)=4,
$$

映射

$$
(c,r)\mapsto\mathbf1_4c+B_er
$$

是 $\mathbb R^4$ 到 $\mathbb R^4$ 的双射。对任意固定分支 $(s,\Delta)$，若所有物理约束只依赖节点动作和由该节点动作产生的物理状态，而不依赖坐标表示 $(c,r)$，则

$$
\mathcal A_{s,\Delta}(B_+)
\quad\text{与}\quad
\mathcal A_{s,\Delta}(I_4)
$$

在节点动作空间中表示同一个集合。因此该分支上的动作基余量相同。若 $B_+$ 与 $I_4$ 的结果不同，差异只能来自公共通道或边通道的坐标专属限制、不同的信息归属，或对公共净功率新增的能量与安全合同。

#### 证明

对任意节点动作 $u$，唯一地有

$$
c=\frac14\mathbf1^\mathsf Tu,
$$

且

$$
u-c\mathbf1\in\mathbf1^\perp=\operatorname{Range}(B_e),
$$

故存在唯一 $r$ 满足 $B_er=u-c\mathbf1$。若约束仅由节点动作及其物理后果决定，改变坐标表示不会改变可行节点动作集合。

### 8.2 加入公共通道后的物理合同

对设备 $i$，

$$
p_{i,k}
=
p_{i,k}^0+c_k+(B_er_k)_i.
$$

节点功率限制给出

$$
-\bar P_i-p_{i,k}^0-(B_er_k)_i
\le c_k\le
\bar P_i-p_{i,k}^0-(B_er_k)_i.
$$

爬坡约束同样限制 $\Delta c_k$。净残差功率为

$$
\mathbf1^\mathsf Tu_k=4c_k,
$$

所以公共动作会直接改变车队净功率、累计净能量、SOC、效率损失和备用容量合同。若误差影响这些物理量，所有边界都必须在 $\mathcal A_{s,\Delta}(B_+)$ 中逐分支展开。

### 8.3 必要条件、有限树充分条件与信息前缀条件

对每个候选 $(B',\mathcal I')$：

**名义物理必要条件**

$$
\mathcal K_{s,0}^{B'}
\cap
\mathcal T_{s,0}(0.02)
\ne\varnothing,
\qquad\forall s.
$$

**稳健物理必要条件**

对每个误差分支必须存在符合相应物理集合的可延续动作；若策略尚不能区分分支，还必须有共同当前动作。

**信息前缀必要条件**

对任意动作块 $q$、时刻 $k$ 和共同信息前缀 $h$，在任一可达策略前缀下必须满足

$$
\bigcap_{\omega\in\Omega_{q,k}(h)}
\mathcal C_{q,k}^{0.02}
(\omega\mid\bar a_{0:k-1}^{\omega})
\ne\varnothing.
$$

这只是必要条件。它不能由完整动作序列集合交集替代。

**有限场景树充分条件**

若完整动态场景树在所有误差分支上满足状态、观测、$\mathcal A_{s,\Delta}(B')$、联合性能和全部非预见约束，则在该有限树上存在一个确定性因果分布式策略。

### 8.4 五种候选扩充的当前判断

| 方案 | 当前判断 |
|---|---|
| 1. 只增加公共功率通道 | 是现有证据支持的最小动作层扩充。16/16 名义离线物理可行不等价于因果或稳健可行；应先检查 $B_+$ 与原信息结构的动态场景树。 |
| 2. 只增加全局净功率缺口或 COI 频率共识估计 | 不能修复 $B_e$ 的节点动作子空间，因此不能解决那 6 个动作层已不可行的场景。 |
| 3. 公共通道加一个标量共识信号 | 只有在方案 1 的当前可延续动作集合或场景树给出信息冲突后，才有理由加入；信号应针对具体冲突信息纤维设计。 |
| 4. 公共通道由确定性控制，残差只作用于零和边通道 | 会改变冻结基线和物理轨迹。当前禁止新仿真时，除非新基线及其响应矩阵已经保存，否则不能数值评估。 |
| 5. 公共和边通道均由分层或双时间尺度策略控制 | 成本和验证复杂度最高；在更小扩充未被证书排除前，不是最小方案。 |

当前能够支持的结构性结论是：若目标确实需要当前 $B_e$ 缺失的净功率方向，则候选 $B'$ 必须满足

$$
\operatorname{Range}(B')\not\subseteq\mathbf1^\perp.
$$

是否还必须增加共识信息，必须由信息前缀可延续集合或非预见场景树判定，不能由既有函数族失败直接推出。

## 9. 数值求解最小数据包：现有文件提取、必须重算与阻断项

### 9.1 当前材料边界

本次会话实际提供的只有问题说明文件和上一版答案。问题说明列出了若干项目路径，但这些代码、JSON 和报告文件本身没有随附件提供。因此下表中的“可提取”表示**从所列现有项目文件中原则上应当优先提取，并需在文件到位后核验字段**；不表示本次会话已经读取到这些字段。

当前约束是：

- 不进行新非线性仿真；
- 不生成新的扰动或响应矩阵；
- 不训练或重新拟合任何策略；
- 允许解析既有文件、对已有矩阵做确定性变换、重解 LP/QP/SOCP、验证对偶证书和重算注册统计门。

### 9.2 最小数据包目录

建议把最小包固定为以下对象；文件格式可以变化，但字段不能缺失。

```text
minimal_numeric_package/
├── manifest.yaml
├── scenario_index.csv
├── model_contract.yaml
├── response_nominal.npz
├── physical_baseline.npz
├── constraints.yaml
├── uncertainty.yaml / uncertainty.npz
├── information_contract.yaml
├── observation_model.npz 或 scenario_tree.json
├── registered_results.json
├── gates.yaml
└── provenance.json
```

### 9.3 逐项数据状态

| 数据对象 | 最小内容 | 可能的现有来源 | 不新增仿真/训练下的状态 |
|---|---|---|---|
| 场景索引与分析分组 | `scenario_id`、运行点、扰动位置与符号、样本权重、开发/保留标记 | 各 `analysis.json`、报告文件 | **优先直接提取。** 分组仅用于离线分析，不能进入运行时信息。若 JSON 只保存汇总均值而没有逐场景键，则不能从均值反推。 |
| 时域与坐标合同 | $n=4$、$T=25$、$\Delta t$、输入/输出堆叠顺序、$C_c,C_d$、惯量加权变换 | `model_contract.md`、求解器代码 | **直接提取并交叉核验。** 代码与文档不一致时必须记录版本，不能自行选择。 |
| 动作基 | $B_e,B_+$、公共/边坐标顺序、坐标专属幅值与变化率限制 | `model_contract.md`、`convex_residual_solver.py`、`common_channel_qp.py` | **直接提取。** $B=I_4$ 仅用于重算全动作 oracle，不需新仿真。 |
| 名义基准输出 | 每场景 $y_s^0\in\mathbb R^{4T}$，以及单位和版本 | 可能存在于 R350/R356/R358/R363 的数值缓存或附属 NPZ；代码本身不足以给出数值 | **必须找到已保存数组。** 若现有文件只有指标汇总，不能恢复 $y_s^0$；重新生成将属于新仿真，当前禁止。 |
| 名义响应矩阵 | 每场景 $G_s\in\mathbb R^{4T\times4T}$，因果块结构和数值精度 | 可能由 `convex_residual_solver.py` 使用的缓存或结果目录保存 | **必须找到已保存矩阵。** 若未序列化，不能从 oracle 动作或最终指标唯一反演；重新识别/仿真当前不允许。 |
| 基线物理轨迹与初值 | $p_s^0$、上一时刻命令、$SOC_{s,0}$、必要的电压/电流/能量初值 | R358/R363 数值结果、原始轨迹缓存 | **字段已保存则直接提取。** 若只保存最大约束裕量而没有轨迹，不能精确重建动态物理集合。 |
| 物理约束合同 | 功率、爬坡、SOC、能量、效率、电压、电流、保护、执行和公共通道净能量合同 | `model_contract.md`、两个凸求解器代码 | **直接提取结构与常数。** 若常数按场景变化，还需要逐场景数组，不能只读默认配置。 |
| 误差语义 | $\Delta$ 是仅评价、测量还是对象一致误差；是否改变零残差基线 | 应由 `model_contract.md` 或生成误差包络的代码明确 | **必须先核验。** 当前说明文件没有给出答案；在未明确前不得计算对象一致 robust margin。 |
| 输出响应误差集合 | 有限 $\Delta^y$ 样本、极点、多面体/范数球参数、时间耦合和因果结构 | R350 的误差包络数据或其附属缓存 | **完整样本/集合已保存则直接提取。** 若只有“门通过/失败”或每指标最大偏差，无法重建 $\mathcal U_s$。 |
| 误差依赖的物理模型 | $f_{s,k,\Delta}$、$g_{s,k,\Delta}$，或状态/约束的提升矩阵 | 未由附件确认存在 | **若已保存则提取；否则当前不可补齐。** 只有 $\Delta^y$ 时只能做输出包络稳健性，不能构造 $\mathcal A_{s,\Delta}(B)$。 |
| 信息与通信合同 | 每个动作块的观测字段、动作前/后时序、延迟、消息方向、量化、缺失规则；公共动作控制主体 | `model_first_distributed_edge.py`、`model_contract.md` | **结构可直接提取。** 代码定义特征不等于已经保存各场景的数值历史。 |
| 已执行轨迹上的完整信息前缀 | 每场景、每动作块、每时刻的 $o_{q,0:k},m_{q,0:k}$ 和时间戳 | R359–R362 的样本/特征缓存，若有 | **已保存则直接提取或从已保存原始轨迹确定性重建。** 若只有回归指标或最终特征摘要，不能恢复前缀。 |
| 反事实观测生成模型或动态场景树 | 任意候选动作下的状态—观测映射，或已经枚举的分支、节点和信息等价类 | 可能不存在于当前分析结果 | **动态信息判定的关键缺口。** 基线日志不能回答动作改变后会看到什么；若没有已保存模型/树，当前不得宣称一般因果信息不可能。 |
| 逐场景 oracle 动作与物理见证 | $a_s^\star$、$p_s$、SOC、活跃约束、最优值 | R350/R358/R363 `analysis.json` 或附属数组 | **若序列化则直接提取。** 若只保存最终指标，需用已有 $y_s^0,G_s$ 和约束确定性重解；这不属于训练或仿真。 |
| 不可行与对偶证书 | 原始对偶射线、求解器状态、容差、残差 | R356/R358 的原始结果，若保存 | **已有原始证书则直接验证。** 若只有 `infeasible` 标志，需用同一矩阵重解才能获得可核验证书。 |
| 注册统计门 | 配对规则、权重、LCB 方法与水平、子组方向性、no-harm、nominal/error 组合 | `model_contract.md`、分析代码和各 `analysis.json` | **直接提取规则。** 若只保存最终 pass/fail，不能重建 gate-faithful margin。 |
| 求解器与版本信息 | 代码提交、依赖版本、容差、缩放、随机种子、输入哈希 | `provenance`、结果元数据、代码仓库 | **直接提取或补写清单。** 不改变数值，只保证可复现。 |

### 9.4 按求解目标划分的最小子包

| 要回答的数值问题 | 最小已有数据 | 能输出什么 | 缺失时的处理 |
|---|---|---|---|
| 名义全动作与动作基余量 | `scenario_index`、$y_s^0$、$G_s$、$C_c,C_d,\Delta t$、基线物理初值、名义约束、$B$ | $\epsilon_{\rm full}$、$\epsilon_{\rm phys}^\star(B_e)$、$\epsilon_{\rm phys}^\star(B_+)$、见证和对偶证书 | 任缺 $y_s^0,G_s$ 或动态物理初值即阻断；不重新仿真生成 |
| 动作子空间几何证书 | $y_s^0$、$G_s$、$B$，若考虑预算再加名义可行域 | SVD、投影残差、增益上界、分离证书 | 没有 $G_s$ 即阻断 |
| 仅评价误差下的性能包络 | 名义子包加完整 $\Delta^y$ 样本/集合与归一化合同 | $V_{\rm envelope}$、最坏输出误差见证 | 只有指标级上下界时只能复算原 gate，不能求新 robust oracle |
| 名义因果信息余量 | 名义子包加信息合同，以及任意候选动作下的观测生成模型或已保存动态场景树 | 带非预见约束的 $V_{\rm information}$、当前可延续动作集合 | 只有基线日志时不能得到一般闭环因果结论 |
| 对象一致稳健余量 | 名义与信息子包加误差依赖的状态、观测、约束和初值模型 | $V_{\rm robust}$、稳健物理见证或证书 | 只有 $\Delta^y$ 时不得计算该量 |
| Gate-faithful 余量 | 逐场景配对结果、分组、权重和完整 gate 规则 | 配对均值、LCB、子组方向性、no-harm 和 gate margin | 只有总 pass/fail 时不能重建 |

因此，当前最小可执行层级取决于已保存对象。不能为了完成更高层级而把缺失的动态观测模型、误差依赖状态模型或响应矩阵用新仿真补齐。

### 9.5 必须由现有数据重新计算的量

下列对象通常不会直接作为项目字段存在，但只要上述矩阵已经保存，就可以在不进行新仿真或训练的条件下确定性重算：

1. $H_s^B=G_s(I_T\otimes B)$；
2. $B_e$ 与 $B_+$ 的可达子空间、奇异值、投影残差和有限时域增益；
3. $B=I_4,B_e,B_+$ 的最大名义 $\epsilon$；
4. 固定 $\epsilon=0.02$ 的可行见证、活跃约束和锥对偶证书；
5. 非唯一最优动作集合或 $\epsilon$-可行动作集合的支撑函数/投影；
6. 给定动作前缀下的当前可延续动作集合 $\mathcal C_{q,k}^{\epsilon}$；
7. 若已有完整动态观测模型或场景树，带非预见约束的信息可恢复余量；
8. 条件协方差、加权投影风险和 Lipschitz 分离量；
9. 给定完整误差集合后的输出包络余量，或给定对象一致模型后的真正稳健余量；
10. 配对均值、单侧置信界、子组方向性和最坏场景 no-harm 的 gate-faithful margin。

这些“重新计算”都是基于既有数据的矩阵运算或优化重解，不包括生成新轨迹。

### 9.6 在当前限制下无法由汇总文件补齐的对象

若以下对象没有被既有项目文件保存，本轮应明确停止相应数值结论：

- $y_s^0$ 或 $G_s$；
- 完整误差矩阵/集合，而非指标级包络摘要；
- 误差依赖的状态、观测和物理约束模型；
- 动作改变后可用于构造信息前缀的反事实观测模型或场景树；
- 逐场景动态物理初值和轨迹；
- 精确注册 gate 规则。

不能从平均改进、单个 oracle 标签、通过率或求解器状态唯一恢复这些对象。若恢复它们需要重新运行非线性系统、重新识别响应或生成新扰动，则在“当前不允许新仿真或训练”的条件下，应把对应量标记为**不可计算**。

### 9.7 建议优先提供的现有项目文件

```text
paper/decoupling_marl_model_first/working/model_contract.md
src/andes_rl_kundur/control/convex_residual_solver.py
src/andes_rl_kundur/control/common_channel_qp.py
src/andes_rl_kundur/control/model_first_distributed_edge.py
results/r350_smooth_convex_residual/analysis.json
results/r356_joint_endpoint_feasibility/analysis.json
results/r358_physical_joint_endpoint_qp/analysis.json
results/r359_neighbour_causal_residual/analysis.json
results/r360_flexible_neighbour_residual/analysis.json
results/r361_neighbour_message_residual/analysis.json
results/r362_shared_prediction_residual/analysis.json
results/r363_common_channel_qp/analysis.json
```

还应同时提供这些 JSON 引用的 NPZ、CSV、轨迹缓存、求解器原始结果和配置文件；仅提供汇总 JSON 可能不足以组成最小数值包。

## 10. 当前能够成立的有界结论和仍不能成立的结论

### 10.1 当前能够成立

1. 问题应被建模为带动作子空间、误差依赖物理可行域、内生观测和非预见约束的有限时域稳健多目标决策问题。

2. 对附件所报告的 16 个开发场景和名义有限响应模型，现有证据支持：原始 $B_e$ 路线至少有 6 个场景在更宽松的无界零和动作条件下仍不能达到联合 $2\%$，因此该有限开发集上的 worst-case 动作基余量低于 $2\%$。

3. 同一有限开发集上，$B_+$ 把名义逐场景离线物理可行率从 10/16 提高到 16/16。该结论只说明信息不受限的名义物理机制存在，不说明因果信息或稳健性已经成立。

4. 对原始 $B_e$ 路线，现有顺序证据首先支持

   ```text
   ACTION-BASIS-LIMITED
   ```

   而不是先归因于某个函数族或训练方法。

5. $B_+$ 在没有坐标专属限制时张成全节点动作空间；但新增公共通道会改变净功率、能量、SOC 和安全合同。

6. 信息不可能性可以由两类严格对象判定：根节点或不可避免可达前缀上的当前可延续动作集合空交，或带非预见约束的完整动态场景树不可行。任意单个可达前缀的空交只排除该前缀的延续；完整动作序列集合不相交本身也不是充分的因果证书。

7. 若响应误差改变物理状态或约束，稳健可行域必须写成 $\mathcal A_{s,\Delta}(B)$；若只提供输出误差包络，只能报告输出包络下的性能稳健性。

### 10.2 当前仍不能成立

1. 不能声称确定性基线已经接近全动作受约束最优值，因为尚未给出 $B=I_4$ 的完整数值求解。

2. 不能声称所有局部或邻居因果策略都不可能有效。既有结果只排除了有限映射；没有动态信息前缀证书或非预见场景树证书。

3. 不能从两个场景的完整 oracle 动作序列或完整可行序列集合不相交，直接推出因果策略不可能。未来观测可能允许策略在共同前缀之后分叉。

4. 不能声称 $B_+$ 加原局部信息一定不足，也不能声称必须增加共识信号。

5. 不能声称

   $$
   \epsilon_{\rm robust}^{\star}
   (B_+,\mathcal I_{\rm local/consensus})
   \ge0.02
   $$

   或小于 $0.02$，因为尚未确认误差是否进入状态、观测和约束，也未获得相应 $\mathcal A_{s,\Delta}(B_+)$ 与动态信息模型。

6. 不能把 nominal/error 指标包络门失败推广为对象一致的鲁棒物理不可能；两者使用的数据和量词不同。

7. 不能把函数族失败等同于 `INFORMATION-LIMITED`。只有不受函数族限制的动态信息可行问题失败，或获得前缀可延续集合证书，才能支持该标签。

8. 不能给出 `FUNCTION-FAMILY-LIMITED`，因为尚未先证明给定信息原则上充分。

9. 不能给出 `TRAINABLE-RESIDUAL-EXISTS`。目前缺少统一因果策略、函数实现和对象一致稳健余量的严格正裕量。

10. 在当前不允许新仿真或训练的条件下，如果既有文件没有保存 $y_s^0,G_s$、误差依赖状态/观测模型或动态场景树，则相应数值量必须标记为不可计算，不能由汇总指标推测。

现阶段最有价值但仍未解的量仍是

$$
\boxed{
\epsilon^\star
\left(
B_+,\mathcal I_{\rm local/consensus}
\right),
}
$$

但它现在应被理解为：在明确误差语义、使用 $\mathcal A_{s,\Delta}(B_+)$、并对每个动作块施加动态非预见约束之后，公共通道和差分通道是否存在统一因果策略的严格正余量。
