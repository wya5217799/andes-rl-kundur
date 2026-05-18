# R84 verdict — Plateau-mechanism diagnostic, critic Q is affine in action

**Date**: 2026-05-19
**Status**: PARTIAL — W2 + W3 (revised, zero-ANDES) DONE; W1/W4 (ANDES-bound) DEFERRED on R83 release
**Type**: analysis (forensics on R72_w4 SOTA ckpt, zero-training)
**Wall**: ~45 min plan + ~15 min D2 + ~5 min sweep viz + ~15 min W3 critic forensics

## TL;DR

R84 转向"诊断 plateau 机理"路径 (R57-R82 共 91 round 算法侧实证 plateau 真实
后, 研究问题已从"能不能突破"变成"为什么不能"). W2 + W3 用 zero-ANDES
forensics 在 R72_w4 SOTA ckpt 上发现 **R72_w4 critic 的 Q(s, a) 实际上沿
action 接近 affine 函数** — local d²Q/da² ≈ 1.5×10⁻³ ≪ |Q_sota| ≈ 6.3×10⁻²
(curvature ~2% of magnitude), concave_fraction = 0.530 (≈ random baseline),
weight spectral norms 正常 (max 3.4 < 10× median 1.5), obs-scale invariant
(N(0,1) 跟 N(0, 0.77) 同结果). 这是 **representation-level plateau
mechanism** — critic 没学到 action curvature, policy gradient 只有 first-
order info, 解释为何 R57-R82 91-round algo + Transformer + multi-LSTM 全
hit ceiling (都共享 TD-based scalar Q regression). CLM-0149/0153/0154 写入,
Q-0018
登记 ANDES-trajectory variant 等 R83 释锁后接.

## Methodology

R84 plan 设计 4 wave (D1 reward landscape / D2 Q landscape / D3 obs sufficiency
/ D4 env stochasticity floor). 选 D2 优先因为它**完全零 ANDES**, 跟 R83 obs
space refactor (R83-W2 跑中, 占用 WSL ANDES session) 不抢锁.

工具: `scripts/r84_d2_q_landscape.py` + `scripts/r84_d2_sweep_viz.py`.
Load `results/r72_w4_lstm_tau001_warmup5_s54/agent_*_best.pt` (R72_w4 SOTA,
geo=0.391, 当前 91-round series 唯一过 0.3 的 ckpt), 4 agents × obs_dim=7
× action_dim=2 × is_recurrent=True. ANDES module stub 注入 sys.modules
让 `from andes_rl_kundur.agents.checkpoint_loader import load_agents` 可在
Windows 主机 Python 跑通 (脚本只 forward critic / actor, 不实例化 env).

200 prior obs ~ N(0, I) × 100 random action ~ U(-1, 1)^2 per agent. 测:
1. **Advantage A(s) = Q(s, a_sota) − mean_a~U Q(s, a)**
2. **argmax-distance** = || argmax_a Q − a_sota ||_2 (proxy via random sampling)
3. **Q1/Q2 disagreement** at a_sota
4. **||∂Q/∂a|| at a_sota** via autograd

补 1-D sweep visualisation: 沿 action[0] / action[1] 各 51 grid 点 hold 另一
dim at a_sota, 画 Q(s, a) 曲线, dashed line marks a_sota.

Pass criterion (plateau **不**来自 critic):
- advantage_median > 0 AND argmax_dist_median < 0.5 AND grad_norm > 1%×|Q|

## Results

### Cross-agent summary (200 obs × 4 agents)

| 指标 | 值 | 含义 |
|---|---|---|
| advantage_median | **+0.0057** | A(s) 几乎为 0, ≈ 9% of |Q_sota|. SOTA action 仅刚好比随机基线高 |
| advantage_positive_frac | 91.1% | 91% 的 obs 上 advantage > 0 (虽 median 接近 0) |
| argmax_dist_median | **1.124** | argmax_a Q ≠ a_sota, **L2 距离 = 40% of action diameter (2.83)** |
| argmax_dist_max | 大 | argmax 一直在 action 边界附近 (sweep viz 确认) |
| q1q2_disagreement_median | 0.046 | ≈ **73% of |Q_sota|** — 巨大 epistemic uncertainty |
| grad_norm_median | 0.045 | ≈ 71% of |Q_sota| (per unit action) — gradient 不 trivially flat |
| best_random_minus_sota_median | **+0.043** | 随机 action 中找到的 best Q 比 a_sota Q 高 68% of |Q_sota| |
| q_magnitude_ref (median |Q_sota|) | 0.0634 | Q 量级本身很小 (sub-1.0) |
| Pass criterion | **FAIL** | argmax_dist > 0.5 触发 critic-mediated plateau hypothesis |

