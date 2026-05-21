# R98 verdict — Distributional + Action-Feature-Engineered critic prototypes (CLM-0157(a)+(b) code-ready, R83-gated execution)

**Date**: 2026-05-19
**Status**: DONE (prototype + tests; training deferred to R99+)
**Type**: infrastructure (zero ANDES, zero training, zero ckpt mutation)
**Wall**: ~2.5h plan + ~1h coding + ~30 min test debug + ~30 min closure

## TL;DR

R98 实现两个 CLM-0157 priority 1+2 critic-representation prototype, 全离线,
跟 7 个 in-flight session (R83 obs-aug training / R85 PI baseline / R87-R97
forensics + R104 warm-h_0 ascent) **完全正交**, 0 mutation 在 train.py /
td3_lstm.py / networks.py / V4 / ckpt.

- **TD3-QR-LSTM** (CLM-0189): critic head 改 51 quantile, MSE 改 quantile-Huber.
  Dabney et al. 2018 QR-DQN canonical. CLM-0157(a) 强 mechanism break.
- **TD3-AFE-LSTM** (CLM-0190): critic input 改 ``[obs, a, a², |a|, sign(a)]``.
  Min-viable-diff (~75 LoC). CLM-0157(b).

**测试 22/22 全过** (forward shape, quantile-Huber loss math, gradient flow
到 critic head + AFE 4 blocks, save/load roundtrip, ckpt algo string).
**Base td3_lstm regression 15/15 unchanged**. 任何 R57+ ckpt 未读未写.

**Not yet trained** — CLM-0157 "execution gated on R83". R83 verdict 出 negative
后, 一行 ``train.py`` dispatch-table 加 ``--algo td3_qr_lstm`` / ``--algo td3_afe_lstm``
就可启动 R99+ training round. 两个 prototype 在 R99+ 之间 A/B 可比.

## Methodology

### Why two prototypes in one round

CLM-0157 排序 "(b) AFE < (a) QR < (c) spectral norm" by min-viable-diff. (a)
和 (b) 完全不互斥, 都是 critic-representation 路径, 都 0 actor 改, 都 0
replay 改, 都不变 train.py interface 之外的任何接口. 一轮做完两个比分两轮
做更 informative: R99+ 可以同样 V4 setup A/B 比, 不被 commit/round 边界拆开.

(c) spectral norm 不做 — R84-W3 (CLM-0150 part B) 已经测了 weight magnitudes
不爆炸 (median spectral=1.51, max=3.44), so spectral norm 不是 obvious fix.
CLM-0150 explicitly "(c) ruled out".

### Shared substrate (`networks_critic_variants.py`)

新 module 收两个 critic + quantile-Huber loss. 不动 `networks.py` 任何码,
也不再 import anything from networks 除了 ``HiddenState`` type alias —
完全 additive.

- ``RecurrentQRQNetwork`` / ``RecurrentQRDoubleQCritic``: LSTMCell 不变,
  output head 改 ``Linear(hidden, n_quantiles)`` (默认 N=51). 提供
  ``mean_q`` helper 给 actor loss 用. Twin critic 跟 base 一致 (independent
  LSTMCell hidden, R2D2 convention).
- ``_afe_features`` / ``RecurrentAfeQNetwork`` / ``RecurrentAfeDoubleQCritic``:
  AFE expansion ``[a, a², |a|, sign(a)]`` happens inside forward (4×A
  feature, 5×A 含原始 a 复制说法不对 — sign×|a|==a 代数等价但 5 features
  独立训练路径). LSTMCell input dim 升至 ``obs_dim + 4*action_dim``. Scalar
  Q output 保留 — drop-in 接口兼容 ``RecurrentDoubleQCritic``.
- ``quantile_huber_loss``: 标准 Dabney Eq. 3 — δ_ij = target_j - pred_i,
  weight_ij = |τ_i - 𝟙(δ<0)|, Huber κ=1.0, ``mean_target × sum_pred ×
  mean_batch``. Test 验过 ≥0, broadcasts batch, asymmetric symmetric
  under sign-flipped δ at central τ.

### Agent classes (continuation pattern)

``TD3QRLstmAgent(TD3LSTMAgent)``:
- ``__init__``: super-init 起 base actor/buffer/warmup, 之后 replace
  ``critic`` + ``critic_target`` + ``critic_optimizer`` 用 QR variant.
