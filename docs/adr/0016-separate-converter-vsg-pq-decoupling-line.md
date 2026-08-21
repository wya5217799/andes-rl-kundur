# ADR-0016: Separate the converter-level VSG P/Q-decoupling line

- **Status:** Accepted
- **Date:** 2026-08-14
- **Deciders:** repository owner and Codex research mission
- **Related:** ADR-0005, ADR-0012, ADR-0015, R382, R383

## Context

The `paralleled-vsg-marl` line has reached an experiment-side terminal state.
Its registered object is a `PV+GENCLS` VSG proxy with a VSG-owned active-power
port, and its meaning of decoupling is limited to common/differential
electromechanical motion.  R382 found no registered joint disturbance/probe
headroom for that formulation.  Replacing its plant with a converter-level
voltage-source model and adding reactive-power dynamics would change the
physical object, action authority, endpoints, initialization risks, and claim
boundary.  It therefore cannot be treated as another attempt on the same line.

Three external research reports motivate a physics-first route: establish the
converter and P/Q-decoupling object before considering multi-agent learning.
They are advisory inputs, not project evidence.  ANDES 2.0.0 provides candidate
converter-level VSG models, while the repository has not yet integrated those
models into its Kundur experiment object.

## Decision

Create the independent manuscript line `converter-vsg-pq-decoupling` with the
provisional title **Physics-First P/Q Decoupling and Coordinated Control of
Converter-Level VSGs**.

Keep ANDES 2.0.0 as the platform of record and preserve the Kundur two-area
network connectivity as the system benchmark.  The line may replace the
generator/VSG device representation with one registered converter-level VSG
per controlled unit.  Device parameters, operating points, disturbances, and
R/X conditions may vary only under prospective contracts; topology
generalization is a later, separately gated extension.

The route order is fixed:

1. object, initialization, and signed per-device `Pref/Qref` authority;
2. matched deterministic P/Q-decoupling control with current, power, voltage,
   convergence, and control-stress guards;
3. non-learning residual headroom and information-value gates;
4. residual MARL only if the preceding gates pass;
5. held-out conditions, alternative topology, EMT, HIL, or deployment evidence
   only after the phasor-domain mechanism is established.

The initial registered model formulation is ANDES `REGCV1`.  Failure of its
prospective object/authority gate stops that formulation.  `REGCV2`, `REGF2`,
or another model may be considered only as a separately authorized successor,
not as an outcome-driven substitution inside the same attempt.

The old line remains active for manuscript closure and keeps all of its
evidence.  No old result, checkpoint, claim, threshold, or performance wording
transfers to the new line.  Reusable source code and methodology are design
inputs that require prospective revalidation.

## Consequences

- A new ANDES trajectory requires a round owned by the new line.
- The first experiment is a model/object/authority gate, not a controller or
  learning comparison.
- The working title remains scientifically useful if learning is never
  authorized; MARL is not pre-committed in the title.
- Small development canaries use minimal concurrency.  A large formal bank
  must use a measured capacity ladder and freeze the highest safe useful
  concurrency, with one native numerical thread per WSL Python process.
- Passing phasor-domain P/Q gates does not establish switching, harmonic,
  protection, EMT, HIL, or deployment validity.

## Rejected alternatives

- **Reopen R382 with a new device model:** rejected because the physical object
  and decoupling definition change.
- **Change the Kundur network immediately:** rejected because it would confound
  the device-model intervention with topology change.
- **Put MARL in the new title now:** rejected because no non-learning headroom
  or information gate has passed on the converter-level object.
- **Move directly to EMT:** rejected because the cheapest decisive gate is the
  ANDES phasor-domain object and authority test.

