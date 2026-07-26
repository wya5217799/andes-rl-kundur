# 面向能量可行多时间尺度 VSG 控制的聚焦调研

**日期：** 2026-07-25  
**性质：** 新方向可行性调研；不包含论文写作、模型修改、训练或新增仿真  
**聚焦问题：** 当前 ANDES/Kundur 项目是否应从“四台 VSG 只调 \(M/D\)”转向“快 \(M/D\) + 慢有功恢复 + 能量/SOC 约束”，以及最低成本的验证路径是什么。

## 摘要

本轮调研把项目原论文、R270/R271 的实证结果、ANDES 2.0.0 本地源码和 2011–2026 年的 VSG、二次调频、BESS 及学习控制文献放在同一控制层级中比较。结论不是“\(M/D\) 无效”，也不是简单地“再加一个功率变量”。在当前摆动方程

\[
M\dot{\omega}=P_m-P_e-D(\omega-1)
\]

中，\(M\) 决定 RoCoF 和暂态轨迹；\(D(1-\omega)\) 已经是隐式比例有功/转矩响应，能够改善 containment 和振荡，但在有限 \(D\) 下必须保留非零频差才能承担持续失衡。额定频率处的持续恢复需要改变 \(P_{\rm ref}\) 或由积分/二次控制提供独立有功；该有功又必须服从功率、能量、SOC、headroom、爬坡和换流器能力约束。

这一区分同时修正了对原论文的误读。Yang 等的四 VSG 工作以功率/频率振荡抑制和系统总 \(H/D\) 近守恒为目标，其频率奖励只衡量各节点是否同步；所有节点保持同一非零频差时奖励仍可为零 [1]。因此 R270/R271 没有否定原论文的同步问题，而是证明当前项目不能把同步收益表述为完整的共同频率恢复。

ANDES 2.0.0 已经提供大部分低成本试验构件：`ESD1` 有 SOC、额定能量、充放电效率和功率入口；`PVD1/DG.set_paux()` 有外部有功指令；`REECA1/REPCA1` 有有功爬坡、限流和频率 PI；`REGCV1/2` 与 `REGF2` 提供 VSG/VSM 型 GFM 动态。但是，内置模型中没有一个同时把 GFM/VSG、BESS 能量状态、双向功率边界和慢速 \(P_{\rm ref}\) 恢复统一为同一设备合同。

最值得进入下一步可行性实验的候选方向是：**能量可行的多时间尺度多 VSG 控制**。先保留现有 \(M/D\) 层负责 RoCoF、峰值和同步，再用独立、受约束的储能有功层完成共同频率恢复和 SOC 回补；先比较 droop、droop+PI/AGC 和 constrained MPC，确认存在 classical gap 后，才允许使用 bounded residual learning。单纯“加 SOC 后继续用 RL 调 \(M/D\)”与已有四机两区 adaptive VSG-BESS 工作高度重叠 [15]；单纯“使用 GNN-RL”也已受到 2025–2026 年网络化学习工作的挤压 [22], [23]。真正可能形成贡献的是控制目标分解、显式能量合同、全拓扑留出、安全约束和严格验证的交叉，而不是算法名称。

---

## 1. 研究问题与边界

### 1.1 冻结的研究问题

**RQ1：** 对当前四 VSG/Kundur 模型，什么是同时保留快速同步能力并实现持续共同频率恢复的最小物理执行器与控制层级？

**RQ2：** ANDES 2.0.0 已支持哪些状态、限制和外部控制接口？最小复用路线与高保真路线分别是什么？

**RQ3：** 在已有 adaptive \(J/D\)、二次频率控制、GFM-BESS 多时间尺度控制和图学习研究之后，什么候选方向仍有可辩护的研究空间？进入学习控制前应由什么实验否证？

### 1.2 本轮不做什么

- 不训练新神经网络；
- 不修改 ANDES 环境或设备模型；
- 不运行新 ANDES 轨迹；
- 不写论文正文、摘要投稿版或论文图；
- 不把一次检索未找到等同于“世界上从未有人做过”；
- 不把 ANDES 正序机电暂态结果外推为 converter inner-loop、限流故障行为或 EMT 稳定性证据。

---

## 2. 方法与证据审计

### 2.1 检索视角

本轮采用三个相互对抗的视角：

1. **主流控制视角：** 梳理 virtual inertia/damping、primary containment、secondary restoration 和 energy management 的职责边界。
2. **模型真实性反方：** 专门寻找对理想 virtual inertia、无限能量、忽略测频噪声、SOC 和 P/Q capability 的批评或限制。
3. **平台与经典基线视角：** 审查 ANDES 2.0.0 的可复用模型和能否先用 PI/MPC 完成 actuator-authority 验证。