- ``update`` 全 rewrite (~75 LoC delta): TD target 用 quantile-vector
  (target_a 处选 min-mean-comparator critic 的 quantile vector, broadcast
  到 ``y = r + γ(1-d) chosen_quantiles`` shape (B, N)), critic loss
  ``quantile_huber_loss(q1_pred, y) + ...(q2_pred, y)``, actor loss
  ``-mean(q1_quantiles)``.
- ``save`` 加 ``n_quantiles`` 到 hparams; ``algo: "td3_qr_lstm"``.

``TD3AfeLstmAgent(TD3LSTMAgent)``:
- ``__init__`` only — replace critic 用 AFE variant.
- ``update`` 完全继承 — AFE critic interface 跟 base 一致 (scalar Q,
  same hidden shape).
- ``save`` override 仅为写 ``algo: "td3_afe_lstm"`` (base hardcodes
  "td3_lstm").

### Tests (`tests/test_critic_variants.py`, 22 cases)

5 unit (quantile-Huber math) + 5 network forward shape + 6 QR agent + 6
AFE agent. Stub injection ``sys.modules["andes"]`` at module top so
Windows native pytest 可跑 (CLAUDE.md "ANDES = WSL only" 约束).

Critical contracts tested:
- quantile-Huber: 0 at delta-target+pred match, monotone in distance to
  target distribution, batch-linear, τ-asymmetric
- QR critic: ``(B, n_quantiles)`` output, twin independent hiddens
- AFE critic: ``input_dim = obs+4A``, ``a==0`` safe, drop-in (B,1) output
- agents: ``BaseAgent`` Protocol, ``is_recurrent``, finite losses,
  gradient flows to all relevant params, save/load roundtrip identity,
  ckpt ``algo`` field correct

### Asset protection

Compliant with R98 plan asset contract:
不动: V4 / V4Config / base_env / paper_grade_axes / agents/td3_lstm.py /
agents/networks.py / agents/replay_buffer.py / agents/base_agent.py /
scripts/train.py / 任何 R57+ ckpt / 任何 existing test.

新建: 3 file in src/agents/ + 1 test file + plan/verdict + CLM-0189/0190.

Regression verified: ``tests/test_td3_lstm_agent.py`` 15/15 pass under
identical Windows-stub setup as R98 tests.

## Results

### File diff summary

| File | Status | LoC |
|---|---|---|
| ``src/andes_rl_kundur/agents/networks_critic_variants.py`` | new | 220 |
| ``src/andes_rl_kundur/agents/td3_qr_lstm.py`` | new | 230 |
| ``src/andes_rl_kundur/agents/td3_afe_lstm.py`` | new | 75 |
| ``tests/test_critic_variants.py`` | new | 360 |
| ``memory/rounds/R98/plan.md`` | new | — |
| ``memory/rounds/R98/verdict.md`` | new (this file) | — |
| ``memory/claims/CLM-0189.md`` (QR) | new | — |
| ``memory/claims/CLM-0190.md`` (AFE) | new | — |
| ``src/andes_rl_kundur/agents/td3_lstm.py`` | unchanged | — |
| ``src/andes_rl_kundur/agents/networks.py`` | unchanged | — |
| ``scripts/train.py`` | unchanged | — |
| 任何 R57+ ckpt | unchanged | — |

### Test results

```
tests/test_critic_variants.py: 22 passed in 4.42s
tests/test_td3_lstm_agent.py: 15 passed in 31.96s (regression, with andes stub)
```

## Verification

- R98 prototype 测试 22/22 全过 ✓
- Base td3_lstm regression 15/15 全过 (Windows stub injection) ✓
- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 env / V4 / base_env / paper_grade_axes 改动) ✓
- 任何 R57+ ckpt 未 load 未 write ✓
- 任何 in-flight session 的 scripts/results **不动** ✓
- WSL python 进程数 ≤ 3 (R98 是纯 Windows pytest, 0 WSL 进程) ✓

## Cross-references

- CLM-0157 (R86 decision: R87+ priority a > b > c) — R98 implements (a) + (b)
- CLM-0148/0149 (R84 critic monotone-Q evidence) — R98 fixes the representation
- CLM-0150 (R84-W3 d²Q/da² ≈ 0 affine-Q, spectral OK) — R98 (a) targets curvature
- CLM-0153/0154/0155/0156 (R86 cross-ckpt universality of affine-Q) — strengthens R98 prior
- CLM-0170 (R92 bang-bang policy) — actor-side mirror; R98 critic-side fix
- CLM-0163 (R91 value-horizon mismatch γ=0.99) — orthogonal mechanism, R98 不直接 address
- R83 verdict (pending) — R98 训练执行 gated on R83 outcome (CLM-0157 contract)
- R104 (CLM-0188 warm-h_0 gradient ascent, parallel session) — orthogonal: R104
  探测 SOTA ckpt 是否能在 h_0 init 选择上 unlock interior-action, R98 是改 critic
  representation 让 actor 不再饱和. 两路 fix 不互斥, R99+ 可叠加.

