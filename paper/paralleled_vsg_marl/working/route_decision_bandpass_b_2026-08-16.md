# Owner route decision — candidate-B bandpass round on the paralleled energy-port channel

## Decision

The repository owner (author/PI) decided on 2026-08-16 that the candidate-B
0.4 Hz ring-edge bandpass stage is tested on the **paralleled-vsg-marl line's
native energy ports** (the power channel already exists there), not by adding
a power channel to the yang-md M/D object. The new-line candidate-A static
homogenization bias remains stopped by R405 (CLM-1180) and does not transfer;
the legacy M/D path on this line stays pinned to zero (R369/R375 stops remain
in force).

Frozen scope for the B round:

- Structure: second-order positive-real bandpass
  F(s) = K * 2*zeta*wm*s / (s^2 + 2*zeta*wm*s + wm^2), wm = 2*pi*0.4 rad/s,
  zeta = 0.35 frozen; bilinear discretization with pre-warping at 0.4 Hz;
  only the gain K is searched inside the round (external solution step 7).
- Channel: the feasibility-native VSG power ports of the R376-R379 object
  (same zero/local arms, same estimators, same thresholds 0.95 / 1.10,
  same 60-record development bank). The bandpass acts on the ring-edge
  frequency differences (B_r^T omega), exactly transparent to common
  frequency by construction (1^T v = 0).
- Decision tree: any frozen-K candidate passing both endpoint thresholds and
  every guard -> BAND-PASS (a separately registered held-out gate follows);
  otherwise BAND-FAIL (the bandpass stage stops without retry).
- No training, no M/D action re-enable, no held-out access, no title claim.

The alpha sweep (R406) closes the first-order family question independently;
this decision does not reopen any stopped family.
