# Converter-Level VSG P/Q-Decoupling Route Contract

## Decision

Use ANDES 2.0.0 on the unchanged Kundur two-area network. Replace the
`PV+GENCLS` proxy only within this line with four prospectively registered
converter-level VSG devices. The `REGCV1` branch closed at R388; successors
restart at object/initialization. Establish object validity, dynamic P/Q
authority, and deterministic P/Q-decoupling value before any learning
experiment.

Route family: F5 one-VSG-one-agent object reconstruction (F4 model-first
methodology). Not a sixth algorithm family; does not reopen the stopped
active-power-port formulation.

## Current disposition

Q-0108 closed positive by R391/CLM-1100 (stock-REGF2 stop); Q-0111 closed
negative by R397/CLM-1130 — the two-unit PPVSM1 cell fails the signed
authority gate on target attribution (a PPVSM1_1 Pref step moves PPVSM1_2's
Pe at least as far as the target's own). PPVSM1 stops before droop-slope
matching; no successor is authorized.

## Gate sequence

1. Qualify the exact object and independently signed P/Q authority.
2. Compare one physics-based decoupler with matched non-learning baselines.
3. Test non-learning residual headroom and causal information value.
4. Permit one residual-learning comparison only if Gate 3 passes.
5. Add robustness, topology, EMT, HIL, and deployment as separate later tiers.

## Fixed scope

- Platform: ANDES 2.0.0 under the registered WSL environment.
- Network: existing Kundur two-area connectivity and four controlled-unit
  locations.
- Closed initial formulation: the exact `REGCV1` card/port tested through R388.
- Selected successor: stock `REGF2` (installed-default parameters, 900-MVA
  rating at the same four locations).
- Current task: none. R397 closes the signed-authority gate and stops the
  two-unit PPVSM1 route; no authority, controller, or successor experiment is
  authorized.
- Evidence transfer: none from earlier lines.
- Implementation reuse: permitted after prospective tests and source binding.

## Resource policy

Short canaries stay serial. Each formal plan freezes its measured whole-host
budget and one native thread per worker.

## Stop and pivot rules

- Any pre-attempt repair requires a successor round, rehearsal, and seal.
- A valid negative object/authority result stops the tested formulation.
- A changed model, topology, or platform is a new prospective route decision,
  not a retry.
- Gates 1-3 authorize no learning, topology, stability, hardware, or deployment
  claim.

## R384--R388 REGCV1 disposition

R384 stops the status-disabled construction. R385 and R387 are analysis-
invalid; R386 passes the structurally clean object. R388 validly stops the
exact REGCV1/card/port at signed authority: all 16 nonzero arms breach a
guard, eight end in native nonconvergence. Another model/card/port restarts
qualification.

## REGF2 successor decision

The validated census selects stock REGF2 as the sole successor object
(family F5). The durable installed-source audit rejects REGCV2 as too close
to the stopped outer structure. R389 owns only exact object, initialization,
and no-action stationarity qualification; any failure stops before
Paux/Qaux authority.

## R389 disposition

CLM-1090 records a valid negative for the exact four-stock-REGF2 default-card
object: construction, initialization, diagnostics, completion, and
electrical envelopes pass; only no-action stationarity fails. Q-0107 closes
negative and the route stops before authority.

## R390 mechanism-only decision

The validated census selected the exact-R389, two-arm, no-time-advance
equilibrium/EIG diagnosis. R390 is invalid by CLM-1095 and supplies no modal
result.

## R391 disposition

CLM-1100 records a valid positive-real local-model stop: two no-time-advance
arms reproduce the same two material real roots with all integrity and
numerical guards passing. Not a physical-instability or causal-loop claim;
opens no authority, controller, or learning work.

## R392 disposition

CLM-1105 records a valid MECHANISM-MIXED attribution: the two R391
positive-real modes are carried jointly by the VSM inertia path, the power
sensing/signal chain, and the voltage outer PI; the rating arm restructures
the spectrum instead of repairing it. The stock-REGF2 route stays stopped;
counterfactual loop removal or single-device isolation needs a new
prospective route decision.

## PPVSM1 successor decision

The PI authorizes the survey main-design successor: a projected-passive
dual-droop VSM (PPVSM1) that deletes the power-sensing/limit-PI chain and
its eight conserved integrals, restores a dissipative swing equation, and
uses a gradient-flow Q-V outer loop with projected limits and a virtual
resistor. First cell: buses 1-2 (buses 3-4 static anchors). Four-unit
scaling is a later gate.

## R393--R396 PPVSM1 disposition

CLM-1125 closes Q-0110 positive: the two-unit PPVSM1 object passes
initialization, the 0.2-second zero-input stationarity gate, and the
spectrum guards. R393-R395 are analysis-invalid instrumentation attempts
(CLM-1110/1115/1120). Only a signed P/Q authority gate opens next.

## R397 disposition

CLM-1130 closes Q-0111 negative: the bank is admissible (all guards but
target attribution pass) but attribution fails on the two PPVSM1_1 Pref
arms — PPVSM1_2's achieved Pe magnitude exceeds the target's own. PPVSM1
stops before droop-slope matching and any controller or learning work;
successors need a new route decision.

## Survey conformance

Against the retained survey synthesis
(`three_report_future_experiment_route_synthesis.md`), two deviations are
accepted; neither reopens a closed round nor authorizes execution.
Details in the 2026-08-14 platform check note.

1. **Starting scale.** The survey's two-unit-first staging was adopted: the
   first cell replaces units 1-2 with StaticGen 3-4 static anchors;
   four-unit scaling is a later gate. Accepted risk: no single-device vs
   inter-device separation at larger scale.
2. **Device specification.** ANDES 2.0.0 is phasor-domain DAE only; survey
   F0 is satisfiable only in averaged form and F6 (EMT/HIL) is unreachable.
   The R384--R391 stops are object-level, not platform.

The route decision was taken in `PPVSM1 successor decision`; R397's
authority stop closes that branch, and any successor needs a new route
decision.
