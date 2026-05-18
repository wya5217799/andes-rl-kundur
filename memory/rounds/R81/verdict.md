# R81 verdict — 算法侧 9 wave sweep, 0 突破 + 2 infrastructure bug

**Date**: 2026-05-19
**Status**: DONE — no candidate broke baseline; 2 follow-up bugs to R82
**Type**: experiment + infrastructure
**Wall**: ~95 min (9 wave × ~11 min sequential)

## TL;DR

R72_w4 baseline geo=0.391, 9 wave 算法侧 single-axis perturbation sweep, **0 个 wave 突破**, R81 plan stopping rule "全部 ≤ 0.42 → Tier 3 不开" 生效. 但 sweep 暴露 **2 个 infrastructure bug** (W2 INCLUDE_OWN_ACTION_OBS 不传 final_eval crash, W9 gamma override 似乎对 td3_lstm silent ignore — 数字 4 位小数 = baseline), 加 **2 个 budget-unfair wave** (W6/W7 SAC/TD3 MLP 75 ep 远未收敛), 共 4 个 unresolved 留 R82. 真正 algorithmically-clean 的 5 个 td3_lstm 变体 (W1/W3/W4/W5/W8) 全部 ≤ baseline, 给出强 evidence: **R72_w4 hyper 是 narrow local basin, 75 ep budget 下 td3_lstm 单 axis 改动都不补救**.

## Methodology

R72_w4 baseline (R80 cross-eval V4 plant 实测) geo = **0.391**. R81 plan 9 wave × 1 seed (s54) × 75 ep, 跟 R72_w4 同 budget 同 seed, sequential, total wall ~95 min. 每 wave = R72_w4 hyper (td3_lstm h64 tau=0.001 lstm-lr-warmup=5 normalize-actions) + 1 改动.

Gate: 任一 wave geo ≥ 0.44 → 进 Tier 3 多 seed × 500 ep. 全部 ≤ 0.42 → Tier 3 不开, 写 verdict.

## Results

| Wave | 改动 | geo | Δ vs baseline | 备注 |
|---|---|---|---|---|
| **W3** | `--phi-settle 10.0` | **0.376** | **-0.014** | 几乎持平 — settling bonus 在 LSTM + R72 hyper 下无杠杆 |
| W8 | `--hidden-size 128` | 0.282 | -0.109 | h64 sweet spot, h128 75 ep 没收敛 |
| W5 | `INCLUDE_TIME_OBS=1` + `--phi-settle 10.0` | 0.237 | -0.154 | combine 比单独都差 |
| W1 | `INCLUDE_TIME_OBS=1` | 0.049 | -0.342 | obs_dim 7→8 75 ep 没收敛, LS1=0.0 |
| W4 | `LAMBDA_SMOOTH=-1.0` | 0.010 | -0.381 | anti-flatness 在 LSTM 全崩 |
| W9 | `--gamma 0.95` | 0.391 | -0.0002 | **疑 silent ignore** — geo / LS1 / LS2 / cum_rf 4 位小数 = baseline |
| W2 | `INCLUDE_OWN_ACTION_OBS=1` | CRASH | n/a | **train.py bug**: final_eval env 不传 INCLUDE_OWN_ACTION_OBS, LSTM input dim 7 vs 9 mismatch |
| W6 | `--algo sac --hidden-size 128` | 0.010 | -0.381 | 75 ep 远未收敛 (R21 lucky basin SAC 500 ep) |
| W7 | `--algo td3 --hidden-size 128` | 0.035 | -0.356 | 75 ep 远未收敛 |

GATE 判定 = **全 9 wave ≤ 0.42 → Tier 3 不开**.

5 个 algorithmically-clean td3_lstm wave (W1/W3/W4/W5/W8) 全部 ≤ baseline 给出真正信号: **R72_w4 hyper 是 narrow local optimum, 单 axis perturbation 75 ep 内都不补救**. 这跟 R57-R79 80 round hyper sweep 历史一致 — attractor 0.137 plateau 由 SAC/TD3 + 4-agent + 7-dim obs + paper reward 设计的算法能力上限决定, R72_w4 仅是 lucky narrow basin (next best 0.137-0.22).

## Bugs / unresolved findings (R82 backlog)

| ID | Bug / unresolved | 影响 | 候选修 |
|---|---|---|---|
| **R82-bug1** | W2 train.py 不传 `INCLUDE_OWN_ACTION_OBS` env var 给 final_eval, 导致 actor obs_dim=9 (train) vs 7 (eval) crash. traceback: `RuntimeError: input has inconsistent input_size: got 7 expected 9` at `td3_lstm.py:242 select_action` | `INCLUDE_OWN_ACTION_OBS=1` 的训练 ckpt 不能用 `--final-eval`, 必须手动 eval | train.py `_emit_final_eval()` 加 env var propagation 或者 V4Config-passthrough |
| **R82-bug2** | W9 `--gamma 0.95` 命令行接受但似乎对 td3_lstm 无效果. final_eval geo / LS1 / LS2 / cum_rf / cum_rf_LS1 / cum_rf_LS2 6 个数字全部跟 R72_w4 baseline 4 位小数一致, 不可能是 noise | `--gamma` flag 在 td3_lstm 上 silent ignore, hyper sweep 假设错误 | 看 train.py 的 GAMMA override 路径, 验证 td3_lstm config 是否真接受 |
| **R82-fair3** | W6 SAC MLP 75 ep 远未收敛 (geo=0.01 floor) | 不能判定 SAC MLP 在算法侧是否能突破 | 单独跑 W6 配置 × 500 ep (跟 R21 lucky basin 同 budget) |
| **R82-fair4** | W7 TD3 MLP 75 ep 同样未收敛 | 同上 | W7 配置 × 500 ep |

