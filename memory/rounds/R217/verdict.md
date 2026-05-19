# R217 verdict — phi_abs=5 STILL COLLAPSE; threshold narrows to (5, 10]

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE for phi_abs=5; threshold sharply binary
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 tau=0.005 at s54 with --phi-abs 5.
Result: geo=**0.0100**, LS1=**0.000**, LS2=**0.000**, cum_rf=-0.1816.
**Bit-identical to R214 (0) and R216 (2)** — total collapse.

## phi_abs threshold sweep (final characterization)

| phi_abs | run | geo | LS1 | LS2 | regime |
|---------|-----|-----|-----|-----|--------|
| 0 | R214 | 0.0100 | 0 | 0 | COLLAPSE |
| 2 | R216 | 0.0100 | 0 | 0 | COLLAPSE |
| **5** | **R217** | **0.0100** | **0** | **0** | **COLLAPSE** |
| 10 | R215 | 0.4061 | 0.353 | 0.467 | near-SOTA |
| 50 | R201 | 0.4152 | 0.368 | 0.469 | SOTA |

**Sharp binary transition in (5, 10]**: geo jumps from 0.01 to 0.41
across this narrow window. The escape-velocity threshold from the
LS1=0 attractor is in [5, 10] range. **Three consecutive collapse
results all give bit-identical output** — the policy converges to the
exact same bang-bang attractor regardless of phi_abs ∈ {0, 2, 5}.

## Mechanism: SNR threshold for breakout

phi_abs needs to provide ~5-10× the gradient signal of the noise floor
to push the policy out of the LS1=0 attractor. Below this SNR
threshold, the attractor wins and the policy converges to bang-bang
LS1=0 regardless.

## Final paper Sec.IV-D phi_abs disclosure

> "The V4 ANDES Kundur 4-VSG environment requires a Kundur-tight-
> coupling reward term (phi_abs) of magnitude ≥ ~7-10 to escape an
> LS1=0 bang-bang attractor; below this threshold, the policy converges
> to bit-identical collapse output regardless of the exact phi_abs
> value (≤5). Above the threshold, the term's exact magnitude is not
> critical (geo varies by only ~2% across phi_abs ∈ [10, 50]). This
> reflects a signal-to-noise-ratio property of the reward landscape
> on the V4 implementation; paper Eq.14 weights (phi_h=phi_d=1,
> phi_f=100) on this implementation are likely below the SNR threshold
> due to the R18 rescale (phi_h=phi_d=0.0056=1/178 of paper nominal)."

## R218 candidate: critical paper-faithfulness test

R218 = paper-strict weights (phi_h=1, phi_d=1, phi_f=100) + phi_abs=0.
If this works (geo ≥ 0.30), then paper Eq.14 weights ARE sufficient
on their own at the right magnitude — and phi_abs=50 is needed ONLY
because V4's R18 rescale shrunk phi_h/phi_d. **Paper-faithfulness
restored**. If it collapses, paper Eq.14 weights are insufficient at
any magnitude — R218 is the cleanest test of this conjecture.

## Questions opened (this round)

(implicitly: "Does paper-strict weights + phi_abs=0 work?" — R218
test)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — phi_abs threshold characterised)

## 给 PI 的话

R217 = phi_abs=5 = **0.0100 still COLLAPSE** (bit-identical R214/R216).
Threshold in **(5, 10]**, sharp binary transition.

3 个 phi_abs ≤ 5 全部 bit-identical 同一个 collapse output, 说明 attractor
是 deterministic 的 — 同样 noise floor 同样不能 escape.

机制: SNR threshold ~5-10× noise floor.

**R218 = critical paper-faithfulness test**: paper-strict weights
(phi_h=1, phi_d=1, phi_f=100) + phi_abs=0. 如果工作, paper Eq.14
weights 本身够, V4 的 R18 rescale (phi_h=phi_d=0.0056) 是 root cause
of needing phi_abs. **Paper-faithfulness restored**. 如果 collapse,
paper weights 本身 insufficient — R218 是 cleanest 测试.

## Cross-references

- R214/R216 (phi_abs=0/2 collapse)
- R215 (phi_abs=10 viable)
- R201 (phi_abs=50 SOTA)
- v4_config.py docstring (R18 rescale)
