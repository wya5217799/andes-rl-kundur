# R389 strict scientific-stop diagnosis

## Immutable symptom and feedback contract

The unique sealed R389 execution is immutable. Diagnosis reads only its
create-only artifacts and the source files bound by the formal seal; it does
not replace the trajectory, tune the card, relax the threshold, or rerun the
scientific object. The formal classifier returns
`STOP-REGF2-OBJECT-INITIALIZATION` with record integrity true. Eleven of the
twelve registered scientific/integrity checks pass. Only `zero_input_drift`
fails.

## Ranked hypotheses and discriminating probes

1. **A coherent growing sampled pattern prevents a stationary trajectory with
   no exogenous post-init action or disturbance.** Recompute the time-indexed
   norm of all Pe, Qe, and bus-voltage deviations and the first registered
   threshold crossing.
2. **The failure is a reference, initialization-residual, limit, or non-finite
   artifact.** Check exact post-PFlow/pre-init source preservation, all 164
   initialized equations, clamped-limit rows, finite-value guards, and native
   solver flags.
3. **A correlated numerical/model-solver interaction contributes the growing
   pattern.** The TDS tolerance is a nonlinear residual tolerance, not a
   directly comparable output-error scale; only tolerance/step sensitivity
   could separate this alternative.
4. **A fast REGF2 voltage/reactive/current or VSM/PLL loop contributes the
   growing mode.** Compare channel chronology with the sealed REGF1/REGF2
   equations and time constants. This source-only probe can rank a mechanism
   candidate but cannot identify a causal eigenmode.

Hypothesis 2 is rejected. Hypothesis 1 is directly supported as a trace-level
description. Physical modal growth and correlated numerical/model-solver
growth remain unresolved. Hypothesis 4 is a bounded mechanism hypothesis
only; R389 contains no linearization, eigenanalysis, gain ablation, or
tolerance-sensitivity bank.

## Evidence decomposition

### Construction, initialization, and electrical guards are not the failure

- The exact packaged XLSX/JSON and derived static-case hashes, installed REGF1
  and REGF2 source hashes, unchanged 10-bus/15-line inventory, and four
  one-to-one REGF2/PLL2 mappings pass.
- Both the stock 900-MVA device-base input card and the deterministic 100-MVA
  system-base runtime card pass. No forbidden dynamic/event model or DAE name
  remains.
- Setup, power flow, TDS initialization/test, native convergence, and the
  complete 0.2-second horizon pass. `execution_error=null`.
- Post-init Pref/Qref exactly preserve the captured static P/Q sources at
  `1e-12`. All 164 initialization equations have zero registered residuals at
  `1e-6`, and there are no clamped-limit rows.
- DAE and REGF2 values remain finite. Every stored bus voltage, current,
  apparent-power, and virtual-frequency sample remains inside the broader
  registered electrical envelope.

### Failure chronology and magnitude

The registered drift ceiling is `2e-4` system pu. At 0.1666667 seconds, all
four Qe traces and the Pe traces of REGF2_1 and REGF2_2 first exceed it. At
0.2 seconds, all four Pe traces, all four Qe traces, and all ten bus-voltage
traces exceed it; only REGF2_1 also exceeds the same drift ceiling in virtual
frequency. The largest absolute deviations are:

- REGF2_4 Qe: `0.006147310127784245` system pu;
- REGF2_3 Qe: `0.004205782748280207` system pu;
- REGF2_1 Qe: `0.003158486501043667` system pu;
- REGF2_2 Qe: `0.0024043953695693787` system pu;
- REGF2_1 Pe: `0.0023689297477620386` system pu; and
- maximum bus-voltage drift: `0.0007896462484743294` pu at bus 1.

On the 100-MVA system base, the largest Pe/Qe deviations correspond to about
0.237 MW and 0.615 Mvar, respectively. These values do not violate the broad
electrical envelope; they violate the prospectively registered stationarity
criterion.

The Euclidean norm of all Pe/Qe/bus-voltage deviations is
`6.03e-7`, `2.37e-6`, `1.91e-5`, `1.51e-4`, `1.18e-3`, and
`9.26e-3` at successive 1/30-second samples from 0.0333 to approximately 0.2
seconds. From 0.1 seconds through the final distinct native sample, the three
successive ratios are about 7.90, 7.84, and 7.83; a least-squares fit of
`ln(norm)` versus time gives `61.85 s^-1`. This is a diagnostic fit over one
short deterministic trajectory, not an identified eigenvalue or stability
certificate.

### Source-consistent mechanism boundary

The sealed REGF2 source uses a VSM integrator with
`Tint = mf*wdrp = 0.00495 s`; its input includes the
`plldw*dd*wdrp` term, the active-power limiter loop, sensed active power, and
virtual speed. The inherited REGF1 plant has 0.005-second sensed-power and
inner-loop time constants, a 0.025-second power-signal lag, active/reactive PI
limit loops, voltage PI loops, and current PI loops. All four Qe traces and two
Pe traces first cross the drift ceiling in the same stored sample, Qe has the
largest observed deviation, and the full bus-voltage field crosses by the
sample at approximately 0.2 seconds, while all broad guards and solver flags
remain valid.

That chronology shows prominent Qe and bus-voltage components and identifies
reactive/voltage, active-power/VSM, and PLL-linked loops as source-visible
candidates. It does not establish modal participation, which loop causes the
pattern, whether it is a physical small-signal instability or a
numerical/model-solver interaction, or whether another card would remove it.
Distinguishing those alternatives requires a new prospective mechanism study,
preferably equilibrium linearization/eigenanalysis before any new trajectory
or parameter sweep.

## Root-cause boundary and disposition

The gate-level basis is proven: the exact stock four-REGF2 object is not
stationary enough under the registered 0.2-second drift criterion when no
exogenous post-init action or disturbance is applied, despite clean native
initialization, convergence, finite values, and broad electrical
admissibility. The trace supports a coherent growing-pattern description, but
R389 does not prove a particular physical or numerical root cause.

Q-0107 must close negative. Stock REGF2 stops before Paux/Qaux authority,
deterministic decoupling, controller comparison, or MARL. No R389 retry,
tolerance change, shorter horizon, threshold relaxation, card tuning, or
post-init action is authorized. A mechanism-only linearization question or a
different pre-specified converter object would require a new prospective
route decision.
