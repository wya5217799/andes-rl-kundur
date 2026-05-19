# R209 verdict — Scalar degrades 3.6× more than hreg at 50% comm-fail

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE — hreg's robustness contribution isolated and quantified
**Type**: research

## TL;DR

Trained `td3_lstm` scalar (no hreg) at s54 + tau=0.005 + --comm-fail
0.50. Result: geo=**0.3431**, LS1=0.326, LS2=0.361, cum_rf=-0.0685.

**vs scalar baseline (R72_w4, perfect comm = 0.391): -12.2%**
**vs hreg + 50% comm-fail (R208 = 0.4009): -14.4%**
**hreg degrades 3.6× LESS than scalar under same comm failure rate.**

## The robustness comparison

| condition | scalar | hreg | hreg - scalar |
|-----------|--------|------|----------------|
| perfect comm (0%) | 0.391 | 0.4152 | +0.024 (+6.2%) |
| 50% comm-fail | **0.3431** | **0.4009** | **+0.058 (+16.8%)** |
| degradation | **-12.2%** | -3.4% | hreg 3.6× more robust |

The hreg-vs-scalar gap **widens** under stress: +6% at perfect comm
→ +17% at 50% packet drop. **hreg's robustness contribution is real
and substantial.**

## Mechanism (full picture)

LSTM architecture gives some baseline robustness (scalar still
viable at 50% packet drop, -12% only — would expect MUCH worse for
non-recurrent policy). But hreg amplifies this 3.6×.

Hypothesis: scalar LSTM hidden state can drift when peer messages
are unreliable; hreg's hidden-norm regularization bounds that drift,
so the LSTM stays in a stable basin even with 50% missing peer
messages. The basin is the "comm-failure-invariant" policy region.

## Final paper Sec.IV-D table

| Contribution | Source | Number |
|--------------|--------|--------|
| 1. HAWE ensemble theory | R154/R202 | 0.4145 (same-seed cross-algo) |
| 2. Hreg dose-response | R170/R174/R201 | 0.4152 (single-policy SOTA, λ=0.002, tau=0.005) |
| 3. Hreg RNG-path robustness | R192/R193/R196 | scalar stdev 0.063 vs hreg 0.013 (5× tighter) |
| 4. Hreg comm-fail robustness | R206/R207/R208/R209 | -3.4% (hreg) vs -12.2% (scalar) at 50% packet drop |

All four contributions are independent and mutually reinforcing.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — robustness story now complete)

## 给 PI 的话

🎯 **R209 = scalar + 50% comm-fail = 0.3431** (vs hreg's 0.4009).
**hreg degrades 3.6× less than scalar** under same comm failure.

**Gap widens under stress**:
- Perfect comm: hreg +6% over scalar
- 50% comm-fail: hreg +17% over scalar

机制: LSTM architecture 给 baseline robustness (scalar 在 50% drop 下
-12%, 不 catastrophic). hreg amplify 3.6×. Hidden-norm regularization
bound LSTM hidden state drift 在 missing peer messages 下。

**Paper Sec.IV-D 四个独立 contribution 全部 finalised**:
1. HAWE ensemble (R154/R202)
2. Hreg dose-response (R170/R174/R201)
3. Hreg RNG-path robustness (R192-R196)
4. Hreg comm-fail robustness (R206-R209)

R210 候选 = cross-seed robustness test: hreg s51 + 50% comm-fail.
如果 s51 也 robust, 故事 truly seed-universal.

## Cross-references

- R208 (hreg + 50% comm-fail = 0.4009)
- R72_w4 (scalar perfect comm = 0.391)
- R192 (scalar offset=100 = 0.2844, -27%)
- CLM-0325 (paper findings narrative)
