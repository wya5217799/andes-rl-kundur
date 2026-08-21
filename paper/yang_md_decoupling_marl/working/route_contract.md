# Yang-compatible common/differential decoupling-MARL route

## Decision

Retain the Yang et al. scientific object and execution semantics: four
network-coupled VSG units, one actor per VSG, direct bounded inertia/droop
adaptation, and local plus permitted neighbour measurements. Change only the
question that the old fixed-topology algorithm sweep could not answer: whether
prospectively heterogeneous operating conditions expose a physical
common/differential decoupling increment that runtime neighbour messages and a
mode-aware MARL objective can recover.

The candidate learner is **common--differential mode-aware multi-agent TD3**
(`CD-MATD3`). It is a future comparison object, not a current result. The next
gate is a non-learning joint-headroom study; no learner is eligible until that
gate passes.

## Research question

Can a fresh Yang-compatible four-actor direct `delta_M/delta_D` controller use
permitted neighbour messages to reduce physical common/differential
cross-response and disturbance-driven inter-VSG differential oscillation
beyond a matched strong deterministic controller, while preserving common
frequency response, solver completion, bounds, saturation, and control stress?

## Paper type and key idea

- Type: technique paper.
- Key idea: keep the Yang control object and actor permissions, but learn a
  differential-mode objective under an explicit common-mode no-harm constraint
  and attribute the increment with matched message and objective ablations.
- Intended contribution count: three -- one bounded mode-aware learner, one
  physical decoupling benchmark, and one coordination-attribution comparison.

## Scientific object

- Platform: ANDES 2.0.0, modified Kundur two-area network.
- Devices: four explicitly identified VSG proxies on one shared network.
- Runtime ownership: actor `i` writes only VSG `i`'s two-dimensional
  `delta_M_i, delta_D_i` vector.
- Action contract: identical physical coordinates, box limits, update timing,
  projection, initialization, and post-processing across all learning arms.
- Deployment information: local frequency/RoCoF/power/action history plus the
  same permitted neighbour messages; global statistics remain training-only
  when used by a critic.
- First-paper scope: fixed connectivity with prospectively varied operating
  point, VSG inertia/droop mismatch, and disturbance location, sign, magnitude,
  and distribution. No topology- or VSG-count-generalization claim.

## Decoupling semantics

Let

\[
z_c=\tfrac14\mathbf 1^\top\Delta f,\qquad z_d=T_d\Delta f,
\]

where `T_d` is the registered arithmetic inter-area plus two intra-area
differential transform. These coordinates are endpoint views, not asserted
eigenmodes.

`Decoupling-Oriented` requires all of the following on fresh paired probes and
disturbances:

1. lower off-diagonal common-to-differential and differential-to-common signed
   response energy;
2. lower disturbance-driven differential-frequency energy and settling;
3. no material degradation in common-frequency integral, worst-unit peak,
   RoCoF, completion/failure, saturation, action effort, or movement;
4. removal of the cross-coordinate objective removes a material part of the
   measured increment.

A coordinate transform, scalar reward increase, legacy composite score, or
average-frequency improvement alone is not decoupling evidence. Electromagnetic
P/Q decoupling, reactive sharing, switching, protection, EMT, HIL, and field
deployment are outside this paper.

## Learner contract

The fresh base learner is memoryless TD3 because repository evidence supports
repeatable four-actor training while legacy recurrent checkpoints carry a
target-alignment defect. Each standard twin critic returns a two-component
value `(Q_common, Q_differential)`. The actor minimizes differential cost under
an adaptive nonnegative multiplier enforcing a prospectively frozen common-mode
cost budget. The common cost retains an absolute-frequency/RoCoF anchor; the
differential cost uses inter-VSG frequency and power disagreement. This rules
out the sync-only collective-drift optimum by construction.

The learner name does not carry the contribution. Physical input-output
decoupling and the two causal ablations below carry it.

## Gate sequence

### G0 -- line and design registration

R398 registers the line, object, title contract, comparison logic, evidence
non-transfer boundary, and next gate. It creates no trajectory or performance
evidence.

### G1 -- non-learning joint headroom

Freeze one heterogeneous development bank and one unseen evaluation bank before
candidate outcome inspection. Revalidate literal four-actor M/D identity and
measure:

- zero adaptation;
- one strongest matched deterministic local/neighbour dynamic M/D law selected
  on development only;
- one bounded outcome-seeing finite M/D oracle using the same action box and
  timing, used only as a training-necessity upper bound.

