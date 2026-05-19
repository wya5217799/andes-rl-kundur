---
round: R79
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R79 plan — paper convergence horizon × Q-0007 untested combo

**Date**: 2026-05-18
**Status**: in-flight
**Type**: training experiment (single seed water-test)
**Wall budget**: ~3 h (单 seed 500 ep)

## TL;DR

> 用户问"训练效果跟 paper 一个水平吗"→ paper facts audit 发现 **未测组合**:
> **500 ep + Q-0007 (best-by-eval)**. CLM-0073 测过 500 ep 但 best-by-train-reward
> bit-identical lock；R66 CLM-0102 修了 Q-0007 LSTM 兼容但没人跑 500 ep.
> 单 seed s59 (R75 SOTA) 水试，看 best_eval.pt 是否持续提升至 500 ep.

## Motivation (paper alignment audit)

paper Sec.IV-B "After 500 episodes, all the performance indexes gradually stabilize near the optimal value" — 我们 SOTA 一直跑 75 ep. 关键 audit:

| Lever | 状态 | 期望 |
|---|---|---|
| 75 ep horizon | 当前 SOTA (R75 W2 s59 v3.1=0.4301) | baseline |
| 500 ep best-by-train-reward | [CLM-0073](../../claims/CLM-0073.md) bit-identical lock | 0 |
| **500 ep + Q-0007 (best-by-eval)** | **未测** | **+14-30%** (SAC/TD3 pattern from CLM-0080) |

Q-0007 已修 LSTM 兼容 ([CLM-0102](../../claims/CLM-0102.md)). 唯一阻挡是没人挤过这个 horizon.

## Hypothesis

H1: best_eval.pt 在 ep 50-300 区间继续提升 (paper "500 ep stabilize" 实际 trajectory).
H2: best_eval.pt v3.1 (eval@final) > R75 W2 s59 best.pt v3.1 (0.4301) by ≥ +14%.
H3 (negative): 若 best_eval.pt v3.1 ≤ 0.43 + 5% noise → LSTM Q-0007 horizon 不是 lever, paper 500 ep 是 SAC-specific 现象.

## Launch command

```bash
# WSL, single seed (~3h wall, 占 1 of 3 parallel slot)
cd ~/code/andes-rl-kundur
python scripts/train.py \
  --algo td3_lstm \
  --normalize-actions \
  --episodes 500 \
  --seed 59 \
  --hidden-size 64 \
  --lstm-lr-warmup-eps 20 \
  --tau 0.001 \
  --eval-every-n-eps 5 \
  --save-dir results/r79_500ep_q7_lstm_s59 \
  > logs/r79_500ep_q7_s59.log 2>&1
```

差别于 R75 W2 s59: 仅 `--episodes 75 → 500` + 加 `--eval-every-n-eps 5`.

## Success criteria

| Outcome | 判定 |
|---|---|
| H1 confirmed + ≥ +14% | open follow-up: 3-seed (s51, s54, s59) 500 ep + Q-0007, 凑 mean |
| ≥ +5% < +14% | open Q-0014: LSTM Q-0007 horizon 效应弱于 SAC/TD3 |
| < +5% noise | H3 confirmed, close negative |
| 训练发散 / NaN | open Q-0015: LSTM 500 ep 稳定性 (CLM-0073 75→500 稳定，500→更长未知) |

## Evaluation

`--final-eval` default on → 训练结束自动跑 LS1+LS2 dual-eval, 写 `final_eval_summary.json`.

人工 follow-up:
1. `python scripts/score_run.py --suffix best_eval --run-dir results/r79_500ep_q7_lstm_s59`
2. `python scripts/score_run.py --suffix final --run-dir results/r79_500ep_q7_lstm_s59`
3. 对比 R75 W2 s59 best.pt v3.1=0.4301

## Risks

1. **500 ep wall time**: CLM-0073 报 4318s = 72 min (LSTM 75→500 ep)，加 Q-0007 eval probe (100 次 × ~10s = 1000s) → 估 90-100 min, 但 ANDES single-session windows 可能 hiccup
2. **Q-0007 probe overhead**: 每 5 ep 跑 LS1+LS2 共 100 步 ANDES TDS, 总 100 次 → 可能浮上 1 GB RAM, 监控
3. **best_eval.pt 也可能早锁**: 类似 best.pt 早锁机制，paper-metric 早收敛 → H3
4. **训练日志吞掉异常**: stdout.log 必须留着, 如 final_eval 失败 dump `final_eval_error.txt`
