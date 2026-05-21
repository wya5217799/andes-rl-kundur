# R104 verdict — Warm-h_0 architectural slack UNIVERSAL (9/9 ckpts)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (Q-0022 promoted to unconditional R96)
**Type**: analysis (frozen-weight grad-ascent, zero ANDES)
**Wall**: ~50 min (25 min code + ~10 min compute + 15 min write)

## TL;DR

R99 / CLM-0183 confirmed Q-0022's architectural premise on R72_w4 SOTA
(N=1 ckpt). R104 extends to N=9 ckpts × 4 agents = 36 LSTM critics:
R58 / R62 / R72 rounds, 7 seeds, hidden=64 + 128.

**UNIVERSAL_FEASIBLE: 9/9 ckpts pass the feasibility gate** (norm_lift
> 50 pp AND ΔQ_abs > 0).

Cross-ckpt median: norm_zero=8.5% of max → norm_star=95.6% of max
(+86.8 pp lift). ΔQ_abs always positive (+0.005 to +0.065 range).

Q-0022 architectural premise NOT R72_w4-specific. R96 (Q-0022
implementation) promoted to **unconditional** — no longer gated on
R94 widen-bound outcome.

Zero ANDES. Zero WSL. Zero conflict.

## Methodology

100 synthetic step-0-like obs (||obs||=0.25, random direction, CLM-0161
matched) × 9 ckpts × 4 agents. For each (ckpt, agent):
1. Baseline: ||a||, Q at h=c=0
2. Grad-ascent (Adam, lr=0.05, 500 steps) over (h_0, c_0) ∈ ℝ^hidden
3. Final: ||a||, Q at h_0*, c_0*
4. Record absolute ΔQ (no relative % outliers from |Q_zero|→0)

Critic Q = min(Q1, Q2) at critic h_critic=0 (TD3 target convention,
matches R86/R99). Both LSTM heads frozen during ascent.

Algo support: only TD3-LSTM (non-recurrent has no h). SAC and TD3-MLP
ckpts NOT in this round's scope.

## Results

### Per-ckpt feasibility (all PASS)

| Ckpt | seeds×agents | norm 0% range | norm * range | ΔQ_abs med | feasible |
|---|---|---|---|---|---|
| r72_w4_lstm_s54 | 4 | 5.7-19.5% | 99.2-99.7% | +0.041 | ✅ |
| r58_lstm_s49 | 4 | 2.3-8.7% | 87-97% | +0.017 | ✅ |
| r58_lstm_s50 | 4 | 6.5-11.5% | 72-97% | +0.016 | ✅ |
| r58_lstm_s51 | 4 | 5.0-11.0% | 71-98% | +0.009 | ✅ |
| r62_lstm_h128_s51 | 4 | 7-12% | **99.8-99.9%** | +0.045 | ✅ |
| r72_w1_lstm_s51 | 4 | 5.3-9.1% | 78-99% | +0.019 | ✅ |
| r72_w2_lstm_s50 | 4 | 6.4-11.0% | 85-97% | +0.007 | ✅ |
| r72_w3_lstm_s52 | 4 | 1.7-9.6% | 71-96% | +0.009 | ✅ |
| r72_w5_lstm_s55 | 4 | 6.3-17.8% | 90-99.7% | +0.042 | ✅ |

### Cross-ckpt aggregate (median across 36 critics)

- norm_zero: **8.5%** of max (universally under-saturated)
- norm_star: **95.6%** of max (universally reachable)
- norm_lift: **+86.8 percentage points**
- ΔQ_abs: **+0.017** (always sign-positive)
- feasibility gate: **9/9 = 100% PASS**

### Notable observations

1. **h=128 (r62) outperforms h=64 ckpts** in norm_star (99.8-99.9%
   vs 71-99%) AND uses smaller ||h*|| (~10 vs ~25-37). Higher-capacity
   LSTMs distribute the saturation-triggering hidden activation across
   more dimensions, easier to encode in a small h_init MLP.

2. **All 36 agents have ΔQ_abs > 0**. Strict universality — not a single
   case where the LSTM weights forbid step-0 saturation.

3. **The R99 +254% rel% outlier reproduces** (r58_s50 ag3 +190%,
   r62 ag0 +407%, r72_w5 ag0 +176%) because some agents have
   |Q_zero| < 0.05. The absolute ΔQ_abs is the robust statistic. CSV
   `per_agent_table.csv` carries both.

4. **Some agents only reach norm_star = 71-72%** (r58_s51 ag1/ag2,
   r58_s50 ag2, r72_w3 ag3). These are still huge lifts from 5-11%
   baseline. The variance reflects asymmetric LSTM weight matrices —
   some directions in h-space saturate the action faster than others.

## Decision

**R96 = Q-0022 implementation promoted to unconditional next round
when WSL slot frees**:

- Implementation: `RecurrentActor.__init__` adds two MLPs:
  ```
  self.h_init = nn.Sequential(nn.Linear(obs_dim, 32), nn.Tanh(),
                              nn.Linear(32, hidden))
  self.c_init = nn.Sequential(nn.Linear(obs_dim, 32), nn.Tanh(),
                              nn.Linear(32, hidden))
  ```
- `forward` first-step-of-episode (controlled by caller flag) uses
  `(h_init(obs_0), c_init(obs_0))` instead of zeros.
