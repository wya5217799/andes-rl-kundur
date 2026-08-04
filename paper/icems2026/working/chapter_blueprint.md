# ICEMS 2026 chapter blueprint

Target: IEEE A4 double column, 4--6 pages, no page numbers.

## Abstract

Write last. Four moves: problem, decoupled controller, frozen paired protocol,
balanced result. Include the R280 three-seed effects and conclude that the
tested shared scalar factorization is meaningfully effective but inferior to
the size-matched centralized actor. Do not generalize this result to MARL as a
class.

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
6. Three contributions plus the bounded positive and negative findings; paper
   organization. Name the common scalar executed action in the architecture
   comparison.

## II. Decoupled control problem

- Four-VSG swing-scale model.
- Common frequency, two-area differential frequency, and synchronization loss.
- Frozen slow droop--PI storage layer.
- Frozen 3-s common-inertia pulse.
- Explain why these layers are validated separately before MARL.

## III. Hard-zero-sum learning architectures

- Shared memoryless actor and seven local observations.
- Scalar two-area projection `q[1,1,-1,-1]`.
- Magnitude, slew, active-window, and physical zero-sum audits.
- Centralized twin critics, reward, and fixed TD3 hyperparameters.
- Size-matched centralized actor with the joint observation and the same
  executed scalar action; this is a comparison with one shared scalar
  factorization, not with MARL as a class.
- Figure 1: multi-layer feedback architecture.

## IV. Prospective experiment

- Modified Kundur/ANDES setup and exact hybrid-actuator boundary.
- 24 disturbances: four locations x two signs x three severities.
- 60-s trajectories, 0.2-s control interval, 60-Hz physical metrics.
- Stagewise matched comparisons R274--R280 and the bounded R291 handoff gate.
- Paired bootstrap and prospectively frozen success/no-harm gates.

## V. Results and discussion

- Table I: classical decomposition, oracle, and R280 paired effects.
- Figure 2: forest plot of paired ratio-of-means effects and 95% intervals.
- R274/R275 positive, R276 additive only.
- R277 establishes attainability only.
- R280 corrects the float32-only audit defect without rerunning trajectories:
  both learned controllers beat `q=0`, while the shared scalar factorization is
  inferior to centralized TD3 on both primary endpoints.
- R291 is a bounded negative result: neither the fixed 5-s extension nor either
  tested deterministic state-aware smooth handoff clears the joint gate over
  the fixed 3-s benchmark.
- Report action, completion, storage, slow/common, fast-safety, and tail guards.
- Discuss why the negative gates are informative: the scalar shared policy is
  effective but does not identify architecture-wide MARL value, and the fixed
  3-s pulse remains a benchmark rather than a solved fast--slow handoff law.

## VI. Limitations

- Three predefined seeds and one independent disturbance bank do not
  characterize the wider seed or plant population.
- Phasor-domain hybrid actuator, not EMT or unified GFM-BESS.
- No stability certificate or topology generalization.
- The shared execution layer centrally aggregates four local votes and does
  not establish fully decentralized deployment.
- R291 covers one plant, one bank, and two deterministic handoff contracts; it
  does not establish 3-s optimality or general handoff ineffectiveness.
- Float32 tolerance repair disclosure.

## VII. Conclusion

Restate the decomposition, the positive learned-allocation result, the
inferiority of the tested shared scalar factorization, and the bounded negative
handoff result. Do not claim MARL is generally unnecessary, modal/dynamic
decoupling, 3-s optimality, or fully decentralized execution. Broader claims
would require a new prospectively sealed study.
