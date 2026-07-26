# ICEMS 2026 chapter blueprint

Target: IEEE A4 double column, 4--6 pages, no page numbers.

## Abstract

Write last. Four moves: problem, decoupled controller, frozen paired protocol,
balanced result. Include the two R278 co-primary effects and conclude that the
architecture is valid but the tested seed does not establish overall adaptive
MARL value.

## I. Introduction

Six flowing paragraphs:

1. VSG background and why paralleled units create common and differential
   frequency coordinates.
2. Classical parallel-VSG restoration and oscillation damping; explain that
   common support and differential allocation are distinct.
3. Adaptive/RL literature; identify the confound when inertia/damping and
   aggregate/differential support are optimized together.
4. Evidence-discipline gap: strong matched baseline, physical 60-Hz
   full-horizon endpoints, uncertainty, safety/storage guards; briefly disclose
   removal of the digest's weighted ensemble.
5. Exact objective and the fast/slow, common/differential architecture.
6. Three contributions plus headline positive and negative findings; paper
   organization.

## II. Decoupled control problem

- Four-VSG swing-scale model.
- Common frequency, two-area differential frequency, and synchronization loss.
- Frozen slow droop--PI storage layer.
- Frozen 3-s common-inertia pulse.
- Explain why these layers are validated separately before MARL.

## III. Hard-zero-sum MARL

- Shared memoryless actor and seven local observations.
- Scalar two-area projection `q[1,1,-1,-1]`.
- Magnitude, slew, active-window, and physical zero-sum audits.
- Centralized twin critics, reward, and fixed TD3 hyperparameters.
- Figure 1: multi-layer feedback architecture.

## IV. Prospective experiment

- Modified Kundur/ANDES setup and exact hybrid-actuator boundary.
- 24 disturbances: four locations x two signs x three severities.
- 60-s trajectories, 0.2-s control interval, 60-Hz physical metrics.
- Stagewise matched comparisons R274--R278.
- Paired bootstrap and prospectively frozen success/no-harm gates.

## V. Results and discussion

- Table I: classical decomposition, oracle, and R278 paired effects.
- Figure 2: forest plot of paired ratio-of-means effects and 95% intervals.
- R274/R275 positive, R276 additive only.
- R277 establishes attainability only.
- R278 synchronization passes, inter-area co-primary fails uncertainty; overall
  `PILOT-NO-GO`.
- Report action, completion, storage, slow/common, fast-safety, and tail guards.
- Discuss why the negative gate is informative: the constrained layer is
  interpretable, but this one policy/seed does not justify more training under
  the frozen protocol.

## VI. Limitations

- Single seed and viewed development bank.
- Phasor-domain hybrid actuator, not EMT or unified GFM-BESS.
- No stability certificate or topology generalization.
- Float32 tolerance repair disclosure.

## VII. Conclusion

Restate the decomposition, the partial MARL signal, and the no-go conclusion.
Do not propose extra experiments as if they were missing from the current
paper; state that broader claims would require a new prospectively sealed
study.
