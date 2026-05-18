# R86 plan — Cross-ckpt replication of R84 critic-monotone-Q pathology

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI confirmed "想想有什么更有意义的研究...启动". R84-W2 在单一 R72_w4 ckpt 上发现 critic 在 action 轴单调 + argmax 在 boundary 的 actor-critic decoupling pathology (CLM-0148/0149), 但 N=1 ckpt 不足以下"R57-R82 91-round plateau 的 mechanism layer 证据"这种 universal claim. R86 测同 mechanism 在多个算法 (SAC / TD3-MLP / TD3-LSTM) × 多 seed 上是否复现.
**Parent**: R84 verdict CLM-0148/0149 ("critic-monotone-in-action on R72_w4 SOTA")

## TL;DR

R86 跑 6 个 ckpt × 4 agent = 24 critic forensics, 测 R84-D2 同 4 个指标
(advantage / argmax_dist / Q1Q2_disagreement / grad_norm) + monotone-Q
检验. **零 ANDES**, 跟 R83 (obs space training, WSL 锁占用) + R85 (classical
PI/Droop baseline) 完全正交. Wall ~10 min compute, ~15 min coding.

**两侧都 paper-publishable**:
- 6/6 ckpt 都 monotone → R84 mechanism 是 **TD-based critic + tanh actor
  范式的 universal pathology**, R87+ 应改 critic 表示 (distributional /
  spectral norm / action feature engineering) 而非 algorithm class
- ≤2/6 ckpt monotone → R72_w4 SOTA 的 critic monotone 是**单 ckpt 现象**
  (可能是 hyperparam-induced overfit), R84 不能 generalise, mechanism
  还要继续找

## R84 立论 + R86 falsification target

**R84-D2 claim (CLM-0148)**: R72_w4 SOTA 4 agents × 200 prior obs 上,
critic Q(s, a) 沿 action 轴**近似单调线性**, argmax_a Q 永远在 boundary
±1, actor 输出 interior a_sota — actor-critic decoupling 一案.

**R84-D2 limit**: N=1 ckpt (R72_w4_lstm_s54). Could be:
- (a) seed 54 specific lottery (R49-α / R57-α 等没复现 0.391, R72_w4 是
  R57+ 91 round 唯一 ckpt 过 0.3, possibly basin-of-attraction outlier)
- (b) td3_lstm class specific (LSTMCell + h0=zeros 可能学到平凡 critic)
- (c) td3+tanh-actor universal (target-policy smoothing + tanh squash 共
  同导致 critic 不 concave around interior policy)
- (d) general TD-based critic 在 7-dim paper-faithful obs 下普遍现象

R86 用 cross-algo cross-seed sample 区分这 4 个 hypothesis.

## Ckpt set (6 ckpts, all obs=7)

| Ckpt | Algo | Hidden | Seed | Source round | Role |
|---|---|---|---|---|---|
| r72_w4_lstm_tau001_warmup5_s54 | td3_lstm | 64 | 54 | R72 SOTA | Anchor (R84-D2 reproducer) |
| r58_paper_strict_pure_td3_lstm_s49 | td3_lstm | 64 | 49 | R58 sweep | Same algo, diff seed |
| r58_paper_strict_pure_td3_lstm_s50 | td3_lstm | 64 | 50 | R58 sweep | Same algo, diff seed |
| r58_paper_strict_pure_td3_s49 | td3 | 64 | 49 | R58 sweep | Same family no LSTM |
| r58_paper_strict_pure_sac_s49 | sac | 64 | 49 | R58 sweep | Different algo class |
| r63_w4_td3_combo_s49 | td3 | 64 | 49 | R63 hyper combo | Diff round/hyper TD3 |

Coverage: 3 algos × 2-3 seeds per algo (SAC 1 ckpt because R86 just needs
"does it happen?" not "how often per algo").

## Forensics design (mirrors R84-D2 + adds explicit monotone test)

