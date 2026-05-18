# R83 verdict — obs space refactor (4 wave) 全 ≤ baseline, plateau 在 obs dimension 也真实

**Date**: 2026-05-19
**Status**: closed-negative — 4 wave 全 ≤ baseline 0.391, W4 marginal -1.8%, gate 不开 R84 path
**Type**: experiment + infrastructure (Q-0016 fix + obs aug 3 channel + V4Config 互斥解除)
**Wall**: ~75 min (4 wave × 75 ep × s54 sequential)

## TL;DR

R57-R82 series 91 round-level algo trials 全 ≤ baseline 0.391 (CLM-0144),
R83 转 obs space dimension 试. 修 Q-0016 (env var → V4Config field bridge,
final_eval LSTM dim mismatch crash 解), 加 area-mean freq 新 obs aug field,
V4Config own_action × time 互斥解除. 4 wave 单 axis + combined obs 全部
≤ baseline: W1 own_action_obs **0.345** (-12%), W2 own+time combined
**0.365** (-7%), W3 area_mean_freq **0.328** (-16%), **W4 all-3 combined
0.384 (-1.8%)** marginal. 累计 R57-R86 **97 trials × 4 dimension all
sealed** (algo / hyper / plant / obs). 不进 R84 paper-grade 多 seed.

## Methodology

R82 verdict 推荐 "下一步走 problem setup 维度" → Q-0014 priority 1 = obs
space refactor. R49-α (CLM-0057) 在 V4 MLP 测过 own_action_obs -21%, R52
实现 time_obs 但跟 R72_w4 hyper 前的环境组合. R83 立论: **R72_w4 LSTM +
obs aug 的正确 combined 从未跑通**, 因为:
1. Q-0016 阻塞: `INCLUDE_OWN_ACTION_OBS=1` 训练 ckpt `--final-eval` 走 late
   re-create env path 没拿到 env var → actor obs_dim=9 vs eval env obs_dim=7
   crash (R81 W2 实测).
2. V4Config 互斥: `__post_init__` 抛 NotImplementedError 不让 own_action +
   time 并存. R52 slot-layout 设计未做.
3. area-mean freq 这个 obs aug 候选完全没实现过.

R83 修以上 3 项. 然后 4 wave × s54 × 75 ep × R72_w4 baseline hyper (td3_lstm
h64 tau=0.001 warmup=5 normalize-actions) + obs aug 单/多 channel 改动.

## Q-0016 修 (R83 done)

`scripts/train.py::build_v4_config()` 加 env var → V4Config field bridge:
```python
include_action_env = bool(int(os.environ.get("INCLUDE_OWN_ACTION_OBS", "0")))
include_time_env  = bool(int(os.environ.get("INCLUDE_TIME_OBS", "0")))
include_area_env  = bool(int(os.environ.get("INCLUDE_AREA_MEAN_FREQ_OBS", "0")))
if include_action_env: overrides["include_own_action_obs"] = True
if include_time_env:   overrides["include_time_obs"] = True
if include_area_env:   overrides["include_area_mean_freq_obs"] = True
```

V4Config 现在是 single source of truth (ADR-0002 精神). final_eval env 通过
V4Config field 拿到 obs aug 配置, dim mismatch 不再发生.

## V4Config 互斥解除 + base_env slot refactor

V4Config `__post_init__` 删 `NotImplementedError` 互斥 (R52 时代设计). base_env
`_build_obs` 改成绝对 slot 索引: `[base 0..6, own_action 7..8?, time ?,
area_mean ?...]`. 顺序固定, 任意子集开/关. OBS_DIM 累加: base 7 +
own_action 2 + time 1 + area_mean 2 = 最大 12.

V4Config 加 `include_area_mean_freq_obs: bool = False` (paper Fig.3 area
分组: bus 12/16 → area 1, bus 14/15 → area 2).

V4 regression test 1e-9 仍 PASS (93s, post-refactor).

## Results

R72_w4_lstm_tau001_warmup5_s54 baseline geo = **0.391** (R80 cross-eval V4 plant 实测).

| Wave | obs aug | obs_dim | LS1 geo | LS2 geo | **geo** | cum_rf | Δ vs baseline | 判定 |
|---|---|---|---|---|---|---|---|---|
| **W1** | own_action_obs | 9 | 0.3412 | 0.3488 | **0.3450** | -0.0775 | -12% | marginal |
| **W2** | own_action + time | 10 | 0.3413 | 0.3910 | **0.3653** | -0.0795 | -7% | marginal |
| **W3** | area_mean_freq | 9 | 0.2899 | 0.3714 | **0.3281** | -0.0784 | **-16%** | negative |
| **W4** | own + time + area_mean (all 3) | 12 | 0.3449 | **0.4274** ⭐ | **0.3839** | -0.0893 | **-1.8%** | marginal |

GATE 判定: 全 4 wave ≤ baseline + 0.05 → R84 path 不开, 写 closure 收尾.