检索优先级为官方标准/报告、出版社页面、作者或机构全文、同行评审论文。无法核验标题、作者或所用结论的材料不进入综合判断。付费墙来源只使用可从官方元数据或摘要确认的结论，不引用无法看到的具体条款。

### 2.2 证据等级

| 等级 | 证据类型 | 本报告用途 |
|---|---|---|
| A | 法规、标准组织、NERC/NREL/UNIFI/WECC 官方报告 | 定义服务边界、模型功能和验证要求 |
| A | 理论证明 + 实验/HIL/实物 BESS | 判断控制结构与物理约束是否成立 |
| B | 理论证明 + 网络仿真 | 判断机制、稳定性和网络耦合 |
| B | 详细 switching/battery 模型或大系统动态仿真 | 判断设备能力与系统效应 |
| C | 单算例正序或 MATLAB 仿真 | 发现候选机制，不单独支撑强结论 |
| P | 本项目 prospective real-ANDES 证据 | 判断当前实现的可达裕度与失败机制 |

### 2.3 项目证据

| 项目证据 | 结果 | 本轮解释 |
|---|---|---|
| 原论文事实库 | 奖励衡量节点频率一致性；不要求回到额定值 | 原课题是同步/振荡抑制，不是完整二次恢复 |
| R270：64 条预注册 real-ANDES 轨迹 | IAE \(-0.311271\%\)，同步损失 \(-7.805520\%\)，最差峰值 \(-8.209868\%\)，RoCoF \(-11.113147\%\) | \(M/D\) 有真实快速暂态能力，但共同恢复裕度很小 |
| R271：源码、平衡点和冻结轨迹审计 | 10/10 源码检查、6/6 轨迹门通过；末 5 s 共同偏差反而恶化 \(0.017570\%\) | 当前 `PV+GENCLS` 四 VSG 代理没有独立 \(P_{\rm ref}\)、SOC、能量或 headroom |
| ANDES 2.0.0 本地源码 | `ESD1`、`PVD1`、`REGCV1/2`、`REGF2`、`REECA1`、`REPCA1` 均存在 | 平台具备组合试验所需的大部分构件，但没有统一 GFM-BESS 合同 |

---

## 3. MECE 控制层级：四个不同问题

把所有“调频”压成一个指标，是本方向最容易产生错误结论的地方。文献和项目方程共同支持以下互斥且基本完备的分层。

| 层级 | 典型时间尺度 | 主要变量 | 主要目标 | 不能独立保证 |
|---|---:|---|---|---|
| 快速惯量/阻尼层 | ms–数秒 | \(M/J\)、\(D\)、RoCoF 通道 | 抑制 RoCoF、峰值、功率/频率振荡和失同步 | 额定频率处持续功率平衡 |
| 一次 containment 层 | 数百 ms–数十秒 | P–f droop、FFR/PFR | 阻止频率继续偏离并建立准稳态 | 零稳态频差 |
| 二次 restoration 层 | 数秒–数分钟 | PI、consensus、AGC、\(P_{\rm ref}\) | 消除频差、恢复功率分配 | 长期能量可用性 |
| 能量/储备恢复层 | 分钟–小时 | SOC/SOE、调度、MPC、充电 | 补回 reserve、管理 headroom 和多次事件 | 快速电磁/机电稳定 |

Simpson-Porco 等的 DAPI 和 Shafiee 等的 distributed secondary control 都明确从一次下垂产生的稳态偏差出发，以较慢积分层恢复额定频率并保持有功分配 [4], [5]。NERC 则从系统服务角度区分 inertia、FFR/PFR 和 secondary/AGC，并强调快速有功响应仍受到 headroom、持续时间、SOC、限流和恢复过程影响 [7]。两类证据互相补强：前者说明“如何恢复”，后者说明“恢复功率从哪里来、能维持多久”。

---

## 4. 分支 A：动态 \(M/D\) 的价值与边界

Synchronverter 奠定了用换流器模拟同步机摆动与下垂行为的基本路线 [3]，而 VSM 与带滤波 frequency droop 在特定小信号条件下还存在参数等价关系 [6]。在此基础上，Alipoor 等通过交替虚拟惯量改善暂态阻尼并以 DSP inverter 实验验证，说明动态调 \(J\) 确实可以改变功率和频率振荡 [2]。Yang 等进一步在多 VSG 网络中实时重分配 \(H/D\)，目标是节点同步且系统总参数尽量不变 [1]。Feng 等则把多 DER 的 inertia/damping 作为网络耦合分配问题，并加入 frequency trajectory 与小信号稳定性约束 [16]。这些工作与 R270 的 RoCoF、峰值和同步改善方向一致，因此项目不应废弃 \(M/D\) 层。

