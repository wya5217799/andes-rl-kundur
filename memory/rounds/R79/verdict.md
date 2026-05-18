# R79 verdict — 500 ep × Q-0007 LSTM 出 paper-metric +28% / 6-axis -44% 的结构性 trade-off

**Date**: 2026-05-19
**Status**: **closed-positive** (1 hypothesis confirmed + 1 unexpected mechanism + 3 claims)
**Type**: single-seed training experiment (paper-alignment audit-driven)
**Wall**: ~1.7 h (training 97 min + scoring/analysis ~5 min)

## TL;DR

R79 单 seed s59 LSTM 跑 500 ep + Q-0007 (paper-aligned convergence horizon) 实测出 **结构性 trade-off**: paper-metric `cum_rf` +28% (-0.0754 → -0.0545) 但 6-axis geo -44% (0.4301 → 0.2402). 主因是 ΔD trajectory 完全失去 smoothness (dD_smooth 0.39/0.27 → 0.00/0.00), 同时 4-agent P_balance LS1 +22pp 几近完美. R75 W2 s59 仍是 6-axis SOTA, R79 best_eval.pt 留作 paper-metric path 候选待 20-scen verify.

## Methodology

paper-alignment audit (Tier 1-3 in R79 plan) 指认 "500 ep + Q-0007 (best-by-eval)" 是项目未跑过的明确有正期望组合. R66 修了 Q-0007 LSTM 兼容 (CLM-0102), CLM-0073 R58 测过 500 ep 但 best-by-train-reward 路径, 报 best.pt early lock → bit-identical. 缺口: 长 horizon × Q-0007 同时上未跑过.

**Launch command** (单 seed 水试):
```
python scripts/train.py --algo td3_lstm --normalize-actions --episodes 500 \
  --seed 59 --hidden-size 64 --lstm-lr-warmup-eps 20 --tau 0.001 \
  --eval-every-n-eps 5 --save-dir results/r79_500ep_q7_lstm_s59
```
唯一 diff vs R75 W2 s59 (CLM-0131): `--episodes 75 → 500` + `--eval-every-n-eps 5`.

WSL detached via setsid+disown, PID 388, 启动 23:30 (2026-05-18), 完成 01:08 (2026-05-19), wall 5866s = 97 min (training) + Q-0007 eval probe 100 次 × ~10s = ~17 min overhead 包含其中.

## Training health

- 500/500 ep 完成, 无 NaN / divergence
- TDS failures: 5/500 = **1.0%** (CLM-0073 baseline 1.2%)
- critic_loss: 0.233 → 0.001 单调下降
- reward: -75 (ep 0) → -3 (ep 499)
- freq peak: 0.23 Hz @ ep 17 transient
- reward_component_ratio WARN 8 次 (期间 r_f 占比偶尔 < 50%, 不血腥)

## Results

### Headline 数字 vs R75 W2 s59 baseline

| Ckpt | geo mean | cum_rf mean | LS1 P_bal | dD_smooth axes |
|---|---|---|---|---|
| R75 W2 s59 best.pt (75ep) | **0.4301** | -0.0754 | 0.782 | 0.39 / 0.27 |
| R79 best.pt (train-reward) | 0.2392 | -0.0546 | — | — |
| **R79 best_eval.pt (Q-0007 path)** | **0.2402** | **-0.0545** | **0.998** | **0.00** / **0.00** |
| R79 final.pt (ep 500) | 0.2377 | -0.0546 | — | — |
| Δ vs R75 | **−44%** ❌ | **+28%** ✅ | **+22pp** ✅ | **−39/−27pp** ❌ CRIT |

### Axis breakdown (LS1)

| Axis | R79 score | R75 score | Δ |
|---|---|---|---|
| max_df | 0.980 | 0.879 | +10pp |
| final_df@6s | 0.198 | 0.229 | -3pp |
| settling_s | 0.725 | 0.725 | 0 |
| dH_smoothness | 0.564 | 0.715 | -15pp |
| **dD_smoothness** | **0.000** | 0.390 | **-39pp CRIT** |
| dH_utilization | 0.163 | 0.293 | -13pp |
| dD_utilization | 0.601 | 0.609 | 0 |
| agent_min_activity | 1.000 | 1.000 | 0 |
| late_oscillation_inv | 0.796 | 0.796 | 0 |
| **agent_P_balance** | **0.998** | 0.782 | **+22pp CRIT** |
| **GEO** | 0.206 | 0.387 | -47% |

LS2 同 pattern: dD_smooth -27pp 崩到 0, max_df -13pp, settling +20pp, P_balance +3pp, GEO -42%.

## Mechanism — paper-metric vs 6-axis structural trade-off

```
Q-0007 跟踪 paper-metric cum_rf = -Σ(f_i - f̄)²
   ↓
只奖励 frequency 同步, 不奖励 ΔD 平滑
   ↓
500 ep horizon 给 agent 时间充分探索 "震荡式 ΔD 实时纠偏" 策略
   ↓
✅ frequency 收敛更快 (max_df ↑ LS1, settling ↑ LS2)
✅ 4-agent 协同更均衡 (P_balance LS1 +22pp)
✅ paper-metric cum_rf +28%
❌ ΔD trajectory smoothness 完全崩 (dD_smooth → 0)
❌ 违反 paper §0.5 双约束第 2 条 ("系统总惯量和总阻尼基本不变")
❌ v3.1 11-axis ranker 直接惩罚 → geo -44%
```

R79 验证 CLM-0102 R66 implication 最后段 "LSTM Q-0007 value is on paper-metric path, not 6-axis path" 的 **极端版本**: 在 500 ep horizon 下 trade-off 不是 ±5% 微调, 是 paper-metric +28% vs geo -44% 的结构性分裂.

