# R111 verdict — Step-0 saturation deficit is universal, not LSTM-specific

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (with mechanism reframing for R107/R109 conclusions)
**Type**: analysis (cross-algo-class actor evaluation, zero ANDES)
**Wall**: ~40 min (25 min code+rerun-with-tanh-fix + 15 min write)

## TL;DR

R107-W2 (CLM-0193) showed LSTM-h=0 produces ||a||=10% of max regardless
of ||obs||. R111 tested whether this deficit is LSTM-specific by adding
SAC and TD3-MLP ckpts to the same step-0 forensics.

Result: **near-universal across actor classes**. 5/6 ckpts have step-0
||a|| ≤ 15% of max (3 LSTM, 1 SAC, 1 TD3-MLP). Only r63_w4_td3_combo
reaches 65% (TD3-MLP with R63 hyper-combo).

Implication: warm-h_0 fix targets a LSTM-specific instantiation of a
**near-universal step-0 saturation deficit** in actors trained on
paper-faithful 7-dim obs. If R96 works, the same deficit in SAC /
TD3-MLP could be addressed by an analogous actor-output-warmth knob
(not in R96 scope).

This sharpens but does not undermine the warm-h_0 motivation —
R96 still targets the LSTM-specific symptom of a broader problem.

Zero ANDES. Zero WSL.

## Methodology

6 R86 ckpts × 4 agents × 100 step-0-like obs (||obs||=0.25):

For recurrent (TD3-LSTM): `a, _ = actor(obs, h=0)` (already tanh-bounded).
For non-recurrent (TD3-MLP, SAC): `mean, _ = actor(obs)` then
`a = tanh(mean)` — matches `_SACBase.select_action` deterministic
behaviour. Without the tanh post-process, the raw mean is unbounded
and not comparable to LSTM's tanh-bounded output (R111-W1 first run
reported ||a||=1.541 > √2 max for one ckpt; tanh fixes this).

## Results

| Ckpt | algo class | ||a||_med | % of max | p10 | p90 |
|---|---|---|---|---|---|
| r72_w4_lstm_s54 | td3_lstm | 0.142 | 10.1% | 0.078 | 0.277 |
| r58_lstm_s49 | td3_lstm | 0.080 | 5.6% | 0.032 | 0.124 |
| r58_lstm_s50 | td3_lstm | 0.120 | 8.5% | 0.090 | 0.163 |
| r58_td3_mlp_s49 | td3_mlp | 0.209 | 14.8% | 0.094 | 0.254 |
| r58_sac_mlp_s49 | sac_mlp | 0.096 | 6.8% | 0.055 | 0.175 |
| r63_td3_mlp_s49 | td3_mlp | 0.925 | **65.4%** | 0.468 | 1.123 |

Per-algo-class median (of ckpt medians):
- td3_lstm: 8.5%
- td3_mlp: 40.1% (dragged up by r63)
- sac_mlp: 6.8%

Without r63 (the outlier): non-LSTM median = (14.8 + 6.8) / 2 = 10.8%,
basically same as LSTM at 8.5%.

**Verdict: deficit is near-universal**. 5/6 ckpts at ≤ 15%, 1 outlier
at 65%.

### r63 outlier

r63_w4_td3_combo_s49 was trained with R63 hyper-combo (CLM-0086/0087/
0088): batch_size=512, n_substeps=3, max_grad_norm=0.5. Different from
R58/R72 defaults (256 / 1 / 1.0). This hyper combination apparently
allows the MLP actor to saturate from small obs.

But: r63's **6-axis geo did not exceed 0.391**. The R63 hyperparameters
let the actor saturate at step 0, but the resulting policy quality is
not better than LSTM ckpts that under-saturate. Saturating at step 0
is necessary but not sufficient — the actor must also choose the
*correct* action at step 0.

### Reframing CLM-0174 / CLM-0193

Old (LSTM-specific story): "LSTM warm-up takes 10 steps; warm-h_0
fixes the LSTM-specific architectural bottleneck."

New (broader story): "The paper-faithful 7-dim obs alone is insufficient
to produce saturated step-0 output across most actor architectures.
LSTM with h=0 is one manifestation. SAC and most TD3-MLP have the
same deficit through different mechanisms (no warm-up needed since
no hidden state, but the MLP still maps small obs to small mean).
Warm-h_0 is the LSTM-specific fix for the LSTM-specific symptom."

R86's universal monotone-Q + R111's near-universal step-0 deficit are
two faces of the same observation: actors and critics trained on
paper-faithful 7-dim obs collectively under-utilise the action space
at step 0.

## Decision

