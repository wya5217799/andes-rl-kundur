# R88 verdict — Phase-breakdown reconciles synthetic vs on-manifold critic forensics

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (mechanism candidate narrowed to transient-phase critic data starvation)
**Type**: analysis (mines cached on-manifold per_step.json, zero ANDES)
**Wall**: ~55 min total (10 min compute + 45 min write)

## TL;DR

R86 (CLM-0155, synthetic-obs cross-ckpt, h_critic=0) found 6/6 ckpts have
monotone-Q in action ⇒ proposed "universal critic representation pathology"
(CLM-0157 R87 priority = action feature engineering / IQN). CLM-0160
(R84-W3-traj on-manifold) refuted this: SOTA critic IS concave on real
ANDES trajectory (advantage +120% of |Q|).

R88-W1 mines the 400-record cached on-manifold per_step.json for
per-step / per-phase breakdown. **On-manifold concavity is BIMODAL**:
step 0-2 (disturbance immediate) has **100% bad-argmax fraction** + only
+14% of |Q| advantage; step ≥ 10 (steady-state) has **2.5% bad-argmax**
+ +131% of |Q| advantage. The critic is competent only after the
transient settles.

New mechanism candidate for the R57-R82 91-round 0.391 plateau (CLM-0144):
**transient-phase critic data starvation**. 6-axis paper-grade metric
is dominated by step 0-5 max_df / dD_smooth / settling proxies — but
critic gets only 6% of training samples from that regime, so it's
under-trained where it most matters.

CLM-0162 supersedes CLM-0157 (action feature engineering withdrawn).
Q-0020 opens transient-replay-reweighting as R87+ candidate priority 1.
Q-0019 (distributional critic) deprioritised but stays open.

Zero ANDES. Zero WSL. Zero conflict with R83/R85/R87.

## Methodology

R84-W3-traj (run earlier in another session, CLM-0160) saved
`results/r84_d2b_q_landscape_trajectory/per_step.json` with 400 records:
4 agents × 2 scenarios (LS1, LS2) × 50 steps. Each record has 11 numeric
fields: scenario, step, agent, obs_norm, sota_action, grad_norm,
q_sota_mean, q_rand_mean, q_rand_max, argmax_dist, q1q2_disagreement,
best_random_minus_sota, advantage.

R88-W1 aggregates by:
1. per agent (4 partitions, 100 records each)
2. per scenario (2 partitions, 200 records each)
3. **per phase** (transient step 0-2, transient step 0-4, transient
   step 0-9, steady step ≥ 10, very late step ≥ 40)

Phase split at step 10 chosen visually from per-step curves (advantage
asymptotes by step 10, argmax_dist drops below 0.20 by step 10).

Output: `results/r84_d2b_q_landscape_trajectory/per_step_phase_breakdown.json`
(50-entry per-step aggregate, sidecar to existing per_step.json).

## Results

### Phase breakdown (the key finding)

| Phase | n | adv_med | adv % of |Q| | argmax_dist | % with dist > 0.5 |
|---|---|---|---|---|---|
| step 0-2 (disturbance immediate) | 24 | +0.014 | **+14%** | **0.913** | **100%** |
| step 0-4 (early transient) | 40 | +0.022 | +20% | 0.779 | 87.5% |
| step 0-9 (transient) | 80 | +0.037 | +34% | 0.455 | 53% |
| step 10+ (steady-state) | 320 | +0.061 | +131% | 0.158 | **2.5%** |
| step 40+ (very late) | 80 | +0.061 | +135% | 0.149 | similar |

**Step 0-2 argmax_dist 0.913** is comparable to R84-W2 synthetic-obs 1.12
and not to steady-state 0.158. The critic at the disturbance moment is
as confused as off-manifold synthetic. q1q2_disagreement also elevated
in transient. Q_sota magnitude is 2× larger in early steps (|Q| ≈ 0.10)
than steady (|Q| ≈ 0.05) — the value function **knows** early disturbance
is high-stake, but doesn't know what action to take.

### Per-step trajectory (8 samples per step, 4 agents × 2 scen)

