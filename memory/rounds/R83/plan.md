# R83 plan — Problem setup refactor (obs space), 修 Q-0016 + 测 R72_w4 hyper + obs augmentation combined

**Status**: ACTIVE (W1 跑中)
**Opened**: 2026-05-19
**Driver**: R82 verdict 推荐 "下一步走 problem setup 维度" (Q-0014 priority 1 = obs space refactor), PI 确认 "继续研究, 别管论文"
**Parent**: R57-R82 series 91 round-level algo trials 全 ≤ baseline 0.391 (CLM-0144)

## TL;DR

R57-R82 91 round 已证 algo 维度 plateau 真实 (CLM-0144). R83 转 obs space:
先修 Q-0016 (INCLUDE_OWN_ACTION_OBS env var → V4Config field 没传, final_eval
late-disable 路径 LSTM input dim mismatch crash, R81 W2 实测), 然后 3 wave
sequential 测 obs augmentation 在 R72_w4 hyper 下是否突破 baseline 0.391:
W1 own_action_obs (R49-α 实现但跟 R72_w4 hyper 没正确 combined), W2 time +
own_action combined (V4Config 互斥需解除 + base_env slot 重设计), W3 area-mean
freq 新 obs aug (3 个 new slot). 单 seed s54 × 75 ep 每 wave ~15 min.

## R57-R82 历史与本轮立论

- **R49-α** (CLM-0057): include_own_action_obs in V4 MLP 测 -21%. **negative**
- **R52** (CLM-0059 follow-up): include_time_obs 实现, R72 hyper 前未跟 SOTA combined
- **R72_w4** (current SOTA): td3_lstm LSTMCell, obs default 7-dim, geo=0.391
- **R81-W1** (time_obs + R72_w4 hyper): geo=0.049, 75 ep 没收敛 (obs_dim 7→8 重训)
- **R81-W2** (own_action_obs + R72_w4 hyper): **CRASH** final_eval (Q-0016 bug)

R83 立论: R49-α 用 V4 MLP, R52 用 R72 前 hyper, **R72_w4 LSTM + obs aug 的正确
combined 从未跑通**. 修 Q-0016 后 W1 应该出第一个 fair data 点.

## Q-0016 修复 (R83 第一步, done)

`scripts/train.py::build_v4_config()` 加 env var → V4Config field 转换:
```python
if include_action_env:
    overrides["include_own_action_obs"] = True
if include_time_env:
    overrides["include_time_obs"] = True
```

V4Config 是 single source of truth (ADR-0002 + R37 CLM-0040 fix 精神). env var
path 现在通过 V4Config field 传到 final_eval env. V4 regression 1e-9 仍 PASS (93s).

## Wave 设计

每 wave = R72_w4 baseline hyper (td3_lstm h64 tau=0.001 warmup=5 normalize-actions)
+ obs augmentation 改动. seed s54 75 ep smoke.

| Wave | obs augmentation | obs_dim | 前置 |
|---|---|---|---|
| **W1** | INCLUDE_OWN_ACTION_OBS=1 (prev action × 2 dim) | 7 → 9 | Q-0016 修 ✓ |
| **W2** | INCLUDE_TIME_OBS=1 + INCLUDE_OWN_ACTION_OBS=1 (combined) | 7 → 10 | 解除 V4Config 互斥 + base_env slot 重设计 |
| **W3** | 加 area-mean freq (area1_mean / area2_mean) 新 aug | 7 → 9 | base_env._build_obs 加 slot + V4Config 新 field |

Gate: 任一 wave geo ≥ 0.44 (+0.05 vs baseline) → R84 paper-grade 多 seed × 500 ep
持平 (∈ [0.34, 0.44]) → marginal, 收敛于 W3 阶段判定
全部 ≤ 0.34 (-0.05) → 写 R83 negative finding, 转 R84 multi-agent structure (CTDE 自写 / message passing)

## 资产保护契约

不动 V4 / V4Config 现有字段 / base_env / paper_grade_axes / TD3LSTMAgent / R57+ ckpt.
**新建** V4Config field (W3 需): `include_area_mean_freq_obs: bool = False` + base_env obs slot.
**改动** (R83 vetted): build_v4_config env-var-to-config bridge, V4Config 互斥放宽 (W2 触发后).

## 资产 + 测试不变量

- V4 regression test 1e-9 必须仍 PASS (W2/W3 修 base_env 后要重 run)
- R57+ SOTA ckpt eval 行为不变 (W3 add new V4Config field default=False)
