# Technical audit

Apply the relevant checks exhaustively. Record `not applicable` explicitly for
entire categories that do not belong to the manuscript.

## System boundary and operating point

- Identify buses, branches, synchronous machines, inverter-based resources,
  loads, controls, protection, communication, and external-grid equivalents.
- Reconcile the narrative model with the equations, parameter tables, simulator
  implementation, initialization, and one-line diagram.
- Verify the equilibrium construction, power-flow solution, disturbance-free
  initialization, and any switching between algebraic and dynamic models.
- Separate model-of-record behavior from proxies, surrogates, reduced models,
  and unavailable plant dynamics.

## Equations, states, and conventions

- Define every state, algebraic variable, parameter, input, output, index, and
  reference frame before use.
- Check dimensional consistency and per-unit bases for power, energy, inertia,
  damping, impedance, voltage, current, time, angular speed, and frequency.
- Verify nominal frequency, angular-frequency conversion, sign conventions,
  Park-frame orientation, and generator-versus-load injection conventions.
- Check discretization, sampling, delay, solver tolerances, event ordering, and
  continuous/discrete controller interaction.
- Recompute damping ratio, frequency, normalization, aggregation, and coordinate
  transforms used by headline results.

## Control authority and feasibility

- Trace every policy or controller output to a physical actuator.
- Verify amplitude, rate, slew, saturation, energy, state-of-charge, recovery,
  deadband, and anti-windup constraints over the full simulation horizon.
- Distinguish parameter modulation from real-time power injection and distinguish
  commanded values from achieved plant responses.
- Check whether the observation and communication pattern matches centralized,
  decentralized, distributed, or local-control claims.
- Compare controller bandwidth with plant modes and with the time scale of the
  claimed effect.

## Frequency and dynamic-performance semantics

- Separate common/center-of-inertia frequency restoration from relative
  synchronization and inter-area motion.
- State whether frequency is electrical speed, bus frequency, arithmetic mean,
  inertia-weighted mean, or another estimator.
- Define RoCoF windows and filters, nadir/zenith extraction, settling or final
  windows, IAE/ISE normalization, and failure handling.
- Distinguish a bounded transient reduction from sustained restoration.
- Match every metric's sign and direction to the prose.

## Small-signal and modal analysis

- Verify the linearization point, state matrix, eigenvalue convention, damping
  ratio, modal frequency, and treatment of conjugate pairs.
- Check participation-factor normalization and whether comparisons across
  operating points remain meaningful.
- Require a branch-tracking rule for parameter sweeps. Inspect mode swaps,
  hybridization, repeated eigenvalues, local modes, and identification flags.
- Bound small-signal findings to the neighborhood of the equilibrium. Treat
  time-domain survival as a separate empirical question.

## Weak-grid and topology claims

- Name the changed physical quantity: short-circuit strength, Thevenin
  impedance, line impedance, network topology, converter penetration, or a
  declared proxy.
- Preserve proxy language when no unit-valid SCR or grid-strength conversion was
  performed.
- Distinguish one-parameter stress tests on one topology from generalization to
  unseen operating points, contingencies, sizes, or graphs.
- Require held-out systems or topologies for topology-general claims.

## Stability and safety

- Identify whether evidence is local small-signal, transient simulation,
  Lyapunov/energy-function analysis, robust analysis, reachability, formal
  verification, or empirical stress testing.
- Match the claim to that evidence class. A reward penalty establishes an
  optimization preference; a guard establishes checked feasibility on its tested
  set; neither alone establishes a certificate.
- Inspect the tested disturbance envelope, region of attraction, parameter
  uncertainty, delay/dropout, faults, outages, and protection interactions before
  accepting robustness or safety wording.

## Learning-enabled control

- Verify training/evaluation separation, frozen checkpoints, seed selection,
  observation/action equality, interaction budgets, tuning budgets, and baseline
  implementation quality.
- Separate policy-class value from information advantage, centralized execution,
  parameter sharing, communication, or selection-oracle effects.
- Treat outcome-seeing selection, retrospective checkpoint choice, and
  post-evaluation metric choice as non-deployable evidence unless explicitly
  framed as an oracle or upper bound.
