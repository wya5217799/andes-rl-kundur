---
round: R298
state: completed
opened: '2026-08-02'
closed: '2026-08-02'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R298 plan -- held-out relative-RoCoF residual evaluation

**Opened**: 2026-08-02
**Driver**: Convert the R297 development candidate into a valid or negative
held-out result before any paper or neural comparison.
**Parent**: Q-0055; CLM-0695.

## TL;DR

Run 36 fresh trajectories on the 12 cases predeclared before R297 outcomes:
baseline explicit DAPI, selected full-anchor residual DAPI, and centralized
vector PI. Freeze paired bootstrap uncertainty, physical/zero-sum guards, and
the comparison ceiling before any formal trace.

## Snapshot at plan-time (oracle as of 2026-08-02)

<!-- Auto-injected by reserve_round.py; preserve as plan-time navigation. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) -- verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0055 [opened R298] Does the selected zero-sum relative-RoCoF DAPI residual retain held-out fast inter-area value against fresh DAPI and centralized vector PI?

## Recently Closed (last 3)

- Q-0054 closed-positive @ R297, by CLM-0695 -- full-anchor development candidate.
- Q-0053 closed-negative @ R296, by CLM-0690 -- half-anchor boundary no-go.
- Q-0052 closed-negative @ R295, by CLM-0685 -- consensus-time-scale no-go.

## Methodology

Use exactly the 12-case Cartesian bank stored in the R297 seal:
`tie k={1.25,1.75} x location={PQ_0,PQ_1,PQ_Bus15} x sign={-1,+1}`.
These exact operating points were not executed in R294--R297 controller
selection. `k` is an impedance-strength proxy within one electrical topology.

Run three arms for 100 steps at 0.2 s with zero M/D modulation and the same
four ESD1 devices and power/current/ramp/SOC/energy projection:

1. explicit neighbour-only DAPI with `Kv=0`;
2. explicit neighbour-only DAPI with selected `Kv=0.2442407` and `tau=0.2 s`;
3. centralized vector PI with joint four-frequency information and `Ksync=1`.

All arms share `Kp=2`, `Ki=0.2`, vector active-power coordinates, horizon,
plant and constraints. The two DAPI arms also share `Kconsensus=1/s`, local
states, ring messages, and compute class.

## Comparison-identifiability gate

| Contrast | Information/action/execution | Allowed inference |
|---|---|---|
| residual DAPI vs baseline DAPI | all matched; `Kv` is sole treatment | incremental value of the executed residual on this bank |
| either DAPI vs centralized vector PI | same physical vector actions and constraints; different joint/local information and laws | executed-formulation comparison only |

Decision: `ALLOW` the primary residual contrast; `QUALIFY` centralized
contrasts; `BLOCK` pure architecture, MARL, topology, stability, safety,
robustness, EMT/HIL, or deployment conclusions.

## Frozen validity and statistical gate

All 36 records and sidecars must exist and pass finite telemetry, TDS, exit,
vector action, storage and physical guards. Both local arms require 100
mechanism samples and residual-sum error at most `1e-12`. Any failure makes the
bank `INVALID` and all performance endpoints non-evidence.

The unit is matched scenario. For each endpoint, compute candidate/reference
ratio of means and a paired 20,000-resample percentile interval with fixed seed
298004. The selected residual passes versus baseline DAPI only if:

- fast inter-area IAE point ratio is at most `0.99` and 95% interval upper
  bound is strictly below `1.0`;
- synchronization-loss point ratio is at most `1.0` and interval upper bound
  at most `1.01`;
- each common-endpoint interval upper bound is at most `1.05` and worst
  individual ratio at most `1.10`;
- every validity and zero-sum guard passes.

Classify `VALID-RELATIVE-ROCOF-PASS`, `VALID-RELATIVE-ROCOF-TRADEOFF`,
`VALID-RELATIVE-ROCOF-NO-VALUE`, or `INVALID`. Centralized comparisons are
secondary: one formulation is clearer only if both differential-endpoint
intervals lie wholly on the same side of one; otherwise report no joint winner.

## Asset preservation contract

- Preserve R274--R297 plans, seals, traces, decisions, feeds, verdicts and
  claims byte-for-byte.
- Add Q-0055/R298 state, one formal runner and focused tests, one JSON seal,
  and create-only records/summary with sidecars; no extra round Markdown.
- Use three scratch-isolated WSL shards. Do not tune, train, edit manuscripts,
  or inspect intermediate endpoints.

## Cross-references

- CLM-0695 authorizes exactly the selected gain and predeclared bank; it is not
  formal evidence.
