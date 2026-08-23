# R474 同时间置换安慰剂：数学、统计与实现 Deep 审查

## 0. 最终判定

**结论：R474 当前版本不得运行。**

| 对象 | 状态 | 判定 |
|---|---|---|
| “当前 P 满足 guardrail §A.1/A.2” | **DISPROVED** | 一个结构性来源-ID反例即可否定逐槽池保持；当前 P 也不是 N 邻居元组的置换 |
| 当前路由门 | **不充分** | 它验证的是自行放宽后的“两槽合并通道池”，而非 guardrail 的逐槽条件；部分检查由预期公式计算或硬编码 |
| 当前确认性主效应 | **未识别** | 新/旧训练批次与 P/N 条件系统性绑定，存在精确的 `2/3` 批次偏移污染项 |
| 当前材料性判定 | **未按声明实现** | 零效应 Holm 与 10% bootstrap 门是两套不同推断；不是材料性假设的 Holm 检验或随机化反演 |
| R474 科学效应 | **未估计** | 没有 R474 训练结果；本报告不对效应方向作结论 |

按计划中“任一路由性质失败即 `FACTORIAL-INVALID`、不启动训练”的规则，当前设计已经在训练前触发阻断。

---

## 1. 路由检查逐性质判定

Guardrail 的核心原文要求：同一时刻、同一真实来源池；对每个 `slot/feature/scenario/time`，N 与 P 的值多重集完全相同；每个来源元组都被移动；P 的来源不是真邻居。当前实现把逐槽条件改成“将两个邻居槽合并后按特征通道比较”，这是实质性放宽，而不是等价 operationalization。

### 1.1 当前实现的判定表

| 性质 | 当前实现 | 判定 | 说明 |
|---|---|---:|---|
| 逐槽/逐特征池保持 | P 的两个 d_omega 槽都取对角设备；两个 omega_dot 槽同理 | **FAIL** | N 的 slot 3/4 来源多重集分别不同于 P；只有把 slot 3+4 合并后才相等 |
| 每个接收者的来源元组发生变化 | N 元组与 `(diagonal, diagonal)` 不同 | **PASS（弱含义）** | 四个接收者的来源-ID元组均改变；但 P 元组集合不是 N 元组集合的置换，因此不满足上位“source-pool permutation”要求 |
| P 来源不是真邻居 | 单一 pivot 为 `i+2` | **PASS** | 对 4 环，`i+2` 不是 `i±1` |
| P/N 使用同一同时刻状态 | 两者由同一 `joint` 构造 | **PASS（实现意图）** | 语义上满足；但 `routing_check` 中该标志直接写死为 `True`，不是实际证据 |
| 实际槽值符合当前 P 公式 | real-ANDES probe 比较槽值 | **PASS 对“错误规格”** | 只能说明代码实现了“复制对角值”的规格，不能证明该规格满足 guardrail |
| N 邻居四元组多重集保持 | P 应为真实 N 四元组的置换 | **FAIL** | 当前 P 生成四个重复来源元组 `(j,j)`，真实 N 不含这些一般元组 |
| 条件支持/冗余结构保持 | N 一般有两个不同邻居值 | **FAIL** | P 恒有 `slot3=slot4`、`slot5=slot6`；网络可近乎完美识别条件，输入秩和协方差结构改变 |

**总体路由判定：FAIL。** 四项中任意一项失败即足以阻断；这里还存在额外的元组与支持结构失败。

### 1.2 一个不依赖任何数值数据的精确反例

实际邻居表为：

```text
COMM_ADJ = {0:(1,3), 1:(0,2), 2:(1,3), 3:(2,0)}
```

仅看 d_omega 的来源设备 ID：

```text
N slot 3: [1, 0, 1, 2]   -> sorted [0, 1, 1, 2]
N slot 4: [3, 2, 3, 0]   -> sorted [0, 2, 3, 3]
P slot 3: [2, 3, 0, 1]   -> sorted [0, 1, 2, 3]
P slot 4: [2, 3, 0, 1]   -> sorted [0, 1, 2, 3]
```

