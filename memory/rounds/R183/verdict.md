# R183 verdict — hreg λ=0.002 at s49 STILL COLLAPSES (Q-0005 mechanism finding)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE for hreg-as-s49-rescue (CLOSED-PARTIAL for Q-0005 mechanism)
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` with the SOTA hyper (λ_h=0.002, lr=1e-4 clamp,
tau=0.001, warmup=5, h=64, ep=75) at seed=49. Result: geo=**0.0461**,
LS1=0.000, LS2=0.213, cum_rf=-0.2767. **Still collapse** (LS1=0
identical to R72_w4 s49 collapse pattern from CLM-0295).

**Q-0005 (R56 seed-collapse mechanism) finding**: The s49 attractor
is **independent of actor-state regularisation**. hreg λ=0.002 lifts
LS2 slightly (0.213 vs R72_w4 s49's 0) but LS1 stays at exactly 0 —
the fast-disturbance recovery channel is broken at training time
regardless of whether actor hidden-norm is regularised.

## Cross-seed picture (now complete for R174 hyper)

| seed | algo | geo | LS1 | LS2 | status |
|------|------|-----|-----|-----|--------|
| s54 | hreg λ=0.002 (R174) | **0.4139** | 0.367 | 0.467 | SOTA |
| s51 | hreg λ=0.002 (R181) | 0.3888 | 0.331 | 0.457 | -2.5% |
| **s49** | **hreg λ=0.002 (R183)** | **0.0461** | **0.000** | 0.213 | **COLLAPSE** |
| s54 | R72_w4 scalar (R72) | 0.391 | 0.354 | 0.431 | baseline |
| s51 | R72_w4 scalar | 0.3562 | 0.321 | 0.395 | -8.9% |
| s49 | R72_w4 scalar | 0.0100 | 0 | 0 | COLLAPSE |

**Pattern**: hreg λ=0.002 improves s51 (relative to R72_w4 scalar) by
+9%, improves s54 by +5.9%, but **does not rescue s49**. The s49
collapse mode is structurally different from a generic
"under-regularised LSTM" failure.

## Mechanism candidates (post-R183)

LS1=0 at s49 means the policy outputs are stuck — either:
1. **Critic representation issue** — the critic gradient signal at s49
   is fundamentally biased (CLM-0157 candidate; tested for QR critic
   by R142, still plateau; but s49-specific not tested)
2. **Env stochasticity / RNG asymmetry** — s49 initial seed leads to
   a different exploration noise trajectory that traps the actor in
   a sub-region of action space where LS1 reward signal is absent
3. **Replay buffer composition** — s49's first ~5 episodes produce
   a buffer that biases the early critic toward a saddle point

The hreg-doesn't-help result rules out actor-hidden-state divergence
as the cause. The remaining candidates are critic-side or env-side.

## Paper implications

R174's SOTA at s54 = single-seed claim. Multi-seed evidence:
- 2/3 seeds give viable training (s54 0.4139, s51 0.3888)
- 1/3 seeds collapses (s49 0.046)

Paper Sec.IV-D should disclose this: **single-seed s54 SOTA + 33%
collapse rate at s49 with same hyper**. This weakens the "robust SOTA"
claim but strengthens the "lucky seed" caveat (already in CLM-0295
about R72_w4). Mean across non-collapsed seeds {s54, s51} =
(0.4139 + 0.3888) / 2 = 0.4014 — still beats R72_w4 mean 0.374.

## Questions opened (this round)

(none — but Q-0005 mechanism narrows to critic/env-side)

## Questions closed (this round)

(none — Q-0005 stays open closed-partial pending mechanism identification)

## Questions advanced (this round, status unchanged)

- Q-0005 (seed collapse) — significant evidence added: hreg does NOT
  rescue collapse; mechanism is not actor-state-norm. Future R184+
  candidate: critic-side rescue (QR or AFE at s49 with hreg).

## 给 PI 的话

🛑 R183 = R174 SOTA hyper at s49 = geo **0.0461** (LS1=0 collapse pattern).
hreg λ=0.002 不 rescue s49。

**对 Q-0005 mechanism 的贡献**: R72_w4 scalar 在 s49 完全 collapse (0.010, LS1=0),
hreg 加上去 LS2 上去一点 (0.213) 但 LS1 仍 0 — actor 的 LSTM hidden-state
regularisation 在 s49 attractor 面前完全没用。机制不在 actor-side。

**剩下的机制候选**: (a) critic 梯度信号 s49-specific 偏 (R142 测过 scalar→QR
没破 plateau, 但 s49 specific 没测); (b) env exploration noise trajectory
trap actor 进 LS1-blind 子空间; (c) replay buffer 前 5 episode 偏成 saddle.

**对 paper 的影响**: R174 SOTA "lucky seed" caveat 更强了 (现在 3 seeds 测完:
s54 0.4139 ✓, s51 0.3888 ✓ (-2.5%), s49 0.046 ✗). 2/3 seeds viable, 1/3 collapse.
Sec.IV-D 必须 disclose 这个 33% collapse rate, 不能藏。

下一步默认: 自动 loop 继续。R184 候选 = (a) longer horizon 200ep at λ=0.002 s54
(Q-0008 测), 或 (b) critic-side rescue 试 R174 hyper + QR critic at s49 (Q-0005 子探究).
我会 launch 哪个 ROI 更高的。

## Cross-references

- CLM-0295 (R72_w4 s49 collapse evidence)
- R174 verdict (single-policy SOTA at s54)
- R181 (s51 cross-seed test)
- Q-0005 (R56 seed-collapse question)
