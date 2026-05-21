# R126 verdict — Less obs-responsive LSTM = better policy (R96 design implication)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (N=2 same-hyper seed comparison, suggestive not confirmed)
**Type**: analysis (cached eval lookup, zero ANDES)
**Wall**: ~25 min

## TL;DR

R125 noted r72_w5_lstm_s55 has highest obs-responsiveness among 9 LSTM
ckpts (51.9%). R126 checks if that obs-responsiveness translates to
better policy: looked up cached 11-axis geo.

**Result: opposite. r72_w4 SOTA (less obs-responsive 41.4%) geo=0.391;
r72_w5 (more obs-responsive 51.9%) geo=0.317.** Same hyper (tau=0.001,
warmup=5, h=64), only seed differs (54 vs 55).

Reading: less h-locked at step 0 is NOT inherently better — the SOTA
learned to defer to accumulated h (history-integrative). R96 (Q-0022)
MLP h_init design should target SOTA's accumulated-h regime, not just
"saturation trigger".

Zero ANDES. Zero WSL.

## Methodology

Loaded:
- `results/r72_w4_lstm_tau001_warmup5_s54/training_log.json` (hyper)
- `results/r72_w5_lstm_tau001_warmup5_s55/training_log.json` (hyper)
- `results/research_loop/eval_v4_baseline/<ckpt>_summary.json` (geo)

## Results

| Ckpt | obs-only max | h-warm med | 11-axis geo |
|---|---|---|---|
| r72_w4_lstm_tau001_warmup5_s54 | 41.4% | ~99.6% | **0.391** (SOTA) |
| r72_w5_lstm_tau001_warmup5_s55 | **51.9%** | ~99.7% | **0.317** |

Δgeo = 0.391 - 0.317 = **0.074 = 19% relative loss**.
Δobs-responsive = 51.9 - 41.4 = +10.5 pp.

Hyper identical (tau=0.001, warmup=5, h=64, paper-faithful obs).
Only seed differs.

## R96 design revision

Original R107/R109: MLP h_init = `Linear(obs_dim, 32) → tanh →
Linear(32, hidden)`, random-initialised, learned via policy gradient.

Revised (post-R126): bootstrap MLP from SOTA's accumulated-h regime.
Concretely:

(a) **Initialisation bootstrap**: pre-compute `h_avg_sota` = mean
    LSTM hidden state across R72_w4 SOTA cached trajectory steps 10+
    (~ 320 samples). Initialise MLP heads so `h_init(obs_0) ≈
    h_avg_sota` for typical step-0 obs.

(b) **First-25-episode regulariser**: add loss `λ ||h_init(obs_0) -
    h_avg_sota||²` with λ decaying linearly to 0 over the first 25
    training episodes. This bootstraps from a known-good h regime
    before letting policy gradient explore.

(c) **No-op alternative (still valid)**: keep R107/R109 random-init
    design. If policy gradient finds a SOTA-like attractor, fine. If
    it falls into a r72_w5-like obs-driven attractor, the geo will
    expose it. R96 design (c) is the falsification path; designs
    (a)+(b) are the safer paths.

R96 launch can proceed with either path. Recommended order:
- First run: (c) plain random init (R109 as-is). If geo > 0.391,
  done.
- If first run is geo < 0.391: try (a) + (b) as R97.

## Decision

R96 launch surface unchanged from R109. R126 supplies a backup design
path (R97) if R96 first run underperforms.

## Infrastructure changes

不动: any code, V4, ckpt, test, R107/R109 artefacts.

新建:
- `memory/rounds/R126/{plan.md, verdict.md}`
- `memory/claims/CLM-0229.md`

## Cross-references

- CLM-0217 (R117 obs ascent universal) — figure data
- CLM-0225 (R125 paper figure)
- CLM-0188 (R104 warm-h_0 unlocks)
- CLM-0161 (R88 history integration steady-state)
- CLM-0229 (this round)

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0022** (warm-h_0 candidate) — design space now has fallback
  (R126) for case where plain random-init MLP doesn't find SOTA-like
  attractor.

## 给 PI 的话

**这周干了啥**：你说"一直干活". R125 figure 说 r72_w5 是 9 个 LSTM ckpts 里 obs-responsiveness 最高的 (51.9% vs SOTA 41.4%). 但 reviewer 问 "obs-responsive 高 = policy 好吗?" — 这个我没回答. R126 5 分钟 cached eval lookup.

**结果（一句话）**：**反直觉! r72_w5 (obs-responsive 51.9%) geo = 0.317; r72_w4 SOTA (obs-responsive 41.4%) geo = 0.391**. 同 hyper (tau=0.001/warmup=5/h=64), 只 seed 差 (54 vs 55). **更 obs-responsive 的 LSTM 反而 geo 差 19%**. 即 SOTA 学到的是更依赖 h 累积 history, 不是更 obs-responsive.

**意外**：这跟我 R125 figure 的 caption 解读相反 — figure 说"least h-locked" 看起来像好事, 数据说不是. 反过来又跟 R88 CLM-0161 (on-manifold critic 在 steady-state concave 但 transient bimodal) 一致 — policy 需要 **h 编码 trajectory history**, 不只是 h mediate 时间 lag. r72_w5 架构 OK 但训练时找到了次优 attractor.

**R96 design implication**: 原 R107/R109 设计是 random-init MLP h_init, 让 policy gradient 自己学. R126 提示可能要加 bootstrap — pre-compute `h_avg_sota` from R72_w4 cached trajectory 然后 regularise MLP `h_init(obs_0) ≈ h_avg_sota` 前 25 episodes. 这是 R97 design 候选 if R96 first run < 0.391.

**我默认下一步做**：(1) R126 关闭 closed-positive, CLM-0229 写入 (已完成). (2) **R96 launch surface 不变**: R109 random-init MLP 仍是 first try; 如果 first run fail, R97 = MLP bootstrap from SOTA h trajectories 是 backup design. (3) 继续 zero-conflict 离线: 下个 R127 候选 — **从 cached r80_v5_cross_eval LS1/LS2 trace 反推真实 step-0 obs vector** 跑 R104 grad-ascent 去掉 synthetic caveat (离线 30 min), 或 **整理 task list + 等 R94 释放 WSL** (任何时候). 沉默继续干.

**你想插一脚就说**：(a) 想我立刻 R127 真实 obs 反推 — 30 min 离线, 把 R86/R99/R104/R107/R117 都 caveat 一起去掉; (b) 想我把 R126 finding 加进 R125 figure 的 annotation (在 r72_w5 数据点旁边标 "geo=0.317" 在 r72_w4 标 "geo=0.391 SOTA") — 5 min; (c) 想我 wind-down 等 R94 — 任何时候说停. 我推荐 (默认) **(1)+(2)+(b)+(a)**: 先 5 min 把 R125 figure 加 geo annotation 让 paper-ready figure 更信息密集, 然后 R127 真实 obs 反推升级证据强度.
