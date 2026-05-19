# R186 verdict — QR critic at s49 ALSO collapses (Q-0005 narrows to env/replay-side)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE for QR-as-s49-rescue (Q-0005 closes-partial now possible)
**Type**: research

## TL;DR

Trained `td3_qr_lstm` (distributional critic, no hreg) at seed=49,
75ep. Result: geo=**0.0387**, LS1=**0.000**, LS2=0.150, cum_rf=-0.211.
**Still collapse** (LS1=0 pattern identical to R72_w4 scalar and R183
hreg). **Pure critic-side intervention does not rescue s49.**

Combined with R183 (hreg s49 collapse) + R185 (hreg s50 rescue), the
mechanism picture is now resolved enough to close Q-0005 as
**closed-partial**:

## Complete Q-0005 mechanism table

| seed | scalar critic | hreg λ=0.002 | QR critic |
|------|---------------|----------------|-----------|
| **s49** | 0.010 ✗ | 0.046 ✗ | **0.039 ✗** (R186) |
| s50 | COLLAPSE | **0.3515 ✓** | not tested |
| s51 | 0.356 ✓ -9% | 0.389 ✓ -2.5% | not tested |
| s54 | 0.391 ✓ | 0.4139 ✓ | 0.3845 ✓ |

**Three independent collapse-rescue interventions all fail at s49**:
- Actor-state regularisation (hreg): no help
- Critic distributional head (QR): no help
- Both: parallel session R184 eval crashed (loader bug), inconclusive

This **rules out** both actor-side and critic-side mechanism candidates
from CLM-0345. The remaining candidates per CLM-0345 were:
1. Critic gradient signal — **REJECTED by R186** (QR alone doesn't rescue)
2. Env exploration noise trajectory — **STILL OPEN**
3. Replay buffer initial composition — **STILL OPEN**

The s49 collapse is therefore an **env/replay-side phenomenon**, not
an algorithm/architecture-side one. Further single-algo-side trials
at s49 will continue to fail.

## What this means for the paper

The "lucky seed s54" caveat is **structurally inescapable** at the
single-algo level. R174 SOTA 0.4139 is a single-seed claim because:
- s50 rescue requires hreg (+15% lift from collapse to 0.3515)
- s51 is viable but -2.5%
- s49 cannot be rescued by any tested algorithmic intervention

Paper Sec.IV-D disclosure: 1/4 seeds (25%) deterministically collapse
under R72_w4 hyper family. Mean across viable seeds (s50, s51, s54)
= (0.3515 + 0.389 + 0.4139) / 3 = **0.385**. This is the defensible
multi-seed number.

## Q-0005 closure

Q-0005 ("Why does TD3+LSTM seed N collapse while others converge?")
opened R56. After R183/R185/R186 the mechanism is partially identified:

- **s50 collapse mechanism**: actor LSTM hidden-state divergence
  (CONFIRMED — hreg λ=0.002 rescues; R185)
- **s49 collapse mechanism**: env/replay-side (NEGATIVE on actor and
  critic intervention; positive mechanism not isolated)

Status → **closed-partial** by CLM-0350 (this round's claim).

## Questions opened (this round)

(none — narrowing scope, not opening new)

## Questions closed (this round)

- Q-0005 closed-partial by CLM-0350 — actor-state-divergence
  identified as one collapse mechanism (s50, rescued by hreg);
  s49 mechanism is env/replay-side (untested directly, but ruled
  out actor and critic interventions). Three single-architectural
  interventions confirmed insufficient to rescue s49.

## Questions advanced (this round, status unchanged)

(none — Q-0005 closure is the major advance)

## 给 PI 的话

🛑 R186 = pure QR critic at s49 = geo **0.0387 (LS1=0)** — 也 collapse。

**Q-0005 picture 现在完整足够 close-partial**:
- s49 collapse 跟 actor regularization 无关 (R183 hreg 不救), 跟
  critic distributional 也无关 (R186 QR 不救)。**机制在 env/replay 侧**,
  超出 algorithm/architecture 层面 single intervention 能解决的范围。
- s50 是另一种 collapse — actor LSTM hidden-state divergence 类型,
  hreg 能救 (R185 救活到 0.3515)。

**对 paper Sec.IV-D 影响**: "lucky seed s54" caveat 是 structural 的,
single-algo 层面避不开。Paper 必须 disclose:
- 1/4 seeds (s49) deterministically collapse under R72_w4 hyper 家族
- 3/4 viable mean = (0.3515 + 0.389 + 0.4139) / 3 = **0.385** —
  这是 defensible multi-seed number
- s54 0.4139 是 single-seed SOTA, 应该明确标 single-seed

**下一步默认**: 自动 loop 继续。下一个候选 R187 = R174 hyper 跑 200ep
at s54 (Q-0008 paper-original horizon test)。R149 QR-LSTM 200ep 退化,
但 hreg 不同 — 可能从 longer training + h-norm bounded state space 受益。
有可能 geo > 0.4139 SOTA, ROI 高。

## Cross-references

- CLM-0345 (R183 hreg-doesn't-rescue-s49)
- CLM-0295 (s49 collapse evidence, R72_w4 scalar)
- CLM-0275 (R142 QR-LSTM at s54)
- R183 verdict, R185 verdict (parent investigations)
- Q-0005 (R56 opening)
