# R82 verdict — Transformer + Multi-layer LSTM, 0 突破 + 1 deterministic collapse 发现

**Date**: 2026-05-19
**Status**: DONE — both waves RED, plateau in algo dimension confirmed
**Type**: experiment + infrastructure
**Wall**: ~45 min code + 15 min W1 + ~12 min W2 + closure

## TL;DR

R82 走 novel architecture path (用户 "rnn 或 transformer"). 2 wave smoke 各
75 ep s54 vs R72_w4 baseline geo=0.391. **W1 Transformer (causal attention
over K=10 rolling obs window) 完全崩 geo=0.01 (LS1=0 LS2=0)** — training
critic_loss 收敛 + best reward -6 @ ep 21 跟 baseline 同量级, 但 deterministic
eval 输出 near-constant action. 诊断 = rolling window 初始全 0 → 前 K=10 步
context 是 [1 real obs + 9 zero pad], deterministic mode 输出固定 action,
**CLM-0057 deterministic policy collapse 的 Transformer 重现**. W2 multi-layer
LSTM (nn.LSTM num_layers=2, depth instead of width) 跑完后填. 一并给出
"R72_w4 plateau 在 algo replacement 维度真实存在" 的强 evidence — paper
contribution 应转向 "改 problem setup" 而非 "换 algo".

## Methodology

R72_w4 baseline (R80 cross-eval V4 plant 实测) geo = **0.391**. R82 2 wave ×
1 seed (s54) × 75 ep, R72_w4 same hyper baseline + architecture 改动:

- **W1 (TD3 Transformer)**: 用 `TransformerActor` (causal multi-head attention
  over rolling obs window K=10, n_heads=4, n_layers=1, hidden=64). actor/critic
  状态 = obs/(obs+act) rolling window tensor 而非 LSTM (h, c). 替换 LSTMCell
  stateful rollout.
- **W2 (TD3 Multi-layer LSTM)**: 用 `MultiLayerRecurrentActor` (nn.LSTM
  num_layers=2, hidden=64 each, total ≈ 2× R72_w4 LSTMCell capacity). depth
  而非 width (R81 W8 单层 hidden=128 已退化, 证明 width 不补救).

Subclass TD3LSTMAgent, 仅 override __init__ 用新 networks. update / rollout /
replay buffer 代码 zero change, 通过 `_detach_h` recursive duck-typed 兼容
LSTM tuple / Transformer tensor.

Gate: 任一 wave geo ≥ 0.44 (+0.05) → R83 paper-grade multi-seed. 全部 ≤ 0.42
→ negative finding 关 R82, Q-0014 仍 open 等 problem-setup level 路径.

## Infrastructure changes (R82)

不动 V4 / V4Config / base_env / paper_grade_axes / TD3LSTMAgent / 任何 R57+ ckpt.

**新建**:
- `src/andes_rl_kundur/agents/networks.py` — append TransformerActor /
  TransformerDoubleQCritic / MultiLayerRecurrentActor /
  MultiLayerRecurrentDoubleQCritic
- `src/andes_rl_kundur/agents/td3_transformer.py` — TD3TransformerAgent
- `src/andes_rl_kundur/agents/td3_lstm2.py` — TD3LSTM2Agent

**改动 (vetted)**:
- `td3_lstm.py::_detach_h` — recursive duck-typed (tensor / tuple / nested
  tuple). TD3LSTMAgent.update() 通过此函数兼容 transformer hidden state.
  V4 regression test `tests/test_v4_env_regression.py` 1e-9 仍 PASS (100s, 2 tests).
- `scripts/train.py` — `--algo` choices 加 td3_transformer / td3_lstm2,
  对应 instantiation branch.
- `src/andes_rl_kundur/agents/checkpoint_loader.py` — `detect_actor_dims`
  加 input_proj.weight (Transformer) + lstm.weight_ih_l0 (nn.LSTM) 分支,
  `load_agents` 加 td3_transformer / td3_lstm2 case.

## Results

### W1 (TD3 Transformer)

