---
status: accepted
---

# ADR-0022: Reactivate ICEMS 2026 with small-step evidence gates

## Decision

The owner reactivates `paper/icems2026` for a bounded positive-core manuscript
repair and, only if one decisive gap remains, a small prospective supplement.
This supersedes ADR-0015 only where it froze the ICEMS line: it does not turn
the shared scalar policy or the three-edge policy into four independently
acting VSG agents, and it does not weaken their registered positive and
negative results. Development proceeds one falsifiable question at a time;
no training, ANDES execution, broad algorithm search, or 200-cell-scale batch
is authorized by this decision. Any paper-facing supplement must later enter a
new evidence round with development and holdout identities frozen before
execution.

`decoupling-marl-model-first` may be read for mechanism definitions,
implementation ideas, strong deterministic-baseline design, and experiment
kill gates. Its plant/action object and numerical results do not transfer into
the ICEMS claim set. A model-first result may enter the ICEMS paper only after
an object-matched prospective reproduction owned by the ICEMS line; otherwise
it remains background or future-work rationale.

## Consequences

- `icems2026` becomes the highest-priority active manuscript line.
- The immediate action is a no-execution compatibility and claim-gap audit.
- The existing ICEMS paper remains defensible without a supplement; a new
  experiment is permitted only when the audit isolates one bounded question
  whose success, pivot, and stop outcomes are fixed in advance.
- A failed authority, deterministic-baseline, headroom, or title-fit gate stops
  that supplement before training rather than triggering another algorithm.
