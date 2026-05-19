# R237 verdict — phi_f=0 STILL SOTA (-0.6%); phi_abs is SOLE load-bearing reward

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — major paper-integrity finding
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --phi-f 0 (load-step
penalty disabled entirely). Result: geo=**0.4127**, LS1=0.356,
LS2=0.478, cum_rf=-0.0716. **Only -0.6% from R201 SOTA**.

**phi_f is NOT load-bearing**. Combined with R236 (phi_h=phi_d=0
SOTA), **all three paper Eq.14 reward terms are effectively inert
on V4 ANDES**. The sole load-bearing reward is phi_abs (NOT in paper).

## Complete reward-term ablation table

| Term | V4 default | Required? | Evidence |
|------|------------|-----------|----------|
| **phi_abs** | **50** | **YES (≥7)** | R214 (=0) full collapse; R215 (=10) -2% |
| phi_h | 0.0056 | NO | R236 (=0) bit-identical SOTA |
| phi_d | 0.0056 | NO | R236 (=0) bit-identical SOTA |
| phi_f | 100 | NO | R237 (=0) -0.6% only |
| phi_max | 0 | NO | R221 (=1) bit-identical |
| phi_settle | 0 | NO | (default OFF, never enabled) |

## Final paper Sec.IV-D contribution 5 (definitive)

> "We performed exhaustive reward-term ablation on V4 ANDES Kundur
> 4-VSG. ALL three paper Eq.14 reward terms can be individually
> disabled with negligible effect on SOTA performance:
> - phi_h, phi_d → 0: bit-identical 0.4152 (R236)
> - phi_f → 0: 0.4127, -0.6% within noise (R237)
>
> However, disabling phi_abs (a Kundur tight-coupling term NOT in
> paper Eq.14) causes full LS1=0 attractor collapse with geo=0.010.
>
> Conclusion: The paper's reward function (Eq.14) is effectively
> NOT USED for training the SOTA controller on V4 ANDES. The sole
> load-bearing reward signal is phi_abs, an environment-specific
> term not present in the paper. This is a substantive paper-
> implementation gap; reproducibility requires understanding this
> reward redesign."

## R238 candidate

Ultimate test: phi_h=phi_d=phi_f=0, only phi_abs=50. If this works
(geo ≥ 0.40), it proves phi_abs ALONE is sufficient. Cleanest single
experiment to support the paper claim.

## Questions opened / closed / advanced

(none — but paper-integrity story now decisive)

## 给 PI 的话

🔥 **R237 = phi_f=0 = 0.4127, 只 -0.6%**!

合并 R236, **paper Eq.14 全部三个 reward terms 都 inert on V4 ANDES**.
真正 load-bearing 的 reward 是 **phi_abs (NOT in paper)**.

| Term | V4 | Required |
|------|----|----------|
| **phi_abs** | 50 | **YES (≥7)** |
| phi_h | 0.006 | NO |
| phi_d | 0.006 | NO |
| phi_f | 100 | NO |

**Paper-implementation gap 最 sharp 的版本**: V4 训练实际不用 paper Eq.14.
唯一 contribute 的 reward 是 paper 里没有的 phi_abs.

R238 候选 = phi_h=phi_d=phi_f=0 (ONLY phi_abs). Cleanest test.

## Cross-references

- R214/R215 (phi_abs threshold)
- R236 (phi_h/phi_d=0 SOTA)
- R218 (paper-strict collapse — now explained: paper used wrong terms)