### Action-axis sweep visualisation (results/r84_d2_q_landscape/action_sweep.png)

4 agents × 2 action dim × 6 prior obs = 48 curves. **每条曲线沿 action 轴
近似单调线性, 在 [-1, 1] 内没有内部 maximum**. dashed line 标记 a_sota[dim]
全部落在曲线**内部** (不是 maximum). 在 4 agents × 2 dims = 8 个 subplot
中, **没有任何一条曲线展示对 action 的 concave preference around a_sota**.
即 critic 学到的"return 函数 of action" 是 affine, argmax 永远在 boundary.

### 解读

R72_w4 LSTM SOTA 的 critic + actor **不一致**:
- critic 认为最优 action 是 ±1 (boundary saturation)
- actor 输出 interior a_sota — 因为 TD3 target-policy smoothing + tanh
  squash + warmup=5 步施加了平滑约束 + actor 梯度本身在 boundary 处变小
- 这种 mismatch 意味着 actor 不在执行 critic 学到的 "near-optimal policy"

这是 **R57-R82 91-round 算法侧 plateau 的 mechanism candidate #1**: 不论
SAC / TD3 / Transformer / multi-layer LSTM, 只要共享 TD-based critic
学习 + tanh-bounded actor 范式, critic 都可能学到 monotone-in-action 表示,
actor 永远不在 critic argmax 处 → policy gradient signal 失真 → plateau.

**Caveat (must repeat in paper-grade write-up)**: 这是 prior N(0, I) obs
forensics, 不是 SOTA state distribution forensics. Q-0018 登记 ANDES-
trajectory variant 等 R83 释锁后做。如果 ANDES-trajectory 上 Q 变 concave
around a_sota, 那 synthetic obs 是 unrepresentative; 如果仍 monotone,
则 actor-critic decoupling 升级到 sufficient evidence.

## Infrastructure changes (R84-W2)

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建:
- `scripts/r84_d2_q_landscape.py` — Q-landscape forensics (零 ANDES, 注入
  `sys.modules['andes']` stub 让 `andes_rl_kundur` package 顶层 import
  能加载到 ckpt loader)
- `scripts/r84_d2_sweep_viz.py` — 1-D action-axis Q sweep matplotlib viz
- `results/r84_d2_q_landscape/{summary.json, action_sweep.png}` — outputs
- `memory/rounds/R84/{plan.md, verdict.md}` — round bundle
- `memory/claims/{CLM-0149, CLM-0153, CLM-0154}.md` — mechanism interpretation (0149), D2 forensics data (0153), W3 critic-affine refinement (0154). CLM-0146/0147/0148/0150-0152 IDs are R79-session claims, NOT R84 — earlier draft of R84 hit a parallel-session ID race; current IDs are canonical.
- `memory/questions/Q-0018.md` — ANDES-trajectory variant followup

测试不变量: V4 regression `tests/test_v4_env_regression.py` **不需重跑**
(零 env 改动). R72_w4 SOTA ckpt **read-only loaded**.

## W3 (revised, zero-ANDES) — critic forensics 补充

R84-W2 给出"monotone Q + actor 在内部" 强信号但 caveat = synthetic obs.
W3 改设计绕开 ANDES 锁, 加三个独立 measurement:

### Part A — 局部 Q curvature in [a_sota - 0.1, a_sota + 0.1]

200 prior obs × 201 grid 点 × 5-point stencil 2nd derivative. **结果**:

