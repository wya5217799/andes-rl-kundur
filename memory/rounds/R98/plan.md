---
round: R98
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R98 plan — Distributional + Action-Feature-Engineered critic prototypes (CLM-0157 priority 1 + 2, offline-only)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI confirmed "继续研究, 别问, 干就完了". CLM-0157 (R86 verdict)
recorded R87+ priority order: (a) distributional critic ≫ (b) action feature
engineering ≫ (c) spectral norm. Other sessions (R87-R97) all in **forensics**
mode (Q-landscape on more ckpts / on-manifold / action-coordination); **0
session 在写 representation fix code**. R98 fills that gap with zero-ANDES,
zero-training, zero-train.py-mutation, pure prototype code + unit tests.
**Parent**: CLM-0157 (R87+ candidate (a)+(b)) + CLM-0148/0149/0150/0153-0156
(critic affine-Q evidence) + CLM-0170 (R92 bang-bang policy: actor-side mirror
of critic argmax-on-boundary, strengthens (a) prior).

## TL;DR

实现两个最小 diff critic variant (无 actor 改, 无 train.py 改, 无 replay 改):

- **`td3_qr_lstm`**: critic head 改 `Linear(hidden, N_QUANTILES=51)`, MSE 改
  quantile-Huber loss. CLM-0157(a). 强 mechanism break.
- **`td3_afe_lstm`**: critic input 改 `[obs, a, a², |a|, sign(a)]`. CLM-0157(b).
  Min-viable-diff.

不动 `td3_lstm.py` / `networks.py` / `train.py` / `replay_buffer.py`. 两个
prototype 各一个文件, 共享一个 critic 网络模块文件. 单元测 forward/backward
shape correctness. **不跑训练** (gated on R83 verdict per CLM-0157), 但代码
路径完整 ready, 一行 `--algo` 就可以 plug into train.py.

## Why now (and not R87+)

CLM-0157 says "execution gated on R83 (obs-space) result". R83 还没出. 但
**prototype 构建**不是 "execution". R83 出 negative (大概率, 7-dim obs 太
窄), R98 prototype 立刻 enable R99+ training round. R83 出 positive (少
概率), R98 prototype 仍是 paper Sec.V "what we considered" 的备选记录.

无下游风险: 两个新 agent 文件不影响任何 R57+ ckpt, 不影响任何 in-flight
session. 唯一 train.py 集成是 dispatch table 加 2 行, 但延后到 R83 verdict
出来之后再做 (R98-W4 verdict 标 deferred).

## Design — `td3_qr_lstm` (CLM-0157(a) distributional critic)

### Critic head

`RecurrentQRQNetwork` (新增 in `networks_critic_variants.py`):

```python
self.lstm = nn.LSTMCell(obs_dim + action_dim, hidden)   # 不变
self.fc_out = nn.Linear(hidden, N_QUANTILES)            # 改: 1 → N_QUANTILES
```

forward 返回 `(quantiles: (B, N), (h_new, c_new))`. Scalar Q proxy = mean of quantiles
(actor loss 用), 但 TD target + critic loss 用全 quantile 向量.

Twin critic: `RecurrentQRDoubleQCritic` 复合 2 个 `RecurrentQRQNetwork`.

### Quantile-Huber loss

```
quantile_targets τ_i = (i + 0.5) / N for i ∈ {0, ..., N-1}
TD target y = r + γ (1-d) · target_quantiles[:, sample_target_a]    # (B, N)
δ_ij = y_j - quantile_pred_i                                          # (B, N, N)
quantile_huber = mean_j |τ_i - 𝟙(δ_ij < 0)| · Huber(δ_ij, κ=1.0)
loss = mean over i (mean over j) over batch
```

详见 Dabney et al. 2018 QR-DQN paper §4.

### Target action

TD3 target policy smoothing 保留 (target_actor + noise + clip). Min-Q target
= `min(mean(q1_target_quantiles), mean(q2_target_quantiles))` — 用 mean 作
twin trick 的 scalar comparator (consistent with TD3 spirit), 但 critic loss
backprop 在 quantile level.

### Actor loss

Actor 不变. Actor loss = `-mean(q1_quantiles)` over actor's chosen action.

### Agent class