但是，这一分支通常不提供独立、长期可持续的 \(P_{\rm ref}\) 恢复。当前方程在稳态时变为

\[
0=P_m-P_e-D(\omega-1).
\]

\(M\) 从平衡关系消失；有限 \(D\) 可通过非零 \(\omega-1\) 提供比例响应，却不能在 \(\omega=1\) 时继续承担非零持续功率。更准确的措辞不是“\(D\) 不是功率通道”，而是“\(D\) 是隐式比例功率/转矩响应，但缺少独立设定值、积分恢复和能量合同”。

Mallada 的 iDroop 研究还从噪声角度给出反证：标准 virtual-inertia 的微分测频通道在其线性模型中可能产生无界噪声放大，而动态 droop 可在不改变稳态解的情况下塑造动态 [10]。Eriksson 等对 synthetic inertia 与 FFR 的定义比较，以及 Fang 等对 power-electronics system inertia 的综述，也把 filtering、endurance、recovery 和实际储能来源列为关键边界 [20], [19]。这些证据不能证明所有带滤波和限幅的 VSG 都有问题，但要求未来模型显式写入测频滤波、延迟和 RoCoF 信号质量，而不能把理想 \(\dot f\) 当成免费状态。

**分支 A 结论：** \(M/D\) 是有价值的快速同步与安全层；把它升级为“完整共同频率恢复层”既不符合方程，也不符合主流分层。

---

## 5. 分支 B：额定频率恢复来自显式有功设定值

二次控制文献对这一点高度一致。DAPI 使用较慢的 distributed integral action，在恢复额定频率的同时保持 active-power sharing [4]；Shafiee 等也采用 droop primary + PI secondary，并用实验考察通信延迟和丢包 [5]。Mégel 等把 storage efficiency 纳入 distributed secondary frequency control [24]，Liang 等则给出同时考虑 storage、voltage 和 ramping constraints 的 MPC 设计 [25]。Pouresmaeil 等在 adaptive VSG 中把 \(H/D\)、droop 和额外频率 PI 分开：前两者塑造惯性与一次动态，积分项通过改变输入有功才实现 nominal recovery [14]。

因此，最低结构不应写成模糊的“AI 同时调所有变量”，而应先定义

\[
P_{\rm cmd}
=P_{\rm schedule}
+P_{\rm inertia}
+P_{\rm droop}
+P_{\rm secondary}
+P_{\rm soc\_recovery}.
\]

各分量随后必须共同经过功率、爬坡和换流器限制。快速层可以由 \(M/D\) 参数变化隐式产生，也可以显式映射为 power request；慢速层必须真正改变 \(P_{\rm ref}\) 或等价有功指令。若原系统的 governor/AGC 已经提供恢复，则必须记录它们的贡献，不能把恢复误归因于 VSG \(M/D\)。

**分支 B 结论：** “快 \(M/D\) + 慢 \(P_{\rm ref}\)”的控制分工是必要建模原则，但它本身并不新；DAPI、PI secondary、MPC 和多时间尺度 GFM-BESS 已覆盖大量结构性内容。

---

## 6. 分支 C：功率恢复必须受能量与换流器能力约束

NERC 将 FFR 描述为快速有功注入或负荷降低，并强调 sustained response、headroom、current limit、delay、SOC 和 energy recovery [7]。欧洲规则也把 FCR 的 containment 与 FRR 的额定频率/计划交换恢复区分，并对有限能量资源规定持续和能量恢复责任 [8]。这些运行定义不提供 Kundur 的容量参数，但否定了“无限持续的虚拟功率”这一模型假设。

在设备与实验层面，Knap 等表明 inertial response 与 primary reserve 必须同时按 power 和 energy sizing [11]；Namor 等在 560 kWh/720 kVA 实物 BESS 上把 period-ahead power/energy budget 与 real-time setpoint deployment 分开 [12]；Gerini 等进一步形成 day-ahead schedule、intra-day MPC 和 real-time GFM 的三层结构，并显式考虑 SOE、P/Q capability 和 BESS 实验验证 [13]。Zuo 等使用详细 switching converter 与 SOC-dependent battery 模型比较 GFM/GFL BESS，显示结果依赖 droop gain 和 filter bandwidth，且系统 restoration 仍由更慢层承担 [17]。UNIFI V2 又从 vendor-agnostic 规范层面要求区分 plant/unit 功能，并把 source-side SOC/能量限制、可调度稳态功率和设备极限视为 GFM 性能的一部分 [30]。