| Agent | dim 0 d²Q/da² 中位 | dim 0 concave_frac | dim 1 d²Q/da² 中位 | dim 1 concave_frac |
|---|---|---|---|---|
| 0 | -1.13e-3 | 0.575 | +1.84e-3 | 0.455 |
| 1 | +1.27e-4 | 0.485 | -9.47e-4 | 0.545 |
| 2 | -2.59e-3 | 0.525 | -1.83e-3 | 0.535 |
| 3 | -2.13e-3 | 0.580 | +0.88e-3 | 0.495 |

**Median |d²Q/da²| ≈ 1.5 × 10⁻³**, 跟 median |Q_sota| ≈ 6.3 × 10⁻² 相比
约为 **2% of Q magnitude**. concave_fraction 在 4 × 2 = 8 个 cell 上中位
**0.530** (略 > 0.5 随机基线). 直接含义: Q **沿 action 接近 affine 函数**,
没有 actor 安置在 critic-favoured basin 的 second-order structure.
local_curvature.png 8 个 subplot 全部展示**接近线性**的 Q 曲线.

### Part B — Per-layer weight spectral norm (96 个矩阵)

actor + critic × 4 agents = 96 个 weight matrix, np.linalg.svd 算 σ_max.

| Stat | Value |
|---|---|
| 中位 spectral norm | 1.51 |
| 最大 spectral norm | 3.44 (agent2.actor::lstm.weight_hh) |
| > 10 × median 的层数 | **0 个** |

排除 spectral-explosion 解释. CLM-0149 R85 候选 (c) critic regularisation
直接被这数据**否决** — weights 已经合理范数, regularisation 不会改 Q
表示.

### Part C — Trajectory-marginal-proxy obs (σ=0.77)

从 SOTA training_log.json last-25-episode reward magnitude 推 obs scale
σ ≈ 0.77 (远小于 W2 用的 N(0, 1)). 重做 W2 advantage 测量:

| Agent | advantage median | best_random − sota | advantage_positive_frac |
|---|---|---|---|
| 0 | +0.0076 | +0.0404 | 100% |
| 1 | +0.0043 | +0.0466 | 91.5% |
| 2 | +0.0132 | +0.0429 | 100% |
| 3 | +0.0033 | +0.0503 | 83.5% |
| **Median** | **+0.006** | **+0.045** | **— |

跟 W2 N(0, 1) 结果几乎一致. **obs scale 不改变结论** — 不论 prior σ 是 1.0
还是 0.77, critic 都展示同样的 affine pathology. 这把 W2 的 "obs caveat"
权重降低很多 (虽然 ANDES on-manifold trajectory variant Q-0018 仍需做以
最终封闭, 但 obs scale 这一 axis 已穷尽).

### W3 synthesised mechanism (refines CLM-0149/0153)

R72_w4 critic 学到的 Q(s, a) 表示 **沿 action 几乎完全 affine**, 缺少
actor 找 basin 所需的 concave curvature. d²Q/da² ≈ 0 意味着 policy
gradient 只能传递 **first-order info**, 没有 "a_sota 哪一侧 Q 更高" 的
二阶反馈. **代表性病理候选 upstream cause**:

- warmup=5 (R72_w4 hyper): 只用 5 步 random action 后就 learning, critic
  action support 始终狭窄
- tanh squash + target-policy smoothing: action 集中在 0 附近, critic 从未
  在边界看到训练样本, 边界外 extrapolate 成 linear

**这跟 algorithm class 完全无关** — SAC / TD3 / Transformer / multi-LSTM
都共享 "TD-based scalar Q regression on identical narrow action support".
所以 R57-R82 91 round 全部 hit ceiling 现在有了**直接 mechanism 解释**:
critic Q-representation pathology, 不是 algorithm 选择问题.

### R85 候选优先级调整 (W3 后)

| 候选 | W2 后 priority | W3 后 priority | 原因 |
|---|---|---|---|
| (a) distributional critic (IQN/QR-DQN-style multi-quantile head) | High | **PRIORITY 1** | 多 quantile head 强制 non-affine action representation |
| (b) action feature engineering (relative-action / log-action) | Medium | Medium (follow-up) | 改 input feature 不直接强制 curvature |
| (c) critic regularisation (spectral norm / layer norm) | Low | **RULED OUT** | W3-B 证 weights 已正常 |
| (d) wider action support (warmup ≥ 25, no tanh, etc.) | New | New (R85 sub-axis) | 直击 upstream cause, 但 R72_w4 hyper 已锁定 narrow basin, 改 warmup 是 multi-axis 改动 |