- ~15-line diff; 2 small MLPs ≈ 4K extra params (vs 60K LSTM).
- Gate: 1 seed × 75 ep R72_w4 hyper × paper-faithful obs. Expected
  ||a||_step_0 lift from 0.15 → 0.7+ (worst case; 1.0 ≈ saturation
  unrealistic for learned MLP first try).

The architectural premise is now confirmed across 36 LSTM critics —
the only remaining unknown is whether a learnable MLP from obs_0 to
h_0 can capture the optimal h* found by grad-ascent (vs a constant
warm h_0 which is a weaker baseline).

## Infrastructure changes

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / R57+ ckpt / R94 in-flight training data / any test.

新建:
- `scripts/r104_warm_h0_multickpt.py`
- `results/r104_warm_h0_multickpt/{summary.json, per_agent_table.csv}`
- `memory/rounds/R104/{plan.md, verdict.md}`
- `memory/claims/CLM-0188.md`

## Cross-references

- CLM-0183 (R99 N=1 feasibility) — R104 upgrades to N=9 ckpts
- CLM-0174 (R95 LSTM warm-up lag) — mechanism universalised
- CLM-0170 (R92 bang-bang saturation) — independent ceiling mechanism
- CLM-0175 (R94 prediction) — R104 decouples Q-0022 from R94
- CLM-0155 (R86 cross-ckpt monotone) — sibling universality result
- Q-0022 — premise upgraded from N=1 to N=9
- CLM-0188 (this round)

## Questions opened (this round)

- (none) — R104 confirms an existing premise

## Questions closed (this round)

- (none) — Q-0022 stays `open` until R96 verifies a learnable MLP
  captures the optimal h*

## Questions advanced (this round, status unchanged)

- **Q-0022** — premise universalised (R99 N=1 → R104 N=9). Log entry
  added.

## 给 PI 的话

**这周干了啥**：你说"一直干活, 别让我提醒你". 我把 R99 / CLM-0183 (R72_w4 SOTA N=1 ckpt warm-h_0 feasibility) 扩到 9 个 LSTM ckpt: R58 (3 seeds) + R62 h=128 + R72 wave (w1/w2/w3/w4/w5). 36 个 LSTM critic instance, 每个跑 500 步 grad-ascent on (h_0, c_0) maximise critic Q. 还加了 absolute ΔQ reporting 解决 R99 agent 1 +254% rel% outlier (|Q_zero|=0.02 division 不稳).

**结果（一句话）**：**UNIVERSAL_FEASIBLE 9/9 ckpts**. Cross-ckpt median norm_zero=**8.5%** of max → norm_star=**95.6%** of max, lift **+86.8 percentage points**. ΔQ_abs 永远 sign-positive (range +0.005 到 +0.065 across ckpts). h=128 ckpt (r62) 表现最好 (norm_star 99.8-99.9% + 最小 ||h*||=10), 跟"高 capacity LSTM 更容易 encode warm h_0" 一致. R86's "synthetic-obs monotone universal" 跟 R104's "warm-h_0 architectural slack universal" 是 paper-faithful 7-dim obs 训练 regime 的孪生 fingerprint.

**意外**：r62_h128 norm_star 几乎到 100%, 而且 ||h*|| 只需 10 (vs h=64 的 25-37). 这告诉我 R96 实施时, 不一定要训练完整 h_dim 的 h_init MLP, 用 h=64 baseline + LayerNorm 可能就够 — 或者 h=128 capacity 直接被 paper 不接受 (用 7-dim obs + h=128 像 over-parameterised), 那 R96 走 h=64 但 h_init head 加 LayerNorm + scaled tanh 让输出 norm 落在 20-35 范围 (覆盖 grad-ascent argmax). 这是 implementation 细节, R96 跑出来 1 seed 就知道.

**我默认下一步做**：(1) R104 关闭 closed-positive, CLM-0188 写入 (已完成). (2) R96 = Q-0022 implementation 仍等 R94 verdict + WSL 释放, 但 R104 已经把"unconditional" 标签贴上 — 不论 R94 outcome, R96 都开. (3) 继续 zero-conflict 离线: 下个候选可能是 **R105 = 把 grad-ascent 推广到 cached trajectory 全 50 步** (per-step architectural slack curve, 看 slack 是否在 steady-state 消失), 或者 **R106 = 用 r80_v5_cross_eval 的 cached LS1 traces 反推真实 step-0 obs**, 去掉 synthetic caveat. 沉默就继续干.

**你想插一脚就说**：(a) 想我立刻把 R96 networks.py 的 patch (warm-h_0 MLP 加到 RecurrentActor) 写成 separate file 不动 networks.py — 我可以新建 `src/.../agents/networks_warmh0.py + RecurrentActorWarmH0(nn.Module)`, R96 训练 import 这个, 不影响 R83/R87/R94 进行中训练; (b) 想我继续 R105 per-step slack curve — 离线 10 分钟, 输出一张图显示 slack 在 step 5 后 < 10 pp; (c) 想我 R106 真实 obs 反推 — 离线 30 分钟, 去掉 synthetic caveat 给 CLM-0188 升级 V-trust 无 caveat; (d) 想我把 R88+R95+R99+R104 整合成 paper Sec.IV-D mechanism story 草稿 — 现在有 5 段 quantitative claim 链, paper 立论最完整. 我推荐 (默认) **(1)+(2)+(a)+(b): R104 关掉, 写 warm-h_0 MLP separate file 准备 drop-in (零风险), 然后 R105 per-step slack curve. 等 R94 我就在那里**.