`PASS` requires at least 5% improvement versus the deterministic baseline on
both off-diagonal cross-response energy and disturbance differential energy,
common no-harm within 3%, nonconstant independently attributable per-VSG
actions, and every completion/bound/stress guard. Otherwise stop this line
before training. These 5% improvement and 3% no-harm effect floors are fixed
here and may not be loosened. Exact estimators, uncertainty, scenario counts,
frequency/RoCoF windows, action timing and units, and resource budgets belong
to the prospective G1 round and may not be filled from observed outcomes.

### G2 -- fresh three-seed development canary

Enter only after G1 passes. Compare fresh scalar-reward memoryless TD3 on the
Yang-compatible object,
CD-MATD3 without neighbour messages, message-enabled CD-MATD3, and the
cross-coordinate-objective ablation. Use identical interaction, tuning,
capacity, checkpoint-selection, and evaluation-data budgets. Stop if the
message arm has no consistent direction, the objective arm reward-hacks, or a
physical/no-harm guard fails.

### G3 -- sealed multi-seed comparison

Enter only after G2 passes. Freeze at least five independent training seeds,
the unseen bank, paired estimands, uncertainty method, capacity, tuning,
checkpoint selection, and artifact budget. Include the strongest G1
deterministic controller. A positive title result requires physical decoupling
gain over that controller plus separately attributable message and objective
increments. Universal MARL or deployment superiority stays outside the claim.

### G4 -- result, claim, and manuscript

Consume only valid final machine decisions. Audit one canonical feed for
evidence and power-system correctness, then register the bounded claim. Draft
the body before title-bearing abstract and contributions.

## Planned comparator contract

| Arm | Object/action/timing | Runtime information | Training-only information | Planned attribution |
|---|---|---|---|---|
| Strong deterministic | same four VSG M/D vectors and limits | matched local/neighbour signals | none | non-learning reference |
| Fresh scalar-reward TD3 | same | Yang-compatible local/neighbour signals | none or matched critic scope, frozen prospectively | matched direct-M/D learner baseline; not an exact Yang SAC reproduction |
| CD-MATD3 no-message | same | local only | same joint critic scope as message arm | mode-aware bundle without runtime coordination |
| CD-MATD3 message | same | local plus permitted neighbours | same as no-message arm | runtime neighbour-message increment |
| Objective ablation | same | same messages as full arm | same as full arm | cross-coordinate objective increment |

All learning arms must match actor/critic capacity, interaction count, tuning
budget, seeds, checkpoint rule, and evaluation access. Parameter sharing and
centralized critics are training architecture, not runtime coordination.
Training seed is the independent learning unit; scenario contrasts are paired
within seed and aggregated to seed-level estimands.

## Comparison identifiability

### G1 decision: ALLOW

- Executed comparison: prospective only; same object/action/timing for zero,
  deterministic, and privileged finite-oracle arms.
- Identified estimand: whether material joint physical headroom exists beyond
  the matched deterministic baseline on the frozen heterogeneous formulation.
- Allowed claim: a positive G1 can authorize training necessity; a negative G1
  closes only this formulation.
- Qualification: the oracle is outcome-seeing and supports headroom, not
  deployability or MARL value.
- Stay out: learner superiority, coordination, topology generalization, safety
  certification, or deployment.

### Future G2/G3 decision: QUALIFY until budget freeze

- Full versus no-message identifies runtime message value only after all
  capacity/training/tuning/selection/evaluation budgets match.
- Full versus objective ablation identifies the registered decoupling-objective
  value under the same condition.
- Full versus fresh scalar-reward TD3 is a method-bundle contrast; it does not
  isolate one algorithmic factor.
- Missing numerical budgets, bank identity, and uncertainty rules block launch
  but do not block G1 design.

## Evidence and reuse boundary

Reusable: environment/agent interfaces, fresh code paths, tests, evaluation
plumbing, physical endpoint definitions after prospective revalidation, and
historical failure mechanisms as design constraints.

Non-transferable: checkpoints, training curves, result values, thresholds,
claims, feeds, manuscript prose, and old title support. Every headline value
must originate from a new prospectively registered round on this line.

## Stop rules

- No algorithm sweep. The selected learner may receive implementation repair,
  not outcome-driven architecture replacement.
- G1 failure ends the experiment route without G2.
- G2 failure ends the selected learner contract without seed expansion.
- Extra information, action coordinates, projection, tuning, or checkpoint
  access narrows the claim or invalidates the intended attribution.
- A successful run establishes only the executed fixed-connectivity ANDES
  formulation and its registered heterogeneous bank.