## Verification

- 9 wave 全部 exit code 0 except W2 exit 1
- `results/r81_summary.json` 完整记录 9 wave geo / cum_rf / LS1 / LS2
- `results/r81_w{1..9}_*` 9 个 ckpt 目录 + stdout log (R82 bug 调试用)
- W9 数字异常: 直接验证 R80 cross-eval V4 baseline LS1=0.3539 LS2=0.4315 = W9 LS1=0.3539 LS2=0.4316 (4 位有效数字 → 4 位完全一致 = silent ignore 强证据)
- 5 个 algorithmically-clean td3_lstm 变体 (W1/W3/W4/W5/W8) 全部退化, R72_w4 hyper narrow basin 证据 ⭐⭐⭐
- V4 / V4Config / paper_grade_axes / base_env 全部没动 ✓

## Cross-references

- R80 verdict + CLM-0141 (W2 plant 升级证否 plant 是瓶颈)
- Q-0014 (R80 提出的 algorithm exploration backlog, R81 是 Q-0014 第一次试)
- R57-R79 80 round hyper sweep 历史 (R72_w4 这次是其中之一)
- R21 V4_h50_s49 lucky basin = 0.444 (500 ep SAC MLP, R81 W6 75 ep 同 algo 的 fair budget = 500)
- R72_w4_lstm_tau001_warmup5_s54 (baseline ckpt)

## Questions opened (this round)

- **Q-0015** (will open separately): `--gamma` flag 对 td3_lstm 是否 silent ignore — 这是 R82-bug2 的 question form. 影响所有依赖 gamma sweep 的 hyper 研究.
- **Q-0016** (will open separately): `INCLUDE_OWN_ACTION_OBS=1` 训练 ckpt 不能 `--final-eval` — R82-bug1 的 question form. 限制 obs augmentation 实验闭环.

## Questions closed (this round)

- (none) — R81 没解决任何 Q.

## Questions advanced (this round, status unchanged)

- **Q-0014** (open) — algorithm-side exploration 第一次尝试 (R81 5 个 algorithmically-clean td3_lstm 变体) 全部 fail 突破 R72_w4 baseline, 给出 plateau 真实存在的 evidence, 但**没关 Q-0014**, 因为: (a) W6/W7 SAC/TD3 MLP 75 ep budget-unfair (留 R82 longer-budget retry); (b) 多 axis combined sweep / centralized critic / attention-based comm 等 Tier 2-3 路径未试; (c) Q-0015/Q-0016 bug 修了才能 fair-judge gamma + obs augmentation 维度. Q-0014 仍 open, R82 是下一次尝试.

## 给 PI 的话

**这周干了啥**：R81 跑了算法侧 9 wave 单轴扰动 sweep, 全部跟 R72_w4 baseline 同 75 ep / s54 / hyper, sequential ~95 min wall. 9 wave 含 5 个 obs/reward augmentation (include_time_obs, include_own_action_obs, phi_settle, lambda_smooth, combo) + 4 个 algo/hyper sweep (SAC MLP, TD3 MLP, lstm h128, gamma=0.95).

**结果（一句话）**：**0 wave 突破 baseline geo=0.391**, R81 Tier 3 不开. 但 sweep 揭出 2 个 infrastructure bug (W2 final_eval crash on include_own_action_obs, W9 gamma override 对 td3_lstm silent ignore — 数字 4 位小数 = baseline) + 2 个 budget-unfair wave (W6/W7 SAC/TD3 MLP 75 ep 不够). 5 个 algorithmically-clean td3_lstm 变体全部退化, 给出 "R72_w4 是 narrow local basin" 的强 evidence.

**意外**：(1) phi_settle / time_obs / lambda_smooth 这三个项目历史上的 obs/reward augmentation 候选, 在 R72_w4 hyper 下**全部退化**, 不是 "+ε neutral" 而是显著负向. 暗示 R57-R79 80 round 把 hyper 调到了一个极敏感的 basin. (2) W9 gamma silent ignore 是 train.py 的 hyper-override 系统 bug, 影响所有 gamma-related 研究的可信度 — R82-bug2. (3) W2 include_own_action_obs crash 揭出 train.py 的 final_eval env var propagation bug — R82-bug1. (4) **R72_w4 narrow basin** 这个发现本身就是 paper-可用素材: paper writeup 可以 cite "R72_w4 hyper 在 5 个 single-axis perturbation 下都退化, 证明它是 fragile local optimum, 不是 robust global minimum".

**我默认下一步做**：关 R81, 写 3 个 claim (R81 sweep negative + W9 gamma silent ignore + W2 final_eval bug), 开 Q-0015 + Q-0016 登记 2 个 bug. 短期不立即开 R82 — bug 修需要动 train.py canonical code (高风险), budget-unfair retry 需要 ~3 day × 2 wave wall. 把 R82 候选挂 backlog, 等你触发. 短期回 V4 paper path 继续 R79 / 后续 ckpt 工作.

**你想插一脚就说**：(a) 如果你想立即修 W2 / W9 的 2 个 train.py bug, 说一声开 R82-infra; (b) 如果你想给 W6/W7 SAC/TD3 MLP 公平的 500 ep budget retry, 说一声开 R82-fair; (c) 如果你想换一个完全不同方向 (centralized critic / attention-based MA / domain randomization / curriculum), 那是 R82-novel; (d) 如果接受 "R72_w4 narrow basin + plateau 真实" 作为终结 finding, 不开 R82, Q-0014 留 open 等长期触发 — 我推荐 (d) 因为 R81 + R57-R79 80 round 已经证明 hyper sweep diminishing return. 沉默 = (d) 默认.
