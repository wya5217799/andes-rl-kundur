# Feasibility-native four-VSG action contract

## Status and authority

- Working title remains exactly **Decoupling-Oriented Coordination of
  Paralleled VSGs With Multi-Agent Reinforcement Learning**.
- This is a prospective method contract produced in the project `scratch`
  lane. Its offline action-manifold gate is implementation-qualified, not
  experimental evidence, and it authorizes no ANDES execution or training.
- R375/CLM-1020 remains authoritative for the stopped controller formulation.
  This contract does not reinterpret its guard-failed endpoint diagnostics.

## Decision

Use **four feasibility-native, deterministic-baseline-anchored VSG residual
actions** as the successor hypothesis. Each physical VSG is one runtime actor
and emits one scalar normalized residual. A separately qualified deterministic
controller supplies an already-feasible power anchor for that VSG; the residual
spans only the anchor's remaining lower/upper headroom before reaching the
VSG-owned `pref/tm` port. No central process pools actor outputs into a scalar
or edge action.

This is structurally different from R375. R375 first formed an unconstrained
four-device physical-power request and then relied on the external energy
projection to repair it. The successor defines the controller and policy output
as a fraction of current feasible headroom. The external projection becomes an
identity guard; any external saturation is a hard invalidity, not an accepted
control event.

It is also different from the Model-First line. That line's reusable physical
governor used three edge actors and separate ESD1 storage devices. The successor
uses four VSG node actors and the already object-gated VSG-owned power-reference
ports. Model-First code may donate constraint logic, tests, and failure lessons,
but its objects, results, residual targets, and claims do not transfer.

## Action definition

For VSG actor `i`, let the physical contract expose the current feasible power
interval

```text
[lower_i(t), upper_i(t)]
```

after applying the unchanged power, ramp, voltage/current capability, SOC, and
energy rules to the current state. The deterministic controller must first
produce

```text
baseline_i(t) in [lower_i(t), upper_i(t)].
```

Actor `i` emits residual `r_i(t) in [-1, 1]`. Its physical request is

```text
if r_i >= 0:
    p_i = baseline_i + r_i * (upper_i - baseline_i)
else:
    p_i = baseline_i + r_i * (baseline_i - lower_i).
```

Consequences:

1. `r_i=0` returns the deterministic baseline exactly.
2. `r_i=+1` and `r_i=-1` reach the exact current upper and lower bounds.
3. One actor cannot change another actor's command.
4. The four executed node actions span one common and three differential
   coordinates whenever the four local intervals retain nonzero authority.
5. An infeasible baseline, or an out-of-range/nonfinite residual, fails closed;
   neither is silently clipped.

The implementation seam is
`src/andes_rl_kundur/control/feasibility_native_vsg_action.py`. Its focused
scratch tests cover four literal actors, per-agent locality, common-plus-three-
differential rank, exact endpoint reachability, randomized feasible states, and
identity through the existing VSG energy port.

## Why this avoids the known neural-residual failure

The successor does not regress a neural network onto a precomputed residual
label. A learned actor chooses `r_i(t)` by reinforcement learning inside the
remaining feasible headroom. Zero residual exactly restores the deterministic
controller. Random, independent-RL, no-message MARL, message-enabled MARL, and
non-learning residual arms use the same residual map and physical limits.

A later non-learning oracle remains mandatory, but its role is only to test
whether time-varying feasible actions can improve on the strongest valid
deterministic controller. It does not become a regression target. If that
oracle finds no incremental headroom, training stops before a neural network is
created.

This removes the two already observed failure mechanisms—post-controller ramp
repair and dependence on a supervised residual label—but it does not guarantee
a positive paper. The non-learning headroom gate can still show that no useful
residual decision problem exists.

## Decoupling semantics

The action vector `p(t) in R^4` is analysed as

```text
p_common = mean(p) * [1, 1, 1, 1]
p_differential = p - p_common.
```

This decomposition is an audit view, not a centralized runtime action. The
four node actions already span the common coordinate and the three-dimensional
zero-sum differential subspace.

`Decoupling-Oriented` passes only if the closed-loop input-output evidence on a
fresh bank jointly shows:

1. lower off-diagonal common/differential signed-response energy;
2. lower disturbance-driven differential-frequency energy and settling time;
3. no material common-frequency, peak, RoCoF, failure, bound-contact, energy,
   or control-stress harm; and
4. for the MARL result, loss of incremental benefit when neighbour messages or
   the decoupling objective is removed.

Coordinate naming, reward reduction, or an identity outer projection alone is
not decoupling evidence.

## Runtime information and coordination

- Actor identity: four node actors `VSG_1..VSG_4` at buses `[12,16,14,15]`.
- Runtime action: one normalized residual scalar per actor, executed around an
  already-feasible deterministic command through that actor's own VSG port.
- Independent/no-message arm: local measurements and local feasibility state
  only.
- Message-enabled arm: the same local inputs plus prospectively frozen
  neighbour messages on the four-node communication ring.
- A centralized critic may exist during training, but no centralized state,
  action pooling, or optimizer may be required at execution.
- Shared parameters do not by themselves establish coordination. The
  message-removal and decoupling-objective ablations own that attribution.

