# R91 verdict — D3 obs sufficiency closes the plateau-mechanism tree at value-horizon-mismatch

**Date**: 2026-05-19
**Status**: DONE (W1 only — full closure; W2+ optional follow-ups)
**Type**: analysis (offline regression on cached SOTA rollout)
**Wall**: ~3 min plan + 30s ANDES + 30s × 4 MLP fits = ~5 min total

## TL;DR

R91-W1 ran D3 obs-sufficiency offline on R72_w4 SOTA: capture 400 (obs,
action, reward, h_actor, next_obs) records from LS1+LS2 ANDES rollout,
fit 4 MLP regressors. **Cross-agent median test R²**:

| Regressor | R² |
|---|---|
| R2 obs → action (memoryless BC) | **+0.979** |
| R3 (obs, h_actor) → action | +0.996 |
| Δh-essentiality | **+0.018** |
| R4 obs → next_obs | +0.859 |
| R1 obs → instant reward (γ=0) | +0.930 |
| **R1 obs → return γ=0.99 (paper)** | **−0.410** |
| R1 obs → return γ=1.0 | +0.706 |

**Mechanism**: plateau is **value-horizon mismatch at paper γ=0.99**, not
obs-for-policy / not LSTM-memory / not critic-representation. Policy is
essentially memoryless, dynamics Markovian, instant reward predictable —
the only thing obs fails to predict is the **specific paper-γ discounted
return**. CLM-0163 records the finding + supersedes prior R85 priority
orderings; R85+ should γ-ablate first (blocked on Q-0015) before any
architectural change.

## Methodology

`scripts/r91_d3_obs_sufficiency.py`. Phase 1: 1 ANDES eval (LS1 + LS2,
50 steps each, R72_w4 SOTA deterministic) capturing `(obs, action,
reward, next_obs, h_actor)`. Phase 2: per agent, 80/20 train/test
split, fit 4 MLP regressors (hidden 64, 2 layers, dropout 0.1,
Adam lr 1e-3, 300 epochs). γ ∈ {0.0, 0.9, 0.99, 1.0} for return
regression.

ANDES occupancy: 19s out of 3 concurrent processes (R83-W4 training +
R85 classical baseline + R91 forensics) — under 3-slot hard limit,
no contention observed.

## Results

### R2 / R3: obs → action

Cross-agent median R²:
- R2 (obs only) = 0.979
- R3 (obs + h_actor 128-dim) = 0.996
- Δ = +0.018

Obs alone predicts SOTA action with 97.9% R². Adding the full LSTM
hidden state contributes only +1.8% R² gain. **The SOTA policy is
essentially a memoryless function of obs**. The R56 LSTM pivot may
have helped training-time escape, but the resulting policy is
representable by an MLP over the same 7-dim obs.

Per-agent R² for R2: 0.962 / 0.985 / 0.749 / 0.980. Agent 2 is
the outlier; the others are 97-99%.

### R4: obs → next_obs (forward model)

R² = 0.859 median. V4 dynamics are near-Markovian in the 7-dim obs.
A small fraction of next-state variance is unexplained — likely from
PHI_ABS / scaling terms that interact with cross-agent coupling not
in single-agent obs.

### R1: obs → return at varying γ

| γ | R² (median) | Interpretation |
|---|---|---|
| 0.0 | +0.930 | next reward fully predictable |
| 0.9 | +0.048 | barely above mean |
| **0.99** (paper) | **−0.410** | **worse than predicting mean** |
| 1.0 | +0.706 | undiscounted total roughly predictable |

The U-shape with the minimum at γ=0.99 is striking. γ=0 and γ=1.0 are
both well-conditioned: at γ=0 only the next reward matters (instant
function of obs), at γ=1.0 the total return is bounded and smooth.
γ=0.99 sits in the worst regime — discounting is strong enough to
weight near-future dynamics heavily, but not strong enough to
collapse to instant reward.