最小可行 BESS 合同至少应包含

\[
-P_{\max}^{\rm ch}\le P_{\rm bess}\le P_{\max}^{\rm dis},
\]

\[
\dot E =
\begin{cases}
-P_{\rm bess}/\eta_{\rm dis},&P_{\rm bess}>0,\\
-\eta_{\rm ch}P_{\rm bess},&P_{\rm bess}<0,
\end{cases}
\qquad SOC=E/E_{\rm rated},
\]

并约束

\[
SOC_{\min}\le SOC\le SOC_{\max},\qquad
P^2+Q^2\le S_{\max}^2,\qquad
|\dot P|\le R_{\max}.
\]

还应记录正负 headroom、功率 lag、限流优先级、SOC recovery 和连续扰动后的 reserve replenishment。若最终文章声称 converter fault/current-limiting 机制，则 ANDES 正序模型不足以单独验证，需要 EMT、HIL 或实物交叉证据 [9], [26]。

**分支 C 结论：** SOC 是必要但不充分的状态。只有 SOC 标量而没有功率/能量/电流/PQ 能力和恢复逻辑，仍可能高估控制器。

---

## 7. 分支 D：学习控制的拥挤区与剩余空间

### 7.1 已被覆盖的近邻

仅用学习器调 \(J/D\) 已不是空白。Oboreh-Snapps 等已经使用 TD3 调节 VSG 惯量/阻尼，并用 Simulink 与 RTDS 考察频率、RoCoF 和 settling [29]；safe RL 工作也已经把 GFM 频率调节、Lyapunov region of attraction 和不确定性结合 [21]。Kang 等在 IEEE 33-bus 多 VSG 上使用 decentralized MARL 调节参数 [22]。

更直接的 novelty risk 是 He 等 2023：其工作已在修改后的四机两区系统中根据系统状态与 BESS SOC 自适应调 VSG inertia/droop，并考虑功率容量和 SOC 范围 [15]。因此，“把本项目 GENCLS 换成带 SOC 的 BESS，然后继续让 RL 调 \(M/D\)”很难构成清晰的新问题。

“图网络 + RL”也不是独立贡献。Eshun、Fatemi 和 Fattahi 2026 已将 spectral virtual inertia allocation、时空 GNN 与 RL 用于 IEEE 118-bus、拓扑变化和约束投影 [23]。这说明项目原定 graph residual 方向仍可作为实现手段，但不能再以“首次使用 GNN-RL”作为核心论点。

### 7.2 本轮未发现被完整覆盖的交叉点

在核验语料中，尚未发现一项工作同时满足：

- 多台、多区域 GFM/VSG；
- 快速且有界的 \(M/D\) 同步/安全层；
- 独立 \(P_{\rm ref}\) 二次恢复；
- SOC、能量、headroom、ramp、current/PQ capability；
- 经典控制上的 bounded residual，而非从零策略；
- 完整 held-out topology/VSG-count/generalisation；
- failure、tail risk、action variation 和约束激活证据；
- real dynamic simulation 后再做跨仿真器或 HIL 验证。

这只是“当前核验语料未形成完整交集”，不是“原创性证明”。尤其是 adaptive VSG-BESS、多时间尺度 BESS、网络化 \(J/D\) 分配和图学习各自都已有强近邻。候选贡献必须来自这些分支之间可被实验明确识别的冲突：例如快速同步层与慢速能量恢复层在 topology shift、SOC 饱和、通信延迟或多次扰动下如何协调，而不是把已有模块简单拼接。

---

## 8. ANDES 2.0.0 平台能力与缺口

本轮直接核验 WSL 环境 `/home/wya/andes_venv`，版本为 `2.0.0`。ANDES 的 hybrid symbolic-numeric framework 已在多个电力系统算例上形成公开的建模与数值验证基础 [27]；`ESD1`、`REECA1` 等设备构件也与 WECC 正序暂态储能/新能源模型体系相衔接 [28]。这些既有验证不自动证明本项目未来自定义 GFM-BESS 方程正确，新增模型仍须单独校核。