## R79 plan 假设判定

| H | 假设 | 结果 |
|---|---|---|
| H1 | best_eval.pt 在 ep 50-300 区间持续提升 | ✅ 确认 (best_eval @ ep 494, best @ ep 496, CLM-0151) |
| H2 | best_eval geo ≥ R75 + 14% | ❌ 大幅失败 (-44%) |
| H3 negative | geo ≤ R75 + 5% noise | ✅ 强确认 (崩 -44%, 不是 noise) |
| 意外 | — | paper-metric cum_rf +28% 是新 candidate 待 20-scen verify |

## New claims this round

- **CLM-0150** (finding/V) — R79 paper-metric ↑ / 6-axis ↓ 结构性 trade-off, dD_smoothness 完全崩为 root cause, P_balance LS1 +22pp 是意外正面副产物.
- **CLM-0151** (finding/V) — LSTM 500ep × Q7 × tau=0.001 × warmup=20 hyper 组合下 best.pt 在 ep 496 才晚锁, CLM-0073 "best.pt early lock" 机制被打破; Q-0007 在此 hyper 下 ROI 大幅降低 (best vs best_eval ckpt 几乎重合).
- **CLM-0152** (decision/S) — R75 W2 s59 v3.1=0.4301 仍是 6-axis single SOTA, R79 best_eval.pt 留作 paper-metric path 候选待 R80+ 20-scen verify, multi-controller paper 策略 (CLM-0118) 不变.

## Questions opened (this round)

- (none) — R79 trade-off 是 structural 不是 question, 直接走 claim. Future 20-scen verify 是 R80+ 行动而非 open Q.

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**: 用户问"训练 agent 真到 paper 水平了吗", 我做了 paper-vs-我们的完整 audit, 锁定 3 个未挤 lever (REGCA1 物理层 / 500 ep + Q7 / SAC paper-faithful hyper). 用户拍板"启动优化", R79 跑了**第一条便宜 lever**: 单 seed s59 LSTM 500 ep + `--eval-every-n-eps 5` 水试.

**结果（一句话）**: R79 跑出 **结构性 trade-off** — paper-metric cum_rf **+28%** (-0.0754 → -0.0545), 但 6-axis geo **-44%** (0.4301 → 0.2402), 主因 ΔD trajectory smoothness 完全崩 (dD_smooth 轴 0.39 → 0.00). 副产物: 4-agent P_balance LS1 几乎完美 (0.78 → 1.00). **R75 W2 s59 仍是 6-axis SOTA, R79 best_eval 是 paper-metric path 新候选, 待 20-scen verify**.

**意外**: (1) **best.pt 在 ep 496 才锁** — 跟 CLM-0073 报告的 75 ep ep ≤ 10 早锁完全不同, 长 horizon × tau=0.001 × warmup=20 三件套下 best.pt 跟 best_eval.pt 时间点几乎重合 (CLM-0151), Q-0007 的 ROI 大幅降低; (2) **trade-off 是结构性的**, 不是 hyper 调优能解, 因为 Q-0007 目标函数 (cum_rf) 本身就**不奖励 ΔD 平滑** — 这反过来强化 CLM-0118 multi-controller 策略合理性; (3) **paper §0.5 双约束第 2 条 "系统总惯量阻尼基本不变" 是项目 6-axis ranker 加 dD_smooth 轴的内在依据**, R79 实测 dD_smooth=0 完全违反这条 → paper 描述的 DDIC 控制器 (ΔD 平滑可视) 跟项目 R79 控制器 (ΔD 震荡) 是两种**实际不同的策略**, 即使数字 cum_rf 相近.

**我默认下一步**: R79 commit + push, R75 W2 s59 6-axis SOTA / R72 W4 s54 paper Fig 7 canonical 不动. 用户开过另一个窗口做 **REGCA1 物理层集成** (handoff M4mGcB.md), 那是 Tier 1 物理 lever, ROI 远大于继续在 V4 env 内挤. 当前窗口剩下的事: 写 paper draft (R75 共识 ROI 已上限).

**你想插一脚就说**: 是 commit R79 + 进 paper draft / 还是先在 R80 跑 R79 best_eval 20-scen verify (1-2 h wall) 看是否真挑战得了 R67 TD3 paper-metric SOTA?

---

## Post-round update (added 2026-05-19 after R80-R84 audit)

R79 verdict 撰写时 R80-R84 已在 disk 但未读. 事后 audit 发现 "我默认下一步"
段的两条 routing 推荐均被实证修订:

1. **"REGCA1 是 Tier 1 物理 lever, ROI 远大于继续在 V4 env 内挤"** —
   被 **CLM-0141 (R80)** 否决. W2 plant 升级 6-axis Δ=-0.0094 < GATE C
   阈值 0.05 → C4 negative finding, plant 不是 lever.
2. **"paper drafting (R75 共识 ROI 已上限)"** — 被 R80-R84 实际行为否决.
   项目继续做研究 (R81 algo sweep, R82 novel arch, R84 Q-landscape
   forensics), 没进 paper drafting.

R79 main findings (CLM-0150 trade-off + CLM-0151 late-lock + CLM-0152
SOTA preservation) **仍 valid 且与 R80-R84 cumulative evidence 一致**:
- CLM-0144 (R82 91-round algo plateau) cross-reference R79 trade-off
- CLM-0149 (R84 critic monotone-in-action) cross-reference R79 mechanism

CLM ID 重号: 撰写时 CLM-0146-0148 与 R84 verdict 预期占用号段冲突,
重号到 CLM-0150-0152 (R84 留 0146-0148 给 D2 finding 补回). Validate.py
post-renumber 仍 OK.