Per ckpt × 4 agent × 200 prior obs ~ N(0, I) × 100 random action ~ U(-1, 1)^2:

1. **Advantage** A(s) = Q(s, a_sota) − mean_a Q(s, a)
2. **argmax_dist** = ||argmax_random_a Q − a_sota||_2
3. **Q1/Q2 disagreement** at a_sota
4. **||∂Q/∂a||** at a_sota (autograd)
5. **NEW: monotone-fraction** — sweep action[d] ∈ [-1, 1] (51 grid) for
   each obs × dim, compute sign changes of dQ/d(action[d]). Define
   `monotone(s, d) := |sign_changes| ≤ 1`. Report fraction of (obs, dim)
   pairs where curve is monotone. **This is the explicit R84 hypothesis
   test** — R84 sweep viz only had 8 subplots (4 agent × 2 dim × prior
   obs samples), not aggregate %.

Pass criterion (this ckpt's critic is **healthy**, plateau NOT critic):
```
advantage_median > 0  AND
argmax_dist_median < 0.5  AND
grad_norm_median > 1% × |Q_sota|  AND
monotone_fraction < 0.5   # less than half of (obs, dim) curves are monotone
```

## Algo-fork in script

- SAC / TD3 (non-recurrent): `critic(obs, action)` returns `(q1, q2)` — no
  hidden state
- TD3-LSTM: `critic(obs, action, h0)` returns `(q1, q2, _h_next)`

R86 script branches via `agent.is_recurrent`. Single h0=zeros for
recurrent critics (R84-D2 convention, same as eval inference at episode
start).

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | (this file) plan.md + ckpt set selection | done |
| **W2** | Write `scripts/r86_qlandscape_multickpt.py` (extends r84_d2 to multi-ckpt loop + adds monotone-fraction stat) | ~25 min |
| **W3** | Run on 6 ckpt × 4 agent, generate per-ckpt sweep PNG + aggregate summary.json | ~10 min compute |
| **W4** | Verdict + CLM-0150 (per-ckpt monotone count) + CLM-0151 (R84 universality verdict) + Q-0019 (next mechanism step) + render | ~30 min |

Total wall ~75 min, **zero ANDES**.

## 资源冲突 gate

- R83 (obs space training): WSL ANDES lock 上, train.py 全力跑. R86 是
  Windows 主 Python forensics on read-only ckpts, **0 WSL 进程**. ✅
- R85 (classical PI/Droop baseline): 计划用 ANDES eval. R86 不 eval, 不
  ANDES, **不抢 ckpt locks** (read-only `.pt`). ✅
- R86 输出 namespace: `results/r86_qlandscape_multickpt/`
- R86 写代码: 仅新建 `scripts/r86_qlandscape_multickpt.py`. **0 mutation 在 src/**

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ / scripts/train.py /
任何 R57+ ckpt / scripts/r84_d2_q_landscape.py / scripts/r84_d2_sweep_viz.py /
any test.

新建: `scripts/r86_qlandscape_multickpt.py`, `results/r86_qlandscape_multickpt/`
output dir, `memory/rounds/R86/{plan.md, verdict.md}`,
`memory/claims/CLM-0150+`, optionally `memory/questions/Q-0019.md`.

## 测试不变量

- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (0 env 改动)
- R57+ SOTA ckpt 完全不读写 / 只 `torch.load` weights_only=True
- R84 outputs (`results/r84_d2_q_landscape/`) 完全不动

## Cross-references

- R84 verdict (CLM-0148/0149) — R86 是其 N=1 → N=6 univeralisation test
- R57-R82 91-round plateau (CLM-0144) — R86 给 mechanism layer 多 ckpt 证据
- R85 classical baseline plan — orthogonal, 不互阻
- R83 obs space plan — orthogonal, 不互阻
- ADR-0001 (src layout) / ADR-0002 (V4 SSOT)