所以两个逐槽等式都失败。omega_dot 两槽有完全相同的来源-ID反例。

真实 N 的有序来源元组多重集为：

```text
[(1,3), (0,2), (1,3), (2,0)]
```

当前 P 为：

```text
[(2,2), (3,3), (0,0), (1,1)]
```

两者不是同一个多重集。当前代码能够得到“两槽合并后每个设备出现两次”，只说明：

```text
multiset(N slot3 ∪ N slot4) = multiset(P slot3 ∪ P slot4)
```

它不能推出 guardrail 所要求的：

```text
multiset(N slot3) = multiset(P slot3)
multiset(N slot4) = multiset(P slot4)
```

这是严格的逻辑缺口，而不是统计波动或实现细节。

### 1.3 重复对角值为何是实质混杂

当前 P 对所有样本强制：

```text
slot3 - slot4 = 0
slot5 - slot6 = 0
```

真实 N 除特殊退化状态外不满足这两个恒等式。因此 N/P 的差异同时包含：

1. 来源是否为真实邻居；
2. 两个邻居槽是否坍缩为一个值；
3. 输入特征秩、协方差和有效信息容量是否降低；
4. 网络能否通过两个精确等式识别条件。

即使最终文字只声称“total algorithm effect”，这仍违反本轮专门设立的干预纯度门，不能通过改写措辞挽救。

### 1.4 own slots `0:3` 不应改动

保留接收者自己的特征是正确做法。若同时置换 own slots，会引入设备身份、局部状态与控制目标的额外变化，使问题更严重。当前缺陷来自错误构造邻居块，不来自 own slots 未改。

---

## 2. 对审查问题 1：干预纯度

### 结论

**当前 `pi(i)=i+2` 并将同一对角特征复制到两个槽的设计不满足 guardrail。** `pi` 作为“每个接收者选一个非邻居设备”的映射确实是唯一的固定点自由对角映射，但它不是“真实 N 邻居四元组的置换”。这两个命题不可混同。

### 必须采用的同成本映射

设 `N[i,3:7]` 是环境已经构造好的真实邻居四元组。选定并预注册一个无固定点的行置换，例如：

```text
rho(i) = (i+1) mod 4
P[i, 0:3] = joint[i, 0:3]
P[i, 3:7] = N[rho(i), 3:7]
```

则：

- **逐槽池保持**：`rho` 是行置换，所以每一列 `c=3..6` 的多重集逐列不变；
- **完整元组池保持**：整个 `3:7` 四元组多重集不变；
- **每个接收者元组改变**：对实际 `COMM_ADJ`，`N[rho(i)]` 与 `N[i]` 的来源-ID元组不同；
- **没有真邻居来源**：`rho(i)=i+1` 的真实邻居是 `i` 与 `i+2`，均不属于接收者 `i` 的真邻居集合 `{i-1,i+1}`；
- **同一时刻**：只读取当前 `joint`；
- **不复制单一来源**：每个 P 邻居元组仍由两个来源构成。

反方向 `rho(i)=i-1` 也成立。精确枚举表明，在当前 4 环、逐槽池保持和非真邻居约束下，这两个方向是两种不同的无槽内重复布线。应固定一个方向作为主分析，另一个方向可作为预注册敏感性检查；不要在看到结果后选择。

### 仍然存在的边界

行移位后，每个 P 邻居元组的来源设备集合是 `{i, i+2}`：一个是接收者自身，一个是对角设备。因此 P 中仍会出现“某个邻居槽与 own 特征完全相等”的结构。对 4 环而言，在同时要求逐槽池保持和不使用真邻居时，这种 self/diagonal 结构基本不可避免。

所以即使修复路由，结论仍只能是：

> 在固定训练预算、固定 4 环拓扑、固定场景库、固定 learner、固定权重和固定 P 行置换下，真实邻居四元组相对于该同时刻错配四元组的总算法效应。

它仍不是纯语义信息值。若必须消除 self-redundancy，需要更大的设备图，或重新设计带有可证明双射的同步多副本实验；不能靠当前 4 个设备内的单设备对角复制解决。

---

## 3. 对审查问题 2：统计协议