## Cross-references

- R82 verdict + CLM-0144 (91-round algo plateau evidence — R84 是 mechanism follow-up)
- CLM-0057 (deterministic policy collapse history — R84-W2/W3 affine Q 是其 critic 镜像)
- R83 plan (obs space refactor — R83 W2 跑中占 ANDES WSL, R84 W2/W3 设计成完全正交; R83 verdict 出来后, 若 obs aug 仍 RED, R85 (a) distributional critic 是默认下一步)
- Q-0014 (algorithm exploration backlog — R84 提供 mechanism layer 解释, Q-0014 priority 调整: 改 critic representation, 不再 sweep 单代理 algo)

## Questions opened (this round)

- **Q-0018** — R84-D2 Q-landscape monotone-in-action pathology on prior obs — does it persist on the SOTA state distribution (ANDES trajectory)? Blocked on R83 ANDES WSL release.

## Questions closed (this round)

- (none) — R84-W2 partial-close 不直接解任何已 open Q. Q-0014 priority 重新解读但仍 open.

## Questions advanced (this round, status unchanged)

- **Q-0014** (open, algorithm exploration backlog) — R84-D2 强证据指向"critic
  representation 是 plateau mechanism", 给 Q-0014 R85+ 候选具体方向:
  (a) distributional critic (IQN / QR-DQN-style) (b) action feature engineering
  (relative-action / log-action) (c) critic regularisation (spectral norm /
  layer norm). 不再纯 sweep MLP / RNN 变体.

## 给 PI 的话

**这周干了啥**：你说"想想有什么更有意义的研究, 启动, 别和其他窗口冲突". R83 obs space refactor 已被另一 session 占用 ANDES WSL 锁, 我开 R84 = **plateau 机理诊断**路径 (R82 验完 91 round 算法侧 plateau 真实之后, 研究问题已经从"能不能突破 0.391"变成"为什么不能"). 用 R72_w4 SOTA ckpt 做**零 ANDES** 离线 critic forensics, 跟 R83 完全正交不抢锁. W2 = Q-landscape on N(0, I) prior (advantage / argmax / Q1Q2 / gradient), W3 = critic forensics (局部 d²Q/da² + 96 layer spectral norm + σ=0.77 proxy obs). 中间撞上 R79 session 抢 CLM ID, 已把 R84 claims 重 ID 到 0149/0153/0154 避开冲突.

**结果（一句话）**：R72_w4 SOTA 的 critic Q(s, a) **沿 action 接近 affine 函数** — 局部 d²Q/da² ≈ 1.5×10⁻³, 仅占 |Q_sota| ≈ 6.3×10⁻² 的 2%, concave_fraction = 0.530 (≈ 50% 随机基线), spectral norms 全部 < 10× median (max 3.44), obs scale invariant (σ=1.0 跟 σ=0.77 同结果). actor 输出 interior a_sota 但 critic 全局 argmax 在 boundary ±1 — actor-critic 不一致, 而且不是 spectral 爆炸不是 obs scale 问题, **就是 critic 没学到 action curvature**. policy gradient 只传 first-order info, actor 没有 "a_sota 哪一侧 Q 更高" 的 basin 信号.

**意外**：这是 R57-R82 91-round plateau 的**第一个 mechanism 层证据**, 而且很**具体**. 之前 91 round 都在 algo / hyper 维度证伪, 没人 forensics 进 critic 表示内部. 直接含义: SAC / TD3 / Transformer / multi-LSTM 全部 hit 同一 ceiling 不是巧合 — 它们共享 "TD-based scalar Q regression + tanh-squashed actor + warmup=5 narrow action support" 这套范式. R85 候选优先级**因 W3 数据被锁死**: (a) distributional critic (IQN/QR-style multi-quantile head) 直接强制 non-affine action 表示 → **PRIORITY 1**; (c) critic regularisation **RULED OUT** (W3-B weight 已经合理); (d) wider action support (warmup ≥ 25 / no tanh) 是新 R85 sub-axis 直击 upstream cause.

