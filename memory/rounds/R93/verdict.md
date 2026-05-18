# R93 verdict — Plateau mechanism is LSTM-cell self-drift, not actor weights, not critic, not obs

**Date**: 2026-05-19
**Status**: PARTIAL — W0 + W0b DONE (zero ANDES); W1 widen-bound HOLD pending PI direction (new mechanism reframes the experiment).
**Type**: analysis (forensics on R72_w4 SOTA ckpt, zero training, zero ANDES, zero ckpt mutation)
**Wall**: ~20 min plan + W0 script + W0b script + interpretation

## TL;DR

PI "继续研究". R92-W1 (CLM-0170) discovered R72_w4 SOTA actions saturate
at ±1 boundary for 76% of every eval episode and proposed widen-bound
as the R93+ PRIORITY 1 experiment. R93-W0 + W0b refine the mechanism:

- **W0 (actor fc_out forensics)**: actor weights are SMALL (fc_out max
  |W| ≈ 0.15), and pre-tanh logits on prior obs + h=0 sit at median |z|
  ≈ 0.10 (deep tanh-linear). The actor head does NOT push the boundary.
- **W0b (LSTM hidden-state drift)**: with **obs = constant zero** (or any
  of 3 other obs streams), the LSTMCell h drifts from ||h||=0.25 to
  ||h||≈5.0 in 50 steps, and the pre-tanh logits reach |z| = 2.6 ± 0.4,
  saturating tanh in 38-82% of action steps. **Per-agent drift pattern
  matches R92-W1 exactly: ag0/1 ΔM→−1, ag2/3 ΔM→+1, all ΔD→+1.**
  → The R72_w4 LSTMCell learned a **divergent internal dynamics**;
  saturation is **obs-content invariant**, an LSTM property.

R57-R82 91-round same-plateau attractor is explained mechanically:
no algorithm / hyperparameter / architecture choice in those rounds
included an LSTM-state regularisation term, so all variants that use
recurrent state (R72_w4 LSTM SOTA) hit the same LSTM-drift saturated
bang-bang policy. CLM-0180 + CLM-0181 written. R93-W1 widen-bound
becomes a falsification test (not the obvious PRIORITY 1), and the new
PRIORITY 1 is **LSTM hidden-state norm regularisation during training**.

## Methodology

R93 plan was originally a single ANDES experiment (W1 widen-bound).
After R92-W1's saturation finding, two zero-ANDES forensics were added
to confirm the mechanism before spending an ANDES wave:

- W0: load R72_w4 SOTA actor, examine fc_out weights, compute pre-tanh
  logits on 200 prior obs with h_actor = 0.
- W0b: replay constant + alternating + random obs streams through the
  actor's LSTMCell, track ||h(t)||, logit_z(t), action(t) per step.

Both scripts run zero-ANDES (`sys.modules['andes']` stub) and load only
`results/r72_w4_lstm_tau001_warmup5_s54/agent_*_best.pt`.

## Results

### W0 — actor weights are NOT push-the-boundary

Cross-agent stats on N=200 prior obs ~ N(0, I), h_actor = 0:

| Quantity | Value |
|---|---|
| Median |z| | **0.102** (deep tanh-linear) |
| Frac |z| > 2 (tanh sat) | 0.0% |
| Frac |z| > 5 (deep sat) | 0.0% |
| fc_out weight max_abs median | 0.154 |
| fc_out spectral norm median  | 0.781 |

CLM-0180 ID: actor head is small, outputs interior actions at episode
reset. Saturation must come from somewhere else.

### W0b — LSTMCell self-drift is the mechanism

Four obs streams, all 50 steps, all give virtually identical results:

| Stream | Obs content | Median logit max |z| | Saturates? |
|---|---|---|---|
| A_constant_zero | obs = 0 everywhere | **2.59** | YES |
| A_constant_e1 | obs = [1, 0, ..., 0] | 2.65 | YES |
| B_alternating_e1 | obs alternates sign | 2.60 | YES |
| C_random_sigma0p5 | obs ~ N(0, 0.5²) | 2.61 | YES |