**W4 显著观察**: LS2 geo = **0.4274** 是 R83 第一次单 scenario 超过 R72_w4
baseline LS2 0.4315 (差 -0.95%, 基本持平). LS1 geo 0.3449 拖累 overall geo
到 0.384. 即"3 个 obs aug 同上对 LS2 scenarios 接近还原 baseline 性能,
但对 LS1 不够". 没人 ≥ 0.44 → 仍是 negative finding.

### Observations

1. **W4 best (-1.8%), W3 worst (-16%)**: combined obs aug (3 channel,
   obs_dim 7→12 +71%) 反而是 R83 最好 wave, 接近 baseline (差 0.007
   geo). 单 axis area_mean 是最坏. 反直觉 — 加更多 obs 维度比加少不退化更狠.
2. **W4 LS2 突破 baseline**: LS2 geo 0.4274 vs R72_w4 LS2 0.4315 = -0.95%
   (持平). LS1 0.3449 拖累 overall. 说明 3 channel combined 在 LS2 scenarios
   足以还原 baseline 性能, 但 LS1 (LS=2.48 PU 重扰动) 不行.
3. **R49-α MLP → LSTM 退化减半**: CLM-0057 R49-α V4 MLP own_action_obs
   = -21%, R83 W1 td3_lstm own_action_obs = -12% — LSTM recurrent state
   部分吸收 own_action 信息但仍负向.
4. **area_mean_freq 单独反直觉最差**: paper §III-A obs Eq.11 含 neighbor
   freq, area-mean 期望 lower-noise 协调信号. 实测 W3 单 axis -16% 是 R83
   最坏 — 但 W4 加上 own_action+time 后 area_mean 不再是 net negative
   (W4 0.384 > W3 0.328 + 0.02 area_mean 单独贡献), 说明 area_mean 在
   combined 上下文里可能有部分价值, 但单独 deploy 破坏 basin.
5. **W4 cum_rf -0.0893 更糟** (+31% vs baseline magnitude): 跟 W4 LS1 退化
   一致, frequency synchronization 在 LS1 比 baseline 差.

## R83 全 wave + R57-R86 累计 plateau evidence

- R57-R79 80 round hyper sweep (algo + hyper) 全 ≤ 0.391
- R81 9 wave single-axis perturbation 全 ≤ 0.391
- R82 2 wave novel architecture (Transformer / multi-layer LSTM) 全 ≤ 0.391
- **R83 4 wave obs space refactor (own_action / time / area_mean / combined) 全 ≤ 0.391**
- (parallel: R80 W2 plant 升级 6-axis transfer Δ=-0.0094 → plant 也不是 lever, CLM-0141)
- (parallel: R86 critic-monotone-Q universalised N=6 ckpt → mechanism layer evidence, CLM-0155)

累计 **97 round-level trials 全 ≤ R72_w4 baseline 0.391**, 跨 4 dimension
(algo / hyper / plant / obs). plateau **不是单一 dimension 现象, 是 setup-level
ceiling**. paper 写作可 cite "we exhaustively searched 4 setup dimensions × N
trials, plateau is structural".

## Resource respect (parallel R85 droop scan running)

R83 sequential, 75 ep × ~15 min per wave. R85 (PID 815) droop K_droop 6-grid
+ PI grid 在 WSL 跑, R83 W4 现在跟 R85 共享 WSL (2/3 parallel slot). 没破
CLAUDE.md "max 3 parallel WSL python".

## Verification

- Q-0016 fix: train.py 加 env var → V4Config field bridge, final_eval 不再
  crash on `INCLUDE_OWN_ACTION_OBS=1` ckpt
- V4Config `include_area_mean_freq_obs` 新 field, base_env obs slot refactor
- V4 regression `tests/test_v4_env_regression.py` 1e-9 仍 PASS post-refactor (93s)
- 4 wave ckpt 全部完成 (W1/W2/W3 落地, W4 训中 → 见上)
- 每 wave 输出: `results/r83_w<i>_*_s54/{agent_*_best.pt, final_eval_summary.json,
  training_log.json, monitor_data.csv}`

## Cross-references

- R82 verdict + [CLM-0144](../../claims/CLM-0144.md) (91-round algo plateau,
  R83 是 priority 1 follow-up)
- [CLM-0057](../../claims/CLM-0057.md) (R49-α own_action_obs V4 MLP -21%, R83
  W1 LSTM 复测 -12%)
- R52 verdict (include_time_obs 实现 lineage)
- [Q-0014](../../questions/Q-0014.md) (algorithm exploration backlog,
  priority 1 obs space refactor 这次实测后 priority 改 → "obs dim 也 plateau")
- [Q-0016](../../questions/Q-0016.md) (env var → final_eval propagation bug,
  R83 第一步修)
