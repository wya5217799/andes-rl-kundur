# R391 strict diagnosis

## Decision

R391 is a valid scientific stop, not an execution or analysis failure. The
authoritative classification is `STOP-REGF2-POSITIVE-REAL-GUARD`. The exact
R389 four-REGF2 equilibrium contains reproducible positive-real directions in
the finite ANDES reduced state matrix before any simulation time advances.
This strongly disfavors time stepping as the sole explanation for R389's
growth, but it does not establish instability of a physical converter,
hardware implementation, or broader REGF2 family.

## Immutable evidence

- Formal seal SHA-256:
  `59c480f793dc8974958496a0c7c4926b44aa6b2d242077fea23961df155a6cea`.
- Formal attempt SHA-256:
  `18a903b25452829bafc8b7734d1871768c7d15734ba56a94b85813740f04fb1b`.
- Formal execution SHA-256:
  `77231c9b95de877c83ed1d4a09710168b6bb249bb1c4b7c1d4e7561a9c7543d8`.
- Formal analysis SHA-256:
  `170658c967798aced2f4b62b614dd2863d2a8445ea4e92fbc2ac05968731619e`.
- Formal manifest SHA-256:
  `47b8ff337f47161ea8309b9e606d2dc719038d2974449551e515aa8f966c715f`.

The record contains two fresh serial arms at native initialization tolerances
`1e-4` and `1e-6`. Neither arm calls `TDS.run()`, applies an action, changes a
controller, or trains a model. Both arms finish setup, power flow, native TDS
initialization/test, and EIG calculation with no execution or typed scientific
exception.

## Integrity and numerical checks

All registered integrity checks are true. In each arm:

- time is exactly `0.0` before and after EIG, and the archived x/y/z vectors
  are exactly unchanged;
- the complete 64-state, 100-algebraic-variable equilibrium has `max|f|=0`
  and `max|g|=3.745103976937614e-7`, with 164 equations, no registered bad
  residual row, no clamp, no zero-time-constant fold, and no dead algebraic
  row;
- the 64 by 64 reduced matrix, every DAE/reduced catalog, the equilibrium
  snapshot, and the four reference rows are identical across the two arms;
- ANDES and independent SciPy spectra match with normalized distance `0.0`;
  the maximum normalized eigenpair backward error is
  `1.8868120112399466e-15`, and the leading eigenvector condition number is
  `8.353337703423357`.

These observations strongly disfavor an eigen-solver failure, sparse-adapter
failure, tolerance-dependent initialization, or time-integration artifact as
the source of the leading positive-real result.

## Spectrum diagnosis

The sealed runtime reports three roots above the prospective `1e-7` guard:

| Root | Real part (`s^-1`) | Imaginary part | Interpretation boundary |
|---|---:|---:|---|
| leading | 46.41533383454654 | 0 | well separated; e-folding time 0.0215446 s |
| second | 4.606789511264594 | 0 | well separated; e-folding time 0.217071 s |
| third | 6.452814682866848e-7 | 0 | inside the registered `1e-6` near-zero region; do not interpret as a material physical mode |

The formal threshold count remains three because that was the frozen rule.
The mechanism conclusion does not depend on the near-zero third root: the two
well-separated real roots are far above both the sign guard and numerical
error scale and reproduce exactly between arms.

## Diagnostic participation, not causality

A diagnostic-only full-precision biorthogonal participation replay of the
sealed first-arm matrix associates the leading root almost entirely with
REGF2 states (`99.9795%` aggregate) rather than PLL2 states (`0.0205%`). Its
largest state-family shares are virtual angle `delta` (`45.48%`), active-power
signal `Psig_y` (`15.82%`), active-power sensing `Psen_y` (`8.56%`), and the
VSM speed integrator `INTw_y` (`8.50%`). The second root is likewise dominated
by REGF2 (`99.9274%`), especially the d-axis outer-voltage PI integrator
`PIvd_xi` (`52.64%`), virtual angle (`23.57%`), and active-power signal
(`11.44%`).

Participation is state association, not output observability, loop causality,
or proof that one gain is incorrectly tuned. The installed equations expose
coupled active-power sensing/signal/limit/VSM-angle and voltage/current PI
loops, but no counterfactual parameter or loop-removal experiment was
authorized in R391.

## Relation to the R389 trajectory

R389's diagnostic sampled-output norm had a fitted log-growth slope of
`61.85 s^-1`; R391's leading local rate is `46.4153 s^-1`, about `24.95%`
lower. The local root predicts a one-sample (`1/30` s) gain of about `4.70`,
whereas the late R389 sampled ratios were about `7.83` to `7.90`. The sign and
fast time scale are compatible with model-embedded growth, but the rates do
not quantitatively identify the R389 trace as a single linear mode. Multiple
modes, algebraic output sensitivity, and departure from the infinitesimal
neighborhood remain possible.

## Ranked diagnosis

1. **Supported endpoint:** the exact initialized ANDES phasor-domain
   REGF2/Kundur reduced model has reproducible local growing directions.
2. **Strongly disfavored as sole cause:** TDS time integration, initialization
   tolerance, sparse conversion, or the eigensolver; the result exists before
   time advances and passes the registered independent numerical checks.
3. **Unresolved mechanism:** which installed REGF2 feedback path or parameter
   combination causes the two material roots. Participation narrows the
   associated states but cannot answer causality.
4. **Unresolved fidelity boundary:** whether the local growth is representative
   of a calibrated physical converter. No EMT, switching, hardware, field,
   uncertainty, or cross-model evidence exists.

## Disposition

Q-0108 can close positive through CLM-1100, while the experimental route stops
negative before Paux/Qaux authority, deterministic decoupling, controller
comparison, or learning. R391 authorizes no parameter tuning, alternative
card, controller, topology, EMT, HIL, or deployment experiment. Any causal
loop isolation or different converter object requires a new prospective route
decision and cannot be treated as an R391 retry.
