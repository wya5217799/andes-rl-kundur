# Owner route decision — external-solution alpha line-sweep on the stopped first-order family

## Decision

The repository owner (author/PI) approved on 2026-08-16 the external
mathematical review's specific request to reopen the frozen first-order
frequency-selective damping family (R376-R379) for ONE bounded line search.
Authority: the external solution's P2 analysis
(tmp/yang_md_decoupling_marl/external_solution_assessment.md and
external_solution_v2_root_cause.md) shows the two frozen points (alpha 0.60:
r_d 0.962 / cross 0.79; alpha 0.90: r_d 0.914 / cross 1.15-1.29) do not prove
first-order impossibility: the sharp two-frequency selectivity bound is 4.76
and linear interpolation predicts a feasible point near alpha ~ 0.675.

Frozen sweep contract:

- Same object, same development bank (60 trajectories), same estimators,
  same thresholds (differential energy <= 0.95, probe cross <= 1.10,
  no-harm guards) as R376-R379.
- Frozen alpha grid: {0.675, 0.625, 0.65, 0.70, 0.725, 0.75, 0.80, 0.85}.
  First evaluated point: 0.675. No gain, order, corner, or grid change is
  authorized inside the round.
- Decision tree:
  - any grid point passes both endpoint thresholds and every guard ->
    SWEEP-FOUND-CANDIDATE (a separately registered held-out gate follows);
  - no grid point passes -> SWEEP-NO-CANDIDATE, closing the first-order
    family within the grid; no further first-order work is authorized.
- No held-out evaluation bank access, no training, no title-positive claim.

This decision reopens nothing else: every other R375-R382 stop rule stays in
force. The round executes on the paralleled-vsg-marl line after R405
completes (host budget sequencing: other_reserved_processes accounts for any
concurrently executing line).
