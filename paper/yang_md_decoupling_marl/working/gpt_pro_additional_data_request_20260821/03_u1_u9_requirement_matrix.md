# U1–U9：仍缺数据、最小补证与结论升级矩阵

## 总表

| U | 当前数学状态 | 项目级仍缺数据 | 最小可接受补证 | 完整补证后可升级到 |
|---|---|---|---|---|
| U1 | conic formulation 与不可识别性已成立 | Object B 全模型、DCF/SLS、lift、active mode、primal/dual | 完整模型 + 一个命名类 + 独立证书 checker | QY10 类在冻结线性 bank 上的可行 witness或类内不可行证书 |
| U2 | 设计与可识别 estimand 已给出 | 新 18-cell outcomes、独立 donor、paired seeds、预算/收敛数据 | 至少一个预注册预算、足够独立 seeds、held-out bank | 算法/架构/预算/finite-bank 特定的 semantic message effect |
| U3 | 增广 MDP 与 aliasing 反例成立 | 项目实际逐步 trace；历史 replay 若要定量偏差 | projector/replay/target parity trace | 证明当前实现 Bellman 一致；历史偏差仅在原 replay 可得时定量 |
| U4 | 当前 surrogate 不包含 exact guard set 的反例成立 | raw train cost、raw endpoint traces、exact guard、命名类 phase-I | 对 finite 350 或 U1 类 exact max-violation | 指定类和固定 bank 上存在/不存在 guard-clean witness |
| U5 | total derivative 恒等式成立 | 完整 A/B/C/D、equilibrium/controller/headroom/reference derivatives、全频 loop | `rho±h,±h/2` 模型导出与 direct FD | 冻结模型上的 total local sensitivity 与误差审计 |
| U6 | 0–0.2 s endpoint bracket 成立 | continuous/ZOH plant、controller、full poles；fractional nonlinear points | `tau=0.1 s` 性能点；完整 model 才能做 pole crossing | finite-bank endpoint bracket；或 nominal local delay margin |
| U7 | fixed-mode zero-bias 下 `O(eps^2)` 条件命题成立 | mixed tensors、amplitude sweep、mode trace、additive lift | `eps,eps/2,eps/4` 与 mode/residual | 冻结 equilibrium 的局部二阶 scaling 与 additive 一阶通道对照 |
| U8 | 一般上界与反例成立 | reduced A/B/C/D、I/O projector、Toeplitz lift、conditioning；可信 state projector | finite-window I/O lift + resolvent conditioning | 每 profile 的数值 cross bound/实际值及其条件性 |
| U9 | branch 解释和 finite-bank 边界成立 | R458 正式 outcome、selection/eval隔离证明 | 按冻结 runner 完成 R458 | 一条 schedule 在 K/4 固定 eval profiles 的 transfer witness |

---

## U1 — 最容易被误写的关键数据

必须额外确认：

1. QY10 的 `||Q||≤1` 是在何种 I/O normalization 下；
2. `T_d` 的行正交性和 `Q_h=T_d^T Qhat_h T_d` 映射；
3. DCF 与 plant/controller 使用同一反馈符号；
4. 角度 gauge/neutral mode 是否已去除；
5. reference denominator 是否对 `q` 固定且严格正；
6. Object B 的 guard denominator 是否重新计算；
7. saturation 是哪一种编码；
8. 对偶变量是否恢复到未缩放原始问题；
9. positive lower bound 是否大于数值误差与 nonlinear discrepancy allowance。

缺任一项，都不能写“类可行/不可行”。

---

## U2 — 数据越多也无法自动证明的部分

有限训练数据观测的是：

```text
finite-budget outcome = population class optimum + optimization/estimation gap
```

因此必须同时保存预算/学习曲线。若 `N-P` 在预算变化时明显变化，应分类为 `optimization-unresolved`，不能写 intrinsic value。即使所有 seeds 都支持 N，也只能写“在该算法、预算和 bank 下真实语义消息优于保边际 placebo”。

建议三层证据：

