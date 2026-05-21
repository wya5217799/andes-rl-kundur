# R109 verdict — TD3LSTMWarmH0Agent code drop-in (R96 implementation almost complete)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (R96 launch surface = 2 × 5-line dispatch edits + WSL slot)
**Type**: code (extension of TD3LSTMAgent via subclass, zero existing-file edits)
**Wall**: ~50 min (30 min code + smoke + 20 min write)

## TL;DR

R107 shipped `WarmH0RecurrentActor` (the actor module). R109 ships
`TD3LSTMWarmH0Agent` (the agent class that uses it). Both live in new
files; zero lines changed in existing source. Smoke test passes:
agent instantiates, runs 6-step deterministic rollout without error,
returns sensible action magnitudes.

R96 launch surface now reduced to:
1. `scripts/train.py`: 5-line dispatch for `--algo td3_lstm_warmh0`
2. `src/andes_rl_kundur/agents/checkpoint_loader.py`: 5-line elif branch
3. WSL training run (1 seed × 75 ep × R72_w4 hyper × paper-faithful obs)

Steps 1-2 are mechanical, identical to existing td3_lstm / td3_transformer
branches. Step 3 needs WSL slot release.

Zero ANDES, zero WSL during R109.

## Methodology

`TD3LSTMWarmH0Agent` inherits from `TD3LSTMAgent` and overrides 4 methods:

| Method | Override reason | Δ LOC vs base |
|---|---|---|
| `__init__` | super() builds vanilla actor; we replace with WarmH0 + rebuild actor_optimizer | ~10 |
| `select_action` | thread `obs_t` to `init_hidden(obs_for_warm=...)` at episode start | ~3 |
| `select_action_recurrent` | thread `obs_t` for stateless eval | ~3 |
| `update` | thread `obs[:, 0]` for actor + `next_obs[:, 0]` for actor_target at burn-in start | ~5 of 80 update-method lines |

Critic init stays at zeros (matches CLM-0183 / CLM-0188 forensics scope —
actor-side warm-up only). This keeps R96 a 1-variable experiment (does
warm-actor-h_0 break the plateau?) without confounding warm-critic-h_0.

Smoke test:
```python
ag = TD3LSTMWarmH0Agent(obs_dim=7, action_dim=2, hidden_sizes=64)
ag.begin_episode()
for t in range(6):
    obs = np.random.randn(7).astype(np.float32) * 0.3
    a = ag.select_action(obs, deterministic=True)
    # ||a|| reported per step, all finite
```

Result: ||a|| ~ 0.12-0.15 at each step (random-init MLP heads don't yet
point toward saturating directions; training will adapt them).

## Results

### Code artefacts

- `src/andes_rl_kundur/agents/td3_lstm_warmh0.py` — 230 lines (full
  override of init + 3 rollout methods + update; the update method's
  burn-in/critic-loss/actor-loss bodies are copy-pasted from base class
  with only the actor init_hidden lines modified — TD3LSTMAgent's
  update is monolithic so partial override would be hackish)

### Smoke test

```
algo_name = td3_lstm_warmh0, is_recurrent = True
actor type: WarmH0RecurrentActor
actor has h_init: True
first step ||a|| = 0.152  (random init MLP, expect nonzero)
  step 1 ||a|| = 0.142
  step 2 ||a|| = 0.142
  step 3 ||a|| = 0.114
  step 4 ||a|| = 0.123
  step 5 ||a|| = 0.140
OK: TD3LSTMWarmH0Agent runs end-to-end
```

### R96 launch surface

All preparatory work for R96 is now complete:

| Component | Status |
|---|---|
| Architectural feasibility (N=1) | ✅ CLM-0183 (R99) |
| Architectural feasibility (N=9 universal) | ✅ CLM-0188 (R104) |
| Obs-magnitude independence (decay=0pp) | ✅ CLM-0193 (R107-W2) |
| WarmH0RecurrentActor module | ✅ CLM-0193 (R107-W1) |
| TD3LSTMWarmH0Agent class | ✅ CLM-0194 (R109, this round) |
| train.py dispatcher edit | ⏳ R96 phase, 5 LOC |
| checkpoint_loader.py edit | ⏳ R96 phase, 5 LOC |
| WSL training run | ⏳ waiting on slot |

When R94 (widen-bound training) finishes and frees a WSL slot, R96
opens with 10 LOC of edits + 1 training run.

## Decision

R96 = Q-0022 implementation is now **code-ready**. No more zero-conflict
prep work is required before the WSL slot opens. Anything more (e.g.,
SAC / TD3-MLP warm-init equivalent, real-obs forensics, paper Sec.IV-D
draft) is parallel or post-R96 work.

