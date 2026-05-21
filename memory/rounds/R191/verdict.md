---
round: R191
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R191 verdict — 200ep horizon collapses even with hreg (-23.6% vs R174 75ep)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — hreg does NOT fix 200ep collapse; horizon is intrinsic limit
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at seed=54 with `--episodes 200`,
all other hypers identical to R174. Result: geo=**0.3162**,
LS1=0.265, LS2=0.378, cum_rf=-0.0631. Training ran to completion (200
eps, not interrupted). vs R174 (75ep, identical hypers, same seed) =
**0.4139**: **-23.6%**.

**Hypothesis refuted**: hreg λ=0.002 was conjectured to stabilise the
long-horizon LSTM drift that caused the R149 200ep QR scalar collapse
(0.18). It does not. Even with hreg's hidden-state regularisation,
extended training **degrades** the policy by 24% vs the 75ep sweet
spot.

## The 200ep collapse pattern (now 2 algorithms tested)

| Run | algo | episodes | seed | geo | vs 75ep R174 |
|-----|------|----------|------|-----|---------------|
| R174 | hreg λ=0.002 | 75 | 54 | **0.4139** (SOTA) | (ref) |
| R149 | QR scalar | 200 | 54 | 0.18 | -57% |
| **R191** | **hreg λ=0.002** | **200** | **54** | **0.3162** | **-23.6%** |

hreg + 200ep is **better than QR + 200ep** (0.32 vs 0.18) — hreg
partially stabilizes — but neither matches the 75ep ceiling.

## Mechanism inference

Training metrics from `training_log.json`:
- Total reward trajectory: warmup avg -61.7, best 10-ep segment -6.3,
  final 10-ep avg -9.8.
- The policy DID learn (warmup recovered ~10× by mid-training).
- Best segment ≠ final segment → **late-stage drift in evaluation
  signal**, even though hreg caps hidden-state norm.

The best-checkpoint selector (lowest validation loss or best episode
reward — implementation depends on monitor.py) captures the best
mid-training policy, but the final evaluation (separate full-rollout
on all 4 scenarios) reflects the deployed policy, which apparently
suffers from late-stage overfitting / drift not detected by training
reward.

**75ep is the structural sweet spot** for this env+algorithm pair, not
just a hyper-budget cap.

## Paper Sec.IV-D implication

The R174 0.4139 SOTA is a **horizon-tuned** result, not just a (seed,
offset) tuned one. Three independent factors compound for SOTA:
1. seed=54 (good RNG basin per CLM-0350)
2. offset=0 (good RNG path per R192/R193)
3. **episodes=75 (best-checkpoint sweet spot)**

Extending any of these dimensions can degrade or collapse the result.

This adds to the methodological finding: "deep RL on physics
simulators is **multi-axis fragile** — seed, env-RNG-path, and
training-budget all interact to produce a narrow good region in
hyper-x-data space."

## Questions opened (this round)

(none — closes a residual hypothesis)

## Questions closed (this round)

(none — Q-0005 already closed-partial; R191 adds horizon to known
fragility axes)

## Questions advanced (this round, status unchanged)

(none — R191 is a clean negative result)

## 给 PI 的话

❌ **R191 (hreg λ=0.002 + 200ep at s54) = geo 0.3162** — 比 R174
(75ep 同 hyper) **跌 -23.6%**. **Hypothesis "hreg 修 200ep collapse"
被 refute**。

200ep collapse pattern (现在 2 个算法):
- R149 (QR scalar 200ep s54) = 0.18 → 严重 collapse
- **R191 (hreg 200ep s54) = 0.3162** → 中等 collapse (hreg 救一部分但不够)
- R174 (hreg 75ep s54) = 0.4139 → SOTA

Training metrics 显示 policy 确实学到了 (warmup avg -61.7 → mid-
training best -6.3), 但 final 10-ep avg -9.8 + final_eval 0.316
说明 **late-stage drift**: best-ckpt tracker 抓住了 mid-training
peak, 但 deployed policy 受 late overfit 影响。

**Paper 影响**: R174 SOTA 0.4139 是 **horizon-tuned** 结果。三个
axes 都需要 disclose:
1. seed=54 (lucky basin)
2. offset=0 (lucky RNG path)
3. **episodes=75 (lucky horizon)**

加入 "multi-axis fragility" 是 paper Sec.IV-D 第四个 methodological
contribution。

## Cross-references

- R174 (hreg 75ep s54 = SOTA 0.4139)
- R149 (200ep QR scalar 0.18 collapse — historical)
- CLM-0325 (hreg dose-response peak λ=0.002)
- CLM-0330 (R174 SOTA)
- CLM-0350 (Q-0005 closed-partial — seed mechanism)
- R192/R193 (offset axis)
