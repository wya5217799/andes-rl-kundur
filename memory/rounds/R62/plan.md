# R62 plan — Q-0007 real重训 + hyper-recon (h128 vs h64) — multi-wave

**Date**: 2026-05-17
**Type**: experiment (Q-0007 enabled retrain + hyper-recon) + breakthrough
**Wall budget**: ~75 min (3 waves × ~25 min each)

## Trigger

R61 PI briefing: user asked "目前各方面参数都是最优吗" + "启动" Q-0007
真正重训 (S1/S2/S3 plan). Realized hyper status is **远没最优**:
- R48 U-curve only测过 TD3 MLP hidden_size; SAC/LSTM hidden_size 从未扫
- LR, γ, τ, batch, buffer, gradient_clip 全 paper Table I 默认，无项目验证
- Q-0007 R61 实现完成但从未在真训练中用过

Multi-wave staged plan:

## Wave 1 — Q-0007 真实首跑 + hyper recon (3 parallel, ~15 min)

3 paths:
1. **S1 path-1**: LSTM Q-0007 s49 (h64, warmup5, eval-every-5)
   — first true prospective Q-0007 use
2. **Hyper recon A**: SAC h128 vs R58 h64 baseline (paper_strict_pure_radsec)
3. **Hyper recon B**: LSTM h128 vs R56/R57 h64 baseline

Goal: validate hyper assumptions before全量重训.

## Wave 2 — exploit Wave 1 findings (3 parallel, ~15 min)

Based on Wave 1 findings:
- SAC h128 + Q7 s49 + s51 (complete 3-seed paper-faithful SAC)
- TD3 normalized h64 + Q7 s50 (test TD3 + Q7 on V4 historical)

## Wave 3 — control + complete 3-seed (3 parallel, ~15 min)

- SAC h64 + Q7 s50 control (compare h64 vs h128 with Q7)
- TD3 h64 + Q7 s49 + s51 (complete TD3 3-seed)

## Hypotheses

- **H_Q7**: Q-0007 best_eval.pt > best.pt by >10% paper-metric for SAC + TD3
- **H_hyper_sac**: SAC h128 > h64 paper-metric
- **H_hyper_lstm**: LSTM h128 > h64 6-axis (paper Sec.IV-A says 4×128)

## Schema plan

- **CLM-0080** (decision/S) — Q-0007 真实首跑结果 (Wave 1+2+3)
- **CLM-0081** (finding/V) — hidden_size hyper recon (h64 vs h128 for SAC/LSTM)
- **CLM-0082** (finding/V) — TD3 + Q-0007 + V4 historical 3-seed paper-metric
- **CLM-0083** (finding/V) — SAC + Q-0007 + paper-strict-radsec 3-seed paper-faithful
- **CLM-0084** (decision/S) — new production candidates per scope
- Q-0007 status: closed-positive if Q-0007 verified empirically
