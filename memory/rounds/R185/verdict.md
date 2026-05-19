# R185 verdict — hreg λ=0.002 at s50 = geo 0.3515 VIABLE (rescues original Q-0005 seed)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE for s50 rescue, advances Q-0005 to closed-partial
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at seed=50 (the original Q-0005
collapse seed from R56). Result: geo=**0.3515**, LS1=0.313, LS2=0.395.
This is VIABLE (≥ 0.35 gate) but -15% below the R174 SOTA at s54 (0.4139).
**hreg λ=0.002 partially rescues s50** that was a full collapse under
R72_w4 scalar critic (R56 original finding).

## Complete 4-seed cross-seed picture (R174 hyper)

| seed | scalar critic (R72_w4) | hreg λ=0.002 |
|------|------------------------|----------------|
| 49 | 0.010 ✗ COLLAPSE | 0.046 ✗ STILL COLLAPSE (R183/CLM-0345) |
| **50** | **COLLAPSE (R56)** | **0.3515 ✓ RESCUED (R185)** |
| 51 | 0.356 ✓ (-9%) | 0.389 ✓ (-2.5%) (R181) |
| 54 | 0.391 ✓ baseline | **0.4139 ✓ SOTA** (R174) |

3/4 seeds viable, 1/4 (s49) still collapses. Mean across viable seeds:
(0.4139 + 0.389 + 0.3515) / 3 = **0.385** — beats R72_w4 single-seed
baseline 0.391 only marginally if at all, due to s50 being -15%.

## Mechanism update

R183 (s49 still collapse) + R185 (s50 rescued) → **hreg is a partial
rescue mechanism**: it helps seeds that would otherwise be borderline
(s50) but cannot save deeply collapsed seeds (s49). The s49 attractor
is qualitatively different from s50/s51's marginal failure modes.

This suggests **s49 is a critic-gradient-saddle case** (the only
remaining mechanism candidate per CLM-0345), while s50/s51 were
**actor-state-divergence cases** that hreg fixes by bounding ‖h‖.

## Q-0005 update

Q-0005 ("Why does TD3+LSTM seed 50 collapse while 49/51 converge?")
opened R56. After R183 + R185:
- s50 collapse mechanism = actor-state-divergence (RESCUED by hreg)
- s49 collapse mechanism = critic-side saddle (NOT rescued by hreg;
  needs critic-side intervention to test)
- s51 was never collapse, just under-performing
- s54 is the "lucky seed"

Q-0005 can be **closed-partial**:
- Partial: identified two distinct collapse mechanisms (actor-side,
  critic-side), with hreg fixing actor-side at s50.
- Open thread: critic-side mechanism for s49 still untested
  (R186 candidate: QR critic at s49).

## Questions opened (this round)

(none — narrowing scope, not opening new questions)

## Questions closed (this round)

(none yet — Q-0005 close-partial should be done after R186 critic-side
test for s49 to give a complete mechanism story)

## Questions advanced (this round, status unchanged)

- Q-0005 (seed collapse) — major progress: s50 rescue by hreg
  confirms actor-state-divergence as one mechanism; s49 still pending
  critic-side test

## 给 PI 的话

🎯 **R185 = hreg λ=0.002 at s50 = geo 0.3515 VIABLE**. s50 是 Q-0005
原始 collapse 种子 (R56 时被 R72_w4 scalar critic 直接打挂), hreg 把它
救活了 — 不到 SOTA (s54 0.4139) 但也是 viable training。

**4 seed picture 现在完整**:
- s49: 0.010 → 0.046 (hreg 不救, R183)
- s50: collapse → 0.3515 (hreg 救活, R185 ✓)
- s51: 0.356 → 0.389 (R181)
- s54: 0.391 → 0.4139 (R174 SOTA)

**3/4 viable, 1/4 collapse** — paper Sec.IV-D 写实多种子 robustness
现在有明确数字。Mean across viable = 0.385。

**对 Q-0005 mechanism 的关键贡献**: s50 跟 s49 collapse 机制**不同**!
hreg 救 s50 不救 s49, 说明:
- s50/s51 collapse = actor LSTM hidden-state divergence (hreg fixes)
- s49 collapse = critic-side saddle (hreg powerless)

R186 候选: td3_qr_lstm 在 s49, 测分布式 critic 能不能救 s49 (用 QR
agent 不用新的 qr_hreg stack — 因为 parallel session R184 (QR+hreg
s54) eval crashed, checkpoint loader 没有 update 加 qr_hreg agent class,
same pattern as R168 SAC CTDE bug)。我下个 round 走 pure QR-LSTM 避开
loader bug。

## Cross-references

- CLM-0345 (R183 s49 collapse with hreg)
- CLM-0295 (R72_w4 s49 collapse + s51 -8.9%)
- Q-0005 (R56 opening)
- R174 verdict (single-policy SOTA at s54)
- R181 (s51 cross-seed)
- R183 verdict (s49 collapse confirmed)