### 3.1 每 seed 配对：原则上正确，但推断域有限

把 seed 作为顶层单位、先在 seed 内聚合固定评估库，再形成 P/N 对比，是当前设计中最合理的配对层级。相同初始化、相同场景顺序和共同随机数可降低差值方差。

但六个 seed 支持的是对冻结训练随机机制的有限推断；四个固定 evaluation profile 并不是从某个场景总体独立抽样，因此不能据此声称对任意场景或拓扑的概率泛化。

### 3.2 “exact sign-flip randomization inversion”名称不准确

代码实际执行：

1. 对六个 seed 差值枚举全部 `2^6=64` 个符号；
2. 只计算零中心点假设的单侧 p 值；
3. 没有反演该检验来构造置信界。

因此它不是代码文字所称的“randomization inversion”。此外，当前没有记录 seed 内 N/P 运行槽的随机标签分配；有限样本“exact”需要真实的随机化不变性，或至少需要明确采用差值分布关于零对称的模型假设。更准确的名称是：

> 在预先声明的符号对称假设下，对六个配对差值进行全枚举符号翻转检验。

若要获得设计型 exact randomization，应在每个 seed 内预先随机分配两个运行槽的 N/P 标签并封存分配记录。

### 3.3 n=6 的离散性非常强

单侧 p 值只能取 `k/64`。两个 primary hypotheses 做 Holm 时，第一个阈值为 `0.025`，因此首个检验只能用最小 p 值 `1/64=0.015625` 通过；`2/64=0.03125` 已失败。对材料性边界做符号翻转时，这通常意味着所有六个中心化差值都必须保持有利符号，门槛非常粗。

这不是禁止 n=6，但必须如实称为低分辨率、低功效的确认性设计，并展示全部 seed 差值与 leave-one-out 敏感性。

### 3.4 当前材料性门不是声明中的检验

代码先对：

```text
H0_zero: mean effect <= 0
```

计算符号翻转 p 值并做 Holm；随后又要求一个独立的 percentile bootstrap 95% CI 下限大于：

```text
delta = log(1.10)
```

这不是对两个材料性假设：

```text
H0_actor:  effect_actor  <= delta
H0_critic: effect_critic <= delta
```

进行 Holm。两套方法的假设、有限样本行为和误差控制不同。对于恰好两个效应，若每个双侧 95% CI 的覆盖完全正确，其下限可被解释为约 2.5% 单侧门，联合使用可能具有保守的 Bonferroni含义；但 n=6 percentile bootstrap 的覆盖不能当作已知保证，而且它仍不是所声明的随机化反演/Holm 材料性程序。

**强制修改：** 直接在 `delta=log(1.10)` 处计算两个单侧材料性 p 值，再对这两个 p 值执行 Holm。bootstrap CI 仅作描述，或由同一检验反演得到与材料性门一致的下界。

### 3.5 旧 R473 数据的诊断性重算证明该差异会改变结论

仅用包内已封存的 R473 六个 critic 差值作方法诊断：

| 检验 | p 值 | Holm 首阈值 0.025 |
|---|---:|---:|
| 零效应 `H0: effect <= 0` | `1/64 = 0.015625` | 通过 |
| 材料性 `H0: effect <= log(1.10)` | `2/64 = 0.03125` | **不通过** |

对应的 97.5% 单侧符号翻转下界之上确界约为 `0.0848624`，低于 `log(1.10)=0.0953102`。这不是 R474 结果，也不重写 R473 的预注册结论；它只证明当前“零效应 Holm + bootstrap 材料性”的混合门与直接材料性检验并不等价，而且差异具有实际判定后果。

### 3.6 bootstrap：可重复，但不应承担确认性门

六个观测的非参数 bootstrap 只有 `6^6=46,656` 个有序重采样，完全枚举成本极低；当前 20,000 次 Monte Carlo 不是主要问题。诊断性完全枚举得到的旧 critic percentile 区间与代码近似区间几乎一致，说明主要缺陷不是 Monte Carlo 噪声，而是：

- n=6 时 percentile 区间覆盖不稳定；
- 它与符号翻转的对称假设/检验族不一致；
- 它没有直接回答 Holm 控制的材料性假设。

