# Discussion and Conclusion draft — Sections VII-VIII (paper-writer, 2026-08-14)

Status: first draft of Sections VII (Discussion and limits) and VIII
(Conclusion). Bound to the limits and allowed-claim wording of R344, R350,
R356, R358, R359-R363. Delivery notes at the end.

---

## VII. Discussion and limits

This section states what the diagnostic chain licenses and what it
refuses, and enumerates the exact scope of every reported number.

### A. What the diagnostic chain says, and what it does not

The three diagnostic layers make the negative verdict attributable rather
than anecdotal. The outcome-seeing oracle shows that almost no nominal
residual value remains after the deterministic controller: the
outcome-seeing offline upper bound reaches the 2% common-endpoint floor to
within 1.7e-9 and no further. The information-family gates then show that
the tested causal maps, with progressively richer neighbour information,
cannot even approach that bound without degrading the differential
endpoint. The action-basis ablation finally shows where the headroom went:
a zero-common basis structurally cannot touch the common endpoint, and one
fleet-equal channel removes it almost entirely. The bottleneck is therefore
the residual contract's action basis, not the information path. This is the
mechanism-level lesson of the paper: before training a distributed learned
residual, verify that the reserved action basis still carries authority
over the endpoint the residual is supposed to improve.

Two disciplined readings are rejected. The negative family results do not
establish that residual learning is impossible or useless in general: they
reject only the four tested tuning-free families under the frozen contracts
on one plant, and no neural policy was ever trained or evaluated. Nor does
the common-channel result establish that a learning method can select the
common channel under causal information; it is an information-unconstrained
feasibility statement. The common channel also breaks the fleet-neutrality
assumption that the deterministic contract reserved for itself, so any
successor formulation must first re-derive the power and energy contract.

### B. Scope of every reported number

Every quantitative statement in this paper is a finite-bank transient
summary: one modified Kundur phasor-domain topology, two locally
constructed operating points, four active-load locations with both signs,
25-sample transients, offline linear-response maps for the headroom gates,
and a centralized deterministic controller. The headroom results read no
holdout cases. The result archive is local and not publicly pushed. The
paper therefore claims no stability certificate, no safety argument, no
robustness outside the registered bank, no topology generalization, no
EMT, HIL, or deployment evidence, and no conclusion about any simulator
other than ANDES 2.0.0. These are not rhetorical hedges; they are the
exact boundaries the sealed gates enforced.

### C. What transfers conceptually

Three design lessons transfer independently of the specific plant. First,
an implementation-faithful contract with canary stages converts simulator
defects into caught failures instead of silent evidence: the repairs listed
in Section III-E changed measured endpoints and would have invalidated any
unchecked study. Second, the headroom-first sequence (deterministic
baseline, outcome-seeing upper bound, causal map families, action-basis
ablation) is a reusable decision procedure that returns an attributable
answer before training compute is committed. Third, zero-sum distributed
action bases cannot reach fleet-common endpoints; common-mode authority
must be designed in or consciously excluded from the start. What does not
transfer is every measured number and every controller: they are evidence
for this plant and this frozen contract only.

## VIII. Conclusion

This paper presented an implementation-faithful, gate-sequenced
methodology for storage-coordinated paralleled VSGs and demonstrated it
end to end on a modified Kundur phasor-domain plant. The implementation
contract reconciled the intended equations with the executable simulator
and its canary stages validated the actuator path before any controller
result was accepted. Under this discipline, the sealed paired bank
produced a bounded deterministic gain and a bounded negative: the
controller reduced the two registered endpoints by 95.5% and 99.3% over
matched zero control, the
outcome-seeing residual upper bound stopped at the 2% common-endpoint
floor to within 1.7e-9, and the tested causal map families added no
qualifying increment under any of the three registered information
configurations. The action-basis ablation completes the diagnosis:
extending the zero-common
three-edge basis with one fleet-equal common channel makes all sixteen
exposed cases physically feasible versus ten of sixteen without it,
identifying the zero-common residual contract, not information
availability, as the structural limiter of common-coordinate headroom.

The negative results in this paper are gate outcomes of the proposed
protocol, not a verdict on learning in general. The positive contribution
is the protocol itself: it established a real deterministic gain, caught
its own fidelity defects, refused training when the measured headroom
could not justify it, and named the mechanism. For the next study, the
operational lesson is direct: design common-mode authority into the
action basis, and re-derive the power and energy contract before any
residual layer is trained.

---

## Delivery notes (not part of the manuscript)

1. Sections I, II, and the Abstract are drafted after the verified
   differentiation pool arrives; Section II will carry the citations.
2. The two "rejected readings" in VII-A implement the hard wording ceiling
   of the argument contract (no unlearnability claim; no causal claim for
   the common channel).
3. Title candidates for PI sign-off will accompany the Abstract.
