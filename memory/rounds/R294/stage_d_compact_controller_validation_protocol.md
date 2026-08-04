# R294 Stage D — compact frozen controller validation

This protocol is frozen after the outcome-aware Stage-C development screen
and before any Stage-D trajectory.  Stage C selected `Ksync=1.0` independently
for both vector formulations.  No Stage-D result may change that gain, the
bank, endpoints, thresholds, or interpretation boundary.

## Purpose and model boundary

The experiment asks whether the selected coupling-aware independent-active-
power laws retain differential-frequency value on held-out operating cases
without material common-frequency or physical-constraint harm.  The full
nonlinear `AndesMultiVSGEnvV4Storage` DAE is the plant of record.  The tested
controllers are non-predictive deterministic fallbacks; passing this gate does
not validate an LPV predictor, MPC/DMPC, neural residual, or a stability proof.

The 12 scenarios are the complement of the four Stage-C development cases in
the fixed Cartesian bank `tie k={1,2} x location={PQ_0,PQ_1,PQ_Bus14,
PQ_Bus15} x disturbance sign={-1,+1}`.  Thus controller outcomes for every
Stage-D scenario are held out from gain selection.  `k` remains an impedance-
strength proxy within one modified Kundur system and is not a multi-topology
claim.

Each scenario runs 100 steps at 0.2 s with three arms (36 trajectories):

1. scalar equal-sharing active-power PI;
2. joint-observation centralized vector PI with `Ksync=1.0`;
3. neighbour-only distributed DAPI with `Ksync=1.0` and integral-consensus
   gain `1.0 1/s`.

All arms use `Kp=2.0`, `Ki=0.2`, zero M/D modulation, the same four ESD1
devices, and exactly the same per-device power, current, ramp, SOC, and energy
projection.

## Comparison-identifiability matrix

| Arm | Runtime information | Physical action | Execution | Inference consequence |
|---|---|---|---|---|
| equal-sharing PI | all four frequencies reduced to their mean | one request repeated as four projected `P_i` | central scalar law | contrast with vector arms combines action-space and coordination value |
| centralized vector | joint four-frequency vector and exact global mean/differential projector | four independent projected `P_i` | one joint controller | upper reference for this executed joint-information law |
| distributed DAPI | local frequency, two ring-neighbour frequencies, and neighbour-coupled integral messages | four independently executed projected `P_i` | no action aggregation or joint-observation server | genuine distributed formulation; contrast with central includes information and law differences |

The central/distributed contrast is therefore not a pure universal
architecture effect.  It estimates the difference between these two executed
formulations under matched plant, gains, horizon, action coordinates, and
constraints.

## Frozen endpoints and decision tree

Every trajectory must complete with finite telemetry, `TDS.test_ok`, zero
storage-constraint violations, and exact declared scalar/vector action shape.
Any failed record makes the formal bank `INVALID` and its performance endpoints
non-evidence.

For each vector candidate versus equal-sharing PI, compute paired scenario-
cluster bootstrap ratios of means (20,000 resamples, fixed seed) and the worst
individual paired ratio.

- Common no-harm: for each of mean-frequency IAE, worst-bus peak, and maximum
  absolute RoCoF, the 95% ratio interval upper bound must be at most `1.05`
  and the worst individual ratio at most `1.10`.
- Differential materiality: for normalized synchronization loss and fast
  inter-area IAE, the point ratio must be at most `0.98` and its 95% interval
  upper bound strictly below `1.0`.

Classify each candidate independently as pass/fail.  The distributed-versus-
central contrast is secondary: call one executed formulation clearer only if
both differential-endpoint 95% intervals lie wholly on the same side of one;
otherwise report no clear difference.

## Allowed conclusion ceiling

If valid and passing, the strongest allowed conclusion is that the named
coupling-aware vector controller retained held-out differential-frequency
improvement without the registered common-frequency harm on this fixed
modified Kundur bank.  A distributed pass establishes a valid genuinely
distributed deterministic baseline.  It does not establish that multi-agent
control, MARL, multiple neural networks, or decentralized control in general
is superior to centralized control.