应保留为描述性敏感性分析，并报告 exact-resample percentile、studentized/参数敏感性以及全部 seed 值；确认性结论由直接材料性检验决定。

### 3.7 现有 power analysis 与材料性目标错位

现有公式把 `log(1.10)` 当成“相对零效应的备择均值”，所以估计的是：真效应恰为 10% 时，拒绝零效应需要多少 seed。它不是“证明效应超过 10%”的功效计算。对于 `H0: effect <= log(1.10)`，若真实效应恰好等于 10%，拒绝概率只能接近显著性水平，而不可能是 80%。

另外，标准差来自另一个消息/no-message 对比的五个 seed。即使假设正态，五个样本给出的标准差不确定性很大；以包内数值计算，95% 卡方区间约为 `[0.0494, 0.2368]`。所以 `adequate_by_normal_approximation=true` 不能作为材料性确认实验的强制放行门。

应先指定有科学意义的材料性以上备择，例如真实改善 20%，再按“直接材料性检验 + 两检验 Holm + 实际相关结构”做仿真/精确功效分析。使用旧方差的粗略正态计算时，n=6 对“真实 20%、证明超过 10%”的功效约 73.5%，而非 80%；该数值仅是规划敏感性，不是保证。

### 3.8 upper median：定义有效，但当前文字和配对解释不精确

代码不是直接对所有 evaluation scenarios 取 upper median；它先在每个 evaluation profile 内形成 endpoint，再对四个 profile endpoint 排序并取索引 2，即四个值中的第三小值。包内复用审计显示每个 arm/seed/stage 有四个 profile 文件。

因此该 endpoint：

- 是一个偏向较差 profile 的离散次序统计量；
- 会丢弃 profile 间大量信息；
- P 与 N 可能由不同 profile 决定第三顺序值；
- `Q_upper(P)-Q_upper(N)` 不等于对配对 profile 差值取同一统计量。

若研究目标明确就是“四个冻结 profile 中第三差表现”，可以保留，但必须准确命名。若目标是平均场景表现或固定库平均效应，应先在同一 profile 内形成 `log(P/N)` 配对差，再按预注册等权平均/稳健函数聚合；upper median 可作为敏感性 endpoint，而不是含混地称为“over scenarios 的 median”。

### 3.9 对 reward 与另一个 source factor 的池化

代码计算的是一个平衡、等权的边际对比：目标 factor 取 P 与 N，另一个 source factor 在 `{0,P,N}` 三个水平、reward 在 `{0,1}` 两个水平上平均。作为冻结有限因子网格上的平均对比，它在代数上成立。

但应改写为：

> 等权边际化于预先冻结的另一个 source 水平与 reward 水平。

不能写“at fixed other factors”，因为它不是把其他因素固定在单一值。还应报告预注册的 simple effects 与交互敏感性；主效应可能掩盖符号相反的交互。除非扩展 multiplicity family，不应把这些敏感性结果升级为额外确认性发现。

### 3.10 48 旧训练 + 60 新训练：当前主效应存在可计算的批次混杂

以 actor 主效应为例，每个 seed 的 P 侧六个 cell 全部是 R474 新训练；N 侧六个 cell 中：

- critic=P 的两个 reward cell 是新训练；
- critic=0/N 的四个 cell 是 R473 旧训练。

若新轮次相对旧轮次给所有 log endpoint 带来加性偏移 `b`，则估计量中的伪效应为：

```text
b × (1 - 1/3) = 2b/3
```

critic 主效应完全同理。偏移可以来自运行时、求解器、调度、硬件、数值非确定性或评估批次。哈希和 hardlink 证明“旧文件没有被改”，不证明“这些旧 arm 在 R474 当前运行时重新训练会逐位相同”。复用旧 evaluation JSON 还把评估批次与来源条件绑定。

因此，旧 N/0 endpoint 只有在一个先验 bridge/reproducibility 实验证明反事实重训等价后，才可能作为确认性参考；当前没有该 bridge，故主效应未被干净识别。

---