| step | adv_med | argmax_dist |
|---|---|---|
| 0 | +0.008 | **1.067** |
| 1 | +0.012 | 0.794 |
| 2 | +0.023 | 0.853 |
| 5 | +0.042 | 0.358 |
| 10 | +0.058 | 0.094 |
| 20 | +0.062 | 0.153 |
| 49 | +0.061 | 0.151 |

Crossover at step ~5: confidence climbs from off-manifold-like to
steady-state-confident. Step 10 is the first "fully recovered" step.

### Three-way reconciliation

| Probe regime | Verdict | Interpretation |
|---|---|---|
| Synthetic N(0, I), h_critic=0 (R84-W2, R86 6/6) | Monotone, boundary argmax | Off-manifold artefact, REAL but doesn't matter |
| Real ANDES traj, all 50 steps averaged (CLM-0160) | Concave, +120% of \|Q\| | TRUE on average, hides asymmetry |
| Real ANDES traj, **per phase** (CLM-0161, this round) | Bimodal: confused 0-2, confident 10+ | **Actionable mechanism candidate** |

R86's finding (6/6 ckpts monotone synthetic) was empirically valid but
its interpretation as "universal critic representation pathology" was
overreach. The synthetic-obs probe stresses regimes the critic never
sees in training; failure there is necessary control but not sufficient
mechanism evidence.

## Decision (CLM-0162 supersedes CLM-0157)

R87+ priority order revised:

1. **Transient-phase replay reweighting** (new PRIORITY 1) — Q-0020.
   Importance-weighted replay buffer with `w(t) = max(1, 5 × (1 - t/5))`
   so step 0-4 get 5×, step 5 gets 1×. Single-knob, 1-file diff in
   TD3 buffer sampling. 1 seed × 75 ep R72_w4 hyper. ~30 min WSL.
2. **D3 obs sufficiency** (CLM-0160-promoted) — kept. BC + V regressor
   on cached SOTA trajectory; check if obs+h_critic at step 0-2 is
   information-sufficient for ε-optimal action.
3. **Curriculum / 2-stage** — alternative form of transient replay.

WITHDRAWN (per CLM-0162):
- Distributional critic (Q-0019, deprioritised but kept open)
- Action feature engineering [a, a², |a|, sign(a)]
- Critic spectral normalisation
- Wider exploration warmup

## Infrastructure changes (R88)

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / any R57+ ckpt / R84 / R86 scripts / any test / any
existing claim except CLM-0157 (auto-superseded via validate.py --fix).

新建:
- `results/r84_d2b_q_landscape_trajectory/per_step_phase_breakdown.json`
- `memory/rounds/R88/{plan.md, verdict.md}`
- `memory/claims/{CLM-0161, CLM-0162}.md`
- `memory/questions/Q-0020.md`

测试不变量: V4 regression 不需重跑. 所有现存数据 read-only.

## Cross-references

- CLM-0160 (R84-W3-traj on-manifold) — parent, what made R88 possible
- CLM-0155/0156 (R86 cross-ckpt synthetic) — stand as empirical findings, interpretation revised
- CLM-0157 — superseded by CLM-0162 (validate.py auto-wrote back-edge)
- CLM-0149/0153/0154 (R84 series) — superseded in interpretation by CLM-0160 (R87 session's
  work, not strictly by R88)
- CLM-0144 (91-round algo plateau) — new mechanism candidate proposed (transient data starvation)
- Q-0014 — narrowed again: not algo class, not critic rep, → transient replay weighting
- Q-0018 — closed-negative per CLM-0160 (need to verify in R84 verdict — that's another session's work)
- Q-0019 — open, deprioritised (distributional critic — log note added)
- Q-0020 — opened (transient replay reweighting candidate)
- R83 plan (obs-space training) — orthogonal, may yield independent fix
- R85 plan (classical baseline) — orthogonal

## Questions opened (this round)

- **Q-0020** — Does transient-phase replay reweighting (×2-5 weight on
  step 0-5 samples) break the 0.391 plateau on R72_w4 hyper? Single-knob,
  cheap, falsifiable, directly motivated by CLM-0161 phase-bimodality.

## Questions closed (this round)

- (none from this round directly; Q-0018 closure noted in CLM-0160 by
  R87 session)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog) — narrowed further.
  CLM-0157's "critic representation" interpretation was wrong;
  CLM-0162's "transient replay reweighting" is the new candidate.
  Q-0014 will close positive iff Q-0020 result is geo > 0.45.
