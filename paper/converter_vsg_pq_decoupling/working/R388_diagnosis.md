# R388 strict scientific-stop diagnosis

## Immutable symptom and feedback contract

The unique sealed R388 execution is immutable. The diagnostic loop reads only
its create-only artifacts and performs no replacement simulation. The initial
feedback contract required the formal classification to be
`REGCV1-SIGNED-AUTHORITY-PASS`; it reproduced red with
`STOP-REGCV1-SIGNED-AUTHORITY`. The formal record nevertheless passes integrity,
reference preservation, initialization diagnostics, and finite-value checks.

The post-diagnosis verification re-hashed every formal manifest entry and
asserted the exact raw-action, guard, convergence, and early-response counts.
It exited green with the valid scientific STOP unchanged.

## Ranked hypotheses and discriminating probes

1. **A genuine dynamic/electrical failure follows correct setpoint writes.**
   Recompute every requested absolute value, target readback, and all eight
   post-write setpoints; then identify the first registered guard crossing in
   each action trace.
2. **The frozen `Qref` field may not behave like the assumed same-sign
   independent reactive-power tracking port.** Compare the zero-arm-subtracted
   target `Qe` change at the first native sample and at 0.5 s against the
   requested sign, and inspect the sealed installed REGCV1 equations.
3. **The `kw=0`, `D=0` active loop (no explicit frequency-droop feedback or
   D-term damping) and PI loops without registered saturations may contribute
   to perturbation growth.** Compare zero/action arms, the order of voltage/
   current/power/speed events, and native early-termination messages against
   the frozen card and source equations.
4. **Initialization, source drift, non-finite values, or action leakage create
   a false failure.** Check the formal integrity, source/reference, residual,
   finite-value, and raw action evidence before any physical interpretation.

Hypothesis 4 is rejected and hypothesis 1 is directly supported. Hypothesis 2
is a supported early-transient observation plus a source-level absence of a
direct same-sign guarantee; it does not establish terminal sign failure or the
cause of the electrical excursions. Hypothesis 3 is a source-and-trace-
consistent mechanism hypothesis, not a modal stability proof or a claim about
every possible REGCV1 parameterization.

## Evidence decomposition

### Construction and software identity are not the failure

- All 17 ordered arms were attempted and captured; `execution_error=null`.
- Every arm has successful setup, power flow, reference-source preservation,
  native initialization/test, zero non-tolerance initialization residuals, no
  clamped-limit row, and finite stored DAE/REGCV1 values.
- All 16 intervention receipts reproduce the requested absolute setpoint within
  `1e-12`; the target readback matches; every non-commanded device/channel
  setpoint is unchanged.
- The zero arm completes 2.0 s with native convergence and remains inside all
  voltage, current, apparent-power, and virtual-speed guards.

The aggregate formal `action_identity=false` is not evidence of write leakage:
the inherited compound check returns false when any arm has a scientific-error
sentinel. Independent receipt replay establishes exact write identity in all
16 action arms.

### Failure chronology

Every one of the 16 action arms leaves at least one registered electrical
envelope. Fifteen first cross a bus-voltage bound; the remaining arm first
crosses apparent power. The first registered event occurs between
`0.7666666666666666 s` and `1.3000000000000007 s`, with median
`0.9549693697916666 s`. Across the action bank:

- 16 cross the bus-voltage envelope;
- 10 cross the current-magnitude bound;
- 13 cross the apparent-power bound;
- six cross the virtual-speed envelope; and
- eight terminate early with native nonconvergence between
  `1.026536619317691 s` and `1.990480459866156 s`.

The early-termination console symptom is `Time step reduced to zero.
Convergence is not likely.` The corrected evidence schema retains each complete
partial trace and classifies it as a scientific solver failure rather than an
integrity defect.

### Directional actuator diagnosis

Diagnostic-only zero-arm subtraction shows that the target-device `Qe` change
has the opposite sign to the requested `Qref` step in all eight `Qref` arms at
the first native sample and 0.5 s. For `Pref`, four of eight arms have a
target-device `Pe` change with the requested sign at both checkpoints. These
are sign-only transient observations, not the registered terminal magnitude-
floor test, which cannot be computed for a bank containing advanced partial
failures.

The exact installed REGCV1 source bound by the seal has the following relevant
structure:

- `Pref2 = ue * Pref - dw * kw` and
  `M * d(dw)/dt = Pref2 - Pe - D * dw`; the frozen card has `kw=0`, hence
  no frequency-droop feedback, and `D=0`.
- `Qref` enters `vref2` through `(ue * Qref - Qe) * kv + vref`, with
  `kv=0.01`; it is not a direct post-initialization `Qe` tracking equation.
  Every registered device has `ue=1` in this bank.
- The voltage and current PI loops have no registered saturation/current-limit
  element that enforces the R388 guard bounds during the run.

This source structure shows that a correct software write has no direct
equation-level guarantee of the gate's assumed same-sign independent P/Q
response. The zero/action contrast, early sign observations, voltage-first
chronology, subsequent current/power growth, and step-size collapse are
consistent with an inadequately damped and unconstrained closed-loop response
under this exact card, but do not isolate that mechanism causally. R388 does
not perform eigenanalysis and therefore does not claim a certified unstable
mode.

## Root-cause boundary and disposition

The primary gate-level cause is a genuine solver/electrical failure after exact
action application: all action arms violate the registered envelope and half
terminate without native convergence. The indirect `Qref` equation and the
early opposite-sign changes expose a mismatch with the assumed independent
same-sign port, but do not prove terminal sign failure or cause the solver and
electrical failures. The current REGCV1/card/port formulation nevertheless
fails Q-0106 before deterministic decoupling or learning.

No R388 retry, smaller step, card tuning, threshold relaxation, controller, or
training is allowed. A different converter model, a differently defined
physical power port, or a changed card would be a new route decision with a new
object qualification sequence; it is not a repair or continuation of this
formal result.