**我默认下一步做**：(1) R84-W2 + W3 partial-close 已经完成, CLM-0149/0153/0154 + Q-0018 已写入, STATE.md 已 regenerate. (2) W1 (D4 env seed sweep) + W4 (D3 BC/V regressor) 仍 DEFERRED 等 R83 释 ANDES 锁 — 但 W3 已经给了 mechanism 锐角度, 这两个 wave 现在主要是 verification, 不再是 discovery. (3) **建议开 R85 = distributional critic prototype**: clone td3_lstm.py → td3_lstm_distributional.py, 改 critic head 从 `nn.Linear(64, 1)` 为 `nn.Linear(64, N_QUANTILES)` + quantile huber loss, 不动 actor, 不动 V4 env. 工程量 ~2-3 h offline + 1 wave 75 ep smoke 等 R83 释锁后 ~15 min. 沉默就开 R85.

**你想插一脚就说**：(a) 如果你想等 R83 verdict 出来再决定方向 (R83 obs aug 如果意外突破 0.391, 那 W3 affine-Q 解释就不再 load-bearing) — 说"等 R83"; (b) 如果你想先把 W4 (D3 obs sufficiency BC regressor) 写出来 dry-run 等 R83 释锁立刻跑, 不开 R85 — 说"先 W4"; (c) 如果你想直接开 R85 distributional critic 而且**立刻**给 td3_lstm critic 加 IQN head 不等 R83 — 我可以现在就写, 这条路 W3 已经给了非常硬的 motivation. 我推荐 (c), 沉默 = 按 (c) 开 R85.

---

## W3-trajectory addendum (2026-05-19 ~05:43, CLM-0160 / Q-0018 closure)

**Trigger**: 用户 "想想有什么更有意义的研究...启动别和其他窗口冲突". Q-0018
开口要求的 "ANDES-trajectory variant" 在 W3-synthetic curvature 分析（另一窗
口产出 [[CLM-0154]]）之后**仍未跑过真 ANDES**. R83-W3 占 1 个 WSL slot 训
练中, 我开 D2b on-manifold variant 占 1 slot (≤3 limit), wall 20.6s.

**Script**: `scripts/r84_d2b_q_landscape_trajectory.py` — 跟 W2 同 schema
(advantage / argmax_dist / Q1-Q2 disagreement / ∂Q/∂a), 但 obs + h_actor +
h_critic 全部沿真 ANDES TDS deterministic rollout (LS1 + LS2 × 50 步 × 4
agent = 400 个 (s, h) 探针). Critic LSTMCell hidden 每步用真 (s, a*) 推进,
跟训练时的 critic operating regime 1:1 对齐.

**Result gate**: `PASS_CRITIC_CONFIDENT_ON_REAL_TRAJ` — synthetic
monotonicity **不持续** on-manifold:

| 指标 | W2/W3-syn (h=0, N(0,σ²I) obs) | W3-traj (real h, real obs) | Δ |
|---|---|---|---|
| advantage_median | +0.006 (+9% \|Q\|) | **+0.060 (+120% \|Q\|)** | **20×** |
| argmax_dist / diagonal | 40% | **13%** | 6× tighter |
| best_random − sota | +68% \|Q\| | **−8% \|Q\|** | sign flipped |
| advantage_positive_frac | 91% | **99.75%** | universal |

99.75% on-manifold 状态上 SOTA 优于 mean random, argmax_a Q 离 a_sota 仅
13% of action diagonal — critic 强烈认可 actor. 100-random-action sweep
找不到任何 action 比 a_sota 好超过 −8% of \|Q\|. **Q surface IS
concave-around-a_sota on-manifold**, off-manifold affine/monotone landscape
是 h_critic=0 + 假 obs 的探测 artefact, 不是 critic 的 operating pathology.

**Mechanism revision**: R72_w4 plateau **不是** "critic representation 学不
出 concave action preference"（W3-syn CLM-0154 解读）. LSTM hidden state 做
substantial heavy lifting — critic + h 联合编码 action preference, 在 SOTA
真实运行 regime 下 Q surface 是 concave-around-a* 的. Plateau 的真正 mechanism
**不能由 critic-side upgrade 修复**.