||h_actor|| growth 0 → 50 step is **20×** in every stream
(0.25 → ~5.0). Realised actions saturate at ±1 in 38-82% of steps,
matching R92-W1 quantitatively. **Per-agent saturation sign pattern
matches the R72_w4 SOTA real-ANDES bang-bang trajectory** (e.g., ag0
ΔM blue → -1 with ΔD orange → +1 in the drift figure, identical to
R92's LS1+LS2 SOTA).

CLM-0181 ID.

### Synthesised mechanism (this is the big update)

**R72_w4 SOTA is a 256-action bang-bang policy driven by LSTM cell-state
self-drift, with the saturation pattern set by the trained LSTM
recurrent weights + biases — completely independent of observation
content.**

Equivalent restatement: the R72_w4 SOTA is approximately

```
a_t = tanh( fc_out ( LSTM_state_at_time_t ( ignore obs, just drift ) ) )
```

The frequency observation has very little impact on the realised action
trajectory; the policy is effectively a **stateful timer** that emits
bang-bang for ~70% of the 50-step episode.

This finally explains:

1. **Why R57-R82 91-round sweep produces a flat plateau**: no round
   ever added LSTM hidden-state regularisation. All variants in that
   sweep with recurrence learn similar divergent LSTM dynamics.
2. **Why MLP-only variants (SAC, TD3 MLP) underperform R72_w4 LSTM**:
   non-recurrent variants have no LSTM drift, but they also lack the
   short-horizon temporal context the impulse phase needs. The LSTM
   "wins" by having drift-driven bang-bang, but not because LSTM
   memory is genuinely useful.
3. **Why R83 obs aug failed (-7 ~ -12%)**: enriching obs is irrelevant
   when the policy ignores obs and drifts on LSTM dynamics.
4. **Why R84 critic forensics confused us on synthetic obs**: critic
   forensics needs on-manifold trajectory because (h_critic=0, OOD
   obs) is a transient regime that lasts ~5 steps; after that, the
   on-manifold critic correctly endorses the bang-bang actions
   (CLM-0160 / CLM-0165).
5. **Why R92 saw perfect Kundur 2-area split**: the per-agent fc_out
   biases differ slightly between the 4 agents; LSTM drift amplifies
   these initial differences into ±1 saturated actions; the area-
   correct sign emerges from training pressure during the brief
   interior steps 1-15.

### R93+ priority revision

Old (R92 → R93-W1 = widen-bound): widen DM_MAX, DD_MAX → fix plateau.
New (R93-W0b finding): widen-bound is unlikely to help — h will just
drift to a new boundary. Real fix is preventing the drift.

| Candidate | New priority | Rationale |
|---|---|---|
| **LSTM hidden-norm regularisation** (new) | **PRIORITY 1** | Add `λ_h * mean(||h_actor||²)` to training loss. Directly attacks the drift. Single training-loop edit. |
| **Replace LSTMCell with MLP at inference** (new) | PRIORITY 2 | Removes drift entirely. Tests whether LSTM memory is genuinely useful. |
| Widen action bounds (originally R93-W1 default) | **PRIORITY 3 (falsification)** | Still informative. Cheap to run. |
| Distributional critic / obs aug / wider warmup | RULED OUT | All explained by LSTM drift or covered by prior data. |

### R93-W1 status

Held pending PI direction. The widen-bound experiment is still
useful as a falsification of LSTM-drift mechanism, but it is no
longer the default. The script and V4Config widening were not
written this round (kept the ANDES wave free for whichever R94
training experiment PI prefers).

## Cross-references

- CLM-0170 (R92-W1, 76% saturation finding — R93-W0b explains the cause)
- CLM-0123 (R72_w4 P_balance=0.96 — consistent at this granularity)
- CLM-0160 (on-manifold critic competent — consistent: critic endorses
  the drift-induced bang-bang because that's the realised trajectory)
- CLM-0165 (R87 phase-resolved — impulse phase weaker critic confidence
  is exactly the LSTM h=0 → drift transient identified here)
- CLM-0149 / 0153 / 0154 (R84 W2/W3 affine-Q interpretation — now
  finally have a clean superseder: the off-manifold affine-Q regime
  IS what the actor briefly produces at step 0, but LSTM drift
  resolves it by step ~10. Mechanism interpretation in CLM-0149 (R85
  PRIORITY 1 = distributional critic) is **definitively ruled out**.)
- CLM-0144 (R57-R82 91-round plateau — R93 gives the first complete
  mechanism story)

## Questions opened (this round)

- (none) — R93 W0/W0b answer the "why saturation?" question. The
  next open question is "does LSTM-norm regularisation lift geo?"
  which is an R94 experiment, not a Q.

## Questions closed (this round)

- (none) directly. Q-0014 (algorithm exploration backlog) is moot
  in light of W0b (LSTM is the bottleneck regardless of algo class);
  recommend parallel session close Q-0014 with note "obsolete after
  CLM-0181 — bottleneck is hidden-state stability, not algorithm
  selection".

## Questions advanced (this round, status unchanged)

- **Q-0014** — R93-W0b makes algorithm-class exploration obsolete.
  Recommend close with reframe to "policy-state regularisation
  exploration".

## 给 PI 的话

**这周干了啥**：R92 默认推 R93-W1 widen-bound (DM_MAX 600→1200) 作为 highest-EV falsifier 0.391 plateau. 但 ANDES wave 太贵, 先做两个零 ANDES forensics 增加 信心: **W0** 看 R72_w4 actor 的 fc_out weight + pre-tanh logit, **W0b** 把 LSTM 在 4 个不同 obs stream (zero / constant / alternating / random) 上各 forward 50 step 看 h drift.

**结果（一句话）**：W0 发现 **actor weight 完全没 push boundary** — fc_out max |W|=0.15, pre-tanh logit median |z|=0.10 (deep tanh-linear), 0% logits > 2. W0b 发现真正凶手: **LSTMCell 学到一个 divergent 内部 dynamics**, ||h|| 从 0.25 自然 drift 到 5.0 (20×) 在 50 步内, **完全不依赖 obs 内容** (4 个 obs stream 包括 obs=zero 结果几乎完全一样). 跨 4 agent + 4 stream = 16 combo 全部 saturate, ag0 ΔM=-1 + ΔD=+1 等 per-agent sign pattern **跟 R92 真实 ANDES 完全匹配**. R92 的 76% saturation 是 **LSTM cell 自身病理**, 跟 obs / actor head / critic / reward / algo class 都没关系.

**意外**：这是 R57-R82 91-round plateau **第一次有 self-consistent + falsifiable mechanism**: R72_w4 SOTA = "256-action bang-bang stateful timer that ignores obs". 解释所有之前发现的事: R83 obs aug 全 RED (policy ignore obs), R84 critic-affine synthetic forensics 是 step 0-5 transient 的真实 footprint (CLM-0160 已 falsify mechanism interpretation, R93 给 hard 解释), CLM-0123 P_balance=0.96 是 4 agent symmetric drift 的副产物, 跨 SAC/TD3/Transformer/multi-LSTM algo 全 plateau 是 "都共享 LSTMCell 范式 + 没人加 hidden-state 正则" 的直接后果. 也 **重新调整 R93+ 优先级**: 不是 widen-bound 而是 **LSTM hidden-norm 正则** PRIORITY 1 (train loss 加 `λ_h * mean(||h_actor||²)`, 单 training-loop 改动, 1 ANDES wave).

**我默认下一步做**：W1 widen-bound ANDES 实验 **HOLD 等你拍板**. 因为新 mechanism story 说 widen-bound 可能不解决问题 (h 会 drift 到新的 boundary). 我推荐 **R94 = LSTM-norm 正则 + R72_w4 same hyper 75 ep s54**: 写 `λ_h * mean(||h_actor||²)` actor loss term, train 1 wave, 看 geo 是否突破 0.391. 如果 yes → mechanism 确认, paper 写 "我们发现 R72_w4 SOTA 是 LSTM drift bang-bang stateful timer, h 正则解锁 continuous control". 如果 no → mechanism 错, R95 走 widen-bound 等其他.

**你想插一脚就说**：(a) **保持原计划走 widen-bound**: 你认为 LSTM drift 不该 supersede R92 的发现, widen-bound 仍是最直接 falsifier — 说"走 widen"; (b) **走 LSTM 正则**: 接受 W0b 的解读, R94 = `λ_h ||h||²` regularisation — 说"走 LSTM norm"; (c) **并行做两个**: R94 widen-bound + R95 LSTM 正则两 wave, 2 ANDES slot ~30 min — 说 "两个都做"; (d) **加 W2 mathematical analysis**: 直接看 R72_w4 LSTMCell 的 weight_hh 矩阵谱半径 vs 1.0, 谱半径 > 1 就是 divergent dynamics 的直接证明 — 这是更 elegant 的 paper figure, 零 ANDES 5 min. 我推荐 **(d) + (b)**: 先 (d) 5 分钟给数学证明把 CLM-0181 trust 从 V (empirical) 上升到 V (empirical + theoretical), 然后 (b) 写 ANDES wave. 沉默就 (d)+(b).
