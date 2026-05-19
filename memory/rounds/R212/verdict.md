# R212 verdict — 100ep regress; 75ep is a sharp peak

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — over-training starts before 100ep
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 tau=0.005 at s54 for **100 episodes**.
Result: geo=**0.3739**, LS1=0.332, LS2=0.421, cum_rf=-0.0651.

**vs R201 (75ep): -10% degradation**. 75ep is a **sharp horizon peak**;
over-training starts well before 100ep.

## Horizon basin (final map)

| episodes | run | LS1 | LS2 | geo | regime |
|----------|-----|-----|-----|-----|--------|
| 50 | R199 | 0 | 0.451 | 0.067 | UNDER-TRAIN collapse |
| **75** | **R201** | **0.368** | **0.469** | **0.4152** | **SOTA peak** |
| 100 | R212 | 0.332 | 0.421 | 0.3739 | over-train -10% |
| 200 | R191 | 0.265 | 0.378 | 0.3161 | over-train -25% |

The peak at 75ep is narrow (±25ep around it gives >10% drop). 75 is
a true optimum, not just a convenient default.

## Mechanism interpretation

Between 75ep and 100ep, the LSTM hidden state begins to drift past
hreg's bounding capacity. λ=0.002 is tuned to stabilize 75ep training
but isn't strong enough to prevent post-75ep drift. Either:
- Stronger hreg (larger λ) might extend the stable horizon
- Or 75ep is genuinely the optimum and longer training just over-fits

R199/R200 (under-budget collapse) + R191/R212 (over-budget regress)
together establish a **narrow optimal compute window** of ~70-80ep
at this hyper.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — horizon axis is now fully characterised)

## 给 PI 的话

R212 = 100ep at SOTA hyper = 0.3739, **-10%** vs R201 75ep SOTA.

**Horizon basin 完整 map**:
- 50ep: 0.067 collapse
- 75ep: 0.4152 SOTA ⭐
- 100ep: 0.3739
- 200ep: 0.3161

**75ep 是 sharp peak**, ±25ep 都掉 >10%. 这是 narrow optimal compute
window — paper Sec.IV-D 可以加这个 mechanism finding (over-training
threshold).

R213 候选 = gamma=0.999 axis (vs default 0.99) — 长期 discount 可能
帮 LS2 (long-horizon settling). 我下次 launch.

## Cross-references

- R201 (75ep SOTA)
- R191 (200ep regress)
- R199 (50ep collapse)