| ANDES 模型/接口 | 已有能力 | 可用于本项目 | 不足 |
|---|---|---|---|
| `ESD1` | `SOCmin/max/init`、`En`、`EtaC/EtaD`、SOC 积分与 SOC 限幅 | 独立 BESS 慢有功执行器 | 基于 `PVD1` 的并网型电流注入，不是 GFM/VSG |
| `PVD1` / `DG.set_paux()` | `Pref`、`Pext0` 外部有功附加信号 | PI/AGC/MPC/RL 的外部控制入口 | 本身不提供二次控制器设计 |
| `REGCV1/2` | `Pref`、\(M\)、\(D\)、frequency droop `kw`、VSG 动态 | 更原生的 VSG 路线 | 无 SOC/电池能量 |
| `REGF2` | VSM 型 grid-forming inverter | GFM/VSM 对照 | 无 SOC/统一储能合同 |
| `REECA1` | `Pref` filter、`dPmax/min`、`Imax` 和 P/Q 限流逻辑 | 有功爬坡与 converter-limit 参考 | GFL 控制链；无 SOC |
| `REPCA1` | plant-level frequency droop/PI、`Kpg/Kig` | 经典厂站频率控制对照 | 不管理 BESS 能量，也不是完整 AGC |

### 8.1 最小复用路线：混合代理

保留当前四台 `PV+GENCLS` 及 \(M/D\) 快速层，在相同或明确指定母线增加独立 `ESD1`，通过 `DG.set_paux()` 施加受限慢速有功。优点是：

- 不破坏现有 V4、sealed bank、physical endpoints 和 residual adapter；
- 可立即验证“显式有功恢复是否有足够收益空间”；
- 自带 SOC/能量/效率和功率限幅基础；
- 适合比较 droop、PI/AGC 和 constrained MPC。

其语义必须诚实表述为“独立 VSG 代理 + GFL BESS 有功支持”，不能说成同一台物理 GFM-BESS。

### 8.2 高保真路线：统一 GFM-BESS

以 `REGCV1/2` 或 `REGF2` 的 VSG/VSM 动态为快层，加入 `ESD1` 风格的 SOC/能量积分、双向功率边界、效率、headroom 和 SOC recovery，再加入 `REECA1` 风格的爬坡/限流与可变 \(P_{\rm ref}\)。这能形成更物理一致的设备合同，但需要：

- 新模型方程和初始化审计；
- 功率流与动态平衡一致性；
- P/Q/current priority；
- 设备容量来源与 per-unit 换算；
- 与 ANDES 既有模型或另一仿真器的交叉验证。

这不是第一轮 feasibility 所必需；应由混合代理试验先证明收益空间。

---

## 9. 候选方向比较

| 候选方向 | 物理问题 | 现有代码复用 | 新颖性风险 | 工程风险 | 当前建议 |
|---|---|---:|---:|---:|---|
| T1：只做 \(M/D\) 同步与安全 | RoCoF、峰值、区间振荡、同步 | 很高 | 中高；已有大量 adaptive \(J/D\) | 低 | 可作为窄机制或 baseline，不宜继续算法扫榜 |
| T2：`GENCLS` 快层 + `ESD1` 慢层 | 同步/containment 与 restoration 分工，显式 SOC/能量 | **最高** | 中；“双层”本身不新 | **低中** | **推荐先做可行性验证** |
| T3：统一 GFM-BESS + 多时间尺度控制 | 同一设备内的 VSG、功率、能量与 converter 约束 | 中 | 较低，但邻近工作强 | 高 | T2 阳性后进入 |
| T4：在固定 Kundur 上更换 RL 算法 | 复用同一 \(M/D\) 合同 | 高 | **极高** | 中 | 停止 |
| T5：直接上 GNN-RL | 拓扑泛化 | 中 | 高；近年已有强近邻 | 高 | 物理模型和 classical gap 明确后再进入 |

### 推荐候选问题

> 在相同功率、能量、SOC、headroom、爬坡及限流约束下，一个把快速 \(M/D\) 同步层与慢速 \(P_{\rm ref}\) 恢复层分开的控制架构，能否在多扰动和拓扑变化下稳定优于最佳单层控制；若经典控制仍存在可重复缺口，bounded residual 是否能在不增加失败率、尾部风险和动作剧烈度的条件下缩小该缺口？

这个问题允许原论文的同步机制继续发挥作用，同时把 R270/R271 暴露的共同恢复和能量真实性缺口转化为可否证研究对象。

---

## 10. 进入 AI 前的四道决定性实验门

本轮不执行实验，但给出下一轮可直接冻结的 go/no-go 逻辑。

### Gate 1：慢有功执行器是否有实质 authority

固定同一场景、容量和约束，比较：

1. 无新增 BESS；
2. BESS P–f droop；
3. droop + PI/AGC；
4. constrained MPC。