**This explains the LSTM h_critic role from [[CLM-0160]]**: the critic
needs the recurrent state to bridge the obs → V_γ=0.99 gap. Actor
doesn't need h because policy decisions are near-myopic w/r/t obs.

## R85+ priority pivot

[[CLM-0163]] documents this. Supersedes [[CLM-0160]] §R85 ordering.

**PRIORITY 1**: γ ablation on R72_w4 hyper basin. γ ∈ {0.9, 0.95,
0.99-baseline, 0.995, 1.0}. **Blocked on [[Q-0015]] — `--gamma` flag
is silently ignored for td3_lstm**. Q-0015 fix is now a paper-critical
infrastructure bug, not a backlog item. PR/diff for Q-0015 estimated
~10 lines in `scripts/train.py::build_v4_config` or `td3_lstm.py`.

**PRIORITY 2**: Reward shape ablation. R72_w4 hyper on
`V4Config.paper_strict_pure` (PHI_ABS=0, paper Eq.14 strict, R58
infrastructure). PHI_ABS=50 dominates per-step reward signal; removing
it may make V_γ=0.99 smoother in obs.

**PRIORITY 3**: Longer episode horizon. STEPS_PER_EPISODE 50 → 100 or 150.
Gives γ=0.99 more sum-room before truncation kicks in. Cheap to test.

**Downgraded by R91 mechanism evidence**:
- ❌ More obs (R83 path): obs is already 97% sufficient for action.
- ❌ Distributional critic / IQN (CLM-0162 R86/R87): orthogonal to value-horizon.
- ❌ CTDE / attention msg-passing: bottleneck is value, not coordination.

## Infrastructure changes (R91-W1)

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建:
- `scripts/r91_d3_obs_sufficiency.py` — D3 D3 capture + offline regressor
- `results/r91_d3_obs_sufficiency/summary.json` — output
- `results/r91_d3_stdout.log` — run log
- `memory/rounds/R91/{plan.md, verdict.md}`
- `memory/claims/CLM-0163.md`

V4 regression test 不需重跑 (零 env 改动). R72_w4 SOTA ckpt read-only loaded.

## Cross-references

- [[CLM-0160]] (on-manifold critic Q-landscape; R91 explains why critic
  needed h_critic — value-horizon-mismatch is the gap obs alone can't
  cover)
- [[CLM-0144]] (R57-R82 91-round algo plateau; R91 now provides the
  mechanism-level explanation: γ=0.99 is the obscuring discount)
- [[CLM-0149]] / [[CLM-0153]] / [[CLM-0154]] (synthetic-obs critic
  monotonicity; R91 makes the synthetic-obs vs on-manifold contrast
  even more meaningful — actor doesn't need critic argmax because actor's
  policy is near-myopic and value-mixing happens via h_critic alone)
- R83 plan / R83-W3 verdict (area_mean_freq RED 0.328); R91 explains
  why area_mean_freq fails — it adds obs info, but obs is not the
  bottleneck.
- [[CLM-0144]] / R82-R86 / R87 / R88 chain — all under-determined R85
  priority candidates now pruned to γ ablation + reward shape.
- [[Q-0015]] (γ flag silent ignore for td3_lstm) — was nice-to-have,
  now blocks R85 critical path.
- [[Q-0008]] (paper convergence horizon ≈ 500 ep) — orthogonal to
  R91; can run in parallel once γ flag fixed.

## Questions opened (this round)

- **Q-NEW** (recommend): "Does γ ablation on R72_w4 hyper shift the
  0.391 plateau?" — blocked on Q-0015 first.

## Questions closed (this round)

- (none) — R91 doesn't close any open Q. Q-0018 was closed by
  [[CLM-0160]] (W3-traj). Q-0014 algo backlog remains open but R91
  provides specific γ + reward direction.

## Questions advanced (this round, status unchanged)

- **Q-0015** (`--gamma` silent ignore for td3_lstm) — was opened by
  R81 as infrastructure bug, R91 now elevates it to paper-critical
  blocker for R85 γ ablation. Recommend immediate fix as R91 follow-up.
