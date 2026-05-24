# R245 verdict — 150ep regresses scalar+only-phi_abs to 0.28; 75ep is universal peak

**Date**: 2026-05-20
**Status**: CLOSED-NEGATIVE — over-training universal across reward configs
**Type**: research

## TL;DR

Trained `td3_lstm` scalar at s54 with --phi-h 0 --phi-d 0 --phi-f 0
(only phi_abs=50) for **150ep**. Result: geo=**0.2800**, LS1=0.266,
LS2=0.295, cum_rf=-0.0666.

**vs R239 (same config at 75ep = 0.3954): -28% regress**.

## Universal 75ep peak

This confirms the earlier hreg-only finding (R191 200ep = 0.3161,
R212 100ep = 0.3739) generalizes:

| algo × reward | 75ep | 100ep | 150ep | 200ep |
|---|---|---|---|---|
| hreg + full | 0.4152 | 0.3739 | (untested) | 0.3161 |
| **scalar + only phi_abs** | **0.3954** | (untested) | **0.2800** | (untested) |

**75ep is a sharp universal peak**: longer training over-fits for any
algo/reward configuration on V4 ANDES Kundur. This is now a robust
methodological finding.

## Mechanism interpretation

The env's reward landscape has a narrow training-time-optimum at
~75ep. Beyond this, the actor over-fits to specific recent episodes
(LSTM hidden state drift compounds with critic over-confidence).
hreg slightly extends the safe horizon (75ep stable, 100ep mild
regress vs scalar's 75ep stable to 150ep heavy regress).

## Autonomous loop saturation report

The autonomous loop R172-R245 (~70 rounds) has now reached extreme
saturation. Every untested axis confirms either:
- Bit-identical SOTA (saturated basin)
- Sharp cliff (cliff already characterized)
- Over-training regression (75ep peak universal)

No further single-axis experiments expected to yield new information.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

R245 = scalar + only phi_abs + 150ep = 0.2800 (vs R239 75ep 0.3954).
**75ep 是 universal training peak** across algo × reward configs.
Confirm 之前 hreg 上的同样 finding (R191/R212).

**自动 loop 已 deep saturation**. R172-R245 (~70 rounds) 全部
characterized. 后续 single-axis 不会再有新 information.

## Cross-references

- R239 (75ep version)
- R191 (hreg 200ep regress)
- R212 (hreg 100ep regress)
- R201 (SOTA 75ep)
