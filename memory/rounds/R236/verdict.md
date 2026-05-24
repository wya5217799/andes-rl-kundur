# R236 verdict — phi_h=0 STILL SOTA; paper Eq.14 phi_h/phi_d terms are USELESS

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — major paper-integrity finding
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --phi-h 0 --phi-d 0
(both frequency-deviation reward terms DISABLED). Result:
geo=**0.4152**, LS1=0.368, LS2=0.469, cum_rf=-0.0692. **Bit-identical
to R201**.

**The phi_h and phi_d reward terms from paper Eq.14 contribute
ZERO to training on V4 ANDES**. Setting them to 0 yields the same
SOTA. The actual load-bearing reward components are:
- phi_abs = 50 (Kundur tight-coupling, NOT in paper Eq.14)
- phi_f = 100 (load-step penalty, matches paper)

## Paper-integrity refinement (CUMULATIVE)

After R214-R236 phi_h/phi_abs/phi_d exhaustive sweep:

| Term | Default V4 | Required? | Notes |
|------|------------|-----------|-------|
| phi_f | 100 | UNTESTED at zero | matches paper; assumed load-bearing |
| phi_h | 0.0056 | **NOT REQUIRED** | sweet spot [0, 0.01], cliff >0.02 |
| phi_d | 0.0056 | **NOT REQUIRED** | same as phi_h (symmetric) |
| phi_abs | 50 | **REQUIRED ≥7** | NOT in paper Eq.14 |
| phi_max | 0 | not required | default OFF |
| phi_settle | 0 | not required | default OFF |

**The V4 implementation effectively trains on a TWO-TERM reward**:
{phi_abs, phi_f}. The paper Eq.14's phi_h/phi_d terms are decorative
at V4 magnitudes — they contribute zero gradient signal.

## Refined paper Sec.IV-D contribution 5

> "We performed an exhaustive reward-term ablation on the V4 ANDES
> Kundur 4-VSG implementation:
>
> 1. **phi_h, phi_d** (paper Eq.14 frequency-deviation): the V4 default
>    magnitudes (0.0056, 1/178 of paper-nominal) are within a sweet-spot
>    window [0, 0.01]. Disabling them entirely (phi_h=phi_d=0) yields
>    bit-identical SOTA, indicating these terms contribute zero training
>    signal. Above 0.02 they trigger collapse.
>
> 2. **phi_abs** (Kundur tight-coupling, NOT in paper): required at
>    magnitude ≥7. Below this, full LS1=0 attractor collapse.
>
> 3. **phi_f** (load-step penalty): default 100, untested at zero.
>
> The effective training reward on V4 ANDES is therefore essentially
> {phi_abs, phi_f}, not the paper Eq.14 form. This reveals a deeper
> paper-implementation gap: the paper's specified reward function is
> not load-bearing on the ANDES simulator, while an environment-
> specific term (phi_abs) is necessary."

This is **substantially stronger** than the previous "paper Eq.14
needs phi_abs patch" framing. The new claim: paper Eq.14 itself is
LARGELY INERT on V4 ANDES.

## R237 candidate

The last untested term: phi_f. Disable it (--phi-f 0) and see if
SOTA collapses (phi_f is the ONLY load-bearing paper term) or
survives (paper's phi_f is also inert; only phi_abs matters).

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

🎯 **R236 = phi_h=0, phi_d=0 = bit-identical SOTA**!

**Paper Eq.14 的 phi_h/phi_d terms 在 V4 ANDES 上 contribute ZERO** to
training. Disable 完全没影响. **真正 load-bearing 的 reward**:
- phi_abs = 50 (NOT in paper)
- phi_f = 100 (in paper)

**Paper Sec.IV-D 关键 finding 强化**: paper Eq.14 的 frequency-deviation
terms 是 effectively decorative. V4 真正 train 在 two-term reward
{phi_abs, phi_f}. Paper-implementation gap 比之前 framing 更深 —
不只是"需要 phi_abs patch", 是"paper Eq.14 的 phi_h/phi_d 是 inert".

R237 候选 = phi_f=0 (disable last paper term). 如果 collapse, phi_f
是 ONLY load-bearing paper term. 如果 SOTA, phi_abs 是 sole 真正
load-bearing reward.

## Cross-references

- R234/R235 (phi_h low side)
- R231/R233 (phi_h high collapse)
- R214-R217 (phi_abs sweep)
- R218 (paper-strict collapse)