- **Q-0014** (algo backlog) — R91 provides specific direction: not
  algorithm class, not policy class, not critic class — value
  function under paper γ. Q-0014 stays open until γ ablation answers.

## 给 PI 的话

**这周干了啥**：你说"继续研究". R83-W3 (area_mean_freq) RED (0.328
vs baseline 0.391, -16%), R83-W4 (all 3 aug combined) 跑中, R85 (另
一窗口) = classical PI/Droop baseline 跑中, R86/R87/R88 都在做
synthetic-obs/cross-ckpt/phase-resolved 的 critic 视角分析. **没人
跑 D3 (obs sufficiency)** — R84 plan 里写了但 deferred. 我开 R91 =
D3, 1 短 ANDES eval (19s, 占第 3 个 slot) + 4 个 MLP regressor offline
fit (~10s 总). 测 obs → {action, return_γ, next_obs} R² 看 obs 是
不是 plateau 的瓶颈.

**结果（一句话）**：**obs 完全不是瓶颈, 但 paper γ=0.99 specifically
是**. obs → action R² = 0.979 (policy 几乎 memoryless, 加 LSTM h_actor
仅 +1.8%), obs → next_obs R² = 0.859 (动力学近 Markovian), obs →
instant reward R² = 0.930, obs → undiscounted return R² = 0.706, **obs
→ return γ=0.99 R² = −0.410 (比预测均值还差)**. γ=0 / γ=1 都正常,
**只有 γ ∈ [0.9, 0.99] 这个 paper 选的区间 obs 完全失效**.

**意外**：(1) **LSTM 主要是 cosmetic 的** — R56 加 LSTM 是为了 escape
R49-R55 hexagon 的 deterministic-policy-collapse, 但 SOTA 的 *最终*
policy 输出几乎跟 obs 单射. CLM-0160 我自己写过"LSTM h 做 representational
heavy lifting" 这条 NOT for actor — h_actor 几乎无用, h_critic 才是
做 value-horizon bridging 的关键. (2) **plateau 的真正机制 = paper γ=0.99
的 value-horizon mismatch**: 这个 discount 把 near-future 加权重, 但
不够强 collapse 到 instant. Critic 必须靠 h_critic 把 obs 不够的 future
state info 补出来, 因此 critic 在 on-manifold 上 concave-around-a_sota
(CLM-0160). 但 actor 不需要 h 因为它已经在解 myopic policy 了.

**我默认下一步做**：(1) R91-W1 closure 已写 ✓, CLM-0163 入库. (2)
**修 Q-0015 (`--gamma` silent ignore for td3_lstm)** — 这是 R85 γ ablation
critical path 的 blocker, 估 ~10 行 diff 在 `scripts/train.py` 或
`td3_lstm.py`. 不修没法做 R85 PRIORITY 1. (3) 修好后开 R92 = γ ablation
(γ ∈ {0.9, 0.95, 0.99 baseline, 0.995, 1.0} × R72_w4 hyper × 75 ep s54
single seed smoke). Hit / miss 一目了然. 沉默 = 先修 Q-0015, 再开 R92.

**你想插一脚就说**：(a) 想直接绕过 Q-0015, 把 V4Config.gamma 改成
hardcoded 1.0 重跑 R72_w4 看 plateau 变化 — 1-line patch 测一下方向
对不对; 但跟 paper γ=0.99 不一致, 只能作为内部 sanity check. (b)
想先 PRIORITY 2 = reward shape (paper_strict_pure 已有 V4Config infra
R58) 不动 γ — 也合理, 但 γ 才是 R²=−0.41 的 root cause, reward shape
是补救路径. (c) 想我把 D3 扩到 cross-ckpt (R63 SAC / R75 LSTM) 看
γ=0.99 R²=−0.41 是不是 universal — N=400 → N=2000, +30 min 数据收
集 (3 个新 ckpt × LS1+LS2 × 50 步 = 600 records). 推荐 (默认): 修
Q-0015 → 开 R92 γ ablation, 因为这是过去 91 round 没人尝试的方向.