## 4. 对审查问题 3：分类树与措辞

### 4.1 分类树问题

1. **`FACTORIAL-INVALID` 用于路由、哈希、奖励或实现身份失败是合理的。** 当前路由已经应触发此状态。
2. **missing/failed seed 不应与 optimization 混为一类。** 缺文件、进程失败、TDS 失败应优先标记 `EXECUTION-INCOMPLETE` 或相应 integrity failure；它们不是“优化尚未收敛”的证据。
3. **计划与代码不一致。** 计划写 failed/missing seed -> `OPTIMIZATION-UNRESOLVED`；aggregate 对无效训练 manifest 写入 `integrity_errors` 并最终给 `FACTORIAL-INVALID`，而缺文件会直接抛异常，通常不会产出任何分类。
4. **half/final 符号翻转只是训练动态敏感性，不是充分或必要的优化判据。** 接近零时极小噪声可触发翻转；同号但持续漂移的训练可通过。
5. **loss plateau 门不能证明策略或 endpoint 收敛。** 当前门只比较 actor/critic loss 最后两个 decile 的绝对中位数比是否在 25% 内；高损失平台、缓慢发散、或 endpoint 漂移均可能通过。反之，健康的持续改进可能被拒绝。
6. **固定预算 total-algorithm-effect 不需要优化收敛。** 若 estimand 明确是 43,200 步后的固定预算效果，动态不稳应作为限定符，而不应抹除该固定预算估计；只有要声称 intrinsic/optimization-resolved effect 时才需要更强收敛证据。
7. **`NOT-SUPPORTED` 只能表示未建立。** 它不证明效应不存在或小于 10%。只有适当的等效/非劣或上界检验才能给 `BELOW-MATERIALITY-ESTABLISHED`。

### 4.2 推荐状态机

按顺序：

1. `DESIGN-INVALID`：路由/因子对比/批次识别条件失败；不训练。
2. `EXECUTION-INCOMPLETE`：缺 shard、失败 seed、缺 eval；不做效应判定。
3. `INTEGRITY-INVALID`：哈希、奖励、初始化、预算或语义门失败。
4. `FIXED-BUDGET-MATERIAL-EFFECT-ESTABLISHED`：直接材料性 p 值通过 Holm。
5. `FIXED-BUDGET-MATERIAL-EFFECT-NOT-ESTABLISHED`：门完整但未通过；不得解释为无效应。
6. `TRAINING-DYNAMICS-UNSTABLE`：可作为 4/5 的并列限定符；若预注册目标要求稳定优化，再把它设为阻断。

### 4.3 total-algorithm-effect 边界

当前“不能声称纯语义信息值或 universal intrinsic communication effect”的边界是正确的，必须保留并进一步具体化。修复后推荐使用：

> 在 4 设备环、冻结场景库、43,200 步训练预算、指定 learner/优化器/初始化/seed、对另一个 source factor 与 reward 水平等权边际化的条件下，真实邻居四元组 N 相对于预注册同时刻行置换 P 的有限库固定预算总算法效应，以 `log(P loss / N loss)` 表示。

不要使用：

- “communication intrinsically has value”；
- “semantic neighbour information value”；
- “all scenarios/topologies”；
- “optimization gap eliminated”；
- “no effect”，除非另有等效性证据。

---

## 5. 对审查问题 4：其他缺陷与更优方案

### 5.1 最优的等/低成本确认性设计

当前真正关心的是 N 与 P 的 actor/critic source effect。零源 0 并非识别 N/P 主效应所必需。采用全部同轮训练的 `2×2 N/P × reward`：

```text
an_cn, an_cp, ap_cn, ap_cp × r0/r1 × seeds 401..406
= 4 × 2 × 6 = 48 fresh training runs
```

与当前 60 个新训练相比：

- 保留当前已经要训练的 `an_cp, ap_cn, ap_cp`：36 runs；
- 新增 fresh `an_cn`：12 runs；
- 删除确认性 `a0_cp, ap_c0`：24 runs；
- 总计 48 runs，少 12 runs。

优势：