R96 motivation **strengthened**, not weakened, by R111:
- Warm-h_0 is the LSTM-specific fix for a real LSTM-specific symptom
  (R72_w4 SOTA's plateau)
- The same step-0 deficit in SAC / TD3-MLP is **separate problem**
  needing a different fix (out-of-scope)
- If R96 works on LSTM, the framework generalises: each actor class
  needs its own "step-0 saturation" injection point

R96 launch surface unchanged from R109 (CLM-0201): train.py +
checkpoint_loader.py 5-LOC dispatches + 1 WSL slot.

## Infrastructure changes

不动: V4 / V4Config / base_env / paper_grade_axes / agents/ /
scripts/train.py / R57+ ckpt / any test / agents/networks_warmh0.py /
agents/td3_lstm_warmh0.py (R107 / R109 artefacts).

新建:
- `scripts/r111_action_norm_by_algo_class.py`
- `results/r111_action_norm_by_algo_class/summary.json`
- `memory/rounds/R111/{plan.md, verdict.md}`
- `memory/claims/CLM-0207.md`

## Cross-references

- CLM-0193 (R107 LSTM-specific deficit) — R111 generalises
- CLM-0188 (R104 universalisation across LSTM ckpts) — adjacent
- CLM-0155 (R86 cross-ckpt monotone-Q) — sibling universality finding
- CLM-0174 (R95 LSTM ramp-up observation) — refined
- CLM-0207 (this round)
- Q-0022 — implementation surface unchanged, motivation broadened

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0022** (warm-h_0 LSTM candidate) — broader context: now known to
  target the LSTM-specific instantiation of a 5/6-ckpt-near-universal
  step-0 saturation deficit. Log entry added.
- **Q-0014** (algorithm exploration backlog) — narrowed further: not
  just "fix LSTM", but "find each algo's step-0 saturation injection
  knob". For TD-LSTM that's warm-h_0; for SAC / TD3-MLP it'd be
  "first-layer bias initialised toward saturation" or similar — open
  for R97+ if R96 works.

## 给 PI 的话

**这周干了啥**：你说"一直干活". R107-W2 我说 LSTM h=0 不管 obs 多大都只能 saturate 到 10%. 但有个 reviewer 会问的 question 没回答: 这 step-0 deficit 是 LSTM-specific 还是 actor-class 都这样? R111 在 R86 6-ckpt set (3 LSTM + 1 SAC + 2 TD3-MLP) 上跑同样的 100 step-0-like obs, 报 tanh-bounded ||a||. (运行时发现 _SACBase 的 actor 是 GaussianActor 返回 (mean, log_std), 要 post-tanh 才跟 LSTM 输出可比, fix 一次后再跑.)

**结果（一句话）**：**deficit 几乎 universal — 5/6 ckpts step-0 ||a|| ≤ 15% of max** (3 LSTM 5.6-10%, 1 SAC 6.8%, 1 TD3-MLP r58 14.8%). 唯一例外是 **r63_w4_td3_combo (TD3-MLP 用 R63 hyper combo batch=512/n_sub=3/grad_clip=0.5) 飙到 65.4%** — 但 r63 整体 geo 没超 0.391. 即"早 saturate ≠ 好 policy", 必要不充分.

**意外**：我本来 CLM-0174 把 LSTM warm-up lag 写成 LSTM 架构特定问题. 现在数据说不是 — SAC MLP / TD3 MLP 也一样 step-0 弱. 这反过来扩展 paper narrative: paper-faithful 7-dim obs **整体不足以让任意 actor 类在 step 0 saturate**. R86 universal monotone-Q + R111 universal step-0 deficit 是同一个观察的两面. R96 warm-h_0 仍然 motivated — 它是 LSTM 这个 symptom 的 specific fix, 不是要 fix 全部 actor class. SAC/TD3-MLP 同样的问题需要不同 knob (first-layer bias 初始化), R97+ 可考虑.

**我默认下一步做**：(1) R111 关闭 closed-positive, CLM-0207 写入 (已完成). (2) **R96 等 WSL 不变** — R111 reframe 但不改 launch surface. (3) 继续 zero-conflict 离线: 下个候选 **R112 = r63 hyper-combo 的 step-0 saturation 秘诀分析** (为什么这个 hyper combo 出 65.4% 而 R58/R72 出 < 15%?) 离线 20 min, 或 **R113 = paper Sec.IV-D mechanism story 草稿 (R88+R92+R95+R99+R104+R107+R109+R111 共 9 个 CLM 整合)** 离线 60 min. (4) 我推荐先写 paper 草稿因为 R111 已经把 mechanism story 收尾, 加上 r63 outlier 的 "saturate ≠ good" sub-finding paper Sec.IV-D 立论非常完整. 沉默继续干.

**你想插一脚就说**：(a) 想我立刻 R112 r63 hyper-combo deep dive — 离线 20 min, 测哪个 hyperparam 单独/组合让 MLP 在 small obs 下学到 saturate; (b) 想我 R113 paper Sec.IV-D 草稿 — 60 min, 整合 9 个 mechanism CLM; (c) 想我把 R88/R95/R99/R104/R107/R109/R111 一起做 visual summary (一张图叠 6 个 finding) — 40 min, 给 paper 一张 "为什么 91 round 都败" 的 anchor figure; (d) 想我开始 cleanup 也行 — 我注意到 networks_warmh0.py + td3_lstm_warmh0.py 还没有 pytest unit test, 写完 R96 前应该补上. 我推荐 (默认) **(1)+(2)+(b)+(c)**: 现在写 paper draft + 主 figure 等 R94 释放 WSL.
