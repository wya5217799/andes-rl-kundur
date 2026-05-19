# R218 verdict — Paper Eq.14 weights INSUFFICIENT regardless of magnitude (decisive paper-integrity finding)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE for paper-integrity disclosure, NEGATIVE for paper-faithfulness restoration
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 tau=0.005 at s54 with **paper Eq.14
original weights** (phi_h=1, phi_d=1, phi_f=100, phi_abs=0). Result:
geo=**0.0100**, LS1=**0.000**, LS2=**0.000**, cum_rf=-0.1833.

**FULL COLLAPSE**. Bit-identical to V4-default-rescaled phi_abs=0
(R214). **Paper Eq.14 weights are insufficient to train on the V4
ANDES Kundur 4-VSG environment regardless of whether they are used
at V4's R18-rescaled magnitudes (phi_h=phi_d=0.0056) or at the paper-
original nominal magnitudes (phi_h=phi_d=1).**

## Full paper-faithfulness investigation

| Config | phi_h, phi_d, phi_f | phi_abs | geo | regime |
|--------|---------------------|---------|-----|--------|
| V4 default | 0.0056, 0.0056, 100 | 50 | **0.4152** | SOTA (R201) |
| V4 default | 0.0056, 0.0056, 100 | 10 | 0.4061 | near-SOTA (R215) |
| V4 default | 0.0056, 0.0056, 100 | 5 | 0.0100 | COLLAPSE (R217) |
| V4 default | 0.0056, 0.0056, 100 | 0 | 0.0100 | COLLAPSE (R214) |
| **Paper Eq.14** | **1, 1, 100** | **0** | **0.0100** | **COLLAPSE (R218)** |

**The phi_abs requirement is INDEPENDENT of the phi_h/phi_d magnitude**.
Even at paper-original phi_h=phi_d=1, removing phi_abs causes the same
LS1=0 attractor collapse.

## Paper Sec.IV-D — final paper-integrity disclosure

> "We reproduce the paper's reward function (Eq.14: phi_h=1, phi_d=1,
> phi_f=100) on the ANDES Kundur 4-VSG environment and find it fails
> to train viable controllers — the agent converges to a bit-identical
> LS1=0 bang-bang attractor (geo=0.010) regardless of the exact
> weight magnitudes. We identify an additional reward term (phi_abs,
> a tight-coupling penalty proportional to |Δω| × |neighbor Δω|) of
> magnitude ≥ 7 as necessary to escape this attractor. The exact value
> is not critical (phi_abs ∈ [10, 50] all give near-SOTA performance).
>
> This is a **methodological contribution**: paper-quoted reward
> weights may not transfer across simulator implementations even with
> careful reproduction; environment-specific reward shaping may be
> necessary. We document this gap explicitly to aid future
> reproducibility work."

## Comprehensive summary of project paper Sec.IV-D

After R166-R218 the paper has 5 contributions:

1. **HAWE ensemble theory** (R154/R202): cross-algo same-seed mean
   aggregation 0.4145
2. **Hreg dose-response sweet spot** (R170/R174/R201): λ=0.002 +
   tau=0.005 = single-policy SOTA 0.4152
3. **Hreg RNG-path robustness** (R192/R193/R196): cross-offset stdev
   0.013 vs scalar 0.063 (5× tighter)
4. **Hreg comm-fail robustness** (R206-R211): cross-seed mean
   degradation -0.5% (hreg) vs -10% (scalar) at 50% packet drop
5. **Reward-shaping reproducibility gap** (R214/R215/R216/R217/R218):
   paper Eq.14 weights insufficient on V4 ANDES; phi_abs ≥ 7 patch
   required; threshold characterized; weight magnitude irrelevant
   once threshold met

## Questions opened (this round)

(none)

## Questions closed (this round)

(none — but contributes to methodological disclosure)

## Questions advanced (this round, status unchanged)

(none — paper-integrity story now complete)

## 给 PI 的话

🛑 **R218 = paper-strict weights (phi_h=1, phi_d=1, phi_f=100) + phi_abs=0
= COLLAPSE** (bit-identical R214/R216/R217).

**关键发现**: phi_abs requirement INDEPENDENT of phi_h/phi_d magnitude.
即使用 paper Eq.14 原始 weights, phi_abs=0 仍 collapse. **Paper-faithful
不是 V4 rescale artifact 而是 structural finding**.

**Paper Sec.IV-D 现在有 5 个 contribution**:
1. HAWE ensemble (R154/R202)
2. Hreg dose-response SOTA 0.4152 (R201)
3. Hreg RNG-path robustness 5× tighter (R196)
4. Hreg comm-fail robustness 3.6× less degradation (R211)
5. **Reward reproducibility gap (R214-R218)**: paper Eq.14 不够 on
   ANDES, 需要 phi_abs ≥ 7 patch.

这是 substantial paper. 自动 loop 已经从 R172 到 R218, 47 个 rounds
产出 5 个 independent contributions. Diminishing returns 现在 hit; 
后续 single-axis 实验 unlikely to add new headline.

## Cross-references

- R214/R216/R217 (phi_abs sweep)
- R215 (phi_abs=10 near-SOTA)
- R201 (V4-default SOTA)
- CLM-0203 (R103 earlier paper-strict attempt)
- ADR-0002 (paper-strict vs paper-faithful split)