- **最低**：一个预算、预注册 primary contrast；
- **较强**：几何 budget sweep + paired seeds；
- **最强但仍非 global**：多 restart、plateau、best-achieved upper bound和独立 lower-bound surrogate。

---

## U3 — 历史数据可得性分支

### 若 R431 replay buffer存在

需要原始：`obs,raw_action,executed_action/reconstructible previous action,reward,next_obs,done`。可逐 transition 比较 historical target 与 corrected target，并报告 target discrepancy distribution。

### 若只有 checkpoints

可在冻结 state bank 上重新评估 raw-vs-executed target差，但这只是 retrospective diagnostic。输出必须写：

```text
historical_training_bias_exact = false
reason = original replay transitions unavailable
```

### 若 current repaired trace通过

只能证明当前 implementation contract 一致，不能自动洗白历史 R431/R451。

---

## U4 — 可行性结论的对象必须命名

推荐两条路径：

1. **350 schedules**：完全枚举，结论是 finite-family × finite-bank；
2. **QY10**：convex/MI-conic certificate，结论是 named linear controller class × finite bank。

不要尝试用 neural policy 的局部 phase-I训练失败证明 class infeasible。对于 neural class，只能交付 witness 或 optimizer failure。

---

## U5 — 完整 total derivative 中必须出现的链

```text
rho
 -> equilibrium x*(rho), y*(rho)
 -> DAE Jacobians and input/output maps
 -> Schur reduction
 -> continuous A/B/C/D
 -> ZOH sampled A/B/C/D
 -> controller/headroom realization
 -> closed-loop G
 -> candidate/reference energies
 -> ratio
```

任何只导出 `dA/dρ` 的结果仍是 partial attribution。状态坐标变化会重新分配 A/B/C terms，必须同时给 total derivative 和物理端口 counterfactual。

---

## U6 — 三种 margin 数据不能混用

| 目标 | 必需数据 | 不能替代它的数据 |
|---|---|---|
| nonlinear endpoint crossing | fractional runtime points、相同 bank、active mode | 局部 loop singular value |
| nominal local stability delay margin | full closed-loop realization、所有 pole branches | 0.3–0.5 Hz 的 41 点 |
| robust stability margin | 结构化 uncertainty set + full-frequency robust test | 5.38% scalar endpoint seam |

若只补 `tau=0.1 s`，只能收窄 endpoint bracket，不能升级为稳定裕度。

---

## U7 — 数值 `O(eps^2)` 的真实性条件

必须同步记录：

- policy equilibrium bias；
- active mode；
- DAE residual；
- trajectory是否留在同一局部 tube；
- fixed horizon；
- controlled-minus-zero-action 使用同一 disturbance/initial state；
- action amplitude与slew实际执行值，而非 raw target。

支持性数据应显示：

```text
MD: ||Δy||/eps -> 0
MD: ||Δy||/eps^2 -> finite/stable
additive port: ||Δy||/eps -> finite nonzero
```

若 mode 切换，正确结论是“Taylor scaling 不适用”，不是机制被反驳。

---

## U8 — full-state projector 是潜在最大陷阱

102 维状态不等同于四个频率坐标。若无法按设备名称、对称群或已验证 coordinate map 构造完整 `P_x`，不要把四维 `P_c/P_d` 直接填充成任意 102×102 projector。

可优先交付不依赖 full-state projector 的结果：

1. exact finite-window common-input → differential-output lift；
2. I/O transfer cross block；
3. reduced swing `Z_dd,S_c,z_dc`；
4. resolvent/Schur conditioning。

只有 `P_x^2=P_x`、rank/basis/physical meaning 均通过核验后，才报告 commutator数值。

---

## U9 — 选择隔离需要“行为证据”

仅在代码里写“select只读dev”仍不够。至少保存：

- select进程的 input inventory；
- selection文件在 eval 开始前的 hash/timestamp；
- eval阶段使用同一 winner的校验；
- dev/eval目录访问隔离或 file-open audit；
- 无 eval-informed rerun/threshold drift的声明与日志。

R458 完成后仍只能报告 `K of 4 fixed profiles`。概率结论必须来自另一个明确抽样设计。