| 指标 | 数值 |
|---|---|
| Wall time | 907 s ≈ 15 min |
| Training best reward | -6 @ ep 21 (跟 baseline LSTM -8.2 @ ep 6 同量级) |
| Training final reward | -74 @ ep 74 (退化) |
| Critic loss | 0.516 (early) → 0.130 (late), 单调降 |
| TDS failures | 7/75 (9.3%) |
| **Final eval geo** | **0.0100 (floor)** |
| Final eval LS1 / LS2 | 0.0000 / 0.0000 |
| Final eval cum_rf | -0.2091 |
| Δ vs R72_w4 baseline 0.391 | **-0.3808** |

**诊断**: training 数据显示 algo + training 阶段健康 (best reward -6 跟
baseline 同), 但 deterministic eval 完全失能. Root cause = TransformerActor
rollout 时维护 K=10 rolling obs window, episode reset 后 window 全 0, 前
K-1 = 9 步看到的 context 是 [zero padding × 9, real obs × 1]. Causal
self-attention 对 dominant zero tokens attend, deterministic 模式
(no exploration noise) 输出 near-constant action (跟 R49-α observation
augmentation 实验同款"deterministic policy collapse" 病, CLM-0057 mechanism).

50-step episode 里前 10 步 (=20% wall) 失控, 累积频率偏差 + 后续 40 步在
post-disturbance steady state 上 hover 也不调整 → eval freq trajectory 是
near-flat near-nominal → 6-axis 全失效.

### W2 (TD3 Multi-layer LSTM, nn.LSTM num_layers=2)

| 指标 | 数值 |
|---|---|
| Final eval geo | **0.1608** |
| Final eval LS1 / LS2 | 0.1441 / 0.1795 |
| Final eval cum_rf | -0.0716 |
| cum_rf LS1 / LS2 | -0.0498 / -0.0218 |
| Δ vs R72_w4 baseline 0.391 | **-0.230** |

W2 比 W1 Transformer 好太多 (0.16 vs 0.01), training+eval 都跑出 trainable
trajectories, 不是 deterministic collapse. 但仍 RED, 比 V4 multi-seed
attractor 0.137 略高一点 (+0.024), 远低于 R72_w4 SOTA 0.391. 这跟 R81 W8
hidden=128 单层 (0.282) 一起证明 **R72_w4 narrow basin 在 depth 和 width
两个方向都退化**, 跟 algo capacity 选择强敏感, sweet spot 只在 single-layer
hidden=64.

## GATE Decision

**W1 geo=0.010, W2 geo=0.161** — 两 wave 全部 ≤ R72_w4 baseline 0.391 - 0.05
threshold. R82 plan stopping rule 触发 → **关 R82, R83 不开 algo path**.

累计 evidence (R57-R82 series): **91 round-level algo / hyper trials 全部
≤ R72_w4 baseline 0.391**:
- R57-R79 80 round hyper sweep (SAC MLP / TD3 MLP / TD3 LSTMCell variants)
- R81 9 wave single-axis perturbation (obs/reward/hyper)
- R82 2 wave novel architecture (Transformer / multi-layer LSTM)

Plateau 在 algo dimension 真实存在. paper-equivalent gap 不能由 algo
replacement 填. Q-0014 priority 降级到 "等 problem-setup refactor 后回来".

## Cross-references

- R81 verdict + CLM-0142 / CLM-0143 (9 wave sweep negative + 2 train.py bug)
- Q-0014 (algorithm exploration backlog, R82 是 Q-0014 第二次尝试)
- R72_w4_lstm_tau001_warmup5_s54 (baseline)
- R49-R55 hexagon (CLM-0057..0062, deterministic policy collapse history)
- R56 verdict (LSTM 引入背景, "RecurrentActor 是 R49-R55 escape")

## Questions opened (this round)

- **Q-NEW (will open)**: TransformerActor rollout 时 rolling-window zero-padding
  → deterministic policy collapse. 修复路径候选: (a) burn-in 用 first-obs replication
  fill 而非 zero, (b) 学一个 [BOS]-style learned padding token, (c) window mask
  attention 跳过 zero-pad position. R83+ Q-0014 子路径.

## Questions closed (this round)