`TD3QRLstmAgent(TD3LSTMAgent)`:
- 重写 `__init__`: 替换 `RecurrentDoubleQCritic` → `RecurrentQRDoubleQCritic`
- 重写 `update`: 复制 base update, 改 critic loss 计算 (~30 line delta)
- `algo_name = "td3_qr_lstm"`, `is_recurrent = True`
- `N_QUANTILES = 51` (QR-DQN canonical)

## Design — `td3_afe_lstm` (CLM-0157(b) action feature engineering)

### Critic input

`RecurrentAfeQNetwork`:

```python
self.lstm = nn.LSTMCell(obs_dim + 5*action_dim, hidden)   # 改 input dim
def forward(obs, action, h_prev):
    afe = torch.cat([action, action**2, action.abs(), torch.sign(action)], dim=-1)
    x = torch.cat([obs, afe], dim=-1)                       # (B, obs+5A)
    ...
```

为什么这 5 个 feature: `action` 保留原 linear path; `action²` 给 critic 直接
expressivity 表达 concave-around-interior preference (二次形); `|action|` 让 critic
能区分 saturation magnitude 不论方向; `sign(action)` 让 critic 用 categorical
information 强化对 boundary 的 attention. 五个加起来覆盖 R84-W3 finding 中
critic 缺失的二阶 + abs-value pathway, 仍是 first-layer feature expansion (没改架构).

### Twin + agent

`RecurrentAfeDoubleQCritic` + `TD3AfeLstmAgent(TD3LSTMAgent)`. 子类只重写
`__init__` 用新 critic 类. **`update()` 不动** — critic interface
`(obs, a) -> q` 不变, 训练循环对外接口 identical.

`algo_name = "td3_afe_lstm"`, `is_recurrent = True`.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | (this file) plan.md | done |
| **W2** | `networks_critic_variants.py` + `td3_qr_lstm.py` + `td3_afe_lstm.py` | ~60 min |
| **W3** | `tests/test_critic_variants.py` forward/backward + dtype/shape | ~20 min |
| **W4** | Verdict + CLM-0176 (QR) + CLM-0177 (AFE) + chat brief | ~30 min |

Total ~2h, **zero ANDES, zero training**.

## 资源冲突 gate

- R83 (obs space training, WSL ANDES): 0 conflict — R98 不动 train.py / V4 / V4Config / base_env / agents/td3_lstm.py.
- R85 (classical PI/Droop, ANDES eval): 0 conflict — R98 不动 paper_path / scenarios.
- R86-R97 (forensics rounds): 0 conflict — R98 不动 scripts/r8*_*.py / results/r8*/.
- R98 输出 namespace: `src/andes_rl_kundur/agents/{networks_critic_variants, td3_qr_lstm, td3_afe_lstm}.py` + `tests/test_critic_variants.py`.

## 资产保护契约

不动: V4 / V4Config / base_env / paper_grade_axes / agents/td3_lstm.py /
agents/networks.py / agents/replay_buffer.py / scripts/train.py / 任何 R57+ ckpt /
任何 existing test.

新建: 3 个 agent / network file + 1 个 test file + plan/verdict + 2 CLM.

## 测试不变量

- V4 regression `tests/test_v4_env_regression.py` **不需重跑** (零 env / agent 现有码 改动)
- R57+ SOTA ckpt 完全不读不写
- 其他 in-flight session 的 scripts/results **不动**

## Gate

Pass = 两个 prototype 单测全过:
- forward 输出 shape 正确 (QR: (B, 51); AFE: (B, 1))
- backward 梯度 nonzero, 不 NaN
- `.save()` / `.load()` round-trip identity

Fail = 任一单测 fail → 修到 pass, 不绕过.

## Cross-references

- CLM-0157 (R86 decision: R87+ priority a > b > c) — R98 实现 a + b 两个
- CLM-0148/0149/0153/0154 (critic affine-Q evidence, R84) — R98 落实 fix
- CLM-0155/0156 (R86 cross-ckpt universality) — strengthens R98 prior
- CLM-0170 (R92 bang-bang policy) — actor-side mirror, R98 critic-side fix
- CLM-0163 (R91 value-horizon mismatch γ=0.99) — 独立 mechanism, 不冲突
- ADR-0001 (src layout) / ADR-0002 (V4 SSOT) — prototype 在 src/agents/, 符合
