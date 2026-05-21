---
round: R259
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R259 plan — Action-vs-disturbance lag correlation (R257 complement)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (probe-first, complement to autonomous-loop R257 smoothness probe)
**Driver**: Autonomous loop's R257 measured action smoothness/TV
and found RL is 3× smoother than droop k=10 (CLM-0475). R259
adds the orthogonal lag/correlation analysis: does RL action
TRACK disturbance dynamics (positive correlation) or is it
decoupled (zero/negative correlation)? Together R257+R259
characterise WHY droop reactive-titrate beats RL smooth-saturated.
**Parent**: CLM-0470 (R256 max-out), CLM-0475 (R257 smoothness inversion).

## TL;DR

Probe `scripts/r257_probe_anticipation_lag.py` (10-min, no env change)
computes per-agent cross-correlation of |action[t]| vs |disturbance[t-k]|
for k ∈ {-2,-1,0,+1,+2}. Reports peak lag and correlation magnitude.

## Pre-registered outcomes

| Pattern | Interpretation |
|---------|----------------|
| Droop peak at k=0 high corr, RL peak at k>0 | RL has LAG, mechanism #2 supported |
| Droop peak at k=0 high corr, RL flat/negative corr | RL DECOUPLED from disturbance (consistent with R256 max-out) |
| Droop and RL both peak at k=0 with similar corr | No timing/coupling difference; mechanism #2 refuted |

## Cross-references

- R256 / CLM-0470 (max-out finding)
- R257 / CLM-0475 (smoothness inversion finding)
- R255 / CLM-0460 (probe-first protocol validation)
- CLM-0445 (RL-vs-droop Pareto, this round's mechanism investigation)