- actor/critic 两个主效应的每个 cell 都来自同一轮；
- fresh `an_cn` 可同时与旧 R473 `an_cn` 做 bit/endpoint bridge，但正式分析只用 fresh 版本；
- 0-source 历史 cell 可保留为描述性背景，不进入确认性主效应；
- 空出的预算可用于预注册的额外 seed、反方向 P 敏感性或更强审计，但必须先重做功效分析，不能结果后选择。

### 5.2 若坚持复用，最低 bridge 要求

至少需要：

1. 在当前 R474 运行时 fresh 重训一个完整 N/N bridge（两 reward × 六 seed）；
2. 对 base、每个 checkpoint、curves、manifest 和重新评估 endpoint 做逐文件/逐数值比较；
3. 所有确认性 checkpoint 在同一个当前 evaluator 下重新评估；不要混用旧 eval JSON 与新 eval；
4. bridge 失败即放弃复用并全新训练目标子因子。

即使 bridge 成功，最干净的做法仍是把 fresh N/N 用于确认性分析。

### 5.3 代码与门控缺陷

#### 路由门存在自证循环

`routing_check` 的池比较由 `joint + 预期公式`重新构造 `n_pool/p_pool`，而不是比较 `source_rows` 实际输出；所以公式和实现可以同时漂移而不被该 flag 捕获。`same_contemporaneous_pool` 直接为 `True`。`every_source_tuple_changed` 只检查 `p_source != i`，没有比较真实 N/P 来源-ID元组。

必须同时具备：

- 来源-ID层的结构证明；
- 对实际 `n_rows/p_rows` 的逐列值池比较；
- 完整邻居四元组多重集比较；
- 对每个 P 槽来源的非真邻居检查；
- 当前错误“对角复制”必须作为负例失败。

#### 单元测试把错误规格写成了通过条件

现有测试明确断言两个 P 槽都等于同一 pivot，并只断言 `channel_block_pools_equal`。即使测试环境完整、全部 green，也只说明错误 operationalization 被稳定实现。必须先改变规格，再改变测试；不能把现有 green 作为纯度证据。

#### rehearsal 的若干 probe 不参与总门

`objective_semantics_probe` 被记录，但没有包含在 `checks["passed"]`；reward 与 terminal truth table 也没有全部以实际布尔结果进入总门。任何关键 probe 都应由结构化 required-check 列表统一汇总，避免“记录了但不阻断”。

#### seal 没有在后续阶段重验全部前置证据

`prepare` 将 reuse、rehearsal、capacity、routing 与两个 review 的哈希写入 seal；继承的 `load_seal` 后续只重验 contract 和 `sources`，不重验这些 evidence hashes。seal 后这些文件漂移时，训练/聚合仍可能继续。应在每个 formal phase 重新哈希所有封存前置证据。

#### review gate 过弱

代码只搜索 Markdown 中是否出现 `Decision: PASS`。该字符串可以出现在引用、否定句或旧结论中。review 记录应采用结构化 JSON：顶层 decision、reviewed commit/file hashes、finding IDs、未关闭 P0/P1 数量、reviewer identity/provenance；seal 验证整个结构与目标哈希。

#### donor reachability 检查过弱

字符串扫描只检查 R474 文件中三个字面名称；R474 仍导入包含 donor 函数的整个 R470 模块。CLI 当前确实拒绝 `donor|...` shard，但“不可达”应由 CLI allowlist、运行时 monkeypatch-to-raise、调用图/AST 检查和训练/eval smoke 共同证明，而不是 grep。

#### base path 的自包含性问题

导入的 R473 donor manifest 中 `base_state_path` 仍指向 R473 路径；继承的 `_load_base` 按该路径读取，因此 R474 hardlink 的本地 base 可能并未被实际使用。哈希相同使数值身份不变，但破坏 R474 结果根的自包含和声明一致性。R474 应显式从 `OUT/donors/seedN/base_state.pt` 读取，并核对封存哈希。

#### 文档数量不一致

brief 写“10 new evaluation shards”，而 shard 列表实际是 10 arms × 2 stages = 20。应统一术语：10 个新 arm，20 个 arm-stage eval shards，内部包含 120 个 arm-stage-seed evaluation jobs/相应 profile 文件。

