---
round: R82
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R82 plan — Transformer-based actor/critic, novel architecture vs R72_w4 LSTM

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: Q-0014 (algorithm exploration backlog), R81 verdict (c) "novel direction" 路径, PI 确认 "继续优化算法，比如用rnn或者transformer"

## TL;DR

R81 9 wave sweep (R72_w4 baseline + 单 axis 改) **0 突破**, 强 evidence 是 R72_w4 是 narrow local basin. R82 走 novel architecture: 把 LSTMCell 换成 Transformer (multi-head self-attention over rolling obs window K=10). 单 seed s54 × 75 ep smoke vs baseline geo=0.391. GREEN ↔ geo ≥ 0.44 (+0.05) → 进 R83 multi-seed × 500 ep. RED ↔ < 0.39 → cycle 2 backup: multi-layer LSTM (num_layers=2, hidden=64 each) 同 budget retry.

## Methodology

实施 path: **subclass TD3LSTMAgent**, 仅替换 actor/critic 类:
- 新 `TransformerActor` / `TransformerDoubleQCritic` in `networks.py`
- 接口跟 `RecurrentActor` 一致: `forward(obs, h_prev) -> (action, h_new)`
- `h` 改为 (B, K, obs_dim) 滚动窗口 instead of LSTM (h, c)
- 新 `TD3TransformerAgent` (subclass TD3LSTMAgent), 仅 override `__init__` 用 Transformer 类
- 训练 / rollout / replay buffer 代码全部不动

不动:
- TD3LSTMAgent (R72_w4 baseline 依赖)
- V4 / V4Config / paper_grade_axes / base_env
- 任何 R57+ SOTA ckpt (含 R72_w4)
- R80 V5 env infrastructure
- R81 9 wave ckpt

新建:
- `src/andes_rl_kundur/agents/networks.py` — append TransformerActor / TransformerDoubleQCritic
- `src/andes_rl_kundur/agents/td3_transformer.py` — TD3TransformerAgent class
- `scripts/train.py` — 注册 `--algo td3_transformer` choice
- `results/r82_w1_td3_transformer_s54/` — smoke ckpt
- `memory/rounds/R82/verdict.md` (跑完写)
- 视结果 1-2 个 claim

## Architecture

TransformerActor:
- Input: obs window (B, K, obs_dim) with K=10
- Positional encoding: learnable embeddings (B, K, hidden)
- Transformer encoder: 1 layer, multi-head attention (n_heads=4), FFN dim=hidden*2, hidden=64
- Causal mask (last token attends to all prior K tokens)
- Output head: Linear(hidden, action_dim) on last token → tanh

TransformerDoubleQCritic:
- Input: obs window (B, K, obs_dim) + action window (B, K, action_dim)
- Concatenated per-token (B, K, obs+action)
- Twin Q networks, each with own transformer encoder
- Q value from last token

Hyper (start with R72_w4-compatible):
- hidden=64 (matches R72_w4)
- K=10 (rolling window length)
- n_heads=4 (hidden=64 / 4 head=16 dim each)
- 1 transformer layer (深度不增加, capacity vs R72_w4 ≈ comparable)

Rationale: smaller transformer first as smoke; if signal exists, R83 grows depth/heads.

## Execution

```
Phase 1: 写 networks.py + td3_transformer.py + train.py registration (~1-1.5 hr)
Phase 2: smoke 75 ep s54 (~15-20 min, transformer 比 LSTM 略慢)
Phase 3: final_eval 6-axis geo + cum_rf
Phase 4: 跟 R72_w4 baseline 0.391 比, GATE 决定
```

Gate:
- geo ≥ 0.44 → R83 multi-seed × 500 ep paper-grade (winner found)
- geo ∈ [0.30, 0.44) → marginal, fallback cycle 2 (multi-layer LSTM)
- geo < 0.30 → architecture 全崩, R82 negative finding + fallback cycle 2

## Stopping rules

- 训练 NaN / TDS fail > 50% → 记 negative finding 跳 cycle 2
- Phase 4 GATE 决定 R83 / cycle 2 / 关 R82
- Cycle 2 (multi-layer LSTM 2 层) 也 fail → R82 verdict: "novel arch 75 ep smoke 都 RED, Q-0014 阻塞需 R83 longer budget"

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / TD3LSTMAgent / 任何 R57+ ckpt. 
V4 regression test (1e-9) 必须仍 PASS — 但 R82 不动 env 不动 reward, 这个 default 满足.
