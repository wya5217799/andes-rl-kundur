# Successor design decision — external-solution-guided static homogenization + ring-edge bandpass

## Decision

The repository owner (author/PI) approved on 2026-08-16 the
external-solution-guided successor direction after the R404 terminal learner
stop. The fixed title, the Yang-compatible four-VSG direct-M/D object, the
eight-profile canary bank identity, the matched-permission protocol, and every
registered threshold stay frozen. The new episode is a **classical deterministic
control structure**, not a learner:

1. **Candidate A — static M/D homogenization.** Per profile, every VSG moves
   its inertia and damping to one common value pair (m*, d*) chosen inside
   the intersection of the four units' individual action boxes
   (M_i in [max(20, M0i-200), M0i+600], D_i in [max(10, D0i-200), D0i+600]),
   starting from the external moment-matched point
   1/m* = mean_i 1/M0i, d* = m*^2 mean_i D0i/M0i^2, clipped to the common
   feasible interval. The move is slew-limited (0.25 normalized per 0.2 s
   step) and then held constant; no dynamic feedback is added.
2. **Candidate B — 0.4 Hz second-order positive-real ring-edge bandpass.**
   Each ring edge filters the two endpoint frequency differences through
   F(s) = K * 2*zeta*wm * s / (s^2 + 2*zeta*wm*s + wm^2), wm = 2*pi*0.4, and
   returns the edge power p = M v, v = -B_r F(s) B_r^T omega. 1^T v = 0 by
   construction, so the controller is exactly transparent to arithmetic
   common frequency. B is only deployed after A is physically characterized.

Authority chain: census PROCEED (tmp census 2026-08-16) ->
owner approval -> this decision record -> prospective evidence round.

## Why this is not a retry of a stopped family

- R369/R399 stopped the **dynamic M/D output-feedback laws with zero static
  bias**; candidate A is a **nonzero static bias** — the external theorem says
  only the static bias moves the first-order cross channel, so this is the one
  untested degree of freedom, not a new member of the stopped dynamic family.
- R376-R379 stopped **first-order frequency-selective channels**; candidate B
  is second-order and spatially projected (ring-edge), a materially different
  structure.
- R375/R381/R382/R404 stops remain untouched; no gain/corner change, retry,
  oracle expansion, training, tuning, or learner replacement is authorized.

## Gate sequence

### Gate A (this round) — linearization + candidate A disclosed-development gate

1. Numerically linearize the ANDES four-VSG modified-Kundur model at each of
   the eight canary profile operating points (profile baseline_m0/d0 and
   steady_loads from the R401 seal). Validate each linearization
   (state-matrix vs. EIG, residual, finiteness), extract the reduced 4x4
   network matrix L, and check L1, 1^T L, and [Pc, L]. Archive the
   linearizations as analysis tools.
2. Run the candidate-A static homogenization arm on all 48 disclosed canary
   scenarios (24 development + 24 evaluation) with the frozen estimators and
   thresholds, against the sealed km2_kd2 deterministic reference values
   (R402, 24 evaluation records) and an in-round matched re-run of km2_kd2
   (must reproduce the sealed values within tolerance).
3. Decision tree (all thresholds frozen):
   - PASS-A: r_cross <= 0.95 **and** r_d <= 0.95 and every no-harm guard
     passes -> authorize the A+B round.
   - PARTIAL-A: r_cross <= 0.95, r_d > 0.95, no-harm passes -> proceed to
     the A+B round per the approved plan; no title claim.
   - NO-CROSS-EFFECT: r_cross > 0.95 -> network-asymmetry dominated;
     owner call before any further physical work.
   - GUARD-FAIL: any completion/saturation/no-harm/stress guard fails ->
     candidate A stops; no retry or repair inside this round.
4. This round performs no training, touches no unseen bank, and produces no
   title-positive claim.

### Gate B (later round) — candidate A+B disclosed-development gate

Same bank, same estimators, same thresholds; A provides the homogenized bias,
B the bandpass edge damping. A later fresh-bank sealed evaluation is only
authorized after a disclosed-development pass.

## Reuse boundary

- Reusable: R380 source-model linearization infrastructure (adapted to the
  M/D actuator and canary profiles), R399/R402 estimators and sealed-bank
  plumbing, the offline certificate checks under tmp/yang_md_decoupling_marl/.
- Never transfer: checkpoints, training curves, learned weights, stopped-family
  gains, and every historical result value; all stay design inputs only.

## Stop rules

- No training, tuning, or learner work in this direction until Gates A and B
  pass on disclosed development and a fresh-bank sealed evaluation is
  separately registered.
- A failed gate stops that candidate without gain/order/corner change or retry.
- Offline linear-model results are analysis tools, never title evidence.
- The alpha sweep on the old first-order family is a separate owner
  authorization on the paralleled-vsg-marl line and is not part of this round.