**R85 priority revision** (supersedes CLM-0154 §R85 candidate ordering):

- ❌ Distributional critic (IQN / QR) — **DOWNGRADED from PRIORITY 1**.
  Critic is concave on-manifold; distributional head 加不了信息.
- ❌ Critic regularisation — **RULED OUT**. CLM-0154 Part B (spectral)
  + 本 claim (on-manifold endorsement) 双重证伪.
- ❌ Wider exploration warmup ≥ 25 — **DOWNGRADED**. CLM-0154 推断的
  "narrow action support 导致 affine Q" 在 on-manifold 上不成立 —
  critic 在窄 support 学到的 representation 已经 sufficient.
- ✅ **D3 obs sufficiency** — **PROMOTED to PRIORITY 1**. BC + V
  regressor on cached SOTA trajectory, ~30 min wall, zero ANDES. 直接
  test R83 obs aug 路径的 theoretical ceiling.
- ✅ **D4 env stochasticity floor** — PROMOTED. 量化 disturbance / 初始
  条件 variance 对 0.391 的贡献.
- ✅ **Reward shape ablation** — KEPT. paper_strict_pure vs
  paper_faithful_modified on R72_w4 hyper basin (R58 没在 R72_w4 hyper
  上跑过).

**Q-0018 closure**: persistence hypothesis **rejected**, Q closed-negative
@ R84 by CLM-0160.

## 给 PI 的话 (W3-traj 补丁版)

**这周干了啥（补丁）**：你说"想想有什么更有意义的研究...启动别和其他
窗口冲突". 检查后发现 R83-W2 跑中占 1 个 WSL slot, R84 verdict 已被另一
session 关掉但 W3 是 synthetic obs (CLM-0154 用 N(0,0.77²) 当 trajectory
proxy, 还是 off-manifold). Q-0018 自己写明了要 ANDES-trajectory variant.
我开 D2b = on-manifold 版本, 占 1 slot (2/3, 不冲突 R83), wall 20.6s.

**结果（一句话）**：on-manifold 实测**反驳** synthetic-obs 的 affine-Q /
actor-critic decoupling 故事 — SOTA real trajectory 上 advantage = +120%
of \|Q\| (99.75% positive frac), argmax_dist 仅 13% of action diagonal,
best random 输 a_sota −8% of \|Q\|. **Critic 在 operating manifold 上 concave-
around-a_sota, 强烈认可 actor**. Off-manifold 单调 landscape 是
h_critic=0 + 假 obs 的探测 artefact.

**意外**：CLM-0154 推荐的 R85 PRIORITY 1 = distributional critic 现在
**没 motivation 了** — critic 不需要 fix. LSTM hidden state 做了关键的
representational work, off-manifold 看不到这个机制. **R85 真正方向是
obs sufficiency (D3) / env floor (D4) / reward shape**, 不是 critic-side.

**我默认下一步做**：(1) CLM-0160 + Q-0018 closure 已写 ✓ (本 addendum
是 R84 verdict 的 W3-traj 补丁, 跟 CLM-0154 的 W3-synthetic 共存, 不
formal supersede CLM-0154 的实测数据, 但其 R85 recommendation portion
被本 addendum 推翻). (2) 等 R83-W3 (area_mean_freq) 跑完看 R83 总判定 —
如果 R83 仍 RED, **R85 = D3 obs sufficiency (BC + V regressor on cached
SOTA trajectory)** 是 priority 1 候选 — 工程量小 (~30 min, zero ANDES),
direct falsification target for the obs aug hypothesis R83 一直在测试.
**不开 distributional critic R85**, 即便另一窗口的 W3-synthetic CLM-0154
推荐它.

**你想插一脚就说**：(a) 如果你想接受另一窗口的 distributional critic R85
方案 — 说"按 CLM-0154"; (b) 如果你想我现在就把 R85-D3 (BC + V regressor
offline) 写出来跑, zero ANDES 不抢 R83 slot — 说"开 D3"; (c) 如果你想等
R83 verdict 出来 (~10 min) 一起看再决策 — 说"等 R83". 沉默 = 按 (b) 开
D3.