### 5.4 当前审查包无法完成的验证

- 包中没有 R473 runner 内容，因此无法执行计划要求的 R474-vs-R473 完整 diff 审计；只有 R470 core 与哈希记录。
- 包中没有 `src/andes_rl_kundur`、环境及多级父脚本，单元测试在导入阶段停止，不能声称 tests passed。
- 没有真实 ANDES 运行环境，本报告没有执行 rehearsal、训练、evaluation 或 aggregate。
- 本审查来自单一模型上下文中的多轮敌对审计，不是两个统计独立 reviewer；不能替代计划要求的两名独立代码审查者。

这些限制不影响路由反例：该反例完全由包内公开的 `COMM_ADJ` 与映射公式推出，已经足以阻断当前版本。

---

## 6. 发现分级与处置

| ID | 级别 | 发现 | 必须处置 |
|---|---:|---|---|
| F-01 | P0 | 当前 P 逐槽池不等、非真实 N 元组置换 | 改为 N 邻居块的循环行置换 |
| F-02 | P0 | P 两对槽恒等，输入秩/冗余改变 | 禁止单一对角值双槽复制；加入负例测试 |
| F-03 | P0 | 新旧训练批次以 `2/3` 系数污染两个主效应 | 全 fresh 2×2 子因子，或先通过 bridge；推荐前者 |
| F-04 | P0 | 材料性未直接检验，声明与代码不一致 | 对 `H0: effect<=log1.10` 直接检验并 Holm |
| F-05 | P1 | n=6 离散且 power analysis 针对错误目标 | 重做实际检验下的材料性功效；展示所有 seed |
| F-06 | P1 | upper median 实为四 profile 的第三顺序值，非简单 scenario median | 冻结准确 estimand；优先 profile 内配对后聚合 |
| F-07 | P1 | sign-flip 的 exact 性依赖未声明的对称/随机化条件 | 明确假设或真实随机分配标签 |
| F-08 | P1 | routing gate 部分由预期公式自证、同池标志硬编码 | 比较实际输出 + 来源-ID结构检查 + mutation tests |
| F-09 | P1 | rehearsal/seal/review gate 未完整闭合 | 所有 probe 进入 pass；load_seal 重验全部 evidence；结构化 review |
| F-10 | P1 | missing/failed/optimization 分类与代码不一致 | 分离 design、execution、integrity、dynamics、effect 状态 |
| F-11 | P2 | imported base manifest 指向父轮路径 | 使用 R474 本地 hardlink 路径并封存 |
| F-12 | P2 | eval shard 数量与文档不一致 | 统一为 20 arm-stage shards |
| F-13 | 验证限制 | 缺依赖与 R473 runner，无法完成全量动态/diff 审计 | 在完整仓库/CI 重新运行，并保留日志与 commit hash |

**关闭条件：F-01 至 F-04 全部关闭前，不得 seal 或启动训练。F-05 至 F-10 应在新的确认性协议封存前关闭。**

---

## 7. 关键内部证据位置

- Guardrail 逐槽要求：`skills/kundur-round/references/experiment-design-guardrails.md:17-34`
- 当前设计的两槽合并放宽：`memory/rounds/R474/plan.md:73-93`
- 当前对角复制实现：`scripts/run_r474_u2_source_factorial.py:151-179`
- 当前 routing check：`scripts/run_r474_u2_source_factorial.py:182-257`
- 当前 tests 固化错误规格：`tests/test_run_r474_u2_source_factorial.py:45-123`
- upper median / main effect / inference / classification：`scripts/run_r470_u2_source_factorial.py:859-1018`
- loss 稳定门：`scripts/run_r470_u2_source_factorial.py:610-625`
- reuse/retrain 方案：`memory/rounds/R474/plan.md:95-123`
- rehearsal 总门遗漏：`scripts/run_r474_u2_source_factorial.py:751-907`
- seal 写入与继承 load_seal：`scripts/run_r474_u2_source_factorial.py:922-1008`；`scripts/run_r470_u2_source_factorial.py:212-220`
