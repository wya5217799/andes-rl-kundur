# Abstract and title candidates — for PI sign-off (paper-writer, 2026-08-14)

Status: draft Abstract (self-contained; no citations) and three title
candidates. The title is PI-owned; exact wording is fixed after this
decision. Bound to the allowed-claim wording of the feeds.

---

## Draft Abstract

Coordinating paralleled virtual synchronous generators (VSGs) with energy
storage is increasingly delegated to learned controllers, but the value of
a learned layer is rarely established before training compute is committed.
Three obstacles block this decision:
executable-plant fidelity, cross-coupled coordinates,
and attribution of a negative verdict. This paper presents
an implementation-faithful, gate-sequenced methodology
for storage-coordinated paralleled VSGs, demonstrated end to end on a
modified Kundur phasor-domain plant. A centralized deterministic
controller establishes a bounded storage-power-control gain: on a
sealed paired bank of sixteen scenarios it reduces the common-coordinate
integral absolute error by 95.5% and the differential-coordinate squared
error by 99.3%. The residual-headroom gate
returns a bounded negative: the outcome-seeing residual upper bound reaches
the registered 2% common-endpoint floor to within 1.7e-9, and four causal
map families under three progressively richer information configurations
add no qualifying increment. An action-basis ablation completes the
diagnosis: one fleet-equal common channel makes all sixteen exposed cases
feasible versus ten of sixteen,
identifying the zero-common residual contract, not information
availability, as the structural limiter of common-coordinate headroom.
The negative results are gate outcomes of the protocol, not a verdict on
learning; the transferable lessons are the fidelity
contract, the headroom-first decision procedure, and designing
common-mode authority into the action basis.

## Title candidates

1. "An Implementation-Faithful Model-First Methodology for
   Storage-Coordinated Paralleled VSGs: Bounded Deterministic-Control Gain
   and Residual-Headroom Limits"
   (current provisional; safest claim match)

2. "Gate-Sequenced Model-First Evaluation of Residual Control for
   Storage-Coordinated Paralleled VSGs: A Bounded Deterministic Gain and a
   Structural Diagnosis of Zero-Common Action Bases"
   (foregrounds the gate sequence and the mechanism finding)

3. "Model-First Gate Sequencing for Storage-Coordinated Paralleled VSGs:
   Deterministic-Control Gain and the Structural Limit of Zero-Common
   Residual Bases"
   (shortest; drops 'implementation-faithful' but keeps the mechanism)

All three drop the MARL term entirely; no candidate exceeds the registered
claim ceiling. Candidate 1 matches the current LINE.md working title.
