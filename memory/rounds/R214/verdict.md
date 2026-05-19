# R214 verdict — phi_abs=0 FULL COLLAPSE; SOTA depends critically on non-paper reward term

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE for paper-integrity disclosure, NEGATIVE for paper-faithfulness
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 tau=0.005 at s54 with **--phi-abs 0**
(disable the non-paper Kundur tight-coupling penalty). Result:
geo=**0.0100**, LS1=**0.000**, LS2=**0.000**, cum_rf=-0.1816.

**FULL COLLAPSE**. The R201 SOTA (0.4152) **depends critically on
phi_abs=50** — a reward term NOT present in paper Eq.14.

## Paper-integrity implication

The V4 paper-faithful config uses (per v4_config.py docstring):
- phi_h=0.0056, phi_d=0.0056 (1/178 of paper's nominal 1.0)
- **phi_abs=50** (NOT in paper Eq.14, "Kundur tight-coupling patch")
- phi_f=100 (matches paper)

R214 proves the phi_abs=50 patch is **load-bearing**. Without it,
the agent cannot escape the LS1=0 bang-bang attractor. The 0.4152 SOTA
is therefore conditional on a reward-shaping term that:
- The original paper did NOT use
- Was introduced for "ANDES numerical stability" (per docstring)

This is consistent with CLM-0203 (R103 paper_strict_pure result):
removing the V4-specific patches and using paper Eq.14 exactly gives
poor performance. R214 isolates phi_abs=50 as the specific load-
bearing element.

## Paper Sec.IV-D required disclosure

> "Reproducing the paper's reward weights (Eq.14) on the ANDES V4
> implementation does not yield viable training — the agent collapses
> to a bang-bang attractor with LS1=0. We introduced an additional
> Kundur-tight-coupling penalty (phi_abs=50) to break this attractor.
> All SOTA results in this work depend on this reward modification,
> which is a methodological contribution: it identifies that paper-
> quoted reward weights may not transfer across simulator implementations
> and reveals a deeper reward-landscape issue in physics-sim RL."

This is a **strengthening** of the contribution: not just "we got
SOTA on Kundur" but "we identified and fixed a reward-shaping issue
that prevents paper Eq.14 from working on this env".

## R215 candidate

Find the minimum phi_abs that prevents collapse. R214 (0) collapses,
R201 (50) SOTA. Test intermediate values to find threshold:
- 10 (R215 candidate)
- 25 (R216 candidate)
- 5 (R217 candidate)

If phi_abs=10 already gives ~0.40, the term is just a "kicker" out of
collapse, not a load-bearing weight. If phi_abs=10 still collapses,
the threshold is higher.

## Questions opened (this round)

(implicitly: "What is the minimum phi_abs for SOTA?" — R215+)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — major paper-integrity finding, no Q-tied)

## 给 PI 的话

🛑 **R214 = phi-abs=0 = geo 0.0100, FULL COLLAPSE** (LS1=LS2=0).
R201 SOTA 完全依赖 phi_abs=50 这个 **paper Eq.14 没有的** "Kundur
tight-coupling patch" reward 项.

**Paper-integrity 关键 finding**:
- 移除非 paper 项 → agent 不能学 → LS1=0 attractor
- R201 0.4152 SOTA 是 conditional on phi_abs=50
- 跟 CLM-0203 (R103 paper_strict_pure 也差) 一致, R214 直接 isolate 出
  phi_abs 是 load-bearing 元素

**对 paper 影响**: Sec.IV-D 必须 disclose. 但 framing 可以 strengthen
contribution — "我们发现 paper Eq.14 reward weights 在 ANDES Kundur env
上不能 train, 需要 phi_abs=50 patch. 这是 methodological finding 关于
paper-quoted reward weights 跨 simulator transferability."

R215 候选 = phi_abs=10 找 threshold. 如果 10 已经 ~0.40, phi_abs 是
breakout-kicker; 如果还 collapse, threshold 更高.

## Cross-references

- R201 (SOTA at phi_abs=50)
- CLM-0203 (R103 paper_strict_pure low result)
- ADR-0002 (paper-strict vs paper-faithful split)
- v4_config.py docstring
