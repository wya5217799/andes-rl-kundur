# Same-line CD-MATD3 training amendment after R399

## Decision

Continue the fixed-title `yang-md-decoupling-marl` manuscript line with the
already selected **common--differential mode-aware multi-agent TD3**
(`CD-MATD3`).  The Yang-compatible scientific object remains four
network-coupled VSG proxies, one independently executed actor row per VSG,
direct bounded `delta_M_i,delta_D_i`, and local plus permitted neighbour
measurements.

This decision is prospective and outcome-aware.  It does not change R399's
valid finite-law `STOP-NO-JOINT-HEADROOM` classification.  R399 now supplies a
strong deterministic comparator and a disclosed risk signal; it no longer
acts as a logical substitute for training the selected neural agents.  No
R399 evaluation profile may become unseen evidence for the learning route.

This amendment supersedes the old route's gate order and stop rules after G1.
All unchanged object, action, information, decoupling, evidence-reuse, and
scope limits in `working/route_contract.md` remain incorporated by reference.

## Paper positioning and logic

- **Type**: technique paper.
- **Background**: Yang-compatible distributed actors can adapt each VSG's
  inertia and droop from local/adjacent measurements, but a synchronization or
  scalar reward does not itself demonstrate input--output decoupling.
- **Limitation 1**: scalar synchronization learning does not separately expose
  common-to-differential and differential-to-common response.
- **Limitation 2**: joint training or a centralized critic does not establish
  that runtime neighbour messages create a coordination increment.
- **Limitation 3**: comparison only with zero or weak control cannot support a
  title-positive result against a matched strong deterministic M/D law.
- **Key idea**: retain the Yang four-actor direct-M/D object and learn a
  common--differential objective under an explicit common-mode no-harm
  constraint, with matched message and objective attribution.

The three challenges and modules are one-to-one:

1. Separate differential improvement from collective frequency drift -> a
   two-component common/differential critic and nonnegative common constraint.
2. Identify runtime coordination -> capacity-matched message and no-message
   actors with identical training-only critic information.
3. Establish a physical increment rather than a reward increment -> matched
   strong deterministic and fresh Yang-compatible learners, fresh held-out
   conditions, physical cross-response endpoints, and no-harm guards.

The intended contributions remain three: the bounded mode-aware learner, the
physical common/differential decoupling evaluation, and the coordination plus
objective attribution comparison.  The paper does not claim a new RL class,
topology/VSG-count generalization, stability or safety certification, EMT,
HIL, hardware, or deployment.

## Fixed learner and non-sweep boundary

- Proposed method: memoryless CD-MATD3 with independently executed actors.
- Fresh Yang-compatible learning baseline: scalar-reward memoryless TD3 on the
  same object/action/timing and permitted local/adjacent observations.  It is
  an engineering baseline for this route, not an exact reproduction of Yang's
  SAC optimizer.
- No-message ablation: same CD-MATD3 capacity and training-only critic scope;
  runtime actors receive local observations only.
- Objective ablation: same messages, capacity, budget, and selection rule as
  the full method, without the cross-coordinate objective bundle.
- No SAC/PPO/GNN/recurrent/other algorithm replacement is eligible after this
  amendment.  Implementation repairs may restore the frozen contract but may
  not change the scientific comparison.

## Gate A -- fresh three-seed development canary

The next evidence round may train exactly three learning arms:

1. fresh Yang-compatible scalar-reward memoryless TD3;
2. CD-MATD3 without runtime neighbour messages;
3. message-enabled CD-MATD3.

Each arm uses exactly three fresh training seeds, the same development
conditions, interaction count, actor/critic capacity, tuning allowance,
checkpoint rule, evaluation access, action box, slew, timing, and physical
post-processing.  The strongest R399 deterministic implementation is an
evaluation reference and receives no training budget.

Before execution, the Gate A round must prospectively freeze the development
bank, 50-Hz controller-to-60-Hz reporting semantics, observation/action units,
literal M/D decoder and readback, update/event timing, reward scaling,
interaction/tuning/checkpoint budgets, convergence and missing-run rules,
capacity evidence, and physical/no-harm estimators.  R400 fills none of these
from a later outcome.

Canary continuation requires:

- all seed runs and evaluations complete and all independent per-VSG action,
  bounds, slew, saturation, solver, and common no-harm guards pass;
- the full method has positive seed-median improvement on both registered
  physical endpoints versus each learning comparator;
- at least two of three seeds improve both endpoints versus each learning
  comparator;
- the point estimate versus the strong deterministic reference is favorable
  on both endpoints, without requiring the formal ten-percent floor yet;
- reward or coordinate score alone cannot pass the canary.

Failure ends this selected learner route without algorithm replacement.  A
pass authorizes only a separately planned formal comparison; it is not title
evidence.

## Gate B -- sealed five-seed held-out comparison

Only a later evidence round may freeze and execute Gate B.  It must use at
least five fresh independent training seeds and a new held-out bank that was
not used by R399, Gate A, tuning, checkpoint selection, or method repair.  The
comparison includes:

- strongest matched deterministic M/D control;
- fresh Yang-compatible scalar-reward TD3;
- full CD-MATD3;
- CD-MATD3 without runtime neighbour messages;
- cross-coordinate-objective ablation.

All learning arms must match interaction, tuning, capacity, checkpoint,
selection, and evaluation budgets.  Training seed is the independent learning
unit; scenario contrasts are paired within seed.

A title-positive result requires every item below:

1. full CD-MATD3 lowers aggregate off-diagonal common/differential
   cross-response energy by at least `10%` versus the strong deterministic
   comparator;
2. full CD-MATD3 lowers aggregate disturbance-driven differential energy by at
   least `10%` versus that comparator;
3. common-frequency integral, worst-unit peak deviation, and RoCoF are each no
   worse than `103%` of the deterministic comparator;
4. message-enabled CD-MATD3 has a consistent positive seed-level increment
   over no-message CD-MATD3 on the registered physical endpoints;
5. removing the cross-coordinate objective removes a material registered
   increment under matched conditions;
6. every completion, solver, actuator identity, independent action, bounds,
   slew, saturation, action-stress, provenance, and uncertainty guard passes.

Exact banks, estimators, uncertainty rules, convergence criteria, training and
tuning budgets, capacity evidence, seal, and stopping implementation must be
frozen before Gate B execution.  The ten-percent improvement and three-percent
no-harm floors cannot be relaxed after outcomes.

## Comparison identifiability

- Full versus no-message identifies the runtime-neighbour-message increment
  only when every non-message privilege is matched.
- Full versus objective ablation identifies the decoupling-objective bundle
  only when runtime messages and all budgets are matched.
- Full versus fresh Yang-compatible TD3 is a method-bundle comparison and does
  not isolate one algorithmic factor.
- Full versus strong deterministic identifies a bounded controller increment
  on the executed bank; it does not prove MARL superiority as a class.

## R400 execution boundary

R400 writes only this decision, its ledger/feed closure, and current-line
navigation.  It runs no ANDES trajectory, implements no learner, trains no
agent, selects no checkpoint, opens no held-out bank, and creates no
performance evidence.  Gate A requires its own prospectively reserved evidence
round and preflight.

## Self-consistency return

- Limitations -> key idea: `PASS`.
- Key idea -> challenges: `PASS`.
- Challenges -> methodology modules: `PASS`.
- Methodology -> contributions and registered comparisons: `PASS`.
- Current next action: `ALLOW` only for a separately frozen Gate A canary.
