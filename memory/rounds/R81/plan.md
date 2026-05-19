---
round: R81
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R81 Plan — 算法侧探索 sweep (突破 V4 attractor 0.137 / R72_w4 SOTA 0.391)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: Q-0014 (R80 verdict 提出 algorithm-side exploration backlog), PI 确认 "启动算法优化，用什么算法，有可能提升的全部使用上"
**Parent**: R80 verdict CLM-0141 (W2 plant 升级 6-axis Δ=-0.94% 证否 plant 是瓶颈)

## TL;DR

R80 证否 plant 是瓶颈, R81 转 algorithm-side 9 个候选 (5 个 Tier 1 obs/reward
augmentation + 4 个 Tier 2 algo / hyper sweep). Sequential single-seed × 75 ep
smoke (每个 ~11 min wall, 总 ~2 hr), 跑完看哪些 6-axis geo 突破 R72_w4 SOTA
0.391 (gate: ≥ +0.05 = 0.44) 或至少超 V4 attractor 0.137. winning 候选进
Tier 3 多 seed × 500 ep paper-grade train.

## Baseline (R80 实测)

| Ckpt | algo | hidden | obs | reward | 6-axis geo (V4 plant) |
|---|---|---|---|---|---|
| R72_w4_LSTM_s54 | td3_lstm | 64 | 7-dim default | paper_faithful+phi_abs=50 | **0.391** ← SOTA |
| R21_h50_s49 | sac MLP | ? | 7-dim default | paper_faithful | 0.444 (lucky basin, 不可复现) |
| V4 multi-seed attractor | sac MLP | 128 | 7-dim default | paper_faithful | 0.137 ± 0.005 (stall) |

## Tier 1 — obs/reward augmentation (sequential, each ~11 min)

每个 candidate = R72_w4 hyper 基础上 +1 改动. 单 seed s54.

| Wave | Candidate | 改动 | 假设 |
|---|---|---|---|
| **R81-W1** | `include_time_obs=1` | INCLUDE_TIME_OBS=1 env var, obs+=1 维 (episode phase) | R52 probe + R72_w4 hyper 没 combined 过. 直接针对 CLM-0057/0058/0059 temporal-flatness bottleneck. |
| **R81-W2** | `include_own_action_obs=1` | INCLUDE_OWN_ACTION_OBS=1, obs+=2 维 (prev action) | R49-α 在 V4 MLP 测过 -21% negative. 但 LSTM + R72_w4 hyper 没测, 也许 LSTM hidden 已经吸收 prev action 信息 → 这个 negative 可能在 LSTM 下变 neutral 或 positive. |
| **R81-W3** | `phi_settle=10.0` | --phi-settle 10 (R33 framework, default 0) | paper Eq.14 没 settle bonus, 但项目 R33 框架支持. 直接惩罚 settling 慢, 也许能突破 6-axis axis 3. |
| **R81-W4** | `lambda_smooth=-1.0` | LAMBDA_SMOOTH=-1.0 env var, R50 anti-flatness | CLM-0057 temporal-flatness 的另一种打法. R50 测过 negative on V4 MLP, R55 windowed 也没救. LSTM + R72 hyper 没试. |
| **R81-W5** | `include_time_obs=1` + `phi_settle=10.0` | combined W1+W3 | 如果 W1 W3 单独都有信号, combined 看是否 additive. 跑在 W1 W3 之后. |

## Tier 2 — algo / hyper sweep (sequential, each ~11 min)

| Wave | Candidate | 改动 | 假设 |
|---|---|---|---|
| **R81-W6** | `algo=sac` + hidden=128 | SAC MLP base (跟 R21 lucky basin 同 algo 但当前 hyper) | R21 lucky 0.444 是 SAC MLP. SAC MLP + R72 时代的 hyper (tau / lr / normalize) 没系统跑过. |
| **R81-W7** | `algo=td3` + hidden=128 | TD3 MLP | TD3 没 LSTM 也能突破 attractor 吗? algo selection 对 plant 是否 sensitive. |
| **R81-W8** | `hidden=128` (td3_lstm) | R72_w4 hyper + 翻倍 hidden | network capacity 是否瓶颈. R68 试过 h128 W4e 但跟当前 SOTA hyper 没 combined. |
| **R81-W9** | `gamma=0.95` (td3_lstm) | discount 缩短, 让 agent 更看近期 reward | R72 用 default 0.99. gamma 是否 SOTA-locked. |

## Tier 3 — paper-grade multi-seed (only if Tier 1+2 winner)

- 3 seed (s51 s52 s54) × 500 ep × Tier 1+2 winning combo
- 跟 R57+ SOTA 走的同一 pipeline
- 目标: 6-axis geo ≥ 0.45 (突破 R72_w4 SOTA 0.391 + R21 lucky 0.444 上限)

## Execution protocol

- Sequential single-seed smoke 75 ep (每个 ~11 min wall)
- 每个 wave 完成后 `--final-eval` 自动跑 LS1+LS2 → JSON 自动 score 6-axis geo
- 不动 V4 / V4Config / paper_grade_axes (Asset 4); 只调 train.py CLI + env var
- 每个 wave 产物 `results/r81_w<N>_<short_desc>_s54/` + stdout log
- 总 wall ≈ 9 × 11 min = ~100 min

## Stopping rules

- 任一 wave 训练崩 (NaN / TDS fail > 50%) → 记入 verdict negative, 跳下一个
- W1-W9 全跑完, 选 6-axis geo ≥ 0.44 (SOTA + 0.05) 的进 Tier 3
- 全部 ≤ 0.42 → Tier 3 不开, R81 verdict "all 9 candidates within plateau noise band", 转向 Q-0014 阻塞
- 任一 ≥ 0.50 → 立即 Tier 3 跑 3 seed × 500 ep 验证

## 资产保护

不动:
- V4 env / V4Config / base_env / paper_grade_axes (Asset 4)
- 任何 R57+ SOTA ckpt
- V5 env (R80 产物保留)
- WSL R79 训练 (handoff 标注 PID 388, 可能已完成)

新建:
- `scripts/r81_algo_sweep.py` (sequential launcher + score collector)
- `results/r81_w{1..9}_*` 9 个 ckpt 目录
- `results/r81_summary.json` (汇总 9 wave 的 6-axis geo + cum_rf)
- `memory/rounds/R81/verdict.md` (跑完写)
- 视结果 1-3 个 new claim