主要终点为 terminal common-frequency absolute error/IAE、恢复时间、失败率、SOC/能量和饱和时间。若 PI/MPC 也不能稳定改善恢复，应先诊断模型、扰动和容量，而不是训练 AI。

### Gate 2：快 \(M/D\) 层是否仍有独立贡献

在相同慢层下，对比关闭/开启冻结的 \(M/D\) 层，检查 RoCoF、峰值、normalized synchronization loss、inter-area oscillation 和 action total variation。只有快层仍提供独立收益，双层问题才成立。

### Gate 3：双层是否具有非加和价值

比较：

- 最佳慢层；
- 最佳快层；
- 快慢联合；
- 等计算/等动作预算的经典联合控制。

如果联合控制不优于最佳单层，研究应缩小为一个层级，不应为了复杂度保留双层。

### Gate 4：是否存在 learning gap

只有在调好的 droop+PI 与 constrained MPC 在预先定义的 topology shift、SOC 饱和、连续扰动、延迟或局部观测下出现稳定复现的缺口时，才训练 bounded residual。学习器必须接受：

- 以经典控制为 prior；
- residual 幅值、速率与能量投影；
- training/deployment 完全一致；
- sealed whole-topology bank；
- failure、CVaR/tail、action TV、SOC 和能量的共同门槛。

若经典控制已经解决问题，结论应是“无需 RL”，这仍然是有价值的可行性结果。

---

## 11. 自我反驳与六门审查

### 11.1 最强反方意见

**反方 1：原论文只承诺同步，为什么要扩大到 restoration？**  
成立。R271 不能用于否定 Yang 等的实际目标。扩大问题的理由只能是项目希望形成更完整、更物理可信的新研究方向，而不是“复现失败”。T1 仍然可以做，但新颖性与系统价值较窄。

**反方 2：\(D\) 已经产生有功响应，是否重复加通道？**  
不会，前提是明确分层。\(D\) 是 frequency-error proportional response；慢层改变 \(P_{\rm ref}\) 并承担零误差恢复和 SOC 回补。报告禁止使用“\(D\) 没有功率作用”这一错误表述。

**反方 3：双层、SOC、MPC 都已有工作，创新在哪里？**  
单个组件没有创新。可能的空间只在未被完整覆盖的交叉：多 VSG、能量可行、快慢目标分解、全拓扑留出、安全 residual 和严格物理端点。若后续更全面检索找到高度相同工作，应进一步收窄或停止。

**反方 4：`GENCLS+ESD1` 不是物理 GFM-BESS。**  
成立。因此 T2 只用于 actuator-authority 和研究问题筛选，不能支撑统一设备机理结论。高保真主张必须转入 T3 或跨工具验证。

**反方 5：SOC 标量过于简单。**  
也成立。第一轮若只判断系统控制 authority，SOC、功率、能量、效率和 capability 可作为最小模型；若声称电池内部物理、寿命或极限能力，需要 state-dependent power、DC voltage、温度/老化等更详细模型 [18]。

### 11.2 六门结论

| 审查门 | 结论 | 说明 |
|---|---|---|
| 问题是否真实 | 通过 | R270/R271、二次控制理论和系统服务定义一致 |
| 原论文是否被公平解释 | 通过，已修正 | 同步问题保留；只否定完整 restoration 外推 |
| 文献是否已有完全相同解 | 暂未发现 | 组件高度拥挤，交叉空白需继续核验 |
| 平台能否低成本验证 | 通过 | ANDES 2.0.0 可用 `ESD1+paux` 先做混合代理 |
| 是否必须立即使用 AI | 不通过 | 必须先过 classical actuator-authority 与 learning-gap 门 |
| 是否足以支撑高保真结论 | 暂不通过 | ANDES 正序混合代理之后仍需统一模型或 EMT/HIL |

---

## 12. 对研究问题的直接回答

### RQ1

最小物理结构是：保留快速 \(M/D\) 或等价有界功率响应来控制 RoCoF、峰值和同步；增加可改变 \(P_{\rm ref}\) 的慢速 PI/consensus/AGC/MPC 来消除持续频差；所有功率请求共同经过 SOC、能量、充放电功率、headroom、ramp/lag 和 converter capability 约束，并设计 SOC/reseve recovery。不能只增加一个无来源的自由 \(P_{\rm ref}\)。

### RQ2

ANDES 2.0.0 已有足够组件开展低成本 feasibility：`ESD1` 负责 SOC/能量，`DG.set_paux()` 负责外部有功，`REECA1/REPCA1` 提供爬坡/限流/PI 参考，`REGCV1/2` 与 `REGF2` 提供 VSG/VSM。最低复用路线是现有四 VSG 快层 + 独立 `ESD1` 慢层；它是混合代理。统一 GFM-BESS 需要自定义模型，是第二阶段。