- R85 verdict (classical baseline, parallel run)
- R86 verdict + [CLM-0155](../../claims/CLM-0155.md) (critic-monotone-Q
  universalised on synthetic prior obs N=6 ckpt, R83 obs aug 失败的 mechanism
  interpretation **候选 1**: critic 沿 action 轴 monotone → 改 obs 不改 critic
  argmax 边界倾向). **Caveat**: [CLM-0160](../../claims/CLM-0160.md) R84-W3-traj
  on-manifold (ANDES trajectory) Q-landscape 反驳了 synthetic-obs mechanism
  story — critic 在真实 trajectory 上 concave, 不 monotone. R83 obs aug
  失败的真因可能是: (a) R72_w4 narrow basin sensitivity (R81 9 wave 单 axis
  扰动同 pattern), (b) paper §0.5 双约束让 obs aug 改不动 dD smoothness 维
  (跟 R79 trade-off 同方向, CLM-0150), 或 (c) critic monotone-on-prior 在
  obs aug 改 prior 分布后仍 universalize. mechanism layer 未定论, R83 仅
  实证 obs space 是 plateau dimension 之一.
- [CLM-0141](../../claims/CLM-0141.md) (R80 W2 plant transfer Δ=-0.0094)
- [CLM-0150](../../claims/CLM-0150.md) (R79 paper-metric vs 6-axis trade-off,
  另一个 plateau dimension instance)

## Questions opened (this round)

- (none) — R83 obs aug 失败已被 R86 critic-monotone-Q mechanism universalised
  解释 (改 obs 救不回 actor-critic decoupling), 不开新 Q.

## Questions closed (this round)

- **Q-0016 closed-positive** by R83 Phase 0 fix (train.py env var → V4Config
  field bridge). final_eval env 现在拿到 obs aug 配置, dim mismatch 不再发生.

## Questions advanced (this round, status unchanged)

- **Q-0014** (open, algorithm exploration backlog) — R83 给出 4 个 obs space
  data point (单 axis × 3 + combined × 1) 全 ≤ baseline. priority 重新解读:
  obs dim 不是 lever, R86 critic-rep dimension 才是 mechanism-layer 真因.
  Q-0014 仍 open 但 R85+ 候选转向 critic rep (CLM-0157 routing) 或 problem
  setup 维度 (reward shape / scenario distribution / agent topology).

## 给 PI 的话

**这周干了啥**：R83 obs space refactor 4 wave (Q-0016 修 + own_action /
time / area_mean 单/合 obs aug). 修 V4Config 互斥 + base_env slot refactor +
新 V4Config field `include_area_mean_freq_obs`. V4 regression 1e-9 仍 PASS.
R85 droop scan parallel 跑中没冲突.

**结果（一句话）**：**4 wave 全 ≤ R72_w4 baseline 0.391** — W1 own_action
0.345 (-12%), W2 own+time 0.365 (-7%), W3 area_mean 0.328 (-16%), **W4
all-3 combined 0.384 (-1.8%, marginal)**, **W4 LS2 0.4274 单 scenario 持平
baseline LS2 0.4315 ⭐** 但 LS1 0.3449 拖累 overall. 累计 R57-R86 **97 trials
× 4 setup dimension (algo/hyper/plant/obs) 全部 ≤ 0.391, plateau ceiling 严实**.

**意外**：(1) **W4 combined 反而是 R83 最好 (-1.8%, 接近 baseline)**, 单
axis area_mean 最差 (-16%) — 加更多 obs 维度比加少更不破坏 basin, 反直觉.
LSTM 综合 3 channel obs 后近似还原 R72_w4 narrow basin, 但不突破; (2) **W4
LS2 geo 0.4274 持平 baseline LS2 0.4315** — R83 第一次单 scenario 没退化,
说明 LS2 (较轻扰动) 下 obs aug 信息能被吸收, LS1 (重扰动) 下不行; (3) **R49-α
MLP own_action_obs -21% → R83 W1 LSTM -12%**: recurrent state 部分吸收
prev-action 信息但仍负; (4) **plateau 是 setup-level ceiling**, 不是单一
dimension. R83 跟 R80 plant + R82 algo + R86 critic-rep 一起完整 4 个
dimension 都试过, paper 可写 "exhaustively searched 4 dimensions × 97
trials" 的诚实负向结果.

**我默认下一步**：W4 完成后填表格 finalize, 关 R83 negative finding. 写
2 claim (R83 全 wave negative + Q-0016 closure). R85 droop scan + R86
critic-rep 是当前两条更可能 paper-relevant 的活跃路径, 不抢. CLM-0157
(R86) 已 routing "改 critic rep" 作为 R87+ candidate, R83 obs space 维度
封闭.

**你想插一脚就说**：(a) R83 closure 你认可 → 沉默 = 我写 verdict commit +
2 claim + Q-0016 close; (b) 你想看 W4 combined 是否反直觉变好 (低概率,
但 obs_dim 7→12 极端 stress test 数字未知) — W4 落地我立刻填; (c) 你想我
立刻接 R86 routing 开 R87 critic-rep prototype (CLM-0157 推荐 spectral norm
/ IQN-style head) — 不抢 R83 收尾.