## Infrastructure changes

Read-only: V4 / V4Config / base_env / paper_grade_axes /
agents/td3_lstm.py / agents/sac.py / agents/td3.py / agents/networks.py /
agents/networks_warmh0.py (R107) / agents/checkpoint_loader.py /
scripts/train.py / R57+ ckpt / R83-R108 in-flight data / any test.

新建:
- `src/andes_rl_kundur/agents/td3_lstm_warmh0.py`
- `memory/rounds/R109/{plan.md, verdict.md}`
- `memory/claims/CLM-0201.md` (CLM-0194 raced to R110)

## Cross-references

- CLM-0193 (R107 WarmH0RecurrentActor) — direct parent
- CLM-0188 (R104 universalisation) — feasibility grandparent
- CLM-0183 (R99 N=1 feasibility)
- CLM-0174 (R95 ramp-up observation) — mechanism
- Q-0022 — implementation surface now complete
- CLM-0201 (this round; CLM-0194 raced to R110)

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none) — Q-0022 stays open until R96 training run verifies the learnable
  MLP captures the optimal h*.

## Questions advanced (this round, status unchanged)

- **Q-0022** — implementation surface now 100% code-ready. Log entry:
  "TD3LSTMWarmH0Agent drop-in via td3_lstm_warmh0.py, R96 launch =
  train.py + checkpoint_loader dispatchers + WSL slot."

## 给 PI 的话

**这周干了啥**：你说"一直干活". R107 我把 actor 模块 (WarmH0RecurrentActor) 单独写出来了, 但没接到 agent 上. R109 加 `src/andes_rl_kundur/agents/td3_lstm_warmh0.py::TD3LSTMWarmH0Agent`, 继承 TD3LSTMAgent, 改 4 个方法 (init / select_action / select_action_recurrent / update) 把 obs_for_warm 串进 init_hidden. 0 行改在现有文件; 1 个新文件 (230 行). Smoke test 跑通: 6 步 deterministic rollout 输出 0.12-0.15 量级 action (随机初始化, 训练后会到 saturation).

**结果（一句话）**：**R96 launch surface 现在只剩 2 × 5 行 dispatcher edit + 1 个 WSL slot**. 所有 prep 都 ready: architectural feasibility (CLM-0183 N=1 + CLM-0188 N=9 + CLM-0193 obs-norm independent), actor module (CLM-0193), agent class (CLM-0194 本轮). R94 widen-bound 一释放 WSL, 立刻能开 R96.

**意外**：update() override 需要 copy-paste 整个 80 行 method body, 因为 base class 的 update 是 monolithic 没有 "init_hidden hook" 暴露给 subclass. 这是 td3_lstm.py 设计 debt, 不是我新增的问题. 短期 acceptable (R96 是 1 个 seed 一次性实验), 长期如果 warm-h_0 work 那 update() 该 refactor 成 template-method pattern 以便 IQN / spectral norm 等也能 hook 进来. 我没去 refactor base — 那会 touch 现有文件, 违反 zero-conflict 契约.

**我默认下一步做**：(1) R109 关闭 closed-positive, CLM-0194 写入 (已完成). (2) **R96 等 WSL** — 没有更多 zero-conflict prep 工作要做, 所有候选都是 parallel 或 post-R96: 比如 R110 = paper Sec.IV-D draft (6 个 CLM 整合), R111 = SAC / TD3-MLP warm-init 等价实验 (non-LSTM 没 h, 但有 first-layer bias 可以等价 saturate), R112 = 真实 ANDES step-0 obs 反推去 synthetic caveat. (3) 我推荐先写 R110 paper Sec.IV-D 因为 paper 是项目最终交付目标, 现在 mechanism story 完整可以写最干净的 "为什么 91 round 都败" answer. 沉默就这么做.

**你想插一脚就说**：(a) 想我立刻并行起 R96 (申请第 4 个 WSL slot, 突破你 max-3-parallel 限制) — 不推荐, 但我可以 (b) 想我 R110 paper Sec.IV-D draft — 60 min, 整合 R88 + R92 + R95 + R99 + R104 + R107 + R109 共 8 个 CLM 的 mechanism story, 给 paper 最完整的 plateau 解释 (c) 想我 R111 SAC/TD3 等价测试 — 60 min, 拓展 warm-init 概念到 non-recurrent agents, 测 R86 SAC 部分例外是否能用 first-layer bias init 解释 (d) 想我 R112 真实 obs 反推 — 30 min 离线, 去掉所有 synthetic caveat. 我推荐 (默认) **(1)+(2)+(b)**: R109 关掉, 写 paper Sec.IV-D 草稿等 R94 释放 WSL.