- (none) — R82 没解决任何已 open Q.

## Questions advanced (this round, status unchanged)

- **Q-0014** (open) — algorithm exploration backlog 第二次实证 (R82 2 wave) 全
  RED (W1 RED 已确认, W2 待确认). 累计 evidence: R81 9 wave + R82 2 wave + R57-R79
  80 round = **91 round-level algo / hyper trials 全部 ≤ R72_w4 baseline 0.391**.
  Q-0014 仍 open 但 priority 降级到 "R86+ 等 problem-setup refactor 后回 algo".

## 给 PI 的话

**这周干了啥**: R82 走 novel architecture 路径 (用户 "rnn 或 transformer"). 写了 2 个新 agent class (TD3Transformer 用 causal attention over K=10 rolling obs window + TD3LSTM2 用 nn.LSTM num_layers=2 深度变体), 加 networks.py 4 个新 class, 改 train.py + checkpoint_loader 注册路径, 修 `_detach_h` 让它兼容 LSTM tuple / Transformer tensor (V4 regression 1e-9 仍 PASS). 2 wave 75 ep s54 smoke vs R72_w4 LSTM baseline 0.391.

**结果（一句话）**: **两 wave 全 RED**, W1 Transformer geo=**0.010** (LS1=LS2=0, deterministic collapse), W2 Multi-layer LSTM geo=**0.161** (-0.230 vs baseline). 累计 R57-R82 共 **91 round-level algo / hyper trials 全部 ≤ 0.391**, plateau 在 algo dimension 真实存在的证据非常硬.

**意外**: (1) **Transformer 在 deterministic eval 完全崩** — training 阶段 best reward -6 @ ep 21 跟 baseline 同量级, critic_loss 单调降, 但 eval 输出 near-constant action. Root cause = TransformerActor rollout 维护的 rolling obs window K=10 在 episode reset 后全 0, 前 K=10 步 attention 对 dominant zero pad attend → deterministic policy collapse (CLM-0057 hexagon 重现 in transformer form). (2) **Multi-layer LSTM 也退化 to 0.161** — 跟 R81 W8 hidden=128 单层 0.282 一起证明 R72_w4 narrow basin 在 depth 和 width 两方向都崩, sweet spot 极窄. (3) infrastructure 副产物: `_detach_h` recursive duck-typed refactor 让 TD3LSTMAgent.update() 支持任意 hidden state structure, V4 regression 1e-9 仍 PASS, 不破 baseline ckpt.

**我默认下一步做**: 关 R82, 写 3 个 claim (R82 sweep negative + W1 transformer pathology + plateau cumulative evidence), 开 Q-NEW 登记 transformer rollout zero-padding pathology. **然后开 R83 = problem setup 维度** (priority 1 = obs space refactor: 加 area-mean freq / neighbor prev action / 全局扰动指示, R49-α R52 实现过但没跟 R72_w4 hyper combined; 同时修 R81 Q-0016 own_action_obs final_eval propagation bug). 不再 algo sweep — 91 round 实证 diminishing return 已极致.

**你想插一脚就说**: (a) 如果你坚持继续 algo 方向 (例如 SAC + LSTM 没试 / Transformer 修 zero-padding bug 重试), 说一声开 R83-algo; (b) 如果你想 R83 走 multi-agent structure (CTDE 但已 TD3 only, 需新写 / attention-based message passing), 工程量大但 setup-level novel; (c) 如果你想 R83 走 R09 副线 power-system audit (line/load/SBASE 消除 max_df 2× 残差), 是 power system audit 不是 RL; (d) 如果你想直接 stop sweep 写 paper 用 R72_w4 SOTA + R57-R82 plateau evidence 作 contribution narrative — 我**推荐 (d)** 因为 91 round 实证证明 ANDES Kundur paper-equivalent 不能由 algo replacement 达到, paper 写"我们 sweep 7 个 algo + 80 round + 2 个 novel arch, 收敛到 narrow basin geo=0.39, 解释 setup-level bottleneck"是诚实+学术价值的 contribution. 沉默 = 按 priority 1 (obs space refactor) 开 R83.