- **Q-0019** (distributional critic) — deprioritised. Critic concave
  on-manifold (CLM-0160) — adding distributional head doesn't
  motivate against this evidence. Stays open as a contingency.

## 给 PI 的话

**这周干了啥**：你说"继续研究". 看 STATE 发现另一 session 跑了 R84-W3-traj 写 CLM-0160 — 直接 refute 我 R86 的 mechanism 解释 (synthetic-obs monotone 是 LSTM h_critic=0 + N(0,I) 的 artefact, 真实 ANDES 轨迹上 critic 是 concave 的, advantage +120% of |Q|). 我没去硬撑 R86 解释, 而是 pivot — 挖另一 session 留在磁盘上的 `per_step.json` (400 records = 4 agents × 2 scen × 50 steps), 做 per-step / per-phase 拆分.

**结果（一句话）**：on-manifold concavity 是 **bimodal in 时间相位**. step 0-2 (扰动 immediate) 24/24 = **100% argmax_dist > 0.5** (跟 off-manifold synthetic 一样混乱), advantage 仅 +14% of |Q|; step ≥ 10 (steady-state) 320 个 sample 仅 **2.5%** bad-argmax, advantage +131% of |Q|. 即 critic **在扰动瞬间是混乱的, 只在稳态时合格**. 这就是 R57-R82 91-round plateau 的最干净 mechanism candidate: **transient phase critic data starvation** — 50 步 episode 里只有 ~6% sample 来自 step 0-2, 但 6-axis metric 主要被 step 0-5 的 max_df / dD_smooth / settling 决定, 算法在最关键的地方训练数据最少.

**意外**：CLM-0160 的 overall median 把这层结构完全遮住. 平均下来 critic 概念性 endorses 99.75% sample, 但你把 step 0-2 单独拆出来 advantage_positive_frac 还是 95.8% 但 argmax_dist 飙到 0.913 — critic 知道 a_sota 比平均随机好, 但 100 个随机 action 里能找出一个比 a_sota 还好 +0.040 ≈ 40% of |Q|. **这是 actor 在 transient phase 没在 critic argmax 处** — R84 actor-critic decoupling 假设的"小幅修正版" 在 transient phase 复活.

**我默认下一步做**：(1) R88 关闭 closed-positive, CLM-0161/0162 + Q-0020 写入 (已完成), CLM-0157 已 auto-supersede 为 CLM-0162. (2) **不开 R89** — Q-0020 (transient replay reweighting × 5 step 0-4 samples) 需要 WSL ANDES, 等 R83 verdict / WSL 释放. (3) 等 R83 verdict 出来:
   - 如果 R83 obs aug 突破 0.391 → R88 mechanism candidate 不需要 test, Q-0020 标 closed-negative-by-orthogonal
   - 如果 R83 RED → 立刻开 R89 W1 = Q-0020 transient replay reweighting, 1 文件 diff 在 TD3 replay buffer sampling, 75 ep 单 seed, ~30 min WSL
. 沉默就这么做.

**你想插一脚就说**：(a) 想立刻并行起 R89 transient replay (不等 R83) — 我可以, 但需要 WSL slot, 你 ack 一下 3-slot 限制 (R83 1 个 + R85 1 个 + R89 1 个 = 3, 刚好); (b) 想我把 R88 phase-breakdown 当成 paper section IV-D 写出来 — 可以, 现在有 quantitative claim: "critic confidence is bimodal in episode phase, 100% bad-argmax at step 0-2 vs 2.5% at step 10+, plateau mechanism = transient-phase data starvation"; (c) 想我再扩 R88 — 比如把 SOTA trajectory 再跑 1 次但每 5 个 step 注一次 random action, 看 critic 怎么 update — 需要 WSL; (d) 觉得 phase-bimodality 还不够稳, 想再确认: 我可以挖 per_step.json 的 advantage histogram 看是不是 R88 step 0-2 的 100% 是 long-tail 还是 bulk — 离线 5 分钟可加. 我推荐 (默认) **(1)+(2): 等 R83 决定 R89 是否需要**.