## Matched comparison contract

Every comparison arm must share the same four node-action coordinates,
feasibility map, actuator path, physical limits, update timing, development and
held-out banks, and failure accounting.

| Arm | Runtime information | Training | Identified role |
|---|---|---|---|
| zero feasible action | none | none | no-control reference |
| local feasibility-native deterministic | local only | none | matched independent classical baseline |
| neighbour feasibility-native deterministic | local + frozen neighbour messages | none | strongest matched distributed baseline |
| bounded random residual | local feasibility state | none | residual-space sanity reference |
| independent RL | local only; separate actor state | separate/local learning | independent learning value |
| no-message MARL | local only | joint multi-agent training | joint-training value without runtime messages |
| message-enabled MARL | local + frozen neighbour messages | same budget as no-message MARL | runtime coordination increment |
| objective ablation | same as message-enabled MARL | same budget | decoupling-objective increment |
| centralized vector oracle | joint information; same four actions | matched diagnostic budget | nondeployable upper reference only |

### Comparison-identifiability return

- **Decision**: `BLOCK` for full comparator freeze; the action coordinates are
  matched, but the exact observations/messages, policy capacity, training and
  tuning interactions, seeds, checkpoint selection, and sealed-evaluation
  budgets do not yet exist.
- **Executed comparison**: none; Gate A is offline implementation only.
- **Identified estimand after repair**: the incremental held-out physical
  decoupling effect of runtime neighbour messages, conditional on the same
  four feasible node actions, training budget, and policy capacity.
- **Allowed claim now**: none; the action seam is eligible for a prospective
  deterministic plan.
- **Stay-out**: MARL class value, coordination benefit, generalization,
  stability, safety certification, and deployment value.
- **Repair before comparator freeze**: populate every arm's exact observation,
  message, capacity, optimization, interaction, tuning, seed/checkpoint, and
  evaluation-data fields after deterministic efficacy and non-learning
  headroom pass.

## Gate sequence

### Gate A — offline action-manifold gate

Current scratch implementation must show:

- four actors and four independently executed node actions;
- no central action aggregation;
- zero residual returns an already-feasible deterministic baseline exactly;
- residual `[-1,1]` spans only that baseline's remaining lower/upper headroom;
- full common-plus-three-differential rank at an unconstrained interior state;
- identity through the unchanged VSG energy-port projector over randomized
  feasible states; and
- fail-closed behavior for malformed residuals and infeasible baselines.

Gate A is implementation-qualified by focused tests. Direct-diagnostic and
baseline-anchored residual paths each exercise 250 randomized feasible physical
states, in addition to explicit actor/locality/rank/boundary/fail-closed cases.
This is engineering proof only: it qualifies the action seam for a prospective
physical plan and supplies no controller or manuscript result.

### Gate B — deterministic physical gate

A separately registered evidence round must compare zero, local deterministic,
and neighbour deterministic controllers on development and untouched held-out
banks. Every deterministic command must already be feasible because it becomes
the residual anchor; an infeasible baseline is not repaired. The neighbour
controller must clear every decoupling and no-harm endpoint while the outer
projection remains identity on every trajectory. Internal headroom fraction
and bound contact are reported as control-stress endpoints, not hidden.

Stop the formulation if the deterministic arm fails, if the feasible action
rank collapses on the registered states, or if any external projection repairs
an action.

### Gate C — non-learning conditional-headroom gate

Only after Gate B passes, evaluate a bounded time-varying residual oracle inside
the deterministic anchor's remaining headroom on development data. Require a
prospectively frozen nontrivial improvement, nonconstant residuals, and a
coordination-dependent target. Stop if no residual decision problem remains.

### Gate D — MARL comparison

Only after Gates B and C pass, freeze actor/critic capacity, interaction,
tuning, seed/checkpoint, and sealed-evaluation budgets. Training success is not
reward convergence: message-enabled MARL must beat the strongest matched
deterministic, independent-RL, and no-message arms on the registered physical
decoupling endpoints without additional failure or stress.

## Reuse boundary

Directly reusable implementation:

- `active_power.py`: exact current feasible intervals;
- `vsg_energy_port.py` and its environment wrapper: four VSG-owned actions and
  achieved-power energy settlement;
- `andes_vsg_env_v4.py`: four VSG identities and local state;
- physical endpoint, sealed-bank, provenance, failure-retention, and training
  infrastructure;
- independent SAC and CTDE scaffolds only after the training gate opens.

Adaptable design donors only:

- R375 common/differential endpoint definitions and distributed observation
  pattern;
- Model-First headroom-aware allocation, constrained-controller, and edge-flow
  code for constraint logic or diagnostic ablations;
- earlier independent/no-message/message comparison plumbing.

Never transfer:

- R375 gains or guard-failed controller as a safe residual base;
- Model-First edge actors, ESD1 acting object, residual labels, outcomes, or
  claims;
- old checkpoints, rewards, training curves, or title evidence.

## Immediate decision

Gate A is complete in `scratch`. No physical run or training is authorized.
The next eligible action is to write one prospective Gate B experiment
contract; launch still requires a separately reserved evidence round and
readiness gate.