### RQ3

推荐的新方向不是“更多 RL”、不是“加 SOC 后继续调 \(M/D\)”，也不是“直接上 GNN”。最可辩护候选是：

> **面向拓扑变化的能量可行多时间尺度多 VSG 控制：将快速同步/安全层与慢速频率恢复/SOC 回补层显式分开，在经典控制上使用受功率、能量和稳定性约束的 bounded residual，并以完整 held-out topology、tail risk 和 physical endpoints 验证。**

当前只能把它定为“值得做 T2 feasibility 的候选”，还不能直接宣布为最终论文方向。下一步应执行 Gate 1–3；只有 classical gap 存在，才需要再次调用 idea-evaluator 决定是否进入学习与拓扑泛化。

---

## References

[1] Q. Yang, L. Yan, X. Chen, Y. Chen, and J. Wen, “A Distributed Dynamic Inertia-Droop Control Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple Paralleled VSGs,” *IEEE Transactions on Power Systems*, vol. 38, no. 6, pp. 5598–5612, 2023.

[2] J. Alipoor, Y. Miura, and T. Ise, “Power System Stabilization Using Virtual Synchronous Generator With Alternating Moment of Inertia,” *IEEE Journal of Emerging and Selected Topics in Power Electronics*, vol. 3, no. 2, pp. 451–458, 2015.

[3] Q.-C. Zhong and G. Weiss, “Synchronverters: Inverters That Mimic Synchronous Generators,” *IEEE Transactions on Industrial Electronics*, vol. 58, no. 4, pp. 1259–1267, 2011.

[4] J. W. Simpson-Porco, Q. Shafiee, F. Dörfler, J. C. Vasquez, J. M. Guerrero, and F. Bullo, “Secondary Frequency and Voltage Control of Islanded Microgrids via Distributed Averaging,” *IEEE Transactions on Industrial Electronics*, vol. 62, no. 11, pp. 7025–7038, 2015.

[5] Q. Shafiee, J. M. Guerrero, and J. C. Vasquez, “Distributed Secondary Control for Islanded Microgrids—A Novel Approach,” *IEEE Transactions on Power Electronics*, vol. 29, no. 2, pp. 1018–1031, 2014.

[6] S. D’Arco and J. A. Suul, “Equivalence of Virtual Synchronous Machines and Frequency-Droops for Converter-Based MicroGrids,” *IEEE Transactions on Smart Grid*, vol. 5, no. 1, pp. 394–395, 2014.

[7] NERC Inverter-Based Resource Performance Task Force, *Fast Frequency Response Concepts and Bulk Power System Reliability Needs*, North American Electric Reliability Corporation, 2020.

[8] European Commission, *Commission Regulation (EU) 2017/1485 Establishing a Guideline on Electricity Transmission System Operation*, 2017.

[9] Y. Lin, J. H. Eto, B. B. Johnson, J. D. Flicker, R. H. Lasseter, H. N. Villegas Pico, G.-S. Seo, B. J. Pierre, and A. Ellis, *Research Roadmap on Grid-Forming Inverters*, National Renewable Energy Laboratory, 2020.

[10] E. Mallada, “iDroop: A Dynamic Droop Controller to Decouple Power Grid’s Steady-State and Dynamic Performance,” in *Proceedings of the IEEE Conference on Decision and Control*, pp. 4957–4964, 2016.

[11] V. Knap, S. K. Chaudhary, D. I. Stroe, M. J. Swierczynski, B.-I. Craciun, and R. Teodorescu, “Sizing of an Energy Storage System for Grid Inertial Response and Primary Frequency Reserve,” *IEEE Transactions on Power Systems*, vol. 31, no. 5, pp. 3447–3456, 2016.

[12] E. Namor, F. Sossan, R. Cherkaoui, and M. Paolone, “Control of Battery Storage Systems for the Simultaneous Provision of Multiple Services,” *IEEE Transactions on Smart Grid*, vol. 10, no. 3, pp. 2799–2808, 2019.

[13] F. Gerini, Y. Zuo, R. Gupta, A. Zecchino, Z. Yuan, E. Vagnoni, R. Cherkaoui, and M. Paolone, “Optimal Grid-Forming Control of Battery Energy Storage Systems Providing Multiple Services: Modeling and Experimental Validation,” *Electric Power Systems Research*, vol. 212, art. 108567, 2022.

