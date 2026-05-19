---
round: R67
state: active
opened: '2026-05-17'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R67 plan — 边际挤水: LSTM-Q7-paper-metric + gamma 单轴扫

**Date**: 2026-05-17
**Type**: hyper-sweep marginal + missing-axis
**Wall budget**: ~30-45 min (3 parallel WSL waves)

## Trigger

R66 收尾后用户问"参数是否最优"，我答：TD3/SAC 基本到顶 (+37.5pp/+32.7pp robust)，
但 3 个未扫轴可能再挤水：gamma/tau/replay_size。LSTM 也有 1 个未测路径：
**Q-0007 on paper-metric** (CLM-0102 修好 Q-0010 后 LSTM 能安全用 eval probe)。

用户："继续挤"。

## Hypotheses

- **H_W1a**: LSTM + Q-0007 在 paper-metric 上吃 SAC/TD3 同款 +14-20% 加成。
  机理: paper-metric (cum_rf) 是 episode-level scalar，跟训练 reward 强相关，
  Q-0007 prospective probe 应该有效。 vs 6-axis (CLM-0102 测的，无加成) 因
  6-axis 是多 axis ranker，跟训练 reward 弱相关。
- **H_W1b**: gamma=0.95 对 short-horizon ANDES (75 ep, 6s sim) 更优。机理:
  ANDES 频率扰动 < 5s 收敛，长 horizon 折扣低权重无意义。
- **H_W1c**: gamma=0.995 对 long-horizon 学习更优。机理: 反向，需更长展望
  才能学到稳态 D-tuning 策略。

## Waves

**W1 (3 parallel, ~12 min wall)**:

- W1a: `LSTM + Q-0007 + paper_strict_pure_radsec` s51
  ```
  LR=3e-3 python scripts/train.py --algo td3_lstm --normalize-actions \
    --episodes 75 --seed 51 --hidden-size 64 --lstm-lr-warmup-eps 5 \
    --reward-config paper_strict_pure_radsec --eval-every-n-eps 5 \
    --save-dir results/r67_w1a_lstm_q7_paper_s51
  ```
  Note: LR=3e-3 will be clamped to 1e-4 by train.py:305 (CLM-0100)
  Eval: paper-strict 20-scen, best_eval suffix

- W1b: `TD3 combo + gamma=0.95` s50
  ```
  N_SUBSTEPS=3 MAX_GRAD_NORM=0.5 LR=3e-3 GAMMA=0.95 python scripts/train.py \
    --algo td3 --normalize-actions --episodes 75 --seed 50 \
    --hidden-size 64 --batch-size 512 --eval-every-n-eps 5 \
    --save-dir results/r67_w1b_td3_combo_gamma095_s50
  ```
  Eval: paper-strict 20-scen, best_eval

- W1c: `TD3 combo + gamma=0.995` s50
  ```
  N_SUBSTEPS=3 MAX_GRAD_NORM=0.5 LR=3e-3 GAMMA=0.995 python scripts/train.py \
    --algo td3 --normalize-actions --episodes 75 --seed 50 \
    --hidden-size 64 --batch-size 512 --eval-every-n-eps 5 \
    --save-dir results/r67_w1c_td3_combo_gamma0995_s50
  ```
  Eval: paper-strict 20-scen, best_eval

**Decision points after W1**:
- If W1a > R65 SAC -0.194 → LSTM 进 paper-metric 排行 → W2 = LSTM 3-seed
- If W1b OR W1c better than R64 combo baseline (-0.118 s50) → W2 = 3-seed gamma 扫
- If neither helps → CLM 记录 negative, 收摊

## GAMMA env var

Need to confirm `GAMMA` env var is read. Check `sac_base.py` for env var pattern.
If not implemented, add it in pre-W1 phase.

## Schema plan

- **CLM-0105** (finding/V) — W1a result: LSTM + Q-0007 paper-metric
- **CLM-0106** (finding/V) — W1b/c result: gamma sweep on TD3 combo
- (W2 conditional claims if extended)
- Optionally close Q-0012 (h=96 marginal) if W1 leads to extension

## Out of scope

- LSTM refactor (Q-0013 deferred)
- code drift bisect (R57→R66, ~30 min deferred)
- tau / replay_size axes (next round if R67 productive)
