# ADR-0015: Reset the fixed title to an object-matched manuscript line

- **Status:** Accepted
- **Date:** 2026-08-12
- **Deciders:** repository owner and Codex route review
- **Related:** ADR-0002, ADR-0005, ADR-0012, R338, R359, R363

## Context

The fixed title requires four properties to coexist in one experiment:
paralleled VSG units, decoupling-oriented physical endpoints, per-unit
coordination, and multi-agent reinforcement learning.  The ICEMS line contains
training, but its headline learned object is scalar/shared rather than one
runtime actor per VSG; its later genuine distributed comparison has a bounded
negative neural-increment result.  The model-first line established stricter
plant, information, actuator, and headroom gates, but did not reach MARL or a
positive controller increment.  Combining their claims would cross manuscript
and experimental-object boundaries rather than repair the title.

The external survey recommends a hybrid deterministic-plus-residual route, and
the original Yang et al. study (DOI `10.1109/TPWRS.2022.3221439`) supplies a
useful per-VSG inertia/droop coordination reference.  The repository already
contains an ANDES four-VSG environment, independent SAC and CTDE agents,
deterministic distributed controllers, safety/headroom mechanisms, and sealed
evaluation infrastructure.  Those implementations are valuable even though
their earlier results cannot be transferred.

## Decision

Create `paralleled-vsg-marl` as the only active title-goal line and preserve the
exact title **Decoupling-Oriented Coordination of Paralleled VSGs With
Multi-Agent Reinforcement Learning**.  Freeze `icems2026`,
`decoupling-marl-model-first`, and the ICEMS-derived `sci-upgrade-survey` as
evidence lines.  Freezing changes navigation and execution authority only; it
does not delete or weaken their bounded claims.

The new line starts from the Yang-compatible object contract: one ANDES VSG
unit equals one runtime agent with one independent bounded inertia/damping or
residual action.  A centralized critic may be used during training, but central
scalar action aggregation and edge actors do not satisfy this identity.

For the fastest defensible scope, `decoupling` means suppressing the
inter-device dynamic coupling and differential oscillation created by
heterogeneous inertia/droop parameters and disturbances.  It does not mean
inner-loop electromagnetic P/Q decoupling, reactive-power sharing, or
circulating-current control, which the current ANDES electromechanical object
does not represent.

The execution order is fixed:

1. prospective per-VSG object/action intervention gate and qualitative Yang
   mechanism reproduction;
2. matched strong deterministic decoupling/coordination baseline and residual
   headroom gate;
3. bounded per-VSG residual MARL with coordination ablations;
4. held-out operating-condition and safety evaluation;
5. topology OOD and real-time evidence only as later venue-driven upgrades.

Code, contracts, probes, and evaluation tools may be adapted prospectively.
Historical checkpoints, result values, claims, and manuscript language do not
move to the new line.  Yang et al. remains an algorithm/object/reward reference,
not a Simulink numerical target.

## Consequences

- Cold start selects one unambiguous manuscript line and cannot silently route
  back to a failed title/object combination.
- The next experiment is an object and actuator-identity gate, not training.
- Existing assets shorten implementation time while every scientific result is
  regenerated on the new object under a new round.
- A failed object gate stops the fixed-title route before compute is spent.
- A passed object gate still does not authorize MARL until the deterministic
  baseline and residual-headroom gate pass.

## Rejected alternatives

- **Keep ICEMS active and rename its agents:** rejected because naming cannot
  turn scalar/shared or edge actions into per-VSG actions, and the genuine
  distributed comparison is already bounded negative.
- **Continue model-first until MARL emerges:** rejected because its completed
  information families and action contract do not currently provide a causal
  controller increment; more variants would extend a negative formulation.
- **Merge old claims into one paper:** rejected because claim union does not
  create one common experimental object.
- **Rebuild everything:** rejected because the repository has reusable
  per-VSG, deterministic-control, safety, and evaluation implementations.