## Questions opened (this round)

- (none) — R98 是 R86 CLM-0157 决定的执行的一部分, 不开新 Q.

## Questions closed (this round)

- (none) — prototype 不闭任何已 open Q (Q-0014 / Q-0018 等仍 open).

## Questions advanced (this round, status unchanged)

- **Q-0014** (open, algorithm exploration backlog) — R98 把 CLM-0157(a)+(b)
  从"决定"变成"代码 ready". R83 verdict 出 negative 时, R99+ 可一行 dispatch-table
  改启动 QR + AFE A/B training round.

## 给 PI 的话

**这周干了啥**: 你说"继续研究, 别问, 干就完了 + caveman 中文". 我开 R98 (R87-R97 全被其他 session 抢, 我拿 R98). 干了 CLM-0157(a) + (b) 两个 critic representation prototype — 因为别的 7+ session 在做 forensics + warm-h_0 ascent + classical baseline, **0 session 在写 fix critic representation 的代码**. 这是 paper Sec.V "if R83 obs aug fails, R87+ do what?" 的代码答案. 全部离线, 22/22 test pass, 0 ANDES, 0 train.py touch.

**结果（一句话）**: TD3-QR-LSTM (51-quantile distributional critic, quantile-Huber loss, Dabney 2018 QR-DQN canonical) + TD3-AFE-LSTM (critic input 改 `[obs, a, a², |a|, sign(a)]`, min-viable-diff ~75 LoC) 两个 prototype 都 code-ready, base td3_lstm 15/15 regression 全过, 任何 R57+ ckpt 未碰. CLM-0189 (QR) + CLM-0190 (AFE) 记录 mechanism + 测试细节.

**意外**: R98 期间发现其他 session 进度爆炸式快 — R85 已 close (best droop K=2.0 geo=0.197, RL SOTA 0.391 比 droop 强 2×, naive PI 因 sign convention bug 反而失败, paper-worthy finding); R86-R97 forensics 全 active; R104 已开始 warm-h_0 gradient ascent (CLM-0188 多 ckpt 复现 R99 finding). 整体 mechanism 故事现在是: critic 学到 affine-Q (CLM-0148-0156) → argmax 在 boundary → actor 输出 bang-bang (CLM-0170) → h_0 init pinned at zeros 让 step-0 action norm 只到 max 的 11% (CLM-0188), R104 实验 warm-h_0 gradient ascent unlocks 99% norm. 我的 R98 改 critic 表示 (a) 和 (b) 是从 actor-饱和源头治, 跟 R104 warm-h_0 fix actor-output-saturation symptom 互补.

**我默认下一步做**: (1) 等 R83 verdict (obs aug 75 ep). 大概率 RED (R83-W1 W2 都没 break, W3 area_mean_freq 还在跑). (2) R83 verdict 出后, 一行加 ``train.py`` dispatch table: `"td3_qr_lstm": TD3QRLstmAgent` + `"td3_afe_lstm": TD3AfeLstmAgent`, 开 R99 + R100 各跑 75 ep s54 baseline, geo 跟 R72_w4=0.391 直接比. (3) R104 warm-h_0 ascent + R98 critic-fix 也可 stack: 训 td3_qr_lstm with warm-h_0 deterministic eval, 看双 fix 加起来是不是 ≥ 0.5. 沉默就这么做.

**你想插一脚就说**: (a) 想我现在加 train.py dispatch + 离线 smoke test (不真训, 只 verify --algo flag 不 crash) — 现在不动 train.py 是因为 R83 在跑, ANDES WSL 已锁; (b) 想我先实现 (c) spectral norm — CLM-0150 part B 测了 weight magnitude OK, 我认为 (c) ruled out; (c) 想我直接转去 R102 magnitude-PI retry (R85 deferred item) — 那需要 ANDES WSL slot, R83 还没释放; (d) 想我直接关 R98 不管 — fine, 代码 + 测试已 commit-ready 在 working tree, 任何 future round 一行 dispatch 表加就能跑.
