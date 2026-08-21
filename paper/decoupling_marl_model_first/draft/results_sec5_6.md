# Results draft — Sections V-VI (paper-writer, 2026-08-14)

Status: first draft of Sections V (Deterministic baseline, residual
headroom) and VI (Information families, mechanism diagnosis). All numbers
are taken verbatim from the bound feeds/claims (R344/R350/R356/R358/
R359-R363, CLM-0910/0915/0930/0940/0945-0965); the prose never exceeds the
allowed-claim wording of each feed. Delivery notes at the end.

---

## V. Deterministic baseline, residual headroom, and information families

This section reports the bounded deterministic gain, the residual-headroom
upper bound, and the information-family gate outcomes produced by the
sealed bank.

### A. Bounded deterministic gain

The sealed physical bank contained sixteen scenarios (two locally
constructed operating points, four active-load locations, both signs),
each executed as a matched pair of 25-sample trajectories (32 formal
trajectories in total). Relative to the paired zero-control arms, the
frozen centralized deterministic controller reduced the mean
common-coordinate integral absolute error by 95.5% and the mean summed
differential-coordinate squared error by 99.3%. Both endpoints improved
directionally at both operating points, every nonzero case engaged the
controller, and no scenario violated the registered 5% no-harm limit. As
preregistered secondary diagnostics that did not enter the classifier, the
scenario-mean frequency IAE fell from 0.00114 to 0.00005 Hz-s and the mean
per-trajectory maximum pairwise frequency deviation fell from 0.00104 to
0.00009 Hz. These are finite-bank transient summaries over one centralized
controller; they establish a bounded deterministic gain and nothing about
stability, safety, distributed execution, or learning.

### B. Residual headroom: the oracle upper bound and physical feasibility

The residual-headroom gate asks whether a zero-common three-edge residual
action, passed through the exact physical projection, can improve the
common endpoint by at least 2% without differential degradation. The
outcome-seeing offline oracle, which ignores every information constraint,
improved the mean common-coordinate IAE by 1.9999998%, i.e. 1.7e-9
short of the strict 2% floor, while improving the differential endpoint by
5.1%; the joint nominal gate therefore did not pass. The held-out
endpoint-local linear proxy, which uses only the two endpoints of each
edge at the causal pre-action time, improved the common endpoint by 0.14%
and worsened the differential endpoint by 14.1%. Both candidates also
failed the mismatch-bounded endpoint gates. The frozen decision tree
returned NO-TRAINING.

Two further feasibility layers bound where physical headroom does and does
not exist. In the relaxed problem (the three edge actions unbounded, all
physical and information restrictions removed), six of the sixteen exposed
cases are certified infeasible for simultaneous 2% improvement in both
endpoints. Adding the exact physical limits to the ten relaxed-optimal
cases leaves all ten accepted with zero linear, power, ramp, and SOC
violations and a minimum SOC margin of 0.235, i.e. per-case physical
action-space headroom exists in ten of the sixteen exposed cases, while
six remain infeasible even in the relaxation.

### C. Information families

Four pre-registered, tuning-free causal map families (fixed affine, RBF
kernel ridge, 5-nearest-neighbour, and quadratic polynomial) were fitted
per edge with leave-one-scenario-out validation and passed through the
exact physical projection. The gate was run over three progressively
richer information configurations: 15-field endpoint-local observations
(snapshot), tested with the affine family and with the three nonlinear
families; the same 15 fields plus one-hop neighbour state messages
(23 fields); and four-step model-prediction messages from the two ring
neighbours replacing the snapshot messages. No family cleared either
endpoint group in any configuration. Table II reports mean nominal
common-coordinate improvement (2% paired gate) and the differential
mean signed relative change, where values above 1 denote worsening.

Table II. Information-family gate outcomes: mean nominal common-coordinate
improvement (percent; the 2% paired gate) and differential mean signed
relative change (multiplicative; values above 1 denote worsening) for each
tested family under the three registered information configurations. No
family cleared either endpoint group. Source: R359-R362 feeds.

| Variant | Affine | RBF | 5-NN | Quadratic |
|---|---|---|---|---|
| Snapshot, common | 0.50% | 0.92% | 0.89% | 1.11% |
| Snapshot, differential | 6.12x | 14.56x | 5.80x | 36.93x |
| One-hop messages, common | 1.06% | 1.01% | 0.79% | -0.95% |
| One-hop messages, differential | 0.94x | 19.81x | 5.05x | 142.74x |
| Prediction messages, common | 0.68% | 1.15% | 1.29% | -0.06% |
| Prediction messages, differential | 3.78x | 32.68x | 4.85x | 672.93x |

The mismatch-bounded endpoint groups failed for every family in every
variant as well. Every integrity check passed in all four gates, so these
failures are gate outcomes of the frozen contracts, not data defects. The
results reject only the tested families under the frozen contracts; they
establish no claim about neural policies, which were never trained or
evaluated anywhere in this line.

## VI. Mechanism diagnosis: the zero-common action basis as structural limiter

This section reports the action-basis ablation that attributes the
negative headroom verdict of Section V.

The information-family negatives leave open whether the residual premise
fails because of information or because of the action basis itself. A
zero-common edge residual satisfies 1' p^r = 0: it redistributes power
among the four nodes and carries no fleet net power, so the common
endpoint can only be improved indirectly through cross-coupling. The
mechanism gate extended the frozen three-edge basis with one fleet-equal
common residual-power channel, the four-channel node-action basis
[1, B_a], and re-solved the identical physically constrained joint
endpoint QP on the same sixteen exposed development cases. All sixteen
cases became physically feasible, versus the ten-of-sixteen three-edge
baseline, and every one of the six previously infeasible scenarios was
unlocked. In every feasible case the common-coordinate ratio reached
0.0000-0.0002 (the registered 2% improvement achieved with essentially the
entire common endpoint removed) with zero differential degradation and
zero physical-limit violations.

This is an information-unconstrained physical feasibility statement: it
shows that the zero-common residual contract itself, not information
availability, is the binding structural constraint on common-coordinate
headroom. The common endpoint cannot be reached through zero-sum edge
channels alone, while a fleet-equal channel removes it directly. It
does not establish that any information path or learning method can select
the common channel, it does not overturn the information-family negatives,
and it authorizes no controller or learning conclusion. The result also
breaks the fleet-neutrality assumption of the earlier residual contract:
any successor formulation must re-derive the power/energy contract before
execution claims are possible.

---

## Delivery notes (not part of the manuscript)

1. The family table above will be typeset with per-cell footnotes pointing
   to the four feeds (R359-R362); the snapshot affine row uses the R359
   mean ratio 0.9950 (0.50% improvement).
2. Rounding: 1.9999998% and 1.7e-9 are the sealed R350 values; the draft
   deliberately keeps the near-miss precision because it is material to the
   headroom verdict.
3. Sections VII (Discussion/limits), II (Related work), I (Introduction),
   VIII (Conclusion), and the Abstract follow in later passes; the
   Related-work section waits for the verified differentiation memo.