[14] M. Pouresmaeil, R. Sangrody, S. Taheri, and E. Pouresmaeil, “An Adaptive Parameter-Based Control Technique of Virtual Synchronous Generator for Smooth Transient Between Islanded and Grid-Connected Mode of Operation,” *IEEE Access*, vol. 9, pp. 137322–137337, 2021.

[15] P. He, Z. Li, H. Jin, C. Zhao, J. Fan, and X. Wu, “An Adaptive VSG Control Strategy of Battery Energy Storage System for Power System Frequency Stability Enhancement,” *International Journal of Electrical Power & Energy Systems*, vol. 149, art. 109039, 2023.

[16] C. Feng, L. Huang, X. He, Y. Wang, F. Dörfler, and C. Kang, “Hybrid Oscillation Damping and Inertia Management for Distributed Energy Resources,” *IEEE Transactions on Power Systems*, vol. 40, no. 6, pp. 5041–5056, 2025.

[17] Y. Zuo, Z. Yuan, F. Sossan, A. Zecchino, R. Cherkaoui, and M. Paolone, “Performance Assessment of Grid-Forming and Grid-Following Converter-Interfaced Battery Energy Storage Systems on Frequency Regulation in Low-Inertia Power Grids,” *Sustainable Energy, Grids and Networks*, vol. 27, art. 100496, 2021.

[18] Y. Chen, K. Zheng, C. Feng, J. Huang, H. Guo, and H. Zhong, “Optimal Grid-Forming BESS Management Incorporating Internal Battery Physics,” *Applied Energy*, vol. 385, art. 125448, 2025.

[19] J. Fang, H. Li, Y. Tang, and F. Blaabjerg, “On the Inertia of Future More-Electronics Power Systems,” *IEEE Journal of Emerging and Selected Topics in Power Electronics*, vol. 7, no. 4, pp. 2130–2146, 2019.

[20] R. Eriksson, N. Modig, and K. Elkington, “Synthetic Inertia versus Fast Frequency Response: A Definition,” *IET Renewable Power Generation*, vol. 12, no. 5, pp. 507–514, 2018.

[21] H. Shuai, B. She, J. Wang, and F. Li, “Safe Reinforcement Learning for Grid-Forming Inverter Based Frequency Regulation with Stability Guarantee,” *Journal of Modern Power Systems and Clean Energy*, vol. 13, no. 1, pp. 79–86, 2025.

[22] S. Kang, Y. Jung, D. You, and G. Jang, “Enhancing Frequency Stability with Decentralized Adaptive Control Using Multi-Agent Deep Reinforcement Learning of Multi-VSGs,” *International Journal of Electrical Power & Energy Systems*, vol. 172, art. 111374, 2025.

[23] C. K. Eshun, N. Fatemi, and J. Fattahi, “Spectral Sensitivity and Physics Informed GNN-RL for Real Time Power Grid Stability,” *Sustainable Energy, Grids and Networks*, vol. 46, art. 102168, 2026.

[24] M. Mégel, E. C. Kerrigan, and G. A. Constantinides, “Distributed Secondary Frequency Control Algorithm Considering Storage Efficiency,” *IEEE Transactions on Smart Grid*, vol. 9, no. 6, pp. 6214–6228, 2018.

[25] L. Liang, Y. Hou, and D. J. Hill, “Design Guidelines for MPC-Based Frequency Regulation for Islanded Microgrids with Storage, Voltage, and Ramping Constraints,” *IET Renewable Power Generation*, vol. 11, no. 8, pp. 1200–1210, 2017.

[26] NERC, *Grid Forming Functional Specifications for BPS-Connected Battery Energy Storage Systems*, North American Electric Reliability Corporation, 2023.

[27] H. Cui, F. Li, and K. Tomsovic, “Hybrid Symbolic-Numeric Framework for Power System Modeling and Analysis,” *IEEE Transactions on Power Systems*, vol. 36, no. 2, pp. 1373–1384, 2021.

[28] WECC Renewable Energy Modeling Task Force, *WECC Battery Storage Dynamic Modeling Guideline*, Western Electricity Coordinating Council, 2017.

[29] O. Oboreh-Snapps, B. She, S. Fahad, H. Chen, J. Kimball, F. Li, H. Cui, and R. Bo, “Virtual Synchronous Generator Control Using Twin Delayed Deep Deterministic Policy Gradient Method,” *IEEE Transactions on Energy Conversion*, vol. 39, no. 1, pp. 214–228, 2024.

[30] B. Kroposki, *UNIFI Specifications for Grid-Forming Inverter-Based Resources, Version 2*, National Renewable Energy Laboratory, 2024.
